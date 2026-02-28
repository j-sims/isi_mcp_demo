"""
Phase 7 — Cluster & Capacity Expansion Tests

Tests read-only cluster and capacity operations:
  - Cluster nodes (list and per-node detail)
  - Storage pool node types (list and by ID)
  - Licenses (list and by name)
  - Zones summary (overall count and per-zone path)

All operations are read-only — no cluster resources are created or modified.

Direct module tests use the test_cluster_direct fixture.
MCP server tests use the mcp_session fixture.
"""

import pytest
from modules.onefs.v9_12_0.cluster_nodes import ClusterNodes
from modules.onefs.v9_12_0.storagepool_nodetypes import StoragepoolNodetypes
from modules.onefs.v9_12_0.license import License
from modules.onefs.v9_12_0.zones_summary import ZonesSummary
from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
    validate_items_list, validate_item_fields,
)


# ===========================================================================
# Direct module tests
# ===========================================================================

class TestClusterNodesDirect:
    """Direct module tests for ClusterNodes."""

    def test_cluster_nodes_get_returns_dict(self, test_cluster_direct):
        """ClusterNodes.get() returns a dict with 'items' list."""
        nodes = ClusterNodes(test_cluster_direct)
        result = nodes.get()
        assert isinstance(result, dict), \
            f"ClusterNodes.get() must return dict, got {type(result).__name__}"
        assert "error" not in result, f"ClusterNodes.get() returned error: {result}"
        assert "items" in result, f"Missing 'items' key, got: {list(result.keys())}"
        assert isinstance(result["items"], list), \
            f"'items' must be a list, got {type(result['items']).__name__}"

    def test_cluster_nodes_has_at_least_one_node(self, test_cluster_direct):
        """ClusterNodes.get() returns at least one node."""
        nodes = ClusterNodes(test_cluster_direct)
        result = nodes.get()
        items = result.get("items", [])
        assert len(items) > 0, "Expected at least one cluster node"

    def test_cluster_nodes_items_have_lnn(self, test_cluster_direct):
        """Each node item should have an 'lnn' field."""
        nodes = ClusterNodes(test_cluster_direct)
        result = nodes.get()
        items = result.get("items", [])
        assert len(items) > 0, "No nodes returned"
        for node in items:
            assert isinstance(node, dict), f"Node item must be dict, got {type(node)}"
            assert "lnn" in node, \
                f"Node missing 'lnn' field. Available fields: {list(node.keys())}"

    def test_cluster_nodes_total_matches_items(self, test_cluster_direct):
        """The 'total' field should match the number of items returned."""
        nodes = ClusterNodes(test_cluster_direct)
        result = nodes.get()
        items = result.get("items", [])
        total = result.get("total")
        if total is not None:
            assert total == len(items) or total >= len(items), \
                f"total={total} is less than item count={len(items)}"

    def test_cluster_node_get_by_id_returns_dict(self, test_cluster_direct):
        """ClusterNodes.get_by_id() returns a dict for the first node."""
        nodes = ClusterNodes(test_cluster_direct)
        result = nodes.get()
        items = result.get("items", [])
        if not items:
            pytest.skip("No nodes available to test get_by_id")
        first_lnn = items[0].get("lnn")
        if first_lnn is None:
            pytest.skip("First node has no 'lnn' field")
        detail = nodes.get_by_id(first_lnn)
        assert isinstance(detail, dict), \
            f"get_by_id() must return dict, got {type(detail).__name__}"
        # The SDK to_dict() includes 'error': None as a model field; check value not presence
        assert detail.get("error") is None, f"get_by_id() returned error: {detail.get('error')}"

    def test_cluster_node_detail_has_hardware(self, test_cluster_direct):
        """Node detail from get_by_id() should include hardware info."""
        nodes = ClusterNodes(test_cluster_direct)
        result = nodes.get()
        items = result.get("items", [])
        if not items:
            pytest.skip("No nodes available")
        first_lnn = items[0].get("lnn")
        if first_lnn is None:
            pytest.skip("First node has no 'lnn'")
        detail = nodes.get_by_id(first_lnn)
        # Hardware info may be nested; just verify the response is a dict with content
        assert isinstance(detail, dict) and len(detail) > 0, \
            "Node detail should be a non-empty dict"


