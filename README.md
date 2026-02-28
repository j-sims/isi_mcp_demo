# PowerScale MCP Server

An MCP (Model Context Protocol) server for Dell PowerScale (Isilon) storage cluster automation. It exposes cluster management capabilities as MCP tools that any LLM client can use to query, configure, and manage one or more PowerScale clusters through natural language.

The server provides 126 tools across 22 groups, including cluster health checks, capacity analysis, node inventory, license status, quota management, snapshots, replication, file operations, SMB/NFS/S3 configuration, user and group management, events, live performance metrics, and network topology. All operations are audited through rendered Ansible playbooks saved for compliance tracking. Credentials are stored in an encrypted Ansible Vault with support for multiple clusters and runtime switching.

The server ships in **read-only mode by default** — all write tools are disabled at startup and must be explicitly enabled using the `powerscale_tools_toggle` management tool. This safe-by-default posture prevents accidental modifications.

## Documentation

- **[Installation & Setup](docs/install.md)** — Initial setup, running the server, and vault credential management
- **[Cluster & Tool Management](docs/management.md)** — Managing multiple clusters, runtime cluster switching, and dynamic tool groups
- **[Features & Tools](docs/features.md)** — Complete feature list, tool groups, and detailed tool descriptions
- **[Capabilities & Functionality](docs/functionality.md)** — Available tool groups and example use cases
- **[Architecture](docs/architecture.md)** — System design, data flow, and component overview
- **[Client Integration](docs/clients.md)** — Connecting Claude Desktop, Claude Code, Cursor, and other LLM clients
- **[Security](docs/security.md)** — Credential management, SSL/TLS, and production best practices
- **[Kubernetes Deployment](docs/kubernetes.md)** — Deploying on Kubernetes with minikube or production clusters

## Quick Start

**For Kubernetes deployment**, see **[Kubernetes Deployment](docs/kubernetes.md)** instead.

**For Docker/Docker Compose deployment:**

```bash
# Clone and setup
git clone <repo-url>
cd isi_mcp_demo
./setup.sh

# Start the server (generates TLS certs, builds image, starts nginx + MCP server)
export VAULT_PASSWORD=$(read -s -p 'Enter vault password: ' pwd && echo $pwd)
docker-compose up -d

# Server is now available at https://localhost/mcp (via nginx reverse proxy)
```

See **[Installation & Setup](docs/install.md)** for detailed Docker deployment instructions.

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

- **Docker and Docker Compose** (standalone `docker-compose` tool, not the `docker compose` plugin)
- PowerScale cluster with OneFS v9.12.0 (only this version has been tested)
- LLM client supporting MCP protocol (Claude, Cursor, Windsurf, etc.)

## Support

This project is community supported and provided on a best-effort basis. For issues, questions, or feature requests, please open an issue on [GitHub](https://github.com/dell/isi_mcp_demo/issues). Refer to the documentation above for additional guidance.
