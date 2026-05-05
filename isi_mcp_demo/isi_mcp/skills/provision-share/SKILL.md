---
description: Create a fully provisioned SMB share with quotas and snapshot schedules
version: "1.0.0"
tags: [provisioning, smb, quotas, snapshots, share-management]
---

# Provision a Share Skill

This skill guides the process of provisioning a complete **SMB share** on PowerScale, including quotas and snapshot scheduling. A provisioned share includes storage access, capacity limits, and backup schedules.

## Important: SMB Shares Only

**When a user asks to "provision a share" or "create a share", this always means an SMB (CIFS/Windows) share.**

- **SMB shares** are created using this skill
- **NFS exports** use a separate skill (available separately)

If a user specifically asks for an NFS export or NFS access, direct them to the provision NFS export skill instead.

## What is Share Provisioning?

Provisioning an SMB share means setting up a complete, production-ready SMB export with:
- **Storage path** — The actual directory on the cluster
- **Share export** — SMB protocol access for Windows/Linux clients
- **Hard quota** — Maximum capacity before writes are rejected
- **Soft quota** — Warning threshold (recommended 80-90% of hard quota)
- **Snapshot schedule** — Automated point-in-time backups for recovery

## Provision a Share Workflow

When a user asks to **"provision a share"** or **"create a new share"**, follow these steps in order:

### Default Assumptions

This skill **always provisions SMB shares**. If the user does not explicitly specify:
- **Filesystem path** — Assume `/ifs/data/{share_name}` (where `{share_name}` is the share name provided)
- **Cluster** — Use the default cluster (no cluster_name parameter needed)
- **Snapshot interval** — Use daily (24-hour snapshots, keep 7 days) if not specified
- **Soft limit** — Calculate as 80% of hard limit if not provided

These defaults enable users to provision an SMB share with minimal input while still getting a production-ready setup.

**If a user asks for an NFS export**, that is a different operation and uses the "Provision NFS Export" skill instead.

### Step 1: Create the SMB Share

Call `powerscale_smb_add()` to export the share via SMB protocol.

**Parameters:**
- `share_name` — Name of the SMB share (e.g., "foo", "projects", "backups")
- `path` — Full path on cluster (typically `/ifs/data/{share_name}`)
- Optional: `description`, `comment` — User-facing labels

**Example:**
```
powerscale_smb_add(
  share_name="foo",
  path="/ifs/data/foo",
  description="Project share for foo team"
)
```

**Verify:**
- SMB share is exported and accessible via `\\<cluster-ip>\foo`
- Users can browse and create files

### Step 2: Set Hard Quota

Call `powerscale_quota_set()` to enforce a maximum storage limit.

**Parameters:**
- `path` — Same path as the share (e.g., `/ifs/data/foo`)
- `hard_limit` — Maximum bytes allowed (writes fail when exceeded)
- `hard_limit_size` — Human-readable format (e.g., "1 TiB", "500 GiB")

**Example:**
```
powerscale_quota_set(
  path="/ifs/data/foo",
  hard_limit_size="1 TiB"
)
```

**Verify:**
- Hard quota is applied: `powerscale_quota_get(path="/ifs/data/foo")`
- Hard limit shows in bytes (converted from TiB)

### Step 3: Set Soft Quota

Call `powerscale_quota_set()` again to set a soft (warning) limit.

**Parameters:**
- `path` — Same path as the share
- `soft_limit` — Warning threshold in bytes (typically 80-90% of hard quota)
- `soft_limit_size` — Human-readable format (e.g., "800 GiB" for a 1 TiB share)

**Example:**
```
powerscale_quota_set(
  path="/ifs/data/foo",
  soft_limit_size="800 GiB"
)
```

**Verify:**
- Soft quota is applied: `powerscale_quota_get(path="/ifs/data/foo")`
- Soft limit shows as 80-90% of hard limit

### Step 4: Create Snapshot Schedule

Call `powerscale_snapshot_schedule_add()` to automate backups.

