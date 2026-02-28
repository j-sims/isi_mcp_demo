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

**Non-interactive (for scripting):**

```bash
./setup.sh --host 192.168.0.33 --user root --pass secret --vault-pass vaultkey123
```

**Start in the foreground (for debugging):**

```bash
./setup.sh --host 192.168.0.33 --pass secret --vault-pass vaultkey123 --nodetach
```

By default, `setup.sh` starts the MCP server in the background. Use `--nodetach` to run in foreground instead.

The setup script also generates self-signed TLS certificates (in `nginx/certs/`) for the nginx reverse proxy. The MCP server will be available at `https://localhost/mcp` via nginx.

**Optionally set debug mode** by exporting `DEBUG=1` before running setup.

## Running the Server

After initial setup, you can start, stop, and restart the server as needed. The stack includes an nginx reverse proxy that provides TLS termination, rate limiting, and security headers.

**Starting the server in the background:**

```bash
export VAULT_PASSWORD=$(read -s -p 'Enter your password: ' pwd && echo $pwd)
docker-compose up -d
```

**Starting the server in the foreground (for debugging):**

```bash
export VAULT_PASSWORD=$(read -s -p 'Enter your password: ' pwd && echo $pwd)
docker-compose up
```

Press `Ctrl+C` to stop.

**Scaling to multiple instances:**

```bash
export VAULT_PASSWORD=$(read -s -p 'Enter your password: ' pwd && echo $pwd)
docker-compose up -d --scale isi_mcp=3
```

Nginx load-balances across all instances using Docker DNS round-robin. The MCP server runs in stateless HTTP mode, so no sticky sessions are required.

**Viewing logs:**

```bash
docker-compose logs -f isi_mcp
docker-compose logs -f nginx
```

**Restarting the server:**

```bash
export VAULT_PASSWORD=$(read -s -p 'Enter your password: ' pwd && echo $pwd)
docker-compose restart
```

**Stopping the server:**

```bash
docker-compose down
```

## TLS Certificates

The setup script generates self-signed certificates automatically. To regenerate:

```bash
rm -rf nginx/certs/
./nginx/generate-certs.sh
docker-compose restart nginx
```

For production, replace `nginx/certs/server.crt` and `nginx/certs/server.key` with certificates from your CA. The certificate files are gitignored.

### Client Certificate Trust

MCP clients connecting to the server must trust the self-signed certificate. The certificate is generated on the **server host** (not inside the container) at `nginx/certs/server.crt`. See **[Client Integration](clients.md)** for step-by-step instructions to copy and trust the certificate on client machines.

## Endpoints

| Endpoint | Protocol | Description |
|---|---|---|
| `https://localhost/mcp` | Streamable HTTP | Primary MCP endpoint (via nginx) |
| `https://localhost/sse` | SSE | Legacy SSE endpoint (via nginx) |
| `https://localhost/health` | HTTP GET | Health check (returns JSON) |

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
