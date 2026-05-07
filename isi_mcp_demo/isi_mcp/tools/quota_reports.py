from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.quota_reports import QuotaReports
from modules.onefs.v9_12_0.debug_stats import DebugStats


@safe_tool(group="quota_reports", mode="read")
def powerscale_quota_report_about_get(report_id: str, cluster_name: str = None) -> dict:
    """
    Get metadata about a specific quota report.

    Returns report info such as generation time, scope, and parameters.

    Arguments:
    - report_id: The quota report ID
    """
    cluster = get_cluster(cluster_name)
    qr = QuotaReports(cluster)
    return qr.get_report_about(report_id)


@safe_tool(group="debug", mode="read")
def powerscale_debug_stats_get(cluster_name: str = None) -> dict:
    """
    Get cumulative Platform API call statistics per resource.

    Returns call counts for each API resource endpoint, useful for
    understanding API usage patterns and diagnosing performance bottlenecks.
    """
    cluster = get_cluster(cluster_name)
    ds = DebugStats(cluster)
    return ds.get()
