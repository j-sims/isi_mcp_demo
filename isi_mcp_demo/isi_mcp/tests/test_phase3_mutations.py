"""
Phase 3 - Medium-Risk Mutation Tests

Tests resource creation and deletion via MCP tools (Ansible-backed operations).
All tests follow these safety rules:
- UUID-based names to prevent naming conflicts
- Create in test body, register for cleanup BEFORE creation call returns
- try/finally where appropriate for inline cleanup
- Verification via direct SDK reads after mutations

Part 3a: Quota Operations (create, remove, set, increment, decrement)
Part 3b: NFS Export Lifecycle (create + verify + remove)
Part 3c: SMB Share Lifecycle (create + verify + remove)
Part 3d: S3 Bucket Lifecycle (create + verify + remove)
Part 3e: SyncIQ Policy Lifecycle (create + verify + remove)
Part 3f: Snapshot Schedule Lifecycle (create + verify + remove)

Note: All Ansible-based creation goes through mcp_session (Docker container).
      Verification reads use direct SDK calls where possible.
"""

import os
import uuid
import pytest
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException

from modules.onefs.v9_12_0.nfs import Nfs
from modules.onefs.v9_12_0.smb import Smb
from modules.onefs.v9_12_0.s3 import S3
from modules.onefs.v9_12_0.synciq import SyncIQ
from modules.onefs.v9_12_0.snapshotschedules import SnapshotSchedules
from modules.onefs.v9_12_0.quotas import Quotas

from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
    validate_items_list,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GiB = 1024 * 1024 * 1024

# SyncIQ self-sync: use the cluster itself as the target (supported by OneFS).
# Source and target must have different paths — source under /ifs/data,
# target under /ifs/synctest (a sibling subtree).
SYNCIQ_SOURCE_PATH = "/ifs/data"
SYNCIQ_TARGET_PATH = "/ifs/synctest"
# Resolved at runtime from environment so tests work against any cluster
_SYNCIQ_TARGET_HOST = os.getenv("TEST_CLUSTER_HOST", "172.16.10.10")


