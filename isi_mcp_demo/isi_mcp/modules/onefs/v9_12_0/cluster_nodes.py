import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class ClusterNodes:

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self):
        """List all cluster nodes with status, state, and version info."""
        cluster_api = isi_sdk.ClusterApi(self.cluster.api_client)
        try:
            result = cluster_api.get_cluster_nodes()
            nodes = result.nodes if result.nodes else []
            items = []
            for n in nodes:
                d = n.to_dict()
                items.append(d)
            return {
                "items": items,
                "total": getattr(result, "total", len(items)),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_by_id(self, node_id: int):
        """
        Get detailed information for a specific cluster node.

        Includes hardware inventory, drive configuration, disk partitions,
        sensors, sleds, network addresses, and node state.

        Arguments:
        - node_id: Logical Node Number (LNN) of the node to retrieve
        """
        cluster_api = isi_sdk.ClusterApi(self.cluster.api_client)
        try:
            result = cluster_api.get_cluster_node(node_id)
            nodes = result.nodes if result.nodes else []
            if nodes:
                return nodes[0].to_dict()
            return {"error": f"Node {node_id} not found"}
        except ApiException as e:
            return {"error": str(e)}
