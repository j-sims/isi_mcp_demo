import os
import yaml
from pathlib import Path
from ansible.parsing.vault import VaultLib, VaultSecret


class VaultManager:
    """
    Singleton that decrypts and caches Ansible Vault cluster credentials.

    Env vars:
      VAULT_FILE     - path to encrypted vault YAML (default: /app/vault.yml)
      VAULT_PASSWORD - vault encryption password (required for encrypted vaults)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.vault_file = Path(os.environ.get("VAULT_FILE", "/app/vault.yml"))

        self._clusters: dict = {}
        self._selected: str | None = None
        self._load_vault()

    def _get_vault_password(self) -> bytes:
        """Get vault password from environment variable.

        Raises:
            ValueError: If vault password is not set and vault is encrypted.
        """
        env_password = os.environ.get("VAULT_PASSWORD")
        if env_password:
            return env_password.encode()
        raise ValueError(
            "Vault is encrypted but VAULT_PASSWORD environment variable is not set. "
            "Set VAULT_PASSWORD to decrypt the vault."
        )

    def _load_vault(self):
        """Load cluster credentials from vault file.

        Supports both Ansible Vault-encrypted files and plaintext YAML.
        If the file starts with the '$ANSIBLE_VAULT' header it is decrypted
        using the configured password. Otherwise it is loaded directly as
        plain YAML — no password required (useful for development/CI).
        """
        encrypted_data = self.vault_file.read_bytes()

        if encrypted_data.startswith(b'$ANSIBLE_VAULT'):
            password_bytes = self._get_vault_password()
            vault = VaultLib(secrets=[("default", VaultSecret(password_bytes))])
            decrypted = vault.decrypt(encrypted_data)
            data = yaml.safe_load(decrypted)
        else:
            data = yaml.safe_load(encrypted_data)

        self._clusters = data.get("clusters", {})

        # Default to first cluster in the YAML ordered dict
        if self._clusters:
            self._selected = next(iter(self._clusters))

    def _save_vault(self):
        """Re-encrypt and write the vault file.

        Uses VaultLib.encrypt() + Path.write_bytes() — no os.remove() call,
        so it works safely on Docker bind-mounted files (avoids EBUSY).

        Requires:
            VAULT_PASSWORD environment variable must be set.
        """
        plaintext = yaml.dump({'clusters': self._clusters}, default_flow_style=False).encode()
        password_bytes = self._get_vault_password()
        vault = VaultLib(secrets=[("default", VaultSecret(password_bytes))])
        encrypted = vault.encrypt(plaintext)
        self.vault_file.write_bytes(encrypted if isinstance(encrypted, bytes) else encrypted.encode())

    def add_cluster(self, name: str, host: str, port: int, username: str, password: str, verify_ssl: bool):
        """Add or update a cluster and persist the vault."""
        if not host.startswith(('http://', 'https://')):
            host = f'https://{host}'
        self._clusters[name] = {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'verify_ssl': verify_ssl,
        }
        if not self._selected:
            self._selected = name
        self._save_vault()

    def remove_cluster(self, name: str) -> bool:
        """Remove a cluster and persist the vault. Returns False if not found."""
        if name not in self._clusters:
            return False
        del self._clusters[name]
        if self._selected == name:
            self._selected = next(iter(self._clusters)) if self._clusters else None
        self._save_vault()
        return True

    def reload(self):
        """Re-read and decrypt the vault file. Called when vault may have changed."""
        self._clusters = {}
        self._selected = None
        self._load_vault()

    @property
    def selected_cluster_name(self) -> str | None:
        return self._selected

    def select_cluster(self, name: str) -> bool:
        """Switch active cluster. Returns True on success, False if name not found."""
        if name not in self._clusters:
            return False
        self._selected = name
        return True

    def list_clusters(self) -> list[dict]:
        """Return list of cluster info dicts (no passwords)."""
        result = []
        for name, cfg in self._clusters.items():
            result.append(
                {
                    "name": name,
                    "host": cfg.get("host", ""),
                    "port": cfg.get("port", 8080),
                    "verify_ssl": cfg.get("verify_ssl", False),
                    "selected": name == self._selected,
                }
            )
        return result

    def get_selected_credentials(self) -> dict | None:
        """Return credentials dict for the currently selected cluster, or None."""
        if not self._selected or self._selected not in self._clusters:
            return None
        return dict(self._clusters[self._selected])
