import random
from datetime import UTC, datetime

import pytest

from core.machines import MACHINES, limits_for
from simulator.model import parse_faults, sample

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_parse_faults() -> None:
    assert parse_faults("P-3:high_vibration, M-2:overheating,") == {
        "P-3": "high_vibration",
        "M-2": "overheating",
    }
    assert parse_faults("") == {}


@pytest.mark.parametrize("spec", ["X-9:overheating", "P-3:melting", "P-3"])
def test_parse_faults_rejects_bad_input(spec: str) -> None:
    with pytest.raises(ValueError):
        parse_faults(spec)


@pytest.mark.parametrize("machine_id", list(MACHINES))
def test_healthy_machine_stays_below_warning(machine_id: str) -> None:
    machine = MACHINES[machine_id]
    rng = random.Random(1)
    for _ in range(200):
        reading = sample(machine, NOW, None, rng)
        for limit in limits_for(machine):
            value = getattr(reading, limit.metric)
            if value is None:
                continue
            if limit.direction == "high":
                assert value < limit.warning, (limit.metric, value)
            else:
                assert value > limit.warning, (limit.metric, value)


@pytest.mark.parametrize(
    ("machine_id", "fault", "metric"),
    [
        ("P-3", "high_vibration", "vibration_mm_s"),
        ("M-2", "overheating", "temperature_c"),
        ("C-1", "overheating", "temperature_c"),
        ("P-1", "low_pressure", "pressure_bar"),
        ("M-1", "overcurrent", "current_a"),
    ],
)
def test_fault_drives_metric_past_alarm(machine_id: str, fault: str, metric: str) -> None:
    machine = MACHINES[machine_id]
    limit = next(lim for lim in limits_for(machine) if lim.metric == metric)
    reading = sample(machine, NOW, fault, random.Random(3))  # type: ignore[arg-type]
    value = getattr(reading, metric)
    if limit.direction == "high":
        assert value > limit.alarm
    else:
        assert value < limit.alarm


def test_motor_has_no_pressure_sensor() -> None:
    reading = sample(MACHINES["M-1"], NOW, "low_pressure", random.Random(0))
    assert reading.pressure_bar is None
