import logging
import os
import socket
import uuid
import ansible_runner
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

logger = logging.getLogger(__name__)


class AnsibleRunner:
    """
    Renders Jinja2 playbook templates and executes them via ansible-runner.

    Accepts a Cluster instance for PowerScale connection credentials and
    provides a pipeline to render templates, save playbooks, and execute them.
    """

    def __init__(self, cluster, templates_dir=None, playbooks_dir=None):
        self.cluster = cluster
        self.debug = cluster.debug

        # Resolve paths relative to the isi_mcp package root
        base_dir = Path(__file__).resolve().parent.parent.parent  # isi_mcp/
        self.templates_dir = Path(templates_dir) if templates_dir else base_dir / "Templates"
        # Explicit arg > PLAYBOOKS_DIR env var > default relative path
        env_playbooks_dir = os.environ.get("PLAYBOOKS_DIR")
        self.playbooks_dir = (
            Path(playbooks_dir) if playbooks_dir
            else Path(env_playbooks_dir) if env_playbooks_dir
            else base_dir / "playbooks"
        )

        # Ensure playbooks output directory exists
        self.playbooks_dir.mkdir(parents=True, exist_ok=True)

        # Build Jinja2 environment pointing at Templates/
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            keep_trailing_newline=True,
        )

    def _get_connection_vars(self) -> dict:
        """Extract PowerScale connection parameters from the Cluster instance.

        Includes placeholder credentials for template rendering only.
        Real credentials are provided to ansible-runner at execution time via extravars.
        This ensures credentials never appear in the rendered playbook files.
        """
        host = self.cluster.host
        if host:
            # Strip protocol prefix — Ansible modules expect bare hostname/IP
            host = host.replace("https://", "").replace("http://", "")
            # Remove trailing port if present (e.g. "192.168.0.33:8080" -> "192.168.0.33")
            if ":" in host:
                host = host.split(":")[0]

        return {
            "onefs_host": host,
            "port_no": str(self.cluster.port),
            "verify_ssl": self.cluster.verify_ssl,
            # Placeholder credentials — these appear in the playbook but are overridden
            # at runtime by ansible-runner's extravars with the real credentials
            "api_user": "{{ api_user }}",
            "api_password": "{{ api_password }}",
        }

    def render_playbook(self, template_name: str, variables: dict) -> Path:
        """
        Render a Jinja2 template with the given variables and save as a YAML playbook.

        Credentials are NOT included during rendering — they are injected by ansible-runner
        at execution time via extravars, so they never appear in the rendered playbook files.

        Args:
            template_name: Filename of the .yml.j2 template (e.g. "smb_create.yml.j2")
            variables: Dict of resource-specific variables to inject

        Returns:
            Path to the rendered playbook file
        """
        # Merge connection vars (without credentials) with resource-specific vars
        # Credentials will be passed via extravars to ansible-runner at execution time
        all_vars = {**self._get_connection_vars(), **variables}

        template = self.jinja_env.get_template(template_name)
        rendered = template.render(**all_vars)

        # Generate a unique filename for audit trail (includes hostname for multi-instance)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = uuid.uuid4().hex[:8]
        hostname = socket.gethostname()[:8]
        base_name = template_name.replace(".yml.j2", "")
        playbook_filename = f"{base_name}_{timestamp}_{hostname}_{run_id}.yml"
        playbook_path = self.playbooks_dir / playbook_filename

        playbook_path.write_text(rendered)

        if self.debug:
            logger.debug("Rendered playbook: %s\n%s", playbook_path, rendered)

        return playbook_path

    def run_playbook(self, playbook_path: Path) -> dict:
        """
        Execute a playbook using ansible-runner and return structured results.

        Credentials are injected via extravars at runtime so they are never
        stored in the rendered playbook files.

        Args:
            playbook_path: Absolute path to the rendered playbook YAML

        Returns:
            dict with keys: success, status, rc, playbook_path, stdout
        """
        # Pass credentials via extravars so ansible-runner can provide them at runtime
        # without them being present in the playbook file
        extravars = {
            "api_user": self.cluster.username,
            "api_password": self.cluster.password,
        }

        runner = ansible_runner.run(
            private_data_dir=str(self.playbooks_dir),
            playbook=str(playbook_path.name),
            quiet=not self.debug,
            extravars=extravars,
        )

        result = {
            "success": runner.status == "successful",
            "status": runner.status,
            "rc": runner.rc,
            "playbook_path": str(playbook_path),
        }

        # Capture stdout for diagnostics
        if runner.stdout:
            result["stdout"] = runner.stdout.read() if hasattr(runner.stdout, "read") else str(runner.stdout)

        # On failure, include stderr if available
        if not result["success"] and runner.stderr:
            result["stderr"] = runner.stderr.read() if hasattr(runner.stderr, "read") else str(runner.stderr)

        # Extract structured task results from runner events
        task_results = {}
        for event in runner.events:
            if event.get("event") == "runner_on_ok":
                task_name = event.get("event_data", {}).get("task", "")
                res = event.get("event_data", {}).get("res", {})
                if task_name and res:
                    task_results[task_name] = res
        result["task_results"] = task_results

        if self.debug:
            logger.debug("Ansible runner status: %s, rc: %s", runner.status, runner.rc)

        return result

    def execute(self, template_name: str, variables: dict) -> dict:
        """
        Full pipeline: render template, then execute the resulting playbook.

        Args:
            template_name: The .yml.j2 template filename
            variables: Resource-specific variables

        Returns:
            dict with execution results (same shape as run_playbook output)
        """
        playbook_path = self.render_playbook(template_name, variables)
        return self.run_playbook(playbook_path)
