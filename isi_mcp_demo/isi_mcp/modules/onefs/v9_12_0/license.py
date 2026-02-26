import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class License:

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self, resume: str = None):
        """
        List all installed licenses with their status and expiration info.

        Returns license name, current status (Evaluation/Activated/Expired/Unlicensed),
        expiration date, days-to-expiry, and any alert flags.
        Supports pagination via resume token for large license lists.
        """
        license_api = isi_sdk.LicenseApi(self.cluster.api_client)
        try:
            kwargs = {}
            if resume:
                kwargs["resume"] = resume
            result = license_api.list_license_licenses(**kwargs)
            licenses = result.licenses if result.licenses else []
            return {
                "items": [lic.to_dict() for lic in licenses],
                "resume": getattr(result, "resume", None),
                "total": getattr(result, "total", len(licenses)),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_by_name(self, name: str):
        """
        Get details for a specific license by name.

        Arguments:
        - name: The license name (e.g. "HDFS", "SmartQuotas", "SnapshotIQ",
                "SyncIQ", "SmartDedupe", "SmartConnect", "SmartConnect_Advanced",
                "InsightIQ", "DataMover", "CloudPools")
        """
        license_api = isi_sdk.LicenseApi(self.cluster.api_client)
        try:
            result = license_api.get_license_license(name)
            licenses = result.licenses if result.licenses else []
            if licenses:
                return licenses[0].to_dict()
            return {"error": f"License '{name}' not found"}
        except ApiException as e:
            return {"error": str(e)}
