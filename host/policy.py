"""Role-based access policy: which servers a role can see and whether it may use write tools."""
import json
from dataclasses import dataclass

from host import config


@dataclass(frozen=True)
class Identity:
    user: str
    role: str
    servers: tuple[str, ...]
    can_write: bool


def resolve_identity(user: str) -> Identity:
    policy = json.loads((config.CONFIG_DIR / "policy.json").read_text())
    role = policy["users"].get(user)
    if role is None:
        raise PermissionError(f"unknown user: {user}")
    spec = policy["roles"][role]
    return Identity(user=user, role=role, servers=tuple(spec["servers"]), can_write=spec["can_write"])


def is_read_only(tool) -> bool:
    """Side-effect classification comes from the server's own MCP tool annotations.

    A tool with no annotation is treated as side-effecting (fail closed).
    """
    annotations = getattr(tool, "annotations", None)
    return bool(annotations and annotations.readOnlyHint)
