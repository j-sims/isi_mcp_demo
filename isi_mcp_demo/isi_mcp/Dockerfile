FROM python:3.12-slim

WORKDIR /app

# Install system dependencies:
#   iputils-ping  - for ICMP health checks
#   sshpass, openssh-client - Ansible connectivity
#   curl - for Docker HEALTHCHECK
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        iputils-ping \
        sshpass \
        openssh-client \
        curl; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shim for pkg_resources (parse_version removed in setuptools>=78).
# The dellemc.powerscale collection imports parse_version and working_set
# from pkg_resources; this shim injects them into the existing package.
COPY modules/shims/pkg_resources_shim.py .
RUN SITE="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib"))')"; \
    if [ -d "$SITE/pkg_resources" ]; then \
        cp pkg_resources_shim.py "$SITE/pkg_resources/_powerscale_shim.py"; \
        printf '\n# Shim: re-add parse_version for dellemc.powerscale\nfrom pkg_resources._powerscale_shim import parse_version, working_set  # noqa\n' \
            >> "$SITE/pkg_resources/__init__.py"; \
    else \
        cp pkg_resources_shim.py "$SITE/pkg_resources.py"; \
    fi

# Create non-root user with fixed UID/GID (must match K8s securityContext)
RUN groupadd -g 1000 mcp && useradd -u 1000 -g mcp -d /app -s /bin/bash mcp

COPY server.py .
COPY modules modules
COPY Templates Templates
COPY tests tests
COPY config config

# Create writable directories: playbooks (audit trail) + .ansible (Ansible temp files)
RUN mkdir -p playbooks .ansible/tmp && chown -R mcp:mcp /app

# Set HOME so Ansible finds ~/.ansible/tmp as writable
ENV HOME=/app

USER mcp

# Install the Dell PowerScale Ansible collection as mcp user
# This ensures the collection is installed to /app/.ansible/collections (readable by mcp)
RUN ansible-galaxy collection install dellemc.powerscale

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -sf http://localhost:8000/health || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
