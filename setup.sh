#!/usr/bin/env bash
#
# setup.sh — First-time setup and cluster management for the PowerScale MCP Server.
#
# Creates cluster credentials, encrypts them, builds the Docker image,
# and starts the MCP server. Requires only Docker — no Ansible needed on the host.
#
# Usage:
#   ./setup.sh                                         # interactive first-time setup
#   ./setup.sh --host 172.16.10.10 --pass secret       # non-interactive setup
#   ./setup.sh list-clusters                           # list all clusters in vault
#   ./setup.sh add-cluster --name lab --host 10.0.0.1  # add/update a cluster
#   ./setup.sh remove-cluster --name lab               # remove a cluster
#   ./setup.sh modify-cluster --name lab --host ...    # modify cluster fields
#   ./setup.sh -h

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }

# ---------------------------------------------------------------------------
# Global paths (derived from SCRIPT_DIR, used by all subcommands)
# ---------------------------------------------------------------------------
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
VAULT_DIR="${SCRIPT_DIR}/vault"
VAULT_FILE="${VAULT_DIR}/vault.yml"

# ---------------------------------------------------------------------------
# Show help
# ---------------------------------------------------------------------------
show_help() {
    cat << 'HELP'
Usage: ./setup.sh [SUBCOMMAND] [OPTIONS]

First-time setup and cluster management for the PowerScale MCP Server.

Subcommands (cluster management — require an existing setup):
  list-clusters                   List all clusters in the vault
  add-cluster   --name --host     Add or update a cluster
  remove-cluster --name           Remove a cluster
  modify-cluster --name           Modify specific fields of a cluster
  Run ./setup.sh <subcommand> --help for subcommand-specific usage.

Setup (no subcommand — first-time initialization):
  Creates encrypted cluster credentials, builds the Docker image, and starts the server.

Required for setup (prompted interactively if not provided):
  --host HOST         Cluster hostname or IP (e.g. 172.16.10.10 or https://172.16.10.10)
  --pass PASS         Cluster admin password

Optional for setup:
  --port PORT         API port (default: 8080)
  --user USER         Cluster username (prompted with 'root' as default)
  --name NAME         Cluster label in vault.yml (default: powerscale)
  --auth true|false   Enable OAuth authentication via Keycloak (default: false)
  --ssl true|false    Enable HTTPS via nginx with TLS (default: false; auto-enabled when --auth true)
  --listen-port PORT  Server listen port (default: 80 for HTTP, 443 for HTTPS)
  --no-cache          Force rebuild Docker image without using cached layers
  -h, --help          Show this help message

Environment Variables (for non-interactive use — avoid shell history):
  VAULT_PASSWORD              Vault encryption password (prompted if not set)
  KEYCLOAK_DB_PASSWORD        Keycloak database password when --auth true (prompted if not set)
  KEYCLOAK_ADMIN_PASSWORD     Keycloak admin password when --auth true (prompted if not set)

Examples:
  # Interactive setup (prompts for all required values)
  ./setup.sh

  # Non-interactive setup using read to avoid shell history
  read -s -p 'Vault password: ' VAULT_PASSWORD && export VAULT_PASSWORD
  read -s -p 'Cluster password: ' CLUSTER_PASS
  ./setup.sh --host 172.16.10.10 --user root --pass "$CLUSTER_PASS"

  # Setup with auth enabled
  read -s -p 'Vault password: ' VAULT_PASSWORD && export VAULT_PASSWORD
  read -s -p 'Keycloak DB password: ' KEYCLOAK_DB_PASSWORD && export KEYCLOAK_DB_PASSWORD
  read -s -p 'Keycloak admin password: ' KEYCLOAK_ADMIN_PASSWORD && export KEYCLOAK_ADMIN_PASSWORD
  ./setup.sh --host 172.16.10.10 --auth true

  # Add a second cluster after initial setup
  ./setup.sh add-cluster --name prod --host 10.0.0.1 --user root

  # List all configured clusters
  ./setup.sh list-clusters

After setup, restart the server:
  ./start.sh

To add or edit clusters later:
  ./setup.sh add-cluster --name <name> --host <host>
  ./setup.sh modify-cluster --name <name> --host <new-host>
  ./setup.sh list-clusters
HELP
}

# ---------------------------------------------------------------------------
# Cluster management subcommand help
# ---------------------------------------------------------------------------
show_cluster_mgmt_help() {
    cat << 'HELP'
Usage: ./setup.sh <subcommand> [OPTIONS]

Cluster Management Subcommands
================================
All subcommands require the vault password (use VAULT_PASSWORD env var or
it will be prompted securely). Passwords are never passed as command-line
arguments — they are always prompted or provided via environment variables.

list-clusters
  List all clusters in the vault with connection details (no passwords shown).
  Usage: ./setup.sh list-clusters

add-cluster
  Add a new cluster to the vault, or update an existing cluster with the same name.
  TLS certificate extraction is attempted automatically.
  Options:
    --name NAME         Cluster label (required)
    --host HOST         Hostname or IP (required; https:// added automatically)
    --port PORT         API port (default: 8080)
    --user USER         Admin username (default: root)
    --pass              Admin password (flag — always prompted securely; never accepted as a CLI value)

remove-cluster
  Remove a cluster from the vault. Cannot remove the currently selected cluster
  unless it is the only one.
  Options:
    --name NAME         Cluster label to remove (required)

modify-cluster
  Update one or more fields of an existing cluster. Only supply the fields
  you want to change — all others are left as-is.
  Options:
    --name NAME             Current cluster label (required)
    --new-name NAME         Rename the cluster
    --host HOST             New hostname or IP
    --port PORT             New API port
    --user USER             New admin username
    --pass                  Update the password (prompted securely; flag, no value)
    --verify-ssl true|false Override SSL verification setting

Environment Variables:
  VAULT_PASSWORD      Vault encryption password (prompted if not set)

Examples:
  # List all clusters
  ./setup.sh list-clusters

  # Add a cluster (password prompted securely)
  ./setup.sh add-cluster --name lab --host 172.16.10.10 --user root

  # Non-interactive add (avoid shell history for passwords)
  read -s -p 'Vault password: ' VAULT_PASSWORD && export VAULT_PASSWORD
  ./setup.sh add-cluster --name lab --host 172.16.10.10 --user root --pass
  # (cluster password is always prompted securely when --pass flag is given)

  # Remove a cluster
  ./setup.sh remove-cluster --name lab

  # Rename a cluster
  ./setup.sh modify-cluster --name lab --new-name lab2

  # Update only the host
  ./setup.sh modify-cluster --name lab --host 172.16.10.20

  # Update only the password (prompted securely)
  ./setup.sh modify-cluster --name lab --pass

Note: Changes to the vault are picked up by the running MCP server within 5 seconds
via its TTL-based cache. To force an immediate reload from an MCP client, use:
  powerscale_cluster_select(cluster_name, reload_vault=True)
HELP
}

# ---------------------------------------------------------------------------
# Shared helpers used by subcommands
# ---------------------------------------------------------------------------

_check_docker_prereqs() {
    if ! command -v docker &>/dev/null; then
        fail "Docker is not installed."
        fail "Install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    if docker compose version &>/dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        fail "docker-compose is not available."
        fail "Install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

_get_vault_pass_for_ops() {
    VAULT_PASS="${VAULT_PASSWORD:-}"
    if [[ -z "$VAULT_PASS" ]]; then
        read -rsp "Vault encryption password: " VAULT_PASS
        echo
    fi
    if [[ -z "$VAULT_PASS" ]]; then
        fail "Vault password is required."
        exit 1
    fi
}

_ensure_vault_exists() {
    if [[ ! -f "$VAULT_FILE" ]]; then
        fail "Vault file not found: $VAULT_FILE"
        fail "Run './setup.sh' first to perform initial setup."
        exit 1
    fi
}

_ensure_image_exists() {
    if ! $COMPOSE_CMD -f "$COMPOSE_FILE" images isi_mcp 2>/dev/null | grep -q isi_mcp; then
        warn "Docker image not found — building now (required for vault operations)..."
        $COMPOSE_CMD -f "$COMPOSE_FILE" build isi_mcp
    fi
}

# ---------------------------------------------------------------------------
# Shared TLS certificate extraction and inspection
#
# Args: <host_bare> <port> <cluster_name>
# Sets globals: CERT_EXTRACTED, IS_SELF_SIGNED, CERT_IS_CA, CLUSTER_CA_BUNDLE
# ---------------------------------------------------------------------------
_extract_and_inspect_cert() {
    local host_bare="$1"
    local port="$2"
    local cluster_name="$3"
    local cert_path="${VAULT_DIR}/${cluster_name}_cert.pem"

    CERT_EXTRACTED=false
    IS_SELF_SIGNED=false
    CERT_IS_CA=false
    CLUSTER_CA_BUNDLE=""

    info "Extracting cluster TLS certificate for SSL verification..."
    if VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "$COMPOSE_FILE" run --rm isi_mcp \
        sh -c "openssl s_client -connect ${host_bare}:${port} \
               -connect_timeout 10 \
               -showcerts </dev/null 2>/dev/null \
               | openssl x509 -outform PEM \
               > /app/vault/${cluster_name}_cert.pem" 2>/dev/null \
        && [[ -s "$cert_path" ]]; then
        CERT_EXTRACTED=true
    fi

    if [[ "$CERT_EXTRACTED" == true ]]; then
        if openssl x509 -in "$cert_path" -text -noout 2>/dev/null \
            | grep -q "CA:TRUE"; then
            CERT_IS_CA=true
        fi
        local subject issuer
        subject=$(openssl x509 -in "$cert_path" -noout -subject 2>/dev/null | sed 's/subject=//')
        issuer=$(openssl x509  -in "$cert_path" -noout -issuer  2>/dev/null | sed 's/issuer=//')
        if [[ "$subject" == "$issuer" ]]; then
            IS_SELF_SIGNED=true
        fi
    fi

    if [[ "$IS_SELF_SIGNED" == true && "$CERT_IS_CA" == true ]]; then
        ok "Cluster cert is a self-signed CA (CA:TRUE) — cert pinning enabled."
        CLUSTER_CA_BUNDLE="/app/vault/${cluster_name}_cert.pem"
    elif [[ "$IS_SELF_SIGNED" == false && "$CERT_EXTRACTED" == true ]]; then
        rm -f "$cert_path" 2>/dev/null || true
        ok "Cluster has a CA-signed certificate — using system CA store."
    else
        rm -f "$cert_path" 2>/dev/null || true
        if [[ "$CERT_EXTRACTED" == true ]]; then
            warn "Cluster cert is X.509 v1 self-signed (no CA:TRUE) — SSL verification will be disabled."
        else
            warn "Could not extract cluster certificate — SSL verification will be disabled."
        fi
    fi
}

# ---------------------------------------------------------------------------
# Subcommand: list-clusters
# ---------------------------------------------------------------------------
do_list_clusters() {
    local args=("$@")
    local i=0
    while [[ $i -lt ${#args[@]} ]]; do
        case "${args[$i]}" in
            -h|--help) show_cluster_mgmt_help; exit 0 ;;
            *) fail "Unknown argument: ${args[$i]}"; echo "Run ./setup.sh list-clusters --help for usage."; exit 1 ;;
        esac
        i=$((i+1))
    done

    _check_docker_prereqs
    _get_vault_pass_for_ops
    _ensure_vault_exists
    _ensure_image_exists

    info "Clusters in vault:"
    echo ""
    VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "$COMPOSE_FILE" run --rm --no-deps isi_mcp \
        python3 -c "
import os, sys
sys.path.insert(0, '/app/isi_mcp')
from modules.ansible.vault_manager import VaultManager
vm = VaultManager()
clusters = vm.list_clusters()
if not clusters:
    print('  (no clusters configured)')
else:
    for c in clusters:
        selected = ' <-- selected' if c.get('selected') else ''
        ssl = 'verify_ssl=true' if c.get('verify_ssl') else 'verify_ssl=false'
        ca  = f\", ca_bundle={c.get('ca_bundle', '')}\" if c.get('ca_bundle') else ''
        print(f\"  {c['name']}: {c['host']}:{c['port']}  [{ssl}{ca}]{selected}\")
print()
print(f'Total: {len(clusters)} cluster(s)')
"
    echo ""
}

# ---------------------------------------------------------------------------
# Subcommand: add-cluster
# ---------------------------------------------------------------------------
do_add_cluster() {
    local CLUSTER_NAME="" CLUSTER_HOST="" CLUSTER_PORT=8080 CLUSTER_USER="" CLUSTER_PASS=""
    local args=("$@")
    local i=0
    while [[ $i -lt ${#args[@]} ]]; do
        case "${args[$i]}" in
            --name)    CLUSTER_NAME="${args[$((i+1))]}";  i=$((i+2)) ;;
            --host)    CLUSTER_HOST="${args[$((i+1))]}";  i=$((i+2)) ;;
            --port)    CLUSTER_PORT="${args[$((i+1))]}";  i=$((i+2)) ;;
            --user)    CLUSTER_USER="${args[$((i+1))]}";  i=$((i+2)) ;;
            --pass)    i=$((i+1)) ;;
            -h|--help) show_cluster_mgmt_help; exit 0 ;;
            *) fail "Unknown argument: ${args[$i]}"; echo "Run ./setup.sh add-cluster --help for usage."; exit 1 ;;
        esac
    done

    # Prompt for required fields
    while [[ -z "$CLUSTER_NAME" ]]; do
        read -rp "Cluster name/label: " CLUSTER_NAME
        [[ -z "$CLUSTER_NAME" ]] && warn "Cluster name is required."
    done
    while [[ -z "$CLUSTER_HOST" ]]; do
        read -rp "Cluster host: " CLUSTER_HOST
        [[ -z "$CLUSTER_HOST" ]] && warn "Cluster host is required."
    done
    if [[ -z "$CLUSTER_USER" ]]; then
        read -rp "Cluster username [root]: " CLUSTER_USER
        CLUSTER_USER="${CLUSTER_USER:-root}"
    fi
    read -rsp "Cluster password for ${CLUSTER_USER}@${CLUSTER_HOST}: " CLUSTER_PASS
    echo
    [[ -z "$CLUSTER_PASS" ]] && { fail "Cluster password is required."; exit 1; }

    _check_docker_prereqs
    _get_vault_pass_for_ops
    _ensure_vault_exists
    _ensure_image_exists

    mkdir -p "$VAULT_DIR"

    # Normalize host — ensure https:// prefix
    local VAULT_HOST
    if [[ "$CLUSTER_HOST" =~ ^https?:// ]]; then
        VAULT_HOST="$CLUSTER_HOST"
    else
        VAULT_HOST="https://${CLUSTER_HOST}"
    fi
    local HOST_BARE="${VAULT_HOST#https://}"
    HOST_BARE="${HOST_BARE#http://}"

    # Extract and inspect TLS cert
    _extract_and_inspect_cert "$HOST_BARE" "$CLUSTER_PORT" "$CLUSTER_NAME"

    # Determine verify_ssl based on cert inspection
    local VERIFY_SSL="true"
    if [[ "$IS_SELF_SIGNED" == true && "$CERT_IS_CA" == false ]]; then
        VERIFY_SSL="false"   # X.509 v1 self-signed — cannot verify
    elif [[ "$CERT_EXTRACTED" == false ]]; then
        VERIFY_SSL="false"   # could not extract — disable to avoid errors
    fi

    # Pass all values securely via environment variables — never as CLI args
    local CA_BUNDLE_VAL="${CLUSTER_CA_BUNDLE:-}"
    export _ISI_NAME="$CLUSTER_NAME"
    export _ISI_HOST="$VAULT_HOST"
    export _ISI_PORT="$CLUSTER_PORT"
    export _ISI_USER="$CLUSTER_USER"
    export _ISI_PASS="$CLUSTER_PASS"
    export _ISI_SSL="$VERIFY_SSL"
    export _ISI_CA="${CA_BUNDLE_VAL}"

    info "Adding cluster '${CLUSTER_NAME}' to vault..."
    VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "$COMPOSE_FILE" run --rm --no-deps \
        -e _ISI_NAME -e _ISI_HOST -e _ISI_PORT \
        -e _ISI_USER -e _ISI_PASS -e _ISI_SSL -e _ISI_CA \
        isi_mcp python3 -c "
import os, sys
sys.path.insert(0, '/app/isi_mcp')
from modules.ansible.vault_manager import VaultManager
vm = VaultManager()
name      = os.environ['_ISI_NAME']
host      = os.environ['_ISI_HOST']
port      = int(os.environ['_ISI_PORT'])
username  = os.environ['_ISI_USER']
password  = os.environ['_ISI_PASS']
verify_ssl = os.environ['_ISI_SSL'].lower() == 'true'
ca_bundle  = os.environ.get('_ISI_CA') or None
vm.add_cluster(name, host, port, username, password, verify_ssl, ca_bundle=ca_bundle)
print(f'Cluster \"{name}\" added/updated in vault.')
print(f'  Host: {host}:{port}  user: {username}  verify_ssl: {verify_ssl}' + (f'  ca_bundle: {ca_bundle}' if ca_bundle else ''))
"

    unset _ISI_NAME _ISI_HOST _ISI_PORT _ISI_USER _ISI_PASS _ISI_SSL _ISI_CA
    ok "Done. The running MCP server reloads the vault within 5 seconds."
}

# ---------------------------------------------------------------------------
# Subcommand: remove-cluster
# ---------------------------------------------------------------------------
do_remove_cluster() {
    local CLUSTER_NAME=""
    local args=("$@")
    local i=0
    while [[ $i -lt ${#args[@]} ]]; do
        case "${args[$i]}" in
            --name)    CLUSTER_NAME="${args[$((i+1))]}";  i=$((i+2)) ;;
            -h|--help) show_cluster_mgmt_help; exit 0 ;;
            *) fail "Unknown argument: ${args[$i]}"; echo "Run ./setup.sh remove-cluster --help for usage."; exit 1 ;;
        esac
    done

    while [[ -z "$CLUSTER_NAME" ]]; do
        read -rp "Cluster name to remove: " CLUSTER_NAME
        [[ -z "$CLUSTER_NAME" ]] && warn "Cluster name is required."
    done

    _check_docker_prereqs
    _get_vault_pass_for_ops
    _ensure_vault_exists
    _ensure_image_exists

    echo ""
    warn "This will permanently remove cluster '${CLUSTER_NAME}' from the vault."
    read -rp "Are you sure? [y/N]: " CONFIRM
    if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
        info "Aborted — no changes made."
        exit 0
    fi

    export _ISI_NAME="$CLUSTER_NAME"
    info "Removing cluster '${CLUSTER_NAME}' from vault..."
    VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "$COMPOSE_FILE" run --rm --no-deps \
        -e _ISI_NAME \
        isi_mcp python3 -c "
import os, sys
sys.path.insert(0, '/app/isi_mcp')
from modules.ansible.vault_manager import VaultManager
vm = VaultManager()
name = os.environ['_ISI_NAME']
clusters = vm.list_clusters()
names = [c['name'] for c in clusters]
if name not in names:
    print(f'ERROR: Cluster \"{name}\" not found. Available: {names}', file=sys.stderr)
    sys.exit(1)
removed = vm.remove_cluster(name)
remaining = [c['name'] for c in vm.list_clusters()]
print(f'Cluster \"{name}\" removed from vault.')
if remaining:
    print(f'Remaining clusters: {remaining}')
else:
    print('No clusters remain in vault.')
"

    # Also remove any associated cert file
    rm -f "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" 2>/dev/null || true
    unset _ISI_NAME
    ok "Done. The running MCP server reloads the vault within 5 seconds."
}

# ---------------------------------------------------------------------------
# Subcommand: modify-cluster
# ---------------------------------------------------------------------------
do_modify_cluster() {
    local CLUSTER_NAME="" NEW_NAME="" NEW_HOST="" NEW_PORT="" NEW_USER=""
    local UPDATE_PASS=false NEW_PASS="" NEW_VERIFY_SSL=""
    local args=("$@")
    local i=0
    while [[ $i -lt ${#args[@]} ]]; do
        case "${args[$i]}" in
            --name)        CLUSTER_NAME="${args[$((i+1))]}";    i=$((i+2)) ;;
            --new-name)    NEW_NAME="${args[$((i+1))]}";        i=$((i+2)) ;;
            --host)        NEW_HOST="${args[$((i+1))]}";        i=$((i+2)) ;;
            --port)        NEW_PORT="${args[$((i+1))]}";        i=$((i+2)) ;;
            --user)        NEW_USER="${args[$((i+1))]}";        i=$((i+2)) ;;
            --pass)        UPDATE_PASS=true;                    i=$((i+1)) ;;
            --verify-ssl)  NEW_VERIFY_SSL="${args[$((i+1))]}";  i=$((i+2)) ;;
            -h|--help) show_cluster_mgmt_help; exit 0 ;;
            *) fail "Unknown argument: ${args[$i]}"; echo "Run ./setup.sh modify-cluster --help for usage."; exit 1 ;;
        esac
    done

    while [[ -z "$CLUSTER_NAME" ]]; do
        read -rp "Cluster name to modify: " CLUSTER_NAME
        [[ -z "$CLUSTER_NAME" ]] && warn "Cluster name is required."
    done

    if [[ "$UPDATE_PASS" == true ]]; then
        read -rsp "New cluster password for '${CLUSTER_NAME}': " NEW_PASS
        echo
        [[ -z "$NEW_PASS" ]] && { fail "Password cannot be empty."; exit 1; }
    fi

    if [[ -n "$NEW_VERIFY_SSL" && "$NEW_VERIFY_SSL" != "true" && "$NEW_VERIFY_SSL" != "false" ]]; then
        fail "--verify-ssl must be 'true' or 'false' (got: ${NEW_VERIFY_SSL})"
        exit 1
    fi

    # Validate that at least one field is being changed
    if [[ -z "$NEW_NAME" && -z "$NEW_HOST" && -z "$NEW_PORT" && -z "$NEW_USER" \
          && "$UPDATE_PASS" == false && -z "$NEW_VERIFY_SSL" ]]; then
        fail "No fields specified to update."
        echo "Specify at least one of: --new-name --host --port --user --pass --verify-ssl"
        echo "Run ./setup.sh modify-cluster --help for usage."
        exit 1
    fi

    _check_docker_prereqs
    _get_vault_pass_for_ops
    _ensure_vault_exists
    _ensure_image_exists

    # Normalize host if provided
    if [[ -n "$NEW_HOST" && ! "$NEW_HOST" =~ ^https?:// ]]; then
        NEW_HOST="https://${NEW_HOST}"
    fi

    # Pass all values securely via environment variables
    export _ISI_NAME="$CLUSTER_NAME"
    export _ISI_NEW_NAME="$NEW_NAME"
    export _ISI_NEW_HOST="$NEW_HOST"
    export _ISI_NEW_PORT="$NEW_PORT"
    export _ISI_NEW_USER="$NEW_USER"
    export _ISI_NEW_PASS="$NEW_PASS"
    export _ISI_NEW_SSL="$NEW_VERIFY_SSL"

    info "Modifying cluster '${CLUSTER_NAME}'..."
    VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "$COMPOSE_FILE" run --rm --no-deps \
        -e _ISI_NAME -e _ISI_NEW_NAME -e _ISI_NEW_HOST -e _ISI_NEW_PORT \
        -e _ISI_NEW_USER -e _ISI_NEW_PASS -e _ISI_NEW_SSL \
        isi_mcp python3 -c "
import os, sys
sys.path.insert(0, '/app/isi_mcp')
from modules.ansible.vault_manager import VaultManager
vm = VaultManager()
name = os.environ['_ISI_NAME']
clusters = vm.list_clusters()
names = [c['name'] for c in clusters]
if name not in names:
    print(f'ERROR: Cluster \"{name}\" not found. Available: {names}', file=sys.stderr)
    sys.exit(1)
kwargs = {}
if os.environ.get('_ISI_NEW_NAME'):  kwargs['new_name']   = os.environ['_ISI_NEW_NAME']
if os.environ.get('_ISI_NEW_HOST'):  kwargs['host']       = os.environ['_ISI_NEW_HOST']
if os.environ.get('_ISI_NEW_PORT'):  kwargs['port']       = int(os.environ['_ISI_NEW_PORT'])
if os.environ.get('_ISI_NEW_USER'):  kwargs['username']   = os.environ['_ISI_NEW_USER']
if os.environ.get('_ISI_NEW_PASS'):  kwargs['password']   = os.environ['_ISI_NEW_PASS']
if os.environ.get('_ISI_NEW_SSL'):   kwargs['verify_ssl'] = os.environ['_ISI_NEW_SSL'].lower() == 'true'
vm.modify_cluster(name, **kwargs)
effective = kwargs.get('new_name', name)
changed = [f'{k}={v}' for k, v in kwargs.items() if k not in ('password', 'new_name')]
if 'new_name'  in kwargs: changed.insert(0, f'renamed to {kwargs[\"new_name\"]}')
if 'password'  in kwargs: changed.append('password=<updated>')
print(f'Cluster \"{name}\" updated: {chr(44).join(changed)}')
print('Current clusters:')
for c in vm.list_clusters():
    sel = ' <-- selected' if c.get('selected') else ''
    print(f\"  {c['name']}: {c['host']}:{c['port']}{sel}\")
"

    unset _ISI_NAME _ISI_NEW_NAME _ISI_NEW_HOST _ISI_NEW_PORT _ISI_NEW_USER _ISI_NEW_PASS _ISI_NEW_SSL
    ok "Done. The running MCP server reloads the vault within 5 seconds."
}

# ---------------------------------------------------------------------------
# Subcommand dispatch — must appear before main setup argument parsing
# ---------------------------------------------------------------------------
if [[ $# -gt 0 ]]; then
    case "$1" in
        list-clusters)
            shift; do_list_clusters "$@"; exit 0 ;;
        add-cluster)
            shift; do_add_cluster "$@"; exit 0 ;;
        remove-cluster)
            shift; do_remove_cluster "$@"; exit 0 ;;
        modify-cluster)
            shift; do_modify_cluster "$@"; exit 0 ;;
    esac
