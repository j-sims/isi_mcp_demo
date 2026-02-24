import os
import sys
import json
import pytest
import httpx
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Auto-discover fixtures from phase-specific fixture modules
pytest_plugins = ["tests.test_phase2_fixtures", "tests.test_phase3_fixtures", "tests.test_phase4_fixtures"]

# Ensure the isi_mcp package root is on sys.path so "modules.*" imports work
ISI_MCP_DIR = Path(__file__).resolve().parent.parent
if str(ISI_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(ISI_MCP_DIR))

# Load .env from the project root (two levels above isi_mcp/)
PROJECT_ROOT = ISI_MCP_DIR.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

import isilon_sdk.v9_12_0 as isi_sdk
from modules.onefs.v9_12_0.cluster import Cluster
from modules.network.utils import pingable

# ---------------------------------------------------------------------------
# Test Cluster Configuration
# ---------------------------------------------------------------------------
TEST_CLUSTER_HOST = os.getenv("TEST_CLUSTER_HOST", "172.16.10.10")
TEST_CLUSTER_PORT = os.getenv("TEST_CLUSTER_PORT", 8080)
TEST_CLUSTER_USERNAME = os.getenv("TEST_CLUSTER_USERNAME", "root")
TEST_CLUSTER_PASSWORD = os.getenv("TEST_CLUSTER_PASSWORD", "a")
TEST_CLUSTER_VERIFY_SSL = os.getenv("TEST_CLUSTER_VERIFY_SSL", "false").lower() == "true"


# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def cluster():
    """Create a single Cluster instance for all module tests (uses vault/env)."""
    return Cluster()


@pytest.fixture(scope="session", autouse=True)
def validate_test_environment():
    """
    Verify test cluster is accessible and enable all tools for testing.
    Skips all tests if cluster is unreachable.
    """
    host_for_ping = TEST_CLUSTER_HOST
    try:
        # Try to ping the cluster
        if not pingable(host_for_ping, timeout=5):
            pytest.skip(
                f"Test cluster {host_for_ping} is not reachable. "
                f"Verify the cluster is online and network connectivity is available."
            )

        # Try to create API client
        c = Cluster(
            host=f"https://{TEST_CLUSTER_HOST}",
            port=TEST_CLUSTER_PORT,
            username=TEST_CLUSTER_USERNAME,
            password=TEST_CLUSTER_PASSWORD,
            verify_ssl=TEST_CLUSTER_VERIFY_SSL
        )
        assert c.api_client is not None, "Failed to create API client"
        print(f"\n✓ Test cluster {TEST_CLUSTER_HOST} is accessible and ready")
        yield
    except Exception as e:
        pytest.skip(
            f"Test cluster {TEST_CLUSTER_HOST} validation failed: {e}"
        )


@pytest.fixture(scope="session")
def test_cluster_direct():
    """
    Create a direct Cluster instance for Phase 1+ tests.
    Uses explicit test cluster configuration (not vault).
    """
    return Cluster(
        host=f"https://{TEST_CLUSTER_HOST}",
        port=TEST_CLUSTER_PORT,
        username=TEST_CLUSTER_USERNAME,
        password=TEST_CLUSTER_PASSWORD,
        verify_ssl=TEST_CLUSTER_VERIFY_SSL
    )


@pytest.fixture
def synciq_available(test_cluster_direct):
    """
    Skip the test if the SyncIQ service is not enabled on the cluster.

    Checks sync/settings service field via SDK:
      "on"     - service running, proceed
      "paused" - service paused, skip
      "off"    - service disabled, skip

    Usage:
        def test_something(self, mcp_session, synciq_available):
            ...
    """
    sync_api = isi_sdk.SyncApi(test_cluster_direct.api_client)
    try:
        settings = sync_api.get_sync_settings()
        service = settings.settings.service
    except Exception as e:
        pytest.skip(f"Could not determine SyncIQ service state: {e}")

    if service != "on":
        pytest.skip(
            f"SyncIQ service is '{service}' (not 'on'). "
            f"Enable with: isi services -a isi_migrate enable && "
            f"isi sync settings modify --service on"
        )


@pytest.fixture
def test_path():
    """
    Generate a unique test path with UUID suffix.
    Used for creating test files/directories on the cluster.
    """
    return f"/ifs/data/test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def cleanup_test_resources():
    """
    Auto-cleanup fixture that runs after each test.
    Subclass or override in specific test modules for cleanup logic.
    """
    yield  # Test runs here
    # Base fixture does nothing - child fixtures override for specific cleanup


# ---------------------------------------------------------------------------
# MCP server fixtures
# ---------------------------------------------------------------------------

MCP_BASE_URL = os.environ.get("MCP_BASE_URL", "http://localhost:8000")
MCP_ENDPOINT = f"{MCP_BASE_URL}/mcp"

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def _parse_response(resp) -> dict:
    """Parse an MCP HTTP response, handling both JSON and SSE formats."""
    content_type = resp.headers.get("content-type", "")

    # Plain JSON response
    if "application/json" in content_type:
        return resp.json()

    # SSE response — extract the JSON from "data: {...}" lines
    if "text/event-stream" in content_type or resp.text.startswith("event:"):
        for line in resp.text.splitlines():
            if line.startswith("data: "):
                return json.loads(line[6:])

    # Fallback: try parsing the whole body
    return resp.json()


@pytest.fixture(scope="session")
def mcp_url():
    return MCP_ENDPOINT


@pytest.fixture(scope="session")
def mcp_session(mcp_url):
    """
    Initialize an MCP session and return a helper callable.

    Usage in tests:
        result = mcp_session("tool_name", {"arg": "value"})
    """
    client = httpx.Client(timeout=30.0)
    _request_id = 0

    def _next_id():
        nonlocal _request_id
        _request_id += 1
        return _request_id

    # Send initialize handshake
    init_resp = client.post(
        mcp_url,
        headers=MCP_HEADERS,
        json={
            "jsonrpc": "2.0",
            "id": _next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "1.0.0"},
            },
        },
    )
    assert init_resp.status_code == 200, f"MCP init failed: {init_resp.text}"

    # Parse init response (may be SSE) and capture session id
    _parse_response(init_resp)
    session_id = init_resp.headers.get("Mcp-Session-Id")
    if session_id:
        MCP_HEADERS["Mcp-Session-Id"] = session_id

    # Send initialized notification
    client.post(
        mcp_url,
        headers=MCP_HEADERS,
        json={
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        },
    )

    def call_tool(name: str, arguments: dict | None = None) -> dict:
        """Call an MCP tool and return the parsed result."""
        resp = client.post(
            mcp_url,
            headers=MCP_HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": _next_id(),
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments or {},
                },
            },
        )
        assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
        body = _parse_response(resp)
        assert "result" in body, f"No result in response: {body}"
        assert body["result"].get("isError") is not True, (
            f"Tool returned error: {body['result']}"
        )

        # Parse the text content back into a Python object
        content = body["result"]["content"]
        assert len(content) > 0, "Empty content in response"
        text = content[0]["text"]
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text

    def list_tools() -> list:
        """List all available MCP tools."""
        resp = client.post(
            mcp_url,
            headers=MCP_HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": _next_id(),
                "method": "tools/list",
                "params": {},
            },
        )
        assert resp.status_code == 200
        body = _parse_response(resp)
        return body["result"]["tools"]

    call_tool.list_tools = list_tools
    call_tool.client = client

    yield call_tool

    client.close()
