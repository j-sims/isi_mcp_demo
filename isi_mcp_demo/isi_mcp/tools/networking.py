from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.network import Network
from typing import Dict, Any, Optional, Any as AnyType


@safe_tool(group="networking", mode="read")
def powerscale_network_groupnets_get(cluster_name: str = None) -> AnyType:
    """
    List all network groupnets on the PowerScale cluster.

    Groupnets are the top-level network partitioning construct in PowerScale.
    Each groupnet contains one or more subnets and has its own DNS configuration.
    Access zones are associated with a groupnet, enabling multi-tenancy.

    Response fields per groupnet:
    - name:               Groupnet name (e.g. "groupnet0")
    - description:        Human-readable description
    - dns_servers:        List of DNS server IP addresses
    - dns_search:         List of DNS search domain suffixes
    - dns_cache_enabled:  Whether DNS caching is enabled for this groupnet
    - allow_wildcard_subdomains: Whether wildcard subdomain resolution is allowed
    - server_side_dns_search:   Whether server-side DNS search is enabled

    Use this tool to understand:
    - How the cluster network is partitioned into groupnets
    - What DNS servers and search domains are configured per groupnet
    - The top-level groupnet names needed to filter subnets and pools
    """
    cluster = get_cluster(cluster_name)
    network = Network(cluster)
    return network.get_groupnets()


@safe_tool(group="networking", mode="read")
def powerscale_network_subnets_get(
    groupnet: Optional[str] = None,
    cluster_name: str = None,
) -> AnyType:
    """
    List network subnets on the PowerScale cluster.

    Subnets belong to a groupnet and define the IP address space, gateway,
    MTU, VLAN configuration, and SmartConnect service settings for a network
    segment.

    Arguments:
    - groupnet: Optional groupnet name to filter results (e.g. "groupnet0").
                If omitted, all subnets across all groupnets are returned.

    Response fields per subnet:
    - name:             Subnet name (e.g. "subnet0")
    - groupnet:         Parent groupnet name
    - addr_family:      Address family: "ipv4" or "ipv6"
    - gateway:          Default gateway IP address
    - gateway_priority: Gateway priority (lower = preferred)
    - prefixlen:        Subnet prefix length (e.g. 24 for /24)
    - mtu:              Maximum transmission unit in bytes
    - vlan_enabled:     Whether VLAN tagging is enabled
    - vlan_id:          VLAN tag ID (if vlan_enabled)
    - sc_service_name:  SmartConnect DNS zone name for this subnet
    - sc_service_addrs: SmartConnect service IP addresses (listen IPs for DNS)
    - dsr_addrs:        Direct Server Return IP addresses

    Use this tool to understand:
    - What IP subnets are configured on the cluster
    - Gateway and routing configuration per subnet
    - SmartConnect DNS zone names and service IPs per subnet
    - VLAN configuration
    """
    cluster = get_cluster(cluster_name)
    network = Network(cluster)
    return network.get_subnets(groupnet=groupnet)


@safe_tool(group="networking", mode="read")
def powerscale_network_pools_get(
    groupnet: Optional[str] = None,
    subnet: Optional[str] = None,
    access_zone: Optional[str] = None,
    cluster_name: str = None,
) -> AnyType:
    """
    List network pools on the PowerScale cluster.

    Pools define the IP address ranges assigned to cluster nodes, the network
    interfaces they use, and SmartConnect load-balancing configuration.
    Each pool is associated with an access zone.

    Arguments:
    - groupnet:    Optional groupnet name filter (e.g. "groupnet0")
    - subnet:      Optional subnet name filter (e.g. "subnet0")
    - access_zone: Optional access zone name filter (e.g. "System")

    Response fields per pool:
    - name:               Pool name (e.g. "pool0")
    - groupnet:           Parent groupnet name
    - subnet:             Parent subnet name
    - access_zone:        Access zone this pool serves
    - addr_family:        "ipv4" or "ipv6"
    - alloc_method:       IP allocation method: "static" or "dynamic"
    - ranges:             List of IP ranges: [{"low": "x.x.x.x", "high": "x.x.x.x"}]
    - ifaces:             List of network interface names assigned to this pool
    - sc_dns_zone:        SmartConnect DNS zone name for this pool
    - sc_dns_zone_aliases: Additional SmartConnect DNS zone aliases
    - sc_connect_policy:  Client connection balancing policy (e.g. "round_robin")
    - sc_failover_policy: Failover policy when nodes are down
    - sc_ttl:             SmartConnect DNS TTL in seconds
    - static_routes:      Static routing rules for this pool
    - rebalance_policy:   IP rebalancing policy after node rejoins

    Use this tool to understand:
    - What IP addresses are available for client connections
    - Which interfaces are in each pool
    - How SmartConnect load-balances client connections per pool
    - IP ranges served by each access zone
    """
    cluster = get_cluster(cluster_name)
    network = Network(cluster)
    return network.get_pools(groupnet=groupnet, subnet=subnet, access_zone=access_zone)


