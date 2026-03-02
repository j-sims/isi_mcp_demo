#!/usr/bin/env bash
#
# runtests-k8s.sh — Run the Kubernetes deployment test suite.
#
# Verifies that the isi-mcp-server is correctly deployed on Kubernetes:
#   - K8s resources exist (Deployment, Service, ConfigMap, Secrets)
#   - Pod is running and healthy
#   - MCP server responds via port-forward (backend direct)
#   - MCP server responds via nginx HTTPS reverse proxy
#   - Utility and management tools work without a PowerScale cluster
#   - Config volume is writable at runtime
#   - System works correctly when scaled to multiple replicas
#
# Prerequisites:
#   k3s running with isi-mcp deployed:
#     export VAULT_PASSWORD='your-password'
#     ./k8s/deploy-k3s.sh
#
# Usage:
#   ./runtests-k8s.sh
#   ./runtests-k8s.sh --cluster-host 172.16.10.10 --cluster-user root --cluster-pass password
#   ./runtests-k8s.sh --mcp-port 18000 --nginx-port 18443
#   ./runtests-k8s.sh --func none --mode read    # filter by function/mode
#   ./runtests-k8s.sh --group utils              # filter by tool group
#   ./runtests-k8s.sh -h

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../../" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
TESTS_DIR="${SCRIPT_DIR}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
MCP_PORT=18001            # Local port for kubectl port-forward → backend:8000
NGINX_PORT=18443          # Local port for kubectl port-forward → nginx:443
NAMESPACE="isi-mcp"
CLUSTER_HOST=""
CLUSTER_USER=""
CLUSTER_PASS=""
FILTER_FUNC=""
FILTER_GROUP=""
FILTER_TOOL=""
FILTER_MODE=""

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
show_help() {
    cat << 'HELP'
Usage: ./runtests-k8s.sh [OPTIONS]

Run the Kubernetes test suite against the deployed isi-mcp-server.
Tests include: K8s infrastructure, MCP protocol (direct backend), nginx HTTPS
proxy, and scaling/load-distribution across multiple replicas.

Options:
  --mcp-port PORT         Local port for backend kubectl port-forward (default: 18001)
  --nginx-port PORT       Local port for nginx kubectl port-forward (default: 18443)
  --namespace NS          K8s namespace (default: isi-mcp)
  --cluster-host HOST     PowerScale cluster host for cluster tests (optional)
  --cluster-user USER     PowerScale cluster username (optional)
  --cluster-pass PASS     PowerScale cluster password (optional)

Test Filters (can be combined):
  --func FUNCTION         Filter by PowerScale function (e.g. none, utils)
  --group GROUP           Filter by tool group (e.g. utils, management)
  --tool TOOL             Filter by individual tool name
  --mode MODE             Filter by tool mode: read or write

  -h, --help              Show this help message

Examples:
  # Run full suite (K8s infra + backend + nginx proxy + scaling)
  ./runtests-k8s.sh

  # Include cluster-facing tool tests
  ./runtests-k8s.sh --cluster-host 172.16.10.10 --cluster-user root --cluster-pass password

  # Run only utility tool tests
  ./runtests-k8s.sh --group utils

  # Run all read tests
  ./runtests-k8s.sh --mode read

  # Custom ports
  ./runtests-k8s.sh --mcp-port 19001 --nginx-port 19443
HELP
    exit 0
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --mcp-port)      MCP_PORT="$2"; shift 2 ;;
    --nginx-port)    NGINX_PORT="$2"; shift 2 ;;
    --namespace)     NAMESPACE="$2"; shift 2 ;;
    --cluster-host)  CLUSTER_HOST="$2"; shift 2 ;;
    --cluster-user)  CLUSTER_USER="$2"; shift 2 ;;
    --cluster-pass)  CLUSTER_PASS="$2"; shift 2 ;;
    --func)          FILTER_FUNC="$2"; shift 2 ;;
    --group)         FILTER_GROUP="$2"; shift 2 ;;
    --tool)          FILTER_TOOL="$2"; shift 2 ;;
    --mode)
      FILTER_MODE="$2"
      if [[ "$FILTER_MODE" != "read" && "$FILTER_MODE" != "write" ]]; then
        fail "--mode must be 'read' or 'write', got: $FILTER_MODE"
      fi
      shift 2 ;;
    -h|--help)       show_help ;;
    *)               fail "Unknown argument: $1 (use -h for help)" ;;
  esac
