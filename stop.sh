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
