from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.filemgmt import FileMgmt
from modules.utils.paging import normalize_resume
from modules.utils.kwargs import parse_json_param, parse_json_list_param
from typing import Dict, Any, Optional


@safe_tool(group="filemgmt", mode="read")
def powerscale_directory_list(
    path: str,
    detail: str = 'default',
    limit: int = 1000,
    resume: Optional[str] = None,
    sort: Optional[str] = None,
    dir: Optional[str] = None,
    type: Optional[str] = None,
    hidden: bool = False,
    access_point: Optional[str] = None,
    cluster_name: str = None,
) -> Dict[str, Any]:
    """
    List the contents of a directory on the PowerScale cluster filesystem.

    Returns files, subdirectories, and other objects within the specified
    directory path. Supports pagination for directories with many entries.

    Usage (pagination):
    - First call: use resume=None (or omit it)
    - If the response contains a non-null "resume" value, call again passing
      that value as the resume argument to fetch the next page
    - Continue until "resume" is None (has_more will be False)

    Arguments:
    - path: Directory path relative to / (e.g. "ifs/data/projects"). Do NOT
      include a leading slash.
    - detail: Attribute detail level — "default" for basic info or "default"
      with additional attributes
    - limit: Maximum number of objects to return per page (default 1000)
    - resume: Pagination token from a previous call (or None for first call)
    - sort: Attribute to sort by (e.g. "name", "size", "last_modified")
    - dir: Sort direction — "ASC" (ascending) or "DESC" (descending)
    - type: Filter by object type — "container" (directories), "object" (files),
      "symbolic_link", "pipe", "character_device", "block_device", "socket",
      "whiteout_file"
    - hidden: If True, include hidden files/directories (names starting with .)
    - access_point: If set, use access-point addressing. The path becomes
      relative to the access point instead of the root namespace.

    Use this tool to answer questions such as:
    - What files are in this directory?
    - List the contents of /ifs/data/projects
    - Show me the subdirectories under a path
    - What files were recently modified in a directory?

    Response fields:
    - children: List of objects (files/directories) with attributes
    - resume: Pagination token for next page, or None if finished
    - has_more: True if more pages exist

    Returns:
    - children: List of directory entry objects for this page
    - resume: Resume token for the next page, or None if finished
    - has_more: True if more pages exist
    """
    resume = normalize_resume(resume)

    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.list_directory(
        path=path, detail=detail, limit=limit, resume=resume,
        sort=sort, dir=dir, type=type, hidden=hidden,
        access_point=access_point)

