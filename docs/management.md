# Cluster and Tool Management

## Cluster Management

Cluster credentials are managed outside the LLM using the `ansible-vault` CLI. Runtime cluster switching is done via MCP tools.

### Adding a Cluster

Edit the vault and add a new entry under `clusters:`:

```bash
docker-compose run --rm isi_mcp ansible-vault edit /app/vault/vault.yml
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
docker-compose run --rm isi_mcp ansible-vault edit /app/vault/vault.yml
```

Delete the cluster entry and save.

### Switching Clusters at Runtime

The LLM can manage clusters using four always-available management tools:

- `powerscale_cluster_list` — lists all configured clusters and shows which is currently selected
- `powerscale_cluster_select` — switches the active cluster by name; set `reload_vault=true` to pick up vault edits made while the server is running
- `powerscale_cluster_add` — add a new cluster to the vault at runtime
- `powerscale_cluster_remove` — remove a cluster from the vault at runtime

All other PowerScale tools automatically operate against the currently selected cluster.

## Dynamic Tool Management

Each MCP tool has a **mode** (`read` or `write`) and an **enabled** flag. The server ships in read-only mode — all 51 write tools are disabled by default and must be explicitly enabled.

Tool state is persisted in `config/tools.json` across container restarts.

### Inspecting Tool State

Three always-available listing tools show the current state of all 126 tools:

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

# Disable write tools (return to read-only mode)
powerscale_tools_toggle(names=["write"], action="disable")
```

Changes persist to `config/tools.json` and survive container restarts.

### Always-Available Management Tools

These tools cannot be disabled and are always accessible to the LLM:

- `powerscale_tools_list` / `powerscale_tools_list_by_group` / `powerscale_tools_list_by_mode` — inspect tool state
- `powerscale_tools_toggle` — enable or disable tools by mode, group, or name
- `powerscale_cluster_list` / `powerscale_cluster_select` — view and switch target clusters
- `powerscale_cluster_add` / `powerscale_cluster_remove` — add or remove clusters from the vault
