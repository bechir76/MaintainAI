"""Synthetic sensor model: normal behaviour per machine type plus injectable faults."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, get_args

from core.machines import MACHINES, Machine

FaultKind = Literal["high_vibration", "overheating", "low_pressure", "overcurrent"]
FAULT_KINDS: tuple[str, ...] = get_args(FaultKind)


@dataclass(frozen=True)
class Reading:
    machine_id: str
    ts: datetime
    temperature_c: float
    vibration_mm_s: float
    pressure_bar: float | None
    current_a: float


# Normal operating point: (temperature, vibration, pressure, current as fraction of rated)
_BASELINE: dict[str, tuple[float, float, float | None, float]] = {
    "pump": (58.0, 2.1, 6.0, 0.82),
    "motor": (98.0, 1.3, None, 0.78),
    "compressor": (88.0, 2.4, 7.25, 0.88),
}

# Values a fault drives the signal towards, chosen to sit beyond the alarm limit.
_FAULT_VIBRATION = {"pump": 7.9, "motor": 5.3, "compressor": 7.9}
_FAULT_TEMPERATURE = {"pump": 93.0, "motor": 151.0, "compressor": 112.0}
_FAULT_PRESSURE = {"pump": 3.2, "compressor": 6.0}


def parse_faults(spec: str) -> dict[str, FaultKind]:
    """Parse "P-3:high_vibration,M-2:overheating" into {machine_id: fault}."""
    faults: dict[str, FaultKind] = {}
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        machine_id, sep, kind = item.partition(":")
        if not sep or machine_id not in MACHINES:
            raise ValueError(f"unknown machine in fault spec: {item!r}")
        if kind not in FAULT_KINDS:
            raise ValueError(f"unknown fault {kind!r}; expected one of {FAULT_KINDS}")
        faults[machine_id] = kind  # type: ignore[assignment]
    return faults


def sample(machine: Machine, ts: datetime, fault: FaultKind | None, rng: random.Random) -> Reading:
    temp, vib, pressure, load = _BASELINE[machine.type]
    current = machine.rated_current_a * load

    if machine.type == "compressor" and pressure is not None:
        # Load/unload cycle between 7.0 and 7.5 bar
        pressure += 0.25 * math.sin(ts.timestamp() / 60.0)

    if fault == "high_vibration":
        vib = _FAULT_VIBRATION[machine.type]
        temp += 6.0
    elif fault == "overheating":
        temp = _FAULT_TEMPERATURE[machine.type]
        current = machine.rated_current_a * 1.02
    elif fault == "low_pressure" and pressure is not None:
        pressure = _FAULT_PRESSURE[machine.type]
    elif fault == "overcurrent":
        current = machine.rated_current_a * 1.2
        temp += 10.0

    return Reading(
        machine_id=machine.id,
        ts=ts,
        temperature_c=round(rng.gauss(temp, temp * 0.01), 2),
        vibration_mm_s=round(max(0.1, rng.gauss(vib, vib * 0.05)), 2),
        pressure_bar=None if pressure is None else round(rng.gauss(pressure, 0.05), 2),
        current_a=round(rng.gauss(current, current * 0.01), 2),
    )
