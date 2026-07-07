import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.utils.errors import safe_api_error


class ApiSessions:
    """Provides access to Platform API session info via the ApiApi.

    Covers API session settings and session invalidation information.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get_session_settings(self):
        """Get HTTP API session settings (timeouts, limits, etc)."""
        api = isi_sdk.ApiApi(self.cluster.api_client)
        result = api.get_settings_sessions()
        return result.settings.to_dict() if hasattr(result, "settings") and result.settings else {}

    def list_invalidations(self):
        """List all Platform API session invalidations."""
        api = isi_sdk.ApiApi(self.cluster.api_client)
        result = api.list_sessions_invalidations()
        invalidations = result.invalidations if hasattr(result, "invalidations") and result.invalidations else []
        return {"items": [i.to_dict() for i in invalidations]}

    def get_invalidation(self, invalidation_id: str):
        """Get a specific Platform API session invalidation.

        Arguments:
        - invalidation_id: The invalidation identifier
        """
        api = isi_sdk.ApiApi(self.cluster.api_client)
        try:
            result = api.get_sessions_invalidation(invalidation_id)
        except ApiException as e:
            # OneFS returns 500 (not 404) when the invalidation does not exist
            if getattr(e, "status", None) == 500:
                return {"error": f"Session invalidation '{invalidation_id}' not found"}
            return {"error": safe_api_error(e)}
        invalidations = result.invalidations if hasattr(result, "invalidations") and result.invalidations else []
        if invalidations:
            return invalidations[0].to_dict()
        return {"error": f"Session invalidation '{invalidation_id}' not found"}
