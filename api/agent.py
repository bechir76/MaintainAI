"""Tool-calling agent loop. Tools are reached only through the MCP server."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Protocol

from mcp import Client

from api.prompts import SYSTEM_PROMPT
from core.config import Role, Settings
from core.llm.base import (
    ChatMessage,
    ChatModel,
    LLMError,
    TextDelta,
    ToolCall,
    ToolCallsRequested,
    ToolSpec,
)
from core.llm.fake_chat import REFUSAL
from core.mcp_client import connect, result_payload

log = logging.getLogger("agent")

NO_EVIDENCE = (
    f"{REFUSAL} I can only answer from the equipment manuals, safety procedures and live "
    "sensor data, and I found nothing relevant for this question."
)
TICKET_INTENT = re.compile(r"\b(ticket|work[- ]?order)s?\b", re.IGNORECASE)
CITATION_REF = re.compile(r"\[((?:S|L)\d+)\]")
TOOL_TIMEOUT = 20.0

EventType = Literal["tool_start", "tool_end", "token", "citations", "done", "error"]


@dataclass(frozen=True)
class AgentEvent:
    type: EventType
    data: dict[str, Any]


Emit = Callable[[AgentEvent], Awaitable[None]]


@dataclass
class Citation:
    id: str
    kind: Literal["document", "sensor"]
    title: str
    text: str
    doc_id: str | None = None
    document: str | None = None
    page: int | None = None
    score: float | None = None
    machine_id: str | None = None


@dataclass
class Sources:
    """Gives every piece of evidence a short, stable id the model can cite."""

    items: dict[str, Citation] = field(default_factory=dict)
    _keys: dict[tuple[Any, ...], str] = field(default_factory=dict)

    def _add(self, prefix: str, key: tuple[Any, ...], make: Callable[[str], Citation]) -> str:
        if key in self._keys:
            return self._keys[key]
        ref = f"{prefix}{sum(1 for k in self.items if k.startswith(prefix)) + 1}"
        self._keys[key] = ref
        self.items[ref] = make(ref)
        return ref

    def passage(self, p: dict[str, Any]) -> str:
        return self._add(
            "S",
            ("doc", p["doc_id"], p["page"], p["text"][:120]),
            lambda ref: Citation(
                id=ref,
                kind="document",
                title=p["title"],
                text=p["text"],
                doc_id=p["doc_id"],
                document=p["document"],
                page=p["page"],
                score=p["score"],
            ),
        )

    def sensor(self, machine_id: str, title: str, text: str) -> str:
        return self._add(
            "L",
            ("sensor", machine_id, text),
            lambda ref: Citation(
                id=ref, kind="sensor", title=title, text=text, machine_id=machine_id
            ),
        )


class ToolExecutor(Protocol):
    async def list_tools(self) -> list[ToolSpec]: ...

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


class MCPToolExecutor:
    def __init__(self, client: Client) -> None:
        self._client = client

    async def list_tools(self) -> list[ToolSpec]:
        result = await self._client.list_tools()
        return [
            ToolSpec(name=t.name, description=t.description or "", parameters=t.input_schema)
            for t in result.tools
        ]

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return result_payload(await self._client.call_tool(name, arguments))


def _sensor_summary(payload: dict[str, Any]) -> str:
    machine = payload["machine"]
    units = {
        "temperature_c": "°C",
        "vibration_mm_s": "mm/s",
        "pressure_bar": "bar",
        "current_a": "A",
    }
    latest = ", ".join(
        f"{metric.split('_')[0]} {s['latest']:g} {units.get(metric, '')}".strip()
        for metric, s in payload.get("stats", {}).items()
    )
    flags = "; ".join(f["message"] for f in payload.get("flags", [])) or "no limit exceeded"
    return (
        f"{machine['id']} ({machine['name']}, {machine['model']}), last "
        f"{payload['window_minutes']} min, {payload['count']} readings. Status: "
        f"{payload['status']}. Latest: {latest}. Flags: {flags}."
    )


def _status(payload: dict[str, Any]) -> str:
    error = payload.get("error")
    if error is None:
        return "ok"
    if "Permission denied" in error:
        return "denied"
    if error.startswith("Not executed"):
        return "blocked"
    return "error"


class Agent:
    def __init__(self, model: ChatModel, settings: Settings) -> None:
        self.model = model
        self.settings = settings

    async def run(
        self, question: str, role: Role, emit: Emit, history: Sequence[ChatMessage] = ()
    ) -> None:
        """Answer `question` as `role`, reporting progress through `emit`."""
        try:
            async with asyncio.timeout(self.settings.agent_timeout_seconds):
                async with connect(
                    self.settings.mcp_server_url, self.settings.key_for_role(role)
                ) as client:
                    await self.run_with(MCPToolExecutor(client), question, emit, history)
        except TimeoutError:
            await emit(AgentEvent("error", {"message": "The request took too long. Try again."}))
        except LLMError as exc:
            log.warning("LLM failure: %s", exc)
            await emit(AgentEvent("error", {"message": "The language model is unavailable."}))
        except Exception:
            log.exception("agent run failed")
            await emit(AgentEvent("error", {"message": "The assistant failed to answer."}))

    async def run_with(
        self,
        tools: ToolExecutor,
        question: str,
        emit: Emit,
        history: Sequence[ChatMessage] = (),
    ) -> None:
        started = time.monotonic()
        specs = await tools.list_tools()
        sources = Sources()
        messages = [
            ChatMessage("system", SYSTEM_PROMPT),
            *history,
            ChatMessage("user", question),
        ]
        calls_made = 0
        evidence = False
        answer = ""
        max_calls = self.settings.agent_max_tool_calls

        for _ in range(max_calls + 2):
            offer = specs if calls_made < max_calls else []
            text, requested = await self._model_turn(messages, offer, emit, stream=evidence)
            if not requested:
                answer = text
                break
            messages.append(ChatMessage("assistant", text, tool_calls=requested))
            for call in requested:
                if calls_made >= max_calls:
                    payload = {"error": "Not executed: tool call limit reached for this question."}
                else:
                    calls_made += 1
                    payload = await self._execute(tools, call, question, emit)
                content, found = self._for_model(call.name, payload, sources)
                evidence = evidence or found
                messages.append(ChatMessage("tool", content, tool_call_id=call.id, name=call.name))

        if not evidence:
            # Nothing came back from the tools, so whatever the model wrote is not grounded.
            answer = NO_EVIDENCE
            await emit(AgentEvent("token", {"text": answer}))

        used = [ref for ref in dict.fromkeys(CITATION_REF.findall(answer)) if ref in sources.items]
        await emit(AgentEvent("citations", {"citations": [asdict(sources.items[r]) for r in used]}))
        await emit(
            AgentEvent(
                "done",
                {
                    "tool_calls": calls_made,
                    "grounded": evidence,
                    "elapsed_ms": int((time.monotonic() - started) * 1000),
                },
            )
        )

    async def _model_turn(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolSpec],
        emit: Emit,
        *,
        stream: bool,
    ) -> tuple[str, list[ToolCall]]:
        """One model call. Text is streamed to the user only once there is evidence."""
        parts: list[str] = []
        requested: list[ToolCall] = []
        async with asyncio.timeout(self.settings.llm_timeout_seconds):
            async for event in self.model.stream(messages, tools):
                if isinstance(event, TextDelta):
                    parts.append(event.text)
                    if stream:
                        await emit(AgentEvent("token", {"text": event.text}))
                elif isinstance(event, ToolCallsRequested):
                    requested.extend(event.calls)
        return "".join(parts), requested

    async def _execute(
        self, tools: ToolExecutor, call: ToolCall, question: str, emit: Emit
    ) -> dict[str, Any]:
        await emit(
            AgentEvent(
                "tool_start", {"id": call.id, "name": call.name, "arguments": call.arguments}
            )
        )
        if call.name == "create_maintenance_ticket" and not TICKET_INTENT.search(question):
            # Writes need an explicit request from the user, whatever the model was told.
            payload: dict[str, Any] = {
                "error": "Not executed: tickets are only created when the user asks for one."
            }
        else:
            try:
                async with asyncio.timeout(TOOL_TIMEOUT):
                    payload = await tools.call(call.name, call.arguments)
            except TimeoutError:
                payload = {"error": f"{call.name} timed out"}
        await emit(
            AgentEvent(
                "tool_end",
                {
                    "id": call.id,
                    "name": call.name,
                    "status": _status(payload),
                    "summary": self._summary(call.name, payload),
                },
            )
        )
        return payload

    @staticmethod
    def _summary(name: str, payload: dict[str, Any]) -> str:
        if "error" in payload:
            return str(payload["error"])[:200]
        if name == "search_manuals":
            n = len(payload.get("results", []))
            return f"{n} relevant passage{'s' if n != 1 else ''}" if n else "no relevant passages"
        if name == "get_sensor_readings":
            return f"{payload['machine']['id']}: {payload['status']}"
        if name == "list_machines":
            return f"{len(payload.get('machines', []))} machines"
        if name == "create_maintenance_ticket":
            return f"ticket #{payload.get('ticket_id')} created"
        return "done"

    @staticmethod
    def _for_model(name: str, payload: dict[str, Any], sources: Sources) -> tuple[str, bool]:
        """Tool result as shown to the model, plus whether it contains usable evidence."""
        if "error" in payload:
            return json.dumps(payload), False
        if name == "search_manuals":
            passages = []
            for p in payload.get("results", []):
                item = {
                    "id": sources.passage(p),
                    "source": f"{p['title']}, page {p['page']}",
                    "text": p["text"],
                }
                if p.get("flagged"):
                    item["warning"] = "instruction-like text was removed from this passage"
                passages.append(item)
            out: dict[str, Any] = {"passages": passages}
            if payload.get("note"):
                out["note"] = payload["note"]
            return json.dumps(out, ensure_ascii=False), bool(passages)
        if name == "get_sensor_readings":
            machine_id = payload["machine"]["id"]
            ref = sources.sensor(
                machine_id, f"{machine_id} live sensor data", _sensor_summary(payload)
            )
            return json.dumps({"ref": ref, **payload}, ensure_ascii=False), payload["count"] > 0
        if name == "list_machines":
            text = "; ".join(
                f"{m['id']} {m['name']}: {m['status']}" for m in payload.get("machines", [])
            )
            ref = sources.sensor("all", "Machine status overview", text)
            return json.dumps({"ref": ref, **payload}, ensure_ascii=False), True
        return json.dumps(payload, ensure_ascii=False), True
