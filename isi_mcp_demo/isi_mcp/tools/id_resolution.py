from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.id_resolution import IdResolution
from modules.onefs.v9_12_0.lfn import LFN
from modules.utils.paging import normalize_resume
from typing import Optional


@safe_tool(group="id_resolution", mode="read")
def powerscale_id_resolution_users_get(
    zone_id: str,
    resume: Optional[str] = None,
    limit: int = 100,
    cluster_name: str = None,
) -> dict:
    """
    List UID/SID to username mappings for an access zone.

    Resolves numeric user identifiers to their associated names.

    Arguments:
    - zone_id: The access zone name or ID (e.g. 'System')
    - resume: Pagination token from a previous call
    - limit: Maximum number of results (default 100)
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    idr = IdResolution(cluster)
    return idr.get_zone_users(zone_id, resume=resume, limit=limit)


@safe_tool(group="id_resolution", mode="read")
def powerscale_id_resolution_user_get(zone_id: str, user_id: str, cluster_name: str = None) -> dict:
    """
    Resolve a specific UID/SID to a username within an access zone.

    Arguments:
    - zone_id: The access zone name or ID
    - user_id: The user UID or SID to resolve
    """
    cluster = get_cluster(cluster_name)
    idr = IdResolution(cluster)
    return idr.get_zone_user(zone_id, user_id)


@safe_tool(group="id_resolution", mode="read")
def powerscale_id_resolution_groups_get(
    zone_id: str,
    resume: Optional[str] = None,
    limit: int = 100,
    cluster_name: str = None,
) -> dict:
    """
    List GID/GSID to groupname mappings for an access zone.

    Resolves numeric group identifiers to their associated names.

    Arguments:
    - zone_id: The access zone name or ID (e.g. 'System')
    - resume: Pagination token from a previous call
    - limit: Maximum number of results (default 100)
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    idr = IdResolution(cluster)
    return idr.get_zone_groups(zone_id, resume=resume, limit=limit)


@safe_tool(group="id_resolution", mode="read")
def powerscale_id_resolution_group_get(zone_id: str, group_id: str, cluster_name: str = None) -> dict:
    """
    Resolve a specific GID/GSID to a groupname within an access zone.

    Arguments:
    - zone_id: The access zone name or ID
    - group_id: The group GID or GSID to resolve
    """
    cluster = get_cluster(cluster_name)
    idr = IdResolution(cluster)
    return idr.get_zone_group(zone_id, group_id)


@safe_tool(group="lfn", mode="read")
def powerscale_lfn_domains_get(resume: Optional[str] = None, cluster_name: str = None) -> dict:
    """
    List all Long File Name configuration domains.

    LFN domains control maximum file name lengths for specific filesystem
    paths. Returns path and configuration for each domain.

    Arguments:
    - resume: Pagination token from a previous call
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    l = LFN(cluster)
    return l.list_domains(resume=resume)


@safe_tool(group="lfn", mode="read")
def powerscale_lfn_path_get(path: str, cluster_name: str = None) -> dict:
    """
    Get Long File Name configuration for a specific path.

    Arguments:
    - path: The filesystem path to query (e.g. '/ifs/data')
    """
    cluster = get_cluster(cluster_name)
    l = LFN(cluster)
    return l.get_path(path)
