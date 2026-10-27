"""Team notes server backed by SQLite. Reads are open; add_note is a side-effecting tool."""
import sqlite3

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from servers.common import DATA_DIR, authenticate

authenticate("notes")
DB = DATA_DIR / "notes.db"
mcp = FastMCP("notes", log_level="WARNING")

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, body TEXT, tags TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    return conn


@mcp.tool(annotations=READ_ONLY)
def list_notes(limit: int = 10) -> list[dict]:
    """List the most recent notes."""
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM notes ORDER BY id DESC LIMIT ?", (min(limit, 50),))]


@mcp.tool(annotations=READ_ONLY)
def search_notes(query: str) -> list[dict]:
    """Search note titles, bodies and tags."""
    terms = [t for t in query.lower().split() if len(t) > 2] or [""]
    clause = "(title LIKE ? OR body LIKE ? OR tags LIKE ?)"
    params = [p for t in terms for p in (f"%{t}%",) * 3]
    with _conn() as c:
        rows = c.execute(f"SELECT * FROM notes WHERE {' OR '.join([clause] * len(terms))} "
                         "ORDER BY id DESC LIMIT 20", params)
        return [dict(r) for r in rows]


@mcp.tool(annotations=WRITE)
def add_note(title: str, body: str, tags: str = "") -> dict:
    """Create a new note. Side-effecting: the host requires approval."""
    with _conn() as c:
        cur = c.execute("INSERT INTO notes (title, body, tags) VALUES (?, ?, ?)", (title, body, tags))
        return {"id": cur.lastrowid, "title": title}


@mcp.prompt()
def meeting_summary(topic: str) -> str:
    """Prompt template: turn notes on a topic into meeting minutes."""
    return f"Use search_notes for '{topic}' and write meeting minutes: decisions, action items, owners."


if __name__ == "__main__":
    mcp.run()
