"""
Phase 1 - Read-Only MCP Tests

Tests read-only operations via the MCP HTTP server.
These tests validate that GET/LIST operations return data in expected format.

Part 1: Config & Capacity (Test infrastructure validation)
Part 2: Snapshots (Pagination, time filtering)
Part 3: FileMgmt (Read operations)
Part 4: DataMover (Read operations)
Part 5: FilePool (Read operations)
Part 6: NFS/SMB Global Settings (Read operations)
Part 7: Management Tools (Tool listing, cluster selection)
"""

import pytest
from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
    validate_items_list, validate_pagination,
    print_test_data
)


# ---------------------------------------------------------------------------
# Part 1: Config & Capacity (Infrastructure Validation)
# ---------------------------------------------------------------------------

class TestConfigTools:
    """Test cluster configuration retrieval."""

    def test_mcp_config(self, mcp_session):
        """powerscale_config returns cluster config and hardware."""
        result = mcp_session("powerscale_config")

        # Verify no errors
        assert_no_error(result, "powerscale_config")
        assert_result_is_dict(result, "powerscale_config")

        # Verify required fields from SDK
        assert "name" in result, "Missing cluster 'name'"
        assert "guid" in result, "Missing cluster 'guid'"
        assert isinstance(result["name"], str), "name must be string"
        assert isinstance(result["guid"], str), "guid must be string"

        # Verify at least one identifying field is present
        assert result.get("name") or result.get("guid"), \
            "Cluster must have name or GUID"

    def test_mcp_config_has_devices(self, mcp_session):
        """powerscale_config includes device/hardware info."""
        result = mcp_session("powerscale_config")

        # Hardware/device info should be present
        has_devices = (
            "devices" in result or
            "hardware" in result or
            "onefs_version" in result
        )
        assert has_devices, \
            f"Config must have device/hardware info. Keys: {list(result.keys())}"


class TestCapacityTools:
    """Test storage capacity retrieval."""

    def test_mcp_capacity(self, mcp_session):
        """powerscale_capacity returns expected capacity stat keys."""
        result = mcp_session("powerscale_capacity")

        # Verify no errors
        assert_no_error(result, "powerscale_capacity")
        assert_result_is_dict(result, "powerscale_capacity")

        # Verify required capacity fields
        expected_keys = [
            "ifs.bytes.avail",
            "ifs.bytes.used",
            "ifs.bytes.total",
        ]
        for key in expected_keys:
            assert key in result, f"Missing capacity key: {key}"

    def test_mcp_capacity_values_valid(self, mcp_session):
        """Capacity values should be positive integers."""
        result = mcp_session("powerscale_capacity")

        # Verify values are valid (convert to int if string)
        avail = int(result.get("ifs.bytes.avail", 0))
        used = int(result.get("ifs.bytes.used", 0))
        total = int(result.get("ifs.bytes.total", 0))

        assert avail > 0, "Available space must be > 0"
        assert used >= 0, "Used space must be >= 0"
        assert total > 0, "Total space must be > 0"
        assert avail + used <= total, \
            "Available + Used should not exceed total"


# ---------------------------------------------------------------------------
# Part 2: Snapshots - Read Operations
# ---------------------------------------------------------------------------

class TestSnapshotReadTools:
    """Test snapshot listing and filtering operations."""

    def test_mcp_snapshot_get(self, mcp_session):
        """powerscale_snapshot_get returns paginated snapshot list."""
        result = mcp_session("powerscale_snapshot_get")

        # Verify structure
        assert_no_error(result, "powerscale_snapshot_get")
        assert_result_is_dict(result, "powerscale_snapshot_get")

        # Verify pagination fields
        items = validate_items_list(result, "powerscale_snapshot_get")
        resume, has_more = validate_pagination(result, "powerscale_snapshot_get")

        # Items should have expected structure
        if items:
            snap = items[0]
            assert isinstance(snap, dict), "Snapshot must be dict"
            assert "name" in snap, "Snapshot must have 'name'"

    def test_mcp_snapshot_schedule_get(self, mcp_session):
        """powerscale_snapshot_schedule_get returns snapshot schedules."""
        result = mcp_session("powerscale_snapshot_schedule_get")

        # Verify structure
        assert_no_error(result, "powerscale_snapshot_schedule_get")
        assert_result_is_dict(result, "powerscale_snapshot_schedule_get")

        # Verify pagination
        items = validate_items_list(result, "powerscale_snapshot_schedule_get")
        resume, has_more = validate_pagination(result, "powerscale_snapshot_schedule_get")

        # Each schedule should have identifying info
        if items:
            sched = items[0]
            assert isinstance(sched, dict), "Schedule must be dict"
            # Schedule may have name, id, or other identifier
            assert len(sched) > 0, "Schedule must have fields"

    def test_mcp_snapshot_pending_get(self, mcp_session):
        """powerscale_snapshot_pending_get returns pending snapshots."""
        result = mcp_session("powerscale_snapshot_pending_get")

        # Verify structure
        assert_no_error(result, "powerscale_snapshot_pending_get")
        assert_result_is_dict(result, "powerscale_snapshot_pending_get")

        # Verify pagination
        items = validate_items_list(result, "powerscale_snapshot_pending_get")
        resume, has_more = validate_pagination(result, "powerscale_snapshot_pending_get")

        # If there are pending snapshots, verify format
        if items:
            snap = items[0]
            assert isinstance(snap, dict), "Pending snapshot must be dict"


