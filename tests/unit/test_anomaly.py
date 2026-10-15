import pytest

from core.machines import MACHINES, Limit, limits_for
from mcp_server.anomaly import evaluate, evaluate_limit, overall_status, stats

VIBRATION = Limit("vibration_mm_s", "Vibration", 4.5, 7.1)
PRESSURE = Limit("pressure_bar", "Pressure", 4.5, 3.5, direction="low")


@pytest.mark.parametrize(
    ("values", "level"),
    [
        ([2.0, 2.1, 2.2], None),
        ([4.4, 4.6, 4.7], "warning"),
        ([7.0, 7.5, 7.8], "alarm"),
        ([7.1, 7.1, 7.1], "alarm"),  # limits are inclusive
    ],
)
def test_high_limit_levels(values: list[float], level: str | None) -> None:
    flag = evaluate_limit(VIBRATION, values)
    assert (flag.level if flag else None) == level


def test_low_limit_direction() -> None:
    flag = evaluate_limit(PRESSURE, [3.3, 3.2, 3.4])
    assert flag is not None
    assert flag.level == "alarm"
    assert flag.message == "Pressure 3.3 is below the alarm limit of 3.5"


def test_single_spike_does_not_raise_flag() -> None:
    assert evaluate_limit(VIBRATION, [2.0, 2.1, 2.0, 9.5, 2.1]) is None
    assert evaluate_limit(VIBRATION, [2.0, 9.5, 2.1]) is None


def test_only_last_three_readings_count() -> None:
    assert evaluate_limit(VIBRATION, [8.0, 8.0, 8.0, 2.0, 2.0, 2.0]) is None


def test_empty_series() -> None:
    assert evaluate_limit(VIBRATION, []) is None


def test_current_limits_follow_rated_current() -> None:
    m2 = MACHINES["M-2"]
    current = next(lim for lim in limits_for(m2) if lim.metric == "current_a")
    assert (current.warning, current.alarm) == (86.1, 94.3)


def test_evaluate_machine_sorts_alarms_first() -> None:
    flags = evaluate(
        MACHINES["M-2"],
        {
            "vibration_mm_s": [3.0, 3.0, 3.0],
            "temperature_c": [150.0, 151.0, 150.0],
            "current_a": [80.0, 81.0, 80.0],
        },
    )
    assert [(f.metric, f.level) for f in flags] == [
        ("temperature_c", "alarm"),
        ("vibration_mm_s", "warning"),
    ]
    assert flags[0].source.startswith("CMS-001")


def test_overall_status() -> None:
    alarm = evaluate_limit(VIBRATION, [8.0, 8.0, 8.0])
    warning = evaluate_limit(VIBRATION, [5.0, 5.0, 5.0])
    assert alarm is not None and warning is not None
    assert overall_status([], has_data=False) == "no_data"
    assert overall_status([], has_data=True) == "ok"
    assert overall_status([warning], has_data=True) == "warning"
    assert overall_status([warning, alarm], has_data=True) == "alarm"


def test_stats() -> None:
    result = stats({"vibration_mm_s": [1.0, 3.0, 2.0], "pressure_bar": []})
    assert list(result) == ["vibration_mm_s"]
    s = result["vibration_mm_s"]
    assert (s.latest, s.minimum, s.maximum, s.mean) == (2.0, 1.0, 3.0, 2.0)
