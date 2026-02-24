import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.ansible.runner import AnsibleRunner

class SyncIQ:
    """holds all functions related to SyncIQ replication on a powerscale cluster."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self):
        sync_api = isi_sdk.SyncApi(self.cluster.api_client)
        try:
            result = sync_api.list_sync_policies()
        except ApiException as e:
            print(f"API error: {e}")
            return

        items = [p.to_dict() for p in result.policies] if result.policies else []

        return {
            "items": items
        }

    def add(self, policy_name: str, source_path: str, target_host: str,
            target_path: str, action: str = "sync", schedule: str = None,
            description: str = None, enabled: bool = None) -> dict:
        """Create a SyncIQ policy via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {
            "policy_name": policy_name,
            "source_path": source_path,
            "target_host": target_host,
            "target_path": target_path,
            "action": action,
        }
        if schedule:
            variables["schedule"] = schedule
        if description:
            variables["description"] = description
        if enabled is not None:
            variables["enabled"] = str(enabled).lower()
        return runner.execute("synciq_create.yml.j2", variables)

    def remove(self, policy_name: str) -> dict:
        """Remove a SyncIQ policy via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {
            "policy_name": policy_name,
        }
        return runner.execute("synciq_remove.yml.j2", variables)
