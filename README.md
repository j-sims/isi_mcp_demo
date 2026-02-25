# PowerScale MCP Server

An MCP (Model Context Protocol) server for Dell PowerScale (Isilon) storage cluster automation. It exposes cluster management capabilities as MCP tools that any LLM client can use to query, configure, and manage one or more PowerScale clusters through natural language.

The server provides 106 tools across 16 groups, including cluster health checks, capacity analysis, quota management, snapshots, replication, file operations, SMB/NFS/S3 configuration, user and group management, events, and live performance metrics. All operations are audited through rendered Ansible playbooks saved for compliance tracking. Credentials are stored in an encrypted Ansible Vault with support for multiple clusters and runtime switching.

## Documentation

- **[Installation & Setup](docs/install.md)** — Initial setup, running the server, and vault credential management
- **[Cluster & Tool Management](docs/management.md)** — Managing multiple clusters, runtime cluster switching, and dynamic tool groups
- **[Features & Tools](docs/features.md)** — Complete feature list, tool groups, and detailed tool descriptions
- **[Capabilities & Functionality](docs/functionality.md)** — Available tool groups and example use cases
- **[Architecture](docs/architecture.md)** — System design, data flow, and component overview
- **[Client Integration](docs/clients.md)** — Connecting Claude Desktop, Claude Code, Cursor, and other LLM clients
- **[Security](docs/security.md)** — Credential management, SSL/TLS, and production best practices

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd isi_mcp_demo
./setup.sh

# Start the server
export VAULT_PASSWORD=$(read -s -p 'Enter vault password: ' pwd && echo $pwd)
docker-compose up -d

# Server is now available at http://localhost:8000
```

See **[Installation & Setup](docs/install.md)** for detailed instructions.

See **[Features & Tools](docs/features.md)** for the complete feature list, tool groups, and detailed tool descriptions.

## Example Usage

The LLM can accomplish tasks like:

```
"Is the cluster healthy?"
"How much free space is on the cluster?"
"Create an NFS export for /ifs/data/projects with read-write access for 10.0.0.0/24"
"Increase the quota on /ifs/home/jsmith by 50 GiB"
"Create a snapshot schedule for /ifs/data that runs daily at midnight"
"List all files in /ifs/data/reports"
"Switch to the production cluster"
```

## System Requirements

- Docker and Docker Compose
- PowerScale cluster with OneFS v9.12.0 (only this version has been tested)
- LLM client supporting MCP protocol (Claude, Cursor, Windsurf, etc.)

## Support

This project is community supported and provided on a best-effort basis. For issues, questions, or feature requests, please open an issue on [GitHub](https://github.com/dell/isi_mcp_demo/issues). Refer to the documentation above for additional guidance.
