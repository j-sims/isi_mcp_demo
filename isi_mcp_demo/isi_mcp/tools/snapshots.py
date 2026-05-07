from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.snapshots import Snapshots
from modules.onefs.v9_12_0.snapshotschedules import SnapshotSchedules
from modules.onefs.v9_12_0.snapshot_changelists import SnapshotChangelists
from modules.utils.paging import normalize_resume, paginated_result
from typing import Dict, Any, Optional


@safe_tool(group="snapshots", mode="read")
def powerscale_snapshot_get(
    limit: int = 1000,
    resume: Optional[str] = None,
    cluster_name: str = None,
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
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    return paginated_result(Snapshots(cluster).get(limit=limit, resume=resume), limit)

@safe_tool(group="snapshots", mode="read")
def powerscale_snapshot_schedule_get(
    limit: int = 1000,
    resume: Optional[str] = None,
    cluster_name: str = None,
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
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    return paginated_result(SnapshotSchedules(cluster).get(limit=limit, resume=resume), limit)

@safe_tool(group="snapshots", mode="write")
def powerscale_snapshot_schedule_create(name: str, path: str, schedule: str,
                                        pattern: str = None, duration: str = None,
                                        alias: str = None,
                                        cluster_name: str = None) -> dict:
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
    cluster = get_cluster(cluster_name)
    schedules = SnapshotSchedules(cluster)
    desired_retention = int(duration) if duration else None
    return schedules.add(name=name, path=path, schedule=schedule,
                         pattern=pattern, desired_retention=desired_retention,
                         alias=alias)

@safe_tool(group="snapshots", mode="write")
def powerscale_snapshot_schedule_remove(name: str, cluster_name: str = None) -> dict:
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
    cluster = get_cluster(cluster_name)
    schedules = SnapshotSchedules(cluster)
    return schedules.remove(name=name)

@safe_tool(group="snapshots", mode="write")
def powerscale_snapshot_create(path: str, snapshot_name: str = None, alias: str = None,
                                desired_retention: int = None, retention_unit: str = "hours",
                                expiration_timestamp: str = None,
                                cluster_name: str = None) -> dict:
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
    cluster = get_cluster(cluster_name)
    snapshots = Snapshots(cluster)
    return snapshots.create(path=path, snapshot_name=snapshot_name, alias=alias,
                           desired_retention=desired_retention,
                           retention_unit=retention_unit,
                           expiration_timestamp=expiration_timestamp)

@safe_tool(group="snapshots", mode="write")
def powerscale_snapshot_delete(snapshot_name: str, cluster_name: str = None) -> dict:
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
    cluster = get_cluster(cluster_name)
    snapshots = Snapshots(cluster)
    return snapshots.delete(snapshot_name=snapshot_name)

@safe_tool(group="snapshots", mode="read")
def powerscale_snapshot_pending_get(begin: int = None, end: int = None,
                                    schedule: str = None, limit: int = 1000,
                                    resume: str = None,
                                    cluster_name: str = None) -> Dict[str, Any]:
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
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    page = Snapshots(cluster).get_pending(begin=begin, end=end, schedule=schedule,
                                          limit=limit, resume=resume)
    return paginated_result(page, limit)

@safe_tool(group="snapshots", mode="write")
def powerscale_snapshot_alias_create(name: str, target: str, cluster_name: str = None) -> dict:
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
    cluster = get_cluster(cluster_name)
    snapshots = Snapshots(cluster)
    return snapshots.create_alias(name=name, target=target)

@safe_tool(group="snapshots", mode="read")
def powerscale_snapshot_alias_get(alias_id: str, cluster_name: str = None) -> dict:
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
    cluster = get_cluster(cluster_name)
    snapshots = Snapshots(cluster)
    return snapshots.get_alias(alias_id=alias_id)

@safe_tool(group="snapshot_changelists", mode="read")
def powerscale_snapshot_changelist_entries_get(
    changelist_id: str,
    resume: Optional[str] = None,
    limit: int = 100,
    cluster_name: str = None,
) -> dict:
    """
    List entries in a snapshot changelist.

    Changelists track file and directory changes between two snapshots.
    Each entry represents a changed file/directory with its change type.

    Arguments:
    - changelist_id: The changelist identifier
    - resume: Pagination token from a previous call
    - limit: Maximum number of results (default 100)
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    sc = SnapshotChangelists(cluster)
    return sc.get_entries(changelist_id, resume=resume, limit=limit)


@safe_tool(group="snapshot_changelists", mode="read")
def powerscale_snapshot_changelist_entry_get(changelist_id: str, entry_id: str, cluster_name: str = None) -> dict:
    """
    Get a specific entry from a snapshot changelist.

    Arguments:
    - changelist_id: The changelist identifier
    - entry_id: The entry ID within the changelist
    """
    cluster = get_cluster(cluster_name)
    sc = SnapshotChangelists(cluster)
    return sc.get_entry(changelist_id, entry_id)


@safe_tool(group="snapshot_changelists", mode="read")
def powerscale_snapshot_changelist_lins_get(
    changelist_id: str,
    resume: Optional[str] = None,
    limit: int = 100,
    cluster_name: str = None,
) -> dict:
    """
    List LIN (Logical Inode Number) entries for a snapshot changelist.

    LIN entries provide inode-level change tracking between snapshots.

    Arguments:
    - changelist_id: The changelist identifier
    - resume: Pagination token from a previous call
    - limit: Maximum number of results (default 100)
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    sc = SnapshotChangelists(cluster)
    return sc.get_lins(changelist_id, resume=resume, limit=limit)


@safe_tool(group="snapshot_changelists", mode="read")
def powerscale_snapshot_changelist_lin_get(changelist_id: str, lin_id: str, cluster_name: str = None) -> dict:
    """
    Get a specific LIN entry from a snapshot changelist.

    Arguments:
    - changelist_id: The changelist identifier
    - lin_id: The LIN (Logical Inode Number)
    """
    cluster = get_cluster(cluster_name)
    sc = SnapshotChangelists(cluster)
    return sc.get_lin(changelist_id, lin_id)
