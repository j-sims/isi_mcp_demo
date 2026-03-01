import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class SupportAssist:
    """Provides access to PowerScale SupportAssist diagnostics via the SupportassistApi.

    Covers SupportAssist settings, status, license activation, tasks, and terms.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get_settings(self):
        """Get SupportAssist configuration settings."""
        api = isi_sdk.SupportassistApi(self.cluster.api_client)
        try:
            result = api.get_supportassist_settings()
            return result.settings.to_dict() if hasattr(result, "settings") and result.settings else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_status(self):
        """Get SupportAssist current status."""
        api = isi_sdk.SupportassistApi(self.cluster.api_client)
        try:
            result = api.get_supportassist_status()
            return result.status.to_dict() if hasattr(result, "status") and result.status else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_license(self):
        """Get SupportAssist license activation status."""
        api = isi_sdk.SupportassistApi(self.cluster.api_client)
        try:
            result = api.get_supportassist_license()
            return result.license.to_dict() if hasattr(result, "license") and result.license else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_terms(self):
        """Get SupportAssist Terms & Conditions text."""
        api = isi_sdk.SupportassistApi(self.cluster.api_client)
        try:
            result = api.get_supportassist_terms()
            return result.terms.to_dict() if hasattr(result, "terms") and result.terms else {}
        except ApiException as e:
            return {"error": str(e)}

    def list_tasks(self):
        """List all SupportAssist tasks."""
        api = isi_sdk.SupportassistApi(self.cluster.api_client)
        try:
            result = api.list_supportassist_task()
            tasks = result.tasks if hasattr(result, "tasks") and result.tasks else []
            return {"items": [t.to_dict() for t in tasks]}
        except ApiException as e:
            return {"error": str(e)}

    def get_task(self, task_id: str):
        """Get a specific SupportAssist task by ID.

        Arguments:
        - task_id: The task identifier
        """
        api = isi_sdk.SupportassistApi(self.cluster.api_client)
        try:
            result = api.get_supportassist_task_by_id(task_id)
            tasks = result.tasks if hasattr(result, "tasks") and result.tasks else []
            if tasks:
                return tasks[0].to_dict()
            return {"error": f"Task '{task_id}' not found"}
        except ApiException as e:
            return {"error": str(e)}
