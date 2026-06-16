"""pytest 公共 fixtures。"""
import pytest


@pytest.fixture
def sample_intent_predictions():
    return ["query", "billing", "technical", "greeting", "other"]


@pytest.fixture
def sample_intent_ground_truth():
    return ["query", "billing", "technical", "greeting", "query"]