fi

# ---------------------------------------------------------------------------
# Initialize config env files from .env.sample if they don't exist yet
# (first-time setup, or after a git pull that added new .env.sample files)
# ---------------------------------------------------------------------------
for _sample in "${SCRIPT_DIR}/config/"*.env.sample; do
    _env="${_sample%.sample}"
    if [[ ! -f "$_env" ]]; then
        cp "$_sample" "$_env"
        ok "Created $(basename "$_env") from $(basename "$_sample")"
    fi
done
unset _sample _env

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
CLUSTER_HOST=""
CLUSTER_PORT=8080
CLUSTER_USER=""
CLUSTER_PASS=""
CLUSTER_NAME="powerscale"
VAULT_PASS="${VAULT_PASSWORD:-}"
AUTH_ARG="false"
SSL_ARG="false"
SSL_ARG_EXPLICIT=false
LISTEN_PORT_ARG=""
NO_CACHE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)         CLUSTER_HOST="$2"; shift 2 ;;
        --port)         CLUSTER_PORT="$2"; shift 2 ;;
        --user)         CLUSTER_USER="$2"; shift 2 ;;
        --pass)         CLUSTER_PASS="$2"; shift 2 ;;
        --name)         CLUSTER_NAME="$2"; shift 2 ;;
        --auth)         AUTH_ARG="$2"; shift 2 ;;
        --ssl)          SSL_ARG="$2"; SSL_ARG_EXPLICIT=true; shift 2 ;;
        --listen-port)  LISTEN_PORT_ARG="$2"; shift 2 ;;
        --no-cache)     NO_CACHE=true; shift ;;
        -h|--help)      show_help; exit 0 ;;
        *)              fail "Unknown argument: $1"; echo "Run ./setup.sh --help for usage."; exit 1 ;;
    esac
