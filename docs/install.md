# Installation and Setup (Docker)

> **For Kubernetes deployment**, see **[Kubernetes Deployment Guide](kubernetes.md)** instead.
>
> This guide covers Docker and Docker Compose deployment only.

## Quick Start

### 1. Prerequisites

- **Docker Compose**: This deployment requires the standalone `docker-compose` tool (v1.x), **not** the `docker compose` plugin (v2).
  - Check your version: `docker-compose --version` (should show `docker-compose` not `Docker Compose`)
  - Install standalone version from https://docs.docker.com/compose/install/standalone/ if needed

### 2. Clone the Repository

```bash
git clone <repo-url>
cd isi_mcp_demo
```

### 3. Run Setup

```bash
./setup.sh
```

The script prompts for your cluster host, credentials, and a vault encryption password, then:
- Creates `vault.yml` with your cluster credentials
- Encrypts the vault using Ansible inside the Docker image (no Ansible needed on your host)
- The vault password is never stored on disk — provide it only at runtime via the `VAULT_PASSWORD` environment variable
- Builds the Docker image and starts the MCP server

**Non-interactive (for scripting — use env vars to avoid shell history):**

```bash
export VAULT_PASSWORD=$(read -s -p 'Vault password: ' pwd && echo $pwd)
./setup.sh --host 192.168.0.33 --user root --pass secret
```

**Start in the foreground (for debugging):**

```bash
export VAULT_PASSWORD=$(read -s -p 'Vault password: ' pwd && echo $pwd)
./setup.sh --host 192.168.0.33 --pass secret --detach false
```

By default, `setup.sh` starts the MCP server in the background. Use `--detach false` or omit the flag to run in foreground instead.

The setup script also generates self-signed TLS certificates (in `nginx/certs/`) for the nginx reverse proxy. The MCP server will be available at `https://localhost/mcp` via nginx.

**Optionally set debug mode** by exporting `DEBUG=1` before running setup.

