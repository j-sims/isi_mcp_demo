import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class LocalInfo:
    """Provides access to local node information via LocalApi, LocalClusterApi, and OsApi.

    Covers local node time, network interfaces, firmware status, internal IP
    addresses, and OS security settings.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    # -----------------------------------------------------------------------
    # LocalApi methods
    # -----------------------------------------------------------------------

    def get_cluster_time(self):
        """Get the current time on the local node."""
        api = isi_sdk.LocalApi(self.cluster.api_client)
        try:
            result = api.get_cluster_time()
            return result.time.to_dict() if hasattr(result, "time") and result.time else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_network_interfaces(self):
        """List network interfaces on the local node."""
        api = isi_sdk.LocalApi(self.cluster.api_client)
        try:
            result = api.get_network_interfaces()
            interfaces = result.interfaces if hasattr(result, "interfaces") and result.interfaces else []
            return {
                "items": [i.to_dict() for i in interfaces],
                "resume": getattr(result, "resume", None),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_firmware_status(self):
        """Get firmware status for the cluster."""
        api = isi_sdk.LocalApi(self.cluster.api_client)
        try:
            result = api.get_upgrade_cluster_firmware_status()
            return result.cluster_firmware_status.to_dict() if hasattr(result, "cluster_firmware_status") and result.cluster_firmware_status else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_firmware_device(self):
        """Get firmware device information for the cluster."""
        api = isi_sdk.LocalApi(self.cluster.api_client)
        try:
            result = api.get_upgrade_cluster_firmware_device()
            nodes = result.nodes if hasattr(result, "nodes") and result.nodes else []
            return {"items": [n.to_dict() for n in nodes]}
        except ApiException as e:
            return {"error": str(e)}

    # -----------------------------------------------------------------------
    # LocalClusterApi methods
    # -----------------------------------------------------------------------

    def get_node_internal_ip(self, node_lnn: int):
        """Get the internal IP address for a specific node.

        Arguments:
        - node_lnn: Logical Node Number (LNN) of the node
        """
        api = isi_sdk.LocalClusterApi(self.cluster.api_client)
        try:
            result = api.get_nodes_node_internal_ip_address(node_lnn)
            return result.to_dict() if result else {}
        except ApiException as e:
            return {"error": str(e)}

    # -----------------------------------------------------------------------
    # OsApi methods
    # -----------------------------------------------------------------------

    def get_os_security(self):
        """Get per-node OS security settings status."""
        api = isi_sdk.OsApi(self.cluster.api_client)
        try:
            result = api.get_os_security()
            return result.os_security.to_dict() if hasattr(result, "os_security") and result.os_security else {}
        except ApiException as e:
            return {"error": str(e)}
