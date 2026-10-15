"""Mistral AI chat (with tool calling) and embeddings over the REST API."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Sequence
from typing import Any

import httpx

from core.llm.base import (
    ChatEvent,
    ChatMessage,
    LLMError,
    TextDelta,
    ToolCall,
    ToolCallsRequested,
    ToolSpec,
)

log = logging.getLogger(__name__)
RETRY_STATUS = {429, 500, 502, 503, 504}


class _MistralHTTP:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = 3,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(timeout, connect=10.0),
            transport=transport,
        )
        self._max_retries = max_retries

    async def _send(self, path: str, payload: dict[str, Any], stream: bool) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            try:
                request = self._client.build_request("POST", path, json=payload)
                response = await self._client.send(request, stream=stream)
            except httpx.TimeoutException as exc:
                raise LLMError(f"Mistral request timed out: {exc}") from exc
            except httpx.HTTPError as exc:
                raise LLMError(f"Mistral request failed: {exc}") from exc
            if response.status_code in RETRY_STATUS and attempt < self._max_retries:
                await response.aclose()
                delay = float(response.headers.get("retry-after", 2**attempt))
                log.warning(
                    "mistral %s returned %s, retrying in %.1fs", path, response.status_code, delay
                )
                await asyncio.sleep(min(delay, 10.0))
                continue
            if response.status_code >= 400:
                body = (await response.aread()).decode(errors="replace")[:300]
                await response.aclose()
                raise LLMError(f"Mistral API error {response.status_code}: {body}")
            return response
        raise LLMError("unreachable")  # pragma: no cover

    async def aclose(self) -> None:
        await self._client.aclose()


def _to_wire(message: ChatMessage) -> dict[str, Any]:
    wire: dict[str, Any] = {"role": message.role, "content": message.content}
    if message.tool_calls:
        wire["tool_calls"] = [
            {
                "id": c.id,
                "type": "function",
                "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
            }
            for c in message.tool_calls
        ]
    if message.role == "tool":
        wire["tool_call_id"] = message.tool_call_id
        wire["name"] = message.name
    return wire


class MistralChatModel:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.mistral.ai/v1",
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.name = model
        self._http = _MistralHTTP(api_key, base_url, timeout, transport)

    async def stream(
        self, messages: Sequence[ChatMessage], tools: Sequence[ToolSpec]
    ) -> AsyncIterator[ChatEvent]:
        payload: dict[str, Any] = {
            "model": self.name,
            "messages": [_to_wire(m) for m in messages],
            "temperature": 0.1,
            "stream": True,
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
            payload["tool_choice"] = "auto"

        response = await self._http._send("/chat/completions", payload, stream=True)
        pending: dict[int, dict[str, str]] = {}
        try:
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta") or {}
                    if delta.get("content"):
                        yield TextDelta(delta["content"])
                    for i, call in enumerate(delta.get("tool_calls") or []):
                        slot = pending.setdefault(
                            call.get("index", i), {"id": "", "name": "", "arguments": ""}
                        )
                        slot["id"] = call.get("id") or slot["id"]
                        fn = call.get("function") or {}
                        slot["name"] = fn.get("name") or slot["name"]
                        args = fn.get("arguments") or ""
                        slot["arguments"] += args if isinstance(args, str) else json.dumps(args)
        except httpx.HTTPError as exc:
            raise LLMError(f"Mistral stream failed: {exc}") from exc
        finally:
            await response.aclose()

        if pending:
            calls = []
            for slot in pending.values():
                try:
                    arguments = json.loads(slot["arguments"] or "{}")
                except json.JSONDecodeError:
                    arguments = {"_raw": slot["arguments"]}
                calls.append(ToolCall(id=slot["id"], name=slot["name"], arguments=arguments))
            yield ToolCallsRequested(calls)

    async def aclose(self) -> None:
        await self._http.aclose()


class MistralEmbedder:
    dim = 1024

    def __init__(
        self,
        api_key: str,
        model: str = "mistral-embed",
        base_url: str = "https://api.mistral.ai/v1",
        timeout: float = 30.0,
        batch_size: int = 32,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.name = model
        self._batch_size = batch_size
        self._http = _MistralHTTP(api_key, base_url, timeout, transport)

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = list(texts[start : start + self._batch_size])
            response = await self._http._send(
                "/embeddings", {"model": self.name, "input": batch}, stream=False
            )
            data = sorted(response.json()["data"], key=lambda d: d["index"])
            vectors.extend(d["embedding"] for d in data)
        return vectors

    async def aclose(self) -> None:
        await self._http.aclose()
