"""Machine registry and alarm limits.

The limits mirror the tables in the sample manuals (CMS-001 p.2 is the site-wide
reference); each one carries its source so anomaly flags can be cited.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

MachineType = Literal["pump", "motor", "compressor"]
Metric = Literal[
    "temperature_c",
    "vibration_mm_s",
    "pressure_bar",
    "current_a",
    "bearing_accel_g",  # high-frequency bearing acceleration, only from replayed CWRU data
    "load_duty_pct",  # share of the last 30 min the compressor ran loaded, from MetroPT-3
]


@dataclass(frozen=True)
class Limit:
    metric: Metric
    label: str
    warning: float
    alarm: float
    direction: Literal["high", "low"] = "high"
    source: str = "CMS-001 Condition Monitoring Alarm Limits, p.2"

    def to_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric,
            "label": self.label,
            "warning": self.warning,
            "alarm": self.alarm,
            "direction": self.direction,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Limit:
        return cls(
            metric=data["metric"],
            label=data["label"],
            warning=float(data["warning"]),
            alarm=float(data["alarm"]),
            direction=data.get("direction", "high"),
            source=data.get("source", ""),
        )


@dataclass(frozen=True)
class Machine:
    id: str
    name: str
    type: MachineType
    model: str
    location: str
    rated_current_a: float
    data_source: str = "simulated"
    # Per-machine limits replacing (or adding to) the type defaults, e.g. for replayed assets
    limits: tuple[Limit, ...] = ()


MACHINES: dict[str, Machine] = {
    m.id: m
    for m in (
        Machine("P-1", "Cooling water pump", "pump", "P-80/200", "Utility building, loop A", 27.0),
        Machine(
            "P-3", "Process water transfer pump", "pump", "P-100/250", "Process hall, line 2", 54.0
        ),
        Machine("M-1", "Exhaust fan motor", "motor", "M-200L", "Roof, fan station 1", 56.0),
        Machine("M-2", "Conveyor drive motor", "motor", "M-225M", "Packaging, conveyor C4", 82.0),
        Machine("C-1", "Plant air compressor", "compressor", "C-37", "Compressor room", 67.0),
    )
}


# Current limits are expressed as a fraction of the machine's rated current.
CURRENT_WARNING_RATIO = 1.05
CURRENT_ALARM_RATIO = 1.15

LIMITS: dict[MachineType, tuple[Limit, ...]] = {
    "pump": (
        Limit("vibration_mm_s", "Bearing housing vibration (mm/s RMS)", 4.5, 7.1),
        Limit("temperature_c", "Bearing temperature (°C)", 80.0, 90.0),
        Limit("pressure_bar", "Discharge pressure (bar)", 4.5, 3.5, direction="low"),
    ),
    "motor": (
        Limit("vibration_mm_s", "Bearing housing vibration (mm/s RMS)", 2.8, 4.5),
        Limit("temperature_c", "Stator winding temperature (°C)", 130.0, 145.0),
    ),
    "compressor": (
        Limit("vibration_mm_s", "Airend vibration (mm/s RMS)", 4.5, 7.1),
        Limit("temperature_c", "Airend discharge temperature (°C)", 105.0, 110.0),
        Limit("pressure_bar", "Delivery pressure (bar)", 8.5, 9.0),
    ),
}


def limits_for(machine: Machine) -> tuple[Limit, ...]:
    current = Limit(
        "current_a",
        "Motor current (A)",
        round(machine.rated_current_a * CURRENT_WARNING_RATIO, 2),
        round(machine.rated_current_a * CURRENT_ALARM_RATIO, 2),
    )
    limits = {lim.metric: lim for lim in (*LIMITS[machine.type], current)}
    limits.update({lim.metric: lim for lim in machine.limits})
    return tuple(limits.values())
