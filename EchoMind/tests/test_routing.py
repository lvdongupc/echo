"""多 Agent 路由逻辑单元测试（无需 LLM API）。"""
import pytest

from agents.agent_orchestrator import AgentOrchestrator, AgentStats, AgentType, Request
from core.intent_recognizer import IntentCategory, UrgencyLevel


@pytest.fixture
def orchestrator():
    return AgentOrchestrator(api_key="test-key", base_url="http://fake")


def test_route_technical_intent(orchestrator):
    assert orchestrator._route(IntentCategory.TECHNICAL, UrgencyLevel.LOW) == AgentType.TECHNICAL


def test_route_billing_intent(orchestrator):
    assert orchestrator._route(IntentCategory.BILLING, UrgencyLevel.LOW) == AgentType.BILLING


def test_route_critical_urgency(orchestrator):
    assert orchestrator._route(IntentCategory.QUERY, UrgencyLevel.CRITICAL) == AgentType.ESCALATION


def test_route_default_general(orchestrator):
    assert orchestrator._route(IntentCategory.GREETING, UrgencyLevel.LOW) == AgentType.GENERAL


def test_collaboration_technical_and_billing(orchestrator):
    req = Request(
        message="登录报错401而且被重复扣款了",
        user_id="u1",
        conv_id="c1",
        intent=IntentCategory.TECHNICAL,
    )
    targets = orchestrator._collaboration_targets(req)
    assert AgentType.TECHNICAL in targets
    assert AgentType.BILLING in targets
    assert len(targets) == 2


def test_collaboration_single_technical(orchestrator):
    req = Request(
        message="App 闪退",
        user_id="u1",
        conv_id="c1",
        intent=IntentCategory.TECHNICAL,
    )
    targets = orchestrator._collaboration_targets(req)
    assert targets == [AgentType.TECHNICAL]


def test_routing_score_prefers_success(orchestrator):
    good = orchestrator._pool[AgentType.TECHNICAL][0]
    for i, agent in enumerate(orchestrator._pool[AgentType.TECHNICAL]):
        if agent is good:
            agent.stats = AgentStats(total=100, success=95, total_ms=500000)
        else:
            agent.stats = AgentStats(total=100, success=50, total_ms=500000)
    chosen = orchestrator._best_agent(AgentType.TECHNICAL)
    assert chosen is good


def test_routing_penalty_reduces_score():
    stats = AgentStats(total=10, success=10, total_ms=1000, monitor_penalty=0.5)
    base = AgentStats(total=10, success=10, total_ms=1000, monitor_penalty=0.0)
    assert stats.routing_score() < base.routing_score()


def test_update_routing_penalties(orchestrator):
    key = "technical_2"
    orchestrator.update_routing_penalties({key: 0.8})
    agent = orchestrator._pool[AgentType.TECHNICAL][2]
    assert agent.stats.monitor_penalty == 0.8