def _unique_name(prefix="test"):
    """Return a name with a unique 8-char hex suffix."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Part 3a: Quota Operations
# ---------------------------------------------------------------------------

class TestQuotaOperations:
    pytestmark = [pytest.mark.func_quotas, pytest.mark.group_quotas, pytest.mark.write]
    """
    Test quota create/remove/set/increment/decrement via MCP.

    Each test that modifies an existing quota (set/increment/decrement)
    first creates a fresh 2 GiB hard quota on its dedicated test directory,
    performs the operation, verifies with the SDK, then removes the quota
    in a try/finally block.

    The `quota_test_directory` fixture provides a freshly-created, empty
    directory under /ifs/data; it is deleted after the test.
    """

    def test_quota_create_via_mcp(
        self, mcp_session, quota_test_directory, test_cluster_direct
    ):
        """powerscale_quota_create creates a 2 GiB hard quota on a test directory."""
        path = quota_test_directory
        quota_api = isi_sdk.QuotaApi(test_cluster_direct.api_client)

        # Pre-check: no quota on the fresh test directory
        pre = quota_api.list_quota_quotas(path=path).quotas or []
        assert len(pre) == 0, f"Expected no pre-existing quota on {path}, found: {pre}"

        # Create quota
        result = mcp_session("powerscale_quota_create", {
            "path": path,
            "quota_type": "hard",
            "limit_size": "2GiB",
        })
        assert_no_error(result, "powerscale_quota_create")
        assert_result_is_dict(result, "powerscale_quota_create")
        assert result.get("success") is True, f"Quota creation failed: {result}"

        # Verify with SDK
        post = quota_api.list_quota_quotas(path=path).quotas or []
        assert len(post) == 1, f"Expected 1 quota after create, found: {len(post)}"
        assert post[0].thresholds.hard == 2 * GiB, (
            f"Expected 2 GiB ({2 * GiB} bytes), got: {post[0].thresholds.hard}"
        )

        # Inline cleanup
        try:
            mcp_session("powerscale_quota_remove", {
                "path": path,
                "quota_type": "hard",
            })
        except Exception as e:
            print(f"\nWarning: Failed to remove test quota on '{path}': {e}")

    def test_quota_remove_via_mcp(
        self, mcp_session, quota_test_directory, test_cluster_direct
    ):
        """powerscale_quota_remove deletes a hard quota and the path has no quota after."""
        path = quota_test_directory
        quota_api = isi_sdk.QuotaApi(test_cluster_direct.api_client)

        # Setup: create 2 GiB quota
        create_result = mcp_session("powerscale_quota_create", {
            "path": path,
            "quota_type": "hard",
            "limit_size": "2GiB",
        })
        assert create_result.get("success") is True, (
            f"Quota creation (setup) failed: {create_result}"
        )
        pre_remove = quota_api.list_quota_quotas(path=path).quotas or []
        assert len(pre_remove) == 1, "Expected 1 quota before remove"

        # Remove
        result = mcp_session("powerscale_quota_remove", {
            "path": path,
            "quota_type": "hard",
        })
        assert_no_error(result, "powerscale_quota_remove")
        assert_result_is_dict(result, "powerscale_quota_remove")
        assert result.get("success") is True, f"Quota remove failed: {result}"

        # Verify removed
        post_remove = quota_api.list_quota_quotas(path=path).quotas or []
        assert len(post_remove) == 0, (
            f"Expected 0 quotas after removal, found: {len(post_remove)}"
        )

    def test_quota_set_via_mcp(
        self, mcp_session, quota_test_directory, test_cluster_direct
    ):
        """powerscale_quota_set changes an existing hard quota to an absolute size."""
        path = quota_test_directory
        quota_api = isi_sdk.QuotaApi(test_cluster_direct.api_client)
        new_size = 3 * GiB

        # Setup: create 2 GiB quota
        create_result = mcp_session("powerscale_quota_create", {
            "path": path,
            "quota_type": "hard",
            "limit_size": "2GiB",
        })
        assert create_result.get("success") is True, (
            f"Quota creation (setup) failed: {create_result}"
        )

        try:
            # Set to 3 GiB (returns a plain string, not JSON dict)
            result = mcp_session("powerscale_quota_set", {
                "path": path,
                "size": new_size,
            })
            assert isinstance(result, str), (
                f"powerscale_quota_set must return a string, got: {type(result)}"
            )
            assert not result.lower().startswith("error"), (
                f"Quota set returned error: {result}"
            )

            # Verify new hard limit via SDK
            quotas = quota_api.list_quota_quotas(path=path).quotas or []
            assert len(quotas) == 1, f"Expected 1 quota, got: {len(quotas)}"
            assert quotas[0].thresholds.hard == new_size, (
                f"Expected {new_size} bytes, got: {quotas[0].thresholds.hard}"
            )
        finally:
            # Cleanup quota
            try:
                mcp_session("powerscale_quota_remove", {
                    "path": path,
                    "quota_type": "hard",
                })
            except Exception as e:
                print(f"\nWarning: Failed to remove quota during cleanup: {e}")

    def test_quota_increment_via_mcp(
        self, mcp_session, quota_test_directory, test_cluster_direct
    ):
        """powerscale_quota_increment increases a hard quota by a delta."""
        path = quota_test_directory
        quota_api = isi_sdk.QuotaApi(test_cluster_direct.api_client)
        delta = 1 * GiB
        expected = 2 * GiB + delta  # 3 GiB

        # Setup: create 2 GiB quota
        create_result = mcp_session("powerscale_quota_create", {
            "path": path,
            "quota_type": "hard",
            "limit_size": "2GiB",
        })
        assert create_result.get("success") is True, (
            f"Quota creation (setup) failed: {create_result}"
        )

        try:
            result = mcp_session("powerscale_quota_increment", {
                "path": path,
                "size": delta,
            })
            assert isinstance(result, str), (
                f"powerscale_quota_increment must return a string"
            )
            assert not result.lower().startswith("error"), (
                f"Quota increment returned error: {result}"
            )

            quotas = quota_api.list_quota_quotas(path=path).quotas or []
            assert len(quotas) == 1
            assert quotas[0].thresholds.hard == expected, (
                f"Expected {expected} bytes after +{delta}, got: {quotas[0].thresholds.hard}"
            )
        finally:
            try:
                mcp_session("powerscale_quota_remove", {
                    "path": path,
                    "quota_type": "hard",
                })
            except Exception as e:
                print(f"\nWarning: Failed to remove quota during cleanup: {e}")

    def test_quota_decrement_via_mcp(
        self, mcp_session, quota_test_directory, test_cluster_direct
    ):
        """powerscale_quota_decrement decreases a hard quota by a delta."""
        path = quota_test_directory
        quota_api = isi_sdk.QuotaApi(test_cluster_direct.api_client)
        delta = 1 * GiB
        expected = 2 * GiB - delta  # 1 GiB (minimum allowed)

        # Setup: create 2 GiB quota
        create_result = mcp_session("powerscale_quota_create", {
            "path": path,
            "quota_type": "hard",
            "limit_size": "2GiB",
        })
        assert create_result.get("success") is True, (
            f"Quota creation (setup) failed: {create_result}"
        )

        try:
            result = mcp_session("powerscale_quota_decrement", {
                "path": path,
                "size": delta,
            })
            assert isinstance(result, str), (
                f"powerscale_quota_decrement must return a string"
            )
            assert not result.lower().startswith("error"), (
                f"Quota decrement returned error: {result}"
            )

            quotas = quota_api.list_quota_quotas(path=path).quotas or []
            assert len(quotas) == 1
            assert quotas[0].thresholds.hard == expected, (
                f"Expected {expected} bytes after -{delta}, got: {quotas[0].thresholds.hard}"
            )
        finally:
            try:
                mcp_session("powerscale_quota_remove", {
                    "path": path,
                    "quota_type": "hard",
                })
            except Exception as e:
                print(f"\nWarning: Failed to remove quota during cleanup: {e}")


# ---------------------------------------------------------------------------
# Part 3b: NFS Export Lifecycle
# ---------------------------------------------------------------------------

class TestNFSExportLifecycle:
    pytestmark = [pytest.mark.func_nfs, pytest.mark.group_nfs, pytest.mark.write]
    """
    Test NFS export create + verify + remove lifecycle via MCP.

    Each test uses a freshly-created unique directory (`nfs_test_directory`
    fixture) as the NFS export path, ensuring isolation between tests.
    Exports are registered in `created_nfs_exports` for SDK-based cleanup.

    Fixture teardown order: `created_nfs_exports` tears down first (removes
    NFS export via SDK), then `nfs_test_directory` tears down (removes dir).
    Ensure `created_nfs_exports` is listed LAST in test parameter lists.
    """

    def test_nfs_create_via_mcp(
        self, mcp_session, nfs_test_directory, test_cluster_direct, created_nfs_exports
    ):
        """powerscale_nfs_create creates an NFS export on a test directory."""
        path = nfs_test_directory
        zone = "System"

        # Register for cleanup before creating (safety first)
        created_nfs_exports.append((path, zone))

        result = mcp_session("powerscale_nfs_create", {
            "path": path,
            "access_zone": zone,
        })
        assert_no_error(result, "powerscale_nfs_create")
        assert_result_is_dict(result, "powerscale_nfs_create")
        assert result.get("success") is True, f"NFS create failed: {result}"

    def test_nfs_create_and_verify_via_mcp(
        self, mcp_session, nfs_test_directory, test_cluster_direct, created_nfs_exports
    ):
        """Create NFS export and verify it appears in the export listing."""
        path = nfs_test_directory
        zone = "System"
        created_nfs_exports.append((path, zone))

        # Create
        create_result = mcp_session("powerscale_nfs_create", {
            "path": path,
            "access_zone": zone,
        })
        assert create_result.get("success") is True, (
            f"NFS create failed: {create_result}"
        )

        # Verify via SDK
        nfs = Nfs(test_cluster_direct)
        all_exports = nfs.get(limit=1000)
        all_paths = [
            p
            for export in all_exports.get("items", [])
            for p in (export.get("paths") or [])
        ]
        assert path in all_paths, (
            f"Created NFS export '{path}' not found in listing. "
            f"Sample paths: {all_paths[:5]}"
        )

    def test_nfs_remove_via_mcp(
        self, mcp_session, nfs_test_directory, test_cluster_direct
    ):
        """Create NFS export and then remove it; verify it's gone."""
        path = nfs_test_directory
        zone = "System"

        # Setup: create export
        create_result = mcp_session("powerscale_nfs_create", {
            "path": path,
            "access_zone": zone,
        })
        assert create_result.get("success") is True, (
            f"NFS create (setup) failed: {create_result}"
        )

        # Remove
        result = mcp_session("powerscale_nfs_remove", {
            "path": path,
            "access_zone": zone,
        })
        assert_no_error(result, "powerscale_nfs_remove")
        assert_result_is_dict(result, "powerscale_nfs_remove")
        assert result.get("success") is True, f"NFS remove failed: {result}"

        # Verify removed via SDK
        nfs = Nfs(test_cluster_direct)
        all_exports = nfs.get(limit=1000)
        all_paths = [
            p
            for export in all_exports.get("items", [])
            for p in (export.get("paths") or [])
        ]
        assert path not in all_paths, (
            f"NFS export '{path}' still present after removal"
        )


