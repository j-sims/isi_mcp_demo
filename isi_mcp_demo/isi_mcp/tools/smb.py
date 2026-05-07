from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.smb import Smb
from modules.utils.paging import normalize_resume, paginated_result
from typing import Dict, Any, Optional


@safe_tool(group="smb", mode="read")
def powerscale_smb_get(
    limit: int = 1000,
    resume: Optional[str] = None,
    cluster_name: str = None,
    ) -> Dict[str, Any]:
    """
    Returns SMB shares on the PowerScale cluster using pagination.

    SMB (Server Message Block) shares define which filesystem paths are shared
    over the SMB/CIFS protocol for access by Windows and other SMB clients.

    Usage:
    - First call: resume=None
    - If "resume" is returned in the response, call again with that value
    - Continue until "resume" is None
    - Do not call repeatedly with the same resume value

    Arguments:
    - limit: Maximum number of shares per page
    - resume: Resume token from a previous call (or None for first call)

    Each share object includes details such as:
    - name: The share name
    - path: The filesystem path being shared
    - description: Human-readable description of the share
    - permissions: Access permissions configured on the share
    - browsable: Whether the share is visible when browsing
    - access_based_enumeration: Whether ABE is enabled
    - continuously_available: Whether the share supports continuous availability
    - file_create_mode: Default file creation permissions
    - directory_create_mode: Default directory creation permissions
    - zone: The access zone the share belongs to

    Use this tool to answer questions about SMB shares such as:
    - What SMB shares are configured on the cluster?
    - Which paths are shared over SMB/CIFS?
    - What permissions are set on a specific share?
    - What access zones have SMB shares?
    - Is a specific directory shared over SMB?

    Returns:
    - items: List of SMB share objects for this page
    - resume: Resume token for the next page, or None if finished
    - has_more: True if more pages exist
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    return paginated_result(Smb(cluster).get(limit=limit, resume=resume), limit)

@safe_tool(group="smb", mode="write")
def powerscale_smb_create(
    share_name: str,
    path: str,
    description: str = None,
    access_zone: str = None,
    create_path: bool = None,
    browsable: bool = None,
    access_based_enumeration: bool = None,
    access_based_enumeration_root_only: bool = None,
    ntfs_acl_support: bool = None,
    oplocks: bool = None,
    continuously_available: bool = None,
    smb3_encryption_enabled: bool = None,
    directory_create_mask: str = None,
    directory_create_mode: str = None,
    file_create_mask: str = None,
    file_create_mode: str = None,
    allow_variable_expansion: bool = None,
    auto_create_directory: bool = None,
    inheritable_path_acl: bool = None,
    allow_delete_readonly: bool = None,
    allow_execute_always: bool = None,
    ca_timeout_value: int = None,
    ca_timeout_unit: str = None,
    strict_ca_lockout: bool = None,
    ca_write_integrity: str = None,
    change_notify: str = None,
    impersonate_guest: str = None,
    impersonate_user: str = None,
    file_filtering_enabled: bool = None,
    file_filter_extension: str = None,
    permissions: str = None,
    host_acls: str = None,
    run_as_root: str = None,
    cluster_name: str = None,
) -> dict:
    """
    Create an SMB (CIFS) share on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new SMB share on the
    live cluster. Always confirm the share name and path with the user before
    calling this tool (e.g. "Create SMB share 'projects' at /ifs/data/projects?").

    This tool uses Ansible automation to create the share via the
    dellemc.powerscale collection. The share will be immediately available
    to SMB/CIFS clients after creation.

    Arguments (required):
    - share_name: The name of the SMB share (e.g. "projects", "finance_data")
    - path: The filesystem path to share (e.g. "/ifs/data/projects"). Must exist
      on the cluster unless create_path is true.

    Arguments (optional — omit to keep cluster defaults):
    - description: Human-readable description of the share
    - access_zone: Access zone containing this share (default "System").
      Use absolute paths for System zone, relative paths for other zones.
    - create_path: Create the filesystem path if it does not already exist
    - browsable: Share is visible in net view and the browse list
    - access_based_enumeration: Only enumerate files/folders the user has access to
    - access_based_enumeration_root_only: Apply ABE on the root directory only
    - ntfs_acl_support: Support NTFS ACLs on files and directories
    - oplocks: Support opportunistic locks (can improve performance)
    - continuously_available: Allow persistent opens on the share (SMB3 CA,
      required for Hyper-V over SMB, SQL Server, etc.)
    - smb3_encryption_enabled: Require SMB3 encryption for this share
    - directory_create_mask: Octal mask for new directories (e.g. "0755")
    - directory_create_mode: Octal mode bits always set on new directories (e.g. "0000")
    - file_create_mask: Octal mask for new files (e.g. "0744")
    - file_create_mode: Octal mode bits always set on new files (e.g. "0000")
    - allow_variable_expansion: Automatic expansion of %U, %D, etc. for home dirs
    - auto_create_directory: Automatically create home directories
    - inheritable_path_acl: Set inheritable ACL on the share path
    - allow_delete_readonly: Allow deletion of read-only files in the share
    - allow_execute_always: Allow users to execute files they have read rights for
    - ca_timeout_value: Persistent open timeout value (integer). Used with
      ca_timeout_unit to set the continuously-available timeout.
    - ca_timeout_unit: Unit for ca_timeout_value — "seconds" (default) or "minutes"
    - strict_ca_lockout: Strict lockout on persistent opens
    - ca_write_integrity: Write-integrity level on CA shares
      (e.g. "none", "write-read-coherent", "full")
    - change_notify: Level of change notification alerts
      ("all", "norecurse", or "none")
    - impersonate_guest: Condition for guest impersonation
      ("always", "bad user", or "never")
    - impersonate_user: User account to impersonate as guest
    - file_filtering_enabled: Enable file filtering on this share (must be true
      for file_filter_extension to take effect)
    - file_filter_extension: JSON string defining file extension filters.
      Format: {"extensions": [".exe", ".bat"], "type": "deny", "state": "present-in-filter"}
      - extensions: list of file extensions to filter
      - type: "deny" (block listed) or "allow" (only allow listed) — default "deny"
      - state: state of the filter entries
    - permissions: JSON string — list of share-level permission entries.
      Each entry: {"permission": "read|write|full", "permission_type": "allow|deny"}
      plus ONE of: "user_name", "group_name", or "wellknown" to identify the trustee.
      Optional "provider_type": "local|file|ads|ldap|nis" (default "local").
      Example: [{"user_name": "admin", "permission": "full", "permission_type": "allow"},
                {"wellknown": "Everyone", "permission": "read", "permission_type": "allow"}]
    - host_acls: JSON string — list of host ACL entries controlling which
      hosts/networks can access the share.
      Each entry: {"name": "<host-or-subnet>", "access_type": "allow|deny"}
      Example: [{"name": "10.0.0.0/24", "access_type": "allow"}]
    - run_as_root: JSON string — list of personas allowed to map to root.
      Each entry: {"name": "<persona>", "type": "<persona-type>"}
      Optional: "provider_type" (default "local"), "state": "allow|absent" (default "allow").
      Example: [{"name": "admin", "type": "user", "provider_type": "local"}]

    Use this tool when the user wants to:
    - Create a new SMB/CIFS share
    - Share a directory over SMB/CIFS protocol
    - Make a filesystem path accessible to Windows clients

    Returns:
    - success: Boolean indicating if the share was created
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    cluster = get_cluster(cluster_name)
    smb = Smb(cluster)
    return smb.add(
        share_name=share_name,
        path=path,
        description=description,
        access_zone=access_zone,
        create_path=create_path,
        browsable=browsable,
        access_based_enumeration=access_based_enumeration,
        access_based_enumeration_root_only=access_based_enumeration_root_only,
        ntfs_acl_support=ntfs_acl_support,
        oplocks=oplocks,
        continuously_available=continuously_available,
        smb3_encryption_enabled=smb3_encryption_enabled,
        directory_create_mask=directory_create_mask,
        directory_create_mode=directory_create_mode,
        file_create_mask=file_create_mask,
        file_create_mode=file_create_mode,
        allow_variable_expansion=allow_variable_expansion,
        auto_create_directory=auto_create_directory,
        inheritable_path_acl=inheritable_path_acl,
        allow_delete_readonly=allow_delete_readonly,
        allow_execute_always=allow_execute_always,
        ca_timeout={"value": ca_timeout_value, "unit": ca_timeout_unit or "seconds"} if ca_timeout_value is not None else None,
        strict_ca_lockout=strict_ca_lockout,
        ca_write_integrity=ca_write_integrity,
        change_notify=change_notify,
        impersonate_guest=impersonate_guest,
        impersonate_user=impersonate_user,
        file_filtering_enabled=file_filtering_enabled,
        file_filter_extension=file_filter_extension,
        permissions=permissions,
        host_acls=host_acls,
        run_as_root=run_as_root,
    )

