"""Replay of real public datasets as if they were live sensor feeds.

* C-1 (compressor) follows the MetroPT-3 dataset (UCI): pneumatic panel pressure, oil
  temperature, motor current and the loaded duty cycle derived from it.
* P-3 (pump) follows the CWRU bearing dataset: vibration velocity and high-frequency
  bearing acceleration computed from the drive-end accelerometer, cycling through a
  healthy recording and inner-race faults of growing size.

Channels a dataset does not measure stay simulated (healthy). The files are produced by
scripts/download_datasets.py.
"""

from __future__ import annotations

import csv
import dataclasses
import gzip
import json
import logging
import random
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from core.machines import Limit, Machine
from simulator.model import Reading, sample

log = logging.getLogger(__name__)

METROPT_FILE = "metropt3_c1.csv.gz"
CWRU_FILE = "cwru_p3.csv"
PROFILES_FILE = "replay_profiles.json"
# Which dataset feeds which machine
METROPT_MACHINE = "C-1"
CWRU_MACHINE = "P-3"


class ReplayDataMissingError(RuntimeError):
    pass


@dataclass(frozen=True)
class MetroPTRow:
    ts: datetime
    pressure_bar: float
    oil_temperature_c: float
    motor_current_a: float
    load_duty_pct: float


def _read_metropt(path: Path) -> Iterator[MetroPTRow]:
    with gzip.open(path, "rt", newline="") as f:
        for row in csv.DictReader(f):
            yield MetroPTRow(
                ts=datetime.fromisoformat(row["ts"]),
                pressure_bar=float(row["tp3"]),
                oil_temperature_c=float(row["oil_temperature"]),
                motor_current_a=float(row["motor_current"]),
                load_duty_pct=float(row["load_duty_pct"]),
            )


class MetroPTStream:
    """Walks through the dataset at `speed` dataset seconds per wall-clock second."""

    def __init__(self, path: Path, start: datetime, speed: float) -> None:
        if speed <= 0:
            raise ValueError("replay speed must be positive")
        self.path = path
        self.start = start
        self.speed = speed
        self._rows = self._from_start()
        self._pending: MetroPTRow | None = next(self._rows, None)
        if self._pending is None:
            raise ReplayDataMissingError(f"no MetroPT-3 data at or after {start}")
        self.last = self._pending

    def _from_start(self) -> Iterator[MetroPTRow]:
        return (r for r in _read_metropt(self.path) if r.ts >= self.start)

    def advance(self, elapsed_seconds: float) -> MetroPTRow:
        """Rows up to the dataset time matching `elapsed_seconds`, averaged into one reading."""
        target = self.start + timedelta(seconds=elapsed_seconds * self.speed)
        batch: list[MetroPTRow] = []
        while self._pending is not None and self._pending.ts <= target:
            batch.append(self._pending)
            self._pending = next(self._rows, None)
        if self._pending is None:
            log.info("MetroPT-3 replay reached the end of the data, starting over")
            self._rows = self._from_start()
            self._pending = next(self._rows, None)
        if batch:
            n = len(batch)
            self.last = MetroPTRow(
                ts=batch[-1].ts,
                pressure_bar=round(sum(r.pressure_bar for r in batch) / n, 3),
                oil_temperature_c=round(sum(r.oil_temperature_c for r in batch) / n, 2),
                motor_current_a=round(sum(r.motor_current_a for r in batch) / n, 3),
                load_duty_pct=batch[-1].load_duty_pct,
            )
        return self.last


@dataclass(frozen=True)
class CWRUWindow:
    stage: str
    velocity_mm_s: float
    bearing_accel_g: float


class CWRUStream:
    """Cycles through the CWRU recordings, `stage_seconds` of wall-clock time per condition."""

    def __init__(self, path: Path, stage_seconds: float) -> None:
        if stage_seconds <= 0:
            raise ValueError("stage duration must be positive")
        self.stage_seconds = stage_seconds
        self.stages: dict[str, list[CWRUWindow]] = {}
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                self.stages.setdefault(row["stage"], []).append(
                    CWRUWindow(
                        stage=row["stage"],
                        velocity_mm_s=float(row["velocity_mm_s"]),
                        bearing_accel_g=float(row["bearing_accel_g"]),
                    )
                )
        if not self.stages:
            raise ReplayDataMissingError(f"{path} is empty")
        self._order = list(self.stages)
        self._tick = 0

    def stage_at(self, elapsed_seconds: float) -> str:
        index = int(elapsed_seconds // self.stage_seconds) % len(self._order)
        return self._order[index]

    def advance(self, elapsed_seconds: float) -> CWRUWindow:
        windows = self.stages[self.stage_at(elapsed_seconds)]
        window = windows[self._tick % len(windows)]
        self._tick += 1
        return window


def load_profiles(directory: Path) -> dict[str, Machine]:
    """Machine registry entries for the replayed assets, written by the download script."""
    path = directory / PROFILES_FILE
    if not path.exists():
        raise ReplayDataMissingError(
            f"{path} not found. Run `make datasets` (scripts/download_datasets.py) first."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    profiles = {}
    for entry in data["machines"]:
        limits = tuple(Limit.from_dict(d) for d in entry.pop("limits", []))
        machine = Machine(**entry, limits=limits)
        profiles[machine.id] = machine
    return profiles


class ReplaySource:
    """Produces readings for the replayed machines; everything else is left to the simulator."""

    def __init__(
        self,
        profiles: dict[str, Machine],
        metropt: MetroPTStream,
        cwru: CWRUStream,
        rng: random.Random,
    ) -> None:
        self.profiles = profiles
        self.metropt = metropt
        self.cwru = cwru
        self.rng = rng

    @classmethod
    def load(
        cls,
        directory: Path,
        *,
        start: datetime,
        speed: float,
        stage_seconds: float,
        rng: random.Random,
    ) -> ReplaySource:
        for name in (METROPT_FILE, CWRU_FILE):
            if not (directory / name).exists():
                missing = directory / name
                raise ReplayDataMissingError(f"{missing} not found. Run `make datasets` first.")
        return cls(
            load_profiles(directory),
            MetroPTStream(directory / METROPT_FILE, start, speed),
            CWRUStream(directory / CWRU_FILE, stage_seconds),
            rng,
        )

    @property
    def machine_ids(self) -> set[str]:
        return set(self.profiles)

    def reading(self, machine_id: str, ts: datetime, elapsed_seconds: float) -> Reading:
        machine = self.profiles[machine_id]
        # Healthy simulated values for the channels the dataset does not cover
        base = sample(machine, ts, None, self.rng)
        if machine_id == METROPT_MACHINE:
            row = self.metropt.advance(elapsed_seconds)
            return dataclasses.replace(
                base,
                temperature_c=row.oil_temperature_c,
                pressure_bar=row.pressure_bar,
                current_a=row.motor_current_a,
                load_duty_pct=row.load_duty_pct,
            )
        if machine_id == CWRU_MACHINE:
            window = self.cwru.advance(elapsed_seconds)
            return dataclasses.replace(
                base,
                vibration_mm_s=round(window.velocity_mm_s, 3),
                bearing_accel_g=round(window.bearing_accel_g, 4),
            )
        return base
