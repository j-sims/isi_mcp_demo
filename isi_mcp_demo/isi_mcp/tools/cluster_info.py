from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.cluster_nodes import ClusterNodes
from modules.onefs.v9_12_0.storagepool_nodetypes import StoragepoolNodetypes
from modules.onefs.v9_12_0.license import License
from modules.onefs.v9_12_0.zones_summary import ZonesSummary
from modules.utils.paging import normalize_resume
from modules.onefs.v9_12_0.hardware import Hardware
from typing import Optional


@safe_tool(group="cluster_nodes", mode="read")
def powerscale_cluster_nodes_get(cluster_name: str = None) -> dict:
    """
    List all nodes in the PowerScale cluster with status, state, and version info.

    Returns a list of node objects. Each node includes:
    - lnn: Logical Node Number (the node's cluster position)
    - id: Node ID
    - node_state: Current operational state (e.g. read-only, smartfail flags)
    - onefs_version: The OneFS version running on the node
    - down_peer: Whether peer connectivity is lost
    - error: Any node-level errors

    Use powerscale_cluster_node_get_by_id for full hardware, drive, sensor,
    and partition details on a specific node.
    """
    cluster = get_cluster(cluster_name)
    nodes = ClusterNodes(cluster)
    return nodes.get()


@safe_tool(group="cluster_nodes", mode="read")
def powerscale_cluster_node_get_by_id(node_id: int, cluster_name: str = None) -> dict:
    """
    Get detailed information for a specific cluster node by its Logical Node Number.

    Returns comprehensive node details including:
    - hardware: Product name, serial number, chassis info
    - drives: Drive status and health per slot
    - partitions: Filesystem partition usage (/, /var, /var/crash, etc.)
    - sensors: Environmental sensors (temperature, voltage, fan RPM)
    - sleds: Drive sled information
    - state: Read-only, smartfail, service light states
    - status: CPU usage, battery, NVRAM, power supplies
    - internal_ip_address: Internal cluster network address

    Arguments:
    - node_id: Logical Node Number (LNN) of the node (use powerscale_cluster_nodes_get
               to list nodes and find their LNNs)
    """
    cluster = get_cluster(cluster_name)
    nodes = ClusterNodes(cluster)
    return nodes.get_by_id(node_id)


@safe_tool(group="storagepool_nodetypes", mode="read")
def powerscale_storagepool_nodetypes_get(cluster_name: str = None) -> dict:
    """
    List all storage pool node types configured on the cluster.

    Node types categorize compatible hardware nodes for storage pool management.
    Each entry includes:
    - id: Node type ID (use with powerscale_storagepool_nodetype_get_by_id)
    - product_name: The hardware product model name
    - nodes: List of node LNNs belonging to this node type
    - manual: Whether the node type assignment was manually configured
    """
    cluster = get_cluster(cluster_name)
    nodetypes = StoragepoolNodetypes(cluster)
    return nodetypes.get()


@safe_tool(group="storagepool_nodetypes", mode="read")
def powerscale_storagepool_nodetype_get_by_id(nodetype_id: int, cluster_name: str = None) -> dict:
    """
    Get details for a specific storage pool node type by ID.

    Arguments:
    - nodetype_id: The integer node type ID (use powerscale_storagepool_nodetypes_get
                   to list node types and find their IDs)
    """
    cluster = get_cluster(cluster_name)
    nodetypes = StoragepoolNodetypes(cluster)
    return nodetypes.get_by_id(nodetype_id)


