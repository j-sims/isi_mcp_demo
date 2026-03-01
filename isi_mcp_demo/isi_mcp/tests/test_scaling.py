"""
test_scaling.py — Concurrent request and load distribution tests.

Validates that the MCP system handles concurrent load correctly and, when
scaled to multiple instances, distributes requests across all backends.

Environment variables:
  MCP_NGINX_URL           Base URL for nginx (default: https://localhost)
  EXPECTED_INSTANCE_COUNT Number of backend instances expected (default: 1)
                          Set to ≥ 2 to enable load-distribution assertions.
  TEST_CONTEXT            "docker" or "k8s" (default: docker)
                          Determines how backend instances are inspected.
  COMPOSE_FILE            docker-compose.yml path (Docker context)
  COMPOSE_OVERRIDE        Override compose file path (Docker context)
  K8S_NAMESPACE           K8s namespace (K8s context, default: isi-mcp)

Usage (Docker, scaled to 3):
  docker compose -f docker-compose.yml -f override.yml up --scale isi_mcp=3 -d
  MCP_NGINX_URL=https://localhost EXPECTED_INSTANCE_COUNT=3 TEST_CONTEXT=docker \\
    pytest tests/test_scaling.py -v

Usage (K8s, scaled to 3):
  kubectl scale deployment isi-mcp --replicas=3 -n isi-mcp
  MCP_NGINX_URL=https://localhost:18443 EXPECTED_INSTANCE_COUNT=3 TEST_CONTEXT=k8s \\
    K8S_NAMESPACE=isi-mcp pytest tests/test_scaling.py -v
"""

import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MCP_NGINX_URL           = os.environ.get("MCP_NGINX_URL", "https://localhost")
EXPECTED_INSTANCE_COUNT = int(os.environ.get("EXPECTED_INSTANCE_COUNT", "1"))
TEST_CONTEXT            = os.environ.get("TEST_CONTEXT", "docker")
COMPOSE_FILE            = os.environ.get("COMPOSE_FILE", "")
COMPOSE_OVERRIDE        = os.environ.get("COMPOSE_OVERRIDE", "")
K8S_NAMESPACE           = os.environ.get("K8S_NAMESPACE", "isi-mcp")

MCP_ENDPOINT = f"{MCP_NGINX_URL}/mcp"
MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_response(resp: httpx.Response) -> dict:
    """Parse an MCP HTTP response, handling both JSON and SSE formats."""
    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        return resp.json()
    if "text/event-stream" in content_type or resp.text.startswith("event:"):
        for line in resp.text.splitlines():
            if line.startswith("data: "):
                return json.loads(line[6:])
    return resp.json()


def _make_initialized_client() -> tuple[httpx.Client, dict]:
    """
    Create an httpx.Client with an active MCP session through nginx.
    Returns (client, headers_with_session_id).
    """
    client = httpx.Client(verify=False, timeout=30.0)
    headers = dict(MCP_HEADERS)

    resp = client.post(
        MCP_ENDPOINT,
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "pytest-scaling", "version": "1.0"},
            },
        },
    )
    assert resp.status_code == 200, f"MCP init failed: {resp.status_code}"
    session_id = resp.headers.get("Mcp-Session-Id")
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    client.post(
        MCP_ENDPOINT,
        headers=headers,
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    return client, headers


def _call_current_time(client: httpx.Client, headers: dict, request_id: int) -> dict:
    """Call the current_time tool and return the parsed result dict."""
    resp = client.post(
        MCP_ENDPOINT,
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": "current_time", "arguments": {}},
        },
    )
    assert resp.status_code == 200, f"Request {request_id} failed: {resp.status_code}"
    body = _parse_response(resp)
    content = body["result"]["content"]
    return json.loads(content[0]["text"])


