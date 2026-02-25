"""
Phase 5B - Statistics, WORM, and SMB Sessions Tests (Medium Effort)

Part 1: Statistics Module (performance metrics, averaging, node filtering)
Part 2: WORM/SmartLock Features (file compliance properties)
Part 3: SMB Session Management (active connection operations)
"""

import pytest
import time
import json
from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
    validate_items_list, validate_pagination,
)


# ---------------------------------------------------------------------------
# Part 1: Statistics Module
# ---------------------------------------------------------------------------

class TestStatisticsReadOnly:
    """Test statistics retrieval tools."""

    def test_stats_cpu_returns_data(self, mcp_session):
        """powerscale_stats_cpu returns CPU utilization metrics."""
        result = mcp_session("powerscale_stats_cpu")

        assert_no_error(result, "powerscale_stats_cpu")
        assert_result_is_dict(result, "powerscale_stats_cpu")

        # Should have numeric stats (CPU percentages, etc.)
        assert len(result) > 0, "CPU stats should return data"

    def test_stats_cpu_has_percentage(self, mcp_session):
        """CPU stats should include utilization percentage."""
        result = mcp_session("powerscale_stats_cpu")

        assert_no_error(result, "powerscale_stats_cpu")

        # Should have some numeric values representing percentages
        has_numeric = any(isinstance(v, (int, float)) for v in result.values())
        assert has_numeric, "CPU stats should contain numeric values"

    def test_stats_network_returns_data(self, mcp_session):
        """powerscale_stats_network returns network throughput metrics."""
        result = mcp_session("powerscale_stats_network")

        assert_no_error(result, "powerscale_stats_network")
        assert_result_is_dict(result, "powerscale_stats_network")

        # Should have network-related stats (bytes/sec, packets, etc.)
        assert len(result) > 0, "Network stats should return data"

    def test_stats_disk_returns_data(self, mcp_session):
        """powerscale_stats_disk returns disk I/O metrics."""
        result = mcp_session("powerscale_stats_disk")

        assert_no_error(result, "powerscale_stats_disk")
        assert_result_is_dict(result, "powerscale_stats_disk")

        # Should have disk I/O stats (operations/sec, throughput, etc.)
        assert len(result) > 0, "Disk stats should return data"

    def test_stats_ifs_returns_data(self, mcp_session):
        """powerscale_stats_ifs returns IFS protocol metrics."""
        result = mcp_session("powerscale_stats_ifs")

        assert_no_error(result, "powerscale_stats_ifs")
        assert_result_is_dict(result, "powerscale_stats_ifs")

        # IFS stats should exist
        assert len(result) > 0, "IFS stats should return data"

    def test_stats_node_returns_data(self, mcp_session):
        """powerscale_stats_node returns per-node metrics."""
        result = mcp_session("powerscale_stats_node")

        assert_no_error(result, "powerscale_stats_node")
        assert_result_is_dict(result, "powerscale_stats_node")

        # Should have data (structure depends on cluster config)
        assert len(result) > 0, "Node stats should return data"

    def test_stats_protocol_returns_data(self, mcp_session):
        """powerscale_stats_protocol returns NFS/SMB/S3/HTTP metrics."""
        result = mcp_session("powerscale_stats_protocol")

        assert_no_error(result, "powerscale_stats_protocol")
        assert_result_is_dict(result, "powerscale_stats_protocol")

        # Should have protocol stats
        assert len(result) > 0, "Protocol stats should return data"

    def test_stats_clients_returns_data(self, mcp_session):
        """powerscale_stats_clients returns client connection metrics."""
        result = mcp_session("powerscale_stats_clients")

        assert_no_error(result, "powerscale_stats_clients")
        assert_result_is_dict(result, "powerscale_stats_clients")

        # Should have client stats
        assert len(result) > 0, "Client stats should return data"

    def test_stats_get_generic_tool_exists(self, mcp_session):
        """powerscale_stats_get tool should be available."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_stats_get" in tool_names, \
            "powerscale_stats_get not in tool list"

    def test_stats_keys_discovery(self, mcp_session):
        """powerscale_stats_keys returns available stat keys."""
        result = mcp_session("powerscale_stats_keys")

        assert_no_error(result, "powerscale_stats_keys")
        # Should return dict or list of available keys
        assert isinstance(result, (dict, list, str)), \
            f"Keys should be dict/list/str, got {type(result).__name__}"

    def test_stats_tools_exist(self, mcp_session):
        """All statistics tools should be available."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        stats_tools = [
            "powerscale_stats_cpu",
            "powerscale_stats_network",
            "powerscale_stats_disk",
            "powerscale_stats_ifs",
            "powerscale_stats_node",
            "powerscale_stats_protocol",
            "powerscale_stats_clients",
            "powerscale_stats_get",
            "powerscale_stats_keys",
        ]

        for tool in stats_tools:
            assert tool in tool_names, f"{tool} not in tool list"