@safe_tool(group="licensing", mode="read")
def powerscale_license_get(resume: Optional[str] = None, cluster_name: str = None) -> dict:
    """
    List all installed PowerScale feature licenses with their status and expiry info.

    Returns a paginated list of license objects. Each license includes:
    - id / name: License feature name (e.g. "SmartQuotas", "SnapshotIQ", "SyncIQ",
                 "SmartConnect_Advanced", "DataMover", "HDFS", "CloudPools")
    - status: One of: Evaluation, Activated, Expired, Unlicensed
    - expiration: Expiration date string (or null for perpetual licenses)
    - days_to_expiry: Days remaining (negative = already expired)
    - days_since_expiry: Days since expiry (if expired)
    - expiring_alert: True if license is about to expire
    - expired_alert: True if license has expired
    - tiers: License tier entitlement details (if applicable)

    Use resume token for pagination if the result includes a non-null resume value.

    Arguments:
    - resume: Pagination token from a previous call (optional)
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    lic = License(cluster)
    return lic.get(resume=resume)


@safe_tool(group="licensing", mode="read")
def powerscale_license_get_by_name(name: str, cluster_name: str = None) -> dict:
    """
    Get license details for a specific PowerScale feature by name.

    Common license names:
    - "HDFS"                  - Hadoop Distributed File System protocol
    - "SmartQuotas"           - Storage quota management
    - "SnapshotIQ"            - Snapshot and snapshot scheduling
    - "SyncIQ"                - Replication and failover
    - "SmartDedupe"           - Data deduplication
    - "SmartConnect"          - Basic SmartConnect DNS load balancing
    - "SmartConnect_Advanced" - Advanced SmartConnect with connection policies
    - "InsightIQ"             - Analytics and reporting
    - "DataMover"             - CloudPools data movement
    - "CloudPools"            - Cloud tiering

    Arguments:
    - name: The license feature name (case-sensitive)
    """
    cluster = get_cluster(cluster_name)
    lic = License(cluster)
    return lic.get_by_name(name)


@safe_tool(group="zones_summary", mode="read")
def powerscale_zones_summary_get(groupnet: Optional[str] = None, cluster_name: str = None) -> dict:
    """
    Retrieve a lightweight summary of all access zones on the cluster.

    Returns the total zone count and a list of zone base paths. This is a
    quick way to enumerate zones without retrieving full configuration details
    (auth providers, SMB settings, etc.) that powerscale_zones_get provides.

    Response structure:
    {
      "count": <int>,      - Total number of access zones
      "zones": [<path>, ...]  - List of zone base paths (e.g. "/ifs", "/ifs/data/zone1")
    }

    Arguments:
    - groupnet: Optional — filter summary to zones in this groupnet (e.g. "groupnet0")
    """
    cluster = get_cluster(cluster_name)
    zs = ZonesSummary(cluster)
    return zs.get(groupnet=groupnet)


@safe_tool(group="zones_summary", mode="read")
def powerscale_zones_summary_zone_get(zone_id, cluster_name: str = None) -> dict:
    """
    Retrieve non-privileged summary information for a specific access zone.

    Returns the base path for the zone. This endpoint is accessible without
    elevated privileges, making it useful for verifying zone existence and
    path from unprivileged contexts.

    Arguments:
    - zone_id: The numeric zone ID (e.g. 1) or zone name (e.g. "System").
               Use powerscale_zones_get to list available zones and get their
               zone_id field. For full zone details with auth providers, use
               powerscale_zones_get.
    """
    cluster = get_cluster(cluster_name)
    zs = ZonesSummary(cluster)
    return zs.get_zone(zone_id)


@safe_tool(group="hardware", mode="read")
def powerscale_hardware_fcports_get(cluster_name: str = None) -> dict:
    """
    List all Fibre Channel ports on the PowerScale cluster.

    Returns FC port details including WWNN, WWPN, state, topology, rate,
    and port identifier. Useful for SAN fabric inventory and troubleshooting.

    Returns:
    - items: List of FC port objects
    """
    cluster = get_cluster(cluster_name)
    hw = Hardware(cluster)
    return hw.get_fcports()


@safe_tool(group="hardware", mode="read")
def powerscale_hardware_fcport_get(port_id: str, cluster_name: str = None) -> dict:
    """
    Get details for a specific Fibre Channel port.

    Returns WWNN, WWPN, state, topology, rate, and firmware info.

    Arguments:
    - port_id: The FC port identifier (e.g. '1:0')
    """
    cluster = get_cluster(cluster_name)
    hw = Hardware(cluster)
    return hw.get_fcport(port_id)


@safe_tool(group="hardware", mode="read")
def powerscale_hardware_tapes_get(cluster_name: str = None) -> dict:
    """
    List all tape and changer devices on the PowerScale cluster.

    Returns tape device inventory including device names, types, and status.
    Useful for NDMP backup infrastructure assessment.

    Returns:
    - items: List of tape/changer device objects
    - resume: Pagination token (if more results available)
    """
    cluster = get_cluster(cluster_name)
    hw = Hardware(cluster)
    return hw.get_tapes()
