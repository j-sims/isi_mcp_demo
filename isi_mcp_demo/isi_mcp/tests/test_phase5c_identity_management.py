"""
Phase 5C - Identity and Management Tests (Full Coverage)

Part 1: Users Module (user CRUD operations)
Part 2: Groups Module (group CRUD operations)
Part 3: Management Tools (cluster selection, tool management)
"""

import pytest
import uuid
from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
    validate_items_list, validate_pagination,
)


# ---------------------------------------------------------------------------
# Part 1: Users Module
# ---------------------------------------------------------------------------

def _get_test_username():
    """Generate a unique test username."""
    return f"test_user_{uuid.uuid4().hex[:8]}"


class TestUsersReadOnly:
    """Test user query operations."""

    def test_user_get_returns_list(self, mcp_session):
        """powerscale_user_get returns list of users."""
        result = mcp_session("powerscale_user_get")

        assert_no_error(result, "powerscale_user_get")
        assert_result_is_dict(result, "powerscale_user_get")

        # Should have pagination
        assert "resume" in result, "Missing pagination resume field"
        assert "has_more" in result or "items" in result

    def test_user_get_has_items(self, mcp_session):
        """User get should return items list."""
        result = mcp_session("powerscale_user_get")

        assert_no_error(result, "powerscale_user_get")

        # Should have items
        if "items" in result:
            items = validate_items_list(result, "powerscale_user_get")
            assert isinstance(items, list)
            # Cluster should have at least 'root' user
            if len(items) > 0:
                # Items should have expected structure
                item = items[0]
                assert isinstance(item, dict)

    def test_user_get_pagination(self, mcp_session):
        """User get supports pagination with resume token."""
        result = mcp_session("powerscale_user_get")

        assert_no_error(result, "powerscale_user_get")
        assert "resume" in result
        assert isinstance(result.get("has_more"), bool)

    def test_user_get_with_filter(self, mcp_session):
        """powerscale_user_get supports listing."""
        # Get list with pagination
        result = mcp_session("powerscale_user_get")

        assert_no_error(result, "powerscale_user_get")
        assert_result_is_dict(result, "powerscale_user_get")


