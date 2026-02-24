"""
Part 1 — Direct module tests.

These tests import each v9_12_0 module, connect to a real PowerScale cluster
via the Cluster class, and call read-only get() functions to verify data is
returned in the expected format.

Run from the isi_mcp/ directory:
    pytest tests/test_modules.py -v
"""

from modules.onefs.v9_12_0.cluster import Cluster
from modules.onefs.v9_12_0.health import Health
from modules.onefs.v9_12_0.capacity import Capacity
from modules.onefs.v9_12_0.quotas import Quotas
from modules.onefs.v9_12_0.smb import Smb
from modules.onefs.v9_12_0.snapshots import Snapshots
from modules.onefs.v9_12_0.synciq import SyncIQ
from modules.onefs.v9_12_0.nfs import Nfs
from modules.onefs.v9_12_0.s3 import S3
from modules.ansible.runner import AnsibleRunner


# ---------------------------------------------------------------------------
# Cluster connectivity
# ---------------------------------------------------------------------------

class TestCluster:

    def test_cluster_connection(self, cluster):
        """Cluster() should create a usable api_client."""
        assert cluster.api_client is not None
        assert cluster.url is not None


# ---------------------------------------------------------------------------
# Health & Capacity (automation modules — unique return shapes)
# ---------------------------------------------------------------------------

class TestHealth:

    def test_health_check(self, cluster):
        """Health.check() returns {status: bool, message: str}."""
        health = Health(cluster)
        result = health.check()
        assert isinstance(result, dict)
        assert "status" in result
        assert "message" in result
        assert isinstance(result["status"], bool)
        assert isinstance(result["message"], str)


class TestCapacity:

    def test_capacity_get(self, cluster):
        """Capacity.get() returns a dict with expected stat keys."""
        capacity = Capacity(cluster)
        result = capacity.get()
        assert isinstance(result, dict)
        expected_keys = [
            "ifs.bytes.avail",
            "ifs.bytes.used",
            "ifs.bytes.total",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Middleware modules — all return {"items": list, ...}
# ---------------------------------------------------------------------------

class TestQuotas:

    def test_quotas_get(self, cluster):
        """Quotas.get() returns {items: list, resume: ...}."""
        quotas = Quotas(cluster)
        result = quotas.get()
        assert isinstance(result, dict)
        assert "items" in result
        assert isinstance(result["items"], list)
        assert "resume" in result


class TestSmb:

    def test_smb_get(self, cluster):
        """Smb.get() returns {items: list, resume: ...}."""
        smb = Smb(cluster)
        result = smb.get()
        assert isinstance(result, dict)
        assert "items" in result
        assert isinstance(result["items"], list)
        assert "resume" in result


class TestSnapshots:

    def test_snapshots_get(self, cluster):
        """Snapshots.get() returns {items: list, resume: ...}."""
        snapshots = Snapshots(cluster)
        result = snapshots.get()
        assert isinstance(result, dict)
        assert "items" in result
        assert isinstance(result["items"], list)
        assert "resume" in result


class TestSyncIQ:

    def test_synciq_get(self, cluster):
        """SyncIQ.get() returns {items: list}."""
        synciq = SyncIQ(cluster)
        result = synciq.get()
        assert isinstance(result, dict)
        assert "items" in result
        assert isinstance(result["items"], list)


class TestNfs:

    def test_nfs_get(self, cluster):
        """Nfs.get() returns {items: list, resume: ...}."""
        nfs = Nfs(cluster)
        result = nfs.get()
        assert isinstance(result, dict)
        assert "items" in result
        assert isinstance(result["items"], list)
        assert "resume" in result


class TestS3:

    def test_s3_get(self, cluster):
        """S3.get() returns {items: list, resume: ...}."""
        s3 = S3(cluster)
        result = s3.get()
        assert isinstance(result, dict)
        assert "items" in result
        assert isinstance(result["items"], list)
        assert "resume" in result


# ---------------------------------------------------------------------------
# Ansible Runner
# ---------------------------------------------------------------------------

class TestAnsibleRunner:

    def test_runner_initialization(self, cluster):
        """AnsibleRunner should initialize with valid cluster."""
        runner = AnsibleRunner(cluster)
        assert runner.templates_dir.exists()
        assert runner.playbooks_dir.exists()

    def test_render_playbook(self, cluster):
        """AnsibleRunner should render a template to a YAML file."""
        runner = AnsibleRunner(cluster)
        playbook_path = runner.render_playbook("smb_create.yml.j2", {
            "share_name": "test_render",
            "path": "/ifs/data/test_render",
        })
        assert playbook_path.exists()
        content = playbook_path.read_text()
        assert "test_render" in content
        assert "state: present" in content
        # Clean up
        playbook_path.unlink()
