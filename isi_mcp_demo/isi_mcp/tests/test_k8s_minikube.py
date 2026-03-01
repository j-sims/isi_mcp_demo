"""
K8s / minikube deployment tests.

These tests verify the MCP server running inside minikube is correctly
deployed and functioning.  They connect via `kubectl port-forward` and
exercise the JSON-RPC MCP protocol.

Prerequisites:
    minikube running with the isi-mcp deployment:
        ./k8s/deploy-minikube.sh

Run via the dedicated runner (sets up port-forward automatically):
    ./runtests-k8s.sh

Or manually (with port-forward already running on port 8000):
    MCP_BASE_URL=http://localhost:8000 pytest tests/test_k8s_minikube.py -v

Environment variables:
    MCP_BASE_URL  - MCP server base URL (default: http://localhost:8000)
    K8S_NAMESPACE - K8s namespace to inspect (default: isi-mcp)
"""

import json
import os
import subprocess
import time

import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MCP_BASE_URL = os.environ.get("MCP_BASE_URL", "http://localhost:8000")
MCP_ENDPOINT = f"{MCP_BASE_URL}/mcp"
K8S_NAMESPACE = os.environ.get("K8S_NAMESPACE", "isi-mcp")

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

# Management tools guaranteed to be enabled regardless of cluster availability
MANAGEMENT_TOOLS = [
    "powerscale_tools_list",
    "powerscale_tools_list_by_group",
    "powerscale_tools_list_by_mode",
    "powerscale_tools_toggle",
    "powerscale_cluster_list",
    "powerscale_cluster_select",
]

# Utility tools that need no cluster
UTILITY_TOOLS = [
    "current_time",
    "bytes_to_human",
    "human_to_bytes",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_mcp_response(resp: httpx.Response) -> dict:
    """Parse MCP response: handles both JSON and SSE formats."""
    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        return resp.json()
    # SSE — extract first data: line
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return resp.json()


def _kubectl(*args: str) -> subprocess.CompletedProcess:
    """Run a kubectl command and return the result."""
    cmd = ["kubectl", "--namespace", K8S_NAMESPACE] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# Session-scoped MCP client fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def mcp_client():
    """
    Verify the MCP server is reachable and establish a session.

    Skips the entire module if the server is not reachable.
    """
    client = httpx.Client(timeout=30.0)
    headers = dict(MCP_HEADERS)
    request_id = 0

    def next_id():
        nonlocal request_id
        request_id += 1
        return request_id

    # Check reachability with retries
    MAX_ATTEMPTS = 5
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            init_resp = client.post(
                MCP_ENDPOINT,
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": next_id(),
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest-k8s", "version": "1.0.0"},
                    },
                },
            )
            if init_resp.status_code == 200:
                break
        except httpx.ConnectError:
            if attempt == MAX_ATTEMPTS:
                pytest.skip(
                    f"MCP server at {MCP_ENDPOINT} is not reachable. "
                    "Start port-forward or run ./runtests-k8s.sh"
                )
            time.sleep(2)

    # Capture session ID
    session_id = init_resp.headers.get("Mcp-Session-Id")
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    # Send initialized notification
    client.post(
        MCP_ENDPOINT,
        headers=headers,
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )

    def call_tool(name: str, arguments: dict | None = None) -> dict:
        resp = client.post(
            MCP_ENDPOINT,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": next_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            },
        )
        assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
        body = _parse_mcp_response(resp)
        assert "result" in body, f"No result in response: {body}"
        assert body["result"].get("isError") is not True, (
            f"Tool returned error: {body['result']}"
        )
        content = body["result"]["content"]
        assert len(content) > 0, "Empty content in response"
        text = content[0]["text"]
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text

    def list_tools() -> list[dict]:
        resp = client.post(
            MCP_ENDPOINT,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": next_id(),
                "method": "tools/list",
                "params": {},
            },
        )
        assert resp.status_code == 200
        body = _parse_mcp_response(resp)
        return body["result"]["tools"]

    call_tool.list_tools = list_tools
    call_tool.client = client

    yield call_tool

    client.close()


