import json
import os
import re
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP
from modules.onefs.v9_12_0.cluster import Cluster
from modules.onefs.v9_12_0.health import Health
from modules.onefs.v9_12_0.capacity import Capacity
from modules.onefs.v9_12_0.quotas import Quotas
from modules.onefs.v9_12_0.snapshots import Snapshots
from modules.onefs.v9_12_0.snapshotschedules import SnapshotSchedules
from modules.onefs.v9_12_0.synciq import SyncIQ
from modules.onefs.v9_12_0.nfs import Nfs
from modules.onefs.v9_12_0.s3 import S3
from modules.onefs.v9_12_0.smb import Smb
from modules.onefs.v9_12_0.config import Config
from modules.onefs.v9_12_0.filemgmt import FileMgmt
from modules.onefs.v9_12_0.datamover import DataMover
from modules.onefs.v9_12_0.filepool import FilePool
from modules.onefs.v9_12_0.users import Users
from modules.onefs.v9_12_0.group import Group
from modules.onefs.v9_12_0.events import Events
from modules.onefs.v9_12_0.statistics import Statistics
from modules.network.utils import pingable
from modules.ansible.vault_manager import VaultManager

import urllib3
from pprint import pprint

cluster = Cluster.from_vault()


mcp = FastMCP(
    "powerscale",
    instructions=(
        "This server provides tools for managing a PowerScale (Isilon) cluster."
    ),
)

# ---------------------------------------------------------------------------
# Tool group registry — maps group names to the tool function names they contain
# ---------------------------------------------------------------------------
TOOL_GROUPS: Dict[str, List[str]] = {
    "health": [
        "powerscale_check_health",
    ],
    "capacity": [
        "powerscale_capacity",
        "powerscale_config",
    ],
    "quotas": [
        "powerscale_quota_get",
        "powerscale_quota_set",
        "powerscale_quota_increment",
        "powerscale_quota_decrement",
        "powerscale_quota_create",
        "powerscale_quota_remove",
    ],
    "snapshots": [
        "powerscale_snapshot_get",
        "powerscale_snapshot_schedule_get",
        "powerscale_snapshot_schedule_create",
        "powerscale_snapshot_schedule_remove",
        "powerscale_snapshot_create",
        "powerscale_snapshot_delete",
        "powerscale_snapshot_pending_get",
        "powerscale_snapshot_alias_create",
        "powerscale_snapshot_alias_get",
    ],
    "synciq": [
        "powerscale_synciq_get",
        "powerscale_synciq_create",
        "powerscale_synciq_remove",
    ],
    "datamover": [
        "powerscale_datamover_policy_get",
        "powerscale_datamover_policy_get_by_id",
        "powerscale_datamover_policy_create",
        "powerscale_datamover_policy_delete",
        "powerscale_datamover_policy_last_job",
        "powerscale_datamover_account_get",
        "powerscale_datamover_account_get_by_id",
        "powerscale_datamover_account_create",
        "powerscale_datamover_account_delete",
        "powerscale_datamover_base_policy_get",
        "powerscale_datamover_base_policy_get_by_id",
        "powerscale_datamover_base_policy_create",
        "powerscale_datamover_base_policy_delete",
    ],
    "filepool": [
        "powerscale_filepool_policy_get",
        "powerscale_filepool_policy_get_by_name",
        "powerscale_filepool_default_policy_get",
        "powerscale_filepool_policy_create",
        "powerscale_filepool_policy_update",
        "powerscale_filepool_policy_remove",
    ],
    "nfs": [
        "powerscale_nfs_get",
        "powerscale_nfs_create",
        "powerscale_nfs_remove",
        "powerscale_nfs_global_settings_get",
        "powerscale_nfs_global_settings_set",
    ],
    "smb": [
        "powerscale_smb_get",
        "powerscale_smb_create",
        "powerscale_smb_remove",
        "powerscale_smb_global_settings_get",
        "powerscale_smb_global_settings_set",
        "powerscale_smb_sessions_get",
        "powerscale_smb_session_close",
        "powerscale_smb_sessions_close_by_user",
        "powerscale_smb_openfiles_get",
        "powerscale_smb_openfile_close",
    ],
    "s3": [
        "powerscale_s3_get",
        "powerscale_s3_create",
        "powerscale_s3_remove",
    ],
    "filemgmt": [
        "powerscale_directory_list",
        "powerscale_directory_attributes",
        "powerscale_directory_create",
        "powerscale_directory_delete",
        "powerscale_directory_move",
        "powerscale_directory_copy",
        "powerscale_file_read",
        "powerscale_file_attributes",
        "powerscale_file_create",
        "powerscale_file_delete",
        "powerscale_file_move",
        "powerscale_file_copy",
        "powerscale_acl_get",
        "powerscale_acl_set",
        "powerscale_metadata_get",
        "powerscale_metadata_set",
        "powerscale_access_point_list",
        "powerscale_access_point_create",
        "powerscale_access_point_delete",
        "powerscale_worm_get",
        "powerscale_worm_set",
        "powerscale_directory_query",
    ],
    "users": [
        "powerscale_user_get",
        "powerscale_user_create",
        "powerscale_user_modify",
        "powerscale_user_remove",
    ],
    "groups": [
        "powerscale_group_get",
        "powerscale_group_create",
        "powerscale_group_modify",
        "powerscale_group_remove",
    ],
    "events": [
        "powerscale_event_get",
        "powerscale_event_get_by_id",
    ],
    "statistics": [
        "powerscale_stats_cpu",
        "powerscale_stats_network",
        "powerscale_stats_disk",
        "powerscale_stats_ifs",
        "powerscale_stats_node",
        "powerscale_stats_protocol",
        "powerscale_stats_clients",
        "powerscale_stats_get",
        "powerscale_stats_keys",
    ],
    "utils": [
        "current_time",
        "bytes_to_human",
        "human_to_bytes",
    ],
}

# Management tools — these cannot be disabled
MANAGEMENT_TOOLS = {
    "powerscale_tools_list",
    "powerscale_tools_toggle",
    "powerscale_cluster_list",
    "powerscale_cluster_select",
    "powerscale_cluster_add",
    "powerscale_cluster_remove",
}

# Build reverse lookup: tool_name -> group_name
_TOOL_TO_GROUP: Dict[str, str] = {}
for _grp, _tools in TOOL_GROUPS.items():
    for _t in _tools:
        _TOOL_TO_GROUP[_t] = _grp

# Stash for disabled tools so they can be re-enabled at runtime
_disabled_tools: Dict[str, Any] = {}  # tool_name -> Tool object

# Path to the persistent config file
TOOL_CONFIG_PATH = os.environ.get("TOOL_CONFIG_PATH", "/app/tool_config.json")


def _load_tool_config() -> dict:
    """Load tool_config.json, returning defaults if missing or invalid."""
    try:
        with open(TOOL_CONFIG_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"disabled_groups": [], "disabled_tools": []}


def _save_tool_config(config: dict) -> None:
    """Persist tool config to disk."""
    with open(TOOL_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def _resolve_names_to_tools(names: List[str]) -> List[str]:
    """Resolve a mix of group names and individual tool names to a flat
    list of individual tool names. Unknown names are silently skipped."""
    result = []
    for name in names:
        if name in TOOL_GROUPS:
            result.extend(TOOL_GROUPS[name])
        elif name in _TOOL_TO_GROUP or name in _disabled_tools:
            result.append(name)
    return result


def _get_reachable_cluster() -> Cluster:
    """Create a cluster from vault and verify network reachability via ping.

    Raises RuntimeError if the cluster host cannot be reached.
    This should be used by all domain tools instead of Cluster.from_vault() directly.
    """
    c = Cluster.from_vault()
    host_for_ping = re.sub(r'^https?://', '', c.host) if c.host else None
    if not host_for_ping:
        raise RuntimeError("No cluster host configured.")
    if not pingable(host_for_ping, debug=c.debug):
        raise RuntimeError(
            f"Cluster host '{host_for_ping}' is not reachable. "
            "Verify the cluster is online and network connectivity is available."
        )
    return c


@mcp.tool()
def current_time() -> dict:
    """
    Return the current local date and time from the PowerScale MCP server.

    This provides a real-time timestamp from the server hosting the MCP service,
    which may differ from the user's local time if the server is in a different
    timezone or geographic location.

    Response fields:
    - date: Current date in yyyy-mm-dd format
    - time: Current time in HH:MM:SS format (24-hour)
    - timezone: Timezone abbreviation (e.g. "UTC", "EST", "PST")
    - gmt_offset: Numeric offset from GMT (e.g. "+0000", "-0500")

    Use this tool to answer questions such as:
    - What time is it on the PowerScale management server?
    - What timezone is the MCP server running in?
    - What is today's date according to the cluster?
    - Is there a time difference between my location and the server?

    This is also useful for correlating timestamps in snapshot schedules,
    replication jobs, or event logs with the actual server clock.
    """
    now = datetime.now().astimezone()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": now.strftime("%Z"),
        "gmt_offset": now.strftime("%z"),
    }

@mcp.tool()
def powerscale_check_health() -> dict:
    """
    Perform a comprehensive health check on the PowerScale (formerly Isilon) cluster.

    This tool runs a series of diagnostic checks against the live cluster and returns
    a pass/fail result with an explanation. The checks are performed in priority order
    and the first failure stops the sequence — this means the most critical issue is
    always reported first.

    Health checks performed (in order):
    1. Quorum — Is the cluster in quorum? Loss of quorum is a critical failure
       indicating the cluster cannot reach consensus among its nodes.
    2. Service light — Is the front-panel service light illuminated? An active
       service light indicates a hardware issue requiring physical attention.
    3. Critical events — Are there unresolved or un-ignored critical events?
       These are high-severity alerts that require administrator action.
    4. Network connectivity — Are all external IPs defined on the cluster
       responding to ping? Unreachable IPs indicate network or node problems.
    5. Capacity — Does the cluster have more than 20% free space? Below this
       threshold the cluster is at risk of performance degradation or running
       out of space.

    Response fields:
    - status: Boolean — True means the cluster is healthy, False means unhealthy
    - message: Human-readable explanation of the result

    Use this tool to answer questions such as:
    - Is the PowerScale cluster healthy?
    - Are there any problems with the cluster right now?
    - Is the cluster in quorum?
    - Are there any critical alerts or events?
    - Can all cluster nodes be reached on the network?
    - Is the cluster running low on disk space?
    """

    try:
        cluster = _get_reachable_cluster()
        health = Health(cluster)
        return health.check()

    except Exception as e:
        return (f"Error {e}")

@mcp.tool()
def powerscale_capacity() -> dict:
    """
    Return real-time storage capacity statistics for the PowerScale cluster.

    This tool queries the cluster API at call time and returns current-state
    capacity data. All size values are in bytes — use the bytes_to_human tool
    to convert them to human-readable formats (GiB, TiB, etc.) when presenting
    results to the user.

    Response fields:
    - ifs.bytes.avail: Available (unused) space on the cluster in bytes
    - ifs.bytes.used: Space currently consumed on the cluster in bytes
    - ifs.bytes.total: Total raw capacity of the cluster in bytes
    - cluster.data.reduce.ratio.dedupe: Data deduplication ratio (e.g. 1.5
      means 1.5x deduplication savings)
    - cluster.compression.overall.ratio: Data compression ratio (e.g. 2.0
      means data is compressed to half its original size)

    Use this tool to answer questions such as:
    - How much data is stored on the PowerScale cluster?
    - How much free space is available?
    - What percentage of capacity is used?
    - What is the total size of the cluster?
    - What is my deduplication ratio?
    - What is my compression ratio?
    - How much effective capacity do I have with dedupe and compression?
    - Am I running low on storage?

    Tip: To calculate percent used, divide ifs.bytes.used by ifs.bytes.total
    and multiply by 100. To calculate effective savings, use the dedupe and
    compression ratios together.
    """
    try:
        cluster = _get_reachable_cluster()
        capacity = Capacity(cluster)
        return capacity.get()

    except Exception as e:
        return (f"Error {e}")

@mcp.tool()
def powerscale_config() -> dict:
    """
    Return cluster configuration and hardware details for the PowerScale cluster.

    This tool queries the cluster API and the Ansible info module to return
    identifying, configuration, and hardware information about the cluster.

    Response fields (from SDK):
    - name: Cluster name
    - guid: Cluster GUID (globally unique identifier)
    - description: Customer-configurable description
    - encoding: Default character encoding
    - has_quorum: Whether the local node is in a group with quorum
    - is_compliance: Whether compliance mode is enabled (stricter WORM)
    - is_virtual: Whether the cluster is a virtual deployment
    - is_vonefs: Whether this is a vOneFS cluster on ESXi
    - is_powerscale_ve: Whether this is a PowerScale VE cluster
    - join_mode: Node join mode ("manual" or "secure")
    - local_devid: Device ID of the queried node
    - local_lnn: Logical node number of the queried node
    - local_serial: Serial number of the queried node
    - onefs_version: OneFS version information (build, release, revision, type, version)
    - timezone: Cluster timezone settings
    - devices: List of device configuration objects

    Response fields (from Ansible — hardware sub-dict):
    - hardware.attributes: Cluster-level attributes (version, config, contact info)
    - hardware.nodes: Per-node hardware details (LNN, partitions, drives)
    - hardware.node_pools: Node pool groupings and membership
    - hardware.storage_pool_tiers: Storage pool tier configuration

    Use this tool to answer questions such as:
    - What is the cluster name?
    - What version of OneFS is running?
    - Is the cluster virtual or physical?
    - What is the cluster GUID?
    - Is compliance mode enabled?
    - What timezone is the cluster configured for?
    - How many nodes are in the cluster?
    - What hardware is in each node?
    - What are the node pools and storage tiers?
    - What drives or partitions does each node have?
    """
    try:
        cluster = _get_reachable_cluster()
        config = Config(cluster)
        return config.get()

    except Exception as e:
        return (f"Error {e}")

@mcp.tool()
def powerscale_quota_get(
    limit: int = 1000,
    resume: Optional[str] = None
    ) -> Dict[str, Any]:
    """
    Return quotas defined on the PowerScale cluster using pagination.

    Quotas control how much storage space a user, group, or directory path can
    consume. This tool retrieves the list of all configured quotas so you can
    inspect limits, usage, and enforcement settings.

    Usage (pagination):
    - First call: use resume=None (or omit it)
    - If the response contains a non-null "resume" value, call again passing
      that value as the resume argument to fetch the next page
    - Continue until "resume" is None (has_more will be False)
    - Do not call repeatedly with the same resume value

    Arguments:
    - limit: Maximum number of quotas to return per page (default 1000)
    - resume: Resume token from a previous call (or None for first call)

    Each quota object includes details such as:
    - path: The filesystem path the quota applies to
    - type: Quota type (e.g. "directory", "user", "group")
    - enforced: Whether the quota is actively enforced
    - thresholds: Hard, soft, and advisory limits in bytes
    - usage: Current space consumption against this quota in bytes
    - persona: The user or group the quota applies to (if not directory type)
    - linked: Whether this quota is linked to a parent
    - notifications: Alert/notification settings for threshold violations

    Use this tool to answer questions such as:
    - What quotas are configured on the cluster?
    - How much storage is allocated to a specific path or user?
    - Which quotas are close to their limits?
    - What is the hard limit on a directory?
    - Are there any quotas that are over their soft limit?
    - How much space is a specific directory actually using vs. its quota?

    Returns:
    - items: List of quota objects for this page
    - resume: Resume token for the next page, or None if finished
    - limit: The page size used
    - has_more: True if more pages exist
    """
    try:
        # Normalize resume in case LLM sends "null"
        resume = None if resume in (None, "null", "None") else resume

        cluster = _get_reachable_cluster()
        quotas = Quotas(cluster)

        page = quotas.get(limit=limit, resume=resume)

        items = page.get("items") or []
        resume = page.get("resume")

        return {
            "items": items,
            "resume": resume,
            "limit": limit,
            "has_more": bool(resume)
        }

    except Exception as e:
        return {"error": str(e)} 

@mcp.tool()
def powerscale_quota_set(path:str, size:int) -> str:
    """
    Set the hard quota on a PowerScale cluster path to an absolute size in bytes.

    IMPORTANT: This is a MUTATING operation that changes quota limits on the live
    cluster. Always confirm both the path and the target size with the user in
    human-readable format (e.g. "Set /ifs/data/projects to 500GiB?") before
    calling this tool. Use the human_to_bytes tool to convert the user's
    human-readable value to bytes if needed.

    Arguments:
    - path: The filesystem path to set the quota on (e.g. "/ifs/data/projects")
    - size: The hard quota limit in bytes (e.g. 536870912000 for 500GiB)

    Use this tool when the user wants to:
    - Set a specific quota size on a directory
    - Replace the current hard limit with a new value
    - Configure a new hard quota on a path

    Do NOT use this tool to increase or decrease a quota — use
    powerscale_quota_increment or powerscale_quota_decrement instead, as those
    adjust the limit relative to the current value.

    Returns a confirmation message describing the change made.
    """
    try:
        cluster = _get_reachable_cluster()
        quotas = Quotas(cluster)
        return quotas.set_hard_quota(path, size)

    except Exception as e:
        return (f"Error {e}")

@mcp.tool()
def powerscale_quota_increment(path:str, size:int) -> str:
    """
    Increase the hard quota on a PowerScale cluster path by a given number of bytes.

    IMPORTANT: This is a MUTATING operation that changes quota limits on the live
    cluster. Always confirm both the path and the increment amount with the user
    in human-readable format (e.g. "Increase /ifs/data/projects by 100GiB?")
    before calling this tool. Use the human_to_bytes tool to convert the user's
    human-readable value to bytes if needed.

    This tool ADDS the specified size to the current hard quota. For example, if
    the current hard limit is 500GiB and you call this with size=107374182400
    (100GiB), the new hard limit will be 600GiB.

    Arguments:
    - path: The filesystem path whose quota to increase (e.g. "/ifs/data/projects")
    - size: The amount to add to the current hard limit, in bytes

    Use this tool when the user wants to:
    - Give more space to a directory or user
    - Increase a quota by a relative amount (e.g. "add 100GiB")
    - Expand a quota that is close to full

    Do NOT use this tool to set an absolute quota value — use
    powerscale_quota_set instead.

    Returns a confirmation message describing the change made.
    """
    try:
        cluster = _get_reachable_cluster()
        quotas = Quotas(cluster)
        return quotas.increment_hard_quota(path, size)

    except Exception as e:
        return (f"Error {e}")

@mcp.tool()
def powerscale_quota_decrement(path:str, size:int) -> str:
    """
    Decrease the hard quota on a PowerScale cluster path by a given number of bytes.

    IMPORTANT: This is a MUTATING operation that changes quota limits on the live
    cluster. Always confirm both the path and the decrement amount with the user
    in human-readable format (e.g. "Reduce /ifs/data/projects by 50GiB?") before
    calling this tool. Use the human_to_bytes tool to convert the user's
    human-readable value to bytes if needed.

    WARNING: Reducing a quota below the current usage will NOT delete data, but
    it will prevent new writes and may trigger over-quota alerts. Always check
    current usage with powerscale_quota_get before reducing a quota.

    This tool SUBTRACTS the specified size from the current hard quota. For
    example, if the current hard limit is 500GiB and you call this with
    size=53687091200 (50GiB), the new hard limit will be 450GiB.

    Arguments:
    - path: The filesystem path whose quota to decrease (e.g. "/ifs/data/projects")
    - size: The amount to subtract from the current hard limit, in bytes

    Use this tool when the user wants to:
    - Reduce space allocated to a directory or user
    - Decrease a quota by a relative amount (e.g. "remove 50GiB")
    - Reclaim unused quota capacity

    Do NOT use this tool to set an absolute quota value — use
    powerscale_quota_set instead.

    Returns a confirmation message describing the change made.
    """
    try:
        cluster = _get_reachable_cluster()
        quotas = Quotas(cluster)
        return quotas.decrement_hard_quota(path, size)

    except Exception as e:
        return (f"Error {e}")

