#!/usr/bin/env bash
#
# start.sh — Start the PowerScale MCP Server
#
# Usage:
#   ./start.sh            — Start services (prompts for required passwords)
#   ./start.sh --reboot   — Tear down existing services first, then start fresh
#   ./start.sh -h         — Show this help
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
REBOOT=false

# ---------------------------------------------------------------------------
# Verify Docker and a Compose implementation are present and the daemon is up.
# Prefers the Compose v2 plugin ("docker compose") over the legacy standalone
# "docker-compose" (v1, end-of-life July 2023). Exits with install guidance if
# anything required is missing.
# ---------------------------------------------------------------------------
if ! command -v docker &>/dev/null; then
    echo "ERROR: Docker is not installed or not on PATH."
    echo "Install Docker Engine: https://docs.docker.com/engine/install/"
    exit 1
fi
if ! docker info &>/dev/null; then
    echo "ERROR: Docker is installed but its daemon is not reachable."
    echo "Start Docker (e.g. 'sudo systemctl start docker') and ensure your user is"
    echo "in the 'docker' group, then re-run this script."
    exit 1
fi
if docker compose version &>/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
    echo "WARNING: Using legacy 'docker-compose' (Compose v1), which is end-of-life (July 2023)."
    echo "         Upgrade to the Compose v2 plugin: https://docs.docker.com/compose/install/linux/"
else
    echo "ERROR: Docker Compose is not available (neither 'docker compose' nor 'docker-compose')."
    echo "Install the Compose v2 plugin: https://docs.docker.com/compose/install/linux/"
    exit 1
fi

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
for arg in "$@"; do
    case "$arg" in
        --reboot) REBOOT=true ;;
        -h|--help)
            sed -n '2,7p' "$0" | sed 's/^# *//'
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--reboot]"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Ensure TLS certificates exist when SSL=true (checked after env init below)
# ---------------------------------------------------------------------------
CERT_SCRIPT="${SCRIPT_DIR}/nginx/generate-certs.sh"
CERT_DIR="${SCRIPT_DIR}/nginx/certs"

# ---------------------------------------------------------------------------
# Initialize config env files from .env.sample if they don't exist yet
# (first-time use, or after a git pull that added new .env.sample files)
# ---------------------------------------------------------------------------
for _sample in "${SCRIPT_DIR}/config/"*.env.sample; do
    _env="${_sample%.sample}"
    if [[ ! -f "$_env" ]]; then
        cp "$_sample" "$_env"
        echo "Created $(basename "$_env") from $(basename "$_sample")"
    fi
done

# Read PORT and SSL from config; export the right port var for docker-compose
PORT=$(grep '^PORT=' "${SCRIPT_DIR}/config/isi_mcp.env" 2>/dev/null | cut -d= -f2- | tr -d ' ')
PORT="${PORT:-80}"
SSL=$(grep '^SSL=' "${SCRIPT_DIR}/config/isi_mcp.env" 2>/dev/null | cut -d= -f2- | tr -d ' ')
SSL="${SSL:-false}"
if [[ "$SSL" == "true" ]]; then
    export HTTPS_PORT="$PORT"
else
    export PORT="$PORT"
fi

# Ensure TLS certificates exist when SSL=true
if [[ "$SSL" == "true" ]]; then
    if [ ! -f "${CERT_DIR}/server.crt" ] || [ ! -f "${CERT_DIR}/server.key" ]; then
        if [[ -x "$CERT_SCRIPT" ]]; then
            echo "TLS certificates not found — generating..."
            "$CERT_SCRIPT"
        else
            echo "ERROR: nginx/generate-certs.sh not found and TLS certs are missing."
            echo "Run nginx/generate-certs.sh manually or place cert files in nginx/certs/."
            exit 1
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Detect whether authentication is enabled in config/isi_mcp.env
# ---------------------------------------------------------------------------
APP_CONFIG="${SCRIPT_DIR}/config/isi_mcp.env"
COMPOSE_PROFILES=""
if grep -qE '^AUTH_ENABLED=true' "$APP_CONFIG" 2>/dev/null; then
    AUTH_ENABLED=true
else
    AUTH_ENABLED=false
fi

# ---------------------------------------------------------------------------
# Prompt for vault password (always required)
# ---------------------------------------------------------------------------
export VAULT_PASSWORD
VAULT_PASSWORD=$(read -rs -p 'Vault password: ' pwd && echo "$pwd")
echo

# ---------------------------------------------------------------------------
# Determine if Keycloak needs initialization
# ---------------------------------------------------------------------------
KEYCLOAK_DB_VOLUME="isi_mcp_demo_keycloak-db-data"
KEYCLOAK_DB_EXISTS=$(docker volume ls 2>/dev/null | grep -q "$KEYCLOAK_DB_VOLUME" && echo true || echo false)

