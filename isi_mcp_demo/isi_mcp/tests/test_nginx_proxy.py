"""
test_nginx_proxy.py — MCP functionality tests through the nginx reverse proxy.

Validates TLS termination, security headers, HTTP→HTTPS redirect, infrastructure
endpoints, and full MCP protocol operation through nginx (not the backend directly).

Environment variables:
  MCP_NGINX_URL   Base URL for nginx (default: https://localhost)
  TEST_CONTEXT    Deployment context: "docker" or "k8s" (default: docker)
                  When "k8s", the HTTP→HTTPS redirect test is skipped because
                  the redirect target hostname is not the port-forwarded address.

Prerequisites (Docker Compose):
  docker-compose up --build -d
  # nginx is available on https://localhost (port 443) and http://localhost (port 80)

Prerequisites (K8s):
  kubectl port-forward -n isi-mcp svc/isi-mcp-nginx 18443:443 &
  MCP_NGINX_URL=https://localhost:18443 pytest tests/test_nginx_proxy.py -v
"""

import os
import json
import pytest
import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MCP_NGINX_URL = os.environ.get("MCP_NGINX_URL", "https://localhost")
TEST_CONTEXT  = os.environ.get("TEST_CONTEXT", "docker")

# Derive the HTTP (non-TLS) base URL for redirect tests (Docker only)
# e.g. https://localhost → http://localhost
#      https://localhost:18443 → http://localhost:18080  (not applicable for k8s)
_https_base = MCP_NGINX_URL.rstrip("/")
HTTP_BASE_URL = _https_base.replace("https://", "http://", 1)
# Strip port from HTTP URL for redirect test (nginx listens on :80, no custom port)
if HTTP_BASE_URL.count(":") > 1:
    # Has a port: strip it — e.g. http://localhost:18443 → http://localhost
    HTTP_BASE_URL = HTTP_BASE_URL.rsplit(":", 1)[0]

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


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


# ---------------------------------------------------------------------------
# Fixture: nginx_client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def nginx_client():
    """
    httpx.Client configured to connect to nginx with SSL verification disabled
    (required for self-signed development certificates).
    """
    with httpx.Client(verify=False, timeout=15.0, follow_redirects=False) as client:
        # Quick sanity check — fail the whole module if nginx is not reachable
        try:
            resp = client.get(f"{MCP_NGINX_URL}/health")
            assert resp.status_code == 200, (
                f"nginx /health returned {resp.status_code} — is nginx running?"
            )
        except httpx.ConnectError as exc:
            pytest.skip(f"nginx not reachable at {MCP_NGINX_URL}: {exc}")
        yield client


