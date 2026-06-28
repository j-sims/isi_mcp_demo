import isilon_sdk.v9_12_0 as isi_sdk
from modules.utils.paging import page_kwargs


class IdResolution:
    """Provides access to UID/GID/SID to name mappings via the IdResolutionZonesApi.

    Resolves numeric user/group identifiers to their associated names within
    specific access zones.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    @staticmethod
    def _check_zone_id(zone_id):
        """Return an error dict if zone_id is None, else None.

        The id-resolution endpoints accept either zone names (like 'System')
        or numeric zone IDs.
        """
        if zone_id is None:
            return {
                "error": (
                    "zone_id is required. Use powerscale_zones_get to list "
                    "available zones and get their names."
                )
            }
        return None

    def get_zone_users(self, zone_id: str, uids: str = None, sids: str = None):
        """Resolve UID/SID to username mappings for an access zone.

        Arguments:
        - zone_id: The access zone name or numeric ID
        - uids: Comma-separated UIDs to resolve
        - sids: Comma-separated SIDs to resolve
        """
        err = self._check_zone_id(zone_id)
        if err:
            return err
        if not uids and not sids:
            return {
                "error": "Either 'uids' or 'sids' parameter is required. "
                "Provide comma-separated values to resolve (e.g., uids='1000,1001')."
            }
        # Convert to int if numeric string
        try:
            zone_id_param = int(zone_id)
        except (ValueError, TypeError):
            zone_id_param = zone_id
        api = isi_sdk.IdResolutionZonesApi(self.cluster.api_client)
        kwargs = {}
        if uids:
            kwargs["uids"] = uids
        if sids:
            kwargs["sids"] = sids
        result = api.get_zone_users(zone_id_param, **kwargs)
        users = result.users if hasattr(result, "users") and result.users else []
        return {
            "items": [u.to_dict() for u in users],
            "resume": getattr(result, "resume", None),
        }

    def get_zone_user(self, zone_id: str, user_id: str):
        """Get a specific UID/SID to username mapping.

        Arguments:
        - zone_id: The access zone name or numeric ID
        - user_id: The user UID or SID to resolve
        """
        err = self._check_zone_id(zone_id)
        if err:
            return err
        # Convert to int if numeric string
        try:
            zone_id_param = int(zone_id)
        except (ValueError, TypeError):
            zone_id_param = zone_id
        api = isi_sdk.IdResolutionZonesApi(self.cluster.api_client)
        result = api.get_zone_user(zone_id_param, user_id)
        users = result.users if hasattr(result, "users") and result.users else []
        if users:
            return users[0].to_dict()
        return {"error": f"User '{user_id}' not found in zone '{zone_id}'"}

    def get_zone_groups(self, zone_id: str, gids: str = None, gsids: str = None):
        """Resolve GID/GSID to groupname mappings for an access zone.

        Arguments:
        - zone_id: The access zone name or numeric ID
        - gids: Comma-separated GIDs to resolve
        - gsids: Comma-separated GSIDs to resolve
        """
        err = self._check_zone_id(zone_id)
        if err:
            return err
        if not gids and not gsids:
            return {
                "error": "Either 'gids' or 'gsids' parameter is required. "
                "Provide comma-separated values to resolve (e.g., gids='1000,1001')."
            }
        # Convert to int if numeric string
        try:
            zone_id_param = int(zone_id)
        except (ValueError, TypeError):
            zone_id_param = zone_id
        api = isi_sdk.IdResolutionZonesApi(self.cluster.api_client)
        kwargs = {}
        if gids:
            kwargs["gids"] = gids
        if gsids:
            kwargs["gsids"] = gsids
        result = api.get_zone_groups(zone_id_param, **kwargs)
        groups = result.groups if hasattr(result, "groups") and result.groups else []
        return {
            "items": [g.to_dict() for g in groups],
            "resume": getattr(result, "resume", None),
        }

    def get_zone_group(self, zone_id: str, group_id: str):
        """Get a specific GID/GSID to groupname mapping.

        Arguments:
        - zone_id: The access zone name or numeric ID
        - group_id: The group GID or GSID to resolve
        """
        err = self._check_zone_id(zone_id)
        if err:
            return err
        # Convert to int if numeric string
        try:
            zone_id_param = int(zone_id)
        except (ValueError, TypeError):
            zone_id_param = zone_id
        api = isi_sdk.IdResolutionZonesApi(self.cluster.api_client)
        result = api.get_zone_group(zone_id_param, group_id)
        groups = result.groups if hasattr(result, "groups") and result.groups else []
        if groups:
            return groups[0].to_dict()
        return {"error": f"Group '{group_id}' not found in zone '{zone_id}'"}
