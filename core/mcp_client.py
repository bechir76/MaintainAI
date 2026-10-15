"""Helpers for talking to the MaintainAI MCP server over streamable HTTP."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.types import CallToolResult


@asynccontextmanager
async def connect(url: str, api_key: str, http_timeout: float = 30.0) -> AsyncIterator[Client]:
    http = create_mcp_http_client(
        headers={"X-API-Key": api_key},
        timeout=httpx2.Timeout(http_timeout, connect=10.0),
    )
    async with http, Client(streamable_http_client(url, http_client=http)) as client:
        yield client


def result_payload(result: CallToolResult) -> dict[str, Any]:
    """Structured content of a tool result, or {"error": text} for failed calls."""
    text = "\n".join(getattr(c, "text", "") for c in result.content)
    if result.is_error:
        return {"error": text or "tool call failed"}
    if isinstance(result.structured_content, dict):
        return result.structured_content
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}
    return parsed if isinstance(parsed, dict) else {"result": parsed}