done

# ---------------------------------------------------------------------------
# Validate filter inputs against tools.json
# ---------------------------------------------------------------------------
TOOLS_JSON="${ROOT_DIR}/isi_mcp_demo/isi_mcp/config/tools.json"

if [[ ! -f "$TOOLS_JSON" ]]; then
    fail "tools.json not found at: $TOOLS_JSON"
fi

# Extract valid functions, groups, and tool names from tools.json
VALID_FUNCTIONS=$(python3 -c "
import json
with open('$TOOLS_JSON') as f:
    tools = json.load(f)
    functions = set()
    for tool_name, tool_data in tools.items():
        if 'function' in tool_data:
            functions.add(tool_data['function'])
    for func in sorted(functions):
        print(func)
" 2>/dev/null)

VALID_GROUPS=$(python3 -c "
import json
with open('$TOOLS_JSON') as f:
    tools = json.load(f)
    groups = set()
    for tool_name, tool_data in tools.items():
        if 'tool_group' in tool_data:
            groups.add(tool_data['tool_group'])
    for group in sorted(groups):
        print(group)
" 2>/dev/null)

VALID_TOOLS=$(python3 -c "
import json
with open('$TOOLS_JSON') as f:
    tools = json.load(f)
    for tool_name in sorted(tools.keys()):
        print(tool_name)
" 2>/dev/null)

# Validate --func argument
if [[ -n "$FILTER_FUNC" ]]; then
    if ! echo "$VALID_FUNCTIONS" | grep -q "^${FILTER_FUNC}$"; then
        fail "--func '$FILTER_FUNC' is not a valid function"
        echo ""
        echo "Valid functions are:"
        echo "$VALID_FUNCTIONS" | sed 's/^/  - /'
        echo ""
        exit 1
    fi
fi

# Validate --group argument
if [[ -n "$FILTER_GROUP" ]]; then
    if ! echo "$VALID_GROUPS" | grep -q "^${FILTER_GROUP}$"; then
        fail "--group '$FILTER_GROUP' is not a valid tool group"
        echo ""
        echo "Valid tool groups are:"
        echo "$VALID_GROUPS" | sed 's/^/  - /'
        echo ""
        exit 1
    fi
fi

# Validate --tool argument
if [[ -n "$FILTER_TOOL" ]]; then
    if ! echo "$VALID_TOOLS" | grep -q "^${FILTER_TOOL}$"; then
        fail "--tool '$FILTER_TOOL' is not a valid tool name"
        echo ""
        echo "Valid tool names (first 20):"
        echo "$VALID_TOOLS" | head -20 | sed 's/^/  - /'
        echo "  ... and more (use --func or --group to filter by function/group)"
        echo ""
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Build pytest marker expression from filter arguments
# ---------------------------------------------------------------------------
MARKER_PARTS=()
[[ -n "$FILTER_FUNC" ]]  && MARKER_PARTS+=("func_${FILTER_FUNC}")
[[ -n "$FILTER_GROUP" ]] && MARKER_PARTS+=("group_${FILTER_GROUP}")
[[ -n "$FILTER_TOOL" ]]  && MARKER_PARTS+=("tool_${FILTER_TOOL}")
[[ -n "$FILTER_MODE" ]]  && MARKER_PARTS+=("${FILTER_MODE}")

MARKER_EXPR=""
PYTEST_MARKER_ARGS=()
if [[ ${#MARKER_PARTS[@]} -gt 0 ]]; then
    # Build marker expression with "and" between parts for valid pytest syntax
    MARKER_EXPR="${MARKER_PARTS[0]}"
    for ((i=1; i<${#MARKER_PARTS[@]}; i++)); do
        MARKER_EXPR="${MARKER_EXPR} and ${MARKER_PARTS[$i]}"
    done
    PYTEST_MARKER_ARGS=("-m" "$MARKER_EXPR")
    info "Test filter: -m \"${MARKER_EXPR}\""
fi

# ---------------------------------------------------------------------------
# Cleanup trap — kill port-forwards and restore replica count on any exit
# ---------------------------------------------------------------------------
PF_PID_BACKEND=0
PF_PID_NGINX=0
ORIGINAL_REPLICAS=1

_cleanup() {
    [[ $PF_PID_BACKEND -ne 0 ]] && kill $PF_PID_BACKEND 2>/dev/null || true
    [[ $PF_PID_NGINX   -ne 0 ]] && kill $PF_PID_NGINX   2>/dev/null || true
    # Restore replica count if we changed it
    if kubectl get deployment isi-mcp -n "$NAMESPACE" &>/dev/null 2>&1; then
        CURRENT=$(kubectl get deployment isi-mcp -n "$NAMESPACE" \
            -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "$ORIGINAL_REPLICAS")
        if [[ "$CURRENT" != "$ORIGINAL_REPLICAS" ]]; then
            kubectl scale deployment isi-mcp --replicas="$ORIGINAL_REPLICAS" \
                -n "$NAMESPACE" 2>/dev/null || true
        fi
    fi
}
trap _cleanup EXIT

# ---------------------------------------------------------------------------
# Check prerequisites
# ---------------------------------------------------------------------------
info "Checking prerequisites..."

command -v kubectl   &>/dev/null || fail "kubectl not found in PATH"
command -v python3   &>/dev/null || fail "python3 not found in PATH"

# Check k3s cluster is accessible
kubectl cluster-info &>/dev/null || \
  fail "Kubernetes cluster is not accessible. Ensure k3s is running: ${ROOT_DIR}/k8s/deploy-k3s.sh"

# Check namespace exists
kubectl get namespace "$NAMESPACE" &>/dev/null || \
  fail "Namespace '$NAMESPACE' not found. Deploy first: ${ROOT_DIR}/k8s/deploy-k3s.sh"

# Check backend deployment exists
kubectl get deployment isi-mcp -n "$NAMESPACE" &>/dev/null || \
  fail "Deployment 'isi-mcp' not found. Deploy first: ${ROOT_DIR}/k8s/deploy-k3s.sh"

# Check nginx deployment exists
kubectl get deployment isi-mcp-nginx -n "$NAMESPACE" &>/dev/null || \
  fail "Deployment 'isi-mcp-nginx' not found. Deploy first: ${ROOT_DIR}/k8s/deploy-k3s.sh"

ok "Prerequisites satisfied."

# ---------------------------------------------------------------------------
# Setup Python virtual environment
# ---------------------------------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
  info "Creating Python virtual environment at $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
fi

info "Installing test dependencies..."
"${VENV_DIR}/bin/pip" install --quiet \
  pytest httpx python-dotenv isilon-sdk ansible-core

ok "Dependencies installed."

# ---------------------------------------------------------------------------
# Start kubectl port-forwards (backend and nginx)
# ---------------------------------------------------------------------------
# Kill any existing port-forwards on these ports
fuser -k "${MCP_PORT}/tcp" 2>/dev/null || true
fuser -k "${NGINX_PORT}/tcp" 2>/dev/null || true

info "Starting kubectl port-forward: localhost:${MCP_PORT} → isi-mcp-backend:8000..."
kubectl port-forward \
  --namespace="$NAMESPACE" \
  svc/isi-mcp-backend "${MCP_PORT}:8000" \
  >/tmp/k8s-pf-backend.log 2>&1 &
PF_PID_BACKEND=$!

info "Starting kubectl port-forward: localhost:${NGINX_PORT} → isi-mcp-nginx:443..."
kubectl port-forward \
  --namespace="$NAMESPACE" \
  svc/isi-mcp-nginx "${NGINX_PORT}:443" \
  >/tmp/k8s-pf-nginx.log 2>&1 &
PF_PID_NGINX=$!

# Wait for backend to be ready
READY=false
for i in $(seq 1 15); do
  if curl -sf -X POST "http://localhost:${MCP_PORT}/mcp" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"runtests","version":"1.0"}}}' \
    &>/dev/null; then
    READY=true
    break
  fi
  sleep 1
done

if [ "$READY" = false ]; then
  kill $PF_PID_BACKEND 2>/dev/null || true
  kill $PF_PID_NGINX 2>/dev/null || true
  fail "MCP backend did not respond within 15s on port ${MCP_PORT}. Check: kubectl logs -n $NAMESPACE deployment/isi-mcp"
fi
ok "MCP backend is responding on localhost:${MCP_PORT}."

# Wait for nginx to be ready (uses --insecure for self-signed cert)
READY=false
for i in $(seq 1 15); do
  if curl -sf --insecure -X POST "https://localhost:${NGINX_PORT}/mcp" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"runtests-nginx","version":"1.0"}}}' \
    &>/dev/null; then
    READY=true
    break
  fi
  sleep 1
done

if [ "$READY" = false ]; then
  kill $PF_PID_BACKEND 2>/dev/null || true
  kill $PF_PID_NGINX 2>/dev/null || true
  fail "nginx did not respond within 15s on port ${NGINX_PORT}. Check: kubectl logs -n $NAMESPACE deployment/isi-mcp-nginx"
fi
ok "nginx is responding on localhost:${NGINX_PORT} (HTTPS)."

# ---------------------------------------------------------------------------
# Validate test filter matches some tests (dry-run collection)
# ---------------------------------------------------------------------------
validate_filter_matches_tests() {
    local test_files=("$@")

    # Do a dry-run collection to count matching tests
    # Count lines that match pytest test item format (e.g., "test_file.py::TestClass::test_method")
    local count
    count=$(python3 -m pytest \
        "${test_files[@]}" \
        "${PYTEST_MARKER_ARGS[@]}" \
        --collect-only -q 2>/dev/null | grep -E "^[^ ].*::" | wc -l)

    if [[ "$count" -eq 0 ]]; then
        fail "No tests match the given filter(s)"
        echo ""
        echo "Filter expression: -m \"${MARKER_EXPR}\""
        echo ""
        if [[ -n "$FILTER_FUNC" ]]; then
            echo "  --func ${FILTER_FUNC}"
        fi
        if [[ -n "$FILTER_GROUP" ]]; then
            echo "  --group ${FILTER_GROUP}"
        fi
        if [[ -n "$FILTER_TOOL" ]]; then
            echo "  --tool ${FILTER_TOOL}"
        fi
        if [[ -n "$FILTER_MODE" ]]; then
            echo "  --mode ${FILTER_MODE}"
        fi
        echo ""
        echo "Run without filters to see all available tests, or use:"
        echo "  ./runtests-k8s.sh -h  # for valid functions, groups, and modes"
        echo ""
        exit 1
    fi

    info "${count} test(s) match the filter"
}

# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------
MCP_BASE_URL="http://localhost:${MCP_PORT}"
NGINX_BASE_URL="https://localhost:${NGINX_PORT}"
K8S_NAMESPACE="$NAMESPACE"

# Build environment variables for pytest (not docker -e flags)
PYTEST_ENV=()
if [ -n "$CLUSTER_HOST" ]; then
  PYTEST_ENV+=("TEST_CLUSTER_HOST=${CLUSTER_HOST}")
fi
if [ -n "$CLUSTER_USER" ]; then
  PYTEST_ENV+=("TEST_CLUSTER_USERNAME=${CLUSTER_USER}")
fi
if [ -n "$CLUSTER_PASS" ]; then
  PYTEST_ENV+=("TEST_CLUSTER_PASSWORD=${CLUSTER_PASS}")
fi

# Change to the isi_mcp dir so conftest.py imports work
cd "${SCRIPT_DIR}/.."

# Validate filter before running (if filters are applied)
if [[ ${#MARKER_PARTS[@]} -gt 0 ]]; then
    validate_filter_matches_tests \
        "tests/test_k8s.py" \
        "tests/test_nginx_proxy.py" \
        "tests/test_scaling.py"
fi

RESULT=0

# ---------------------------------------------------------------------------
# Part 1 — K8s infrastructure and backend MCP tests
# ---------------------------------------------------------------------------
echo ""
info "=========================================="
info "  Part 1 — K8s infrastructure and backend MCP tests"
info "=========================================="
echo ""

info "Running K8s infrastructure and protocol tests..."
env MCP_BASE_URL="$MCP_BASE_URL" K8S_NAMESPACE="$K8S_NAMESPACE" \
  "${PYTEST_ENV[@]}" \
  "${VENV_DIR}/bin/pytest" \
  tests/test_k8s.py \
  -v \
  --tb=short \
  "${PYTEST_MARKER_ARGS[@]}" \
  || RESULT=$?

if [[ $RESULT -eq 0 ]]; then
    ok "Part 1 passed"
else
    warn "Part 1 had failures (exit code $RESULT) — continuing to nginx/scaling tests"
fi

# ---------------------------------------------------------------------------
# Part 2 — Nginx proxy tests (MCP through HTTPS reverse proxy)
# ---------------------------------------------------------------------------
echo ""
info "=========================================="
info "  Part 2 — Nginx proxy tests (HTTPS)"
info "=========================================="
echo ""

info "Running nginx proxy and security tests via https://localhost:${NGINX_PORT}..."
NGINX_RESULT=0
MCP_NGINX_URL="$NGINX_BASE_URL" \
TEST_CONTEXT=k8s \
K8S_NAMESPACE="$K8S_NAMESPACE" \
"${VENV_DIR}/bin/pytest" \
  tests/test_nginx_proxy.py \
  -v \
  --tb=short \
  "${PYTEST_MARKER_ARGS[@]}" \
  || NGINX_RESULT=$?

if [[ $NGINX_RESULT -eq 0 ]]; then
    ok "Part 2 (nginx proxy) passed"
else
    warn "Part 2 (nginx proxy) had failures (exit code $NGINX_RESULT)"
    RESULT=$NGINX_RESULT
fi

# ---------------------------------------------------------------------------
# Part 3 — Scaling tests (scale to 3 replicas, verify load distribution)
# ---------------------------------------------------------------------------
echo ""
info "=========================================="
info "  Part 3 — Scaling tests (3 replicas)"
info "=========================================="
echo ""

# Capture original replica count so we can restore it
ORIGINAL_REPLICAS=$(kubectl get deployment isi-mcp -n "$NAMESPACE" \
    -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "1")

info "Scaling isi-mcp deployment to 3 replicas (was ${ORIGINAL_REPLICAS})..."
kubectl scale deployment isi-mcp --replicas=3 -n "$NAMESPACE"

info "Waiting for 3 replicas to become ready..."
kubectl rollout status deployment/isi-mcp -n "$NAMESPACE" --timeout=120s
ok "All 3 replicas are ready."

SCALE_RESULT=0
MCP_NGINX_URL="$NGINX_BASE_URL" \
EXPECTED_INSTANCE_COUNT=3 \
TEST_CONTEXT=k8s \
K8S_NAMESPACE="$K8S_NAMESPACE" \
"${VENV_DIR}/bin/pytest" \
  tests/test_scaling.py \
  -v \
  --tb=short \
  "${PYTEST_MARKER_ARGS[@]}" \
  || SCALE_RESULT=$?

if [[ $SCALE_RESULT -eq 0 ]]; then
    ok "Part 3 (scaling) passed"
else
    warn "Part 3 (scaling) had failures (exit code $SCALE_RESULT)"
    RESULT=$SCALE_RESULT
fi

# Restore original replica count
info "Restoring isi-mcp deployment to ${ORIGINAL_REPLICAS} replica(s)..."
kubectl scale deployment isi-mcp --replicas="$ORIGINAL_REPLICAS" -n "$NAMESPACE"
ok "Deployment restored to ${ORIGINAL_REPLICAS} replica(s)."

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
kill $PF_PID_BACKEND 2>/dev/null || true
kill $PF_PID_NGINX 2>/dev/null || true

echo ""
if [ $RESULT -eq 0 ]; then
  ok "All K8s tests passed."
  echo ""
  echo "Deployment is healthy and all tests passed."
  echo "Connect an MCP client via backend:  kubectl port-forward -n $NAMESPACE svc/isi-mcp-backend 8000:8000"
  echo "Connect an MCP client via nginx:    kubectl port-forward -n $NAMESPACE svc/isi-mcp-nginx 8443:443"
else
  echo ""
  echo -e "${RED}[FAIL]${NC}  Some K8s tests failed (exit code $RESULT). See output above."
  exit $RESULT
fi
