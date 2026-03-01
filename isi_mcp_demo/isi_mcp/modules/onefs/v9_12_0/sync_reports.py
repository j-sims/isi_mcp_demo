import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class SyncReports:
    """Provides access to SyncIQ policy reports and subreports via the SyncReportsApi.

    Subreports provide detailed per-run information for SyncIQ policy execution history.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get_subreports(self, report_id: str, resume: str = None, limit: int = 100,
                       sort: str = None, dir: str = None):
        """List subreports for a SyncIQ report.

        Arguments:
        - report_id: The SyncIQ report ID
        - resume: Pagination token from a previous call
        - limit: Maximum number of results (default 100)
        - sort: Field to sort by
        - dir: Sort direction ('ASC' or 'DESC')
        """
        api = isi_sdk.SyncReportsApi(self.cluster.api_client)
        try:
            kwargs = {"report_id": report_id}
            if resume:
                kwargs["resume"] = resume
            else:
                kwargs["limit"] = limit
                if sort:
                    kwargs["sort"] = sort
                if dir:
                    kwargs["dir"] = dir
            result = api.get_report_subreports(**kwargs)
            subreports = result.subreports if hasattr(result, "subreports") and result.subreports else []
            return {
                "items": [s.to_dict() for s in subreports],
                "resume": getattr(result, "resume", None),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_subreport(self, report_id: str, subreport_id: str):
        """Get a specific subreport from a SyncIQ report.

        Arguments:
        - report_id: The SyncIQ report ID
        - subreport_id: The subreport ID
        """
        api = isi_sdk.SyncReportsApi(self.cluster.api_client)
        try:
            result = api.get_report_subreport(report_id, subreport_id)
            subreports = result.subreports if hasattr(result, "subreports") and result.subreports else []
            if subreports:
                return subreports[0].to_dict()
            return {"error": f"Subreport '{subreport_id}' not found in report '{report_id}'"}
        except ApiException as e:
            return {"error": str(e)}
