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
- Pluggable LLM: OpenAI or Claude tool calling, or an offline planner so it runs with no API key
- CLI, FastAPI and a React web UI (identity switcher, live tool trace, approval cards, audit viewer)

See [docs/architecture.md](docs/architecture.md) for the design, the security boundaries and the
MCP vs. function-calling comparison.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/setup_config.py      # generate per-server tokens (gitignored)
python scripts/seed_data.py         # create tickets.db and notes.db
# pick an LLM (optional; with no key the offline planner is used):
export OPENAI_API_KEY=...           # OpenAI, model via OPENAI_MODEL (default gpt-4o-mini)
# export ANTHROPIC_API_KEY=...      # or Anthropic Claude, model via ASSISTANT_MODEL
# export LLM_PROVIDER=openai|anthropic|offline   # force a choice when both keys are set
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

## Web UI

```bash
cd frontend && npm install && npm run build && cd ..   # once
uvicorn host.api:app                                   # UI + API on http://localhost:8000
```

For frontend development run `uvicorn host.api:app` and, in `frontend/`, `npm run dev`
(http://localhost:5173, API calls are proxied to port 8000).

- **Left:** switch between the demo users and see the tools each role discovers (hr/notes/tickets disappear for the intern).
- **Centre:** chat. Side-effecting tools pause the run and show an **approval card** with the exact arguments and
  a countdown to the server's auto-reject.
- **Right:** live trace of every MCP call with its decision chip and any injection warning.
- **Audit log tab:** filter by user, server and decision. Employees and interns see only their own entries;
  roles with `audit_all` in `config/policy.json` (manager, hr) see everyone's.

Frontend tests: `cd frontend && npm test`.

## HTTP API

```bash
uvicorn host.api:app --reload
curl 'localhost:8000/tools?user=ivan'
curl -X POST localhost:8000/ask -H 'content-type: application/json' \
  -d '{"user":"alice","question":"Create a ticket: test","approve_writes":true,"offline":true}'
curl 'localhost:8000/audit?viewer=hana&server=tickets'   # viewer decides what is visible
curl localhost:8000/users                                  # demo users and roles

# Interactive approval: the run pauses at a side-effecting tool and waits for a human decision
curl -X POST localhost:8000/ask -H 'content-type: application/json' \
  -d '{"user":"alice","question":"Create a ticket: test","interactive":true,"offline":true}'
#  -> {"status":"pending_approval","approval_id":"ab12...","tool":"create_ticket","args":{...}}
curl -X POST localhost:8000/approvals/ab12... -H 'content-type: application/json' \
  -d '{"user":"alice","approve":true}'
#  -> {"status":"done","answer":"...","trace":[...]}
```

Only the user who started a run can answer its approvals, and an unanswered approval is rejected after
120 s (fail closed).

## Tests

```bash
pytest
```

They run against real stdio MCP servers on isolated temp data and cover role-scoped discovery, approval
and denial with no side effect, path traversal, per-server tokens, injection flagging the audit shape and the API pending-approval flow (approve, reject, wrong user, timeout).

## Project layout

```
frontend/    React + TypeScript + Tailwind UI (Vite)
host/        assistant loop, MCP client manager, policy, audit, guard, planners, CLI, API
servers/     filesystem (docs + hr), notes, tickets  - independent MCP servers
config/      servers.json, policy.json (tokens are generated and gitignored)
data/        synthetic docs, HR docs, seeded SQLite databases
docs/        architecture.md
tests/       end-to-end tests
```

## Possible improvements

Remote servers over HTTP with OAuth, a web UI for approvals, resource subscriptions, vector search in the
docs server, and real SSO for identity.
