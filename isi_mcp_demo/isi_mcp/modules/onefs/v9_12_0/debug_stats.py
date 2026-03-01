import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class DebugStats:
    """Provides access to PowerScale API debug statistics via the DebugApi.

    Returns cumulative per-resource call statistics for the platform API.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self):
        """Retrieve cumulative API call statistics per resource."""
        api = isi_sdk.DebugApi(self.cluster.api_client)
        try:
            result = api.get_debug_stats()
            return result.stats.to_dict() if hasattr(result, "stats") and result.stats else {}
        except ApiException as e:
            return {"error": str(e)}
