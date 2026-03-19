#!/usr/bin/env bash
#
# setup.sh — First-time setup for the PowerScale MCP Server.
#
# Creates cluster credentials, encrypts them, builds the Docker image,
# and starts the MCP server. Requires only Docker — no Ansible needed on the host.
#
# Usage:
#   ./setup.sh                                         # interactive prompts
#   ./setup.sh --host 172.16.10.10 --pass secret       # non-interactive
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
  --host HOST         Cluster hostname or IP (e.g. 172.16.10.10 or https://172.16.10.10)
  --pass PASS         Cluster admin password

Optional:
  --port PORT         API port (default: 8080)
  --user USER         Cluster username (prompted with 'root' as default)
  --name NAME         Cluster label in vault.yml (default: isilon)
  --auth true|false   Enable OAuth authentication via Keycloak (default: false)
  -h, --help          Show this help message

Environment Variables (for non-interactive setup — avoid shell history):
  VAULT_PASSWORD              Vault encryption password (prompted if not set)
  KEYCLOAK_DB_PASSWORD        Keycloak database password when --auth true (prompted if not set)
  KEYCLOAK_ADMIN_PASSWORD     Keycloak admin password when --auth true (prompted if not set)

Examples:
  # Interactive setup (prompts for all required values)
  ./setup.sh

  # Non-interactive setup using read to avoid shell history
  read -s -p 'Vault password: ' VAULT_PASSWORD && export VAULT_PASSWORD
  read -s -p 'Cluster password: ' CLUSTER_PASS
  ./setup.sh --host 172.16.10.10 --user root --pass "$CLUSTER_PASS"

  # Setup with auth enabled
  read -s -p 'Vault password: ' VAULT_PASSWORD && export VAULT_PASSWORD
  read -s -p 'Keycloak DB password: ' KEYCLOAK_DB_PASSWORD && export KEYCLOAK_DB_PASSWORD
  read -s -p 'Keycloak admin password: ' KEYCLOAK_ADMIN_PASSWORD && export KEYCLOAK_ADMIN_PASSWORD
  ./setup.sh --host 172.16.10.10 --auth true

After setup, restart the server with vault password:
  read -s -p 'Vault password: ' VAULT_PASSWORD && export VAULT_PASSWORD
  docker compose up -d

To edit vault credentials later (requires vault password):
  docker compose exec isi_mcp ansible-vault edit /app/vault/vault.yml
HELP
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
CLUSTER_HOST=""
CLUSTER_PORT=8080
CLUSTER_USER=""
CLUSTER_PASS=""
CLUSTER_NAME="isilon"
VAULT_PASS="${VAULT_PASSWORD:-}"
AUTH_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)       CLUSTER_HOST="$2"; shift 2 ;;
        --port)       CLUSTER_PORT="$2"; shift 2 ;;
        --user)       CLUSTER_USER="$2"; shift 2 ;;
        --pass)       CLUSTER_PASS="$2"; shift 2 ;;
        --name)       CLUSTER_NAME="$2"; shift 2 ;;
        --auth)       AUTH_ARG="$2"; shift 2 ;;
        -h|--help)    show_help; exit 0 ;;
        *)            fail "Unknown argument: $1"; echo "Run ./setup.sh --help for usage."; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Apply --auth argument to config/isi_mcp.env if provided
# ---------------------------------------------------------------------------
APP_CONFIG_EARLY="${SCRIPT_DIR}/config/isi_mcp.env"
if [[ -n "$AUTH_ARG" ]]; then
    if [[ "$AUTH_ARG" == "true" || "$AUTH_ARG" == "false" ]]; then
        sed -i "s/^AUTH_ENABLED=.*/AUTH_ENABLED=${AUTH_ARG}/" "$APP_CONFIG_EARLY"
        ok "Set AUTH_ENABLED=${AUTH_ARG} in config/isi_mcp.env"
    else
        fail "--auth must be 'true' or 'false' (got: ${AUTH_ARG})"
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Check prerequisites (docker and docker-compose required for setup)
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
# Check for existing setup (vault.yml and/or keycloak-db-data volume)
# Ask before prompting for new credentials
# ---------------------------------------------------------------------------
VAULT_DIR="${SCRIPT_DIR}/vault"
VAULT_FILE="${VAULT_DIR}/vault.yml"
SKIP_SETUP=false
KEYCLOAK_DB_VOLUME="isi_mcp_demo_keycloak-db-data"

