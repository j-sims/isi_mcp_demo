#!/bin/sh
set -e
# Fix ownership of bind-mounted directories so the mcp user can write to them.
# Runs as root before privilege drop; failures are non-fatal.
chown -R mcp:mcp /app/playbooks /app/vault 2>/dev/null || true
exec gosu mcp "$@"
