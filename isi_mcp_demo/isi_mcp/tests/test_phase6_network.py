"""
Phase 6 — Network Topology Tests

Tests read-only network topology operations:
  - Groupnets (DNS configuration, network partitioning)
  - Subnets (gateway, prefix, VLAN, SmartConnect service)
  - Pools (IP ranges, SmartConnect, interfaces, access zones)
  - Network interfaces (physical/virtual NICs per node)
  - External network settings (global IPv6, SmartConnect defaults)
  - DNS cache configuration
  - Access zones (groupnet association, auth providers)
  - Network map (composite topology with zones + SMB share overlay)

All operations are read-only — no cluster resources are created or modified.
"""

import pytest
from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
    validate_item_fields,
)


# ---------------------------------------------------------------------------
# TestNetworkGroupnets
# ---------------------------------------------------------------------------

class TestNetworkGroupnets:
    pytestmark = [pytest.mark.func_networking, pytest.mark.group_networking, pytest.mark.read]
    """Test groupnet listing."""

    def test_groupnets_get_returns_list(self, mcp_session):
        """powerscale_network_groupnets_get returns a non-empty list."""
        result = mcp_session("powerscale_network_groupnets_get")

        assert not isinstance(result, str), \
            f"powerscale_network_groupnets_get returned error string: {result}"
        assert isinstance(result, list), \
            f"Expected list, got {type(result).__name__}: {result}"
        assert len(result) > 0, "Groupnet list is empty — expected at least one groupnet"

    def test_groupnets_have_required_fields(self, mcp_session):
        """Each groupnet has name, dns_servers, and dns_search fields."""
        result = mcp_session("powerscale_network_groupnets_get")

        assert isinstance(result, list) and len(result) > 0, \
            "Expected non-empty list of groupnets"

        for item in result:
            assert isinstance(item, dict), f"Groupnet item should be dict, got {type(item)}"
            validate_item_fields(item, ["name", "dns_servers", "dns_search"], "groupnet")


# ---------------------------------------------------------------------------
# TestNetworkSubnets
# ---------------------------------------------------------------------------

class TestNetworkSubnets:
    pytestmark = [pytest.mark.func_networking, pytest.mark.group_networking, pytest.mark.read]
    """Test subnet listing and filtering."""

    def test_subnets_get_returns_list(self, mcp_session):
        """powerscale_network_subnets_get returns a list with required fields."""
        result = mcp_session("powerscale_network_subnets_get")

        assert not isinstance(result, str), \
            f"powerscale_network_subnets_get returned error string: {result}"
        assert isinstance(result, list), \
            f"Expected list, got {type(result).__name__}: {result}"
        assert len(result) > 0, "Subnet list is empty — expected at least one subnet"

        for item in result:
            validate_item_fields(item, ["name", "groupnet", "gateway", "prefixlen"], "subnet")

    def test_subnets_filter_by_groupnet(self, mcp_session):
        """Filtering subnets by groupnet name returns a non-empty subset."""
        # Get all groupnets first to find a valid groupnet name
        groupnets = mcp_session("powerscale_network_groupnets_get")
        assert isinstance(groupnets, list) and len(groupnets) > 0, \
            "Could not retrieve groupnets for filter test"

        groupnet_name = groupnets[0]["name"]
        result = mcp_session("powerscale_network_subnets_get", {"groupnet": groupnet_name})

        assert isinstance(result, list), \
            f"Expected list, got {type(result).__name__}"
        assert len(result) > 0, \
            f"No subnets found for groupnet '{groupnet_name}'"

        # All returned subnets must belong to the requested groupnet
        for item in result:
            assert item.get("groupnet") == groupnet_name, \
                f"Subnet '{item.get('name')}' has groupnet '{item.get('groupnet')}', expected '{groupnet_name}'"

    def test_subnets_have_smartconnect_fields(self, mcp_session):
        """Each subnet exposes SmartConnect service name and address fields."""
        result = mcp_session("powerscale_network_subnets_get")

        assert isinstance(result, list) and len(result) > 0, \
            "Expected non-empty subnet list"

        for item in result:
            assert "sc_service_name" in item, \
                f"Subnet '{item.get('name')}' missing 'sc_service_name' field"
            assert "sc_service_addrs" in item, \
                f"Subnet '{item.get('name')}' missing 'sc_service_addrs' field"


# ---------------------------------------------------------------------------
# TestNetworkPools
# ---------------------------------------------------------------------------

