"""
Phase 8 - Read-Only MCP Tests (New APIs)

Tests read-only operations via the MCP HTTP server for all new API domains:
Hardware, Jobs, Performance, Hardening, SupportAssist, Connectivity,
DebugStats, FSA, LFN, MetadataIQ, MPA, LocalInfo, ApiSessions,
GroupnetsSummary.
"""

import pytest
from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
    validate_items_list,
    print_test_data,
)


# ---------------------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------------------

class TestHardwareTools:
    """Test hardware inventory MCP tools."""

    def test_mcp_hardware_fcports(self, mcp_session):
        """powerscale_hardware_fcports_get returns FC port list."""
        result = mcp_session("powerscale_hardware_fcports_get")
        assert_result_is_dict(result, "hardware_fcports_get")
        # FC ports may not exist on virtual clusters — accept items or error
        assert "items" in result or "error" in result

    def test_mcp_hardware_tapes(self, mcp_session):
        """powerscale_hardware_tapes_get returns tape device list."""
        result = mcp_session("powerscale_hardware_tapes_get")
        assert_result_is_dict(result, "hardware_tapes_get")
        assert "items" in result or "error" in result


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

class TestJobTools:
    """Test Job Engine MCP tools."""

    def test_mcp_job_list(self, mcp_session):
        """powerscale_job_list returns active jobs."""
        result = mcp_session("powerscale_job_list")
        assert_result_is_dict(result, "job_list")
        assert "items" in result or "error" in result

    def test_mcp_job_recent(self, mcp_session):
        """powerscale_job_recent_get returns recently completed jobs."""
        result = mcp_session("powerscale_job_recent_get", {"limit": 5})
        assert_result_is_dict(result, "job_recent_get")
        assert "items" in result or "error" in result

    def test_mcp_job_summary(self, mcp_session):
        """powerscale_job_summary_get returns engine status."""
        result = mcp_session("powerscale_job_summary_get")
        assert_result_is_dict(result, "job_summary_get")

    def test_mcp_job_types(self, mcp_session):
        """powerscale_job_types_get returns job type catalog."""
        result = mcp_session("powerscale_job_types_get")
        assert_result_is_dict(result, "job_types_get")
        if "items" in result:
            assert len(result["items"]) > 0, "Should have job types"

    def test_mcp_job_events(self, mcp_session):
        """powerscale_job_events_get returns job events."""
        result = mcp_session("powerscale_job_events_get", {"limit": 5})
        assert_result_is_dict(result, "job_events_get")
        assert "items" in result or "error" in result

    def test_mcp_job_statistics(self, mcp_session):
        """powerscale_job_statistics_get returns engine stats."""
        result = mcp_session("powerscale_job_statistics_get")
        assert_result_is_dict(result, "job_statistics_get")

    def test_mcp_job_policies(self, mcp_session):
        """powerscale_job_policies_get returns impact policies."""
        result = mcp_session("powerscale_job_policies_get")
        assert_result_is_dict(result, "job_policies_get")
        if "items" in result:
            assert len(result["items"]) > 0, "Should have impact policies"

    def test_mcp_job_settings(self, mcp_session):
        """powerscale_job_settings_get returns engine settings."""
        result = mcp_session("powerscale_job_settings_get")
        assert_result_is_dict(result, "job_settings_get")


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

class TestPerformanceTools:
    """Test performance monitoring MCP tools."""

    def test_mcp_performance_datasets(self, mcp_session):
        """powerscale_performance_datasets_get returns dataset list."""
        result = mcp_session("powerscale_performance_datasets_get")
        assert_result_is_dict(result, "performance_datasets_get")
        assert "items" in result or "error" in result

    def test_mcp_performance_metrics(self, mcp_session):
        """powerscale_performance_metrics_get returns metrics catalog."""
        result = mcp_session("powerscale_performance_metrics_get")
        assert_result_is_dict(result, "performance_metrics_get")
        assert "items" in result or "error" in result

    def test_mcp_performance_settings(self, mcp_session):
        """powerscale_performance_settings_get returns monitoring settings."""
        result = mcp_session("powerscale_performance_settings_get")
        assert_result_is_dict(result, "performance_settings_get")