# ---------------------------------------------------------------------------
# Part 3c: SMB Share Lifecycle
# ---------------------------------------------------------------------------

class TestSMBShareLifecycle:
    pytestmark = [pytest.mark.func_smb, pytest.mark.group_smb, pytest.mark.write]
    """
    Test SMB share create + verify + remove lifecycle via MCP.

    Uses /ifs/data as the path (always exists on any PowerScale cluster).
    Multiple SMB shares on the same path are allowed as long as share names differ.
    Share names use UUID suffixes to prevent conflicts.
    Shares are registered in `created_smb_shares` for Ansible-based cleanup.
    """

    def test_smb_create_via_mcp(
        self, mcp_session, created_smb_shares
    ):
        """powerscale_smb_create creates an SMB share on /ifs/data."""
        share_name = _unique_name("smb")
        created_smb_shares.append(share_name)

        result = mcp_session("powerscale_smb_create", {
            "share_name": share_name,
            "path": "/ifs/data",
        })
        assert_no_error(result, "powerscale_smb_create")
        assert_result_is_dict(result, "powerscale_smb_create")
        assert result.get("success") is True, f"SMB create failed: {result}"

    def test_smb_create_and_verify_via_mcp(
        self, mcp_session, created_smb_shares, test_cluster_direct
    ):
        """Create SMB share and verify it appears in the share listing."""
        share_name = _unique_name("smb")
        created_smb_shares.append(share_name)

        create_result = mcp_session("powerscale_smb_create", {
            "share_name": share_name,
            "path": "/ifs/data",
        })
        assert create_result.get("success") is True, (
            f"SMB create failed: {create_result}"
        )

        # Verify via SDK
        smb = Smb(test_cluster_direct)
        all_shares = smb.get(limit=1000)
        share_names = [s.get("name") for s in all_shares.get("items", [])]
        assert share_name in share_names, (
            f"Created share '{share_name}' not found in listing. "
            f"Sample names: {share_names[:5]}"
        )

    def test_smb_remove_via_mcp(
        self, mcp_session, test_cluster_direct
    ):
        """Create SMB share and then remove it; verify it's gone."""
        share_name = _unique_name("smb")

        # Setup
        create_result = mcp_session("powerscale_smb_create", {
            "share_name": share_name,
            "path": "/ifs/data",
        })
        assert create_result.get("success") is True, (
            f"SMB create (setup) failed: {create_result}"
        )

        # Remove
        result = mcp_session("powerscale_smb_remove", {
            "share_name": share_name,
        })
        assert_no_error(result, "powerscale_smb_remove")
        assert_result_is_dict(result, "powerscale_smb_remove")
        assert result.get("success") is True, f"SMB remove failed: {result}"

        # Verify removed via SDK
        smb = Smb(test_cluster_direct)
        all_shares = smb.get(limit=1000)
        share_names = [s.get("name") for s in all_shares.get("items", [])]
        assert share_name not in share_names, (
            f"SMB share '{share_name}' still present after removal"
        )


