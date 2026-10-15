import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest

from api.agent import NO_EVIDENCE, Agent, AgentEvent
from core.config import Settings
from core.llm.base import ChatEvent, ChatMessage, TextDelta, ToolCall, ToolCallsRequested, ToolSpec

PASSAGE = {
    "doc_id": "P-MT-02",
    "document": "P-MT-02_pump_maintenance_troubleshooting.pdf",
    "title": "P-Series Centrifugal Pumps - Maintenance and Troubleshooting Guide",
    "page": 3,
    "score": 0.41,
    "text": "If the vibration exceeds 7.1 mm/s RMS, stop the pump and investigate.",
    "flagged": False,
    "findings": [],
}
SENSOR = {
    "machine": {"id": "P-3", "name": "Process water transfer pump", "model": "P-100/250"},
    "window_minutes": 10,
    "count": 3,
    "status": "alarm",
    "flags": [{"message": "Vibration 7.9 is above the alarm limit of 7.1"}],
    "stats": {"vibration_mm_s": {"latest": 7.9, "min": 7.5, "max": 8.1, "mean": 7.8}},
    "recent": [],
}
TOOLS = [
    ToolSpec(name, "", {"type": "object"})
    for name in ("search_manuals", "get_sensor_readings", "create_maintenance_ticket")
]


class ScriptedModel:
    """Plays back one list of events per model turn and records what it was offered."""

    name = "scripted"

    def __init__(self, turns: list[list[ChatEvent]], delay: float = 0.0) -> None:
        self.turns = turns
        self.delay = delay
        self.offered: list[list[str]] = []
        self.seen: list[list[ChatMessage]] = []

    async def stream(
        self, messages: Sequence[ChatMessage], tools: Sequence[ToolSpec]
    ) -> AsyncIterator[ChatEvent]:
        self.offered.append([t.name for t in tools])
        self.seen.append(list(messages))
        if self.delay:
            await asyncio.sleep(self.delay)
        turn = self.turns.pop(0) if self.turns else [TextDelta("final answer")]
        for event in turn:
            yield event


class StubTools:
    def __init__(self, responses: dict[str, dict[str, Any]], delay: float = 0.0) -> None:
        self.responses = responses
        self.delay = delay
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_tools(self) -> list[ToolSpec]:
        return TOOLS

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, arguments))
        if self.delay:
            await asyncio.sleep(self.delay)
        return self.responses.get(name, {"error": "unknown"})


def call(name: str, idx: int = 1, **args: Any) -> ToolCall:
    return ToolCall(f"c{idx}", name, args)


async def run(
    model: ScriptedModel, tools: StubTools, question: str, **settings: Any
) -> list[AgentEvent]:
    events: list[AgentEvent] = []

    async def emit(event: AgentEvent) -> None:
        events.append(event)

    agent = Agent(model, Settings(_env_file=None, **settings))
    await agent.run_with(tools, question, emit)
    return events


def text_of(events: list[AgentEvent]) -> str:
    return "".join(e.data["text"] for e in events if e.type == "token")


def of_type(events: list[AgentEvent], kind: str) -> list[dict[str, Any]]:
    return [e.data for e in events if e.type == kind]


async def test_grounded_answer_streams_with_used_citations() -> None:
    model = ScriptedModel(
        [
            [
                ToolCallsRequested(
                    [
                        call("search_manuals", 1, query="vibration"),
                        call("get_sensor_readings", 2, machine_id="P-3"),
                    ]
                )
            ],
            [TextDelta("P-3 is in alarm [L1]. "), TextDelta("Stop the pump [S1]. Also [S9].")],
        ]
    )
    tools = StubTools({"search_manuals": {"results": [PASSAGE]}, "get_sensor_readings": SENSOR})
    events = await run(model, tools, "Pump P-3 is vibrating, what should I check?")

    assert text_of(events) == "P-3 is in alarm [L1]. Stop the pump [S1]. Also [S9]."
    [citations] = of_type(events, "citations")
    assert [c["id"] for c in citations["citations"]] == ["L1", "S1"]  # S9 does not exist
    assert citations["citations"][1]["page"] == 3
    assert "Vibration 7.9" in citations["citations"][0]["text"]
    assert of_type(events, "done")[0]["grounded"] is True
    assert [e["name"] for e in of_type(events, "tool_end")] == [
        "search_manuals",
        "get_sensor_readings",
    ]
    # The model saw tool results with stable ids and the system prompt first.
    tool_msgs = [m for m in model.seen[1] if m.role == "tool"]
    assert '"id": "S1"' in tool_msgs[0].content
    assert model.seen[0][0].role == "system"


async def test_answer_without_evidence_is_replaced_and_never_streamed() -> None:
    model = ScriptedModel(
        [
            [ToolCallsRequested([call("search_manuals", query="warranty")])],
            [TextDelta("The warranty is 5 years.")],  # made up by the model
        ]
    )
    tools = StubTools({"search_manuals": {"results": [], "note": "not covered"}})
    events = await run(model, tools, "What is the warranty of a Siemens turbine?")
    assert text_of(events) == NO_EVIDENCE
    assert "warranty" not in text_of(events)
    assert of_type(events, "citations")[0]["citations"] == []
    assert of_type(events, "done")[0]["grounded"] is False