# ---------------------------------------------------------------------------
# K8s infrastructure tests
# ---------------------------------------------------------------------------

class TestK8sInfrastructure:
    pytestmark = [pytest.mark.func_none, pytest.mark.read]
    """Verify the K8s deployment resources are correctly configured."""

    def test_namespace_exists(self):
        """The isi-mcp namespace must exist."""
        result = subprocess.run(
            ["kubectl", "get", "namespace", K8S_NAMESPACE, "-o", "jsonpath={.metadata.name}"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, (
            f"Namespace '{K8S_NAMESPACE}' does not exist: {result.stderr}"
        )
        assert result.stdout.strip() == K8S_NAMESPACE

    def test_deployment_exists(self):
        """The isi-mcp Deployment must exist."""
        result = _kubectl("get", "deployment", "isi-mcp", "-o", "jsonpath={.metadata.name}")
        assert result.returncode == 0, f"Deployment missing: {result.stderr}"
        assert "isi-mcp" in result.stdout

    def test_deployment_replicas_ready(self):
        """All desired replicas must be in the Ready state."""
        result = _kubectl(
            "get", "deployment", "isi-mcp",
            "-o", "jsonpath={.status.readyReplicas}/{.spec.replicas}",
        )
        assert result.returncode == 0, f"Could not get deployment status: {result.stderr}"
        parts = result.stdout.strip().split("/")
        ready, desired = int(parts[0] or 0), int(parts[1] or 1)
        assert ready >= desired, (
            f"Deployment not fully ready: {ready}/{desired} replicas. "
            f"Check: kubectl get pods -n {K8S_NAMESPACE}"
        )

    def test_pod_running(self):
        """At least one pod must be in Running state."""
        result = _kubectl(
            "get", "pods",
            "-l", "app=isi-mcp",
            "-o", "jsonpath={.items[*].status.phase}",
        )
        assert result.returncode == 0, f"Could not get pod status: {result.stderr}"
        phases = result.stdout.strip().split()
        assert len(phases) > 0, "No pods found for app=isi-mcp"
        assert all(p == "Running" for p in phases), (
            f"Some pods not Running: {phases}"
        )

    def test_service_exists(self):
        """The isi-mcp Service must exist and expose port 8000."""
        result = _kubectl(
            "get", "service", "isi-mcp",
            "-o", "jsonpath={.spec.ports[0].port}",
        )
        assert result.returncode == 0, f"Service missing: {result.stderr}"
        assert result.stdout.strip() == "8000"

    def test_configmap_tools_exists(self):
        """The isi-mcp-tools ConfigMap must exist."""
        result = _kubectl("get", "configmap", "isi-mcp-tools", "-o", "jsonpath={.metadata.name}")
        assert result.returncode == 0, f"ConfigMap missing: {result.stderr}"
        assert "isi-mcp-tools" in result.stdout

    def test_configmap_tools_has_json(self):
        """The ConfigMap must contain valid tools.json."""
        result = _kubectl(
            "get", "configmap", "isi-mcp-tools",
            "-o", "jsonpath={.data.tools\\.json}",
        )
        assert result.returncode == 0, f"Could not read ConfigMap: {result.stderr}"
        tools_json = json.loads(result.stdout)
        assert isinstance(tools_json, dict), "tools.json is not a dict"
        assert len(tools_json) > 0, "tools.json is empty"
        assert "current_time" in tools_json, "Missing 'current_time' tool entry"

    def test_secret_credentials_exists(self):
        """The isi-mcp-credentials Secret must exist."""
        result = _kubectl("get", "secret", "isi-mcp-credentials", "-o", "jsonpath={.metadata.name}")
        assert result.returncode == 0, f"Secret 'isi-mcp-credentials' missing: {result.stderr}"

    def test_secret_vault_exists(self):
        """The isi-mcp-vault Secret must exist with a vault.yml key."""
        result = _kubectl(
            "get", "secret", "isi-mcp-vault",
            "-o", "jsonpath={.data.vault\\.yml}",
        )
        assert result.returncode == 0, f"Secret 'isi-mcp-vault' missing: {result.stderr}"
        assert len(result.stdout.strip()) > 0, "vault.yml key is empty in secret"

    def test_init_container_completed(self):
        """The init-config container must have completed successfully."""
        result = _kubectl(
            "get", "pods",
            "-l", "app=isi-mcp",
            "-o", "jsonpath={.items[0].status.initContainerStatuses[0].state.terminated.exitCode}",
        )
        assert result.returncode == 0
        exit_code = result.stdout.strip()
        assert exit_code == "0", (
            f"init-config container exited with code {exit_code!r}. "
            f"Check: kubectl logs -n {K8S_NAMESPACE} <pod> -c init-config"
        )


# ---------------------------------------------------------------------------
# MCP protocol tests (no cluster required)
# ---------------------------------------------------------------------------

class TestMCPProtocol:
    pytestmark = [pytest.mark.func_none, pytest.mark.read]
    """Verify MCP protocol basics work via the K8s-hosted server."""

    def test_initialize_response_structure(self, mcp_client):
        """MCP initialize must return correct protocol version and server info."""
        # The mcp_client fixture already performed initialize; re-initialize to check response
        resp = mcp_client.client.post(
            MCP_ENDPOINT,
            headers=MCP_HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 999,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "k8s-test", "version": "1.0"},
                },
            },
        )
        assert resp.status_code == 200
        body = _parse_mcp_response(resp)
        result = body["result"]
        assert result["protocolVersion"] == "2025-06-18"
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "powerscale"
        assert "tools" in result["capabilities"]

    def test_tools_list_returns_tools(self, mcp_client):
        """tools/list must return a non-empty list of tools."""
        tools = mcp_client.list_tools()
        assert isinstance(tools, list), "tools/list result is not a list"
        assert len(tools) > 0, "tools/list returned empty list"

    def test_tools_list_count(self, mcp_client):
        """Server must expose at least the utility + management tools."""
        tools = mcp_client.list_tools()
        tool_names = {t["name"] for t in tools}
        expected = set(UTILITY_TOOLS + MANAGEMENT_TOOLS)
        missing = expected - tool_names
        assert not missing, f"Missing tools from list: {missing}"

    def test_tools_list_has_input_schema(self, mcp_client):
        """Each tool entry must have name, description, and inputSchema."""
        tools = mcp_client.list_tools()
        for tool in tools[:10]:  # Spot-check first 10
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool['name']!r} missing 'description'"
            assert "inputSchema" in tool, f"Tool {tool['name']!r} missing 'inputSchema'"

    def test_unknown_tool_returns_error(self, mcp_client):
        """Calling a non-existent tool must return an MCP isError response."""
        # call_tool asserts isError is not True, so unknown tools raise AssertionError
        with pytest.raises(AssertionError, match="Tool returned error"):
            mcp_client("nonexistent_tool_xyz")


