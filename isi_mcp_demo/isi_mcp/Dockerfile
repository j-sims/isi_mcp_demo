FROM python:3.12-slim

WORKDIR /app

# Install system dependencies:
#   iputils-ping  - for ICMP health checks
#   sshpass, openssh-client - Ansible connectivity
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        iputils-ping \
        sshpass \
        openssh-client; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the Dell PowerScale Ansible collection
RUN ansible-galaxy collection install dellemc.powerscale

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

COPY server.py .
COPY modules modules
COPY Templates Templates
COPY tests tests
COPY tool_config.json .

# Create playbooks directory for rendered playbooks
RUN mkdir -p playbooks

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
