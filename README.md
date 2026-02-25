# PowerScale MCP Server

An MCP (Model Context Protocol) server for Dell PowerScale (Isilon) storage cluster automation. It exposes cluster management capabilities as MCP tools that any LLM client can use to query, configure, and manage one or more PowerScale clusters through natural language.

## Quick Start

### 1. Clone the Repository

```bash
git clone <repo-url>
cd isi_mcp_demo
```

### 2. Run Setup

```bash
./setup.sh
```

The script prompts for your cluster host, credentials, and a vault encryption password, then:
- Creates `vault.yml` with your cluster credentials
- Encrypts the vault using Ansible inside the Docker image (no Ansible needed on your host)
- The vault password is never stored on disk — provide it only at runtime via the `VAULT_PASSWORD` environment variable
- Builds the Docker image and starts the MCP server

**Non-interactive (for scripting):**

```bash
./setup.sh --host 192.168.0.33 --user root --pass secret --vault-pass vaultkey123
```

**Start in the foreground (for debugging):**

```bash
./setup.sh --host 192.168.0.33 --pass secret --vault-pass vaultkey123 --nodetach
```

By default, `setup.sh` starts the MCP server in the background. Use `--nodetach` to run in foreground instead.

The MCP server will be available at `http://localhost:8000`.

**Optionally set debug mode** by exporting `DEBUG=1` before running setup.

### Running the Server

After initial setup, you can start, stop, and restart the server as needed.

**Starting the server in the background:**

```bash
export VAULT_PASSWORD=$(read -s -p 'Enter your password: ' pwd && echo $pwd)
docker-compose up -d
```

**Starting the server in the foreground (for debugging):**

```bash
export VAULT_PASSWORD=$(read -s -p 'Enter your password: ' pwd && echo $pwd)
docker-compose up
```

Press `Ctrl+C` to stop.

**Viewing logs:**

```bash
docker-compose logs -f isi_mcp
```

**Restarting the server:**

```bash
export VAULT_PASSWORD=$(read -s -p 'Enter your password: ' pwd && echo $pwd)
docker-compose restart
```

**Stopping the server:**

```bash
docker-compose down
```

### Managing Credentials

Credentials are stored in an Ansible Vault encrypted file (`vault.yml`). The vault is excluded from git via `.gitignore`.

**Edit or add clusters after initial setup:**

First, view the encrypted vault to see the current structure:

```bash
echo -n 'your-vault-password' | docker-compose run --rm isi_mcp ansible-vault view /app/vault/vault.yml
```

Then edit it:

```bash
echo -n 'your-vault-password' | docker-compose run --rm isi_mcp ansible-vault edit /app/vault/vault.yml
```

After making changes, either restart the server:

```bash
VAULT_PASSWORD='your-vault-password' docker-compose restart
```

Or use the `powerscale_cluster_select` MCP tool with `reload_vault=true` to reload without restarting.

## Cluster Management

Cluster credentials are managed outside the LLM using the `ansible-vault` CLI. Runtime cluster switching is done via MCP tools.

### Adding a Cluster

Edit the vault and add a new entry under `clusters:`:

```bash
echo -n 'your-vault-password' | docker-compose run --rm isi_mcp ansible-vault edit /app/vault/vault.yml
```

Add a new cluster entry:

```yaml
clusters:
  prod:
    host: "https://192.168.0.33"
    port: 8080
    username: root
    password: secret
    verify_ssl: false
  dr:
    host: "https://10.0.1.50"
    port: 8080
    username: admin
    password: secret
    verify_ssl: true
```

Save and close. If the server is running, use the `powerscale_cluster_select` tool with `reload_vault=true` to pick up the changes.

### Removing a Cluster

Edit the vault and delete the cluster entry:

```bash
echo -n 'your-vault-password' | docker-compose run --rm isi_mcp ansible-vault edit /app/vault/vault.yml
```

Delete the cluster entry and save.

### Switching Clusters at Runtime

The LLM can manage clusters using four always-available management tools:

- `powerscale_cluster_list` — lists all configured clusters and shows which is currently selected
- `powerscale_cluster_select` — switches the active cluster by name; set `reload_vault=true` to pick up vault edits made while the server is running
- `powerscale_cluster_add` — add a new cluster to the vault at runtime
- `powerscale_cluster_remove` — remove a cluster from the vault at runtime

All other PowerScale tools automatically operate against the currently selected cluster.

### Changing the Vault Password

To rekey the vault (change its encryption password), use Docker to run the ansible-vault rekey command:

```bash
# Prompt for old password and new password (never stored on disk)
export OLD_VAULT_PASSWORD=$(read -s -p 'Enter current vault password: ' pwd && echo $pwd)
export NEW_VAULT_PASSWORD=$(read -s -p 'Enter new vault password: ' pwd && echo $pwd)
docker-compose run --rm -e VAULT_PASSWORD="$OLD_VAULT_PASSWORD" isi_mcp \
  ansible-vault rekey /app/vault/vault.yml --vault-password-file /dev/stdin <<< "$NEW_VAULT_PASSWORD"
unset OLD_VAULT_PASSWORD NEW_VAULT_PASSWORD
```

Then restart the server with the new vault password:

```bash
export VAULT_PASSWORD=$(read -s -p 'Enter your password: ' pwd && echo $pwd)
docker-compose restart
```

## Capabilities

The server provides 108 MCP tools organized into groups. All tool groups are enabled by default. The LLM can use `powerscale_tools_list` and `powerscale_tools_toggle` to disable groups and keep the tool list small for LLM context efficiency.

### Tool Groups

