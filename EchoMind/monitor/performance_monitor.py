"""
亮点：利用 Monitor 监控 Agent 在线表现

核心问题：如何利用 Monitor 监控 Agent 的在线表现？

本模块的答案：
  1. 实时采集 —— 每隔 N 秒从 Orchestrator 和 ToolManager 拉取最新统计
  2. 异常检测 —— Z-score 统计方法，自动发现指标突变
  3. 路由反馈 —— 将 Agent 成功率/延迟写回 Orchestrator，
     Orchestrator 的 _best_agent() 会据此动态调整路由权重
  4. 优化建议 —— 基于规则生成可操作的优化建议（不是空话）
  5. 告警 —— 超阈值时打日志 + 可选 Webhook
"""
import asyncio
import logging
import os
import statistics
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

import httpx
from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)


# ── 数据结构 ──────────────────────────────────────────────────────────────────

class Severity(Enum):
    INFO     = "info"
    WARNING  = "warning"
    ERROR    = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    severity:    Severity
    metric:      str
    message:     str
    value:       float
    threshold:   float
    ts:          str = field(default_factory=lambda: datetime.now().isoformat())
    resolved:    bool = False


@dataclass
class Suggestion:
    """可操作的优化建议。"""
    title:       str
    detail:      str
    action:      str    # 具体操作步骤
    priority:    int    # 1-10


# ── 异常检测 ──────────────────────────────────────────────────────────────────

class AnomalyDetector:
    """
    基于滑动窗口 Z-score 的异常检测。

    Z-score = |当前值 - 均值| / 标准差
    超过 sensitivity 倍标准差则判定为异常。
    """

    def __init__(self, window: int = 60, sensitivity: float = 2.5):
        self._window      = window
        self._sensitivity = sensitivity
        self._history: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=window))

    def record(self, metric: str, value: float) -> Optional[Dict[str, Any]]:
        """记录一个数据点，如果异常则返回异常信息，否则返回 None。"""
        buf = self._history[metric]
        buf.append(value)

        if len(buf) < self._window // 2:
            return None  # 数据不足，不检测

        mean  = statistics.mean(buf)
        stdev = statistics.stdev(buf) if len(buf) > 1 else 0.0
        if stdev == 0:
            return None

        z = abs(value - mean) / stdev
        if z > self._sensitivity:
            return {
                "metric":   metric,
                "value":    value,
                "mean":     mean,
                "z_score":  round(z, 2),
                "severity": "high" if z > self._sensitivity * 1.5 else "medium",
            }
        return None


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("无效环境变量 %s=%r，使用默认 %s", name, raw, default)
        return default


# ── 性能监控器 ────────────────────────────────────────────────────────────────

