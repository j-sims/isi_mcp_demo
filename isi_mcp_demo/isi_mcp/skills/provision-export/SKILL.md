---
description: Create a fully provisioned NFS export with quotas and snapshot schedules
version: "1.0.0"
tags: [provisioning, nfs, quotas, snapshots, export-management]
---

# Provision an Export Skill

This skill guides the process of provisioning a complete **NFS export** on PowerScale, including quotas and snapshot scheduling. A provisioned export includes network access, capacity limits, and backup schedules.

## Important: NFS Exports Only

**When a user asks to "provision an export" or "create an NFS export", this always means an NFS (Network File System) export.**

- **NFS exports** are created using this skill
- **SMB shares** use a separate skill (Provision a Share)

If a user specifically asks for an SMB share or CIFS access, direct them to the provision share skill instead.

## What is Export Provisioning?

Provisioning an NFS export means setting up a complete, production-ready NFS export with:
- **Storage path** — The actual directory on the cluster
- **Export configuration** — NFS protocol access for Unix/Linux/Mac clients
- **Hard quota** — Maximum capacity before writes are rejected
- **Soft quota** — Warning threshold (recommended 80-90% of hard quota)
- **Snapshot schedule** — Automated point-in-time backups for recovery

## Provision an Export Workflow

When a user asks to **"provision an export"** or **"create an NFS export"**, follow these steps in order:

### Default Assumptions

This skill **always provisions NFS exports**. If the user does not explicitly specify:
- **Filesystem path** — Assume `/ifs/data/{export_name}` (where `{export_name}` is the export name provided)
- **Cluster** — Use the default cluster (no cluster_name parameter needed)
- **Snapshot interval** — Use daily (24-hour snapshots, keep 7 days) if not specified
- **Soft limit** — Calculate as 80% of hard limit if not provided

These defaults enable users to provision an NFS export with minimal input while still getting a production-ready setup.

**If a user asks for an SMB share**, that is a different operation and uses the "Provision a Share" skill instead.

### Step 1: Create the NFS Export

Call `powerscale_nfs_add()` to export the directory via NFS protocol.

**Parameters:**
- `export_name` — Name/identifier for the NFS export (e.g., "data", "home", "backups")
- `path` — Full path on cluster (typically `/ifs/data/{export_name}`)
- Optional: `description`, `comment` — User-facing labels

**Example:**
```
powerscale_nfs_add(
  export_name="data",
  path="/ifs/data/data",
  description="NFS export for data team"
)
```

**Verify:**
- NFS export is created and accessible via `nfs://<cluster-ip>/{export_name}` or `<cluster-ip>:/ifs/data/{export_name}`
- Unix/Linux clients can mount the export: `mount <cluster-ip>:/ifs/data/data /mnt/data`

### Step 2: Set Hard Quota

Call `powerscale_quota_set()` to enforce a maximum storage limit.

**Parameters:**
- `path` — Same path as the export (e.g., `/ifs/data/data`)
- `hard_limit` — Maximum bytes allowed (writes fail when exceeded)
- `hard_limit_size` — Human-readable format (e.g., "1 TiB", "500 GiB")

**Example:**
```
powerscale_quota_set(
  path="/ifs/data/data",
  hard_limit_size="2 TiB"
)
```

**Verify:**
- Hard quota is applied: `powerscale_quota_get(path="/ifs/data/data")`
- Hard limit shows in bytes (converted from TiB)

### Step 3: Set Soft Quota

Call `powerscale_quota_set()` again to set a soft (warning) limit.

**Parameters:**
- `path` — Same path as the export
- `soft_limit` — Warning threshold in bytes (typically 80-90% of hard quota)
- `soft_limit_size` — Human-readable format (e.g., "1.6 TiB" for a 2 TiB export)

**Example:**
```
powerscale_quota_set(
  path="/ifs/data/data",
  soft_limit_size="1.6 TiB"
)
```

**Verify:**
- Soft quota is applied: `powerscale_quota_get(path="/ifs/data/data")`
- Soft limit shows as 80% of hard limit

### Step 4: Create Snapshot Schedule

Call `powerscale_snapshot_schedule_add()` to automate backups.

**Parameters:**
- `path` — Same path as the export
- `schedule_name` — Descriptive name (e.g., "data-hourly", "data-daily")
- `interval` — How often to snapshot (e.g., "hourly", "daily", "weekly")
- `keep` — How many snapshots to retain (e.g., 24 for hourly, 7 for daily)

**Example:**
```
powerscale_snapshot_schedule_add(
  path="/ifs/data/data",
  schedule_name="data-daily",
  interval="daily",
  keep=7
)
```

