from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.supportassist import SupportAssist


@safe_tool(group="supportassist", mode="read")
def powerscale_supportassist_settings_get(cluster_name: str = None) -> dict:
    """
    Get SupportAssist configuration settings.

    Returns connection settings, proxy configuration, auto-case creation status,
    and gateway settings for Dell SupportAssist integration.
    """
    cluster = get_cluster(cluster_name)
    sa = SupportAssist(cluster)
    return sa.get_settings()


@safe_tool(group="supportassist", mode="read")
def powerscale_supportassist_status_get(cluster_name: str = None) -> dict:
    """
    Get SupportAssist current status.

    Returns connectivity status, last contact time, and overall health
    of the SupportAssist service.
    """
    cluster = get_cluster(cluster_name)
    sa = SupportAssist(cluster)
    return sa.get_status()


@safe_tool(group="supportassist", mode="read")
def powerscale_supportassist_license_get(cluster_name: str = None) -> dict:
    """
    Get SupportAssist license activation status.

    Returns whether SupportAssist is activated and license entitlement details.
    """
    cluster = get_cluster(cluster_name)
    sa = SupportAssist(cluster)
    return sa.get_license()


@safe_tool(group="supportassist", mode="read")
def powerscale_supportassist_terms_get(cluster_name: str = None) -> dict:
    """
    Get SupportAssist Terms & Conditions text and acceptance status.
    """
    cluster = get_cluster(cluster_name)
    sa = SupportAssist(cluster)
    return sa.get_terms()


@safe_tool(group="supportassist", mode="read")
def powerscale_supportassist_tasks_get(cluster_name: str = None) -> dict:
    """
    List all SupportAssist tasks.

    Returns pending, running, and completed SupportAssist tasks such as
    log collection, diagnostics uploads, and payload requests.

    Returns:
    - items: List of task objects
    """
    cluster = get_cluster(cluster_name)
    sa = SupportAssist(cluster)
    return sa.list_tasks()


@safe_tool(group="supportassist", mode="read")
def powerscale_supportassist_task_get(task_id: str, cluster_name: str = None) -> dict:
    """
    Get a specific SupportAssist task by ID.

    Arguments:
    - task_id: The task identifier
    """
    cluster = get_cluster(cluster_name)
    sa = SupportAssist(cluster)
    return sa.get_task(task_id)
