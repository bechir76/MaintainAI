import os
import sys

import pytest
from mcp import Client, StdioServerParameters
from psycopg_pool import ConnectionPool

from core.mcp_client import result_payload

pytestmark = pytest.mark.integration


async def test_stdio_transport_uses_key_from_environment(
    ingested: ConnectionPool, database_url: str
) -> None:
    env = {
        **os.environ,
        "DATABASE_URL": database_url,
        "LLM_PROVIDER": "fake",
        "MCP_API_KEYS": "stdio-viewer:viewer",
        "MAINTAINAI_API_KEY": "stdio-viewer",
    }
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_server", "--transport", "stdio"], env=env
    )
    async with Client(params) as client:
        search = await client.call_tool(
            "search_manuals", {"query": "lockout tagout steps verify isolation"}
        )
        ticket = await client.call_tool(
            "create_maintenance_ticket",
            {
                "machine_id": "P-1",
                "title": "Test ticket",
                "description": "Should be refused for a viewer.",
                "priority": "low",
            },
        )
    assert not search.is_error
    assert result_payload(search)["results"][0]["doc_id"] == "SOP-LOTO-001"
    assert ticket.is_error
    assert "Permission denied" in result_payload(ticket)["error"]