@pytest.fixture(scope="module")
def nginx_mcp_session(nginx_client):
    """
    Initialize a full MCP session through nginx and return a call_tool callable.
    """
    _request_id = 0

    def _next_id():
        nonlocal _request_id
        _request_id += 1
        return _request_id

    headers = dict(MCP_HEADERS)
    mcp_endpoint = f"{MCP_NGINX_URL}/mcp"

    init_resp = nginx_client.post(
        mcp_endpoint,
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": _next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "pytest-nginx", "version": "1.0.0"},
            },
        },
    )
    assert init_resp.status_code == 200, (
        f"MCP initialize via nginx failed: {init_resp.status_code} {init_resp.text[:200]}"
    )

    session_id = init_resp.headers.get("Mcp-Session-Id")
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    # Send initialized notification
    nginx_client.post(
        mcp_endpoint,
        headers=headers,
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )

    def call_tool(name: str, arguments: dict | None = None) -> dict:
        resp = nginx_client.post(
            mcp_endpoint,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": _next_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            },
        )
        assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}"
        body = _parse_response(resp)
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

    def list_tools() -> list:
        resp = nginx_client.post(
            mcp_endpoint,
            headers=headers,
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
    return call_tool


# ---------------------------------------------------------------------------
# TestNginxHTTPS — TLS, redirect, security headers
# ---------------------------------------------------------------------------

@pytest.mark.nginx
@pytest.mark.read
@pytest.mark.func_none
class TestNginxHTTPS:
    """Validate TLS termination, HTTP→HTTPS redirect, and security response headers."""

    def test_tls_handshake_succeeds(self, nginx_client):
        """HTTPS connection to nginx completes without SSL error."""
        resp = nginx_client.get(f"{MCP_NGINX_URL}/health")
        assert resp.status_code == 200, (
            f"Expected 200 from /health via HTTPS, got {resp.status_code}"
        )

    def test_http_to_https_redirect(self):
        """GET http://localhost/health returns a 3xx redirect pointing to HTTPS."""
        if TEST_CONTEXT == "k8s":
            pytest.skip(
                "HTTP→HTTPS redirect test skipped in K8s mode: redirect target "
                "hostname does not match port-forwarded address."
            )
        with httpx.Client(verify=False, timeout=10.0, follow_redirects=False) as c:
            resp = c.get(f"{HTTP_BASE_URL}/health")
        assert resp.status_code in (301, 302, 307, 308), (
            f"Expected redirect from HTTP, got {resp.status_code}"
        )
        location = resp.headers.get("location", "")
        assert location.startswith("https://"), (
            f"Redirect location does not point to HTTPS: {location!r}"
        )

    def test_security_header_hsts(self, nginx_client):
        """Response includes Strict-Transport-Security header."""
        resp = nginx_client.get(f"{MCP_NGINX_URL}/health")
        hsts = resp.headers.get("strict-transport-security", "")
        assert hsts, "Missing Strict-Transport-Security header"
        assert "max-age=" in hsts, f"HSTS header missing max-age: {hsts!r}"

    def test_security_header_x_frame_options(self, nginx_client):
        """Response includes X-Frame-Options: DENY."""
        resp = nginx_client.get(f"{MCP_NGINX_URL}/health")
        xfo = resp.headers.get("x-frame-options", "")
        assert xfo.upper() == "DENY", (
            f"Expected X-Frame-Options: DENY, got {xfo!r}"
        )

    def test_security_header_x_content_type(self, nginx_client):
        """Response includes X-Content-Type-Options: nosniff."""
        resp = nginx_client.get(f"{MCP_NGINX_URL}/health")
        xcto = resp.headers.get("x-content-type-options", "")
        assert xcto.lower() == "nosniff", (
            f"Expected X-Content-Type-Options: nosniff, got {xcto!r}"
        )

    def test_unknown_path_returns_404(self, nginx_client):
        """Non-routed path returns 404 (nginx catch-all)."""
        resp = nginx_client.get(f"{MCP_NGINX_URL}/not-a-valid-path")
        assert resp.status_code == 404, (
            f"Expected 404 for unknown path, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# TestNginxEndpoints — /health and /version bypass rate limiting
# ---------------------------------------------------------------------------

@pytest.mark.nginx
@pytest.mark.read
@pytest.mark.func_none
class TestNginxEndpoints:
    """Validate infrastructure endpoints routed through nginx without rate limiting."""

    def test_health_endpoint(self, nginx_client):
        """GET /health returns 200 OK."""
        resp = nginx_client.get(f"{MCP_NGINX_URL}/health")
        assert resp.status_code == 200, (
            f"Expected 200 from /health, got {resp.status_code}: {resp.text[:100]}"
        )

    def test_version_endpoint(self, nginx_client):
        """GET /version returns 200 with JSON containing a 'version' key."""
        resp = nginx_client.get(f"{MCP_NGINX_URL}/version")
        assert resp.status_code == 200, (
            f"Expected 200 from /version, got {resp.status_code}: {resp.text[:100]}"
        )
        body = resp.json()
        assert "version" in body, f"Missing 'version' key in /version response: {body}"
        assert isinstance(body["version"], str) and body["version"], (
            f"'version' value is empty or not a string: {body['version']!r}"
        )


# ---------------------------------------------------------------------------
# TestNginxMCPProtocol — Full MCP protocol through nginx
# ---------------------------------------------------------------------------

@pytest.mark.nginx
@pytest.mark.read
@pytest.mark.func_none
class TestNginxMCPProtocol:
    """Validate full MCP JSON-RPC protocol operates correctly through nginx."""

    def test_initialize_through_nginx(self, nginx_client):
        """MCP initialize handshake succeeds via HTTPS and returns valid protocol fields."""
        resp = nginx_client.post(
            f"{MCP_NGINX_URL}/mcp",
            headers=MCP_HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest-nginx-probe", "version": "1.0"},
                },
            },
        )
        assert resp.status_code == 200, (
            f"MCP initialize via nginx: HTTP {resp.status_code}"
        )
        body = _parse_response(resp)
        result = body.get("result", {})
        assert result.get("protocolVersion") == "2025-06-18", (
            f"Unexpected protocolVersion: {result.get('protocolVersion')!r}"
        )
        assert "serverInfo" in result, "Missing serverInfo in initialize response"

    def test_tool_call_through_nginx(self, nginx_mcp_session):
        """current_time tool returns valid result (date/time/timezone) via nginx."""
        result = nginx_mcp_session("current_time")
        assert isinstance(result, dict), f"Expected dict result, got {type(result)}"
        for key in ("date", "time", "timezone"):
            assert key in result, f"Missing key '{key}' in current_time result: {result}"

    def test_tools_list_through_nginx(self, nginx_mcp_session):
        """tools/list returns a non-empty list of tool definitions via nginx."""
        tools = nginx_mcp_session.list_tools()
        assert isinstance(tools, list), f"Expected list of tools, got {type(tools)}"
        assert len(tools) > 0, "tools/list returned empty list via nginx"
        # Spot-check that each entry has required MCP fields
        for tool in tools[:3]:
            assert "name" in tool, f"Tool missing 'name' field: {tool}"
            assert "description" in tool, f"Tool '{tool.get('name')}' missing 'description'"
            assert "inputSchema" in tool, f"Tool '{tool.get('name')}' missing 'inputSchema'"