done

# Auth requires nginx, which is only started with the ssl profile.
if [[ "$AUTH_ARG" == "true" ]]; then
    if [[ "$SSL_ARG_EXPLICIT" == "true" && "$SSL_ARG" == "false" ]]; then
        fail "--auth true requires SSL (nginx). --ssl false is not compatible with --auth true."
        exit 1
    fi
    SSL_ARG="true"
    [[ "$SSL_ARG_EXPLICIT" == "false" ]] && info "Auto-enabling SSL: Keycloak authentication requires nginx"
fi

# When --listen-port is not given, default the port for the selected mode
# (443 for HTTPS, 80 for HTTP). User can override with --listen-port.
if [[ -z "$LISTEN_PORT_ARG" ]]; then
    if [[ "$SSL_ARG" == "true" ]]; then
        LISTEN_PORT_ARG="443"
    else
        LISTEN_PORT_ARG="80"
    fi
fi

# ---------------------------------------------------------------------------
# Apply CLI server-config args to config/isi_mcp.env (CLI takes precedence)
# ---------------------------------------------------------------------------
APP_CONFIG_EARLY="${SCRIPT_DIR}/config/isi_mcp.env"
if [[ "$AUTH_ARG" == "true" || "$AUTH_ARG" == "false" ]]; then
    sed -i "s/^AUTH_ENABLED=.*/AUTH_ENABLED=${AUTH_ARG}/" "$APP_CONFIG_EARLY"
    ok "Set AUTH_ENABLED=${AUTH_ARG} in config/isi_mcp.env"
