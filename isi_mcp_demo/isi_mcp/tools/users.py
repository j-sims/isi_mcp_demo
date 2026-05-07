from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.users import Users
from modules.onefs.v9_12_0.group import Group
from modules.utils.paging import normalize_resume, paginated_result
from typing import Dict, Any, Optional


@safe_tool(group="users", mode="read")
def powerscale_user_get(
    user_name: Optional[str] = None,
    provider_type: Optional[str] = None,
    access_zone: Optional[str] = None,
    limit: int = 1000,
    resume: Optional[str] = None,
    cluster_name: str = None,
) -> Dict[str, Any]:
    """
    List local users on the PowerScale cluster, or retrieve a specific user by name.

    Users are local or external accounts that can authenticate against the cluster
    and access data according to their group memberships and role assignments.

    Arguments:
    - user_name: If provided, fetch only this user (exact match). If omitted, list all.
    - provider_type: Filter by authentication provider — 'local', 'file', 'ldap',
      'ads', or 'nis'. Defaults to all providers when omitted.
    - access_zone: Filter by access zone name. Defaults to all zones when omitted.
    - limit: Maximum number of users per page (list mode only).
    - resume: Resume token from a previous call for pagination (list mode only).

    Returns per user:
    - name: Account name
    - uid: UNIX user ID
    - gid: Primary group ID
    - email: Email address
    - enabled: Whether the account is active
    - home_directory: Home directory path
    - shell: Login shell
    - provider: Authentication provider
    - member_of: Groups this user belongs to
    - sid: Windows Security Identifier
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    page = Users(cluster).get(
        user_name=user_name, provider_type=provider_type,
        access_zone=access_zone, limit=limit, resume=resume,
    )
    return paginated_result(page, limit)


@safe_tool(group="users", mode="write")
def powerscale_user_create(
    user_name: str,
    password: str,
    access_zone: Optional[str] = None,
    provider_type: Optional[str] = None,
    primary_group: Optional[str] = None,
    enabled: Optional[bool] = None,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    home_directory: Optional[str] = None,
    shell: Optional[str] = None,
    user_id: Optional[int] = None,
    role_name: Optional[str] = None,
    role_state: Optional[str] = None,
    update_password: str = "on_create",
    cluster_name: str = None,
) -> dict:
    """
    Create a new local user on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation. It creates a new user account on the
    live cluster. Always confirm the username and settings with the user before
    calling this tool (e.g. "Create user 'alice' with primary group 'users'?").

    This tool uses Ansible automation via the dellemc.powerscale collection.
    Creation is only supported for local provider accounts.

    Arguments (required):
    - user_name: The account name to create (e.g. "alice", "svc_backup")
    - password: Initial password for the account

    Arguments (optional — omit to use cluster defaults):
    - access_zone: Access zone to create the user in (default: System zone)
    - provider_type: Authentication provider — 'local' (default), 'file', 'ldap',
      'ads', or 'nis'. Creation is only supported for 'local'.
    - primary_group: Primary group name for file ownership (e.g. "Isilon Users")
    - enabled: Whether the account is active (default: true)
    - email: Email address for the account
    - full_name: Display name / GECOS field
    - home_directory: Absolute path to home directory (must be unused)
    - shell: Login shell path (e.g. "/bin/bash", "/bin/sh")
    - user_id: Explicit UID to assign (auto-assigned if omitted)
    - role_name: Role to assign to the user upon creation (system zone only)
    - role_state: 'present-for-user' to assign the role
    - update_password: 'on_create' (set only at creation) or 'always' (update on every run)
    """
    cluster = get_cluster(cluster_name)
    users = Users(cluster)
    return users.add(
        user_name=user_name,
        password=password,
        access_zone=access_zone,
        provider_type=provider_type,
        primary_group=primary_group,
        enabled=enabled,
        email=email,
        full_name=full_name,
        home_directory=home_directory,
        shell=shell,
        user_id=user_id,
        role_name=role_name,
        role_state=role_state,
        update_password=update_password,
    )


@safe_tool(group="users", mode="write")
def powerscale_user_modify(
    user_name: str,
    access_zone: Optional[str] = None,
    provider_type: Optional[str] = None,
    primary_group: Optional[str] = None,
    enabled: Optional[bool] = None,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    home_directory: Optional[str] = None,
    shell: Optional[str] = None,
    password: Optional[str] = None,
    update_password: Optional[str] = None,
    role_name: Optional[str] = None,
    role_state: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Modify an existing user account on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation. It updates the specified user account
    on the live cluster. Always confirm the change with the user before calling
    (e.g. "Disable account 'alice'?" or "Set primary group to 'admins' for 'bob'?").

    Only the fields you provide will be changed; omitted fields are left unchanged.
    Role management (add/remove role assignments) is only supported in the system zone.

    Arguments (required):
    - user_name: The account name to modify

    Arguments (optional — only provided fields are updated):
    - access_zone: Access zone the user lives in (default: System zone)
    - provider_type: Authentication provider (default: 'local')
    - primary_group: New primary group name
    - enabled: True to enable, False to disable the account
    - email: New email address
    - full_name: New display name / GECOS field
    - home_directory: New home directory path
    - shell: New login shell path
    - password: New password (requires update_password='always' to take effect)
    - update_password: 'always' to change the password now, 'on_create' to skip
    - role_name: Role to assign or remove
    - role_state: 'present-for-user' to assign, 'absent-for-user' to remove
    """
    cluster = get_cluster(cluster_name)
    users = Users(cluster)
    return users.modify(
        user_name=user_name,
        access_zone=access_zone,
        provider_type=provider_type,
        primary_group=primary_group,
        enabled=enabled,
        email=email,
        full_name=full_name,
        home_directory=home_directory,
        shell=shell,
        password=password,
        update_password=update_password,
        role_name=role_name,
        role_state=role_state,
    )


