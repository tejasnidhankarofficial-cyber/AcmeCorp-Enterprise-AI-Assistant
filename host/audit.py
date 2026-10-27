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