else
    fail "--auth must be 'true' or 'false' (got: ${AUTH_ARG})"
    exit 1
fi
if [[ "$SSL_ARG" == "true" || "$SSL_ARG" == "false" ]]; then
    sed -i "s/^SSL=.*/SSL=${SSL_ARG}/" "$APP_CONFIG_EARLY"
    ok "Set SSL=${SSL_ARG} in config/isi_mcp.env"
else
    fail "--ssl must be 'true' or 'false' (got: ${SSL_ARG})"
    exit 1
fi
if [[ -n "$LISTEN_PORT_ARG" ]]; then
    if [[ "$LISTEN_PORT_ARG" =~ ^[0-9]+$ ]]; then
        sed -i "s/^PORT=.*/PORT=${LISTEN_PORT_ARG}/" "$APP_CONFIG_EARLY"
        ok "Set PORT=${LISTEN_PORT_ARG} in config/isi_mcp.env"
    else
        fail "--listen-port must be a number (got: ${LISTEN_PORT_ARG})"
        exit 1
    fi
fi

# Read effective PORT and SSL from config (after all CLI overrides applied above)
PORT=$(grep '^PORT=' "$APP_CONFIG_EARLY" 2>/dev/null | cut -d= -f2- | tr -d ' ')
PORT="${PORT:-80}"
SSL=$(grep '^SSL=' "$APP_CONFIG_EARLY" 2>/dev/null | cut -d= -f2- | tr -d ' ')
SSL="${SSL:-false}"
if [[ "$SSL" == "true" ]]; then
    export HTTPS_PORT="$PORT"
