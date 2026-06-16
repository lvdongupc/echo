"""检索优化与工具层逻辑单元测试（无需 LLM / MCP 服务）。"""
import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from echo_mcp.tool_manager import CircuitBreaker, CircuitState, MCPToolManager, Tool, ToolResult


def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3, recovery_s=60.0)
    assert cb.allow() is True
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow() is False


def test_circuit_breaker_recovers():
    cb = CircuitBreaker(failure_threshold=2, recovery_s=0.01)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    import time
    time.sleep(0.02)
    assert cb.allow() is True
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_tool_stats_success_rate():
    tool = Tool(name="t", description="", handler=AsyncMock(), schema={})
    tool.stats.total = 10
    tool.stats.success = 8
    assert tool.stats.success_rate == pytest.approx(0.8)


def test_merge_dedup_logic():
    """模拟 search_with_rewrite 的去重合并逻辑（相同内容不同 score 视为不同项）。"""
    items_a = [{"title": "A", "content": "退款7天内", "score": 0.9}]
    items_b = [{"title": "A", "content": "退款7天内", "score": 0.9}]
    items_c = [{"title": "B", "content": "发票政策", "score": 0.7}]

    seen, merged = set(), []
    for item in items_a + items_b + items_c:
        key = hashlib.md5(str(item).encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            merged.append(item)

    assert len(merged) == 2


@pytest.mark.asyncio
async def test_call_unknown_tool():
    mgr = MCPToolManager(api_key="test", base_url="http://fake")
    result = await mgr.call("missing_tool", {})
    assert result.success is False
    assert "不存在" in (result.error or "")


@pytest.mark.asyncio
async def test_call_with_cache():
    handler = AsyncMock(return_value=[{"content": "cached"}])
    tool = Tool(
        name="knowledge_search",
        description="",
        handler=handler,
        schema={},
        cache_ttl=300.0,
    )
    mgr = MCPToolManager(api_key="test", base_url="http://fake")
    mgr.register(tool)

    r1 = await mgr.call("knowledge_search", {"query": "退款"}, use_cache=True)
    r2 = await mgr.call("knowledge_search", {"query": "退款"}, use_cache=True)

    assert r1.success is True
    assert r2.cached is True
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_fallback_on_handler_error():
    async def failing_handler(params, context):
        raise RuntimeError("ChromaDB down")

    async def fallback(params, context, error):
        return [{"title": "降级", "content": "请稍后重试", "fallback": True}]

    tool = Tool(
        name="knowledge_search",
        description="",
        handler=failing_handler,
        schema={},
        fallback=fallback,
    )
    mgr = MCPToolManager(api_key="test", base_url="http://fake")
    mgr.register(tool)

    result = await mgr.call("knowledge_search", {"query": "test"})
    assert result.success is True
    assert result.data[0]["fallback"] is True
