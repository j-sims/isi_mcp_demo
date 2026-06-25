# Connecting to LLM Clients

## Server URL

The URL to use depends on whether SSL is enabled in `config/isi_mcp.env`:

| Mode | Default port | Client URL |
|---|---|---|
| `SSL=false` (default) | 80 | `http://localhost/mcp` |
| `SSL=true` | 443 | `https://localhost/mcp` |

When `SSL=false`, connect directly to the MCP server over HTTP — no nginx, no certificates, no trust setup. This is the default mode and requires no additional steps beyond running `./setup.sh`.

When `SSL=true`, traffic flows through an nginx reverse proxy with TLS. Clients must trust the CA certificate before they can connect (see below).

---

## SSL=false (Default) — No Certificate Setup Needed

Connect your client using `http://localhost/mcp` (or `http://<server-ip>/mcp` if accessing remotely). Skip the certificate trust section below.

## SSL=true — Trusting the Server Certificate

When SSL is enabled, the server uses a local CA to sign its TLS certificate. MCP clients will refuse to connect until the CA certificate is trusted on the client machine. This is a one-time setup step.

`setup.sh --ssl true` (or `nginx/generate-certs.sh`) creates two files in `nginx/certs/`:
- `ca.crt` — the local CA certificate (what clients must trust)
- `server.crt` — the server certificate signed by that CA (used by nginx only)

**Step 1: Copy the CA certificate from the server host**

```bash
scp user@mcp-server:/path/to/isi_mcp_demo/nginx/certs/ca.crt ~/.certs/powerscale-mcp-ca.crt
```

If running locally, the CA certificate is at `nginx/certs/ca.crt` in the project directory.

**Step 2: Trust the CA certificate — choose one option**

**Option A — Per-session environment variable (Claude Code / Node.js clients):**

```bash
export NODE_EXTRA_CA_CERTS=~/.certs/powerscale-mcp-ca.crt
```

Add this to your shell profile (`~/.bashrc`, `~/.profile`, etc.) and relaunch VSCode/Claude Code from that shell to make it permanent.

> **Important**: `NODE_EXTRA_CA_CERTS` must point to `ca.crt` (the CA), not `server.crt`. Node.js rejects server certificates that are self-signed at depth zero, even if explicitly trusted.

**Option B — System-wide trust (Linux):**

```bash
sudo cp ~/.certs/powerscale-mcp-ca.crt /usr/local/share/ca-certificates/powerscale-mcp-ca.crt
sudo update-ca-certificates
```

**Option B — System-wide trust (macOS):**

```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ~/.certs/powerscale-mcp-ca.crt
```

> **Production**: Replace the self-signed CA with certificates from a trusted CA (e.g., your company CA or a public CA) and clients will trust it automatically — no manual steps required.

> **Port conflict**: If running k3s or other services that bind port 443 via iptables (e.g., Traefik), they will intercept connections before nginx receives them. Stop those services before starting this stack, or change the nginx port mapping in `docker-compose.yml`.

---

## Claude Desktop

Add to your Claude Desktop configuration file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "powerscale": {
      "url": "http://localhost/mcp"
    }
  }
}
```

Replace `http://localhost/mcp` with `https://localhost/mcp` if `SSL=true`.

## Claude Code (CLI)

```bash
# HTTP (default)
claude mcp add --transport http powerscale http://localhost/mcp

# HTTPS (SSL=true)
claude mcp add --transport http powerscale https://localhost/mcp
```

## Cursor

Open **Settings > MCP** and add a new server:

- **Name**: `powerscale`
- **Type**: `sse`
- **URL**: `http://localhost/sse` (or `https://localhost/sse` if SSL=true)

## Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "powerscale": {
      "serverUrl": "http://localhost/sse"
    }
  }
}
```

Replace `http://localhost/sse` with `https://localhost/sse` if `SSL=true`.

## Continue.dev (VS Code / JetBrains)

Add to your Continue configuration (`~/.continue/config.yaml`):

```yaml
mcpServers:
  - name: powerscale
    url: http://localhost/mcp
```

Replace `http://localhost/mcp` with `https://localhost/mcp` if `SSL=true`.

## Open WebUI

Navigate to **Workspace > Tools > Add MCP Server**:

- **URL**: `http://localhost/sse` (or `https://localhost/sse` if SSL=true)

## Generic MCP Client

Any MCP-compatible client can connect using the server's HTTP+SSE transport:

| Mode | MCP endpoint | SSE endpoint |
|---|---|---|
| `SSL=false` (default) | `http://localhost/mcp` | `http://localhost/sse` |
| `SSL=true` | `https://localhost/mcp` | `https://localhost/sse` |
