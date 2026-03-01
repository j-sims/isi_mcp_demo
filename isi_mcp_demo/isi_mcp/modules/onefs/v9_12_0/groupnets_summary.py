import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class GroupnetsSummary:
    """Provides access to groupnet summary info via the GroupnetsSummaryApi."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self):
        """Get groupnet summary information (count, names, subnets)."""
        api = isi_sdk.GroupnetsSummaryApi(self.cluster.api_client)
        try:
            result = api.get_groupnets_summary()
            return result.summary.to_dict() if hasattr(result, "summary") and result.summary else {}
        except ApiException as e:
            return {"error": str(e)}
