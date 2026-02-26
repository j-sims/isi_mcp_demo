# Capabilities and Functionality

The server provides comprehensive cluster management through 124 MCP tools organized into 21 groups. All tool groups are enabled by default but can be dynamically disabled to optimize LLM context usage.

See **[Features & Tools](features.md)** for the complete list of tool groups and detailed tool descriptions.

## Dynamic Tool Management

All tool groups can be enabled or disabled at runtime using two always-available management tools:

- `powerscale_tools_list` — shows all groups and their enabled/disabled status
- `powerscale_tools_toggle` — enables or disables groups by name

This keeps the LLM's context window efficient by only loading tools relevant to the current task.

## Example Questions

The following examples demonstrate the types of tasks you can accomplish with the PowerScale MCP server:

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
- "List all nodes in the cluster and show their hardware details"
- "Which licenses are installed and are any expiring soon?"
- "What is the network topology — groupnets, subnets, and pools?"
- "How many access zones are configured on this cluster?"