# Keycloak needs initialization if: (1) volume doesn't exist, OR (2) --reboot is set
KEYCLOAK_NEEDS_INIT=false
if [[ "$AUTH_ENABLED" == true ]]; then
    if [[ "$KEYCLOAK_DB_EXISTS" == false ]] || [[ "$REBOOT" == true ]]; then
        KEYCLOAK_NEEDS_INIT=true
    fi
    COMPOSE_PROFILES="--profile auth"
fi

# ---------------------------------------------------------------------------
# Resolve Keycloak passwords (from vault, or prompt as fallback)
# ---------------------------------------------------------------------------
# Helper: decrypt vault and extract a top-level keycloak.<key> value.
# Uses the already-built isi_mcp image so no host-side ansible is needed.
_vault_get_keycloak() {
    local key="$1"
    local _raw
    # Use a unique line-prefix marker so grep can isolate vault output even if
    # docker compose prints container lifecycle messages to stdout on this platform.
    _raw=$($COMPOSE_CMD -f "$COMPOSE_FILE" run --rm --no-deps \
        -e VAULT_PASSWORD \
        isi_mcp python3 -c "
import os, yaml
from ansible.parsing.vault import VaultLib, VaultSecret
pwd = os.environ.get('VAULT_PASSWORD', '').encode()
vault = VaultLib([('default', VaultSecret(pwd))])
try:
    data = yaml.safe_load(vault.decrypt(open('/app/vault/vault.yml').read()))
    kc = data.get('keycloak') if isinstance(data, dict) else None
    val = kc.get('$key') if isinstance(kc, dict) else None
    print('__VAULT__' + str(val) if val else '__VAULT__', end='')
except Exception:
    print('__VAULT__', end='')
" 2>/dev/null) || true
    printf '%s' "$_raw" | grep -o '__VAULT__.*' | sed 's/^__VAULT__//'
}

if [[ "$AUTH_ENABLED" == true ]]; then
    # DB password is needed every startup (keycloak connects to postgres on boot).
    export KEYCLOAK_DB_PASSWORD
    KEYCLOAK_DB_PASSWORD=$(_vault_get_keycloak "db_password")
    if [[ -z "$KEYCLOAK_DB_PASSWORD" ]]; then
        echo "WARNING: Keycloak DB password not found in vault (vault.yml missing or keycloak.db_password not set)."
        KEYCLOAK_DB_PASSWORD=$(read -rs -p 'Keycloak DB password: ' pwd && echo "$pwd")
        echo
    else
        echo "Keycloak DB password: (loaded from vault)"
    fi

    # Admin bootstrap password only needed when initialising for the first time.
    export KEYCLOAK_ADMIN_PASSWORD
    if [[ "$KEYCLOAK_NEEDS_INIT" == true ]]; then
        KEYCLOAK_ADMIN_PASSWORD=$(_vault_get_keycloak "admin_password")
        if [[ -z "$KEYCLOAK_ADMIN_PASSWORD" ]]; then
            echo "WARNING: Keycloak admin password not found in vault (vault.yml missing or keycloak.admin_password not set)."
            KEYCLOAK_ADMIN_PASSWORD=$(read -rs -p 'Keycloak admin password: ' pwd && echo "$pwd")
            echo
        else
            echo "Keycloak admin password: (loaded from vault)"
        fi
    else
        KEYCLOAK_ADMIN_PASSWORD=""
    fi
else
    # Set empty defaults to avoid docker-compose variable substitution errors
    export KEYCLOAK_DB_PASSWORD=""
    export KEYCLOAK_ADMIN_PASSWORD=""
fi

# Add ssl profile when SSL=true
[[ "$SSL" == "true" ]] && COMPOSE_PROFILES="$COMPOSE_PROFILES --profile ssl"

# Build compose file list: always base, plus http.yml overlay when SSL=false
COMPOSE_FILES="-f ${SCRIPT_DIR}/docker-compose.yml"
[[ "$SSL" == "false" ]] && COMPOSE_FILES="$COMPOSE_FILES -f ${SCRIPT_DIR}/docker-compose.http.yml"

# ---------------------------------------------------------------------------
# Start services
# ---------------------------------------------------------------------------
if [[ "$REBOOT" == true ]]; then
    echo "Stopping existing services..."
    $COMPOSE_CMD $COMPOSE_FILES $COMPOSE_PROFILES down
    echo
fi

echo "Starting services..."
# Remove any stopped containers before starting to avoid a docker-compose 1.29.2
# bug where it looks up 'ContainerConfig' from old container image metadata —
# a field dropped in newer Docker Engine versions.
$COMPOSE_CMD $COMPOSE_FILES $COMPOSE_PROFILES rm -sf 2>/dev/null || true
$COMPOSE_CMD $COMPOSE_FILES $COMPOSE_PROFILES up -d --build
echo "Done. Services are running."
