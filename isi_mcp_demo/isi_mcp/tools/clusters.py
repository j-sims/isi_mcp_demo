"""Cluster management MCP tools: list, setdefault, add, remove, modify.

These tools are always registered and cannot be disabled via the toggle.
Call register(mcp) from server.py after the FastMCP instance is created.
"""

import logging
import os
import re
import subprocess
from typing import Any, Dict

logger = logging.getLogger(__name__)


def register(mcp, vault_manager_class):
    """Register the five cluster-management tools against the given FastMCP instance."""

    VaultManager = vault_manager_class

    @mcp.tool()
    def powerscale_cluster_list() -> Dict[str, Any]:
        """
        List all PowerScale clusters configured in the vault and show which one
        is the default.

        Returns a list of clusters with their name, host, port, verify_ssl status,
        and whether each is the default target. Passwords are never included in
        the response.

        Use this tool to:
        - See which clusters are available to manage
        - Check which cluster is the default target for all other PowerScale tools
        - Verify cluster configuration before switching
        """
        try:
            vm = VaultManager()
            clusters = vm.list_clusters()
            default = vm.selected_cluster_name
            return {
                "clusters": clusters,
                "default": default,
                "total": len(clusters),
            }
        except FileNotFoundError:
            return {"error": "Vault file not found. Ensure vault.yml is mounted into the container."}
        except Exception as e:
            return {"error": f"Failed to read vault: {str(e)}"}

    @mcp.tool()
    def powerscale_cluster_setdefault(cluster_name: str, reload_vault: bool = False) -> Dict[str, Any]:
        """
        Set the default PowerScale cluster that tools will operate against when no
        cluster_name is specified.

        IMPORTANT: This is a MUTATING operation that changes the default cluster for all
        subsequent tool calls that omit cluster_name. The change takes effect immediately.

        Note: You can target any cluster directly without changing the default by passing
        cluster_name to any tool. Use this tool only when you want to change which cluster
        is used implicitly for tool calls that do not specify cluster_name.

        Arguments:
        - cluster_name: The name of the cluster as defined in the vault file
          (e.g. "lab_cluster", "production"). Use powerscale_cluster_list to
          see available names.
        - reload_vault: If True, re-read and decrypt the vault file before
          updating. Use this if clusters were added/removed externally.
          Default is False.

        Use this tool when:
        - The user wants to change which cluster is targeted by default
        - The user wants to switch the default from lab to production (or vice versa)
        - The user asks "set default cluster to X" or "make production the default"
        """
        try:
            vm = VaultManager()
            if reload_vault:
                vm.reload()
            if vm.select_cluster(cluster_name):
                return {
                    "success": True,
                    "default": cluster_name,
                    "message": f"Default cluster set to '{cluster_name}'. Tools without an explicit cluster_name will now target this cluster.",
                }
            else:
                available = [c["name"] for c in vm.list_clusters()]
                return {
                    "success": False,
                    "error": f"Cluster '{cluster_name}' not found in vault.",
                    "available_clusters": available,
                }
        except Exception as e:
            return {"error": f"Failed to select cluster: {str(e)}"}

    @mcp.tool()
    def powerscale_cluster_add(
        name: str,
        host: str,
        port: int = 8080,
        username: str = "root",
        password: str = "",
        verify_ssl: bool = True,
    ) -> Dict[str, Any]:
        """
        Add a new PowerScale cluster to the vault, or update an existing one.

        IMPORTANT: This is a MUTATING operation. Confirm with the user before executing.

        The cluster credentials are encrypted and saved to the vault file immediately.
        This tool automatically extracts the cluster's TLS certificate for SSL verification
        (useful for self-signed certificates), but falls back gracefully if extraction fails.

        Use powerscale_cluster_setdefault to change the default cluster.

        Arguments:
        - name: Cluster label used to identify it (e.g. "production", "lab")
        - host: Hostname or IP address (https:// prefix added automatically if omitted)
        - port: API port (default 8080)
        - username: Admin username (default root)
        - password: Admin password
        - verify_ssl: Whether to verify SSL certificates (default true; auto-disabled cert extracted)
        """
        try:
            host_bare = re.sub(r'^https?://', '', host).split(':')[0]
            vault_dir = os.path.dirname(os.environ.get("VAULT_FILE", "/app/vault/vault.yml"))
            cert_path_container = f"{vault_dir}/{name}_cert.pem"

            cert_extracted = False
            try:
                result = subprocess.run(
                    ["sh", "-c",
                     f"openssl s_client -connect {host_bare}:{port} -showcerts "
                     f"</dev/null 2>/dev/null | openssl x509 -outform PEM > {cert_path_container}"],
                    timeout=10, capture_output=True,
                )
                cert_extracted = (
                    result.returncode == 0
                    and os.path.exists(cert_path_container)
                    and os.path.getsize(cert_path_container) > 0
                )
            except (subprocess.TimeoutExpired, OSError, FileNotFoundError) as e:
                logger.debug(f"Certificate extraction failed: {e}")

            # Three SSL cases:
            #   a) CA-signed cert (Subject != Issuer): use system CA store, verify_ssl=True
            #   b) Self-signed with CA:TRUE: pin against this cert as ca_bundle
            #   c) Self-signed without CA:TRUE (PowerScale default): auto-disable SSL
            ca_bundle = None
            cert_is_ca = False
            is_self_signed = False
            if cert_extracted:
                try:
                    check = subprocess.run(
                        ["openssl", "x509", "-in", cert_path_container, "-text", "-noout"],
                        capture_output=True, text=True, timeout=5,
                    )
                    cert_is_ca = "CA:TRUE" in check.stdout

                    id_check = subprocess.run(
                        ["openssl", "x509", "-in", cert_path_container, "-noout", "-subject", "-issuer"],
                        capture_output=True, text=True, timeout=5,
                    )
                    lines = id_check.stdout.strip().splitlines()
                    subject = next((l.split("subject=", 1)[1] for l in lines if "subject=" in l), "")
                    issuer = next((l.split("issuer=", 1)[1] for l in lines if "issuer=" in l), "")
                    is_self_signed = subject.strip() == issuer.strip()

                    if is_self_signed and cert_is_ca:
                        ca_bundle = cert_path_container
                        logger.info(f"Extracted CA-capable self-signed cert for cluster '{name}'")
                    else:
                        try:
                            os.remove(cert_path_container)
                        except OSError:
                            pass
                        if is_self_signed:
                            logger.debug(f"Cert for '{name}' is self-signed but lacks CA:TRUE (X.509 v1)")
                        else:
                            logger.debug(f"Cert for '{name}' is CA-signed — will use system CA store")
                except (subprocess.TimeoutExpired, OSError) as e:
                    logger.debug(f"Cert inspection failed: {e}")

            ssl_note = None
            if ca_bundle:
                effective_verify_ssl = True
                ssl_note = "Certificate pinning active — cluster cert extracted and trusted directly."
            elif not verify_ssl:
                effective_verify_ssl = False
            elif is_self_signed and not cert_is_ca:
                effective_verify_ssl = False
                ssl_note = (
                    "SSL verification auto-disabled: the cluster's TLS certificate is X.509 v1 "
                    "(self-signed, no CA:TRUE extension) and cannot be used as a trust anchor. "
                    "This is the default for PowerScale self-signed certificates."
                )
            else:
                effective_verify_ssl = True

            vm = VaultManager()
            vm.add_cluster(name, host, port, username, password, effective_verify_ssl, ca_bundle=ca_bundle)
            response = {
                "success": True,
                "cluster": name,
                "ssl_verified": ca_bundle is not None,
                "verify_ssl": effective_verify_ssl,
                "message": f"Cluster '{name}' saved to vault. Use powerscale_cluster_select to target it.",
                "clusters": vm.list_clusters(),
            }
            if ssl_note:
                response["ssl_note"] = ssl_note
            return response
        except Exception as e:
            return {"error": f"Failed to add cluster: {str(e)}"}

    @mcp.tool()
    def powerscale_cluster_remove(name: str) -> Dict[str, Any]:
        """
        Remove a PowerScale cluster from the vault.

        IMPORTANT: This is a MUTATING operation. Confirm with the user before executing.

        Cannot remove the default cluster — use powerscale_cluster_setdefault
        to change the default to a different cluster first.

        Arguments:
        - name: The cluster label to remove (use powerscale_cluster_list to see available names)
        """
        try:
            vm = VaultManager()
            if vm.selected_cluster_name == name:
                return {
                    "success": False,
                    "error": f"Cannot remove the default cluster '{name}'. "
                             "Use powerscale_cluster_setdefault to change the default to a different cluster first.",
                }
            removed = vm.remove_cluster(name)
            if not removed:
                available = [c["name"] for c in vm.list_clusters()]
                return {
                    "success": False,
                    "error": f"Cluster '{name}' not found in vault.",
                    "available_clusters": available,
                }
            return {
                "success": True,
                "message": f"Cluster '{name}' removed from vault.",
                "clusters": vm.list_clusters(),
            }
        except Exception as e:
            return {"error": f"Failed to remove cluster: {str(e)}"}

    @mcp.tool()
    def powerscale_cluster_modify(
        name: str,
        new_name: str = None,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        verify_ssl: bool = None,
    ) -> Dict[str, Any]:
        """
        Modify an existing PowerScale cluster entry in the vault.

        IMPORTANT: This is a MUTATING operation. Confirm with the user before executing.

        Only supply the fields you want to change — unspecified fields are left as-is.
        To rename a cluster, provide new_name. SSL certificate handling is NOT
        automatically re-run when host changes; use powerscale_cluster_add to
        replace the entry with full cert extraction if needed.

        Arguments:
        - name: Current cluster label (use powerscale_cluster_list to see names)
        - new_name: Rename the cluster to this label (optional)
        - host: New hostname or IP address (https:// prefix added automatically if omitted)
        - port: New API port
        - username: New admin username
        - password: New admin password
        - verify_ssl: Whether to verify SSL certificates
        """
        try:
            vm = VaultManager()
            clusters = {c["name"] for c in vm.list_clusters()}
            if name not in clusters:
                return {
                    "success": False,
                    "error": f"Cluster '{name}' not found in vault.",
                    "available_clusters": sorted(clusters),
                }
            if new_name and new_name != name and new_name in clusters:
                return {
                    "success": False,
                    "error": f"A cluster named '{new_name}' already exists. Choose a different name.",
                }
            updated = vm.modify_cluster(
                name,
                new_name=new_name,
                host=host,
                port=port,
                username=username,
                password=password,
                verify_ssl=verify_ssl,
            )
            if not updated:
                return {"success": False, "error": f"Cluster '{name}' not found in vault."}
            effective_name = new_name if new_name else name
            return {
                "success": True,
                "cluster": effective_name,
                "message": f"Cluster '{name}' updated successfully.",
                "clusters": vm.list_clusters(),
            }
        except Exception as e:
            return {"error": f"Failed to modify cluster: {str(e)}"}
