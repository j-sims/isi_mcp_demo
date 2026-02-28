# Connecting to LLM Clients

The PowerScale MCP server is accessed via an nginx reverse proxy at `https://localhost`. The proxy provides TLS termination, rate limiting, and security headers. Configuration varies by client.

## Trusting the Server Certificate

The server uses a self-signed TLS certificate by default. MCP clients will refuse to connect until the certificate is trusted on the client machine. This is a one-time setup step.

**Step 1: Copy the certificate from the server host**

```bash
scp user@mcp-server:/path/to/isi_mcp_demo/nginx/certs/server.crt ~/.certs/mcp-server.crt
```

The certificate lives at `nginx/certs/server.crt` in the project directory on the server host (it is generated on the host by `setup.sh`, not inside the container).

**Step 2: Trust the certificate — choose one option**

**Option A — Per-session environment variable (Claude Code / Node.js clients):**

```bash
export NODE_EXTRA_CA_CERTS=~/.certs/mcp-server.crt
```

Add this to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) to make it permanent.

**Option B — System-wide trust (Linux):**

```bash
sudo cp ~/.certs/mcp-server.crt /usr/local/share/ca-certificates/mcp-server.crt
sudo update-ca-certificates
```

**Option B — System-wide trust (macOS):**

```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ~/.certs/mcp-server.crt
```

> **Production**: Replace the self-signed certificate with one signed by a trusted CA (e.g., Let's Encrypt or your company CA) and clients will trust it automatically — no manual steps required.

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
