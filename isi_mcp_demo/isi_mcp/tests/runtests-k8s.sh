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
  -h, --help              Show this help message

Examples:
  # Run K8s infrastructure + protocol tests only
  ./runtests-k8s.sh

  # Include cluster-facing tool tests
  ./runtests-k8s.sh --cluster-host 172.16.10.10 --cluster-user root --cluster-pass password
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
    -h|--help)       show_help ;;
    *)               fail "Unknown argument: $1 (use -h for help)" ;;
  esac
done

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

RESULT=0
MCP_BASE_URL="$MCP_BASE_URL" \
K8S_NAMESPACE="$K8S_NAMESPACE" \
"${VENV_DIR}/bin/pytest" \
  tests/test_k8s_minikube.py \
  -v \
  --tb=short \
  "${EXTRA_ENV_ARGS[@]}" \
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
