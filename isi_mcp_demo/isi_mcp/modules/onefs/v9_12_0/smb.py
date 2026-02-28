import json
import logging
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.ansible.runner import AnsibleRunner

logger = logging.getLogger(__name__)

class Smb:
    """holds all functions related to SMB shares on a powerscale cluster."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self, limit=1000, resume=None):
        protocols_api = isi_sdk.ProtocolsApi(self.cluster.api_client)
        kwargs = {"limit": limit}
        if resume:
            kwargs["resume"] = resume
        result = protocols_api.list_smb_shares(**kwargs)

        items = [s.to_dict() for s in result.shares] if result.shares else []

        return {
            "items": items,
            "resume": result.resume
        }

    def add(self, share_name: str, path: str, description: str = None,
            access_zone: str = None, create_path: bool = None,
            browsable: bool = None, access_based_enumeration: bool = None,
            access_based_enumeration_root_only: bool = None,
            ntfs_acl_support: bool = None, oplocks: bool = None,
            continuously_available: bool = None,
            smb3_encryption_enabled: bool = None,
            directory_create_mask: str = None, directory_create_mode: str = None,
            file_create_mask: str = None, file_create_mode: str = None,
            allow_variable_expansion: bool = None,
            auto_create_directory: bool = None,
            inheritable_path_acl: bool = None,
            allow_delete_readonly: bool = None,
            allow_execute_always: bool = None,
            ca_timeout: dict = None,
            strict_ca_lockout: bool = None,
            ca_write_integrity: str = None,
            change_notify: str = None,
            impersonate_guest: str = None,
            impersonate_user: str = None,
            file_filtering_enabled: bool = None,
            file_filter_extension: str = None,
            permissions: str = None,
            host_acls: str = None,
            run_as_root: str = None) -> dict:
        """Create an SMB share via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {
            "share_name": share_name,
            "path": path,
        }
        if description:
            variables["description"] = description
        if access_zone:
            variables["access_zone"] = access_zone

        # Boolean parameters — pass through when explicitly set
        bool_params = {
            "create_path": create_path,
            "browsable": browsable,
            "access_based_enumeration": access_based_enumeration,
            "access_based_enumeration_root_only": access_based_enumeration_root_only,
            "ntfs_acl_support": ntfs_acl_support,
            "oplocks": oplocks,
            "continuously_available": continuously_available,
            "smb3_encryption_enabled": smb3_encryption_enabled,
            "strict_ca_lockout": strict_ca_lockout,
            "allow_variable_expansion": allow_variable_expansion,
            "auto_create_directory": auto_create_directory,
            "inheritable_path_acl": inheritable_path_acl,
            "allow_delete_readonly": allow_delete_readonly,
            "allow_execute_always": allow_execute_always,
            "file_filtering_enabled": file_filtering_enabled,
        }
        for key, val in bool_params.items():
            if val is not None:
                variables[key] = val

        # Octal string parameters
        for key, val in [("directory_create_mask", directory_create_mask),
                         ("directory_create_mode", directory_create_mode),
                         ("file_create_mask", file_create_mask),
                         ("file_create_mode", file_create_mode)]:
            if val:
                variables[key] = val

        # String parameters
        for key, val in [("ca_write_integrity", ca_write_integrity),
                         ("change_notify", change_notify),
                         ("impersonate_guest", impersonate_guest),
                         ("impersonate_user", impersonate_user)]:
            if val:
                variables[key] = val

        # Dict parameter — ca_timeout
        if ca_timeout:
            variables["ca_timeout"] = ca_timeout

        # Complex parameters — JSON strings parsed to Python objects
        if file_filter_extension:
            variables["file_filter_extension"] = json.loads(file_filter_extension)
        if permissions:
            variables["permissions"] = json.loads(permissions)
        if host_acls:
            variables["host_acls"] = json.loads(host_acls)
        if run_as_root:
            variables["run_as_root"] = json.loads(run_as_root)

        return runner.execute("smb_create.yml.j2", variables)

    def get_global_settings(self) -> dict:
        """Retrieve SMB global settings via SDK."""
        protocols_api = isi_sdk.ProtocolsApi(self.cluster.api_client)
        try:
            result = protocols_api.get_smb_settings_global()
            return result.to_dict()
        except ApiException as e:
            return {"error": str(e)}

    def set_global_settings(self, service: bool = None,
                            support_smb2: bool = None,
                            support_smb3_encryption: bool = None,
                            access_based_share_enum: bool = None,
                            dot_snap_accessible_child: bool = None,
                            dot_snap_accessible_root: bool = None,
                            dot_snap_visible_child: bool = None,
                            dot_snap_visible_root: bool = None,
                            enable_security_signatures: bool = None,
                            require_security_signatures: bool = None,
                            reject_unencrypted_access: bool = None,
                            server_side_copy: bool = None,
                            support_multichannel: bool = None,
                            support_netbios: bool = None,
                            guest_user: str = None,
                            server_string: str = None,
                            onefs_cpu_multiplier: int = None,
                            onefs_num_workers: int = None,
                            ignore_eas: bool = None) -> dict:
        """Update SMB global settings via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {}

        bool_params = {
            "service": service,
            "support_smb2": support_smb2,
            "support_smb3_encryption": support_smb3_encryption,
            "access_based_share_enum": access_based_share_enum,
            "dot_snap_accessible_child": dot_snap_accessible_child,
            "dot_snap_accessible_root": dot_snap_accessible_root,
            "dot_snap_visible_child": dot_snap_visible_child,
            "dot_snap_visible_root": dot_snap_visible_root,
            "enable_security_signatures": enable_security_signatures,
            "require_security_signatures": require_security_signatures,
            "reject_unencrypted_access": reject_unencrypted_access,
            "server_side_copy": server_side_copy,
            "support_multichannel": support_multichannel,
            "support_netbios": support_netbios,
            "ignore_eas": ignore_eas,
        }
        for key, val in bool_params.items():
            if val is not None:
                variables[key] = val

        if guest_user is not None:
            variables["guest_user"] = guest_user
        if server_string is not None:
            variables["server_string"] = server_string
        if onefs_cpu_multiplier is not None:
            variables["onefs_cpu_multiplier"] = onefs_cpu_multiplier
        if onefs_num_workers is not None:
            variables["onefs_num_workers"] = onefs_num_workers

        return runner.execute("smb_global_settings.yml.j2", variables)

    def remove(self, share_name: str) -> dict:
        """Remove an SMB share via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {
            "share_name": share_name,
        }
        return runner.execute("smb_remove.yml.j2", variables)

    def get_sessions(self, limit: int = 1000, lnn: str = None,
                     lnn_skip: str = None, resume: str = None) -> dict:
        """List all open SMB sessions across cluster nodes."""
        protocols_api = isi_sdk.ProtocolsApi(self.cluster.api_client)
        try:
            kwargs = {}
            if resume:
                kwargs["resume"] = resume
            else:
                kwargs["limit"] = limit
                if lnn:
                    kwargs["lnn"] = lnn
                if lnn_skip:
                    kwargs["lnn_skip"] = lnn_skip
            result = protocols_api.get_smb_sessions(**kwargs)
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"error": str(e)}

        nodes = [n.to_dict() for n in result.nodes] if result.nodes else []
        return {
            "nodes": nodes,
            "resume": result.resume,
            "total": result.total,
        }

    def delete_session(self, session_id: str) -> dict:
        """Close an SMB session by ID."""
        protocols_api = isi_sdk.ProtocolsApi(self.cluster.api_client)
        try:
            protocols_api.delete_smb_session(session_id)
            return {"success": True, "message": f"SMB session '{session_id}' closed"}
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"error": str(e)}

    def delete_sessions_by_user(self, computer: str, user: str) -> dict:
        """Close all SMB sessions for a specific user on a specific computer."""
        protocols_api = isi_sdk.ProtocolsApi(self.cluster.api_client)
        try:
            protocols_api.delete_smb_sessions_computer_user(user, computer)
            return {"success": True, "message": f"All SMB sessions for user '{user}' on computer '{computer}' closed"}
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"error": str(e)}

    def get_openfiles(self, limit: int = 1000, resume: str = None,
                      sort: str = None, dir: str = None) -> dict:
        """List all open files on the SMB server."""
        protocols_api = isi_sdk.ProtocolsApi(self.cluster.api_client)
        try:
            kwargs = {}
            if resume:
                kwargs["resume"] = resume
            else:
                kwargs["limit"] = limit
                if sort:
                    kwargs["sort"] = sort
                if dir:
                    kwargs["dir"] = dir
            result = protocols_api.get_smb_openfiles(**kwargs)
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"error": str(e)}

        items = [f.to_dict() for f in result.openfiles] if result.openfiles else []
        return {
            "items": items,
            "resume": result.resume,
            "total": result.total,
        }

    def delete_openfile(self, openfile_id: str) -> dict:
        """Close (forcibly terminate) an open SMB file by ID."""
        protocols_api = isi_sdk.ProtocolsApi(self.cluster.api_client)
        try:
            protocols_api.delete_smb_openfile(openfile_id)
            return {"success": True, "message": f"SMB open file '{openfile_id}' closed"}
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"error": str(e)}
