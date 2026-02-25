# Installation and Setup

## Quick Start

### 1. Clone the Repository

```bash
git clone <repo-url>
cd isi_mcp_demo
```

### 2. Run Setup

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

The MCP server will be available at `http://localhost:8000`.

**Optionally set debug mode** by exporting `DEBUG=1` before running setup.

## Running the Server

After initial setup, you can start, stop, and restart the server as needed.

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

**Viewing logs:**

```bash
docker-compose logs -f isi_mcp
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
