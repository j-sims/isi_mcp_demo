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

Tools are organized into groups that can be enabled or disabled at runtime. This keeps the LLM's context window efficient — only the tools relevant to the current task are loaded.

The LLM automatically manages this using two always-available management tools:

- `powerscale_tools_list` — shows all groups and their enabled/disabled status
- `powerscale_tools_toggle` — enables or disables groups by name

Tool state is persisted in `tool_config.json` across server restarts.

### Always-Available Management Tools

These tools cannot be disabled and are always accessible to the LLM:

- `powerscale_tools_list` / `powerscale_tools_toggle` — manage which tool groups are loaded
- `powerscale_cluster_list` / `powerscale_cluster_select` — view and switch target clusters
- `powerscale_cluster_add` / `powerscale_cluster_remove` — add new clusters to the vault or remove existing ones
