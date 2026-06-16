"""评测数据集加载与规模校验。"""
from evaluation.datasets.loader import dataset_stats, load_dialog_cases, load_intent_cases


def test_intent_cases_count():
    cases = load_intent_cases()
    assert len(cases) >= 80


def test_dialog_cases_count():
    cases = load_dialog_cases()
    assert len(cases) >= 20


def test_intent_labels_coverage():
    cases = load_intent_cases()
    labels = {c.expected_intent for c in cases}
    expected = {
        "query", "request", "complaint", "technical", "billing",
        "escalation", "greeting", "account", "feedback", "other",
    }
    assert expected.issubset(labels)


def test_multi_turn_intent_cases():
    cases = load_intent_cases()
    with_history = [c for c in cases if c.history]
    assert len(with_history) >= 5


def test_dataset_stats():
    stats = dataset_stats()
    assert stats["intent_cases"] >= 80
    assert stats["dialog_cases"] >= 20
    assert stats["dialog_multi_turn"] >= 10