class TestNetworkPools:
    pytestmark = [pytest.mark.func_networking, pytest.mark.group_networking, pytest.mark.read]
    """Test pool listing, IP ranges, and SmartConnect configuration."""

    def test_pools_get_returns_list(self, mcp_session):
        """powerscale_network_pools_get returns a list with required fields."""
        result = mcp_session("powerscale_network_pools_get")

        assert not isinstance(result, str), \
            f"powerscale_network_pools_get returned error string: {result}"
        assert isinstance(result, list), \
            f"Expected list, got {type(result).__name__}: {result}"
        assert len(result) > 0, "Pool list is empty — expected at least one pool"

        for item in result:
            validate_item_fields(item, ["name", "access_zone", "ranges"], "pool")

    def test_pools_have_smartconnect_config(self, mcp_session):
        """Each pool exposes SmartConnect DNS zone and connection policy fields."""
        result = mcp_session("powerscale_network_pools_get")

        assert isinstance(result, list) and len(result) > 0, \
            "Expected non-empty pool list"

        for item in result:
            assert "sc_dns_zone" in item, \
                f"Pool '{item.get('name')}' missing 'sc_dns_zone' field"
            assert "sc_connect_policy" in item, \
                f"Pool '{item.get('name')}' missing 'sc_connect_policy' field"

    def test_pools_filter_by_access_zone(self, mcp_session):
        """Filtering pools by access_zone='System' returns a non-empty subset."""
        result = mcp_session("powerscale_network_pools_get", {"access_zone": "System"})

        assert isinstance(result, list), \
            f"Expected list, got {type(result).__name__}"
        assert len(result) > 0, \
            "No pools found for access_zone 'System'"

        for item in result:
            assert item.get("access_zone") == "System", \
                f"Pool '{item.get('name')}' has access_zone '{item.get('access_zone')}', expected 'System'"


# ---------------------------------------------------------------------------
# TestNetworkInterfaces
# ---------------------------------------------------------------------------

class TestNetworkInterfaces:
    pytestmark = [pytest.mark.func_networking, pytest.mark.group_networking, pytest.mark.read]
    """Test network interface listing."""

    def test_interfaces_get_returns_list(self, mcp_session):
        """powerscale_network_interfaces_get returns a list with required fields."""
        result = mcp_session("powerscale_network_interfaces_get")

        assert not isinstance(result, str), \
            f"powerscale_network_interfaces_get returned error string: {result}"
        assert isinstance(result, list), \
            f"Expected list, got {type(result).__name__}: {result}"
        assert len(result) > 0, "Interface list is empty — expected at least one interface"

        for item in result:
            validate_item_fields(item, ["name", "lnn", "status", "ip_addrs"], "interface")

    def test_interfaces_have_link_fields(self, mcp_session):
        """Each interface exposes linklayer and mtu fields."""
        result = mcp_session("powerscale_network_interfaces_get")

        assert isinstance(result, list) and len(result) > 0, \
            "Expected non-empty interface list"

        for item in result:
            assert "linklayer" in item, \
                f"Interface '{item.get('name')}' missing 'linklayer' field"
            assert "mtu" in item, \
                f"Interface '{item.get('name')}' missing 'mtu' field"


# ---------------------------------------------------------------------------
# TestNetworkExternal
# ---------------------------------------------------------------------------

class TestNetworkExternal:
    pytestmark = [pytest.mark.func_networking, pytest.mark.group_networking, pytest.mark.read]
    """Test global external network settings."""

    def test_external_get_returns_dict(self, mcp_session):
        """powerscale_network_external_get returns a dict."""
        result = mcp_session("powerscale_network_external_get")

        assert not isinstance(result, str), \
            f"powerscale_network_external_get returned error string: {result}"
        assert_result_is_dict(result, "powerscale_network_external_get")

    def test_external_has_required_fields(self, mcp_session):
        """External network settings include key configuration fields."""
        result = mcp_session("powerscale_network_external_get")

        assert isinstance(result, dict), \
            f"Expected dict, got {type(result).__name__}"

        for field in ["default_groupnet", "ipv6_enabled", "sc_rebalance_delay"]:
            assert field in result, \
                f"External settings missing field '{field}'. Available: {list(result.keys())}"


# ---------------------------------------------------------------------------
# TestNetworkDNS
# ---------------------------------------------------------------------------

class TestNetworkDNS:
    pytestmark = [pytest.mark.func_networking, pytest.mark.group_networking, pytest.mark.read]
    """Test DNS cache configuration."""

    def test_dns_get_returns_dict(self, mcp_session):
        """powerscale_network_dns_get returns a dict."""
        result = mcp_session("powerscale_network_dns_get")

        assert not isinstance(result, str), \
            f"powerscale_network_dns_get returned error string: {result}"
        assert_result_is_dict(result, "powerscale_network_dns_get")

    def test_dns_has_required_fields(self, mcp_session):
        """DNS cache config includes expected fields."""
        result = mcp_session("powerscale_network_dns_get")

        assert isinstance(result, dict), \
            f"Expected dict, got {type(result).__name__}"

        for field in ["cluster_timeout", "dns_timeout", "cache_entry_limit"]:
            assert field in result, \
                f"DNS cache settings missing field '{field}'. Available: {list(result.keys())}"


# ---------------------------------------------------------------------------
# TestZones
# ---------------------------------------------------------------------------

