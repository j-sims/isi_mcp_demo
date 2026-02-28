# Features and Tools

## Feature Overview

The PowerScale MCP server provides comprehensive automation and management capabilities for PowerScale clusters:

- **Multi-cluster support** with runtime cluster switching
- **126 MCP tools** organized into 22 groups (118 domain + 8 management)
- **Read-only by default** — all 51 write tools are disabled at startup; enable as needed
- **Dynamic tool management** to keep LLM context efficient
- **Health checks** including quorum, service lights, critical events, network, and capacity
- **Node inventory** with per-node hardware, drive, sensor, and state details
- **License status** for all installed PowerScale feature licenses
- **Network topology** including groupnets, subnets, pools, interfaces, DNS, and access zones
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

| Group | Tools | Read | Write | Description |
|-------|-------|------|-------|-------------|
| Health | 1 | 1 | 0 | Cluster health checks (quorum, service lights, critical events, network, capacity) |
| Capacity | 2 | 2 | 0 | Storage statistics and configuration |
| Quotas | 6 | 1 | 5 | Quota CRUD and adjustment |
| Snapshots | 9 | 4 | 5 | Snapshots, schedules, and aliases |
| SyncIQ | 3 | 1 | 2 | Replication policies |
| DataMover | 13 | 7 | 6 | Data movement policies and accounts |
| FilePool | 6 | 3 | 3 | File pool policy management |
| NFS | 5 | 2 | 3 | NFS exports and global settings |
| SMB | 10 | 4 | 6 | SMB shares, settings, and sessions |
| S3 | 3 | 1 | 2 | S3 bucket management |
| FileMgmt | 22 | 9 | 13 | Directory/file/ACL/metadata operations |
| Users | 4 | 1 | 3 | Local user management |
| Groups | 4 | 1 | 3 | Local group management |
| Events | 2 | 2 | 0 | Event and alert browsing |
| Statistics | 9 | 9 | 0 | Performance metrics |
| Networking | 8 | 8 | 0 | Network topology (groupnets, subnets, pools, interfaces, DNS, zones, map) |
| ClusterNodes | 2 | 2 | 0 | Node inventory with hardware, drives, sensors, and state |
| StoragepoolNodetypes | 2 | 2 | 0 | Storage pool node type listings |
| Licensing | 2 | 2 | 0 | Feature license status and expiry |
| ZonesSummary | 2 | 2 | 0 | Lightweight access zone count and path summary |
| Utils | 3 | 3 | 0 | Utilities (time, unit conversion) |
| Management | 8 | 4 | 4 | Tool listing/toggling and cluster switching (always enabled) |

**Total: 126 tools across 22 groups (71 read + 51 write + 4 management-write)**

**Default state**: The server starts in read-only mode. All 51 write tools (across domain groups) are disabled at startup. Use `powerscale_tools_toggle` to enable write functionality as needed:

```
# Enable all write tools
powerscale_tools_toggle(names=["write"], action="enable")

# Enable a specific group
powerscale_tools_toggle(names=["quotas"], action="enable")

# Enable a single tool
powerscale_tools_toggle(names=["powerscale_quota_set"], action="enable")
```

Use `powerscale_tools_list`, `powerscale_tools_list_by_group`, and `powerscale_tools_list_by_mode` to inspect the current enabled/disabled state of all tools.

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

### Networking (8 tools)
Network topology inspection across the full groupnet hierarchy:
- **Groupnets**: list all groupnets with DNS server and search domain configuration
- **Subnets**: list subnets with gateway, prefix length, VLAN, and SmartConnect service details
- **Pools**: list IP address pools with ranges, SmartConnect DNS zones, and connection policies
- **Interfaces**: list physical and virtual network interfaces per node with link and MTU details
- **External settings**: global external network configuration including IPv6 and SmartConnect defaults
- **DNS cache**: DNS resolver cache configuration
- **Access zones**: list zones with groupnet association and authentication providers
- **Network map**: composite topology view assembling the full groupnets → subnets → pools → zones → SMB shares hierarchy in a single response

### ClusterNodes (2 tools)
Node inventory and status reporting:
- **List nodes**: all cluster nodes with Logical Node Number (LNN), node state, OneFS version, and peer connectivity status
- **Node detail**: full per-node inventory including hardware (product name, serial number, chassis), drive configuration and health per slot, disk partitions with usage, environmental sensors (temperature, voltage, fan RPM), NVRAM and battery status, and read-only/smartfail/service-light state flags

### StoragepoolNodetypes (2 tools)
Storage pool node type information:
- **List node types**: all node types with product name, associated node LNNs, SmartJob Manager capability, and manual assignment flag
- **Node type by ID**: retrieve details for a specific node type; use the list tool first to discover IDs

### Licensing (2 tools)
Feature license status and expiry tracking:
- **List licenses**: all installed PowerScale feature licenses including name, activation status (Evaluation / Activated / Expired / Unlicensed), expiration date, days to expiry, and alert flags for expiring or expired licenses
- **License by name**: retrieve status for a specific feature by name (e.g. SmartQuotas, SnapshotIQ, SyncIQ, SmartConnect_Advanced, DataMover, HDFS, CloudPools)

### ZonesSummary (2 tools)
Lightweight access zone summary:
- **Zones summary**: total zone count and list of zone base paths — a fast alternative to the full zones listing when only counts or paths are needed; supports optional groupnet filter
- **Zone by ID**: retrieve the base path for a specific zone ID without requiring elevated privileges

### Utils (3 tools)
Utility functions for working with the MCP server:
- Get current server time (useful for time-based operations)
- Convert byte values to human-readable IEC format (GiB, TiB, etc.)
- Convert human-readable sizes to byte values
