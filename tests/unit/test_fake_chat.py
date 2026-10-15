import json

from core.llm.base import ChatMessage, TextDelta, ToolCallsRequested, ToolSpec
from core.llm.fake_chat import REFUSAL, FakeChatModel

ALL_TOOLS = {"search_manuals", "get_sensor_readings", "create_maintenance_ticket", "list_machines"}


def test_plan_reads_sensors_and_searches_for_named_machine() -> None:
    calls = FakeChatModel().plan("Pump P-3 is vibrating, what should I check?", ALL_TOOLS)
    assert [(c.name, c.arguments) for c in calls] == [
        ("get_sensor_readings", {"machine_id": "P-3", "minutes": 10}),
        (
            "search_manuals",
            {"query": "Pump is vibrating, what should I check?", "machine_type": "pump"},
        ),
    ]


def test_plan_ticket_only_when_asked() -> None:
    calls = FakeChatModel().plan("Create a ticket for m2, winding alarm", ALL_TOOLS)
    ticket = next(c for c in calls if c.name == "create_maintenance_ticket")
    assert ticket.arguments["machine_id"] == "M-2"
    assert ticket.arguments["priority"] == "high"
    assert "create_maintenance_ticket" not in {
        c.name for c in FakeChatModel().plan("M-2 is hot", ALL_TOOLS)
    }


def test_plan_uses_type_words_and_list_machines() -> None:
    calls = FakeChatModel().plan("Which machines are in alarm? compressor first", ALL_TOOLS)
    assert calls[0].name == "list_machines"
    assert calls[-1].arguments["machine_type"] == "compressor"


def test_compose_cites_best_sentence() -> None:
    passages = {
        "passages": [
            {
                "id": "S1",
                "text": "Short.\nRegrease the bearings every 4,000 operating hours with 15 g.",
            }
        ]
    }
    answer = FakeChatModel().compose(
        "How often to regrease bearings?", [("search_manuals", passages)]
    )
    assert "Regrease the bearings every 4,000 operating hours with 15 g. [S1]" in answer


def test_compose_reports_permission_error_and_refuses_without_evidence() -> None:
    model = FakeChatModel()
    denied = model.compose(
        "ticket", [("create_maintenance_ticket", {"error": "Permission denied"})]
    )
    assert "could not create the ticket" in denied
    assert model.compose("anything", [("search_manuals", {"passages": []})]) == REFUSAL


async def test_stream_round_trip() -> None:
    model = FakeChatModel()
    tools = [ToolSpec("search_manuals", "", {})]
    first = [e async for e in model.stream([ChatMessage("user", "pump vibration limits")], tools)]
    assert isinstance(first[0], ToolCallsRequested)

    payload = {"passages": [{"id": "S1", "text": "The vibration alarm limit is 7.1 mm/s RMS."}]}
    history = [
        ChatMessage("user", "pump vibration limits"),
        ChatMessage("assistant", "", tool_calls=first[0].calls),
        ChatMessage("tool", json.dumps(payload), tool_call_id="call1", name="search_manuals"),
    ]
    second = [e async for e in model.stream(history, tools)]
    text = "".join(e.text for e in second if isinstance(e, TextDelta))
    assert text.endswith("The vibration alarm limit is 7.1 mm/s RMS. [S1]")
