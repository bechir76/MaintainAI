# Connecting the MCP server to other agents

The MaintainAI MCP server exposes four tools to any MCP-compatible client:

| Tool | Role | Purpose |
|---|---|---|
| `search_manuals(query, machine_type?, top_k=5)` | viewer | Passages from manuals and safety procedures with document, page and score |
| `get_sensor_readings(machine_id, minutes=10)` | viewer | Recent readings plus anomaly flags against the CMS-001 alarm limits |
| `list_machines()` | viewer | All machines with current status |
| `create_maintenance_ticket(machine_id, title, description, priority)` | technician | Writes a ticket to Postgres |

Every call is authenticated with an API key, checked against the key's role, validated, and
written to the `audit_log` table.

## Streamable HTTP (recommended)

Start the stack (`make up`) or just the server (`make mcp`). The endpoint is
`http://localhost:8001/mcp`; pass the key in an `X-API-Key` header (or
`Authorization: Bearer <key>`). Requests without a valid key get `401` before any MCP
processing happens.

Most clients accept a JSON configuration like this:

```json
{
  "mcpServers": {
    "maintainai": {
      "type": "http",
      "url": "http://localhost:8001/mcp",
      "headers": { "X-API-Key": "technician-dev-key" }
    }
  }
}
```

The server runs in stateless mode with JSON responses, so it can be scaled horizontally
behind a load balancer without sticky sessions.

### Host header check

DNS rebinding protection is on: only the hosts listed in `MCP_ALLOWED_HOSTS` are accepted
(default `localhost:*,127.0.0.1:*,mcp-server:*,maintainai-mcp-server:*`). Add your own
host name if you expose the server under another name.

## stdio

Clients that launch servers as subprocesses can use the stdio transport. The API key comes
from the `MAINTAINAI_API_KEY` environment variable and is checked exactly like the HTTP header.

```json
{
  "mcpServers": {
    "maintainai": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/MaintainAI", "python", "-m", "mcp_server", "--transport", "stdio"],
      "env": {
        "DATABASE_URL": "postgresql://maintainai:maintainai@localhost:5432/maintainai",
        "MAINTAINAI_API_KEY": "viewer-dev-key"
      }
    }
  }
}
```

The database must be reachable and the manuals ingested (`make up` takes care of both).

## MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

Choose *Streamable HTTP*, enter `http://localhost:8001/mcp` and add the header
`X-API-Key: viewer-dev-key`. Try `create_maintenance_ticket` with the viewer key to see the
permission check, then look at the audit trail:

```bash
docker compose exec db psql -U maintainai -c "SELECT ts, principal, tool, status, detail FROM audit_log ORDER BY id DESC LIMIT 10"
```

## Python

```python
import asyncio
from core.mcp_client import connect, result_payload

async def main() -> None:
    async with connect("http://localhost:8001/mcp", "viewer-dev-key") as client:
        result = await client.call_tool("get_sensor_readings", {"machine_id": "P-3"})
        print(result_payload(result)["flags"])

asyncio.run(main())
```

## Keys and roles

Keys are configured with `MCP_API_KEYS` as comma-separated `key:role` pairs. Roles:

- `viewer`: `search_manuals`, `get_sensor_readings`, `list_machines`; documents with access
  level `viewer` only.
- `technician`: everything above, plus `create_maintenance_ticket` and restricted documents
  (for example the electrical test procedure M-ETP-05).

The development keys in `.env.example` are for local use only. In Kubernetes they come from a
Secret (see `deploy/helm`).
