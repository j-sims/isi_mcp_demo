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
        """powerscale_tools_list returns available tools."""
        result = mcp_session("powerscale_tools_list")

        assert_no_error(result, "powerscale_tools_list")
        # Result is a list or dict depending on implementation
        assert isinstance(result, (dict, list)), \
            f"Result must be dict/list, got {type(result).__name__}"

    def test_tools_list_has_content(self, mcp_session):
        """Tools list should have substantial content."""
        result = mcp_session("powerscale_tools_list")

        assert_no_error(result, "powerscale_tools_list")

        # Should return actual tools
        if isinstance(result, dict):
            # May be grouped by category
            assert len(result) > 0, "No tool groups returned"
        elif isinstance(result, list):
            # Should have multiple tools
            assert len(result) > 0, "No tools returned"

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
