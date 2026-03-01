import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class Hardening:
    """Provides access to PowerScale security hardening status via the HardeningApi.

    Covers hardening profiles, service state, and compliance reports.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get_profiles(self):
        """List available hardening profiles with their descriptions and applied status."""
        api = isi_sdk.HardeningApi(self.cluster.api_client)
        try:
            result = api.get_hardening_list()
            profiles = result.profiles if hasattr(result, "profiles") and result.profiles else []
            return {"items": [p.to_dict() for p in profiles]}
        except ApiException as e:
            return {"error": str(e)}

    def get_state(self):
        """Get the current state of the hardening service (Running or Available)."""
        api = isi_sdk.HardeningApi(self.cluster.api_client)
        try:
            result = api.get_hardening_state()
            return result.state.to_dict() if hasattr(result, "state") and result.state else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_reports(self):
        """List compliance reports for all hardening rules."""
        api = isi_sdk.HardeningApi(self.cluster.api_client)
        try:
            result = api.list_hardening_reports()
            reports = result.reports if hasattr(result, "reports") and result.reports else []
            return {"items": [r.to_dict() for r in reports]}
        except ApiException as e:
            return {"error": str(e)}
