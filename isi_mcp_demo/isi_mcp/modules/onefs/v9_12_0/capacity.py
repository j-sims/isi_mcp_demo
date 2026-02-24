import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.network.utils import pingable

class Capacity:

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug
        
    def get(self):
        stats_api = isi_sdk.StatisticsApi(self.cluster.api_client)

        keys = [
            "ifs.bytes.avail",
            "ifs.bytes.used",
            "ifs.bytes.total",
            "cluster.data.reduce.ratio.dedupe",
            "cluster.compression.overall.ratio",

        ]

        try:
            result = stats_api.get_statistics_current(
                keys=keys,
                degraded=False,
                show_nodes=True,
                timeout=15
            )
        except ApiException as e:
            print(f"API error: {e}")
            return

        stats = {}
        for s in result.stats:
            # Convert numeric string values to int/float
            value = s.value
            try:
                # Try int first
                value = int(value)
            except (ValueError, TypeError):
                try:
                    # Fall back to float
                    value = float(value)
                except (ValueError, TypeError):
                    # Keep as string if conversion fails
                    pass
            stats[s.key] = value
        return stats