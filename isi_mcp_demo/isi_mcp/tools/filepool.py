from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.filepool import FilePool
from typing import Dict, Any


@safe_tool(group="filepool", mode="read")
def powerscale_filepool_policy_get(cluster_name: str = None) -> Dict[str, Any]:
    """
    Returns all FilePool policies on the PowerScale cluster.

    FilePool policies automate data tiering by defining file matching criteria
    (name patterns, size, age, file type) and actions (move to a storage pool,
    set protection level, set access pattern) applied to matching files.

    Unlike most list tools, FilePool policies are NOT paginated. All policies
    are returned in a single response.

    Each policy object includes:
    - id: Unique policy identifier
    - name: The policy name
    - description: Human-readable description
    - apply_order: Evaluation order relative to other policies
    - file_matching_pattern: The rules defining which files match this policy
      (nested or_criteria -> and_criteria structure)
    - actions: List of actions applied to matching files (storage pool moves,
      protection changes, access pattern settings)
    - state: Policy health state
    - state_details: Additional state information
    - birth_cluster_id: GUID of the cluster where the policy was created

    Use this tool to answer questions such as:
    - What FilePool policies are configured?
    - How is data tiering set up on the cluster?
    - Which files are being moved to which storage pools?
    - What file matching criteria are used for tiering?
    - Are any FilePool policies in a bad state?

    Returns:
    - items: List of all FilePool policy objects
    - total: Total number of policies
    """
    cluster = get_cluster(cluster_name)
    filepool = FilePool(cluster)
    return filepool.get()

@safe_tool(group="filepool", mode="read")
def powerscale_filepool_policy_get_by_name(policy_id: str, cluster_name: str = None) -> Dict[str, Any]:
    """
    Retrieve detailed information about a specific FilePool policy by name or ID.

    Use this tool to inspect the full configuration of a single FilePool policy,
    including its file matching rules and actions.

    Arguments:
    - policy_id: The policy name or ID to retrieve (e.g. "archive-old-logs")

    Use this tool to answer questions such as:
    - What are the matching criteria for a specific policy?
    - What actions does a specific FilePool policy apply?
    - What is the apply_order of a given policy?

    Returns:
    - success: Boolean indicating if the policy was found
    - policy: Complete policy object with all configuration details
    - error: Error message if the policy was not found
    """
    cluster = get_cluster(cluster_name)
    filepool = FilePool(cluster)
    return filepool.get_policy(policy_id=policy_id)

@safe_tool(group="filepool", mode="read")
def powerscale_filepool_default_policy_get(cluster_name: str = None) -> Dict[str, Any]:
    """
    Return the system default FilePool policy on the PowerScale cluster.

    The default policy applies to all files that do not match any custom
    FilePool policy. It defines the baseline storage pool, protection level,
    and access pattern for unclassified files.

    Use this tool to answer questions such as:
    - What is the default tiering behavior for files?
    - Where do unmatched files go?
    - What is the default protection level?

    Returns:
    - success: Boolean indicating if the operation succeeded
    - default_policy: The default policy object with actions and settings
    """
    cluster = get_cluster(cluster_name)
    filepool = FilePool(cluster)
    return filepool.get_default_policy()

