"""
Phase 3 - Cleanup Fixtures and Utilities

Provides pytest fixtures for managing resources created during Phase 3
medium-risk mutation tests.

Resources tracked and cleaned up:
- NFS exports (by path + zone, deleted via SDK by export ID)
- SMB shares (by share name, deleted via Ansible module)
- S3 buckets (by bucket name, deleted via Ansible module)
- SyncIQ policies (by policy name, deleted via Ansible module)
- Snapshot schedules (by schedule name, deleted via Ansible module)
- Test directories (by path, deleted via SDK — used by quota and NFS tests)

Usage in tests:
    def test_something(self, mcp_session, created_smb_shares, test_cluster_direct):
        share_name = "test_share_abc12345"
        created_smb_shares.append(share_name)  # Register for cleanup
        result = mcp_session("powerscale_smb_create", {...})
        # Cleanup happens automatically after the test
"""

import uuid
import pytest
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException

from modules.onefs.v9_12_0.smb import Smb
from modules.onefs.v9_12_0.s3 import S3
from modules.onefs.v9_12_0.snapshotschedules import SnapshotSchedules
from modules.onefs.v9_12_0.filemgmt import FileMgmt


def _unique_name(prefix="test"):
    """Generate a unique resource name with 8-char UUID hex suffix."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Test Directory Fixture (for quota and NFS tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def quota_test_directory(mcp_session):
    """
    Create a unique empty directory under /ifs/data for quota tests.

    Yields the full path (e.g., /ifs/data/test_quota_abc12345).
    Deletes the directory via MCP after the test, regardless of quota state.
    """
    dir_suffix = uuid.uuid4().hex[:8]
    api_path = f"ifs/data/test_quota_{dir_suffix}"   # no leading slash for MCP
    full_path = f"/{api_path}"                        # with leading slash for SDK/quotas

    # Create directory via MCP
    try:
        result = mcp_session("powerscale_directory_create", {
            "path": api_path,
            "recursive": True,
        })
        if not result.get("success"):
            pytest.skip(f"Could not create quota test directory: {result}")
    except AssertionError as e:
        pytest.skip(f"powerscale_directory_create not available: {e}")

    yield full_path

    # Cleanup: delete directory (quota should already be removed by test)
    try:
        mcp_session("powerscale_directory_delete", {
            "path": api_path,
            "recursive": True,
        })
        print(f"\nCleaned up quota test dir: {full_path}")
    except Exception as e:
        print(f"\nWarning: Failed to cleanup quota test dir '{full_path}': {e}")


@pytest.fixture
def nfs_test_directory(mcp_session):
    """
    Create a unique empty directory under /ifs/data for NFS export tests.

    Yields the full path (e.g., /ifs/data/test_nfs_abc12345).
    Deletes the directory via MCP after the test. NFS export cleanup should
    happen before directory cleanup — ensure `created_nfs_exports` is listed
    AFTER this fixture in test parameter lists so it tears down first.
    """
    dir_suffix = uuid.uuid4().hex[:8]
    api_path = f"ifs/data/test_nfs_{dir_suffix}"   # no leading slash for MCP
    full_path = f"/{api_path}"                      # with leading slash for NFS

    # Create directory via MCP
    try:
        result = mcp_session("powerscale_directory_create", {
            "path": api_path,
            "recursive": True,
        })
        if not result.get("success"):
            pytest.skip(f"Could not create NFS test directory: {result}")
    except AssertionError as e:
        pytest.skip(f"powerscale_directory_create not available: {e}")

    yield full_path

    # Cleanup: delete directory
    try:
        mcp_session("powerscale_directory_delete", {
            "path": api_path,
            "recursive": True,
        })
        print(f"\nCleaned up NFS test dir: {full_path}")
    except Exception as e:
        print(f"\nWarning: Failed to cleanup NFS test dir '{full_path}': {e}")


# ---------------------------------------------------------------------------
# NFS Export Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_nfs_exports(test_cluster_direct):
    """
    Track and cleanup NFS exports created during tests.

    Tests append (path, access_zone) tuples to the returned list.
    Cleanup uses the SDK directly (by export ID) to avoid needing Ansible
    on the host.

    Usage:
        def test_nfs(self, mcp_session, nfs_test_directory, created_nfs_exports):
            created_nfs_exports.append((nfs_test_directory, "System"))
            result = mcp_session("powerscale_nfs_create", {...})
    """
    exports = []  # list of (path, access_zone) tuples
    yield exports

    if not exports:
        return

    protocols_api = isi_sdk.ProtocolsApi(test_cluster_direct.api_client)
    for path, zone in exports:
        try:
            # Find the export by path (client-side filter)
            result = protocols_api.list_nfs_exports(zone=zone)
            for export in result.exports or []:
                if path in (export.paths or []):
                    protocols_api.delete_nfs_export(export.id, zone=zone)
                    print(f"\nCleaned up NFS export: {path} (ID: {export.id})")
        except ApiException as e:
            print(f"\nWarning: Failed to cleanup NFS export '{path}': {e}")
        except Exception as e:
            print(f"\nWarning: Unexpected error cleaning up NFS export '{path}': {e}")


# ---------------------------------------------------------------------------
# SMB Share Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_smb_shares(test_cluster_direct):
    """
    Track and cleanup SMB shares created during tests.

    Tests append share names to the returned list.
    Cleanup calls Smb.remove() (Ansible-based) — may fail on host venv if
    the dellemc.powerscale collection is not installed there, but that is
    handled gracefully with a warning.

    Usage:
        def test_smb(self, mcp_session, created_smb_shares):
            created_smb_shares.append("test_share_abc12345")
            result = mcp_session("powerscale_smb_create", {...})
    """
    share_names = []
    yield share_names

    if not share_names:
        return

    smb = Smb(test_cluster_direct)
    for share_name in share_names:
        try:
            result = smb.remove(share_name=share_name)
            if result.get("success"):
                print(f"\nCleaned up SMB share: {share_name}")
            else:
                print(f"\nWarning: SMB share removal may have failed for '{share_name}': {result}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup SMB share '{share_name}': {e}")


# ---------------------------------------------------------------------------
# S3 Bucket Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_s3_buckets(test_cluster_direct):
    """
    Track and cleanup S3 buckets created during tests.

    Tests append bucket names to the returned list.
    Cleanup calls S3.remove() (Ansible-based) — may fail on host venv if
    the collection is not installed.

    Usage:
        def test_s3(self, mcp_session, created_s3_buckets):
            created_s3_buckets.append("s3bkt-abc12345")
            result = mcp_session("powerscale_s3_create", {...})
    """
    bucket_names = []
    yield bucket_names

    if not bucket_names:
        return

    s3 = S3(test_cluster_direct)
    for bucket_name in bucket_names:
        try:
            result = s3.remove(s3_bucket_name=bucket_name)
            if result.get("success"):
                print(f"\nCleaned up S3 bucket: {bucket_name}")
            else:
                print(f"\nWarning: S3 bucket removal may have failed for '{bucket_name}': {result}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup S3 bucket '{bucket_name}': {e}")


# ---------------------------------------------------------------------------
# SyncIQ Policy Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_synciq_policies(mcp_session):
    """
    Track and cleanup SyncIQ policies created during tests.

    Tests append policy names to the returned list.
    Cleanup calls powerscale_synciq_remove via MCP (routes through Docker container
    where the dellemc.powerscale Ansible collection is installed).

    Usage:
        def test_synciq(self, mcp_session, created_synciq_policies):
            created_synciq_policies.append("test_policy_abc12345")
            result = mcp_session("powerscale_synciq_create", {...})
    """
    policy_names = []
    yield policy_names

    if not policy_names:
        return

    for policy_name in policy_names:
        try:
            result = mcp_session("powerscale_synciq_remove", {"policy_name": policy_name})
            if isinstance(result, dict) and result.get("success"):
                print(f"\nCleaned up SyncIQ policy: {policy_name}")
            else:
                print(f"\nWarning: SyncIQ policy removal may have failed for '{policy_name}': {result}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup SyncIQ policy '{policy_name}': {e}")


# ---------------------------------------------------------------------------
# Snapshot Schedule Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_snapshot_schedules(test_cluster_direct):
    """
    Track and cleanup snapshot schedules created during tests.

    Tests append schedule names to the returned list.
    Cleanup calls SnapshotSchedules.remove() (Ansible-based).

    Usage:
        def test_schedule(self, mcp_session, created_snapshot_schedules):
            created_snapshot_schedules.append("test_sched_abc12345")
            result = mcp_session("powerscale_snapshot_schedule_create", {...})
    """
    schedule_names = []
    yield schedule_names

    if not schedule_names:
        return

    schedules = SnapshotSchedules(test_cluster_direct)
    for name in schedule_names:
        try:
            result = schedules.remove(name=name)
            if result.get("success"):
                print(f"\nCleaned up snapshot schedule: {name}")
            else:
                print(f"\nWarning: Snapshot schedule removal may have failed for '{name}': {result}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup snapshot schedule '{name}': {e}")
