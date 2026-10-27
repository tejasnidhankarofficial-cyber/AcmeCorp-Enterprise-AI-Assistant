"""Generate one random token per MCP server.

host_secrets.json  -> plaintext tokens, held by the host only
server_tokens.json -> SHA-256 hashes, read by each server to authenticate the host
"""
import hashlib
import json
import secrets
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "config"


def main(force: bool = False) -> None:
    servers = json.loads((CONFIG / "servers.json").read_text())
    secrets_path, hashes_path = CONFIG / "host_secrets.json", CONFIG / "server_tokens.json"
    if secrets_path.exists() and hashes_path.exists() and not force:
        print("tokens already exist (use --force to rotate)")
        return
    tokens = {name: secrets.token_urlsafe(32) for name in servers}
    secrets_path.write_text(json.dumps(tokens, indent=2))
    hashes_path.write_text(json.dumps(
        {n: hashlib.sha256(t.encode()).hexdigest() for n, t in tokens.items()}, indent=2))
    secrets_path.chmod(0o600)
    print(f"wrote tokens for: {', '.join(tokens)}")


if __name__ == "__main__":
    import sys
    main(force="--force" in sys.argv)
