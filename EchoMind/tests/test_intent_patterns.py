"""意图识别模式匹配与投票逻辑（无需 LLM API）。"""
import pytest

from core.intent_recognizer import IntentCategory, IntentRecognizer


@pytest.fixture
def recognizer():
    return IntentRecognizer(api_key="test-key", base_url="http://fake")


def test_pattern_recognize_billing(recognizer):
    result = recognizer._pattern_recognize("申请退款被拒绝了")
    assert result["intent"] == IntentCategory.BILLING
    assert result["confidence"] > 0


def test_pattern_recognize_technical(recognizer):
    result = recognizer._pattern_recognize("应用 crash 了")
    assert result["intent"] == IntentCategory.TECHNICAL


def test_pattern_recognize_escalation(recognizer):
    result = recognizer._pattern_recognize("我要转人工")
    assert result["intent"] == IntentCategory.ESCALATION


def test_pattern_recognize_greeting(recognizer):
    result = recognizer._pattern_recognize("hello")
    assert result["intent"] == IntentCategory.GREETING


def test_vote_without_embedding(recognizer):
    """第三方 API 模式下 LLM 85% + Pattern 15%。"""
    llm = {"intent": IntentCategory.BILLING, "confidence": 0.9}
    emb = {"intent": IntentCategory.OTHER, "confidence": 0.0}
    pat = {"intent": IntentCategory.BILLING, "confidence": 0.5}
    assert recognizer._vote(llm, emb, pat) == IntentCategory.BILLING


def test_vote_llm_failed_falls_back_to_pattern(recognizer):
    llm = {"intent": IntentCategory.OTHER, "confidence": 0.0, "failed": True}
    emb = {"intent": IntentCategory.OTHER, "confidence": 0.0}
    pat = {"intent": IntentCategory.TECHNICAL, "confidence": 0.3}
    assert recognizer._vote(llm, emb, pat) == IntentCategory.TECHNICAL


def test_vote_low_confidence_returns_other(recognizer):
    recognizer.threshold = 0.9
    llm = {"intent": IntentCategory.QUERY, "confidence": 0.2}
    emb = {"intent": IntentCategory.OTHER, "confidence": 0.0}
    pat = {"intent": IntentCategory.OTHER, "confidence": 0.0}
    assert recognizer._vote(llm, emb, pat) == IntentCategory.OTHER


def test_urgency_critical(recognizer):
    level = recognizer._urgency("紧急！系统挂了", IntentCategory.TECHNICAL)
    from core.intent_recognizer import UrgencyLevel
    assert level == UrgencyLevel.CRITICAL

def test_local_embedding_stable(recognizer):
    v1 = recognizer._local_embedding("退款流程")
    v2 = recognizer._local_embedding("退款流程")
    assert v1 == v2
    assert len(v1) == 256
