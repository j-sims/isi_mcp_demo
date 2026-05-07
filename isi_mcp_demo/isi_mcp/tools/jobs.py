from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.jobs import Jobs
from modules.utils.paging import normalize_resume
from typing import Optional


@safe_tool(group="jobs", mode="read")
def powerscale_job_list(cluster_name: str = None) -> dict:
    """
    List all running and paused jobs on the PowerScale cluster.

    Returns active job instances from the Job Engine, including job type,
    state (running/paused/waiting), priority, impact policy, progress,
    and phase information.

    Returns:
    - items: List of job objects
    - total: Total number of active jobs
    """
    cluster = get_cluster(cluster_name)
    j = Jobs(cluster)
    return j.list_jobs()


@safe_tool(group="jobs", mode="read")
def powerscale_job_get(job_id: int, cluster_name: str = None) -> dict:
    """
    Get details for a specific running or paused job.

    Arguments:
    - job_id: The job instance ID
    """
    cluster = get_cluster(cluster_name)
    j = Jobs(cluster)
    return j.get_job(job_id)


@safe_tool(group="jobs", mode="read")
def powerscale_job_recent_get(limit: int = 50, cluster_name: str = None) -> dict:
    """
    List recently completed jobs on the PowerScale cluster.

    Shows jobs that have finished, failed, or been cancelled. Useful for
    post-execution auditing and troubleshooting.

    Arguments:
    - limit: Maximum number of recent jobs to return (default 50)

    Returns:
    - items: List of recently completed job objects
    - total: Total count
    """
    cluster = get_cluster(cluster_name)
    j = Jobs(cluster)
    return j.get_recent(limit=limit)


@safe_tool(group="jobs", mode="read")
def powerscale_job_summary_get(cluster_name: str = None) -> dict:
    """
    Get the Job Engine status summary.

    Returns high-level engine state including whether the job engine is
    running, paused, or disabled, and aggregate counts of active jobs.
    """
    cluster = get_cluster(cluster_name)
    j = Jobs(cluster)
    return j.get_summary()


@safe_tool(group="jobs", mode="read")
def powerscale_job_types_get(cluster_name: str = None) -> dict:
    """
    List all available job types on the PowerScale cluster.

    Returns the full catalog of job types (e.g. TreeDelete, SmartPools,
    MultiScan, Collect, ShadowStoreProtect, etc.) with their descriptions,
    enabled state, priority, impact policy, and schedule.

    Returns:
    - items: List of job type objects
    """
    cluster = get_cluster(cluster_name)
    j = Jobs(cluster)
    return j.get_types()


@safe_tool(group="jobs", mode="read")
def powerscale_job_type_get(job_type_id: str, cluster_name: str = None) -> dict:
    """
    Get details for a specific job type.

    Arguments:
    - job_type_id: The job type name (e.g. 'TreeDelete', 'SmartPools',
                   'Collect', 'MultiScan', 'ShadowStoreProtect', 'FlexProtect')
    """
    cluster = get_cluster(cluster_name)
    j = Jobs(cluster)
    return j.get_type(job_type_id)


@safe_tool(group="jobs", mode="read")
def powerscale_job_events_get(
    resume: Optional[str] = None,
    limit: int = 100,
    job_id: Optional[int] = None,
    job_type: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Retrieve Job Engine events with optional filtering and pagination.

    Events include job state changes, completions, failures, and progress updates.

    Arguments:
    - resume: Pagination token from a previous call
    - limit: Maximum number of results (default 100)
    - job_id: Filter events by job instance ID
    - job_type: Filter events by job type name
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    j = Jobs(cluster)
    return j.get_events(resume=resume, limit=limit, job_id=job_id, job_type=job_type)


@safe_tool(group="jobs", mode="read")
def powerscale_job_reports_get(
    resume: Optional[str] = None,
    limit: int = 100,
    job_id: Optional[int] = None,
    job_type: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    List Job Engine reports with optional filtering and pagination.

    Reports contain detailed execution results for completed jobs.

    Arguments:
    - resume: Pagination token from a previous call
    - limit: Maximum number of results (default 100)
    - job_id: Filter reports by job instance ID
    - job_type: Filter reports by job type name
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    j = Jobs(cluster)
    return j.get_reports(resume=resume, limit=limit, job_id=job_id, job_type=job_type)


@safe_tool(group="jobs", mode="read")
def powerscale_job_statistics_get(cluster_name: str = None) -> dict:
    """
    Get Job Engine statistics.

    Returns aggregate statistics about job execution, throughput, and resource usage.
    """
    cluster = get_cluster(cluster_name)
    j = Jobs(cluster)
    return j.get_statistics()


@safe_tool(group="jobs", mode="read")
def powerscale_job_policies_get(cluster_name: str = None) -> dict:
    """
    List all job impact policies.

    Impact policies control how aggressively jobs consume cluster resources
    (e.g. LOW, MEDIUM, HIGH, OFF_HOURS).

    Returns:
    - items: List of impact policy objects
    """
    cluster = get_cluster(cluster_name)
    j = Jobs(cluster)
    return j.get_policies()


@safe_tool(group="jobs", mode="read")
def powerscale_job_policy_get(policy_id: str, cluster_name: str = None) -> dict:
    """
    Get details for a specific job impact policy.

    Arguments:
    - policy_id: The impact policy name (e.g. 'LOW', 'MEDIUM', 'HIGH', 'OFF_HOURS')
    """
    cluster = get_cluster(cluster_name)
    j = Jobs(cluster)
    return j.get_policy(policy_id)


@safe_tool(group="jobs", mode="read")
def powerscale_job_settings_get(cluster_name: str = None) -> dict:
    """
    Get Job Engine generic settings.

    Returns engine-level configuration like default priority, scheduling parameters,
    and global enable/disable state.
    """
    cluster = get_cluster(cluster_name)
    j = Jobs(cluster)
    return j.get_settings()
