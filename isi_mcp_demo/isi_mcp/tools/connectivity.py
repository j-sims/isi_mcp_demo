from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.connectivity import Connectivity


@safe_tool(group="connectivity", mode="read")
def powerscale_connectivity_settings_get(cluster_name: str = None) -> dict:
    """
    Get connectivity diagnostic configuration settings.

    Returns configuration for Dell connectivity services including proxy
    settings, gateway info, and service enablement status.
    """
    cluster = get_cluster(cluster_name)
    conn = Connectivity(cluster)
    return conn.get_settings()


@safe_tool(group="connectivity", mode="read")
def powerscale_connectivity_status_get(cluster_name: str = None) -> dict:
    """
    Get connectivity diagnostic current status.

    Returns current connectivity health, last check time, and any issues.
    """
    cluster = get_cluster(cluster_name)
    conn = Connectivity(cluster)
    return conn.get_status()


@safe_tool(group="connectivity", mode="read")
def powerscale_connectivity_license_get(cluster_name: str = None) -> dict:
    """
    Get connectivity service license activation status.
    """
    cluster = get_cluster(cluster_name)
    conn = Connectivity(cluster)
    return conn.get_license()


@safe_tool(group="connectivity", mode="read")
def powerscale_connectivity_terms_get(cluster_name: str = None) -> dict:
    """
    Get telemetry notice text for Dell Technologies connectivity services.

    Returns the terms and acceptance status for telemetry data collection.
    """
    cluster = get_cluster(cluster_name)
    conn = Connectivity(cluster)
    return conn.get_terms()


@safe_tool(group="connectivity", mode="read")
def powerscale_connectivity_tasks_get(cluster_name: str = None) -> dict:
    """
    List all connectivity diagnostic tasks.

    Returns:
    - items: List of connectivity task objects
    """
    cluster = get_cluster(cluster_name)
    conn = Connectivity(cluster)
    return conn.list_tasks()


@safe_tool(group="connectivity", mode="read")
def powerscale_connectivity_task_get(task_id: str, cluster_name: str = None) -> dict:
    """
    Get a specific connectivity diagnostic task by ID.

    Arguments:
    - task_id: The task identifier
    """
    cluster = get_cluster(cluster_name)
    conn = Connectivity(cluster)
    return conn.get_task(task_id)
