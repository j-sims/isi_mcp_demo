#!/usr/bin/env bash
#
# start.sh — Start the PowerScale MCP Demo services
#
# Usage:
#   ./start.sh            — Start services (prompt for vault password)
#   ./start.sh --reboot   — Tear down existing services first, then start fresh
#

set -euo pipefail

REBOOT=false

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --reboot)
            REBOOT=true
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--reboot]"
            exit 1
            ;;
    esac
done

# Tear down existing services if --reboot was specified
if [ "$REBOOT" = true ]; then
    echo "Stopping and removing existing services..."
    docker-compose down -v
    echo "Services stopped."
    echo
fi

# Prompt for vault password (input is hidden)
export VAULT_PASSWORD
VAULT_PASSWORD=$(read -rs -p 'Enter vault password: ' pwd && echo "$pwd")
echo  # newline after silent input

echo "Starting services..."
docker-compose up -d

echo "Done. Services are running."