# ---------------------------------------------------------------------------
# Utility tool tests (no cluster required)
# ---------------------------------------------------------------------------

class TestUtilityTools:
    pytestmark = [pytest.mark.func_none, pytest.mark.group_utils, pytest.mark.read]
    """Utility tools must work without a PowerScale cluster."""

    def test_current_time(self, mcp_client):
        """current_time returns date, time, timezone, gmt_offset."""
        result = mcp_client("current_time")
        assert isinstance(result, dict)
        assert "date" in result
        assert "time" in result
        assert "timezone" in result
        assert "gmt_offset" in result

    def test_bytes_to_human(self, mcp_client):
        """bytes_to_human converts bytes to IEC string."""
        result = mcp_client("bytes_to_human", {"bytes_value": 1073741824})
        assert isinstance(result, dict)
        assert "bytes" in result
        assert "human_readable" in result
        assert result["bytes"] == 1073741824
        assert "GiB" in result["human_readable"]

    def test_human_to_bytes(self, mcp_client):
        """human_to_bytes converts IEC string to bytes."""
        result = mcp_client("human_to_bytes", {"human_value": "1GiB"})
        assert isinstance(result, dict)
        assert "bytes" in result
        assert result["bytes"] == 1073741824

    def test_bytes_roundtrip(self, mcp_client):
        """bytes_to_human and human_to_bytes are inverse operations."""
        original = 10 * 1024 ** 3  # 10 GiB exactly
        human_result = mcp_client("bytes_to_human", {"bytes_value": original})
        human_str = human_result["human_readable"]
        bytes_result = mcp_client("human_to_bytes", {"human_value": human_str})
        assert bytes_result["bytes"] == original


