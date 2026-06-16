"""意图识别指标计算单元测试（无需 LLM API）。"""
import pytest

from evaluation.metrics import compute_classification_metrics


def test_perfect_accuracy(sample_intent_predictions):
    metrics = compute_classification_metrics(
        sample_intent_predictions,
        sample_intent_predictions,
    )
    assert metrics["accuracy"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["correct"] == metrics["total"]


def test_partial_accuracy(sample_intent_predictions, sample_intent_ground_truth):
    metrics = compute_classification_metrics(
        sample_intent_predictions,
        sample_intent_ground_truth,
    )
    assert metrics["accuracy"] == 0.8
    assert metrics["correct"] == 4
    assert metrics["total"] == 5


def test_per_class_f1(sample_intent_predictions, sample_intent_ground_truth):
    metrics = compute_classification_metrics(
        sample_intent_predictions,
        sample_intent_ground_truth,
    )
    assert "query" in metrics["per_class"]
    query = metrics["per_class"]["query"]
    assert query["precision"] == 1.0
    assert query["recall"] == 0.5
    assert query["f1"] == pytest.approx(2 / 3, rel=1e-3)


def test_empty_predictions():
    metrics = compute_classification_metrics([], [])
    assert metrics["accuracy"] == 0.0
    assert metrics["total"] == 0
