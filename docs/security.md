# Security

## Credential Management

- Cluster credentials are stored in an Ansible Vault encrypted file — never in plaintext config files
- The encrypted vault (`vault.yml`) is excluded from git via `.gitignore`
- The vault password is never stored on disk — provide it only at runtime via the `VAULT_PASSWORD` environment variable
- Credentials are decrypted in memory and cached by the VaultManager singleton for the duration of the server process

## Access Control

All 212 tools ship enabled by default. There are two approaches to controlling tool access:

### Without Authentication (`AUTH_ENABLED=false`)

Use `config/tools.json` and the `powerscale_tools_toggle` management tool to enable or disable tools by group, mode, or individual name. This is suitable for single-user or trusted-network deployments. For example, disable all write tools to restrict the server to read-only operations, or disable specific groups to limit scope.

### With Authentication (`AUTH_ENABLED=true`) — Recommended for Production

**Keycloak RBAC** provides per-user access control with two dimensions:

- **Mode roles**: `mcp-read` (read tools), `mcp-write` (write tools, includes read), `mcp-admin` (management tools, includes write)
- **Group roles**: `mcp-group-{name}` roles restrict visibility to specific tool groups (e.g., `mcp-group-quotas`, `mcp-group-smb`). If a user has no group roles, all groups are accessible (backward compatible). `mcp-admin` always bypasses group filtering
- Users only see and can call tools matching both their mode and group roles
- 39 group roles are available (one per tool group, excluding `management`)

Both mechanisms can be used together — tool toggle controls which tools are registered with the server, while RBAC controls which registered tools each authenticated user can see and call.

Four **management write tools** (`powerscale_tools_toggle`, `powerscale_cluster_select`, `powerscale_cluster_add`, `powerscale_cluster_remove`) cannot be disabled and are always available

## Mutating Operations

All mutating operations (create, delete, modify, set) include safety prompts in their tool descriptions, instructing the LLM to confirm with the user before executing. The MCP protocol allows the LLM client to prompt for confirmation before calling these tools.

## SSL/TLS Configuration

### Cluster-to-Server TLS

The MCP server verifies TLS certificates for all cluster connections. By default, `verify_ssl: true` — the server validates the cluster's certificate against the system certificate store.

For **self-signed certificates** (common on PowerScale clusters), the server supports per-cluster CA bundle pinning via the `ca_bundle` field:

```yaml
clusters:
  my_cluster:
    host: "https://192.168.0.33"
    port: 8080
    username: root
    password: ...
    verify_ssl: true
    ca_bundle: /app/vault/my_cluster_cert.pem  # Path to cluster's self-signed cert (container path)
```

The `ca_bundle` field takes precedence — when present, the server validates the cluster certificate specifically against this CA bundle rather than the system certificate store.

**Automatic extraction (recommended):**
- `./setup.sh` automatically extracts the cluster's TLS certificate during initial setup and stores it in the vault directory
- No manual steps required — the certificate is extracted inside the container and referenced in `vault.yml`
- Transparent to the user — just run `./setup.sh` as normal

**Manual refresh after cluster certificate rotation:**
- If the cluster's certificate changes (e.g., re-keyed or renewed), re-run `./setup.sh` to extract and update the `ca_bundle`
- Alternatively, use the `powerscale_cluster_add` management tool at runtime to update the cluster and extract the new certificate

**For CA-signed certificates (production):**
- If your cluster uses a certificate signed by your corporate CA, omit the `ca_bundle` field and keep `verify_ssl: true`
- The certificate will be validated against the system certificate store (assuming your CA root is installed in the container)

**For development/testing only:**
- Set `verify_ssl: false` to disable all certificate verification (exposes you to MITM attacks — only for isolated test networks)

### Client-to-Server TLS (Nginx Reverse Proxy)

The server ships with an nginx reverse proxy that terminates TLS for all client connections:

- `./setup.sh` and `./nginx/generate-certs.sh` generate a **local CA** (`ca.crt`) and a **server certificate** (`server.crt`) signed by that CA
- Certificates are stored in `nginx/certs/` (gitignored — never committed)
- Clients must trust `ca.crt` (not `server.crt`) — see [Client Integration](clients.md) for instructions. Node.js-based clients (Claude Code, VSCode extensions) require `NODE_EXTRA_CA_CERTS` pointing to `ca.crt`
- For production, replace with certificates from your CA — clients will trust them automatically
- nginx enforces TLS 1.2+ with strong cipher suites
- HTTP requests are automatically redirected to HTTPS (301)
- For step-by-step procedures (regeneration, bring-your-own cert, rotation, client trust setup), see **[TLS Certificate Guide](tls.md)**

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

## Client Authentication (OAuth 2.1 / OIDC)

By default the server runs without client authentication (suitable for local or private-network deployments). For environments exposed beyond a trusted network, **FastMCP-native OAuth 2.1 authentication** can be enabled to require a valid identity before any MCP tool can be invoked.

### Architecture

