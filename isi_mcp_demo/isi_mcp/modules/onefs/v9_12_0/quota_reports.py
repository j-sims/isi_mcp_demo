import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class QuotaReports:
    """Provides access to quota report metadata via the QuotaReportsApi."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get_report_about(self, report_id: str):
        """Get metadata/info about a specific quota report.

        Arguments:
        - report_id: The quota report ID
        """
        api = isi_sdk.QuotaReportsApi(self.cluster.api_client)
        try:
            result = api.get_report_about(report_id)
            return result.about.to_dict() if hasattr(result, "about") and result.about else {}
        except ApiException as e:
            return {"error": str(e)}
