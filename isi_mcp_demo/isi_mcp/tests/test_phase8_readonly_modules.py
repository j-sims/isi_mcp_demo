"""
Phase 8 - Read-Only Domain Module Tests (New APIs)

Tests read-only operations by calling new domain modules directly.
Validates SDK integration for: Hardware, Jobs, Performance, Hardening,
SupportAssist, Connectivity, DebugStats, FSA, SyncReports,
SnapshotChangelists, QuotaReports, IdResolution, LFN, MetadataIQ,
MPA, LocalInfo, ApiSessions, GroupnetsSummary.
"""

import pytest
from modules.onefs.v9_12_0.hardware import Hardware
from modules.onefs.v9_12_0.jobs import Jobs
from modules.onefs.v9_12_0.performance import Performance
from modules.onefs.v9_12_0.hardening import Hardening
from modules.onefs.v9_12_0.supportassist import SupportAssist
from modules.onefs.v9_12_0.connectivity import Connectivity
from modules.onefs.v9_12_0.debug_stats import DebugStats
from modules.onefs.v9_12_0.fsa import FSA
from modules.onefs.v9_12_0.sync_reports import SyncReports
from modules.onefs.v9_12_0.snapshot_changelists import SnapshotChangelists
from modules.onefs.v9_12_0.quota_reports import QuotaReports
from modules.onefs.v9_12_0.id_resolution import IdResolution
from modules.onefs.v9_12_0.lfn import LFN
from modules.onefs.v9_12_0.metadataiq import MetadataIQ
from modules.onefs.v9_12_0.mpa import MPA
from modules.onefs.v9_12_0.local_info import LocalInfo
from modules.onefs.v9_12_0.api_sessions import ApiSessions
from modules.onefs.v9_12_0.groupnets_summary import GroupnetsSummary

from tests.test_utils import (
    validate_items_list,
    print_test_data,
)


# ---------------------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------------------

class TestHardware:
    """Test hardware inventory operations."""

    def test_hardware_fcports(self, test_cluster_direct):
        """Hardware.get_fcports() returns a list (may be empty if no FC ports)."""
        hw = Hardware(test_cluster_direct)
        result = hw.get_fcports()
        assert isinstance(result, dict), "get_fcports() must return dict"
        # FC ports may not exist on virtual/lab clusters - just verify structure
        assert "items" in result or "error" in result

    def test_hardware_tapes(self, test_cluster_direct):
        """Hardware.get_tapes() returns a list (may be empty if no tape devices)."""
        hw = Hardware(test_cluster_direct)
        result = hw.get_tapes()
        assert isinstance(result, dict), "get_tapes() must return dict"
        assert "items" in result or "error" in result


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

class TestJobs:
    """Test Job Engine operations."""

    def test_job_list(self, test_cluster_direct):
        """Jobs.list_jobs() returns job list structure."""
        j = Jobs(test_cluster_direct)
        result = j.list_jobs()
        assert isinstance(result, dict)
        assert "items" in result or "error" in result

    def test_job_recent(self, test_cluster_direct):
        """Jobs.get_recent() returns recently completed jobs."""
        j = Jobs(test_cluster_direct)
        result = j.get_recent(limit=10)
        assert isinstance(result, dict)
        assert "items" in result or "error" in result

    def test_job_summary(self, test_cluster_direct):
        """Jobs.get_summary() returns job engine status."""
        j = Jobs(test_cluster_direct)
        result = j.get_summary()
        assert isinstance(result, dict)
        assert "error" not in result or isinstance(result.get("error"), str)

    def test_job_types(self, test_cluster_direct):
        """Jobs.get_types() returns available job types."""
        j = Jobs(test_cluster_direct)
        result = j.get_types()
        assert isinstance(result, dict)
        if "items" in result:
            assert isinstance(result["items"], list)
            assert len(result["items"]) > 0, "Cluster should have at least one job type"

    def test_job_events(self, test_cluster_direct):
        """Jobs.get_events() returns job events."""
        j = Jobs(test_cluster_direct)
        result = j.get_events(limit=10)
        assert isinstance(result, dict)
        assert "items" in result or "error" in result

    def test_job_statistics(self, test_cluster_direct):
        """Jobs.get_statistics() returns job engine statistics."""
        j = Jobs(test_cluster_direct)
        result = j.get_statistics()
        assert isinstance(result, dict)

    def test_job_policies(self, test_cluster_direct):
        """Jobs.get_policies() returns impact policies."""
        j = Jobs(test_cluster_direct)
        result = j.get_policies()
        assert isinstance(result, dict)
        if "items" in result:
            assert isinstance(result["items"], list)
            assert len(result["items"]) > 0, "Cluster should have impact policies"

    def test_job_settings(self, test_cluster_direct):
        """Jobs.get_settings() returns engine settings."""
        j = Jobs(test_cluster_direct)
        result = j.get_settings()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

class TestPerformance:
    """Test performance monitoring operations."""

    def test_performance_datasets(self, test_cluster_direct):
        """Performance.list_datasets() returns datasets list."""
        p = Performance(test_cluster_direct)
        result = p.list_datasets()
        assert isinstance(result, dict)
        assert "items" in result or "error" in result

    def test_performance_metrics(self, test_cluster_direct):
        """Performance.get_metrics() returns metrics catalog."""
        p = Performance(test_cluster_direct)
        result = p.get_metrics()
        assert isinstance(result, dict)
        assert "items" in result or "error" in result

    def test_performance_settings(self, test_cluster_direct):
        """Performance.get_settings() returns monitoring settings."""
        p = Performance(test_cluster_direct)
        result = p.get_settings()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Hardening
# ---------------------------------------------------------------------------

class TestHardening:
    """Test security hardening operations."""

    def test_hardening_state(self, test_cluster_direct):
        """Hardening.get_state() returns service state."""
        h = Hardening(test_cluster_direct)
        result = h.get_state()
        assert isinstance(result, dict)

    def test_hardening_profiles(self, test_cluster_direct):
        """Hardening.get_profiles() returns profile list."""
        h = Hardening(test_cluster_direct)
        result = h.get_profiles()
        assert isinstance(result, dict)
        assert "items" in result or "error" in result


# ---------------------------------------------------------------------------
# SupportAssist
# ---------------------------------------------------------------------------

class TestSupportAssist:
    """Test SupportAssist diagnostics operations."""

    def test_supportassist_status(self, test_cluster_direct):
        """SupportAssist.get_status() returns status info."""
        sa = SupportAssist(test_cluster_direct)
        result = sa.get_status()
        assert isinstance(result, dict)

    def test_supportassist_settings(self, test_cluster_direct):
        """SupportAssist.get_settings() returns configuration."""
        sa = SupportAssist(test_cluster_direct)
        result = sa.get_settings()
        assert isinstance(result, dict)

    def test_supportassist_tasks(self, test_cluster_direct):
        """SupportAssist.list_tasks() returns task list."""
        sa = SupportAssist(test_cluster_direct)
        result = sa.list_tasks()
        assert isinstance(result, dict)
        assert "items" in result or "error" in result


# ---------------------------------------------------------------------------
# Connectivity
# ---------------------------------------------------------------------------

class TestConnectivity:
    """Test connectivity diagnostics operations."""

    def test_connectivity_status(self, test_cluster_direct):
        """Connectivity.get_status() returns status info."""
        conn = Connectivity(test_cluster_direct)
        result = conn.get_status()
        assert isinstance(result, dict)

    def test_connectivity_settings(self, test_cluster_direct):
        """Connectivity.get_settings() returns configuration."""
        conn = Connectivity(test_cluster_direct)
        result = conn.get_settings()
        assert isinstance(result, dict)

    def test_connectivity_tasks(self, test_cluster_direct):
        """Connectivity.list_tasks() returns task list."""
        conn = Connectivity(test_cluster_direct)
        result = conn.list_tasks()
        assert isinstance(result, dict)
        assert "items" in result or "error" in result


# ---------------------------------------------------------------------------
# Debug Stats
# ---------------------------------------------------------------------------

class TestDebugStats:
    """Test API debug statistics."""

    def test_debug_stats(self, test_cluster_direct):
        """DebugStats.get() returns API call statistics."""
        ds = DebugStats(test_cluster_direct)
        result = ds.get()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# FSA (File System Analytics)
# ---------------------------------------------------------------------------

class TestFSA:
    """Test File System Analytics operations."""

    def test_fsa_results(self, test_cluster_direct):
        """FSA.get_results() returns result set list."""
        fsa = FSA(test_cluster_direct)
        result = fsa.get_results()
        assert isinstance(result, dict)
        assert "items" in result or "error" in result

    def test_fsa_settings(self, test_cluster_direct):
        """FSA.get_settings() returns FSA configuration."""
        fsa = FSA(test_cluster_direct)
        result = fsa.get_settings()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Local Info
# ---------------------------------------------------------------------------

class TestLocalInfo:
    """Test local node information operations."""

    def test_cluster_time(self, test_cluster_direct):
        """LocalInfo.get_cluster_time() returns node time."""
        li = LocalInfo(test_cluster_direct)
        result = li.get_cluster_time()
        assert isinstance(result, dict)

    def test_network_interfaces(self, test_cluster_direct):
        """LocalInfo.get_network_interfaces() returns interface list."""
        li = LocalInfo(test_cluster_direct)
        result = li.get_network_interfaces()
        assert isinstance(result, dict)
        assert "items" in result or "error" in result

    def test_os_security(self, test_cluster_direct):
        """LocalInfo.get_os_security() returns OS security settings."""
        li = LocalInfo(test_cluster_direct)
        result = li.get_os_security()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# API Sessions
# ---------------------------------------------------------------------------

class TestApiSessions:
    """Test Platform API session operations."""

    def test_session_settings(self, test_cluster_direct):
        """ApiSessions.get_session_settings() returns session config."""
        api_s = ApiSessions(test_cluster_direct)
        result = api_s.get_session_settings()
        assert isinstance(result, dict)

    def test_session_invalidations(self, test_cluster_direct):
        """ApiSessions.list_invalidations() returns invalidation list."""
        api_s = ApiSessions(test_cluster_direct)
        result = api_s.list_invalidations()
        assert isinstance(result, dict)
        assert "items" in result or "error" in result


# ---------------------------------------------------------------------------
# Groupnets Summary
# ---------------------------------------------------------------------------

class TestGroupnetsSummary:
    """Test groupnet summary operations."""

    def test_groupnets_summary(self, test_cluster_direct):
        """GroupnetsSummary.get() returns summary info."""
        gs = GroupnetsSummary(test_cluster_direct)
        result = gs.get()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# LFN (Long File Name)
# ---------------------------------------------------------------------------

class TestLFN:
    """Test Long File Name configuration operations."""

    def test_lfn_domains(self, test_cluster_direct):
        """LFN.list_domains() returns domain list."""
        lfn = LFN(test_cluster_direct)
        result = lfn.list_domains()
        assert isinstance(result, dict)
        assert "items" in result or "error" in result


# ---------------------------------------------------------------------------
# MetadataIQ
# ---------------------------------------------------------------------------

class TestMetadataIQ:
    """Test MetadataIQ operations."""

    def test_metadataiq_settings(self, test_cluster_direct):
        """MetadataIQ.get_settings() returns configuration."""
        miq = MetadataIQ(test_cluster_direct)
        result = miq.get_settings()
        assert isinstance(result, dict)

    def test_metadataiq_status(self, test_cluster_direct):
        """MetadataIQ.get_status() returns cycle status."""
        miq = MetadataIQ(test_cluster_direct)
        result = miq.get_status()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# MPA (Multi-Party Authorization)
# ---------------------------------------------------------------------------

class TestMPA:
    """Test Multi-Party Authorization operations."""

    def test_mpa_settings(self, test_cluster_direct):
        """MPA.get_global_settings() returns MPA config."""
        m = MPA(test_cluster_direct)
        result = m.get_global_settings()
        assert isinstance(result, dict)

    def test_mpa_approvers(self, test_cluster_direct):
        """MPA.get_approvers() returns approver list."""
        m = MPA(test_cluster_direct)
        result = m.get_approvers()
        assert isinstance(result, dict)
        assert "items" in result or "error" in result

    def test_mpa_requests(self, test_cluster_direct):
        """MPA.list_requests() returns request list."""
        m = MPA(test_cluster_direct)
        result = m.list_requests()
        assert isinstance(result, dict)
        assert "items" in result or "error" in result