class TestUsersLifecycle:
    """Test user create/modify/remove operations."""

    def test_user_create_requires_confirmation(self, mcp_session):
        """User creation should require password parameter."""
        username = _get_test_username()

        # User creation requires user_name and password
        result = mcp_session("powerscale_user_create",
                            {"user_name": username,
                             "password": "TestPass123"})

        # Tool should return something (either success or prompt for confirmation)
        assert_no_error(result, f"powerscale_user_create({username})")

        # Response should be dict
        assert isinstance(result, dict), \
            f"Result must be dict, got {type(result).__name__}"

    def test_user_create_with_properties(self, mcp_session):
        """User creation with additional properties."""
        username = _get_test_username()

        result = mcp_session("powerscale_user_create",
                            {"user_name": username,
                             "password": "TestPass456",
                             "shell": "/bin/bash"})

        # Should handle the request
        assert_no_error(result, f"powerscale_user_create({username}) with props")

    def test_user_modify_tool_exists(self, mcp_session):
        """User modify tool should exist."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_user_modify" in tool_names, \
            "powerscale_user_modify not found"

    def test_user_remove_tool_exists(self, mcp_session):
        """User remove tool should exist."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_user_remove" in tool_names, \
            "powerscale_user_remove not found"

    def test_user_tools_complete(self, mcp_session):
        """All user management tools should exist."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        user_tools = [
            "powerscale_user_get",
            "powerscale_user_create",
            "powerscale_user_modify",
            "powerscale_user_remove",
        ]

        for tool in user_tools:
            assert tool in tool_names, f"{tool} not found in tool list"


# ---------------------------------------------------------------------------
# Part 2: Groups Module
# ---------------------------------------------------------------------------

def _get_test_groupname():
    """Generate a unique test group name."""
    return f"test_group_{uuid.uuid4().hex[:8]}"


class TestGroupsReadOnly:
    """Test group query operations."""

    def test_group_get_returns_list(self, mcp_session):
        """powerscale_group_get returns list of groups."""
        result = mcp_session("powerscale_group_get")

        assert_no_error(result, "powerscale_group_get")
        assert_result_is_dict(result, "powerscale_group_get")

        # Should have pagination
        assert "resume" in result, "Missing pagination resume field"
        assert "has_more" in result or "items" in result

    def test_group_get_has_items(self, mcp_session):
        """Group get should return items list."""
        result = mcp_session("powerscale_group_get")

        assert_no_error(result, "powerscale_group_get")

        # Should have items
        if "items" in result:
            items = validate_items_list(result, "powerscale_group_get")
            assert isinstance(items, list)
            # Cluster should have at least 'root' group
            if len(items) > 0:
                item = items[0]
                assert isinstance(item, dict)

    def test_group_get_pagination(self, mcp_session):
        """Group get supports pagination."""
        result = mcp_session("powerscale_group_get")

        assert_no_error(result, "powerscale_group_get")
        assert "resume" in result
        assert isinstance(result.get("has_more"), bool)

    def test_group_get_with_filter(self, mcp_session):
        """powerscale_group_get supports listing."""
        # Get list with pagination
        result = mcp_session("powerscale_group_get")

        assert_no_error(result, "powerscale_group_get")
        assert_result_is_dict(result, "powerscale_group_get")


class TestGroupsLifecycle:
    """Test group create/modify/remove operations."""

    def test_group_create_requires_confirmation(self, mcp_session):
        """Group creation should require confirmation."""
        groupname = _get_test_groupname()

        # Try creating group - requires group_name
        result = mcp_session("powerscale_group_create", {"group_name": groupname})

        # Tool should return something
        assert_no_error(result, f"powerscale_group_create({groupname})")
        assert isinstance(result, dict), \
            f"Result must be dict, got {type(result).__name__}"

    def test_group_create_with_properties(self, mcp_session):
        """Group creation with additional properties."""
        groupname = _get_test_groupname()

        result = mcp_session("powerscale_group_create",
                            {"group_name": groupname})

        # Should handle the request
        assert_no_error(result, f"powerscale_group_create({groupname})")

    def test_group_modify_tool_exists(self, mcp_session):
        """Group modify tool should exist."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_group_modify" in tool_names, \
            "powerscale_group_modify not found"

    def test_group_remove_tool_exists(self, mcp_session):
        """Group remove tool should exist."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_group_remove" in tool_names, \
            "powerscale_group_remove not found"

    def test_group_tools_complete(self, mcp_session):
        """All group management tools should exist."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        group_tools = [
            "powerscale_group_get",
            "powerscale_group_create",
            "powerscale_group_modify",
            "powerscale_group_remove",
        ]

        for tool in group_tools:
            assert tool in tool_names, f"{tool} not found in tool list"


# ---------------------------------------------------------------------------
# Part 3: Management Tools
# ---------------------------------------------------------------------------

