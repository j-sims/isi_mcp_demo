# Connecting to LLM Clients

The PowerScale MCP server exposes a standard MCP HTTP+SSE endpoint at `http://localhost:8000`. Configuration varies by client.

## Claude Desktop

Add to your Claude Desktop configuration file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "powerscale": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Claude Code (CLI)

```bash
claude mcp add --transport http powerscale http://localhost:8000/mcp
claude --agent PowerscaleAgent --agents '{"PowerscaleAgent": {"description": "Interacts with the MCP server using detailed context", "prompt": "You are a knowledgeable assistant for managing a Powerscale Cluster.", "context": "CONTEXT.md"}}'
```

## Cursor

Open **Settings > MCP** and add a new server:

- **Name**: `powerscale`
- **Type**: `sse`
- **URL**: `http://localhost:8000/sse`

## Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "powerscale": {
      "serverUrl": "http://localhost:8000/sse"
    }
  }
}
```

## Continue.dev (VS Code / JetBrains)

Add to your Continue configuration (`~/.continue/config.yaml`):

```yaml
mcpServers:
  - name: powerscale
    url: http://localhost:8000/mcp
```

## Open WebUI

Navigate to **Workspace > Tools > Add MCP Server**:

- **URL**: `http://localhost:8000/sse`

## Generic MCP Client

Any MCP-compatible client can connect using the server's HTTP+SSE transport:

- **SSE endpoint**: `http://localhost:8000/sse`
- **MCP endpoint**: `http://localhost:8000/mcp`
