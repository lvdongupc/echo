"""加载评测数据集（JSON），供 Evaluator / API / CLI 共用。"""
from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from evaluation.types import IntentTestCase

_DATA_DIR = pathlib.Path(__file__).parent


def _load_json(name: str) -> List[Dict[str, Any]]:
    path = _DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"评测数据集不存在: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{name} 应为 JSON 数组")
    return data


def load_intent_cases(path: Optional[pathlib.Path] = None) -> List["IntentTestCase"]:
    """加载意图识别评测用例。"""
    from evaluation.types import IntentTestCase
    if path is None:
        raw = _load_json("intent_cases.json")
    else:
        raw = json.loads(path.read_text(encoding="utf-8"))
    cases: List[IntentTestCase] = []
    for item in raw:
        history = item.get("history")
        context = item.get("context")
        if history and context is None:
            context = {"history": history}
        cases.append(IntentTestCase(
            message=str(item["message"]),
            expected_intent=str(item["expected_intent"]),
            context=context,
            history=history,
        ))
    return cases


def load_dialog_cases(path: Optional[pathlib.Path] = None) -> List[Dict[str, Any]]:
    """加载对话质量评测用例（单轮 question 或多轮 turns）。"""
    if path is None:
        return _load_json("dialog_cases.json")
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_stats() -> Dict[str, Any]:
    """返回数据集规模统计，供 /eval 接口展示。"""
    intent_cases = load_intent_cases()
    dialog_cases = load_dialog_cases()
    intent_by_label: Dict[str, int] = {}
    for c in intent_cases:
        intent_by_label[c.expected_intent] = intent_by_label.get(c.expected_intent, 0) + 1

    multi_turn = sum(1 for c in dialog_cases if c.get("turns"))
    single_turn = len(dialog_cases) - multi_turn
    total_dialog_turns = sum(
        len(c["turns"]) if c.get("turns") else 1
        for c in dialog_cases
    )

    return {
        "intent_cases": len(intent_cases),
        "intent_by_label": intent_by_label,
        "dialog_cases": len(dialog_cases),
        "dialog_single_turn": single_turn,
        "dialog_multi_turn": multi_turn,
        "dialog_total_turns": total_dialog_turns,
    }
