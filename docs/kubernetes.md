# Kubernetes Deployment Guide

This guide covers deploying the PowerScale MCP Server (`isi-mcp-server`) on Kubernetes,
with detailed instructions for local development using **minikube**.

---

## Overview

The MCP server runs as a single-container Deployment. Key resources:

| Resource | Type | Purpose |
|---|---|---|
| `isi-mcp` | Namespace | Isolates all server resources |
| `isi-mcp-tools` | ConfigMap | Baseline `tools.json` tool configuration |
| `isi-mcp-credentials` | Secret | Ansible Vault password (`VAULT_PASSWORD`) |
| `isi-mcp-vault` | Secret | Encrypted `vault.yml` cluster credentials |
| `isi-mcp` | Deployment | The MCP server pod |
| `isi-mcp` | Service | ClusterIP on port 8000 |

### Volume Design

The server needs both read-only cluster credentials and a writable config directory
(so `powerscale_tools_toggle` can persist tool enable/disable state at runtime).

An **init container** copies the `tools.json` baseline from the ConfigMap (read-only)
into an `emptyDir` volume (writable) before the main container starts:

```
ConfigMap: isi-mcp-tools
    └── tools.json  →(init container copies)→  emptyDir /app/config/tools.json
                                                      ↑ main container reads/writes here

Secret: isi-mcp-vault
    └── vault.yml   →  /app/vault/vault.yml (read-only)

emptyDir /app/playbooks  →  Ansible playbook audit trail (ephemeral)
```

> **Note**: Tool state changes made via `powerscale_tools_toggle` are written to the
> `emptyDir` and survive container restarts but are **lost if the pod is deleted**.
> The ConfigMap is the persistent baseline. To make tool state durable, replace the
> `emptyDir` with a `PersistentVolumeClaim`.

---

## Prerequisites