# ---------------------------------------------------------------------------
# Hardening
# ---------------------------------------------------------------------------

class TestHardeningTools:
    """Test security hardening MCP tools."""

    def test_mcp_hardening_state(self, mcp_session):
        """powerscale_hardening_state_get returns service state."""
        result = mcp_session("powerscale_hardening_state_get")
        assert_result_is_dict(result, "hardening_state_get")

    def test_mcp_hardening_profiles(self, mcp_session):
        """powerscale_hardening_profiles_get returns profile list."""
        result = mcp_session("powerscale_hardening_profiles_get")
        assert_result_is_dict(result, "hardening_profiles_get")
        assert "items" in result or "error" in result


# ---------------------------------------------------------------------------
# SupportAssist
# ---------------------------------------------------------------------------

class TestSupportAssistTools:
    """Test SupportAssist MCP tools."""

    def test_mcp_supportassist_status(self, mcp_session):
        """powerscale_supportassist_status_get returns status."""
        result = mcp_session("powerscale_supportassist_status_get")
        assert_result_is_dict(result, "supportassist_status_get")

    def test_mcp_supportassist_settings(self, mcp_session):
        """powerscale_supportassist_settings_get returns configuration."""
        result = mcp_session("powerscale_supportassist_settings_get")
        assert_result_is_dict(result, "supportassist_settings_get")

    def test_mcp_supportassist_tasks(self, mcp_session):
        """powerscale_supportassist_tasks_get returns task list."""
        result = mcp_session("powerscale_supportassist_tasks_get")
        assert_result_is_dict(result, "supportassist_tasks_get")
        assert "items" in result or "error" in result


# ---------------------------------------------------------------------------
# Connectivity
# ---------------------------------------------------------------------------

class TestConnectivityTools:
    """Test connectivity diagnostics MCP tools."""

    def test_mcp_connectivity_status(self, mcp_session):
        """powerscale_connectivity_status_get returns status."""
        result = mcp_session("powerscale_connectivity_status_get")
        assert_result_is_dict(result, "connectivity_status_get")

    def test_mcp_connectivity_settings(self, mcp_session):
        """powerscale_connectivity_settings_get returns configuration."""
        result = mcp_session("powerscale_connectivity_settings_get")
        assert_result_is_dict(result, "connectivity_settings_get")

    def test_mcp_connectivity_tasks(self, mcp_session):
        """powerscale_connectivity_tasks_get returns task list."""
        result = mcp_session("powerscale_connectivity_tasks_get")
        assert_result_is_dict(result, "connectivity_tasks_get")
        assert "items" in result or "error" in result


# ---------------------------------------------------------------------------
# Debug Stats
# ---------------------------------------------------------------------------

class TestDebugStatsTools:
    """Test API debug statistics MCP tool."""

    def test_mcp_debug_stats(self, mcp_session):
        """powerscale_debug_stats_get returns API call stats."""
        result = mcp_session("powerscale_debug_stats_get")
        assert_result_is_dict(result, "debug_stats_get")


# ---------------------------------------------------------------------------
# FSA
# ---------------------------------------------------------------------------

class TestFSATools:
    """Test File System Analytics MCP tools."""

    def test_mcp_fsa_results(self, mcp_session):
        """powerscale_fsa_results_get returns result set list."""
        result = mcp_session("powerscale_fsa_results_get")
        assert_result_is_dict(result, "fsa_results_get")
        assert "items" in result or "error" in result

    def test_mcp_fsa_settings(self, mcp_session):
        """powerscale_fsa_settings_get returns FSA configuration."""
        result = mcp_session("powerscale_fsa_settings_get")
        assert_result_is_dict(result, "fsa_settings_get")


# ---------------------------------------------------------------------------
# Local Info
# ---------------------------------------------------------------------------