else
    export PORT="$PORT"
fi

# ---------------------------------------------------------------------------
# Check prerequisites (docker and docker-compose required for setup)
# ---------------------------------------------------------------------------
if ! command -v docker &>/dev/null; then
    fail "Docker is not installed."
    fail "Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if docker compose version &>/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
else
    fail "docker-compose is not available."
    fail "Install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# ---------------------------------------------------------------------------
# Check for existing setup (vault.yml and/or keycloak-db-data volume)
# Ask before prompting for new credentials
# ---------------------------------------------------------------------------
SKIP_SETUP=false
KEYCLOAK_DB_VOLUME="isi_mcp_demo_keycloak-db-data"

mkdir -p "$VAULT_DIR"

# Pre-create bind-mounted writable dirs before Docker starts so Docker does not create
# them as root. The container runs as mcp (UID 1000); when setup.sh is run with sudo
# the mkdir produces root-owned dirs and the container cannot write. Transfer ownership
# to UID 1000 whenever we are running as root.
mkdir -p "${SCRIPT_DIR}/playbooks" "${SCRIPT_DIR}/audit"
if [[ $EUID -eq 0 ]]; then
    chown 1000:1000 "${SCRIPT_DIR}/playbooks" "${SCRIPT_DIR}/audit"
fi

# Check for existing vault and keycloak volume
VAULT_EXISTS=false
KEYCLOAK_VOLUME_EXISTS=false

if [[ -f "$VAULT_FILE" ]]; then
    FIRST_LINE="$(head -c 14 "$VAULT_FILE")"
    if [[ "$FIRST_LINE" == '$ANSIBLE_VAULT' ]]; then
        VAULT_EXISTS=true
    fi
fi

if docker volume ls 2>/dev/null | grep -q "$KEYCLOAK_DB_VOLUME"; then
    KEYCLOAK_VOLUME_EXISTS=true
fi

