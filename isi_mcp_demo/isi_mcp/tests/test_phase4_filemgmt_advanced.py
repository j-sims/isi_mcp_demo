"""
Phase 4c - FileMgmt Advanced Operations Tests

Tests ACL, metadata, access point, WORM, and directory query operations
via MCP tools (SDK-backed).

- ACL get/set (POSIX mode and ownership changes)
- Metadata get/set (custom attributes)
- Access point list/create/delete
- WORM get (read-only — set requires SmartLock domain)
- Directory query (attribute-based search)
"""

import uuid
import json
import pytest

from modules.onefs.v9_12_0.filemgmt import FileMgmt

from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
)


def _unique_path(prefix="test_adv"):
    """Return a path under /ifs/data with a UUID suffix (no leading slash)."""
    return f"ifs/data/{prefix}_{uuid.uuid4().hex[:8]}"


def _unique_name(prefix="test"):
    """Return a name with a unique 8-char hex suffix."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# ACL Operations
# ---------------------------------------------------------------------------

class TestACLGet:
    """Test ACL retrieval via MCP."""

    def test_acl_get_ifs_data(self, mcp_session):
        """powerscale_acl_get returns ACL info for /ifs/data."""
        result = mcp_session("powerscale_acl_get", {
            "path": "ifs/data",
        })
        assert isinstance(result, dict), "ACL result must be dict"
        # ACL response should have owner, group, and mode or acl entries
        assert "owner" in result or "acl" in result or "mode" in result, (
            f"ACL response missing expected fields. Keys: {list(result.keys())}"
        )

    def test_acl_get_created_dir(self, mcp_session, filemgmt_test_dir):
        """powerscale_acl_get works on a freshly created directory."""
        result = mcp_session("powerscale_acl_get", {
            "path": filemgmt_test_dir,
        })
        assert isinstance(result, dict), "ACL result must be dict"
        assert len(result) > 0, "ACL should not be empty"


class TestACLSet:
    """Test ACL modification via MCP."""

    def test_acl_set_mode(self, mcp_session, filemgmt_test_dir):
        """powerscale_acl_set can change POSIX mode on a directory."""
        # Get original ACL to restore later
        original = mcp_session("powerscale_acl_get", {
            "path": filemgmt_test_dir,
        })
        original_mode = original.get("mode")

        # Set a known mode
        new_mode = "0755"
        result = mcp_session("powerscale_acl_set", {
            "path": filemgmt_test_dir,
            "mode": new_mode,
        })
        assert_result_is_dict(result, "acl_set_mode")
        assert result.get("success") is True, f"ACL set failed: {result}"

        # Verify the change
        after = mcp_session("powerscale_acl_get", {
            "path": filemgmt_test_dir,
        })
        assert after.get("mode") == new_mode, (
            f"Mode not changed: expected {new_mode}, got {after.get('mode')}"
        )

        # Restore original mode if it existed
        if original_mode:
            try:
                mcp_session("powerscale_acl_set", {
                    "path": filemgmt_test_dir,
                    "mode": original_mode,
                })
            except Exception as e:
                print(f"\nWarning: Failed to restore original mode: {e}")

    def test_acl_set_owner(self, mcp_session, filemgmt_test_dir):
        """powerscale_acl_set can change ownership on a directory."""
        result = mcp_session("powerscale_acl_set", {
            "path": filemgmt_test_dir,
            "owner": "root",
        })
        assert_result_is_dict(result, "acl_set_owner")
        assert result.get("success") is True, f"ACL set owner failed: {result}"

        # Verify owner
        after = mcp_session("powerscale_acl_get", {
            "path": filemgmt_test_dir,
        })
        owner = after.get("owner", {})
        owner_name = owner.get("name") if isinstance(owner, dict) else None
        assert owner_name == "root", (
            f"Owner not changed: expected 'root', got {owner}"
        )


# ---------------------------------------------------------------------------
# Metadata Operations
# ---------------------------------------------------------------------------

class TestMetadataGet:
    """Test metadata retrieval via MCP."""

    def test_metadata_get_directory(self, mcp_session, filemgmt_test_dir):
        """powerscale_metadata_get returns attrs for a directory."""
        result = mcp_session("powerscale_metadata_get", {
            "path": filemgmt_test_dir,
            "is_directory": True,
        })
        assert isinstance(result, dict), "Metadata result must be dict"
        assert "attrs" in result, f"Missing 'attrs' key. Keys: {list(result.keys())}"
        assert isinstance(result["attrs"], list), "'attrs' must be list"

    def test_metadata_get_file(
        self, mcp_session, filemgmt_test_dir, created_files
    ):
        """powerscale_metadata_get returns attrs for a file."""
        file_path = f"{filemgmt_test_dir}/meta_test.txt"
        created_files.append(file_path)
        mcp_session("powerscale_file_create", {
            "path": file_path,
            "contents": "metadata test",
        })

        result = mcp_session("powerscale_metadata_get", {
            "path": file_path,
            "is_directory": False,
        })
        assert isinstance(result, dict), "Metadata result must be dict"
        assert "attrs" in result, "Missing 'attrs' key"


class TestMetadataSet:
    """Test metadata modification via MCP."""

    def test_metadata_set_directory(self, mcp_session, filemgmt_test_dir):
        """powerscale_metadata_set can set custom attrs on a directory."""
        attrs = json.dumps([
            {"name": "test_attr", "value": "test_value", "op": "update"},
        ])

        result = mcp_session("powerscale_metadata_set", {
            "path": filemgmt_test_dir,
            "attrs": attrs,
            "action": "update",
            "is_directory": True,
        })
        assert_result_is_dict(result, "metadata_set")
        assert result.get("success") is True, f"Metadata set failed: {result}"

        # Note: get_directory_metadata returns system attrs only; user-defined
        # attrs are stored but not surfaced in the same metadata endpoint.
        # We verify the set operation succeeded (no error) above.

    def test_metadata_set_file(
        self, mcp_session, filemgmt_test_dir, created_files
    ):
        """powerscale_metadata_set can set custom attrs on a file."""
        file_path = f"{filemgmt_test_dir}/meta_set_test.txt"
        created_files.append(file_path)
        mcp_session("powerscale_file_create", {
            "path": file_path,
            "contents": "metadata set test",
        })

        attrs = json.dumps([
            {"name": "department", "value": "engineering", "op": "update"},
        ])

        result = mcp_session("powerscale_metadata_set", {
            "path": file_path,
            "attrs": attrs,
            "action": "update",
            "is_directory": False,
        })
        assert_result_is_dict(result, "metadata_set_file")
        assert result.get("success") is True, f"Metadata set failed: {result}"


# ---------------------------------------------------------------------------
# Access Point Operations
# ---------------------------------------------------------------------------

class TestAccessPointList:
    """Test access point listing via MCP."""

    def test_access_point_list(self, mcp_session):
        """powerscale_access_point_list returns namespace access points."""
        result = mcp_session("powerscale_access_point_list", {})
        assert isinstance(result, dict), "Access point list must be dict"
        # The result should have some key with access point data
        # Typically "namespaces" or similar
        assert len(result) > 0, "Access point list should not be empty"


class TestAccessPointLifecycle:
    """Test access point create + delete lifecycle via MCP."""

    def test_access_point_create_and_delete(
        self, mcp_session, filemgmt_test_dir, created_access_points
    ):
        """Create an access point, verify it, then delete it."""
        ap_name = _unique_name("ap")
        full_path = f"/{filemgmt_test_dir}"  # access point path needs leading slash
        created_access_points.append(ap_name)

        # Create
        result = mcp_session("powerscale_access_point_create", {
            "name": ap_name,
            "path": full_path,
        })
        assert_result_is_dict(result, "access_point_create")
        assert result.get("success") is True, (
            f"Access point create failed: {result}"
        )

        # Verify it appears in the listing
        list_result = mcp_session("powerscale_access_point_list", {})
        # Check namespaces list for our access point
        namespaces = list_result.get("namespaces", [])
        if isinstance(namespaces, list):
            ap_names = [
                ns.get("name") for ns in namespaces
                if isinstance(ns, dict)
            ]
            assert ap_name in ap_names, (
                f"Access point '{ap_name}' not found in listing. "
                f"Found: {ap_names[:10]}"
            )

        # Delete (fixture also does cleanup, but test the explicit delete)
        del_result = mcp_session("powerscale_access_point_delete", {
            "name": ap_name,
        })
        assert_result_is_dict(del_result, "access_point_delete")
        assert del_result.get("success") is True, (
            f"Access point delete failed: {del_result}"
        )

        # Remove from cleanup list since we already deleted
        created_access_points.remove(ap_name)


# ---------------------------------------------------------------------------
# WORM / SmartLock Operations (read-only tests)
# ---------------------------------------------------------------------------

class TestWORMGet:
    """Test WORM property retrieval via MCP.

    WORM set requires a SmartLock-enabled directory, which may not exist on
    the test cluster. We test only the read (get) operation, which should
    work on any file path (returning default empty WORM state).
    """

    def test_worm_get(
        self, mcp_session, filemgmt_test_dir, created_files
    ):
        """powerscale_worm_get returns WORM properties for a file."""
        file_path = f"{filemgmt_test_dir}/worm_test.txt"
        created_files.append(file_path)
        mcp_session("powerscale_file_create", {
            "path": file_path,
            "contents": "worm test",
        })

        try:
            result = mcp_session("powerscale_worm_get", {
                "path": file_path,
            })
            # If WORM is supported, we get a dict back
            assert isinstance(result, dict), "WORM result must be dict"
        except AssertionError as e:
            # WORM may not be available if not in a SmartLock domain
            err_str = str(e).lower()
            if "worm" in err_str or "smartlock" in err_str or "not supported" in err_str:
                pytest.skip(f"WORM/SmartLock not available on test cluster: {e}")
            raise


# ---------------------------------------------------------------------------
# Directory Query Operations
# ---------------------------------------------------------------------------

class TestDirectoryQuery:
    """Test directory query (attribute-based search) via MCP."""

    def test_directory_query_basic(
        self, mcp_session, filemgmt_test_dir, created_files
    ):
        """powerscale_directory_query returns a valid response structure."""
        # Create some test files
        for name in ["query_a.txt", "query_b.txt", "other.log"]:
            path = f"{filemgmt_test_dir}/{name}"
            created_files.append(path)
            mcp_session("powerscale_file_create", {
                "path": path,
                "contents": f"content of {name}",
            })

        # Query all files (wildcard match)
        conditions = json.dumps([
            {"attr": "name", "operator": "like", "value": "*"},
        ])

        try:
            result = mcp_session("powerscale_directory_query", {
                "path": filemgmt_test_dir,
                "conditions": conditions,
            })
            assert isinstance(result, dict), "Query result must be dict"
            assert "children" in result, f"Missing 'children'. Keys: {list(result.keys())}"
            children = result.get("children", [])
            assert isinstance(children, list), "'children' must be list"
            # Query may return all children or a subset depending on API
            # behavior; just verify the structure is correct
        except AssertionError as e:
            # Directory query may not be supported on all cluster versions
            err_str = str(e).lower()
            if "not supported" in err_str or "not found" in err_str:
                pytest.skip(f"Directory query not available: {e}")
            raise

    def test_directory_query_pagination_fields(
        self, mcp_session, filemgmt_test_dir
    ):
        """powerscale_directory_query returns pagination fields."""
        conditions = json.dumps([
            {"attr": "name", "operator": "like", "value": "*"},
        ])

        try:
            result = mcp_session("powerscale_directory_query", {
                "path": filemgmt_test_dir,
                "conditions": conditions,
                "limit": 10,
            })
            assert isinstance(result, dict), "Query result must be dict"
            assert "resume" in result, "Missing 'resume' field"
            assert "has_more" in result, "Missing 'has_more' field"
        except AssertionError as e:
            err_str = str(e).lower()
            if "not supported" in err_str or "not found" in err_str:
                pytest.skip(f"Directory query not available: {e}")
            raise
