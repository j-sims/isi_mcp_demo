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
  --name NAME         Cluster label in vault.yml (default: isilon)
  --auth true|false   Enable OAuth authentication via Keycloak (default: false)
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

After setup, restart the server with vault password:
  read -s -p 'Vault password: ' VAULT_PASSWORD && export VAULT_PASSWORD
  docker compose up -d

To edit vault credentials later (requires vault password):
  docker compose exec isi_mcp ansible-vault edit /app/vault/vault.yml
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
    --pass PASS         Admin password (prompted securely if not provided)

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
  read -s -p 'Cluster password: ' CLUSTER_PASS
  ./setup.sh add-cluster --name lab --host 172.16.10.10 --user root --pass "$CLUSTER_PASS"

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
" 2>/dev/null
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
            --pass)    CLUSTER_PASS="${args[$((i+1))]}";  i=$((i+2)) ;;
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
    if [[ -z "$CLUSTER_PASS" ]]; then
        read -rsp "Cluster password for ${CLUSTER_USER}@${CLUSTER_HOST}: " CLUSTER_PASS
        echo
        [[ -z "$CLUSTER_PASS" ]] && { fail "Cluster password is required."; exit 1; }
    fi

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
" 2>/dev/null

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
" 2>/dev/null

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
" 2>/dev/null

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
# Parse arguments
# ---------------------------------------------------------------------------
CLUSTER_HOST=""
CLUSTER_PORT=8080
CLUSTER_USER=""
CLUSTER_PASS=""
CLUSTER_NAME="isilon"
VAULT_PASS="${VAULT_PASSWORD:-}"
AUTH_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)       CLUSTER_HOST="$2"; shift 2 ;;
        --port)       CLUSTER_PORT="$2"; shift 2 ;;
        --user)       CLUSTER_USER="$2"; shift 2 ;;
        --pass)       CLUSTER_PASS="$2"; shift 2 ;;
        --name)       CLUSTER_NAME="$2"; shift 2 ;;
        --auth)       AUTH_ARG="$2"; shift 2 ;;
        -h|--help)    show_help; exit 0 ;;
        *)            fail "Unknown argument: $1"; echo "Run ./setup.sh --help for usage."; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Apply --auth argument to config/isi_mcp.env if provided
# ---------------------------------------------------------------------------
APP_CONFIG_EARLY="${SCRIPT_DIR}/config/isi_mcp.env"
if [[ -n "$AUTH_ARG" ]]; then
    if [[ "$AUTH_ARG" == "true" || "$AUTH_ARG" == "false" ]]; then
        sed -i "s/^AUTH_ENABLED=.*/AUTH_ENABLED=${AUTH_ARG}/" "$APP_CONFIG_EARLY"
        ok "Set AUTH_ENABLED=${AUTH_ARG} in config/isi_mcp.env"
    else
        fail "--auth must be 'true' or 'false' (got: ${AUTH_ARG})"
        exit 1
    fi
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

# Pre-create playbooks dir as the current user so Docker doesn't create it as root.
# The container runs as mcp (UID 1000); the host user running setup.sh must also be
# UID 1000 (or the directory must be group/world writable) for writes to succeed.
mkdir -p "${SCRIPT_DIR}/playbooks"

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

