#!/usr/bin/env bash
#
# runtests.sh — Set up the environment and run the full test suite.
#
# Part 1: Direct module tests (imports modules, talks to the cluster directly)
# Part 2: MCP server tests (talks to the MCP HTTP server via JSON-RPC)
#
# Usage:
#   ./runtests.sh -h                                                    # show help
#   ./runtests.sh --cluster-host HOST --cluster-user USER --cluster-pass PASS
#   ./runtests.sh --cluster-host HOST --cluster-user USER --cluster-pass PASS --part1
#   ./runtests.sh --cluster-host HOST --cluster-user USER --cluster-pass PASS --part2

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../../" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
ISI_MCP_DIR="${SCRIPT_DIR}/.."
TESTS_DIR="${SCRIPT_DIR}"
OVERRIDE_FILE="${TESTS_DIR}/docker-compose.test-override.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }

# ---------------------------------------------------------------------------
# Show help
# ---------------------------------------------------------------------------
show_help() {
    cat << 'HELP'
Usage: ./runtests.sh [OPTIONS]

Set up environment and run full test suite against a PowerScale cluster.

Required Arguments:
  --cluster-host HOST   Cluster hostname or IP address (e.g., 172.16.10.10)
  --cluster-user USER   Cluster username (e.g., root)
  --cluster-pass PASS   Cluster password

Optional Arguments:
  -o, --output-dir DIR  Top-level directory for test artifacts (default: /tmp)
                        A timestamped subdir isi_mcp_demo_tests_DDMMYYYY_HHMM is
                        created inside DIR for each run.
  --part1              Run only Part 1 (direct module tests)
  --part2              Run only Part 2 (MCP server tests)
  -h, --help           Show this help message

Examples:
  # Run full test suite against a cluster (artifacts go to /tmp/isi_mcp_demo_tests_<DATE>)
  ./runtests.sh --cluster-host 172.16.10.10 --cluster-user root --cluster-pass password

  # Run with a custom output directory
  ./runtests.sh --cluster-host 172.16.10.10 --cluster-user root --cluster-pass password -o /var/log/tests

  # Run only Part 1 tests
  ./runtests.sh --cluster-host 172.16.10.10 --cluster-user root --cluster-pass password --part1

  # Run only Part 2 tests
  ./runtests.sh --cluster-host 172.16.10.10 --cluster-user root --cluster-pass password --part2
HELP
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
RUN_PART1=true
RUN_PART2=true
CLUSTER_HOST=""
CLUSTER_USER=""
CLUSTER_PASS=""
OUTPUT_DIR="/tmp"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        --cluster-host)
            CLUSTER_HOST="$2"
            shift 2
            ;;
        --cluster-user)
            CLUSTER_USER="$2"
            shift 2
            ;;
        --cluster-pass)
            CLUSTER_PASS="$2"
            shift 2
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --part1)
            RUN_PART2=false
            shift
            ;;
        --part2)
            RUN_PART1=false
            shift
            ;;
        *)
            fail "Unknown option: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$CLUSTER_HOST" ]] || [[ -z "$CLUSTER_USER" ]] || [[ -z "$CLUSTER_PASS" ]]; then
    fail "Missing required arguments"
    echo ""
    show_help
    exit 1
fi

# ---------------------------------------------------------------------------
# 0a. Create timestamped output directory for test artifacts
# ---------------------------------------------------------------------------
DATE=$(date +%d%m%Y_%H%M)
TEST_OUTPUT_DIR="${OUTPUT_DIR}/isi_mcp_demo_tests_${DATE}"
mkdir -p "$TEST_OUTPUT_DIR"
info "Test artifacts will be written to: ${TEST_OUTPUT_DIR}"

# Set up log file for script output
RUNTESTS_LOG="${TEST_OUTPUT_DIR}/runtests.log"
exec 1> >(tee -a "$RUNTESTS_LOG")
exec 2> >(tee -a "$RUNTESTS_LOG" >&2)

# ---------------------------------------------------------------------------
# 0. Verify cluster reachability
# ---------------------------------------------------------------------------
info "Verifying cluster connectivity to ${CLUSTER_HOST}..."

