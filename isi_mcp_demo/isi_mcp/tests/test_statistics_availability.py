"""Tests for statistics availability checking in Statistics module."""
import pytest
from unittest.mock import Mock, patch, MagicMock

pytestmark = [pytest.mark.func_statistics, pytest.mark.group_statistics, pytest.mark.read]


from modules.onefs.v9_12_0.statistics import Statistics
from isilon_sdk.v9_12_0.rest import ApiException


class MockCluster:
    """Mock cluster for testing."""
    def __init__(self, api_client=None):
        self.debug = False
        self.api_client = api_client or Mock()


class TestStatisticsAvailability:
    """Test suite for statistics availability checking."""

    def test_check_node_stats_available_with_per_node_data(self):
        """Test that node stats are detected as available when per-node data exists."""
        # Create mock stats with node data (devid is not None)
        mock_stat = Mock()
        mock_stat.devid = 1
        mock_stat.key = "node.load.1min"
        mock_stat.value = "2.5"

        mock_result = Mock()
        mock_result.stats = [mock_stat]

        mock_api = Mock()
        mock_api.get_statistics_current.return_value = mock_result

        with patch('isilon_sdk.v9_12_0.StatisticsApi', return_value=mock_api):
            stats = Statistics(MockCluster())
            available = stats._check_node_stats_available()
            assert available is True

    def test_check_node_stats_available_without_per_node_data(self):
        """Test that node stats are detected as unavailable when no per-node data."""
        # Create mock result with cluster aggregate only (devid is None)
        mock_stat = Mock()
        mock_stat.devid = None
        mock_stat.key = "cluster.load.1min"
        mock_stat.value = "2.5"

        mock_result = Mock()
        mock_result.stats = [mock_stat]

        mock_api = Mock()
        mock_api.get_statistics_current.return_value = mock_result

        with patch('isilon_sdk.v9_12_0.StatisticsApi', return_value=mock_api):
            stats = Statistics(MockCluster())
            available = stats._check_node_stats_available()
            assert available is False

    def test_check_node_stats_available_empty_result(self):
        """Test that node stats are unavailable when result is empty."""
        mock_result = Mock()
        mock_result.stats = []

        mock_api = Mock()
        mock_api.get_statistics_current.return_value = mock_result

        with patch('isilon_sdk.v9_12_0.StatisticsApi', return_value=mock_api):
            stats = Statistics(MockCluster())
            available = stats._check_node_stats_available()
            assert available is False

    def test_check_node_stats_available_api_error(self):
        """Test that node stats are unavailable when API call fails."""
        mock_api = Mock()
        mock_api.get_statistics_current.side_effect = ApiException("API Error")

        with patch('isilon_sdk.v9_12_0.StatisticsApi', return_value=mock_api):
            stats = Statistics(MockCluster())
            available = stats._check_node_stats_available()
            assert available is False

    def test_get_node_performance_includes_warning_when_unavailable(self):
        """Test that get_node_performance includes warning when stats unavailable."""
        # Mock _fetch_averaged to return empty result (no node entries)
        stats = Statistics(MockCluster())

        with patch.object(stats, '_fetch_averaged', return_value={}):
            result = stats.get_node_performance()
            assert "_warning" in result
            assert "not available" in result["_warning"].lower() or "unavailable" in result["_warning"].lower()
            assert "virtual cluster" in result["_warning"].lower()

    def test_get_node_performance_no_warning_when_available(self):
        """Test that get_node_performance doesn't warn when stats are available."""
        # Mock _fetch_averaged to return node data
        mock_result = {
            "node_1": {"node.load.1min": 2.5},
            "node_2": {"node.load.1min": 1.8}
        }

        stats = Statistics(MockCluster())

        with patch.object(stats, '_fetch_averaged', return_value=mock_result):
            result = stats.get_node_performance()
            assert "_warning" not in result
            assert "node_1" in result
            assert "node_2" in result

    def test_get_node_performance_warning_includes_alternatives(self):
        """Test that warning mentions alternative statistics tools."""
        stats = Statistics(MockCluster())

        with patch.object(stats, '_fetch_averaged', return_value={}):
            result = stats.get_node_performance()
            warning = result["_warning"]
            assert "cluster-level statistics" in warning.lower()
            assert "powerscale_stats" in warning.lower()

    def test_get_node_performance_preserves_error(self):
        """Test that errors from _fetch_averaged are preserved."""
        stats = Statistics(MockCluster())
        error_result = {"error": "API connection failed"}

        with patch.object(stats, '_fetch_averaged', return_value=error_result):
            result = stats.get_node_performance()
            assert "error" in result
            assert result["error"] == "API connection failed"
            # No warning should be added when there's an error
            assert "_warning" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
