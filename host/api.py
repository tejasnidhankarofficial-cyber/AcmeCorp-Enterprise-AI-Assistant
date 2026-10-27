"""FastAPI wrapper: expose the assistant over HTTP.  uvicorn host.api:app --reload

Demo-grade identity: the caller names a user. In production this would sit behind real auth (OIDC/JWT).
Side-effecting tools are denied unless the request sets approve_writes=true (stand-in for a UI approval step).
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from host import config
from host.assistant import Assistant, deny_all
from host.audit import tail
from host.cli import auto_yes

app = FastAPI(title="MCP Enterprise Knowledge Assistant")


class AskRequest(BaseModel):
    user: str
    question: str
    approve_writes: bool = False
    offline: bool = False


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
        async with Assistant(req.user, approver=auto_yes if req.approve_writes else deny_all,
                             offline=req.offline) as a:
            answer = await a.ask(req.question)
            return {"answer": answer.text, "trace": answer.trace}
    except PermissionError as exc:
        raise HTTPException(403, str(exc))


@app.get("/audit")
async def audit(n: int = 20):
    return tail(config.AUDIT_LOG, min(n, 200))