@safe_tool(group="filepool", mode="write")
def powerscale_filepool_policy_create(
    policy_name: str,
    file_matching_pattern: str,
    description: str = None,
    apply_order: int = None,
    apply_data_storage_policy: str = None,
    apply_snapshot_storage_policy: str = None,
    set_requested_protection: str = None,
    set_data_access_pattern: str = None,
    set_write_performance_optimization: str = None,
    cluster_name: str = None,
) -> dict:
    """
    Create a FilePool policy on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new FilePool tiering
    policy on the live cluster. Always confirm the policy name and configuration
    with the user before calling this tool.

    This tool uses Ansible automation to create the policy via the
    dellemc.powerscale collection.

    Arguments (required):
    - policy_name: A unique name for the policy (e.g. "archive-old-logs")
    - file_matching_pattern: JSON string defining the file matching rules.
      Structure: {"or_criteria": [{"and_criteria": [<criterion>, ...]}, ...]}
      Maximum 3 or_criteria groups, maximum 5 and_criteria per group.

      Each criterion is a dict with:
      - type (required): "file_name", "file_path", "file_type", "file_attribute",
        "size", "accessed", "created", "modified", or "metadata_changed"
      - condition: Comparison operator (varies by type):
        * name/path: "matches", "does_not_match", "contains", "does_not_contain"
        * file_type: "matches", "does_not_match"
        * file_attribute: "matches", "does_not_match", "exists", "does_not_exist"
        * size: "equal", "not_equal", "greater_than", "greater_than_equal_to",
          "less_than", "less_than_equal_to"
        * date types: "after", "before", "is_newer_than", "is_older_than"
      - value: Value to compare against (for name/path/attribute types)
      - case_sensitive: Boolean for name/path matching
      - file_type_option: For file_type criteria (e.g. "directory", "file", "other")
      - size_info: For size criteria: {"size_value": <int>, "size_unit": "<unit>"}
        Units: "B", "KB", "MB", "GB", "TB"
      - datetime_value: For date after/before: "YYYY-MM-DD HH:MM" format
      - relative_datetime_count: For is_newer_than/is_older_than:
        {"time_value": <int>, "time_unit": "<unit>"}
        Units: "years", "months", "weeks", "days", "hours"
      - field: For file_attribute type, the attribute field name

      Example -- match .log files larger than 1 GB not accessed in 90 days:
      '{"or_criteria": [{"and_criteria": [
        {"type": "file_name", "condition": "matches", "value": "*.log",
         "case_sensitive": false},
        {"type": "size", "condition": "greater_than",
         "size_info": {"size_value": 1, "size_unit": "GB"}},
        {"type": "accessed", "condition": "is_older_than",
         "relative_datetime_count": {"time_value": 90, "time_unit": "days"}}
      ]}]}'

    Arguments (optional -- omit to keep cluster defaults):
    - description: Human-readable description of the policy
    - apply_order: Integer ordering relative to other policies (lower = evaluated first)
    - apply_data_storage_policy: JSON string defining where to store file data.
      Format: {"ssd_strategy": "<strategy>", "storagepool": "<pool_name>"}
      ssd_strategy options: "metadata", "metadata-write", "data", "avoid"
    - apply_snapshot_storage_policy: JSON string for snapshot data storage.
      Same format as apply_data_storage_policy.
    - set_requested_protection: Protection level string. Options include:
      "default", "+1", "+2:1", "+2d:1n", "+3", "+3:1", "+3d:1n1d", "+4",
      "2x", "3x", "4x", "5x", "6x", "7x", "8x", "mirrored"
    - set_data_access_pattern: Optimization hint for data access.
      Options: "random", "concurrency", "streaming"
    - set_write_performance_optimization: Write caching strategy.
      Options: "enable_smartcache", "disable_smartcache"

    Use this tool when the user wants to:
    - Create an automated data tiering policy
    - Move old or large files to a different storage pool
    - Set protection levels based on file criteria
    - Optimize access patterns for specific file types

    Returns:
    - success: Boolean indicating if the policy was created
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    cluster = get_cluster(cluster_name)
    filepool = FilePool(cluster)
    return filepool.create(
        policy_name=policy_name,
        file_matching_pattern=file_matching_pattern,
        description=description,
        apply_order=apply_order,
        apply_data_storage_policy=apply_data_storage_policy,
        apply_snapshot_storage_policy=apply_snapshot_storage_policy,
        set_requested_protection=set_requested_protection,
        set_data_access_pattern=set_data_access_pattern,
        set_write_performance_optimization=set_write_performance_optimization,
    )

@safe_tool(group="filepool", mode="write")
def powerscale_filepool_policy_update(
    policy_id: str,
    description: str = None,
    apply_order: int = None,
    file_matching_pattern: str = None,
    apply_data_storage_policy: str = None,
    apply_snapshot_storage_policy: str = None,
    set_requested_protection: str = None,
    set_data_access_pattern: str = None,
    set_write_performance_optimization: str = None,
    cluster_name: str = None,
) -> dict:
    """
    Update an existing FilePool policy on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that modifies a FilePool policy on
    the live cluster. Always confirm the policy name and the changes with the
    user before calling this tool.

    This tool uses the SDK directly because the Ansible module does not support
    policy modification. Only the fields you provide will be changed; omitted
    fields remain unchanged.

    Arguments (required):
    - policy_id: The policy name or ID to update (e.g. "archive-old-logs")

    Arguments (optional -- provide only fields to change):
    - description: New description
    - apply_order: New evaluation order
    - file_matching_pattern: JSON string with new matching rules (same format
      as powerscale_filepool_policy_create)
    - apply_data_storage_policy: JSON string with new data storage pool settings
      Format: {"ssd_strategy": "<strategy>", "storagepool": "<pool_name>"}
    - apply_snapshot_storage_policy: JSON string with new snapshot storage settings
    - set_requested_protection: New protection level string
    - set_data_access_pattern: New access pattern ("random", "concurrency", "streaming")
    - set_write_performance_optimization: New write perf setting
      ("enable_smartcache", "disable_smartcache")

    Use this tool when the user wants to:
    - Change the file matching criteria of an existing policy
    - Move a policy's target to a different storage pool
    - Change the protection level or access pattern of a policy
    - Reorder a policy relative to other policies

    Returns:
    - success: Boolean indicating if the update succeeded
    - message: Success or error message
    """
    cluster = get_cluster(cluster_name)
    filepool = FilePool(cluster)
    return filepool.update(
        policy_id=policy_id,
        description=description,
        apply_order=apply_order,
        file_matching_pattern=file_matching_pattern,
        apply_data_storage_policy=apply_data_storage_policy,
        apply_snapshot_storage_policy=apply_snapshot_storage_policy,
        set_requested_protection=set_requested_protection,
        set_data_access_pattern=set_data_access_pattern,
        set_write_performance_optimization=set_write_performance_optimization,
    )

@safe_tool(group="filepool", mode="write")
def powerscale_filepool_policy_remove(policy_name: str, cluster_name: str = None) -> dict:
    """
    Remove a FilePool policy from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes a FilePool tiering
    policy from the live cluster. Always confirm the policy name with the user
    before calling this tool (e.g. "Remove FilePool policy 'archive-old-logs'?").
    Files that were already tiered by this policy remain in their current
    location -- only the policy definition is removed.

    Arguments:
    - policy_name: The name of the FilePool policy to remove

    Use this tool when the user wants to:
    - Remove or delete a FilePool tiering policy
    - Stop automatic data movement for specific file criteria
    - Clean up unused tiering policies

    Returns:
    - success: Boolean indicating if the policy was removed
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    cluster = get_cluster(cluster_name)
    filepool = FilePool(cluster)
    return filepool.delete(policy_name=policy_name)
