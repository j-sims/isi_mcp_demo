#!/usr/bin/env bash
#
# runtests-k8s.sh — Run the K8s/minikube deployment test suite.
#
# Verifies that the isi-mcp-server is correctly deployed on minikube:
#   - K8s resources exist (Deployment, Service, ConfigMap, Secrets)
#   - Pod is running and healthy
#   - MCP server responds via port-forward
#   - Utility and management tools work without a PowerScale cluster
#   - Config volume is writable at runtime
#
# Prerequisites:
#   minikube running with isi-mcp deployed:
#     export VAULT_PASSWORD='your-password'
#     ./k8s/deploy-minikube.sh
#
# Usage:
#   ./runtests-k8s.sh
#   ./runtests-k8s.sh --cluster-host 172.16.10.10 --cluster-user root --cluster-pass password
#   ./runtests-k8s.sh --mcp-port 18000
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
MCP_PORT=18001            # Local port for kubectl port-forward
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

Run the K8s/minikube test suite against the deployed isi-mcp-server.

Options:
  --mcp-port PORT         Local port for kubectl port-forward (default: 18001)
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
  # Run K8s infrastructure + protocol tests only
  ./runtests-k8s.sh

  # Include cluster-facing tool tests
  ./runtests-k8s.sh --cluster-host 172.16.10.10 --cluster-user root --cluster-pass password

  # Run only utility tool tests
  ./runtests-k8s.sh --group utils

  # Run all read tests
  ./runtests-k8s.sh --mode read
HELP
    exit 0
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --mcp-port)      MCP_PORT="$2"; shift 2 ;;
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
# Check prerequisites
# ---------------------------------------------------------------------------
info "Checking prerequisites..."

command -v kubectl   &>/dev/null || fail "kubectl not found in PATH"
command -v minikube  &>/dev/null || fail "minikube not found in PATH"
command -v python3   &>/dev/null || fail "python3 not found in PATH"

# Check minikube is running
minikube status 2>/dev/null | grep -q "Running" || \
  fail "minikube is not running. Deploy first: ${ROOT_DIR}/k8s/deploy-minikube.sh"

# Check namespace exists
kubectl get namespace "$NAMESPACE" &>/dev/null || \
  fail "Namespace '$NAMESPACE' not found. Deploy first: ${ROOT_DIR}/k8s/deploy-minikube.sh"

# Check deployment exists
kubectl get deployment isi-mcp -n "$NAMESPACE" &>/dev/null || \
  fail "Deployment 'isi-mcp' not found. Deploy first: ${ROOT_DIR}/k8s/deploy-minikube.sh"

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
# Start kubectl port-forward
# ---------------------------------------------------------------------------
# Kill any existing port-forward on this port
fuser -k "${MCP_PORT}/tcp" 2>/dev/null || true

info "Starting kubectl port-forward on localhost:${MCP_PORT} → isi-mcp:8000..."
kubectl port-forward \
  --namespace="$NAMESPACE" \
  svc/isi-mcp "${MCP_PORT}:8000" \
  >/tmp/k8s-pf.log 2>&1 &
PF_PID=$!

# Wait for port to be ready
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
  kill $PF_PID 2>/dev/null || true
  fail "MCP server did not respond within 15s on port ${MCP_PORT}. Check: kubectl logs -n $NAMESPACE deployment/isi-mcp"
fi
ok "MCP server is responding on localhost:${MCP_PORT}."

# ---------------------------------------------------------------------------
# Validate test filter matches some tests (dry-run collection)
# ---------------------------------------------------------------------------
validate_filter_matches_tests() {
    local test_file="$1"

    # Do a dry-run collection to count matching tests
    # Count lines that match pytest test item format (e.g., "test_file.py::TestClass::test_method")
    local count=$(python3 -m pytest \
        "${test_file}" \
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
K8S_NAMESPACE="$NAMESPACE"

EXTRA_ENV_ARGS=()
if [ -n "$CLUSTER_HOST" ]; then
  EXTRA_ENV_ARGS+=(-e "TEST_CLUSTER_HOST=${CLUSTER_HOST}")
fi
if [ -n "$CLUSTER_USER" ]; then
  EXTRA_ENV_ARGS+=(-e "TEST_CLUSTER_USERNAME=${CLUSTER_USER}")
fi
if [ -n "$CLUSTER_PASS" ]; then
  EXTRA_ENV_ARGS+=(-e "TEST_CLUSTER_PASSWORD=${CLUSTER_PASS}")
fi

info "Running K8s test suite..."
echo ""

# Change to the isi_mcp dir so conftest.py imports work
cd "${SCRIPT_DIR}/.."

# Validate filter before running (if filters are applied)
if [[ ${#MARKER_PARTS[@]} -gt 0 ]]; then
    validate_filter_matches_tests "tests/test_k8s_minikube.py"
fi

RESULT=0
MCP_BASE_URL="$MCP_BASE_URL" \
K8S_NAMESPACE="$K8S_NAMESPACE" \
"${VENV_DIR}/bin/pytest" \
  tests/test_k8s_minikube.py \
  -v \
  --tb=short \
  "${EXTRA_ENV_ARGS[@]}" \
  "${PYTEST_MARKER_ARGS[@]}" \
  || RESULT=$?

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
kill $PF_PID 2>/dev/null || true

echo ""
if [ $RESULT -eq 0 ]; then
  ok "All K8s tests passed."
  echo ""
  echo "Deployment is healthy and all tests passed."
  echo "Connect an MCP client: kubectl port-forward -n $NAMESPACE svc/isi-mcp 8000:8000"
else
  fail "Some K8s tests failed (exit code $RESULT). See output above."
fi
