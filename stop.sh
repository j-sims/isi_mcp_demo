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
# Detect whether the auth profile is active (so Keycloak services are stopped)
# ---------------------------------------------------------------------------
COMPOSE_PROFILES=""
if grep -qE '^\s*-\s*AUTH_ENABLED=true' "$COMPOSE_FILE"; then
    COMPOSE_PROFILES="--profile auth"
fi

# ---------------------------------------------------------------------------
# Stop services
# ---------------------------------------------------------------------------
if [[ "$CLEAN" == true ]]; then
    echo "Stopping services, removing volumes and the vault..."
    docker-compose -f "$COMPOSE_FILE" $COMPOSE_PROFILES down -v && \
    rm vault/vault.yml && \
    echo done
else
    echo "Stopping services..."
    docker-compose -f "$COMPOSE_FILE" $COMPOSE_PROFILES down
fi

echo "Done."