# ---------------------------------------------------------------------------
# Part 3d: S3 Bucket Lifecycle
# ---------------------------------------------------------------------------

class TestS3BucketLifecycle:
    pytestmark = [pytest.mark.func_s3, pytest.mark.group_s3, pytest.mark.write]
    """
    Test S3 bucket create + verify + remove lifecycle via MCP.

    S3 bucket names must be 3-63 chars, lowercase letters/numbers/hyphens.
    Uses /ifs/data as the path. Skips gracefully if S3 is not enabled on
    the cluster.
    """

    @staticmethod
    def _s3_bucket_name():
        """Generate a valid S3 bucket name (lowercase, hyphens, 3-63 chars)."""
        return f"s3bkt-{uuid.uuid4().hex[:8]}"

    def test_s3_create_via_mcp(
        self, mcp_session, created_s3_buckets
    ):
        """powerscale_s3_create creates an S3 bucket with its own unique path."""
        bucket_name = self._s3_bucket_name()
        # Each bucket gets its own path under /ifs/data so there's no
        # conflict with other buckets that already occupy the same path.
        bucket_path = f"/ifs/data/{bucket_name}"
        created_s3_buckets.append(bucket_name)

        result = mcp_session("powerscale_s3_create", {
            "s3_bucket_name": bucket_name,
            "path": bucket_path,
            "create_path": True,
        })
        assert_no_error(result, "powerscale_s3_create")
        assert_result_is_dict(result, "powerscale_s3_create")
        if not result.get("success"):
            # S3 may not be licensed/enabled on this cluster
            err = str(result).lower()
            if any(kw in err for kw in ("license", "not enabled", "service", "disabled")):
                pytest.skip(f"S3 not available on this cluster: {result}")
        assert result.get("success") is True, f"S3 create failed: {result}"

    def test_s3_create_and_verify_via_mcp(
        self, mcp_session, created_s3_buckets, test_cluster_direct
    ):
        """Create S3 bucket and verify it appears in the bucket listing."""
        bucket_name = self._s3_bucket_name()
        bucket_path = f"/ifs/data/{bucket_name}"
        created_s3_buckets.append(bucket_name)

        create_result = mcp_session("powerscale_s3_create", {
            "s3_bucket_name": bucket_name,
            "path": bucket_path,
            "create_path": True,
        })
        if not create_result.get("success"):
            err = str(create_result).lower()
            if any(kw in err for kw in ("license", "not enabled", "service", "disabled")):
                pytest.skip(f"S3 not available on this cluster: {create_result}")
        assert create_result.get("success") is True, (
            f"S3 create failed: {create_result}"
        )

        # Verify via SDK
        s3 = S3(test_cluster_direct)
        all_buckets = s3.get(limit=1000)
        bucket_names = [b.get("name") for b in all_buckets.get("items", [])]
        assert bucket_name in bucket_names, (
            f"Created bucket '{bucket_name}' not found in listing. "
            f"Sample names: {bucket_names[:5]}"
        )

    def test_s3_remove_via_mcp(
        self, mcp_session, test_cluster_direct
    ):
        """Create S3 bucket and then remove it; verify it's gone."""
        bucket_name = self._s3_bucket_name()
        bucket_path = f"/ifs/data/{bucket_name}"

        # Setup
        create_result = mcp_session("powerscale_s3_create", {
            "s3_bucket_name": bucket_name,
            "path": bucket_path,
            "create_path": True,
        })
        if not create_result.get("success"):
            err = str(create_result).lower()
            if any(kw in err for kw in ("license", "not enabled", "service", "disabled")):
                pytest.skip(f"S3 not available on this cluster: {create_result}")
        assert create_result.get("success") is True, (
            f"S3 create (setup) failed: {create_result}"
        )

        # Remove
        result = mcp_session("powerscale_s3_remove", {
            "s3_bucket_name": bucket_name,
        })
        assert_no_error(result, "powerscale_s3_remove")
        assert_result_is_dict(result, "powerscale_s3_remove")
        assert result.get("success") is True, f"S3 remove failed: {result}"

        # Verify removed via SDK
        s3 = S3(test_cluster_direct)
        all_buckets = s3.get(limit=1000)
        bucket_names = [b.get("name") for b in all_buckets.get("items", [])]
        assert bucket_name not in bucket_names, (
            f"S3 bucket '{bucket_name}' still present after removal"
        )