mkdir -p "$VAULT_DIR"

# Pre-create playbooks dir as the current user so Docker doesn't create it as root.
# The container runs as mcp (UID 1000); the host user running setup.sh must also be
# UID 1000 (or the directory must be group/world writable) for writes to succeed.
mkdir -p "${SCRIPT_DIR}/playbooks"

# Check for existing vault and keycloak volume
VAULT_EXISTS=false
KEYCLOAK_VOLUME_EXISTS=false

if [[ -f "$VAULT_FILE" ]]; then
    FIRST_LINE="$(head -c 14 "$VAULT_FILE")"
    if [[ "$FIRST_LINE" == '$ANSIBLE_VAULT' ]]; then
        VAULT_EXISTS=true
    fi
fi

if docker volume ls 2>/dev/null | grep -q "$KEYCLOAK_DB_VOLUME"; then
    KEYCLOAK_VOLUME_EXISTS=true
fi

# If either exists, prompt user
if [[ "$VAULT_EXISTS" == true ]] || [[ "$KEYCLOAK_VOLUME_EXISTS" == true ]]; then
    EXISTING_STATE=""
    [[ "$VAULT_EXISTS" == true ]] && EXISTING_STATE="${EXISTING_STATE}  • vault.yml (encrypted credentials)\n"
    [[ "$KEYCLOAK_VOLUME_EXISTS" == true ]] && EXISTING_STATE="${EXISTING_STATE}  • keycloak-db-data (database volume)\n"

    warn "Existing setup detected:\n${EXISTING_STATE}"
    read -rp "Keep existing setup and skip credential setup? [Y/n]: " KEEP_SETUP

    if [[ "$KEEP_SETUP" != "n" && "$KEEP_SETUP" != "N" ]]; then
        ok "Keeping existing setup — skipping credential setup."
        SKIP_SETUP=true
    else
        # User wants to overwrite — delete existing setup
        info "Removing existing setup..."

        # Delete vault directory if it exists (removes vault.yml + any *.pem files)
        if [[ "$VAULT_EXISTS" == true ]]; then
            rm -rf "$VAULT_DIR"
            ok "Removed vault directory"
        fi

        # Remove cluster cert PEM files (in case vault was deleted separately)
        rm -f "${VAULT_DIR}"/*.pem 2>/dev/null || true

        # Remove TLS certs so setup.sh generates fresh ones
        if [[ -d "${SCRIPT_DIR}/nginx/certs" ]]; then
            rm -rf "${SCRIPT_DIR}/nginx/certs"
            ok "Removed nginx/certs (will regenerate)"
        fi

        # Remove rendered playbooks from prior run
        rm -f "${SCRIPT_DIR}/playbooks"/*.yml 2>/dev/null || true

        # Stop containers and remove volume
        if [[ "$KEYCLOAK_VOLUME_EXISTS" == true ]]; then
            info "Stopping containers..."
            $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" down 2>/dev/null || true

            info "Removing keycloak database volume..."
            docker volume rm "$KEYCLOAK_DB_VOLUME" 2>/dev/null || warn "Could not remove volume (may be in use)"
            ok "Removed keycloak-db-data"
        fi

        ok "Existing setup cleared — proceeding with fresh installation"
    fi
fi

# ---------------------------------------------------------------------------
# Prompt for cluster credentials (only if not keeping existing vault)
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == false ]]; then
    while [[ -z "$CLUSTER_HOST" ]]; do
        read -rp "Cluster host: " input_host
        CLUSTER_HOST="$input_host"
        if [[ -z "$CLUSTER_HOST" ]]; then
            warn "Cluster host is required."
        fi
    done

    while [[ -z "$CLUSTER_USER" ]]; do
        read -rp "Cluster username: " input_user
        CLUSTER_USER="$input_user"
        if [[ -z "$CLUSTER_USER" ]]; then
            warn "Cluster username is required."
        fi
    done

    while [[ -z "$CLUSTER_PASS" ]]; do
        read -rsp "Cluster password for ${CLUSTER_USER}@${CLUSTER_HOST}: " input_pass
        echo
        CLUSTER_PASS="$input_pass"
        if [[ -z "$CLUSTER_PASS" ]]; then
            warn "Cluster password is required."
        fi
    done
fi

# ---------------------------------------------------------------------------
# Prompt for vault password (always needed to encrypt/decrypt vault)
# ---------------------------------------------------------------------------
if [[ -z "$VAULT_PASS" ]]; then
    read -rsp "Vault encryption password (for vault.yml): " VAULT_PASS
    echo
fi
if [[ -z "$VAULT_PASS" ]]; then
    fail "Vault password is required."
    exit 1
fi

# ---------------------------------------------------------------------------
# Check config/isi_mcp.env to see if authentication is enabled.
# Set AUTH_ENABLED=true there to enable OAuth via Keycloak.
# If enabled, prompt for Keycloak passwords (never stored in files).
# ---------------------------------------------------------------------------
APP_CONFIG="${APP_CONFIG_EARLY}"
COMPOSE_PROFILES=""
if grep -qE '^AUTH_ENABLED=true' "$APP_CONFIG" 2>/dev/null; then
    info "Authentication is enabled in config/isi_mcp.env. Keycloak credentials required."
    if [[ -z "${KEYCLOAK_DB_PASSWORD:-}" ]]; then
        read -rsp "Keycloak database password (KEYCLOAK_DB_PASSWORD): " KEYCLOAK_DB_PASSWORD
        echo
        export KEYCLOAK_DB_PASSWORD
    fi
    if [[ -z "$KEYCLOAK_DB_PASSWORD" ]]; then
        fail "KEYCLOAK_DB_PASSWORD is required when AUTH_ENABLED=true."
        exit 1
    fi
    if [[ -z "${KEYCLOAK_ADMIN_PASSWORD:-}" ]]; then
        read -rsp "Keycloak admin password (KEYCLOAK_ADMIN_PASSWORD): " KEYCLOAK_ADMIN_PASSWORD
        echo
        export KEYCLOAK_ADMIN_PASSWORD
    fi
    if [[ -z "$KEYCLOAK_ADMIN_PASSWORD" ]]; then
        fail "KEYCLOAK_ADMIN_PASSWORD is required when AUTH_ENABLED=true."
        exit 1
    fi
    COMPOSE_PROFILES="--profile auth"
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
# Initialize cluster CA bundle variable (will be set during cert extraction)
# ---------------------------------------------------------------------------
CLUSTER_CA_BUNDLE=""

# ---------------------------------------------------------------------------
# Write plaintext vault.yml (will be encrypted in the next step)
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == false ]]; then
    {
        cat << VAULT_EOF
clusters:
  ${CLUSTER_NAME}:
    host: "${VAULT_HOST}"
    port: ${CLUSTER_PORT}
    username: ${CLUSTER_USER}
    password: ${CLUSTER_PASS}
    verify_ssl: true
VAULT_EOF
        if [[ -n "${KEYCLOAK_DB_PASSWORD:-}" ]]; then
            cat << KEYCLOAK_EOF

keycloak:
  db_password: ${KEYCLOAK_DB_PASSWORD}
  admin_password: ${KEYCLOAK_ADMIN_PASSWORD}
KEYCLOAK_EOF
        fi
    } > "$VAULT_FILE"
    chmod 600 "$VAULT_FILE"
    ok "Created vault.yml (plaintext — will encrypt next)"
fi

# ---------------------------------------------------------------------------
# Generate TLS certificates for nginx (if not already present)
# ---------------------------------------------------------------------------
CERT_SCRIPT="${SCRIPT_DIR}/nginx/generate-certs.sh"
if [[ -x "$CERT_SCRIPT" ]]; then
    info "Checking TLS certificates..."
    "$CERT_SCRIPT"
else
    warn "nginx/generate-certs.sh not found — skipping TLS cert generation."
    warn "Run nginx/generate-certs.sh manually before starting with HTTPS."
fi

# ---------------------------------------------------------------------------
# Build the Docker image (required so Ansible is available for encryption)
# ---------------------------------------------------------------------------
info "Building Docker image..."
$COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" build
ok "Image built"

# ---------------------------------------------------------------------------
# Extract cluster TLS certificate (for SSL verification without replacing cert)
#
# Uses the just-built Docker image — no openssl needed on the host.
# The vault dir is already bind-mounted at /app/vault inside the container.
# Extracts the cert and saves it to vault/${CLUSTER_NAME}_cert.pem, then updates vault.yml.
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == false ]]; then
    HOST_BARE="${VAULT_HOST#https://}"  # strip https:// prefix
    HOST_BARE="${HOST_BARE#http://}"
    info "Extracting cluster TLS certificate for SSL verification..."

    # Use openssl inside the container to extract the certificate
    CERT_EXTRACTED=false
    if $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" run --rm isi_mcp \
        sh -c "openssl s_client -connect ${HOST_BARE}:${CLUSTER_PORT} \
               -showcerts </dev/null 2>/dev/null \
               | openssl x509 -outform PEM \
               > /app/vault/${CLUSTER_NAME}_cert.pem" 2>/dev/null \
        && [[ -s "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" ]]; then
        CERT_EXTRACTED=true
    fi

    # Inspect the extracted cert to decide the SSL strategy.
    #
    # Three cases:
    #   a) CA-signed cert (Subject != Issuer): customer installed their own cert.
    #      Keep verify_ssl: true and rely on the system CA store.
    #   b) Self-signed with CA:TRUE: valid v3 self-signed CA cert.
    #      Store as ca_bundle for cert pinning.
    #   c) Self-signed without CA:TRUE: PowerScale default X.509 v1 cert.
    #      Cannot be used as a CA bundle — set verify_ssl: false.
    CERT_IS_CA=false
    IS_SELF_SIGNED=false
    if [[ "$CERT_EXTRACTED" == true ]]; then
        if openssl x509 -in "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" -text -noout 2>/dev/null \
            | grep -q "CA:TRUE"; then
            CERT_IS_CA=true
        fi
        SUBJECT=$(openssl x509 -in "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" -noout -subject 2>/dev/null | sed 's/subject=//')
        ISSUER=$(openssl x509  -in "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" -noout -issuer  2>/dev/null | sed 's/issuer=//')
        if [[ "$SUBJECT" == "$ISSUER" ]]; then
            IS_SELF_SIGNED=true
        fi
    fi

    if [[ "$IS_SELF_SIGNED" == true && "$CERT_IS_CA" == true ]]; then
        # (b) Self-signed v3 CA cert — use for cert pinning
        ok "Cluster certificate saved to vault/${CLUSTER_NAME}_cert.pem (CA:TRUE — cert pinning enabled)"
        CLUSTER_CA_BUNDLE="/app/vault/${CLUSTER_NAME}_cert.pem"
        if grep -q "^    ca_bundle:" "$VAULT_FILE" 2>/dev/null; then
            sed -i "s|^    ca_bundle:.*|    ca_bundle: ${CLUSTER_CA_BUNDLE}|" "$VAULT_FILE"
        else
            sed -i "/^    verify_ssl:/a\\    ca_bundle: ${CLUSTER_CA_BUNDLE}" "$VAULT_FILE"
        fi
    elif [[ "$IS_SELF_SIGNED" == false && "$CERT_EXTRACTED" == true ]]; then
        # (a) CA-signed cert — keep verify_ssl: true, use system CA store
        rm -f "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" 2>/dev/null || true
        ok "Cluster has a CA-signed certificate — SSL verification enabled using system CA store."
    else
        # (c) Self-signed without CA:TRUE (PowerScale v1 default) or extraction failed
        rm -f "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" 2>/dev/null || true
        if [[ "$CERT_EXTRACTED" == true ]]; then
            warn "Cluster cert is X.509 v1 self-signed (no CA:TRUE) — typical for PowerScale default certs."
        else
            warn "Could not extract cluster certificate."
        fi
        warn "Setting verify_ssl: false in vault.yml — SSL certificate will not be verified."
        sed -i "s/^    verify_ssl:.*/    verify_ssl: false/" "$VAULT_FILE"
    fi