@safe_tool(group="users", mode="write")
def powerscale_user_remove(
    user_name: str,
    access_zone: Optional[str] = None,
    provider_type: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Delete a local user account from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation. It permanently deletes the user account
    from the cluster. All role assignments are automatically removed. This cannot be
    undone. Always confirm with the user before calling
    (e.g. "Delete user account 'alice'?").

    Deletion is only supported for local provider accounts.

    Arguments (required):
    - user_name: The account name to delete

    Arguments (optional):
    - access_zone: Access zone the user lives in (default: System zone)
    - provider_type: Authentication provider — must be 'local' for deletion
    """
    cluster = get_cluster(cluster_name)
    users = Users(cluster)
    return users.remove(
        user_name=user_name,
        access_zone=access_zone,
        provider_type=provider_type,
    )


@safe_tool(group="groups", mode="read")
def powerscale_group_get(
    group_name: Optional[str] = None,
    group_id: Optional[int] = None,
    provider_type: Optional[str] = None,
    access_zone: Optional[str] = None,
    limit: int = 1000,
    resume: Optional[str] = None,
    cluster_name: str = None,
) -> Dict[str, Any]:
    """
    List groups on the PowerScale cluster, or retrieve a specific group by name or GID.

    Groups control access to resources and appear as UNIX groups or Windows security
    groups depending on the authentication provider. Local groups can have members
    added and removed; external groups (ads, ldap, nis) are read-only from the
    cluster's perspective.

    Arguments:
    - group_name: If provided, fetch only this group (exact match). If omitted, list all.
    - group_id: GID to look up instead of name (e.g. 2000). Use group_name OR group_id.
    - provider_type: Filter by authentication provider — 'local', 'file', 'ldap',
      'ads', or 'nis'. Defaults to all providers when omitted.
    - access_zone: Filter by access zone name. Defaults to all zones when omitted.
    - limit: Maximum number of groups per page (list mode only).
    - resume: Resume token from a previous call for pagination (list mode only).

    Returns per group:
    - name: Group name
    - gid: UNIX group ID
    - sid: Windows Security Identifier
    - provider: Authentication provider and zone (e.g. 'lsa-local-provider:System')
    - members: List of member SIDs
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    page = Group(cluster).get(
        group_name=group_name, group_id=group_id, provider_type=provider_type,
        access_zone=access_zone, limit=limit, resume=resume,
    )
    return paginated_result(page, limit)


@safe_tool(group="groups", mode="write")
def powerscale_group_create(
    group_name: str,
    group_id: Optional[int] = None,
    access_zone: Optional[str] = None,
    provider_type: Optional[str] = None,
    users: Optional[str] = None,
    user_state: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Create a new local group on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation. It creates a new group on the live
    cluster. Always confirm the group name and initial members with the user before
    calling this tool (e.g. "Create group 'developers' with GID 2500?").

    This tool uses Ansible automation via the dellemc.powerscale collection.
    Creation is only supported for local provider groups. Groups from external
    providers (ads, ldap, nis) are managed externally.

    Arguments (required):
    - group_name: The name of the group to create (e.g. "developers", "svc_backup")

    Arguments (optional — omit to use cluster defaults):
    - group_id: Explicit GID to assign (auto-assigned if omitted)
    - access_zone: Access zone to create the group in (default: System zone)
    - provider_type: Authentication provider — 'local' (default). Only 'local' is
      supported for creation.
    - users: JSON array of user dicts to add as initial members. Each dict must have
      exactly one key: "user_name" (str) or "user_id" (int).
      Example: '[{"user_name": "alice"}, {"user_name": "bob"}, {"user_id": 1001}]'
    - user_state: Required when users is provided — must be 'present-in-group' to add
      the specified users as members during creation.

    Use this tool when the user wants to:
    - Create a new local group for file access control
    - Create a group with an explicit GID for NFS compatibility
    - Create a group and immediately populate it with members
    """
    cluster = get_cluster(cluster_name)
    grp = Group(cluster)
    return grp.add(
        group_name=group_name,
        group_id=group_id,
        access_zone=access_zone,
        provider_type=provider_type,
        users=users,
        user_state=user_state,
    )


@safe_tool(group="groups", mode="write")
def powerscale_group_modify(
    group_name: Optional[str] = None,
    group_id: Optional[int] = None,
    users: Optional[str] = None,
    user_state: Optional[str] = None,
    access_zone: Optional[str] = None,
    provider_type: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Add or remove members from an existing group on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation. It modifies group membership on the
    live cluster. Always confirm the members and action with the user before calling
    (e.g. "Add users 'alice' and 'bob' to group 'developers'?").

    Either group_name or group_id must be provided to identify the group.
    Modification is only supported for local provider groups.

    Arguments (one required to identify the group):
    - group_name: The name of the group to modify
    - group_id: The GID of the group to modify

    Arguments (required for member management):
    - users: JSON array of user dicts specifying which users to add or remove.
      Each dict must have exactly one key: "user_name" (str) or "user_id" (int).
      Example: '[{"user_name": "alice"}, {"user_id": 1001}]'
    - user_state: What to do with the listed users:
      - 'present-in-group': Add these users to the group
      - 'absent-in-group': Remove these users from the group

    Arguments (optional filters):
    - access_zone: Access zone the group lives in (default: System zone)
    - provider_type: Authentication provider (default: 'local')

    Use this tool when the user wants to:
    - Add one or more users to a group
    - Remove one or more users from a group
    - Manage group membership by UID instead of username
    """
    cluster = get_cluster(cluster_name)
    grp = Group(cluster)
    return grp.modify(
        group_name=group_name,
        group_id=group_id,
        access_zone=access_zone,
        provider_type=provider_type,
        users=users,
        user_state=user_state,
    )


@safe_tool(group="groups", mode="write")
def powerscale_group_remove(
    group_name: Optional[str] = None,
    group_id: Optional[int] = None,
    access_zone: Optional[str] = None,
    provider_type: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Delete a local group from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation. It permanently deletes the group from
    the cluster. Member associations are removed; the member users themselves are
    not deleted. This cannot be undone. Always confirm with the user before calling
    (e.g. "Delete group 'developers'?").

    Either group_name or group_id must be provided to identify the group.
    Deletion is only supported for local provider groups.

    Arguments (one required to identify the group):
    - group_name: The name of the group to delete
    - group_id: The GID of the group to delete

    Arguments (optional):
    - access_zone: Access zone the group lives in (default: System zone)
    - provider_type: Authentication provider — must be 'local' for deletion

    Use this tool when the user wants to:
    - Remove a group that is no longer needed
    - Clean up groups before decommissioning an access zone
    """
    cluster = get_cluster(cluster_name)
    grp = Group(cluster)
    return grp.remove(
        group_name=group_name,
        group_id=group_id,
        access_zone=access_zone,
        provider_type=provider_type,
    )
