"""FastAPI wrapper: expose the assistant over HTTP.  uvicorn host.api:app --reload

Demo-grade identity: the caller names a user. In production this would sit behind real auth (OIDC/JWT).
Side-effecting tools are handled one of three ways:
  default                denied
  approve_writes=true    pre-approved (automation / testing)
  interactive=true       the run pauses and returns status=pending_approval; answer it with POST /approvals/{id}
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from host import config
from host.approvals import ApprovalBroker
from host.assistant import Assistant, deny_all
from host.audit import query
from host.llm import make_planner
from host.policy import list_identities, resolve_identity
from host.cli import auto_yes

app = FastAPI(title="MCP Enterprise Knowledge Assistant")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
broker = ApprovalBroker()


class AskRequest(BaseModel):
    user: str
    question: str
    approve_writes: bool = False
    offline: bool = False
    interactive: bool = False


class ApprovalDecision(BaseModel):
    user: str
    approve: bool


@app.get("/tools")
async def tools(user: str):
    try:
        async with Assistant(user, offline=True) as a:
            return {"user": user, "role": a.identity.role,
                    "tools": [{"name": t.qualified, "read_only": t.read_only, "description": t.description}
                              for t in a.mcp.tools.values()]}
    except PermissionError as exc:
        raise HTTPException(403, str(exc))


@app.post("/ask")
async def ask(req: AskRequest):
    try:
        if req.interactive:
            return await broker.start(req.user, req.question, offline=req.offline)
        async with Assistant(req.user, approver=auto_yes if req.approve_writes else deny_all,
                             offline=req.offline) as a:
            answer = await a.ask(req.question)
            return {"answer": answer.text, "trace": answer.trace}
    except PermissionError as exc:
        raise HTTPException(403, str(exc))


@app.get("/users")
async def users():
    """Demo users for the UI's identity switcher."""
    return [{"user": i.user, "role": i.role, "servers": list(i.servers), "can_write": i.can_write,
             "audit_all": i.audit_all} for i in list_identities()]


@app.get("/info")
async def info():
    """Which planner the server is using (openai / anthropic / offline)."""
    return {"planner": type(make_planner()).__name__}


@app.get("/audit")
async def audit(viewer: str, n: int = 100, user: str | None = None, server: str | None = None,
                decision: str | None = None, flagged: bool | None = None):
    """Audit entries visible to `viewer`: everyone's for roles with audit_all, otherwise only their own."""
    try:
        identity = resolve_identity(viewer)
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    if not identity.audit_all:
        user = identity.user
    return query(config.AUDIT_LOG, user=user, server=server, decision=decision, flagged=flagged,
                 limit=min(n, 500))


@app.post("/approvals/{approval_id}")
async def decide(approval_id: str, decision: ApprovalDecision):
    """Approve or reject a paused side-effecting tool call, then return the run's next event."""
    try:
        return await broker.resolve(approval_id, decision.user, decision.approve)
    except KeyError:
        raise HTTPException(404, "no such pending approval (expired or already answered)")
    except PermissionError as exc:
        raise HTTPException(403, str(exc))


# Serve the built frontend (npm run build) from the same origin; mounted last so API routes win.
_dist = config.ROOT / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
