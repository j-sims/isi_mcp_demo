# Architecture

## System Overview

```
LLM Client (Claude, GPT, etc.)
    |
    | HTTPS (TLS 1.2+)
    v
Nginx Reverse Proxy (nginx/nginx.conf)
    |--- TLS termination, rate limiting, security headers
    |--- Load balancing (round-robin across N instances)
    |
    | HTTP (internal network)
    v
FastMCP Server (server.py) — stateless HTTP mode
    |
    |--- VaultManager (modules/vault_manager.py)
    |       |--- Ansible Vault decryption & caching
    |       |--- Multi-cluster credential registry
    |       |--- Runtime cluster selection
    |
    |--- Domain Modules (modules/onefs/v9_12_0/)
    |       |--- Cluster (auth & API client, created from vault)
    |       |--- Health, Capacity, Quotas, Snapshots, Config
    |       |--- SMB, NFS, S3 (shares + global settings)
    |       |--- FileMgmt (namespace API)
    |       |--- DataMover, FilePool, SyncIQ
    |       |--- Users, Groups, Events, Statistics
    |       |--- Network (groupnets, subnets, pools, interfaces, DNS, zones)
    |       |--- ClusterNodes, StoragepoolNodetypes, License, ZonesSummary
    |
    |--- Ansible Automation (modules/ansible/)
    |       |--- AnsibleRunner (template rendering + execution)
    |       |--- Jinja2 Templates (Templates/*.yml.j2)
    |
    |--- Network Utilities (modules/network/)
            |--- ICMP ping checks
```

## Core Components

### MCP Server Layer
The server exposes MCP tools using the FastMCP framework. Each tool is decorated with `@mcp.tool()` and provides cluster operations. Tools handle user-facing operations and coordinate with domain modules.

### Domain Modules
Located in `modules/onefs/v9_12_0/`, these modules provide business logic for cluster operations:

- **Cluster**: Base class that manages API client configuration and authentication via the isilon-sdk
- **Health**: Comprehensive health checks (quorum, service lights, critical events, network connectivity, capacity)
- **Capacity**: Storage capacity statistics and configuration details
- **Quotas**: Quota lifecycle management
- **Snapshots**: Snapshot and snapshot schedule operations
- **SyncIQ**: Replication policy management
- **DataMover**: Policy, account, and base policy management
- **FilePool**: File pool policy management
- **SMB**: SMB share operations and global settings
- **NFS**: NFS export operations and global settings
- **S3**: S3 bucket operations
- **FileMgmt**: Namespace and file management (directories, files, ACLs, metadata, WORM, access points)
- **Users**: Local user management
- **Groups**: Local group management
- **Events**: Event and alert browsing
- **Statistics**: Performance metrics collection
- **Network**: Network topology — groupnets, subnets, pools, interfaces, external settings, DNS cache, access zones, and composite network map
- **ClusterNodes**: Node inventory with hardware, drives, partitions, sensors, and state (read-only via ClusterApi)
- **StoragepoolNodetypes**: Storage pool node type listings (read-only via StoragepoolApi)
- **License**: Feature license status and expiry for all installed OneFS licenses (read-only via LicenseApi)
- **ZonesSummary**: Lightweight access zone count and path summary (read-only via ZonesSummaryApi)

### Vault Management
The VaultManager singleton decrypts and caches cluster credentials from an Ansible Vault encrypted file. It supports multiple named clusters, with the first cluster becoming the default. Two MCP management tools allow runtime cluster switching.

### Ansible Automation
Write/mutating operations use Ansible playbooks via the `dellemc.powerscale` collection for idempotent, auditable changes. The workflow:
1. Domain module calls `AnsibleRunner` with template name and variables
2. `AnsibleRunner` renders a Jinja2 template with connection credentials and resource parameters
3. The rendered playbook is saved to `playbooks/` for audit trail
4. `ansible-runner` executes the playbook (Python-native, no subprocess)
5. Structured result is returned to the MCP tool

### Read vs Write Operations
- **Read operations** use the **isilon-sdk** Python SDK directly for efficient queries
- **Write/mutating operations** use **Ansible playbooks** for idempotent, auditable changes with full rollback capabilities

## Data Flow

1. LLM client connects to nginx at `https://host/mcp` (TLS)
2. Nginx terminates TLS, applies rate limiting, and proxies to backend
3. LLM invokes an MCP tool with parameters
4. Tool function in `server.py` is executed
5. Tool creates a `Cluster` instance from vault credentials
6. Tool calls domain module methods passing the cluster instance
7. Domain module uses either:
   - isilon-sdk API client for read operations, or
   - AnsibleRunner for mutating operations
8. Result is returned as JSON-serializable data
9. MCP server sends result back through nginx to LLM client

## Horizontal Scaling

The server runs in **stateless HTTP mode** (`stateless_http=True`), allowing multiple instances behind nginx without session affinity:

- **Tool state**: Each instance periodically re-reads `tools.json` from disk (5-second TTL cache). A toggle on one instance writes to the shared file; others pick it up within the TTL.
- **Cluster selection**: The selected cluster is persisted to `config/cluster_state.json` with the same TTL-based refresh pattern.
- **File locking**: Both `tools.json` and `cluster_state.json` use `fcntl.flock` to prevent concurrent write corruption.
- **Playbook audit trail**: Filenames include the container hostname to prevent collisions across instances.
- **Docker Compose**: Use `docker-compose up --scale isi_mcp=N` — all instances share the bind-mounted `config/` directory.
- **Kubernetes**: Use HPA or set `replicas: N` — instances share a PVC for config persistence.
