from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.quotas import Quotas
from modules.utils.paging import normalize_resume, paginated_result
from typing import Dict, Any, Optional


@safe_tool(group="quotas", mode="read")
def powerscale_quota_get(
    limit: int = 1000,
    resume: Optional[str] = None,
    cluster_name: str = None,
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
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    return paginated_result(Quotas(cluster).get(limit=limit, resume=resume), limit)

@safe_tool(group="quotas", mode="write")
def powerscale_quota_set(path:str, size:int, cluster_name: str = None) -> str:
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
    cluster = get_cluster(cluster_name)
    quotas = Quotas(cluster)
    return quotas.set_hard_quota(path, size)

@safe_tool(group="quotas", mode="write")
def powerscale_quota_increment(path:str, size:int, cluster_name: str = None) -> str:
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
    cluster = get_cluster(cluster_name)
    quotas = Quotas(cluster)
    return quotas.increment_hard_quota(path, size)

@safe_tool(group="quotas", mode="write")
def powerscale_quota_decrement(path:str, size:int, cluster_name: str = None) -> str:
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
    cluster = get_cluster(cluster_name)
    quotas = Quotas(cluster)
    return quotas.decrement_hard_quota(path, size)

@safe_tool(group="quotas", mode="write")
def powerscale_quota_create(path: str, quota_type: str, limit_size: str,
                             soft_grace_period: str = None,
                             soft_grace_period_unit: str = "days",
                             include_overheads: bool = False,
                             persona: str = None,
                             cluster_name: str = None) -> dict:
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
    cluster = get_cluster(cluster_name)
    quotas = Quotas(cluster)
    return quotas.add_quota(path=path, quota_type=quota_type,
                            limit_size=limit_size,
                            soft_grace_period=soft_grace_period,
                            soft_grace_period_unit=soft_grace_period_unit,
                            include_overheads=include_overheads,
                            persona=persona)

@safe_tool(group="quotas", mode="write")
def powerscale_quota_remove(path: str, quota_type: str, cluster_name: str = None) -> dict:
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
    cluster = get_cluster(cluster_name)
    quotas = Quotas(cluster)
    return quotas.remove_quota(path=path, quota_type=quota_type)