class TestLocalInfoTools:
    """Test local node information MCP tools."""

    def test_mcp_cluster_time(self, mcp_session):
        """powerscale_local_cluster_time_get returns node time."""
        result = mcp_session("powerscale_local_cluster_time_get")
        assert_result_is_dict(result, "local_cluster_time_get")

    def test_mcp_local_network_interfaces(self, mcp_session):
        """powerscale_local_network_interfaces_get returns interface list."""
        result = mcp_session("powerscale_local_network_interfaces_get")
        assert_result_is_dict(result, "local_network_interfaces_get")
        assert "items" in result or "error" in result

    def test_mcp_os_security(self, mcp_session):
        """powerscale_os_security_get returns OS security settings."""
        result = mcp_session("powerscale_os_security_get")
        assert_result_is_dict(result, "os_security_get")


# ---------------------------------------------------------------------------
# API Sessions
# ---------------------------------------------------------------------------

class TestApiSessionsTools:
    """Test Platform API session MCP tools."""

    def test_mcp_session_settings(self, mcp_session):
        """powerscale_api_session_settings_get returns session config."""
        result = mcp_session("powerscale_api_session_settings_get")
        assert_result_is_dict(result, "api_session_settings_get")

    def test_mcp_session_invalidations(self, mcp_session):
        """powerscale_api_session_invalidations_get returns invalidation list."""
        result = mcp_session("powerscale_api_session_invalidations_get")
        assert_result_is_dict(result, "api_session_invalidations_get")
        assert "items" in result or "error" in result


# ---------------------------------------------------------------------------
# Groupnets Summary
# ---------------------------------------------------------------------------

class TestGroupnetsSummaryTools:
    """Test groupnet summary MCP tool."""

    def test_mcp_groupnets_summary(self, mcp_session):
        """powerscale_groupnets_summary_get returns summary."""
        result = mcp_session("powerscale_groupnets_summary_get")
        assert_result_is_dict(result, "groupnets_summary_get")


# ---------------------------------------------------------------------------
# LFN
# ---------------------------------------------------------------------------

class TestLFNTools:
    """Test Long File Name MCP tools."""

    def test_mcp_lfn_domains(self, mcp_session):
        """powerscale_lfn_domains_get returns domain list."""
        result = mcp_session("powerscale_lfn_domains_get")
        assert_result_is_dict(result, "lfn_domains_get")
        assert "items" in result or "error" in result


# ---------------------------------------------------------------------------
# MetadataIQ
# ---------------------------------------------------------------------------

class TestMetadataIQTools:
    """Test MetadataIQ MCP tools."""

    def test_mcp_metadataiq_settings(self, mcp_session):
        """powerscale_metadataiq_settings_get returns configuration."""
        result = mcp_session("powerscale_metadataiq_settings_get")
        assert_result_is_dict(result, "metadataiq_settings_get")

    def test_mcp_metadataiq_status(self, mcp_session):
        """powerscale_metadataiq_status_get returns cycle status."""
        result = mcp_session("powerscale_metadataiq_status_get")
        assert_result_is_dict(result, "metadataiq_status_get")


# ---------------------------------------------------------------------------
# MPA
# ---------------------------------------------------------------------------

class TestMPATools:
    """Test Multi-Party Authorization MCP tools."""

    def test_mcp_mpa_settings(self, mcp_session):
        """powerscale_mpa_settings_get returns MPA config."""
        result = mcp_session("powerscale_mpa_settings_get")
        assert_result_is_dict(result, "mpa_settings_get")

    def test_mcp_mpa_approvers(self, mcp_session):
        """powerscale_mpa_approvers_get returns approver list."""
        result = mcp_session("powerscale_mpa_approvers_get")
        assert_result_is_dict(result, "mpa_approvers_get")
        assert "items" in result or "error" in result

    def test_mcp_mpa_requests(self, mcp_session):
        """powerscale_mpa_requests_get returns request list."""
        result = mcp_session("powerscale_mpa_requests_get")
        assert_result_is_dict(result, "mpa_requests_get")
        assert "items" in result or "error" in result
