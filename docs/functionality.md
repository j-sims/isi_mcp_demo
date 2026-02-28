# Capabilities and Functionality

The server provides comprehensive cluster management through 126 MCP tools organized into 22 groups. The server starts in **read-only mode** — all 51 write tools are disabled by default and must be explicitly enabled before the LLM can make changes to the cluster.

See **[Features & Tools](features.md)** for the complete list of tool groups and detailed tool descriptions.

## Dynamic Tool Management

Tools can be enabled or disabled at runtime using always-available management tools. Targets can be a mode (`"read"` / `"write"`), a group name (e.g. `"quotas"`), or an individual tool name:

- `powerscale_tools_list` — flat list of all tools with name, group, mode, and enabled status
- `powerscale_tools_list_by_group` — tools organized by functional area
- `powerscale_tools_list_by_mode` — tools split into read vs write with counts
- `powerscale_tools_toggle` — enables or disables tools by mode, group, or name

This keeps the LLM's context window efficient and ensures write capabilities are only active when intentionally enabled.

## Example Questions

The following examples demonstrate the types of tasks you can accomplish with the PowerScale MCP server.

**Read-only (available immediately after startup):**
- "Is the cluster healthy?"
- "How much free space is on the cluster?"
- "Show me all SMB shares"
- "List all files in /ifs/data/reports"
- "What SyncIQ replication policies are configured?"
- "Switch to the production cluster"
- "List all nodes in the cluster and show their hardware details"
- "Which licenses are installed and are any expiring soon?"
- "What is the network topology — groupnets, subnets, and pools?"
- "How many access zones are configured on this cluster?"

**Write operations (require enabling write tools first):**
- "Enable write tools for NFS, then create an NFS export for /ifs/data/projects with read-write access for 10.0.0.0/24"
- "Enable quota write tools, then increase the quota on /ifs/home/jsmith by 50 GiB"
- "Enable SMB write tools, then disable the SMB service on the cluster"
- "Enable snapshot write tools, then create a snapshot schedule for /ifs/data that runs daily at midnight"
