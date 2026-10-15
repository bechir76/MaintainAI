"""Deterministic offline chat model.

Behaves like a tool-calling LLM with simple rules so the full agent loop
(tool selection, MCP calls, citations, refusals, permission errors) can run in
tests and CI without an API key:

* first turn: choose tools from the question (machine IDs, ticket requests);
* next turn: compose an extractive answer from the tool results, citing the
  passages it quotes.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Sequence
from typing import Any

from core.llm.base import ChatEvent, ChatMessage, TextDelta, ToolCall, ToolCallsRequested, ToolSpec
from core.llm.text import tokenize

REFUSAL = "I don't know based on the available documents."

_MACHINE_ID = re.compile(r"\b([PMC])-?(\d{1,2})\b", re.IGNORECASE)
_TYPE_BY_PREFIX = {"P": "pump", "M": "motor", "C": "compressor"}
_TYPE_WORDS = {
    "pump": "pump",
    "pumps": "pump",
    "motor": "motor",
    "motors": "motor",
    "compressor": "compressor",
    "compressors": "compressor",
}
_TICKET = re.compile(r"\b(ticket|work[- ]order)\b", re.IGNORECASE)
_ALL_MACHINES = re.compile(r"\b(all|which|every) (the )?machines?\b", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n")


def _machine_ids(text: str) -> list[str]:
    seen: list[str] = []
    for prefix, number in _MACHINE_ID.findall(text):
        machine_id = f"{prefix.upper()}-{int(number)}"
        if machine_id not in seen:
            seen.append(machine_id)
    return seen


def _machine_type(text: str, ids: list[str]) -> str | None:
    if ids:
        return _TYPE_BY_PREFIX[ids[0][0]]
    for word in re.findall(r"[a-z]+", text.lower()):
        if word in _TYPE_WORDS:
            return _TYPE_WORDS[word]
    return None


def _priority(text: str) -> str:
    lowered = text.lower()
    if any(w in lowered for w in ("critical", "urgent", "trip", "fire", "danger")):
        return "critical"
    if any(w in lowered for w in ("alarm", "high", "overheat", "vibrat")):
        return "high"
    return "medium"


class FakeChatModel:
    name = "fake-planner-v1"

    def plan(self, question: str, tool_names: set[str]) -> list[ToolCall]:
        ids = _machine_ids(question)
        machine_type = _machine_type(question, ids)
        calls: list[ToolCall] = []

        def add(name: str, args: dict[str, Any]) -> None:
            if name in tool_names:
                calls.append(ToolCall(id=f"call{len(calls) + 1}", name=name, arguments=args))

        if _ALL_MACHINES.search(question):
            add("list_machines", {})
        for machine_id in ids[:2]:
            add("get_sensor_readings", {"machine_id": machine_id, "minutes": 10})
        if _TICKET.search(question) and ids:
            add(
                "create_maintenance_ticket",
                {
                    "machine_id": ids[0],
                    "title": f"{ids[0]}: {question[:80]}".strip(),
                    "description": question[:1000],
                    "priority": _priority(question),
                },
            )
        query = re.sub(r"\s+", " ", _MACHINE_ID.sub(" ", question)).strip()
        if len(query) >= 3:
            args: dict[str, Any] = {"query": query[:500]}
            if machine_type:
                args["machine_type"] = machine_type
            add("search_manuals", args)
        return calls

    def compose(self, question: str, results: list[tuple[str, dict[str, Any]]]) -> str:
        q_tokens = set(tokenize(question))
        lines: list[str] = []
        evidence = False

        for name, payload in results:
            if name == "create_maintenance_ticket":
                if "error" in payload:
                    lines.append(f"I could not create the ticket: {payload['error']}")
                else:
                    ticket, machine = payload.get("ticket_id"), payload.get("machine_id")
                    lines.append(
                        f"Created ticket #{ticket} for {machine} "
                        f"with priority {payload.get('priority')}."
                    )
                    evidence = True
            elif name == "get_sensor_readings" and "error" not in payload:
                evidence = True
                machine = payload.get("machine", {}).get("id", "?")
                ref = payload.get("ref", "")
                flags = payload.get("flags", [])
                if flags:
                    detail = "; ".join(f["message"] for f in flags)
                    status = payload["status"]
                    lines.append(f"Live data for {machine} shows {status}: {detail} [{ref}].")
                else:
                    lines.append(f"Live data for {machine} is within the alarm limits [{ref}].")
            elif name == "list_machines" and "error" not in payload:
                evidence = True
                flagged = [m for m in payload.get("machines", []) if m.get("status") not in ("ok",)]
                summary = ", ".join(f"{m['id']} ({m['status']})" for m in flagged) or "none"
                lines.append(f"Machines needing attention: {summary} [{payload.get('ref', '')}].")
            elif name == "search_manuals":
                passages = payload.get("passages", [])
                if passages:
                    evidence = True
                    lines.append("From the documentation:")
                for passage in passages[:3]:
                    sentence = self._best_sentence(passage.get("text", ""), q_tokens)
                    if sentence:
                        lines.append(f"- {sentence} [{passage['id']}]")

        if not evidence and not any(n == "create_maintenance_ticket" for n, _ in results):
            return REFUSAL
        return "\n".join(lines)

    @staticmethod
    def _best_sentence(text: str, q_tokens: set[str]) -> str:
        best, best_score = "", -1
        for sentence in _SENTENCE.split(text):
            sentence = sentence.strip()
            # Quote complete sentences only, not headings or table fragments.
            if len(sentence) < 25 or not sentence.endswith(".") or "[removed" in sentence:
                continue
            sentence = sentence.removeprefix("- ")
            score = len(q_tokens & set(tokenize(sentence)))
            if score > best_score:
                best, best_score = sentence, score
        return best

    async def stream(
        self, messages: Sequence[ChatMessage], tools: Sequence[ToolSpec]
    ) -> AsyncIterator[ChatEvent]:
        last_user = max(i for i, m in enumerate(messages) if m.role == "user")
        question = messages[last_user].content
        tool_messages = [m for m in messages[last_user + 1 :] if m.role == "tool"]

        if not tool_messages and tools:
            calls = self.plan(question, {t.name for t in tools})
            if calls:
                yield ToolCallsRequested(calls)
                return

        results = []
        for m in tool_messages:
            try:
                payload = json.loads(m.content)
            except json.JSONDecodeError:
                payload = {"error": m.content}
            results.append((m.name or "", payload if isinstance(payload, dict) else {}))
        answer = self.compose(question, results) if tool_messages else REFUSAL
        for word in re.findall(r"\S+\s*", answer):
            yield TextDelta(word)