**Parameters:**
- `path` — Same path as the share
- `schedule_name` — Descriptive name (e.g., "foo-hourly", "foo-daily")
- `interval` — How often to snapshot (e.g., "hourly", "daily", "weekly")
- `keep` — How many snapshots to retain (e.g., 24 for hourly, 7 for daily)

**Example:**
```
powerscale_snapshot_schedule_add(
  path="/ifs/data/foo",
  schedule_name="foo-hourly",
  interval="hourly",
  keep=24
)
```

**Verify:**
- Snapshot schedule is created: `powerscale_snapshot_schedule_list()`
- First snapshot is created within the interval

## Complete Example

**User Request:**
> "Provision a share named 'projects' with a 2 TiB hard limit and 1.5 TiB soft limit. Take hourly snapshots, keeping the last 24 hours."

**Execute these steps:**

1. **Create SMB share:**
   ```
   powerscale_smb_add(
     share_name="projects",
     path="/ifs/data/projects",
     description="Project collaboration share"
   )
   ```

2. **Set hard quota:**
   ```
   powerscale_quota_set(
     path="/ifs/data/projects",
     hard_limit_size="2 TiB"
   )
   ```

3. **Set soft quota:**
   ```
   powerscale_quota_set(
     path="/ifs/data/projects",
     soft_limit_size="1.5 TiB"
   )
   ```

4. **Create snapshot schedule:**
   ```
   powerscale_snapshot_schedule_add(
     path="/ifs/data/projects",
     schedule_name="projects-hourly",
     interval="hourly",
     keep=24
   )
   ```

**Result:**
- SMB share is accessible at `\\<cluster-ip>\projects`
- Hard quota limits writes at 2 TiB
- Soft quota warns admins at 1.5 TiB
- Hourly snapshots are retained for 24 hours

## Size Guidelines

Choose appropriate quota sizes based on use case:

| Use Case | Hard Limit | Soft Limit | Snapshot |
|----------|-----------|-----------|----------|
| Home directory | 100 GiB | 80 GiB | Daily (7 days) |
| Project team | 500 GiB – 2 TiB | 80-90% of hard | Hourly (24h) |
| Development | 1-5 TiB | 80-90% of hard | Hourly (7 days) |
| Archive | 10+ TiB | 95% of hard | Weekly (4 weeks) |
| Backup target | No hard limit | 95% of capacity | N/A |

## Troubleshooting

### SMB share creation fails
- Path may not exist or lack permissions
- Share name may conflict with existing share (rename and retry)
- SMB service may be disabled (enable via `powerscale_smb_global_settings_set`)

### Quota fails to apply
- Path must already exist (create it first if needed)
- User must have admin privileges
- Path may already have a quota (update instead of create)

### Snapshot schedule not creating snapshots
- SMB share must have data to snapshot
- Interval must be valid: "hourly", "daily", "weekly", "monthly"
- Cluster must have free space for snapshots

### Users can write past hard quota
- Hard quota was not applied correctly (verify with `powerscale_quota_get`)
- Quota enforcement may be disabled on the share
- Check SMB global settings for quota enforcement flags

## Post-Provisioning

Once provisioned, the share is ready for users. Optional next steps:

- **Set ACLs** — `powerscale_directory_acl_set()` to control who can access
- **Enable SMB encryption** — `powerscale_smb_global_settings_set(encryption=true)`
- **Configure data protection** — Set up SyncIQ for replication if needed
- **Monitor capacity** — Track quota usage with `powerscale_quota_get()`

## Notes

- **All steps are REQUIRED** for a fully provisioned share — skipping any step leaves the share incomplete
- **Order matters** — Create the SMB share first, then quotas, then snapshots
- **User confirmation** — All steps are mutating operations and require explicit confirmation before execution
- **Naming convention** — Use consistent, descriptive names (e.g., `share-name-hourly` for snapshots)
- **Soft quota best practice** — Set soft limit to 80-90% of hard limit for early warnings

## Related Skills & Tools

- **Manage Quotas** — Adjust quota limits after provisioning
- **SMB Configuration** — Fine-tune SMB settings (encryption, signing, versions)
- **Snapshot Recovery** — Restore files from snapshots
- **Performance Tuning** — Optimize cluster for share workloads
