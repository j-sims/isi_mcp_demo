"""
Phase 4 - FileMgmt Directory & File Operations Tests

Tests file and directory CRUD operations via MCP tools (SDK-backed).

Part 4a: Directory Operations
- Create, list, attributes, copy, move, delete

Part 4b: File Operations
- Create, read, attributes, copy, move, delete

All tests use the `filemgmt_test_dir` or `created_directories`/`created_files`
fixtures for automatic cleanup. Paths passed to MCP tools must NOT have a
leading slash (e.g. "ifs/data/test_abc" not "/ifs/data/test_abc").

Note on copy/move:
- The OneFS Namespace API copy source uses the x-isi-ifs-copy-source header
  which requires a /namespace/ prefix (e.g. "/namespace/ifs/data/...")
- The MCP tool passes source directly to the SDK which sets this header
- Move destinations use x-isi-ifs-set-location which also requires /namespace/

Note on file contents:
- The SDK's create_file() JSON-serializes the body, so a plain string "Hello"
  gets stored as '"Hello"' (with quotes). The read back includes these quotes.
"""

import uuid
import json
import pytest

from modules.onefs.v9_12_0.filemgmt import FileMgmt

from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
)


def _unique_path(prefix="test_fm"):
    """Return a path under /ifs/data with a UUID suffix (no leading slash)."""
    return f"ifs/data/{prefix}_{uuid.uuid4().hex[:8]}"


def _strip_json_quotes(s: str) -> str:
    """Strip surrounding JSON double-quotes if present.

    The SDK's create_file() JSON-encodes the body, wrapping plain strings
    in double-quotes. This helper strips them for comparison.
    """
    if s and len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


# ---------------------------------------------------------------------------
# Part 4a: Directory Operations
# ---------------------------------------------------------------------------

class TestDirectoryCreate:
    """Test directory creation via MCP."""

    def test_directory_create(self, mcp_session, created_directories):
        """powerscale_directory_create creates a directory."""
        path = _unique_path("dir")
        created_directories.append(path)

        result = mcp_session("powerscale_directory_create", {
            "path": path,
            "recursive": True,
        })
        assert_result_is_dict(result, "directory_create")
        assert result.get("success") is True, f"Directory create failed: {result}"

    def test_directory_create_nested(self, mcp_session, created_directories):
        """powerscale_directory_create with recursive creates nested dirs."""
        parent = _unique_path("nested")
        path = f"{parent}/sub1/sub2"
        # Register the top-level parent for cleanup (recursive delete)
        created_directories.append(parent)

        result = mcp_session("powerscale_directory_create", {
            "path": path,
            "recursive": True,
        })
        assert_result_is_dict(result, "directory_create_nested")
        assert result.get("success") is True, f"Nested create failed: {result}"

        # Verify nested dir exists via listing
        list_result = mcp_session("powerscale_directory_list", {
            "path": f"{parent}/sub1",
        })
        assert isinstance(list_result, dict), "List must return dict"
        children = list_result.get("children", [])
        child_names = [c.get("name") for c in children]
        assert "sub2" in child_names, (
            f"Nested dir 'sub2' not found in {child_names}"
        )


class TestDirectoryList:
    """Test directory listing via MCP."""

    def test_directory_list_ifs(self, mcp_session):
        """powerscale_directory_list returns children for /ifs."""
        result = mcp_session("powerscale_directory_list", {
            "path": "ifs",
            "limit": 100,
        })
        assert isinstance(result, dict), "List must return dict"
        children = result.get("children", [])
        assert isinstance(children, list), "'children' must be list"
        assert len(children) > 0, "/ifs should have at least one child"

        # /ifs/data should exist on every cluster
        child_names = [c.get("name") for c in children]
        assert "data" in child_names, (
            f"'data' not found in /ifs listing: {child_names}"
        )

    def test_directory_list_has_resume(self, mcp_session):
        """powerscale_directory_list has resume and has_more fields."""
        result = mcp_session("powerscale_directory_list", {
            "path": "ifs",
            "limit": 100,
        })
        assert "resume" in result, "Missing 'resume' field"
        assert "has_more" in result, "Missing 'has_more' field"

    def test_directory_list_created_dir(
        self, mcp_session, filemgmt_test_dir
    ):
        """Listing a freshly created directory returns empty children."""
        result = mcp_session("powerscale_directory_list", {
            "path": filemgmt_test_dir,
        })
        assert isinstance(result, dict), "List must return dict"
        children = result.get("children", [])
        assert isinstance(children, list), "'children' must be list"
        # Freshly created dir should be empty
        assert len(children) == 0, (
            f"Expected empty dir, found {len(children)} children"
        )