@safe_tool(group="networking", mode="read")
def powerscale_network_interfaces_get(
    lnn: Optional[int] = None,
    cluster_name: str = None,
) -> AnyType:
    """
    List network interfaces on PowerScale cluster nodes.

    Returns physical and virtual network interface information for each node,
    including IP addresses, link layer type, MAC address, and pool membership.

    Arguments:
    - lnn: Optional logical node number to filter results to a single node.
           If omitted, interfaces from all nodes are returned.

    Response fields per interface:
    - id:           Interface ID in format "lnn:name" (e.g. "1:ext-1")
    - name:         Interface name (e.g. "ext-1")
    - nic_name:     Physical NIC name
    - lnn:          Logical node number
    - type:         Interface type (e.g. "vlan", "aggregated")
    - linklayer:    Link layer type: "ethernet" or "aggregated"
    - status:       Interface status: "up", "down", or "no_carrier"
    - ip_addrs:     List of IP addresses assigned to this interface
    - ipv4_gateway: IPv4 gateway for this interface
    - ipv6_gateway: IPv6 gateway for this interface
    - macaddr:      MAC address
    - mtu:          Maximum transmission unit in bytes
    - speed:        Interface speed in Mbps
    - flags:        List of interface flags
    - owners:       List of pool names that own this interface
    - vlans:        List of VLAN IDs configured on this interface

    Use this tool to understand:
    - Which physical interfaces are on each node
    - Interface status and IP assignments per node
    - Which pools own which interfaces
    - Network interface link state and speed
    """
    cluster = get_cluster(cluster_name)
    network = Network(cluster)
    return network.get_interfaces(lnn=lnn)


@safe_tool(group="networking", mode="read")
def powerscale_network_external_get(cluster_name: str = None) -> Dict[str, Any]:
    """
    Get global external network settings for the PowerScale cluster.

    Returns cluster-wide networking configuration including IPv6 settings,
    SmartConnect defaults, source-based routing, and TCP port configuration.

    Response fields:
    - default_groupnet:          Default groupnet for non-multitenant programs
    - ipv6_enabled:              Whether IPv6 is enabled on external interfaces
    - ipv6_accept_redirects:     Whether ICMPv6 redirects are processed
    - ipv6_auto_config_enabled:  Whether IPv6 auto-configuration (rtsold) is on
    - ipv6_dad_enabled:          Whether Duplicate Address Detection is enabled on pools
    - ipv6_dad_timeout:          DAD completion timeout in seconds
    - ipv6_generate_link_local:  Whether Link Local addresses are auto-generated
    - sbr:                       Whether Source-Based Routing is enabled
    - sc_rebalance_delay:        Seconds to wait before rebalancing SmartConnect IPs
    - sc_server_ttl:             TTL for SmartConnect NS and SOA DNS records
    - tcp_ports:                 List of available client TCP port ranges
    - lagg_lacp_fast_timeout:    Whether LACP fast timeout mode is enabled

    Use this tool to understand:
    - Global IPv6 configuration
    - SmartConnect rebalance behavior
    - Source-based routing configuration
    - Available TCP ports for client connections
    """
    cluster = get_cluster(cluster_name)
    network = Network(cluster)
    return network.get_external()


@safe_tool(group="networking", mode="read")
def powerscale_network_dns_get(cluster_name: str = None) -> Dict[str, Any]:
    """
    Get DNS cache configuration and TTL settings for the PowerScale cluster.

    Returns the cluster-wide DNS cache settings that control how DNS query
    responses are cached, including TTL bounds per response type.

    Response fields:
    - cache_entry_limit:   Maximum number of entries in the DNS cache
    - cluster_timeout:     Timeout for cluster-internal DNS queries (seconds)
    - dns_timeout:         Timeout for external DNS queries (seconds)
    - eager_refresh:       Lead time before cache entry expiry to pre-refresh (seconds)
    - testping_delta:      Interval between connectivity test pings (seconds)
    - ttl_min_noerror:     Minimum TTL for successful DNS responses (seconds)
    - ttl_max_noerror:     Maximum TTL for successful DNS responses (seconds)
    - ttl_min_nxdomain:    Minimum TTL for NXDOMAIN (domain not found) responses
    - ttl_max_nxdomain:    Maximum TTL for NXDOMAIN responses
    - ttl_min_servfail:    Minimum TTL for SERVFAIL responses
    - ttl_max_servfail:    Maximum TTL for SERVFAIL responses
    - ttl_min_other:       Minimum TTL for other failure responses
    - ttl_max_other:       Maximum TTL for other failure responses

    Use this tool to understand:
    - How aggressively DNS responses are cached
    - DNS query timeout configuration
    - Cache size limits
    """
    cluster = get_cluster(cluster_name)
    network = Network(cluster)
    return network.get_dns_cache()


