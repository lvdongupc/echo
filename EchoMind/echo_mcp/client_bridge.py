"""
MCP Client 桥接层 —— 通过标准 MCP 协议（list_tools / call_tool）调用 EchoMind MCP Server。

当前使用 in-process FastMCP，无需独立子进程；后续可扩展为 stdio / SSE 传输。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


class MCPClientBridge:
    """In-process MCP Client，包装 FastMCP Server 实例。"""

    TRANSPORT = "in-process"

    def __init__(self, mcp: FastMCP):
        self._mcp = mcp

    @property
    def transport(self) -> str:
        return self.TRANSPORT

    async def list_tools(self) -> List[Dict[str, Any]]:
        """返回 MCP 工具列表（name / description / inputSchema）。"""
        tools = await self._mcp.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description or "",
                "inputSchema": t.inputSchema or {"type": "object", "properties": {}},
            }
            for t in tools
        ]

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """
        调用 MCP 工具，返回结构化结果。

        FastMCP call_tool 返回 (content_blocks, structured_dict)。
        优先使用 structured['result']，否则解析 text content。
        """
        arguments = arguments or {}
        logger.debug("MCP call_tool: %s args=%s", name, arguments)
        content_blocks, structured = await self._mcp.call_tool(name, arguments)

        if isinstance(structured, dict) and "result" in structured:
            return structured["result"]

        if content_blocks:
            texts = [getattr(c, "text", str(c)) for c in content_blocks]
            combined = "\n".join(texts)
            try:
                return json.loads(combined)
            except json.JSONDecodeError:
                return combined

        return None

    async def to_claude_tools(self) -> List[Dict[str, Any]]:
        """将 MCP 工具 schema 转为 Anthropic messages API tools 格式。"""
        claude_tools = []
        for t in await self.list_tools():
            claude_tools.append({
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["inputSchema"],
            })
        return claude_tools
