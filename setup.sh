#!/usr/bin/env bash
#
# setup.sh — First-time setup for the PowerScale MCP Server.
#
# Creates cluster credentials, encrypts them, builds the Docker image,
# and starts the MCP server. Requires only Docker — no Ansible needed on the host.
#
# Usage:
#   ./setup.sh                                         # interactive prompts
#   ./setup.sh --host 192.168.0.33 --pass secret       # non-interactive
#   ./setup.sh --host 192.168.0.33 --pass secret --detach
#   ./setup.sh -h

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }

# ---------------------------------------------------------------------------
# Show help
# ---------------------------------------------------------------------------
show_help() {
    cat << 'HELP'
Usage: ./setup.sh [OPTIONS]

First-time setup for the PowerScale MCP Server.
Creates encrypted cluster credentials, builds the Docker image, and starts the server.

Required (prompted interactively if not provided):
  --host HOST     Cluster hostname or IP (e.g. 192.168.0.33 or https://192.168.0.33)
  --pass PASS     Cluster admin password

Optional:
  --port PORT     API port (default: 8080)
  --user USER     Cluster username (default: root)
  --name NAME     Cluster label in vault.yml (default: my_cluster)
  --vault-pass VAULTPASS  Vault encryption password (prompted if not provided)
  --detach        Start the server in the background (default: foreground)
  -h, --help      Show this help message

Examples:
  # Interactive setup (prompts for host, cluster password, and vault password)
  ./setup.sh

  # Non-interactive setup
  ./setup.sh --host 192.168.0.33 --user root --pass secret --vault-pass vaultkey123

  # Start in background
  ./setup.sh --host 192.168.0.33 --pass secret --vault-pass vaultkey123 --detach

After setup, restart the server with vault password:
  docker compose up -e VAULT_PASSWORD=vaultkey123

To edit vault credentials later (requires vault password):
  # First, decrypt locally
  echo -n "vaultkey123" | ansible-vault view vault.yml
  # Or use docker-compose with VAULT_PASSWORD set
  docker compose exec -e VAULT_PASSWORD=vaultkey123 isi_mcp bash
HELP
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
CLUSTER_HOST=""
CLUSTER_PORT=8080
CLUSTER_USER="root"
CLUSTER_PASS=""
CLUSTER_NAME="my_cluster"
VAULT_PASS=""
NODETACH=true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)       CLUSTER_HOST="$2"; shift 2 ;;
        --port)       CLUSTER_PORT="$2"; shift 2 ;;
        --user)       CLUSTER_USER="$2"; shift 2 ;;
        --pass)       CLUSTER_PASS="$2"; shift 2 ;;
        --name)       CLUSTER_NAME="$2"; shift 2 ;;
        --vault-pass) VAULT_PASS="$2"; shift 2 ;;
        --nodetach)     NODETACH=false; shift ;;
        -h|--help)    show_help; exit 0 ;;
        *)            fail "Unknown argument: $1"; echo "Run ./setup.sh --help for usage."; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Check prerequisites
# ---------------------------------------------------------------------------
if ! command -v docker &>/dev/null; then
    fail "Docker is not installed."
    fail "Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if docker compose version &>/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
else
    fail "docker-compose is not available."
    fail "Install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# ---------------------------------------------------------------------------
# Prompt for missing required arguments
# ---------------------------------------------------------------------------
if [[ -z "$CLUSTER_HOST" ]]; then
    read -rp "Cluster host (e.g. 192.168.0.33): " CLUSTER_HOST
fi
if [[ -z "$CLUSTER_HOST" ]]; then
    fail "Cluster host is required."
    exit 1
fi

if [[ -z "$CLUSTER_PASS" ]]; then
    read -rsp "Cluster password for ${CLUSTER_USER}@${CLUSTER_HOST}: " CLUSTER_PASS
    echo
fi
if [[ -z "$CLUSTER_PASS" ]]; then
    fail "Cluster password is required."
    exit 1
fi

if [[ -z "$VAULT_PASS" ]]; then
    read -rsp "Vault encryption password (for vault.yml): " VAULT_PASS
    echo
fi
if [[ -z "$VAULT_PASS" ]]; then
    fail "Vault password is required."
    exit 1
fi

# ---------------------------------------------------------------------------
# Normalize host — ensure https:// prefix
# ---------------------------------------------------------------------------
if [[ "$CLUSTER_HOST" =~ ^https?:// ]]; then
    VAULT_HOST="$CLUSTER_HOST"
else
    VAULT_HOST="https://${CLUSTER_HOST}"
fi

# ---------------------------------------------------------------------------
# Check for existing encrypted vault — ask before overwriting
# ---------------------------------------------------------------------------
VAULT_FILE="${SCRIPT_DIR}/vault.yml"
SKIP_SETUP=false

if [[ -f "$VAULT_FILE" ]]; then
    FIRST_LINE="$(head -c 14 "$VAULT_FILE")"
    if [[ "$FIRST_LINE" == '$ANSIBLE_VAULT' ]]; then
        warn "vault.yml already exists and is encrypted."
        read -rp "Reconfigure with new cluster credentials? [y/N]: " RECONFIGURE
        if [[ "$RECONFIGURE" != "y" && "$RECONFIGURE" != "Y" ]]; then
            ok "Keeping existing vault.yml — skipping credential setup."
            SKIP_SETUP=true
        fi
    else
        warn "vault.yml exists but is not encrypted — it will be overwritten and encrypted."
    fi
fi

# ---------------------------------------------------------------------------
# Write plaintext vault.yml (will be encrypted in the next step)
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == false ]]; then
    cat > "$VAULT_FILE" << VAULT_EOF
