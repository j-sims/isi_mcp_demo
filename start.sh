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
# Detect whether authentication is enabled in docker-compose.yml
# ---------------------------------------------------------------------------
COMPOSE_PROFILES=""
if grep -qE '^\s*-\s*AUTH_ENABLED=true' "$COMPOSE_FILE"; then
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
# Prompt for Keycloak passwords if authentication is enabled
# ---------------------------------------------------------------------------
if [[ "$AUTH_ENABLED" == true ]]; then
    export KEYCLOAK_DB_PASSWORD
    KEYCLOAK_DB_PASSWORD=$(read -rs -p 'Keycloak DB password: ' pwd && echo "$pwd")
    echo
    export KEYCLOAK_ADMIN_PASSWORD
    KEYCLOAK_ADMIN_PASSWORD=$(read -rs -p 'Keycloak admin password: ' pwd && echo "$pwd")
    echo
    COMPOSE_PROFILES="--profile auth"
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
docker-compose -f "$COMPOSE_FILE" $COMPOSE_PROFILES up -d
echo "Done. Services are running."
