import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.network.utils import pingable

class Health:

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = self.cluster.debug
        self.cluster_api = isi_sdk.ClusterApi(self.cluster.api_client)
    
    def check(self):
        if not self.check_quorum():
            return { "status" : False, "message":"Cluster does not have quorum" } # Fail health check if quorum is false
        if self.check_servicelight():
            return { "status" : False, "message":"One or more servicelights are on" } # Fail health check if servicelight is true
        if len(self.get_critical_events()) > 0:
            return { "status" : False, "message":"There are unresolved critical events" } # Fail if there are critical events
        if not self.check_all_nodes_pingable():
            return { "status" : False, "message":"All external IPs are not reachable" } # Fail if any nodes are not on the network
        ifs_percent_free = self.get_ifs_percent_free()
        if ifs_percent_free <= 20:
            return { "status" : False, "message":f"Cluster is getting low on space - {ifs_percent_free}% Remaining" } # Fail if any nodes are not on the network

        return({"status": True, "message": "Cluster is healthy"})

    def check_quorum(self):
        resp = self.cluster_api.get_cluster_config()

        try:
            quorum = resp.has_quorum
        except Exception:
            quorum = resp.get('has_quorum') if isinstance(resp, dict) else None

        return quorum

    def check_servicelight(self):
        nodes = self.cluster_api.get_cluster_nodes().nodes
        for node in nodes:
            if node.state.servicelight.enabled:
                return node.state.servicelight.enabled

    def get_nodes(self):
        return self.cluster_api.get_cluster_nodes()
        
    def get_critical_events(self):

        events_api = isi_sdk.EventApi(self.cluster.api_client)

        try:
            # list event groups (high-level clusters of events)
            event_groups = events_api.get_event_eventgroup_occurrences(resolved="false", ignore="false").eventgroups
            critical_events = []

            for group in event_groups:
                # check group severity (if the property exists)
                if getattr(group, "severity", "").lower() == "critical":
                    critical_events.append(group)

            if critical_events:
                for ce in critical_events:
                    return ce.to_dict()
            else:
                return []

        except ApiException as e:
            print(f"Exception calling EventsApi: {e}")

    def check_all_nodes_pingable(self):
        nodes = self.cluster_api.get_cluster_external_ips()
        for node in nodes:
            if self.debug:
                print(f"Checking Node {node}")
            if not pingable(node, debug=self.debug):
                if self.debug:
                    print(f"Node {node} Failed")
                return False
        return True

    def get_ifs_percent_free(self):
        stats_api = isi_sdk.StatisticsApi(self.cluster.api_client)

        keys = [
            "ifs.bytes.avail",
            "ifs.bytes.used",
            "ifs.bytes.total",
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
            stats[s.key] = s.value

        percent_free = float(stats.get('ifs.bytes.avail', 0)) / float(stats.get('ifs.bytes.total', 0))
        return (round(percent_free * 100, 2))


