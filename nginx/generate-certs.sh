#!/usr/bin/env bash
#
# Generate TLS certificates for the nginx reverse proxy.
# Creates a local CA and a server cert signed by it, so that
# NODE_EXTRA_CA_CERTS can trust the CA and Node.js will accept the server cert.
#
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

echo "Generating local CA key and certificate..."
openssl req -x509 -nodes \
    -days 3650 \
    -newkey rsa:2048 \
    -keyout "${CERT_DIR}/ca.key" \
    -out "${CERT_DIR}/ca.crt" \
    -subj "/C=US/ST=Local/L=Local/O=PowerScale-MCP-CA/CN=PowerScale-MCP Local CA" \
    2>/dev/null

echo "Generating server key and CSR..."
openssl req -nodes \
    -newkey rsa:2048 \
    -keyout "${CERT_DIR}/server.key" \
    -out "${CERT_DIR}/server.csr" \
    -subj "/C=US/ST=Local/L=Local/O=PowerScale-MCP/CN=localhost" \
    2>/dev/null

echo "Signing server cert with local CA..."
openssl x509 -req \
    -days 365 \
    -in "${CERT_DIR}/server.csr" \
    -CA "${CERT_DIR}/ca.crt" \
    -CAkey "${CERT_DIR}/ca.key" \
    -CAcreateserial \
    -out "${CERT_DIR}/server.crt" \
    -extfile <(printf "subjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=CA:FALSE") \
    2>/dev/null

rm -f "${CERT_DIR}/server.csr" "${CERT_DIR}/ca.srl"

chmod 600 "${CERT_DIR}/server.key" "${CERT_DIR}/ca.key"
chmod 644 "${CERT_DIR}/server.crt" "${CERT_DIR}/ca.crt"

echo "Certificates generated in ${CERT_DIR}/"
echo "  - ca.crt      (local CA — add to NODE_EXTRA_CA_CERTS and system trust store)"
echo "  - server.crt  (server cert signed by local CA)"
echo "  - server.key  (server private key)"
echo ""
echo "To trust the CA system-wide:"
echo "  sudo cp ${CERT_DIR}/ca.crt /usr/local/share/ca-certificates/powerscale-mcp-ca.crt"
echo "  sudo update-ca-certificates"
echo ""
echo "To trust in Node.js (Claude Code / VSCode):"
echo "  export NODE_EXTRA_CA_CERTS=${CERT_DIR}/ca.crt"