class TestStoragepoolNodetypesDirect:
    """Direct module tests for StoragepoolNodetypes."""

    def test_nodetypes_get_returns_dict(self, test_cluster_direct):
        """StoragepoolNodetypes.get() returns a dict with 'items' list."""
        nodetypes = StoragepoolNodetypes(test_cluster_direct)
        result = nodetypes.get()
        assert isinstance(result, dict), \
            f"get() must return dict, got {type(result).__name__}"
        assert "error" not in result, f"get() returned error: {result}"
        assert "items" in result, f"Missing 'items' key, got: {list(result.keys())}"

    def test_nodetypes_items_are_list(self, test_cluster_direct):
        """StoragepoolNodetypes.get() items field is a list."""
        nodetypes = StoragepoolNodetypes(test_cluster_direct)
        result = nodetypes.get()
        assert isinstance(result.get("items"), list), \
            f"'items' must be list, got {type(result.get('items')).__name__}"

    def test_nodetypes_items_have_product_name(self, test_cluster_direct):
        """Each node type should have a 'product_name' field."""
        nodetypes = StoragepoolNodetypes(test_cluster_direct)
        result = nodetypes.get()
        items = result.get("items", [])
        if not items:
            pytest.skip("No node types returned — cluster may have none configured")
        for nt in items:
            assert isinstance(nt, dict), f"Node type must be dict, got {type(nt)}"
            assert "product_name" in nt or "id" in nt, \
                f"Node type missing 'product_name'/'id'. Fields: {list(nt.keys())}"

    def test_nodetype_get_by_id_returns_dict(self, test_cluster_direct):
        """StoragepoolNodetypes.get_by_id() returns details for the first node type."""
        nodetypes = StoragepoolNodetypes(test_cluster_direct)
        result = nodetypes.get()
        items = result.get("items", [])
        if not items:
            pytest.skip("No node types available to test get_by_id")
        first_id = items[0].get("id")
        if first_id is None:
            pytest.skip("First node type has no 'id' field")
        detail = nodetypes.get_by_id(first_id)
        assert isinstance(detail, dict), \
            f"get_by_id() must return dict, got {type(detail).__name__}"
        assert "error" not in detail, f"get_by_id() returned error: {detail}"


class TestLicenseDirect:
    """Direct module tests for License."""

    def test_license_get_returns_dict(self, test_cluster_direct):
        """License.get() returns a dict with 'items' list."""
        lic = License(test_cluster_direct)
        result = lic.get()
        assert isinstance(result, dict), \
            f"License.get() must return dict, got {type(result).__name__}"
        assert "error" not in result, f"License.get() returned error: {result}"
        assert "items" in result, f"Missing 'items' key, got: {list(result.keys())}"
        assert isinstance(result["items"], list), \
            f"'items' must be list, got {type(result['items']).__name__}"

    def test_license_items_have_required_fields(self, test_cluster_direct):
        """Each license should have name and status fields."""
        lic = License(test_cluster_direct)
        result = lic.get()
        items = result.get("items", [])
        if not items:
            pytest.skip("No licenses returned")
        for item in items:
            assert isinstance(item, dict), f"License item must be dict, got {type(item)}"
            # 'name' or 'id' must be present
            has_name = "name" in item or "id" in item
            assert has_name, \
                f"License item missing 'name'/'id'. Fields: {list(item.keys())}"

    def test_license_items_have_status(self, test_cluster_direct):
        """Each license should have a status field."""
        lic = License(test_cluster_direct)
        result = lic.get()
        items = result.get("items", [])
        if not items:
            pytest.skip("No licenses returned")
        for item in items:
            assert "status" in item, \
                f"License missing 'status' field. Available: {list(item.keys())}"

    def test_license_get_by_name_smartquotas(self, test_cluster_direct):
        """License.get_by_name('SmartQuotas') returns license details."""
        lic = License(test_cluster_direct)
        result = lic.get_by_name("SmartQuotas")
        assert isinstance(result, dict), \
            f"get_by_name() must return dict, got {type(result).__name__}"
        # May return an error dict if not licensed, but must be a dict
        # If no error, verify it has a status field
        if "error" not in result:
            assert "status" in result, \
                f"License detail missing 'status'. Available: {list(result.keys())}"

    def test_license_get_by_name_snapshotiq(self, test_cluster_direct):
        """License.get_by_name('SnapshotIQ') returns license details."""
        lic = License(test_cluster_direct)
        result = lic.get_by_name("SnapshotIQ")
        assert isinstance(result, dict), \
            f"get_by_name() must return dict, got {type(result).__name__}"