class TestDirectoryAttributes:
    """Test directory attribute retrieval via MCP."""

    def test_directory_attributes_ifs_data(self, mcp_session):
        """powerscale_directory_attributes returns headers for /ifs/data."""
        result = mcp_session("powerscale_directory_attributes", {
            "path": "ifs/data",
        })
        assert isinstance(result, dict), "Attributes must be dict"
        assert len(result) > 0, "Attributes should not be empty"

    def test_directory_attributes_created_dir(
        self, mcp_session, filemgmt_test_dir
    ):
        """powerscale_directory_attributes works on a freshly created dir."""
        result = mcp_session("powerscale_directory_attributes", {
            "path": filemgmt_test_dir,
        })
        assert isinstance(result, dict), "Attributes must be dict"
        assert len(result) > 0, "Attributes should not be empty"


class TestDirectoryCopy:
    """Test directory copy via MCP."""

    def test_directory_copy(
        self, mcp_session, filemgmt_test_dir, created_directories
    ):
        """powerscale_directory_copy copies a directory."""
        dest = _unique_path("dircopy")
        created_directories.append(dest)

        # Create a file inside the source dir so we can verify the copy
        file_path = f"{filemgmt_test_dir}/testfile.txt"
        mcp_session("powerscale_file_create", {
            "path": file_path,
            "contents": "copy test content",
        })

        # Copy source must use /namespace/ prefix (OneFS API requirement)
        result = mcp_session("powerscale_directory_copy", {
            "source": f"/namespace/{filemgmt_test_dir}",
            "destination": dest,
            "merge": True,
        })
        assert_result_is_dict(result, "directory_copy")
        assert result.get("success") is True, f"Directory copy failed: {result}"

        # Verify copied file exists in destination
        list_result = mcp_session("powerscale_directory_list", {
            "path": dest,
        })
        child_names = [c.get("name") for c in list_result.get("children", [])]
        assert "testfile.txt" in child_names, (
            f"Copied file not found in destination: {child_names}"
        )


class TestDirectoryMove:
    """Test directory move/rename via MCP."""

    def test_directory_move(
        self, mcp_session, created_directories
    ):
        """powerscale_directory_move renames a directory."""
        src = _unique_path("dirsrc")
        dest = _unique_path("dirdst")
        # Only register dest for cleanup since src will be moved
        created_directories.append(dest)

        # Create source
        mcp_session("powerscale_directory_create", {
            "path": src,
            "recursive": True,
        })

        # Move destination must use /namespace/ prefix
        result = mcp_session("powerscale_directory_move", {
            "path": src,
            "destination": f"/namespace/{dest}",
        })
        assert_result_is_dict(result, "directory_move")
        assert result.get("success") is True, f"Directory move failed: {result}"

        # Verify destination exists
        dest_result = mcp_session("powerscale_directory_list", {
            "path": dest,
        })
        assert isinstance(dest_result, dict), "Dest listing must return dict"


class TestDirectoryDelete:
    """Test directory deletion via MCP."""

    def test_directory_delete_empty(self, mcp_session):
        """powerscale_directory_delete removes an empty directory."""
        path = _unique_path("dirdel")

        # Create
        create_result = mcp_session("powerscale_directory_create", {
            "path": path,
            "recursive": True,
        })
        assert create_result.get("success") is True

        # Delete
        result = mcp_session("powerscale_directory_delete", {
            "path": path,
            "recursive": False,
        })
        assert_result_is_dict(result, "directory_delete")
        assert result.get("success") is True, f"Directory delete failed: {result}"

    def test_directory_delete_recursive(self, mcp_session):
        """powerscale_directory_delete with recursive removes dir + contents."""
        path = _unique_path("dirdelr")

        # Create dir with a file inside
        mcp_session("powerscale_directory_create", {
            "path": path,
            "recursive": True,
        })
        mcp_session("powerscale_file_create", {
            "path": f"{path}/child.txt",
            "contents": "will be deleted",
        })

        # Delete recursively
        result = mcp_session("powerscale_directory_delete", {
            "path": path,
            "recursive": True,
        })
        assert_result_is_dict(result, "directory_delete_recursive")
        assert result.get("success") is True, f"Recursive delete failed: {result}"