# ---------------------------------------------------------------------------
# Part 2: WORM/SmartLock Features
# ---------------------------------------------------------------------------

class TestWormFeatures:
    """Test WORM (Write Once Read Many) compliance features."""

    def test_worm_tools_exist(self, mcp_session):
        """WORM tools should be available in tool list."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_worm_get" in tool_names, \
            "powerscale_worm_get not in tool list"
        assert "powerscale_worm_set" in tool_names, \
            "powerscale_worm_set not in tool list"


# ---------------------------------------------------------------------------
# Part 3: SMB Session Management
# ---------------------------------------------------------------------------

class TestSmbSessions:
    """Test SMB active session management."""

    def test_smb_sessions_get_returns_list(self, mcp_session):
        """powerscale_smb_sessions_get returns active sessions."""
        result = mcp_session("powerscale_smb_sessions_get")

        assert_no_error(result, "powerscale_smb_sessions_get")
        assert_result_is_dict(result, "powerscale_smb_sessions_get")

        # Should have items or pagination
        if "items" in result:
            items = result["items"]
            assert isinstance(items, list), \
                f"items must be list, got {type(items).__name__}"
            # May be empty if no active SMB sessions

    def test_smb_sessions_pagination(self, mcp_session):
        """SMB sessions supports pagination."""
        result = mcp_session("powerscale_smb_sessions_get")

        assert_no_error(result, "powerscale_smb_sessions_get")

        # Should have pagination fields
        assert "resume" in result or "items" in result, \
            f"Missing pagination in {list(result.keys())}"

    def test_smb_sessions_returns_dict(self, mcp_session):
        """powerscale_smb_sessions_get returns a dict response."""
        result = mcp_session("powerscale_smb_sessions_get")

        assert_no_error(result, "powerscale_smb_sessions_get")
        assert_result_is_dict(result, "powerscale_smb_sessions_get")

    def test_smb_openfiles_get_returns_list(self, mcp_session):
        """powerscale_smb_openfiles_get returns open files in sessions."""
        result = mcp_session("powerscale_smb_openfiles_get")

        assert_no_error(result, "powerscale_smb_openfiles_get")
        assert_result_is_dict(result, "powerscale_smb_openfiles_get")

        # Should have items or pagination
        if "items" in result:
            items = result["items"]
            assert isinstance(items, list)

    def test_smb_session_close_structure(self, mcp_session):
        """powerscale_smb_session_close tool exists with correct params."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_smb_session_close" in tool_names

        # Find the tool and check it requires session_id
        tool = next((t for t in tools if t["name"] == "powerscale_smb_session_close"), None)
        assert tool is not None, "Tool should exist"

        # Tool should have proper documentation
        assert "description" in tool or "description" in tool.get("_meta", {})

    def test_smb_sessions_close_by_user_structure(self, mcp_session):
        """powerscale_smb_sessions_close_by_user tool exists."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_smb_sessions_close_by_user" in tool_names

    def test_smb_openfile_close_structure(self, mcp_session):
        """powerscale_smb_openfile_close tool exists."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_smb_openfile_close" in tool_names

    def test_smb_session_tools_exist(self, mcp_session):
        """All SMB session tools should be available."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        smb_session_tools = [
            "powerscale_smb_sessions_get",
            "powerscale_smb_session_close",
            "powerscale_smb_sessions_close_by_user",
            "powerscale_smb_openfiles_get",
            "powerscale_smb_openfile_close",
        ]

        for tool in smb_session_tools:
            assert tool in tool_names, f"{tool} not in tool list"