class PerformanceMonitor:
    """
    Agent 在线表现监控。

    与 Orchestrator 的联动：
      Monitor 采集 → 发现某 Agent 成功率下降 →
      Orchestrator.get_stats() 中该 Agent 的 routing_score 自动降低 →
      _best_agent() 路由时自动绕开该 Agent

    这就是"利用 Monitor 监控在线表现"的闭环。
    """

    def __init__(
        self,
        orchestrator,
        tool_manager,
        interval_s:       float = 10.0,
        webhook_url:      Optional[str] = None,
        prometheus_port:  Optional[int] = None,   # None = 不启动
        *,
        agent_success_rate_threshold: Optional[float] = None,
        agent_avg_ms_threshold:       Optional[float] = None,
        tool_success_rate_threshold:  Optional[float] = None,
        tool_avg_ms_threshold:        Optional[float] = None,
        penalty_success_rate:         Optional[float] = None,
        penalty_avg_ms:               Optional[float] = None,
        suggestion_success_rate:      Optional[float] = None,
        suggestion_min_total:         Optional[int] = None,
        anomaly_sensitivity:          Optional[float] = None,
    ):
        # 告警阈值（默认适配远程 LLM：单次 Agent 调用 5–8s 属常见范围）
        self._agent_sr_threshold = agent_success_rate_threshold if agent_success_rate_threshold is not None else _env_float("MONITOR_AGENT_SUCCESS_RATE_THRESHOLD", 0.80)
        self._agent_ms_threshold = agent_avg_ms_threshold if agent_avg_ms_threshold is not None else _env_float("MONITOR_AGENT_AVG_MS_THRESHOLD", 8000.0)
        self._tool_sr_threshold = tool_success_rate_threshold if tool_success_rate_threshold is not None else _env_float("MONITOR_TOOL_SUCCESS_RATE_THRESHOLD", 0.95)
        self._tool_ms_threshold = tool_avg_ms_threshold if tool_avg_ms_threshold is not None else _env_float("MONITOR_TOOL_AVG_MS_THRESHOLD", 5000.0)

        # 路由降权阈值（可与告警分离；默认略严于告警以保留路由反馈）
        self._penalty_sr = penalty_success_rate if penalty_success_rate is not None else _env_float("MONITOR_PENALTY_SUCCESS_RATE", 0.85)
        self._penalty_ms = penalty_avg_ms if penalty_avg_ms is not None else _env_float("MONITOR_PENALTY_AVG_MS", 7000.0)

        self._suggestion_sr = suggestion_success_rate if suggestion_success_rate is not None else _env_float("MONITOR_SUGGESTION_SUCCESS_RATE", 0.75)
        self._suggestion_min_total = suggestion_min_total if suggestion_min_total is not None else int(_env_float("MONITOR_SUGGESTION_MIN_TOTAL", 10))

        self.THRESHOLDS = {
            "agent_success_rate": (self._agent_sr_threshold, Severity.ERROR,   "less_than"),
            "tool_success_rate":  (self._tool_sr_threshold, Severity.WARNING,  "less_than"),
            "agent_avg_ms":       (self._agent_ms_threshold, Severity.WARNING, "greater_than"),
            "tool_avg_ms":        (self._tool_ms_threshold, Severity.ERROR,    "greater_than"),
        }

        self._orchestrator = orchestrator
        self._tool_manager = tool_manager
        self._interval     = interval_s
        self._webhook      = webhook_url
        anomaly_z = anomaly_sensitivity if anomaly_sensitivity is not None else _env_float("ANOMALY_DETECTION_THRESHOLD", 2.5)
        self._detector     = AnomalyDetector(sensitivity=anomaly_z)

        self._alerts:      List[Alert]      = []
        self._suggestions: List[Suggestion] = []
        self._active       = False
        self._task:        Optional[asyncio.Task] = None

        logger.info(
            "Monitor 阈值: agent_sr<%s agent_ms>%sms penalty_sr<%s penalty_ms>%sms",
            self._agent_sr_threshold,
            self._agent_ms_threshold,
            self._penalty_sr,
            self._penalty_ms,
        )

        # Prometheus 指标（可选）
        self._prom: Dict[str, Any] = {}
        if prometheus_port:
            self._setup_prometheus(prometheus_port)

    def _setup_prometheus(self, port: int) -> None:
        self._prom = {
            "agent_success_rate": Gauge("agent_success_rate", "Agent 成功率", ["agent"]),
            "agent_latency_ms":   Histogram("agent_latency_ms", "Agent 延迟", ["agent"]),
            "tool_success_rate":  Gauge("tool_success_rate", "工具成功率", ["tool"]),
            "requests_total":     Counter("requests_total", "总请求数"),
        }
        start_http_server(port)
        logger.info(f"Prometheus 已启动: :{port}")

    # ── 生命周期 ──────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._task   = asyncio.create_task(self._loop())
        logger.info(f"Monitor 已启动，采集间隔 {self._interval}s")

    async def stop(self) -> None:
        self._active = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    # ── 采集循环 ──────────────────────────────────────────────────────────────

    async def _loop(self) -> None:
        while self._active:
            try:
                await self._collect()
            except Exception as ex:
                logger.error(f"Monitor 采集异常: {ex}")
            await asyncio.sleep(self._interval)

    async def _collect(self) -> None:
        """
        采集 Agent 和工具的实时统计，检测异常，生成建议。

        关键：这里读取的 stats 就是 Orchestrator/ToolManager 在处理请求时
        实时更新的数据，Monitor 不需要额外埋点。
        """
        agent_stats = self._orchestrator.get_stats()
        tool_stats  = self._tool_manager.get_stats()
        routing_penalties: Dict[str, float] = {}

        # ── Agent 指标 ────────────────────────────────────────────────────────
        for agent_key, s in agent_stats.items():
            sr  = s["success_rate"]
            ms  = s["avg_ms"]

            # 异常检测
            for metric, value in [("agent_success_rate", sr), ("agent_avg_ms", ms)]:
                anomaly = self._detector.record(f"{metric}:{agent_key}", value)
                if anomaly:
                    logger.warning(f"异常检测 [{agent_key}] {metric}={value:.3f} z={anomaly['z_score']}")

            # 阈值告警
            self._check_threshold("agent_success_rate", sr, agent_key)
            self._check_threshold("agent_avg_ms", ms, agent_key)

            # Prometheus
            if "agent_success_rate" in self._prom:
                self._prom["agent_success_rate"].labels(agent=agent_key).set(sr)
                self._prom["agent_latency_ms"].labels(agent=agent_key).observe(ms)

            routing_penalties[agent_key] = self._routing_penalty(sr, ms)

        # ── 工具指标 ──────────────────────────────────────────────────────────
        for tool_name, s in tool_stats.items():
            sr = s["success_rate"]
            ms = s["avg_latency_ms"]
            cf = s["consecutive_fails"]

            self._check_threshold("tool_success_rate", sr, tool_name)
            self._check_threshold("tool_avg_ms", ms, tool_name)

            if "tool_success_rate" in self._prom:
                self._prom["tool_success_rate"].labels(tool=tool_name).set(sr)

            # 连续失败 → 生成具体建议
            if cf >= 3:
                self._add_suggestion(Suggestion(
                    title=f"工具 {tool_name} 连续失败 {cf} 次",
                    detail=f"成功率 {sr:.1%}，平均延迟 {ms:.0f}ms，熔断状态: {s['circuit_state']}",
                    action="1. 检查工具依赖服务是否正常\n2. 查看错误日志\n3. 考虑增加超时时间或降级策略",
                    priority=9,
                ))

        # ── 路由优化建议 ──────────────────────────────────────────────────────
        updater = getattr(self._orchestrator, "update_routing_penalties", None)
        if updater:
            updater(routing_penalties)
        self._generate_routing_suggestions(agent_stats)

    def _routing_penalty(self, success_rate: float, avg_ms: float) -> float:
        """把在线表现转成 0-0.9 的路由降权系数。"""
        penalty = 0.0
        if success_rate < self._penalty_sr:
            penalty += min(0.5, (self._penalty_sr - success_rate) * 2)
        if avg_ms > self._penalty_ms:
            penalty += min(0.4, (avg_ms - self._penalty_ms) / 10000)
        return min(penalty, 0.9)

    def _check_threshold(self, metric: str, value: float, label: str) -> None:
        if metric not in self.THRESHOLDS:
            return
        metric_key = f"{metric}:{label}"
        threshold, severity, operator = self.THRESHOLDS[metric]
        triggered = (operator == "less_than" and value < threshold) or \
                    (operator == "greater_than" and value > threshold)

        # 指标恢复时标记已有告警为 resolved，避免 active_alerts 永久堆积
        if not triggered:
            for alert in self._alerts:
                if alert.metric == metric_key and not alert.resolved:
                    alert.resolved = True
            return

        # 同一 metric 未恢复前不重复追加告警（避免每 10s 刷一条）
        if any(a.metric == metric_key and not a.resolved for a in self._alerts):
            return

        alert = Alert(
            severity=severity,
            metric=metric_key,
            message=f"{label} 的 {metric} = {value:.3f}，阈值 {threshold}",
            value=value,
            threshold=threshold,
        )
        self._alerts.append(alert)
        logger.warning(f"[{severity.value.upper()}] {alert.message}")
        if self._webhook:
            asyncio.create_task(self._send_webhook(alert))

    def _generate_routing_suggestions(self, agent_stats: Dict[str, Any]) -> None:
        """
        基于 Agent 在线表现生成路由优化建议。
        这是 Monitor → Orchestrator 反馈闭环的体现。
        """
        for agent_key, s in agent_stats.items():
            if s["success_rate"] < self._suggestion_sr and s["total"] > self._suggestion_min_total:
                self._add_suggestion(Suggestion(
                    title=f"Agent {agent_key} 成功率偏低",
                    detail=f"成功率 {s['success_rate']:.1%}，路由评分 {s['routing_score']:.3f}",
                    action=(
                        "Orchestrator 的 _best_agent() 已自动降低该 Agent 的路由权重。\n"
                        "建议：1. 检查 system_prompt 是否需要优化\n"
                        "      2. 检查该类型问题的复杂度是否超出 Agent 能力\n"
                        "      3. 考虑增加同类型 Agent 实例"
                    ),
                    priority=8,
                ))

    def _add_suggestion(self, s: Suggestion) -> None:
        # 去重：相同 title 不重复添加
        if not any(x.title == s.title for x in self._suggestions):
            self._suggestions.append(s)
            logger.info(f"优化建议 [P{s.priority}]: {s.title}")

    async def _send_webhook(self, alert: Alert) -> None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                await c.post(self._webhook, json=asdict(alert))  # type: ignore
        except Exception as ex:
            logger.error(f"Webhook 发送失败: {ex}")

    # ── 查询接口 ──────────────────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        """返回当前监控摘要，供 API 层暴露。"""
        return {
            "thresholds": {
                "agent_success_rate": self._agent_sr_threshold,
                "agent_avg_ms":       self._agent_ms_threshold,
                "penalty_success_rate": self._penalty_sr,
                "penalty_avg_ms":       self._penalty_ms,
            },
            "agent_stats":   self._orchestrator.get_stats(),
            "tool_stats":    self._tool_manager.get_stats(),
            "active_alerts": [asdict(a) for a in self._alerts if not a.resolved][-10:],
            "suggestions":   [
                {"title": s.title, "action": s.action, "priority": s.priority}
                for s in sorted(self._suggestions, key=lambda x: -x.priority)[:5]
            ],
        }