@safe_tool(group="smb", mode="write")
def powerscale_smb_remove(share_name: str, cluster_name: str = None) -> dict:
    """
    Remove an SMB (CIFS) share from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes an SMB share from the
    live cluster. Always confirm the share name with the user before calling
    this tool (e.g. "Remove SMB share 'projects'?"). This does NOT delete the
    underlying data on the filesystem — it only removes the share definition.

    Arguments:
    - share_name: The name of the SMB share to remove (e.g. "projects")

    Use this tool when the user wants to:
    - Remove or delete an SMB/CIFS share
    - Stop sharing a directory over SMB/CIFS
    - Unshare a path from Windows clients

    Returns:
    - success: Boolean indicating if the share was removed
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    cluster = get_cluster(cluster_name)
    smb = Smb(cluster)
    return smb.remove(share_name=share_name)

@safe_tool(group="smb", mode="read")
def powerscale_smb_global_settings_get(cluster_name: str = None) -> dict:
    """
    Retrieve the current SMB global settings from the PowerScale cluster.

    Returns the cluster-wide SMB configuration including service status,
    protocol version support, security settings, and performance tuning.

    Key fields in the response:
    - service: Whether the SMB service is enabled
    - support_smb2: Whether SMB2 protocol is supported
    - support_smb3_encryption: Whether SMB3 encryption is supported
    - enable_security_signatures: Whether signed SMB packets are supported
    - require_security_signatures: Whether signed SMB packets are required
    - reject_unencrypted_access: Whether unencrypted access is rejected
    - support_multichannel: Whether SMB multichannel is supported
    - support_netbios: Whether NetBIOS is supported
    - server_side_copy: Whether server-side copy is enabled
    - guest_user: The user used for guest access
    - server_string: The server description string

    Use this tool to:
    - Check if the SMB service is enabled or disabled
    - See which SMB protocol versions are supported (SMB2, SMB3)
    - Review SMB security settings (encryption, signing)
    - View SMB performance configuration (workers, multichannel)
    """
    cluster = get_cluster(cluster_name)
    smb = Smb(cluster)
    return smb.get_global_settings()

@safe_tool(group="smb", mode="write")
def powerscale_smb_global_settings_set(
    service: bool = None,
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
    ignore_eas: bool = None,
    cluster_name: str = None,
) -> dict:
    """
    Update SMB global settings on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that changes cluster-wide SMB
    configuration. Always confirm the intended changes with the user before
    calling this tool. Only pass the parameters you want to change — omitted
    parameters are left at their current values.

    Arguments:
    - service: Enable (true) or disable (false) the SMB service entirely
    - support_smb2: Enable/disable SMB2 protocol support
    - support_smb3_encryption: Enable/disable SMB3 encryption support
    - access_based_share_enum: Only enumerate files/folders the user has access to
    - dot_snap_accessible_child: Allow access to .snapshot in share subdirectories
    - dot_snap_accessible_root: Allow access to .snapshot in share root
    - dot_snap_visible_child: Show .snapshot in share subdirectories
    - dot_snap_visible_root: Show .snapshot in share root
    - enable_security_signatures: Support signed SMB packets
    - require_security_signatures: Require signed SMB packets
    - reject_unencrypted_access: Reject unencrypted access when SMB3 encryption is on
    - server_side_copy: Enable server-side copy
    - support_multichannel: Enable SMB multichannel
    - support_netbios: Enable NetBIOS support
    - guest_user: Fully-qualified user for guest access
    - server_string: Server description string
    - onefs_cpu_multiplier: OneFS driver worker threads per CPU
    - onefs_num_workers: Maximum OneFS driver worker threads
    - ignore_eas: Ignore extended attributes on files

    Use this tool to:
    - Enable or disable the SMB service
    - Control which SMB protocol versions are supported
    - Configure SMB security (encryption, signing)
    - Tune SMB performance settings
    """
    cluster = get_cluster(cluster_name)
    smb = Smb(cluster)
    return smb.set_global_settings(
        service=service,
        support_smb2=support_smb2,
        support_smb3_encryption=support_smb3_encryption,
        access_based_share_enum=access_based_share_enum,
        dot_snap_accessible_child=dot_snap_accessible_child,
        dot_snap_accessible_root=dot_snap_accessible_root,
        dot_snap_visible_child=dot_snap_visible_child,
        dot_snap_visible_root=dot_snap_visible_root,
        enable_security_signatures=enable_security_signatures,
        require_security_signatures=require_security_signatures,
        reject_unencrypted_access=reject_unencrypted_access,
        server_side_copy=server_side_copy,
        support_multichannel=support_multichannel,
        support_netbios=support_netbios,
        guest_user=guest_user,
        server_string=server_string,
        onefs_cpu_multiplier=onefs_cpu_multiplier,
        onefs_num_workers=onefs_num_workers,
        ignore_eas=ignore_eas,
    )

@safe_tool(group="smb", mode="read")
def powerscale_smb_sessions_get(
    limit: int = 1000,
    lnn: Optional[str] = None,
    lnn_skip: Optional[str] = None,
    resume: Optional[str] = None,
    cluster_name: str = None,
    ) -> Dict[str, Any]:
    """
    Returns active SMB sessions across cluster nodes.

    SMB sessions represent active client connections to the cluster over the
    SMB/CIFS protocol. Each session tracks the connected user, client computer,
    open file count, idle/active time, and encryption status.

    Usage:
    - First call: resume=None
    - If "resume" is returned in the response, call again with that value
    - Continue until "resume" is None

    Arguments:
    - limit: Maximum number of sessions per page
    - lnn: Logical node number to query (use "all" for all nodes)
    - lnn_skip: When lnn="all", skip this specific node LNN
    - resume: Resume token from a previous call (or None for first call)

    Results are organized by node. Each node entry includes:
    - lnn: Logical node number
    - id: Node ID
    - total: Session count on this node
    - sessions: List of session objects, each containing:
      - id: Session ID (used for closing the session)
      - user: Authenticated username
      - computer: Client computer hostname
      - client_type: SMB dialect/version (e.g., "SMB3")
      - openfiles: Number of open files in this session
      - active_time: Time session has been active (seconds)
      - idle_time: Time session has been idle (seconds)
      - encryption: Whether the session uses encryption
      - guest_login: Whether this is a guest login

    Use this tool to answer questions such as:
    - Which clients are currently connected over SMB?
    - How many open files does a specific session have?
    - Which users have active SMB connections?
    - Is a specific client using encrypted SMB sessions?

    Returns:
    - nodes: List of node objects, each with session data
    - resume: Resume token for the next page, or None if finished
    - total: Total number of sessions across all nodes
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    smb = Smb(cluster)

    page = smb.get_sessions(limit=limit, lnn=lnn, lnn_skip=lnn_skip, resume=resume)
    if "error" in page:
        return page

    return {
        "nodes": page.get("nodes", []),
        "resume": page.get("resume"),
        "total": page.get("total"),
        "has_more": bool(page.get("resume")),
    }

