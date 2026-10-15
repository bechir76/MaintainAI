# MaintainAI

Maintenance assistant for industrial equipment (pumps, motors, compressors).

Work in progress.

## Sample data

The documents in `data/manuals` are sample documents written for this demo. The equipment
(P-Series pumps, M-Series motors, C-Series compressors), the figures and the procedures are
realistic but fictional and must not be used to maintain real machines. They are generated from
Markdown sources in `data/manuals/src` with `make manuals`.

## Connecting the MCP server to another agent

The tools are served over MCP (streamable HTTP at `http://localhost:8001/mcp`, or stdio), so any
MCP-compatible client can use them. Pass an API key in the `X-API-Key` header:

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

See [docs/mcp-clients.md](docs/mcp-clients.md) for stdio, MCP Inspector and Python examples.