@safe_tool(group="filemgmt", mode="read")
def powerscale_directory_attributes(path: str, cluster_name: str = None) -> Dict[str, Any]:
    """
    Get attribute information for a directory on the PowerScale cluster.

    Retrieves metadata headers for the specified directory without
    transferring its contents. Returns information such as last-modified
    time, content type, and resource type.

    Arguments:
    - path: Directory path relative to / (e.g. "ifs/data/projects"). Do NOT
      include a leading slash.

    Use this tool when you need to:
    - Check if a directory exists
    - Get the last-modified time of a directory
    - Inspect directory metadata without listing contents

    Returns:
    - A dict of HTTP header key-value pairs containing directory attributes
      such as Last-Modified, Content-Type, and x-isi-ifs-target-type.
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.get_directory_attributes(path=path)

@safe_tool(group="filemgmt", mode="write")
def powerscale_directory_create(
    path: str,
    recursive: bool = True,
    access_control: Optional[str] = None,
    overwrite: bool = False,
    access_point: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Create a directory on the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that creates a new directory
    on the live cluster. Always confirm the path with the user before
    calling this tool (e.g. "Create directory /ifs/data/projects/new-dir?").

    Arguments:
    - path: Directory path to create relative to / (e.g. "ifs/data/projects/new-dir").
      Do NOT include a leading slash.
    - recursive: If True (default), create parent directories as needed.
    - access_control: POSIX permission mode string (e.g. "0755") or a
      pre-defined ACL value. Optional.
    - overwrite: If True, replace existing directory attributes/ACLs.
    - access_point: If set, use access-point addressing. The path becomes
      relative to the access point.

    Use this tool when the user wants to:
    - Create a new directory on the cluster
    - Make a new folder in the filesystem
    - Set up a directory structure

    Returns:
    - success: Boolean indicating if the directory was created
    - message: Human-readable confirmation
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.create_directory(
        path=path, recursive=recursive, access_control=access_control,
        overwrite=overwrite, access_point=access_point)

@safe_tool(group="filemgmt", mode="write")
def powerscale_directory_delete(
    path: str,
    recursive: bool = False,
    access_point: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Delete a directory from the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that permanently deletes a
    directory from the live cluster. Always confirm the path and whether
    recursive deletion is intended with the user before calling this tool
    (e.g. "Delete directory /ifs/data/projects/old-dir and all its contents?").

    WARNING: When recursive=True, ALL files and subdirectories within the
    directory will be permanently deleted. Use with extreme caution.

    Arguments:
    - path: Directory path to delete relative to / (e.g. "ifs/data/projects/old-dir").
      Do NOT include a leading slash.
    - recursive: If True, delete the directory and all contents. Default False
      (only deletes empty directories for safety).
    - access_point: If set, use access-point addressing.

    Use this tool when the user wants to:
    - Delete or remove a directory
    - Clean up an empty directory
    - Recursively remove a directory tree

    Returns:
    - success: Boolean indicating if the directory was deleted
    - message: Human-readable confirmation
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.delete_directory(
        path=path, recursive=recursive, access_point=access_point)

@safe_tool(group="filemgmt", mode="write")
def powerscale_directory_move(
    path: str,
    destination: str,
    access_point: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Move or rename a directory on the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that moves/renames a directory
    on the live cluster. Always confirm the source and destination paths
    with the user before calling this tool (e.g. "Move directory
    /ifs/data/old-name to /ifs/data/new-name?").

    Arguments:
    - path: Current directory path relative to / (e.g. "ifs/data/old-name").
      Do NOT include a leading slash.
    - destination: Full destination path for the directory
      (e.g. "/ifs/data/new-name"). Include the leading slash.
    - access_point: If set, use access-point addressing for the source path.

    Use this tool when the user wants to:
    - Rename a directory
    - Move a directory to a different location
    - Reorganize the directory structure

    Returns:
    - success: Boolean indicating if the directory was moved
    - message: Human-readable confirmation
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.move_directory(
        path=path, destination=destination, access_point=access_point)

@safe_tool(group="filemgmt", mode="write")
def powerscale_directory_copy(
    source: str,
    destination: str,
    overwrite: bool = False,
    merge: bool = False,
    continue_on_error: bool = False,
    cluster_name: str = None,
) -> dict:
    """
    Recursively copy a directory on the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that copies a directory and all
    its contents on the live cluster. Always confirm the source and destination
    paths with the user before calling this tool (e.g. "Copy directory
    /ifs/data/projects to /ifs/data/projects-backup?").

    Symbolic links in the source are copied as regular files.

    Arguments:
    - source: Full path to the source directory (e.g. "/ifs/data/projects").
      Include the leading slash.
    - destination: Destination path relative to / (e.g. "ifs/data/projects-backup").
      Do NOT include a leading slash.
    - overwrite: If True, replace existing attributes/ACLs at destination.
    - merge: If True, merge contents with an existing directory of the same name.
    - continue_on_error: If True, continue copying remaining objects on
      conflict or error instead of aborting.

    Use this tool when the user wants to:
    - Copy a directory to a new location
    - Create a backup of a directory
    - Duplicate a directory structure

    Returns:
    - success: Boolean — True if copy completed without errors
    - errors: List of any copy errors encountered
    - message: Human-readable confirmation
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.copy_directory(
        source=source, destination=destination, overwrite=overwrite,
        merge=merge, continue_on_error=continue_on_error)

@safe_tool(group="filemgmt", mode="read")
def powerscale_file_read(
    path: str,
    byte_range: Optional[str] = None,
    cluster_name: str = None,
) -> Dict[str, Any]:
    """
    Read the contents of a file on the PowerScale cluster filesystem.

    Retrieves the full text contents of a file. This tool is designed for
    text files. Binary files will be returned with lossy encoding. File
    streaming is NOT supported — the entire file must fit in memory.

    Contents are truncated at 1 MiB to avoid overwhelming the LLM context.
    For larger files, use the byte_range parameter to read specific portions.

    Arguments:
    - path: File path relative to / (e.g. "ifs/data/projects/readme.txt").
      Do NOT include a leading slash.
    - byte_range: Optional byte range to retrieve (e.g. "bytes=0-1023" for
      the first 1024 bytes). Use this for large files or to read specific
      portions.

    Use this tool to answer questions such as:
    - What are the contents of this file?
    - Read the config file at this path
    - Show me what's in this log file

    Response fields:
    - contents: The file contents as text
    - size: Total file size in bytes
    - truncated: True if contents were truncated due to size limit
    - headers: HTTP response headers with file metadata

    Returns:
    - contents: The text content of the file
    - size: File size in bytes
    - truncated: Whether the content was truncated
    - headers: Response headers with metadata
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.get_file_contents(path=path, byte_range=byte_range)

@safe_tool(group="filemgmt", mode="read")
def powerscale_file_attributes(path: str, cluster_name: str = None) -> Dict[str, Any]:
    """
    Get attribute information for a file on the PowerScale cluster.

    Retrieves metadata headers for the specified file without transferring
    its contents. Returns information such as file size, last-modified time,
    content type, and other attributes.

    Arguments:
    - path: File path relative to / (e.g. "ifs/data/projects/readme.txt").
      Do NOT include a leading slash.

    Use this tool when you need to:
    - Check if a file exists
    - Get the size of a file without reading it
    - Get the last-modified time of a file
    - Check file type or encoding

    Returns:
    - A dict of HTTP header key-value pairs containing file attributes
      such as Content-Length, Last-Modified, Content-Type, and
      x-isi-ifs-target-type.
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.get_file_attributes(path=path)

@safe_tool(group="filemgmt", mode="write")
def powerscale_file_create(
    path: str,
    contents: str = '',
    access_control: Optional[str] = None,
    content_type: Optional[str] = None,
    overwrite: bool = False,
    cluster_name: str = None,
) -> dict:
    """
    Create a file on the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that creates a new file on the
    live cluster. Always confirm the path and intent with the user before
    calling this tool (e.g. "Create file /ifs/data/projects/config.txt?").

    File streaming is NOT supported — the entire file contents must be
    provided as a string. Best suited for small text files.

    Arguments:
    - path: File path to create relative to / (e.g. "ifs/data/projects/config.txt").
      Do NOT include a leading slash.
    - contents: The file contents as a string. Default is empty string.
    - access_control: POSIX permission mode string (e.g. "0644") or a
      pre-defined ACL value. Optional.
    - content_type: MIME type of the content (e.g. "text/plain",
      "application/json"). Optional.
    - overwrite: If True, replace an existing file at this path.

    Use this tool when the user wants to:
    - Create a new file on the cluster
    - Write text content to a file
    - Create a configuration or data file

    Returns:
    - success: Boolean indicating if the file was created
    - message: Human-readable confirmation
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.create_file(
        path=path, contents=contents, access_control=access_control,
        content_type=content_type, overwrite=overwrite)

@safe_tool(group="filemgmt", mode="write")
def powerscale_file_delete(path: str, cluster_name: str = None) -> dict:
    """
    Delete a file from the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that permanently deletes a file
    from the live cluster. Always confirm the path with the user before
    calling this tool (e.g. "Delete file /ifs/data/projects/old-file.txt?").

    Arguments:
    - path: File path to delete relative to / (e.g. "ifs/data/projects/old-file.txt").
      Do NOT include a leading slash.

    Use this tool when the user wants to:
    - Delete or remove a file
    - Clean up an unwanted file

    Returns:
    - success: Boolean indicating if the file was deleted
    - message: Human-readable confirmation
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.delete_file(path=path)

@safe_tool(group="filemgmt", mode="write")
def powerscale_file_move(
    path: str,
    destination: str,
    cluster_name: str = None,
) -> dict:
    """
    Move or rename a file on the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that moves/renames a file on the
    live cluster. Always confirm the source and destination paths with the
    user before calling this tool (e.g. "Move file /ifs/data/old.txt to
    /ifs/data/new.txt?").

    The destination path must not already exist.

    Arguments:
    - path: Current file path relative to / (e.g. "ifs/data/old.txt").
      Do NOT include a leading slash.
    - destination: Full destination path for the file (e.g. "/ifs/data/new.txt").
      Include the leading slash.

    Use this tool when the user wants to:
    - Rename a file
    - Move a file to a different directory
    - Reorganize files

    Returns:
    - success: Boolean indicating if the file was moved
    - message: Human-readable confirmation
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.move_file(path=path, destination=destination)

@safe_tool(group="filemgmt", mode="write")
def powerscale_file_copy(
    source: str,
    destination: str,
    overwrite: bool = False,
    clone: bool = False,
    snapshot: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Copy a file on the PowerScale cluster filesystem.

    IMPORTANT: This is a MUTATING operation that copies a file on the live
    cluster. Always confirm the source and destination paths with the user
    before calling this tool (e.g. "Copy file /ifs/data/report.txt to
    /ifs/data/report-backup.txt?").

    Supports Copy-on-Write (CoW) cloning for space-efficient copies and
    can clone files from specific snapshots.

    Arguments:
    - source: Full path to the source file (e.g. "/ifs/data/report.txt").
      Include the leading slash.
    - destination: Destination path relative to / (e.g. "ifs/data/report-backup.txt").
      Do NOT include a leading slash.
    - overwrite: If True, replace an existing file at the destination.
    - clone: If True, create a CoW (Copy-on-Write) clone instead of a full
      copy. Clones are space-efficient as they share data blocks.
    - snapshot: Snapshot name to clone the file from. Only valid when
      clone=True.

    Use this tool when the user wants to:
    - Copy a file to a new location
    - Create a backup copy of a file
    - Clone a file efficiently using CoW
    - Restore a file from a snapshot

    Returns:
    - success: Boolean — True if copy completed without errors
    - errors: List of any copy errors encountered
    - message: Human-readable confirmation
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.copy_file(
        source=source, destination=destination, overwrite=overwrite,
        clone=clone, snapshot=snapshot)

@safe_tool(group="filemgmt", mode="read")
def powerscale_acl_get(
    path: str,
    zone: Optional[str] = None,
    cluster_name: str = None,
) -> Dict[str, Any]:
    """
    Get the access control list (ACL) for a file or directory on the
    PowerScale cluster.

    Returns the full ACL including individual access entries, owner, group,
    POSIX mode, and authoritative source (acl or mode).

    Arguments:
    - path: Namespace path relative to / (e.g. "ifs/data/projects").
      Do NOT include a leading slash.
    - zone: Access zone name. Optional — defaults to the System zone.

    Use this tool to answer questions such as:
    - What are the permissions on this file or directory?
    - Who owns this file?
    - What ACL entries are set on this path?
    - What is the POSIX mode of this directory?

    Response fields:
    - acl: List of ACL entry objects, each with accesstype, accessrights,
      inherit_flags, and trustee
    - owner: Owner identity (id, name, type)
    - group: Group identity (id, name, type)
    - mode: POSIX mode string (e.g. "0755")
    - authoritative: Whether "acl" or "mode" is authoritative

    Returns:
    - Full ACL dict with acl entries, owner, group, mode, and authoritative
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.get_acl(path=path, zone=zone)

@safe_tool(group="filemgmt", mode="write")
def powerscale_acl_set(
    path: str,
    mode: Optional[str] = None,
    owner: Optional[str] = None,
    group: Optional[str] = None,
    acl: Optional[str] = None,
    action: str = 'replace',
    zone: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Set the access control list (ACL) on a file or directory on the
    PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that changes permissions on the
    live cluster. Always confirm the path and intended permission changes
    with the user before calling this tool.

    Two modes of operation:
    1. POSIX mode: Set mode="0755" (simple permissions)
    2. ACL entries: Provide acl as a JSON string with detailed access entries

    Arguments:
    - path: Namespace path relative to / (e.g. "ifs/data/projects").
      Do NOT include a leading slash.
    - mode: POSIX mode string (e.g. "0755", "0644"). Sets traditional
      Unix permissions. Use this for simple permission changes.
    - owner: Owner name to set (e.g. "root", "admin").
    - group: Group name to set (e.g. "wheel", "staff").
    - acl: JSON string for fine-grained access control. Must be a JSON ARRAY
      of ACL entry objects (not a single object). Do NOT put owner/group/mode
      here — use the dedicated owner/group/mode arguments above for those.
      Example:
      '[{"accesstype":"allow","accessrights":["dir_gen_all"],
        "inherit_flags":["container_inherit","object_inherit"],
        "trustee":{"name":"admin","type":"user"}}]'
    - action: "replace" (default) to replace entire ACL, or "update" to
      merge with existing ACL entries.
    - zone: Access zone name. Optional.

    Use this tool when the user wants to:
    - Change file or directory permissions
    - Set ownership on a path
    - Configure ACL entries for specific users or groups

    Returns:
    - success: Boolean indicating if the ACL was set
    - message: Human-readable confirmation
    """
    acl_list = parse_json_list_param("acl", acl)

    # Auto-detect authoritative type based on what's being set.
    # OneFS requires 'authoritative' for all ACL set operations.
    authoritative = "mode"  # default to mode for owner/group changes
    if acl_list is not None:
        authoritative = "acl"

    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.set_acl(
        path=path, mode=mode, owner=owner, group=group,
        acl=acl_list, action=action, authoritative=authoritative,
        zone=zone)

@safe_tool(group="filemgmt", mode="read")
def powerscale_metadata_get(
    path: str,
    is_directory: bool = True,
    zone: Optional[str] = None,
    cluster_name: str = None,
) -> Dict[str, Any]:
    """
    Get metadata attributes for a file or directory on the PowerScale cluster.

    Retrieves user-defined and system metadata attributes for the specified
    namespace object.

    Arguments:
    - path: Path relative to / (e.g. "ifs/data/projects" or
      "ifs/data/projects/file.txt"). Do NOT include a leading slash.
    - is_directory: True (default) if the path is a directory, False if it
      is a file. This determines which API endpoint is used.
    - zone: Access zone name. Optional.

    Use this tool to answer questions such as:
    - What metadata is set on this file or directory?
    - What custom attributes are attached to this path?
    - What are the system attributes of this object?

    Response fields:
    - attrs: List of attribute objects, each with name, namespace, and value

    Returns:
    - attrs: List of metadata attribute dicts
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.get_metadata(path=path, is_directory=is_directory, zone=zone)

