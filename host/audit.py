"""Append-only JSONL audit trail: one line per tool-call decision."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path


class AuditLog:
    def __init__(self, path: Path, session_id: str, user: str, role: str):
        self.path, self.session_id, self.user, self.role = path, session_id, user, role
        path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, *, server: str, tool: str, args: dict, decision: str, result: str = "",
               started: float | None = None, flags: list[str] | None = None) -> dict:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "session": self.session_id,
            "user": self.user,
            "role": self.role,
            "server": server,
            "tool": tool,
            "args": args,
            "decision": decision,  # allowed | approved | denied_role | denied_user | error
            "result": result[:200],
            "duration_ms": round((time.monotonic() - started) * 1000) if started else None,
            "flags": flags or [],
        }
        with self.path.open("a") as fh:
            fh.write(json.dumps(entry) + "\n")
        return entry


def tail(path: Path, n: int = 10) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()[-n:]]


def query(path: Path, *, user: str | None = None, server: str | None = None, decision: str | None = None,
          flagged: bool | None = None, limit: int = 100) -> list[dict]:
    """Filtered audit entries, newest first."""
    if not path.exists():
        return []
    entries = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    keep = [e for e in reversed(entries)
            if (user is None or e["user"] == user)
            and (server is None or e["server"] == server)
            and (decision is None or e["decision"] == decision)
            and (flagged is None or bool(e["flags"]) == flagged)]
    return keep[:limit]
