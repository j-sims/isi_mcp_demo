import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class IdResolution:
    """Provides access to UID/GID/SID to name mappings via the IdResolutionZonesApi.

    Resolves numeric user/group identifiers to their associated names within
    specific access zones.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get_zone_users(self, zone_id: str, resume: str = None, limit: int = 100):
        """List UID/SID to username mappings for an access zone.

        Arguments:
        - zone_id: The access zone name or ID
        - resume: Pagination token from a previous call
        - limit: Maximum number of results (default 100)
        """
        api = isi_sdk.IdResolutionZonesApi(self.cluster.api_client)
        try:
            kwargs = {}
            if resume:
                kwargs["resume"] = resume
            else:
                kwargs["limit"] = limit
            result = api.get_zone_users(zone_id, **kwargs)
            users = result.users if hasattr(result, "users") and result.users else []
            return {
                "items": [u.to_dict() for u in users],
                "resume": getattr(result, "resume", None),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_zone_user(self, zone_id: str, user_id: str):
        """Get a specific UID/SID to username mapping.

        Arguments:
        - zone_id: The access zone name or ID
        - user_id: The user UID or SID to resolve
        """
        api = isi_sdk.IdResolutionZonesApi(self.cluster.api_client)
        try:
            result = api.get_zone_user(zone_id, user_id)
            users = result.users if hasattr(result, "users") and result.users else []
            if users:
                return users[0].to_dict()
            return {"error": f"User '{user_id}' not found in zone '{zone_id}'"}
        except ApiException as e:
            return {"error": str(e)}

    def get_zone_groups(self, zone_id: str, resume: str = None, limit: int = 100):
        """List GID/GSID to groupname mappings for an access zone.

        Arguments:
        - zone_id: The access zone name or ID
        - resume: Pagination token from a previous call
        - limit: Maximum number of results (default 100)
        """
        api = isi_sdk.IdResolutionZonesApi(self.cluster.api_client)
        try:
            kwargs = {}
            if resume:
                kwargs["resume"] = resume
            else:
                kwargs["limit"] = limit
            result = api.get_zone_groups(zone_id, **kwargs)
            groups = result.groups if hasattr(result, "groups") and result.groups else []
            return {
                "items": [g.to_dict() for g in groups],
                "resume": getattr(result, "resume", None),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_zone_group(self, zone_id: str, group_id: str):
        """Get a specific GID/GSID to groupname mapping.

        Arguments:
        - zone_id: The access zone name or ID
        - group_id: The group GID or GSID to resolve
        """
        api = isi_sdk.IdResolutionZonesApi(self.cluster.api_client)
        try:
            result = api.get_zone_group(zone_id, group_id)
            groups = result.groups if hasattr(result, "groups") and result.groups else []
            if groups:
                return groups[0].to_dict()
            return {"error": f"Group '{group_id}' not found in zone '{zone_id}'"}
        except ApiException as e:
            return {"error": str(e)}