@safe_tool(group="filemgmt", mode="write")
def powerscale_metadata_set(
    path: str,
    attrs: str,
    action: str = 'update',
    is_directory: bool = True,
    zone: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Set metadata attributes on a file or directory on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that modifies metadata on the
    live cluster. Always confirm the path and attributes with the user
    before calling this tool.

    Arguments:
    - path: Path relative to / (e.g. "ifs/data/projects"). Do NOT include
      a leading slash.
    - attrs: JSON string of attribute objects to set. Each object must have
      "name" and "value" keys, and optionally "namespace" and "op".
      Example: '[{"name":"department","value":"engineering"},
                 {"name":"classification","value":"internal"}]'
    - action: "update" (default) to merge with existing attributes, or
      "replace" to replace all attributes.
    - is_directory: True (default) if the path is a directory, False if a file.
    - zone: Access zone name. Optional.

    Use this tool when the user wants to:
    - Set custom metadata on a file or directory
    - Tag files with attributes
    - Update metadata values

    Returns:
    - success: Boolean indicating if metadata was set
    - message: Human-readable confirmation
    """
    attrs_list = parse_json_list_param("attrs", attrs)

    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.set_metadata(
        path=path, attrs=attrs_list, action=action,
        is_directory=is_directory, zone=zone)

@safe_tool(group="filemgmt", mode="read")
def powerscale_access_point_list(
    versions: bool = False,
    cluster_name: str = None,
) -> Dict[str, Any]:
    """
    List namespace access points on the PowerScale cluster.

    Access points are named entry points into the cluster filesystem that
    provide scoped access to specific directory trees.

    Arguments:
    - versions: If True, include protocol version information for each
      access point.

    Use this tool to answer questions such as:
    - What access points are configured on the cluster?
    - What namespace entry points are available?

    Returns:
    - namespaces: List of access point objects with path and name information
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.list_access_points(versions=versions)

