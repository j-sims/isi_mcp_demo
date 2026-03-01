import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class MetadataIQ:
    """Provides access to MetadataIQ insights via the MetadataiqApi.

    Covers MetadataIQ settings, current cycle status, and CA certificate info.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get_settings(self):
        """Get MetadataIQ configuration settings."""
        api = isi_sdk.MetadataiqApi(self.cluster.api_client)
        try:
            result = api.get_metadataiq_settings()
            return result.settings.to_dict() if hasattr(result, "settings") and result.settings else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_status(self):
        """Get MetadataIQ current cycle status."""
        api = isi_sdk.MetadataiqApi(self.cluster.api_client)
        try:
            result = api.get_metadataiq_status()
            return result.status.to_dict() if hasattr(result, "status") and result.status else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_certificate(self):
        """Get MetadataIQ CA certificate information."""
        api = isi_sdk.MetadataiqApi(self.cluster.api_client)
        try:
            result = api.get_metadataiq_certificate()
            return result.certificate.to_dict() if hasattr(result, "certificate") and result.certificate else {}
        except ApiException as e:
            return {"error": str(e)}