**Verify:**
- Snapshot schedule is created: `powerscale_snapshot_schedule_list()`
- First snapshot is created within the interval

## Complete Example

**User Request:**
> "Provision an export named 'archive' with a 10 TiB hard limit and 8 TiB soft limit. Take daily snapshots, keeping the last 7 days."

**Execute these steps:**

1. **Create NFS export:**
   ```
   powerscale_nfs_add(
     export_name="archive",
     path="/ifs/data/archive",
     description="NFS export for long-term archival"
   )
   ```

2. **Set hard quota:**
   ```
   powerscale_quota_set(
     path="/ifs/data/archive",
     hard_limit_size="10 TiB"
   )
   ```

3. **Set soft quota:**
   ```
   powerscale_quota_set(
     path="/ifs/data/archive",
     soft_limit_size="8 TiB"
   )
   ```

4. **Create snapshot schedule:**
   ```
   powerscale_snapshot_schedule_add(
     path="/ifs/data/archive",
     schedule_name="archive-daily",
     interval="daily",
     keep=7
   )
   ```

**Result:**
- NFS export is accessible at `archive.<cluster-ip>` or `<cluster-ip>:/ifs/data/archive`
- Unix/Linux clients can mount: `mount <cluster-ip>:/ifs/data/archive /mnt/archive`
- Hard quota limits writes at 10 TiB
- Soft quota warns admins at 8 TiB
- Daily snapshots are retained for 7 days

## Size Guidelines

Choose appropriate quota sizes based on use case:

| Use Case | Hard Limit | Soft Limit | Snapshot |
|----------|-----------|-----------|----------|
| Home directory | 100 GiB | 80 GiB | Daily (7 days) |
| Project team | 500 GiB – 2 TiB | 80-90% of hard | Hourly (24h) |
| Development | 1-5 TiB | 80-90% of hard | Hourly (7 days) |
| Archive | 10+ TiB | 95% of hard | Weekly (4 weeks) |
| Backup target | No hard limit | 95% of capacity | N/A |

## NFS-Specific Considerations

**Access Control:**
- By default, NFS exports allow read/write access from any client
- Use `powerscale_nfs_global_settings_set()` to restrict by IP range if needed
- Consider security groups or firewall rules for production exports

**NFS Versions:**
- Modern exports should support NFSv3, NFSv4, NFSv4.1
- Legacy systems may require NFSv3 only
- Check `powerscale_nfs_global_settings_get()` for current settings

**Performance:**
- NFS thread tuning affects concurrent client performance
- Larger thread counts help high-concurrency workloads
- Default settings work for most use cases

## Troubleshooting

### NFS export creation fails
- Path may not exist or lack permissions
- Export path may conflict with existing export (rename and retry)
- NFS service may be disabled (enable via `powerscale_nfs_global_settings_set`)

### Quota fails to apply
- Path must already exist (create it first if needed)
- User must have admin privileges
- Path may already have a quota (update instead of create)

### Snapshot schedule not creating snapshots
- NFS export must have data to snapshot
- Interval must be valid: "hourly", "daily", "weekly", "monthly"
- Cluster must have free space for snapshots

### Clients cannot mount the export
- NFS service must be enabled on the cluster
- Client firewall may be blocking NFS ports (111, 2049, 20048)
- Check cluster network configuration: `powerscale_network_status()`
- Verify export is created: `powerscale_nfs_list()`

## Post-Provisioning

Once provisioned, the export is ready for clients. Optional next steps:

- **Set access controls** — Restrict export to specific IP ranges
- **Enable Kerberos** — `powerscale_nfs_global_settings_set(kerberos=true)` for secure authentication
- **Configure data protection** — Set up SyncIQ for replication if needed
- **Monitor capacity** — Track quota usage with `powerscale_quota_get()`
- **Tune performance** — Adjust NFS thread counts for workload

## Notes

- **All steps are REQUIRED** for a fully provisioned export — skipping any step leaves the export incomplete
- **Order matters** — Create the NFS export first, then quotas, then snapshots
- **User confirmation** — All steps are mutating operations and require explicit confirmation before execution
- **Naming convention** — Use consistent, descriptive names (e.g., `export-name-daily` for snapshots)
- **Soft quota best practice** — Set soft limit to 80-90% of hard limit for early warnings

## Related Skills & Tools

- **Provision a Share** — Create SMB shares (Windows/CIFS) instead of NFS exports
- **Manage Quotas** — Adjust quota limits after provisioning
- **NFS Configuration** — Fine-tune NFS settings (versions, security, performance)
- **Snapshot Recovery** — Restore files from snapshots
- **Performance Tuning** — Optimize cluster for export workloads
