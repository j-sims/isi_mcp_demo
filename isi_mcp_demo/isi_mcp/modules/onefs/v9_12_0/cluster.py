import os
import urllib3

import isilon_sdk.v9_12_0 as isi_sdk

class Cluster:

    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        verify_ssl: bool = None,
        debug_env_var: str = "DEBUG",
        ):

        self.debug = False
        if os.environ.get(debug_env_var):
            print("DEBUG Flag Detected, setting DEBUG Mode")
            self.debug = True
            print(os.environ)

        self.port = int(port or os.environ.get("PORT", 0)) or None
        self.host = host or os.environ.get("HOST")
        self.username = username or os.environ.get("USERNAME")
        self.password = password or os.environ.get("PASSWORD")

        if verify_ssl is None:
            verify_ssl = os.environ.get("VERIFY_SSL", "False").lower() == "true"
        self.verify_ssl = verify_ssl

        if not self.host or not self.port or not self.username or not self.password:
            if self.debug:
                print("One or more required environment variables are missing:")
                print(f"HOST={self.host}, PORT={self.port}, USERNAME={self.username}")

        self.url = f"{self.host}:{self.port}" if self.host and self.port else None

        if self.debug:
            print(f"PORT: {self.port}")
            print(f"HOST: {self.host}")
            print(f"USERNAME: {self.username}")
            print(f"VERIFY_SSL: {self.verify_ssl}")
            print(f"URL: {self.url}")

        # disable urllib3 warnings if SSL verification is turned off
        if not self.verify_ssl:
            urllib3.disable_warnings()

        # Build SDK configuration and API client
        cfg = isi_sdk.Configuration()
        if self.url:
            cfg.host = self.url
        if self.username:
            cfg.username = self.username
        if self.password:
            cfg.password = self.password
        cfg.verify_ssl = self.verify_ssl

        self.api_client = isi_sdk.ApiClient(cfg)

    @classmethod
    def from_vault(cls, debug_env_var: str = "DEBUG"):
        """Create a Cluster from the currently-selected vault credentials.
        Falls back to env vars if no vault is configured."""
        from modules.ansible.vault_manager import VaultManager

        try:
            vm = VaultManager()
            creds = vm.get_selected_credentials()
        except Exception:
            creds = None

        if creds:
            return cls(
                host=creds.get("host"),
                port=creds.get("port"),
                username=creds.get("username"),
                password=creds.get("password"),
                verify_ssl=creds.get("verify_ssl"),
                debug_env_var=debug_env_var,
            )
        # Fallback: use env vars (original behavior)
        return cls(debug_env_var=debug_env_var)