clusters:
  ${CLUSTER_NAME}:
    host: "${VAULT_HOST}"
    port: ${CLUSTER_PORT}
    username: ${CLUSTER_USER}
    password: ${CLUSTER_PASS}
    verify_ssl: false
VAULT_EOF
    chmod 600 "$VAULT_FILE"
    ok "Created vault.yml (plaintext — will encrypt next)"
fi

# ---------------------------------------------------------------------------
# Build the Docker image (required so Ansible is available for encryption)
# ---------------------------------------------------------------------------
info "Building Docker image..."
$COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" build
ok "Image built"

# ---------------------------------------------------------------------------
# Encrypt vault.yml using VaultLib Python API inside the built image.
#
# We read the plaintext /app/vault.yml (via the existing :ro service mount),
# encrypt it in-memory with VaultLib, and write to stdout. On the host we
# redirect stdout to a temp file and then rename it atomically. This avoids
# the EBUSY error that ansible-vault encrypt triggers when it tries to shred
# the original file via os.remove() on a Docker bind-mounted path.
#
# The vault password is passed directly (never stored on disk).
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == false ]]; then
    info "Encrypting vault.yml..."
    VAULT_TMP="${VAULT_FILE}.tmp"
    $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" run --rm isi_mcp \
        python3 -c "
import sys
from ansible.parsing.vault import VaultLib, VaultSecret
# Read password from stdin (passed via environment via -e)
password = sys.argv[1].encode() if len(sys.argv) > 1 else b''
if not password:
    print('ERROR: Vault password required', file=sys.stderr)
    sys.exit(1)
vault = VaultLib([('default', VaultSecret(password))])
plaintext = open('/app/vault.yml', 'rb').read()
encrypted = vault.encrypt(plaintext)
sys.stdout.buffer.write(encrypted if isinstance(encrypted, bytes) else encrypted.encode())
" "$VAULT_PASS" > "${VAULT_TMP}"
    mv "${VAULT_TMP}" "${VAULT_FILE}"
    chmod 600 "${VAULT_FILE}"
    ok "vault.yml encrypted"
fi

# ---------------------------------------------------------------------------
# Print connection instructions (before starting so they're visible above logs)
# ---------------------------------------------------------------------------
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ok "Setup complete! Connecting to: ${VAULT_HOST}:${CLUSTER_PORT} as ${CLUSTER_USER}"
echo ""
info "MCP server will be available at: http://localhost:8000"
echo ""
warn "IMPORTANT: Save your vault password in a secure location!"
warn "You will need it to restart the server later."
echo ""
info "Connect your LLM client:"
echo "  Claude Code: claude mcp add --transport http powerscale http://localhost:8000/mcp"
echo "  Claude Desktop: Add to claude_desktop_config.json:"
echo '    { "mcpServers": { "powerscale": { "url": "http://localhost:8000/mcp" } } }'
echo "  Cursor/Windsurf SSE endpoint: http://localhost:8000/sse"
echo ""
info "To restart the server later (requires vault password):"
echo "  VAULT_PASSWORD='your-vault-password' $COMPOSE_CMD -f ${SCRIPT_DIR}/docker-compose.yml up -d"
echo ""
info "To add or edit clusters later:"
echo "  # View encrypted vault (requires vault password):"
echo "  echo -n 'your-vault-password' | $COMPOSE_CMD -f ${SCRIPT_DIR}/docker-compose.yml run --rm isi_mcp ansible-vault view /app/vault.yml"
echo ""
info "To stop the server:"
echo "  $COMPOSE_CMD -f ${SCRIPT_DIR}/docker-compose.yml down"
echo ""
info "To start claude with the Powerscale Agent:"
echo "claude --agents '{"PowerscaleAgent": {"description": "Interacts with the MCP server using detailed context", "prompt": "You are a knowledgeable assistant for managing a Powerscale Cluster.", "context": "CONTEXT.md"}}'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ---------------------------------------------------------------------------
# Start the server.
#
# Stop any existing container first. docker-compose v1 (<=1.29.2) has a bug
# where recreating a container reads 'ContainerConfig' from the image manifest,
# which was removed in newer Docker Engine versions, causing a KeyError. Stopping
# the old container before 'up' avoids the recreate path entirely.
# ---------------------------------------------------------------------------
info "Stopping any existing container..."
$COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" down 2>/dev/null || true

if [[ "$NODETACH" == true ]]; then
    info "Starting MCP server in background..."
    VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" up -d
    ok "Server started. View logs: $COMPOSE_CMD -f ${SCRIPT_DIR}/docker-compose.yml logs -f"
else
    info "Starting MCP server (Ctrl+C to stop)..."
    VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" up
fi
