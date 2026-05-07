from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.verify import Verify
from modules.onefs.v9_12_0.capacity import Capacity
from modules.onefs.v9_12_0.config import Config


@safe_tool(group="verify", mode="read")
def powerscale_cluster_verify(cluster_name: str = None) -> dict:
    """
    Perform a comprehensive cluster state verification on the PowerScale (formerly Isilon) cluster.

    This tool runs a series of diagnostic checks against the live cluster and returns
    a pass/fail result with an explanation. The checks are performed in priority order
    and the first failure stops the sequence — this means the most critical issue is
    always reported first.

    Verification checks performed (in order):
    1. Quorum — Is the cluster in quorum? Loss of quorum is a critical failure
       indicating the cluster cannot reach consensus among its nodes.
    2. Service light — Is the front-panel service light illuminated? An active
       service light indicates a hardware issue requiring physical attention.
    3. Critical events — Are there unresolved or un-ignored critical events?
       These are high-severity alerts that require administrator action.
    4. Network connectivity — Are all external IPs defined on the cluster
       responding to ping? Unreachable IPs indicate network or node problems.
    5. Capacity — Does the cluster have more than 20% free space? Below this
       threshold the cluster is at risk of performance degradation or running
       out of space.

    Response fields:
    - status: Boolean — True means verification passed, False means verification failed
    - message: Human-readable explanation of the result

    Use this tool to answer questions such as:
    - Is the PowerScale cluster in a good operational state?
    - Are there any problems with the cluster right now?
    - Is the cluster in quorum?
    - Are there any critical alerts or events?
    - Can all cluster nodes be reached on the network?
    - Is the cluster running low on disk space?
    """

    cluster = get_cluster(cluster_name)
    verifier = Verify(cluster)
    return verifier.verify()

@safe_tool(group="capacity", mode="read")
def powerscale_capacity(cluster_name: str = None) -> dict:
    """
    Return real-time storage capacity statistics for the PowerScale cluster.

    This tool queries the cluster API at call time and returns current-state
    capacity data. All size values are in bytes — use the bytes_to_human tool
    to convert them to human-readable formats (GiB, TiB, etc.) when presenting
    results to the user.

    Response fields:
    - ifs.bytes.avail: Available (unused) space on the cluster in bytes
    - ifs.bytes.used: Space currently consumed on the cluster in bytes
    - ifs.bytes.total: Total raw capacity of the cluster in bytes
    - cluster.data.reduce.ratio.dedupe: Data deduplication ratio (e.g. 1.5
      means 1.5x deduplication savings)
    - cluster.compression.overall.ratio: Data compression ratio (e.g. 2.0
      means data is compressed to half its original size)

    Use this tool to answer questions such as:
    - How much data is stored on the PowerScale cluster?
    - How much free space is available?
    - What percentage of capacity is used?
    - What is the total size of the cluster?
    - What is my deduplication ratio?
    - What is my compression ratio?
    - How much effective capacity do I have with dedupe and compression?
    - Am I running low on storage?

    Tip: To calculate percent used, divide ifs.bytes.used by ifs.bytes.total
    and multiply by 100. To calculate effective savings, use the dedupe and
    compression ratios together.
    """
    cluster = get_cluster(cluster_name)
    capacity = Capacity(cluster)
    return capacity.get()

@safe_tool(group="capacity", mode="read")
def powerscale_config(cluster_name: str = None) -> dict:
    """
    Return cluster configuration and hardware details for the PowerScale cluster.

    This tool queries the cluster API and the Ansible info module to return
    identifying, configuration, and hardware information about the cluster.

    Response fields (from SDK):
    - name: Cluster name
    - guid: Cluster GUID (globally unique identifier)
    - description: Customer-configurable description
    - encoding: Default character encoding
    - has_quorum: Whether the local node is in a group with quorum
    - is_compliance: Whether compliance mode is enabled (stricter WORM)
    - is_virtual: Whether the cluster is a virtual deployment
    - is_vonefs: Whether this is a vOneFS cluster on ESXi
    - is_powerscale_ve: Whether this is a PowerScale VE cluster
    - join_mode: Node join mode ("manual" or "secure")
    - local_devid: Device ID of the queried node
    - local_lnn: Logical node number of the queried node
    - local_serial: Serial number of the queried node
    - onefs_version: OneFS version information (build, release, revision, type, version)
    - timezone: Cluster timezone settings
    - devices: List of device configuration objects

    Response fields (from Ansible — hardware sub-dict):
    - hardware.attributes: Cluster-level attributes (version, config, contact info)
    - hardware.nodes: Per-node hardware details (LNN, partitions, drives)
    - hardware.node_pools: Node pool groupings and membership
    - hardware.storage_pool_tiers: Storage pool tier configuration

    Use this tool to answer questions such as:
    - What is the cluster name?
    - What version of OneFS is running?
    - Is the cluster virtual or physical?
    - What is the cluster GUID?
    - Is compliance mode enabled?
    - What timezone is the cluster configured for?
    - How many nodes are in the cluster?
    - What hardware is in each node?
    - What are the node pools and storage tiers?
    - What drives or partitions does each node have?
    """
    cluster = get_cluster(cluster_name)
    config = Config(cluster)
    return config.get()
