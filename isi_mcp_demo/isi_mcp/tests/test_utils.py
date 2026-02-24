"""
Test utilities for MCP server and domain module tests.

Provides helpers for:
- Validating MCP responses
- Checking data formats
- Capturing exceptions
"""

import json
import traceback
import pytest


# ---------------------------------------------------------------------------
# MCP Response Validation
# ---------------------------------------------------------------------------

def assert_no_error(result, test_name=""):
    """
    Verify MCP result doesn't have isError=True.

    Usage:
        result = mcp_session("powerscale_thing_get")
        assert_no_error(result)
    """
    if isinstance(result, dict) and result.get("isError"):
        error_msg = result.get("content", result)
        pytest.fail(f"{test_name}: Tool returned error: {error_msg}")


def assert_result_is_dict(result, test_name=""):
    """Verify result is a dict."""
    assert isinstance(result, dict), \
        f"{test_name}: Result must be dict, got {type(result).__name__}"


# ---------------------------------------------------------------------------
# Data Format Validation
# ---------------------------------------------------------------------------

def validate_items_list(result, test_name=""):
    """
    Validate standard pagination response structure.

    Returns the items list if valid.

    Usage:
        items = validate_items_list(result, "quota_get")
        assert len(items) > 0
    """
    assert isinstance(result, dict), \
        f"{test_name}: Result must be dict, got {type(result).__name__}"
    assert "items" in result, \
        f"{test_name}: Missing 'items' key in {list(result.keys())}"
    assert isinstance(result["items"], list), \
        f"{test_name}: 'items' must be list, got {type(result['items']).__name__}"
    return result["items"]


def validate_pagination(result, test_name=""):
    """
    Validate pagination fields in response.

    Returns (resume_token, has_more) tuple.

    Usage:
        resume, has_more = validate_pagination(result)
        if has_more:
            # fetch next page with resume
    """
    assert isinstance(result, dict), \
        f"{test_name}: Result must be dict"
    assert "resume" in result, \
        f"{test_name}: Missing 'resume' field"
    assert "has_more" in result or "resume" in result, \
        f"{test_name}: Missing pagination fields"

    return result.get("resume"), result.get("has_more")


def validate_item_fields(item, required_fields, test_name=""):
    """
    Validate that an item has all required fields.

    Usage:
        item = items[0]
        validate_item_fields(item, ["name", "path", "id"], "quota_item")
    """
    assert isinstance(item, dict), \
        f"{test_name}: Item must be dict"

    missing = [f for f in required_fields if f not in item]
    if missing:
        pytest.fail(
            f"{test_name}: Item missing fields: {missing}\n"
            f"Available fields: {list(item.keys())}"
        )


# ---------------------------------------------------------------------------
# Exception & Error Capture
# ---------------------------------------------------------------------------

def capture_exception(func, *args, **kwargs):
    """
    Call function and capture full exception info.

    Returns dict with error details or the actual result.

    Usage:
        result = capture_exception(config.get)
        if "error" in result:
            print(result["traceback"])
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }


def expect_exception(func, expected_exception_type, *args, **kwargs):
    """
    Call function and verify it raises expected exception.

    Usage:
        expect_exception(quota_set, ValueError, "/nonexistent", 1000)
    """
    try:
        result = func(*args, **kwargs)
        pytest.fail(f"Expected {expected_exception_type.__name__} but got result: {result}")
    except expected_exception_type:
        pass  # Expected
    except Exception as e:
        pytest.fail(
            f"Expected {expected_exception_type.__name__} but got "
            f"{type(e).__name__}: {e}"
        )


# ---------------------------------------------------------------------------
# Test Data Formatting
# ---------------------------------------------------------------------------

def format_result_for_log(result, max_length=500):
    """
    Format result for logging with truncation.

    Usage:
        print(f"Result: {format_result_for_log(result)}")
    """
    if isinstance(result, dict) or isinstance(result, list):
        text = json.dumps(result, indent=2)
    else:
        text = str(result)

    if len(text) > max_length:
        return text[:max_length] + f"\n... ({len(text)} chars total)"
    return text


def print_test_data(label, data):
    """
    Print test data with label (for debugging).

    Usage:
        print_test_data("Cluster config", config)
    """
    print(f"\n{'='*60}")
    print(f"{label}:")
    print(f"{'='*60}")
    print(format_result_for_log(data))
    print()


# ---------------------------------------------------------------------------
# Response Comparison
# ---------------------------------------------------------------------------

def compare_responses(before, after, changed_fields=None, test_name=""):
    """
    Compare two responses and verify only expected fields changed.

    Usage:
        before = nfs_mod.get_global_settings()
        # ... make change ...
        after = nfs_mod.get_global_settings()
        compare_responses(before, after, ["v3_enabled"], "nfs_settings")
    """
    if changed_fields is None:
        changed_fields = []

    changes = {}
    for key in set(list(before.keys()) + list(after.keys())):
        before_val = before.get(key)
        after_val = after.get(key)
        if before_val != after_val:
            changes[key] = {"before": before_val, "after": after_val}

    # Verify only expected fields changed
    unexpected = set(changes.keys()) - set(changed_fields)
    if unexpected:
        pytest.fail(
            f"{test_name}: Unexpected fields changed: {unexpected}\n"
            f"Changes: {changes}"
        )

    # Verify all expected fields actually changed
    missing_changes = set(changed_fields) - set(changes.keys())
    if missing_changes:
        pytest.fail(
            f"{test_name}: Expected changes did not occur: {missing_changes}\n"
            f"Actual changes: {changes}"
        )

    return changes


# ---------------------------------------------------------------------------
# Test Data Helpers
# ---------------------------------------------------------------------------

def get_safe_test_value(field_name, resource_type=""):
    """
    Get a safe test value for a field (won't cause cluster issues).

    Usage:
        name = get_safe_test_value("share_name")
        # Returns something like "test_abc12345"
    """
    import uuid
    suffix = uuid.uuid4().hex[:8]

    if "name" in field_name.lower():
        return f"test_{suffix}"
    elif "path" in field_name.lower():
        return f"/ifs/data/test_{suffix}"
    elif "size" in field_name.lower():
        return 1024 * 1024 * 1024  # 1 GB (minimum)
    else:
        return f"test_{suffix}"


# ---------------------------------------------------------------------------
# Fixtures (for use in test classes)
# ---------------------------------------------------------------------------

class TestResponseValidator:
    """
    Mixin class for test classes to provide validation helpers.

    Usage:
        class TestMyFeature(TestResponseValidator):
            def test_something(self, mcp_session):
                result = mcp_session("tool_name")
                self.assert_valid_response(result)
    """

    def assert_valid_response(self, result, test_name=None):
        """Assert response is valid dict with no errors."""
        name = test_name or self._testMethodName
        assert_no_error(result, name)
        assert_result_is_dict(result, name)

    def assert_has_items(self, result, test_name=None):
        """Assert response has items list."""
        name = test_name or self._testMethodName
        validate_items_list(result, name)

    def assert_paginated(self, result, test_name=None):
        """Assert response has pagination fields."""
        name = test_name or self._testMethodName
        validate_pagination(result, name)