# ---------------------------------------------------------------------------
# Management tool tests (no cluster required)
# ---------------------------------------------------------------------------

class TestManagementTools:
    pytestmark = [pytest.mark.func_none, pytest.mark.group_management, pytest.mark.read]
    """Management tools must work without a PowerScale cluster."""

    def test_tools_list_flat(self, mcp_client):
        """powerscale_tools_list returns flat tool listing with expected fields."""
        result = mcp_client("powerscale_tools_list")
        assert isinstance(result, list), "Expected list"
        assert len(result) > 0
        first = result[0]
        assert "name" in first
        assert "group" in first
        assert "mode" in first
        assert "enabled" in first

    def test_tools_list_by_group(self, mcp_client):
        """powerscale_tools_list_by_group returns groups dict keyed by group name."""
        result = mcp_client("powerscale_tools_list_by_group")
        assert isinstance(result, dict)
        # Response structure: {"groups": {...}, "total_enabled": N, "total_disabled": N}
        assert "groups" in result, f"Expected 'groups' key, got: {list(result.keys())}"
        groups = result["groups"]
        assert "management" in groups, f"Missing 'management' group, got: {list(groups.keys())}"
        assert "utils" in groups

    def test_tools_list_by_mode(self, mcp_client):
        """powerscale_tools_list_by_mode returns read and write categories."""
        result = mcp_client("powerscale_tools_list_by_mode")
        assert isinstance(result, dict)
        # Response structure: {"by_mode": {"read": [...], "write": [...]}, "read_count": N, "write_count": N}
        assert "by_mode" in result, f"Expected 'by_mode' key, got: {list(result.keys())}"
        by_mode = result["by_mode"]
        assert "read" in by_mode
        assert "write" in by_mode
        assert "read_count" in result
        assert "write_count" in result
        assert result["read_count"] > 0
        assert result["write_count"] > 0

    def test_tools_toggle_enable_disable(self, mcp_client):
        """powerscale_tools_toggle can disable and re-enable a single tool."""
        # Disable bytes_to_human
        r1 = mcp_client("powerscale_tools_toggle", {
            "names": ["bytes_to_human"], "action": "disable"
        })
        assert isinstance(r1, dict)

        # Verify it's gone from tools list
        tools_after = mcp_client.list_tools()
        tool_names = {t["name"] for t in tools_after}
        assert "bytes_to_human" not in tool_names, (
            "bytes_to_human should be disabled but still appears in tools/list"
        )

        # Re-enable it
        r2 = mcp_client("powerscale_tools_toggle", {
            "names": ["bytes_to_human"], "action": "enable"
        })
        assert isinstance(r2, dict)

        # Verify it's back
        tools_restored = mcp_client.list_tools()
        restored_names = {t["name"] for t in tools_restored}
        assert "bytes_to_human" in restored_names, (
            "bytes_to_human should be re-enabled but is missing from tools/list"
        )

    def test_cluster_list(self, mcp_client):
        """powerscale_cluster_list returns available clusters or vault error."""
        result = mcp_client("powerscale_cluster_list")
        assert isinstance(result, dict)
        # If vault is properly configured, expect clusters list;
        # otherwise vault decryption error is acceptable in test environments
        if "error" in result:
            assert "vault" in result["error"].lower() or "decrypt" in result["error"].lower(), (
                f"Unexpected error (not vault-related): {result['error']}"
            )
        else:
            assert "clusters" in result
            assert "selected" in result
            assert isinstance(result["clusters"], list)


# ---------------------------------------------------------------------------
# Configuration persistence tests
# ---------------------------------------------------------------------------