class TestZones:
    pytestmark = [pytest.mark.func_networking, pytest.mark.group_networking, pytest.mark.read]
    """Test access zone listing."""

    def test_zones_get_returns_list(self, mcp_session):
        """powerscale_zones_get returns a non-empty list."""
        result = mcp_session("powerscale_zones_get")

        assert not isinstance(result, str), \
            f"powerscale_zones_get returned error string: {result}"
        assert isinstance(result, list), \
            f"Expected list, got {type(result).__name__}: {result}"
        assert len(result) > 0, "Zone list is empty — expected at least one zone"

    def test_zones_include_system_zone(self, mcp_session):
        """The 'System' access zone is always present."""
        result = mcp_session("powerscale_zones_get")

        assert isinstance(result, list) and len(result) > 0, \
            "Expected non-empty zone list"

        zone_names = [z.get("name") for z in result]
        assert "System" in zone_names, \
            f"'System' zone not found. Available zones: {zone_names}"

    def test_zones_have_groupnet_and_auth_fields(self, mcp_session):
        """Each zone exposes groupnet and auth_providers fields."""
        result = mcp_session("powerscale_zones_get")

        assert isinstance(result, list) and len(result) > 0, \
            "Expected non-empty zone list"

        for item in result:
            assert isinstance(item, dict), f"Zone item should be dict, got {type(item)}"
            validate_item_fields(item, ["name", "groupnet", "auth_providers"], "zone")


# ---------------------------------------------------------------------------
# TestNetworkMap
# ---------------------------------------------------------------------------

class TestNetworkMap:
    pytestmark = [pytest.mark.func_networking, pytest.mark.group_networking, pytest.mark.read]
    """Test the composite network topology map."""

    def test_network_map_returns_dict_with_groupnets(self, mcp_session):
        """powerscale_network_map returns a dict with 'groupnets' key."""
        result = mcp_session("powerscale_network_map")

        assert not isinstance(result, str), \
            f"powerscale_network_map returned error string: {result}"
        assert_result_is_dict(result, "powerscale_network_map")
        assert "groupnets" in result, \
            f"Map missing 'groupnets' key. Available keys: {list(result.keys())}"
        assert isinstance(result["groupnets"], list), \
            f"'groupnets' should be list, got {type(result['groupnets']).__name__}"
        assert len(result["groupnets"]) > 0, \
            "Network map has empty groupnets list"

    def test_network_map_groupnets_have_subnets(self, mcp_session):
        """Each groupnet in the map contains a 'subnets' list."""
        result = mcp_session("powerscale_network_map")

        assert isinstance(result, dict) and "groupnets" in result, \
            "Expected network map with groupnets"

        for gn in result["groupnets"]:
            assert "subnets" in gn, \
                f"Groupnet '{gn.get('name')}' missing 'subnets' key"
            assert isinstance(gn["subnets"], list), \
                f"Groupnet '{gn.get('name')}' 'subnets' should be list"

    def test_network_map_subnets_have_pools(self, mcp_session):
        """Each subnet in the map contains a 'pools' list."""
        result = mcp_session("powerscale_network_map")

        assert isinstance(result, dict) and "groupnets" in result

        for gn in result["groupnets"]:
            for sn in gn.get("subnets", []):
                assert "pools" in sn, \
                    f"Subnet '{sn.get('name')}' in groupnet '{gn.get('name')}' missing 'pools' key"
                assert isinstance(sn["pools"], list), \
                    f"Subnet '{sn.get('name')}' 'pools' should be list"

    def test_network_map_groupnets_have_zones_with_smb_shares(self, mcp_session):
        """Each groupnet in the map contains a 'zones' list; each zone has 'smb_shares'."""
        result = mcp_session("powerscale_network_map")

        assert isinstance(result, dict) and "groupnets" in result

        for gn in result["groupnets"]:
            assert "zones" in gn, \
                f"Groupnet '{gn.get('name')}' missing 'zones' key"
            assert isinstance(gn["zones"], list), \
                f"Groupnet '{gn.get('name')}' 'zones' should be list"

            for zone in gn.get("zones", []):
                assert "smb_shares" in zone, \
                    f"Zone '{zone.get('name')}' in groupnet '{gn.get('name')}' missing 'smb_shares' key"
                assert isinstance(zone["smb_shares"], list), \
                    f"Zone '{zone.get('name')}' 'smb_shares' should be list"


# ---------------------------------------------------------------------------
# TestNetworkToolsRegistration
# ---------------------------------------------------------------------------

class TestNetworkToolsRegistration:
    pytestmark = [pytest.mark.func_none, pytest.mark.group_management, pytest.mark.read]
    """Verify all networking tools are registered in the MCP server."""

    def test_networking_tools_exist(self, mcp_session):
        """All 8 networking tools should be available in the tool list."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        expected = [
            "powerscale_network_groupnets_get",
            "powerscale_network_subnets_get",
            "powerscale_network_pools_get",
            "powerscale_network_interfaces_get",
            "powerscale_network_external_get",
            "powerscale_network_dns_get",
            "powerscale_zones_get",
            "powerscale_network_map",
        ]

        missing = [t for t in expected if t not in tool_names]
        assert not missing, \
            f"Missing networking tools in MCP tool list: {missing}"
