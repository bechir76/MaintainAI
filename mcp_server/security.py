"""API-key authentication and role-based tool permissions."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from dataclasses import dataclass

from core.config import Role

READ_TOOLS = frozenset({"search_manuals", "get_sensor_readings", "list_machines"})
WRITE_TOOLS = frozenset({"create_maintenance_ticket"})

PERMISSIONS: dict[Role, frozenset[str]] = {
    "viewer": READ_TOOLS,
    "technician": READ_TOOLS | WRITE_TOOLS,
}


@dataclass(frozen=True)
class Principal:
    id: str  # role plus a short key fingerprint; the key itself is never logged
    role: Role


class AuthError(Exception):
    pass


def fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def extract_key(headers: Mapping[str, str] | None) -> str | None:
    if not headers:
        return None
    key = headers.get("x-api-key")
    if key:
        return key.strip()
    auth = headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token.strip()
    return None


def authenticate(key: str | None, key_roles: Mapping[str, Role]) -> Principal:
    if not key:
        raise AuthError("missing API key")
    # Compare against every key so timing does not reveal which prefix matched.
    matched: Role | None = None
    for candidate, role in key_roles.items():
        if hmac.compare_digest(candidate.encode(), key.encode()):
            matched = role
    if matched is None:
        raise AuthError("invalid API key")
    return Principal(id=f"{matched}:{fingerprint(key)}", role=matched)


def is_allowed(role: Role, tool: str) -> bool:
    return tool in PERMISSIONS[role]
