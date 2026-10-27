import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from host import config

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated copy of data/config/logs so tests never touch the real demo data."""
    data, cfg, logs = tmp_path / "data", tmp_path / "config", tmp_path / "logs"
    shutil.copytree(ROOT / "data" / "docs", data / "docs")
    shutil.copytree(ROOT / "data" / "hr", data / "hr")
    shutil.copytree(ROOT / "config", cfg)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "seed_data.py"), str(data)], check=True,
                   capture_output=True)
    monkeypatch.setattr(config, "DATA_DIR", data)
    monkeypatch.setattr(config, "CONFIG_DIR", cfg)
    monkeypatch.setattr(config, "LOG_DIR", logs)
    monkeypatch.setattr(config, "AUDIT_LOG", logs / "audit.jsonl")
    return type("Env", (), {"data": data, "config": cfg, "audit": logs / "audit.jsonl"})


def read_audit(env) -> list[dict]:
    return [json.loads(line) for line in env.audit.read_text().splitlines()]
