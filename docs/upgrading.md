# Upgrading

This guide explains how to check your installed version, compare it against the latest release, and upgrade.

## Checking Your Current Version

**From the VERSION file on your local system:**

```bash
cat VERSION
```

**Via the running server's HTTP endpoint:**

```bash
curl -sk https://localhost/version
```

Both return the same version string (e.g. `1.0.54`).

## Checking for Updates

Fetch the latest metadata from the repository without changing your local files:

```bash
git fetch origin
```

Then compare your local VERSION against the remote:

```bash
# Local version
cat VERSION

# Latest version on the remote main branch
git show origin/master:VERSION
```

To see what commits are in the remote that are not yet in your local copy:

```bash
git log HEAD..origin/master --oneline
```

## Upgrading

> Startup after an upgrade typically takes **up to 60 seconds** while Docker rebuilds the image and the MCP server initialises.

### Standard upgrade (recommended)

1. **Stop the running services:**

   ```bash
   ./stop.sh
   ```

2. **Pull the latest changes:**

   ```bash
   git pull
   ```

3. **Check for new settings in the sample config** (optional but recommended):

   A `git pull` may add new settings to `config/isi_mcp.env.sample`. Your local `config/isi_mcp.env` is never overwritten — compare the two and add any new settings you need:

   ```bash
   diff config/isi_mcp.env.sample config/isi_mcp.env
   ```

4. **Start the services** (rebuilds the Docker image automatically):

   ```bash
   ./start.sh
   ```

   `start.sh` prompts for the vault password (and Keycloak passwords if `AUTH_ENABLED=true`), then rebuilds and starts all containers.

### Upgrade with a clean restart

Use this if a configuration change requires containers to be re-created (e.g. a new `docker-compose.yml` volume or service definition):

```bash
./stop.sh
git pull
./start.sh --reboot
```

`--reboot` tears down the existing containers before starting fresh. Volumes (Keycloak database, generated playbooks) are preserved.

### Verifying the upgrade

After startup, confirm the server is running the new version:

```bash
# Check the server is healthy
curl -sk https://localhost/health

# Confirm the version
curl -sk https://localhost/version
```

## Notes

- **Vault credentials are never stored on disk.** You will always be prompted for the vault password on start.
- **`stop.sh --clean` is destructive** — it removes the Keycloak database volume and all generated playbooks. Do not use it for routine upgrades.
- **`config/*.env` files are excluded from git.** They are created from `config/*.env.sample` on first run of `setup.sh` and are never overwritten by a `git pull`. Your local settings (including `AUTH_ENABLED=true`) are preserved across upgrades.
- **`config/*.env.sample` files are tracked by git.** A pull may update them with new default settings. Use `diff` to compare against your live `.env` files after a pull.
- **`vault.yml` is excluded from git** (via `.gitignore`) and is never overwritten by a pull.