```
MCP Client (Claude Code, Cursor, etc.)
  │
  │  1. GET /.well-known/oauth-protected-resource
  │     ← { authorization_servers: ["https://<host>/auth/realms/powerscale"] }
  │
  │  2. OAuth 2.1 + PKCE flow (browser popup for interactive clients)
  │     or Client Credentials grant (for service accounts / CI-CD)
  │     ← access_token  (JWT signed by Keycloak)
  │
  │  3. Authorization: Bearer <jwt>  (every request)
  │
  ▼  HTTPS :443
nginx  ─  TLS termination + rate limiting only  (no auth logic)
  │
  ▼
isi_mcp :8000
  FastMCP  auth = RemoteAuthProvider + JWTVerifier
  ├── Validates JWT signature via Keycloak JWKS endpoint
  ├── Checks issuer, audience, and token expiry
  ├── Extracts user identity from token claims
  └── Serves /.well-known/oauth-protected-resource for client auto-discovery

  ▼  /auth/  (proxied by nginx)
Keycloak :8080  ─  Identity Provider
  ├── Local users (admin-managed)
  ├── Active Directory / LDAP federation
  └── Third-party SSO (Google, Azure AD, Okta, etc.)
```

### How It Works

1. **Discovery**: MCP clients fetch `/.well-known/oauth-protected-resource` to learn which authorization server to use. FastMCP serves this endpoint automatically when auth is configured — no client-side setup required.
2. **Login flow**: Interactive clients (Claude Code, Cursor) open a browser window for the user to authenticate against Keycloak. The OAuth 2.1 + PKCE flow completes and an access token is stored in the client's credential store.
3. **Token validation**: Every MCP request must carry a valid `Authorization: Bearer <jwt>` header. FastMCP validates the JWT signature using Keycloak's JWKS endpoint, then checks the issuer, audience, and expiry fields.
4. **Token refresh**: MCP clients handle refresh automatically per the MCP specification — users do not need to re-authenticate until the session expires.
5. **Service accounts**: Automated workflows and CI/CD pipelines use the Client Credentials grant (no browser required) via the `powerscale-m2m` confidential client.

### Identity Sources

Keycloak supports multiple identity sources that can be active simultaneously:

| Source | Notes |
|---|---|
| **Local users** | Created directly in Keycloak admin console |
| **Active Directory / LDAP** | User Federation — Keycloak binds to AD and syncs users/groups |
| **OIDC SSO** | Identity Brokering — Google, Azure AD/Entra, Okta, GitHub, etc. |

See [Installation Guide — Enabling Authentication](install.md#enabling-authentication-optional) for setup steps.

### Roles

Three realm roles are defined in the pre-configured `powerscale` realm:

| Role | Access |
|---|---|
| `mcp-read` | Read-only (non-destructive) tools |
| `mcp-write` | All domain tools — read and write (includes `mcp-read` via Keycloak composite role) |
| `mcp-admin` | All tools including management tools (`powerscale_tools_toggle`, cluster management, etc.) — includes `mcp-write` |

Roles are **enforced by the MCP server** via a FastMCP middleware layer (`RoleEnforcementMiddleware` in `server.py`). Every tool call is checked against the caller's JWT `realm_access.roles` claim before execution. Unauthenticated calls are rejected at the HTTP layer (401) before they reach the role check.

The tool list returned to a client is also filtered to only include tools the caller is permitted to invoke — a user with `mcp-read` will not see write or management tools in their `tools/list` response.

### Token Security

- Access tokens expire after **15 minutes** (configurable in Keycloak realm settings)
- Refresh sessions expire after **8 hours**
- The `powerscale-mcp` client is public (no client secret); PKCE is enforced to prevent authorization code interception
- The `powerscale-m2m` client is confidential — store its client secret securely (e.g., in a secrets manager, not in source control)

## Network Security

In production environments:

- Replace self-signed certificates with CA-signed certificates
- Enable `AUTH_ENABLED=true` in `config/isi_mcp.env` to require authenticated access (see above)
- Restrict access to trusted networks via firewall rules even when auth is enabled
- Use the rate limiting configuration to prevent abuse
- Monitor nginx access logs for suspicious activity

## Playbook Audit Trail

- All rendered Ansible playbooks are saved to the `playbooks/` directory for audit trail purposes
- Rendered playbooks contain resource parameters and configuration but **never** actual credentials
- **Cluster API credentials** (username, password) are injected at runtime via ansible-runner's `extravars` mechanism
- **User account passwords** are also injected via `extravars`, using `{{ user_password }}` placeholders in templates
- This pattern ensures sensitive values never appear in the audit trail — only placeholders that are replaced at execution time
- When running multiple instances, playbook filenames include the container hostname to prevent collisions

## Recommended Practices

1. **Enable authentication** (set `AUTH_ENABLED=true` in `config/isi_mcp.env`) for any deployment accessible beyond localhost or a trusted private network
2. **Assign least-privilege roles** — use group roles (e.g., `mcp-group-quotas`) to limit users to only the tool groups they need
3. **Rotate vault passwords regularly** using the vault rekey command
4. **Use strong vault passwords** with sufficient entropy
5. **Restrict access to vault.yml** file permissions (read-only by server user)
6. **Use per-cluster CA bundle pinning** for self-signed certificates (recommended) — `setup.sh` extracts them automatically. For production, replace with CA-signed certificates if possible
7. **Protect the Keycloak admin console** — restrict `/auth/admin/` by IP at the nginx layer if the server is internet-facing
8. **Rotate the `powerscale-m2m` client secret** periodically via Keycloak admin → Clients → Credentials → Regenerate
9. **Log MCP operations** via nginx access logs for compliance auditing
10. **Monitor cluster access** for suspicious activity patterns
11. **Keep the server updated** with security patches for FastMCP, Keycloak, and dependencies
