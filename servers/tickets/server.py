"""Helpdesk ticket server backed by SQLite. create_ticket is side-effecting."""
import sqlite3

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from servers.common import DATA_DIR, authenticate

authenticate("tickets")
DB = DATA_DIR / "tickets.db"
mcp = FastMCP("tickets", log_level="WARNING")

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
PRIORITIES = {"low", "medium", "high"}


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, category TEXT,
        status TEXT DEFAULT 'open', priority TEXT DEFAULT 'medium', assignee TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    return conn


@mcp.tool(annotations=READ_ONLY)
def search_tickets(query: str = "", status: str = "") -> list[dict]:
    """Search tickets by text in title/description, optionally filtered by status (open, in_progress, closed)."""
    terms = [t for t in query.lower().split() if len(t) > 2] or [""]
    clause = "(title LIKE ? OR description LIKE ?)"
    like = [p for t in terms for p in (f"%{t}%", f"%{t}%")]
    sql = f"SELECT * FROM tickets WHERE ({' OR '.join([clause] * len(terms))})"
    params = list(like)
    if status:
        sql, params = sql + " AND status = ?", params + [status]
    # rank by how many terms matched
    sql += f" ORDER BY ({' + '.join([clause] * len(terms))}) DESC, id DESC LIMIT 10"
    with _conn() as c:
        return [dict(r) for r in c.execute(sql, params + like)]


@mcp.tool(annotations=READ_ONLY)
def get_ticket(ticket_id: int) -> dict:
    """Fetch one ticket by id."""
    with _conn() as c:
        row = c.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise ValueError(f"ticket {ticket_id} not found")
    return dict(row)


@mcp.tool(annotations=WRITE)
def create_ticket(title: str, description: str, priority: str = "medium") -> dict:
    """Open a new helpdesk ticket. Side-effecting: the host requires approval."""
    if priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {sorted(PRIORITIES)}")
    with _conn() as c:
        cur = c.execute("INSERT INTO tickets (title, description, category, priority) VALUES (?, ?, 'general', ?)",
                        (title, description, priority))
        return {"id": cur.lastrowid, "status": "open", "title": title}


@mcp.prompt()
def triage_ticket(ticket_id: int) -> str:
    """Prompt template: triage a ticket."""
    return f"Fetch ticket {ticket_id} with get_ticket, then suggest a category, priority and next step."


if __name__ == "__main__":
    mcp.run()
