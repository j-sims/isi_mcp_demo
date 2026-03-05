"""
IAC_MODE tests — verify AnsibleRunner behaviour with and without IAC_MODE.

These are Part 1 (direct module) tests: they import AnsibleRunner directly,
use a real Cluster connection to render a template, and check the response
shape returned by execute().

Part A — IAC_MODE disabled (default)
    Verifies that execute() delegates to run_playbook() (ansible-runner is invoked).

Part B — IAC_MODE enabled
    Verifies that execute() renders and writes the playbook but does NOT call
    run_playbook(), and returns the expected IaC-mode response dict.
"""

import os
import sys
import importlib
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# test_nfs_client_validation.py installs a session-level Mock for modules.ansible.runner
# (sys.modules['modules.ansible.runner'] = Mock()) so that file can skip the ansible
# import.  Since that file runs before this one in the full test suite, we must evict
# the mock and force-import the real module before any AnsibleRunner reference below.
sys.modules.pop('modules.ansible.runner', None)

from modules.ansible.runner import AnsibleRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_runner_result():
    """Return a MagicMock shaped like a successful ansible-runner result."""
    m = MagicMock()
    m.status = "successful"
    m.rc = 0
    m.stdout = None
    m.stderr = None
    m.events = []
    return m


# ---------------------------------------------------------------------------
# Part A — Normal mode (IAC_MODE not set / falsy)
# ---------------------------------------------------------------------------

class TestAnsibleRunnerNormalMode:
    """AnsibleRunner.execute() in default mode delegates to run_playbook()."""

    pytestmark = [pytest.mark.func_snapshots, pytest.mark.group_snapshots, pytest.mark.write]

    def test_execute_calls_run_playbook(self, cluster, tmp_path):
        """When IAC_MODE is not set, execute() calls run_playbook()."""
        runner = AnsibleRunner(cluster, playbooks_dir=tmp_path)

        # Patch run_playbook on the instance so we don't need a live cluster call
        expected = {"success": True, "status": "successful", "rc": 0, "playbook_path": "x"}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IAC_MODE", None)
            with patch.object(runner, "run_playbook", return_value=expected) as mock_rp:
                result = runner.execute("snapshot_create.yml.j2", {
                    "path": "/ifs/test",
                    "snapshot_name": "test-snapshot",
                })

        mock_rp.assert_called_once()
        assert "iac_mode" not in result
        assert result["success"] is True

    def test_execute_iac_mode_false_string_calls_run_playbook(self, cluster, tmp_path):
        """IAC_MODE=false must NOT suppress run_playbook() invocation."""
        runner = AnsibleRunner(cluster, playbooks_dir=tmp_path)

        expected = {"success": True, "status": "successful", "rc": 0, "playbook_path": "x"}
        with patch.dict(os.environ, {"IAC_MODE": "false"}):
            with patch.object(runner, "run_playbook", return_value=expected) as mock_rp:
                result = runner.execute("snapshot_create.yml.j2", {
                    "path": "/ifs/test",
                    "snapshot_name": "test-snapshot",
                })

        mock_rp.assert_called_once()
        assert "iac_mode" not in result

    def test_execute_iac_mode_empty_string_calls_run_playbook(self, cluster, tmp_path):
        """IAC_MODE='' (empty) must NOT suppress run_playbook() invocation."""
        runner = AnsibleRunner(cluster, playbooks_dir=tmp_path)

        expected = {"success": True, "status": "successful", "rc": 0, "playbook_path": "x"}
        with patch.dict(os.environ, {"IAC_MODE": ""}):
            with patch.object(runner, "run_playbook", return_value=expected) as mock_rp:
                result = runner.execute("snapshot_create.yml.j2", {
                    "path": "/ifs/test",
                    "snapshot_name": "test-snapshot",
                })

        mock_rp.assert_called_once()
        assert "iac_mode" not in result


# ---------------------------------------------------------------------------
# Part B — IAC_MODE enabled
# ---------------------------------------------------------------------------