# ---------------------------------------------------------------------------
# Part 3e: SyncIQ Policy Lifecycle
# ---------------------------------------------------------------------------

class TestSyncIQPolicyLifecycle:
    pytestmark = [pytest.mark.func_synciq, pytest.mark.group_synciq, pytest.mark.write]
    """
    Test SyncIQ policy create + verify + remove lifecycle via MCP.

    Uses the cluster itself as both source and target (self-sync), which
    OneFS supports as long as the source and target paths differ.
    - Source: /ifs/data
    - Target host: the cluster's own management IP
    - Target path: /ifs/synctest  (a sibling tree, not under /ifs/data)

    SyncIQ policies are just configuration; the policy is created here but
    never triggered to run. Skips gracefully if SyncIQ is not licensed.
    """

    @staticmethod
    def _synciq_args(policy_name: str) -> dict:
        return {
            "policy_name": policy_name,
            "source_path": SYNCIQ_SOURCE_PATH,
            "target_host": _SYNCIQ_TARGET_HOST,
            "target_path": SYNCIQ_TARGET_PATH,
        }

    def test_synciq_create_via_mcp(
        self, mcp_session, synciq_available, created_synciq_policies
    ):
        """powerscale_synciq_create creates a SyncIQ self-sync policy."""
        policy_name = _unique_name("synciq")
        created_synciq_policies.append(policy_name)

        result = mcp_session("powerscale_synciq_create", self._synciq_args(policy_name))
        assert_no_error(result, "powerscale_synciq_create")
        assert_result_is_dict(result, "powerscale_synciq_create")
        assert result.get("success") is True, f"SyncIQ create failed: {result}"

    def test_synciq_create_and_verify_via_mcp(
        self, mcp_session, synciq_available, created_synciq_policies, test_cluster_direct
    ):
        """Create SyncIQ policy and verify it appears in the policy listing."""
        policy_name = _unique_name("synciq")
        created_synciq_policies.append(policy_name)

        create_result = mcp_session("powerscale_synciq_create", self._synciq_args(policy_name))
        assert create_result.get("success") is True, (
            f"SyncIQ create failed: {create_result}"
        )

        # Verify via SDK
        synciq = SyncIQ(test_cluster_direct)
        all_policies = synciq.get()
        policy_names = [p.get("name") for p in all_policies.get("items", [])]
        assert policy_name in policy_names, (
            f"Created policy '{policy_name}' not found in listing. "
            f"Sample names: {policy_names[:5]}"
        )

    def test_synciq_remove_via_mcp(
        self, mcp_session, synciq_available, test_cluster_direct
    ):
        """Create SyncIQ policy and then remove it; verify it's gone."""
        policy_name = _unique_name("synciq")

        # Setup
        create_result = mcp_session("powerscale_synciq_create", self._synciq_args(policy_name))
        assert create_result.get("success") is True, (
            f"SyncIQ create (setup) failed: {create_result}"
        )

        # Remove
        result = mcp_session("powerscale_synciq_remove", {
            "policy_name": policy_name,
        })
        assert_no_error(result, "powerscale_synciq_remove")
        assert_result_is_dict(result, "powerscale_synciq_remove")
        assert result.get("success") is True, f"SyncIQ remove failed: {result}"

        # Verify removed via SDK
        synciq = SyncIQ(test_cluster_direct)
        all_policies = synciq.get()
        policy_names = [p.get("name") for p in all_policies.get("items", [])]
        assert policy_name not in policy_names, (
            f"SyncIQ policy '{policy_name}' still present after removal"
        )


