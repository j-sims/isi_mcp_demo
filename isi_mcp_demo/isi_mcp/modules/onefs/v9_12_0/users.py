import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.ansible.runner import AnsibleRunner


class Users:
    """Manages local user accounts on a PowerScale cluster."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self, user_name=None, provider_type=None, access_zone=None,
            limit=1000, resume=None):
        """List users or retrieve a specific user via the Auth API."""
        auth_api = isi_sdk.AuthApi(self.cluster.api_client)
        try:
            if user_name:
                # Fetch a single user by name
                auth_user_id = f"user:{user_name}"
                kwargs = {}
                if provider_type:
                    kwargs["provider"] = provider_type
                if access_zone:
                    kwargs["zone"] = access_zone
                result = auth_api.get_auth_user(auth_user_id, **kwargs)
                users = result.users if result.users else []
                return {"items": [u.to_dict() for u in users], "resume": None}
            else:
                # List all users with optional filters
                kwargs = {"limit": limit}
                if resume:
                    kwargs["resume"] = resume
                if provider_type:
                    kwargs["provider"] = provider_type
                if access_zone:
                    kwargs["zone"] = access_zone
                result = auth_api.list_auth_users(**kwargs)
                users = result.users if result.users else []
                return {
                    "items": [u.to_dict() for u in users],
                    "resume": result.resume,
                }
        except ApiException as e:
            return {"error": str(e)}

    def add(self, user_name: str, password: str,
            access_zone: str = None, provider_type: str = None,
            primary_group: str = None, enabled: bool = None,
            email: str = None, full_name: str = None,
            home_directory: str = None, shell: str = None,
            user_id: int = None,
            role_name: str = None, role_state: str = None,
            update_password: str = "on_create") -> dict:
        """Create a local user via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {
            "user_name": user_name,
            "password": password,
            "update_password": update_password,
        }
        if access_zone:
            variables["access_zone"] = access_zone
        if provider_type:
            variables["provider_type"] = provider_type
        if primary_group:
            variables["primary_group"] = primary_group
        if enabled is not None:
            variables["enabled"] = enabled
        if email:
            variables["email"] = email
        if full_name:
            variables["full_name"] = full_name
        if home_directory:
            variables["home_directory"] = home_directory
        if shell:
            variables["shell"] = shell
        if user_id is not None:
            variables["user_id"] = user_id
        if role_name:
            variables["role_name"] = role_name
        if role_state:
            variables["role_state"] = role_state
        return runner.execute("user_create.yml.j2", variables)

    def modify(self, user_name: str,
               access_zone: str = None, provider_type: str = None,
               primary_group: str = None, enabled: bool = None,
               email: str = None, full_name: str = None,
               home_directory: str = None, shell: str = None,
               password: str = None, update_password: str = None,
               role_name: str = None, role_state: str = None) -> dict:
        """Modify an existing user via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {
            "user_name": user_name,
        }
        if access_zone:
            variables["access_zone"] = access_zone
        if provider_type:
            variables["provider_type"] = provider_type
        if primary_group is not None:
            variables["primary_group"] = primary_group
        if enabled is not None:
            variables["enabled"] = enabled
        if email is not None:
            variables["email"] = email
        if full_name is not None:
            variables["full_name"] = full_name
        if home_directory is not None:
            variables["home_directory"] = home_directory
        if shell is not None:
            variables["shell"] = shell
        if password is not None:
            variables["password"] = password
        if update_password is not None:
            variables["update_password"] = update_password
        if role_name:
            variables["role_name"] = role_name
        if role_state:
            variables["role_state"] = role_state
        return runner.execute("user_modify.yml.j2", variables)

    def remove(self, user_name: str,
               access_zone: str = None, provider_type: str = None) -> dict:
        """Delete a local user via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {
            "user_name": user_name,
        }
        if access_zone:
            variables["access_zone"] = access_zone
        if provider_type:
            variables["provider_type"] = provider_type
        return runner.execute("user_remove.yml.j2", variables)
