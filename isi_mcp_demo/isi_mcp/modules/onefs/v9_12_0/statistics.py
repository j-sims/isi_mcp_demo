import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class Statistics:
    """Provides access to PowerScale real-time performance statistics via the StatisticsApi."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def _check_node_stats_available(self):
        """
        Check if per-node statistics are available on this cluster.

        Virtual cluster deployments may have limited per-node stats.
        This performs a quick test by attempting to fetch a single node stat.

        Returns:
            Boolean: True if per-node stats are available, False otherwise
        """
        stats_api = isi_sdk.StatisticsApi(self.cluster.api_client)
        try:
            # Try to fetch a single node stat
            result = stats_api.get_statistics_current(
                keys=["node.load.1min"],
                degraded=False,
                show_nodes=True,
                timeout=5,
            )
            # Check if we got back any node-specific data (not just cluster aggregate)
            if result.stats:
                for stat in result.stats:
                    if stat.devid is not None:
                        return True
            return False
        except ApiException:
            # If API call fails, assume unavailable
            return False

    def _fetch_current(self, keys, show_nodes=False):
        """Single instantaneous poll for the given stat keys.

        The PowerScale statistics endpoint returns a sample every ~5 seconds.
        Call this method multiple times (waiting ≥5 seconds between calls) to
        collect a series of samples for trending or averaging.

        Args:
            keys: List of stat key strings to retrieve.
            show_nodes: If True, group results by node device ID. If False,
                        return cluster-aggregate values.

        Returns:
            When show_nodes=False: {key: value, "_sample_time": <unix_ts>} dict.
            When show_nodes=True: {"node_<devid>": {key: value}, "_sample_time": <unix_ts>} dict.
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
            """Convert stat values to JSON-serializable Python types."""
            if value is None:
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    if isinstance(value, list):
                        out = []
                        for item in value:
                            if hasattr(item, "to_dict"):
                                out.append(item.to_dict())
                            elif isinstance(item, dict):
                                out.append(item)
                            else:
                                out.append(str(item))
                        return out
                    return value

        sample_time = None

        if not show_nodes:
            data = {}
            for s in result.stats:
                if sample_time is None and hasattr(s, "time") and s.time is not None:
                    sample_time = s.time
                data[s.key] = _coerce(s.value)
            if sample_time is not None:
                data["_sample_time"] = sample_time
            return data

        # Per-node grouping
        nodes = {}
        for s in result.stats:
            if sample_time is None and hasattr(s, "time") and s.time is not None:
                sample_time = s.time
            devid = f"node_{s.devid}" if s.devid is not None else "cluster"
            if devid not in nodes:
                nodes[devid] = {}
            nodes[devid][s.key] = _coerce(s.value)
        if sample_time is not None:
            nodes["_sample_time"] = sample_time
        return nodes

    def get_cpu(self):
        """Retrieve a single instantaneous cluster CPU utilization sample.

        Returns:
            Dict with keys: cluster.cpu.sys.avg, cluster.cpu.user.avg,
            cluster.cpu.idle.avg, cluster.cpu.intr.avg (all in percent),
            and _sample_time (Unix timestamp of the sample).
        """
        keys = [
            "cluster.cpu.sys.avg",
            "cluster.cpu.user.avg",
            "cluster.cpu.idle.avg",
            "cluster.cpu.intr.avg",
        ]
        return self._fetch_current(keys)

    def get_network(self):
        """Retrieve a single instantaneous cluster external network traffic sample.

        Returns:
            Dict with byte rates, packet rates, and error rates for external
            cluster network interfaces (bytes/sec, packets/sec, errors/sec),
            and _sample_time (Unix timestamp of the sample).
        """
        keys = [
            "cluster.net.ext.bytes.in.rate",
            "cluster.net.ext.bytes.out.rate",
            "cluster.net.ext.packets.in.rate",
            "cluster.net.ext.packets.out.rate",
            "cluster.net.ext.errors.in.rate",
            "cluster.net.ext.errors.out.rate",
        ]
        return self._fetch_current(keys)

    def get_disk(self):
        """Retrieve a single instantaneous cluster disk I/O sample.

        Returns:
            Dict with cluster-level disk byte rates and transfer rates
            (bytes/sec and transfers/sec), and _sample_time (Unix timestamp
            of the sample).
        """
        keys = [
            "cluster.disk.bytes.in.rate",
            "cluster.disk.bytes.out.rate",
            "cluster.disk.xfers.in.rate",
            "cluster.disk.xfers.out.rate",
            "cluster.disk.xfers.rate",
        ]
        return self._fetch_current(keys)

    def get_ifs(self):
        """Retrieve a single instantaneous OneFS filesystem I/O sample.

        Returns:
            Dict with filesystem-level byte rates and operation rates
            (bytes/sec and ops/sec at the IFS layer), and _sample_time
            (Unix timestamp of the sample).
        """
        keys = [
            "ifs.bytes.in.rate",
            "ifs.bytes.out.rate",
            "ifs.ops.in.rate",
            "ifs.ops.out.rate",
        ]
        return self._fetch_current(keys)

    def get_node_performance(self):
        """Retrieve a single instantaneous per-node performance sample.

        Note: Per-node statistics may be unavailable on virtual cluster deployments.
        If unavailable, a warning note is included in the result.

        Returns:
            Dict keyed by "node_<devid>", each containing load averages,
            memory usage, CPU throttling, and open file count per node.
            Top-level _sample_time key contains the Unix timestamp of the sample.
            If unavailable, includes "_warning" key with explanation.
        """
        keys_full = [
            "node.cpu.throttling",
            "node.load.1min",
            "node.load.5min",
            "node.load.15min",
            "node.memory.used",
            "node.memory.free",
            "node.open.files",
        ]
        keys_fallback = [k for k in keys_full if k != "node.cpu.throttling"]

        result = self._fetch_current(keys_full, show_nodes=True)

        # node.cpu.throttling is unavailable on some clusters (e.g. virtual); retry without it
        if "error" in result:
            result = self._fetch_current(keys_fallback, show_nodes=True)
            if "error" not in result:
                result["_note"] = "node.cpu.throttling is not available on this cluster and was excluded."

        # Check availability and add warning if needed
        if isinstance(result, dict) and "error" not in result:
            node_entries = {k: v for k, v in result.items() if k.startswith("node_")}
            if not node_entries:
                result["_warning"] = "Per-node statistics are not available on this cluster. This is typical for virtual cluster deployments. Use cluster-level statistics (powerscale_stats_cpu, powerscale_stats_network, etc.) instead."

        return result

    def get_protocol(self):
        """Retrieve a single instantaneous per-protocol operation rate sample.

        Returns:
            Dict with ops/sec for NFS, NFSv4, SMB/CIFS, SMB2, HTTP, FTP, HDFS,
            and _sample_time (Unix timestamp of the sample).
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
        return self._fetch_current(keys)

    def get_clients(self):
        """Retrieve a single instantaneous client connection count sample.

        Returns:
            Dict with active and connected client counts per protocol
            (NFS, NFSv4, CIFS, SMB2, HTTP, FTP, HDFS). These are
            cluster-aggregate values (sum across all nodes), plus
            _sample_time (Unix timestamp of the sample).
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
        return self._fetch_current(keys)

    def get_current(self, keys, show_nodes=False):
        """Retrieve a single instantaneous statistics sample for arbitrary user-specified keys.

        Args:
            keys: List of stat key strings to retrieve.
            show_nodes: If True, return per-node breakdown; if False, cluster totals.

        Returns:
            Dict for the requested keys plus _sample_time (Unix timestamp).
        """
        return self._fetch_current(keys, show_nodes=show_nodes)

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