class TestConfigPersistence:
    pytestmark = [pytest.mark.func_none, pytest.mark.read]
    """Verify tools.json is writable at runtime (emptyDir config volume)."""

    def test_tools_config_writable_in_pod(self):
        """Pod must be able to write to /app/config/tools.json."""
        result = _kubectl(
            "exec", "deployment/isi-mcp", "--",
            "python3", "-c",
            "import json, os; "
            "p = os.environ.get('TOOLS_CONFIG_PATH', '/app/config/tools.json'); "
            "d = json.loads(open(p).read()); "
            "open(p, 'w').write(json.dumps(d)); "
            "print('writable')",
        )
        assert result.returncode == 0, f"Config not writable: {result.stderr}"
        assert "writable" in result.stdout

    def test_tools_json_has_all_tools(self):
        """tools.json inside the pod must contain all expected tool entries."""
        result = _kubectl(
            "exec", "deployment/isi-mcp", "--",
            "python3", "-c",
            "import json, os; "
            "p = os.environ.get('TOOLS_CONFIG_PATH', '/app/config/tools.json'); "
            "d = json.loads(open(p).read()); "
            "print(len(d))",
        )
        assert result.returncode == 0, f"Could not read tools.json: {result.stderr}"
        count = int(result.stdout.strip())
        assert count >= 100, f"Expected 100+ tools, found {count}"

    def test_vault_file_accessible_in_pod(self):
        """vault.yml must be accessible inside the pod."""
        result = _kubectl(
            "exec", "deployment/isi-mcp", "--",
            "test", "-f", "/app/vault/vault.yml",
        )
        assert result.returncode == 0, (
            "vault.yml not found at /app/vault/vault.yml inside the pod"
        )

    def test_playbooks_dir_writable_in_pod(self):
        """Playbooks directory must be writable."""
        result = _kubectl(
            "exec", "deployment/isi-mcp", "--",
            "sh", "-c",
            "touch /app/playbooks/test_write.tmp && rm /app/playbooks/test_write.tmp && echo ok",
        )
        assert result.returncode == 0, f"Playbooks dir not writable: {result.stderr}"
        assert "ok" in result.stdout


# ---------------------------------------------------------------------------
# Server health / startup tests
# ---------------------------------------------------------------------------

class TestServerHealth:
    pytestmark = [pytest.mark.func_none, pytest.mark.read]
    """Verify the server started cleanly and loaded all tools."""

    def test_server_loaded_tools(self):
        """Server must report tool-config startup lines and be accepting requests."""
        # Check full logs (not just tail) for startup messages
        result = _kubectl("logs", "deployment/isi-mcp")
        assert result.returncode == 0, f"Could not get logs: {result.stderr}"
        log_text = result.stdout
        # Server startup logs "N tools enabled, M tools disabled"
        assert "tools enabled" in log_text, (
            f"Expected tool-config startup log. Got:\n{log_text[-2000:]}"
        )
        # uvicorn logs "Uvicorn running on" during startup
        assert "Uvicorn running on" in log_text or "Application startup complete" in log_text, (
            f"Server did not start cleanly. Logs:\n{log_text[-2000:]}"
        )

    def test_no_import_errors_in_logs(self):
        """Server logs must not contain Python import errors."""
        result = _kubectl("logs", "deployment/isi-mcp")
        assert result.returncode == 0
        log_text = result.stdout
        # Filter out expected vault connection warnings
        for line in log_text.splitlines():
            if "ImportError" in line or "ModuleNotFoundError" in line:
                pytest.fail(f"Import error in server logs: {line}")

    def test_env_vars_configured(self):
        """Required environment variables must be set in the pod."""
        for env_var in ["VAULT_FILE", "VAULT_PASSWORD", "TOOLS_CONFIG_PATH"]:
            result = _kubectl(
                "exec", "deployment/isi-mcp", "--",
                "python3", "-c",
                f"import os; v = os.environ.get('{env_var}', ''); "
                f"assert v, f'{{repr(v)}}'; print('ok')",
            )
            assert result.returncode == 0, (
                f"Env var {env_var!r} is not set or empty: {result.stderr}"
            )
