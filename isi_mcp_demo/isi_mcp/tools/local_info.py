from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.local_info import LocalInfo
from modules.onefs.v9_12_0.api_sessions import ApiSessions
from modules.onefs.v9_12_0.groupnets_summary import GroupnetsSummary


@safe_tool(group="local_info", mode="read")
def powerscale_local_cluster_time_get(cluster_name: str = None) -> dict:
    """
    Get the current time on the local cluster node.

    Returns the node's system clock time. Useful for verifying NTP sync
    and time consistency across the cluster.
    """
    cluster = get_cluster(cluster_name)
    li = LocalInfo(cluster)
    return li.get_cluster_time()


@safe_tool(group="local_info", mode="read")
def powerscale_local_network_interfaces_get(cluster_name: str = None) -> dict:
    """
    List network interfaces on the local cluster node.

    Returns interface details including name, IP addresses, MTU, flags,
    and link status.

    Returns:
    - items: List of network interface objects
    """
    cluster = get_cluster(cluster_name)
    li = LocalInfo(cluster)
    return li.get_network_interfaces()


@safe_tool(group="local_info", mode="read")
def powerscale_firmware_status_get(cluster_name: str = None) -> dict:
    """
    Get firmware status for the cluster.

    Returns current firmware versions and upgrade status.
    """
    cluster = get_cluster(cluster_name)
    li = LocalInfo(cluster)
    return li.get_firmware_status()


@safe_tool(group="local_info", mode="read")
def powerscale_firmware_device_get(cluster_name: str = None) -> dict:
    """
    Get firmware device information for the cluster.

    Returns per-node firmware device status and version details.

    Returns:
    - items: List of node firmware objects
    """
    cluster = get_cluster(cluster_name)
    li = LocalInfo(cluster)
    return li.get_firmware_device()


@safe_tool(group="local_info", mode="read")
def powerscale_node_internal_ip_get(node_lnn: int, cluster_name: str = None) -> dict:
    """
    Get the internal IP address for a specific cluster node.

    Arguments:
    - node_lnn: Logical Node Number (LNN) of the node
    """
    cluster = get_cluster(cluster_name)
    li = LocalInfo(cluster)
    return li.get_node_internal_ip(node_lnn)


@safe_tool(group="local_info", mode="read")
def powerscale_os_security_get(cluster_name: str = None) -> dict:
    """
    Get per-node OS security settings status.

    Returns OS-level security configuration such as FIPS mode, secure boot
    status, and other security posture information.
    """
    cluster = get_cluster(cluster_name)
    li = LocalInfo(cluster)
    return li.get_os_security()


@safe_tool(group="api_sessions", mode="read")
def powerscale_api_session_settings_get(cluster_name: str = None) -> dict:
    """
    Get HTTP API session settings.

    Returns session timeout, maximum sessions, and other session
    configuration parameters for the Platform API.
    """
    cluster = get_cluster(cluster_name)
    api_s = ApiSessions(cluster)
    return api_s.get_session_settings()


@safe_tool(group="api_sessions", mode="read")
def powerscale_api_session_invalidations_get(cluster_name: str = None) -> dict:
    """
    List all Platform API session invalidations.

    Returns:
    - items: List of session invalidation objects
    """
    cluster = get_cluster(cluster_name)
    api_s = ApiSessions(cluster)
    return api_s.list_invalidations()


@safe_tool(group="api_sessions", mode="read")
def powerscale_api_session_invalidation_get(invalidation_id: str, cluster_name: str = None) -> dict:
    """
    Get a specific Platform API session invalidation.

    Arguments:
    - invalidation_id: The invalidation identifier
    """
    cluster = get_cluster(cluster_name)
    api_s = ApiSessions(cluster)
    return api_s.get_invalidation(invalidation_id)


@safe_tool(group="groupnets_summary", mode="read")
def powerscale_groupnets_summary_get(cluster_name: str = None) -> dict:
    """
    Get groupnet summary information.

    Returns aggregate information about network groupnets including count,
    names, and subnet details. A lighter-weight alternative to
    powerscale_network_groupnets_get for quick topology overview.
    """
    cluster = get_cluster(cluster_name)
    gs = GroupnetsSummary(cluster)
    return gs.get()