# ---------------------------------------------------------------------------
# Part 3f: Snapshot Schedule Lifecycle
# ---------------------------------------------------------------------------

class TestSnapshotScheduleLifecycle:
    pytestmark = [pytest.mark.func_snapshots, pytest.mark.group_snapshots, pytest.mark.write]
    """
    Test snapshot schedule create + verify + remove lifecycle via MCP.

    Uses /ifs/data as the snapshot path (always exists).
    Schedule uses a simple daily isidate string.
    """

    def test_snapshot_schedule_create_via_mcp(
        self, mcp_session, created_snapshot_schedules
    ):
        """powerscale_snapshot_schedule_create creates a snapshot schedule."""
        schedule_name = _unique_name("sched")
        created_snapshot_schedules.append(schedule_name)

        result = mcp_session("powerscale_snapshot_schedule_create", {
            "name": schedule_name,
            "path": "/ifs/data",
            "schedule": "Every day at 12:00 AM",
        })
        assert_no_error(result, "powerscale_snapshot_schedule_create")
        assert_result_is_dict(result, "powerscale_snapshot_schedule_create")
        assert result.get("success") is True, (
            f"Snapshot schedule create failed: {result}"
        )

    def test_snapshot_schedule_create_and_verify_via_mcp(
        self, mcp_session, created_snapshot_schedules, test_cluster_direct
    ):
        """Create snapshot schedule and verify it appears in the schedule listing."""
        schedule_name = _unique_name("sched")
        created_snapshot_schedules.append(schedule_name)

        create_result = mcp_session("powerscale_snapshot_schedule_create", {
            "name": schedule_name,
            "path": "/ifs/data",
            "schedule": "Every day at 12:00 AM",
        })
        assert create_result.get("success") is True, (
            f"Snapshot schedule create failed: {create_result}"
        )

        # Verify via SDK
        schedules = SnapshotSchedules(test_cluster_direct)
        all_schedules = schedules.get(limit=1000)
        schedule_names = [s.get("name") for s in all_schedules.get("items", [])]
        assert schedule_name in schedule_names, (
            f"Created schedule '{schedule_name}' not found in listing. "
            f"Sample names: {schedule_names[:5]}"
        )

    def test_snapshot_schedule_remove_via_mcp(
        self, mcp_session, test_cluster_direct
    ):
        """Create snapshot schedule and then remove it; verify it's gone."""
        schedule_name = _unique_name("sched")

        # Setup
        create_result = mcp_session("powerscale_snapshot_schedule_create", {
            "name": schedule_name,
            "path": "/ifs/data",
            "schedule": "Every day at 12:00 AM",
        })
        assert create_result.get("success") is True, (
            f"Snapshot schedule create (setup) failed: {create_result}"
        )

        # Remove
        result = mcp_session("powerscale_snapshot_schedule_remove", {
            "name": schedule_name,
        })
        assert_no_error(result, "powerscale_snapshot_schedule_remove")
        assert_result_is_dict(result, "powerscale_snapshot_schedule_remove")
        assert result.get("success") is True, (
            f"Snapshot schedule remove failed: {result}"
        )

        # Verify removed via SDK
        schedules = SnapshotSchedules(test_cluster_direct)
        all_schedules = schedules.get(limit=1000)
        schedule_names = [s.get("name") for s in all_schedules.get("items", [])]
        assert schedule_name not in schedule_names, (
            f"Snapshot schedule '{schedule_name}' still present after removal"
        )
