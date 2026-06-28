import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.utils.errors import safe_api_error

class Config:

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self):
        cluster_api = isi_sdk.ClusterApi(self.cluster.api_client)

        result = cluster_api.get_cluster_config()

        config = result.to_dict()

        hardware_info = self.get_hardware_info()
        if "error" not in hardware_info:
            config["hardware"] = hardware_info

        return config

    def get_hardware_info(self):
        """Gather hardware configuration via the isilon SDK.

        Returns a dict with keys: nodes, node_pools, storage_pool_tiers.
        On failure, returns a dict with an 'error' key.
        """
        cluster_api = isi_sdk.ClusterApi(self.cluster.api_client)
        storagepool_api = isi_sdk.StoragepoolApi(self.cluster.api_client)

        # Hardware info is best-effort: get() treats a returned {"error": ...} as a
        # signal to omit the optional "hardware" key rather than fail the whole
        # cluster-config fetch. Honor that documented contract by catching here
        # instead of letting an ApiException propagate and abort get().
        try:
            nodes = cluster_api.get_cluster_nodes()
            node_pools = storagepool_api.list_storagepool_nodepools()
            tiers = storagepool_api.list_storagepool_tiers()
        except ApiException as e:
            return {"error": safe_api_error(e)}

        return {
            "nodes": nodes.to_dict().get("nodes", []),
            "node_pools": node_pools.to_dict().get("nodepools", []),
            "storage_pool_tiers": tiers.to_dict().get("tiers", []),
        }