# Prompt user based on what exists
if [[ "$VAULT_EXISTS" == true && "$KEYCLOAK_VOLUME_EXISTS" == true ]]; then
    # Both exist — offer to keep everything
    warn "Existing setup detected:\n  • vault.yml (encrypted credentials)\n  • keycloak-db-data (database volume)\n"
    read -rp "Keep existing setup and skip credential setup? [Y/n]: " KEEP_SETUP

    if [[ "$KEEP_SETUP" != "n" && "$KEEP_SETUP" != "N" ]]; then
        ok "Keeping existing setup — skipping credential setup."
        SKIP_SETUP=true
    else
        info "Removing existing setup..."
        rm -rf "$VAULT_DIR"
        rm -f "${VAULT_DIR}"/*.pem 2>/dev/null || true
        if [[ -d "${SCRIPT_DIR}/nginx/certs" ]]; then
            rm -rf "${SCRIPT_DIR}/nginx/certs"
            ok "Removed nginx/certs (will regenerate)"
        fi
        rm -f "${SCRIPT_DIR}/playbooks"/*.yml 2>/dev/null || true
        info "Stopping containers..."
        $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" down 2>/dev/null || true
        info "Removing keycloak database volume..."
        docker volume rm "$KEYCLOAK_DB_VOLUME" 2>/dev/null || warn "Could not remove volume (may be in use)"
        ok "Existing setup cleared — proceeding with fresh installation"
    fi

elif [[ "$VAULT_EXISTS" == true ]]; then
    # Only vault exists — offer to keep it
    warn "Existing setup detected:\n  • vault.yml (encrypted credentials)\n"
    read -rp "Keep existing vault and skip credential setup? [Y/n]: " KEEP_SETUP

    if [[ "$KEEP_SETUP" != "n" && "$KEEP_SETUP" != "N" ]]; then
        ok "Keeping existing vault — skipping credential setup."
        SKIP_SETUP=true
    else
        info "Removing existing vault..."
        rm -rf "$VAULT_DIR"
        rm -f "${VAULT_DIR}"/*.pem 2>/dev/null || true
        if [[ -d "${SCRIPT_DIR}/nginx/certs" ]]; then
            rm -rf "${SCRIPT_DIR}/nginx/certs"
            ok "Removed nginx/certs (will regenerate)"
        fi
        rm -f "${SCRIPT_DIR}/playbooks"/*.yml 2>/dev/null || true
        ok "Vault removed — proceeding with fresh installation"
    fi

elif [[ "$KEYCLOAK_VOLUME_EXISTS" == true ]]; then
    # Volume exists but vault is missing — credentials must be reconfigured
    warn "Keycloak database volume found but vault.yml is missing."
    warn "Credentials must be configured again."
    echo ""
    read -rp "Keep the existing Keycloak database volume? [Y/n]: " KEEP_VOL

    if [[ "$KEEP_VOL" != "n" && "$KEEP_VOL" != "N" ]]; then
        ok "Keeping Keycloak volume — proceeding with credential setup."
    else
        info "Removing Keycloak database volume..."
        $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" down 2>/dev/null || true
        docker volume rm "$KEYCLOAK_DB_VOLUME" 2>/dev/null || warn "Could not remove volume (may be in use)"
        ok "Removed keycloak-db-data — proceeding with fresh installation"
    fi
fi

# ---------------------------------------------------------------------------
# Prompt for cluster credentials (only if not keeping existing vault)
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == false ]]; then
    while [[ -z "$CLUSTER_HOST" ]]; do
        read -rp "Cluster host: " input_host
        CLUSTER_HOST="$input_host"
        if [[ -z "$CLUSTER_HOST" ]]; then
            warn "Cluster host is required."
        fi
    done

    while [[ -z "$CLUSTER_USER" ]]; do
        read -rp "Cluster username: " input_user
        CLUSTER_USER="$input_user"
        if [[ -z "$CLUSTER_USER" ]]; then
            warn "Cluster username is required."
        fi
    done

    while [[ -z "$CLUSTER_PASS" ]]; do
        read -rsp "Cluster password for ${CLUSTER_USER}@${CLUSTER_HOST}: " input_pass
        echo
        CLUSTER_PASS="$input_pass"
        if [[ -z "$CLUSTER_PASS" ]]; then
            warn "Cluster password is required."
        fi
    done
fi

# ---------------------------------------------------------------------------
# Prompt for vault password (always needed to encrypt/decrypt vault)
# ---------------------------------------------------------------------------
if [[ -z "$VAULT_PASS" ]]; then
    read -rsp "Vault encryption password (for vault.yml): " VAULT_PASS
    echo
fi
if [[ -z "$VAULT_PASS" ]]; then
    fail "Vault password is required."
    exit 1
fi

# ---------------------------------------------------------------------------
# Check config/isi_mcp.env to see if authentication is enabled.
# Set AUTH_ENABLED=true there to enable OAuth via Keycloak.
# If enabled, prompt for Keycloak passwords (never stored in files).
# ---------------------------------------------------------------------------
APP_CONFIG="${APP_CONFIG_EARLY}"
COMPOSE_PROFILES=""
if grep -qE '^AUTH_ENABLED=true' "$APP_CONFIG" 2>/dev/null; then
    if [[ "$SKIP_SETUP" == false ]]; then
        # New setup — passwords required
        info "Authentication is enabled. Keycloak credentials required."
        if [[ -z "${KEYCLOAK_DB_PASSWORD:-}" ]]; then
            read -rsp "Keycloak database password (KEYCLOAK_DB_PASSWORD): " KEYCLOAK_DB_PASSWORD
            echo
            export KEYCLOAK_DB_PASSWORD
        fi
        if [[ -z "$KEYCLOAK_DB_PASSWORD" ]]; then
            fail "KEYCLOAK_DB_PASSWORD is required when AUTH_ENABLED=true."
            exit 1
        fi
        if [[ -z "${KEYCLOAK_ADMIN_PASSWORD:-}" ]]; then
            read -rsp "Keycloak admin password (KEYCLOAK_ADMIN_PASSWORD): " KEYCLOAK_ADMIN_PASSWORD
            echo
            export KEYCLOAK_ADMIN_PASSWORD
        fi
        if [[ -z "$KEYCLOAK_ADMIN_PASSWORD" ]]; then
            fail "KEYCLOAK_ADMIN_PASSWORD is required when AUTH_ENABLED=true."
            exit 1
        fi
    else
        # Existing vault — Keycloak credentials will be read from the vault after the
        # image is built. No prompts needed; only the vault password is required.
        info "Authentication is enabled — Keycloak credentials will be read from vault."
    fi
    COMPOSE_PROFILES="--profile auth"
fi
if [[ "$SSL" == "true" ]]; then
    COMPOSE_PROFILES="$COMPOSE_PROFILES --profile ssl"
fi

# ---------------------------------------------------------------------------
# Normalize host — ensure https:// prefix
# ---------------------------------------------------------------------------
if [[ "$CLUSTER_HOST" =~ ^https?:// ]]; then
    VAULT_HOST="$CLUSTER_HOST"
else
    VAULT_HOST="https://${CLUSTER_HOST}"
fi

# ---------------------------------------------------------------------------
# Initialize variables set during cert extraction (SKIP_SETUP=false path)
# ---------------------------------------------------------------------------
CLUSTER_CA_BUNDLE=""
VERIFY_SSL="true"

# ---------------------------------------------------------------------------
# Generate TLS certificates for nginx (only when SSL=true)
# ---------------------------------------------------------------------------
CERT_SCRIPT="${SCRIPT_DIR}/nginx/generate-certs.sh"
CERT_DIR="${SCRIPT_DIR}/nginx/certs"
if [[ "$SSL" == "true" ]]; then
    if [[ -f "${CERT_DIR}/server.crt" && -f "${CERT_DIR}/server.key" ]]; then
        warn "SSL certificates already exist in nginx/certs/."
        read -rp "Regenerate certificates? [y/N]: " REGEN_CERTS
        if [[ "$REGEN_CERTS" == "y" || "$REGEN_CERTS" == "Y" ]]; then
            if [[ -x "$CERT_SCRIPT" ]]; then
                "$CERT_SCRIPT" --force
            else
                warn "nginx/generate-certs.sh not found — keeping existing certificates."
            fi
        else
            info "Keeping existing certificates."
        fi
    else
        if [[ -x "$CERT_SCRIPT" ]]; then
            info "Generating TLS certificates..."
            "$CERT_SCRIPT"
        else
            warn "nginx/generate-certs.sh not found — skipping TLS cert generation."
            warn "Place cert files in nginx/certs/ before starting with SSL=true."
        fi
    fi
else
    info "SSL=false — skipping TLS certificate generation."
fi

# ---------------------------------------------------------------------------
# Build the Docker image (required so Ansible is available for encryption)
# ---------------------------------------------------------------------------
info "Building Docker image..."
BUILD_FLAG=""
[[ "$NO_CACHE" == true ]] && BUILD_FLAG="--no-cache" && info "Cache disabled — forcing full rebuild"
$COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" build $BUILD_FLAG
ok "Image built"

# ---------------------------------------------------------------------------
# Validate vault password early (existing-setup path only).
# Fail fast with a clear message rather than a cryptic Python traceback buried
# inside a later docker compose run call.
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == true ]]; then
    info "Validating vault password..."
    if ! VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" \
        run --rm --no-deps isi_mcp python3 -c "
import os
from ansible.parsing.vault import VaultLib, VaultSecret
pwd = os.environ.get('VAULT_PASSWORD', '').encode()
VaultLib([('default', VaultSecret(pwd))]).decrypt(open('/app/vault/vault.yml').read())
print('vault ok')
"; then
        fail "Vault password is incorrect or vault is corrupted."
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# If keeping an existing vault with auth enabled, read Keycloak credentials
# from the vault using the vault password already collected above.
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == true ]] && grep -qE '^AUTH_ENABLED=true' "$APP_CONFIG" 2>/dev/null \
        && [[ -z "${KEYCLOAK_DB_PASSWORD:-}" ]]; then
    info "Reading Keycloak credentials from vault..."
    # Use unique line-prefix markers so grep can isolate vault output even if
    # docker compose prints container lifecycle messages to stdout on this platform.
    _KC_CREDS=$(VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" \
        run --rm --no-deps isi_mcp python3 -c "
import os, yaml
from ansible.parsing.vault import VaultLib, VaultSecret
pwd = os.environ.get('VAULT_PASSWORD', '').encode()
vault = VaultLib([('default', VaultSecret(pwd))])
with open('/app/vault/vault.yml') as f:
    data = yaml.safe_load(vault.decrypt(f.read()))
kc = data.get('keycloak') if isinstance(data, dict) else None
db_pass = kc.get('db_password') if isinstance(kc, dict) else None
admin_pass = kc.get('admin_password') if isinstance(kc, dict) else None
if db_pass:
    print('__KC_DB__' + str(db_pass))
    print('__KC_ADMIN__' + str(admin_pass or ''))
else:
    print('__KC_NOTFOUND__')
" 2>/dev/null) || true
    if printf '%s\n' "$_KC_CREDS" | grep -q '^__KC_DB__'; then
        KEYCLOAK_DB_PASSWORD=$(printf '%s\n' "$_KC_CREDS" | grep '^__KC_DB__' | head -1 | sed 's/^__KC_DB__//')
        KEYCLOAK_ADMIN_PASSWORD=$(printf '%s\n' "$_KC_CREDS" | grep '^__KC_ADMIN__' | head -1 | sed 's/^__KC_ADMIN__//')
        export KEYCLOAK_DB_PASSWORD KEYCLOAK_ADMIN_PASSWORD
        ok "Keycloak credentials loaded from vault."
    else
        warn "Keycloak credentials not found in vault (auth was added after initial setup)."
        info "Please enter Keycloak passwords to add them to the vault now."
        read -rsp "Keycloak database password (KEYCLOAK_DB_PASSWORD): " KEYCLOAK_DB_PASSWORD
        echo
        export KEYCLOAK_DB_PASSWORD
        if [[ -z "$KEYCLOAK_DB_PASSWORD" ]]; then
            fail "KEYCLOAK_DB_PASSWORD is required when AUTH_ENABLED=true."
            exit 1
        fi
        read -rsp "Keycloak admin password (KEYCLOAK_ADMIN_PASSWORD): " KEYCLOAK_ADMIN_PASSWORD
        echo
        export KEYCLOAK_ADMIN_PASSWORD
        if [[ -z "$KEYCLOAK_ADMIN_PASSWORD" ]]; then
            fail "KEYCLOAK_ADMIN_PASSWORD is required when AUTH_ENABLED=true."
            exit 1
        fi
    fi
    unset _KC_CREDS
fi

# ---------------------------------------------------------------------------
# Guard against Keycloak DB volume/password mismatch.
#
# If the user supplies a KEYCLOAK_DB_PASSWORD that differs from what was used
# to initialise the Postgres volume, Keycloak will fail to connect to its
# database. Detect this and offer to drop and recreate the volume.
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == true ]] \
    && grep -qE '^AUTH_ENABLED=true' "$APP_CONFIG" 2>/dev/null \
    && [[ "$KEYCLOAK_VOLUME_EXISTS" == true ]] \
    && [[ -n "${KEYCLOAK_DB_PASSWORD:-}" ]]; then

    _VAULT_KC_DB=$(VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" \
        run --rm --no-deps isi_mcp python3 -c "
import os, yaml
from ansible.parsing.vault import VaultLib, VaultSecret
pwd = os.environ.get('VAULT_PASSWORD', '').encode()
vault = VaultLib([('default', VaultSecret(pwd))])
try:
    data = yaml.safe_load(vault.decrypt(open('/app/vault/vault.yml').read()))
    print('__VKC__' + str(data.get('keycloak', {}).get('db_password', '')), end='')
except Exception:
    print('__VKC__', end='')
" 2>/dev/null) || true
    _VAULT_KC_DB=$(printf '%s' "$_VAULT_KC_DB" | grep -o '__VKC__.*' | sed 's/^__VKC__//')

    if [[ -n "$_VAULT_KC_DB" && "$_VAULT_KC_DB" != "$KEYCLOAK_DB_PASSWORD" ]]; then
        warn "KEYCLOAK_DB_PASSWORD differs from the value stored in the vault."
        warn "The Keycloak Postgres volume was initialised with the old password."
        warn "Changing the password WITHOUT dropping the volume will cause Keycloak to fail to start."
        echo ""
        read -rp "Drop and recreate the Keycloak database volume (loses all realm data)? [y/N]: " _DROP_VOL
        if [[ "$_DROP_VOL" == "y" || "$_DROP_VOL" == "Y" ]]; then
            info "Stopping containers and removing Keycloak database volume..."
            $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" down 2>/dev/null || true
            docker volume rm "$KEYCLOAK_DB_VOLUME" 2>/dev/null \
                || { fail "Could not remove volume. Stop all running containers first and retry."; exit 1; }
            ok "Volume removed — Keycloak will be re-initialised with the new password."
            KEYCLOAK_VOLUME_EXISTS=false
        else
            info "Keeping existing volume — reverting to the password stored in the vault."
            KEYCLOAK_DB_PASSWORD="$_VAULT_KC_DB"
            export KEYCLOAK_DB_PASSWORD
        fi
    fi
    unset _VAULT_KC_DB _DROP_VOL
fi

# ---------------------------------------------------------------------------
# If keeping an existing vault but auth is now enabled, inject keycloak section
# (handles the case where setup was initially done without auth, auth enabled later)
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == true ]] && grep -qE '^AUTH_ENABLED=true' "$APP_CONFIG" 2>/dev/null \
        && [[ -n "${KEYCLOAK_DB_PASSWORD:-}" ]]; then
    info "Checking vault for keycloak credentials..."
    export _KC_DB_PASS="$KEYCLOAK_DB_PASSWORD"
    export _KC_ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-}"
    VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" run --rm --no-deps \
        -e VAULT_PASSWORD -e _KC_DB_PASS -e _KC_ADMIN_PASS \
        isi_mcp python3 -c "
import os, yaml, sys
from ansible.parsing.vault import VaultLib, VaultSecret
pwd = os.environ.get('VAULT_PASSWORD', '').encode()
vault = VaultLib([('default', VaultSecret(pwd))])
with open('/app/vault/vault.yml') as f:
    data = yaml.safe_load(vault.decrypt(f.read()))
data['keycloak'] = {
    'db_password': os.environ['_KC_DB_PASS'],
    'admin_password': os.environ.get('_KC_ADMIN_PASS', ''),
}
plaintext = yaml.dump(data, default_flow_style=False).encode()
encrypted = vault.encrypt(plaintext)
with open('/app/vault/vault.yml', 'wb') as f:
    f.write(encrypted if isinstance(encrypted, bytes) else encrypted.encode())
print('Keycloak credentials added to vault.')
"
    unset _KC_DB_PASS _KC_ADMIN_PASS
    ok "Vault updated with keycloak credentials."
fi

# ---------------------------------------------------------------------------
# Extract cluster TLS certificate (for SSL verification)
#
# Uses the just-built Docker image — no openssl needed on the host.
# Sets VERIFY_SSL and CLUSTER_CA_BUNDLE bash variables used by vault creation.
# Three cases:
#   a) CA-signed cert (Subject != Issuer): verify_ssl=true, use system CA store.
#   b) Self-signed with CA:TRUE: cert pinning via ca_bundle.
#   c) Self-signed without CA:TRUE (PowerScale v1 default): verify_ssl=false.
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == false ]]; then
    HOST_BARE="${VAULT_HOST#https://}"
    HOST_BARE="${HOST_BARE#http://}"
    info "Extracting cluster TLS certificate for SSL verification..."

    CERT_EXTRACTED=false
    if $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" run --rm isi_mcp \
        sh -c "openssl s_client -connect ${HOST_BARE}:${CLUSTER_PORT} \
               -connect_timeout 10 \
               -showcerts </dev/null 2>/dev/null \
               | openssl x509 -outform PEM \
               > /app/vault/${CLUSTER_NAME}_cert.pem" 2>/dev/null \
        && [[ -s "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" ]]; then
        CERT_EXTRACTED=true
    fi

    CERT_IS_CA=false
    IS_SELF_SIGNED=false
    if [[ "$CERT_EXTRACTED" == true ]]; then
        if openssl x509 -in "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" -text -noout 2>/dev/null \
            | grep -q "CA:TRUE"; then
            CERT_IS_CA=true
        fi
        SUBJECT=$(openssl x509 -in "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" -noout -subject 2>/dev/null | sed 's/subject=//')
        ISSUER=$(openssl x509  -in "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" -noout -issuer  2>/dev/null | sed 's/issuer=//')
        if [[ "$SUBJECT" == "$ISSUER" ]]; then
            IS_SELF_SIGNED=true
        fi
    fi

    if [[ "$IS_SELF_SIGNED" == true && "$CERT_IS_CA" == true ]]; then
        ok "Cluster certificate saved to vault/${CLUSTER_NAME}_cert.pem (CA:TRUE — cert pinning enabled)"
        CLUSTER_CA_BUNDLE="/app/vault/${CLUSTER_NAME}_cert.pem"
    elif [[ "$IS_SELF_SIGNED" == false && "$CERT_EXTRACTED" == true ]]; then
        rm -f "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" 2>/dev/null || true
        ok "Cluster has a CA-signed certificate — SSL verification enabled using system CA store."
    else
        rm -f "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" 2>/dev/null || true
        if [[ "$CERT_EXTRACTED" == true ]]; then
            warn "Cluster cert is X.509 v1 self-signed (no CA:TRUE) — typical for PowerScale default certs."
        else
            warn "Could not extract cluster certificate."
        fi
        warn "SSL verification will be disabled (verify_ssl: false)."
        VERIFY_SSL="false"
    fi
fi

# ---------------------------------------------------------------------------
# Create and encrypt vault.yml in a single step.
#
# All credentials are passed via environment variables — never as CLI arguments
# (which are visible in docker inspect / ps aux) and never written to disk in
# plaintext. Python builds the YAML dict, yaml.dump handles all quoting, and
# VaultLib encrypts in memory before writing the ciphertext to vault.yml.
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == false ]]; then
    info "Creating and encrypting vault.yml..."
    mkdir -p "$VAULT_DIR"
    export _ISI_NAME="$CLUSTER_NAME"
    export _ISI_HOST="$VAULT_HOST"
    export _ISI_PORT="$CLUSTER_PORT"
    export _ISI_USER="$CLUSTER_USER"
    export _ISI_PASS="$CLUSTER_PASS"
    export _ISI_SSL="$VERIFY_SSL"
    export _ISI_CA="${CLUSTER_CA_BUNDLE:-}"
    export _KC_DB_PASS="${KEYCLOAK_DB_PASSWORD:-}"
    export _KC_ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-}"

    VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" run --rm --no-deps \
        -e _ISI_NAME -e _ISI_HOST -e _ISI_PORT -e _ISI_USER -e _ISI_PASS \
        -e _ISI_SSL -e _ISI_CA -e _KC_DB_PASS -e _KC_ADMIN_PASS \
        isi_mcp python3 -c "
import os, yaml
from ansible.parsing.vault import VaultLib, VaultSecret
from pathlib import Path
name       = os.environ['_ISI_NAME']
host       = os.environ['_ISI_HOST']
port       = int(os.environ['_ISI_PORT'])
username   = os.environ['_ISI_USER']
password   = os.environ['_ISI_PASS']
verify_ssl = os.environ['_ISI_SSL'].lower() == 'true'
ca_bundle  = os.environ.get('_ISI_CA') or None
kc_db      = os.environ.get('_KC_DB_PASS', '')
kc_admin   = os.environ.get('_KC_ADMIN_PASS', '')
data = {'clusters': {name: {
    'host': host, 'port': port, 'username': username,
    'password': password, 'verify_ssl': verify_ssl,
}}}
if ca_bundle:
    data['clusters'][name]['ca_bundle'] = ca_bundle
if kc_db:
    data['keycloak'] = {'db_password': kc_db, 'admin_password': kc_admin}
pwd = os.environ['VAULT_PASSWORD'].encode()
vault = VaultLib([('default', VaultSecret(pwd))])
plaintext = yaml.dump(data, default_flow_style=False).encode()
encrypted = vault.encrypt(plaintext)
Path('/app/vault/vault.yml').write_bytes(
    encrypted if isinstance(encrypted, bytes) else encrypted.encode()
)
print('vault.yml created and encrypted.')
"
    unset _ISI_NAME _ISI_HOST _ISI_PORT _ISI_USER _ISI_PASS _ISI_SSL _ISI_CA _KC_DB_PASS _KC_ADMIN_PASS
    chmod 600 "$VAULT_FILE"
    ok "vault.yml created and encrypted"
fi

# ---------------------------------------------------------------------------
# Print connection instructions (before starting so they're visible above logs)
# ---------------------------------------------------------------------------
if [[ "$SSL" == "true" ]]; then
    _MCP_URL="https://localhost:${PORT}/mcp"
    _SSE_URL="https://localhost:${PORT}/sse"
else
    _MCP_URL="http://localhost:${PORT}/mcp"
    _SSE_URL="http://localhost:${PORT}/sse"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ "$SKIP_SETUP" == false ]]; then
    ok "Setup complete! Connecting to: ${VAULT_HOST}:${CLUSTER_PORT} as ${CLUSTER_USER}"
else
    ok "Setup complete! Using existing cluster configuration."
fi
echo ""
if [[ "$SSL" == "true" ]]; then
    info "MCP server will be available at: ${_MCP_URL} (via nginx, TLS)"
else
    info "MCP server will be available at: ${_MCP_URL} (direct HTTP)"
fi
echo ""
warn "IMPORTANT: Save your vault password in a secure location!"
warn "You will need it to restart the server later."
echo ""
info "Connect your LLM client:"
echo "  Claude Code: claude mcp add --transport http powerscale ${_MCP_URL}"
echo "  Claude Desktop: Add to claude_desktop_config.json:"
echo "    { \"mcpServers\": { \"powerscale\": { \"url\": \"${_MCP_URL}\" } } }"
echo "  Cursor/Windsurf SSE endpoint: ${_SSE_URL}"
echo ""
if [[ "$SSL" == "true" ]]; then
    warn "Note: Self-signed certs require clients to accept untrusted certificates."
    echo ""
fi
if grep -qE '^AUTH_ENABLED=true' "$APP_CONFIG" 2>/dev/null; then
    if [[ "$SSL" == "true" ]]; then
        _KC_ADMIN_URL="https://localhost:${PORT}/auth/admin"
    else
        _KC_ADMIN_URL="http://localhost:${PORT}/auth/admin"
    fi
    info "Keycloak admin console:"
    echo "  ${_KC_ADMIN_URL}"
    echo ""
fi
info "To restart the server later:"
echo "  ./start.sh"
echo ""
info "To add or edit clusters later:"
echo "  ./setup.sh add-cluster --name <name> --host <host>"
echo "  ./setup.sh modify-cluster --name <name> --host <new-host>"
echo "  ./setup.sh list-clusters"
echo ""
info "To stop the server:"
echo "  ./stop.sh"
echo ""
info "To start claude with the Powerscale Agent:"
echo "claude --agent PowerscaleAgent --agents '{
  "PowerscaleAgent": {
    "description": "Interacts with the MCP server using detailed context",
    "prompt": "You are a knowledgeable assistant for managing a Powerscale Cluster.",
    "context": "AGENT-CONTEXT.md"
  }
}'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ---------------------------------------------------------------------------
# Build compose file list: always base, plus http.yml overlay when SSL=false
# ---------------------------------------------------------------------------
COMPOSE_FILES="-f ${SCRIPT_DIR}/docker-compose.yml"
[[ "$SSL" == "false" ]] && COMPOSE_FILES="$COMPOSE_FILES -f ${SCRIPT_DIR}/docker-compose.http.yml"

# ---------------------------------------------------------------------------
# Start the server.
#
# Stop any existing container first. docker-compose v1 (<=1.29.2) has a bug
# where recreating a container reads 'ContainerConfig' from the image manifest,
# which was removed in newer Docker Engine versions, causing a KeyError. Stopping
# the old container before 'up' avoids the recreate path entirely.
# ---------------------------------------------------------------------------
info "Stopping any existing container..."
$COMPOSE_CMD $COMPOSE_FILES $COMPOSE_PROFILES down 2>/dev/null || true

info "Starting MCP server in background..."
VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD $COMPOSE_FILES $COMPOSE_PROFILES up -d
ok "Server started. View logs: $COMPOSE_CMD $COMPOSE_FILES logs -f"
