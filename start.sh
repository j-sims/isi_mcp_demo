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
# Ensure TLS certificates exist before starting nginx
# ---------------------------------------------------------------------------
CERT_SCRIPT="${SCRIPT_DIR}/nginx/generate-certs.sh"
CERT_DIR="${SCRIPT_DIR}/nginx/certs"
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
    docker-compose -f "$COMPOSE_FILE" run --rm --no-deps \
        -e VAULT_PASSWORD \
        isi_mcp python3 -c "
import os, yaml
from ansible.parsing.vault import VaultLib, VaultSecret
pwd = os.environ.get('VAULT_PASSWORD', '').encode()
vault = VaultLib([('default', VaultSecret(pwd))])
try:
    data = yaml.safe_load(vault.decrypt(open('/app/vault/vault.yml').read()))
    print(data.get('keycloak', {}).get('$key', ''), end='')
except Exception:
    pass
" 2>/dev/null
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

# ---------------------------------------------------------------------------
# Start services
# ---------------------------------------------------------------------------
if [[ "$REBOOT" == true ]]; then
    echo "Stopping existing services..."
    docker-compose -f "$COMPOSE_FILE" $COMPOSE_PROFILES down
    echo
fi

echo "Starting services..."
docker-compose -f "$COMPOSE_FILE" $COMPOSE_PROFILES up -d --build
echo "Done. Services are running."