@safe_tool(group="smb", mode="write")
def powerscale_smb_session_close(session_id: str, cluster_name: str = None) -> Dict[str, Any]:
    """
    Closes (forcibly terminates) an active SMB session by session ID.

    IMPORTANT: This is a MUTATING operation. It will disconnect the client
    immediately. Any unsaved work in open files may be lost.

    Use powerscale_smb_sessions_get to list sessions and retrieve their IDs
    before calling this tool.

    Arguments:
    - session_id: The numeric session ID to close (from sessions list)

    Returns:
    - success: True if the session was closed
    - message: Confirmation message
    """
    cluster = get_cluster(cluster_name)
    smb = Smb(cluster)
    return smb.delete_session(session_id)

@safe_tool(group="smb", mode="write")
def powerscale_smb_sessions_close_by_user(
    computer: str,
    user: str,
    cluster_name: str = None,
    ) -> Dict[str, Any]:
    """
    Closes all active SMB sessions for a specific user on a specific client computer.

    IMPORTANT: This is a MUTATING operation. It will disconnect all matching
    sessions immediately. Any unsaved work in open files may be lost.

    This is useful for closing all sessions from a specific client machine
    or for a specific user without needing individual session IDs.

    Arguments:
    - computer: The client computer hostname (e.g., "DESKTOP-ABC123")
    - user: The username whose sessions should be closed (e.g., "DOMAIN\\\\username")

    Returns:
    - success: True if sessions were closed
    - message: Confirmation message
    """
    cluster = get_cluster(cluster_name)
    smb = Smb(cluster)
    return smb.delete_sessions_by_user(computer=computer, user=user)

