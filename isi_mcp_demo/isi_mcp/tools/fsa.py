from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.fsa import FSA
from typing import Optional


@safe_tool(group="fsa", mode="read")
def powerscale_fsa_results_get(cluster_name: str = None) -> dict:
    """
    List all available FSA (File System Analytics) result sets.

    FSA scans the filesystem and produces result sets containing statistics
    about file distribution, sizes, ages, and storage pool usage.

    Returns:
    - items: List of FSA result set objects (with ID, timestamp, status, path)
    """
    cluster = get_cluster(cluster_name)
    fsa = FSA(cluster)
    return fsa.get_results()


@safe_tool(group="fsa", mode="read")
def powerscale_fsa_result_get(result_id: int, cluster_name: str = None) -> dict:
    """
    Get details for a specific FSA result set.

    Arguments:
    - result_id: The FSA result set ID
    """
    cluster = get_cluster(cluster_name)
    fsa = FSA(cluster)
    return fsa.get_result(result_id)


@safe_tool(group="fsa", mode="read")
def powerscale_fsa_index_get(cluster_name: str = None) -> dict:
    """
    Get available FSA index table names.

    Returns the list of index tables that can be queried for FSA data.
    """
    cluster = get_cluster(cluster_name)
    fsa = FSA(cluster)
    return fsa.get_index()


@safe_tool(group="fsa", mode="read")
def powerscale_fsa_settings_get(scope: Optional[str] = None, cluster_name: str = None) -> dict:
    """
    Get FSA configuration settings.

    Arguments:
    - scope: Optional scope filter for settings
    """
    cluster = get_cluster(cluster_name)
    fsa = FSA(cluster)
    return fsa.get_settings(scope=scope)


@safe_tool(group="fsa", mode="read")
def powerscale_fsa_top_dirs_get(result_id: int, cluster_name: str = None) -> dict:
    """
    Get top directories from an FSA result set.

    Returns directories ranked by space consumption, file count, or other
    metrics. Useful for identifying storage hotspots.

    Arguments:
    - result_id: The FSA result set ID
    """
    cluster = get_cluster(cluster_name)
    fsa = FSA(cluster)
    return fsa.get_top_dirs(result_id)


@safe_tool(group="fsa", mode="read")
def powerscale_fsa_top_dir_get(result_id: int, top_dir_id: int, cluster_name: str = None) -> dict:
    """
    Get a specific top directory entry from an FSA result set.

    Arguments:
    - result_id: The FSA result set ID
    - top_dir_id: The top directory entry ID
    """
    cluster = get_cluster(cluster_name)
    fsa = FSA(cluster)
    return fsa.get_top_dir(result_id, top_dir_id)


@safe_tool(group="fsa", mode="read")
def powerscale_fsa_top_files_get(result_id: int, cluster_name: str = None) -> dict:
    """
    Get top files from an FSA result set.

    Returns files ranked by size. Useful for identifying the largest files
    consuming storage.

    Arguments:
    - result_id: The FSA result set ID
    """
    cluster = get_cluster(cluster_name)
    fsa = FSA(cluster)
    return fsa.get_top_files(result_id)


@safe_tool(group="fsa", mode="read")
def powerscale_fsa_top_file_get(result_id: int, top_file_id: int, cluster_name: str = None) -> dict:
    """
    Get a specific top file entry from an FSA result set.

    Arguments:
    - result_id: The FSA result set ID
    - top_file_id: The top file entry ID
    """
    cluster = get_cluster(cluster_name)
    fsa = FSA(cluster)
    return fsa.get_top_file(result_id, top_file_id)


@safe_tool(group="fsa", mode="read")
def powerscale_fsa_histogram_get(result_id: int, cluster_name: str = None) -> dict:
    """
    Get histogram of file counts for an FSA result set.

    Returns file distribution data (e.g. by size bucket, age bucket).

    Arguments:
    - result_id: The FSA result set ID
    """
    cluster = get_cluster(cluster_name)
    fsa = FSA(cluster)
    return fsa.get_histogram(result_id)


@safe_tool(group="fsa", mode="read")
def powerscale_fsa_histogram_stat_get(result_id: int, stat: str, cluster_name: str = None) -> dict:
    """
    Get histogram filtered by a specific statistic.

    Arguments:
    - result_id: The FSA result set ID
    - stat: The statistic name to filter histogram by
    """
    cluster = get_cluster(cluster_name)
    fsa = FSA(cluster)
    return fsa.get_histogram_stat(result_id, stat)


@safe_tool(group="fsa", mode="read")
def powerscale_fsa_directories_get(result_id: int, cluster_name: str = None) -> dict:
    """
    Get directory information from an FSA result set.

    Returns directory-level statistics including file counts, sizes, and paths.

    Arguments:
    - result_id: The FSA result set ID
    """
    cluster = get_cluster(cluster_name)
    fsa = FSA(cluster)
    return fsa.get_directories(result_id)


@safe_tool(group="fsa", mode="read")
def powerscale_fsa_directory_get(result_id: int, directory_id: int, cluster_name: str = None) -> dict:
    """
    Get specific directory information from an FSA result set.

    Arguments:
    - result_id: The FSA result set ID
    - directory_id: The directory entry ID
    """
    cluster = get_cluster(cluster_name)
    fsa = FSA(cluster)
    return fsa.get_directory(result_id, directory_id)
