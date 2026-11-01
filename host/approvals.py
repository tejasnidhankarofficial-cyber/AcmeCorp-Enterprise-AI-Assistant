"""Pending-approval broker for the HTTP API.

An assistant run executes in a background task. When it reaches a side-effecting tool, the run pauses and the
API returns a `pending_approval` event. A second request (same user) approves or rejects, and the run resumes.
Unanswered approvals are rejected after APPROVAL_TIMEOUT seconds (fail closed).
"""
import asyncio
import uuid
from dataclasses import dataclass, field

from host.assistant import Assistant

APPROVAL_TIMEOUT = 120
RUN_RETENTION = 300


@dataclass
class Run:
    user: str
    events: asyncio.Queue = field(default_factory=asyncio.Queue)
    task: asyncio.Task | None = None


class ApprovalBroker:
    def __init__(self, timeout: float = APPROVAL_TIMEOUT):
        self.timeout = timeout
        self.runs: dict[str, Run] = {}
        self.pending: dict[str, tuple[str, asyncio.Future]] = {}  # approval_id -> (run_id, future)

    async def start(self, user: str, question: str, offline: bool = False) -> dict:
        Assistant(user, offline=offline)  # fail fast on an unknown user (raises PermissionError)
        run_id, run = uuid.uuid4().hex[:12], Run(user)
        self.runs[run_id] = run

        async def approver(server: str, tool: str, args: dict) -> bool:
            approval_id = uuid.uuid4().hex[:12]
            future = asyncio.get_running_loop().create_future()
            self.pending[approval_id] = (run_id, future)
            await run.events.put({"status": "pending_approval", "run_id": run_id, "approval_id": approval_id,
                                  "server": server, "tool": tool, "args": args})
            try:
                return await asyncio.wait_for(future, self.timeout)
            except asyncio.TimeoutError:
                return False
            finally:
                self.pending.pop(approval_id, None)

        async def work() -> None:
            try:
                async with Assistant(user, approver=approver, offline=offline) as assistant:
                    answer = await assistant.ask(question)
                await run.events.put({"status": "done", "run_id": run_id, "answer": answer.text, "trace": answer.trace})
            except Exception as exc:  # surface failures to the caller instead of hanging the request
                await run.events.put({"status": "error", "run_id": run_id, "detail": str(exc)})
            finally:
                asyncio.get_running_loop().call_later(RUN_RETENTION, self.runs.pop, run_id, None)

        run.task = asyncio.create_task(work())
        return await self._next_event(run_id)

    async def resolve(self, approval_id: str, user: str, approve: bool) -> dict:
        entry = self.pending.get(approval_id)
        if entry is None:
            raise KeyError(approval_id)
        run_id, future = entry
        if self.runs[run_id].user != user:
            raise PermissionError("only the user who started this run can answer its approvals")
        if not future.done():
            future.set_result(approve)
        return await self._next_event(run_id)

    async def _next_event(self, run_id: str) -> dict:
        event = await self.runs[run_id].events.get()
        if event["status"] != "pending_approval":
            self.runs.pop(run_id, None)
        return event
