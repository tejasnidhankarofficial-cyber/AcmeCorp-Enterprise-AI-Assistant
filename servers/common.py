"""Shared helpers for every MCP server: paths and per-server authentication."""
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(os.environ.get("MCP_CONFIG_DIR", ROOT / "config"))
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR", ROOT / "data"))


def authenticate(server_name: str) -> None:
    """Refuse to start unless the host presented this server's own token.

    Each server stores only the SHA-256 of its token (config/server_tokens.json),
    so a token for one server is useless against another.
    """
    presented = os.environ.get("MCP_AUTH_TOKEN", "")
    try:
        expected = json.loads((CONFIG_DIR / "server_tokens.json").read_text()).get(server_name)
    except FileNotFoundError:
        expected = None
    digest = hashlib.sha256(presented.encode()).hexdigest()
    if not expected or not hmac.compare_digest(digest, expected):
        print(f"[{server_name}] authentication failed - refusing to start", file=sys.stderr)
        sys.exit(1)
