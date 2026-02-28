# Security

## Credential Management

- Cluster credentials are stored in an Ansible Vault encrypted file — never in plaintext config files
- The encrypted vault (`vault.yml`) is excluded from git via `.gitignore`
- The vault password is never stored on disk — provide it only at runtime via the `VAULT_PASSWORD` environment variable
- Credentials are decrypted in memory and cached by the VaultManager singleton for the duration of the server process

## Write Tools Disabled by Default

The server ships in **read-only mode** — all 51 write tools are disabled at startup. This safe-by-default posture means:

- A newly deployed server can only query cluster state, not modify it
- Write capabilities must be explicitly enabled using `powerscale_tools_toggle` before the LLM can make changes
- Enabled state persists in `config/tools.json`; re-disable write tools after a task is complete if desired

To enable all write tools: `powerscale_tools_toggle(names=["write"], action="enable")`

To return to read-only mode: `powerscale_tools_toggle(names=["write"], action="disable")`

## Mutating Operations

All mutating operations (create, delete, modify, set) include safety prompts in their tool descriptions, instructing the LLM to confirm with the user before executing. The MCP protocol allows the LLM client to prompt for confirmation before calling these tools.

## SSL/TLS Configuration

- Set `verify_ssl: false` only for clusters with self-signed certificates
- For production clusters, always use valid certificates and set `verify_ssl: true`
- Certificate verification is per-cluster and configured in the vault

## Network Security

The MCP server itself does not implement authentication. In production environments:

- Secure the HTTP endpoint at the network level (firewall rules, private networks)
- Run behind a reverse proxy with authentication (OAuth, mTLS, etc.)
- Restrict access to trusted networks only
- Use HTTPS for client connections to the reverse proxy

## Playbook Audit Trail

- All rendered Ansible playbooks are saved to the `playbooks/` directory for audit trail purposes
- Rendered playbooks contain resource parameters but NOT actual credentials
- Credentials are injected at runtime via ansible-runner's extravars mechanism, keeping them out of saved files

## Recommended Practices

1. **Keep write tools disabled** until needed — enable for the task, then disable again to minimize risk
2. **Rotate vault passwords regularly** using the vault rekey command
3. **Use strong vault passwords** with sufficient entropy
4. **Restrict access to vault.yml** file permissions (read-only by server user)
5. **Log MCP operations** at the reverse proxy level for compliance auditing
6. **Monitor cluster access** for suspicious activity patterns
7. **Keep the server updated** with security patches for FastMCP and dependencies