fi

# ---------------------------------------------------------------------------
# Encrypt vault.yml using VaultLib Python API inside the built image.
#
# We read the plaintext /app/vault/vault.yml (via the directory bind mount),
# encrypt it in-memory with VaultLib, and write to stdout. On the host we
# redirect stdout to a temp file and then rename it atomically.
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
plaintext = open('/app/vault/vault.yml', 'rb').read()
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
info "MCP server will be available at: https://localhost/mcp (via nginx)"
info "  Direct backend (no TLS):      http://localhost:8000 (not exposed by default)"
echo ""
warn "IMPORTANT: Save your vault password in a secure location!"
warn "You will need it to restart the server later."
echo ""
info "Connect your LLM client:"
echo "  Claude Code: claude mcp add --transport http powerscale https://localhost/mcp"
echo "  Claude Desktop: Add to claude_desktop_config.json:"
echo '    { "mcpServers": { "powerscale": { "url": "https://localhost/mcp" } } }'
echo "  Cursor/Windsurf SSE endpoint: https://localhost/sse"
echo ""
warn "Note: Self-signed certs require clients to accept untrusted certificates."
echo ""
info "To restart the server later (requires vault password):"
echo "  read -s -p 'Vault password: ' VAULT_PASSWORD && export VAULT_PASSWORD"
if [[ -n "$COMPOSE_PROFILES" ]]; then
echo "  read -s -p 'Keycloak DB password: ' KEYCLOAK_DB_PASSWORD && export KEYCLOAK_DB_PASSWORD"
echo "  read -s -p 'Keycloak admin password: ' KEYCLOAK_ADMIN_PASSWORD && export KEYCLOAK_ADMIN_PASSWORD"
fi
echo "  $COMPOSE_CMD -f ${SCRIPT_DIR}/docker-compose.yml $COMPOSE_PROFILES up -d"
echo ""
info "To add or edit clusters later:"
echo "  $COMPOSE_CMD -f ${SCRIPT_DIR}/docker-compose.yml exec isi_mcp ansible-vault edit /app/vault/vault.yml"
echo ""
info "To stop the server:"
echo "  $COMPOSE_CMD -f ${SCRIPT_DIR}/docker-compose.yml down"
echo ""
info "To start claude with the Powerscale Agent:"
echo "claude --agent PowerscaleAgent --agents '{
  "PowerscaleAgent": {
    "description": "Interacts with the MCP server using detailed context",
    "prompt": "You are a knowledgeable assistant for managing a Powerscale Cluster.",
    "context": "AGENT-CONTEXT.md"
  }
}'"
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
$COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" $COMPOSE_PROFILES down 2>/dev/null || true

info "Starting MCP server in background..."
VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" $COMPOSE_PROFILES up -d
ok "Server started. View logs: $COMPOSE_CMD -f ${SCRIPT_DIR}/docker-compose.yml logs -f"
