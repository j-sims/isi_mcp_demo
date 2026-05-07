from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.mpa import MPA


@safe_tool(group="mpa", mode="read")
def powerscale_mpa_approvers_get(cluster_name: str = None) -> dict:
    """
    List all Multi-Party Authorization (MPA) approvers on the cluster.

    MPA requires approval from multiple parties before executing
    privileged operations.

    Returns:
    - items: List of approver objects
    """
    cluster = get_cluster(cluster_name)
    m = MPA(cluster)
    return m.get_approvers()


@safe_tool(group="mpa", mode="read")
def powerscale_mpa_approver_get(approver_id: str, cluster_name: str = None) -> dict:
    """
    Get details for a specific MPA approver.

    Arguments:
    - approver_id: The approver identifier
    """
    cluster = get_cluster(cluster_name)
    m = MPA(cluster)
    return m.get_approver(approver_id)


@safe_tool(group="mpa", mode="read")
def powerscale_mpa_requests_get(cluster_name: str = None) -> dict:
    """
    List all MPA (Multi-Party Authorization) requests.

    Returns pending, approved, and denied authorization requests.

    Returns:
    - items: List of MPA request objects
    """
    cluster = get_cluster(cluster_name)
    m = MPA(cluster)
    return m.list_requests()


@safe_tool(group="mpa", mode="read")
def powerscale_mpa_request_get(request_id: str, cluster_name: str = None) -> dict:
    """
    Get details for a specific MPA request.

    Arguments:
    - request_id: The MPA request identifier
    """
    cluster = get_cluster(cluster_name)
    m = MPA(cluster)
    return m.get_request(request_id)


@safe_tool(group="mpa", mode="read")
def powerscale_mpa_settings_get(cluster_name: str = None) -> dict:
    """
    Get MPA global configuration settings.

    Returns whether MPA is enabled, required approval count, and other
    global configuration parameters.
    """
    cluster = get_cluster(cluster_name)
    m = MPA(cluster)
    return m.get_global_settings()


@safe_tool(group="mpa", mode="read")
def powerscale_mpa_request_lifecycle_get(cluster_name: str = None) -> dict:
    """
    Get MPA request lifecycle configuration.

    Returns timeout values, expiration policies, and other lifecycle
    parameters for MPA authorization requests.
    """
    cluster = get_cluster(cluster_name)
    m = MPA(cluster)
    return m.get_request_lifecycle()


@safe_tool(group="mpa", mode="read")
def powerscale_mpa_privilege_actions_get(cluster_name: str = None) -> dict:
    """
    Get MPA privileged action metadata.

    Returns the list of actions that require Multi-Party Authorization
    and their associated metadata.
    """
    cluster = get_cluster(cluster_name)
    m = MPA(cluster)
    return m.get_privilege_action_metadata()


@safe_tool(group="mpa", mode="read")
def powerscale_mpa_trust_anchors_get(cluster_name: str = None) -> dict:
    """
    List trusted root CAs for MPA.

    Returns:
    - items: List of trust anchor (CA certificate) objects
    """
    cluster = get_cluster(cluster_name)
    m = MPA(cluster)
    return m.list_trust_anchors()
