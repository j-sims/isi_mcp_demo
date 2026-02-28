import logging
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException

logger = logging.getLogger(__name__)


class Network:
    """Holds all read-only functions related to PowerScale network topology."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get_groupnets(self) -> list:
        """List all groupnets with DNS configuration."""
        network_api = isi_sdk.NetworkApi(self.cluster.api_client)
        try:
            result = network_api.list_network_groupnets()
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"error": str(e)}

        items = []
        for g in (result.groupnets or []):
            d = g.to_dict()
            items.append({
                "name": d.get("name"),
                "description": d.get("description"),
                "dns_servers": d.get("dns_servers", []),
                "dns_search": d.get("dns_search", []),
                "dns_cache_enabled": d.get("dns_cache_enabled"),
                "allow_wildcard_subdomains": d.get("allow_wildcard_subdomains"),
                "server_side_dns_search": d.get("server_side_dns_search"),
            })
        return items

    def get_subnets(self, groupnet: str = None) -> list:
        """List subnets, optionally filtered by groupnet name."""
        network_api = isi_sdk.NetworkApi(self.cluster.api_client)
        try:
            kwargs = {}
            if groupnet:
                kwargs["groupnet"] = groupnet
            result = network_api.get_network_subnets(**kwargs)
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"error": str(e)}

        items = []
        for s in (result.subnets or []):
            d = s.to_dict()
            # sc_service_addrs is a list of objects; extract addr strings
            sc_addrs = []
            for addr_obj in (d.get("sc_service_addrs") or []):
                if isinstance(addr_obj, dict):
                    sc_addrs.append(addr_obj.get("high") or addr_obj.get("low") or str(addr_obj))
                else:
                    sc_addrs.append(str(addr_obj))
            items.append({
                "name": d.get("name"),
                "groupnet": d.get("groupnet"),
                "description": d.get("description"),
                "addr_family": d.get("addr_family"),
                "gateway": d.get("gateway"),
                "gateway_priority": d.get("gateway_priority"),
                "prefixlen": d.get("prefixlen"),
                "mtu": d.get("mtu"),
                "vlan_enabled": d.get("vlan_enabled"),
                "vlan_id": d.get("vlan_id"),
                "sc_service_name": d.get("sc_service_name"),
                "sc_service_addrs": sc_addrs,
                "dsr_addrs": d.get("dsr_addrs", []),
            })
        return items

    def get_pools(self, groupnet: str = None, subnet: str = None,
                  access_zone: str = None) -> list:
        """List network pools with IP ranges and SmartConnect settings."""
        network_api = isi_sdk.NetworkApi(self.cluster.api_client)
        try:
            kwargs = {}
            if groupnet:
                kwargs["groupnet"] = groupnet
            if subnet:
                kwargs["subnet"] = subnet
            if access_zone:
                kwargs["access_zone"] = access_zone
            result = network_api.get_network_pools(**kwargs)
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"error": str(e)}

        items = []
        for p in (result.pools or []):
            d = p.to_dict()
            # Normalize ranges list
            ranges = []
            for r in (d.get("ranges") or []):
                if isinstance(r, dict):
                    ranges.append({"low": r.get("low"), "high": r.get("high")})
                else:
                    ranges.append(str(r))
            # Normalize ifaces list
            ifaces = []
            for iface in (d.get("ifaces") or []):
                if isinstance(iface, dict):
                    ifaces.append(iface.get("iface") or str(iface))
                else:
                    ifaces.append(str(iface))
            items.append({
                "name": d.get("name"),
                "groupnet": d.get("groupnet"),
                "subnet": d.get("subnet"),
                "description": d.get("description"),
                "access_zone": d.get("access_zone"),
                "addr_family": d.get("addr_family"),
                "alloc_method": d.get("alloc_method"),
                "ranges": ranges,
                "ifaces": ifaces,
                "sc_dns_zone": d.get("sc_dns_zone"),
                "sc_dns_zone_aliases": d.get("sc_dns_zone_aliases", []),
                "sc_connect_policy": d.get("sc_connect_policy"),
                "sc_failover_policy": d.get("sc_failover_policy"),
                "sc_ttl": d.get("sc_ttl"),
                "sc_subnet": d.get("sc_subnet"),
                "static_routes": d.get("static_routes", []),
                "rebalance_policy": d.get("rebalance_policy"),
            })
        return items

    def get_interfaces(self, lnn: int = None) -> list:
        """List node network interfaces, optionally filtered by logical node number."""
        network_api = isi_sdk.NetworkApi(self.cluster.api_client)
        try:
            kwargs = {}
            if lnn is not None:
                kwargs["lnn"] = [lnn]
            result = network_api.get_network_interfaces(**kwargs)
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"error": str(e)}

        items = []
        for iface in (result.interfaces or []):
            d = iface.to_dict()
            items.append({
                "id": d.get("id"),
                "name": d.get("name"),
                "nic_name": d.get("nic_name"),
                "lnn": d.get("lnn"),
                "type": d.get("type"),
                "linklayer": d.get("linklayer"),
                "status": d.get("status"),
                "ip_addrs": d.get("ip_addrs", []),
                "ipv4_gateway": d.get("ipv4_gateway"),
                "ipv6_gateway": d.get("ipv6_gateway"),
                "macaddr": d.get("macaddr"),
                "mtu": d.get("mtu"),
                "speed": d.get("speed"),
                "flags": d.get("flags", []),
                "owners": d.get("owners", []),
                "vlans": d.get("vlans", []),
            })
        return items

    def get_external(self) -> dict:
        """Get global external network settings."""
        network_api = isi_sdk.NetworkApi(self.cluster.api_client)
        try:
            result = network_api.get_network_external()
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"error": str(e)}

        d = result.to_dict() if hasattr(result, "to_dict") else {}
        # The result may have a nested 'settings' key
        settings = d.get("settings", d)
        return {
            "default_groupnet": settings.get("default_groupnet"),
            "ipv6_enabled": settings.get("ipv6_enabled"),
            "ipv6_accept_redirects": settings.get("ipv6_accept_redirects"),
            "ipv6_auto_config_enabled": settings.get("ipv6_auto_config_enabled"),
            "ipv6_dad_enabled": settings.get("ipv6_dad_enabled"),
            "ipv6_dad_timeout": settings.get("ipv6_dad_timeout"),
            "ipv6_generate_link_local": settings.get("ipv6_generate_link_local"),
            "sbr": settings.get("sbr"),
            "sc_rebalance_delay": settings.get("sc_rebalance_delay"),
            "sc_server_ttl": settings.get("sc_server_ttl"),
            "tcp_ports": settings.get("tcp_ports", []),
            "lagg_lacp_fast_timeout": settings.get("lagg_lacp_fast_timeout"),
        }

    def get_dns_cache(self) -> dict:
        """Get DNS cache configuration and TTL settings."""
        network_api = isi_sdk.NetworkApi(self.cluster.api_client)
        try:
            result = network_api.get_network_dnscache()
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"error": str(e)}

        d = result.to_dict() if hasattr(result, "to_dict") else {}
        settings = d.get("settings", d)
        return {
            "cache_entry_limit": settings.get("cache_entry_limit"),
            "cluster_timeout": settings.get("cluster_timeout"),
            "dns_timeout": settings.get("dns_timeout"),
            "eager_refresh": settings.get("eager_refresh"),
            "testping_delta": settings.get("testping_delta"),
            "ttl_min_noerror": settings.get("ttl_min_noerror"),
            "ttl_max_noerror": settings.get("ttl_max_noerror"),
            "ttl_min_nxdomain": settings.get("ttl_min_nxdomain"),
            "ttl_max_nxdomain": settings.get("ttl_max_nxdomain"),
            "ttl_min_servfail": settings.get("ttl_min_servfail"),
            "ttl_max_servfail": settings.get("ttl_max_servfail"),
            "ttl_min_other": settings.get("ttl_min_other"),
            "ttl_max_other": settings.get("ttl_max_other"),
        }

    def get_zones(self) -> list:
        """List all access zones with groupnet association and auth providers."""
        zones_api = isi_sdk.ZonesApi(self.cluster.api_client)
        try:
            result = zones_api.list_zones()
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"error": str(e)}

        items = []
        for z in (result.zones or []):
            d = z.to_dict()
            items.append({
                "name": d.get("name"),
                "id": d.get("id"),
                "groupnet": d.get("groupnet"),
                "path": d.get("path"),
                "description": d.get("description"),
                "auth_providers": d.get("auth_providers", []),
                "smb_shares_visible": d.get("smb_shares_visible"),
                "system_provider": d.get("system_provider"),
                "user_mapping_rules": d.get("user_mapping_rules", []),
                "home_directory_umask": d.get("home_directory_umask"),
                "ifs_restricted": d.get("ifs_restricted"),
            })
        return items

    def get_network_map(self) -> dict:
        """Build a comprehensive network topology map.

        Assembles groupnets → subnets → pools hierarchy and overlays
        access zones (linked by groupnet name) with their SMB shares.

        Returns a nested dict with partial failure isolation — if any
        sub-query fails, that section includes an 'error' key rather
        than aborting the entire map.
        """
        network_api = isi_sdk.NetworkApi(self.cluster.api_client)
        zones_api = isi_sdk.ZonesApi(self.cluster.api_client)
        protocols_api = isi_sdk.ProtocolsApi(self.cluster.api_client)

        # 1. Fetch all zones upfront; group by their groupnet
        zones_by_groupnet = {}
        try:
            zones_result = zones_api.list_zones()
            for z in (zones_result.zones or []):
                d = z.to_dict()
                gn = d.get("groupnet", "")
                zones_by_groupnet.setdefault(gn, []).append({
                    "name": d.get("name"),
                    "id": d.get("id"),
                    "groupnet": gn,
                    "path": d.get("path"),
                    "auth_providers": d.get("auth_providers", []),
                    "smb_shares_visible": d.get("smb_shares_visible"),
                })
        except ApiException as e:
            logger.error("API error fetching zones: %s", e)
            zones_by_groupnet = {}

        # 2. Fetch SMB shares per zone name
        def _get_smb_shares(zone_name: str) -> list:
            try:
                result = protocols_api.list_smb_shares(zone=zone_name, limit=1000)
                shares = []
                for s in (result.shares or []):
                    sd = s.to_dict()
                    shares.append({
                        "name": sd.get("name"),
                        "path": sd.get("path"),
                        "description": sd.get("description"),
                        "access_zone": sd.get("access_zone"),
                    })
                return shares
            except ApiException as e:
                logger.error("API error fetching SMB shares for zone '%s': %s", zone_name, e)
                return []

        # Attach SMB shares to each zone
        for gn_zones in zones_by_groupnet.values():
            for zone in gn_zones:
                zone["smb_shares"] = _get_smb_shares(zone["name"])

        # 3. Fetch all groupnets
        groupnets_out = []
        try:
            gn_result = network_api.list_network_groupnets()
            for g in (gn_result.groupnets or []):
                gd = g.to_dict()
                gn_name = gd.get("name", "")

                # 4. Fetch subnets for this groupnet
                subnets_out = []
                try:
                    sn_result = network_api.get_network_subnets(groupnet=gn_name)
                    for s in (sn_result.subnets or []):
                        sd = s.to_dict()
                        sn_name = sd.get("name", "")

                        # SmartConnect service addrs — extract as strings
                        sc_addrs = []
                        for addr_obj in (sd.get("sc_service_addrs") or []):
                            if isinstance(addr_obj, dict):
                                sc_addrs.append(addr_obj.get("high") or addr_obj.get("low") or str(addr_obj))
                            else:
                                sc_addrs.append(str(addr_obj))

                        # 5. Fetch pools for this groupnet+subnet
                        pools_out = []
                        try:
                            pool_result = network_api.get_network_pools(
                                groupnet=gn_name, subnet=sn_name
                            )
                            for p in (pool_result.pools or []):
                                pd = p.to_dict()
                                ranges = []
                                for r in (pd.get("ranges") or []):
                                    if isinstance(r, dict):
                                        ranges.append({"low": r.get("low"), "high": r.get("high")})
                                    else:
                                        ranges.append(str(r))
                                ifaces = []
                                for iface in (pd.get("ifaces") or []):
                                    if isinstance(iface, dict):
                                        ifaces.append(iface.get("iface") or str(iface))
                                    else:
                                        ifaces.append(str(iface))
                                pools_out.append({
                                    "name": pd.get("name"),
                                    "access_zone": pd.get("access_zone"),
                                    "alloc_method": pd.get("alloc_method"),
                                    "ranges": ranges,
                                    "ifaces": ifaces,
                                    "sc_dns_zone": pd.get("sc_dns_zone"),
                                    "sc_dns_zone_aliases": pd.get("sc_dns_zone_aliases", []),
                                    "sc_connect_policy": pd.get("sc_connect_policy"),
                                    "sc_failover_policy": pd.get("sc_failover_policy"),
                                    "sc_ttl": pd.get("sc_ttl"),
                                })
                        except ApiException as e:
                            logger.error("API error fetching pools for %s/%s: %s", gn_name, sn_name, e)
                            pools_out = [{"error": str(e)}]

                        subnets_out.append({
                            "name": sn_name,
                            "addr_family": sd.get("addr_family"),
                            "gateway": sd.get("gateway"),
                            "gateway_priority": sd.get("gateway_priority"),
                            "prefixlen": sd.get("prefixlen"),
                            "mtu": sd.get("mtu"),
                            "vlan_enabled": sd.get("vlan_enabled"),
                            "vlan_id": sd.get("vlan_id"),
                            "sc_service_name": sd.get("sc_service_name"),
                            "sc_service_addrs": sc_addrs,
                            "pools": pools_out,
                        })
                except ApiException as e:
                    logger.error("API error fetching subnets for groupnet '%s': %s", gn_name, e)
                    subnets_out = [{"error": str(e)}]

                groupnets_out.append({
                    "name": gn_name,
                    "description": gd.get("description"),
                    "dns_servers": gd.get("dns_servers", []),
                    "dns_search": gd.get("dns_search", []),
                    "dns_cache_enabled": gd.get("dns_cache_enabled"),
                    "subnets": subnets_out,
                    "zones": zones_by_groupnet.get(gn_name, []),
                })
        except ApiException as e:
            logger.error("API error fetching groupnets: %s", e)
            return {"error": str(e), "groupnets": []}

        return {"groupnets": groupnets_out}
