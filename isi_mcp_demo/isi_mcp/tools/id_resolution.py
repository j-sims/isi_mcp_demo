from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.id_resolution import IdResolution
from modules.onefs.v9_12_0.lfn import LFN
from modules.utils.paging import normalize_resume
from typing import Optional


@safe_tool(group="id_resolution", mode="read")
def powerscale_id_resolution_users_get(
    zone_id: str,
    uids: Optional[str] = None,
    sids: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Resolve specific UIDs or SIDs to usernames within an access zone.

    Resolves numeric user identifiers to their associated user names.

    Arguments:
    - zone_id: The numeric zone ID (e.g. 1). Use powerscale_zones_get to list
      available zones and get their zone_id field.
    - uids: REQUIRED (if sids not provided). Comma-separated UIDs to resolve
      (e.g. "1000,1001,1002" or "0" for root). At least one of uids or sids must be provided.
    - sids: REQUIRED (if uids not provided). Comma-separated SIDs to resolve
      (e.g. "S-1-5-21-..."). At least one of uids or sids must be provided.
    """
    cluster = get_cluster(cluster_name)
    idr = IdResolution(cluster)
    return idr.get_zone_users(zone_id, uids=uids, sids=sids)


@safe_tool(group="id_resolution", mode="read")
def powerscale_id_resolution_user_get(zone_id: str, user_id: str, cluster_name: str = None) -> dict:
    """
    Resolve a specific UID/SID to a username within an access zone.

    Arguments:
    - zone_id: The numeric zone ID (e.g. 1). Use powerscale_zones_get to list
      available zones and get their zone_id field.
    - user_id: The user UID or SID to resolve
    """
    cluster = get_cluster(cluster_name)
    idr = IdResolution(cluster)
    return idr.get_zone_user(zone_id, user_id)


@safe_tool(group="id_resolution", mode="read")
def powerscale_id_resolution_groups_get(
    zone_id: str,
    gids: Optional[str] = None,
    gsids: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Resolve specific GIDs or GSIDs to group names within an access zone.

    Resolves numeric group identifiers to their associated group names.

    Arguments:
    - zone_id: The numeric zone ID (e.g. 1). Use powerscale_zones_get to list
      available zones and get their zone_id field.
    - gids: REQUIRED (if gsids not provided). Comma-separated GIDs to resolve
      (e.g. "1000,1001,1002" or "0" for wheel). At least one of gids or gsids must be provided.
    - gsids: REQUIRED (if gids not provided). Comma-separated GSIDs to resolve
      (e.g. "S-1-5-21-..."). At least one of gids or gsids must be provided.
    """
    cluster = get_cluster(cluster_name)
    idr = IdResolution(cluster)
    return idr.get_zone_groups(zone_id, gids=gids, gsids=gsids)


@safe_tool(group="id_resolution", mode="read")
def powerscale_id_resolution_group_get(zone_id: str, group_id: str, cluster_name: str = None) -> dict:
    """
    Resolve a specific GID/GSID to a groupname within an access zone.

    Arguments:
    - zone_id: The numeric zone ID (e.g. 1). Use powerscale_zones_get to list
      available zones and get their zone_id field.
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
