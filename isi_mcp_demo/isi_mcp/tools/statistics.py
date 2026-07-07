from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.statistics import Statistics
from modules.utils.paging import normalize_resume
from typing import Dict, Any, List, Optional


@safe_tool(group="statistics", mode="read")
def powerscale_stats_cpu(cluster_name: str = None) -> Dict[str, Any]:
    """
    Return a single instantaneous cluster CPU utilization sample.

    Each call returns one snapshot from the PowerScale statistics endpoint,
    which refreshes approximately every 5 seconds. To collect trend data,
    call this tool multiple times and wait at least 5 seconds between calls.
    Always check that _sample_time has changed between calls to confirm
    you received a new sample (not a cached repeat).

    Response fields (all values are percentages, 0.0–100.0):
    - cluster.cpu.sys.avg:  CPU time spent in kernel/system mode
    - cluster.cpu.user.avg: CPU time spent in user-space processes
    - cluster.cpu.idle.avg: CPU idle time (higher is better)
    - cluster.cpu.intr.avg: CPU time handling hardware interrupts
    - _sample_time:         Unix timestamp of when this sample was taken

    Note: The PAPI returns these values as per-mille integers (0–1000); this tool
    divides by 10 to produce percentages. powerscale_stats_get returns raw per-mille
    values for the same keys.

    Tip: A healthy cluster typically has idle > 50%. Values of sys+user > 80%
    combined may indicate CPU pressure. High intr can suggest network or disk
    interrupt storms.

    Use this tool when the user asks:
    - Is the cluster CPU busy or overloaded?
    - What is the CPU utilization?
    - Is there high system or user CPU usage?
    - Is the cluster under CPU pressure?
    - What percentage of CPU is idle?
    """
    cluster = get_cluster(cluster_name)
    stats = Statistics(cluster)
    return stats.get_cpu()


@safe_tool(group="statistics", mode="read")
def powerscale_stats_network(cluster_name: str = None) -> Dict[str, Any]:
    """
    Return a single instantaneous cluster external network traffic sample.

    Each call returns one snapshot from the PowerScale statistics endpoint,
    which refreshes approximately every 5 seconds. To collect trend data,
    call this tool multiple times and wait at least 5 seconds between calls.
    Always check that _sample_time has changed between calls to confirm
    you received a new sample (not a cached repeat).

    Response fields:
    - cluster.net.ext.bytes.in.rate:    Inbound bytes per second (from clients)
    - cluster.net.ext.bytes.out.rate:   Outbound bytes per second (to clients)
    - cluster.net.ext.packets.in.rate:  Inbound packets per second
    - cluster.net.ext.packets.out.rate: Outbound packets per second
    - cluster.net.ext.errors.in.rate:   Inbound network errors per second
    - cluster.net.ext.errors.out.rate:  Outbound network errors per second
    - _sample_time:                     Unix timestamp of when this sample was taken

    Tip: Use bytes_to_human tool to convert byte rates to human-readable
    formats (MiB/s, GiB/s). Non-zero error rates may indicate cabling,
    switch, or NIC issues.

    Use this tool when the user asks:
    - What is the network throughput?
    - How much data is flowing to/from clients?
    - Are there network errors on the cluster?
    - What is the inbound or outbound bandwidth utilization?
    - Is there a network bottleneck?
    """
    cluster = get_cluster(cluster_name)
    stats = Statistics(cluster)
    return stats.get_network()


@safe_tool(group="statistics", mode="read")
def powerscale_stats_disk(cluster_name: str = None) -> Dict[str, Any]:
    """
    Return a single instantaneous cluster disk I/O sample.

    Each call returns one snapshot from the PowerScale statistics endpoint,
    which refreshes approximately every 5 seconds. To collect trend data,
    call this tool multiple times and wait at least 5 seconds between calls.
    Always check that _sample_time has changed between calls to confirm
    you received a new sample (not a cached repeat).

    Response fields:
    - cluster.disk.bytes.in.rate:  Bytes written to disk per second
    - cluster.disk.bytes.out.rate: Bytes read from disk per second
    - cluster.disk.xfers.in.rate:  Write I/O operations per second (IOPS)
    - cluster.disk.xfers.out.rate: Read I/O operations per second (IOPS)
    - cluster.disk.xfers.rate:     Total I/O operations per second (IOPS)
    - _sample_time:                Unix timestamp of when this sample was taken

    Tip: Use bytes_to_human tool to convert byte rates to human-readable
    formats. High disk I/O with low cache hit rates may indicate the workload
    is not cache-friendly.

    Use this tool when the user asks:
    - Is disk I/O high?
    - What is the disk throughput or transfer rate?
    - How many disk I/Os (IOPS) per second?
    - Is there a disk I/O bottleneck?
    - What is the disk read vs write rate?
    """
    cluster = get_cluster(cluster_name)
    stats = Statistics(cluster)
    return stats.get_disk()


