#!/usr/bin/env bash
#
# stop.sh — Stop the PowerScale MCP Server
#
# Usage:
#   ./stop.sh          — Stop services (containers removed, volumes persist)
#   ./stop.sh --clean  — Stop services and remove volumes (destructive)
#   ./stop.sh -h       — Show this help
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
CLEAN=false

# Detect docker compose command (v2 plugin preferred over standalone v1)
if docker compose version &>/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "ERROR: docker-compose is not available."
    echo "Install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
for arg in "$@"; do
    case "$arg" in
        --clean) CLEAN=true ;;
        -h|--help)
            sed -n '2,7p' "$0" | sed 's/^# *//'
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--clean]"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Detect active profiles (auth and/or ssl) from config
# ---------------------------------------------------------------------------
APP_CONFIG="${SCRIPT_DIR}/config/isi_mcp.env"
COMPOSE_PROFILES=""
if grep -qE '^AUTH_ENABLED=true' "$APP_CONFIG" 2>/dev/null; then
    COMPOSE_PROFILES="--profile auth"
fi
SSL=$(grep '^SSL=' "$APP_CONFIG" 2>/dev/null | cut -d= -f2- | tr -d ' ')
if [[ "${SSL:-false}" == "true" ]]; then
    COMPOSE_PROFILES="$COMPOSE_PROFILES --profile ssl"
fi

# Build compose file list (http overlay when SSL=false, as in start.sh)
COMPOSE_FILES="-f ${COMPOSE_FILE}"
if [[ "${SSL:-false}" == "false" ]]; then
    COMPOSE_FILES="$COMPOSE_FILES -f ${SCRIPT_DIR}/docker-compose.http.yml"
fi

# ---------------------------------------------------------------------------
# Stop services
# ---------------------------------------------------------------------------
if [[ "$CLEAN" == true ]]; then
    echo "Stopping services, removing volumes, certs, and vault..."
    $COMPOSE_CMD $COMPOSE_FILES $COMPOSE_PROFILES down -v && \
    rm -rf "${SCRIPT_DIR}/vault" && \
    rm -rf "${SCRIPT_DIR}/nginx/certs" && \
    rm -f "${SCRIPT_DIR}/playbooks"/*.yml 2>/dev/null || true && \
    echo done
else
    echo "Stopping services..."
    $COMPOSE_CMD $COMPOSE_FILES $COMPOSE_PROFILES down
fi

echo "Done."
