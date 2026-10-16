"""Anomaly flags for sensor readings, following the rules of site standard CMS-001.

A limit counts as reached when the median of the last three readings is beyond
it, so a single spike is reported in the statistics but does not raise a flag.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import median
from typing import Literal

from core.machines import Limit, Machine, Metric, limits_for

Level = Literal["warning", "alarm"]
Status = Literal["ok", "warning", "alarm", "no_data"]
METRICS: tuple[Metric, ...] = (
    "temperature_c",
    "vibration_mm_s",
    "pressure_bar",
    "current_a",
    "bearing_accel_g",
    "load_duty_pct",
)
EVALUATION_WINDOW = 3


@dataclass(frozen=True)
class Flag:
    metric: Metric
    label: str
    level: Level
    value: float
    limit: float
    direction: Literal["high", "low"]
    source: str

    @property
    def message(self) -> str:
        relation = "above" if self.direction == "high" else "below"
        return f"{self.label} {self.value:g} is {relation} the {self.level} limit of {self.limit:g}"


@dataclass(frozen=True)
class MetricStats:
    latest: float
    minimum: float
    maximum: float
    mean: float


def _beyond(value: float, threshold: float, direction: str) -> bool:
    return value >= threshold if direction == "high" else value <= threshold


def evaluate_limit(limit: Limit, values: Sequence[float]) -> Flag | None:
    """`values` are in chronological order."""
    if not values:
        return None
    value = round(median(values[-EVALUATION_WINDOW:]), 2)
    for level, threshold in (("alarm", limit.alarm), ("warning", limit.warning)):
        if _beyond(value, threshold, limit.direction):
            return Flag(
                metric=limit.metric,
                label=limit.label,
                level=level,  # type: ignore[arg-type]
                value=value,
                limit=threshold,
                direction=limit.direction,
                source=limit.source,
            )
    return None


def evaluate(machine: Machine, series: dict[Metric, list[float]]) -> list[Flag]:
    flags = []
    for limit in limits_for(machine):
        flag = evaluate_limit(limit, series.get(limit.metric, []))
        if flag:
            flags.append(flag)
    return sorted(flags, key=lambda f: f.level != "alarm")


def overall_status(flags: Sequence[Flag], has_data: bool) -> Status:
    if not has_data:
        return "no_data"
    if any(f.level == "alarm" for f in flags):
        return "alarm"
    if flags:
        return "warning"
    return "ok"


def stats(series: dict[Metric, list[float]]) -> dict[Metric, MetricStats]:
    return {
        metric: MetricStats(
            latest=values[-1],
            minimum=min(values),
            maximum=max(values),
            mean=round(sum(values) / len(values), 2),
        )
        for metric, values in series.items()
        if values
    }
