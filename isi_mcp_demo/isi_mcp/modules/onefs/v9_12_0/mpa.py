import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class MPA:
    """Provides access to Multi-Party Authorization data via the MpaApi.

    Covers MPA approvers, requests, global settings, trust anchors,
    request lifecycle config, and privileged action metadata.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get_approvers(self):
        """List all MPA approvers."""
        api = isi_sdk.MpaApi(self.cluster.api_client)
        try:
            result = api.get_mpa_approvers()
            approvers = result.approvers if hasattr(result, "approvers") and result.approvers else []
            return {"items": [a.to_dict() for a in approvers]}
        except ApiException as e:
            return {"error": str(e)}

    def get_approver(self, approver_id: str):
        """Get details for a specific MPA approver.

        Arguments:
        - approver_id: The approver identifier
        """
        api = isi_sdk.MpaApi(self.cluster.api_client)
        try:
            result = api.get_mpa_approver(approver_id)
            approvers = result.approvers if hasattr(result, "approvers") and result.approvers else []
            if approvers:
                return approvers[0].to_dict()
            return {"error": f"Approver '{approver_id}' not found"}
        except ApiException as e:
            return {"error": str(e)}

    def list_requests(self):
        """List all MPA requests."""
        api = isi_sdk.MpaApi(self.cluster.api_client)
        try:
            result = api.list_mpa_requests()
            requests = result.requests if hasattr(result, "requests") and result.requests else []
            return {"items": [r.to_dict() for r in requests]}
        except ApiException as e:
            return {"error": str(e)}

    def get_request(self, request_id: str):
        """Get details for a specific MPA request.

        Arguments:
        - request_id: The MPA request identifier
        """
        api = isi_sdk.MpaApi(self.cluster.api_client)
        try:
            result = api.get_mpa_request(request_id)
            requests = result.requests if hasattr(result, "requests") and result.requests else []
            if requests:
                return requests[0].to_dict()
            return {"error": f"MPA request '{request_id}' not found"}
        except ApiException as e:
            return {"error": str(e)}

    def get_global_settings(self):
        """Get MPA global configuration settings."""
        api = isi_sdk.MpaApi(self.cluster.api_client)
        try:
            result = api.get_settings_global()
            return result.global_settings.to_dict() if hasattr(result, "global_settings") and result.global_settings else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_request_lifecycle(self):
        """Get MPA request lifecycle configuration (timeouts, expiry, etc)."""
        api = isi_sdk.MpaApi(self.cluster.api_client)
        try:
            result = api.get_settings_config_request_lifecycle()
            return result.request_lifecycle.to_dict() if hasattr(result, "request_lifecycle") and result.request_lifecycle else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_privilege_action_metadata(self):
        """Get MPA privileged action metadata (which actions require MPA)."""
        api = isi_sdk.MpaApi(self.cluster.api_client)
        try:
            result = api.get_settings_privilege_action_metadata()
            return result.privilege_action_metadata.to_dict() if hasattr(result, "privilege_action_metadata") and result.privilege_action_metadata else {}
        except ApiException as e:
            return {"error": str(e)}

    def list_trust_anchors(self):
        """List trusted root CAs for MPA."""
        api = isi_sdk.MpaApi(self.cluster.api_client)
        try:
            result = api.list_mpa_trust_anchors()
            anchors = result.trust_anchors if hasattr(result, "trust_anchors") and result.trust_anchors else []
            return {"items": [a.to_dict() for a in anchors]}
        except ApiException as e:
            return {"error": str(e)}