@safe_tool(group="filemgmt", mode="write")
def powerscale_access_point_create(
    name: str,
    path: str,
    cluster_name: str = None,
) -> dict:
    """
    Create a namespace access point on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new access point
    on the live cluster. Only root users can create access points. Always
    confirm the access point name and path with the user before calling
    this tool.

    Arguments:
    - name: Name for the access point (e.g. "projects")
    - path: Absolute filesystem path the access point maps to
      (e.g. "/ifs/data/projects")

    Use this tool when the user wants to:
    - Create a new namespace access point
    - Set up a scoped entry point into the filesystem

    Returns:
    - success: Boolean indicating if the access point was created
    - message: Human-readable confirmation
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.create_access_point(name=name, path=path)

@safe_tool(group="filemgmt", mode="write")
def powerscale_access_point_delete(name: str, cluster_name: str = None) -> dict:
    """
    Delete a namespace access point from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes an access point
    from the live cluster. Only root users can delete access points. Always
    confirm the access point name with the user before calling this tool.
    This does NOT delete the underlying directory — it only removes the
    access point definition.

    Arguments:
    - name: Name of the access point to delete (e.g. "projects")

    Use this tool when the user wants to:
    - Remove a namespace access point
    - Delete an access point entry

    Returns:
    - success: Boolean indicating if the access point was deleted
    - message: Human-readable confirmation
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.delete_access_point(name=name)