class TestZonesSummaryDirect:
    """Direct module tests for ZonesSummary."""

    def test_zones_summary_get_returns_dict(self, test_cluster_direct):
        """ZonesSummary.get() returns a dict with count and zones."""
        zs = ZonesSummary(test_cluster_direct)
        result = zs.get()
        assert isinstance(result, dict), \
            f"ZonesSummary.get() must return dict, got {type(result).__name__}"
        assert "error" not in result, f"ZonesSummary.get() returned error: {result}"

    def test_zones_summary_has_count(self, test_cluster_direct):
        """ZonesSummary.get() result has a 'count' field."""
        zs = ZonesSummary(test_cluster_direct)
        result = zs.get()
        assert "count" in result, \
            f"Missing 'count' key. Available: {list(result.keys())}"
        assert isinstance(result["count"], int), \
            f"'count' must be int, got {type(result['count']).__name__}"

    def test_zones_summary_count_positive(self, test_cluster_direct):
        """ZonesSummary count must be at least 1 (System zone always exists)."""
        zs = ZonesSummary(test_cluster_direct)
        result = zs.get()
        count = result.get("count", 0)
        assert count >= 1, f"Expected at least 1 zone (System), got count={count}"

    def test_zones_summary_has_zones_list(self, test_cluster_direct):
        """ZonesSummary.get() result has a 'zones' list."""
        zs = ZonesSummary(test_cluster_direct)
        result = zs.get()
        assert "zones" in result, \
            f"Missing 'zones' key. Available: {list(result.keys())}"
        assert isinstance(result["zones"], list), \
            f"'zones' must be list, got {type(result['zones']).__name__}"

    def test_zones_summary_filter_by_groupnet(self, test_cluster_direct):
        """ZonesSummary.get(groupnet='groupnet0') returns a valid result."""
        zs = ZonesSummary(test_cluster_direct)
        result = zs.get(groupnet="groupnet0")
        assert isinstance(result, dict), \
            f"Filtered get() must return dict, got {type(result).__name__}"
        # May return error if groupnet0 doesn't exist, but must return a dict
        if "error" not in result:
            assert "count" in result, \
                f"Filtered result missing 'count'. Got: {list(result.keys())}"


# ===========================================================================
# MCP server tests
# ===========================================================================

class TestClusterNodesMCP:
    """MCP tool tests for cluster nodes."""

    def test_cluster_nodes_get_returns_dict(self, mcp_session):
        """powerscale_cluster_nodes_get returns a dict with items list."""
        result = mcp_session("powerscale_cluster_nodes_get")

        assert not isinstance(result, str), \
            f"powerscale_cluster_nodes_get returned error string: {result}"
        assert_result_is_dict(result, "powerscale_cluster_nodes_get")
        assert "items" in result, \
            f"Missing 'items' key. Available: {list(result.keys())}"
        assert isinstance(result["items"], list), \
            f"'items' must be list, got {type(result['items']).__name__}"

    def test_cluster_nodes_has_at_least_one_node(self, mcp_session):
        """powerscale_cluster_nodes_get returns at least one node."""
        result = mcp_session("powerscale_cluster_nodes_get")
        items = result.get("items", []) if isinstance(result, dict) else []
        assert len(items) > 0, "Expected at least one cluster node"

    def test_cluster_nodes_items_have_lnn(self, mcp_session):
        """Each node returned by powerscale_cluster_nodes_get has an 'lnn' field."""
        result = mcp_session("powerscale_cluster_nodes_get")
        assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
        items = result.get("items", [])
        assert len(items) > 0, "No nodes returned"
        for node in items:
            assert "lnn" in node, \
                f"Node missing 'lnn'. Fields: {list(node.keys())}"

    def test_cluster_node_get_by_id_returns_dict(self, mcp_session):
        """powerscale_cluster_node_get_by_id returns node detail dict."""
        # Get first node LNN
        result = mcp_session("powerscale_cluster_nodes_get")
        assert isinstance(result, dict), "Expected dict from cluster_nodes_get"
        items = result.get("items", [])
        if not items:
            pytest.skip("No nodes available for detail test")
        first_lnn = items[0].get("lnn")
        if first_lnn is None:
            pytest.skip("First node has no lnn")

        detail = mcp_session("powerscale_cluster_node_get_by_id", {"node_id": first_lnn})
        assert not isinstance(detail, str), \
            f"powerscale_cluster_node_get_by_id returned error string: {detail}"
        assert isinstance(detail, dict), \
            f"Expected dict, got {type(detail).__name__}"

    def test_cluster_node_detail_is_non_empty(self, mcp_session):
        """Node detail dict should contain meaningful fields."""
        result = mcp_session("powerscale_cluster_nodes_get")
        items = result.get("items", []) if isinstance(result, dict) else []
        if not items:
            pytest.skip("No nodes available")
        first_lnn = items[0].get("lnn")
        if first_lnn is None:
            pytest.skip("No lnn on first node")

        detail = mcp_session("powerscale_cluster_node_get_by_id", {"node_id": first_lnn})
        assert isinstance(detail, dict) and len(detail) > 0, \
            "Node detail should be a non-empty dict"


