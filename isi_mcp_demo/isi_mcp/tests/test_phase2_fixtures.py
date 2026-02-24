"""
Phase 2 - Cleanup Fixtures and Utilities

Provides pytest fixtures for managing and restoring state for test resources
created during Phase 2 low-risk mutation tests.

Usage in tests:
    def test_something(self, mcp_session, created_snapshot_aliases, test_cluster_direct):
        alias_name = "test_alias_abc12345"
        # ... create alias ...
        created_snapshot_aliases.append(alias_name)  # Register for cleanup
        # ... test assertions ...
        # Cleanup happens automatically after the test
"""

import pytest
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException

from modules.onefs.v9_12_0.snapshots import Snapshots
from modules.onefs.v9_12_0.nfs import Nfs
from modules.onefs.v9_12_0.smb import Smb
from modules.onefs.v9_12_0.filepool import FilePool


# ---------------------------------------------------------------------------
# Snapshot Alias Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_snapshot_aliases(test_cluster_direct):
    """
    Track and cleanup snapshot aliases created during tests.

    Tests append alias names to the returned list; cleanup deletes them all
    via the SDK after the test completes.

    Usage:
        def test_alias(self, mcp_session, created_snapshot_aliases):
            created_snapshot_aliases.append("my_alias")
            result = mcp_session("powerscale_snapshot_alias_create", {...})
    """
    aliases = []  # List of alias names to cleanup
    yield aliases

    # Cleanup phase
    if not aliases:
        return

    snapshot_api = isi_sdk.SnapshotApi(test_cluster_direct.api_client)
    for alias_name in aliases:
        try:
            snapshot_api.delete_snapshot_alias(alias_name)
            print(f"\nCleaned up snapshot alias: {alias_name}")
        except ApiException as e:
            print(f"\nWarning: Failed to cleanup alias '{alias_name}': {e}")
        except Exception as e:
            print(f"\nWarning: Unexpected error cleaning up alias '{alias_name}': {e}")


# ---------------------------------------------------------------------------
# Snapshot Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_snapshots(test_cluster_direct):
    """
    Track and cleanup snapshots created during tests.

    Tests append snapshot names to the returned list; cleanup deletes them
    all via Ansible after the test completes.

    Usage:
        def test_snap(self, mcp_session, created_snapshots):
            created_snapshots.append("my_snapshot")
            result = mcp_session("powerscale_snapshot_create", {...})
    """
    snapshot_names = []
    yield snapshot_names

    # Cleanup phase
    if not snapshot_names:
        return

    snapshots_mod = Snapshots(test_cluster_direct)
    for snap_name in snapshot_names:
        try:
            result = snapshots_mod.delete(snap_name)
            if result.get("success"):
                print(f"\nCleaned up snapshot: {snap_name}")
            else:
                print(f"\nWarning: Snapshot delete may have failed for '{snap_name}': {result}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup snapshot '{snap_name}': {e}")


# ---------------------------------------------------------------------------
# FilePool Policy Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_filepool_policies(test_cluster_direct):
    """
    Track and cleanup FilePool policies created during tests.

    Tests append policy names to the returned list; cleanup removes them
    all via Ansible after the test completes.

    Usage:
        def test_policy(self, mcp_session, created_filepool_policies):
            created_filepool_policies.append("my_policy")
            result = mcp_session("powerscale_filepool_policy_create", {...})
    """
    policy_names = []
    yield policy_names

    # Cleanup phase
    if not policy_names:
        return

    fp = FilePool(test_cluster_direct)
    for policy_name in policy_names:
        try:
            result = fp.delete(policy_name)
            if result.get("success"):
                print(f"\nCleaned up FilePool policy: {policy_name}")
            else:
                print(f"\nWarning: FilePool policy delete may have failed for '{policy_name}': {result}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup FilePool policy '{policy_name}': {e}")


# ---------------------------------------------------------------------------
# Global Settings State Capture Helpers
# ---------------------------------------------------------------------------

def capture_nfs_settings(cluster) -> dict:
    """
    Capture current NFS global settings for later restore.

    Returns the full settings dict from Nfs.get_global_settings().
    """
    nfs = Nfs(cluster)
    return nfs.get_global_settings()


def restore_nfs_settings(cluster, original_settings: dict) -> dict:
    """
    Restore NFS global settings to a previously captured state.

    Only restores the `rquota_enabled` and `service` fields, which are
    the settings mutated in Phase 2 tests. Skips fields not present.

    Returns the result of Nfs.set_global_settings() or success dict.
    """
    nfs = Nfs(cluster)

    # Extract settings from nested structure if present
    settings = original_settings.get("settings", original_settings)

    restore_kwargs = {}
    if "rquota_enabled" in settings:
        restore_kwargs["rquota_enabled"] = settings["rquota_enabled"]
    if "service" in settings:
        restore_kwargs["service"] = settings["service"]

    if not restore_kwargs:
        return {"success": True, "message": "No NFS settings to restore"}

    return nfs.set_global_settings(**restore_kwargs)


def capture_smb_settings(cluster) -> dict:
    """
    Capture current SMB global settings for later restore.

    Returns the full settings dict from Smb.get_global_settings().
    """
    smb = Smb(cluster)
    return smb.get_global_settings()


def restore_smb_settings(cluster, original_settings: dict) -> dict:
    """
    Restore SMB global settings to a previously captured state.

    Only restores the `dot_snap_visible_root` and `service` fields, which are
    the settings mutated in Phase 2 tests. Skips fields not present.

    Returns the result of Smb.set_global_settings() or success dict.
    """
    smb = Smb(cluster)

    # Extract settings from nested structure if present
    settings = original_settings.get("settings", original_settings)

    restore_kwargs = {}
    if "dot_snap_visible_root" in settings:
        restore_kwargs["dot_snap_visible_root"] = settings["dot_snap_visible_root"]
    if "service" in settings:
        restore_kwargs["service"] = settings["service"]

    if not restore_kwargs:
        return {"success": True, "message": "No SMB settings to restore"}

    return smb.set_global_settings(**restore_kwargs)


def get_nested_setting(settings_dict: dict, key: str):
    """
    Extract a setting value from either a flat or nested dict.

    Handles both:
        {"rquota_enabled": True, ...}    (flat)
        {"settings": {"rquota_enabled": True, ...}}  (nested)

    Returns the value or None if not found.
    """
    if "settings" in settings_dict and isinstance(settings_dict["settings"], dict):
        return settings_dict["settings"].get(key)
    return settings_dict.get(key)
