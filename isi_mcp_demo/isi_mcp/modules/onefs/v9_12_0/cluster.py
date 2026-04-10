import logging
import os
from typing import Any, Dict, Optional
import urllib3

import isilon_sdk.v9_12_0 as isi_sdk

logger = logging.getLogger(__name__)

class Cluster:
    """Manages API connection to a PowerScale cluster."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
        ca_bundle: Optional[str] = None,
        debug_env_var: str = "DEBUG",
        connect_timeout: Optional[int] = None,
        read_timeout: Optional[int] = None,
    ) -> None:
        """Initialize a Cluster connection.

        Args:
            host: Cluster hostname or IP. Falls back to HOST env var.
            port: Cluster API port. Falls back to PORT env var (default 8080).
            username: API username. Falls back to USERNAME env var.
            password: API password. Falls back to PASSWORD env var.
            verify_ssl: Whether to verify SSL certificates. Falls back to VERIFY_SSL env var.
            ca_bundle: Path to CA bundle file for SSL verification.
            debug_env_var: Environment variable to check for debug mode (default 'DEBUG').
            connect_timeout: Connection timeout in seconds (default 30).
            read_timeout: Read timeout in seconds (default 30).
        """

        self.debug = False
        if os.environ.get(debug_env_var):
            logger.debug("DEBUG flag detected, enabling debug mode")
            self.debug = True

        self.port = int(port or os.environ.get("PORT", 0)) or None
        self.host = host or os.environ.get("HOST")
        self.username = username or os.environ.get("USERNAME")
        self.password = password or os.environ.get("PASSWORD")
        self.connect_timeout = connect_timeout or int(os.environ.get("CONNECT_TIMEOUT", 30))
        self.read_timeout = read_timeout or int(os.environ.get("READ_TIMEOUT", 30))

        # ca_bundle takes precedence for SSL verification
        # If provided, urllib3 will verify the cluster cert against this CA bundle file
        if ca_bundle:
            self.verify_ssl = ca_bundle
        else:
            if verify_ssl is None:
                verify_ssl = os.environ.get("VERIFY_SSL", "True").lower() == "true"
            self.verify_ssl = verify_ssl

        if not self.host or not self.port or not self.username or not self.password:
            logger.debug(
                "One or more required config values are missing: "
                "HOST=%s, PORT=%s, USERNAME=%s",
                self.host, self.port, self.username,
            )

        self.url = f"{self.host}:{self.port}" if self.host and self.port else None

        if self.debug:
            logger.debug("HOST=%s PORT=%s USERNAME=%s VERIFY_SSL=%s URL=%s",
                         self.host, self.port, self.username, self.verify_ssl, self.url)

        # disable urllib3 warnings only if SSL verification is explicitly disabled (not when using ca_bundle)
        if self.verify_ssl is False:
            urllib3.disable_warnings()

        # Build SDK configuration and API client
        cfg = isi_sdk.Configuration()
        if self.url:
            cfg.host = self.url
        if self.username:
            cfg.username = self.username
        if self.password:
            cfg.password = self.password
        # verify_ssl must be a bool; ca_bundle path goes in ssl_ca_cert.
        # Disable hostname checking because cluster certs often lack IP SANs
        # but the cert chain is still verified against the extracted CA bundle.
        if isinstance(self.verify_ssl, str):
            cfg.verify_ssl = True
            cfg.ssl_ca_cert = self.verify_ssl
            cfg.assert_hostname = False
        else:
            cfg.verify_ssl = self.verify_ssl

        self.api_client = isi_sdk.ApiClient(cfg)

        # Inject a default HTTP timeout on every SDK call so tools never hang
        # indefinitely waiting for a slow or unresponsive cluster.
        # Override per-call by passing _request_timeout explicitly (existing calls
        # that already pass timeout= on statistics endpoints are unaffected because
        # those use the statistics_api timeout kwarg, not _request_timeout).
        _api_timeout = int(os.environ.get("API_TIMEOUT", 30))
        _orig_call_api = self.api_client.call_api

        def _call_api_with_timeout(*args, **kwargs):
            if "_request_timeout" not in kwargs:
                kwargs["_request_timeout"] = (_api_timeout, _api_timeout)
            return _orig_call_api(*args, **kwargs)

        self.api_client.call_api = _call_api_with_timeout

    def verify(self) -> bool:
        """
        Verify cluster connectivity and authentication.
        Returns True if the cluster is accessible with valid credentials, False otherwise.
        May raise exceptions on connection errors.
        """
        try:
            config = self.get_config()
            return config is not None
        except Exception:
            return False

    def get_config(self) -> Dict[str, Any]:
        """
        Get cluster configuration from the local/config endpoint.
        Returns the configuration dict or raises an exception on failure.
        """
        try:
            local_api = isi_sdk.LocalApi(self.api_client)
            config_response = local_api.get_local_config()
            # Handle both object and dict responses
            if hasattr(config_response, 'to_dict'):
                return config_response.to_dict()
            elif isinstance(config_response, dict):
                return config_response
            else:
                return config_response
        except Exception as e:
            logger.debug("Failed to get config: %s", e)
            raise

    @classmethod
    def from_vault(cls, debug_env_var: str = "DEBUG") -> "Cluster":
        """Create a Cluster from the currently-selected vault credentials.
        Falls back to env vars if no vault is configured."""
        from modules.ansible.vault_manager import VaultManager

        try:
            vm = VaultManager()
            creds = vm.get_selected_credentials()
        except Exception as exc:
            logger.warning("Failed to load vault credentials: %s — falling back to env vars", exc)
            creds = None

        if creds:
            return cls(
                host=creds.get("host"),
                port=creds.get("port"),
                username=creds.get("username"),
                password=creds.get("password"),
                verify_ssl=creds.get("verify_ssl"),
                ca_bundle=creds.get("ca_bundle"),
                debug_env_var=debug_env_var,
            )
        # Fallback: use env vars (original behavior)
        return cls(debug_env_var=debug_env_var)

    @classmethod
    def from_vault_by_name(cls, name: str, debug_env_var: str = "DEBUG"):
        """Create a Cluster from a specific named vault entry.
        Raises ValueError if the cluster name is not found."""
        from modules.ansible.vault_manager import VaultManager

        vm = VaultManager()
        creds = vm.get_credentials(name)
        if not creds:
            available = [c["name"] for c in vm.list_clusters()]
            raise ValueError(f"Cluster '{name}' not found in vault. Available: {available}")
        return cls(
            host=creds.get("host"),
            port=creds.get("port"),
            username=creds.get("username"),
            password=creds.get("password"),
            verify_ssl=creds.get("verify_ssl"),
            ca_bundle=creds.get("ca_bundle"),
            debug_env_var=debug_env_var,
        )