**Optionally enable IaC mode** by exporting `IAC_MODE=true` before running setup (see [IaC Workflow Integration](#iac-workflow-integration) below).

## Running the Server

After initial setup, use `start.sh` and `stop.sh` to manage the server. These scripts read `config/isi_mcp.env` to detect whether authentication is enabled, prompt for the required passwords, and handle the `--profile auth` flag automatically.

**Starting the server:**

```bash
./start.sh
```

Prompts for the vault password (and Keycloak passwords if `AUTH_ENABLED=true`) then starts all services in the background.

**Stopping the server:**

```bash
./stop.sh
```

**Tearing down and restarting (e.g. after a config change):**

```bash
./start.sh --reboot
```

Stops existing containers, then starts fresh. Volumes (Keycloak database, playbooks) are preserved.

**Removing all data (volumes included):**

```bash
./stop.sh --clean
```

> **Warning**: `--clean` deletes the Keycloak database volume. All users, clients, and realm configuration will be lost and re-imported from `keycloak/realm-export.json` on next start.

**Viewing logs:**

```bash
docker-compose logs -f isi_mcp
docker-compose logs -f nginx
docker-compose logs -f keycloak
```

## Configuration Files

Non-secret configuration is stored as flat `KEY=VALUE` files in the top-level `config/` directory. These files are committed to the repository and loaded by Docker Compose at startup via `env_file:`.

| File | Service | Purpose |
|---|---|---|
| `config/isi_mcp.env` | isi_mcp | App settings: `VAULT_FILE`, `AUTH_ENABLED`, `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `MCP_PUBLIC_URL` |
| `config/keycloak.env` | keycloak | Non-secret Keycloak settings: DB connection, hostname, HTTP port, admin username |
| `config/keycloak-db.env` | keycloak-db | Non-secret Postgres settings: `POSTGRES_DB`, `POSTGRES_USER` |

**Secrets** (`VAULT_PASSWORD`, `KEYCLOAK_DB_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`) are never stored in files — they are passed as environment variables at startup and held in memory only.

**Host-level toggles** (`DEBUG`, `ENABLE_ALL_TOOLS`, `IAC_MODE`) remain in the `environment:` section of `docker-compose.yml` because they are typically passed from the host shell rather than set persistently.

To change a setting, edit the appropriate `.env` file and restart. For example, to set the public URL for a production host:

```bash
# Edit config/isi_mcp.env
MCP_PUBLIC_URL=https://powerscale-mcp.example.com

./start.sh
```

## TLS Certificates

The setup script generates self-signed certificates automatically on first run. The `start.sh` script also checks for missing certificates and auto-generates them if needed.

For full details on all certificate options — including auto-generated development certificates, bring-your-own CA-signed certificates, certificate rotation, and client trust configuration — see **[TLS Certificate Guide](tls.md)**.

**Quick reference:**

| Task | Command |
|---|---|
| Regenerate dev certs (e.g. after hostname change) | `nginx/generate-certs.sh --force && docker-compose restart nginx` |
| Install a CA-signed cert | Copy `server.crt` and `server.key` into `nginx/certs/`, then `docker-compose restart nginx` |
| Trust CA in Node.js / Claude Code | `export NODE_EXTRA_CA_CERTS=/path/to/nginx/certs/ca.crt` |

## Endpoints

| Endpoint | Protocol | Description |
|---|---|---|
| `https://localhost/mcp` | Streamable HTTP | Primary MCP endpoint (via nginx) |
| `https://localhost/sse` | SSE | Legacy SSE endpoint (via nginx) |
| `https://localhost/health` | HTTP GET | Health check (returns JSON) |
| `https://localhost/version` | HTTP GET | Server version (returns JSON) |
| `https://localhost/auth/` | HTTP | Keycloak IdP (OAuth flows, JWKS, admin console — when auth is enabled) |

## Managing Vault Credentials

Credentials are stored in an Ansible Vault encrypted file (`vault.yml`). The vault is excluded from git via `.gitignore`.

**Edit or add clusters after initial setup:**

First, view the encrypted vault to see the current structure:

```bash
echo -n 'your-vault-password' | docker-compose run --rm isi_mcp ansible-vault view /app/vault/vault.yml
```

Then edit it:

```bash
echo -n 'your-vault-password' | docker-compose run --rm isi_mcp ansible-vault edit /app/vault/vault.yml
```

After making changes, either restart the server:

```bash
VAULT_PASSWORD='your-vault-password' docker-compose restart
```

Or use the `powerscale_cluster_select` MCP tool with `reload_vault=true` to reload without restarting.

### Changing the Vault Password

To rekey the vault (change its encryption password), use Docker to run the ansible-vault rekey command:

```bash
# Prompt for old password and new password (never stored on disk)
export OLD_VAULT_PASSWORD=$(read -s -p 'Enter current vault password: ' pwd && echo $pwd)
export NEW_VAULT_PASSWORD=$(read -s -p 'Enter new vault password: ' pwd && echo $pwd)
docker-compose run --rm -e VAULT_PASSWORD="$OLD_VAULT_PASSWORD" isi_mcp \
  ansible-vault rekey /app/vault/vault.yml --vault-password-file /dev/stdin <<< "$NEW_VAULT_PASSWORD"
unset OLD_VAULT_PASSWORD NEW_VAULT_PASSWORD
```

Then restart the server with the new vault password:

```bash
export VAULT_PASSWORD=$(read -s -p 'Enter your password: ' pwd && echo $pwd)
docker-compose restart
```

## Enabling Authentication (Optional)

By default the server runs without client authentication. The steps below add OAuth 2.1 / OIDC authentication backed by **Keycloak**, a self-hosted identity provider. Once enabled, every MCP client must authenticate before invoking any tool. MCP-spec-compliant clients (Claude Code, Cursor) handle the OAuth flow automatically via browser login — no manual token management is needed.

For a full explanation of the authentication architecture and security model, see [Security — Client Authentication](security.md#client-authentication-oauth-21--oidc).

### Prerequisites

- Docker Compose (same as the base install)
- The Keycloak container and its PostgreSQL database are included in `docker-compose.yml` under the `auth` profile — no extra software required

### Step 1: Enable Auth in config/isi_mcp.env

Open `config/isi_mcp.env` and change the `AUTH_ENABLED` line:

```
AUTH_ENABLED=true
```

That's the only file change needed. Passwords are never stored in files.

### Step 2: Run Setup

```bash
./setup.sh
```

`setup.sh` reads `config/isi_mcp.env`, detects `AUTH_ENABLED=true`, and prompts for the two Keycloak passwords in addition to the usual cluster credentials and vault password.

For non-interactive setup with auth, pass all three passwords via environment variables:

```bash
export VAULT_PASSWORD=$(read -s -p 'Vault password: ' pwd && echo $pwd)
export KEYCLOAK_DB_PASSWORD=$(read -s -p 'Keycloak DB password: ' pwd && echo $pwd)
export KEYCLOAK_ADMIN_PASSWORD=$(read -s -p 'Keycloak admin password: ' pwd && echo $pwd)
./setup.sh --host 192.168.0.33 --user root --pass secret
```

All passwords are handled in memory only — nothing is written to disk. `setup.sh` automatically adds `--profile auth` to start the Keycloak services.

**Subsequent starts** (vault already exists):

```bash
./start.sh
```

`start.sh` detects `AUTH_ENABLED=true` in `config/isi_mcp.env` and prompts for all three passwords automatically.

> **Tip**: A password manager or secrets manager (e.g., `pass`, Vault, AWS Secrets Manager) can pre-export the password variables before calling `start.sh` to avoid typing them each time.

On first start, Keycloak initialises its database and imports the pre-configured `powerscale` realm from `keycloak/realm-export.json` (this takes ~30–60 seconds).

### Step 3: Verify Keycloak Is Ready

```bash
# Check all services are healthy
docker-compose ps

# Confirm Keycloak OIDC discovery endpoint is responding
curl -sk https://localhost/auth/realms/powerscale/.well-known/openid-configuration | jq .issuer
# Expected: "http://keycloak:8080/realms/powerscale"

# Confirm MCP server advertises the auth server (RFC 9728)
curl -sk https://localhost/mcp/.well-known/oauth-protected-resource | jq .
# Expected: { "resource": "...", "authorization_servers": [...] }

# Confirm unauthenticated requests are rejected
curl -sk -o /dev/null -w "%{http_code}" -X POST https://localhost/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
# Expected: 401

# Confirm health check remains unauthenticated
curl -sk https://localhost/health
# Expected: {"status":"ok","tools_loaded":...}
```

### Step 4: Add Users

Create at least one user before configuring MCP clients — you'll need credentials to log in when the browser authentication prompt appears.

#### Local Users

In the Keycloak admin console (https://localhost/auth/admin/):

1. Select the **powerscale** realm
2. Go to **Users → Add user** → fill in username → **Save**
3. Go to the **Credentials** tab → **Set password** → disable "Temporary"
4. Go to the **Role mapping** tab → Assign exactly **one** of:
   - `mcp-read` — read-only access (health, capacity, quota queries, etc.)
   - `mcp-write` — read + write access to all domain tools (quota set, SMB/NFS create, etc.)
   - `mcp-admin` — full access including management tools (`powerscale_tools_toggle`, cluster add/remove, etc.)
   > Keycloak composite roles automatically expand in the JWT: assigning `mcp-admin` grants `mcp-write` and `mcp-read` as well.

#### Active Directory / LDAP

1. Admin console → **User Federation → Add LDAP provider**
2. Set **Connection URL** (`ldap://dc.example.com:389` or `ldaps://...636`)
3. Set **Bind DN** and **Bind Credential** (service account), then click **Test connection** and **Test authentication**
4. Set **Users DN** to the OU containing your users (e.g. `OU=Users,DC=example,DC=com`)
5. Set **Username LDAP attribute** to `sAMAccountName`
6. **Save**, then click **Synchronize all users**
7. Assign roles to synced users or map AD groups to roles via a group-ldap-mapper

For LDAPS with a private CA, mount the AD CA cert into the Keycloak container and build a Java truststore — see `AUTH_PLAN.md` → Step 6 for commands.

#### Third-Party SSO (Google, Azure AD, Okta, etc.)

Admin console → **Identity Providers → Add provider → OpenID Connect v1.0** → enter the provider's discovery URL, client ID, and client secret.

### Step 5: Configure MCP Clients

#### Claude Code (automatic OAuth flow — recommended)

Claude Code discovers the auth server automatically. When you first invoke the server, it opens a browser window to the Keycloak login page — log in with the username and password you created in Step 4.

```bash
# Register the server — auth is auto-discovered
claude mcp add --transport http powerscale https://localhost/mcp

# Trigger any MCP call (e.g. open /mcp in Claude Code).
# Claude Code detects the 401, opens a browser login window to Keycloak.
# Log in with the user you created in Step 4.
# Tokens are stored and refreshed automatically.
```

#### Service Accounts / CI-CD (Client Credentials grant)

Use the `powerscale-m2m` confidential client. Copy the client secret from the Keycloak admin console (https://localhost/auth/admin/ → Clients → powerscale-m2m → Credentials), then:

```bash
TOKEN=$(curl -sk -X POST \
  https://localhost/auth/realms/powerscale/protocol/openid-connect/token \
  -d "grant_type=client_credentials" \
  -d "client_id=powerscale-m2m" \
  -d "client_secret=<secret>" \
  | jq -r .access_token)
```

Configure `.mcp.json`:

```json
{
  "mcpServers": {
    "powerscale": {
      "type": "http",
      "url": "https://localhost/mcp",
      "headers": {
        "Authorization": "Bearer ${MCP_TOKEN}"
      }
    }
  }
}
```

### Disabling Authentication

Change `AUTH_ENABLED` back to `false` in `config/isi_mcp.env`, then restart:

```bash
./start.sh --reboot
```

`start.sh` will no longer detect auth in `config/isi_mcp.env`, so it prompts only for the vault password and starts without the `auth` profile — Keycloak and its database will not start.

---

## IaC Workflow Integration

### IAC_MODE Environment Variable

By default, the MCP server executes Ansible playbooks immediately when a write tool is called. For environments that require change control, peer review, or automated testing before changes reach a production cluster, set `IAC_MODE=true`.

When `IAC_MODE` is enabled:
- Write tools **render** the Ansible playbook and write it to the `playbooks/` directory.
- The playbook is **not executed**. Ansible is never invoked.
- The MCP tool returns a response telling the user that the playbook has been generated and must be run through the external IaC workflow.

The `playbooks/` directory is already bind-mounted to the host (`./playbooks` in `docker-compose.yml`), so generated playbooks are immediately accessible outside the container.

**Starting the server in IaC mode:**

```bash
export VAULT_PASSWORD=$(read -s -p 'Enter your password: ' pwd && echo $pwd)
export IAC_MODE=true
docker-compose up -d
```

Or set it permanently in a `.env` file at the repository root:

```bash
echo "IAC_MODE=true" >> .env
```

> **Security note**: Rendered playbooks contain connection parameters (host, port, SSL setting) but never credentials. API credentials are injected by `ansible-runner` at execution time via `extravars` and never written to disk.

### Integrating with a Git-based IaC Workflow

The high-level pattern is:

1. An LLM client calls a write tool via the MCP server (e.g., create an SMB share).
2. The MCP server generates the Ansible playbook in `./playbooks/` and returns the file path to the LLM.
3. An external process monitors `./playbooks/` (via a file-watcher, cron job, or webhook trigger), picks up the new file, and opens a pull request in your IaC Git repository.
4. Automated tests (syntax check, dry-run, policy lint) run in CI against the PR.
5. A human reviewer approves the PR.
6. The merge pipeline executes the playbook against the cluster using `ansible-runner` or `ansible-playbook` with the appropriate vault credentials.

**Example directory layout for the IaC repository:**

```
infra-iac/
├── playbooks/          ← rendered playbooks from the MCP server (bind mount or rsync target)
├── tests/
│   └── syntax_check.sh ← runs ansible-playbook --syntax-check on new playbooks
├── .github/
│   └── workflows/
│       └── playbook-pr.yml  ← CI: lint → dry-run → approval gate → apply
└── README.md
```

**Key considerations:**

- Keep `IAC_MODE=true` on any MCP server instance that touches production clusters without direct execution authority.
- Use `IAC_MODE=false` (the default) for development or staging clusters where the LLM can apply changes immediately.
- The `playbooks/` directory should be excluded from the MCP server's own Git repository (it already is via `.gitignore`) and tracked separately in your IaC repo.
- Playbook filenames include a timestamp and unique ID (`{operation}_{YYYYMMDD_HHMMSS}_{host}_{id}.yml`), making it straightforward to trace a playbook back to the LLM session that created it.
