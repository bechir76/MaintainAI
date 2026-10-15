from typing import Any

import httpx
import pytest
from psycopg_pool import ConnectionPool

from core.mcp_client import connect, result_payload
from tests.integration.conftest import TECH_KEY, VIEWER_KEY

pytestmark = pytest.mark.integration


async def call(url: str, key: str, tool: str, args: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    async with connect(url, key) as client:
        result = await client.call_tool(tool, args)
    return bool(result.is_error), result_payload(result)


def audit_rows(pool: ConnectionPool) -> list[tuple[str, str, str]]:
    with pool.connection() as conn:
        rows = conn.execute("SELECT tool, status, role FROM audit_log ORDER BY id").fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def test_requests_without_valid_key_are_rejected(mcp_url: str) -> None:
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    for headers in ({}, {"X-API-Key": "nope"}):
        response = httpx.post(mcp_url, json=body, headers=headers)
        assert response.status_code == 401


def test_health_endpoint(mcp_url: str) -> None:
    response = httpx.get(mcp_url.replace("/mcp", "/healthz"))
    assert response.json() == {"status": "ok"}


async def test_lists_tools_with_schemas(mcp_url: str) -> None:
    async with connect(mcp_url, VIEWER_KEY) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == {
        "search_manuals",
        "get_sensor_readings",
        "create_maintenance_ticket",
        "list_machines",
    }
    schema = tools["create_maintenance_ticket"].input_schema
    assert schema["properties"]["priority"]["enum"] == ["low", "medium", "high", "critical"]


async def test_search_returns_citable_passages(mcp_url: str, clean_db: ConnectionPool) -> None:
    error, out = await call(
        mcp_url,
        VIEWER_KEY,
        "search_manuals",
        {"query": "troubleshooting high vibration pump steps", "machine_type": "pump"},
    )
    assert not error
    top = out["results"][0]
    assert (top["doc_id"], top["page"]) == ("P-MT-02", 3)
    assert top["score"] >= out["min_score"]
    assert audit_rows(clean_db) == [("search_manuals", "ok", "viewer")]


async def test_search_with_nothing_relevant_returns_note(mcp_url: str) -> None:
    _, out = await call(
        mcp_url, VIEWER_KEY, "search_manuals", {"query": "Who won the football world cup in 2018?"}
    )
    assert out["results"] == []
    assert "do not cover" in out["note"]


async def test_restricted_document_requires_technician(mcp_url: str) -> None:
    args = {"query": "insulation resistance test voltage polarization index", "top_k": 10}
    _, viewer = await call(mcp_url, VIEWER_KEY, "search_manuals", args)
    _, tech = await call(mcp_url, TECH_KEY, "search_manuals", args)
    assert "M-ETP-05" not in {r["doc_id"] for r in viewer["results"]}
    assert tech["results"][0]["doc_id"] == "M-ETP-05"


async def test_injected_passage_is_neutralised(mcp_url: str) -> None:
    _, out = await call(
        mcp_url,
        VIEWER_KEY,
        "search_manuals",
        {"query": "P-100/250 mechanical seal upgrade kit SK-250-SIC affected pumps"},
    )
    bulletin = [r for r in out["results"] if r["doc_id"] == "SB-P-017" and r["page"] == 1]
    assert bulletin
    assert any(r["flagged"] for r in bulletin)
    for passage in bulletin:
        assert "ignore all previous" not in passage["text"].lower()
        assert "create_maintenance_ticket" not in passage["text"]


async def test_sensor_readings_flag_anomalies(mcp_url: str, sensor_data: ConnectionPool) -> None:
    _, p3 = await call(mcp_url, VIEWER_KEY, "get_sensor_readings", {"machine_id": "p-3"})
    assert p3["machine"]["id"] == "P-3"
    assert p3["status"] == "alarm"
    assert p3["flags"][0]["metric"] == "vibration_mm_s"
    assert p3["flags"][0]["source"].startswith("CMS-001")
    assert 0 < len(p3["recent"]) <= 12
    assert p3["count"] >= len(p3["recent"])

    _, p1 = await call(mcp_url, VIEWER_KEY, "get_sensor_readings", {"machine_id": "P-1"})
    assert p1["status"] == "ok"
    assert p1["flags"] == []


async def test_list_machines(mcp_url: str, sensor_data: ConnectionPool) -> None:
    _, out = await call(mcp_url, VIEWER_KEY, "list_machines", {})
    status = {m["id"]: m["status"] for m in out["machines"]}
    assert status == {"C-1": "ok", "M-1": "ok", "M-2": "alarm", "P-1": "ok", "P-3": "alarm"}


async def test_viewer_cannot_create_ticket(mcp_url: str, clean_db: ConnectionPool) -> None:
    error, out = await call(
        mcp_url,
        VIEWER_KEY,
        "create_maintenance_ticket",
        {
            "machine_id": "P-3",
            "title": "Vibration alarm",
            "description": "Vibration at 7.9 mm/s, above alarm limit.",
            "priority": "high",
        },
    )
    assert error
    assert "Permission denied" in out["error"]
    with clean_db.connection() as conn:
        tickets = conn.execute("SELECT count(*) FROM tickets").fetchone()
    assert tickets == (0,)
    assert audit_rows(clean_db) == [("create_maintenance_ticket", "denied", "viewer")]


async def test_technician_creates_ticket(mcp_url: str, clean_db: ConnectionPool) -> None:
    error, out = await call(
        mcp_url,
        TECH_KEY,
        "create_maintenance_ticket",
        {
            "machine_id": "m-2",
            "title": "Winding temperature alarm",
            "description": "Winding at 151 C, above the 145 C alarm limit (CMS-001 p.2).",
            "priority": "high",
        },
    )
    assert not error
    assert out["machine_id"] == "M-2"
    assert out["status"] == "open"
    assert out["created_by"].startswith("technician:")
    with clean_db.connection() as conn:
        row = conn.execute("SELECT machine_id, priority, created_by FROM tickets").fetchone()
    assert row is not None
    assert row[:2] == ("M-2", "high")
    assert audit_rows(clean_db) == [("create_maintenance_ticket", "ok", "technician")]


async def test_invalid_arguments_are_rejected_and_audited(
    mcp_url: str, clean_db: ConnectionPool
) -> None:
    error, out = await call(
        mcp_url, VIEWER_KEY, "get_sensor_readings", {"machine_id": "P-3; DROP TABLE", "minutes": 0}
    )
    assert error
    assert "machine_id" in out["error"]
    assert "minutes" in out["error"]
    error, out = await call(mcp_url, VIEWER_KEY, "list_machines", {"extra": 1})
    assert error
    assert [r[:2] for r in audit_rows(clean_db)] == [
        ("get_sensor_readings", "invalid"),
        ("list_machines", "invalid"),
    ]


async def test_unknown_machine_is_an_error(mcp_url: str, clean_db: ConnectionPool) -> None:
    error, out = await call(mcp_url, VIEWER_KEY, "get_sensor_readings", {"machine_id": "X-9"})
    assert error
    assert "Unknown machine" in out["error"]
    assert audit_rows(clean_db) == [("get_sensor_readings", "error", "viewer")]


async def test_unknown_tool_is_audited(mcp_url: str, clean_db: ConnectionPool) -> None:
    error, _ = await call(mcp_url, TECH_KEY, "drop_everything", {})
    assert error
    assert audit_rows(clean_db) == [("drop_everything", "invalid", "technician")]
