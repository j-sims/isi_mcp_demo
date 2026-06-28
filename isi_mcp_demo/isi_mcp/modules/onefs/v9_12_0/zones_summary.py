import isilon_sdk.v9_12_0 as isi_sdk


class ZonesSummary:

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self, groupnet: str = None):
        """
        Retrieve a summary of all access zones on the cluster.

        Returns the total zone count and a list of zone paths. This is a
        lightweight alternative to the full zones listing — useful for a
        quick count or to enumerate zone paths without auth-provider details.

        Arguments:
        - groupnet: Optional — filter summary to zones in this groupnet name
        """
        zones_summary_api = isi_sdk.ZonesSummaryApi(self.cluster.api_client)
        kwargs = {}
        if groupnet:
            kwargs["groupnet"] = groupnet
        result = zones_summary_api.get_zones_summary(**kwargs)
        summary = result.summary if result.summary else None
        if summary is None:
            return {"count": 0, "zones": []}
        d = summary.to_dict()
        # Normalise: the SDK uses 'list' as the field name for zone paths
        zones = d.get("list") or []
        return {
            "count": d.get("count", len(zones)),
            "zones": zones,
        }

    def get_zone(self, zone_id):
        """
        Retrieve non-privileged summary information for a specific access zone.

        Arguments:
        - zone_id: The zone name (e.g. "System") or numeric zone ID to retrieve
        """
        zones_summary_api = isi_sdk.ZonesSummaryApi(self.cluster.api_client)
        # Convert to string for URL path parameter
        zone_id_param = str(zone_id)
        result = zones_summary_api.get_zones_summary_zone(zone_id_param)
        summary = result.summary if result.summary else None
        if summary is None:
            return {"error": f"Zone {zone_id} not found"}
        return summary.to_dict()
