import isilon_sdk.v9_12_0 as isi_sdk

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

        result = stats_api.get_statistics_current(
            keys=keys,
            degraded=False,
            show_nodes=True,
            timeout=15
        )

        stats = {}
        for s in result.stats:
            value = s.value
            # Preserve values that are already numeric. Calling int() first would
            # truncate a native float — e.g. a dedupe/compression ratio of 1.5 -> 1
            # — silently corrupting the metric. The int()/float() parsing below is
            # only for numeric *strings* the SDK may return.
            if not isinstance(value, (int, float)):
                try:
                    # Try int first (numeric string like "42")
                    value = int(value)
                except (ValueError, TypeError):
                    try:
                        # Fall back to float (numeric string like "1.5")
                        value = float(value)
                    except (ValueError, TypeError):
                        # Keep as string if conversion fails
                        pass
            stats[s.key] = value
        return stats
