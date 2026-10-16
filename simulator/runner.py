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

from core.config import Settings, get_settings
from core.db import create_pool, seed_machines
from core.machines import MACHINES
from simulator.model import FaultKind, Reading, parse_faults, sample
from simulator.replay import ReplaySource

log = logging.getLogger("simulator")
HEARTBEAT = Path("/tmp/simulator-heartbeat")  # noqa: S108 - container-local liveness file
RETENTION = timedelta(days=2)


def write_readings(pool: ConnectionPool, readings: list[Reading]) -> None:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO sensor_readings
                (machine_id, ts, temperature_c, vibration_mm_s, pressure_bar, current_a,
                 bearing_accel_g, load_duty_pct)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    r.machine_id,
                    r.ts,
                    r.temperature_c,
                    r.vibration_mm_s,
                    r.pressure_bar,
                    r.current_a,
                    r.bearing_accel_g,
                    r.load_duty_pct,
                )
                for r in readings
            ],
        )


def tick(
    pool: ConnectionPool,
    faults: dict[str, FaultKind],
    rng: random.Random,
    ts: datetime,
    replay: ReplaySource | None = None,
    elapsed_seconds: float = 0.0,
    skip: frozenset[str] = frozenset(),
) -> None:
    readings = []
    for m in MACHINES.values():
        if m.id in skip:
            continue
        if replay is not None and m.id in replay.machine_ids:
            readings.append(replay.reading(m.id, ts, elapsed_seconds))
        else:
            readings.append(sample(m, ts, faults.get(m.id), rng))
    write_readings(pool, readings)


def backfill(
    pool: ConnectionPool,
    faults: dict[str, FaultKind],
    rng: random.Random,
    minutes: int,
    interval: float,
    skip: frozenset[str] = frozenset(),
) -> None:
    """Fill the last few minutes so the dashboard has history right after start-up.

    Replayed machines are skipped: their history starts when the replay starts.
    """
    now = datetime.now(UTC)
    steps = int(minutes * 60 / interval)
    for i in range(steps, 0, -1):
        tick(pool, faults, rng, now - timedelta(seconds=i * interval), skip=skip)


def build_replay(settings: Settings, rng: random.Random) -> ReplaySource | None:
    if settings.sim_mode != "replay":
        return None
    return ReplaySource.load(
        Path(settings.replay_dir),
        start=datetime.fromisoformat(settings.replay_start),
        speed=settings.replay_speed,
        stage_seconds=settings.replay_stage_minutes * 60,
        rng=rng,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    faults = parse_faults(settings.sim_faults)
    rng = random.Random()
    replay = build_replay(settings, rng)
    pool = create_pool(settings.database_url, max_size=2)
    seed_machines(pool, replay.profiles if replay else None)
    replayed = frozenset(replay.machine_ids) if replay else frozenset()

    running = True

    def stop(_signum: int, _frame: FrameType | None) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    backfill(
        pool, faults, rng, settings.sim_backfill_minutes, settings.sim_interval_seconds, replayed
    )
    log.info("simulating %d machines, faults=%s", len(MACHINES), faults or "none")
    if replay:
        log.info(
            "replaying real data for %s from %s at %gx",
            ", ".join(sorted(replayed)),
            settings.replay_start,
            settings.replay_speed,
        )

    started = time.monotonic()
    while running:
        tick(pool, faults, rng, datetime.now(UTC), replay, time.monotonic() - started)
        with pool.connection() as conn:
            cutoff = datetime.now(UTC) - RETENTION
            conn.execute("DELETE FROM sensor_readings WHERE ts < %s", (cutoff,))
        with contextlib.suppress(OSError):
            HEARTBEAT.touch()
        time.sleep(settings.sim_interval_seconds)
    pool.close()


if __name__ == "__main__":
    main()
