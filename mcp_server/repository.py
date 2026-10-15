"""Database access for the MCP tools (synchronous; called from worker threads)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from core.machines import Machine, Metric
from mcp_server.anomaly import METRICS


def _machine(row: tuple[Any, ...]) -> Machine:
    return Machine(
        id=row[0], name=row[1], type=row[2], model=row[3], location=row[4], rated_current_a=row[5]
    )


def list_machines(pool: ConnectionPool) -> list[Machine]:
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT id, name, machine_type, model, location, rated_current_a "
            "FROM machines ORDER BY id"
        ).fetchall()
    return [_machine(r) for r in rows]


def get_machine(pool: ConnectionPool, machine_id: str) -> Machine | None:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT id, name, machine_type, model, location, rated_current_a "
            "FROM machines WHERE id = %s",
            (machine_id,),
        ).fetchone()
    return _machine(row) if row else None


Row = tuple[datetime, float | None, float | None, float | None, float | None]


def recent_readings(
    pool: ConnectionPool, machine_ids: list[str], minutes: int
) -> dict[str, list[Row]]:
    """Readings of the last `minutes`, per machine, in chronological order."""
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT machine_id, ts, temperature_c, vibration_mm_s, pressure_bar, current_a
            FROM sensor_readings
            WHERE machine_id = ANY(%s) AND ts >= now() - make_interval(mins => %s)
            ORDER BY machine_id, ts
            """,
            (machine_ids, minutes),
        ).fetchall()
    out: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        out[r[0]].append((r[1], r[2], r[3], r[4], r[5]))
    return out


def series(rows: list[Row]) -> dict[Metric, list[float]]:
    result: dict[Metric, list[float]] = {}
    for i, metric in enumerate(METRICS, start=1):
        values = [r[i] for r in rows if r[i] is not None]
        if values:
            result[metric] = values  # type: ignore[assignment]
    return result


def insert_ticket(
    pool: ConnectionPool,
    *,
    machine_id: str,
    title: str,
    description: str,
    priority: str,
    created_by: str,
) -> tuple[int, str, datetime]:
    with pool.connection() as conn:
        row = conn.execute(
            """
            INSERT INTO tickets (machine_id, title, description, priority, created_by)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, status, created_at
            """,
            (machine_id, title, description, priority, created_by),
        ).fetchone()
    assert row is not None
    return row[0], row[1], row[2]


def insert_audit(
    pool: ConnectionPool,
    *,
    principal: str,
    role: str | None,
    tool: str,
    arguments: dict[str, Any],
    status: str,
    detail: str | None,
) -> None:
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (principal, role, tool, arguments, status, detail)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (principal, role, tool, Jsonb(arguments), status, detail),
        )
