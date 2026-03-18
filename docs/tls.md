# TLS Certificate Guide

## Overview

The PowerScale MCP Server always requires TLS. nginx listens on port 443 (HTTPS) and redirects all plain-HTTP traffic to HTTPS. There is no HTTP-only mode.

There are two distinct TLS layers:

| Layer | What it secures | Configured where |
|---|---|---|
| **Client → MCP server** (nginx) | Traffic between LLM clients and the server | `nginx/certs/` |
| **MCP server → PowerScale cluster** (isilon SDK) | Traffic between the server and cluster APIs | `verify_ssl` in vault.yml |

This guide covers the **client → MCP server** layer only. For cluster-side TLS, see `verify_ssl` in `vault.yml` (set `false` only for clusters with self-signed certificates).

---

## Option 1: Auto-Generated Development Certificates (Default)

`setup.sh` and `start.sh` automatically generate a local CA and a server certificate when no certificates are present. This is the default for new deployments and requires no manual certificate management.

### Generated files

| File | Purpose | Permissions |
|---|---|---|
| `nginx/certs/ca.crt` | Local CA certificate | 644 |
| `nginx/certs/ca.key` | Local CA private key | 600 |
| `nginx/certs/server.crt` | Server certificate (signed by the local CA) | 644 |
| `nginx/certs/server.key` | Server private key | 600 |

All four files are gitignored — they are never committed to the repository.

### When certificates are generated

- **`setup.sh`**: always calls `nginx/generate-certs.sh` during initial setup (skips if already present).
- **`start.sh`**: checks for `server.crt` and `server.key` at startup and auto-generates if missing.

### SANs included

The script detects all local hostnames and IP addresses at generation time and includes them in the server certificate's Subject Alternative Names (SANs). If the server is later accessed from a new hostname or IP that was not present when the certificate was generated, regenerate the certificate.

### Regenerating development certificates

Regenerate after a hostname/IP change, or when the certificate is about to expire (development certs are valid for 365 days; the CA cert is valid for 3650 days):

```bash
nginx/generate-certs.sh --force
docker-compose restart nginx
```

`--force` overwrites existing certificates. Without it, the script exits immediately if certificates already exist.

To check certificate expiry:

```bash
openssl x509 -in nginx/certs/server.crt -noout -dates
```

---

## Option 2: Bring-Your-Own Certificate (Production)

For production deployments, replace the auto-generated certificates with certificates issued by your organisation's CA or a public CA. Clients trust CA-signed certificates automatically via their OS trust store — no `NODE_EXTRA_CA_CERTS` or manual trust step is needed.

### Certificate requirements