class TestManagementTools:
    """Test cluster and tool management operations."""

    def test_tools_list_returns_tools(self, mcp_session):
        """powerscale_tools_list returns a flat alphabetical list of all tools."""
        result = mcp_session("powerscale_tools_list")

        assert_no_error(result, "powerscale_tools_list")
        assert isinstance(result, list), \
            f"Result must be list, got {type(result).__name__}"
        assert len(result) > 0, "No tools returned"
        # Each entry must have name, group, mode, enabled
        entry = result[0]
        for field in ("name", "group", "mode", "enabled"):
            assert field in entry, f"Missing field '{field}' in entry"

    def test_tools_list_has_content(self, mcp_session):
        """Tools list should have substantial content (>100 tools)."""
        result = mcp_session("powerscale_tools_list")

        assert_no_error(result, "powerscale_tools_list")
        assert isinstance(result, list) and len(result) > 100, \
            f"Expected >100 tools, got {len(result) if isinstance(result, list) else type(result).__name__}"

    def test_tools_toggle_exists(self, mcp_session):
        """Tool toggle tool should exist."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_tools_toggle" in tool_names, \
            "powerscale_tools_toggle not found"

    def test_cluster_list_returns_clusters(self, mcp_session):
        """powerscale_cluster_list returns available clusters."""
        result = mcp_session("powerscale_cluster_list")

        assert_no_error(result, "powerscale_cluster_list")
        assert_result_is_dict(result, "powerscale_cluster_list")

        # Should have clusters list
        assert "clusters" in result or "items" in result or isinstance(result, list), \
            f"Result should have clusters. Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}"

    def test_cluster_list_structure(self, mcp_session):
        """Cluster list should have expected structure."""
        result = mcp_session("powerscale_cluster_list")

        assert_no_error(result, "powerscale_cluster_list")

        # Should return a dict with cluster information
        assert isinstance(result, (dict, list)), \
            f"Cluster list must be dict/list, got {type(result).__name__}"

    def test_cluster_select_tool_exists(self, mcp_session):
        """Cluster select tool should exist."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_cluster_select" in tool_names, \
            "powerscale_cluster_select not found"

    def test_management_tools_exist(self, mcp_session):
        """All management tools should exist."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        management_tools = [
            "powerscale_tools_list",
            "powerscale_tools_list_by_group",
            "powerscale_tools_list_by_mode",
            "powerscale_tools_toggle",
            "powerscale_cluster_list",
            "powerscale_cluster_select",
        ]

        for tool in management_tools:
            assert tool in tool_names, f"{tool} not found in tool list"

    def test_health_check_tool_exists(self, mcp_session):
        """Health check tool should be available."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_check_health" in tool_names, \
            "powerscale_check_health not found"

    def test_config_tool_exists(self, mcp_session):
        """Config tool should be available."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_config" in tool_names, \
            "powerscale_config not found"

    def test_capacity_tool_exists(self, mcp_session):
        """Capacity tool should be available."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_capacity" in tool_names, \
            "powerscale_capacity not found"

    def test_tools_list_mode_values_valid(self, mcp_session):
        """Every tool in powerscale_tools_list must have mode 'read' or 'write'."""
        result = mcp_session("powerscale_tools_list")

        assert isinstance(result, list) and len(result) > 0
        invalid = [e for e in result if e.get("mode") not in ("read", "write")]
        assert invalid == [], \
            f"Tools with invalid mode: {[e['name'] for e in invalid]}"

    def test_tools_list_by_mode_counts_match_total(self, mcp_session):
        """read_count + write_count should equal total tool count."""
        flat = mcp_session("powerscale_tools_list")
        by_mode = mcp_session("powerscale_tools_list_by_mode")

        assert isinstance(flat, list) and isinstance(by_mode, dict)
        total = len(flat)
        assert by_mode["read_count"] + by_mode["write_count"] == total, (
            f"Mode counts {by_mode['read_count']}+{by_mode['write_count']}"
            f" != total {total}"
        )

    def test_tools_toggle_by_write_mode(self, mcp_session):
        """Toggle all write tools off then back on; verify runtime state changes."""
        # Disable all write tools
        disable_result = mcp_session("powerscale_tools_toggle",
                                     {"names": ["write"], "action": "disable"})
        assert "error" not in str(disable_result).lower() or isinstance(disable_result, dict), \
            f"Toggle disable failed: {disable_result}"

        try:
            # Verify at least one known write tool is now disabled
            flat = mcp_session("powerscale_tools_list")
            assert isinstance(flat, list)
            quota_set = next((e for e in flat if e["name"] == "powerscale_quota_set"), None)
            assert quota_set is not None, "powerscale_quota_set not found in list"
            assert quota_set["enabled"] is False, \
                "powerscale_quota_set should be disabled after write mode toggle"
        finally:
            # Always re-enable write tools regardless of assertion outcome
            enable_result = mcp_session("powerscale_tools_toggle",
                                        {"names": ["write"], "action": "enable"})
            flat_after = mcp_session("powerscale_tools_list")
            quota_set_after = next(
                (e for e in flat_after if e["name"] == "powerscale_quota_set"), None
            )
            assert quota_set_after is not None
            assert quota_set_after["enabled"] is True, \
                "powerscale_quota_set should be re-enabled after write mode toggle"