@safe_tool(group="statistics", mode="read")
def powerscale_stats_ifs(cluster_name: str = None) -> Dict[str, Any]:
    """
    Return a single instantaneous OneFS filesystem I/O sample.

    Each call returns one snapshot from the PowerScale statistics endpoint,
    which refreshes approximately every 5 seconds. To collect trend data,
    call this tool multiple times and wait at least 5 seconds between calls.
    Always check that _sample_time has changed between calls to confirm
    you received a new sample (not a cached repeat).

    Response fields:
    - ifs.bytes.in.rate:  Bytes written to the filesystem per second
    - ifs.bytes.out.rate: Bytes read from the filesystem per second
    - ifs.ops.in.rate:    Write operations per second at the filesystem layer
    - ifs.ops.out.rate:   Read operations per second at the filesystem layer
    - _sample_time:       Unix timestamp of when this sample was taken

    Note: IFS rates reflect activity at the OneFS filesystem layer, which
    includes cache effects. Disk rates (powerscale_stats_disk) reflect
    actual physical disk I/O. The difference between IFS and disk rates
    indicates how much data is being served from cache.

    Use this tool when the user asks:
    - What is the overall filesystem throughput?
    - How many IOPS is the cluster handling?
    - What is the filesystem read vs write rate?
    - How much data is the filesystem serving per second?
    """
    cluster = get_cluster(cluster_name)
    stats = Statistics(cluster)
    return stats.get_ifs()


@safe_tool(group="statistics", mode="read")
def powerscale_stats_node(cluster_name: str = None) -> Dict[str, Any]:
    """
    Return a single instantaneous per-node performance sample.

    Each call returns one snapshot from the PowerScale statistics endpoint,
    which refreshes approximately every 5 seconds. To collect trend data,
    call this tool multiple times and wait at least 5 seconds between calls.
    Always check that _sample_time has changed between calls to confirm
    you received a new sample (not a cached repeat).

    Response is a dict keyed by "node_<devid>" (e.g. "node_1", "node_2"),
    with a top-level "_sample_time" Unix timestamp. Each node entry contains:
    - node.cpu.throttling: CPU throttling percentage (>0 indicates thermal
                           or power-related throttling)
    - node.load.1min:      1-minute CPU load average
    - node.load.5min:      5-minute CPU load average
    - node.load.15min:     15-minute CPU load average
    - node.memory.used:    Memory in use (bytes)
    - node.memory.free:    Free memory (bytes)
    - node.open.files:     Number of open file handles on this node

    Tip: Use bytes_to_human tool to convert memory values to human-readable
    formats. Load averages above the number of CPU cores on a node indicate
    CPU saturation.

    DEPLOYMENT NOTES:
    Per-node statistics may be unavailable on virtual cluster deployments.
    If unavailable, the result will include a "_warning" key with guidance.
    Use cluster-level statistics (powerscale_stats_cpu, powerscale_stats_network,
    etc.) as an alternative for virtual clusters.
    On some clusters node.cpu.throttling is not collected; in that case the field
    is omitted from each node entry and a "_note" key explains the exclusion (the
    other metrics are still returned).

    Use this tool when the user asks:
    - Which nodes are the busiest?
    - What is the load average per node?
    - Is any node overloaded or struggling?
    - How much memory is free on each node?
    - Is there CPU throttling on any node?
    - Are there hot spots in the cluster?
    """
    cluster = get_cluster(cluster_name)
    stats = Statistics(cluster)
    return stats.get_node_performance()


@safe_tool(group="statistics", mode="read")
def powerscale_stats_protocol(cluster_name: str = None) -> Dict[str, Any]:
    """
    Return a single instantaneous per-protocol operation rate sample.

    Each call returns one snapshot from the PowerScale statistics endpoint,
    which refreshes approximately every 5 seconds. To collect trend data,
    call this tool multiple times and wait at least 5 seconds between calls.
    Always check that _sample_time has changed between calls to confirm
    you received a new sample (not a cached repeat).

    Response fields (all values are operations per second):
    - cluster.protostats.nfs:   NFSv3 operation rate
    - cluster.protostats.nfs4:  NFSv4 operation rate
    - cluster.protostats.cifs:  SMB1/CIFS operation rate
    - cluster.protostats.smb2:  SMB2/SMB3 operation rate
    - cluster.protostats.http:  HTTP/S3 operation rate
    - cluster.protostats.ftp:   FTP operation rate
    - cluster.protostats.hdfs:  HDFS operation rate
    - _sample_time:             Unix timestamp of when this sample was taken

    Note: These are current operation rates (ops/sec), not cumulative totals.
    A value of 0 means no active I/O for that protocol.

    Use this tool when the user asks:
    - How many NFS or SMB operations per second?
    - Which protocol has the most traffic?
    - Is NFS or CIFS/SMB busy right now?
    - What is the HTTP or S3 operation rate?
    - Which protocols are active on the cluster?
    """
    cluster = get_cluster(cluster_name)
    stats = Statistics(cluster)
    return stats.get_protocol()


