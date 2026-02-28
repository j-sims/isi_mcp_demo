#!/usr/bin/env bash
#
# Generate self-signed TLS certificates for the nginx reverse proxy.
# Certs are placed in nginx/certs/ (gitignored).
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="${SCRIPT_DIR}/certs"

if [ -f "${CERT_DIR}/server.crt" ] && [ -f "${CERT_DIR}/server.key" ]; then
    echo "Certificates already exist in ${CERT_DIR}. Skipping generation."
    echo "Delete them and re-run to regenerate."
    exit 0
fi

mkdir -p "${CERT_DIR}"

echo "Generating self-signed TLS certificate..."
openssl req -x509 -nodes \
    -days 365 \
    -newkey rsa:2048 \
    -keyout "${CERT_DIR}/server.key" \
    -out "${CERT_DIR}/server.crt" \
    -subj "/C=US/ST=Local/L=Local/O=PowerScale-MCP/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
    2>/dev/null

chmod 600 "${CERT_DIR}/server.key"
chmod 644 "${CERT_DIR}/server.crt"

echo "Certificates generated in ${CERT_DIR}/"
echo "  - server.crt (self-signed, valid 365 days)"
echo "  - server.key"
