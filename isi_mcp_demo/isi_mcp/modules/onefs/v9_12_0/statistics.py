import time
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class Statistics:
    """Provides access to PowerScale real-time performance statistics via the StatisticsApi."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def _fetch_current(self, keys, show_nodes=False):
        """Single instantaneous poll for the given stat keys.

        Args:
            keys: List of stat key strings to retrieve.
            show_nodes: If True, group results by node device ID. If False,
                        return cluster-aggregate values.

        Returns:
            When show_nodes=False: {key: value} flat dict.
            When show_nodes=True: {"node_<devid>": {key: value}} dict.
            On error: {"error": str(e)}
        """
        stats_api = isi_sdk.StatisticsApi(self.cluster.api_client)
        try:
            result = stats_api.get_statistics_current(
                keys=keys,
                degraded=False,
                show_nodes=show_nodes,
                timeout=15,
            )
        except ApiException as e:
            return {"error": str(e)}

        def _coerce(value):
            """Convert numeric strings to int or float."""
            try:
                return int(value)
            except (ValueError, TypeError):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return value

        if not show_nodes:
            return {s.key: _coerce(s.value) for s in result.stats}

        # Per-node grouping
        nodes = {}
        for s in result.stats:
            devid = f"node_{s.devid}" if s.devid is not None else "cluster"
            if devid not in nodes:
                nodes[devid] = {}
            nodes[devid][s.key] = _coerce(s.value)
        return nodes

    def _fetch_averaged(self, keys, show_nodes=False, samples=6, interval=5):
        """Take multiple samples and return averaged values for a smoother reading.

        Default: 6 samples × 5 seconds = 30-second averaging window.

        Args:
            keys: List of stat key strings to retrieve.
            show_nodes: If True, group results by node device ID.
            samples: Number of readings to take.
            interval: Seconds between each reading.

        Returns:
            Same dict shape as _fetch_current, but with averaged numeric values.
        """
        accumulated = {}  # key -> list of values  (flat mode)
        node_accumulated = {}  # node -> key -> list of values  (per-node mode)

        for i in range(samples):
            if i > 0:
                time.sleep(interval)
            data = self._fetch_current(keys, show_nodes=show_nodes)

            if "error" in data:
                # Propagate first error encountered
                return data

            if not show_nodes:
                for key, value in data.items():
                    if isinstance(value, (int, float)):
                        accumulated.setdefault(key, []).append(value)
                    else:
                        accumulated[key] = value  # non-numeric: keep last value
            else:
                for node, node_data in data.items():
                    node_accumulated.setdefault(node, {})
                    for key, value in node_data.items():
                        if isinstance(value, (int, float)):
                            node_accumulated[node].setdefault(key, []).append(value)
                        else:
                            node_accumulated[node][key] = value

        if not show_nodes:
            return {
                key: (sum(vals) / len(vals) if isinstance(vals, list) else vals)
                for key, vals in accumulated.items()
            }

        return {
            node: {
                key: (sum(vals) / len(vals) if isinstance(vals, list) else vals)
                for key, vals in key_data.items()
            }
            for node, key_data in node_accumulated.items()
        }

    def get_cpu(self):
        """Retrieve 30-second averaged cluster CPU utilization metrics.

        Returns:
            Dict with keys: cluster.cpu.sys.avg, cluster.cpu.user.avg,
            cluster.cpu.idle.avg, cluster.cpu.intr.avg (all in percent).
        """
        keys = [
            "cluster.cpu.sys.avg",
            "cluster.cpu.user.avg",
            "cluster.cpu.idle.avg",
            "cluster.cpu.intr.avg",
        ]
        return self._fetch_averaged(keys)

    def get_network(self):
        """Retrieve 30-second averaged cluster external network traffic metrics.

        Returns:
            Dict with byte rates, packet rates, and error rates for external
            cluster network interfaces (bytes/sec, packets/sec, errors/sec).
        """
        keys = [
            "cluster.net.ext.bytes.in.rate",
            "cluster.net.ext.bytes.out.rate",
            "cluster.net.ext.packets.in.rate",
            "cluster.net.ext.packets.out.rate",
            "cluster.net.ext.errors.in.rate",
            "cluster.net.ext.errors.out.rate",
        ]
        return self._fetch_averaged(keys)

    def get_disk(self):
        """Retrieve 30-second averaged cluster disk I/O metrics.

        Returns:
            Dict with cluster-level disk byte rates and transfer rates
            (bytes/sec and transfers/sec).
        """
        keys = [
            "cluster.disk.bytes.in.rate",
            "cluster.disk.bytes.out.rate",
            "cluster.disk.xfers.in.rate",
            "cluster.disk.xfers.out.rate",
            "cluster.disk.xfers.rate",
        ]
        return self._fetch_averaged(keys)

    def get_ifs(self):
        """Retrieve 30-second averaged OneFS filesystem I/O rates.

        Returns:
            Dict with filesystem-level byte rates and operation rates
            (bytes/sec and ops/sec at the IFS layer).
        """
        keys = [
            "ifs.bytes.in.rate",
            "ifs.bytes.out.rate",
            "ifs.ops.in.rate",
            "ifs.ops.out.rate",
        ]
        return self._fetch_averaged(keys)

    def get_node_performance(self):
        """Retrieve 30-second averaged per-node performance metrics.

        Returns:
            Dict keyed by "node_<devid>", each containing load averages,
            memory usage, CPU throttling, and open file count per node.
        """
        keys = [
            "node.cpu.throttling",
            "node.load.1min",
            "node.load.5min",
            "node.load.15min",
            "node.memory.used",
            "node.memory.free",
            "node.open.files",
        ]
        return self._fetch_averaged(keys, show_nodes=True)

    def get_protocol(self):
        """Retrieve 30-second averaged per-protocol operation rates.

        Returns:
            Dict with ops/sec for NFS, NFSv4, SMB/CIFS, SMB2, HTTP, FTP, HDFS.
            Values represent current operation rates (not cumulative totals).
        """
        keys = [
            "cluster.protostats.nfs",
            "cluster.protostats.nfs4",
            "cluster.protostats.cifs",
            "cluster.protostats.smb2",
            "cluster.protostats.http",
            "cluster.protostats.ftp",
            "cluster.protostats.hdfs",
        ]
        return self._fetch_averaged(keys)

    def get_clients(self):
        """Retrieve 30-second averaged client connection counts by protocol.

        Returns:
            Dict with active and connected client counts per protocol
            (NFS, NFSv4, CIFS, SMB2, HTTP, FTP, HDFS). These are
            cluster-aggregate values (sum across all nodes).
        """
        keys = [
            "node.clientstats.active.nfs",
            "node.clientstats.active.nfs4",
            "node.clientstats.active.cifs",
            "node.clientstats.active.smb2",
            "node.clientstats.active.http",
            "node.clientstats.active.ftp",
            "node.clientstats.active.hdfs",
            "node.clientstats.connected.nfs",
            "node.clientstats.connected.cifs",
            "node.clientstats.connected.http",
        ]
        return self._fetch_averaged(keys)

    def get_current(self, keys, show_nodes=False):
        """Retrieve 30-second averaged statistics for arbitrary user-specified keys.

        Args:
            keys: List of stat key strings to retrieve.
            show_nodes: If True, return per-node breakdown; if False, cluster totals.

        Returns:
            Averaged dict for the requested keys.
        """
        return self._fetch_averaged(keys, show_nodes=show_nodes)

    def get_keys(self, limit=100, resume=None, queryable=False):
        """List available statistics keys with metadata.

        Args:
            limit: Maximum number of keys to return per page.
            resume: Pagination token from a previous call.
            queryable: If True, return only keys that can be queried.

        Returns:
            Dict with 'keys' list (each item has 'key', 'description', 'units',
            'type') and 'resume' pagination token.
        """
        stats_api = isi_sdk.StatisticsApi(self.cluster.api_client)
        try:
            kwargs = {"limit": limit}
            if resume:
                kwargs["resume"] = resume
            if queryable:
                kwargs["queryable"] = True
            result = stats_api.get_statistics_keys(**kwargs)
        except ApiException as e:
            return {"keys": [], "resume": None, "error": str(e)}

        keys_out = []
        if result.keys:
            for k in result.keys:
                entry = {"key": k.key}
                if hasattr(k, "description") and k.description:
                    entry["description"] = k.description
                if hasattr(k, "units") and k.units:
                    entry["units"] = k.units
                if hasattr(k, "type") and k.type:
                    entry["type"] = k.type
                keys_out.append(entry)

        return {
            "keys": keys_out,
            "resume": getattr(result, "resume", None),
            "has_more": bool(getattr(result, "resume", None)),
        }