# ---------------------------------------------------------------------------
# Part 4b: File Operations
# ---------------------------------------------------------------------------

class TestFileCreate:
    """Test file creation via MCP."""

    def test_file_create_empty(
        self, mcp_session, filemgmt_test_dir, created_files
    ):
        """powerscale_file_create creates an empty file."""
        file_path = f"{filemgmt_test_dir}/empty.txt"
        created_files.append(file_path)

        result = mcp_session("powerscale_file_create", {
            "path": file_path,
        })
        assert_result_is_dict(result, "file_create_empty")
        assert result.get("success") is True, f"File create failed: {result}"

    def test_file_create_with_contents(
        self, mcp_session, filemgmt_test_dir, created_files
    ):
        """powerscale_file_create writes text content to a file."""
        file_path = f"{filemgmt_test_dir}/hello.txt"
        created_files.append(file_path)
        content = "Hello, PowerScale!"

        result = mcp_session("powerscale_file_create", {
            "path": file_path,
            "contents": content,
        })
        assert_result_is_dict(result, "file_create_contents")
        assert result.get("success") is True, f"File create failed: {result}"

        # Verify contents via read (SDK wraps strings in JSON quotes)
        read_result = mcp_session("powerscale_file_read", {
            "path": file_path,
        })
        assert isinstance(read_result, dict), "Read must return dict"
        actual = _strip_json_quotes(read_result.get("contents", ""))
        assert actual == content, (
            f"Contents mismatch: expected '{content}', got '{actual}'"
        )

    def test_file_create_json(
        self, mcp_session, filemgmt_test_dir, created_files
    ):
        """powerscale_file_create can write JSON content."""
        file_path = f"{filemgmt_test_dir}/config.json"
        created_files.append(file_path)
        data = {"key": "value", "number": 42}
        content = json.dumps(data)

        result = mcp_session("powerscale_file_create", {
            "path": file_path,
            "contents": content,
            "content_type": "application/json",
        })
        assert result.get("success") is True, f"JSON file create failed: {result}"

        # Verify contents — the SDK JSON-encodes the body, so the stored
        # content is a JSON-encoded JSON string. Parse accordingly.
        read_result = mcp_session("powerscale_file_read", {
            "path": file_path,
        })
        raw = read_result.get("contents", "")
        # Try parsing directly first (if stored as-is), then try double-decode
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            parsed = None
        assert parsed == data, (
            f"JSON mismatch: expected {data}, got {parsed} (raw: {raw!r})"
        )


class TestFileRead:
    """Test file reading via MCP."""

    def test_file_read_contents(
        self, mcp_session, filemgmt_test_dir, created_files
    ):
        """powerscale_file_read returns file contents and metadata."""
        file_path = f"{filemgmt_test_dir}/read_test.txt"
        created_files.append(file_path)
        content = "Line 1\nLine 2\nLine 3"

        mcp_session("powerscale_file_create", {
            "path": file_path,
            "contents": content,
        })

        result = mcp_session("powerscale_file_read", {
            "path": file_path,
        })
        assert isinstance(result, dict), "Read must return dict"
        assert "contents" in result, "Missing 'contents' field"
        assert "size" in result, "Missing 'size' field"
        assert "truncated" in result, "Missing 'truncated' field"
        # SDK JSON-encodes the body (quotes + escape sequences like \n → \\n)
        # Use json.loads() to properly decode the full JSON string
        raw = result["contents"]
        try:
            actual = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            actual = _strip_json_quotes(raw)
        assert actual == content, (
            f"Content mismatch: expected {content!r}, got {actual!r}"
        )
        assert result["truncated"] is False

    def test_file_read_has_headers(
        self, mcp_session, filemgmt_test_dir, created_files
    ):
        """powerscale_file_read returns HTTP headers as metadata."""
        file_path = f"{filemgmt_test_dir}/headers_test.txt"
        created_files.append(file_path)

        mcp_session("powerscale_file_create", {
            "path": file_path,
            "contents": "header test",
        })

        result = mcp_session("powerscale_file_read", {
            "path": file_path,
        })
        assert "headers" in result, "Missing 'headers' field"
        assert isinstance(result["headers"], dict), "'headers' must be dict"


