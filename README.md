# PowerScale MCP Server

Manage PowerScale storage clusters using natural language. Ask your LLM client:
- "Is the cluster healthy?"
- "Create an NFS export for /ifs/data/projects with read-write access for 10.0.0.0/24"
- "Increase the quota on /ifs/home/jsmith by 50 GiB"

The server translates plain English into cluster operations, eliminating manual Ansible scripting and API complexity.

**Why?** Storage cluster management spreads across CLIs, APIs, and spreadsheets. This MCP (Model Context Protocol) server abstracts that friction, letting you manage infrastructure through conversation while maintaining full audit trails for compliance.

**What's Included:** 212 tools across 41 functional groups—health checks, capacity analysis, quotas, snapshots, replication, file operations, NFS/SMB/S3 configuration, user management, performance metrics, and advanced analytics. All operations are audited through rendered Ansible playbooks. Credentials are encrypted and support multi-cluster management—seamlessly operate on any cluster via optional `cluster_name` parameter for parallel cross-cluster operations, or use runtime cluster switching for sequential operations. Two control modes: simple tool toggles or fine-grained Keycloak RBAC for production deployments.

## Example Usage

### Quick Checks
```
"Is the cluster healthy?"
"How much free space is on the cluster?"
"List all current snapshot schedules"
"Switch to the production cluster"
"Compare capacity usage across all clusters in parallel"
"Check health on prod, dr, and staging clusters simultaneously"
```

### Multi-Step Operational Tasks
```
"Create an /ifs/data/financial directory with ACLs for the Finance group,
set up SMB and NFS access, create a 5GB hard quota with 4GB soft quota,
schedule snapshots 4 times daily, and replicate to our DR cluster every 20 minutes"

"Set up home directories for 10 new contractors (contractor01-contractor10) with
individual SMB shares, 2GB quotas, daily snapshots, and add them all to the
contractors security group"

"Create a student lab environment: set up 10 student users with home dirs,
SMB shares, 2GB quotas, and daily snapshot schedules at noon"
```

### Reporting & Analysis
```
"Generate a CSV of quota usage with a chargeback analysis at $0.30/MiB
and save it as ChargeBack-$(date).csv"

"Create a custom HTML report named PowerscaleSummary-$(date).html with
cluster health, capacity, quota usage, and replication status, formatted
as a dark-themed dashboard with tabs for each cluster"

"Generate a PCI compliance report comparing our cluster configuration against
current standards and highlight any risks or misconfigurations"
```

### Interactive Guided Setup
```
"I need storage for a new application. Walk me through the setup process,
asking me questions about capacity, performance, redundancy, and access
requirements, then configure the storage appropriately"
```

### Administrative Cleanup
```
"Remove all lab users, groups, home directories, quotas, and snapshot
schedules we created during testing so we can start fresh"
```

## Documentation

- **[Installation & Setup](docs/install.md)** — Initial setup, running the server, and vault credential management
- **[Upgrading](docs/upgrading.md)** — Checking your version, comparing against the repo, and upgrading
- **[Cluster & Tool Management](docs/management.md)** — Managing multiple clusters, runtime cluster switching, and dynamic tool groups
- **[Features & Tools](docs/features.md)** — Complete feature list, tool groups, and detailed tool descriptions
- **[Capabilities & Functionality](docs/functionality.md)** — Available tool groups and example use cases
- **[Architecture](docs/architecture.md)** — System design, data flow, and component overview
- **[Client Integration](docs/clients.md)** — Connecting Claude Desktop, Claude Code, Cursor, and other LLM clients
- **[Security](docs/security.md)** — Credential management, SSL/TLS, and production best practices
- **[TLS Certificates](docs/tls.md)** — Auto-generated dev certs, bring-your-own CA-signed certs, rotation, and client trust
- **[Kubernetes Deployment](docs/kubernetes.md)** — Deploying on Kubernetes (k3s, minikube, EKS, etc.)

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

> **Client setup required**: MCP clients must trust the server's local CA certificate before connecting. See **[Client Integration](docs/clients.md)** for instructions.

See **[Installation & Setup](docs/install.md)** for detailed Docker deployment instructions.

See **[Features & Tools](docs/features.md)** for the complete feature list, tool groups, and detailed tool descriptions.

## System Requirements

- **Docker and Docker Compose** (standalone `docker-compose` tool, not the `docker compose` plugin)
- PowerScale cluster with OneFS v9.12.0 (only this version has been tested)
- LLM client supporting MCP protocol (Claude, Cursor, Windsurf, etc.)

## Support Matrix

| Component | Version | Status | Notes |
|-----------|---------|--------|-------|
| **PowerScale** | 9.12.0 | Tested | Only this OneFS version has been validated |
| **Python** | 3.12 | Required | Used in Docker image |
| **isilon-sdk** | >=0.7.0, <1.0.0 | Required | PowerScale API client library |
| **ansible-core** | >=2.16.0, <3.0.0 | Required | Ansible automation framework |
| **ansible-runner** | >=2.4.0, <3.0.0 | Required | Python-native Ansible playbook execution |
| **dellemc.powerscale** | Latest | Required | Dell PowerScale Ansible collection (auto-installed) |
| **fastmcp** | >=2.0.0, <3.0.0 | Required | MCP server framework |
| **uvicorn** | >=0.30.0, <1.0.0 | Required | ASGI server |
| **Docker** | 20.10+ | Recommended | For containerized deployment |
| **Docker Compose** | 1.29+ | Recommended | Standalone tool (not docker compose plugin) |
| **Kubernetes** | 1.20+ | Optional | For K8s deployment (k3s, minikube, EKS, etc.) |
| **Node.js** | 14+ | Optional | For MCP client (Claude Code, Claude Desktop) |

**Version Policy**: Patch versions (e.g., 0.7.0 → 0.7.1) are automatically compatible. Major/minor version changes may introduce breaking changes—test thoroughly before upgrading production deployments.

## Project Status

This is a proof-of-concept demonstration of MCP capabilities for PowerScale cluster automation. Use at your own risk in non-production environments. The project is actively maintained and suitable for testing, learning, and sandbox deployments. For production use, thoroughly validate all operations in a staging cluster first.

## Support

This project is community supported and provided on a best-effort basis. For issues, questions, or feature requests, please open an issue on [GitHub](https://github.com/dell/isi_mcp_demo/issues). Refer to the documentation above for additional guidance.
