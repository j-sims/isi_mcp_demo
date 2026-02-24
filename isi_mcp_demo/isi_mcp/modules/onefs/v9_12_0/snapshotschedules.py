import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.ansible.runner import AnsibleRunner


class SnapshotSchedules:
    """Manages snapshot schedules on a PowerScale cluster."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self, limit=1000, resume=None):
        """Return a paginated list of snapshot schedules.

        Args:
            limit: Maximum number of schedules to return per page.
            resume: Resume token from a previous call for pagination.

        Returns:
            dict with 'items' (list of schedule dicts) and 'resume' token.
        """
        snapshot_api = isi_sdk.SnapshotApi(self.cluster.api_client)
        try:
            kwargs = {"limit": limit}
            if resume:
                kwargs["resume"] = resume
            result = snapshot_api.list_snapshot_schedules(**kwargs)
        except ApiException as e:
            print(f"API error: {e}")
            return {"items": [], "resume": None}

        items = [s.to_dict() for s in result.schedules] if result.schedules else []

        return {
            "items": items,
            "resume": result.resume,
        }

    def add(self, name: str, path: str, schedule: str, pattern: str = None,
            desired_retention: int = None, retention_unit: str = "days",
            alias: str = None) -> dict:
        """Create a snapshot schedule via Ansible.

        Args:
            name: Schedule name.
            path: Filesystem path to snapshot.
            schedule: isidate schedule string (e.g. "Every day every 4 hours").
            pattern: Snapshot naming pattern (strftime). Defaults to "{name}_%Y-%m-%d_%H:%M".
            desired_retention: Retention period as an integer.
            retention_unit: Unit for retention period (default "days").
            alias: Optional alias for the latest snapshot in this schedule.

        Returns:
            dict with success status and Ansible execution details.
        """
        runner = AnsibleRunner(self.cluster)
        variables = {
            "name": name,
            "path": path,
            "schedule": schedule,
            "pattern": pattern or f"{name}_%Y-%m-%d_%H:%M",
        }
        if desired_retention:
            variables["desired_retention"] = desired_retention
            variables["retention_unit"] = retention_unit
        if alias:
            variables["alias"] = alias
        return runner.execute("snapshot_schedule_create.yml.j2", variables)

    def remove(self, name: str) -> dict:
        """Remove a snapshot schedule via Ansible.

        Args:
            name: Name of the snapshot schedule to remove.

        Returns:
            dict with success status and Ansible execution details.
        """
        runner = AnsibleRunner(self.cluster)
        variables = {
            "name": name,
        }
        return runner.execute("snapshot_schedule_remove.yml.j2", variables)
