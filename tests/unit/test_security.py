import pytest

from mcp_server.security import (
    AuthError,
    authenticate,
    extract_key,
    fingerprint,
    is_allowed,
)

KEYS = {"view-key": "viewer", "tech-key": "technician"}


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"x-api-key": " view-key "}, "view-key"),
        ({"authorization": "Bearer tech-key"}, "tech-key"),
        ({"authorization": "bearer tech-key"}, "tech-key"),
        ({"authorization": "Basic abc"}, None),
        ({"authorization": "Bearer"}, None),
        ({}, None),
        (None, None),
    ],
)
def test_extract_key(headers: dict[str, str] | None, expected: str | None) -> None:
    assert extract_key(headers) == expected


def test_authenticate_maps_key_to_role() -> None:
    principal = authenticate("tech-key", KEYS)  # type: ignore[arg-type]
    assert principal.role == "technician"
    assert principal.id == f"technician:{fingerprint('tech-key')}"
    assert "tech-key" not in principal.id


@pytest.mark.parametrize("key", [None, "", "wrong", "view-key-extra"])
def test_authenticate_rejects_bad_keys(key: str | None) -> None:
    with pytest.raises(AuthError):
        authenticate(key, KEYS)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("role", "tool", "allowed"),
    [
        ("viewer", "search_manuals", True),
        ("viewer", "get_sensor_readings", True),
        ("viewer", "list_machines", True),
        ("viewer", "create_maintenance_ticket", False),
        ("technician", "create_maintenance_ticket", True),
        ("technician", "search_manuals", True),
        ("technician", "drop_tables", False),
    ],
)
def test_role_permissions(role: str, tool: str, allowed: bool) -> None:
    assert is_allowed(role, tool) is allowed  # type: ignore[arg-type]