# If either exists, prompt user
if [[ "$VAULT_EXISTS" == true ]] || [[ "$KEYCLOAK_VOLUME_EXISTS" == true ]]; then
    EXISTING_STATE=""
    [[ "$VAULT_EXISTS" == true ]] && EXISTING_STATE="${EXISTING_STATE}  • vault.yml (encrypted credentials)\n"
    [[ "$KEYCLOAK_VOLUME_EXISTS" == true ]] && EXISTING_STATE="${EXISTING_STATE}  • keycloak-db-data (database volume)\n"

    warn "Existing setup detected:\n${EXISTING_STATE}"
    read -rp "Keep existing setup and skip credential setup? [Y/n]: " KEEP_SETUP

    if [[ "$KEEP_SETUP" != "n" && "$KEEP_SETUP" != "N" ]]; then
        ok "Keeping existing setup — skipping credential setup."
        SKIP_SETUP=true
    else
        # User wants to overwrite — delete existing setup
        info "Removing existing setup..."

        # Delete vault directory if it exists (removes vault.yml + any *.pem files)
        if [[ "$VAULT_EXISTS" == true ]]; then
            rm -rf "$VAULT_DIR"
            ok "Removed vault directory"
        fi

        # Remove cluster cert PEM files (in case vault was deleted separately)
        rm -f "${VAULT_DIR}"/*.pem 2>/dev/null || true

        # Remove TLS certs so setup.sh generates fresh ones
        if [[ -d "${SCRIPT_DIR}/nginx/certs" ]]; then
            rm -rf "${SCRIPT_DIR}/nginx/certs"
            ok "Removed nginx/certs (will regenerate)"
        fi

        # Remove rendered playbooks from prior run
        rm -f "${SCRIPT_DIR}/playbooks"/*.yml 2>/dev/null || true

        # Stop containers and remove volume
        if [[ "$KEYCLOAK_VOLUME_EXISTS" == true ]]; then
            info "Stopping containers..."
            $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" down 2>/dev/null || true

            info "Removing keycloak database volume..."
            docker volume rm "$KEYCLOAK_DB_VOLUME" 2>/dev/null || warn "Could not remove volume (may be in use)"
            ok "Removed keycloak-db-data"
        fi

        ok "Existing setup cleared — proceeding with fresh installation"
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
    info "Authentication is enabled in config/isi_mcp.env. Keycloak credentials required."
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
    COMPOSE_PROFILES="--profile auth"
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
# Initialize cluster CA bundle variable (will be set during cert extraction)
# ---------------------------------------------------------------------------
CLUSTER_CA_BUNDLE=""

# ---------------------------------------------------------------------------
# Write plaintext vault.yml (will be encrypted in the next step)
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == false ]]; then
    {
        cat << VAULT_EOF
clusters:
  ${CLUSTER_NAME}:
    host: "${VAULT_HOST}"
    port: ${CLUSTER_PORT}
    username: ${CLUSTER_USER}
    password: ${CLUSTER_PASS}
    verify_ssl: true
VAULT_EOF
        if [[ -n "${KEYCLOAK_DB_PASSWORD:-}" ]]; then
            cat << KEYCLOAK_EOF

keycloak:
  db_password: ${KEYCLOAK_DB_PASSWORD}
  admin_password: ${KEYCLOAK_ADMIN_PASSWORD}
KEYCLOAK_EOF
        fi
    } > "$VAULT_FILE"
    chmod 600 "$VAULT_FILE"
    ok "Created vault.yml (plaintext — will encrypt next)"
fi

# ---------------------------------------------------------------------------
# Generate TLS certificates for nginx (if not already present)
# ---------------------------------------------------------------------------
CERT_SCRIPT="${SCRIPT_DIR}/nginx/generate-certs.sh"
if [[ -x "$CERT_SCRIPT" ]]; then
    info "Checking TLS certificates..."
    "$CERT_SCRIPT"
else
    warn "nginx/generate-certs.sh not found — skipping TLS cert generation."
    warn "Run nginx/generate-certs.sh manually before starting with HTTPS."
fi

# ---------------------------------------------------------------------------
# Build the Docker image (required so Ansible is available for encryption)
# ---------------------------------------------------------------------------
info "Building Docker image..."
$COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" build
ok "Image built"

# ---------------------------------------------------------------------------
# Extract cluster TLS certificate (for SSL verification without replacing cert)
#
# Uses the just-built Docker image — no openssl needed on the host.
# The vault dir is already bind-mounted at /app/vault inside the container.
# Extracts the cert and saves it to vault/${CLUSTER_NAME}_cert.pem, then updates vault.yml.
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == false ]]; then
    HOST_BARE="${VAULT_HOST#https://}"  # strip https:// prefix
    HOST_BARE="${HOST_BARE#http://}"
    info "Extracting cluster TLS certificate for SSL verification..."

    # Use openssl inside the container to extract the certificate
    CERT_EXTRACTED=false
    if $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" run --rm isi_mcp \
        sh -c "openssl s_client -connect ${HOST_BARE}:${CLUSTER_PORT} \
               -showcerts </dev/null 2>/dev/null \
               | openssl x509 -outform PEM \
               > /app/vault/${CLUSTER_NAME}_cert.pem" 2>/dev/null \
        && [[ -s "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" ]]; then
        CERT_EXTRACTED=true
    fi

    # Inspect the extracted cert to decide the SSL strategy.
    #
    # Three cases:
    #   a) CA-signed cert (Subject != Issuer): customer installed their own cert.
    #      Keep verify_ssl: true and rely on the system CA store.
    #   b) Self-signed with CA:TRUE: valid v3 self-signed CA cert.
    #      Store as ca_bundle for cert pinning.
    #   c) Self-signed without CA:TRUE: PowerScale default X.509 v1 cert.
    #      Cannot be used as a CA bundle — set verify_ssl: false.
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
        # (b) Self-signed v3 CA cert — use for cert pinning
        ok "Cluster certificate saved to vault/${CLUSTER_NAME}_cert.pem (CA:TRUE — cert pinning enabled)"
        CLUSTER_CA_BUNDLE="/app/vault/${CLUSTER_NAME}_cert.pem"
        if grep -q "^    ca_bundle:" "$VAULT_FILE" 2>/dev/null; then
            sed -i "s|^    ca_bundle:.*|    ca_bundle: ${CLUSTER_CA_BUNDLE}|" "$VAULT_FILE"
        else
            sed -i "/^    verify_ssl:/a\\    ca_bundle: ${CLUSTER_CA_BUNDLE}" "$VAULT_FILE"
        fi
    elif [[ "$IS_SELF_SIGNED" == false && "$CERT_EXTRACTED" == true ]]; then
        # (a) CA-signed cert — keep verify_ssl: true, use system CA store
        rm -f "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" 2>/dev/null || true
        ok "Cluster has a CA-signed certificate — SSL verification enabled using system CA store."
    else
        # (c) Self-signed without CA:TRUE (PowerScale v1 default) or extraction failed
        rm -f "${VAULT_DIR}/${CLUSTER_NAME}_cert.pem" 2>/dev/null || true
        if [[ "$CERT_EXTRACTED" == true ]]; then
            warn "Cluster cert is X.509 v1 self-signed (no CA:TRUE) — typical for PowerScale default certs."
        else
            warn "Could not extract cluster certificate."
        fi
        warn "Setting verify_ssl: false in vault.yml — SSL certificate will not be verified."
        sed -i "s/^    verify_ssl:.*/    verify_ssl: false/" "$VAULT_FILE"
    fi