class TestAnsibleRunnerIacMode:
    """AnsibleRunner.execute() in IAC_MODE skips run_playbook() entirely."""

    pytestmark = [pytest.mark.func_snapshots, pytest.mark.group_snapshots, pytest.mark.write]

    @pytest.mark.parametrize("iac_value", ["true", "1", "yes", "True", "TRUE", "YES"])
    def test_execute_iac_mode_skips_run_playbook(self, cluster, tmp_path, iac_value):
        """When IAC_MODE is truthy, execute() renders playbook but does NOT call run_playbook()."""
        runner = AnsibleRunner(cluster, playbooks_dir=tmp_path)

        with patch.dict(os.environ, {"IAC_MODE": iac_value}):
            with patch.object(runner, "run_playbook") as mock_rp:
                result = runner.execute("snapshot_create.yml.j2", {
                    "path": "/ifs/test",
                    "snapshot_name": "test-snapshot-iac",
                })

        # run_playbook must NOT have been called
        mock_rp.assert_not_called()

        # Response shape
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert result["iac_mode"] is True
        assert result["success"] is True
        assert "playbook_path" in result
        assert "message" in result

        # The message should mention IAC_MODE and external workflow
        assert "IAC_MODE" in result["message"]
        assert "playbook" in result["message"].lower()

        # The playbook file must exist on disk (rendering happened)
        playbook_path = Path(result["playbook_path"])
        assert playbook_path.exists(), f"Expected playbook to exist at {playbook_path}"
        assert playbook_path.stat().st_size > 0, "Playbook file should not be empty"

    def test_execute_iac_mode_playbook_content(self, cluster, tmp_path):
        """The generated playbook must be valid YAML with expected PowerScale fields."""
        import yaml

        runner = AnsibleRunner(cluster, playbooks_dir=tmp_path)

        with patch.dict(os.environ, {"IAC_MODE": "true"}):
            result = runner.execute("snapshot_create.yml.j2", {
                "path": "/ifs/iac-test",
                "snapshot_name": "iac-test-snapshot",
            })

        assert isinstance(result, dict)
        assert result.get("iac_mode") is True

        playbook_path = Path(result["playbook_path"])
        content = playbook_path.read_text()

        # Must be valid YAML
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, list), "Playbook should be a YAML list (play list)"

        # Should reference the PowerScale collection
        assert "dellemc.powerscale" in content or "powerscale" in content.lower()

        # Connection host placeholder should be present
        assert "onefs_host" in content
        # Credential placeholders (not real values) should appear
        assert "api_user" in content
        assert "api_password" in content

    def test_execute_iac_mode_no_cluster_credentials_in_playbook(self, cluster, tmp_path):
        """Rendered playbook must never contain real cluster credentials.

        Uses a synthetic Cluster-like mock with a long, unique sentinel password
        so the assertion is always meaningful regardless of the real test cluster
        credentials (which may be short, e.g. 'a').
        """
        SENTINEL_PASSWORD = "UNIQUE_SENTINEL_PASSWORD_ZXQ9182736"
        SENTINEL_USER = "UNIQUE_SENTINEL_USER_ABC4567890"

        fake_cluster = MagicMock()
        fake_cluster.host = cluster.host
        fake_cluster.port = cluster.port
        fake_cluster.verify_ssl = cluster.verify_ssl
        fake_cluster.username = SENTINEL_USER
        fake_cluster.password = SENTINEL_PASSWORD
        fake_cluster.debug = False

        runner = AnsibleRunner(fake_cluster, playbooks_dir=tmp_path)

        with patch.dict(os.environ, {"IAC_MODE": "true"}):
            result = runner.execute("snapshot_create.yml.j2", {
                "path": "/ifs/sec-test",
                "snapshot_name": "sec-test",
            })

        content = Path(result["playbook_path"]).read_text()
        assert SENTINEL_PASSWORD not in content, "Sentinel password must not appear in rendered playbook"
        assert SENTINEL_USER not in content, "Sentinel username must not appear in rendered playbook"
        # Placeholders should be present instead
        assert "{{ api_user }}" in content
        assert "{{ api_password }}" in content
