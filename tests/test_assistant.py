import json
import os
import sqlite3
import subprocess
import sys

import pytest

from host.assistant import Assistant, deny_all
from tests.conftest import ROOT, read_audit


async def approve(server, tool, args):
    return True


def ticket_count(env) -> int:
    with sqlite3.connect(env.data / "tickets.db") as c:
        return c.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]


async def test_tool_discovery_is_role_scoped(env):
    async with Assistant("ivan", offline=True) as intern, Assistant("hana", offline=True) as hr:
        assert {t.server for t in intern.mcp.tools.values()} == {"docs"}
        assert {t.server for t in hr.mcp.tools.values()} == {"docs", "hr", "notes", "tickets"}


async def test_side_effect_classification_comes_from_server_annotations(env):
    async with Assistant("alice", offline=True) as a:
        assert a.mcp.tools["docs__search_docs"].read_only
        assert not a.mcp.tools["tickets__create_ticket"].read_only
        assert not a.mcp.tools["notes__add_note"].read_only


async def test_intern_cannot_reach_hr_documents(env):
    async with Assistant("ivan", offline=True) as a:
        answer = await a.ask("What is the salary band for L4?")
    assert "don't have a tool" in answer.text
    assert answer.trace == []  # nothing was even attempted


async def test_hr_role_can_read_hr_documents(env):
    async with Assistant("hana", offline=True) as a:
        answer = await a.ask("What is the salary band?")
    assert "Salary Bands" in answer.text


async def test_write_requires_approval_and_denial_has_no_side_effect(env):
    before = ticket_count(env)
    async with Assistant("alice", approver=deny_all, offline=True) as a:
        answer = await a.ask("Create a ticket: broken keyboard")
    assert "DENIED" in answer.text
    assert ticket_count(env) == before
    assert read_audit(env)[-1]["decision"] == "denied_user"


async def test_approved_write_executes_and_is_audited(env):
    before = ticket_count(env)
    async with Assistant("alice", approver=approve, offline=True) as a:
        await a.ask("Create a ticket: broken keyboard")
    assert ticket_count(env) == before + 1
    entry = read_audit(env)[-1]
    assert (entry["server"], entry["tool"], entry["decision"]) == ("tickets", "create_ticket", "approved")


async def test_role_without_write_permission_is_denied_even_if_user_approves(env):
    policy = json.loads((env.config / "policy.json").read_text())
    policy["roles"]["intern"] = {"servers": ["docs", "tickets"], "can_write": False}
    (env.config / "policy.json").write_text(json.dumps(policy))
    before = ticket_count(env)
    async with Assistant("ivan", approver=approve, offline=True) as a:
        answer = await a.ask("Create a ticket: need a chair")
    assert "DENIED" in answer.text and ticket_count(env) == before
    assert read_audit(env)[-1]["decision"] == "denied_role"


async def test_path_traversal_is_blocked_by_the_server(env):
    async with Assistant("alice", offline=True) as a:
        trace: list = []
        out = await a._execute("docs__read_doc", {"path": "../hr/salary-bands.md"}, trace)
    assert out.startswith("ERROR") and "escapes" in out
    assert trace[0]["decision"] == "error"


async def test_unknown_tool_is_rejected(env):
    async with Assistant("alice", offline=True) as a:
        assert (await a._execute("hr__read_doc", {"path": "x"}, [])).startswith("DENIED")


async def test_prompt_injection_is_flagged_and_does_not_trigger_a_write(env):
    before = ticket_count(env)
    async with Assistant("alice", approver=approve, offline=True) as a:
        answer = await a.ask("Tell me about the analytics vendor")
    assert ticket_count(env) == before
    assert "injected instruction" in answer.text
    assert any("prompt_injection_suspected" in e["flags"] for e in read_audit(env))


async def test_audit_entries_have_the_expected_shape(env):
    async with Assistant("bob", offline=True) as a:
        await a.ask("What is the leave policy?")
    for entry in read_audit(env):
        assert {"ts", "session", "user", "role", "server", "tool", "args", "decision", "duration_ms"} <= entry.keys()
        assert entry["user"] == "bob" and entry["role"] == "manager"


def test_server_refuses_to_start_with_a_wrong_token(env):
    proc = subprocess.run(
        [sys.executable, "-m", "servers.notes.server"], cwd=ROOT, capture_output=True, text=True, timeout=20,
        env={**os.environ, "MCP_AUTH_TOKEN": "not-the-token", "MCP_CONFIG_DIR": str(env.config),
             "MCP_DATA_DIR": str(env.data)})
    assert proc.returncode == 1 and "authentication failed" in proc.stderr


def test_one_servers_token_does_not_unlock_another(env):
    tokens = json.loads((ROOT / "config" / "host_secrets.json").read_text())
    proc = subprocess.run(
        [sys.executable, "-m", "servers.notes.server"], cwd=ROOT, capture_output=True, text=True, timeout=20,
        env={**os.environ, "MCP_AUTH_TOKEN": tokens["tickets"], "MCP_CONFIG_DIR": str(env.config),
             "MCP_DATA_DIR": str(env.data)})
    assert proc.returncode == 1


def test_unknown_user_is_rejected():
    with pytest.raises(PermissionError):
        Assistant("mallory")
