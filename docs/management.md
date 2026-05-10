# Cluster and Tool Management

## Cluster Management

Cluster credentials are managed via `setup.sh` subcommands or directly through MCP tools. Runtime cluster switching is done via MCP tools.

### Adding a Cluster

Use the `setup.sh add-cluster` subcommand — it handles TLS certificate extraction automatically and never exposes credentials to the shell history:

```bash
# Interactive (prompts for name, host, user, and password)
./setup.sh add-cluster

# Non-interactive
./setup.sh add-cluster --name dr --host 10.0.1.50 --user admin
```

The running server reloads the vault within 5 seconds — no restart needed.

Alternatively, use the `powerscale_cluster_add` MCP tool to add a cluster directly from an LLM session.

### Removing a Cluster

```bash
./setup.sh remove-cluster --name dr
```

The script prompts for confirmation before making any changes. The running server reloads the vault within 5 seconds.

Alternatively, use the `powerscale_cluster_remove` MCP tool from an LLM session.

### Modifying a Cluster

To update individual fields of an existing cluster without replacing the entire entry:

```bash
./setup.sh modify-cluster --name dr --host 10.0.1.51     # update host
./setup.sh modify-cluster --name dr --pass                # update password (prompted)
./setup.sh modify-cluster --name dr --new-name dr2        # rename
./setup.sh modify-cluster --name dr --verify-ssl false    # change SSL setting
```

Alternatively, use the `powerscale_cluster_modify` MCP tool from an LLM session.

### Listing Clusters

```bash
./setup.sh list-clusters
```

### Cluster Operations

#### Sequential Cluster Switching (Session-Based)

Use management tools to switch your active cluster and operate sequentially:

- `powerscale_cluster_list` — lists all configured clusters and shows which is currently selected
- `powerscale_cluster_setdefault` — switches the active cluster by name; set `reload_vault=true` to pick up vault edits made while the server is running
- `powerscale_cluster_add` — add a new cluster to the vault at runtime (also handles TLS cert extraction)
- `powerscale_cluster_remove` — remove a cluster from the vault at runtime
- `powerscale_cluster_modify` — update one or more fields of an existing cluster (name, host, port, username, password, verify_ssl) without replacing the entire entry; only supply the fields you want to change

#### Parallel Cross-Cluster Operations

All PowerScale tools accept an optional `cluster_name` parameter. This allows you to:
- **Operate on any cluster without changing session context** — run multiple operations across different clusters in a single request
- **Execute parallel cluster commands** — query health, capacity, quotas across all clusters simultaneously without sequential switching

Examples:
```
# Get capacity from prod and dr clusters in parallel
powerscale_capacity(cluster_name="prod")
powerscale_capacity(cluster_name="dr")

# Check health on multiple clusters at once
powerscale_cluster_verify(cluster_name="staging")
powerscale_cluster_verify(cluster_name="prod")

# Mix default cluster with explicit cluster_name calls
powerscale_quota_get()  # Uses currently selected cluster
powerscale_quota_get(cluster_name="prod")  # Explicitly targets prod
```

This approach is ideal for:
- **Comparative analysis** — compare metrics across clusters (capacity, quotas, performance)
- **Parallel verification** — health checks on multiple clusters simultaneously
- **Multi-cluster operations** — replicate configurations or sync data across clusters

## Dynamic Tool Management

Each MCP tool has a **mode** (`read` or `write`) and an **enabled** flag. All 213 tools ship enabled by default. Tool access can be controlled in two ways:

- **Without auth** (`AUTH_ENABLED=false`): Use `powerscale_tools_toggle` and `config/tools.json` to enable/disable tools by group, mode, or name. This is the primary access control mechanism for single-user or trusted-network deployments.
- **With auth** (`AUTH_ENABLED=true`): Keycloak RBAC provides per-user access control via mode roles and group roles. The tool toggle mechanism still works alongside RBAC — it controls which tools are registered, while RBAC controls which registered tools each user can see.

Tool state is persisted in `config/tools.json` across container restarts.

**Important**: The 5 management write tools (`powerscale_tools_toggle`, `powerscale_cluster_setdefault`, `powerscale_cluster_add`, `powerscale_cluster_remove`, `powerscale_cluster_modify`) cannot be disabled and are always available, regardless of their `enabled` flag in `config/tools.json`.

### Inspecting Tool State

Three always-available listing tools show the current state of all 213 tools:

- `powerscale_tools_list` — flat alphabetical list with name, group, mode, and enabled status for every tool
- `powerscale_tools_list_by_group` — tools grouped by functional area
- `powerscale_tools_list_by_mode` — tools split into read vs write, with counts

### Enabling Write Tools

Use `powerscale_tools_toggle` to enable or disable tools at runtime. The `names` parameter accepts:

- A **mode** string: `"read"` or `"write"` — toggles all tools of that mode
- A **group** name: e.g. `"quotas"`, `"filemgmt"`, `"smb"` — toggles all tools in that group
- An **individual tool** name: e.g. `"powerscale_quota_set"` — toggles a single tool

```
# Enable all write tools at once
powerscale_tools_toggle(names=["write"], action="enable")

# Enable only quota write tools
powerscale_tools_toggle(names=["quotas"], action="enable")

# Enable a single tool
powerscale_tools_toggle(names=["powerscale_quota_set"], action="enable")

# Disable write tools (restrict to read-only)
powerscale_tools_toggle(names=["write"], action="disable")
```

Changes persist to `config/tools.json` and survive container restarts.

### Always-Available Management Tools

These tools cannot be disabled and are always accessible to the LLM:

- `powerscale_tools_list` / `powerscale_tools_list_by_group` / `powerscale_tools_list_by_mode` — inspect tool state
- `powerscale_tools_toggle` — enable or disable tools by mode, group, or name
- `powerscale_cluster_list` / `powerscale_cluster_setdefault` — view and switch target clusters
- `powerscale_cluster_add` / `powerscale_cluster_remove` / `powerscale_cluster_modify` — add, remove, or update clusters in the vault
