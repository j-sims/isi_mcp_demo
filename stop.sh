#!/usr/bin/env bash
#
# stop.sh — Stop the PowerScale MCP Demo services
#
# Usage:
#   ./stop.sh          — Stop services (containers remain, volumes persist)
#   ./stop.sh --clean  — Stop services and remove volumes
#

set -euo pipefail

CLEAN=false

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --clean)
            CLEAN=true
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--clean]"
            exit 1
            ;;
    esac
done

# Stop services
if [ "$CLEAN" = true ]; then
    echo "Stopping services and removing volumes..."
    docker-compose down -v
else
    echo "Stopping services..."
    docker-compose down
fi

echo "Done."
