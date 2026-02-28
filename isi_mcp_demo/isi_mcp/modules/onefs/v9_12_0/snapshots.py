import logging
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.ansible.runner import AnsibleRunner

logger = logging.getLogger(__name__)


class Snapshots:
    """Manages snapshots on a PowerScale cluster."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self, limit=1000, resume=None):
        """Return a paginated list of snapshots.

        Args:
            limit: Maximum number of snapshots to return per page.
            resume: Resume token from a previous call for pagination.

        Returns:
            dict with 'items' (list of snapshot dicts) and 'resume' token.
        """
        snapshot_api = isi_sdk.SnapshotApi(self.cluster.api_client)
        try:
            kwargs = {"limit": limit}
            if resume:
                kwargs["resume"] = resume
            result = snapshot_api.list_snapshot_snapshots(**kwargs)
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"items": [], "resume": None}

        items = [s.to_dict() for s in result.snapshots] if result.snapshots else []

        return {
            "items": items,
            "resume": result.resume
        }

    def create(self, path: str, snapshot_name: str = None, alias: str = None,
               desired_retention: int = None, retention_unit: str = "hours",
               expiration_timestamp: str = None) -> dict:
        """Create a snapshot via Ansible.

        Args:
            path: Filesystem path to snapshot.
            snapshot_name: Name for snapshot (auto-generated if omitted).
            alias: Alias name to create for this snapshot.
            desired_retention: Retention period as an integer.
            retention_unit: Unit for retention (default "hours"). Options: hours, days, weeks.
            expiration_timestamp: UTC expiration time (mutually exclusive with retention).

        Returns:
            dict with success status and Ansible execution details.
        """
        runner = AnsibleRunner(self.cluster)
        variables = {
            "path": path,
            "snapshot_name": snapshot_name or f"snapshot-{path.replace('/', '-')}",
        }
        if alias:
            variables["alias"] = alias
        if desired_retention:
            variables["desired_retention"] = desired_retention
            variables["retention_unit"] = retention_unit
        if expiration_timestamp:
            variables["expiration_timestamp"] = expiration_timestamp
        return runner.execute("snapshot_create.yml.j2", variables)

    def delete(self, snapshot_name: str) -> dict:
        """Remove a snapshot via Ansible.

        Args:
            snapshot_name: Name or ID of the snapshot to delete.

        Returns:
            dict with success status and Ansible execution details.
        """
        runner = AnsibleRunner(self.cluster)
        variables = {
            "snapshot_name": snapshot_name,
        }
        return runner.execute("snapshot_remove.yml.j2", variables)

    def get_pending(self, begin: int = None, end: int = None, schedule: str = None,
                   limit: int = 1000, resume: str = None) -> dict:
        """Return a paginated list of pending snapshots.

        Args:
            begin: Unix epoch time to start generating matches (default: now).
            end: Unix epoch time to end generating matches (default: forever).
            schedule: Filter by specific schedule name.
            limit: Maximum number of pending snapshots to return per page.
            resume: Resume token from a previous call for pagination.

        Returns:
            dict with 'items' (list of pending snapshot dicts), 'resume' token, and 'has_more'.
        """
        snapshot_api = isi_sdk.SnapshotApi(self.cluster.api_client)
        try:
            kwargs = {"limit": limit}
            if resume:
                kwargs["resume"] = resume
            if begin is not None:
                kwargs["begin"] = begin
            if end is not None:
                kwargs["end"] = end
            if schedule:
                kwargs["schedule"] = schedule
            result = snapshot_api.get_snapshot_pending(**kwargs)
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"items": [], "resume": None, "has_more": False}

        items = [p.to_dict() for p in result.pending] if result.pending else []

        return {
            "items": items,
            "resume": result.resume,
            "has_more": bool(result.resume)
        }

    def create_alias(self, name: str, target: str) -> dict:
        """Create a snapshot alias via SDK.

        Args:
            name: Alias name to create.
            target: Snapshot name or ID to point alias to.

        Returns:
            dict with success status and alias details.
        """
        snapshot_api = isi_sdk.SnapshotApi(self.cluster.api_client)
        try:
            alias_params = isi_sdk.SnapshotAliasCreateParams(name=name, target=target)
            result = snapshot_api.create_snapshot_alias(alias_params)
            return {
                "success": True,
                "message": f"Snapshot alias '{name}' created pointing to '{target}'",
                "id": result.id if hasattr(result, 'id') else None
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

    def get_alias(self, alias_id: str) -> dict:
        """Get information about a snapshot alias.

        Args:
            alias_id: Alias name or ID to retrieve.

        Returns:
            dict with alias details.
        """
        snapshot_api = isi_sdk.SnapshotApi(self.cluster.api_client)
        try:
            result = snapshot_api.get_snapshot_alias(alias_id)
            alias_dict = result.aliases[0].to_dict() if result.aliases else {}
            return {
                "success": True,
                "alias": alias_dict
            }
        except ApiException as e:
            return {
                "success": False,
                "error": f"API error: {e}"
            }

