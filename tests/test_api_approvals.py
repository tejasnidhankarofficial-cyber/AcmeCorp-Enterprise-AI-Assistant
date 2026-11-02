import asyncio
import sqlite3

import httpx
import pytest

from host import api
from host.approvals import ApprovalBroker


@pytest.fixture
async def client(env):
    api.broker = ApprovalBroker(timeout=2)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://t") as c:
        yield c


def tickets(env) -> int:
    with sqlite3.connect(env.data / "tickets.db") as c:
        return c.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]


ASK = {"user": "alice", "question": "Create a ticket: broken keyboard", "offline": True, "interactive": True}


async def test_run_pauses_for_approval_then_executes_on_approve(client, env):
    before = tickets(env)
    pending = (await client.post("/ask", json=ASK)).json()
    assert pending["status"] == "pending_approval" and pending["tool"] == "create_ticket"
    assert tickets(env) == before  # nothing happened while waiting

    done = (await client.post(f"/approvals/{pending['approval_id']}", json={"user": "alice", "approve": True})).json()
    assert done["status"] == "done" and done["trace"][0]["decision"] == "approved"
    assert tickets(env) == before + 1


async def test_rejection_has_no_side_effect(client, env):
    before = tickets(env)
    pending = (await client.post("/ask", json=ASK)).json()
    done = (await client.post(f"/approvals/{pending['approval_id']}", json={"user": "alice", "approve": False})).json()
    assert done["trace"][0]["decision"] == "denied_user" and tickets(env) == before


async def test_another_user_cannot_answer_my_approval(client, env):
    pending = (await client.post("/ask", json=ASK)).json()
    resp = await client.post(f"/approvals/{pending['approval_id']}", json={"user": "bob", "approve": True})
    assert resp.status_code == 403
    # the real owner can still answer
    done = (await client.post(f"/approvals/{pending['approval_id']}", json={"user": "alice", "approve": False})).json()
    assert done["status"] == "done"


async def test_unanswered_approval_times_out_and_fails_closed(client, env):
    before = tickets(env)
    pending = (await client.post("/ask", json=ASK)).json()
    await asyncio.sleep(2.5)
    resp = await client.post(f"/approvals/{pending['approval_id']}", json={"user": "alice", "approve": True})
    assert resp.status_code == 404 and tickets(env) == before


async def test_read_only_question_never_pauses(client, env):
    body = {**ASK, "question": "What is the leave policy?"}
    assert (await client.post("/ask", json=body)).json()["status"] == "done"


async def test_unknown_user_is_forbidden(client, env):
    assert (await client.post("/ask", json={**ASK, "user": "mallory"})).status_code == 403


async def _seed_audit(client):
    await client.post("/ask", json={"user": "alice", "question": "What is the leave policy?", "offline": True})
    await client.post("/ask", json={"user": "hana", "question": "What is the salary band?", "offline": True})


async def test_users_endpoint_lists_roles(client):
    users = {u["user"]: u for u in (await client.get("/users")).json()}
    assert users["ivan"]["servers"] == ["docs"] and users["hana"]["audit_all"] is True
    assert users["alice"]["audit_all"] is False


async def test_audit_is_scoped_to_the_viewer_unless_role_allows_all(client):
    await _seed_audit(client)
    own = (await client.get("/audit", params={"viewer": "alice"})).json()
    assert own and {e["user"] for e in own} == {"alice"}
    # alice cannot widen her view by asking for someone else's entries
    spoof = (await client.get("/audit", params={"viewer": "alice", "user": "hana"})).json()
    assert {e["user"] for e in spoof} == {"alice"}
    everyone = (await client.get("/audit", params={"viewer": "hana"})).json()
    assert {e["user"] for e in everyone} == {"alice", "hana"}


async def test_audit_filters_and_order(client):
    await _seed_audit(client)
    hr_only = (await client.get("/audit", params={"viewer": "bob", "server": "hr"})).json()
    assert hr_only and all(e["server"] == "hr" for e in hr_only)
    allowed = (await client.get("/audit", params={"viewer": "bob", "decision": "allowed", "user": "alice"})).json()
    assert all(e["decision"] == "allowed" and e["user"] == "alice" for e in allowed)
    ts = [e["ts"] for e in (await client.get("/audit", params={"viewer": "bob"})).json()]
    assert ts == sorted(ts, reverse=True)


async def test_audit_rejects_unknown_viewer(client):
    assert (await client.get("/audit", params={"viewer": "mallory"})).status_code == 403
