import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class Hardware:
    """Provides access to PowerScale hardware inventory via the HardwareApi.

    Covers Fibre Channel ports and tape/changer devices.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get_fcports(self):
        """List all Fibre Channel ports on the cluster."""
        api = isi_sdk.HardwareApi(self.cluster.api_client)
        try:
            result = api.get_hardware_fcports()
            ports = result.fcports if hasattr(result, "fcports") and result.fcports else []
            return {"items": [p.to_dict() for p in ports]}
        except ApiException as e:
            return {"error": str(e)}

    def get_fcport(self, port_id: str):
        """Get details for a specific Fibre Channel port.

        Arguments:
        - port_id: The FC port identifier (e.g. '1:0')
        """
        api = isi_sdk.HardwareApi(self.cluster.api_client)
        try:
            result = api.get_hardware_fcport(port_id)
            ports = result.fcports if hasattr(result, "fcports") and result.fcports else []
            if ports:
                return ports[0].to_dict()
            return {"error": f"FC port '{port_id}' not found"}
        except ApiException as e:
            return {"error": str(e)}

    def get_tapes(self):
        """List all tape and changer devices on the cluster."""
        api = isi_sdk.HardwareApi(self.cluster.api_client)
        try:
            result = api.get_hardware_tapes()
            devices = result.devices if hasattr(result, "devices") and result.devices else []
            return {
                "items": [d.to_dict() for d in devices],
                "resume": getattr(result, "resume", None),
            }
        except ApiException as e:
            return {"error": str(e)}
