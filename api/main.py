from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from api.agent import Agent, AgentEvent
from core.config import Role, Settings, get_settings
from core.llm import build_chat_model
from core.llm.base import ChatMessage
from core.mcp_client import connect, result_payload

log = logging.getLogger("api")


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, Field(max_length=4000)]


class ChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=2000)]
    # Demo simplification: the UI picks the role. In production it would come from the
    # user's identity (SSO group claims), never from the request body.
    role: Role = "viewer"
    history: Annotated[list[HistoryItem], Field(max_length=20)] = []


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    model = build_chat_model(settings)
    app.state.settings = settings
    app.state.agent = Agent(model, settings)
    log.info("agent ready with model %s, MCP at %s", model.name, settings.mcp_server_url)
    yield
    aclose = getattr(model, "aclose", None)
    if aclose:
        await aclose()


app = FastAPI(title="MaintainAI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def agent_dep(request: Request) -> Agent:
    agent: Agent = request.app.state.agent
    return agent


def settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def sse(event: AgentEvent) -> str:
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"


@app.post("/chat")
async def chat(body: ChatRequest, agent: Annotated[Agent, Depends(agent_dep)]) -> StreamingResponse:
    """Answer a question as a stream of server-sent events.

    Events: tool_start, tool_end, token, citations, done, error.
    """
    queue: asyncio.Queue[AgentEvent | None] = asyncio.Queue()
    history = [ChatMessage(h.role, h.content) for h in body.history[-10:]]

    async def produce() -> None:
        try:
            await agent.run(body.message, body.role, queue.put, history)
        finally:
            await queue.put(None)

    async def stream() -> AsyncIterator[str]:
        task = asyncio.create_task(produce())
        try:
            while (event := await queue.get()) is not None:
                yield sse(event)
        finally:
            # Client went away: stop the agent instead of finishing the answer for nobody.
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/machines")
async def machines(settings: Annotated[Settings, Depends(settings_dep)]) -> dict[str, Any]:
    try:
        async with asyncio.timeout(10):
            async with connect(settings.mcp_server_url, settings.key_for_role("viewer")) as client:
                payload = result_payload(await client.call_tool("list_machines", {}))
    except Exception as exc:
        log.warning("machine list unavailable: %r", exc)
        raise HTTPException(status_code=503, detail="MCP server unavailable") from exc
    if "error" in payload:
        raise HTTPException(status_code=502, detail=payload["error"])
    return payload


@app.get("/healthz")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health", response_model=None)
async def health(settings: Annotated[Settings, Depends(settings_dep)]) -> JSONResponse:
    """Readiness: the API is only useful when it can reach the MCP server."""
    mcp_status = "ok"
    try:
        async with asyncio.timeout(5):
            async with connect(settings.mcp_server_url, settings.key_for_role("viewer")) as client:
                await client.list_tools()
    except Exception:
        mcp_status = "unreachable"
    ok = mcp_status == "ok"
    return JSONResponse(
        {
            "status": "ok" if ok else "degraded",
            "mcp": mcp_status,
            "llm_provider": settings.resolved_provider,
        },
        status_code=200 if ok else 503,
    )