@mcp.tool()
def powerscale_snapshot_get(
    limit: int = 1000,
    resume: Optional[str] = None
    ) -> Dict[str, Any]:
    """
    Returns snapshots on the PowerScale cluster using pagination.

    Usage:
    - First call: resume=None
    - If "resume" is returned in the response, call again with that value
    - Continue until "resume" is None
    - Do not call repeatedly with the same resume value

    Arguments:
    - limit: Maximum number of snapshots per page
    - resume: Resume token from a previous call (or None for first call)

    Each snapshot object includes details such as:
    - name: The snapshot name
    - path: The filesystem path the snapshot protects
    - created: Timestamp of when the snapshot was created
    - expires: Expiration timestamp (if set)
    - size: Size of the snapshot in bytes
    - state: Current state of the snapshot (e.g. "active")
    - schedule: The schedule that created the snapshot (if applicable)
    - alias: Any alias associated with the snapshot
    - has_locks: Whether the snapshot has locks preventing deletion
    - pct_filesystem: Percentage of filesystem used by the snapshot
    - pct_reserve: Percentage of snapshot reserve used
    - shadow_bytes: Bytes of shadow store data
    - target_id: Target snapshot ID for clones
    - target_name: Target snapshot name for clones

    Use this tool to answer questions about snapshots such as:
    - What snapshots exist on the cluster?
    - When was the last snapshot taken for a path?
    - How much space are snapshots consuming?
    - Are there any expired snapshots?
    - What snapshot schedules are active?

    Returns:
    - items: List of snapshot objects for this page
    - resume: Resume token for the next page, or None if finished
    - has_more: True if more pages exist
    """
    try:
        resume = None if resume in (None, "null", "None") else resume

        cluster = _get_reachable_cluster()
        snapshots = Snapshots(cluster)

        page = snapshots.get(limit=limit, resume=resume)

        items = page.get("items") or []
        resume = page.get("resume")

        return {
            "items": items,
            "resume": resume,
            "limit": limit,
            "has_more": bool(resume)
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_snapshot_schedule_get(
    limit: int = 1000,
    resume: Optional[str] = None
    ) -> Dict[str, Any]:
    """
    Returns snapshot schedules on the PowerScale cluster using pagination.

    Snapshot schedules define recurring policies that automatically create
    snapshots on a path at a specified interval.

    Usage:
    - First call: resume=None
    - If "resume" is returned in the response, call again with that value
    - Continue until "resume" is None
    - Do not call repeatedly with the same resume value

    Arguments:
    - limit: Maximum number of schedules per page
    - resume: Resume token from a previous call (or None for first call)

    Each schedule object includes details such as:
    - id: Unique schedule identifier
    - name: The schedule name
    - path: The filesystem path being snapshotted
    - schedule: The isidate schedule string (e.g. "Every day every 4 hours")
    - duration: Retention period in seconds (how long snapshots are kept)
    - pattern: Naming pattern for generated snapshots (strftime format)
    - next_run: Timestamp of the next scheduled run
    - next_snapshot: Name of the next snapshot to be created
    - alias: Alias pointing to the latest snapshot in this schedule

    Use this tool to answer questions about snapshot schedules such as:
    - What snapshot schedules are configured on the cluster?
    - How often are snapshots taken for a path?
    - When is the next snapshot scheduled?
    - How long are snapshots retained?
    - What naming pattern is used for snapshots?

    Returns:
    - items: List of snapshot schedule objects for this page
    - resume: Resume token for the next page, or None if finished
    - has_more: True if more pages exist
    """
    try:
        resume = None if resume in (None, "null", "None") else resume

        cluster = _get_reachable_cluster()
        schedules = SnapshotSchedules(cluster)

        page = schedules.get(limit=limit, resume=resume)

        items = page.get("items") or []
        resume = page.get("resume")

        return {
            "items": items,
            "resume": resume,
            "limit": limit,
            "has_more": bool(resume)
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_synciq_get() -> Dict[str, Any]:
    """
    Returns all SyncIQ replication policies on the PowerScale cluster.

    SyncIQ is the replication engine for PowerScale. Each policy defines a replication
    relationship between a source and target cluster/path.

    Each policy object includes details such as:
    - name: The policy name
    - id: Unique policy identifier
    - enabled: Whether the policy is active
    - action: The replication action (e.g. "sync" or "copy")
    - source_root_path: The source directory path being replicated
    - target_host: The target cluster hostname or IP
    - target_path: The target directory path
    - schedule: The replication schedule (cron-style or manual)
    - last_success: Timestamp of last successful replication
    - last_started: Timestamp of last job start
    - last_job_state: State of the last job (e.g. "finished", "failed")
    - target_snapshot_archive: Whether target snapshots are archived
    - workers_per_node: Number of worker threads per node

    Use this tool to answer questions about replication such as:
    - What replication policies are configured?
    - Is replication running between specific clusters?
    - When did the last successful replication complete?
    - Are any replication policies disabled or failing?
    - What paths are being replicated?

    Returns:
    - items: List of SyncIQ policy objects
    """
    try:
        cluster = _get_reachable_cluster()
        synciq = SyncIQ(cluster)
        return synciq.get()

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_nfs_get(
    limit: int = 1000,
    resume: Optional[str] = None
    ) -> Dict[str, Any]:
    """
    Returns NFS exports on the PowerScale cluster using pagination.

    NFS (Network File System) exports define which filesystem paths are shared
    over the NFS protocol and the access rules for each export.

    Usage:
    - First call: resume=None
    - If "resume" is returned in the response, call again with that value
    - Continue until "resume" is None
    - Do not call repeatedly with the same resume value

    Arguments:
    - limit: Maximum number of exports per page
    - resume: Resume token from a previous call (or None for first call)

    Each export object includes details such as:
    - id: Unique export identifier
    - paths: List of filesystem paths shared by this export
    - description: Human-readable description of the export
    - clients: List of client hostnames/IPs allowed to access this export
    - root_clients: Clients granted root access
    - read_only_clients: Clients with read-only access
    - read_write_clients: Clients with read-write access
    - map_root: User mapping for root access (e.g. "root", "nobody")
    - map_all: User mapping applied to all users
    - security_flavors: Authentication methods (e.g. "unix", "krb5")
    - block_size: NFS block size
    - read_only: Whether the export is globally read-only
    - zone: The access zone the export belongs to

    Use this tool to answer questions about NFS exports such as:
    - What NFS exports are configured on the cluster?
    - Which paths are shared over NFS?
    - What clients have access to a specific export?
    - Are there any exports with root access granted?
    - What access zones have NFS exports?

    Returns:
    - items: List of NFS export objects for this page
    - resume: Resume token for the next page, or None if finished
    - has_more: True if more pages exist
    """
    try:
        resume = None if resume in (None, "null", "None") else resume

        cluster = _get_reachable_cluster()
        nfs = Nfs(cluster)

        page = nfs.get(limit=limit, resume=resume)

        items = page.get("items") or []
        resume = page.get("resume")

        return {
            "items": items,
            "resume": resume,
            "limit": limit,
            "has_more": bool(resume)
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_s3_get(
    limit: int = 1000,
    resume: Optional[str] = None
    ) -> Dict[str, Any]:
    """
    Returns S3 buckets on the PowerScale cluster using pagination.

    PowerScale supports an S3-compatible object storage interface. Each bucket
    maps to a directory on the cluster filesystem and provides S3 API access.

    Usage:
    - First call: resume=None
    - If "resume" is returned in the response, call again with that value
    - Continue until "resume" is None
    - Do not call repeatedly with the same resume value

    Arguments:
    - limit: Maximum number of buckets per page
    - resume: Resume token from a previous call (or None for first call)

    Each bucket object includes details such as:
    - name: The bucket name (used in S3 API requests)
    - id: Unique bucket identifier
    - path: The filesystem path the bucket maps to
    - owner: The bucket owner
    - description: Human-readable description
    - create_path: Whether to create the path if it does not exist
    - acl: Access control list defining permissions
    - object_acl_policy: Policy for object-level ACLs
    - zone: The access zone the bucket belongs to

    Use this tool to answer questions about S3 buckets such as:
    - What S3 buckets are configured on the cluster?
    - Which filesystem paths are exposed as S3 buckets?
    - Who owns a specific bucket?
    - What access zones have S3 buckets?
    - What are the ACL settings for a bucket?

    Returns:
    - items: List of S3 bucket objects for this page
    - resume: Resume token for the next page, or None if finished
    - has_more: True if more pages exist
    """
    try:
        resume = None if resume in (None, "null", "None") else resume

        cluster = _get_reachable_cluster()
        s3 = S3(cluster)

        page = s3.get(limit=limit, resume=resume)

        items = page.get("items") or []
        resume = page.get("resume")

        return {
            "items": items,
            "resume": resume,
            "limit": limit,
            "has_more": bool(resume)
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_smb_get(
    limit: int = 1000,
    resume: Optional[str] = None
    ) -> Dict[str, Any]:
    """
    Returns SMB shares on the PowerScale cluster using pagination.

    SMB (Server Message Block) shares define which filesystem paths are shared
    over the SMB/CIFS protocol for access by Windows and other SMB clients.

    Usage:
    - First call: resume=None
    - If "resume" is returned in the response, call again with that value
    - Continue until "resume" is None
    - Do not call repeatedly with the same resume value

    Arguments:
    - limit: Maximum number of shares per page
    - resume: Resume token from a previous call (or None for first call)

    Each share object includes details such as:
    - name: The share name
    - path: The filesystem path being shared
    - description: Human-readable description of the share
    - permissions: Access permissions configured on the share
    - browsable: Whether the share is visible when browsing
    - access_based_enumeration: Whether ABE is enabled
    - continuously_available: Whether the share supports continuous availability
    - file_create_mode: Default file creation permissions
    - directory_create_mode: Default directory creation permissions
    - zone: The access zone the share belongs to

    Use this tool to answer questions about SMB shares such as:
    - What SMB shares are configured on the cluster?
    - Which paths are shared over SMB/CIFS?
    - What permissions are set on a specific share?
    - What access zones have SMB shares?
    - Is a specific directory shared over SMB?

    Returns:
    - items: List of SMB share objects for this page
    - resume: Resume token for the next page, or None if finished
    - has_more: True if more pages exist
    """
    try:
        resume = None if resume in (None, "null", "None") else resume

        cluster = _get_reachable_cluster()
        smb = Smb(cluster)

        page = smb.get(limit=limit, resume=resume)

        items = page.get("items") or []
        resume = page.get("resume")

        return {
            "items": items,
            "resume": resume,
            "limit": limit,
            "has_more": bool(resume)
        }

    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------------------------
# Ansible-based create / remove tools
# ---------------------------------------------------------------------------

@mcp.tool()
def powerscale_smb_create(
    share_name: str,
    path: str,
    description: str = None,
    access_zone: str = None,
    create_path: bool = None,
    browsable: bool = None,
    access_based_enumeration: bool = None,
    access_based_enumeration_root_only: bool = None,
    ntfs_acl_support: bool = None,
    oplocks: bool = None,
    continuously_available: bool = None,
    smb3_encryption_enabled: bool = None,
    directory_create_mask: str = None,
    directory_create_mode: str = None,
    file_create_mask: str = None,
    file_create_mode: str = None,
    allow_variable_expansion: bool = None,
    auto_create_directory: bool = None,
    inheritable_path_acl: bool = None,
    allow_delete_readonly: bool = None,
    allow_execute_always: bool = None,
    ca_timeout_value: int = None,
    ca_timeout_unit: str = None,
    strict_ca_lockout: bool = None,
    ca_write_integrity: str = None,
    change_notify: str = None,
    impersonate_guest: str = None,
    impersonate_user: str = None,
    file_filtering_enabled: bool = None,
    file_filter_extension: str = None,
    permissions: str = None,
    host_acls: str = None,
    run_as_root: str = None,
) -> dict:
    """
    Create an SMB (CIFS) share on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new SMB share on the
    live cluster. Always confirm the share name and path with the user before
    calling this tool (e.g. "Create SMB share 'projects' at /ifs/data/projects?").

    This tool uses Ansible automation to create the share via the
    dellemc.powerscale collection. The share will be immediately available
    to SMB/CIFS clients after creation.

    Arguments (required):
    - share_name: The name of the SMB share (e.g. "projects", "finance_data")
    - path: The filesystem path to share (e.g. "/ifs/data/projects"). Must exist
      on the cluster unless create_path is true.

    Arguments (optional — omit to keep cluster defaults):
    - description: Human-readable description of the share
    - access_zone: Access zone containing this share (default "System").
      Use absolute paths for System zone, relative paths for other zones.
    - create_path: Create the filesystem path if it does not already exist
    - browsable: Share is visible in net view and the browse list
    - access_based_enumeration: Only enumerate files/folders the user has access to
    - access_based_enumeration_root_only: Apply ABE on the root directory only
    - ntfs_acl_support: Support NTFS ACLs on files and directories
    - oplocks: Support opportunistic locks (can improve performance)
    - continuously_available: Allow persistent opens on the share (SMB3 CA,
      required for Hyper-V over SMB, SQL Server, etc.)
    - smb3_encryption_enabled: Require SMB3 encryption for this share
    - directory_create_mask: Octal mask for new directories (e.g. "0755")
    - directory_create_mode: Octal mode bits always set on new directories (e.g. "0000")
    - file_create_mask: Octal mask for new files (e.g. "0744")
    - file_create_mode: Octal mode bits always set on new files (e.g. "0000")
    - allow_variable_expansion: Automatic expansion of %U, %D, etc. for home dirs
    - auto_create_directory: Automatically create home directories
    - inheritable_path_acl: Set inheritable ACL on the share path
    - allow_delete_readonly: Allow deletion of read-only files in the share
    - allow_execute_always: Allow users to execute files they have read rights for
    - ca_timeout_value: Persistent open timeout value (integer). Used with
      ca_timeout_unit to set the continuously-available timeout.
    - ca_timeout_unit: Unit for ca_timeout_value — "seconds" (default) or "minutes"
    - strict_ca_lockout: Strict lockout on persistent opens
    - ca_write_integrity: Write-integrity level on CA shares
      (e.g. "none", "write-read-coherent", "full")
    - change_notify: Level of change notification alerts
      ("all", "norecurse", or "none")
    - impersonate_guest: Condition for guest impersonation
      ("always", "bad user", or "never")
    - impersonate_user: User account to impersonate as guest
    - file_filtering_enabled: Enable file filtering on this share (must be true
      for file_filter_extension to take effect)
    - file_filter_extension: JSON string defining file extension filters.
      Format: {"extensions": [".exe", ".bat"], "type": "deny", "state": "present-in-filter"}
      - extensions: list of file extensions to filter
      - type: "deny" (block listed) or "allow" (only allow listed) — default "deny"
      - state: state of the filter entries
    - permissions: JSON string — list of share-level permission entries.
      Each entry: {"permission": "read|write|full", "permission_type": "allow|deny"}
      plus ONE of: "user_name", "group_name", or "wellknown" to identify the trustee.
      Optional "provider_type": "local|file|ads|ldap|nis" (default "local").
      Example: [{"user_name": "admin", "permission": "full", "permission_type": "allow"},
                {"wellknown": "Everyone", "permission": "read", "permission_type": "allow"}]
    - host_acls: JSON string — list of host ACL entries controlling which
      hosts/networks can access the share.
      Each entry: {"name": "<host-or-subnet>", "access_type": "allow|deny"}
      Example: [{"name": "10.0.0.0/24", "access_type": "allow"}]
    - run_as_root: JSON string — list of personas allowed to map to root.
      Each entry: {"name": "<persona>", "type": "<persona-type>"}
      Optional: "provider_type" (default "local"), "state": "allow|absent" (default "allow").
      Example: [{"name": "admin", "type": "user", "provider_type": "local"}]

    Use this tool when the user wants to:
    - Create a new SMB/CIFS share
    - Share a directory over SMB/CIFS protocol
    - Make a filesystem path accessible to Windows clients

    Returns:
    - success: Boolean indicating if the share was created
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        smb = Smb(cluster)
        return smb.add(
            share_name=share_name,
            path=path,
            description=description,
            access_zone=access_zone,
            create_path=create_path,
            browsable=browsable,
            access_based_enumeration=access_based_enumeration,
            access_based_enumeration_root_only=access_based_enumeration_root_only,
            ntfs_acl_support=ntfs_acl_support,
            oplocks=oplocks,
            continuously_available=continuously_available,
            smb3_encryption_enabled=smb3_encryption_enabled,
            directory_create_mask=directory_create_mask,
            directory_create_mode=directory_create_mode,
            file_create_mask=file_create_mask,
            file_create_mode=file_create_mode,
            allow_variable_expansion=allow_variable_expansion,
            auto_create_directory=auto_create_directory,
            inheritable_path_acl=inheritable_path_acl,
            allow_delete_readonly=allow_delete_readonly,
            allow_execute_always=allow_execute_always,
            ca_timeout={"value": ca_timeout_value, "unit": ca_timeout_unit or "seconds"} if ca_timeout_value is not None else None,
            strict_ca_lockout=strict_ca_lockout,
            ca_write_integrity=ca_write_integrity,
            change_notify=change_notify,
            impersonate_guest=impersonate_guest,
            impersonate_user=impersonate_user,
            file_filtering_enabled=file_filtering_enabled,
            file_filter_extension=file_filter_extension,
            permissions=permissions,
            host_acls=host_acls,
            run_as_root=run_as_root,
        )
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_smb_remove(share_name: str) -> dict:
    """
    Remove an SMB (CIFS) share from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes an SMB share from the
    live cluster. Always confirm the share name with the user before calling
    this tool (e.g. "Remove SMB share 'projects'?"). This does NOT delete the
    underlying data on the filesystem — it only removes the share definition.

    Arguments:
    - share_name: The name of the SMB share to remove (e.g. "projects")

    Use this tool when the user wants to:
    - Remove or delete an SMB/CIFS share
    - Stop sharing a directory over SMB/CIFS
    - Unshare a path from Windows clients

    Returns:
    - success: Boolean indicating if the share was removed
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        smb = Smb(cluster)
        return smb.remove(share_name=share_name)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_smb_global_settings_get() -> dict:
    """
    Retrieve the current SMB global settings from the PowerScale cluster.

    Returns the cluster-wide SMB configuration including service status,
    protocol version support, security settings, and performance tuning.

    Key fields in the response:
    - service: Whether the SMB service is enabled
    - support_smb2: Whether SMB2 protocol is supported
    - support_smb3_encryption: Whether SMB3 encryption is supported
    - enable_security_signatures: Whether signed SMB packets are supported
    - require_security_signatures: Whether signed SMB packets are required
    - reject_unencrypted_access: Whether unencrypted access is rejected
    - support_multichannel: Whether SMB multichannel is supported
    - support_netbios: Whether NetBIOS is supported
    - server_side_copy: Whether server-side copy is enabled
    - guest_user: The user used for guest access
    - server_string: The server description string

    Use this tool to:
    - Check if the SMB service is enabled or disabled
    - See which SMB protocol versions are supported (SMB2, SMB3)
    - Review SMB security settings (encryption, signing)
    - View SMB performance configuration (workers, multichannel)
    """
    try:
        cluster = _get_reachable_cluster()
        smb = Smb(cluster)
        return smb.get_global_settings()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_smb_global_settings_set(
    service: bool = None,
    support_smb2: bool = None,
    support_smb3_encryption: bool = None,
    access_based_share_enum: bool = None,
    dot_snap_accessible_child: bool = None,
    dot_snap_accessible_root: bool = None,
    dot_snap_visible_child: bool = None,
    dot_snap_visible_root: bool = None,
    enable_security_signatures: bool = None,
    require_security_signatures: bool = None,
    reject_unencrypted_access: bool = None,
    server_side_copy: bool = None,
    support_multichannel: bool = None,
    support_netbios: bool = None,
    guest_user: str = None,
    server_string: str = None,
    onefs_cpu_multiplier: int = None,
    onefs_num_workers: int = None,
    ignore_eas: bool = None,
) -> dict:
    """
    Update SMB global settings on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that changes cluster-wide SMB
    configuration. Always confirm the intended changes with the user before
    calling this tool. Only pass the parameters you want to change — omitted
    parameters are left at their current values.

    Arguments:
    - service: Enable (true) or disable (false) the SMB service entirely
    - support_smb2: Enable/disable SMB2 protocol support
    - support_smb3_encryption: Enable/disable SMB3 encryption support
    - access_based_share_enum: Only enumerate files/folders the user has access to
    - dot_snap_accessible_child: Allow access to .snapshot in share subdirectories
    - dot_snap_accessible_root: Allow access to .snapshot in share root
    - dot_snap_visible_child: Show .snapshot in share subdirectories
    - dot_snap_visible_root: Show .snapshot in share root
    - enable_security_signatures: Support signed SMB packets
    - require_security_signatures: Require signed SMB packets
    - reject_unencrypted_access: Reject unencrypted access when SMB3 encryption is on
    - server_side_copy: Enable server-side copy
    - support_multichannel: Enable SMB multichannel
    - support_netbios: Enable NetBIOS support
    - guest_user: Fully-qualified user for guest access
    - server_string: Server description string
    - onefs_cpu_multiplier: OneFS driver worker threads per CPU
    - onefs_num_workers: Maximum OneFS driver worker threads
    - ignore_eas: Ignore extended attributes on files

    Use this tool to:
    - Enable or disable the SMB service
    - Control which SMB protocol versions are supported
    - Configure SMB security (encryption, signing)
    - Tune SMB performance settings
    """
    try:
        cluster = _get_reachable_cluster()
        smb = Smb(cluster)
        return smb.set_global_settings(
            service=service,
            support_smb2=support_smb2,
            support_smb3_encryption=support_smb3_encryption,
            access_based_share_enum=access_based_share_enum,
            dot_snap_accessible_child=dot_snap_accessible_child,
            dot_snap_accessible_root=dot_snap_accessible_root,
            dot_snap_visible_child=dot_snap_visible_child,
            dot_snap_visible_root=dot_snap_visible_root,
            enable_security_signatures=enable_security_signatures,
            require_security_signatures=require_security_signatures,
            reject_unencrypted_access=reject_unencrypted_access,
            server_side_copy=server_side_copy,
            support_multichannel=support_multichannel,
            support_netbios=support_netbios,
            guest_user=guest_user,
            server_string=server_string,
            onefs_cpu_multiplier=onefs_cpu_multiplier,
            onefs_num_workers=onefs_num_workers,
            ignore_eas=ignore_eas,
        )
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_smb_sessions_get(
    limit: int = 1000,
    lnn: Optional[str] = None,
    lnn_skip: Optional[str] = None,
    resume: Optional[str] = None,
    ) -> Dict[str, Any]:
    """
    Returns active SMB sessions across cluster nodes.

    SMB sessions represent active client connections to the cluster over the
    SMB/CIFS protocol. Each session tracks the connected user, client computer,
    open file count, idle/active time, and encryption status.

    Usage:
    - First call: resume=None
    - If "resume" is returned in the response, call again with that value
    - Continue until "resume" is None

    Arguments:
    - limit: Maximum number of sessions per page
    - lnn: Logical node number to query (use "all" for all nodes)
    - lnn_skip: When lnn="all", skip this specific node LNN
    - resume: Resume token from a previous call (or None for first call)

    Results are organized by node. Each node entry includes:
    - lnn: Logical node number
    - id: Node ID
    - total: Session count on this node
    - sessions: List of session objects, each containing:
      - id: Session ID (used for closing the session)
      - user: Authenticated username
      - computer: Client computer hostname
      - client_type: SMB dialect/version (e.g., "SMB3")
      - openfiles: Number of open files in this session
      - active_time: Time session has been active (seconds)
      - idle_time: Time session has been idle (seconds)
      - encryption: Whether the session uses encryption
      - guest_login: Whether this is a guest login

    Use this tool to answer questions such as:
    - Which clients are currently connected over SMB?
    - How many open files does a specific session have?
    - Which users have active SMB connections?
    - Is a specific client using encrypted SMB sessions?

    Returns:
    - nodes: List of node objects, each with session data
    - resume: Resume token for the next page, or None if finished
    - total: Total number of sessions across all nodes
    """
    try:
        resume = None if resume in (None, "null", "None") else resume

        cluster = _get_reachable_cluster()
        smb = Smb(cluster)

        page = smb.get_sessions(limit=limit, lnn=lnn, lnn_skip=lnn_skip, resume=resume)

        return {
            "nodes": page.get("nodes", []),
            "resume": page.get("resume"),
            "total": page.get("total"),
            "has_more": bool(page.get("resume")),
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_smb_session_close(session_id: str) -> Dict[str, Any]:
    """
    Closes (forcibly terminates) an active SMB session by session ID.

    IMPORTANT: This is a MUTATING operation. It will disconnect the client
    immediately. Any unsaved work in open files may be lost.

    Use powerscale_smb_sessions_get to list sessions and retrieve their IDs
    before calling this tool.

    Arguments:
    - session_id: The numeric session ID to close (from sessions list)

    Returns:
    - success: True if the session was closed
    - message: Confirmation message
    """
    try:
        cluster = _get_reachable_cluster()
        smb = Smb(cluster)
        return smb.delete_session(session_id)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_smb_sessions_close_by_user(
    computer: str,
    user: str,
    ) -> Dict[str, Any]:
    """
    Closes all active SMB sessions for a specific user on a specific client computer.

    IMPORTANT: This is a MUTATING operation. It will disconnect all matching
    sessions immediately. Any unsaved work in open files may be lost.

    This is useful for closing all sessions from a specific client machine
    or for a specific user without needing individual session IDs.

    Arguments:
    - computer: The client computer hostname (e.g., "DESKTOP-ABC123")
    - user: The username whose sessions should be closed (e.g., "DOMAIN\\\\username")

    Returns:
    - success: True if sessions were closed
    - message: Confirmation message
    """
    try:
        cluster = _get_reachable_cluster()
        smb = Smb(cluster)
        return smb.delete_sessions_by_user(computer=computer, user=user)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_smb_openfiles_get(
    limit: int = 1000,
    resume: Optional[str] = None,
    sort: Optional[str] = None,
    dir: Optional[str] = None,
    ) -> Dict[str, Any]:
    """
    Returns all files currently open via SMB on the cluster.

    Open files represent filesystem objects that SMB clients currently have
    open. This is useful for identifying locked files, tracking active usage,
    and diagnosing access conflicts.

    Usage:
    - First call: resume=None
    - If "resume" is returned in the response, call again with that value
    - Continue until "resume" is None

    Arguments:
    - limit: Maximum number of open file entries per page
    - resume: Resume token from a previous call (or None for first call)
    - sort: Field to sort results by (default: "id")
    - dir: Sort direction — "ASC" or "DESC"

    Each open file entry includes:
    - id: Open file ID (used for closing the file handle)
    - file: Path of the open file
    - user: User who has the file open
    - locks: Number of locks held on the file
    - permissions: List of permissions granted (e.g., ["read", "write"])

    Use this tool to answer questions such as:
    - Which files are currently open via SMB?
    - Who has a specific file open?
    - Are there any file locks currently held?
    - How many SMB clients have files open?

    Returns:
    - items: List of open file objects for this page
    - resume: Resume token for the next page, or None if finished
    - total: Total number of open files
    - has_more: True if more pages exist
    """
    try:
        resume = None if resume in (None, "null", "None") else resume

        cluster = _get_reachable_cluster()
        smb = Smb(cluster)

        page = smb.get_openfiles(limit=limit, resume=resume, sort=sort, dir=dir)

        return {
            "items": page.get("items", []),
            "resume": page.get("resume"),
            "total": page.get("total"),
            "has_more": bool(page.get("resume")),
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_smb_openfile_close(openfile_id: str) -> Dict[str, Any]:
    """
    Closes (forcibly terminates) an open SMB file handle by ID.

    IMPORTANT: This is a MUTATING operation. Forcibly closing a file handle
    may cause data loss if the client has unsaved changes. Use with caution.

    Use powerscale_smb_openfiles_get to list open files and retrieve their IDs
    before calling this tool.

    Arguments:
    - openfile_id: The numeric open file ID to close (from open files list)

    Returns:
    - success: True if the file handle was closed
    - message: Confirmation message
    """
    try:
        cluster = _get_reachable_cluster()
        smb = Smb(cluster)
        return smb.delete_openfile(openfile_id)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_nfs_create(
    path: str,
    access_zone: str = "System",
    description: str = None,
    clients: str = None,
    read_only: bool = None,
    # Phase 1 - Client Management
    client_state: str = None,
    read_only_clients: str = None,
    read_write_clients: str = None,
    root_clients: str = None,
    # Phase 2 - Security & Configuration
    security_flavors: str = None,
    sub_directories_mountable: bool = None,
    # Phase 3 - Root Mapping
    map_root: str = None,
    # Phase 4 - Advanced Features
    map_non_root: str = None,
    ignore_unresolvable_hosts: bool = None
) -> dict:
    """
    Create an NFS export on the PowerScale cluster with comprehensive configuration options.

    IMPORTANT: This is a MUTATING operation that creates a new NFS export on the
    live cluster. Always confirm the path and access settings with the user before
    calling this tool (e.g. "Create NFS export for /ifs/data/projects in access
    zone System?").

    This tool uses Ansible automation to create the export via the
    dellemc.powerscale collection.

    BASIC ARGUMENTS:
    - path: The filesystem path to export (e.g. "/ifs/data/projects") [REQUIRED]
    - access_zone: The access zone for the export (default: "System")
    - description: Optional human-readable description

    CLIENT ACCESS CONTROL (Basic):
    - clients: Comma-separated list of client hostnames or IPs allowed basic access
      (e.g. "10.0.0.1,10.0.0.2,client.example.com"). Access type determined by
      read_only parameter.
    - read_only: If True, the export is read-only. If omitted, defaults to read-write.

    CLIENT ACCESS CONTROL (Advanced - Phase 1):
    - client_state: Control client list behavior - "present-in-export" or "absent-in-export"
    - read_only_clients: Comma-separated list of clients with read-only access
      (e.g. "10.0.0.0/24,readonly-server.example.com")
    - read_write_clients: Comma-separated list of clients with read-write access
      (e.g. "10.0.1.0/24,app-server.example.com")
    - root_clients: Comma-separated list of clients with root access (no root squashing)
      (e.g. "10.0.2.10,trusted-server.example.com")

    CLIENT PARAMETER VALIDATION:
    Valid client formats: IP addresses (192.168.1.100), CIDR notation (192.168.0.0/24),
    or DNS hostnames (nfs-server.example.com). Clients will be validated before export creation.
    Common mistakes: mixing IP/CIDR incorrectly (e.g., 192.168.1.0/32 is single host not subnet),
    unresolvable hostnames, empty client lists. Use ignore_unresolvable_hosts=true to suppress
    hostname resolution errors if using dynamic DNS or wildcard patterns.

    SECURITY & CONFIGURATION (Phase 2):
    - security_flavors: Comma-separated list of authentication types. Options:
      "unix" (standard UNIX auth), "krb5" (Kerberos 5), "krb5i" (Kerberos with integrity),
      "krb5p" (Kerberos with privacy/encryption). Example: "unix,krb5p"
    - sub_directories_mountable: If True, clients can mount subdirectories of the export path

    USER MAPPING (Phase 3 & 4):
    - map_root: JSON string for root user mapping configuration. Example:
      '{"enabled": true, "user": "nobody", "primary_group": "nobody"}'
      Fields: enabled (bool), user (str), primary_group (str), secondary_groups (list of
      {"name": str, "state": str})
    - map_non_root: JSON string for non-root user mapping. Same structure as map_root.

    ADVANCED OPTIONS (Phase 4):
    - ignore_unresolvable_hosts: If True, suppress errors for client hostnames that
      cannot be resolved via DNS

    COMMON USE CASES:

    1. Basic read-write export for trusted network:
       path="/ifs/data", read_write_clients="10.0.0.0/24"

    2. Mixed permissions (some RO, some RW, one root):
       path="/ifs/shared", read_only_clients="10.0.1.0/24",
       read_write_clients="10.0.2.0/24", root_clients="10.0.2.10"

    3. Kerberos-secured export with root squashing:
       path="/ifs/secure", security_flavors="krb5p",
       map_root='{"enabled": true, "user": "nobody", "primary_group": "nobody"}'

    4. Application export with subdirectory mounting:
       path="/ifs/apps", sub_directories_mountable=true,
       read_write_clients="app-servers.example.com"

    Returns:
    - success: Boolean indicating if the export was created
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        nfs = Nfs(cluster)

        # Parse basic client list
        clients_list = [c.strip() for c in clients.split(",")] if clients else None

        # Parse Phase 1 - Client Management lists
        read_only_clients_list = [c.strip() for c in read_only_clients.split(",")] if read_only_clients else None
        read_write_clients_list = [c.strip() for c in read_write_clients.split(",")] if read_write_clients else None
        root_clients_list = [c.strip() for c in root_clients.split(",")] if root_clients else None

        # Parse Phase 2 - Security flavors list
        security_flavors_list = [f.strip() for f in security_flavors.split(",")] if security_flavors else None

        # Parse Phase 3 & 4 - User mapping JSON
        map_root_dict = json.loads(map_root) if map_root else None
        map_non_root_dict = json.loads(map_non_root) if map_non_root else None

        return nfs.add(
            path=path,
            access_zone=access_zone,
            description=description,
            clients=clients_list,
            read_only=read_only,
            # Phase 1
            client_state=client_state,
            read_only_clients=read_only_clients_list,
            read_write_clients=read_write_clients_list,
            root_clients=root_clients_list,
            # Phase 2
            security_flavors=security_flavors_list,
            sub_directories_mountable=sub_directories_mountable,
            # Phase 3
            map_root=map_root_dict,
            # Phase 4
            map_non_root=map_non_root_dict,
            ignore_unresolvable_hosts=ignore_unresolvable_hosts
        )
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_nfs_remove(path: str, access_zone: str = "System") -> dict:
    """
    Remove an NFS export from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes an NFS export from the
    live cluster. Always confirm the path with the user before calling this tool
    (e.g. "Remove NFS export for /ifs/data/projects?"). This does NOT delete the
    underlying data — it only removes the export definition.

    Arguments:
    - path: The filesystem path of the export to remove (e.g. "/ifs/data/projects")
    - access_zone: The access zone the export belongs to (default: "System")

    Use this tool when the user wants to:
    - Remove or delete an NFS export
    - Stop sharing a directory over NFS
    - Unshare a path from NFS clients

    Returns:
    - success: Boolean indicating if the export was removed
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        nfs = Nfs(cluster)
        return nfs.remove(path=path, access_zone=access_zone)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_nfs_global_settings_get() -> dict:
    """
    Retrieve the current NFS global settings from the PowerScale cluster.

    Returns the cluster-wide NFS configuration including service status,
    protocol version support, and performance tuning.

    Key fields in the response:
    - service: Whether the NFS service is enabled
    - nfsv3_enabled: Whether NFSv3 protocol is enabled
    - nfsv4_enabled: Whether NFSv4 protocol is enabled
    - nfsv40_enabled: Whether NFSv4.0 is enabled
    - nfsv41_enabled: Whether NFSv4.1 is enabled
    - nfsv42_enabled: Whether NFSv4.2 is enabled
    - rpc_maxthreads: Maximum nfsd thread pool threads
    - rpc_minthreads: Minimum nfsd thread pool threads
    - rquota_enabled: Whether rquota protocol is enabled

    Use this tool to:
    - Check if the NFS service is enabled or disabled
    - See which NFS protocol versions are enabled (v3, v4, v4.0, v4.1, v4.2)
    - Review NFS performance configuration (thread pools)
    - Check RDMA and rquota status
    """
    try:
        cluster = _get_reachable_cluster()
        nfs = Nfs(cluster)
        return nfs.get_global_settings()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_nfs_global_settings_set(
    service: bool = None,
    nfsv3_enabled: bool = None,
    nfsv3_rdma_enabled: bool = None,
    nfsv4_enabled: bool = None,
    nfsv40_enabled: bool = None,
    nfsv41_enabled: bool = None,
    nfsv42_enabled: bool = None,
    rpc_maxthreads: int = None,
    rpc_minthreads: int = None,
    rquota_enabled: bool = None,
    nfs_rdma_enabled: bool = None,
) -> dict:
    """
    Update NFS global settings on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that changes cluster-wide NFS
    configuration. Always confirm the intended changes with the user before
    calling this tool. Only pass the parameters you want to change — omitted
    parameters are left at their current values.

    Arguments:
    - service: Enable (true) or disable (false) the NFS service entirely
    - nfsv3_enabled: Enable/disable NFSv3 protocol
    - nfsv3_rdma_enabled: Enable/disable RDMA for NFSv3
    - nfsv4_enabled: Enable/disable all minor versions of NFSv4
    - nfsv40_enabled: Enable/disable NFSv4.0
    - nfsv41_enabled: Enable/disable NFSv4.1
    - nfsv42_enabled: Enable/disable NFSv4.2
    - rpc_maxthreads: Maximum number of threads in the nfsd thread pool
    - rpc_minthreads: Minimum number of threads in the nfsd thread pool
    - rquota_enabled: Enable/disable the rquota protocol
    - nfs_rdma_enabled: Enable/disable RDMA for NFS (PowerScale 9.8+)

    Use this tool to:
    - Enable or disable the NFS service
    - Control which NFS protocol versions are enabled (v3, v4.0, v4.1, v4.2)
    - Tune NFS thread pool sizes
    - Enable or disable RDMA and rquota
    """
    try:
        cluster = _get_reachable_cluster()
        nfs = Nfs(cluster)

        # Build nfsv3 dict if any v3 params are set
        nfsv3 = None
        if nfsv3_enabled is not None or nfsv3_rdma_enabled is not None:
            nfsv3 = {}
            if nfsv3_enabled is not None:
                nfsv3["nfsv3_enabled"] = nfsv3_enabled
            if nfsv3_rdma_enabled is not None:
                nfsv3["nfsv3_rdma_enabled"] = nfsv3_rdma_enabled

        # Build nfsv4 dict if any v4 params are set
        nfsv4 = None
        if any(v is not None for v in [nfsv4_enabled, nfsv40_enabled, nfsv41_enabled, nfsv42_enabled]):
            nfsv4 = {}
            if nfsv4_enabled is not None:
                nfsv4["nfsv4_enabled"] = nfsv4_enabled
            if nfsv40_enabled is not None:
                nfsv4["nfsv40_enabled"] = nfsv40_enabled
            if nfsv41_enabled is not None:
                nfsv4["nfsv41_enabled"] = nfsv41_enabled
            if nfsv42_enabled is not None:
                nfsv4["nfsv42_enabled"] = nfsv42_enabled

        return nfs.set_global_settings(
            service=service,
            nfsv3=nfsv3,
            nfsv4=nfsv4,
            rpc_maxthreads=rpc_maxthreads,
            rpc_minthreads=rpc_minthreads,
            rquota_enabled=rquota_enabled,
            nfs_rdma_enabled=nfs_rdma_enabled,
        )
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_s3_create(s3_bucket_name: str, path: str, owner: str = "root",
                         description: str = None, create_path: bool = None) -> dict:
    """
    Create an S3 bucket on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new S3 bucket on the
    live cluster. Always confirm the bucket name, path, and owner with the user
    before calling this tool (e.g. "Create S3 bucket 'data-lake' at
    /ifs/data/s3/data-lake owned by root?").

    This tool uses Ansible automation to create the bucket via the
    dellemc.powerscale collection.

    Arguments:
    - s3_bucket_name: The name for the S3 bucket (e.g. "data-lake")
    - path: The filesystem path the bucket maps to (e.g. "/ifs/data/s3/data-lake")
    - owner: The bucket owner (default: "root")
    - description: Optional human-readable description
    - create_path: If True, create the filesystem path if it does not exist

    Use this tool when the user wants to:
    - Create a new S3 bucket on PowerScale
    - Enable S3 object access to a filesystem path
    - Set up S3-compatible storage

    Returns:
    - success: Boolean indicating if the bucket was created
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        s3 = S3(cluster)
        return s3.add(s3_bucket_name=s3_bucket_name, path=path, owner=owner,
                      description=description, create_path=create_path)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_s3_remove(s3_bucket_name: str) -> dict:
    """
    Remove an S3 bucket from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes an S3 bucket from the
    live cluster. Always confirm the bucket name with the user before calling
    this tool (e.g. "Remove S3 bucket 'data-lake'?"). This does NOT delete the
    underlying data on the filesystem — it only removes the bucket definition.

    Arguments:
    - s3_bucket_name: The name of the S3 bucket to remove (e.g. "data-lake")

    Use this tool when the user wants to:
    - Remove or delete an S3 bucket
    - Disable S3 access to a filesystem path
    - Clean up unused S3 buckets

    Returns:
    - success: Boolean indicating if the bucket was removed
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        s3 = S3(cluster)
        return s3.remove(s3_bucket_name=s3_bucket_name)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_snapshot_schedule_create(name: str, path: str, schedule: str,
                                        pattern: str = None, duration: str = None,
                                        alias: str = None) -> dict:
    """
    Create a snapshot schedule on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new snapshot schedule
    on the live cluster. Always confirm the schedule name, path, and frequency
    with the user before calling this tool (e.g. "Create snapshot schedule
    'daily-backup' for /ifs/data/projects running every day at midnight?").

    This tool uses Ansible automation to create the schedule via the
    dellemc.powerscale collection.

    Arguments:
    - name: The name of the snapshot schedule (e.g. "daily-backup")
    - path: The filesystem path to snapshot (e.g. "/ifs/data/projects")
    - schedule: The schedule in PowerScale isidate format: "<interval> [<frequency>]"

      The interval specifies WHICH days, and the optional frequency specifies
      WHEN or HOW OFTEN within those days.

      Interval formats:
      - "Every [{other | <N>}] {weekday | day}"
      - "Every [{other | <N>}] week [on <day>]"
      - "Every [{other | <N>}] month [on the <N>]"
      - "Every [<day>[, ...] [of every [{other | <N>}] week]]"
      - "The last {day | weekday | <day>} of every [{other | <N>}] month"
      - "The <N> {weekday | <day>} of every [{other | <N>}] month"
      - "Yearly on <month> <N>"
      - "Yearly on the {last | <N>} [weekday | <day>] of <month>"

      Frequency formats (appended after interval):
      - "at <hh>[:<mm>] [{AM | PM}]"
      - "every [<N>] {hours | minutes} [between <hh> [{AM|PM}] and <hh> [{AM|PM}]]"
      - "every [<N>] {hours | minutes} [from <hh> [{AM|PM}] to <hh> [{AM|PM}]]"

      Examples:
      - "Every day at 12:00 AM"              (daily at midnight)
      - "Every day every 4 hours"            (every 4 hours, every day)
      - "Every day every 30 minutes"         (every 30 min, every day)
      - "Every Monday at 2:00 AM"            (weekly on Monday)
      - "Every other day at 6:00 PM"         (every 2 days at 6 PM)
      - "Every day every 1 hours between 8:00 AM and 6:00 PM"  (hourly during business hours)
      - "Every 2 weeks on Monday at 3:00 AM" (biweekly)
      - "Every month on the 1 at 1:00 AM"    (monthly on the 1st)

      IMPORTANT: For hourly/minute schedules you MUST include the day interval
      (e.g. "Every day") before the frequency (e.g. "every 4 hours").
      "Every 4 hours" alone is NOT valid — use "Every day every 4 hours".

    - pattern: Snapshot naming pattern (default: "{name}_%Y-%m-%d_%H:%M").
      Use strftime format codes for timestamps.
    - duration: Retention period for snapshots (e.g. "7" for 7 days)
    - alias: Optional alias for the latest snapshot in this schedule

    Use this tool when the user wants to:
    - Create a scheduled snapshot policy
    - Set up automated backups/snapshots for a path
    - Configure periodic point-in-time snapshots

    Returns:
    - success: Boolean indicating if the schedule was created
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        schedules = SnapshotSchedules(cluster)
        desired_retention = int(duration) if duration else None
        return schedules.add(name=name, path=path, schedule=schedule,
                             pattern=pattern, desired_retention=desired_retention,
                             alias=alias)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_snapshot_schedule_remove(name: str) -> dict:
    """
    Remove a snapshot schedule from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes a snapshot schedule from
    the live cluster. Always confirm the schedule name with the user before
    calling this tool (e.g. "Remove snapshot schedule 'daily-backup'?"). This
    does NOT delete existing snapshots — it only removes the schedule so no new
    snapshots will be created.

    Arguments:
    - name: The name of the snapshot schedule to remove (e.g. "daily-backup")

    Use this tool when the user wants to:
    - Remove or delete a snapshot schedule
    - Stop automated snapshots for a path
    - Disable a snapshot policy

    Returns:
    - success: Boolean indicating if the schedule was removed
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        schedules = SnapshotSchedules(cluster)
        return schedules.remove(name=name)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_snapshot_create(path: str, snapshot_name: str = None, alias: str = None,
                                desired_retention: int = None, retention_unit: str = "hours",
                                expiration_timestamp: str = None) -> dict:
    """
    Create a manual snapshot on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new snapshot on the live
    cluster. Always confirm the path and snapshot name with the user before calling
    this tool (e.g. "Create snapshot of /ifs/data/projects with name 'pre-upgrade'?").

    This tool uses Ansible automation to create the snapshot via the
    dellemc.powerscale collection. Snapshots provide point-in-time protection and can
    be used for recovery, testing, or backup purposes.

    Arguments:
    - path: The filesystem path to snapshot (e.g. "/ifs/data/projects"). Must exist
      on the cluster.
    - snapshot_name: Optional name for the snapshot. If omitted, a name will be
      auto-generated based on the path.
    - alias: Optional human-friendly alias to create for this snapshot. Aliases make
      it easier to reference snapshots without using generated names.
    - desired_retention: Optional retention period as an integer (e.g. 7 for 7 hours/days/weeks).
      Snapshots older than this will be automatically deleted.
    - retention_unit: Unit for retention period. Options: "hours", "days", "weeks".
      Default is "hours".
    - expiration_timestamp: Optional UTC expiration timestamp (mutually exclusive with
      desired_retention). Format: "2024-12-31 23:59:59"

    Use this tool when the user wants to:
    - Create a one-time snapshot before risky operations (upgrades, migrations, etc.)
    - Take a manual backup outside of scheduled snapshots
    - Create a point-in-time snapshot for testing or recovery
    - Snapshot a specific directory or path immediately

    Returns:
    - success: Boolean indicating if the snapshot was created
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        snapshots = Snapshots(cluster)
        return snapshots.create(path=path, snapshot_name=snapshot_name, alias=alias,
                               desired_retention=desired_retention,
                               retention_unit=retention_unit,
                               expiration_timestamp=expiration_timestamp)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_snapshot_delete(snapshot_name: str) -> dict:
    """
    Delete a snapshot from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes a snapshot from the live
    cluster. Always confirm the snapshot name with the user before calling this tool
    (e.g. "Delete snapshot 'pre-upgrade'?"). Deleted snapshots enter a deleting state
    until the system can reclaim the space used. This operation CANNOT be undone.

    This tool uses Ansible automation to delete the snapshot via the
    dellemc.powerscale collection.

    Arguments:
    - snapshot_name: The name or ID of the snapshot to delete (e.g. "pre-upgrade",
      "ScheduleName_2024-01-15_10:30")

    Use this tool when the user wants to:
    - Remove old or unused snapshots
    - Free up snapshot reserve space
    - Clean up test snapshots
    - Delete snapshots manually outside of retention policies

    Returns:
    - success: Boolean indicating if the snapshot was deleted
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        snapshots = Snapshots(cluster)
        return snapshots.delete(snapshot_name=snapshot_name)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_snapshot_pending_get(begin: int = None, end: int = None,
                                    schedule: str = None, limit: int = 1000,
                                    resume: str = None) -> Dict[str, Any]:
    """
    Return a list of snapshots scheduled to be created in the future.

    This tool queries the cluster to show which snapshots will be taken based on
    configured snapshot schedules. It's useful for verifying schedule configuration
    and predicting upcoming snapshot activity.

    Usage (pagination):
    - First call: use resume=None (or omit it)
    - If the response contains a non-null "resume" value, call again passing
      that value as the resume argument to fetch the next page
    - Continue until "resume" is None (has_more will be False)

    Arguments:
    - begin: Optional Unix epoch time to start listing pending snapshots (default: now).
      Only snapshots scheduled after this time will be returned.
    - end: Optional Unix epoch time to stop listing pending snapshots (default: forever).
      Only snapshots scheduled before this time will be returned.
    - schedule: Optional schedule name to filter by. If specified, only pending
      snapshots for that specific schedule will be returned.
    - limit: Maximum number of pending snapshots to return per page (default: 1000)
    - resume: Resume token from a previous call (or None for first call)

    Each pending snapshot object includes:
    - snapshot: The name that will be assigned to the snapshot
    - path: The filesystem path that will be snapshotted
    - time: Unix epoch timestamp when the snapshot will be created
    - schedule: The schedule name that will create this snapshot

    Use this tool to answer questions such as:
    - What snapshots will be created soon?
    - When is the next snapshot scheduled for a specific path?
    - Is my snapshot schedule working correctly?
    - How many snapshots will be created in the next 24 hours?
    - What schedule is responsible for upcoming snapshots?

    Returns:
    - items: List of pending snapshot objects for this page
    - resume: Resume token for the next page, or None if finished
    - has_more: True if more pages exist
    """
    try:
        # Normalize resume in case LLM sends "null"
        resume = None if resume in (None, "null", "None") else resume

        cluster = _get_reachable_cluster()
        snapshots = Snapshots(cluster)

        page = snapshots.get_pending(begin=begin, end=end, schedule=schedule,
                                     limit=limit, resume=resume)

        items = page.get("items") or []
        resume_token = page.get("resume")

        return {
            "items": items,
            "resume": resume_token,
            "limit": limit,
            "has_more": bool(resume_token)
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_snapshot_alias_create(name: str, target: str) -> dict:
    """
    Create an alias pointing to an existing snapshot.

    IMPORTANT: This is a MUTATING operation that creates a new snapshot alias on
    the live cluster. Always confirm the alias name and target snapshot with the
    user before calling this tool (e.g. "Create alias 'production-stable' pointing
    to snapshot 'pre-upgrade-2024-01-15'?").

    Snapshot aliases provide human-friendly names that point to specific snapshots.
    They make it easier to reference important snapshots without remembering
    auto-generated names or timestamps. Aliases are especially useful for marking
    known-good states or important milestones.

    Arguments:
    - name: The alias name to create (e.g. "production-stable", "last-good-config")
    - target: The snapshot name or ID to point the alias to (e.g. "pre-upgrade-2024-01-15")

    Use this tool when the user wants to:
    - Create a memorable name for an important snapshot
    - Mark a snapshot as a known-good state
    - Make it easier to reference a specific snapshot for recovery
    - Tag snapshots with meaningful names (e.g. "before-migration", "quarterly-backup")

    Returns:
    - success: Boolean indicating if the alias was created
    - message: Confirmation message
    - id: The alias ID if available
    """
    try:
        cluster = _get_reachable_cluster()
        snapshots = Snapshots(cluster)
        return snapshots.create_alias(name=name, target=target)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_snapshot_alias_get(alias_id: str) -> dict:
    """
    Get information about a snapshot alias.

    This tool retrieves details about a specific snapshot alias, including what
    snapshot it points to and when it was created.

    Arguments:
    - alias_id: The alias name or ID to retrieve information about
      (e.g. "production-stable", "last-good-config")

    The alias object includes details such as:
    - name: The alias name
    - target: The snapshot name or ID the alias points to
    - created: When the alias was created (if available)

    Use this tool when the user wants to:
    - Find out which snapshot an alias points to
    - Verify an alias exists and is configured correctly
    - Get details about a specific alias
    - Check when an alias was created

    Returns:
    - success: Boolean indicating if the alias was found
    - alias: Dictionary with alias details (name, target, etc.)
    - error: Error message if the alias was not found
    """
    try:
        cluster = _get_reachable_cluster()
        snapshots = Snapshots(cluster)
        return snapshots.get_alias(alias_id=alias_id)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_synciq_create(policy_name: str, source_path: str,
                              target_host: str, target_path: str,
                              action: str = "sync", schedule: str = None,
                              description: str = None, enabled: bool = None) -> dict:
    """
    Create a SyncIQ replication policy on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new replication policy
    on the live cluster. Always confirm all parameters with the user before
    calling this tool (e.g. "Create SyncIQ policy 'dr-repl' to replicate
    /ifs/data/projects to target-cluster.example.com:/ifs/data/projects-replica?").

    SyncIQ policies define replication relationships between source and target
    clusters. Once created, the policy can be run manually or on a schedule.

    This tool uses Ansible automation to create the policy via the
    dellemc.powerscale collection.

    Arguments:
    - policy_name: The name of the replication policy (e.g. "dr-repl")
    - source_path: The source directory to replicate (e.g. "/ifs/data/projects")
    - target_host: The target cluster hostname or IP (e.g. "target-cluster.example.com")
    - target_path: The target directory path (e.g. "/ifs/data/projects-replica")
    - action: The replication action - "sync" (default) or "copy"
    - schedule: Optional schedule (e.g. "Every day at 2:00 AM")
    - description: Optional human-readable description
    - enabled: Whether the policy should be enabled immediately (default: True)

    Use this tool when the user wants to:
    - Create a new replication policy between clusters
    - Set up disaster recovery replication
    - Configure data mirroring to a remote cluster

    Returns:
    - success: Boolean indicating if the policy was created
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        synciq = SyncIQ(cluster)
        return synciq.add(policy_name=policy_name, source_path=source_path,
                          target_host=target_host, target_path=target_path,
                          action=action, schedule=schedule, description=description,
                          enabled=enabled)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_synciq_remove(policy_name: str) -> dict:
    """
    Remove a SyncIQ replication policy from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes a replication policy
    from the live cluster. Always confirm the policy name with the user before
    calling this tool (e.g. "Remove SyncIQ policy 'dr-repl'?"). This stops
    future replication jobs but does NOT delete data on the source or target.

    Arguments:
    - policy_name: The name of the SyncIQ policy to remove (e.g. "dr-repl")

    Use this tool when the user wants to:
    - Remove or delete a replication policy
    - Stop replication between clusters
    - Clean up an old or unused SyncIQ policy

    Returns:
    - success: Boolean indicating if the policy was removed
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        synciq = SyncIQ(cluster)
        return synciq.remove(policy_name=policy_name)
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# DataMover Policy Management Tools
# ============================================================================

@mcp.tool()
def powerscale_datamover_policy_get(limit: int = 1000, resume: str = None) -> Dict[str, Any]:
    """
    Returns a paginated list of DataMover policies on the PowerScale cluster.

    DataMover provides data movement capabilities for migrating, copying, or
    replicating data within or between PowerScale clusters. Each policy defines
    the source, destination, schedule, and other parameters for data movement jobs.

    Arguments:
    - limit: Maximum number of policies to return (default 1000)
    - resume: Resume token from previous call for pagination (optional)

    Use this tool when the user wants to:
    - List all DataMover policies
    - See what data movement jobs are configured
    - Check policy configurations before creating a new one
    - Browse existing policies for reference

    Returns:
    - items: List of DataMover policy objects with full details
    - resume: Token for fetching the next page (None if last page)

    Note: If there are many policies, use the resume token to page through results.
    For example, after the first call returns a resume token, call again with that
    token to get the next batch of results.
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        # Normalize resume token (handle "null", "None", None)
        resume = None if resume in (None, "null", "None") else resume
        return datamover.get_policies(limit=limit, resume=resume)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_datamover_policy_get_by_id(policy_id: str) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific DataMover policy by ID or name.

    Use this tool to get complete configuration details for a single DataMover policy,
    including source/destination paths, schedule, priority, enabled status, and all
    policy-specific attributes.

    Arguments:
    - policy_id: The policy name or ID to retrieve (e.g. "data-migration-policy" or "12345")

    Use this tool when the user wants to:
    - View detailed configuration of a specific policy
    - Check settings before modifying a policy
    - Verify policy parameters after creation
    - Inspect a policy mentioned by name

    Returns:
    - success: Boolean indicating if the operation succeeded
    - policy: Complete policy object with all configuration details
    - error: Error message if the operation failed
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        return datamover.get_policy(policy_id=policy_id)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_datamover_policy_create(name: str, base_policy_id: int = None,
                                       enabled: bool = None, priority: str = None,
                                       run_now: bool = None, schedule: str = None) -> dict:
    """
    Create a new DataMover policy on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new data movement policy
    on the live cluster. Always confirm the policy name and configuration with the user
    before calling this tool (e.g. "Create DataMover policy 'archive-old-data' with
    base_policy_id 1?").

    Arguments:
    - name: A user-provided policy name (required, e.g. "archive-old-data")
    - base_policy_id: The unique base policy identifier to use as a template (optional)
    - enabled: True to enable the policy immediately, False to create it disabled (optional)
    - priority: The relative priority of the policy, e.g. "high", "medium", "low" (optional)
    - run_now: Execute the policy immediately instead of waiting for schedule (optional, default False)
    - schedule: The schedule for the policy - start time, recurrence, etc. (optional)

    Use this tool when the user wants to:
    - Create a new data movement policy
    - Set up automated data migration or archival
    - Configure data replication or copying between paths
    - Establish a new data movement job

    Returns:
    - success: Boolean indicating if the policy was created
    - message: Success or error message
    - id: The ID of the newly created policy (if successful)

    Note: DataMover policies require a base policy to define the data movement operation.
    Use base_policy_id to reference an existing base policy, or the policy may use defaults.
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        return datamover.create_policy(name=name, base_policy_id=base_policy_id,
                                       enabled=enabled, priority=priority,
                                       run_now=run_now, schedule=schedule)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_datamover_policy_delete(policy_id: str) -> dict:
    """
    Delete a DataMover policy from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that permanently removes a data movement
    policy from the live cluster. Always confirm the policy ID/name with the user before
    calling this tool (e.g. "Delete DataMover policy 'archive-old-data'?"). This stops
    future data movement jobs but does NOT affect data that has already been moved.

    Arguments:
    - policy_id: The name or ID of the DataMover policy to delete (e.g. "archive-old-data" or "12345")

    Use this tool when the user wants to:
    - Remove or delete a data movement policy
    - Stop a DataMover policy that is no longer needed
    - Clean up an old or unused policy
    - Disable data movement operations permanently

    Returns:
    - success: Boolean indicating if the policy was deleted
    - message: Success or error message
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        return datamover.delete_policy(policy_id=policy_id)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_datamover_policy_last_job(policy_id: str) -> dict:
    """
    Retrieve the last job information for a specific DataMover policy.

    Use this tool to get details about the most recent execution of a DataMover policy,
    including the job ID and last execution timestamp. This helps track policy execution
    history and troubleshoot issues with data movement jobs.

    Arguments:
    - policy_id: The policy name or ID to query (e.g. "archive-old-data" or "12345")

    Use this tool when the user wants to:
    - Check when a policy last ran
    - Get the job ID for the most recent execution
    - Verify that a policy is executing as expected
    - Troubleshoot policy execution issues
    - Track data movement job history

    Returns:
    - success: Boolean indicating if the operation succeeded
    - last_job: Object containing job ID and execution timestamp
    - error: Error message if the operation failed
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        return datamover.get_policy_last_job(policy_id=policy_id)
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# DataMover Account Management Tools
# ============================================================================

@mcp.tool()
def powerscale_datamover_account_get(limit: int = 1000, resume: str = None) -> Dict[str, Any]:
    """
    Returns a paginated list of DataMover accounts on the PowerScale cluster.

    DataMover accounts represent connections to data storage locations (local paths,
    NFS exports, S3 buckets, etc.) that can be used as sources or targets for data
    movement operations. Each account contains connection details, credentials, and
    configuration for a specific storage location.

    Arguments:
    - limit: Maximum number of accounts to return (default 1000)
    - resume: Resume token from previous call for pagination (optional)

    Use this tool when the user wants to:
    - List all DataMover accounts
    - See what storage locations are configured for data movement
    - Check account configurations before creating policies
    - Browse existing accounts for reference

    Returns:
    - items: List of DataMover account objects with full details
    - resume: Token for fetching the next page (None if last page)
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        # Normalize resume token (handle "null", "None", None)
        resume = None if resume in (None, "null", "None") else resume
        return datamover.get_accounts(limit=limit, resume=resume)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_datamover_account_get_by_id(account_id: str) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific DataMover account by ID or name.

    Use this tool to get complete configuration details for a single DataMover account,
    including storage type, URI, credentials, network restrictions, and all account-specific
    settings.

    Arguments:
    - account_id: The account name or ID to retrieve (e.g. "s3-archive" or "12345")

    Use this tool when the user wants to:
    - View detailed configuration of a specific account
    - Check account settings before using in a policy
    - Verify account parameters after creation
    - Inspect an account mentioned by name

    Returns:
    - success: Boolean indicating if the operation succeeded
    - account: Complete account object with all configuration details
    - error: Error message if the operation failed
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        return datamover.get_account(account_id=account_id)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_datamover_account_create(name: str, account_type: str, uri: str,
                                        briefcase: str = None, enforce_sse: bool = None,
                                        local_network_pool: str = None, max_sparks: int = None,
                                        remote_network_pool: str = None, storage_class: str = None) -> dict:
    """
    Create a new DataMover account on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new data storage account
    on the live cluster. Always confirm the account name and configuration with the user
    before calling this tool (e.g. "Create DataMover account 's3-archive' pointing to
    s3://mybucket?").

    Arguments:
    - name: Name for this DataMover account (required, e.g. "s3-archive")
    - account_type: Type of data storage (required, e.g. "s3", "nfs", "local")
    - uri: Valid URI pointing to the data storage (required, e.g. "s3://bucket-name")
    - briefcase: Opaque container for additional key-value data (optional)
    - enforce_sse: Enforce Server-Side Encryption for AWS S3 (optional, default False)
    - local_network_pool: Local network restriction for connections (optional)
    - max_sparks: Limit of concurrent tasks per node (optional)
    - remote_network_pool: Remote network restriction for connections (optional)
    - storage_class: Storage class for cloud accounts (optional, e.g. "STANDARD", "GLACIER")

    Use this tool when the user wants to:
    - Create a new data storage account
    - Configure access to S3, NFS, or local storage
    - Set up source or target locations for data movement
    - Establish credentials for external storage

    Returns:
    - success: Boolean indicating if the account was created
    - message: Success or error message
    - id: The ID of the newly created account (if successful)

    Note: Credentials should be configured separately or passed via the briefcase parameter.
    Different account types (S3, NFS, local) have different URI formats and requirements.
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        return datamover.create_account(name=name, account_type=account_type, uri=uri,
                                        briefcase=briefcase, enforce_sse=enforce_sse,
                                        local_network_pool=local_network_pool,
                                        max_sparks=max_sparks,
                                        remote_network_pool=remote_network_pool,
                                        storage_class=storage_class)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_datamover_account_delete(account_id: str) -> dict:
    """
    Delete a DataMover account from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that permanently removes a data storage
    account from the live cluster. Always confirm the account ID/name with the user before
    calling this tool (e.g. "Delete DataMover account 's3-archive'?"). This removes the
    account configuration but does NOT affect data in the storage location itself.

    Arguments:
    - account_id: The name or ID of the DataMover account to delete (e.g. "s3-archive" or "12345")

    Use this tool when the user wants to:
    - Remove or delete a storage account
    - Clean up an old or unused account
    - Decommission access to a storage location
    - Remove account configurations

    Returns:
    - success: Boolean indicating if the account was deleted
    - message: Success or error message

    Warning: Deleting an account that is referenced by existing policies will cause those
    policies to fail. Always check policy dependencies before deleting accounts.
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        return datamover.delete_account(account_id=account_id)
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# DataMover Base Policy Management Tools
# ============================================================================

@mcp.tool()
def powerscale_datamover_base_policy_get(limit: int = 1000, resume: str = None) -> Dict[str, Any]:
    """
    Returns a paginated list of DataMover base policies on the PowerScale cluster.

    Base policies serve as templates for creating concrete data movement policies.
    They define common configurations like source/target accounts, paths, schedules,
    and retention settings that can be reused across multiple policies. Regular policies
    can inherit from base policies to simplify configuration and maintain consistency.

    Arguments:
    - limit: Maximum number of base policies to return (default 1000)
    - resume: Resume token from previous call for pagination (optional)

    Use this tool when the user wants to:
    - List all DataMover base policies
    - See available policy templates
    - Check base policy configurations before creating concrete policies
    - Browse existing base policies for reference

    Returns:
    - items: List of DataMover base policy objects with full details
    - resume: Token for fetching the next page (None if last page)
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        # Normalize resume token (handle "null", "None", None)
        resume = None if resume in (None, "null", "None") else resume
        return datamover.get_base_policies(limit=limit, resume=resume)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_datamover_base_policy_get_by_id(base_policy_id: str) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific DataMover base policy by ID or name.

    Use this tool to get complete configuration details for a single DataMover base policy,
    including source/target accounts, paths, schedules, retention settings, and all
    template-specific attributes.

    Arguments:
    - base_policy_id: The base policy name or ID to retrieve (e.g. "s3-archive-template" or "1")

    Use this tool when the user wants to:
    - View detailed configuration of a specific base policy
    - Check template settings before creating derived policies
    - Verify base policy parameters after creation
    - Inspect a base policy mentioned by name

    Returns:
    - success: Boolean indicating if the operation succeeded
    - base_policy: Complete base policy object with all configuration details
    - error: Error message if the operation failed
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        return datamover.get_base_policy(base_policy_id=base_policy_id)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_datamover_base_policy_create(name: str, enabled: bool = None, priority: str = None,
                                            source_account_id: str = None, source_base_path: str = None,
                                            target_account_id: str = None, target_base_path: str = None) -> dict:
    """
    Create a new DataMover base policy on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new base policy template
    on the live cluster. Always confirm the base policy name and configuration with the user
    before calling this tool (e.g. "Create DataMover base policy 's3-archive-template'
    from account 'local-data' to 's3-archive'?").

    Arguments:
    - name: A user-provided base policy name (required, e.g. "s3-archive-template")
    - enabled: True to enable the base policy, False otherwise (optional)
    - priority: The relative priority (optional, e.g. "high", "medium", "low")
    - source_account_id: Source data storage account ID or name (optional)
    - source_base_path: Filesystem base path on source (optional, e.g. "/ifs/data")
    - target_account_id: Destination data storage account ID or name (optional)
    - target_base_path: Filesystem base path on target (optional, e.g. "/archive")

    Use this tool when the user wants to:
    - Create a new base policy template
    - Define common data movement configurations
    - Set up reusable policy templates
    - Establish standard source/target patterns

    Returns:
    - success: Boolean indicating if the base policy was created
    - message: Success or error message
    - id: The ID of the newly created base policy (if successful)

    Note: Base policies serve as templates. Create concrete policies that reference
    the base policy ID to inherit its configuration.
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        return datamover.create_base_policy(name=name, enabled=enabled, priority=priority,
                                           source_account_id=source_account_id,
                                           source_base_path=source_base_path,
                                           target_account_id=target_account_id,
                                           target_base_path=target_base_path)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_datamover_base_policy_delete(base_policy_id: str) -> dict:
    """
    Delete a DataMover base policy from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that permanently removes a base policy
    template from the live cluster. Always confirm the base policy ID/name with the user
    before calling this tool (e.g. "Delete DataMover base policy 's3-archive-template'?").
    This removes the template but does NOT affect concrete policies that were created
    from it.

    Arguments:
    - base_policy_id: The name or ID of the base policy to delete (e.g. "s3-archive-template" or "1")

    Use this tool when the user wants to:
    - Remove or delete a base policy template
    - Clean up an old or unused template
    - Remove deprecated policy configurations
    - Decommission policy templates

    Returns:
    - success: Boolean indicating if the base policy was deleted
    - message: Success or error message

    Warning: Ensure no active policies are depending on this base policy before deletion.
    Deleting a base policy that is referenced by existing policies may cause issues.
    """
    try:
        cluster = _get_reachable_cluster()
        datamover = DataMover(cluster)
        return datamover.delete_base_policy(base_policy_id=base_policy_id)
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------------------------
# FilePool policy tools
# ---------------------------------------------------------------------------

@mcp.tool()
def powerscale_filepool_policy_get() -> Dict[str, Any]:
    """
    Returns all FilePool policies on the PowerScale cluster.

    FilePool policies automate data tiering by defining file matching criteria
    (name patterns, size, age, file type) and actions (move to a storage pool,
    set protection level, set access pattern) applied to matching files.

    Unlike most list tools, FilePool policies are NOT paginated. All policies
    are returned in a single response.

    Each policy object includes:
    - id: Unique policy identifier
    - name: The policy name
    - description: Human-readable description
    - apply_order: Evaluation order relative to other policies
    - file_matching_pattern: The rules defining which files match this policy
      (nested or_criteria -> and_criteria structure)
    - actions: List of actions applied to matching files (storage pool moves,
      protection changes, access pattern settings)
    - state: Policy health state
    - state_details: Additional state information
    - birth_cluster_id: GUID of the cluster where the policy was created

    Use this tool to answer questions such as:
    - What FilePool policies are configured?
    - How is data tiering set up on the cluster?
    - Which files are being moved to which storage pools?
    - What file matching criteria are used for tiering?
    - Are any FilePool policies in a bad state?

    Returns:
    - items: List of all FilePool policy objects
    - total: Total number of policies
    """
    try:
        cluster = _get_reachable_cluster()
        filepool = FilePool(cluster)
        return filepool.get()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_filepool_policy_get_by_name(policy_id: str) -> Dict[str, Any]:
    """
    Retrieve detailed information about a specific FilePool policy by name or ID.

    Use this tool to inspect the full configuration of a single FilePool policy,
    including its file matching rules and actions.

    Arguments:
    - policy_id: The policy name or ID to retrieve (e.g. "archive-old-logs")

    Use this tool to answer questions such as:
    - What are the matching criteria for a specific policy?
    - What actions does a specific FilePool policy apply?
    - What is the apply_order of a given policy?

    Returns:
    - success: Boolean indicating if the policy was found
    - policy: Complete policy object with all configuration details
    - error: Error message if the policy was not found
    """
    try:
        cluster = _get_reachable_cluster()
        filepool = FilePool(cluster)
        return filepool.get_policy(policy_id=policy_id)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_filepool_default_policy_get() -> Dict[str, Any]:
    """
    Return the system default FilePool policy on the PowerScale cluster.

    The default policy applies to all files that do not match any custom
    FilePool policy. It defines the baseline storage pool, protection level,
    and access pattern for unclassified files.

    Use this tool to answer questions such as:
    - What is the default tiering behavior for files?
    - Where do unmatched files go?
    - What is the default protection level?

    Returns:
    - success: Boolean indicating if the operation succeeded
    - default_policy: The default policy object with actions and settings
    """
    try:
        cluster = _get_reachable_cluster()
        filepool = FilePool(cluster)
        return filepool.get_default_policy()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_filepool_policy_create(
    policy_name: str,
    file_matching_pattern: str,
    description: str = None,
    apply_order: int = None,
    apply_data_storage_policy: str = None,
    apply_snapshot_storage_policy: str = None,
    set_requested_protection: str = None,
    set_data_access_pattern: str = None,
    set_write_performance_optimization: str = None,
) -> dict:
    """
    Create a FilePool policy on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new FilePool tiering
    policy on the live cluster. Always confirm the policy name and configuration
    with the user before calling this tool.

    This tool uses Ansible automation to create the policy via the
    dellemc.powerscale collection.

    Arguments (required):
    - policy_name: A unique name for the policy (e.g. "archive-old-logs")
    - file_matching_pattern: JSON string defining the file matching rules.
      Structure: {"or_criteria": [{"and_criteria": [<criterion>, ...]}, ...]}
      Maximum 3 or_criteria groups, maximum 5 and_criteria per group.

      Each criterion is a dict with:
      - type (required): "file_name", "file_path", "file_type", "file_attribute",
        "size", "accessed", "created", "modified", or "metadata_changed"
      - condition: Comparison operator (varies by type):
        * name/path: "matches", "does_not_match", "contains", "does_not_contain"
        * file_type: "matches", "does_not_match"
        * file_attribute: "matches", "does_not_match", "exists", "does_not_exist"
        * size: "equal", "not_equal", "greater_than", "greater_than_equal_to",
          "less_than", "less_than_equal_to"
        * date types: "after", "before", "is_newer_than", "is_older_than"
      - value: Value to compare against (for name/path/attribute types)
      - case_sensitive: Boolean for name/path matching
      - file_type_option: For file_type criteria (e.g. "directory", "file", "other")
      - size_info: For size criteria: {"size_value": <int>, "size_unit": "<unit>"}
        Units: "B", "KB", "MB", "GB", "TB"
      - datetime_value: For date after/before: "YYYY-MM-DD HH:MM" format
      - relative_datetime_count: For is_newer_than/is_older_than:
        {"time_value": <int>, "time_unit": "<unit>"}
        Units: "years", "months", "weeks", "days", "hours"
      - field: For file_attribute type, the attribute field name

      Example -- match .log files larger than 1 GB not accessed in 90 days:
      '{"or_criteria": [{"and_criteria": [
        {"type": "file_name", "condition": "matches", "value": "*.log",
         "case_sensitive": false},
        {"type": "size", "condition": "greater_than",
         "size_info": {"size_value": 1, "size_unit": "GB"}},
        {"type": "accessed", "condition": "is_older_than",
         "relative_datetime_count": {"time_value": 90, "time_unit": "days"}}
      ]}]}'

    Arguments (optional -- omit to keep cluster defaults):
    - description: Human-readable description of the policy
    - apply_order: Integer ordering relative to other policies (lower = evaluated first)
    - apply_data_storage_policy: JSON string defining where to store file data.
      Format: {"ssd_strategy": "<strategy>", "storagepool": "<pool_name>"}
      ssd_strategy options: "metadata", "metadata-write", "data", "avoid"
    - apply_snapshot_storage_policy: JSON string for snapshot data storage.
      Same format as apply_data_storage_policy.
    - set_requested_protection: Protection level string. Options include:
      "default", "+1", "+2:1", "+2d:1n", "+3", "+3:1", "+3d:1n1d", "+4",
      "2x", "3x", "4x", "5x", "6x", "7x", "8x", "mirrored"
    - set_data_access_pattern: Optimization hint for data access.
      Options: "random", "concurrency", "streaming"
    - set_write_performance_optimization: Write caching strategy.
      Options: "enable_smartcache", "disable_smartcache"

    Use this tool when the user wants to:
    - Create an automated data tiering policy
    - Move old or large files to a different storage pool
    - Set protection levels based on file criteria
    - Optimize access patterns for specific file types

    Returns:
    - success: Boolean indicating if the policy was created
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        filepool = FilePool(cluster)
        return filepool.create(
            policy_name=policy_name,
            file_matching_pattern=file_matching_pattern,
            description=description,
            apply_order=apply_order,
            apply_data_storage_policy=apply_data_storage_policy,
            apply_snapshot_storage_policy=apply_snapshot_storage_policy,
            set_requested_protection=set_requested_protection,
            set_data_access_pattern=set_data_access_pattern,
            set_write_performance_optimization=set_write_performance_optimization,
        )
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_filepool_policy_update(
    policy_id: str,
    description: str = None,
    apply_order: int = None,
    file_matching_pattern: str = None,
    apply_data_storage_policy: str = None,
    apply_snapshot_storage_policy: str = None,
    set_requested_protection: str = None,
    set_data_access_pattern: str = None,
    set_write_performance_optimization: str = None,
) -> dict:
    """
    Update an existing FilePool policy on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that modifies a FilePool policy on
    the live cluster. Always confirm the policy name and the changes with the
    user before calling this tool.

    This tool uses the SDK directly because the Ansible module does not support
    policy modification. Only the fields you provide will be changed; omitted
    fields remain unchanged.

    Arguments (required):
    - policy_id: The policy name or ID to update (e.g. "archive-old-logs")

    Arguments (optional -- provide only fields to change):
    - description: New description
    - apply_order: New evaluation order
    - file_matching_pattern: JSON string with new matching rules (same format
      as powerscale_filepool_policy_create)
    - apply_data_storage_policy: JSON string with new data storage pool settings
      Format: {"ssd_strategy": "<strategy>", "storagepool": "<pool_name>"}
    - apply_snapshot_storage_policy: JSON string with new snapshot storage settings
    - set_requested_protection: New protection level string
    - set_data_access_pattern: New access pattern ("random", "concurrency", "streaming")
    - set_write_performance_optimization: New write perf setting
      ("enable_smartcache", "disable_smartcache")

    Use this tool when the user wants to:
    - Change the file matching criteria of an existing policy
    - Move a policy's target to a different storage pool
    - Change the protection level or access pattern of a policy
    - Reorder a policy relative to other policies

    Returns:
    - success: Boolean indicating if the update succeeded
    - message: Success or error message
    """
    try:
        cluster = _get_reachable_cluster()
        filepool = FilePool(cluster)
        return filepool.update(
            policy_id=policy_id,
            description=description,
            apply_order=apply_order,
            file_matching_pattern=file_matching_pattern,
            apply_data_storage_policy=apply_data_storage_policy,
            apply_snapshot_storage_policy=apply_snapshot_storage_policy,
            set_requested_protection=set_requested_protection,
            set_data_access_pattern=set_data_access_pattern,
            set_write_performance_optimization=set_write_performance_optimization,
        )
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_filepool_policy_remove(policy_name: str) -> dict:
    """
    Remove a FilePool policy from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes a FilePool tiering
    policy from the live cluster. Always confirm the policy name with the user
    before calling this tool (e.g. "Remove FilePool policy 'archive-old-logs'?").
    Files that were already tiered by this policy remain in their current
    location -- only the policy definition is removed.

    Arguments:
    - policy_name: The name of the FilePool policy to remove

    Use this tool when the user wants to:
    - Remove or delete a FilePool tiering policy
    - Stop automatic data movement for specific file criteria
    - Clean up unused tiering policies

    Returns:
    - success: Boolean indicating if the policy was removed
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        filepool = FilePool(cluster)
        return filepool.delete(policy_name=policy_name)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_quota_create(path: str, quota_type: str, limit_size: str,
                             soft_grace_period: str = None,
                             soft_grace_period_unit: str = "days",
                             include_overheads: bool = False,
                             persona: str = None) -> dict:
    """
    Create a new quota on the PowerScale cluster using Ansible automation.

    IMPORTANT: This is a MUTATING operation that creates a new quota on the
    live cluster. Always confirm the path, type, and limit with the user before
    calling this tool (e.g. "Create a hard quota of 500GiB on /ifs/data/projects?").

    This tool creates quotas of any type (hard, soft, advisory) via the
    dellemc.powerscale Ansible collection. Use this instead of powerscale_quota_set
    when you need to CREATE a new quota (rather than modify an existing one).

    Arguments:
    - path: The filesystem path to apply the quota to (e.g. "/ifs/data/projects")
    - quota_type: The type of quota — "hard" (prevents writes beyond limit),
      "soft" (allows temporary overages with grace period), or "advisory"
      (generates alerts but does not enforce)
    - limit_size: The quota limit as a human-readable string (e.g. "500GiB",
      "1TiB"). Use IEC units (KiB, MiB, GiB, TiB).
    - soft_grace_period: Grace period value for soft quotas (default: "7").
      Only applicable when quota_type is "soft".
    - soft_grace_period_unit: Unit for the grace period (default: "days").
      Options: "hours", "days", "weeks", "months".
      Only applicable when quota_type is "soft".
    - include_overheads: Whether to include protection overhead in usage
      calculation (default: False)
    - persona: Optional user or group name to apply the quota to. If omitted,
      the quota applies to the directory.

    Use this tool when the user wants to:
    - Create a new hard, soft, or advisory quota
    - Set up storage limits on a directory
    - Configure quota policies for users or groups

    Returns:
    - success: Boolean indicating if the quota was created
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        quotas = Quotas(cluster)
        return quotas.add_quota(path=path, quota_type=quota_type,
                                limit_size=limit_size,
                                soft_grace_period=soft_grace_period,
                                soft_grace_period_unit=soft_grace_period_unit,
                                include_overheads=include_overheads,
                                persona=persona)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_quota_remove(path: str, quota_type: str) -> dict:
    """
    Remove a quota from the PowerScale cluster using Ansible automation.

    IMPORTANT: This is a MUTATING operation that removes a quota from the live
    cluster. Always confirm the path and quota type with the user before calling
    this tool (e.g. "Remove the hard quota on /ifs/data/projects?"). This does
    NOT delete data — it only removes the quota enforcement.

    Arguments:
    - path: The filesystem path of the quota to remove (e.g. "/ifs/data/projects")
    - quota_type: The type of quota to remove — "hard", "soft", or "advisory"

    Use this tool when the user wants to:
    - Remove or delete a quota
    - Stop enforcing storage limits on a path
    - Clean up an unused quota

    Returns:
    - success: Boolean indicating if the quota was removed
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    try:
        cluster = _get_reachable_cluster()
        quotas = Quotas(cluster)
        return quotas.remove_quota(path=path, quota_type=quota_type)
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------------------------
# Namespace / file management tools
# ---------------------------------------------------------------------------

@mcp.tool()
def powerscale_directory_list(
    path: str,
    detail: str = 'default',
    limit: int = 1000,
    resume: Optional[str] = None,
    sort: Optional[str] = None,
    dir: Optional[str] = None,
    type: Optional[str] = None,
    hidden: bool = False,
    access_point: Optional[str] = None
) -> Dict[str, Any]:
    """
    List the contents of a directory on the PowerScale cluster filesystem.

    Returns files, subdirectories, and other objects within the specified
    directory path. Supports pagination for directories with many entries.

    Usage (pagination):
    - First call: use resume=None (or omit it)
    - If the response contains a non-null "resume" value, call again passing
      that value as the resume argument to fetch the next page
    - Continue until "resume" is None (has_more will be False)

    Arguments:
    - path: Directory path relative to / (e.g. "ifs/data/projects"). Do NOT
      include a leading slash.
    - detail: Attribute detail level — "default" for basic info or "default"
      with additional attributes
    - limit: Maximum number of objects to return per page (default 1000)
    - resume: Pagination token from a previous call (or None for first call)
    - sort: Attribute to sort by (e.g. "name", "size", "last_modified")
    - dir: Sort direction — "ASC" (ascending) or "DESC" (descending)
    - type: Filter by object type — "container" (directories), "object" (files),
      "symbolic_link", "pipe", "character_device", "block_device", "socket",
      "whiteout_file"
    - hidden: If True, include hidden files/directories (names starting with .)
    - access_point: If set, use access-point addressing. The path becomes
      relative to the access point instead of the root namespace.

    Use this tool to answer questions such as:
    - What files are in this directory?
    - List the contents of /ifs/data/projects
    - Show me the subdirectories under a path
    - What files were recently modified in a directory?

    Response fields:
    - children: List of objects (files/directories) with attributes
    - resume: Pagination token for next page, or None if finished
    - has_more: True if more pages exist

    Returns:
    - children: List of directory entry objects for this page
    - resume: Resume token for the next page, or None if finished
    - has_more: True if more pages exist
    """
    try:
        resume = None if resume in (None, "null", "None") else resume

        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.list_directory(
            path=path, detail=detail, limit=limit, resume=resume,
            sort=sort, dir=dir, type=type, hidden=hidden,
            access_point=access_point)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_directory_attributes(path: str) -> Dict[str, Any]:
    """
    Get attribute information for a directory on the PowerScale cluster.

    Retrieves metadata headers for the specified directory without
    transferring its contents. Returns information such as last-modified
    time, content type, and resource type.

    Arguments:
    - path: Directory path relative to / (e.g. "ifs/data/projects"). Do NOT
      include a leading slash.

    Use this tool when you need to:
    - Check if a directory exists
    - Get the last-modified time of a directory
    - Inspect directory metadata without listing contents

    Returns:
    - A dict of HTTP header key-value pairs containing directory attributes
      such as Last-Modified, Content-Type, and x-isi-ifs-target-type.
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.get_directory_attributes(path=path)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_directory_create(
    path: str,
    recursive: bool = True,
    access_control: Optional[str] = None,
    overwrite: bool = False,
    access_point: Optional[str] = None
) -> dict:
    """
    Create a directory on the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that creates a new directory
    on the live cluster. Always confirm the path with the user before
    calling this tool (e.g. "Create directory /ifs/data/projects/new-dir?").

    Arguments:
    - path: Directory path to create relative to / (e.g. "ifs/data/projects/new-dir").
      Do NOT include a leading slash.
    - recursive: If True (default), create parent directories as needed.
    - access_control: POSIX permission mode string (e.g. "0755") or a
      pre-defined ACL value. Optional.
    - overwrite: If True, replace existing directory attributes/ACLs.
    - access_point: If set, use access-point addressing. The path becomes
      relative to the access point.

    Use this tool when the user wants to:
    - Create a new directory on the cluster
    - Make a new folder in the filesystem
    - Set up a directory structure

    Returns:
    - success: Boolean indicating if the directory was created
    - message: Human-readable confirmation
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.create_directory(
            path=path, recursive=recursive, access_control=access_control,
            overwrite=overwrite, access_point=access_point)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_directory_delete(
    path: str,
    recursive: bool = False,
    access_point: Optional[str] = None
) -> dict:
    """
    Delete a directory from the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that permanently deletes a
    directory from the live cluster. Always confirm the path and whether
    recursive deletion is intended with the user before calling this tool
    (e.g. "Delete directory /ifs/data/projects/old-dir and all its contents?").

    WARNING: When recursive=True, ALL files and subdirectories within the
    directory will be permanently deleted. Use with extreme caution.

    Arguments:
    - path: Directory path to delete relative to / (e.g. "ifs/data/projects/old-dir").
      Do NOT include a leading slash.
    - recursive: If True, delete the directory and all contents. Default False
      (only deletes empty directories for safety).
    - access_point: If set, use access-point addressing.

    Use this tool when the user wants to:
    - Delete or remove a directory
    - Clean up an empty directory
    - Recursively remove a directory tree

    Returns:
    - success: Boolean indicating if the directory was deleted
    - message: Human-readable confirmation
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.delete_directory(
            path=path, recursive=recursive, access_point=access_point)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_directory_move(
    path: str,
    destination: str,
    access_point: Optional[str] = None
) -> dict:
    """
    Move or rename a directory on the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that moves/renames a directory
    on the live cluster. Always confirm the source and destination paths
    with the user before calling this tool (e.g. "Move directory
    /ifs/data/old-name to /ifs/data/new-name?").

    Arguments:
    - path: Current directory path relative to / (e.g. "ifs/data/old-name").
      Do NOT include a leading slash.
    - destination: Full destination path for the directory
      (e.g. "/ifs/data/new-name"). Include the leading slash.
    - access_point: If set, use access-point addressing for the source path.

    Use this tool when the user wants to:
    - Rename a directory
    - Move a directory to a different location
    - Reorganize the directory structure

    Returns:
    - success: Boolean indicating if the directory was moved
    - message: Human-readable confirmation
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.move_directory(
            path=path, destination=destination, access_point=access_point)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_directory_copy(
    source: str,
    destination: str,
    overwrite: bool = False,
    merge: bool = False,
    continue_on_error: bool = False
) -> dict:
    """
    Recursively copy a directory on the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that copies a directory and all
    its contents on the live cluster. Always confirm the source and destination
    paths with the user before calling this tool (e.g. "Copy directory
    /ifs/data/projects to /ifs/data/projects-backup?").

    Symbolic links in the source are copied as regular files.

    Arguments:
    - source: Full path to the source directory (e.g. "/ifs/data/projects").
      Include the leading slash.
    - destination: Destination path relative to / (e.g. "ifs/data/projects-backup").
      Do NOT include a leading slash.
    - overwrite: If True, replace existing attributes/ACLs at destination.
    - merge: If True, merge contents with an existing directory of the same name.
    - continue_on_error: If True, continue copying remaining objects on
      conflict or error instead of aborting.

    Use this tool when the user wants to:
    - Copy a directory to a new location
    - Create a backup of a directory
    - Duplicate a directory structure

    Returns:
    - success: Boolean — True if copy completed without errors
    - errors: List of any copy errors encountered
    - message: Human-readable confirmation
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.copy_directory(
            source=source, destination=destination, overwrite=overwrite,
            merge=merge, continue_on_error=continue_on_error)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_file_read(
    path: str,
    byte_range: Optional[str] = None
) -> Dict[str, Any]:
    """
    Read the contents of a file on the PowerScale cluster filesystem.

    Retrieves the full text contents of a file. This tool is designed for
    text files. Binary files will be returned with lossy encoding. File
    streaming is NOT supported — the entire file must fit in memory.

    Contents are truncated at 1 MiB to avoid overwhelming the LLM context.
    For larger files, use the byte_range parameter to read specific portions.

    Arguments:
    - path: File path relative to / (e.g. "ifs/data/projects/readme.txt").
      Do NOT include a leading slash.
    - byte_range: Optional byte range to retrieve (e.g. "bytes=0-1023" for
      the first 1024 bytes). Use this for large files or to read specific
      portions.

    Use this tool to answer questions such as:
    - What are the contents of this file?
    - Read the config file at this path
    - Show me what's in this log file

    Response fields:
    - contents: The file contents as text
    - size: Total file size in bytes
    - truncated: True if contents were truncated due to size limit
    - headers: HTTP response headers with file metadata

    Returns:
    - contents: The text content of the file
    - size: File size in bytes
    - truncated: Whether the content was truncated
    - headers: Response headers with metadata
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.get_file_contents(path=path, byte_range=byte_range)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_file_attributes(path: str) -> Dict[str, Any]:
    """
    Get attribute information for a file on the PowerScale cluster.

    Retrieves metadata headers for the specified file without transferring
    its contents. Returns information such as file size, last-modified time,
    content type, and other attributes.

    Arguments:
    - path: File path relative to / (e.g. "ifs/data/projects/readme.txt").
      Do NOT include a leading slash.

    Use this tool when you need to:
    - Check if a file exists
    - Get the size of a file without reading it
    - Get the last-modified time of a file
    - Check file type or encoding

    Returns:
    - A dict of HTTP header key-value pairs containing file attributes
      such as Content-Length, Last-Modified, Content-Type, and
      x-isi-ifs-target-type.
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.get_file_attributes(path=path)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_file_create(
    path: str,
    contents: str = '',
    access_control: Optional[str] = None,
    content_type: Optional[str] = None,
    overwrite: bool = False
) -> dict:
    """
    Create a file on the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that creates a new file on the
    live cluster. Always confirm the path and intent with the user before
    calling this tool (e.g. "Create file /ifs/data/projects/config.txt?").

    File streaming is NOT supported — the entire file contents must be
    provided as a string. Best suited for small text files.

    Arguments:
    - path: File path to create relative to / (e.g. "ifs/data/projects/config.txt").
      Do NOT include a leading slash.
    - contents: The file contents as a string. Default is empty string.
    - access_control: POSIX permission mode string (e.g. "0644") or a
      pre-defined ACL value. Optional.
    - content_type: MIME type of the content (e.g. "text/plain",
      "application/json"). Optional.
    - overwrite: If True, replace an existing file at this path.

    Use this tool when the user wants to:
    - Create a new file on the cluster
    - Write text content to a file
    - Create a configuration or data file

    Returns:
    - success: Boolean indicating if the file was created
    - message: Human-readable confirmation
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.create_file(
            path=path, contents=contents, access_control=access_control,
            content_type=content_type, overwrite=overwrite)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_file_delete(path: str) -> dict:
    """
    Delete a file from the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that permanently deletes a file
    from the live cluster. Always confirm the path with the user before
    calling this tool (e.g. "Delete file /ifs/data/projects/old-file.txt?").

    Arguments:
    - path: File path to delete relative to / (e.g. "ifs/data/projects/old-file.txt").
      Do NOT include a leading slash.

    Use this tool when the user wants to:
    - Delete or remove a file
    - Clean up an unwanted file

    Returns:
    - success: Boolean indicating if the file was deleted
    - message: Human-readable confirmation
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.delete_file(path=path)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_file_move(
    path: str,
    destination: str
) -> dict:
    """
    Move or rename a file on the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that moves/renames a file on the
    live cluster. Always confirm the source and destination paths with the
    user before calling this tool (e.g. "Move file /ifs/data/old.txt to
    /ifs/data/new.txt?").

    The destination path must not already exist.

    Arguments:
    - path: Current file path relative to / (e.g. "ifs/data/old.txt").
      Do NOT include a leading slash.
    - destination: Full destination path for the file (e.g. "/ifs/data/new.txt").
      Include the leading slash.

    Use this tool when the user wants to:
    - Rename a file
    - Move a file to a different directory
    - Reorganize files

    Returns:
    - success: Boolean indicating if the file was moved
    - message: Human-readable confirmation
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.move_file(path=path, destination=destination)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_file_copy(
    source: str,
    destination: str,
    overwrite: bool = False,
    clone: bool = False,
    snapshot: Optional[str] = None
) -> dict:
    """
    Copy a file on the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that copies a file on the live
    cluster. Always confirm the source and destination paths with the user
    before calling this tool (e.g. "Copy file /ifs/data/report.txt to
    /ifs/data/report-backup.txt?").

    Supports Copy-on-Write (CoW) cloning for space-efficient copies and
    can clone files from specific snapshots.

    Arguments:
    - source: Full path to the source file (e.g. "/ifs/data/report.txt").
      Include the leading slash.
    - destination: Destination path relative to / (e.g. "ifs/data/report-backup.txt").
      Do NOT include a leading slash.
    - overwrite: If True, replace an existing file at the destination.
    - clone: If True, create a CoW (Copy-on-Write) clone instead of a full
      copy. Clones are space-efficient as they share data blocks.
    - snapshot: Snapshot name to clone the file from. Only valid when
      clone=True.

    Use this tool when the user wants to:
    - Copy a file to a new location
    - Create a backup copy of a file
    - Clone a file efficiently using CoW
    - Restore a file from a snapshot

    Returns:
    - success: Boolean — True if copy completed without errors
    - errors: List of any copy errors encountered
    - message: Human-readable confirmation
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.copy_file(
            source=source, destination=destination, overwrite=overwrite,
            clone=clone, snapshot=snapshot)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_acl_get(
    path: str,
    zone: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get the access control list (ACL) for a file or directory on the
    PowerScale cluster.

    Returns the full ACL including individual access entries, owner, group,
    POSIX mode, and authoritative source (acl or mode).

    Arguments:
    - path: Namespace path relative to / (e.g. "ifs/data/projects").
      Do NOT include a leading slash.
    - zone: Access zone name. Optional — defaults to the System zone.

    Use this tool to answer questions such as:
    - What are the permissions on this file or directory?
    - Who owns this file?
    - What ACL entries are set on this path?
    - What is the POSIX mode of this directory?

    Response fields:
    - acl: List of ACL entry objects, each with accesstype, accessrights,
      inherit_flags, and trustee
    - owner: Owner identity (id, name, type)
    - group: Group identity (id, name, type)
    - mode: POSIX mode string (e.g. "0755")
    - authoritative: Whether "acl" or "mode" is authoritative

    Returns:
    - Full ACL dict with acl entries, owner, group, mode, and authoritative
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.get_acl(path=path, zone=zone)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_acl_set(
    path: str,
    mode: Optional[str] = None,
    owner: Optional[str] = None,
    group: Optional[str] = None,
    acl: Optional[str] = None,
    action: str = 'replace',
    zone: Optional[str] = None
) -> dict:
    """
    Set the access control list (ACL) on a file or directory on the
    PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that changes permissions on the
    live cluster. Always confirm the path and intended permission changes
    with the user before calling this tool.

    Two modes of operation:
    1. POSIX mode: Set mode="0755" (simple permissions)
    2. ACL entries: Provide acl as a JSON string with detailed access entries

    Arguments:
    - path: Namespace path relative to / (e.g. "ifs/data/projects").
      Do NOT include a leading slash.
    - mode: POSIX mode string (e.g. "0755", "0644"). Sets traditional
      Unix permissions. Use this for simple permission changes.
    - owner: Owner name to set (e.g. "root", "admin").
    - group: Group name to set (e.g. "wheel", "staff").
    - acl: JSON string of ACL entry objects for fine-grained access control.
      Example:
      '[{"accesstype":"allow","accessrights":["dir_gen_all"],
        "inherit_flags":["container_inherit","object_inherit"],
        "trustee":{"name":"admin","type":"user"}}]'
    - action: "replace" (default) to replace entire ACL, or "update" to
      merge with existing ACL entries.
    - zone: Access zone name. Optional.

    Use this tool when the user wants to:
    - Change file or directory permissions
    - Set ownership on a path
    - Configure ACL entries for specific users or groups

    Returns:
    - success: Boolean indicating if the ACL was set
    - message: Human-readable confirmation
    """
    try:
        acl_list = None
        if acl:
            acl_list = json.loads(acl)

        # Auto-detect authoritative type based on what's being set.
        # OneFS requires 'authoritative' for all ACL set operations.
        authoritative = "mode"  # default to mode for owner/group changes
        if acl_list is not None:
            authoritative = "acl"

        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.set_acl(
            path=path, mode=mode, owner=owner, group=group,
            acl=acl_list, action=action, authoritative=authoritative,
            zone=zone)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_metadata_get(
    path: str,
    is_directory: bool = True,
    zone: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get metadata attributes for a file or directory on the PowerScale cluster.

    Retrieves user-defined and system metadata attributes for the specified
    namespace object.

    Arguments:
    - path: Path relative to / (e.g. "ifs/data/projects" or
      "ifs/data/projects/file.txt"). Do NOT include a leading slash.
    - is_directory: True (default) if the path is a directory, False if it
      is a file. This determines which API endpoint is used.
    - zone: Access zone name. Optional.

    Use this tool to answer questions such as:
    - What metadata is set on this file or directory?
    - What custom attributes are attached to this path?
    - What are the system attributes of this object?

    Response fields:
    - attrs: List of attribute objects, each with name, namespace, and value

    Returns:
    - attrs: List of metadata attribute dicts
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.get_metadata(path=path, is_directory=is_directory, zone=zone)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_metadata_set(
    path: str,
    attrs: str,
    action: str = 'update',
    is_directory: bool = True,
    zone: Optional[str] = None
) -> dict:
    """
    Set metadata attributes on a file or directory on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that modifies metadata on the
    live cluster. Always confirm the path and attributes with the user
    before calling this tool.

    Arguments:
    - path: Path relative to / (e.g. "ifs/data/projects"). Do NOT include
      a leading slash.
    - attrs: JSON string of attribute objects to set. Each object must have
      "name" and "value" keys, and optionally "namespace" and "op".
      Example: '[{"name":"department","value":"engineering"},
                 {"name":"classification","value":"internal"}]'
    - action: "update" (default) to merge with existing attributes, or
      "replace" to replace all attributes.
    - is_directory: True (default) if the path is a directory, False if a file.
    - zone: Access zone name. Optional.

    Use this tool when the user wants to:
    - Set custom metadata on a file or directory
    - Tag files with attributes
    - Update metadata values

    Returns:
    - success: Boolean indicating if metadata was set
    - message: Human-readable confirmation
    """
    try:
        attrs_list = json.loads(attrs)

        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.set_metadata(
            path=path, attrs=attrs_list, action=action,
            is_directory=is_directory, zone=zone)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_access_point_list(
    versions: bool = False
) -> Dict[str, Any]:
    """
    List namespace access points on the PowerScale cluster.

    Access points are named entry points into the cluster filesystem that
    provide scoped access to specific directory trees.

    Arguments:
    - versions: If True, include protocol version information for each
      access point.

    Use this tool to answer questions such as:
    - What access points are configured on the cluster?
    - What namespace entry points are available?

    Returns:
    - namespaces: List of access point objects with path and name information
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.list_access_points(versions=versions)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_access_point_create(
    name: str,
    path: str
) -> dict:
    """
    Create a namespace access point on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new access point
    on the live cluster. Only root users can create access points. Always
    confirm the access point name and path with the user before calling
    this tool.

    Arguments:
    - name: Name for the access point (e.g. "projects")
    - path: Absolute filesystem path the access point maps to
      (e.g. "/ifs/data/projects")

    Use this tool when the user wants to:
    - Create a new namespace access point
    - Set up a scoped entry point into the filesystem

    Returns:
    - success: Boolean indicating if the access point was created
    - message: Human-readable confirmation
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.create_access_point(name=name, path=path)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_access_point_delete(name: str) -> dict:
    """
    Delete a namespace access point from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes an access point
    from the live cluster. Only root users can delete access points. Always
    confirm the access point name with the user before calling this tool.
    This does NOT delete the underlying directory — it only removes the
    access point definition.

    Arguments:
    - name: Name of the access point to delete (e.g. "projects")

    Use this tool when the user wants to:
    - Remove a namespace access point
    - Delete an access point entry

    Returns:
    - success: Boolean indicating if the access point was deleted
    - message: Human-readable confirmation
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.delete_access_point(name=name)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_worm_get(path: str) -> Dict[str, Any]:
    """
    Get WORM (Write Once Read Many) properties for a file on the
    PowerScale cluster.

    WORM / SmartLock protects files from modification and deletion until
    a retention date has passed. This tool retrieves the WORM state for
    a specific file.

    Arguments:
    - path: File path relative to / (e.g. "ifs/data/compliance/report.pdf").
      Do NOT include a leading slash. The file must be in a SmartLock
      directory.

    Use this tool to answer questions such as:
    - Is this file committed to WORM?
    - What is the retention date on this file?
    - What SmartLock domain does this file belong to?

    Response fields:
    - worm_committed: Whether the file is committed to WORM state
    - worm_retention_date: The retention expiration date (UTC)
    - worm_retention_date_val: Retention date as epoch timestamp
    - worm_override_retention_date: Override retention date if set

    Returns:
    - Full WORM properties dict for the file
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.get_worm_properties(path=path)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_worm_set(
    path: str,
    commit_to_worm: bool = False,
    worm_retention_date: Optional[str] = None
) -> dict:
    """
    Set WORM (Write Once Read Many) properties on a file on the
    PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that commits a file to WORM
    state and/or sets a retention date. Once committed, a WORM file CANNOT
    be modified or deleted until the retention period expires. Always confirm
    the path, commit flag, and retention date with the user before calling
    this tool. This action may be IRREVERSIBLE.

    Arguments:
    - path: File path relative to / (e.g. "ifs/data/compliance/report.pdf").
      Do NOT include a leading slash. The file must be in a SmartLock
      directory.
    - commit_to_worm: If True, commit the file to WORM state. Once
      committed, the file cannot be modified or deleted until the retention
      date passes.
    - worm_retention_date: Retention expiration date in UTC string format
      (e.g. "2025-12-31T23:59:59Z"). After this date, the file can be
      deleted (but not modified).

    Use this tool when the user wants to:
    - Commit a file to WORM/SmartLock protection
    - Set or extend a retention date on a file
    - Lock a file for compliance purposes

    Returns:
    - success: Boolean indicating if WORM properties were set
    - message: Human-readable confirmation
    """
    try:
        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.set_worm_properties(
            path=path, commit_to_worm=commit_to_worm,
            worm_retention_date=worm_retention_date)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def powerscale_directory_query(
    path: str,
    conditions: str,
    logic: str = 'and',
    result_attrs: Optional[str] = None,
    limit: int = 1000,
    resume: Optional[str] = None,
    sort: Optional[str] = None,
    dir: Optional[str] = None,
    type: Optional[str] = None,
    hidden: bool = False,
    max_depth: Optional[int] = None
) -> Dict[str, Any]:
    """
    Query objects within a directory on the PowerScale cluster by attribute
    conditions.

    Performs an advanced search within a directory tree, filtering objects
    by system-defined or user-defined attributes. Supports pagination for
    large result sets.

    Usage (pagination):
    - First call: use resume=None (or omit it)
    - If the response contains a non-null "resume" value, call again passing
      that value as the resume argument to fetch the next page
    - Continue until "resume" is None (has_more will be False)

    Arguments:
    - path: Directory path to query relative to / (e.g. "ifs/data/projects").
      Do NOT include a leading slash.
    - conditions: JSON string of condition objects. Each condition has:
      - attr: Attribute name (e.g. "name", "size", "type", "owner",
        "last_modified")
      - operator: Comparison operator ("=", "!=", ">", "<", ">=", "<=",
        "like")
      - value: Value to compare against
      Example: '[{"attr":"name","operator":"like","value":"*.log"},
                 {"attr":"size","operator":">","value":"1048576"}]'
    - logic: How to combine conditions — "and" (default, all must match) or
      "or" (any can match)
    - result_attrs: Optional JSON string of attribute names to include in
      results (e.g. '["name","size","last_modified"]'). If omitted, default
      attributes are returned.
    - limit: Maximum number of objects to return per page (default 1000)
    - resume: Pagination token from a previous call
    - sort: Attribute to sort results by
    - dir: Sort direction — "ASC" or "DESC"
    - type: Filter by object type (e.g. "container", "object")
    - hidden: If True, include hidden files in results
    - max_depth: Maximum directory depth to search. If omitted, searches
      all depths.

    Use this tool to answer questions such as:
    - Find all .log files in this directory tree
    - Which files are larger than 1 GiB under this path?
    - Search for files modified after a certain date
    - Find files owned by a specific user

    Returns:
    - children: List of matching objects with their attributes
    - resume: Pagination token for next page, or None if finished
    - has_more: True if more pages exist
    """
    try:
        resume = None if resume in (None, "null", "None") else resume

        conditions_list = json.loads(conditions)
        result_attrs_list = json.loads(result_attrs) if result_attrs else None

        cluster = _get_reachable_cluster()
        fm = FileMgmt(cluster)
        return fm.query_directory(
            path=path, conditions=conditions_list, logic=logic,
            result_attrs=result_attrs_list, limit=limit, resume=resume,
            sort=sort, dir=dir, type=type, hidden=hidden,
            max_depth=max_depth)
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------------------------
# Utility tools
# ---------------------------------------------------------------------------

@mcp.tool()
def bytes_to_human(bytes_value: int) -> dict:
    """
    Convert a byte value to a human-readable IEC string (base-1024).

    IEC units use base-1024 (binary) prefixes: KiB, MiB, GiB, TiB, PiB, EiB.
    The tool automatically selects the most appropriate unit for readability.

    Only one value should be submitted per call.

    Arguments:
    - bytes_value: An integer number of bytes (e.g. 84079902720)

    Response fields:
    - bytes: The original byte value (echoed back for reference)
    - human_readable: The formatted string (e.g. "78.31GiB")

    Use this tool when you need to:
    - Present capacity, quota, or snapshot sizes in a readable format
    - Convert raw byte values from other PowerScale tools for the user
    - Format storage statistics before displaying them

    Example: 84079902720 bytes -> "78.31GiB"
    """
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB"]
    value = float(bytes_value)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return {
                "bytes": bytes_value,
                "human_readable": f"{value:.2f}{unit}"
            }
        value /= 1024

@mcp.tool()
def human_to_bytes(human_value: str) -> dict:
    """
    Convert a human-readable IEC string (base-1024) to an integer byte value.

    This is the inverse of bytes_to_human. It parses a size string with an IEC
    unit suffix and returns the equivalent number of bytes.

    Supported units: B, KiB, MiB, GiB, TiB, PiB, EiB (base-1024).

    Only one value should be submitted per call.

    Arguments:
    - human_value: A size string with unit (e.g. "78.31GiB", "500MiB", "1TiB")

    Response fields:
    - human_readable: The original string (echoed back for reference)
    - bytes: The computed integer byte value

    Use this tool when you need to:
    - Convert a user-provided size (e.g. "500GiB") into bytes for quota tools
    - Prepare byte values for powerscale_quota_set, powerscale_quota_increment,
      or powerscale_quota_decrement which require sizes in bytes
    - Validate or normalize a user's size input

    Example: "78.31GiB" -> 84079902720 bytes
    """
    units = {
        "B": 0,
        "KiB": 1,
        "MiB": 2,
        "GiB": 3,
        "TiB": 4,
        "PiB": 5,
        "EiB": 6,
    }

    match = re.fullmatch(r"\s*([\d.]+)\s*(B|KiB|MiB|GiB|TiB|PiB|EiB)\s*", human_value)
    if not match:
        raise ValueError(f"Invalid human-readable value: {human_value}")

    value = float(match.group(1))
    unit = match.group(2)

    bytes_value = int(value * (1024 ** units[unit]))

    return {
        "human_readable": human_value,
        "bytes": bytes_value
    }

# ---------------------------------------------------------------------------
# Tool management tools — always registered, cannot be disabled
# ---------------------------------------------------------------------------

@mcp.tool()
def powerscale_tools_list() -> Dict[str, Any]:
    """
    List all available PowerScale MCP tools and their current status.

    Returns every tool organised by group, showing whether each tool is
    currently enabled (registered with the MCP server) or disabled (removed
    from the tool list to save tokens).

    Use this tool to:
    - See which tool groups and individual tools are available
    - Check which tools are currently disabled
    - Decide which groups to enable or disable with powerscale_tools_toggle

    Response fields:
    - groups: Dict mapping group name to a list of tool entries, each with
      "name" and "status" ("enabled" or "disabled")
    - total_enabled: Number of currently enabled tools
    - total_disabled: Number of currently disabled tools
    """
    enabled_tools = set(mcp._tool_manager._tools.keys())
    groups = {}
    for group_name, tool_names in TOOL_GROUPS.items():
        entries = []
        for tool_name in tool_names:
            status = "enabled" if tool_name in enabled_tools else "disabled"
            entries.append({"name": tool_name, "status": status})
        groups[group_name] = entries

    total_enabled = sum(
        1 for entries in groups.values()
        for e in entries if e["status"] == "enabled"
    )
    total_disabled = sum(
        1 for entries in groups.values()
        for e in entries if e["status"] == "disabled"
    )

    return {
        "groups": groups,
        "total_enabled": total_enabled,
        "total_disabled": total_disabled,
    }


@mcp.tool()
def powerscale_tools_toggle(names: List[str], action: str) -> Dict[str, Any]:
    """
    Enable or disable PowerScale MCP tools at runtime.

    IMPORTANT: This is a MUTATING operation that changes which tools are
    available to the LLM. After toggling, the MCP client will be notified
    that the tool list has changed and will re-fetch it automatically.

    You can pass group names (e.g. "filemgmt", "synciq") to toggle all tools
    in that group at once, or individual tool names for fine-grained control.

    Available groups: health, capacity, quotas, snapshots, synciq, datamover,
    filepool, nfs, smb, s3, filemgmt, utils

    Arguments:
    - names: List of group names and/or individual tool names to toggle.
      Examples: ["filemgmt"], ["synciq", "s3"], ["powerscale_quota_remove"]
    - action: "disable" to remove tools from the tool list, or "enable" to
      restore them.

    Use this tool when:
    - The user wants to reduce token usage by disabling unused tool groups
    - The user wants to re-enable previously disabled tools
    - You need to streamline the tool list for a specific task

    Returns:
    - action: The action performed ("disable" or "enable")
    - toggled: List of tool names that were actually toggled
    - skipped: List of names that were already in the requested state
    - total_enabled: Updated count of enabled tools
    - total_disabled: Updated count of disabled tools
    """
    if action not in ("enable", "disable"):
        return {"error": f"Invalid action '{action}'. Must be 'enable' or 'disable'."}

    tool_names = _resolve_names_to_tools(names)
    toggled = []
    skipped = []

    if action == "disable":
        for name in tool_names:
            if name in MANAGEMENT_TOOLS:
                skipped.append(name)
                continue
            if name in mcp._tool_manager._tools:
                _disabled_tools[name] = mcp._tool_manager._tools[name]
                mcp.remove_tool(name)
                toggled.append(name)
            else:
                skipped.append(name)
    else:  # enable
        for name in tool_names:
            if name in _disabled_tools:
                tool_obj = _disabled_tools.pop(name)
                mcp.add_tool(tool_obj)
                toggled.append(name)
            else:
                skipped.append(name)

    # Persist to config file
    config = _load_tool_config()
    disabled_set = set(config.get("disabled_groups", []))
    disabled_tool_set = set(config.get("disabled_tools", []))

    for name in names:
        if name in TOOL_GROUPS:
            if action == "disable":
                disabled_set.add(name)
            else:
                disabled_set.discard(name)
        elif name in _TOOL_TO_GROUP:
            if action == "disable":
                disabled_tool_set.add(name)
            else:
                disabled_tool_set.discard(name)

    config["disabled_groups"] = sorted(disabled_set)
    config["disabled_tools"] = sorted(disabled_tool_set)
    _save_tool_config(config)

    return {
        "action": action,
        "toggled": toggled,
        "skipped": skipped,
        "total_enabled": len(mcp._tool_manager._tools),
        "total_disabled": len(_disabled_tools),
    }


# ---------------------------------------------------------------------------
# Cluster management tools — always registered, cannot be disabled
# ---------------------------------------------------------------------------

@mcp.tool()
def powerscale_cluster_list() -> Dict[str, Any]:
    """
    List all PowerScale clusters configured in the vault and show which one
    is currently selected.

    Returns a list of clusters with their name, host, port, verify_ssl status,
    and whether each is the currently selected target. Passwords are never
    included in the response.

    Use this tool to:
    - See which clusters are available to manage
    - Check which cluster is currently targeted by all other PowerScale tools
    - Verify cluster configuration before switching
    """
    try:
        vm = VaultManager()
        clusters = vm.list_clusters()
        selected = vm.selected_cluster_name
        return {
            "clusters": clusters,
            "selected": selected,
            "total": len(clusters),
        }
    except FileNotFoundError:
        return {"error": "Vault file not found. Ensure vault.yml is mounted into the container."}
    except Exception as e:
        return {"error": f"Failed to read vault: {str(e)}"}


@mcp.tool()
def powerscale_cluster_select(cluster_name: str, reload_vault: bool = False) -> Dict[str, Any]:
    """
    Switch the active PowerScale cluster that all tools will operate against.

    IMPORTANT: This is a MUTATING operation that changes which cluster all
    subsequent tool calls will target. The change takes effect immediately.

    Arguments:
    - cluster_name: The name of the cluster as defined in the vault file
      (e.g. "lab_cluster", "production"). Use powerscale_cluster_list to
      see available names.
    - reload_vault: If True, re-read and decrypt the vault file before
      selecting. Use this if clusters were added/removed externally.
      Default is False.

    Use this tool when:
    - The user wants to manage a different PowerScale cluster
    - The user wants to switch from lab to production (or vice versa)
    - The user asks "switch to cluster X" or "target the production cluster"
    """
    try:
        vm = VaultManager()
        if reload_vault:
            vm.reload()

        if vm.select_cluster(cluster_name):
            return {
                "success": True,
                "selected": cluster_name,
                "message": f"Now targeting cluster '{cluster_name}'. All subsequent tools will operate against this cluster.",
            }
        else:
            available = [c["name"] for c in vm.list_clusters()]
            return {
                "success": False,
                "error": f"Cluster '{cluster_name}' not found in vault.",
                "available_clusters": available,
            }
    except Exception as e:
        return {"error": f"Failed to select cluster: {str(e)}"}


@mcp.tool()
def powerscale_cluster_add(
    name: str,
    host: str,
    port: int = 8080,
    username: str = "root",
    password: str = "",
    verify_ssl: bool = False,
) -> Dict[str, Any]:
    """
    Add a new PowerScale cluster to the vault, or update an existing one.

    IMPORTANT: This is a MUTATING operation. Confirm with the user before executing.

    The cluster credentials are encrypted and saved to the vault file immediately.
    Use powerscale_cluster_select to switch to the new cluster.

    Arguments:
    - name: Cluster label used to identify it (e.g. "production", "lab")
    - host: Hostname or IP address (https:// prefix added automatically if omitted)
    - port: API port (default 8080)
    - username: Admin username (default root)
    - password: Admin password
    - verify_ssl: Whether to verify SSL certificates (default false for self-signed certs)
    """
    try:
        vm = VaultManager()
        vm.add_cluster(name, host, port, username, password, verify_ssl)
        return {
            "success": True,
            "cluster": name,
            "message": f"Cluster '{name}' saved to vault. Use powerscale_cluster_select to target it.",
            "clusters": vm.list_clusters(),
        }
    except Exception as e:
        return {"error": f"Failed to add cluster: {str(e)}"}


@mcp.tool()
def powerscale_cluster_remove(name: str) -> Dict[str, Any]:
    """
    Remove a PowerScale cluster from the vault.

    IMPORTANT: This is a MUTATING operation. Confirm with the user before executing.

    Cannot remove the currently selected cluster — use powerscale_cluster_select
    to switch to a different cluster first.

    Arguments:
    - name: The cluster label to remove (use powerscale_cluster_list to see available names)
    """
    try:
        vm = VaultManager()
        if vm.selected_cluster_name == name:
            return {
                "success": False,
                "error": f"Cannot remove the currently selected cluster '{name}'. "
                         "Use powerscale_cluster_select to switch to a different cluster first.",
            }
        removed = vm.remove_cluster(name)
        if not removed:
            available = [c["name"] for c in vm.list_clusters()]
            return {
                "success": False,
                "error": f"Cluster '{name}' not found in vault.",
                "available_clusters": available,
            }
        return {
            "success": True,
            "message": f"Cluster '{name}' removed from vault.",
            "clusters": vm.list_clusters(),
        }
    except Exception as e:
        return {"error": f"Failed to remove cluster: {str(e)}"}


# ---------------------------------------------------------------------------
# Startup: apply disabled tools from config file
# ---------------------------------------------------------------------------

def _apply_startup_config() -> None:
    """Disable tools listed in tool_config.json at server startup.

    Set ENABLE_ALL_TOOLS=true to skip disabling (used by test harness).
    """
    if os.environ.get("ENABLE_ALL_TOOLS", "").lower() == "true":
        total = len(mcp._tool_manager._tools)
        print(f"  [tool-config] ENABLE_ALL_TOOLS set — all {total} tools enabled")
        return

    config = _load_tool_config()
    names_to_disable = []

    for group in config.get("disabled_groups", []):
        if group in TOOL_GROUPS:
            names_to_disable.extend(TOOL_GROUPS[group])

    for tool_name in config.get("disabled_tools", []):
        if tool_name not in names_to_disable:
            names_to_disable.append(tool_name)

    for name in names_to_disable:
        if name in MANAGEMENT_TOOLS:
            continue
        if name in mcp._tool_manager._tools:
            _disabled_tools[name] = mcp._tool_manager._tools[name]
            mcp._tool_manager.remove_tool(name)
            print(f"  [tool-config] Disabled: {name}")

    enabled = len(mcp._tool_manager._tools)
    disabled = len(_disabled_tools)
    print(f"  [tool-config] {enabled} tools enabled, {disabled} tools disabled")


# ---------------------------------------------------------------------------
# User management tools
# ---------------------------------------------------------------------------

@mcp.tool()
def powerscale_user_get(
    user_name: Optional[str] = None,
    provider_type: Optional[str] = None,
    access_zone: Optional[str] = None,
    limit: int = 1000,
    resume: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List local users on the PowerScale cluster, or retrieve a specific user by name.

    Users are local or external accounts that can authenticate against the cluster
    and access data according to their group memberships and role assignments.

    Arguments:
    - user_name: If provided, fetch only this user (exact match). If omitted, list all.
    - provider_type: Filter by authentication provider — 'local', 'file', 'ldap',
      'ads', or 'nis'. Defaults to all providers when omitted.
    - access_zone: Filter by access zone name. Defaults to all zones when omitted.
    - limit: Maximum number of users per page (list mode only).
    - resume: Resume token from a previous call for pagination (list mode only).

    Returns per user:
    - name: Account name
    - uid: UNIX user ID
    - gid: Primary group ID
    - email: Email address
    - enabled: Whether the account is active
    - home_directory: Home directory path
    - shell: Login shell
    - provider: Authentication provider
    - member_of: Groups this user belongs to
    - sid: Windows Security Identifier
    """
    try:
        resume = None if resume in (None, "null", "None") else resume
        cluster = _get_reachable_cluster()
        users = Users(cluster)
        page = users.get(
            user_name=user_name,
            provider_type=provider_type,
            access_zone=access_zone,
            limit=limit,
            resume=resume,
        )
        items = page.get("items") or []
        tok = page.get("resume")
        return {
            "items": items,
            "resume": tok,
            "has_more": bool(tok),
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def powerscale_user_create(
    user_name: str,
    password: str,
    access_zone: Optional[str] = None,
    provider_type: Optional[str] = None,
    primary_group: Optional[str] = None,
    enabled: Optional[bool] = None,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    home_directory: Optional[str] = None,
    shell: Optional[str] = None,
    user_id: Optional[int] = None,
    role_name: Optional[str] = None,
    role_state: Optional[str] = None,
    update_password: str = "on_create",
) -> dict:
    """
    Create a new local user on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation. It creates a new user account on the
    live cluster. Always confirm the username and settings with the user before
    calling this tool (e.g. "Create user 'alice' with primary group 'users'?").

    This tool uses Ansible automation via the dellemc.powerscale collection.
    Creation is only supported for local provider accounts.

    Arguments (required):
    - user_name: The account name to create (e.g. "alice", "svc_backup")
    - password: Initial password for the account

    Arguments (optional — omit to use cluster defaults):
    - access_zone: Access zone to create the user in (default: System zone)
    - provider_type: Authentication provider — 'local' (default), 'file', 'ldap',
      'ads', or 'nis'. Creation is only supported for 'local'.
    - primary_group: Primary group name for file ownership (e.g. "Isilon Users")
    - enabled: Whether the account is active (default: true)
    - email: Email address for the account
    - full_name: Display name / GECOS field
    - home_directory: Absolute path to home directory (must be unused)
    - shell: Login shell path (e.g. "/bin/bash", "/bin/sh")
    - user_id: Explicit UID to assign (auto-assigned if omitted)
    - role_name: Role to assign to the user upon creation (system zone only)
    - role_state: 'present-for-user' to assign the role
    - update_password: 'on_create' (set only at creation) or 'always' (update on every run)
    """
    try:
        cluster = _get_reachable_cluster()
        users = Users(cluster)
        return users.add(
            user_name=user_name,
            password=password,
            access_zone=access_zone,
            provider_type=provider_type,
            primary_group=primary_group,
            enabled=enabled,
            email=email,
            full_name=full_name,
            home_directory=home_directory,
            shell=shell,
            user_id=user_id,
            role_name=role_name,
            role_state=role_state,
            update_password=update_password,
        )
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def powerscale_user_modify(
    user_name: str,
    access_zone: Optional[str] = None,
    provider_type: Optional[str] = None,
    primary_group: Optional[str] = None,
    enabled: Optional[bool] = None,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    home_directory: Optional[str] = None,
    shell: Optional[str] = None,
    password: Optional[str] = None,
    update_password: Optional[str] = None,
    role_name: Optional[str] = None,
    role_state: Optional[str] = None,
) -> dict:
    """
    Modify an existing user account on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation. It updates the specified user account
    on the live cluster. Always confirm the change with the user before calling
    (e.g. "Disable account 'alice'?" or "Set primary group to 'admins' for 'bob'?").

    Only the fields you provide will be changed; omitted fields are left unchanged.
    Role management (add/remove role assignments) is only supported in the system zone.

    Arguments (required):
    - user_name: The account name to modify

    Arguments (optional — only provided fields are updated):
    - access_zone: Access zone the user lives in (default: System zone)
    - provider_type: Authentication provider (default: 'local')
    - primary_group: New primary group name
    - enabled: True to enable, False to disable the account
    - email: New email address
    - full_name: New display name / GECOS field
    - home_directory: New home directory path
    - shell: New login shell path
    - password: New password (requires update_password='always' to take effect)
    - update_password: 'always' to change the password now, 'on_create' to skip
    - role_name: Role to assign or remove
    - role_state: 'present-for-user' to assign, 'absent-for-user' to remove
    """
    try:
        cluster = _get_reachable_cluster()
        users = Users(cluster)
        return users.modify(
            user_name=user_name,
            access_zone=access_zone,
            provider_type=provider_type,
            primary_group=primary_group,
            enabled=enabled,
            email=email,
            full_name=full_name,
            home_directory=home_directory,
            shell=shell,
            password=password,
            update_password=update_password,
            role_name=role_name,
            role_state=role_state,
        )
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def powerscale_user_remove(
    user_name: str,
    access_zone: Optional[str] = None,
    provider_type: Optional[str] = None,
) -> dict:
    """
    Delete a local user account from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation. It permanently deletes the user account
    from the cluster. All role assignments are automatically removed. This cannot be
    undone. Always confirm with the user before calling
    (e.g. "Delete user account 'alice'?").

    Deletion is only supported for local provider accounts.

    Arguments (required):
    - user_name: The account name to delete

    Arguments (optional):
    - access_zone: Access zone the user lives in (default: System zone)
    - provider_type: Authentication provider — must be 'local' for deletion
    """
    try:
        cluster = _get_reachable_cluster()
        users = Users(cluster)
        return users.remove(
            user_name=user_name,
            access_zone=access_zone,
            provider_type=provider_type,
        )
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Group management tools
# ---------------------------------------------------------------------------

@mcp.tool()
def powerscale_group_get(
    group_name: Optional[str] = None,
    group_id: Optional[int] = None,
    provider_type: Optional[str] = None,
    access_zone: Optional[str] = None,
    limit: int = 1000,
    resume: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List groups on the PowerScale cluster, or retrieve a specific group by name or GID.

    Groups control access to resources and appear as UNIX groups or Windows security
    groups depending on the authentication provider. Local groups can have members
    added and removed; external groups (ads, ldap, nis) are read-only from the
    cluster's perspective.

    Arguments:
    - group_name: If provided, fetch only this group (exact match). If omitted, list all.
    - group_id: GID to look up instead of name (e.g. 2000). Use group_name OR group_id.
    - provider_type: Filter by authentication provider — 'local', 'file', 'ldap',
      'ads', or 'nis'. Defaults to all providers when omitted.
    - access_zone: Filter by access zone name. Defaults to all zones when omitted.
    - limit: Maximum number of groups per page (list mode only).
    - resume: Resume token from a previous call for pagination (list mode only).

    Returns per group:
    - name: Group name
    - gid: UNIX group ID
    - sid: Windows Security Identifier
    - provider: Authentication provider and zone (e.g. 'lsa-local-provider:System')
    - members: List of member SIDs
    """
    try:
        resume = None if resume in (None, "null", "None") else resume
        cluster = _get_reachable_cluster()
        grp = Group(cluster)
        page = grp.get(
            group_name=group_name,
            group_id=group_id,
            provider_type=provider_type,
            access_zone=access_zone,
            limit=limit,
            resume=resume,
        )
        items = page.get("items") or []
        tok = page.get("resume")
        return {
            "items": items,
            "resume": tok,
            "has_more": bool(tok),
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def powerscale_group_create(
    group_name: str,
    group_id: Optional[int] = None,
    access_zone: Optional[str] = None,
    provider_type: Optional[str] = None,
    users: Optional[str] = None,
    user_state: Optional[str] = None,
) -> dict:
    """
    Create a new local group on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation. It creates a new group on the live
    cluster. Always confirm the group name and initial members with the user before
    calling this tool (e.g. "Create group 'developers' with GID 2500?").

    This tool uses Ansible automation via the dellemc.powerscale collection.
    Creation is only supported for local provider groups. Groups from external
    providers (ads, ldap, nis) are managed externally.

    Arguments (required):
    - group_name: The name of the group to create (e.g. "developers", "svc_backup")

    Arguments (optional — omit to use cluster defaults):
    - group_id: Explicit GID to assign (auto-assigned if omitted)
    - access_zone: Access zone to create the group in (default: System zone)
    - provider_type: Authentication provider — 'local' (default). Only 'local' is
      supported for creation.
    - users: JSON array of user dicts to add as initial members. Each dict must have
      exactly one key: "user_name" (str) or "user_id" (int).
      Example: '[{"user_name": "alice"}, {"user_name": "bob"}, {"user_id": 1001}]'
    - user_state: Required when users is provided — must be 'present-in-group' to add
      the specified users as members during creation.

    Use this tool when the user wants to:
    - Create a new local group for file access control
    - Create a group with an explicit GID for NFS compatibility
    - Create a group and immediately populate it with members
    """
    try:
        cluster = _get_reachable_cluster()
        grp = Group(cluster)
        return grp.add(
            group_name=group_name,
            group_id=group_id,
            access_zone=access_zone,
            provider_type=provider_type,
            users=users,
            user_state=user_state,
        )
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def powerscale_group_modify(
    group_name: Optional[str] = None,
    group_id: Optional[int] = None,
    users: Optional[str] = None,
    user_state: Optional[str] = None,
    access_zone: Optional[str] = None,
    provider_type: Optional[str] = None,
) -> dict:
    """
    Add or remove members from an existing group on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation. It modifies group membership on the
    live cluster. Always confirm the members and action with the user before calling
    (e.g. "Add users 'alice' and 'bob' to group 'developers'?").

    Either group_name or group_id must be provided to identify the group.
    Modification is only supported for local provider groups.

    Arguments (one required to identify the group):
    - group_name: The name of the group to modify
    - group_id: The GID of the group to modify

    Arguments (required for member management):
    - users: JSON array of user dicts specifying which users to add or remove.
      Each dict must have exactly one key: "user_name" (str) or "user_id" (int).
      Example: '[{"user_name": "alice"}, {"user_id": 1001}]'
    - user_state: What to do with the listed users:
      - 'present-in-group': Add these users to the group
      - 'absent-in-group': Remove these users from the group

    Arguments (optional filters):
    - access_zone: Access zone the group lives in (default: System zone)
    - provider_type: Authentication provider (default: 'local')

    Use this tool when the user wants to:
    - Add one or more users to a group
    - Remove one or more users from a group
    - Manage group membership by UID instead of username
    """
    try:
        cluster = _get_reachable_cluster()
        grp = Group(cluster)
        return grp.modify(
            group_name=group_name,
            group_id=group_id,
            access_zone=access_zone,
            provider_type=provider_type,
            users=users,
            user_state=user_state,
        )
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def powerscale_group_remove(
    group_name: Optional[str] = None,
    group_id: Optional[int] = None,
    access_zone: Optional[str] = None,
    provider_type: Optional[str] = None,
) -> dict:
    """
    Delete a local group from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation. It permanently deletes the group from
    the cluster. Member associations are removed; the member users themselves are
    not deleted. This cannot be undone. Always confirm with the user before calling
    (e.g. "Delete group 'developers'?").

    Either group_name or group_id must be provided to identify the group.
    Deletion is only supported for local provider groups.

    Arguments (one required to identify the group):
    - group_name: The name of the group to delete
    - group_id: The GID of the group to delete

    Arguments (optional):
    - access_zone: Access zone the group lives in (default: System zone)
    - provider_type: Authentication provider — must be 'local' for deletion

    Use this tool when the user wants to:
    - Remove a group that is no longer needed
    - Clean up groups before decommissioning an access zone
    """
    try:
        cluster = _get_reachable_cluster()
        grp = Group(cluster)
        return grp.remove(
            group_name=group_name,
            group_id=group_id,
            access_zone=access_zone,
            provider_type=provider_type,
        )
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Events tools
# ---------------------------------------------------------------------------

@mcp.tool()
def powerscale_event_get(
    limit: int = 100,
    resume: Optional[str] = None,
    begin: Optional[int] = None,
    end: Optional[int] = None,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    ignore: Optional[bool] = None,
    sort: Optional[str] = None,
    dir: Optional[str] = None,
    cause: Optional[str] = None,
    event_count: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Retrieve event group occurrences from the PowerScale cluster with optional
    filtering, sorting, and pagination.

    Each result item represents an "event group occurrence" — a logical cluster
    of related individual events (e.g. all occurrences of a particular hardware
    fault are grouped together). Key fields in each item include:
    - id: Unique event group identifier (use with powerscale_event_get_by_id)
    - severity: "emergency", "critical", "warning", or "information"
    - cause: Short description of the event type
    - cause_string: Human-readable description
    - begin: Unix timestamp when the event group started
    - end: Unix timestamp when it ended (null if still active)
    - resolved: Whether the event group has been resolved
    - ignore: Whether the event group has been ignored/suppressed
    - event_count: Number of individual events in this group
    - last_event_begin: Timestamp of the most recent event in the group

    Pagination:
    - Use 'limit' to control the number of results per page (default 100).
    - If 'has_more' is True in the response, pass the returned 'resume' token
      to the next call to fetch the next page.
    - IMPORTANT: When 'resume' is provided, all other filter/sort parameters
      are ignored by the API. Use the same filters for subsequent pages by
      relying on the resume token chain.

    Date range filtering (Unix epoch timestamps):
    - 'begin': Return events that were active after this time.
    - 'end': Return events that were active before this time.
    - To get events from the last 24 hours: begin=<current_epoch - 86400>.
      Use the 'current_time' tool (utils group) to get the current epoch.
    - To get events from the last 7 days: begin=<current_epoch - 604800>.

    Arguments:
    - limit: Maximum results per page (default 100, max 4294967295)
    - resume: Pagination token from a previous call
    - begin: Unix timestamp — events active after this time
    - end: Unix timestamp — events active before this time
    - severity: Comma-separated severity levels to filter by, e.g. "critical"
                or "critical,warning". Valid: emergency, critical, warning,
                information
    - resolved: True to return only resolved events, False for unresolved only
    - ignore: True to return only ignored events, False for non-ignored only
    - sort: Field to sort by — e.g. "severity", "begin", "last_event_begin",
            "event_count", "cause"
    - dir: Sort direction — "ASC" or "DESC"
    - cause: Filter by cause text (substring match)
    - event_count: Return only event groups with more than this many occurrences
                   (useful for finding frequently recurring events)

    Use this tool when the user wants to:
    - See current active or unresolved cluster events/alerts
    - Find critical or warning events on the cluster
    - Investigate events within a specific date range
    - Search for events by cause description
    - Find high-frequency recurring events
    - Page through a large event history
    """
    resume = None if resume in (None, "null", "None") else resume
    try:
        cluster = _get_reachable_cluster()
        events = Events(cluster)
        page = events.get(
            limit=limit,
            resume=resume,
            begin=begin,
            end=end,
            severity=severity,
            resolved=resolved,
            ignore=ignore,
            sort=sort,
            dir=dir,
            cause=cause,
            event_count=event_count,
        )
        items = page.get("items") or []
        next_resume = page.get("resume")
        result = {
            "items": items,
            "resume": next_resume,
            "limit": limit,
            "has_more": bool(next_resume),
        }
        if "error" in page:
            result["error"] = page["error"]
        return result
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def powerscale_event_get_by_id(event_id: str) -> Dict[str, Any]:
    """
    Retrieve a single event group occurrence by its ID.

    Returns the full detail of one event group occurrence, including all fields
    such as severity, cause, cause_string, begin/end timestamps, event_count,
    resolved status, and associated devids (node IDs).

    Arguments:
    - event_id: The event group occurrence ID. Obtain IDs from the 'id' field
                of results returned by powerscale_event_get.

    Use this tool when the user wants to:
    - Inspect the full details of a specific event
    - Get the complete cause description and resolution information for an alert
    - Check whether a specific event has been resolved
    """
    try:
        cluster = _get_reachable_cluster()
        events = Events(cluster)
        return events.get_by_id(event_id)
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Statistics tools
# ---------------------------------------------------------------------------


@mcp.tool()
def powerscale_stats_cpu() -> Dict[str, Any]:
    """
    Return 30-second averaged cluster CPU utilization metrics.

    This tool samples CPU statistics 6 times over 30 seconds and returns the
    averaged values. Inform the user that results will take approximately
    30 seconds to collect before responding.

    Response fields (all values are percentages, 0–100):
    - cluster.cpu.sys.avg:  Average CPU time spent in kernel/system mode
    - cluster.cpu.user.avg: Average CPU time spent in user-space processes
    - cluster.cpu.idle.avg: Average CPU idle time (higher is better)
    - cluster.cpu.intr.avg: Average CPU time handling hardware interrupts

    Tip: A healthy cluster typically has idle > 50%. Values of sys+user > 80%
    combined may indicate CPU pressure. High intr can suggest network or disk
    interrupt storms.

    Use this tool when the user asks:
    - Is the cluster CPU busy or overloaded?
    - What is the CPU utilization?
    - Is there high system or user CPU usage?
    - Is the cluster under CPU pressure?
    - What percentage of CPU is idle?
    """
    try:
        cluster = _get_reachable_cluster()
        stats = Statistics(cluster)
        return stats.get_cpu()
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def powerscale_stats_network() -> Dict[str, Any]:
    """
    Return 30-second averaged cluster external network traffic metrics.

    This tool samples network statistics 6 times over 30 seconds and returns
    the averaged values. Inform the user that results will take approximately
    30 seconds to collect before responding.

    Response fields:
    - cluster.net.ext.bytes.in.rate:    Inbound bytes per second (from clients)
    - cluster.net.ext.bytes.out.rate:   Outbound bytes per second (to clients)
    - cluster.net.ext.packets.in.rate:  Inbound packets per second
    - cluster.net.ext.packets.out.rate: Outbound packets per second
    - cluster.net.ext.errors.in.rate:   Inbound network errors per second
    - cluster.net.ext.errors.out.rate:  Outbound network errors per second

    Tip: Use bytes_to_human tool to convert byte rates to human-readable
    formats (MiB/s, GiB/s). Non-zero error rates may indicate cabling,
    switch, or NIC issues.

    Use this tool when the user asks:
    - What is the network throughput?
    - How much data is flowing to/from clients?
    - Are there network errors on the cluster?
    - What is the inbound or outbound bandwidth utilization?
    - Is there a network bottleneck?
    """
    try:
        cluster = _get_reachable_cluster()
        stats = Statistics(cluster)
        return stats.get_network()
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def powerscale_stats_disk() -> Dict[str, Any]:
    """
    Return 30-second averaged cluster disk I/O metrics.

    This tool samples disk statistics 6 times over 30 seconds and returns
    the averaged values. Inform the user that results will take approximately
    30 seconds to collect before responding.

    Response fields:
    - cluster.disk.bytes.in.rate:  Bytes written to disk per second
    - cluster.disk.bytes.out.rate: Bytes read from disk per second
    - cluster.disk.xfers.in.rate:  Write I/O operations per second (IOPS)
    - cluster.disk.xfers.out.rate: Read I/O operations per second (IOPS)
    - cluster.disk.xfers.rate:     Total I/O operations per second (IOPS)

    Tip: Use bytes_to_human tool to convert byte rates to human-readable
    formats. High disk I/O with low cache hit rates may indicate the workload
    is not cache-friendly.

    Use this tool when the user asks:
    - Is disk I/O high?
    - What is the disk throughput or transfer rate?
    - How many disk I/Os (IOPS) per second?
    - Is there a disk I/O bottleneck?
    - What is the disk read vs write rate?
    """
    try:
        cluster = _get_reachable_cluster()
        stats = Statistics(cluster)
        return stats.get_disk()
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def powerscale_stats_ifs() -> Dict[str, Any]:
    """
    Return 30-second averaged OneFS filesystem I/O rates.

    This tool samples IFS-level statistics 6 times over 30 seconds and returns
    the averaged values. Inform the user that results will take approximately
    30 seconds to collect before responding.

    Response fields:
    - ifs.bytes.in.rate:  Bytes written to the filesystem per second
    - ifs.bytes.out.rate: Bytes read from the filesystem per second
    - ifs.ops.in.rate:    Write operations per second at the filesystem layer
    - ifs.ops.out.rate:   Read operations per second at the filesystem layer

    Note: IFS rates reflect activity at the OneFS filesystem layer, which
    includes cache effects. Disk rates (powerscale_stats_disk) reflect
    actual physical disk I/O. The difference between IFS and disk rates
    indicates how much data is being served from cache.

    Use this tool when the user asks:
    - What is the overall filesystem throughput?
    - How many IOPS is the cluster handling?
    - What is the filesystem read vs write rate?
    - How much data is the filesystem serving per second?
    """
    try:
        cluster = _get_reachable_cluster()
        stats = Statistics(cluster)
        return stats.get_ifs()
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def powerscale_stats_node() -> Dict[str, Any]:
    """
    Return 30-second averaged per-node performance metrics.

    This tool samples node statistics 6 times over 30 seconds and returns
    the averaged values per node. Inform the user that results will take
    approximately 30 seconds to collect before responding.

    Response is a dict keyed by "node_<devid>" (e.g. "node_1", "node_2").
    Each node entry contains:
    - node.cpu.throttling: CPU throttling percentage (>0 indicates thermal
                           or power-related throttling)
    - node.load.1min:      1-minute CPU load average
    - node.load.5min:      5-minute CPU load average
    - node.load.15min:     15-minute CPU load average
    - node.memory.used:    Memory in use (bytes)
    - node.memory.free:    Free memory (bytes)
    - node.open.files:     Number of open file handles on this node

    Tip: Use bytes_to_human tool to convert memory values to human-readable
    formats. Load averages above the number of CPU cores on a node indicate
    CPU saturation.

    DEPLOYMENT NOTES:
    Per-node statistics may be unavailable on virtual cluster deployments.
    If unavailable, the result will include a "_warning" key with guidance.
    Use cluster-level statistics (powerscale_stats_cpu, powerscale_stats_network,
    etc.) as an alternative for virtual clusters.

    Use this tool when the user asks:
    - Which nodes are the busiest?
    - What is the load average per node?
    - Is any node overloaded or struggling?
    - How much memory is free on each node?
    - Is there CPU throttling on any node?
    - Are there hot spots in the cluster?
    """
    try:
        cluster = _get_reachable_cluster()
        stats = Statistics(cluster)
        return stats.get_node_performance()
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def powerscale_stats_protocol() -> Dict[str, Any]:
    """
    Return 30-second averaged per-protocol operation rates.

    This tool samples protocol statistics 6 times over 30 seconds and returns
    the averaged values. Inform the user that results will take approximately
    30 seconds to collect before responding.

    Response fields (all values are operations per second):
    - cluster.protostats.nfs:   NFSv3 operation rate
    - cluster.protostats.nfs4:  NFSv4 operation rate
    - cluster.protostats.cifs:  SMB1/CIFS operation rate
    - cluster.protostats.smb2:  SMB2/SMB3 operation rate
    - cluster.protostats.http:  HTTP/S3 operation rate
    - cluster.protostats.ftp:   FTP operation rate
    - cluster.protostats.hdfs:  HDFS operation rate

    Note: These are current operation rates (ops/sec), not cumulative totals.
    A value of 0 means no active I/O for that protocol.

    Use this tool when the user asks:
    - How many NFS or SMB operations per second?
    - Which protocol has the most traffic?
    - Is NFS or CIFS/SMB busy right now?
    - What is the HTTP or S3 operation rate?
    - Which protocols are active on the cluster?
    """
    try:
        cluster = _get_reachable_cluster()
        stats = Statistics(cluster)
        return stats.get_protocol()
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def powerscale_stats_clients() -> Dict[str, Any]:
    """
    Return 30-second averaged client connection counts by protocol.

    This tool samples client statistics 6 times over 30 seconds and returns
    the averaged values. Inform the user that results will take approximately
    30 seconds to collect before responding.

    Response fields (cluster-aggregate counts across all nodes):
    Active clients (currently performing I/O):
    - node.clientstats.active.nfs:   Active NFSv3 clients
    - node.clientstats.active.nfs4:  Active NFSv4 clients
    - node.clientstats.active.cifs:  Active SMB1/CIFS clients
    - node.clientstats.active.smb2:  Active SMB2/SMB3 clients
    - node.clientstats.active.http:  Active HTTP clients
    - node.clientstats.active.ftp:   Active FTP clients
    - node.clientstats.active.hdfs:  Active HDFS clients

    Connected clients (mounted/connected but not necessarily active):
    - node.clientstats.connected.nfs:  Connected NFS clients
    - node.clientstats.connected.cifs: Connected CIFS clients
    - node.clientstats.connected.http: Connected HTTP clients

    Tip: The difference between connected and active counts shows idle
    connections. Large numbers of connected but inactive clients can
    consume resources.

    Use this tool when the user asks:
    - How many clients are connected to the cluster?
    - How many active NFS mounts or sessions?
    - How many CIFS/SMB sessions are there?
    - How many clients are actively doing I/O vs just mounted?
    - What is the client load on the cluster?
    """
    try:
        cluster = _get_reachable_cluster()
        stats = Statistics(cluster)
        return stats.get_clients()
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def powerscale_stats_get(
    keys: List[str],
    show_nodes: bool = False,
) -> Dict[str, Any]:
    """
    Retrieve 30-second averaged statistics for arbitrary user-specified stat keys.

    This is a power-user tool for querying any statistics keys by name.
    Results are averaged over 6 samples taken at 5-second intervals (30 seconds
    total). Inform the user that results will take approximately 30 seconds
    to collect before responding.

    Arguments:
    - keys: List of statistics key strings to retrieve. Use powerscale_stats_keys
            to discover available keys. Example keys:
              "cluster.cpu.sys.avg"
              "node.disk.bytes.in.rate.avg"
              "ifs.bytes.in.rate"
              "cluster.protostats.nfs"
    - show_nodes: If True, results are grouped by node device ID
                  ({"node_1": {key: value}, "node_2": {...}}). If False
                  (default), cluster-aggregate values are returned.

    Use this tool when the user wants to:
    - Query a specific statistic not covered by other powerscale_stats_* tools
    - Retrieve multiple heterogeneous stats in a single call
    - Investigate a specific performance metric by key name
    - Build custom performance dashboards or reports
    """
    try:
        cluster = _get_reachable_cluster()
        stats = Statistics(cluster)
        return stats.get_current(keys, show_nodes=show_nodes)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def powerscale_stats_keys(
    limit: int = 100,
    resume: Optional[str] = None,
    queryable: bool = False,
) -> Dict[str, Any]:
    """
    List available statistics keys with metadata (description, units, type).

    This tool is useful for discovering what performance metrics are available
    on the cluster. Results are not averaged — this is a metadata lookup only.

    Response fields:
    - keys: List of key objects, each containing:
        - key:         The stat key string (use with powerscale_stats_get)
        - description: Human-readable description of the metric
        - units:       Units of measurement (e.g. "%" , "B/s", "ops/s")
        - type:        Data type (e.g. "rate", "gauge", "counter")
    - resume: Pagination token (pass to next call if has_more is True)
    - has_more: Whether additional keys are available

    Arguments:
    - limit:     Number of keys to return per page (default 100)
    - resume:    Pagination token from a previous call
    - queryable: If True, return only keys that support querying (default False)

    Use this tool when the user asks:
    - What statistics or performance metrics are available?
    - What keys can I use with powerscale_stats_get?
    - Is there a stat key for [specific metric]?
    - What units does [stat key] use?
    """
    resume = None if resume in (None, "null", "None") else resume
    try:
        cluster = _get_reachable_cluster()
        stats = Statistics(cluster)
        return stats.get_keys(limit=limit, resume=resume, queryable=queryable)
    except Exception as e:
        return f"Error: {e}"


_apply_startup_config()


app = mcp.http_app()
app.state.json_response = True