- **Format**: PEM (Base64-encoded DER with `-----BEGIN CERTIFICATE-----` headers)
- **Filename**: must be exactly `server.crt` and `server.key`
- **SANs**: the certificate must include a SAN matching every hostname and IP clients use to connect (e.g. `powerscale-mcp.example.com`, the server's LAN IP)
- **Key**: unencrypted private key (nginx does not support password-protected keys without additional configuration)

### Installation

1. Obtain a certificate and private key from your CA.

2. Copy the files into `nginx/certs/`:

   ```bash
   cp /path/to/your/server.crt nginx/certs/server.crt
   cp /path/to/your/server.key nginx/certs/server.key
   chmod 600 nginx/certs/server.key
   ```

3. Restart nginx to pick up the new certificate:

   ```bash
   docker-compose restart nginx
   ```

4. Verify the certificate is being served:

   ```bash
   openssl s_client -connect localhost:443 -servername localhost </dev/null 2>/dev/null \
       | openssl x509 -noout -subject -issuer -dates
   ```

nginx reads whatever files are in `nginx/certs/` at container start. No nginx configuration changes are required.

### Certificates with an intermediate chain

If your CA uses an intermediate certificate, concatenate the server certificate and intermediates into `server.crt` (server cert first, then intermediate, then root if needed):

```bash
cat server.crt intermediate.crt > nginx/certs/server.crt
```

nginx supports chained PEM certificates natively.

---

## Certificate Rotation

### Rotating certificates without downtime

1. Copy the new certificate and key into `nginx/certs/`:

   ```bash
   cp new-server.crt nginx/certs/server.crt
   cp new-server.key nginx/certs/server.key
   chmod 600 nginx/certs/server.key
   ```

2. Send nginx a reload signal (reloads configuration without dropping active connections):

   ```bash
   docker-compose exec nginx nginx -s reload
   ```

3. Verify the new certificate is live:

   ```bash
   openssl s_client -connect localhost:443 </dev/null 2>/dev/null | openssl x509 -noout -dates
   ```

### Rotation checklist

- [ ] New certificate is valid (`-dates` shows future `notAfter`)
- [ ] SANs cover all hostnames and IPs clients connect from
- [ ] Clients trust the new issuing CA (update `NODE_EXTRA_CA_CERTS` if the CA changed)
- [ ] nginx loaded the new certificate (`docker-compose logs nginx` shows no errors)

---

## Client Trust Configuration

### Why clients must trust the CA certificate

For auto-generated development certificates, clients must trust `ca.crt` — not `server.crt` directly. Trusting the CA means clients will continue to trust new server certificates signed by the same CA (e.g. after rotation or regeneration). Trusting `server.crt` directly would break on the next rotation.

For CA-signed production certificates, clients trust your CA automatically via the OS trust store — no manual action is needed.

### Claude Code / Node.js-based clients

Node.js does not use the OS trust store by default. Set `NODE_EXTRA_CA_CERTS` to point to `ca.crt`:

```bash
export NODE_EXTRA_CA_CERTS=/path/to/isi_mcp_demo/nginx/certs/ca.crt
```

Add this to your shell profile (`~/.bashrc`, `~/.zshrc`) to persist across sessions. The path must be the **absolute path** to `ca.crt` on the machine running the MCP client (not inside the Docker container).

### System trust store (Linux)

Installing into the system trust store makes all applications (including Claude Desktop) trust the certificate:

```bash
sudo cp nginx/certs/ca.crt /usr/local/share/ca-certificates/powerscale-mcp-ca.crt
sudo update-ca-certificates
```

### System trust store (macOS)

```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain \
    nginx/certs/ca.crt
```

### System trust store (Windows)

```powershell
certutil -addstore Root nginx\certs\ca.crt
```

For complete per-client instructions including Claude Desktop and Cursor, see **[Client Integration](clients.md)**.

---

## Troubleshooting

### "certificate verify failed" / "unable to verify the first certificate"

- Verify `NODE_EXTRA_CA_CERTS` points to `ca.crt` (not `server.crt`)
- Verify the path is the absolute path and the file is readable by the client process
- If the server was moved to a new hostname or IP since certs were generated, regenerate them: `nginx/generate-certs.sh --force`

### "depth zero self-signed certificate"

The server certificate is self-signed rather than CA-signed. The auto-generated certs use a two-tier CA structure; a "depth zero" error means the cert was placed there manually as a self-signed cert, not one generated by `generate-certs.sh`.

Fix: delete `nginx/certs/` and regenerate:

```bash
rm -rf nginx/certs/
nginx/generate-certs.sh
docker-compose restart nginx
```

### nginx fails to start / "no such file or directory" for cert

Certificates are missing from `nginx/certs/`. Run `nginx/generate-certs.sh` or copy your certificate files into place, then start the server.

### Certificate expired

Development server certificates expire after 365 days. Regenerate:

```bash
nginx/generate-certs.sh --force
docker-compose restart nginx
```

### SANs do not include the hostname I am connecting from

Regenerate the certificate on the server host so the new hostname or IP is detected automatically:

```bash
nginx/generate-certs.sh --force
docker-compose restart nginx
```

To add a specific hostname that `hostname -I` does not detect (e.g. a DNS alias), edit `nginx/generate-certs.sh` and append to the `SAN` variable before running:

```bash
SAN="${SAN},DNS:powerscale-mcp.example.com"
```

### Verifying the certificate nginx is currently serving

```bash
echo | openssl s_client -connect localhost:443 2>/dev/null \
    | openssl x509 -noout -text \
    | grep -A5 "Subject Alternative Name"
```
