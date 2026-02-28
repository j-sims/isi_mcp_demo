# Connecting to LLM Clients

The PowerScale MCP server is accessed via an nginx reverse proxy at `https://localhost`. The proxy provides TLS termination, rate limiting, and security headers. Configuration varies by client.

> **Note**: If using self-signed certificates (default for development), your MCP client must be configured to accept untrusted certificates.

## Claude Desktop

Add to your Claude Desktop configuration file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "powerscale": {
      "url": "https://localhost/mcp"
    }
  }
}
```

## Claude Code (CLI)

```bash
claude mcp add --transport http powerscale https://localhost/mcp
claude --agent PowerscaleAgent --agents '{"PowerscaleAgent": {"description": "Interacts with the MCP server using detailed context", "prompt": "You are a knowledgeable assistant for managing a Powerscale Cluster.", "context": "CONTEXT.md"}}'
```

## Cursor

Open **Settings > MCP** and add a new server:

- **Name**: `powerscale`
- **Type**: `sse`
- **URL**: `https://localhost/sse`

## Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "powerscale": {
      "serverUrl": "https://localhost/sse"
    }
  }
}
```

## Continue.dev (VS Code / JetBrains)

Add to your Continue configuration (`~/.continue/config.yaml`):

```yaml
mcpServers:
  - name: powerscale
    url: https://localhost/mcp
```

## Open WebUI

Navigate to **Workspace > Tools > Add MCP Server**:

- **URL**: `https://localhost/sse`

## Generic MCP Client

Any MCP-compatible client can connect using the server's HTTP+SSE transport:

- **SSE endpoint**: `https://localhost/sse`
- **MCP endpoint**: `https://localhost/mcp`
