import logging
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException

logger = logging.getLogger(__name__)


class DataMover:
    """Manages DataMover policies and operations on a PowerScale cluster."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get_policies(self, limit=1000, resume=None):
        """Return a paginated list of DataMover policies.

        Args:
            limit: Maximum number of policies to return per page.
            resume: Resume token from a previous call for pagination.

        Returns:
            dict with 'items' (list of policy dicts) and 'resume' token.
        """
        datamover_api = isi_sdk.DatamoverApi(self.cluster.api_client)
        try:
            kwargs = {"limit": limit}
            if resume:
                kwargs["resume"] = resume
            result = datamover_api.list_datamover_policies(**kwargs)
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"items": [], "resume": None}

        items = [p.to_dict() for p in result.policies] if result.policies else []

        return {
            "items": items,
            "resume": result.resume
        }

    def get_policy(self, policy_id: str) -> dict:
        """Get information about a specific DataMover policy.

        Args:
            policy_id: Policy name or ID to retrieve.

        Returns:
            dict with policy details.
        """
        datamover_api = isi_sdk.DatamoverApi(self.cluster.api_client)
        try:
            result = datamover_api.get_datamover_policy(policy_id)
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

    def create_policy(self, name: str, base_policy_id: int = None,
                     enabled: bool = None, priority: str = None,
                     run_now: bool = None, schedule: str = None,
                     **kwargs) -> dict:
        """Create a DataMover policy via SDK.

        Args:
            name: A user-provided policy name (required).
            base_policy_id: The unique base policy identifier.
            enabled: True to enable the policy, False otherwise.
            priority: The relative priority of the policy.
            run_now: Execute the policy immediately instead of waiting for schedule.
            schedule: The schedule of the policy (start time, recurrence, etc.).
            **kwargs: Additional policy parameters (briefcase, parent_exec_policy_id, etc.).

        Returns:
            dict with success status and policy creation details.
        """
        datamover_api = isi_sdk.DatamoverApi(self.cluster.api_client)
        try:
            # Build policy parameters
            policy_params = {"name": name}

            if base_policy_id is not None:
                policy_params["base_policy_id"] = base_policy_id
            if enabled is not None:
                policy_params["enabled"] = enabled
            if priority is not None:
                policy_params["priority"] = priority
            if run_now is not None:
                policy_params["run_now"] = run_now
            if schedule is not None:
                policy_params["schedule"] = schedule

            # Add any additional kwargs
            policy_params.update(kwargs)

            # Create the policy object
            policy = isi_sdk.DatamoverPolicyCreateParams(**policy_params)

            result = datamover_api.create_datamover_policy(datamover_policy=policy)

            return {
                "success": True,
                "message": f"DataMover policy '{name}' created successfully",
                "id": result.id if hasattr(result, 'id') else None
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

    def delete_policy(self, policy_id: str) -> dict:
        """Delete a DataMover policy.

        Args:
            policy_id: Policy name or ID to delete.

        Returns:
            dict with success status.
        """
        datamover_api = isi_sdk.DatamoverApi(self.cluster.api_client)
        try:
            datamover_api.delete_datamover_policy(policy_id)
            return {
                "success": True,
                "message": f"DataMover policy '{policy_id}' deleted successfully"
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

    def get_policy_last_job(self, policy_id: str) -> dict:
        """Get the last job information for a specific DataMover policy.

        Args:
            policy_id: Policy name or ID to query.

        Returns:
            dict with last job details (job ID and execution time).
        """
        datamover_policies_api = isi_sdk.DatamoverPoliciesApi(self.cluster.api_client)
        try:
            result = datamover_policies_api.get_policy_last_job(policy_id)
            job_dict = result.to_dict() if result else {}
            return {
                "success": True,
                "last_job": job_dict
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

    # ========================================================================
    # Account Management Methods
    # ========================================================================

    def get_accounts(self, limit=1000, resume=None):
        """Return a paginated list of DataMover accounts.

        Args:
            limit: Maximum number of accounts to return per page.
            resume: Resume token from a previous call for pagination.

        Returns:
            dict with 'items' (list of account dicts) and 'resume' token.
        """
        datamover_api = isi_sdk.DatamoverApi(self.cluster.api_client)
        try:
            kwargs = {"limit": limit}
            if resume:
                kwargs["resume"] = resume
            result = datamover_api.list_datamover_accounts(**kwargs)
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"items": [], "resume": None}

        items = [a.to_dict() for a in result.accounts] if result.accounts else []

        return {
            "items": items,
            "resume": result.resume
        }

    def get_account(self, account_id: str) -> dict:
        """Get information about a specific DataMover account.

        Args:
            account_id: Account name or ID to retrieve.

        Returns:
            dict with account details.
        """
        datamover_api = isi_sdk.DatamoverApi(self.cluster.api_client)
        try:
            result = datamover_api.get_datamover_account(account_id)
            account_dict = result.accounts[0].to_dict() if result.accounts else {}
            return {
                "success": True,
                "account": account_dict
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

    def create_account(self, name: str, account_type: str, uri: str,
                      briefcase: str = None, credentials: dict = None,
                      enforce_sse: bool = None, local_network_pool: str = None,
                      max_sparks: int = None, remote_network_pool: str = None,
                      storage_class: str = None, **kwargs) -> dict:
        """Create a DataMover account via SDK.

        Args:
            name: Name for this DataMover account (required).
            account_type: Type of the data storage account (required, e.g. "s3", "nfs").
            uri: A valid URI pointing to the data storage (required).
            briefcase: Opaque container for storing additional data (optional).
            credentials: Credentials object for authentication (optional).
            enforce_sse: Enforce Server-Side Encryption (AWS S3 only, optional).
            local_network_pool: Local network restriction (optional).
            max_sparks: Limit of concurrent tasks per node (optional).
            remote_network_pool: Remote network restriction (optional).
            storage_class: Storage class for cloud accounts (optional).
            **kwargs: Additional account parameters.

        Returns:
            dict with success status and account creation details.
        """
        datamover_api = isi_sdk.DatamoverApi(self.cluster.api_client)
        try:
            # Build account parameters
            account_params = {
                "name": name,
                "account_type": account_type,
                "uri": uri
            }

            if briefcase is not None:
                account_params["briefcase"] = briefcase
            if credentials is not None:
                account_params["credentials"] = credentials
            if enforce_sse is not None:
                account_params["enforce_sse"] = enforce_sse
            if local_network_pool is not None:
                account_params["local_network_pool"] = local_network_pool
            if max_sparks is not None:
                account_params["max_sparks"] = max_sparks
            if remote_network_pool is not None:
                account_params["remote_network_pool"] = remote_network_pool
            if storage_class is not None:
                account_params["storage_class"] = storage_class

            # Add any additional kwargs
            account_params.update(kwargs)

            # Create the account object
            account = isi_sdk.DatamoverAccountCreateParams(**account_params)

            result = datamover_api.create_datamover_account(datamover_account=account)

            return {
                "success": True,
                "message": f"DataMover account '{name}' created successfully",
                "id": result.id if hasattr(result, 'id') else None
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

    def delete_account(self, account_id: str) -> dict:
        """Delete a DataMover account.

        Args:
            account_id: Account name or ID to delete.

        Returns:
            dict with success status.
        """
        datamover_api = isi_sdk.DatamoverApi(self.cluster.api_client)
        try:
            datamover_api.delete_datamover_account(account_id)
            return {
                "success": True,
                "message": f"DataMover account '{account_id}' deleted successfully"
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

    # ========================================================================
    # Base Policy Management Methods
    # ========================================================================

    def get_base_policies(self, limit=1000, resume=None):
        """Return a paginated list of DataMover base policies.

        Args:
            limit: Maximum number of base policies to return per page.
            resume: Resume token from a previous call for pagination.

        Returns:
            dict with 'items' (list of base policy dicts) and 'resume' token.
        """
        datamover_api = isi_sdk.DatamoverApi(self.cluster.api_client)
        try:
            kwargs = {"limit": limit}
            if resume:
                kwargs["resume"] = resume
            result = datamover_api.list_datamover_base_policies(**kwargs)
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"items": [], "resume": None}

        items = [bp.to_dict() for bp in result.policies] if result.policies else []

        return {
            "items": items,
            "resume": result.resume
        }

    def get_base_policy(self, base_policy_id: str) -> dict:
        """Get information about a specific DataMover base policy.

        Args:
            base_policy_id: Base policy name or ID to retrieve.

        Returns:
            dict with base policy details.
        """
        datamover_api = isi_sdk.DatamoverApi(self.cluster.api_client)
        try:
            result = datamover_api.get_datamover_base_policy(base_policy_id)
            base_policy_dict = result.base_policies[0].to_dict() if result.base_policies else {}
            return {
                "success": True,
                "base_policy": base_policy_dict
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

    def create_base_policy(self, name: str, enabled: bool = None,
                          priority: str = None, source_account_id: str = None,
                          source_base_path: str = None, target_account_id: str = None,
                          target_base_path: str = None, **kwargs) -> dict:
        """Create a DataMover base policy via SDK.

        Args:
            name: A user-provided base policy name (required).
            enabled: True to enable the base policy, False otherwise (optional).
            priority: The relative priority of the base policy (optional).
            source_account_id: Source data storage account identifier (optional).
            source_base_path: Filesystem base path on source system (optional).
            target_account_id: Destination data storage account identifier (optional).
            target_base_path: Filesystem base path on target system (optional).
            **kwargs: Additional base policy parameters (schedule, source_subpaths, etc.).

        Returns:
            dict with success status and base policy creation details.
        """
        datamover_api = isi_sdk.DatamoverApi(self.cluster.api_client)
        try:
            # Build base policy parameters
            base_policy_params = {"name": name}

            if enabled is not None:
                base_policy_params["enabled"] = enabled
            if priority is not None:
                base_policy_params["priority"] = priority
            if source_account_id is not None:
                base_policy_params["source_account_id"] = source_account_id
            if source_base_path is not None:
                base_policy_params["source_base_path"] = source_base_path
            if target_account_id is not None:
                base_policy_params["target_account_id"] = target_account_id
            if target_base_path is not None:
                base_policy_params["target_base_path"] = target_base_path

            # Add any additional kwargs
            base_policy_params.update(kwargs)

            # Create the base policy object
            base_policy = isi_sdk.DatamoverBasePolicyCreateParams(**base_policy_params)

            result = datamover_api.create_datamover_base_policy(datamover_base_policy=base_policy)

            return {
                "success": True,
                "message": f"DataMover base policy '{name}' created successfully",
                "id": result.id if hasattr(result, 'id') else None
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

    def delete_base_policy(self, base_policy_id: str) -> dict:
        """Delete a DataMover base policy.

        Args:
            base_policy_id: Base policy name or ID to delete.

        Returns:
            dict with success status.
        """
        datamover_api = isi_sdk.DatamoverApi(self.cluster.api_client)
        try:
            datamover_api.delete_datamover_base_policy(base_policy_id)
            return {
                "success": True,
                "message": f"DataMover base policy '{base_policy_id}' deleted successfully"
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }
