"""
Phase 1 - Read-Only Domain Module Tests

Tests read-only operations by calling domain modules directly.
These tests validate SDK integration and data format expectations.

Tests:
- Cluster connectivity
- Config (cluster info, hardware)
- Capacity (storage stats)
- Quotas (quota listing, pagination)
- Snapshots (snapshot listing)
- NFS/SMB (export/share listing)
- S3 (bucket listing)
"""

import pytest
from modules.onefs.v9_12_0.config import Config
from modules.onefs.v9_12_0.capacity import Capacity
from modules.onefs.v9_12_0.quotas import Quotas
from modules.onefs.v9_12_0.snapshots import Snapshots
from modules.onefs.v9_12_0.snapshotschedules import SnapshotSchedules
from modules.onefs.v9_12_0.nfs import Nfs
from modules.onefs.v9_12_0.smb import Smb
from modules.onefs.v9_12_0.s3 import S3
from modules.onefs.v9_12_0.datamover import DataMover
from modules.onefs.v9_12_0.filepool import FilePool

from tests.test_utils import (
    validate_items_list, validate_pagination,
    print_test_data
)


# ---------------------------------------------------------------------------
# Cluster Connectivity
# ---------------------------------------------------------------------------

class TestClusterConnectivity:
    """Test cluster connection via test_cluster_direct fixture."""
    pytestmark = [pytest.mark.func_verify, pytest.mark.group_verify, pytest.mark.read]

    def test_cluster_connection(self, test_cluster_direct):
        """Cluster() should create a usable api_client."""
        assert test_cluster_direct.api_client is not None, \
            "api_client must not be None"
        assert test_cluster_direct.url is not None, \
            "url must not be None"
        assert "172.16.10.10" in test_cluster_direct.url or \
               "http" in test_cluster_direct.url, \
            f"url should contain host, got: {test_cluster_direct.url}"


# ---------------------------------------------------------------------------
# Config Module Tests
# ---------------------------------------------------------------------------

class TestConfig:
    """Test cluster configuration retrieval."""
    pytestmark = [pytest.mark.func_capacity, pytest.mark.group_capacity, pytest.mark.read]

    def test_config_get(self, test_cluster_direct):
        """Config.get() returns cluster configuration."""
        config = Config(test_cluster_direct)
        result = config.get()

        # Verify structure
        assert isinstance(result, dict), "Config.get() must return dict"
        assert result.get("name"), "Cluster must have 'name'"
        assert result.get("guid"), "Cluster must have 'guid'"

    def test_config_get_hardware_info(self, test_cluster_direct):
        """Config.get_hardware_info() returns hardware details."""
        config = Config(test_cluster_direct)
        result = config.get_hardware_info()

        # Verify structure
        assert isinstance(result, dict), "get_hardware_info() must return dict"

        # Should have hardware info
        has_hardware = (
            result.get("attributes") or
            result.get("nodes") or
            len(result) > 0
        )
        assert has_hardware, \
            f"Hardware info must not be empty, got keys: {list(result.keys())}"


# ---------------------------------------------------------------------------
# Capacity Module Tests
# ---------------------------------------------------------------------------

class TestCapacity:
    """Test storage capacity retrieval."""
    pytestmark = [pytest.mark.func_capacity, pytest.mark.group_capacity, pytest.mark.read]

    def test_capacity_get(self, test_cluster_direct):
        """Capacity.get() returns storage capacity stats."""
        capacity = Capacity(test_cluster_direct)
        result = capacity.get()

        # Verify structure
        assert isinstance(result, dict), "Capacity.get() must return dict"

        # Verify required keys
        expected_keys = [
            "ifs.bytes.avail",
            "ifs.bytes.used",
            "ifs.bytes.total",
        ]
        for key in expected_keys:
            assert key in result, f"Missing capacity key: {key}"

    def test_capacity_values_reasonable(self, test_cluster_direct):
        """Capacity values should be reasonable."""
        capacity = Capacity(test_cluster_direct)
        result = capacity.get()

        avail = result.get("ifs.bytes.avail", 0)
        used = result.get("ifs.bytes.used", 0)
        total = result.get("ifs.bytes.total", 0)

        # Basic sanity checks
        assert avail > 0, "Available must be > 0"
        assert used >= 0, "Used must be >= 0"
        assert total > avail, "Total must be > available"


# ---------------------------------------------------------------------------
# Quotas Module Tests
# ---------------------------------------------------------------------------

class TestQuotas:
    """Test quota listing and pagination."""
    pytestmark = [pytest.mark.func_quotas, pytest.mark.group_quotas, pytest.mark.read]

    def test_quotas_get(self, test_cluster_direct):
        """Quotas.get() returns paginated quota list."""
        quotas = Quotas(test_cluster_direct)
        result = quotas.get()

        # Verify structure
        assert isinstance(result, dict), "Quotas.get() must return dict"

        # Verify pagination
        items = validate_items_list(result, "Quotas.get")
        resume, has_more = validate_pagination(result, "Quotas.get")

        # If quotas exist, verify format
        if items:
            quota = items[0]
            assert isinstance(quota, dict), "Quota must be dict"
            assert "path" in quota or "id" in quota, \
                "Quota must have 'path' or 'id'"

    def test_quotas_pagination(self, test_cluster_direct):
        """Quotas.get() supports pagination with small limit."""
        quotas = Quotas(test_cluster_direct)

        # First page with small limit
        result1 = quotas.get(limit=5)
        items1 = result1.get("items", [])
        resume1 = result1.get("resume")

        # If we got results and there's a resume token, can get next page
        if items1 and resume1:
            result2 = quotas.get(limit=5, resume=resume1)
            items2 = result2.get("items", [])

            # Items should be different
            if items1 and items2:
                ids1 = [q.get("id") or q.get("path") for q in items1]
                ids2 = [q.get("id") or q.get("path") for q in items2]
                assert ids1 != ids2, "Pages should have different items"


# ---------------------------------------------------------------------------
# Snapshots Module Tests
# ---------------------------------------------------------------------------

class TestSnapshots:
    """Test snapshot listing."""
    pytestmark = [pytest.mark.func_snapshots, pytest.mark.group_snapshots, pytest.mark.read]

    def test_snapshots_get(self, test_cluster_direct):
        """Snapshots.get() returns snapshot list."""
        snapshots = Snapshots(test_cluster_direct)
        result = snapshots.get()

        # Verify structure
        assert isinstance(result, dict), "Snapshots.get() must return dict"

        # Verify pagination
        items = validate_items_list(result, "Snapshots.get")
        resume, has_more = validate_pagination(result, "Snapshots.get")

        # If snapshots exist, verify format
        if items:
            snap = items[0]
            assert isinstance(snap, dict), "Snapshot must be dict"
            assert "name" in snap, "Snapshot must have 'name'"

    def test_snapshot_schedules_get(self, test_cluster_direct):
        """SnapshotSchedules.get() returns schedules."""
        schedules = SnapshotSchedules(test_cluster_direct)
        result = schedules.get()

        # Verify structure
        assert isinstance(result, dict), "SnapshotSchedules.get() must return dict"

        # Verify pagination
        items = validate_items_list(result, "SnapshotSchedules.get")
        resume, has_more = validate_pagination(result, "SnapshotSchedules.get")


# ---------------------------------------------------------------------------
# NFS Module Tests
# ---------------------------------------------------------------------------

class TestNfs:
    """Test NFS export listing and global settings."""
    pytestmark = [pytest.mark.func_nfs, pytest.mark.group_nfs, pytest.mark.read]

    def test_nfs_get(self, test_cluster_direct):
        """Nfs.get() returns NFS export list."""
        nfs = Nfs(test_cluster_direct)
        result = nfs.get()

        # Verify structure
        assert isinstance(result, dict), "Nfs.get() must return dict"

        # Verify pagination
        items = validate_items_list(result, "Nfs.get")
        resume, has_more = validate_pagination(result, "Nfs.get")

        # If exports exist, verify format
        if items:
            export = items[0]
            assert isinstance(export, dict), "Export must be dict"

    def test_nfs_global_settings_get(self, test_cluster_direct):
        """Nfs.get_global_settings() returns NFS configuration."""
        nfs = Nfs(test_cluster_direct)
        result = nfs.get_global_settings()

        # Verify structure
        assert isinstance(result, dict), "get_global_settings() must return dict"
        assert len(result) > 0, "NFS settings should not be empty"


# ---------------------------------------------------------------------------
# SMB Module Tests
# ---------------------------------------------------------------------------

class TestSmb:
    """Test SMB share listing and global settings."""
    pytestmark = [pytest.mark.func_smb, pytest.mark.group_smb, pytest.mark.read]

    def test_smb_get(self, test_cluster_direct):
        """Smb.get() returns SMB share list."""
        smb = Smb(test_cluster_direct)
        result = smb.get()

        # Verify structure
        assert isinstance(result, dict), "Smb.get() must return dict"

        # Verify pagination
        items = validate_items_list(result, "Smb.get")
        resume, has_more = validate_pagination(result, "Smb.get")

        # If shares exist, verify format
        if items:
            share = items[0]
            assert isinstance(share, dict), "Share must be dict"

    def test_smb_global_settings_get(self, test_cluster_direct):
        """Smb.get_global_settings() returns SMB configuration."""
        smb = Smb(test_cluster_direct)
        result = smb.get_global_settings()

        # Verify structure
        assert isinstance(result, dict), "get_global_settings() must return dict"
        assert len(result) > 0, "SMB settings should not be empty"


# ---------------------------------------------------------------------------
# S3 Module Tests
# ---------------------------------------------------------------------------

class TestS3:
    """Test S3 bucket listing."""
    pytestmark = [pytest.mark.func_s3, pytest.mark.group_s3, pytest.mark.read]

    def test_s3_get(self, test_cluster_direct):
        """S3.get() returns S3 bucket list."""
        s3 = S3(test_cluster_direct)
        result = s3.get()

        # Verify structure
        assert isinstance(result, dict), "S3.get() must return dict"

        # Verify pagination
        items = validate_items_list(result, "S3.get")
        resume, has_more = validate_pagination(result, "S3.get")

        # If buckets exist, verify format
        if items:
            bucket = items[0]
            assert isinstance(bucket, dict), "Bucket must be dict"


# ---------------------------------------------------------------------------
# DataMover Module Tests
# ---------------------------------------------------------------------------

class TestDataMover:
    """Test DataMover policy and account listing."""
    pytestmark = [pytest.mark.func_datamover, pytest.mark.group_datamover, pytest.mark.read]

    def test_datamover_get_policies(self, test_cluster_direct):
        """DataMover.get_policies() returns policies."""
        dm = DataMover(test_cluster_direct)
        result = dm.get_policies()

        # Verify structure
        assert isinstance(result, dict), "get_policies() must return dict"

        # Verify pagination
        items = validate_items_list(result, "DataMover.get_policies")
        resume, has_more = validate_pagination(result, "DataMover.get_policies")

    def test_datamover_get_accounts(self, test_cluster_direct):
        """DataMover.get_accounts() returns accounts."""
        dm = DataMover(test_cluster_direct)
        result = dm.get_accounts()

        # Verify structure
        assert isinstance(result, dict), "get_accounts() must return dict"

        # Verify pagination
        items = validate_items_list(result, "DataMover.get_accounts")
        resume, has_more = validate_pagination(result, "DataMover.get_accounts")

    def test_datamover_get_base_policies(self, test_cluster_direct):
        """DataMover.get_base_policies() returns base policies."""
        dm = DataMover(test_cluster_direct)
        result = dm.get_base_policies()

        # Verify structure
        assert isinstance(result, dict), "get_base_policies() must return dict"

        # Verify pagination
        items = validate_items_list(result, "DataMover.get_base_policies")
        resume, has_more = validate_pagination(result, "DataMover.get_base_policies")


# ---------------------------------------------------------------------------
# FilePool Module Tests
# ---------------------------------------------------------------------------

class TestFilePool:
    """Test FilePool policy listing."""
    pytestmark = [pytest.mark.func_filepool, pytest.mark.group_filepool, pytest.mark.read]

    def test_filepool_get(self, test_cluster_direct):
        """FilePool.get() returns policies."""
        fp = FilePool(test_cluster_direct)
        result = fp.get()

        # Verify structure
        assert isinstance(result, dict), "FilePool.get() must return dict"

        # FilePool may use different structure
        if "items" in result:
            items = result["items"]
            assert isinstance(items, list), "items must be list"

    def test_filepool_get_default_policy(self, test_cluster_direct):
        """FilePool.get_default_policy() returns default policy."""
        fp = FilePool(test_cluster_direct)
        result = fp.get_default_policy()

        # Verify structure
        assert isinstance(result, dict), "get_default_policy() must return dict"
