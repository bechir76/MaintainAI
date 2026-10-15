import pytest
from pydantic import ValidationError

from mcp_server.schemas import CreateTicketInput, SearchManualsInput, SensorReadingsInput


def test_machine_id_is_normalised() -> None:
    assert SensorReadingsInput(machine_id="p-3").machine_id == "P-3"


@pytest.mark.parametrize("machine_id", ["P3", "P-3; DROP TABLE", "", "PUMP-3", "P-1234"])
def test_machine_id_pattern(machine_id: str) -> None:
    with pytest.raises(ValidationError):
        SensorReadingsInput(machine_id=machine_id)


@pytest.mark.parametrize("minutes", [0, 1441, -5])
def test_minutes_bounds(minutes: int) -> None:
    with pytest.raises(ValidationError):
        SensorReadingsInput(machine_id="P-3", minutes=minutes)


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchManualsInput.model_validate({"query": "pump vibration", "role": "technician"})


def test_query_is_cleaned_and_bounded() -> None:
    assert SearchManualsInput(query="  pump\x00 vibration​ ").query == "pump vibration"
    with pytest.raises(ValidationError):
        SearchManualsInput(query="x" * 501)
    with pytest.raises(ValidationError):
        SearchManualsInput(query="pump", machine_type="turbine")  # type: ignore[arg-type]


def test_ticket_priority_and_lengths() -> None:
    ticket = CreateTicketInput(
        machine_id="m-2",
        title="Winding temperature alarm",
        description="Winding at 151 C, above the 145 C alarm limit.",
        priority="high",
    )
    assert ticket.machine_id == "M-2"
    with pytest.raises(ValidationError):
        CreateTicketInput(
            machine_id="M-2",
            title="Hot",
            description="too short",
            priority="urgent",  # type: ignore[arg-type]
        )