@safe_tool(group="networking", mode="read")
def powerscale_zones_get(cluster_name: str = None) -> AnyType:
    """
    List all access zones on the PowerScale cluster.

    Access zones provide multi-tenancy by partitioning the cluster into isolated
    namespaces, each with its own authentication providers, SMB shares, NFS
    exports, and network groupnet association.

    Response fields per zone:
    - name:               Zone name (e.g. "System", "Zone2")
    - id:                 Numeric zone ID
    - groupnet:           Network groupnet this zone is associated with
    - path:               Root IFS path for this zone (e.g. "/ifs")
    - description:        Human-readable description
    - auth_providers:     List of authentication providers (e.g. ["lsa-local-provider:System"])
    - smb_shares_visible: Whether all SMB shares are visible or only accessible ones
    - system_provider:    The default system authentication provider name
    - user_mapping_rules: List of user identity mapping rules
    - home_directory_umask: Default umask for user home directories (octal)
    - ifs_restricted:     Whether IFS access is restricted to the zone path

    Use this tool to understand:
    - How the cluster is partitioned into access zones
    - Which groupnet (and therefore which subnet/pool) each zone uses
    - Authentication providers per zone
    - Zone root paths (used to scope file access)

    Use powerscale_network_map for a comprehensive view that joins zones
    with their groupnet, subnets, pools, and SMB shares in one response.
    """
    cluster = get_cluster(cluster_name)
    network = Network(cluster)
    return network.get_zones()


@safe_tool(group="networking", mode="read")
def powerscale_network_map(cluster_name: str = None) -> Dict[str, Any]:
    """
    Return a comprehensive network topology map of the PowerScale cluster.

    This tool assembles the complete network hierarchy in a single response,
    making it easy to understand how network resources relate to each other
    and to the file-serving infrastructure.

    The response structure is:
    {
      "groupnets": [
        {
          "name": "groupnet0",
          "dns_servers": ["x.x.x.x"],
          "dns_search": ["example.com"],
          "subnets": [
            {
              "name": "subnet0",
              "gateway": "x.x.x.x",
              "prefixlen": 24,
              "sc_service_name": "smartconnect.example.com",
              "sc_service_addrs": ["x.x.x.x"],
              "pools": [
                {
                  "name": "pool0",
                  "access_zone": "System",
                  "ranges": [{"low": "x.x.x.x", "high": "x.x.x.x"}],
                  "sc_dns_zone": "pool.example.com",
                  "sc_connect_policy": "round_robin",
                  "ifaces": ["ext-1:1"]
                }
              ]
            }
          ],
          "zones": [
            {
              "name": "System",
              "path": "/ifs",
              "auth_providers": ["lsa-local-provider:System"],
              "smb_shares": [
                {"name": "share1", "path": "/ifs/data", "description": "..."}
              ]
            }
          ]
        }
      ]
    }

    Key relationships:
    - groupnet → subnets → pools: The network hierarchy (groupnet owns subnets,
      subnets own pools). Pools contain IP address ranges and SmartConnect config.
    - groupnet → zones: Each access zone references a groupnet. Zones scoped to
      the same groupnet share the same network segment.
    - zone → smb_shares: SMB shares are scoped to an access zone. The overlay
      shows which shares are served over which network segment.

    Use this tool to answer questions like:
    - "What IP addresses does the System zone use for client connections?"
    - "Which SMB shares are accessible from the external subnet?"
    - "How is SmartConnect configured for each network segment?"
    - "What DNS name should clients use to connect to a given zone?"

    Note: If a subsection fails to retrieve, it will contain an "error" key
    rather than causing the entire map to fail.
    """
    cluster = get_cluster(cluster_name)
    network = Network(cluster)
    return network.get_network_map()
