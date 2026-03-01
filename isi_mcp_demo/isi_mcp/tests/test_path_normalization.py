"""Tests for path normalization in FileMgmt module."""
import pytest

pytestmark = [pytest.mark.func_filemgmt, pytest.mark.group_filemgmt, pytest.mark.read]

from modules.onefs.v9_12_0.filemgmt import FileMgmt


class MockCluster:
    """Mock cluster for testing without API calls."""
    def __init__(self):
        self.debug = False
        self.api_client = None


def test_normalize_path_no_slash():
    """Test path without leading slash."""
    fm = FileMgmt(MockCluster())
    assert fm._normalize_path("ifs/data/projects") == "ifs/data/projects"


def test_normalize_path_with_leading_slash():
    """Test path with leading slash."""
    fm = FileMgmt(MockCluster())
    assert fm._normalize_path("/ifs/data/projects") == "ifs/data/projects"


def test_normalize_path_with_double_leading_slash():
    """Test path with double leading slash."""
    fm = FileMgmt(MockCluster())
    assert fm._normalize_path("//ifs/data/projects") == "ifs/data/projects"


def test_normalize_path_with_trailing_slash():
    """Test path with trailing slash."""
    fm = FileMgmt(MockCluster())
    assert fm._normalize_path("ifs/data/projects/") == "ifs/data/projects"


def test_normalize_path_with_both_slashes():
    """Test path with both leading and trailing slashes."""
    fm = FileMgmt(MockCluster())
    assert fm._normalize_path("/ifs/data/projects/") == "ifs/data/projects"


def test_normalize_path_empty():
    """Test empty path."""
    fm = FileMgmt(MockCluster())
    assert fm._normalize_path("") == ""


def test_normalize_path_root():
    """Test root path."""
    fm = FileMgmt(MockCluster())
    assert fm._normalize_path("/") == ""


def test_normalize_path_single_component():
    """Test path with single component."""
    fm = FileMgmt(MockCluster())
    assert fm._normalize_path("ifs") == "ifs"
    assert fm._normalize_path("/ifs") == "ifs"


def test_normalize_path_relative_path():
    """Test relative path without ifs prefix."""
    fm = FileMgmt(MockCluster())
    assert fm._normalize_path("data/projects") == "data/projects"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
