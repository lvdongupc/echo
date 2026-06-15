"""
EchoMind 标准 MCP Server（FastMCP / Model Context Protocol）。

工具在此用 @mcp.tool 注册，由 MCPClientBridge 通过 call_tool / list_tools 调用。
"""
import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from echo_mcp.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


class EchoMindMCPServer:
    """封装 FastMCP 实例与 EchoMind 工具注册。"""

    def __init__(self, name: str = "EchoMind"):
        self.mcp: FastMCP = FastMCP(name)
        self._kb: Optional[KnowledgeBase] = None
        self._tools_registered = False

    def bind_knowledge_base(self, kb: KnowledgeBase) -> None:
        """绑定知识库并注册 MCP 工具（仅执行一次）。"""
        self._kb = kb
        if self._tools_registered:
            return
        self._register_tools()
        self._tools_registered = True
        logger.info("MCP Server 工具已注册: knowledge_search")

    def _register_tools(self) -> None:
        kb = self._kb

        @self.mcp.tool()
        async def knowledge_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
            """搜索 EchoMind 知识库（ChromaDB 向量检索），返回 title/content/score 列表。"""
            if kb is None:
                raise RuntimeError("知识库未初始化")
            return kb.search(query, top_k=top_k)

    @property
    def knowledge_base(self) -> Optional[KnowledgeBase]:
        return self._kb