# ---------------------------------------------------------------------------
# Part 3: FileMgmt - Read Operations
# ---------------------------------------------------------------------------

class TestFileMgmtReadTools:
    """Test filesystem navigation and attribute retrieval."""

    def test_mcp_directory_list(self, mcp_session):
        """powerscale_directory_list returns directory contents."""
        # List root filesystem
        result = mcp_session("powerscale_directory_list", {"path": "/ifs"})

        # Verify structure
        assert_no_error(result, "powerscale_directory_list")
        assert_result_is_dict(result, "powerscale_directory_list")

        # Directory listing returns "children" (not "items")
        assert "children" in result, \
            f"powerscale_directory_list: Missing 'children' key in {list(result.keys())}"
        assert isinstance(result["children"], list), \
            f"powerscale_directory_list: 'children' must be list"

        children = result["children"]

        # Each child should have name
        if children:
            child = children[0]
            assert isinstance(child, dict), "Child must be dict"
            assert "name" in child, "Child must have 'name'"

    def test_mcp_acl_get(self, mcp_session):
        """powerscale_acl_get returns ACL for a path."""
        # Get ACL for /ifs (should exist)
        result = mcp_session("powerscale_acl_get", {"path": "/ifs"})

        # Verify structure
        assert_no_error(result, "powerscale_acl_get")
        assert_result_is_dict(result, "powerscale_acl_get")

        # ACL should have entries
        assert "acl" in result or "entries" in result or len(result) > 0, \
            "ACL response must have entries"

    def test_mcp_metadata_get(self, mcp_session):
        """powerscale_metadata_get returns metadata for a path."""
        # Get metadata for /ifs
        result = mcp_session("powerscale_metadata_get", {"path": "/ifs"})

        # Verify structure
        assert_no_error(result, "powerscale_metadata_get")
        assert_result_is_dict(result, "powerscale_metadata_get")

    def test_mcp_access_point_list(self, mcp_session):
        """powerscale_access_point_list returns access points."""
        result = mcp_session("powerscale_access_point_list")

        # Verify structure
        assert_no_error(result, "powerscale_access_point_list")
        assert_result_is_dict(result, "powerscale_access_point_list")

        # May be empty or have items
        if "items" in result:
            items = result["items"]
            assert isinstance(items, list), "items must be list"

    def test_mcp_worm_get(self, mcp_session):
        """powerscale_worm_get returns WORM properties for a path."""
        # Get WORM for /ifs
        result = mcp_session("powerscale_worm_get", {"path": "/ifs"})

        # Verify structure
        assert_no_error(result, "powerscale_worm_get")
        assert_result_is_dict(result, "powerscale_worm_get")


# ---------------------------------------------------------------------------
# Part 4: DataMover - Read Operations
# ---------------------------------------------------------------------------

class TestDatamoverReadTools:
    """Test DataMover policy and account querying."""

    def test_mcp_datamover_policy_get(self, mcp_session):
        """powerscale_datamover_policy_get returns policies."""
        result = mcp_session("powerscale_datamover_policy_get")

        # Verify structure
        assert_no_error(result, "powerscale_datamover_policy_get")
        assert_result_is_dict(result, "powerscale_datamover_policy_get")

        # Verify pagination
        items = validate_items_list(result, "powerscale_datamover_policy_get")

        # If policies exist, verify format
        if items:
            policy = items[0]
            assert isinstance(policy, dict), "Policy must be dict"

    def test_mcp_datamover_account_get(self, mcp_session):
        """powerscale_datamover_account_get returns accounts."""
        result = mcp_session("powerscale_datamover_account_get")

        # Verify structure
        assert_no_error(result, "powerscale_datamover_account_get")
        assert_result_is_dict(result, "powerscale_datamover_account_get")

        # Verify pagination
        items = validate_items_list(result, "powerscale_datamover_account_get")

        # If accounts exist, verify format
        if items:
            account = items[0]
            assert isinstance(account, dict), "Account must be dict"

    def test_mcp_datamover_base_policy_get(self, mcp_session):
        """powerscale_datamover_base_policy_get returns base policies."""
        result = mcp_session("powerscale_datamover_base_policy_get")

        # Verify structure
        assert_no_error(result, "powerscale_datamover_base_policy_get")
        assert_result_is_dict(result, "powerscale_datamover_base_policy_get")

        # Verify pagination
        items = validate_items_list(result, "powerscale_datamover_base_policy_get")