| Group | Tools | Description |
|-------|-------|-------------|
| **health** | 1 | Cluster health checks (quorum, service lights, critical events, network, capacity) |
| **capacity** | 2 | Storage capacity stats and cluster configuration |
| **quotas** | 6 | Quota management (get, set, increment, decrement, create, remove) |
| **snapshots** | 9 | Snapshot listing, schedule management, creation, deletion, aliases |
| **synciq** | 3 | SyncIQ replication policy management (get, create, remove) |
| **datamover** | 13 | DataMover policy, account, and base policy management |
| **filepool** | 6 | File pool policy management (get, create, update, remove) |
| **nfs** | 5 | NFS export management and global settings (service enable/disable, NFSv3/v4 version control) |
| **smb** | 10 | SMB share management, global settings (service, SMB2/SMB3, encryption, signing), and session/open-file tracking |
| **s3** | 3 | S3 bucket management (get, create, remove) |
| **filemgmt** | 22 | Namespace operations (directory/file CRUD, ACLs, metadata, WORM, access points) |
| **users** | 4 | Local user management (get, create, modify, remove) |
| **groups** | 4 | Local group management (get, create, modify, remove) |
| **events** | 2 | Event and alert browsing with filtering, sorting, and pagination |
| **statistics** | 9 | Live performance metrics (CPU, network, disk, IFS, protocol, client stats) |
| **utils** | 3 | Utilities (current time, bytes-to-human, human-to-bytes) |

### Always-Available Management Tools

These tools cannot be disabled:

- `powerscale_tools_list` / `powerscale_tools_toggle` — manage which tool groups are loaded
- `powerscale_cluster_list` / `powerscale_cluster_select` — view and switch target clusters
- `powerscale_cluster_add` / `powerscale_cluster_remove` — add new clusters to the vault or remove existing ones

### Example Questions

- "Is the cluster healthy?"
- "How much free space is on the cluster?"
- "Show me all SMB shares"
- "Create an NFS export for /ifs/data/projects with read-write access for 10.0.0.0/24"
- "Increase the quota on /ifs/home/jsmith by 50 GiB"
- "Disable the SMB service on the cluster"
- "Enable NFSv4.2 support"
- "Create a snapshot schedule for /ifs/data that runs daily at midnight"
- "List all files in /ifs/data/reports"
- "What SyncIQ replication policies are configured?"
- "Switch to the production cluster"

## Architecture

```
LLM Client (Claude, GPT, etc.)
    |
    | MCP Protocol (HTTP/SSE)
    v
FastMCP Server (server.py)
    |
    |--- VaultManager (modules/vault_manager.py)
    |       |--- Ansible Vault decryption & caching
    |       |--- Multi-cluster credential registry
    |       |--- Runtime cluster selection
    |
    |--- Domain Modules (modules/onefs/v9_12_0/)
    |       |--- Cluster (auth & API client, created from vault)
    |       |--- Health, Capacity, Quotas, Snapshots, ...
    |       |--- SMB, NFS, S3 (shares + global settings)
    |       |--- FileMgmt (namespace API)
    |       |--- DataMover, FilePool, SyncIQ, Config
    |
    |--- Ansible Automation (modules/ansible/)
    |       |--- AnsibleRunner (template rendering + execution)
    |       |--- Jinja2 Templates (Templates/*.yml.j2)
    |       |--- dellemc.powerscale Ansible collection
    |
    |--- Network Utilities (modules/network/)
            |--- ICMP ping checks
```

Read operations use the **isilon-sdk** Python SDK directly. Write/mutating operations use **Ansible playbooks** via the `dellemc.powerscale` collection for idempotent, auditable changes. Rendered playbooks are saved to `playbooks/` for audit trail.

## Connecting to LLM Clients

The server exposes a standard MCP HTTP+SSE endpoint at `http://localhost:8000`. Configuration varies by client.

### Claude Desktop

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

### Claude Code (CLI)

```bash
claude mcp add --transport http powerscale http://localhost:8000/mcp
claude --agent PowerscaleAgent --agents '{"PowerscaleAgent": {"description": "Interacts with the MCP server using detailed context", "prompt": "You are a knowledgeable assistant for managing a Powerscale Cluster.", "context": "CONTEXT.md"}}'
```

### Cursor

Open **Settings > MCP** and add a new server:

- **Name**: `powerscale`
- **Type**: `sse`
- **URL**: `http://localhost:8000/sse`

### Windsurf

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

### Continue.dev (VS Code / JetBrains)

Add to your Continue configuration (`~/.continue/config.yaml`):

```yaml
mcpServers:
  - name: powerscale
    url: http://localhost:8000/mcp
```

### Open WebUI

Navigate to **Workspace > Tools > Add MCP Server**:

- **URL**: `http://localhost:8000/sse`

### Generic MCP Client

Any MCP-compatible client can connect using the server's HTTP+SSE transport:

- **SSE endpoint**: `http://localhost:8000/sse`
- **MCP endpoint**: `http://localhost:8000/mcp`

## Dynamic Tool Management

Tools are organized into groups that can be enabled or disabled at runtime. This keeps the LLM's context window efficient — only the tools relevant to the current task are loaded.

The LLM automatically manages this using two always-available management tools:

- `powerscale_tools_list` — shows all groups and their enabled/disabled status
- `powerscale_tools_toggle` — enables or disables groups by name

Tool state is persisted in `tool_config.json` across server restarts.

## Security Notes

- Cluster credentials are stored in an Ansible Vault encrypted file — never in plaintext config files
- The encrypted vault (`vault.yml`) is excluded from git via `.gitignore`. The vault password is never stored on disk.
- All mutating operations include safety prompts in their tool descriptions, instructing the LLM to confirm with the user before executing
- Set `verify_ssl: false` only for clusters with self-signed certificates
- The MCP server itself does not implement authentication — secure it at the network level or behind a reverse proxy in production
