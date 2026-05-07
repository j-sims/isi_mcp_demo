from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.performance import Performance


@safe_tool(group="performance", mode="read")
def powerscale_performance_datasets_get(cluster_name: str = None) -> dict:
    """
    List all performance datasets on the PowerScale cluster.

    Datasets define collections of metrics for performance monitoring and analysis.

    Returns:
    - items: List of dataset objects
    - total: Total number of datasets
    """
    cluster = get_cluster(cluster_name)
    p = Performance(cluster)
    return p.list_datasets()


@safe_tool(group="performance", mode="read")
def powerscale_performance_dataset_get(dataset_id: int, cluster_name: str = None) -> dict:
    """
    Get details for a specific performance dataset.

    Arguments:
    - dataset_id: The dataset ID
    """
    cluster = get_cluster(cluster_name)
    p = Performance(cluster)
    return p.get_dataset(dataset_id)


@safe_tool(group="performance", mode="read")
def powerscale_performance_metrics_get(cluster_name: str = None) -> dict:
    """
    List all available performance metrics on the cluster.

    Returns the full catalog of metrics that can be included in performance
    datasets for monitoring (throughput, latency, IOPS, etc.).

    Returns:
    - items: List of metric objects with name, description, units, and type
    """
    cluster = get_cluster(cluster_name)
    p = Performance(cluster)
    return p.get_metrics()


@safe_tool(group="performance", mode="read")
def powerscale_performance_metric_get(metric_id: str, cluster_name: str = None) -> dict:
    """
    Get details for a specific performance metric.

    Arguments:
    - metric_id: The metric name/ID
    """
    cluster = get_cluster(cluster_name)
    p = Performance(cluster)
    return p.get_metric(metric_id)


@safe_tool(group="performance", mode="read")
def powerscale_performance_settings_get(cluster_name: str = None) -> dict:
    """
    Get performance monitoring settings.

    Returns configuration for the performance monitoring subsystem.
    """
    cluster = get_cluster(cluster_name)
    p = Performance(cluster)
    return p.get_settings()


@safe_tool(group="performance", mode="read")
def powerscale_performance_dataset_filters_get(dataset_id: int, cluster_name: str = None) -> dict:
    """
    List all filters for a specific performance dataset.

    Filters define which metrics/nodes are included in the dataset.

    Arguments:
    - dataset_id: The dataset ID
    """
    cluster = get_cluster(cluster_name)
    p = Performance(cluster)
    return p.list_dataset_filters(dataset_id)


@safe_tool(group="performance", mode="read")
def powerscale_performance_dataset_filter_get(dataset_id: int, filter_id: int, cluster_name: str = None) -> dict:
    """
    Get a specific filter for a performance dataset.

    Arguments:
    - dataset_id: The dataset ID
    - filter_id: The filter ID
    """
    cluster = get_cluster(cluster_name)
    p = Performance(cluster)
    return p.get_dataset_filter(dataset_id, filter_id)


@safe_tool(group="performance", mode="read")
def powerscale_performance_dataset_workloads_get(dataset_id: int, cluster_name: str = None) -> dict:
    """
    List all workloads for a specific performance dataset.

    Workloads define workload categories being tracked within a dataset.

    Arguments:
    - dataset_id: The dataset ID
    """
    cluster = get_cluster(cluster_name)
    p = Performance(cluster)
    return p.list_dataset_workloads(dataset_id)


@safe_tool(group="performance", mode="read")
def powerscale_performance_dataset_workload_get(dataset_id: int, workload_id: int, cluster_name: str = None) -> dict:
    """
    Get a specific workload for a performance dataset.

    Arguments:
    - dataset_id: The dataset ID
    - workload_id: The workload ID
    """
    cluster = get_cluster(cluster_name)
    p = Performance(cluster)
    return p.get_dataset_workload(dataset_id, workload_id)
