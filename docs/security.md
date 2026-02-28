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

### Cluster-to-Server TLS

- Set `verify_ssl: false` only for clusters with self-signed certificates
- For production clusters, always use valid certificates and set `verify_ssl: true`
- Certificate verification is per-cluster and configured in the vault

### Client-to-Server TLS (Nginx Reverse Proxy)

The server ships with an nginx reverse proxy that terminates TLS for all client connections:

- Self-signed certificates are generated automatically by `./setup.sh` and `./nginx/generate-certs.sh`
- Certificates are stored in `nginx/certs/` (gitignored — never committed)
- For production, replace with certificates from your CA
- nginx enforces TLS 1.2+ with strong cipher suites
- HTTP requests are automatically redirected to HTTPS (301)

### Security Headers

Nginx adds the following security headers to all responses:

| Header | Value |
|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

### Rate Limiting

Nginx rate-limits requests to the MCP endpoints at 10 requests/second per client IP with a burst allowance of 20. The `/health` endpoint is excluded from rate limiting. This protects the PowerScale cluster from excessive API calls.

## Network Security

The MCP server itself does not implement authentication. The nginx reverse proxy provides the first layer of defense. In production environments:

- Replace self-signed certificates with CA-signed certificates
- Add authentication at the nginx layer (OAuth, mTLS, API keys, etc.)
- Restrict access to trusted networks only via firewall rules
- Use the rate limiting configuration to prevent abuse
- Monitor nginx access logs for suspicious activity

## Playbook Audit Trail

- All rendered Ansible playbooks are saved to the `playbooks/` directory for audit trail purposes
- Rendered playbooks contain resource parameters but NOT actual credentials
- Credentials are injected at runtime via ansible-runner's extravars mechanism, keeping them out of saved files
- When running multiple instances, playbook filenames include the container hostname to prevent collisions

## Recommended Practices

1. **Keep write tools disabled** until needed — enable for the task, then disable again to minimize risk
2. **Rotate vault passwords regularly** using the vault rekey command
3. **Use strong vault passwords** with sufficient entropy
4. **Restrict access to vault.yml** file permissions (read-only by server user)
5. **Replace self-signed certs** with CA-signed certificates for production
6. **Log MCP operations** via nginx access logs for compliance auditing
7. **Monitor cluster access** for suspicious activity patterns
8. **Keep the server updated** with security patches for FastMCP and dependencies
