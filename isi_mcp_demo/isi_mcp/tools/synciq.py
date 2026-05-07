from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.synciq import SyncIQ
from modules.onefs.v9_12_0.sync_reports import SyncReports
from modules.utils.paging import normalize_resume
from typing import Dict, Any, Optional


@safe_tool(group="synciq", mode="read")
def powerscale_synciq_get(cluster_name: str = None) -> Dict[str, Any]:
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
    cluster = get_cluster(cluster_name)
    synciq = SyncIQ(cluster)
    return synciq.get()

@safe_tool(group="synciq", mode="write")
def powerscale_synciq_create(policy_name: str, source_path: str,
                              target_host: str, target_path: str,
                              action: str = "sync", schedule: str = None,
                              description: str = None, enabled: bool = None,
                              cluster_name: str = None) -> dict:
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
    cluster = get_cluster(cluster_name)
    synciq = SyncIQ(cluster)
    return synciq.add(policy_name=policy_name, source_path=source_path,
                      target_host=target_host, target_path=target_path,
                      action=action, schedule=schedule, description=description,
                      enabled=enabled)

@safe_tool(group="synciq", mode="write")
def powerscale_synciq_remove(policy_name: str, cluster_name: str = None) -> dict:
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
    cluster = get_cluster(cluster_name)
    synciq = SyncIQ(cluster)
    return synciq.remove(policy_name=policy_name)

@safe_tool(group="synciq_reports", mode="read")
def powerscale_synciq_report_subreports_get(
    report_id: str,
    resume: Optional[str] = None,
    limit: int = 100,
    cluster_name: str = None,
) -> dict:
    """
    List subreports for a SyncIQ policy report.

    Subreports provide per-run execution details (bytes transferred, files
    scanned, errors, duration, etc.) for SyncIQ replication operations.

    Arguments:
    - report_id: The SyncIQ report ID (from powerscale_synciq_get or sync report APIs)
    - resume: Pagination token from a previous call
    - limit: Maximum number of results (default 100)
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    sr = SyncReports(cluster)
    return sr.get_subreports(report_id, resume=resume, limit=limit)


@safe_tool(group="synciq_reports", mode="read")
def powerscale_synciq_report_subreport_get(report_id: str, subreport_id: str, cluster_name: str = None) -> dict:
    """
    Get a specific subreport from a SyncIQ report.

    Arguments:
    - report_id: The SyncIQ report ID
    - subreport_id: The subreport ID
    """
    cluster = get_cluster(cluster_name)
    sr = SyncReports(cluster)
    return sr.get_subreport(report_id, subreport_id)
