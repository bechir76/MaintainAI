import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from core.config import Settings

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client(
    mcp_url: str, test_settings: Settings, monkeypatch_module: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    settings = test_settings.model_copy(update={"mcp_server_url": mcp_url})
    monkeypatch_module.setattr("api.main.get_settings", lambda: settings)
    from api.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def monkeypatch_module() -> Iterator[pytest.MonkeyPatch]:
    with pytest.MonkeyPatch.context() as mp:
        yield mp


def ask(client: TestClient, message: str, role: str = "viewer") -> list[tuple[str, Any]]:
    events = []
    with client.stream("POST", "/chat", json={"message": message, "role": role}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        kind = None
        for line in response.iter_lines():
            if line.startswith("event: "):
                kind = line[7:]
            elif line.startswith("data: "):
                events.append((kind, json.loads(line[6:])))
    return events


def answer(events: list[tuple[str, Any]]) -> str:
    return "".join(data["text"] for kind, data in events if kind == "token")


def test_health_and_liveness(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    health = client.get("/health").json()
    assert health == {"status": "ok", "mcp": "ok", "llm_provider": "fake"}


def test_machines_endpoint(client: TestClient, sensor_data: ConnectionPool) -> None:
    machines = client.get("/machines").json()["machines"]
    assert {m["id"]: m["status"] for m in machines}["P-3"] == "alarm"


def test_vibration_question_end_to_end(client: TestClient, sensor_data: ConnectionPool) -> None:
    events = ask(client, "Pump P-3 is vibrating, what should I check?")
    kinds = [k for k, _ in events]
    assert kinds[0] == "tool_start"
    assert kinds[-2:] == ["citations", "done"]
    tools = {d["name"]: d["status"] for k, d in events if k == "tool_end"}
    assert tools == {"get_sensor_readings": "ok", "search_manuals": "ok"}

    text = answer(events)
    assert "[L1]" in text
    assert "[S1]" in text
    citations = next(d for k, d in events if k == "citations")["citations"]
    docs = {(c["doc_id"], c["page"]) for c in citations if c["kind"] == "document"}
    assert ("P-MT-02", 3) in docs
    assert next(d for k, d in events if k == "done")["grounded"] is True


def test_out_of_scope_question_gets_i_dont_know(client: TestClient) -> None:
    events = ask(client, "What is the warranty period for a Siemens gas turbine?")
    assert answer(events).startswith("I don't know")
    assert next(d for k, d in events if k == "citations")["citations"] == []


def test_viewer_ticket_request_is_denied(client: TestClient, sensor_data: ConnectionPool) -> None:
    events = ask(client, "Create a ticket for P-3, vibration alarm", role="viewer")
    ticket = next(
        d for k, d in events if k == "tool_end" and d["name"] == "create_maintenance_ticket"
    )
    assert ticket["status"] == "denied"
    assert "could not create the ticket" in answer(events)
    with sensor_data.connection() as conn:
        assert conn.execute("SELECT count(*) FROM tickets").fetchone() == (0,)


def test_technician_ticket_request_creates_ticket(
    client: TestClient, sensor_data: ConnectionPool
) -> None:
    events = ask(client, "Create a ticket for M-2, winding overheating alarm", role="technician")
    ticket = next(
        d for k, d in events if k == "tool_end" and d["name"] == "create_maintenance_ticket"
    )
    assert ticket["status"] == "ok"
    with sensor_data.connection() as conn:
        row = conn.execute("SELECT machine_id, priority FROM tickets").fetchone()
    assert row == ("M-2", "high")


def test_request_validation(client: TestClient) -> None:
    assert client.post("/chat", json={"message": ""}).status_code == 422
    assert client.post("/chat", json={"message": "hi", "role": "admin"}).status_code == 422
