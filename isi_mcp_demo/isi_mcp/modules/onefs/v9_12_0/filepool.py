import json
import logging
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.ansible.runner import AnsibleRunner

logger = logging.getLogger(__name__)


class FilePool:
    """Manages FilePool policies on a PowerScale cluster."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    # ------------------------------------------------------------------
    # Read operations (SDK)
    # ------------------------------------------------------------------

    def get(self):
        """Return all filepool policies.

        The FilePool API does not support pagination — all policies are
        returned in a single response.

        Returns:
            dict with 'items' (list of policy dicts) and 'total' count.
        """
        filepool_api = isi_sdk.FilepoolApi(self.cluster.api_client)
        try:
            result = filepool_api.list_filepool_policies()
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"items": [], "total": 0}

        items = [p.to_dict() for p in result.policies] if result.policies else []

        return {
            "items": items,
            "total": result.total if hasattr(result, 'total') else len(items)
        }

    def get_policy(self, policy_id: str) -> dict:
        """Get a single filepool policy by name or ID.

        Args:
            policy_id: Policy name or ID to retrieve.

        Returns:
            dict with success status and policy details.
        """
        filepool_api = isi_sdk.FilepoolApi(self.cluster.api_client)
        try:
            result = filepool_api.get_filepool_policy(policy_id)
            policy_dict = result.policies[0].to_dict() if result.policies else {}
            return {
                "success": True,
                "policy": policy_dict
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

    def get_default_policy(self) -> dict:
        """Get the system default filepool policy.

        Returns:
            dict with default policy details.
        """
        filepool_api = isi_sdk.FilepoolApi(self.cluster.api_client)
        try:
            result = filepool_api.get_filepool_default_policy()
            policy_dict = result.default_policy.to_dict() if hasattr(result, 'default_policy') and result.default_policy else {}
            return {
                "success": True,
                "default_policy": policy_dict
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

    # ------------------------------------------------------------------
    # Create (Ansible)
    # ------------------------------------------------------------------

    def create(self, policy_name: str,
               file_matching_pattern: str,
               description: str = None,
               apply_order: int = None,
               apply_data_storage_policy: str = None,
               apply_snapshot_storage_policy: str = None,
               set_requested_protection: str = None,
               set_data_access_pattern: str = None,
               set_write_performance_optimization: str = None) -> dict:
        """Create a filepool policy via Ansible.

        Args:
            policy_name: Unique name for the policy.
            file_matching_pattern: JSON string defining the matching rules.
            description: Optional description.
            apply_order: Optional ordering relative to other policies.
            apply_data_storage_policy: JSON string with ssd_strategy and storagepool.
            apply_snapshot_storage_policy: JSON string, same structure as data storage.
            set_requested_protection: Protection string.
            set_data_access_pattern: "random", "concurrency", or "streaming".
            set_write_performance_optimization: "enable_smartcache" or "disable_smartcache".

        Returns:
            dict with success status and Ansible execution details.
        """
        runner = AnsibleRunner(self.cluster)
        variables = {
            "policy_name": policy_name,
            "file_matching_pattern": json.loads(file_matching_pattern),
        }
        if description:
            variables["description"] = description
        if apply_order is not None:
            variables["apply_order"] = apply_order
        if apply_data_storage_policy:
            variables["apply_data_storage_policy"] = json.loads(apply_data_storage_policy)
        if apply_snapshot_storage_policy:
            variables["apply_snapshot_storage_policy"] = json.loads(apply_snapshot_storage_policy)
        if set_requested_protection:
            variables["set_requested_protection"] = set_requested_protection
        if set_data_access_pattern:
            variables["set_data_access_pattern"] = set_data_access_pattern
        if set_write_performance_optimization:
            variables["set_write_performance_optimization"] = set_write_performance_optimization

        return runner.execute("filepool_create.yml.j2", variables)

    # ------------------------------------------------------------------
    # Update (SDK — Ansible does not support modify)
    # ------------------------------------------------------------------

    def update(self, policy_id: str,
               description: str = None,
               apply_order: int = None,
               file_matching_pattern: str = None,
               apply_data_storage_policy: str = None,
               apply_snapshot_storage_policy: str = None,
               set_requested_protection: str = None,
               set_data_access_pattern: str = None,
               set_write_performance_optimization: str = None) -> dict:
        """Update a filepool policy via SDK.

        Only supplied (non-None) fields are modified. The Ansible module
        does not support modification, so this method uses the SDK directly.

        Args:
            policy_id: Policy name or ID to update.
            description: New description (optional).
            apply_order: New apply order (optional).
            file_matching_pattern: JSON string for new matching rules (optional).
            apply_data_storage_policy: JSON string (optional).
            apply_snapshot_storage_policy: JSON string (optional).
            set_requested_protection: Protection string (optional).
            set_data_access_pattern: Access pattern string (optional).
            set_write_performance_optimization: Write perf string (optional).

        Returns:
            dict with success status.
        """
        filepool_api = isi_sdk.FilepoolApi(self.cluster.api_client)
        try:
            update_params = {}

            if description is not None:
                update_params["description"] = description
            if apply_order is not None:
                update_params["apply_order"] = apply_order

            if file_matching_pattern is not None:
                update_params["file_matching_pattern"] = json.loads(file_matching_pattern)

            actions = self._build_actions(
                apply_data_storage_policy=apply_data_storage_policy,
                apply_snapshot_storage_policy=apply_snapshot_storage_policy,
                set_requested_protection=set_requested_protection,
                set_data_access_pattern=set_data_access_pattern,
                set_write_performance_optimization=set_write_performance_optimization,
            )
            if actions is not None:
                update_params["actions"] = actions

            if not update_params:
                return {
                    "success": False,
                    "error": "No fields provided to update."
                }

            policy = isi_sdk.FilepoolPolicy(**update_params)
            filepool_api.update_filepool_policy(
                filepool_policy=policy,
                filepool_policy_id=policy_id
            )

            return {
                "success": True,
                "message": f"FilePool policy '{policy_id}' updated successfully"
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

    # ------------------------------------------------------------------
    # Delete (Ansible)
    # ------------------------------------------------------------------

    def delete(self, policy_name: str) -> dict:
        """Remove a filepool policy via Ansible.

        Args:
            policy_name: Name of the policy to remove.

        Returns:
            dict with success status and Ansible execution details.
        """
        runner = AnsibleRunner(self.cluster)
        variables = {
            "policy_name": policy_name,
        }
        return runner.execute("filepool_remove.yml.j2", variables)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_actions(self, apply_data_storage_policy=None,
                       apply_snapshot_storage_policy=None,
                       set_requested_protection=None,
                       set_data_access_pattern=None,
                       set_write_performance_optimization=None):
        """Convert friendly action parameters to SDK FilepoolPolicyAction list.

        Returns list of action dicts, or None if no actions provided.
        """
        actions = []

        if apply_data_storage_policy:
            parsed = json.loads(apply_data_storage_policy) if isinstance(apply_data_storage_policy, str) else apply_data_storage_policy
            actions.append({
                "action_type": "apply_data_storage_policy",
                "action_param": json.dumps(parsed) if isinstance(parsed, dict) else str(parsed)
            })

        if apply_snapshot_storage_policy:
            parsed = json.loads(apply_snapshot_storage_policy) if isinstance(apply_snapshot_storage_policy, str) else apply_snapshot_storage_policy
            actions.append({
                "action_type": "apply_snapshot_storage_policy",
                "action_param": json.dumps(parsed) if isinstance(parsed, dict) else str(parsed)
            })

        if set_requested_protection:
            actions.append({
                "action_type": "set_requested_protection",
                "action_param": set_requested_protection
            })

        if set_data_access_pattern:
            actions.append({
                "action_type": "set_data_access_pattern",
                "action_param": set_data_access_pattern
            })

        if set_write_performance_optimization:
            actions.append({
                "action_type": "set_write_performance_optimization",
                "action_param": set_write_performance_optimization
            })

        return actions if actions else None
