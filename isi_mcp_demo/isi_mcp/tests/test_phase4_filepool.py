"""
Phase 4e - FilePool Policy Operations Tests

Tests FilePool policy read, create, update, and remove operations via MCP.

FilePool policies automate data tiering by defining file matching criteria
and actions. Read operations use the SDK; create/remove use Ansible;
update uses the SDK directly (Ansible doesn't support modify).

Tests skip gracefully if FilePool operations fail due to cluster limitations.
"""

import uuid
import json
import pytest

from modules.onefs.v9_12_0.filepool import FilePool

from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
)


def _unique_name(prefix="test_fp"):
    """Return a name with a unique 8-char hex suffix."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# Minimal file matching pattern: match all .tmp files
_MINIMAL_PATTERN = json.dumps({
    "or_criteria": [{
        "and_criteria": [{
            "type": "file_name",
            "condition": "matches",
            "value": "*.tmp",
            "case_sensitive": False,
        }]
    }]
})


# ---------------------------------------------------------------------------
# FilePool Policy - Read Operations
# ---------------------------------------------------------------------------

class TestFilePoolPolicyRead:
    pytestmark = [pytest.mark.func_filepool, pytest.mark.group_filepool, pytest.mark.read]
    """Test FilePool policy read operations via MCP."""

    def test_filepool_policy_get(self, mcp_session):
        """powerscale_filepool_policy_get returns all FilePool policies."""
        result = mcp_session("powerscale_filepool_policy_get")
        assert isinstance(result, dict), "FilePool list must be dict"
        assert "items" in result, f"Missing 'items'. Keys: {list(result.keys())}"
        assert isinstance(result["items"], list), "'items' must be list"
        assert "total" in result, "Missing 'total' field"

    def test_filepool_default_policy_get(self, mcp_session):
        """powerscale_filepool_default_policy_get returns the default policy."""
        result = mcp_session("powerscale_filepool_default_policy_get")
        assert isinstance(result, dict), "Default policy must be dict"
        assert result.get("success") is True, (
            f"Default policy get failed: {result}"
        )
        assert "default_policy" in result, "Missing 'default_policy' key"

    def test_filepool_policy_get_by_name_nonexistent(self, mcp_session):
        """powerscale_filepool_policy_get_by_name handles missing policy."""
        try:
            result = mcp_session("powerscale_filepool_policy_get_by_name", {
                "policy_id": "nonexistent_fp_policy_999",
            })
        except AssertionError as e:
            # Tool may return error for nonexistent policy
            if "not found" in str(e).lower() or "404" in str(e):
                return
            raise

        if isinstance(result, dict):
            assert result.get("success") is False or "error" in result, (
                f"Expected failure for nonexistent policy: {result}"
            )


# ---------------------------------------------------------------------------
# FilePool Policy - Lifecycle (Create + Verify + Update + Delete)
# ---------------------------------------------------------------------------

class TestFilePoolPolicyLifecycle:
    pytestmark = [pytest.mark.func_filepool, pytest.mark.group_filepool, pytest.mark.write]
    """Test FilePool policy create + update + remove lifecycle via MCP."""

    def test_filepool_policy_create_and_remove(
        self, mcp_session, created_filepool_policies
    ):
        """Create a FilePool policy, verify it, then remove it."""
        policy_name = _unique_name("fppol")
        created_filepool_policies.append(policy_name)

        # Create via Ansible
        result = mcp_session("powerscale_filepool_policy_create", {
            "policy_name": policy_name,
            "file_matching_pattern": _MINIMAL_PATTERN,
            "description": "Test policy for Phase 4 testing",
        })
        assert_result_is_dict(result, "filepool_policy_create")
        assert result.get("success") is True, (
            f"FilePool policy create failed: {result}"
        )

        # Verify it exists in the listing
        list_result = mcp_session("powerscale_filepool_policy_get")
        policy_names = [p.get("name") for p in list_result.get("items", [])]
        assert policy_name in policy_names, (
            f"Created policy '{policy_name}' not found. "
            f"Found: {policy_names[:10]}"
        )

        # Verify via get_by_name
        get_result = mcp_session("powerscale_filepool_policy_get_by_name", {
            "policy_id": policy_name,
        })
        assert get_result.get("success") is True, (
            f"FilePool policy get_by_name failed: {get_result}"
        )
        assert get_result.get("policy", {}).get("name") == policy_name

        # Remove via Ansible
        del_result = mcp_session("powerscale_filepool_policy_remove", {
            "policy_name": policy_name,
        })
        assert_result_is_dict(del_result, "filepool_policy_remove")
        assert del_result.get("success") is True, (
            f"FilePool policy remove failed: {del_result}"
        )

        # Remove from cleanup list since we already deleted
        created_filepool_policies.remove(policy_name)

        # Verify deleted
        post_list = mcp_session("powerscale_filepool_policy_get")
        post_names = [p.get("name") for p in post_list.get("items", [])]
        assert policy_name not in post_names, (
            f"Policy '{policy_name}' still present after removal"
        )

    def test_filepool_policy_create_verify_update(
        self, mcp_session, created_filepool_policies
    ):
        """Create a FilePool policy, update its description, verify change."""
        policy_name = _unique_name("fpupd")
        created_filepool_policies.append(policy_name)

        # Create
        result = mcp_session("powerscale_filepool_policy_create", {
            "policy_name": policy_name,
            "file_matching_pattern": _MINIMAL_PATTERN,
            "description": "Original description",
        })
        assert result.get("success") is True, (
            f"FilePool policy create failed: {result}"
        )

        # Update description via SDK
        new_desc = "Updated description for testing"
        update_result = mcp_session("powerscale_filepool_policy_update", {
            "policy_id": policy_name,
            "description": new_desc,
        })
        assert_result_is_dict(update_result, "filepool_policy_update")
        assert update_result.get("success") is True, (
            f"FilePool policy update failed: {update_result}"
        )

        # Verify the description changed
        get_result = mcp_session("powerscale_filepool_policy_get_by_name", {
            "policy_id": policy_name,
        })
        assert get_result.get("success") is True
        policy = get_result.get("policy", {})
        assert policy.get("description") == new_desc, (
            f"Description not updated: expected '{new_desc}', "
            f"got '{policy.get('description')}'"
        )