# Extract host without protocol prefix (if present)
PING_HOST="$CLUSTER_HOST"
if [[ "$PING_HOST" =~ ^https?:// ]]; then
    PING_HOST="${PING_HOST#*://}"
    PING_HOST="${PING_HOST%:*}"  # Remove port if present
fi

if ! ping -c 1 -W 2 "$PING_HOST" > /dev/null 2>&1; then
    fail "Cluster host '${PING_HOST}' is not reachable"
    echo ""
    echo "Verify:"
    echo "  1. The cluster hostname/IP is correct: ${CLUSTER_HOST}"
    echo "  2. The cluster is online and accessible from this network"
    echo "  3. Firewall rules allow ICMP ping from this host"
    echo ""
    exit 1
fi
ok "Cluster ${PING_HOST} is reachable"

# ---------------------------------------------------------------------------
# 1. Create / activate virtual environment
# ---------------------------------------------------------------------------
info "Setting up Python virtual environment at ${VENV_DIR}"

if [[ ! -d "${VENV_DIR}" ]]; then
    python3 -m venv "${VENV_DIR}"
    ok "Created new venv"
else
    ok "Venv already exists"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
ok "Activated venv (python: $(python --version))"

# ---------------------------------------------------------------------------
# 2. Install dependencies
# ---------------------------------------------------------------------------
info "Installing project dependencies"
pip install --quiet -r "${ISI_MCP_DIR}/requirements.txt"
ok "Installed requirements.txt"

info "Installing test dependencies"
pip install --quiet -r "${ISI_MCP_DIR}/requirements-test.txt"
ok "Installed requirements-test.txt"

# ---------------------------------------------------------------------------
# 2.5. Set up vault file for tests
# ---------------------------------------------------------------------------
info "Setting up vault credentials for cluster ${CLUSTER_HOST}"

# Always create fresh vault.yml with provided credentials
# Create test vault password (remove any existing directory first)
rm -rf "${ROOT_DIR}/.vault_password"
echo "test-password" > "${ROOT_DIR}/.vault_password"
chmod 600 "${ROOT_DIR}/.vault_password"
ok "Created .vault_password"

# Determine if host includes protocol prefix
if [[ "$CLUSTER_HOST" =~ ^https?:// ]]; then
    VAULT_HOST="$CLUSTER_HOST"
else
    VAULT_HOST="https://${CLUSTER_HOST}"
fi

# Create vault directory and unencrypted vault with provided cluster credentials
mkdir -p "${ROOT_DIR}/vault"
cat > "${ROOT_DIR}/vault/vault.yml" << VAULT_EOF
# Test vault file - created by runtests.sh
# This file uses the cluster credentials provided at runtime
clusters:
  test_cluster:
    host: "${VAULT_HOST}"
    port: 8080
    username: ${CLUSTER_USER}
    password: ${CLUSTER_PASS}
    verify_ssl: false
VAULT_EOF

# Encrypt vault with ansible-vault
if command -v ansible-vault &> /dev/null; then
    ansible-vault encrypt "${ROOT_DIR}/vault/vault.yml" --vault-password-file "${ROOT_DIR}/.vault_password" 2>/dev/null
    ok "Created encrypted vault/vault.yml with cluster credentials"
else
    warn "ansible-vault not found in PATH, vault/vault.yml created unencrypted"
fi

# ---------------------------------------------------------------------------
# 3. Run Part 1 — Direct module tests
# ---------------------------------------------------------------------------
if [[ "${RUN_PART1}" == true ]]; then
    echo ""
    info "=========================================="
    info "  Part 1 — Direct module tests"
    info "=========================================="
    echo ""

    if TEST_CLUSTER_HOST="$CLUSTER_HOST" \
       TEST_CLUSTER_USER="$CLUSTER_USER" \
       TEST_CLUSTER_PASSWORD="$CLUSTER_PASS" \
       PLAYBOOKS_DIR="${TEST_OUTPUT_DIR}" \
       python -m pytest \
        "${TESTS_DIR}/test_modules.py" \
        "${TESTS_DIR}/test_phase1_readonly_modules.py" \
        "${TESTS_DIR}/test_phase8_readonly_modules.py" \
        "${TESTS_DIR}/test_nfs_client_validation.py" \
        "${TESTS_DIR}/test_path_normalization.py" \
        "${TESTS_DIR}/test_statistics_availability.py" \
        -v; then
        ok "Part 1 passed"
    else
        fail "Part 1 failed"
        if [[ "${RUN_PART2}" == true ]]; then
            warn "Continuing to Part 2 despite Part 1 failures..."
        else
            exit 1
        fi
    fi
fi

# ---------------------------------------------------------------------------
# 4. Manage docker-compose for MCP server
# ---------------------------------------------------------------------------
if [[ "${RUN_PART2}" == true ]]; then
    echo ""
    info "=========================================="
    info "  Preparing MCP server (docker-compose)"
    info "=========================================="
    echo ""

    # Write the test override file to redirect playbook artifacts to the output dir
    # and expose port 8000 directly (nginx is not used for testing)
    cat > "${OVERRIDE_FILE}" << EOF
services:
  isi_mcp:
    ports:
      - "8000:8000"
    volumes:
      - ${TEST_OUTPUT_DIR}:/app/playbooks
EOF
    info "Playbook artifacts will be written to: ${TEST_OUTPUT_DIR}"

    # Check if docker-compose services are already running
    if docker compose -f "${ROOT_DIR}/docker-compose.yml" -f "${OVERRIDE_FILE}" ps --status running 2>/dev/null | grep -q isi_mcp; then
        warn "MCP server container is already running — stopping and removing"
        docker compose -f "${ROOT_DIR}/docker-compose.yml" -f "${OVERRIDE_FILE}" down
        ok "Stopped and removed existing containers"
    elif docker-compose -f "${ROOT_DIR}/docker-compose.yml" -f "${OVERRIDE_FILE}" ps --filter "status=running" 2>/dev/null | grep -q isi_mcp; then
        warn "MCP server container is already running — stopping and removing"
        docker-compose -f "${ROOT_DIR}/docker-compose.yml" -f "${OVERRIDE_FILE}" down
        ok "Stopped and removed existing containers"
    fi

    info "Building and starting MCP server (all tools enabled for testing)"
    export ENABLE_ALL_TOOLS=true
    export VAULT_PASSWORD="test-password"
    docker compose -f "${ROOT_DIR}/docker-compose.yml" -f "${OVERRIDE_FILE}" up --build -d 2>/dev/null \
        || docker-compose -f "${ROOT_DIR}/docker-compose.yml" -f "${OVERRIDE_FILE}" up --build -d
    ok "MCP server container started"

    # Wait for the server to be ready (POST to /mcp since GET returns 406)
    info "Waiting for MCP server to be ready on port 8000..."
    MAX_WAIT=30
    WAITED=0
    until curl -sf -X POST http://localhost:8000/mcp \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"healthcheck","version":"1.0.0"}}}' \
        > /dev/null 2>&1 || [[ ${WAITED} -ge ${MAX_WAIT} ]]; do
        sleep 1
        WAITED=$((WAITED + 1))
    done

    if [[ ${WAITED} -ge ${MAX_WAIT} ]]; then
        fail "MCP server did not become ready within ${MAX_WAIT}s"
        info "Check logs with: docker compose -f ${ROOT_DIR}/docker-compose.yml logs"
        exit 1
    fi
    ok "MCP server is ready (took ${WAITED}s)"

    # -----------------------------------------------------------------------
    # 5. Run Part 2 — MCP server tests
    # -----------------------------------------------------------------------
    echo ""
    info "=========================================="
    info "  Part 2 — MCP server tests"
    info "=========================================="
    echo ""

    if TEST_CLUSTER_HOST="$CLUSTER_HOST" \
       TEST_CLUSTER_USER="$CLUSTER_USER" \
       TEST_CLUSTER_PASSWORD="$CLUSTER_PASS" \
       PLAYBOOKS_DIR="${TEST_OUTPUT_DIR}" \
       python -m pytest \
        "${TESTS_DIR}/test_mcp_server.py" \
        "${TESTS_DIR}/test_phase1_readonly_mcp.py" \
        "${TESTS_DIR}/test_phase2_lowrisk_mutations.py" \
        "${TESTS_DIR}/test_phase3_mutations.py" \
        "${TESTS_DIR}/test_phase4_filemgmt.py" \
        "${TESTS_DIR}/test_phase4_filemgmt_advanced.py" \
        "${TESTS_DIR}/test_phase4_datamover.py" \
        "${TESTS_DIR}/test_phase4_filepool.py" \
        "${TESTS_DIR}/test_phase5a_events_utilities.py" \
        "${TESTS_DIR}/test_phase5b_statistics_worm_sessions.py" \
        "${TESTS_DIR}/test_phase5c_identity_management.py" \
        "${TESTS_DIR}/test_phase6_network.py" \
        "${TESTS_DIR}/test_phase7_cluster_capacity.py" \
        "${TESTS_DIR}/test_phase8_readonly_mcp.py" \
        -v; then
        ok "Part 2 passed"
    else
        fail "Part 2 failed"
    fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
info "=========================================="
info "  Done"
info "=========================================="
echo ""
info "Test artifacts written to:  ${TEST_OUTPUT_DIR}"
info "Script output logged to:    ${RUNTESTS_LOG}"
info "To stop the MCP server:     docker compose -f ${ROOT_DIR}/docker-compose.yml down"
info "To rerun tests:             ${TESTS_DIR}/runtests.sh"
echo ""

# Blank the override file so the repo stays clean
> "${OVERRIDE_FILE}"

echo "Removing the venv environment"
rm -rf "${VENV_DIR}"
