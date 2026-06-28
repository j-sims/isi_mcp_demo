from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.nfs import Nfs
from modules.utils.paging import normalize_resume, paginated_result
from modules.utils.kwargs import parse_json_param
from typing import Dict, Any, Optional


@safe_tool(group="nfs", mode="read")
def powerscale_nfs_get(
    limit: int = 1000,
    resume: Optional[str] = None,
    cluster_name: str = None,
    ) -> Dict[str, Any]:
    """
    Returns NFS exports on the PowerScale cluster using pagination.

    NFS (Network File System) exports define which filesystem paths are shared
    over the NFS protocol and the access rules for each export.

    Usage:
    - First call: resume=None
    - If "resume" is returned in the response, call again with that value
    - Continue until "resume" is None
    - Do not call repeatedly with the same resume value

    Arguments:
    - limit: Maximum number of exports per page
    - resume: Resume token from a previous call (or None for first call)

    Each export object includes details such as:
    - id: Unique export identifier
    - paths: List of filesystem paths shared by this export
    - description: Human-readable description of the export
    - clients: List of client hostnames/IPs allowed to access this export
    - root_clients: Clients granted root access
    - read_only_clients: Clients with read-only access
    - read_write_clients: Clients with read-write access
    - map_root: User mapping for root access (e.g. "root", "nobody")
    - map_all: User mapping applied to all users
    - security_flavors: Authentication methods (e.g. "unix", "krb5")
    - block_size: NFS block size
    - read_only: Whether the export is globally read-only
    - zone: The access zone the export belongs to

    Use this tool to answer questions about NFS exports such as:
    - What NFS exports are configured on the cluster?
    - Which paths are shared over NFS?
    - What clients have access to a specific export?
    - Are there any exports with root access granted?
    - What access zones have NFS exports?

    Returns:
    - items: List of NFS export objects for this page
    - resume: Resume token for the next page, or None if finished
    - has_more: True if more pages exist
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    return paginated_result(Nfs(cluster).get(limit=limit, resume=resume), limit)

@safe_tool(group="nfs", mode="write")
def powerscale_nfs_create(
    path: str,
    access_zone: str = "System",
    description: str = None,
    clients: str = None,
    read_only: bool = None,
    # Phase 1 - Client Management
    client_state: str = None,
    read_only_clients: str = None,
    read_write_clients: str = None,
    root_clients: str = None,
    # Phase 2 - Security & Configuration
    security_flavors: str = None,
    sub_directories_mountable: bool = None,
    # Phase 3 - Root Mapping
    map_root: str = None,
    # Phase 4 - Advanced Features
    map_non_root: str = None,
    ignore_unresolvable_hosts: bool = None,
    cluster_name: str = None,
) -> dict:
    """
    Create an NFS export on the PowerScale cluster with comprehensive configuration options.

    IMPORTANT: This is a MUTATING operation that creates a new NFS export on the
    live cluster. Always confirm the path and access settings with the user before
    calling this tool (e.g. "Create NFS export for /ifs/data/projects in access
    zone System?").

    This tool uses Ansible automation to create the export via the
    dellemc.powerscale collection.

    BASIC ARGUMENTS:
    - path: The filesystem path to export (e.g. "/ifs/data/projects") [REQUIRED]
    - access_zone: The access zone for the export (default: "System")
    - description: Optional human-readable description

    CLIENT ACCESS CONTROL (Basic):
    - clients: Comma-separated list of client hostnames or IPs allowed basic access
      (e.g. "10.0.0.1,10.0.0.2,client.example.com"). Access type determined by
      read_only parameter.
    - read_only: If True, the export is read-only. If omitted, defaults to read-write.

    CLIENT ACCESS CONTROL (Advanced - Phase 1):
    - client_state: Control client list behavior - "present-in-export" or "absent-in-export"
    - read_only_clients: Comma-separated list of clients with read-only access
      (e.g. "10.0.0.0/24,readonly-server.example.com")
    - read_write_clients: Comma-separated list of clients with read-write access
      (e.g. "10.0.1.0/24,app-server.example.com")
    - root_clients: Comma-separated list of clients with root access (no root squashing)
      (e.g. "10.0.2.10,trusted-server.example.com")

    CLIENT PARAMETER VALIDATION:
    Valid client formats: IP addresses (192.168.1.100), CIDR notation (192.168.0.0/24),
    or DNS hostnames (nfs-server.example.com). Clients will be validated before export creation.
    Common mistakes: mixing IP/CIDR incorrectly (e.g., 192.168.1.0/32 is single host not subnet),
    unresolvable hostnames, empty client lists. Use ignore_unresolvable_hosts=true to suppress
    hostname resolution errors if using dynamic DNS or wildcard patterns.

    SECURITY & CONFIGURATION (Phase 2):
    - security_flavors: Comma-separated list of authentication types. Options:
      "unix" (standard UNIX auth), "krb5" (Kerberos 5), "krb5i" (Kerberos with integrity),
      "krb5p" (Kerberos with privacy/encryption). Example: "unix,krb5p"
    - sub_directories_mountable: If True, clients can mount subdirectories of the export path

    USER MAPPING (Phase 3 & 4):
    - map_root: JSON string for root user mapping configuration. Example:
      '{"enabled": true, "user": "nobody", "primary_group": "nobody"}'
      Fields: enabled (bool), user (str), primary_group (str), secondary_groups (list of
      {"name": str, "state": str})
    - map_non_root: JSON string for non-root user mapping. Same structure as map_root.

    ADVANCED OPTIONS (Phase 4):
    - ignore_unresolvable_hosts: If True, suppress errors for client hostnames that
      cannot be resolved via DNS

    COMMON USE CASES:

    1. Basic read-write export for trusted network:
       path="/ifs/data", read_write_clients="10.0.0.0/24"

    2. Mixed permissions (some RO, some RW, one root):
       path="/ifs/shared", read_only_clients="10.0.1.0/24",
       read_write_clients="10.0.2.0/24", root_clients="10.0.2.10"

    3. Kerberos-secured export with root squashing:
       path="/ifs/secure", security_flavors="krb5p",
       map_root='{"enabled": true, "user": "nobody", "primary_group": "nobody"}'

    4. Application export with subdirectory mounting:
       path="/ifs/apps", sub_directories_mountable=true,
       read_write_clients="app-servers.example.com"

    Returns:
    - success: Boolean indicating if the export was created
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    cluster = get_cluster(cluster_name)
    nfs = Nfs(cluster)

    # Parse basic client list
    clients_list = [c.strip() for c in clients.split(",")] if clients else None

    # Parse Phase 1 - Client Management lists
    read_only_clients_list = [c.strip() for c in read_only_clients.split(",")] if read_only_clients else None
    read_write_clients_list = [c.strip() for c in read_write_clients.split(",")] if read_write_clients else None
    root_clients_list = [c.strip() for c in root_clients.split(",")] if root_clients else None

    # Parse Phase 2 - Security flavors list
    security_flavors_list = [f.strip() for f in security_flavors.split(",")] if security_flavors else None

    # Parse Phase 3 & 4 - User mapping JSON
    map_root_dict = parse_json_param("map_root", map_root)
    map_non_root_dict = parse_json_param("map_non_root", map_non_root)

    return nfs.add(
        path=path,
        access_zone=access_zone,
        description=description,
        clients=clients_list,
        read_only=read_only,
        # Phase 1
        client_state=client_state,
        read_only_clients=read_only_clients_list,
        read_write_clients=read_write_clients_list,
        root_clients=root_clients_list,
        # Phase 2
        security_flavors=security_flavors_list,
        sub_directories_mountable=sub_directories_mountable,
        # Phase 3
        map_root=map_root_dict,
        # Phase 4
        map_non_root=map_non_root_dict,
        ignore_unresolvable_hosts=ignore_unresolvable_hosts
    )

@safe_tool(group="nfs", mode="write")
def powerscale_nfs_remove(path: str, access_zone: str = "System", cluster_name: str = None) -> dict:
    """
    Remove an NFS export from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes an NFS export from the
    live cluster. Always confirm the path with the user before calling this tool
    (e.g. "Remove NFS export for /ifs/data/projects?"). This does NOT delete the
    underlying data — it only removes the export definition.

    Arguments:
    - path: The filesystem path of the export to remove (e.g. "/ifs/data/projects")
    - access_zone: The access zone the export belongs to (default: "System")

    Use this tool when the user wants to:
    - Remove or delete an NFS export
    - Stop sharing a directory over NFS
    - Unshare a path from NFS clients

    Returns:
    - success: Boolean indicating if the export was removed
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    cluster = get_cluster(cluster_name)
    nfs = Nfs(cluster)
    return nfs.remove(path=path, access_zone=access_zone)

@safe_tool(group="nfs", mode="read")
def powerscale_nfs_global_settings_get(cluster_name: str = None) -> dict:
    """
    Retrieve the current NFS global settings from the PowerScale cluster.

    Returns the cluster-wide NFS configuration including service status,
    protocol version support, and performance tuning.

    Key fields in the response:
    - service: Whether the NFS service is enabled
    - nfsv3_enabled: Whether NFSv3 protocol is enabled
    - nfsv4_enabled: Whether NFSv4 protocol is enabled
    - nfsv40_enabled: Whether NFSv4.0 is enabled
    - nfsv41_enabled: Whether NFSv4.1 is enabled
    - nfsv42_enabled: Whether NFSv4.2 is enabled
    - rpc_maxthreads: Maximum nfsd thread pool threads
    - rpc_minthreads: Minimum nfsd thread pool threads
    - rquota_enabled: Whether rquota protocol is enabled

    Use this tool to:
    - Check if the NFS service is enabled or disabled
    - See which NFS protocol versions are enabled (v3, v4, v4.0, v4.1, v4.2)
    - Review NFS performance configuration (thread pools)
    - Check RDMA and rquota status
    """
    cluster = get_cluster(cluster_name)
    nfs = Nfs(cluster)
    return nfs.get_global_settings()

@safe_tool(group="nfs", mode="write")
def powerscale_nfs_global_settings_set(
    service: bool = None,
    nfsv3_enabled: bool = None,
    nfsv3_rdma_enabled: bool = None,
    nfsv4_enabled: bool = None,
    nfsv40_enabled: bool = None,
    nfsv41_enabled: bool = None,
    nfsv42_enabled: bool = None,
    rpc_maxthreads: int = None,
    rpc_minthreads: int = None,
    rquota_enabled: bool = None,
    nfs_rdma_enabled: bool = None,
    cluster_name: str = None,
) -> dict:
    """
    Update NFS global settings on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that changes cluster-wide NFS
    configuration. Always confirm the intended changes with the user before
    calling this tool. Only pass the parameters you want to change — omitted
    parameters are left at their current values.

    Arguments:
    - service: Enable (true) or disable (false) the NFS service entirely
    - nfsv3_enabled: Enable/disable NFSv3 protocol
    - nfsv3_rdma_enabled: Enable/disable RDMA for NFSv3
    - nfsv4_enabled: Enable/disable all minor versions of NFSv4
    - nfsv40_enabled: Enable/disable NFSv4.0
    - nfsv41_enabled: Enable/disable NFSv4.1
    - nfsv42_enabled: Enable/disable NFSv4.2
    - rpc_maxthreads: Maximum number of threads in the nfsd thread pool
    - rpc_minthreads: Minimum number of threads in the nfsd thread pool
    - rquota_enabled: Enable/disable the rquota protocol
    - nfs_rdma_enabled: Enable/disable RDMA for NFS (PowerScale 9.8+)

    Use this tool to:
    - Enable or disable the NFS service
    - Control which NFS protocol versions are enabled (v3, v4.0, v4.1, v4.2)
    - Tune NFS thread pool sizes
    - Enable or disable RDMA and rquota
    """
    cluster = get_cluster(cluster_name)
    nfs = Nfs(cluster)

    # Build nfsv3 dict if any v3 params are set
    nfsv3 = None
    if nfsv3_enabled is not None or nfsv3_rdma_enabled is not None:
        nfsv3 = {}
        if nfsv3_enabled is not None:
            nfsv3["nfsv3_enabled"] = nfsv3_enabled
        if nfsv3_rdma_enabled is not None:
            nfsv3["nfsv3_rdma_enabled"] = nfsv3_rdma_enabled

    # Build nfsv4 dict if any v4 params are set
    nfsv4 = None
    if any(v is not None for v in [nfsv4_enabled, nfsv40_enabled, nfsv41_enabled, nfsv42_enabled]):
        nfsv4 = {}
        if nfsv4_enabled is not None:
            nfsv4["nfsv4_enabled"] = nfsv4_enabled
        if nfsv40_enabled is not None:
            nfsv4["nfsv40_enabled"] = nfsv40_enabled
        if nfsv41_enabled is not None:
            nfsv4["nfsv41_enabled"] = nfsv41_enabled
        if nfsv42_enabled is not None:
            nfsv4["nfsv42_enabled"] = nfsv42_enabled

    return nfs.set_global_settings(
        service=service,
        nfsv3=nfsv3,
        nfsv4=nfsv4,
        rpc_maxthreads=rpc_maxthreads,
        rpc_minthreads=rpc_minthreads,
        rquota_enabled=rquota_enabled,
        nfs_rdma_enabled=nfs_rdma_enabled,
    )