@safe_tool(group="smb", mode="read")
def powerscale_smb_openfiles_get(
    limit: int = 1000,
    resume: Optional[str] = None,
    sort: Optional[str] = None,
    dir: Optional[str] = None,
    cluster_name: str = None,
    ) -> Dict[str, Any]:
    """
    Returns all files currently open via SMB on the cluster.

    Open files represent filesystem objects that SMB clients currently have
    open. This is useful for identifying locked files, tracking active usage,
    and diagnosing access conflicts.

    Usage:
    - First call: resume=None
    - If "resume" is returned in the response, call again with that value
    - Continue until "resume" is None

    Arguments:
    - limit: Maximum number of open file entries per page
    - resume: Resume token from a previous call (or None for first call)
    - sort: Field to sort results by (default: "id")
    - dir: Sort direction — "ASC" or "DESC"

    Each open file entry includes:
    - id: Open file ID (used for closing the file handle)
    - file: Path of the open file
    - user: User who has the file open
    - locks: Number of locks held on the file
    - permissions: List of permissions granted (e.g., ["read", "write"])

    Use this tool to answer questions such as:
    - Which files are currently open via SMB?
    - Who has a specific file open?
    - Are there any file locks currently held?
    - How many SMB clients have files open?

    Returns:
    - items: List of open file objects for this page
    - resume: Resume token for the next page, or None if finished
    - total: Total number of open files
    - has_more: True if more pages exist
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    smb = Smb(cluster)

    page = smb.get_openfiles(limit=limit, resume=resume, sort=sort, dir=dir)
    if "error" in page:
        return page

    return {
        "items": page.get("items", []),
        "resume": page.get("resume"),
        "total": page.get("total"),
        "has_more": bool(page.get("resume")),
    }

@safe_tool(group="smb", mode="write")
def powerscale_smb_openfile_close(openfile_id: str, cluster_name: str = None) -> Dict[str, Any]:
    """
    Closes (forcibly terminates) an open SMB file handle by ID.

    IMPORTANT: This is a MUTATING operation. Forcibly closing a file handle
    may cause data loss if the client has unsaved changes. Use with caution.

    Use powerscale_smb_openfiles_get to list open files and retrieve their IDs
    before calling this tool.

    Arguments:
    - openfile_id: The numeric open file ID to close (from open files list)

    Returns:
    - success: True if the file handle was closed
    - message: Confirmation message
    """
    cluster = get_cluster(cluster_name)
    smb = Smb(cluster)
    return smb.delete_openfile(openfile_id)
