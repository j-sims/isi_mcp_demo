#!/usr/bin/env bash
#
# deploy-minikube.sh — Build and deploy the isi-mcp-server to minikube.
#
# Prerequisites:
#   - minikube installed and available in PATH
#   - kubectl installed and available in PATH
#   - Docker installed and available in PATH
#   - vault/vault.yml exists (run ./setup.sh first to create it)
#   - VAULT_PASSWORD env var set, or pass --vault-password flag
#
# Usage:
#   export VAULT_PASSWORD='your-vault-password'
#   ./k8s/deploy-minikube.sh
#
#   # Or pass vault password inline:
#   ./k8s/deploy-minikube.sh --vault-password 'your-vault-password'
#
#   # Skip minikube start (if already running):
#   ./k8s/deploy-minikube.sh --skip-start
#
#   # Teardown:
#   ./k8s/deploy-minikube.sh --teardown

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME="isi-mcp-server"
IMAGE_TAG="latest"
NAMESPACE="isi-mcp"

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
# Parse arguments
# ---------------------------------------------------------------------------
SKIP_START=false
TEARDOWN=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --vault-password)
      VAULT_PASSWORD="$2"
      shift 2
      ;;
    --skip-start)
      SKIP_START=true
      shift
      ;;
    --teardown)
      TEARDOWN=true
      shift
      ;;
    -h|--help)
      cat << 'HELP'
Usage: ./k8s/deploy-minikube.sh [OPTIONS]

Deploy isi-mcp-server to a local minikube cluster.

Options:
  --vault-password PASS  Ansible vault password (or set VAULT_PASSWORD env var)
  --skip-start           Skip 'minikube start' (if minikube is already running)
  --teardown             Delete all isi-mcp resources and stop minikube
  -h, --help             Show this help message

Examples:
  # Full deploy
  export VAULT_PASSWORD='secret'
  ./k8s/deploy-minikube.sh

  # Deploy without restarting minikube
  ./k8s/deploy-minikube.sh --skip-start --vault-password 'secret'

  # Teardown
  ./k8s/deploy-minikube.sh --teardown
HELP
      exit 0
      ;;
    *)
      fail "Unknown argument: $1 (use -h for help)"
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Teardown
# ---------------------------------------------------------------------------
if [ "$TEARDOWN" = true ]; then
  info "Tearing down isi-mcp deployment..."
  kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
  ok "Namespace '$NAMESPACE' deleted."
  info "To stop minikube: minikube stop"
  exit 0
fi

# ---------------------------------------------------------------------------
# Validate prerequisites
# ---------------------------------------------------------------------------
info "Checking prerequisites..."

command -v minikube &>/dev/null || fail "minikube not found in PATH"
command -v kubectl  &>/dev/null || fail "kubectl not found in PATH"
command -v docker   &>/dev/null || fail "docker not found in PATH"

VAULT_FILE="${PROJECT_ROOT}/vault/vault.yml"
[ -f "$VAULT_FILE" ] || fail "vault/vault.yml not found. Run ./setup.sh first to create it."

VAULT_PASSWORD="${VAULT_PASSWORD:-}"
[ -n "$VAULT_PASSWORD" ] || fail "VAULT_PASSWORD is not set. Export it or use --vault-password."

ok "All prerequisites satisfied."

# ---------------------------------------------------------------------------
# Start minikube
# ---------------------------------------------------------------------------
if [ "$SKIP_START" = false ]; then
  info "Starting minikube..."
  minikube start --driver=docker 2>&1 | tail -5
  ok "minikube started."
else
  info "Skipping minikube start (--skip-start)."
  minikube status | grep -q "Running" || fail "minikube is not running. Remove --skip-start to start it."
fi

# ---------------------------------------------------------------------------
# Build Docker image inside minikube's Docker daemon
# ---------------------------------------------------------------------------
info "Pointing Docker CLI at minikube's daemon..."
eval "$(minikube docker-env)"

info "Building Docker image '${IMAGE_NAME}:${IMAGE_TAG}'..."
docker build \
  -t "${IMAGE_NAME}:${IMAGE_TAG}" \
  "${PROJECT_ROOT}/isi_mcp_demo/isi_mcp/"
ok "Image built: ${IMAGE_NAME}:${IMAGE_TAG}"

# Reset Docker env so subsequent kubectl/minikube commands work normally
eval "$(minikube docker-env --unset)" 2>/dev/null || true

# ---------------------------------------------------------------------------
# Create namespace first (needed before secrets)
# ---------------------------------------------------------------------------
info "Applying namespace..."
kubectl apply -f "${SCRIPT_DIR}/namespace.yaml"

# ---------------------------------------------------------------------------
# Create / update Kubernetes secrets
# ---------------------------------------------------------------------------
info "Creating/updating secret 'isi-mcp-credentials' (vault password)..."
kubectl create secret generic isi-mcp-credentials \
  --namespace="$NAMESPACE" \
  --from-literal=vault-password="$VAULT_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -
ok "Secret 'isi-mcp-credentials' ready."

info "Creating/updating secret 'isi-mcp-vault' (encrypted vault file)..."
kubectl create secret generic isi-mcp-vault \
  --namespace="$NAMESPACE" \
  --from-file=vault.yml="${VAULT_FILE}" \
  --dry-run=client -o yaml | kubectl apply -f -
ok "Secret 'isi-mcp-vault' ready."

# ---------------------------------------------------------------------------
# Apply remaining Kubernetes manifests
# ---------------------------------------------------------------------------
info "Applying Kubernetes manifests..."
kubectl apply -k "${SCRIPT_DIR}/"
ok "Manifests applied."

# ---------------------------------------------------------------------------
# Wait for rollout
# ---------------------------------------------------------------------------
info "Waiting for deployment rollout (timeout: 5m)..."
kubectl rollout status deployment/isi-mcp \
  --namespace="$NAMESPACE" \
  --timeout=300s
ok "Deployment is ready."

# ---------------------------------------------------------------------------
# Verify server is responding
# ---------------------------------------------------------------------------
info "Verifying MCP server is responding via port-forward..."

# Start port-forward in background
kubectl port-forward \
  --namespace="$NAMESPACE" \
  svc/isi-mcp 18000:8000 &>/dev/null &
PF_PID=$!

# Give it a moment to establish
sleep 3

RESPONSE=$(curl -sf \
  -X POST http://localhost:18000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"deploy-check","version":"1.0"}}}' \
  2>/dev/null || echo "FAILED")

kill $PF_PID 2>/dev/null || true

if echo "$RESPONSE" | grep -q '"result"'; then
  ok "MCP server is responding correctly."
else
  warn "Could not verify MCP response (server may still be starting). Check logs:"
  echo "  kubectl logs -n $NAMESPACE deployment/isi-mcp --tail=20"
fi

# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}=============================="
echo -e " Deployment Complete"
echo -e "==============================${NC}"
echo ""
echo "Namespace : $NAMESPACE"
echo "Image     : ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "Useful commands:"
echo "  # Watch pod status"
echo "  kubectl get pods -n $NAMESPACE -w"
echo ""
echo "  # View server logs"
echo "  kubectl logs -n $NAMESPACE deployment/isi-mcp -f"
echo ""
echo "  # Port-forward for local access"
echo "  kubectl port-forward -n $NAMESPACE svc/isi-mcp 8000:8000"
echo "  # Then connect MCP client to http://localhost:8000"
echo ""
echo "  # Run K8s tests"
echo "  ./runtests-k8s.sh"
echo ""
echo "  # Teardown"
echo "  ./k8s/deploy-minikube.sh --teardown"
