"""Runs the evaluation cases through the real agent and MCP server."""

from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from typing import Any

from psycopg_pool import ConnectionPool

from api.agent import Agent, AgentEvent, MCPToolExecutor, ToolExecutor
from core.config import Settings
from core.llm.base import ChatModel, ToolSpec
from core.mcp_client import connect
from evals.dataset import Case, Dataset
from evals.metrics import CaseResult
from mcp_server.injection import scan
from simulator.model import parse_faults
from simulator.runner import backfill

log = logging.getLogger("evals")
MANUALS = Path(__file__).resolve().parents[1] / "data" / "manuals"
EVAL_FAULTS = "P-3:high_vibration,M-2:overheating"


class RecordingTools:
    """Passes calls through to the MCP server and keeps what came back."""

    def __init__(self, inner: ToolExecutor) -> None:
        self.inner = inner
        self.calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    async def list_tools(self) -> list[ToolSpec]:
        return await self.inner.list_tools()

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = await self.inner.call(name, arguments)
        self.calls.append((name, arguments, payload))
        return payload


def seed_sensor_data(pool: ConnectionPool) -> None:
    backfill(pool, parse_faults(EVAL_FAULTS), random.Random(42), minutes=3, interval=5)


def count_tickets(pool: ConnectionPool) -> int:
    with pool.connection() as conn:
        row = conn.execute("SELECT count(*) FROM tickets").fetchone()
    return int(row[0]) if row else 0


async def run_case(
    case: Case, agent: Agent, mcp_url: str, settings: Settings, pool: ConnectionPool
) -> CaseResult:
    events: list[AgentEvent] = []

    async def emit(event: AgentEvent) -> None:
        events.append(event)

    tickets_before = count_tickets(pool)
    started = time.monotonic()
    async with connect(mcp_url, settings.key_for_role(case.role)) as client:
        tools = RecordingTools(MCPToolExecutor(client))
        try:
            await agent.run_with(tools, case.question, emit)
        except Exception as exc:  # recorded as a failure of this case, the run goes on
            log.exception("case %s failed", case.id)
            events.append(AgentEvent("error", {"message": repr(exc)}))

    retrieved: list[tuple[str, int]] = []
    passages: list[tuple[str, str]] = []
    for name, _, payload in tools.calls:
        if name == "search_manuals":
            for p in payload.get("results", []):
                retrieved.append((p["doc_id"], p["page"]))
                passages.append((p["doc_id"], p["text"]))

    citations: list[dict[str, Any]] = next(
        (e.data["citations"] for e in events if e.type == "citations"), []
    )
    error = next((e.data["message"] for e in events if e.type == "error"), None)
    return CaseResult(
        case=case,
        answer="".join(e.data["text"] for e in events if e.type == "token"),
        retrieved=retrieved,
        cited=[(c["doc_id"], c["page"]) for c in citations if c["kind"] == "document"],
        tool_statuses=[(e.data["name"], e.data["status"]) for e in events if e.type == "tool_end"],
        tickets_created=count_tickets(pool) - tickets_before,
        passages_seen=passages,
        injection_leaks=sum(1 for _, text in passages if scan(text)),
        error=error,
        elapsed_ms=int((time.monotonic() - started) * 1000),
    )


async def run_all(
    dataset: Dataset,
    model: ChatModel,
    settings: Settings,
    pool: ConnectionPool,
    mcp_url: str,
) -> list[CaseResult]:
    agent = Agent(model, settings)
    results = []
    for case in dataset.cases:
        result = await run_case(case, agent, mcp_url, settings, pool)
        log.info("%-34s %-12s %5d ms", case.id, case.kind, result.elapsed_ms)
        results.append(result)
    return results