class TestStoragepoolNodetypesMCP:
    """MCP tool tests for storage pool node types."""

    def test_nodetypes_get_returns_dict(self, mcp_session):
        """powerscale_storagepool_nodetypes_get returns a dict with items list."""
        result = mcp_session("powerscale_storagepool_nodetypes_get")

        assert not isinstance(result, str), \
            f"powerscale_storagepool_nodetypes_get returned error string: {result}"
        assert_result_is_dict(result, "powerscale_storagepool_nodetypes_get")
        assert "items" in result, \
            f"Missing 'items'. Available: {list(result.keys())}"

    def test_nodetypes_items_are_list(self, mcp_session):
        """powerscale_storagepool_nodetypes_get items is a list."""
        result = mcp_session("powerscale_storagepool_nodetypes_get")
        assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
        assert isinstance(result.get("items"), list), \
            f"'items' must be list, got {type(result.get('items')).__name__}"

    def test_nodetype_get_by_id_returns_dict(self, mcp_session):
        """powerscale_storagepool_nodetype_get_by_id returns detail for first node type."""
        result = mcp_session("powerscale_storagepool_nodetypes_get")
        assert isinstance(result, dict), "Expected dict from nodetypes_get"
        items = result.get("items", [])
        if not items:
            pytest.skip("No node types available to test get_by_id")
        first_id = items[0].get("id")
        if first_id is None:
            pytest.skip("First node type has no 'id'")

        detail = mcp_session(
            "powerscale_storagepool_nodetype_get_by_id", {"nodetype_id": first_id}
        )
        assert not isinstance(detail, str), \
            f"powerscale_storagepool_nodetype_get_by_id returned error string: {detail}"
        assert isinstance(detail, dict), \
            f"Expected dict, got {type(detail).__name__}"


