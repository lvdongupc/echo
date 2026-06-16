"""将 EvalReport 格式化为 Markdown / 控制台摘要。"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from evaluation.types import EvalReport


def format_console_summary(
    report: EvalReport,
    *,
    intent_metrics: Optional[Dict[str, Any]] = None,
    dataset_stats: Optional[Dict[str, Any]] = None,
) -> str:
    """生成适合终端打印的评测摘要。"""
    lines = [
        "",
        "=" * 60,
        "  EchoMind 评测报告",
        "=" * 60,
        f"  时间: {report.timestamp}",
    ]

    if dataset_stats:
        lines.append(
            f"  数据集: 意图 {dataset_stats.get('intent_cases', '?')} 条 | "
            f"对话 {dataset_stats.get('dialog_cases', '?')} 组 "
            f"({dataset_stats.get('dialog_total_turns', '?')} 轮)"
        )

    lines.extend([
        "",
        "── 总体 ──",
        f"  通过: {report.passed}/{report.total} ({report.pass_rate:.1%})",
    ])

    if report.avg_scores:
        lines.append("")
        lines.append("── 平均得分 ──")
        for k, v in sorted(report.avg_scores.items()):
            lines.append(f"  {k:20s} {v:.4f}")

    per_class = (intent_metrics or {}).get("per_class") or {}
    if per_class:
        lines.append("")
        lines.append("── 意图识别（按类别 F1）──")
        for label, m in sorted(per_class.items()):
            lines.append(
                f"  {label:12s}  P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}"
            )

    wrong = _intent_failures(report, intent_metrics)
    if wrong:
        lines.append("")
        lines.append(f"── 意图识别错误样本（前 {min(10, len(wrong))} 条）──")
        for w in wrong[:10]:
            lines.append(f"  x [{w['expected']}->{w['predicted']}] {w['message'][:50]}")

    if report.regressions:
        lines.append("")
        lines.append("── 回归告警 ──")
        for r in report.regressions:
            lines.append(f"  ! {r}")

    lines.append("")
    lines.append("── 优化建议 ──")
    for rec in report.recommendations:
        lines.append(f"  - {rec}")

    lines.append("=" * 60)
    return "\n".join(lines)


def format_markdown_report(
    report: EvalReport,
    *,
    intent_metrics: Optional[Dict[str, Any]] = None,
    dataset_stats: Optional[Dict[str, Any]] = None,
) -> str:
    """生成可提交的 Markdown 评测报告。"""
    lines = [
        "# EchoMind 评测报告",
        "",
        f"**生成时间:** {report.timestamp}  ",
        f"**通过率:** {report.passed}/{report.total} ({report.pass_rate:.1%})",
        "",
    ]

    if dataset_stats:
        lines.extend([
            "## 数据集规模",
            "",
            "| 类型 | 数量 |",
            "|------|------|",
            f"| 意图识别用例 | {dataset_stats.get('intent_cases', 0)} |",
            f"| 对话用例（组） | {dataset_stats.get('dialog_cases', 0)} |",
            f"| 对话总轮次 | {dataset_stats.get('dialog_total_turns', 0)} |",
            "",
        ])
        by_label = dataset_stats.get("intent_by_label") or {}
        if by_label:
            lines.append("### 意图分布")
            lines.append("")
            for label, count in sorted(by_label.items()):
                lines.append(f"- `{label}`: {count}")
            lines.append("")

    if report.avg_scores:
        lines.extend([
            "## 平均得分",
            "",
            "| 指标 | 分数 |",
            "|------|------|",
        ])
        for k, v in sorted(report.avg_scores.items()):
            lines.append(f"| {k} | {v:.4f} |")
        lines.append("")

    per_class = (intent_metrics or {}).get("per_class") or {}
    if per_class:
        lines.extend([
            "## 意图识别（按类别）",
            "",
            "| 意图 | Precision | Recall | F1 |",
            "|------|-----------|--------|-----|",
        ])
        for label, m in sorted(per_class.items()):
            lines.append(
                f"| {label} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} |"
            )
        acc = (intent_metrics or {}).get("accuracy")
        macro = (intent_metrics or {}).get("macro_f1")
        if acc is not None:
            lines.extend(["", f"**Accuracy:** {acc:.1%}  ", f"**Macro-F1:** {macro:.3f}  ", ""])

    dialog_results = [r for r in report.results if r.test_id.startswith("dialog_")]
    if dialog_results:
        lines.extend([
            "## 对话质量（LLM-as-Judge）",
            "",
            "| 用例 | 综合分 | 通过 |",
            "|------|--------|------|",
        ])
        for r in dialog_results:
            overall = r.scores.get("overall", 0)
            lines.append(f"| {r.test_id} | {overall:.3f} | {'✓' if r.passed else '✗'} |")
        lines.append("")

    wrong = _intent_failures(report, intent_metrics)
    if wrong:
        lines.extend([
            "## 意图识别错误样本",
            "",
            "| 消息 | 期望 | 预测 | 置信度 |",
            "|------|------|------|--------|",
        ])
        for w in wrong[:20]:
            msg = w["message"].replace("|", "\\|")[:40]
            lines.append(
                f"| {msg} | {w['expected']} | {w['predicted']} | {w.get('confidence', 0):.2f} |"
            )
        lines.append("")

    if report.regressions:
        lines.extend(["## 回归告警", ""])
        for r in report.regressions:
            lines.append(f"- {r}")
        lines.append("")

    lines.extend(["## 优化建议", ""])
    for rec in report.recommendations:
        lines.append(f"- {rec}")
    lines.append("")

    return "\n".join(lines)


def _intent_failures(
    report: EvalReport,
    intent_metrics: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if intent_metrics and intent_metrics.get("cases"):
        return [
            c for c in intent_metrics["cases"]
            if c.get("expected") != c.get("predicted")
        ]
    for r in report.results:
        if r.test_id == "intent_recognition":
            cases = r.metadata.get("cases") or []
            return [c for c in cases if c.get("expected") != c.get("predicted")]
    return []


def report_to_dict(
    report: EvalReport,
    *,
    intent_metrics: Optional[Dict[str, Any]] = None,
    dataset_stats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """完整 JSON 可序列化报告（含 per_class 与数据集信息）。"""
    payload = asdict(report)
    if intent_metrics:
        payload["intent_metrics"] = intent_metrics
    if dataset_stats:
        payload["dataset_stats"] = dataset_stats
    payload["intent_failures"] = _intent_failures(report, intent_metrics)
    return payload