@safe_tool(group="statistics", mode="read")
def powerscale_stats_clients(cluster_name: str = None) -> Dict[str, Any]:
    """
    Return a single instantaneous client connection count sample.

    Each call returns one snapshot from the PowerScale statistics endpoint,
    which refreshes approximately every 5 seconds. To collect trend data,
    call this tool multiple times and wait at least 5 seconds between calls.
    Always check that _sample_time has changed between calls to confirm
    you received a new sample (not a cached repeat).

    Response fields (cluster-aggregate counts across all nodes):
    Active clients (currently performing I/O):
    - node.clientstats.active.nfs:   Active NFSv3 clients
    - node.clientstats.active.nfs4:  Active NFSv4 clients
    - node.clientstats.active.cifs:  Active SMB1/CIFS clients
    - node.clientstats.active.smb2:  Active SMB2/SMB3 clients
    - node.clientstats.active.http:  Active HTTP clients
    - node.clientstats.active.ftp:   Active FTP clients
    - node.clientstats.active.hdfs:  Active HDFS clients

    Connected clients (mounted/connected but not necessarily active):
    - node.clientstats.connected.nfs:  Connected NFS clients
    - node.clientstats.connected.cifs: Connected CIFS clients
    - node.clientstats.connected.http: Connected HTTP clients
    - _sample_time:                    Unix timestamp of when this sample was taken

    Tip: The difference between connected and active counts shows idle
    connections. Large numbers of connected but inactive clients can
    consume resources.

    Use this tool when the user asks:
    - How many clients are connected to the cluster?
    - How many active NFS mounts or sessions?
    - How many CIFS/SMB sessions are there?
    - How many clients are actively doing I/O vs just mounted?
    - What is the client load on the cluster?
    """
    cluster = get_cluster(cluster_name)
    stats = Statistics(cluster)
    return stats.get_clients()


@safe_tool(group="statistics", mode="read")
def powerscale_stats_get(
    keys: List[str],
    show_nodes: bool = False,
    cluster_name: str = None,
) -> Dict[str, Any]:
    """
    Retrieve a single instantaneous statistics sample for arbitrary user-specified stat keys.

    This is a power-user tool for querying any statistics keys by name.
    Each call returns one snapshot from the PowerScale statistics endpoint,
    which refreshes approximately every 5 seconds. To collect trend data,
    call this tool multiple times and wait at least 5 seconds between calls.
    Always check that _sample_time has changed between calls to confirm
    you received a new sample (not a cached repeat).

    Arguments:
    - keys: List of statistics key strings to retrieve. Use powerscale_stats_keys
            to discover available keys. Example keys:
              "cluster.cpu.sys.avg"
              "node.disk.bytes.in.rate.avg"
              "ifs.bytes.in.rate"
              "cluster.protostats.nfs"
    - show_nodes: If True, results are grouped by node device ID
                  ({"node_1": {key: value}, "node_2": {...}}). If False
                  (default), cluster-aggregate values are returned.
    The response always includes "_sample_time" (Unix timestamp).

    Use this tool when the user wants to:
    - Query a specific statistic not covered by other powerscale_stats_* tools
    - Retrieve multiple heterogeneous stats in a single call
    - Investigate a specific performance metric by key name
    - Build custom performance dashboards or reports
    """
    cluster = get_cluster(cluster_name)
    stats = Statistics(cluster)
    return stats.get_current(keys, show_nodes=show_nodes)


@safe_tool(group="statistics", mode="read")
def powerscale_stats_keys(
    limit: int = 100,
    resume: Optional[str] = None,
    queryable: bool = False,
    cluster_name: str = None,
) -> Dict[str, Any]:
    """
    List available statistics keys with metadata (description, units, type).

    This tool is useful for discovering what performance metrics are available
    on the cluster. Results are not averaged — this is a metadata lookup only.

    Response fields:
    - keys: List of key objects, each containing:
        - key:         The stat key string (use with powerscale_stats_get)
        - description: Human-readable description of the metric
        - units:       Units of measurement (e.g. "%" , "B/s", "ops/s")
        - type:        Data type (e.g. "rate", "gauge", "counter")
    - resume: Pagination token (pass to next call if has_more is True)
    - has_more: Whether additional keys are available

    Arguments:
    - limit:     Number of keys to return per page (default 100)
    - resume:    Pagination token from a previous call
    - queryable: If True, return only keys that support querying (default False)

    Use this tool when the user asks:
    - What statistics or performance metrics are available?
    - What keys can I use with powerscale_stats_get?
    - Is there a stat key for [specific metric]?
    - What units does [stat key] use?
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    stats = Statistics(cluster)
    return stats.get_keys(limit=limit, resume=resume, queryable=queryable)
