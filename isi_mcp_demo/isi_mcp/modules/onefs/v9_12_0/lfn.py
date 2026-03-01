import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class LFN:
    """Provides access to Long File Name configuration via the LfnApi.

    LFN domains control maximum file name lengths for specific filesystem paths.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def list_domains(self, resume: str = None):
        """List all long file name configuration domains.

        Arguments:
        - resume: Pagination token from a previous call
        """
        api = isi_sdk.LfnApi(self.cluster.api_client)
        try:
            kwargs = {}
            if resume:
                kwargs["resume"] = resume
            result = api.list_lfn(**kwargs)
            domains = result.lfn if hasattr(result, "lfn") and result.lfn else []
            return {
                "items": [d.to_dict() for d in domains],
                "resume": getattr(result, "resume", None),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_path(self, path: str):
        """Get long file name configuration for a specific path.

        Arguments:
        - path: The filesystem path to query (e.g. '/ifs/data')
        """
        api = isi_sdk.LfnApi(self.cluster.api_client)
        try:
            result = api.get_lfn_path(path)
            domains = result.lfn if hasattr(result, "lfn") and result.lfn else []
            if domains:
                return domains[0].to_dict()
            return {"error": f"LFN config for path '{path}' not found"}
        except ApiException as e:
            return {"error": str(e)}
