"""Connects to MCP servers over stdio, discovers tools and routes namespaced tool calls."""
import json
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from host import config
from host.policy import is_read_only

SEP = "__"


@dataclass
class ToolInfo:
    server: str
    name: str
    description: str
    input_schema: dict
    read_only: bool

    @property
    def qualified(self) -> str:
        return f"{self.server}{SEP}{self.name}"


class MCPManager:
    """One MCP client session per allowed server. Servers a role may not use are never started."""

    def __init__(self, allowed_servers: tuple[str, ...]):
        self.allowed = allowed_servers
        self.sessions: dict[str, ClientSession] = {}
        self.tools: dict[str, ToolInfo] = {}
        self._stack = AsyncExitStack()

    async def __aenter__(self) -> "MCPManager":
        registry, secrets = config.load_servers(), config.load_secrets()
        for name in self.allowed:
            spec = registry[name]
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", spec["module"], *spec["args"]],
                cwd=config.ROOT,
                env={"MCP_AUTH_TOKEN": secrets[name],  # this server's token only
                     "MCP_DATA_DIR": str(config.DATA_DIR),
                     "MCP_CONFIG_DIR": str(config.CONFIG_DIR),
                     "FASTMCP_LOG_LEVEL": "WARNING"},
            )
            read, write = await self._stack.enter_async_context(stdio_client(params))
            session = await self._stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.sessions[name] = session
            for tool in (await session.list_tools()).tools:
                info = ToolInfo(name, tool.name, tool.description or "", tool.inputSchema, is_read_only(tool))
                self.tools[info.qualified] = info
        return self

    async def __aexit__(self, *exc) -> None:
        await self._stack.aclose()

    async def call(self, qualified: str, args: dict) -> tuple[str, bool]:
        """Invoke a tool. Returns (text, is_error)."""
        info = self.tools[qualified]
        result = await self.sessions[info.server].call_tool(info.name, args)
        structured = getattr(result, "structuredContent", None)
        if structured is not None and not result.isError:
            text = json.dumps(structured.get("result", structured), default=str)
        else:
            text = "\n".join(getattr(c, "text", "") for c in result.content)
        return text, bool(result.isError)

    async def list_resources(self, server: str) -> list[str]:
        return [str(r.uri) for r in (await self.sessions[server].list_resources()).resources]

    async def list_prompts(self, server: str) -> list[str]:
        return [p.name for p in (await self.sessions[server].list_prompts()).prompts]
