import json
from collections.abc import Callable

import httpx
import pytest

from core.llm.base import ChatMessage, LLMError, TextDelta, ToolCall, ToolCallsRequested, ToolSpec
from core.llm.mistral import MistralChatModel, MistralEmbedder

Handler = Callable[[httpx.Request], httpx.Response]


def sse(*chunks: dict[str, object]) -> bytes:
    lines = [f"data: {json.dumps(c)}\n\n" for c in chunks] + ["data: [DONE]\n\n"]
    return "".join(lines).encode()


async def test_embedder_batches_and_orders_by_index() -> None:
    calls: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body["input"])
        data = [{"index": i, "embedding": [float(len(t))]} for i, t in enumerate(body["input"])]
        return httpx.Response(200, json={"data": list(reversed(data))})

    emb = MistralEmbedder("key", batch_size=2, transport=httpx.MockTransport(handler))
    vectors = await emb.embed(["a", "bb", "ccc"])
    assert vectors == [[1.0], [2.0], [3.0]]
    assert calls == [["a", "bb"], ["ccc"]]
    await emb.aclose()


async def test_retries_on_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("core.llm.mistral.asyncio.sleep", no_sleep)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.5]}]})

    emb = MistralEmbedder("key", transport=httpx.MockTransport(handler))
    assert await emb.embed(["x"]) == [[0.5]]
    assert attempts == 3


async def test_client_error_raises_llm_error() -> None:
    emb = MistralEmbedder(
        "key", transport=httpx.MockTransport(lambda r: httpx.Response(401, text="bad key"))
    )
    with pytest.raises(LLMError, match="401"):
        await emb.embed(["x"])


async def test_timeout_raises_llm_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    emb = MistralEmbedder("key", transport=httpx.MockTransport(handler))
    with pytest.raises(LLMError, match="timed out"):
        await emb.embed(["x"])


async def test_chat_streams_text() -> None:
    body = sse(
        {"choices": [{"delta": {"role": "assistant", "content": "Check "}}]},
        {"choices": [{"delta": {"content": "the coupling."}}]},
    )
    model = MistralChatModel(
        "key",
        "mistral-small-latest",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)),
    )
    events = [e async for e in model.stream([ChatMessage("user", "hi")], [])]
    assert events == [TextDelta("Check "), TextDelta("the coupling.")]
    await model.aclose()


async def test_chat_collects_tool_calls_and_sends_wire_format() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(
            200,
            content=sse(
                {
                    "choices": [
                        {
                            "delta": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "abc123xyz",
                                        "function": {
                                            "name": "get_sensor_readings",
                                            "arguments": '{"machine_id": "P-3"}',
                                        },
                                    },
                                    {
                                        "id": "def456uvw",
                                        "function": {"name": "search_manuals", "arguments": "{bad"},
                                    },
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                }
            ),
        )

    history = [
        ChatMessage("system", "rules"),
        ChatMessage(
            "assistant", "", tool_calls=[ToolCall("id1", "search_manuals", {"query": "q"})]
        ),
        ChatMessage("tool", "{}", tool_call_id="id1", name="search_manuals"),
    ]
    tools = [ToolSpec("get_sensor_readings", "Read sensors", {"type": "object"})]
    model = MistralChatModel("key", "m", transport=httpx.MockTransport(handler))
    events = [e async for e in model.stream(history, tools)]

    assert events == [
        ToolCallsRequested(
            [
                ToolCall("abc123xyz", "get_sensor_readings", {"machine_id": "P-3"}),
                ToolCall("def456uvw", "search_manuals", {"_raw": "{bad"}),
            ]
        )
    ]
    assert seen["tool_choice"] == "auto"
    messages = seen["messages"]
    assert isinstance(messages, list)
    assert messages[1]["tool_calls"][0]["function"]["arguments"] == '{"query": "q"}'
    assert messages[2]["tool_call_id"] == "id1"
    assert messages[2]["name"] == "search_manuals"