fi

# ---------------------------------------------------------------------------
# Encrypt vault.yml using VaultLib Python API inside the built image.
#
# We read the plaintext /app/vault/vault.yml (via the directory bind mount),
# encrypt it in-memory with VaultLib, and write to stdout. On the host we
# redirect stdout to a temp file and then rename it atomically.
#
# The vault password is passed directly (never stored on disk).
# ---------------------------------------------------------------------------
if [[ "$SKIP_SETUP" == false ]]; then
    info "Encrypting vault.yml..."
    VAULT_TMP="${VAULT_FILE}.tmp"
    $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" run --rm isi_mcp \
        python3 -c "
import sys
from ansible.parsing.vault import VaultLib, VaultSecret
# Read password from stdin (passed via environment via -e)
password = sys.argv[1].encode() if len(sys.argv) > 1 else b''
if not password:
    print('ERROR: Vault password required', file=sys.stderr)
    sys.exit(1)
vault = VaultLib([('default', VaultSecret(password))])
plaintext = open('/app/vault/vault.yml', 'rb').read()
encrypted = vault.encrypt(plaintext)
sys.stdout.buffer.write(encrypted if isinstance(encrypted, bytes) else encrypted.encode())
" "$VAULT_PASS" > "${VAULT_TMP}"
    mv "${VAULT_TMP}" "${VAULT_FILE}"
    chmod 600 "${VAULT_FILE}"
    ok "vault.yml encrypted"
fi

# ---------------------------------------------------------------------------
# Print connection instructions (before starting so they're visible above logs)
# ---------------------------------------------------------------------------
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ok "Setup complete! Connecting to: ${VAULT_HOST}:${CLUSTER_PORT} as ${CLUSTER_USER}"
echo ""
info "MCP server will be available at: https://localhost/mcp (via nginx)"
info "  Direct backend (no TLS):      http://localhost:8000 (not exposed by default)"
echo ""
warn "IMPORTANT: Save your vault password in a secure location!"
warn "You will need it to restart the server later."
echo ""
info "Connect your LLM client:"
echo "  Claude Code: claude mcp add --transport http powerscale https://localhost/mcp"
echo "  Claude Desktop: Add to claude_desktop_config.json:"
echo '    { "mcpServers": { "powerscale": { "url": "https://localhost/mcp" } } }'
echo "  Cursor/Windsurf SSE endpoint: https://localhost/sse"
echo ""
warn "Note: Self-signed certs require clients to accept untrusted certificates."
echo ""
info "To restart the server later (requires vault password):"
echo "  read -s -p 'Vault password: ' VAULT_PASSWORD && export VAULT_PASSWORD"
if [[ -n "$COMPOSE_PROFILES" ]]; then
echo "  read -s -p 'Keycloak DB password: ' KEYCLOAK_DB_PASSWORD && export KEYCLOAK_DB_PASSWORD"
echo "  read -s -p 'Keycloak admin password: ' KEYCLOAK_ADMIN_PASSWORD && export KEYCLOAK_ADMIN_PASSWORD"
fi
echo "  $COMPOSE_CMD -f ${SCRIPT_DIR}/docker-compose.yml $COMPOSE_PROFILES up -d"
echo ""
info "To add or edit clusters later:"
echo "  $COMPOSE_CMD -f ${SCRIPT_DIR}/docker-compose.yml exec isi_mcp ansible-vault edit /app/vault/vault.yml"
echo ""
info "To stop the server:"
echo "  $COMPOSE_CMD -f ${SCRIPT_DIR}/docker-compose.yml down"
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
# Start the server.
#
# Stop any existing container first. docker-compose v1 (<=1.29.2) has a bug
# where recreating a container reads 'ContainerConfig' from the image manifest,
# which was removed in newer Docker Engine versions, causing a KeyError. Stopping
# the old container before 'up' avoids the recreate path entirely.
# ---------------------------------------------------------------------------
info "Stopping any existing container..."
$COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" $COMPOSE_PROFILES down 2>/dev/null || true

info "Starting MCP server in background..."
VAULT_PASSWORD="$VAULT_PASS" $COMPOSE_CMD -f "${SCRIPT_DIR}/docker-compose.yml" $COMPOSE_PROFILES up -d
ok "Server started. View logs: $COMPOSE_CMD -f ${SCRIPT_DIR}/docker-compose.yml logs -f"