class TestFileAttributes:
    """Test file attribute retrieval via MCP."""

    def test_file_attributes(
        self, mcp_session, filemgmt_test_dir, created_files
    ):
        """powerscale_file_attributes returns header dict for a file."""
        file_path = f"{filemgmt_test_dir}/attrs_test.txt"
        created_files.append(file_path)

        mcp_session("powerscale_file_create", {
            "path": file_path,
            "contents": "attribute test",
        })

        result = mcp_session("powerscale_file_attributes", {
            "path": file_path,
        })
        assert isinstance(result, dict), "Attributes must be dict"
        assert len(result) > 0, "Attributes should not be empty"


class TestFileCopy:
    """Test file copy via MCP."""

    def test_file_copy(
        self, mcp_session, filemgmt_test_dir, created_files
    ):
        """powerscale_file_copy copies a file to a new location."""
        src_path = f"{filemgmt_test_dir}/original.txt"
        dest_path = f"{filemgmt_test_dir}/copy.txt"
        created_files.append(src_path)
        created_files.append(dest_path)
        content = "original content"

        mcp_session("powerscale_file_create", {
            "path": src_path,
            "contents": content,
        })

        # Copy source must use /namespace/ prefix
        result = mcp_session("powerscale_file_copy", {
            "source": f"/namespace/{src_path}",
            "destination": dest_path,
        })
        assert_result_is_dict(result, "file_copy")
        assert result.get("success") is True, f"File copy failed: {result}"

        # Verify copy has same content
        read_result = mcp_session("powerscale_file_read", {
            "path": dest_path,
        })
        actual = _strip_json_quotes(read_result.get("contents", ""))
        assert actual == content, (
            f"Copy content mismatch: expected {content!r}, got {actual!r}"
        )


class TestFileMove:
    """Test file move/rename via MCP."""

    def test_file_move(
        self, mcp_session, filemgmt_test_dir, created_files
    ):
        """powerscale_file_move renames a file."""
        src_path = f"{filemgmt_test_dir}/before_move.txt"
        dest_path = f"{filemgmt_test_dir}/after_move.txt"
        # Only register dest since src gets moved
        created_files.append(dest_path)
        content = "move me"

        mcp_session("powerscale_file_create", {
            "path": src_path,
            "contents": content,
        })

        # Move destination must use /namespace/ prefix
        result = mcp_session("powerscale_file_move", {
            "path": src_path,
            "destination": f"/namespace/{dest_path}",
        })
        assert_result_is_dict(result, "file_move")
        assert result.get("success") is True, f"File move failed: {result}"

        # Verify destination has correct content
        read_result = mcp_session("powerscale_file_read", {
            "path": dest_path,
        })
        actual = _strip_json_quotes(read_result.get("contents", ""))
        assert actual == content


class TestFileDelete:
    """Test file deletion via MCP."""

    def test_file_delete(self, mcp_session, filemgmt_test_dir):
        """powerscale_file_delete removes a file."""
        file_path = f"{filemgmt_test_dir}/to_delete.txt"

        # Create file
        mcp_session("powerscale_file_create", {
            "path": file_path,
            "contents": "delete me",
        })

        # Delete
        result = mcp_session("powerscale_file_delete", {
            "path": file_path,
        })
        assert_result_is_dict(result, "file_delete")
        assert result.get("success") is True, f"File delete failed: {result}"

        # Verify deleted: listing parent should not show the file
        list_result = mcp_session("powerscale_directory_list", {
            "path": filemgmt_test_dir,
        })
        child_names = [c.get("name") for c in list_result.get("children", [])]
        assert "to_delete.txt" not in child_names, (
            f"File still present after deletion: {child_names}"
        )
