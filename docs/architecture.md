# Architecture

## Components

```
Employee ── CLI (host/cli.py) or HTTP (host/api.py)
                │
        Host / Assistant (host/assistant.py)
        ├─ Planner: Claude tool use, or the offline keyword planner (host/llm.py)
        ├─ Policy:  role -> visible servers, write permission (host/policy.py)
        ├─ Guard:   injection tripwire + untrusted-output fencing (host/guard.py)
        ├─ Audit:   append-only JSONL (host/audit.py)
        └─ MCPManager: one MCP client session per allowed server (host/mcp_manager.py)
                │  stdio / JSON-RPC
   ┌────────────┼──────────────┬───────────────┐
 docs         hr            notes          tickets
 (read-only)  (read-only)   (read + write) (read + create)
 servers/filesystem (one codebase, two roots)   servers/notes   servers/tickets
```

## Request flow (list tools → plan → call tool → answer)

1. **Identify** the user and resolve their role from `config/policy.json`.
2. **Connect** only to the servers that role may use. Other servers are never started, so their tools
   are never discovered. Each server is launched with its own token.
3. **Discover** with MCP `tools/list`. The host namespaces tools (`tickets__create_ticket`) and records
   each tool's `readOnlyHint` annotation, which comes from the server, not from the host.
4. **Plan**: the LLM receives the tool schemas and the question, and returns tool calls.
5. **Gate** each call:
   - read-only tool: run it.
   - side-effecting tool: check `can_write` for the role (`denied_role`), then ask the human
     (`denied_user`), then run (`approved`).
6. **Execute** with MCP `tools/call`. Results are scanned for injection patterns and wrapped in
   `<untrusted_tool_output>` before the LLM sees them.
7. **Audit**: every decision is written to `logs/audit.jsonl`.
8. **Answer**: the loop repeats (max 6 steps) until the LLM answers without tool calls.

## Security boundaries

| Boundary | Enforced by | Where |
|---|---|---|
| Who may see which servers/tools | Role policy; unauthorized servers are never spawned | host |
| Who may use side-effecting tools | `can_write` plus per-call human approval; fail closed on unannotated tools | host |
| Host to server identity | Per-server random token; the server stores only its SHA-256 and exits on mismatch | server |
| File access | Resolved path must stay inside the server's root (blocks `../`) | server |
| Credential isolation | A server receives only its own token, so the notes token cannot start the tickets server | host + server |
| Untrusted content | Tool output is fenced, flagged on injection patterns, and cannot act on its own because writes still need approval | host |
| Accountability | Structured audit log: user, role, server, tool, args, decision, duration, flags | host |

Defence in depth: the server enforces what it owns (sandbox, auth), and the host enforces what the
caller is allowed to do (role, approval). Neither trusts the LLM.

The injection tripwire is a heuristic and can be bypassed. The controls that actually matter are
structural: a poisoned document can ask for a write, but the write still needs role permission and a
human "yes".

## MCP vs. ad-hoc function calling

| | Ad-hoc function calling | MCP |
|---|---|---|
| Tool definition | Hand-written JSON schemas inside each app | Server publishes its own schemas via `tools/list` |
| Reuse | Re-implement per app and per model vendor | Write a server once and any MCP host can use it |
| Discovery | Static, compiled into the app | Dynamic: connect, list, adapt |
| Capabilities | Tools only | Tools, resources (data) and prompts (templates) |
| Process/trust boundary | Functions run inside the app process with the app's privileges | Server is a separate process/credential domain with its own auth and sandbox |
| Adding an integration | Change and redeploy the app | Add an entry to `config/servers.json` |
| Safety metadata | Convention | Standard annotations (`readOnlyHint`, `destructiveHint`) the host can act on |

In this repo: adding the `hr` server was one config entry plus one policy line because the filesystem
server is reused with a different root. The host code did not change.

## Design decisions

- **stdio transport**: simplest secure default for local servers: no network port, and the parent
  process owns the child. Remote servers (HTTP/SSE with OAuth) are the next step.
- **Offline planner**: keeps the demo and tests deterministic and free of API calls. The Claude planner
  uses the same interface, so the rest of the host is identical.
- **Namespacing** (`server__tool`) avoids collisions between servers and makes audit entries unambiguous.
- **Annotations as the source of truth** for side effects, so a new server's write tools are gated
  without host changes.

## Known limitations / next steps

- Roles come from a static file and the API trusts the `user` field. Real deployments need OIDC/JWT.
- Approval is synchronous. The HTTP API only supports "deny" or "pre-approve"; a real UI would hold the
  call pending.
- Keyword search only. A vector index inside the docs server would improve retrieval.
- Resource subscriptions (change notifications when a policy updates) are not implemented.
- The injection detector is regex-based.
