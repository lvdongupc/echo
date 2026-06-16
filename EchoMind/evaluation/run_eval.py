#!/usr/bin/env python3
"""
EchoMind 评测 CLI — 从框架产出可量化证据。

用法:
  python -m evaluation.run_eval                    # 完整评测（意图 + 对话 Judge）
  python -m evaluation.run_eval --intent-only      # 仅意图识别（更快、更省 API）
  python -m evaluation.run_eval --no-save-baseline   # 不写 baseline.json
  python -m evaluation.run_eval --output-dir evaluation/baselines
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# 确保 EchoMind 根目录在 sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")


def _anthropic_cfg() -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("错误: 请设置 ANTHROPIC_API_KEY（.env 或环境变量）")
    cfg = {"api_key": api_key, "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")}
    base_url = os.getenv("ANTHROPIC_BASE_URL", "").strip()
    if base_url:
        cfg["base_url"] = base_url
    return cfg


async def _run(args: argparse.Namespace) -> int:
    from agents.agent_orchestrator import AgentOrchestrator
    from core.intent_recognizer import IntentRecognizer
    from evaluation.datasets.loader import dataset_stats, load_dialog_cases, load_intent_cases
    from evaluation.evaluator import EndToEndEvaluator
    from evaluation.report import format_console_summary, format_markdown_report, report_to_dict

    cfg = _anthropic_cfg()
    stats = dataset_stats()
    intent_cases = load_intent_cases()
    dialog_cases = None if args.intent_only else load_dialog_cases()

    recognizer = IntentRecognizer(
        api_key=cfg["api_key"],
        base_url=cfg.get("base_url"),
        model=cfg["model"],
    )
    orchestrator = AgentOrchestrator(
        api_key=cfg["api_key"],
        base_url=cfg.get("base_url"),
        model=cfg["model"],
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = output_dir / "baseline.json"

    evaluator = EndToEndEvaluator(
        orchestrator=orchestrator,
        recognizer=recognizer,
        api_key=cfg["api_key"],
        base_url=cfg.get("base_url"),
        model=cfg["model"],
        baseline_path=str(baseline_path) if args.save_baseline else None,
    )

    mode = "intent-only" if args.intent_only else "full"
    print(f"开始评测 [{mode}] — 意图 {stats['intent_cases']} 条", end="")
    if dialog_cases:
        print(f"，对话 {stats['dialog_cases']} 组（{stats['dialog_total_turns']} 轮）", end="")
    print(" ...")

    t0 = time.monotonic()
    report = await evaluator.run(
        intent_cases=intent_cases,
        dialog_cases=dialog_cases,
        dataset_stats=stats,
    )
    elapsed = time.monotonic() - t0
    intent_metrics = report.intent_metrics or {}

    print(format_console_summary(report, intent_metrics=intent_metrics, dataset_stats=stats))
    print(f"  耗时: {elapsed:.1f}s")

    # 写入完整 JSON + Markdown 摘要
    ts_slug = report.timestamp.replace(":", "-").split(".")[0]
    json_path = output_dir / f"report_{ts_slug}.json"
    md_path = output_dir / f"report_{ts_slug}.md"
    latest_md = output_dir / "latest_summary.md"

    payload = report_to_dict(report, intent_metrics=intent_metrics, dataset_stats=stats)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_text = format_markdown_report(report, intent_metrics=intent_metrics, dataset_stats=stats)
    md_path.write_text(md_text, encoding="utf-8")
    latest_md.write_text(md_text, encoding="utf-8")

    print(f"\n  报告已保存:")
    print(f"    JSON:     {json_path}")
    print(f"    Markdown: {md_path}")
    if args.save_baseline:
        print(f"    Baseline: {baseline_path}")

    return 0 if report.pass_rate >= args.min_pass_rate else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="EchoMind 评测 CLI")
    parser.add_argument("--intent-only", action="store_true", help="仅跑意图识别评测")
    parser.add_argument("--no-save-baseline", action="store_true", help="不更新 baseline.json")
    parser.add_argument(
        "--output-dir",
        default=str(_ROOT / "evaluation" / "baselines"),
        help="报告输出目录",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.0,
        help="低于此通过率时 exit code=1（CI 用）",
    )
    args = parser.parse_args()
    args.save_baseline = not args.no_save_baseline
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