def _get_docker_backend_container_names() -> list[str]:
    """
    Return the names of running isi_mcp backend containers (excludes nginx).
    Requires COMPOSE_FILE; falls back to plain `docker compose ps`.
    """
    cmd = ["docker", "compose"]
    if COMPOSE_FILE:
        cmd += ["-f", COMPOSE_FILE]
    if COMPOSE_OVERRIDE and os.path.exists(COMPOSE_OVERRIDE):
        cmd += ["-f", COMPOSE_OVERRIDE]
    cmd += ["ps", "--status", "running", "--format", "json"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []

    containers = []
    try:
        # docker compose ps --format json emits one JSON object per line
        for line in result.stdout.strip().splitlines():
            entry = json.loads(line)
            name = entry.get("Name", "") or entry.get("name", "")
            service = entry.get("Service", "") or entry.get("service", "")
            # Include isi_mcp service containers, exclude nginx
            if service == "isi_mcp" or (
                "isi_mcp" in name and "nginx" not in name
            ):
                containers.append(name)
    except (json.JSONDecodeError, KeyError):
        pass
    return containers


def _get_k8s_backend_pod_names() -> list[str]:
    """Return the names of Running isi-mcp backend pods."""
    result = subprocess.run(
        [
            "kubectl", "get", "pods",
            "-n", K8S_NAMESPACE,
            "-l", "app=isi-mcp",
            "--field-selector", "status.phase=Running",
            "-o", "jsonpath={.items[*].metadata.name}",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    return result.stdout.strip().split()


def _check_docker_container_served_requests(container_name: str, since_time: str) -> bool:
    """Return True if the container logged any POST /mcp requests since since_time."""
    result = subprocess.run(
        ["docker", "logs", "--since", since_time, container_name],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    return "POST /mcp" in output


def _check_k8s_pod_served_requests(pod_name: str) -> bool:
    """Return True if the pod logged any POST /mcp requests in the last 2 minutes."""
    result = subprocess.run(
        ["kubectl", "logs", pod_name, "-n", K8S_NAMESPACE, "--since=2m"],
        capture_output=True,
        text=True,
    )
    return "POST /mcp" in result.stdout


# ---------------------------------------------------------------------------
# Module-level skip: nginx must be reachable
# ---------------------------------------------------------------------------

def pytest_runtest_setup(item):
    pass  # Handled by the fixture below


@pytest.fixture(scope="module", autouse=True)
def require_nginx():
    """Skip entire module if nginx is not reachable."""
    try:
        with httpx.Client(verify=False, timeout=10.0) as c:
            resp = c.get(f"{MCP_NGINX_URL}/health")
            if resp.status_code != 200:
                pytest.skip(
                    f"nginx /health returned {resp.status_code} at {MCP_NGINX_URL}"
                )
    except httpx.ConnectError as exc:
        pytest.skip(f"nginx not reachable at {MCP_NGINX_URL}: {exc}")


# ---------------------------------------------------------------------------
# TestConcurrentRequests
# ---------------------------------------------------------------------------

@pytest.mark.scaling
@pytest.mark.read
@pytest.mark.func_none
class TestConcurrentRequests:
    """Validate that the system handles concurrent load without errors."""

    def test_concurrent_tool_calls(self):
        """
        Fire 20 concurrent current_time tool calls through nginx.
        All must return HTTP 200 with valid date/time/timezone fields.
        """
        N = 20
        errors = []

        def _worker(worker_id: int) -> dict:
            client, headers = _make_initialized_client()
            try:
                return _call_current_time(client, headers, worker_id)
            finally:
                client.close()

        with ThreadPoolExecutor(max_workers=N) as pool:
            futures = {pool.submit(_worker, i): i for i in range(1, N + 1)}
            for future in as_completed(futures):
                worker_id = futures[future]
                try:
                    result = future.result()
                    for key in ("date", "time", "timezone"):
                        if key not in result:
                            errors.append(
                                f"Worker {worker_id}: missing '{key}' in {result}"
                            )
                except Exception as exc:
                    errors.append(f"Worker {worker_id} raised: {exc}")

        assert not errors, (
            f"{len(errors)} of {N} concurrent requests failed:\n"
            + "\n".join(errors)
        )

    def test_no_errors_under_sequential_load(self):
        """
        30 sequential requests through nginx all succeed.
        Validates no session or state corruption across replicas.
        """
        client, headers = _make_initialized_client()
        errors = []
        try:
            for i in range(1, 31):
                try:
                    result = _call_current_time(client, headers, i)
                    if "date" not in result:
                        errors.append(f"Request {i}: missing 'date' in {result}")
                except Exception as exc:
                    errors.append(f"Request {i} raised: {exc}")
        finally:
            client.close()

        assert not errors, (
            f"{len(errors)} of 30 sequential requests failed:\n"
            + "\n".join(errors)
        )


# ---------------------------------------------------------------------------
# TestLoadDistribution
# ---------------------------------------------------------------------------

@pytest.mark.scaling
@pytest.mark.read
@pytest.mark.func_none
class TestLoadDistribution:
    """Validate multi-instance routing when EXPECTED_INSTANCE_COUNT ≥ 2."""

    def test_expected_instance_count_running(self):
        """
        Verify the expected number of backend instances are currently running.
        """
        if TEST_CONTEXT == "docker":
            names = _get_docker_backend_container_names()
        else:
            names = _get_k8s_backend_pod_names()

        assert len(names) == EXPECTED_INSTANCE_COUNT, (
            f"Expected {EXPECTED_INSTANCE_COUNT} backend instance(s) running, "
            f"found {len(names)}: {names}"
        )

    def test_requests_reach_multiple_backends(self):
        """
        After 30 requests through nginx, at least 2 different backend instances
        must have served traffic (verified via container/pod access logs).

        Skipped when EXPECTED_INSTANCE_COUNT < 2.
        """
        if EXPECTED_INSTANCE_COUNT < 2:
            pytest.skip(
                f"EXPECTED_INSTANCE_COUNT={EXPECTED_INSTANCE_COUNT} — "
                "set to ≥ 2 to verify load distribution."
            )

        # Record start time before sending requests (for Docker log --since filter)
        start_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Send 30 requests to give nginx time to distribute across instances
        client, headers = _make_initialized_client()
        try:
            for i in range(1, 31):
                _call_current_time(client, headers, i)
        finally:
            client.close()

        # Allow a moment for logs to flush
        time.sleep(1)

        # Inspect each backend instance for access log entries
        if TEST_CONTEXT == "docker":
            instances = _get_docker_backend_container_names()
            served = [
                name for name in instances
                if _check_docker_container_served_requests(name, start_ts)
            ]
        else:
            instances = _get_k8s_backend_pod_names()
            served = [
                pod for pod in instances
                if _check_k8s_pod_served_requests(pod)
            ]

        assert len(served) >= 2, (
            f"Expected at least 2 backend instances to serve traffic, "
            f"but only {len(served)} did: {served} "
            f"(total instances: {instances})"
        )
