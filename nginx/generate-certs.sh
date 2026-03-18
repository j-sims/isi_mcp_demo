#!/usr/bin/env bash
#
# Generate TLS certificates for the nginx reverse proxy.
# Creates a local CA and a server cert signed by it, so that
# NODE_EXTRA_CA_CERTS can trust the CA and Node.js will accept the server cert.
#
# The server cert SAN includes all local IPs and hostnames detected at
# generation time, so it works from any interface (localhost, LAN, etc).
#
# Certs are placed in nginx/certs/ (gitignored).
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="${SCRIPT_DIR}/certs"
FORCE=false

for arg in "$@"; do
    case "$arg" in
        --force) FORCE=true ;;
        -h|--help)
            echo "Usage: $0 [--force]"
            echo "  --force   Overwrite existing certificates (default: skip if present)"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--force]"
            exit 1
            ;;
    esac
done

if [[ "$FORCE" == false ]] && [ -f "${CERT_DIR}/server.crt" ] && [ -f "${CERT_DIR}/server.key" ]; then
    echo "Certificates already exist in ${CERT_DIR}. Skipping generation."
    echo "Use --force to overwrite existing certificates."
    exit 0
fi

mkdir -p "${CERT_DIR}"

# Build SAN list from all local IPs and hostnames
HOSTNAME="$(hostname -f 2>/dev/null || hostname)"
SHORT_HOSTNAME="$(hostname -s 2>/dev/null || hostname)"

SAN="DNS:localhost,DNS:${HOSTNAME}"
[ "${SHORT_HOSTNAME}" != "${HOSTNAME}" ] && SAN="${SAN},DNS:${SHORT_HOSTNAME}"

# Add all non-loopback IPv4 addresses
while IFS= read -r ip; do
    SAN="${SAN},IP:${ip}"
done < <(hostname -I 2>/dev/null | tr ' ' '\n' | grep -v '^$' | grep -v ':')

# Add all non-loopback IPv6 addresses
while IFS= read -r ip; do
    SAN="${SAN},IP:${ip}"
done < <(hostname -I 2>/dev/null | tr ' ' '\n' | grep ':' | grep -v '^$')

# Always include loopback
SAN="${SAN},IP:127.0.0.1,IP:::1"

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
    -subj "/C=US/ST=Local/L=Local/O=PowerScale-MCP/CN=${HOSTNAME}" \
    2>/dev/null

echo "Signing server cert with local CA..."
openssl x509 -req \
    -days 365 \
    -in "${CERT_DIR}/server.csr" \
    -CA "${CERT_DIR}/ca.crt" \
    -CAkey "${CERT_DIR}/ca.key" \
    -CAcreateserial \
    -out "${CERT_DIR}/server.crt" \
    -extfile <(printf "subjectAltName=${SAN}\nbasicConstraints=CA:FALSE") \
    2>/dev/null

rm -f "${CERT_DIR}/server.csr" "${CERT_DIR}/ca.srl"

chmod 600 "${CERT_DIR}/server.key" "${CERT_DIR}/ca.key"
chmod 644 "${CERT_DIR}/server.crt" "${CERT_DIR}/ca.crt"

echo "Certificates generated in ${CERT_DIR}/"
echo "  - ca.crt      (local CA — add to NODE_EXTRA_CA_CERTS and system trust store)"
echo "  - server.crt  (server cert signed by local CA)"
echo "  - server.key  (server private key)"
echo ""
echo "SANs included in server cert:"
echo "  ${SAN}" | tr ',' '\n' | sed 's/^/    /'
echo ""
echo "To trust the CA system-wide:"
echo "  sudo cp ${CERT_DIR}/ca.crt /usr/local/share/ca-certificates/powerscale-mcp-ca.crt"
echo "  sudo update-ca-certificates"
echo ""
echo "To trust in Node.js (Claude Code / VSCode):"
echo "  export NODE_EXTRA_CA_CERTS=${CERT_DIR}/ca.crt"
