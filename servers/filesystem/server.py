"""Sandboxed, read-only document server. Launched once per document root (docs, hr)."""
import argparse
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from servers.common import DATA_DIR, authenticate

MAX_READ_CHARS = 20_000
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
STOPWORDS = {"the", "a", "an", "of", "to", "is", "are", "and", "or", "for", "in", "on", "what", "our",
             "how", "do", "i", "we", "my", "me", "can", "does", "about", "with", "any", "there"}

parser = argparse.ArgumentParser()
parser.add_argument("--name", required=True)
parser.add_argument("--root", required=True, help="directory under data/ to expose")
args = parser.parse_args()

authenticate(args.name)
ROOT = (DATA_DIR / args.root).resolve()
mcp = FastMCP(args.name, log_level="WARNING")


def safe_path(relative: str) -> Path:
    """Resolve a user-supplied path and refuse anything outside the sandbox root."""
    candidate = (ROOT / relative).resolve()
    if not candidate.is_relative_to(ROOT):
        raise ValueError("path escapes the document root")
    return candidate


def _files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and p.suffix in {".md", ".txt"})


@mcp.tool(annotations=READ_ONLY)
def list_docs(subdir: str = "") -> list[str]:
    """List documents (relative paths), optionally within a subdirectory."""
    base = safe_path(subdir)
    return [str(p.relative_to(ROOT)) for p in _files() if p.is_relative_to(base)]


@mcp.tool(annotations=READ_ONLY)
def read_doc(path: str) -> str:
    """Read the full text of one document by its relative path."""
    target = safe_path(path)
    if not target.is_file():
        raise ValueError(f"no such document: {path}")
    return target.read_text()[:MAX_READ_CHARS]


@mcp.tool(annotations=READ_ONLY)
def search_docs(query: str, max_results: int = 5) -> list[dict]:
    """Keyword search across documents. Returns path, score and a matching snippet."""
    terms = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if t not in STOPWORDS]
    hits = []
    for path in _files():
        text = path.read_text()
        lowered = text.lower()
        score = sum(lowered.count(t) for t in terms) + 3 * sum(t in path.stem.lower() for t in terms)
        if not score:
            continue
        snippet = next((ln.strip() for ln in text.splitlines() if any(t in ln.lower() for t in terms)), "")
        if "archive" in path.relative_to(ROOT).parts:
            score = max(1, score // 3)  # superseded documents rank lower
        hits.append({"path": str(path.relative_to(ROOT)), "score": score, "snippet": snippet[:240]})
    return sorted(hits, key=lambda h: -h["score"])[:max_results]


@mcp.resource(f"{args.name}://index")
def index() -> str:
    """Index of every document this server exposes."""
    return "\n".join(str(p.relative_to(ROOT)) for p in _files())


@mcp.prompt()
def summarize_policy(path: str) -> str:
    """Prompt template: summarize a policy document for an employee."""
    return f"Read the document '{path}' with the read_doc tool, then summarize it in 5 bullet points, citing the file."


if __name__ == "__main__":
    mcp.run()
