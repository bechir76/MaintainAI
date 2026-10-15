"""Sensor simulator loop: writes readings for every machine into Postgres on a fixed interval."""

from __future__ import annotations

import contextlib
import logging
import random
import signal
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import FrameType

from psycopg_pool import ConnectionPool

from core.config import get_settings
from core.db import create_pool, seed_machines
from core.machines import MACHINES
from simulator.model import FaultKind, Reading, parse_faults, sample

log = logging.getLogger("simulator")
HEARTBEAT = Path("/tmp/simulator-heartbeat")  # noqa: S108 - container-local liveness file
RETENTION = timedelta(days=2)


def write_readings(pool: ConnectionPool, readings: list[Reading]) -> None:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO sensor_readings
                (machine_id, ts, temperature_c, vibration_mm_s, pressure_bar, current_a)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                (r.machine_id, r.ts, r.temperature_c, r.vibration_mm_s, r.pressure_bar, r.current_a)
                for r in readings
            ],
        )


def tick(
    pool: ConnectionPool, faults: dict[str, FaultKind], rng: random.Random, ts: datetime
) -> None:
    write_readings(pool, [sample(m, ts, faults.get(m.id), rng) for m in MACHINES.values()])


def backfill(
    pool: ConnectionPool,
    faults: dict[str, FaultKind],
    rng: random.Random,
    minutes: int,
    interval: float,
) -> None:
    """Fill the last few minutes so the dashboard has history right after start-up."""
    now = datetime.now(UTC)
    steps = int(minutes * 60 / interval)
    for i in range(steps, 0, -1):
        tick(pool, faults, rng, now - timedelta(seconds=i * interval))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    faults = parse_faults(settings.sim_faults)
    pool = create_pool(settings.database_url, max_size=2)
    seed_machines(pool)
    rng = random.Random()

    running = True

    def stop(_signum: int, _frame: FrameType | None) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    backfill(pool, faults, rng, settings.sim_backfill_minutes, settings.sim_interval_seconds)
    log.info("simulating %d machines, faults=%s", len(MACHINES), faults or "none")

    while running:
        tick(pool, faults, rng, datetime.now(UTC))
        with pool.connection() as conn:
            cutoff = datetime.now(UTC) - RETENTION
            conn.execute("DELETE FROM sensor_readings WHERE ts < %s", (cutoff,))
        with contextlib.suppress(OSError):
            HEARTBEAT.touch()
        time.sleep(settings.sim_interval_seconds)
    pool.close()


if __name__ == "__main__":
    main()