@safe_tool(group="filemgmt", mode="read")
def powerscale_worm_get(path: str, cluster_name: str = None) -> Dict[str, Any]:
    """
    Get WORM (Write Once Read Many) properties for a file on the
    PowerScale cluster.

    WORM / SmartLock protects files from modification and deletion until
    a retention date has passed. This tool retrieves the WORM state for
    a specific file.

    Arguments:
    - path: File path relative to / (e.g. "ifs/data/compliance/report.pdf").
      Do NOT include a leading slash. The file must be in a SmartLock
      directory.

    Use this tool to answer questions such as:
    - Is this file committed to WORM?
    - What is the retention date on this file?
    - What SmartLock domain does this file belong to?

    Response fields:
    - worm_committed: Whether the file is committed to WORM state
    - worm_retention_date: The retention expiration date (UTC)
    - worm_retention_date_val: Retention date as epoch timestamp
    - worm_override_retention_date: Override retention date if set

    Returns:
    - Full WORM properties dict for the file
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.get_worm_properties(path=path)

@safe_tool(group="filemgmt", mode="write")
def powerscale_worm_set(
    path: str,
    commit_to_worm: bool = False,
    worm_retention_date: Optional[str] = None,
    cluster_name: str = None,
) -> dict:
    """
    Set WORM (Write Once Read Many) properties on a file on the
    PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that commits a file to WORM
    state and/or sets a retention date. Once committed, a WORM file CANNOT
    be modified or deleted until the retention period expires. Always confirm
    the path, commit flag, and retention date with the user before calling
    this tool. This action may be IRREVERSIBLE.

    Arguments:
    - path: File path relative to / (e.g. "ifs/data/compliance/report.pdf").
      Do NOT include a leading slash. The file must be in a SmartLock
      directory.
    - commit_to_worm: If True, commit the file to WORM state. Once
      committed, the file cannot be modified or deleted until the retention
      date passes.
    - worm_retention_date: Retention expiration date in UTC string format
      (e.g. "2025-12-31T23:59:59Z"). After this date, the file can be
      deleted (but not modified).

    Use this tool when the user wants to:
    - Commit a file to WORM/SmartLock protection
    - Set or extend a retention date on a file
    - Lock a file for compliance purposes

    Returns:
    - success: Boolean indicating if WORM properties were set
    - message: Human-readable confirmation
    """
    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.set_worm_properties(
        path=path, commit_to_worm=commit_to_worm,
        worm_retention_date=worm_retention_date)

@safe_tool(group="filemgmt", mode="read")
def powerscale_directory_query(
    path: str,
    conditions: str,
    logic: str = 'and',
    result_attrs: Optional[str] = None,
    limit: int = 1000,
    resume: Optional[str] = None,
    sort: Optional[str] = None,
    dir: Optional[str] = None,
    type: Optional[str] = None,
    hidden: bool = False,
    max_depth: Optional[int] = None,
    cluster_name: str = None,
) -> Dict[str, Any]:
    """
    Query objects within a directory on the PowerScale cluster by attribute
    conditions.

    Performs an advanced search within a directory tree, filtering objects
    by system-defined or user-defined attributes. Supports pagination for
    large result sets.

    Usage (pagination):
    - First call: use resume=None (or omit it)
    - If the response contains a non-null "resume" value, call again passing
      that value as the resume argument to fetch the next page
    - Continue until "resume" is None (has_more will be False)

    Arguments:
    - path: Directory path to query relative to / (e.g. "ifs/data/projects").
      Do NOT include a leading slash.
    - conditions: JSON string of condition objects. Each condition has:
      - attr: Attribute name (e.g. "name", "size", "type", "owner",
        "last_modified")
      - operator: Comparison operator ("=", "!=", ">", "<", ">=", "<=",
        "like")
      - value: Value to compare against
      Example: '[{"attr":"name","operator":"like","value":"*.log"},
                 {"attr":"size","operator":">","value":"1048576"}]'
    - logic: How to combine conditions — "and" (default, all must match) or
      "or" (any can match)
    - result_attrs: Optional JSON string of attribute names to include in
      results (e.g. '["name","size","last_modified"]'). If omitted, default
      attributes are returned.
    - limit: Maximum number of objects to return per page (default 1000)
    - resume: Pagination token from a previous call
    - sort: Attribute to sort results by
    - dir: Sort direction — "ASC" or "DESC"
    - type: Filter by object type (e.g. "container", "object")
    - hidden: If True, include hidden files in results
    - max_depth: Maximum directory depth to search. If omitted, searches
      all depths.

    Use this tool to answer questions such as:
    - Find all .log files in this directory tree
    - Which files are larger than 1 GiB under this path?
    - Search for files modified after a certain date
    - Find files owned by a specific user

    Returns:
    - children: List of matching objects with their attributes
    - resume: Pagination token for next page, or None if finished
    - has_more: True if more pages exist
    """
    resume = normalize_resume(resume)

    conditions_list = parse_json_list_param("conditions", conditions)
    result_attrs_list = parse_json_param("result_attrs", result_attrs)

    cluster = get_cluster(cluster_name)
    fm = FileMgmt(cluster)
    return fm.query_directory(
        path=path, conditions=conditions_list, logic=logic,
        result_attrs=result_attrs_list, limit=limit, resume=resume,
        sort=sort, dir=dir, type=type, hidden=hidden,
        max_depth=max_depth)
