import json
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.ansible.runner import AnsibleRunner


class Group:
    """Manages local groups on a PowerScale cluster."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self, group_name=None, group_id=None, provider_type=None,
            access_zone=None, limit=1000, resume=None):
        """List groups or retrieve a specific group via the Auth API."""
        auth_api = isi_sdk.AuthApi(self.cluster.api_client)
        try:
            if group_name or group_id is not None:
                # Fetch a single group by name or GID
                if group_name:
                    auth_group_id = f"group:{group_name}"
                else:
                    auth_group_id = f"GID:{group_id}"
                kwargs = {}
                if provider_type:
                    kwargs["provider"] = provider_type
                if access_zone:
                    kwargs["zone"] = access_zone
                result = auth_api.get_auth_group(auth_group_id, **kwargs)
                groups = result.groups if result.groups else []
                return {"items": [g.to_dict() for g in groups], "resume": None}
            else:
                # List all groups with optional filters
                kwargs = {"limit": limit}
                if resume:
                    kwargs["resume"] = resume
                if provider_type:
                    kwargs["provider"] = provider_type
                if access_zone:
                    kwargs["zone"] = access_zone
                result = auth_api.list_auth_groups(**kwargs)
                groups = result.groups if result.groups else []
                return {
                    "items": [g.to_dict() for g in groups],
                    "resume": result.resume,
                }
        except ApiException as e:
            return {"error": str(e)}

    def add(self, group_name: str,
            group_id: int = None,
            access_zone: str = None,
            provider_type: str = None,
            users=None,
            user_state: str = None) -> dict:
        """Create a local group via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {"group_name": group_name}
        if group_id is not None:
            variables["group_id"] = group_id
        if access_zone:
            variables["access_zone"] = access_zone
        if provider_type:
            variables["provider_type"] = provider_type
        if users:
            if isinstance(users, str):
                users = json.loads(users)
            variables["users"] = users
        if user_state:
            variables["user_state"] = user_state
        return runner.execute("group_create.yml.j2", variables)

    def modify(self, group_name: str = None,
               group_id: int = None,
               access_zone: str = None,
               provider_type: str = None,
               users=None,
               user_state: str = None) -> dict:
        """Add or remove members from an existing group via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {}
        if group_name:
            variables["group_name"] = group_name
        if group_id is not None:
            variables["group_id"] = group_id
        if access_zone:
            variables["access_zone"] = access_zone
        if provider_type:
            variables["provider_type"] = provider_type
        if users:
            if isinstance(users, str):
                users = json.loads(users)
            variables["users"] = users
        if user_state:
            variables["user_state"] = user_state
        return runner.execute("group_modify.yml.j2", variables)

    def remove(self, group_name: str = None,
               group_id: int = None,
               access_zone: str = None,
               provider_type: str = None) -> dict:
        """Delete a local group via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {}
        if group_name:
            variables["group_name"] = group_name
        if group_id is not None:
            variables["group_id"] = group_id
        if access_zone:
            variables["access_zone"] = access_zone
        if provider_type:
            variables["provider_type"] = provider_type
        return runner.execute("group_remove.yml.j2", variables)
