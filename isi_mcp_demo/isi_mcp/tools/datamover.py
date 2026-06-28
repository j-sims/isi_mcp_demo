from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.datamover import DataMover
from modules.utils.paging import normalize_resume
from typing import Dict, Any


@safe_tool(group="datamover", mode="read")
def powerscale_datamover_policy_get(limit: int = 1000, resume: str = None, cluster_name: str = None) -> Dict[str, Any]:
    """
    Returns a paginated list of DataMover policies on the PowerScale cluster.

    DataMover provides data movement capabilities for migrating, copying, or
    replicating data within or between PowerScale clusters. Each policy defines
    the source, destination, schedule, and other parameters for data movement jobs.

    Arguments:
    - limit: Maximum number of policies to return (default 1000)
    - resume: Resume token from previous call for pagination (optional)

    Use this tool when the user wants to:
    - List all DataMover policies
    - See what data movement jobs are configured
    - Check policy configurations before creating a new one
    - Browse existing policies for reference

    Returns:
    - items: List of DataMover policy objects with full details
    - resume: Token for fetching the next page (None if last page)

    Note: If there are many policies, use the resume token to page through results.
    For example, after the first call returns a resume token, call again with that
    token to get the next batch of results.
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    # Normalize resume token (handle "null", "None", None)
    resume = normalize_resume(resume)
    return datamover.get_policies(limit=limit, resume=resume)

@safe_tool(group="datamover", mode="read")
def powerscale_datamover_policy_get_by_id(policy_id: str, cluster_name: str = None) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific DataMover policy by ID or name.

    Use this tool to get complete configuration details for a single DataMover policy,
    including source/destination paths, schedule, priority, enabled status, and all
    policy-specific attributes.

    Arguments:
    - policy_id: The policy name or ID to retrieve (e.g. "data-migration-policy" or "12345")

    Use this tool when the user wants to:
    - View detailed configuration of a specific policy
    - Check settings before modifying a policy
    - Verify policy parameters after creation
    - Inspect a policy mentioned by name

    Returns:
    - success: Boolean indicating if the operation succeeded
    - policy: Complete policy object with all configuration details
    - error: Error message if the operation failed
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    return datamover.get_policy(policy_id=policy_id)

@safe_tool(group="datamover", mode="write")
def powerscale_datamover_policy_create(name: str, policy_type: str,
                                       base_policy_id: int = None,
                                       enabled: bool = None, priority: str = None,
                                       run_now: bool = None, schedule: str = None,
                                       cluster_name: str = None) -> dict:
    """
    Create a new DataMover policy on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new data movement policy
    on the live cluster. Always confirm the policy name and configuration with the user
    before calling this tool (e.g. "Create DataMover policy 'archive-old-data' with
    base_policy_id 1?").

    Arguments:
    - name: A user-provided policy name (required, e.g. "archive-old-data")
    - policy_type: The type of data movement operation (required). One of:
        "COPY"        — copy data from source to target
        "REPEAT_COPY" — repeatedly copy data on a schedule
        "CREATION"    — create data at the target
        "EXPIRATION"  — expire/delete data at the target
    - base_policy_id: The unique base policy identifier to use as a template (optional)
    - enabled: True to enable the policy immediately, False to create it disabled (optional)
    - priority: The relative priority of the policy, e.g. "high", "medium", "low" (optional)
    - run_now: Execute the policy immediately instead of waiting for schedule (optional, default False)
    - schedule: The schedule for the policy - start time, recurrence, etc. (optional)

    Use this tool when the user wants to:
    - Create a new data movement policy
    - Set up automated data migration or archival
    - Configure data replication or copying between paths
    - Establish a new data movement job

    Returns:
    - success: Boolean indicating if the policy was created
    - message: Success or error message
    - id: The ID of the newly created policy (if successful)

    Note: DataMover policies require a base policy to define the data movement operation.
    Use base_policy_id to reference an existing base policy, or the policy may use defaults.
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    return datamover.create_policy(name=name, policy_type=policy_type,
                                   base_policy_id=base_policy_id,
                                   enabled=enabled, priority=priority,
                                   run_now=run_now, schedule=schedule)

@safe_tool(group="datamover", mode="write")
def powerscale_datamover_policy_delete(policy_id: str, cluster_name: str = None) -> dict:
    """
    Delete a DataMover policy from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that permanently removes a data movement
    policy from the live cluster. Always confirm the policy ID/name with the user before
    calling this tool (e.g. "Delete DataMover policy 'archive-old-data'?"). This stops
    future data movement jobs but does NOT affect data that has already been moved.

    Arguments:
    - policy_id: The name or ID of the DataMover policy to delete (e.g. "archive-old-data" or "12345")

    Use this tool when the user wants to:
    - Remove or delete a data movement policy
    - Stop a DataMover policy that is no longer needed
    - Clean up an old or unused policy
    - Disable data movement operations permanently

    Returns:
    - success: Boolean indicating if the policy was deleted
    - message: Success or error message
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    return datamover.delete_policy(policy_id=policy_id)

@safe_tool(group="datamover", mode="read")
def powerscale_datamover_policy_last_job(policy_id: str, cluster_name: str = None) -> dict:
    """
    Retrieve the last job information for a specific DataMover policy.

    Use this tool to get details about the most recent execution of a DataMover policy,
    including the job ID and last execution timestamp. This helps track policy execution
    history and troubleshoot issues with data movement jobs.

    Arguments:
    - policy_id: The policy name or ID to query (e.g. "archive-old-data" or "12345")

    Use this tool when the user wants to:
    - Check when a policy last ran
    - Get the job ID for the most recent execution
    - Verify that a policy is executing as expected
    - Troubleshoot policy execution issues
    - Track data movement job history

    Returns:
    - success: Boolean indicating if the operation succeeded
    - last_job: Object containing job ID and execution timestamp
    - error: Error message if the operation failed
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    return datamover.get_policy_last_job(policy_id=policy_id)

@safe_tool(group="datamover", mode="read")
def powerscale_datamover_account_get(limit: int = 1000, resume: str = None, cluster_name: str = None) -> Dict[str, Any]:
    """
    Returns a paginated list of DataMover accounts on the PowerScale cluster.

    DataMover accounts represent connections to data storage locations (local paths,
    NFS exports, S3 buckets, etc.) that can be used as sources or targets for data
    movement operations. Each account contains connection details, credentials, and
    configuration for a specific storage location.

    Arguments:
    - limit: Maximum number of accounts to return (default 1000)
    - resume: Resume token from previous call for pagination (optional)

    Use this tool when the user wants to:
    - List all DataMover accounts
    - See what storage locations are configured for data movement
    - Check account configurations before creating policies
    - Browse existing accounts for reference

    Returns:
    - items: List of DataMover account objects with full details
    - resume: Token for fetching the next page (None if last page)
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    # Normalize resume token (handle "null", "None", None)
    resume = normalize_resume(resume)
    return datamover.get_accounts(limit=limit, resume=resume)

@safe_tool(group="datamover", mode="read")
def powerscale_datamover_account_get_by_id(account_id: str, cluster_name: str = None) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific DataMover account by ID or name.

    Use this tool to get complete configuration details for a single DataMover account,
    including storage type, URI, credentials, network restrictions, and all account-specific
    settings.

    Arguments:
    - account_id: The account name or ID to retrieve (e.g. "s3-archive" or "12345")

    Use this tool when the user wants to:
    - View detailed configuration of a specific account
    - Check account settings before using in a policy
    - Verify account parameters after creation
    - Inspect an account mentioned by name

    Returns:
    - success: Boolean indicating if the operation succeeded
    - account: Complete account object with all configuration details
    - error: Error message if the operation failed
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    return datamover.get_account(account_id=account_id)

@safe_tool(group="datamover", mode="write")
def powerscale_datamover_account_create(name: str, account_type: str, uri: str,
                                        briefcase: str = None, enforce_sse: bool = None,
                                        local_network_pool: str = None, max_sparks: int = None,
                                        remote_network_pool: str = None, storage_class: str = None,
                                        cluster_name: str = None) -> dict:
    """
    Create a new DataMover account on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new data storage account
    on the live cluster. Always confirm the account name and configuration with the user
    before calling this tool (e.g. "Create DataMover account 's3-archive' pointing to
    s3://mybucket?").

    Arguments:
    - name: Name for this DataMover account (required, e.g. "s3-archive")
    - account_type: Type of data storage (required, e.g. "s3", "nfs", "local")
    - uri: Valid URI pointing to the data storage (required, e.g. "s3://bucket-name")
    - briefcase: Opaque container for additional key-value data (optional)
    - enforce_sse: Enforce Server-Side Encryption for AWS S3 (optional, default False)
    - local_network_pool: Local network restriction for connections (optional)
    - max_sparks: Limit of concurrent tasks per node (optional)
    - remote_network_pool: Remote network restriction for connections (optional)
    - storage_class: Storage class for cloud accounts (optional, e.g. "STANDARD", "GLACIER")

    Use this tool when the user wants to:
    - Create a new data storage account
    - Configure access to S3, NFS, or local storage
    - Set up source or target locations for data movement
    - Establish credentials for external storage

    Returns:
    - success: Boolean indicating if the account was created
    - message: Success or error message
    - id: The ID of the newly created account (if successful)

    Note: Credentials should be configured separately or passed via the briefcase parameter.
    Different account types (S3, NFS, local) have different URI formats and requirements.
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    return datamover.create_account(name=name, account_type=account_type, uri=uri,
                                    briefcase=briefcase, enforce_sse=enforce_sse,
                                    local_network_pool=local_network_pool,
                                    max_sparks=max_sparks,
                                    remote_network_pool=remote_network_pool,
                                    storage_class=storage_class)

@safe_tool(group="datamover", mode="write")
def powerscale_datamover_account_delete(account_id: str, cluster_name: str = None) -> dict:
    """
    Delete a DataMover account from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that permanently removes a data storage
    account from the live cluster. Always confirm the account ID/name with the user before
    calling this tool (e.g. "Delete DataMover account 's3-archive'?"). This removes the
    account configuration but does NOT affect data in the storage location itself.

    Arguments:
    - account_id: The name or ID of the DataMover account to delete (e.g. "s3-archive" or "12345")

    Use this tool when the user wants to:
    - Remove or delete a storage account
    - Clean up an old or unused account
    - Decommission access to a storage location
    - Remove account configurations

    Returns:
    - success: Boolean indicating if the account was deleted
    - message: Success or error message

    Warning: Deleting an account that is referenced by existing policies will cause those
    policies to fail. Always check policy dependencies before deleting accounts.
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    return datamover.delete_account(account_id=account_id)

@safe_tool(group="datamover", mode="read")
def powerscale_datamover_base_policy_get(limit: int = 1000, resume: str = None, cluster_name: str = None) -> Dict[str, Any]:
    """
    Returns a paginated list of DataMover base policies on the PowerScale cluster.

    Base policies serve as templates for creating concrete data movement policies.
    They define common configurations like source/target accounts, paths, schedules,
    and retention settings that can be reused across multiple policies. Regular policies
    can inherit from base policies to simplify configuration and maintain consistency.

    Arguments:
    - limit: Maximum number of base policies to return (default 1000)
    - resume: Resume token from previous call for pagination (optional)

    Use this tool when the user wants to:
    - List all DataMover base policies
    - See available policy templates
    - Check base policy configurations before creating concrete policies
    - Browse existing base policies for reference

    Returns:
    - items: List of DataMover base policy objects with full details
    - resume: Token for fetching the next page (None if last page)
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    # Normalize resume token (handle "null", "None", None)
    resume = normalize_resume(resume)
    return datamover.get_base_policies(limit=limit, resume=resume)

@safe_tool(group="datamover", mode="read")
def powerscale_datamover_base_policy_get_by_id(base_policy_id: str, cluster_name: str = None) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific DataMover base policy by ID or name.

    Use this tool to get complete configuration details for a single DataMover base policy,
    including source/target accounts, paths, schedules, retention settings, and all
    template-specific attributes.

    Arguments:
    - base_policy_id: The base policy name or ID to retrieve (e.g. "s3-archive-template" or "1")

    Use this tool when the user wants to:
    - View detailed configuration of a specific base policy
    - Check template settings before creating derived policies
    - Verify base policy parameters after creation
    - Inspect a base policy mentioned by name

    Returns:
    - success: Boolean indicating if the operation succeeded
    - base_policy: Complete base policy object with all configuration details
    - error: Error message if the operation failed
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    return datamover.get_base_policy(base_policy_id=base_policy_id)

@safe_tool(group="datamover", mode="write")
def powerscale_datamover_base_policy_create(name: str, enabled: bool = None, priority: str = None,
                                            source_account_id: str = None, source_base_path: str = None,
                                            target_account_id: str = None, target_base_path: str = None,
                                            override_list: str = None,
                                            cluster_name: str = None) -> dict:
    """
    Create a new DataMover base policy on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new base policy template
    on the live cluster. Always confirm the base policy name and configuration with the user
    before calling this tool (e.g. "Create DataMover base policy 's3-archive-template'
    from account 'local-data' to 's3-archive'?").

    Arguments:
    - name: A user-provided base policy name (required, e.g. "s3-archive-template")
    - enabled: True to enable the base policy, False otherwise (optional)
    - priority: The relative priority (optional, e.g. "high", "medium", "low")
    - source_account_id: Source data storage account ID or name (optional)
    - source_base_path: Filesystem base path on source (optional, e.g. "/ifs/data")
    - target_account_id: Destination data storage account ID or name (optional)
    - target_base_path: Filesystem base path on target (optional, e.g. "/archive")
    - override_list: JSON array of field names that child policies are permitted to
      override (optional, defaults to [] meaning no overrides allowed).
      Allowed values: "ENABLED", "PRIORITY", "SCHEDULE", "BRIEFCASE",
      "SOURCE_ACCOUNT_ID", "TARGET_ACCOUNT_ID", "BASE_ACCOUNT_ID",
      "TASK_ACCOUNT_ID", "SUBPATHS", "SOURCE_BASE_PATH", "TARGET_BASE_PATH",
      "SRC_DATASET_RETENTION", "TGT_DATASET_RETENTION".
      Example: '["ENABLED","PRIORITY"]'

    Use this tool when the user wants to:
    - Create a new base policy template
    - Define common data movement configurations
    - Set up reusable policy templates
    - Establish standard source/target patterns

    Returns:
    - success: Boolean indicating if the base policy was created
    - message: Success or error message
    - id: The ID of the newly created base policy (if successful)

    Note: Base policies serve as templates. Create concrete policies that reference
    the base policy ID to inherit its configuration.
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    return datamover.create_base_policy(name=name, enabled=enabled, priority=priority,
                                       source_account_id=source_account_id,
                                       source_base_path=source_base_path,
                                       target_account_id=target_account_id,
                                       target_base_path=target_base_path,
                                       override_list=override_list)

@safe_tool(group="datamover", mode="write")
def powerscale_datamover_base_policy_delete(base_policy_id: str, cluster_name: str = None) -> dict:
    """
    Delete a DataMover base policy from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that permanently removes a base policy
    template from the live cluster. Always confirm the base policy ID/name with the user
    before calling this tool (e.g. "Delete DataMover base policy 's3-archive-template'?").
    This removes the template but does NOT affect concrete policies that were created
    from it.

    Arguments:
    - base_policy_id: The name or ID of the base policy to delete (e.g. "s3-archive-template" or "1")

    Use this tool when the user wants to:
    - Remove or delete a base policy template
    - Clean up an old or unused template
    - Remove deprecated policy configurations
    - Decommission policy templates

    Returns:
    - success: Boolean indicating if the base policy was deleted
    - message: Success or error message

    Warning: Ensure no active policies are depending on this base policy before deletion.
    Deleting a base policy that is referenced by existing policies may cause issues.
    """
    cluster = get_cluster(cluster_name)
    datamover = DataMover(cluster)
    return datamover.delete_base_policy(base_policy_id=base_policy_id)
