"""
Phase 4 - Cleanup Fixtures and Utilities

Provides pytest fixtures for managing resources created during Phase 4
advanced mutation tests (FileMgmt, DataMover, FilePool).

Resources tracked and cleaned up:
- Test directories (created/copied/moved via FileMgmt SDK)
- Test files (created/copied/moved via FileMgmt SDK)
- Access points (created via FileMgmt SDK)
- FilePool policies (created via Ansible, deleted via Ansible)
- DataMover policies (created/deleted via SDK)
- DataMover accounts (created/deleted via SDK)
- DataMover base policies (created/deleted via SDK)

Usage in tests:
    def test_something(self, mcp_session, created_directories):
        path = "ifs/data/test_abc12345"
        created_directories.append(path)
        result = mcp_session("powerscale_directory_create", {"path": path})
"""

import uuid
import pytest
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException

from modules.onefs.v9_12_0.filemgmt import FileMgmt
from modules.onefs.v9_12_0.filepool import FilePool
from modules.onefs.v9_12_0.datamover import DataMover


def _unique_name(prefix="test"):
    """Generate a unique resource name with 8-char UUID hex suffix."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Directory Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_directories(mcp_session):
    """
    Track and cleanup directories created during tests.

    Tests append paths (without leading slash, e.g. "ifs/data/test_abc")
    to the returned list. Cleanup deletes recursively via MCP.
    """
    paths = []
    yield paths

    if not paths:
        return

    for path in reversed(paths):  # reverse to delete children first
        try:
            mcp_session("powerscale_directory_delete", {
                "path": path,
                "recursive": True,
            })
            print(f"\nCleaned up directory: {path}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup directory '{path}': {e}")


# ---------------------------------------------------------------------------
# File Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_files(mcp_session):
    """
    Track and cleanup files created during tests.

    Tests append paths (without leading slash, e.g. "ifs/data/test.txt")
    to the returned list. Cleanup deletes via MCP.
    """
    paths = []
    yield paths

    if not paths:
        return

    for path in paths:
        try:
            mcp_session("powerscale_file_delete", {"path": path})
            print(f"\nCleaned up file: {path}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup file '{path}': {e}")


# ---------------------------------------------------------------------------
# Access Point Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_access_points(mcp_session):
    """
    Track and cleanup access points created during tests.

    Tests append access point names to the returned list.
    Cleanup deletes via MCP.
    """
    names = []
    yield names

    if not names:
        return

    for name in names:
        try:
            mcp_session("powerscale_access_point_delete", {"name": name})
            print(f"\nCleaned up access point: {name}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup access point '{name}': {e}")


# ---------------------------------------------------------------------------
# FilePool Policy Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_filepool_policies(test_cluster_direct):
    """
    Track and cleanup FilePool policies created during tests.

    Tests append policy names to the returned list.
    Cleanup calls FilePool.delete() (Ansible-based).
    """
    policy_names = []
    yield policy_names

    if not policy_names:
        return

    filepool = FilePool(test_cluster_direct)
    for name in policy_names:
        try:
            result = filepool.delete(policy_name=name)
            if result.get("success"):
                print(f"\nCleaned up FilePool policy: {name}")
            else:
                print(f"\nWarning: FilePool policy removal may have failed for '{name}': {result}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup FilePool policy '{name}': {e}")


# ---------------------------------------------------------------------------
# DataMover Policy Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_datamover_policies(test_cluster_direct):
    """
    Track and cleanup DataMover policies created during tests.

    Tests append policy IDs/names to the returned list.
    Cleanup calls DataMover.delete_policy() (SDK-based).
    """
    policy_ids = []
    yield policy_ids

    if not policy_ids:
        return

    dm = DataMover(test_cluster_direct)
    for pid in policy_ids:
        try:
            result = dm.delete_policy(str(pid))
            if result.get("success"):
                print(f"\nCleaned up DataMover policy: {pid}")
            else:
                print(f"\nWarning: DataMover policy removal may have failed for '{pid}': {result}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup DataMover policy '{pid}': {e}")


# ---------------------------------------------------------------------------
# DataMover Account Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_datamover_accounts(test_cluster_direct):
    """
    Track and cleanup DataMover accounts created during tests.

    Tests append account IDs/names to the returned list.
    Cleanup calls DataMover.delete_account() (SDK-based).
    """
    account_ids = []
    yield account_ids

    if not account_ids:
        return

    dm = DataMover(test_cluster_direct)
    for aid in account_ids:
        try:
            result = dm.delete_account(str(aid))
            if result.get("success"):
                print(f"\nCleaned up DataMover account: {aid}")
            else:
                print(f"\nWarning: DataMover account removal may have failed for '{aid}': {result}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup DataMover account '{aid}': {e}")


# ---------------------------------------------------------------------------
# DataMover Base Policy Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def created_datamover_base_policies(test_cluster_direct):
    """
    Track and cleanup DataMover base policies created during tests.

    Tests append base policy IDs/names to the returned list.
    Cleanup calls DataMover.delete_base_policy() (SDK-based).
    """
    bp_ids = []
    yield bp_ids

    if not bp_ids:
        return

    dm = DataMover(test_cluster_direct)
    for bpid in bp_ids:
        try:
            result = dm.delete_base_policy(str(bpid))
            if result.get("success"):
                print(f"\nCleaned up DataMover base policy: {bpid}")
            else:
                print(f"\nWarning: DataMover base policy removal may have failed for '{bpid}': {result}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup DataMover base policy '{bpid}': {e}")


# ---------------------------------------------------------------------------
# Composite fixture: test directory with file inside
# ---------------------------------------------------------------------------

@pytest.fixture
def filemgmt_test_dir(mcp_session):
    """
    Create a unique test directory and yield its path (no leading slash).

    Automatically creates and cleans up the directory. Use this for tests
    that need a directory to work with.

    Yields the path without leading slash (e.g. "ifs/data/test_fm_abc12345").
    """
    suffix = uuid.uuid4().hex[:8]
    api_path = f"ifs/data/test_fm_{suffix}"

    try:
        result = mcp_session("powerscale_directory_create", {
            "path": api_path,
            "recursive": True,
        })
        if not (isinstance(result, dict) and result.get("success")):
            pytest.skip(f"Could not create test directory: {result}")
    except AssertionError as e:
        pytest.skip(f"powerscale_directory_create not available: {e}")

    yield api_path

    try:
        mcp_session("powerscale_directory_delete", {
            "path": api_path,
            "recursive": True,
        })
        print(f"\nCleaned up test dir: /{api_path}")
    except Exception as e:
        print(f"\nWarning: Failed to cleanup test dir '/{api_path}': {e}")
