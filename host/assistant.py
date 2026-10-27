"""The host: LLM planner loop + policy enforcement + approval + audit around MCP tool calls."""
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from host import config, guard
from host.audit import AuditLog
from host.llm import OfflinePlanner, make_planner
from host.mcp_manager import MCPManager
from host.policy import resolve_identity

Approver = Callable[[str, str, dict], Awaitable[bool]]
MAX_STEPS = 6


async def deny_all(server: str, tool: str, args: dict) -> bool:
    return False


@dataclass
class Answer:
    text: str
    trace: list[dict] = field(default_factory=list)


class Assistant:
    def __init__(self, user: str, approver: Approver = deny_all, offline: bool = False):
        self.identity = resolve_identity(user)
        self.approver = approver
        self.planner = make_planner(offline)
        self.audit = AuditLog(config.AUDIT_LOG, uuid.uuid4().hex[:8], self.identity.user, self.identity.role)
        self.mcp = MCPManager(self.identity.servers)

    async def __aenter__(self) -> "Assistant":
        await self.mcp.__aenter__()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.mcp.__aexit__(*exc)

    @property
    def tool_specs(self) -> list[dict]:
        return [{"name": t.qualified, "description": f"[{t.server}] {t.description}", "input_schema": t.input_schema}
                for t in self.mcp.tools.values()]

    async def ask(self, question: str) -> Answer:
        messages: list[dict] = [{"role": "user", "content": question}]
        trace: list[dict] = []
        for _ in range(MAX_STEPS):
            turn = await self.planner.next_turn(messages, self.tool_specs)
            if not turn.tool_calls:
                return Answer(turn.text, trace)
            messages.append({"role": "assistant", "content": turn.assistant_content})
            results = []
            for call in turn.tool_calls:
                content = await self._execute(call.name, call.args, trace)
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": content})
            messages.append({"role": "user", "content": results})
        return Answer("I couldn't finish within the step limit.", trace)

    async def _execute(self, qualified: str, args: dict, trace: list[dict]) -> str:
        info = self.mcp.tools.get(qualified)
        if info is None:  # model asked for a tool it was never shown
            return "DENIED: unknown tool"
        started = time.monotonic()

        def log(decision: str, result: str = "", flags: list[str] | None = None) -> None:
            trace.append(self.audit.record(server=info.server, tool=info.name, args=args, decision=decision,
                                           result=result, started=started, flags=flags))

        if not info.read_only:
            if not self.identity.can_write:
                log("denied_role")
                return f"DENIED: role '{self.identity.role}' may not use side-effecting tools"
            if not await self.approver(info.server, info.name, args):
                log("denied_user")
                return "DENIED: the user did not approve this action"
            decision = "approved"
        else:
            decision = "allowed"

        text, is_error = await self.mcp.call(qualified, args)
        if is_error:
            log("error", text)
            return f"ERROR: {text}"
        flags = guard.scan(text)
        log(decision, text, flags)
        return guard.fence(text, flags)
