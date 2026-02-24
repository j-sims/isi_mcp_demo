"""
Phase 2 - Low-Risk Mutation Tests

Tests non-destructive mutating operations that can be safely undone.

Part 2a: Snapshot Aliases (create + verify + cleanup)
Part 2b: Snapshot Create/Delete (Ansible lifecycle)
Part 2c: NFS Global Settings (change + verify + restore)
Part 2d: SMB Global Settings (change + verify + restore)
Part 2e: FilePool Policy (create + verify + delete)

All tests follow these safety rules:
- State captured BEFORE any mutation
- State RESTORED in try/finally to guarantee cleanup
- UUID-based names to prevent conflicts
- Skip gracefully if preconditions are not met
"""

import uuid
import json
import pytest
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException

from modules.onefs.v9_12_0.snapshots import Snapshots
from modules.onefs.v9_12_0.nfs import Nfs
from modules.onefs.v9_12_0.smb import Smb

from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
    validate_items_list, print_test_data
)
from tests.test_phase2_fixtures import (
    capture_nfs_settings,
    capture_smb_settings,
    get_nested_setting,
)


def _unique_name(prefix="test"):
    """Generate a unique resource name with 8-char UUID suffix."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Part 2a: Snapshot Aliases
# ---------------------------------------------------------------------------

class TestSnapshotAliases:
    """
    Test snapshot alias create/get operations.

    Requires at least one existing snapshot on the cluster.
    Aliases are registered for cleanup via the created_snapshot_aliases fixture.
    """

    def test_snapshot_alias_create_via_mcp(
        self, mcp_session, created_snapshot_aliases, test_cluster_direct
    ):
        """powerscale_snapshot_alias_create creates an alias for an existing snapshot."""
        # --- Prerequisites: find an existing snapshot to alias ---
        snaps = Snapshots(test_cluster_direct)
        existing = snaps.get(limit=1)
        if not existing.get("items"):
            pytest.skip("No snapshots available on cluster — cannot create alias")

        snap_name = existing["items"][0]["name"]
        alias_name = _unique_name("alias")

        # Register for cleanup BEFORE creating (in case assertion fails mid-test)
        created_snapshot_aliases.append(alias_name)

        # --- Execute ---
        result = mcp_session("powerscale_snapshot_alias_create", {
            "name": alias_name,
            "target": snap_name,
        })

        # --- Verify ---
        assert_no_error(result, "powerscale_snapshot_alias_create")
        assert_result_is_dict(result, "powerscale_snapshot_alias_create")
        assert result.get("success") is True, \
            f"Expected success=True, got: {result}"

    def test_snapshot_alias_get_via_mcp(
        self, mcp_session, created_snapshot_aliases, test_cluster_direct
    ):
        """powerscale_snapshot_alias_get retrieves an alias by name."""
        # --- Prerequisites: find an existing snapshot ---
        snaps = Snapshots(test_cluster_direct)
        existing = snaps.get(limit=1)
        if not existing.get("items"):
            pytest.skip("No snapshots available on cluster — cannot create alias to retrieve")

        snap_name = existing["items"][0]["name"]
        alias_name = _unique_name("alias")

        # Create alias first
        created_snapshot_aliases.append(alias_name)
        create_result = mcp_session("powerscale_snapshot_alias_create", {
            "name": alias_name,
            "target": snap_name,
        })
        assert create_result.get("success") is True, \
            f"Alias creation failed: {create_result}"

        # --- Execute: retrieve alias ---
        result = mcp_session("powerscale_snapshot_alias_get", {
            "alias_id": alias_name,
        })

        # --- Verify ---
        assert_no_error(result, "powerscale_snapshot_alias_get")
        assert_result_is_dict(result, "powerscale_snapshot_alias_get")
        # Response should have success and alias details
        assert result.get("success") is True, \
            f"Expected success=True, got: {result}"

    def test_snapshot_alias_create_module(
        self, created_snapshot_aliases, test_cluster_direct
    ):
        """Snapshots.create_alias() creates an alias via SDK."""
        # --- Prerequisites ---
        snaps = Snapshots(test_cluster_direct)
        existing = snaps.get(limit=1)
        if not existing.get("items"):
            pytest.skip("No snapshots available — cannot create alias")

        snap_name = existing["items"][0]["name"]
        alias_name = _unique_name("alias")
        created_snapshot_aliases.append(alias_name)

        # --- Execute ---
        result = snaps.create_alias(name=alias_name, target=snap_name)

        # --- Verify ---
        assert isinstance(result, dict), "create_alias() must return dict"
        assert result.get("success") is True, \
            f"create_alias() failed: {result}"
        assert "message" in result, "Result should have message"

    def test_snapshot_alias_get_module(
        self, created_snapshot_aliases, test_cluster_direct
    ):
        """Snapshots.get_alias() retrieves alias details via SDK."""
        # --- Prerequisites ---
        snaps = Snapshots(test_cluster_direct)
        existing = snaps.get(limit=1)
        if not existing.get("items"):
            pytest.skip("No snapshots available — cannot create alias")

        snap_name = existing["items"][0]["name"]
        alias_name = _unique_name("alias")
        created_snapshot_aliases.append(alias_name)

        # Create alias
        create_result = snaps.create_alias(name=alias_name, target=snap_name)
        assert create_result.get("success") is True, \
            f"Alias creation failed: {create_result}"

        # --- Execute: get alias ---
        result = snaps.get_alias(alias_name)

        # --- Verify ---
        assert isinstance(result, dict), "get_alias() must return dict"
        assert result.get("success") is True, \
            f"get_alias() failed: {result}"


# ---------------------------------------------------------------------------
# Part 2b: Snapshot Create / Delete
# ---------------------------------------------------------------------------

class TestSnapshotCreateDelete:
    """
    Test snapshot lifecycle: create via Ansible, verify, delete via Ansible.

    Uses /ifs as the snapshot path (always present).
    Snapshot names are registered for cleanup via created_snapshots fixture.
    """

    def test_snapshot_create_via_mcp(
        self, mcp_session, created_snapshots
    ):
        """powerscale_snapshot_create creates a snapshot of /ifs."""
        snap_name = _unique_name("snap")
        created_snapshots.append(snap_name)

        # --- Execute ---
        # desired_retention is required by dellemc.powerscale.snapshot module
        result = mcp_session("powerscale_snapshot_create", {
            "path": "/ifs",
            "snapshot_name": snap_name,
            "desired_retention": 1,
            "retention_unit": "hours",
        })

        # --- Verify ---
        assert_no_error(result, "powerscale_snapshot_create")
        assert_result_is_dict(result, "powerscale_snapshot_create")
        assert result.get("success") is True, \
            f"Snapshot creation failed: {result}"

    def test_snapshot_delete_via_mcp(
        self, mcp_session, created_snapshots, test_cluster_direct
    ):
        """powerscale_snapshot_delete removes a snapshot."""
        snap_name = _unique_name("snap")
        # Do NOT register for cleanup fixture — we're deleting it ourselves

        # --- Setup: create snapshot first ---
        create_result = mcp_session("powerscale_snapshot_create", {
            "path": "/ifs",
            "snapshot_name": snap_name,
            "desired_retention": 1,
            "retention_unit": "hours",
        })
        assert create_result.get("success") is True, \
            f"Snapshot creation (setup) failed: {create_result}"

        # --- Execute: delete it ---
        result = mcp_session("powerscale_snapshot_delete", {
            "snapshot_name": snap_name,
        })

        # --- Verify ---
        assert_no_error(result, "powerscale_snapshot_delete")
        assert_result_is_dict(result, "powerscale_snapshot_delete")
        assert result.get("success") is True, \
            f"Snapshot deletion failed: {result}"

    def test_snapshot_create_and_verify_via_mcp(
        self, mcp_session, created_snapshots, test_cluster_direct
    ):
        """Create snapshot and verify it appears in the listing."""
        snap_name = _unique_name("snap")
        created_snapshots.append(snap_name)

        # Create
        create_result = mcp_session("powerscale_snapshot_create", {
            "path": "/ifs",
            "snapshot_name": snap_name,
            "desired_retention": 1,
            "retention_unit": "hours",
        })
        assert create_result.get("success") is True, \
            f"Snapshot creation failed: {create_result}"

        # Verify: snapshot appears in list
        snaps = Snapshots(test_cluster_direct)
        all_snaps = snaps.get(limit=1000)
        snap_names = [s.get("name") for s in all_snaps.get("items", [])]
        assert snap_name in snap_names, \
            f"Created snapshot '{snap_name}' not found in listing. Names: {snap_names[:10]}"

    # NOTE: test_snapshot_create_module and test_snapshot_delete_module are
    # intentionally omitted. Snapshots.create/delete use Ansible (dellemc.powerscale
    # collection), which is only installed inside the Docker container, not in the
    # host venv where module tests run. The MCP tests above cover this code path
    # end-to-end via the container.


# ---------------------------------------------------------------------------
# Part 2c: NFS Global Settings
# ---------------------------------------------------------------------------

class TestNFSGlobalSettings:
    """
    Test NFS global settings update with state restore.

    Toggles `rquota_enabled` (a safe, low-impact boolean) and restores
    the original value after the test, even if assertions fail.
    """

    def test_nfs_global_settings_read_module(self, test_cluster_direct):
        """Nfs.get_global_settings() returns non-empty settings dict."""
        nfs = Nfs(test_cluster_direct)
        result = nfs.get_global_settings()

        assert isinstance(result, dict), "get_global_settings() must return dict"
        assert len(result) > 0, "NFS settings must not be empty"
        # No error key
        assert "error" not in result, f"get_global_settings() returned error: {result}"

    def test_nfs_global_settings_set_via_mcp(self, mcp_session, test_cluster_direct):
        """powerscale_nfs_global_settings_set toggles rquota_enabled and restores."""
        nfs = Nfs(test_cluster_direct)
        original = capture_nfs_settings(test_cluster_direct)

        # Find the rquota_enabled field (may be nested under "settings")
        current_rquota = get_nested_setting(original, "rquota_enabled")
        if current_rquota is None:
            pytest.skip("rquota_enabled field not found in NFS settings response")

        new_rquota = not current_rquota

        try:
            # --- Execute: toggle rquota_enabled ---
            result = mcp_session("powerscale_nfs_global_settings_set", {
                "rquota_enabled": new_rquota,
            })

            # --- Verify change ---
            assert_no_error(result, "powerscale_nfs_global_settings_set")
            assert_result_is_dict(result, "powerscale_nfs_global_settings_set")
            assert result.get("success") is True, \
                f"set failed: {result}"

            # Verify settings actually changed
            updated = nfs.get_global_settings()
            updated_rquota = get_nested_setting(updated, "rquota_enabled")
            assert updated_rquota == new_rquota, \
                f"rquota_enabled did not change to {new_rquota}, got: {updated_rquota}"

        finally:
            # --- Restore via MCP (not via module) ---
            # Module Ansible calls require dellemc.powerscale collection which is
            # only installed inside the Docker container, not in the host venv.
            mcp_session("powerscale_nfs_global_settings_set", {
                "rquota_enabled": current_rquota,
            })
            restored = nfs.get_global_settings()
            restored_rquota = get_nested_setting(restored, "rquota_enabled")
            assert restored_rquota == current_rquota, \
                f"CRITICAL: Failed to restore NFS rquota_enabled to {current_rquota}. " \
                f"Current value: {restored_rquota}. Manual restore required!"

    # NOTE: test_nfs_global_settings_set_module is intentionally omitted.
    # Nfs.set_global_settings() uses Ansible (dellemc.powerscale collection),
    # only installed in the Docker container. The MCP test above covers this path.


# ---------------------------------------------------------------------------
# Part 2d: SMB Global Settings
# ---------------------------------------------------------------------------

class TestSMBGlobalSettings:
    """
    Test SMB global settings update with state restore.

    Toggles `dot_snap_visible_root` (a safe display setting that does not
    affect active SMB sessions) and restores the original after the test.
    """

    def test_smb_global_settings_read_module(self, test_cluster_direct):
        """Smb.get_global_settings() returns non-empty settings dict."""
        smb = Smb(test_cluster_direct)
        result = smb.get_global_settings()

        assert isinstance(result, dict), "get_global_settings() must return dict"
        assert len(result) > 0, "SMB settings must not be empty"
        assert "error" not in result, f"get_global_settings() returned error: {result}"

    def test_smb_global_settings_set_via_mcp(self, mcp_session, test_cluster_direct):
        """powerscale_smb_global_settings_set toggles dot_snap_visible_root and restores."""
        smb = Smb(test_cluster_direct)
        original = capture_smb_settings(test_cluster_direct)

        current_dot_snap = get_nested_setting(original, "dot_snap_visible_root")
        if current_dot_snap is None:
            pytest.skip("dot_snap_visible_root field not found in SMB settings response")

        new_dot_snap = not current_dot_snap

        try:
            # --- Execute ---
            result = mcp_session("powerscale_smb_global_settings_set", {
                "dot_snap_visible_root": new_dot_snap,
            })

            # --- Verify ---
            assert_no_error(result, "powerscale_smb_global_settings_set")
            assert_result_is_dict(result, "powerscale_smb_global_settings_set")
            assert result.get("success") is True, \
                f"SMB settings set failed: {result}"

            # Verify change took effect
            updated = smb.get_global_settings()
            updated_dot_snap = get_nested_setting(updated, "dot_snap_visible_root")
            assert updated_dot_snap == new_dot_snap, \
                f"dot_snap_visible_root did not change. Expected {new_dot_snap}, got: {updated_dot_snap}"

        finally:
            # --- Restore via MCP (not via module) ---
            # Module Ansible calls require dellemc.powerscale collection which is
            # only installed inside the Docker container, not in the host venv.
            mcp_session("powerscale_smb_global_settings_set", {
                "dot_snap_visible_root": current_dot_snap,
            })
            restored = smb.get_global_settings()
            restored_dot_snap = get_nested_setting(restored, "dot_snap_visible_root")
            assert restored_dot_snap == current_dot_snap, \
                f"CRITICAL: Failed to restore dot_snap_visible_root. " \
                f"Expected {current_dot_snap}, got: {restored_dot_snap}. Manual restore required!"

    # NOTE: test_smb_global_settings_set_module is intentionally omitted.
    # Smb.set_global_settings() uses Ansible (dellemc.powerscale collection),
    # only installed in the Docker container. The MCP test above covers this path.


# ---------------------------------------------------------------------------
# Part 2e: FilePool Policy Create / Delete
# ---------------------------------------------------------------------------
# NOTE: FilePool policy creation is not supported on this test cluster.
# The dellemc.powerscale.filepoolpolicy Ansible module requires specific
# cluster capabilities (SmartPools license) that are not available here.
# These tests are commented out until a compatible cluster is available.

# class TestFilePoolPolicyLifecycle:
#     """
#     Test FilePool policy create + verify + delete lifecycle.
#
#     FilePool policies are Ansible-based and relatively safe to create/delete.
#     Policy names use UUIDs to avoid conflicts with production policies.
#     """
#
#     def test_filepool_policy_create_via_mcp(...): ...
#     def test_filepool_policy_remove_via_mcp(...): ...
#     def test_filepool_policy_create_and_verify_via_mcp(...): ...
#     def test_filepool_policy_create_module(...): ...
#     def test_filepool_policy_delete_module(...): ...
