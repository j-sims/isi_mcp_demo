from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.s3 import S3
from modules.utils.paging import normalize_resume, paginated_result
from typing import Dict, Any, Optional


@safe_tool(group="s3", mode="read")
def powerscale_s3_get(
    limit: int = 1000,
    resume: Optional[str] = None,
    cluster_name: str = None,
    ) -> Dict[str, Any]:
    """
    Returns S3 buckets on the PowerScale cluster using pagination.

    PowerScale supports an S3-compatible object storage interface. Each bucket
    maps to a directory on the cluster filesystem and provides S3 API access.

    Usage:
    - First call: resume=None
    - If "resume" is returned in the response, call again with that value
    - Continue until "resume" is None
    - Do not call repeatedly with the same resume value

    Arguments:
    - limit: Maximum number of buckets per page
    - resume: Resume token from a previous call (or None for first call)

    Each bucket object includes details such as:
    - name: The bucket name (used in S3 API requests)
    - id: Unique bucket identifier
    - path: The filesystem path the bucket maps to
    - owner: The bucket owner
    - description: Human-readable description
    - create_path: Whether to create the path if it does not exist
    - acl: Access control list defining permissions
    - object_acl_policy: Policy for object-level ACLs
    - zone: The access zone the bucket belongs to

    Use this tool to answer questions about S3 buckets such as:
    - What S3 buckets are configured on the cluster?
    - Which filesystem paths are exposed as S3 buckets?
    - Who owns a specific bucket?
    - What access zones have S3 buckets?
    - What are the ACL settings for a bucket?

    Returns:
    - items: List of S3 bucket objects for this page
    - resume: Resume token for the next page, or None if finished
    - has_more: True if more pages exist
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    return paginated_result(S3(cluster).get(limit=limit, resume=resume), limit)

@safe_tool(group="s3", mode="write")
def powerscale_s3_create(s3_bucket_name: str, path: str, owner: str = "root",
                         description: str = None, create_path: bool = None,
                         cluster_name: str = None) -> dict:
    """
    Create an S3 bucket on the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that creates a new S3 bucket on the
    live cluster. Always confirm the bucket name, path, and owner with the user
    before calling this tool (e.g. "Create S3 bucket 'data-lake' at
    /ifs/data/s3/data-lake owned by root?").

    This tool uses Ansible automation to create the bucket via the
    dellemc.powerscale collection.

    Arguments:
    - s3_bucket_name: The name for the S3 bucket (e.g. "data-lake")
    - path: The filesystem path the bucket maps to (e.g. "/ifs/data/s3/data-lake")
    - owner: The bucket owner (default: "root")
    - description: Optional human-readable description
    - create_path: If True, create the filesystem path if it does not exist

    Use this tool when the user wants to:
    - Create a new S3 bucket on PowerScale
    - Enable S3 object access to a filesystem path
    - Set up S3-compatible storage

    Returns:
    - success: Boolean indicating if the bucket was created
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    cluster = get_cluster(cluster_name)
    s3 = S3(cluster)
    return s3.add(s3_bucket_name=s3_bucket_name, path=path, owner=owner,
                  description=description, create_path=create_path)

@safe_tool(group="s3", mode="write")
def powerscale_s3_remove(s3_bucket_name: str, cluster_name: str = None) -> dict:
    """
    Remove an S3 bucket from the PowerScale cluster.

    IMPORTANT: This is a MUTATING operation that removes an S3 bucket from the
    live cluster. Always confirm the bucket name with the user before calling
    this tool (e.g. "Remove S3 bucket 'data-lake'?"). This does NOT delete the
    underlying data on the filesystem — it only removes the bucket definition.

    Arguments:
    - s3_bucket_name: The name of the S3 bucket to remove (e.g. "data-lake")

    Use this tool when the user wants to:
    - Remove or delete an S3 bucket
    - Disable S3 access to a filesystem path
    - Clean up unused S3 buckets

    Returns:
    - success: Boolean indicating if the bucket was removed
    - status: Ansible execution status ("successful" or "failed")
    - playbook_path: Path to the executed playbook (for audit)
    """
    cluster = get_cluster(cluster_name)
    s3 = S3(cluster)
    return s3.remove(s3_bucket_name=s3_bucket_name)
