"""
Phase 5A - Events Tool Tests

Tests event querying operations.
These are read-only operations that don't require cluster resource creation.

NOTE: Utility function tools (current_time, bytes_to_human, human_to_bytes) are
defined in server.py but are NOT properly exposed through the MCP interface.
This test file focuses on tools that ARE available in the MCP layer.
"""

import pytest
from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
    validate_items_list, validate_pagination,
)


# ---------------------------------------------------------------------------
# Part 1: Events Module
# ---------------------------------------------------------------------------

class TestEventsTools:
    """Test event querying operations."""

    def test_event_get_returns_dict(self, mcp_session):
        """powerscale_event_get returns a dict response."""
        result = mcp_session("powerscale_event_get")

        # Verify no errors
        assert_no_error(result, "powerscale_event_get")
        assert_result_is_dict(result, "powerscale_event_get")

    def test_event_get_has_pagination(self, mcp_session):
        """Event get response should have pagination fields."""
        result = mcp_session("powerscale_event_get")

        assert_no_error(result, "powerscale_event_get")

        # Should have pagination
        assert "resume" in result or "items" in result, \
            "Missing pagination/items field"

    def test_event_tools_exist(self, mcp_session):
        """Event tools should be available in tool list."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        assert "powerscale_event_get" in tool_names, \
            "powerscale_event_get not in tool list"
        assert "powerscale_event_get_by_id" in tool_names, \
            "powerscale_event_get_by_id not in tool list"
