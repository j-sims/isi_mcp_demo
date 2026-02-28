import re
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.ansible.runner import AnsibleRunner

class Nfs:
    """holds all functions related to NFS exports on a powerscale cluster."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def _validate_client(self, client: str) -> bool:
        """
        Validate a single NFS client entry.

        Valid formats:
        - IP address: 192.168.1.100
        - CIDR notation: 192.168.0.0/24
        - Hostname: server.example.com
        - Wildcard hostname: *.example.com

        Args:
            client: Client string to validate

        Returns:
            True if valid, False otherwise
        """
        if not client or not isinstance(client, str):
            return False

        # Check if it's IP/CIDR notation
        if '/' in client or (client.count('.') == 3 and all(c.isdigit() or c == '.' for c in client)):
            # Try to parse as IP or CIDR
            parts = client.split('/')
            ip_part = parts[0]

            # Validate IP octets
            try:
                octets = ip_part.split('.')
                if len(octets) != 4:
                    return False
                for octet in octets:
                    num = int(octet)
                    if num < 0 or num > 255:
                        return False
            except ValueError:
                return False

            # If CIDR notation, validate prefix length
            if len(parts) == 2:
                try:
                    prefix = int(parts[1])
                    if prefix < 0 or prefix > 32:
                        return False
                except ValueError:
                    return False
            elif len(parts) > 2:
                return False

            return True

        # Pattern for hostname (including wildcard)
        hostname_pattern = r'^(\*\.)?([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
        if re.match(hostname_pattern, client):
            return True

        return False

    def _validate_clients(self, clients: list, param_name: str = "clients") -> tuple:
        """
        Validate a list of NFS client entries.

        Args:
            clients: List of client entries
            param_name: Parameter name for error messages

        Returns:
            Tuple of (is_valid: bool, error_message: str or None)
        """
        if not clients:
            return True, None

        if not isinstance(clients, list):
            return False, f"{param_name} must be a list"

        invalid_clients = [c for c in clients if not self._validate_client(c)]
        if invalid_clients:
            return False, f"Invalid client format(s) in {param_name}: {', '.join(invalid_clients)}. Valid formats: IP address (192.168.1.100), CIDR (192.168.0.0/24), hostname (server.example.com)"

        return True, None

    def get(self, limit=1000, resume=None):
        protocols_api = isi_sdk.ProtocolsApi(self.cluster.api_client)
        kwargs = {"limit": limit}
        if resume:
            kwargs["resume"] = resume
        result = protocols_api.list_nfs_exports(**kwargs)

        items = [e.to_dict() for e in result.exports] if result.exports else []

        return {
            "items": items,
            "resume": result.resume
        }

    def add(self, path: str, access_zone: str = "System", description: str = None,
            clients: list = None, read_only: bool = None,
            # Phase 1 - Client Management
            client_state: str = None, read_only_clients: list = None,
            read_write_clients: list = None, root_clients: list = None,
            # Phase 2 - Security & Configuration
            security_flavors: list = None, sub_directories_mountable: bool = None,
            # Phase 3 - Root Mapping
            map_root: dict = None,
            # Phase 4 - Advanced Features
            map_non_root: dict = None, ignore_unresolvable_hosts: bool = None) -> dict:
        """Create an NFS export via Ansible."""
        # Validate client parameters
        for param_name, param_value in [
            ("clients", clients),
            ("read_only_clients", read_only_clients),
            ("read_write_clients", read_write_clients),
            ("root_clients", root_clients)
        ]:
            is_valid, error = self._validate_clients(param_value, param_name)
            if not is_valid:
                return {"success": False, "status": "failed", "error": error}

        runner = AnsibleRunner(self.cluster)
        variables = {
            "path": path,
            "access_zone": access_zone,
        }
        if description:
            variables["description"] = description
        if clients:
            variables["clients"] = clients
        if read_only is not None:
            variables["read_only"] = str(read_only).lower()

        # Phase 1 - Client Management
        if client_state:
            variables["client_state"] = client_state
        if read_only_clients:
            variables["read_only_clients"] = read_only_clients
        if read_write_clients:
            variables["read_write_clients"] = read_write_clients
        if root_clients:
            variables["root_clients"] = root_clients

        # Phase 2 - Security & Configuration
        if security_flavors:
            variables["security_flavors"] = security_flavors
        if sub_directories_mountable is not None:
            variables["sub_directories_mountable"] = str(sub_directories_mountable).lower()

        # Phase 3 - Root Mapping
        if map_root:
            variables["map_root"] = map_root

        # Phase 4 - Advanced Features
        if map_non_root:
            variables["map_non_root"] = map_non_root
        if ignore_unresolvable_hosts is not None:
            variables["ignore_unresolvable_hosts"] = str(ignore_unresolvable_hosts).lower()

        return runner.execute("nfs_create.yml.j2", variables)

    def get_global_settings(self) -> dict:
        """Retrieve NFS global settings via SDK."""
        protocols_api = isi_sdk.ProtocolsApi(self.cluster.api_client)
        try:
            result = protocols_api.get_nfs_settings_global()
            return result.to_dict()
        except ApiException as e:
            return {"error": str(e)}

    def set_global_settings(self, service: bool = None,
                            nfsv3: dict = None,
                            nfsv4: dict = None,
                            rpc_maxthreads: int = None,
                            rpc_minthreads: int = None,
                            rquota_enabled: bool = None,
                            nfs_rdma_enabled: bool = None) -> dict:
        """Update NFS global settings via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {}

        if service is not None:
            variables["service"] = service
        if nfsv3 is not None:
            variables["nfsv3"] = nfsv3
        if nfsv4 is not None:
            variables["nfsv4"] = nfsv4
        if rpc_maxthreads is not None:
            variables["rpc_maxthreads"] = rpc_maxthreads
        if rpc_minthreads is not None:
            variables["rpc_minthreads"] = rpc_minthreads
        if rquota_enabled is not None:
            variables["rquota_enabled"] = rquota_enabled
        if nfs_rdma_enabled is not None:
            variables["nfs_rdma_enabled"] = nfs_rdma_enabled

        return runner.execute("nfs_global_settings.yml.j2", variables)

    def remove(self, path: str, access_zone: str = "System") -> dict:
        """Remove an NFS export via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {
            "path": path,
            "access_zone": access_zone,
        }
        return runner.execute("nfs_remove.yml.j2", variables)