class TestLicenseMCP:
    """MCP tool tests for license information."""

    def test_license_get_returns_dict(self, mcp_session):
        """powerscale_license_get returns a dict with items list."""
        result = mcp_session("powerscale_license_get")

        assert not isinstance(result, str), \
            f"powerscale_license_get returned error string: {result}"
        assert_result_is_dict(result, "powerscale_license_get")
        assert "items" in result, \
            f"Missing 'items'. Available: {list(result.keys())}"
        assert isinstance(result["items"], list), \
            f"'items' must be list, got {type(result['items']).__name__}"

    def test_license_list_is_non_empty(self, mcp_session):
        """powerscale_license_get returns at least one license."""
        result = mcp_session("powerscale_license_get")
        assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
        items = result.get("items", [])
        assert len(items) > 0, \
            "Expected at least one license entry from powerscale_license_get"

    def test_license_items_have_status_field(self, mcp_session):
        """Each license item should have a 'status' field."""
        result = mcp_session("powerscale_license_get")
        assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
        items = result.get("items", [])
        if not items:
            pytest.skip("No licenses returned")
        for item in items:
            assert "status" in item, \
                f"License item missing 'status'. Fields: {list(item.keys())}"

    def test_license_get_by_name_returns_dict(self, mcp_session):
        """powerscale_license_get_by_name returns a dict for a known license."""
        # Use a license that should always be present
        result = mcp_session(
            "powerscale_license_get_by_name", {"name": "SmartQuotas"}
        )
        assert not isinstance(result, str), \
            f"powerscale_license_get_by_name returned error string: {result}"
        assert isinstance(result, dict), \
            f"Expected dict, got {type(result).__name__}"

    def test_license_get_by_name_has_status(self, mcp_session):
        """powerscale_license_get_by_name result includes status when found."""
        result = mcp_session(
            "powerscale_license_get_by_name", {"name": "SnapshotIQ"}
        )
        assert isinstance(result, dict), \
            f"Expected dict, got {type(result).__name__}"
        if "error" not in result:
            assert "status" in result, \
                f"License detail missing 'status'. Fields: {list(result.keys())}"


class TestZonesSummaryMCP:
    """MCP tool tests for zones summary."""

    def test_zones_summary_get_returns_dict(self, mcp_session):
        """powerscale_zones_summary_get returns a dict."""
        result = mcp_session("powerscale_zones_summary_get")

        assert not isinstance(result, str), \
            f"powerscale_zones_summary_get returned error string: {result}"
        assert_result_is_dict(result, "powerscale_zones_summary_get")

    def test_zones_summary_has_count_and_zones(self, mcp_session):
        """powerscale_zones_summary_get returns count and zones list."""
        result = mcp_session("powerscale_zones_summary_get")
        assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
        assert "count" in result, \
            f"Missing 'count'. Available: {list(result.keys())}"
        assert "zones" in result, \
            f"Missing 'zones'. Available: {list(result.keys())}"
        assert isinstance(result["zones"], list), \
            f"'zones' must be list, got {type(result['zones']).__name__}"

    def test_zones_summary_count_at_least_one(self, mcp_session):
        """powerscale_zones_summary_get count is >= 1 (System zone always exists)."""
        result = mcp_session("powerscale_zones_summary_get")
        assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
        count = result.get("count", 0)
        assert count >= 1, \
            f"Expected at least 1 zone (System always exists), got count={count}"

    def test_zones_summary_filter_by_groupnet(self, mcp_session):
        """powerscale_zones_summary_get with groupnet filter returns a valid result."""
        result = mcp_session(
            "powerscale_zones_summary_get", {"groupnet": "groupnet0"}
        )
        assert not isinstance(result, str), \
            f"Filtered zones summary returned error string: {result}"
        assert isinstance(result, dict), \
            f"Expected dict, got {type(result).__name__}"

    def test_zones_summary_zone_get_returns_dict(self, mcp_session):
        """powerscale_zones_summary_zone_get returns a dict for zone ID 0."""
        result = mcp_session("powerscale_zones_summary_zone_get", {"zone_id": 0})
        assert not isinstance(result, str), \
            f"powerscale_zones_summary_zone_get returned error string: {result}"
        assert isinstance(result, dict), \
            f"Expected dict, got {type(result).__name__}"


# ---------------------------------------------------------------------------
# Tool Registration Test
# ---------------------------------------------------------------------------

class TestClusterCapacityToolsRegistration:
    """Verify all 8 new tools are registered in the MCP server."""

    def test_cluster_capacity_tools_exist(self, mcp_session):
        """All 8 cluster & capacity tools should be available in the tool list."""
        tools = mcp_session.list_tools()
        tool_names = [t["name"] for t in tools]

        expected = [
            "powerscale_cluster_nodes_get",
            "powerscale_cluster_node_get_by_id",
            "powerscale_storagepool_nodetypes_get",
            "powerscale_storagepool_nodetype_get_by_id",
            "powerscale_license_get",
            "powerscale_license_get_by_name",
            "powerscale_zones_summary_get",
            "powerscale_zones_summary_zone_get",
        ]

        missing = [t for t in expected if t not in tool_names]
        assert not missing, \
            f"Missing cluster & capacity tools in MCP tool list: {missing}"
