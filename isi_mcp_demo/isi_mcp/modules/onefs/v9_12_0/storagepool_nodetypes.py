import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class StoragepoolNodetypes:

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self):
        """
        List all storage pool node types configured on the cluster.

        Node types group compatible hardware nodes together for storage pool
        management. Each entry includes the product name, associated node IDs,
        and whether the node type was manually assigned.
        """
        storagepool_api = isi_sdk.StoragepoolApi(self.cluster.api_client)
        try:
            result = storagepool_api.get_storagepool_nodetypes()
            nodetypes = result.nodetypes if result.nodetypes else []
            return {
                "items": [n.to_dict() for n in nodetypes],
                "total": getattr(result, "total", len(nodetypes)),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_by_id(self, nodetype_id: int):
        """
        Get details for a specific storage pool node type by ID.

        Arguments:
        - nodetype_id: The integer node type ID to retrieve
        """
        storagepool_api = isi_sdk.StoragepoolApi(self.cluster.api_client)
        try:
            result = storagepool_api.get_storagepool_nodetype(nodetype_id)
            nodetypes = result.nodetypes if result.nodetypes else []
            if nodetypes:
                return nodetypes[0].to_dict()
            return {"error": f"Node type {nodetype_id} not found"}
        except ApiException as e:
            return {"error": str(e)}
