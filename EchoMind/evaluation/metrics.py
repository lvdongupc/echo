"""评测指标纯函数（无 LLM / 外部依赖）。"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List


def compute_classification_metrics(
    predictions: List[str],
    ground_truth: List[str],
) -> Dict[str, Any]:
    """
    计算 Accuracy / Macro-F1 / per-class 指标。
    供 IntentEvaluator 与单元测试共用。
    """
    if not predictions:
        return {"accuracy": 0.0, "macro_f1": 0.0, "per_class": {}, "total": 0, "correct": 0}

    correct = sum(p == g for p, g in zip(predictions, ground_truth))
    accuracy = correct / len(predictions)

    labels = sorted(set(ground_truth + predictions))
    per_class: Dict[str, Dict[str, float]] = {}
    for label in labels:
        tp = sum(p == label and g == label for p, g in zip(predictions, ground_truth))
        fp = sum(p == label and g != label for p, g in zip(predictions, ground_truth))
        fn = sum(p != label and g == label for p, g in zip(predictions, ground_truth))
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        per_class[label] = {"precision": prec, "recall": rec, "f1": f1}

    macro_f1 = statistics.mean(v["f1"] for v in per_class.values()) if per_class else 0.0
    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
        "total": len(predictions),
        "correct": correct,
    }