async def test_model_answering_without_tools_gets_refusal() -> None:
    events = await run(ScriptedModel([[TextDelta("From memory: 42.")]]), StubTools({}), "hi")
    assert text_of(events) == NO_EVIDENCE


async def test_tool_call_budget_is_enforced() -> None:
    greedy = [[ToolCallsRequested([call("search_manuals", i, query=f"q{i}")])] for i in range(10)]
    model = ScriptedModel(greedy)
    tools = StubTools({"search_manuals": {"results": [PASSAGE]}})
    events = await run(model, tools, "question", agent_max_tool_calls=3)

    assert len(tools.calls) == 3
    assert of_type(events, "done")[0]["tool_calls"] == 3
    # Once the budget is spent the model is called without tools to force an answer.
    assert model.offered[3] == []


async def test_extra_calls_in_one_turn_beyond_budget_are_refused() -> None:
    calls = [call("search_manuals", i, query="x") for i in range(4)]
    model = ScriptedModel([[ToolCallsRequested(calls)], [TextDelta("done [S1]")]])
    tools = StubTools({"search_manuals": {"results": [PASSAGE]}})
    await run(model, tools, "question", agent_max_tool_calls=2)
    assert len(tools.calls) == 2
    refused = [m for m in model.seen[1] if m.role == "tool" and "limit reached" in m.content]
    assert len(refused) == 2


async def test_ticket_requires_explicit_request() -> None:
    model = ScriptedModel(
        [
            [ToolCallsRequested([call("create_maintenance_ticket", machine_id="P-3")])],
            [TextDelta("ok")],
        ]
    )
    tools = StubTools({"create_maintenance_ticket": {"ticket_id": 1}})
    events = await run(model, tools, "Pump P-3 is vibrating, what should I check?")
    assert tools.calls == []
    assert of_type(events, "tool_end")[0]["status"] == "blocked"


async def test_ticket_with_explicit_request_is_executed() -> None:
    model = ScriptedModel(
        [
            [ToolCallsRequested([call("create_maintenance_ticket", machine_id="P-3")])],
            [TextDelta("Created.")],
        ]
    )
    tools = StubTools({"create_maintenance_ticket": {"ticket_id": 7, "machine_id": "P-3"}})
    events = await run(model, tools, "Please open a ticket for P-3")
    assert tools.calls[0][0] == "create_maintenance_ticket"
    assert of_type(events, "tool_end")[0] == {
        "id": "c1",
        "name": "create_maintenance_ticket",
        "status": "ok",
        "summary": "ticket #7 created",
    }
    assert text_of(events) == "Created."


async def test_permission_error_is_reported_as_denied() -> None:
    model = ScriptedModel(
        [[ToolCallsRequested([call("create_maintenance_ticket")])], [TextDelta("No.")]]
    )
    tools = StubTools({"create_maintenance_ticket": {"error": "Permission denied: role viewer"}})
    events = await run(model, tools, "create a ticket for P-3")
    assert of_type(events, "tool_end")[0]["status"] == "denied"


async def test_slow_tool_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("api.agent.TOOL_TIMEOUT", 0.05)
    model = ScriptedModel([[ToolCallsRequested([call("search_manuals", query="x")])]])
    tools = StubTools({"search_manuals": {"results": [PASSAGE]}}, delay=1.0)
    events = await run(model, tools, "question")
    assert of_type(events, "tool_end")[0]["summary"] == "search_manuals timed out"
    assert text_of(events) == NO_EVIDENCE


async def test_slow_model_times_out() -> None:
    model = ScriptedModel([[TextDelta("late")]], delay=1.0)
    with pytest.raises(TimeoutError):
        await run(model, StubTools({}), "question", llm_timeout_seconds=0.05)


async def test_run_reports_unreachable_mcp_server() -> None:
    events: list[AgentEvent] = []

    async def emit(event: AgentEvent) -> None:
        events.append(event)

    settings = Settings(_env_file=None, mcp_server_url="http://127.0.0.1:9/mcp")
    await Agent(ScriptedModel([]), settings).run("question", "viewer", emit)
    assert [e.type for e in events] == ["error"]


async def test_run_reports_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[AgentEvent] = []

    async def emit(event: AgentEvent) -> None:
        events.append(event)

    async def slow(*args: Any, **kwargs: Any) -> None:
        await asyncio.sleep(1)

    agent = Agent(ScriptedModel([]), Settings(_env_file=None, agent_timeout_seconds=0.05))
    monkeypatch.setattr(agent, "run_with", slow)
    monkeypatch.setattr("api.agent.connect", _null_connect)
    await agent.run("question", "viewer", emit)
    assert events[0].data["message"].startswith("The request took too long")


class _NullClient:
    async def __aenter__(self) -> "_NullClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None


def _null_connect(*args: Any, **kwargs: Any) -> _NullClient:
    return _NullClient()
