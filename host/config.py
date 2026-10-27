"""Host configuration: paths, server registry, secrets."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(os.environ.get("MCP_CONFIG_DIR", ROOT / "config"))
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR", ROOT / "data"))
LOG_DIR = Path(os.environ.get("MCP_LOG_DIR", ROOT / "logs"))
AUDIT_LOG = LOG_DIR / "audit.jsonl"
MODEL = os.environ.get("ASSISTANT_MODEL", "claude-sonnet-5-5")


def load_servers() -> dict:
    return json.loads((CONFIG_DIR / "servers.json").read_text())


def load_secrets() -> dict:
    path = CONFIG_DIR / "host_secrets.json"
    if not path.exists():
        raise SystemExit("config/host_secrets.json missing - run: python scripts/setup_config.py")
    return json.loads(path.read_text())
