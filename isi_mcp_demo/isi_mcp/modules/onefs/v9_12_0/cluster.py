import logging
import os
import urllib3

import isilon_sdk.v9_12_0 as isi_sdk

logger = logging.getLogger(__name__)

class Cluster:

    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        verify_ssl: bool = None,
        ca_bundle: str = None,
        debug_env_var: str = "DEBUG",
        ):

        self.debug = False
        if os.environ.get(debug_env_var):
            logger.debug("DEBUG flag detected, enabling debug mode")
            self.debug = True

        self.port = int(port or os.environ.get("PORT", 0)) or None
        self.host = host or os.environ.get("HOST")
        self.username = username or os.environ.get("USERNAME")
        self.password = password or os.environ.get("PASSWORD")

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

    @classmethod
    def from_vault(cls, debug_env_var: str = "DEBUG"):
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