- [minikube](https://minikube.sigs.k8s.io/docs/start/) v1.30+
- [kubectl](https://kubernetes.io/docs/tasks/tools/) v1.28+
- [Docker](https://docs.docker.com/get-docker/) (minikube driver)
- Vault credentials set up: run `./setup.sh` from the project root first

---

## Quick Start — minikube

### 1. Create the vault

If you haven't already, set up your cluster credentials:

```bash
./setup.sh
```

This creates `vault/vault.yml` (Ansible-vault encrypted) and prompts for a vault password.

### 2. Deploy

```bash
export VAULT_PASSWORD='your-vault-password'
./k8s/deploy-minikube.sh
```

The script:
1. Starts minikube (Docker driver)
2. Builds the Docker image **inside** minikube's Docker daemon (no registry needed)
3. Creates K8s Secrets for the vault password and encrypted vault file
4. Applies namespace, ConfigMap, Deployment, and Service
5. Waits for the Deployment rollout to complete
6. Verifies the MCP server is responding

### 3. Connect

```bash
kubectl port-forward -n isi-mcp svc/isi-mcp 8000:8000
```

The MCP server is now available at `http://localhost:8000`. Connect your MCP client
(Claude Desktop, Cursor, etc.) to this endpoint.

### 4. Verify

```bash
# Check pod status
kubectl get pods -n isi-mcp

# View logs
kubectl logs -n isi-mcp deployment/isi-mcp

# Run the K8s test suite
./runtests-k8s.sh
```

---

## Deploying Without Cluster Credentials

You can deploy the server without a PowerScale cluster — all management and utility
tools still work (tool listing, unit conversion, etc.). Only cluster-facing tools will
return errors.

Create a minimal vault:

```bash
cat > /tmp/vault-placeholder.yml << 'EOF'
clusters:
  placeholder:
    host: "https://0.0.0.0"
    port: 8080
    username: none
    password: none
    verify_ssl: false
EOF

# Create an encrypted vault from the placeholder
echo -n "mypassword" | ansible-vault encrypt /tmp/vault-placeholder.yml \
  --vault-password-file /dev/stdin

mkdir -p vault
cp /tmp/vault-placeholder.yml vault/vault.yml

export VAULT_PASSWORD='mypassword'
./k8s/deploy-minikube.sh
```

---

## Teardown

```bash
./k8s/deploy-minikube.sh --teardown
```

This deletes the `isi-mcp` namespace (and all resources in it) from minikube.
It does not stop minikube itself. To stop minikube: `minikube stop`.

---

## Production Deployment

For production (non-minikube) deployments, two changes are required:

### 1. Push the image to a registry

Build and push the image to your container registry:

```bash
docker build -t your-registry/isi-mcp-server:1.0.0 isi_mcp_demo/isi_mcp/
docker push your-registry/isi-mcp-server:1.0.0
```

Update [k8s/deployment.yaml](../k8s/deployment.yaml) — change `image` and `imagePullPolicy`:

```yaml
containers:
  - name: isi-mcp
    image: your-registry/isi-mcp-server:1.0.0   # your registry
    imagePullPolicy: Always                       # pull from registry
```

If the registry is private, add an `imagePullSecrets` entry.

### 2. Create secrets via your secrets manager

Do not commit secrets to git. Use your production secret management workflow:

```bash
# Example: create secrets manually
kubectl create secret generic isi-mcp-credentials \
  --namespace=isi-mcp \
  --from-literal=vault-password="${VAULT_PASSWORD}"

kubectl create secret generic isi-mcp-vault \
  --namespace=isi-mcp \
  --from-file=vault.yml=vault/vault.yml
```

Or use Helm, ArgoCD, Vault Agent Injector, External Secrets Operator, etc.

### 3. Persistent tool state (optional)

If you want tool enable/disable state to persist across pod deletions, replace the
`emptyDir` config volume with a `PersistentVolumeClaim`:

```yaml
# Add to deployment.yaml volumes:
- name: config
  persistentVolumeClaim:
    claimName: isi-mcp-config
```

```yaml
# Separate PVC manifest:
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: isi-mcp-config
  namespace: isi-mcp
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Mi
```

With a PVC, you'll also need an init container that only copies if the file doesn't
already exist (to avoid overwriting saved state on restart):

```yaml
initContainers:
  - name: init-config
    image: isi-mcp-server:latest
    command:
      - /bin/sh
      - -c
      - |
        if [ ! -f /app/config/tools.json ]; then
          cp /config-source/tools.json /app/config/tools.json
          echo "Initialized tools.json from ConfigMap"
        else
          echo "tools.json already exists, skipping copy"
        fi
```

### 4. Playbook audit trail persistence (optional)

Ansible playbooks rendered during write operations are stored in `/app/playbooks`.
By default this is an `emptyDir` (lost on pod deletion). For a durable audit trail,
use a PVC:

```yaml
- name: playbooks
  persistentVolumeClaim:
    claimName: isi-mcp-playbooks
```

---

## Environment Variables Reference

| Variable | Source | Default | Description |
|---|---|---|---|
| `VAULT_PASSWORD` | Secret `isi-mcp-credentials` | required | Ansible Vault decryption key |
| `VAULT_FILE` | Deployment env | `/app/vault/vault.yml` | Path to the encrypted vault file |
| `TOOLS_CONFIG_PATH` | Deployment env | `/app/config/tools.json` | Path to tool configuration |
| `DEBUG` | ConfigMap `isi-mcp-env` | (empty) | Set to `1` for verbose logging |
| `ENABLE_ALL_TOOLS` | ConfigMap `isi-mcp-env` | (empty) | Set to `true` to bypass enabled flags (test mode) |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Namespace: isi-mcp                                     │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Deployment: isi-mcp                             │  │
│  │                                                  │  │
│  │  initContainer: init-config                      │  │
│  │    copies ConfigMap → emptyDir(/app/config)      │  │
│  │                                                  │  │
│  │  Container: isi-mcp                              │  │
│  │    image: isi-mcp-server:latest                  │  │
│  │    port: 8000                                    │  │
│  │    /app/config     ← emptyDir (writable)         │  │
│  │    /app/vault      ← Secret (read-only)          │  │
│  │    /app/playbooks  ← emptyDir (writable)         │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
│  ┌───────────────────────┤                              │
│  │  Service: isi-mcp     │                              │
│  │  ClusterIP:8000       │                              │
│  └───────────────────────┘                              │
│                                                         │
│  ConfigMap: isi-mcp-tools   (baseline tools.json)       │
│  Secret: isi-mcp-credentials (VAULT_PASSWORD)           │
│  Secret: isi-mcp-vault       (vault.yml)                │
└─────────────────────────────────────────────────────────┘
             │
             │ kubectl port-forward :8000
             │
          MCP Client (Claude Desktop, Cursor, etc.)
             │
             └── connects to PowerScale cluster via SDK
```

---

## Troubleshooting

### Pod stuck in `Init:Error` or `Init:CrashLoopBackOff`

The init container failed to copy tools.json. Check its logs:

```bash
kubectl logs -n isi-mcp <pod-name> -c init-config
```

Usually caused by the ConfigMap not existing. Verify:

```bash
kubectl get configmap isi-mcp-tools -n isi-mcp
```

### Pod stuck in `Pending`

Check events:

```bash
kubectl describe pod -n isi-mcp <pod-name>
```

Common causes:
- Image not found: the image must be built in minikube's Docker daemon (`eval $(minikube docker-env)`)
- Missing secret: verify `isi-mcp-credentials` and `isi-mcp-vault` exist

### Server starts but tools return "Cluster host is not reachable"

This is expected if no PowerScale cluster is configured or reachable. The server is
healthy — cluster connectivity errors are per-tool. Check vault configuration:

```bash
# Exec into the pod and test vault loading
kubectl exec -n isi-mcp deployment/isi-mcp -- \
  python3 -c "from modules.ansible.vault_manager import VaultManager; v = VaultManager(); print(v.list_clusters())"
```

### View server logs

```bash
kubectl logs -n isi-mcp deployment/isi-mcp -f
```

### Run tests against the deployed server

```bash
# In a separate terminal, start port-forward
kubectl port-forward -n isi-mcp svc/isi-mcp 8000:8000

# Run the K8s test suite
./runtests-k8s.sh

# Run against a specific cluster (if available)
./runtests-k8s.sh --cluster-host 172.16.10.10 --cluster-user root --cluster-pass password
```
