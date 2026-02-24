"""
Part 2 — MCP server tests.

These tests call each MCP tool through the running HTTP server at
http://localhost:8000 using the JSON-RPC protocol.

Prerequisites:
    docker-compose up --build -d

Run from the isi_mcp/ directory:
    pytest tests/test_mcp_server.py -v
"""

import pytest


# ---------------------------------------------------------------------------
# Tool listing
# ---------------------------------------------------------------------------

class TestToolsList:

    def test_mcp_tools_list(self, mcp_session):
        """Server should expose all expected tools."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        expected = [
            "current_time",
            "powerscale_check_health",
            "powerscale_capacity",
            "powerscale_quota_get",
            "powerscale_quota_set",
            "powerscale_quota_increment",
            "powerscale_quota_decrement",
            "powerscale_snapshot_get",
            "powerscale_synciq_get",
            "powerscale_nfs_get",
            "powerscale_s3_get",
            "bytes_to_human",
            "human_to_bytes",
            "powerscale_smb_create",
            "powerscale_smb_remove",
            "powerscale_nfs_create",
            "powerscale_nfs_remove",
            "powerscale_s3_create",
            "powerscale_s3_remove",
            "powerscale_snapshot_schedule_create",
            "powerscale_snapshot_schedule_remove",
            "powerscale_synciq_create",
            "powerscale_synciq_remove",
            "powerscale_quota_create",
            "powerscale_quota_remove",
        ]

        for name in expected:
            assert name in tool_names, f"Missing tool: {name}"


# ---------------------------------------------------------------------------
# Utility tools (no cluster needed)
# ---------------------------------------------------------------------------

class TestUtilityTools:

    def test_mcp_current_time(self, mcp_session):
        """current_time returns date, time, timezone, gmt_offset."""
        result = mcp_session("current_time")
        assert isinstance(result, dict)
        assert "date" in result
        assert "time" in result
        assert "timezone" in result
        assert "gmt_offset" in result

    def test_mcp_bytes_to_human(self, mcp_session):
        """bytes_to_human converts 84079902720 to ~78.31GiB."""
        result = mcp_session("bytes_to_human", {"bytes_value": 84079902720})
        assert isinstance(result, dict)
        assert "bytes" in result
        assert "human_readable" in result
        assert result["bytes"] == 84079902720
        assert "GiB" in result["human_readable"]

    def test_mcp_human_to_bytes(self, mcp_session):
        """human_to_bytes converts '78.31GiB' back to bytes."""
        result = mcp_session("human_to_bytes", {"human_value": "78.31GiB"})
        assert isinstance(result, dict)
        assert "bytes" in result
        assert "human_readable" in result
        assert isinstance(result["bytes"], int)
        assert result["bytes"] > 0


# ---------------------------------------------------------------------------
# Cluster tools (require live PowerScale)
# ---------------------------------------------------------------------------

class TestHealthTool:

    def test_mcp_check_health(self, mcp_session):
        """powerscale_check_health returns status and message."""
        result = mcp_session("powerscale_check_health")
        assert isinstance(result, dict)
        assert "status" in result
        assert "message" in result


class TestCapacityTool:

    def test_mcp_capacity(self, mcp_session):
        """powerscale_capacity returns capacity stat keys."""
        result = mcp_session("powerscale_capacity")
        assert isinstance(result, dict)
        expected_keys = [
            "ifs.bytes.avail",
            "ifs.bytes.used",
            "ifs.bytes.total",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"


class TestQuotaTool:

    def test_mcp_quota_get(self, mcp_session):
        """powerscale_quota_get returns paginated items."""
        result = mcp_session("powerscale_quota_get")
        assert isinstance(result, dict)
        assert "items" in result
        assert isinstance(result["items"], list)
        assert "resume" in result
        assert "has_more" in result


class TestSnapshotTool:

    def test_mcp_snapshot_get(self, mcp_session):
        """powerscale_snapshot_get returns paginated items."""
        result = mcp_session("powerscale_snapshot_get")
        assert isinstance(result, dict)
        assert "items" in result
        assert isinstance(result["items"], list)
        assert "resume" in result
        assert "has_more" in result


class TestSyncIQTool:

    def test_mcp_synciq_get(self, mcp_session):
        """powerscale_synciq_get returns items list."""
        result = mcp_session("powerscale_synciq_get")
        assert isinstance(result, dict)
        assert "items" in result
        assert isinstance(result["items"], list)


class TestNfsTool:

    def test_mcp_nfs_get(self, mcp_session):
        """powerscale_nfs_get returns paginated items."""
        result = mcp_session("powerscale_nfs_get")
        assert isinstance(result, dict)
        assert "items" in result
        assert isinstance(result["items"], list)
        assert "resume" in result
        assert "has_more" in result


class TestS3Tool:

    def test_mcp_s3_get(self, mcp_session):
        """powerscale_s3_get returns paginated items."""
        result = mcp_session("powerscale_s3_get")
        assert isinstance(result, dict)
        assert "items" in result
        assert isinstance(result["items"], list)
        assert "resume" in result
        assert "has_more" in result
