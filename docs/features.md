# Features and Tools

## Feature Overview

The PowerScale MCP server provides comprehensive automation and management capabilities for PowerScale clusters:

- **Multi-cluster support** with runtime cluster switching
- **108 MCP tools** organized into 16 manageable tool groups
- **Dynamic tool management** to keep LLM context efficient
- **Health checks** including quorum, service lights, critical events, network, and capacity
- **Quota management** with support for directory, user, and group quotas
- **Snapshot & replication** including SyncIQ policies and DataMover operations
- **File operations** including directory/file CRUD, ACLs, metadata, and WORM/SmartLock
- **SMB & NFS** share and export management with global settings control
- **S3 buckets** for object storage
- **User & group** management for local authentication
- **Events & alerts** with filtering, sorting, and pagination
- **Live performance metrics** including CPU, network, disk, IFS, protocol, and client stats
- **Audited operations** through rendered Ansible playbooks
- **Encrypted credentials** in Ansible Vault format

## Tool Groups

| Group | Count | Description |
|-------|-------|-------------|
| Health | 1 | Cluster health checks (quorum, service lights, critical events, network, capacity) |
| Capacity | 2 | Storage statistics and configuration |
| Quotas | 6 | Quota CRUD and adjustment |
| Snapshots | 9 | Snapshots, schedules, and aliases |
| SyncIQ | 3 | Replication policies |
| DataMover | 13 | Data movement policies and accounts |
| FilePool | 6 | File pool policy management |
| NFS | 5 | NFS exports and global settings |
| SMB | 10 | SMB shares, settings, and sessions |
| S3 | 3 | S3 bucket management |
| FileMgmt | 22 | Directory/file/ACL/metadata operations |
| Users | 4 | Local user management |
| Groups | 4 | Local group management |
| Events | 2 | Event and alert browsing |
| Statistics | 9 | Performance metrics |
| Utils | 3 | Utilities (time, unit conversion) |

**Total: 106 tools across 16 groups**

All tool groups are enabled by default but can be dynamically disabled to keep the LLM's context window efficient. Use `powerscale_tools_list` and `powerscale_tools_toggle` to manage which groups are active.

## Detailed Tool Descriptions

### Health (1 tool)
Comprehensive cluster health monitoring with a single command that checks quorum status, service lights, critical events, network connectivity, and available capacity.

### Capacity (2 tools)
Query cluster capacity metrics and configuration including total/used/available storage, deduplication ratios, compression ratios, and cluster hardware details.

### Quotas (6 tools)
Full quota lifecycle management:
- Query existing quotas with pagination
- Set hard quota limits
- Increment or decrement quotas
- Create new quotas with retention policies
- Remove quotas

Supports directory, user, and group quotas with hard, soft, and advisory enforcement modes.

### Snapshots (9 tools)
Snapshot and schedule management:
- List snapshots with filtering
- Create manual snapshots
- Delete snapshots
- List snapshot schedules
- Create scheduled snapshots (daily, weekly, monthly, hourly)
- Remove snapshot schedules
- Create and retrieve snapshot aliases for easy reference
- List pending snapshots

### SyncIQ (3 tools)
Replication policy management:
- List all SyncIQ replication policies
- Create new replication policies between clusters
- Remove replication policies

### DataMover (13 tools)
Data movement policies with support for policies, accounts, and base policy templates:
- List and retrieve policies with detailed configuration
- Create, modify, and delete policies
- List and retrieve storage accounts
- Create and delete accounts
- List and retrieve base policy templates
- Create and delete base policies
- Retrieve job history for policies

### FilePool (6 tools)
File pool policy management for automated data tiering:
- List all FilePool policies
- Retrieve specific policies by name
- Retrieve default policy
- Create new tiering policies with file matching rules
- Update existing policies
- Delete policies

### NFS (5 tools)
NFS export and global settings management:
- List NFS exports
- Create NFS exports with fine-grained access control (read-only, read-write, root clients)
- Remove NFS exports
- Get and set global NFS settings (service enable/disable, NFSv3/v4.x version control, thread tuning)

### SMB (10 tools)
SMB/CIFS share and session management:
- List SMB shares
- Create SMB shares with advanced options (encryption, signing, ACL support)
- Remove SMB shares
- Get and set global SMB settings
- List active SMB sessions
- Close specific SMB sessions
- Close sessions by user and computer
- List open files
- Close open file handles

### S3 (3 tools)
S3-compatible object storage bucket management:
- List S3 buckets
- Create buckets mapped to filesystem paths
- Remove buckets

### FileMgmt (22 tools)
Comprehensive namespace and file management:
- **Directory operations**: list, create, delete, move, copy, get attributes
- **File operations**: read, create, delete, move, copy, get attributes
- **ACL management**: get and set access control lists
- **Metadata**: get and set custom metadata attributes
- **WORM/SmartLock**: get and set retention properties
- **Access points**: list, create, and delete namespace access points
- **Directory queries**: advanced search with attribute filtering

### Users (4 tools)
Local user account management:
- List users with filtering by provider and access zone
- Retrieve specific users by name
- Create new local users with full attribute configuration
- Modify user properties (password, group membership, email, home directory, shell)
- Delete local user accounts

### Groups (4 tools)
Local group management:
- List groups with filtering by provider and access zone
- Retrieve specific groups by name or GID
- Create new local groups with initial member assignment
- Add and remove group members
- Delete local groups

### Events (2 tools)
Event and alert browsing with powerful filtering:
- List event group occurrences with filtering by severity, date range, resolved status, and cause
- Retrieve detailed information about specific events
- Support for pagination and sorting

### Statistics (9 tools)
Real-time performance metrics collection:
- **CPU metrics**: system, user, idle, interrupt utilization
- **Network metrics**: inbound/outbound bytes and packets, error rates
- **Disk I/O**: read/write throughput and IOPS
- **IFS metrics**: filesystem-level read/write rates
- **Per-node metrics**: CPU throttling, load averages, memory usage, open files
- **Protocol stats**: operation rates by protocol (NFS, SMB, HTTP/S3, etc.)
- **Client stats**: active and connected client counts by protocol
- **Custom queries**: retrieve any statistic by key name
- **Key discovery**: browse available statistics with metadata

All metrics are averaged over 30 seconds to smooth out spikes and provide reliable baselines.

### Utils (3 tools)
Utility functions for working with the MCP server:
- Get current server time (useful for time-based operations)
- Convert byte values to human-readable IEC format (GiB, TiB, etc.)
- Convert human-readable sizes to byte values
