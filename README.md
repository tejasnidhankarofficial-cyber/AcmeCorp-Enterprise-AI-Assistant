# MCP-Enabled Enterprise Knowledge Assistant

An AI assistant for a fictional company (Acme Corp) that reaches documents, notes and tickets through the
**Model Context Protocol** instead of hard-coded plugins. Each system is its own MCP server with its own
credential and trust level. The host adds role-based visibility, human approval for side-effecting tools,
and a full audit trail.

> All data is synthetic (fictional company, generated tickets/notes). No real personal data is included.

## Features

- Standard tool discovery (`tools/list`), plus MCP resources and prompts
- 4 MCP servers: `docs`, `hr` (same code, different sandbox root), `notes`, `tickets`
- Per-server authentication (random token; the server keeps only the hash)
- Role-based tool visibility: an intern never even discovers the HR server
- Approval gate for side-effecting tools, classified from the server's own `readOnlyHint` annotation
- Audited tool calls (`logs/audit.jsonl`), prompt-injection tripwire, path-traversal protection
- Works with Claude (tool use) or an offline planner, so it runs with no API key
- CLI and FastAPI interfaces, 14 end-to-end tests

See [docs/architecture.md](docs/architecture.md) for the design, the security boundaries and the
MCP vs. function-calling comparison.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/setup_config.py      # generate per-server tokens (gitignored)
python scripts/seed_data.py         # create tickets.db and notes.db
export ANTHROPIC_API_KEY=...        # optional; without it the offline planner is used
```

Users and roles (`config/policy.json`): `ivan` intern, `alice` employee, `bob` manager, `hana` hr.

## Demo script

```bash
# 1. Tool discovery differs by role
python -m host.cli --user ivan --list-tools     # docs only (3 tools)
python -m host.cli --user hana --list-tools     # docs, hr, notes, tickets (12 tools)

# 2. Question answered from documents (cites the current policy, not the archived one)
python -m host.cli --user alice --ask "What is our remote work policy?"

# 3. Multi-server question: tickets + docs in one answer
python -m host.cli --user alice --ask "Any tickets about VPN issues?"

# 4. Side-effecting tool -> approval prompt (answer n to see the denial, y to create)
python -m host.cli --user alice --ask "Create a ticket: monitor flickering"

# 5. Security boundary: the intern has no path to HR data
python -m host.cli --user ivan --ask "What is the salary band for L4?"
python -m host.cli --user hana --ask "What is the salary band?"

# 6. Prompt injection: a doc tries to make the assistant open a privileged ticket
python -m host.cli --user alice --auto-approve --ask "Tell me about the analytics vendor"
#    -> flagged, ignored, and no ticket is created even with --auto-approve

# 7. Inspect the audit trail
python -m host.cli --audit 10
```

Add `--offline` to force the keyword planner. Interactive mode: `python -m host.cli --user alice`
(commands: `/tools`, `/audit`, `/quit`).

### Sample audit entry

```json
{"ts": "2026-10-27T22:54:43+00:00", "session": "59532faa", "user": "alice", "role": "employee",
 "server": "tickets", "tool": "create_ticket", "args": {"title": "VPN down again", "priority": "medium"},
 "decision": "approved", "result": "{\"id\": 62, \"status\": \"open\"}", "duration_ms": 2, "flags": []}
```

`decision` is one of `allowed`, `approved`, `denied_role`, `denied_user`, `error`.

## HTTP API

```bash
uvicorn host.api:app --reload
curl 'localhost:8000/tools?user=ivan'
curl -X POST localhost:8000/ask -H 'content-type: application/json' \
  -d '{"user":"alice","question":"Create a ticket: test","approve_writes":true,"offline":true}'
curl 'localhost:8000/audit?n=5'
```

## Tests

```bash
pytest
```

They run against real stdio MCP servers on isolated temp data and cover role-scoped discovery, approval
and denial with no side effect, path traversal, per-server tokens, injection flagging and the audit shape.

## Project layout

```
host/        assistant loop, MCP client manager, policy, audit, guard, planners, CLI, API
servers/     filesystem (docs + hr), notes, tickets  - independent MCP servers
config/      servers.json, policy.json (tokens are generated and gitignored)
data/        synthetic docs, HR docs, seeded SQLite databases
docs/        architecture.md
tests/       end-to-end tests
```

## Possible improvements

Remote servers over HTTP with OAuth, a pending-approval UI, resource subscriptions, vector search in the
docs server, and real SSO for identity.