# ---------------------------------------------------------------------------
# Part 5: FilePool - Read Operations
# ---------------------------------------------------------------------------

class TestFilePoolReadTools:
    """Test FilePool policy querying."""

    def test_mcp_filepool_policy_get(self, mcp_session):
        """powerscale_filepool_policy_get returns policies."""
        result = mcp_session("powerscale_filepool_policy_get")

        # Verify structure
        assert_no_error(result, "powerscale_filepool_policy_get")
        assert_result_is_dict(result, "powerscale_filepool_policy_get")

        # FilePool uses different pagination (may not have 'items')
        if "items" in result:
            items = result["items"]
            assert isinstance(items, list), "items must be list"

    def test_mcp_filepool_default_policy_get(self, mcp_session):
        """powerscale_filepool_default_policy_get returns default policy."""
        result = mcp_session("powerscale_filepool_default_policy_get")

        # Verify structure
        assert_no_error(result, "powerscale_filepool_default_policy_get")
        assert_result_is_dict(result, "powerscale_filepool_default_policy_get")


# ---------------------------------------------------------------------------
# Part 6: NFS/SMB Global Settings (Read Operations)
# ---------------------------------------------------------------------------

class TestNFSGlobalSettingsTools:
    """Test NFS global settings retrieval."""

    def test_mcp_nfs_global_settings_get(self, mcp_session):
        """powerscale_nfs_global_settings_get returns NFS settings."""
        result = mcp_session("powerscale_nfs_global_settings_get")

        # Verify structure
        assert_no_error(result, "powerscale_nfs_global_settings_get")
        assert_result_is_dict(result, "powerscale_nfs_global_settings_get")

        # Should have some settings
        assert len(result) > 0, "NFS settings should not be empty"


class TestSMBGlobalSettingsTools:
    """Test SMB global settings retrieval."""

    def test_mcp_smb_global_settings_get(self, mcp_session):
        """powerscale_smb_global_settings_get returns SMB settings."""
        result = mcp_session("powerscale_smb_global_settings_get")

        # Verify structure
        assert_no_error(result, "powerscale_smb_global_settings_get")
        assert_result_is_dict(result, "powerscale_smb_global_settings_get")

        # Should have some settings
        assert len(result) > 0, "SMB settings should not be empty"


# ---------------------------------------------------------------------------
# Part 7: Management Tools (Tool Management)
# ---------------------------------------------------------------------------

class TestManagementTools:
    """Test tool management operations."""

    def test_mcp_tools_list(self, mcp_session):
        """powerscale_tools_list returns a flat list of all tools."""
        result = mcp_session("powerscale_tools_list")

        assert_no_error(result, "powerscale_tools_list")
        assert isinstance(result, list), \
            f"powerscale_tools_list: expected list, got {type(result).__name__}"
        assert len(result) > 0, "powerscale_tools_list should return tools"
        # Each entry should have name, group, mode, enabled
        entry = result[0]
        for field in ("name", "group", "mode", "enabled"):
            assert field in entry, \
                f"powerscale_tools_list: missing field '{field}' in entry"

    def test_mcp_tools_list_by_group(self, mcp_session):
        """powerscale_tools_list_by_group returns tools organised by group."""
        result = mcp_session("powerscale_tools_list_by_group")

        assert_no_error(result, "powerscale_tools_list_by_group")
        assert_result_is_dict(result, "powerscale_tools_list_by_group")
        assert "groups" in result, "tools_list_by_group should have 'groups' key"
        assert "total_enabled" in result
        assert isinstance(result["groups"], dict) and len(result["groups"]) > 0

    def test_mcp_tools_list_by_mode(self, mcp_session):
        """powerscale_tools_list_by_mode returns tools grouped into read/write."""
        result = mcp_session("powerscale_tools_list_by_mode")

        assert_no_error(result, "powerscale_tools_list_by_mode")
        assert_result_is_dict(result, "powerscale_tools_list_by_mode")
        assert "by_mode" in result, "tools_list_by_mode should have 'by_mode' key"
        assert "read" in result["by_mode"] and "write" in result["by_mode"]
        assert result["read_count"] > 0 and result["write_count"] > 0

    def test_mcp_cluster_list(self, mcp_session):
        """powerscale_cluster_list returns available clusters."""
        result = mcp_session("powerscale_cluster_list")

        # Verify structure
        assert_no_error(result, "powerscale_cluster_list")
        assert_result_is_dict(result, "powerscale_cluster_list")

        # Should have clusters info
        assert "clusters" in result or "items" in result or len(result) > 0, \
            "cluster_list should return cluster information"
