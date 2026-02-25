# Architecture

## System Overview

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

1. LLM client connects to MCP server via HTTP/SSE
2. LLM invokes an MCP tool with parameters
3. Tool function in `server.py` is executed
4. Tool creates a `Cluster` instance from vault credentials
5. Tool calls domain module methods passing the cluster instance
6. Domain module uses either:
   - isilon-sdk API client for read operations, or
   - AnsibleRunner for mutating operations
7. Result is returned as JSON-serializable data
8. MCP server sends result back to LLM client
