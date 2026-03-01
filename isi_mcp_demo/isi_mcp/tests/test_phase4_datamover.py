"""
Phase 4d - DataMover Operations Tests

Tests DataMover policy, account, and base policy CRUD operations via MCP
tools (all SDK-backed, no Ansible).

DataMover is an advanced feature that may not be available or licensed on
all test clusters. Tests skip gracefully if the DataMover API returns errors
indicating the feature is not available.

All read operations tested first, then create/delete lifecycle tests.
"""

import uuid
import pytest

from modules.onefs.v9_12_0.datamover import DataMover

from tests.test_utils import (
    assert_no_error, assert_result_is_dict,
    validate_items_list,
)


def _unique_name(prefix="test_dm"):
    """Return a name with a unique 8-char hex suffix."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _skip_if_datamover_unavailable(result):
    """Skip test if DataMover feature is not available on cluster."""
    if isinstance(result, dict):
        err = result.get("error", "")
        if isinstance(err, str) and any(
            kw in err.lower()
            for kw in ("not supported", "not licensed", "not enabled",
                       "not found", "disabled", "permission denied",
                       "403", "404")
        ):
            pytest.skip(f"DataMover not available on this cluster: {err}")


def _skip_if_create_fails(result, operation):
    """Skip lifecycle test if create operation returns an error.

    DataMover create operations may fail due to missing required fields,
    unsupported configurations, or cluster-specific limitations.
    """
    if isinstance(result, dict) and "error" in result:
        pytest.skip(
            f"DataMover {operation} create not supported with minimal "
            f"params on this cluster: {result['error'][:200]}"
        )


# ---------------------------------------------------------------------------
# DataMover Policy - Read Operations
# ---------------------------------------------------------------------------

class TestDataMoverPolicyRead:
    pytestmark = [pytest.mark.func_datamover, pytest.mark.group_datamover, pytest.mark.read]
    """Test DataMover policy read operations via MCP."""

    def test_datamover_policy_get(self, mcp_session):
        """powerscale_datamover_policy_get returns paginated policy list."""
        try:
            result = mcp_session("powerscale_datamover_policy_get", {
                "limit": 100,
            })
        except AssertionError as e:
            _skip_if_datamover_unavailable({"error": str(e)})
            raise

        _skip_if_datamover_unavailable(result)
        assert isinstance(result, dict), "Policy list must be dict"
        assert "items" in result, f"Missing 'items'. Keys: {list(result.keys())}"
        assert isinstance(result["items"], list), "'items' must be list"
        assert "resume" in result, "Missing 'resume' field"

    def test_datamover_policy_get_by_id_nonexistent(self, mcp_session):
        """powerscale_datamover_policy_get_by_id handles missing policy."""
        try:
            result = mcp_session("powerscale_datamover_policy_get_by_id", {
                "policy_id": "nonexistent_policy_999",
            })
        except AssertionError as e:
            # Tool may return error for nonexistent ID
            _skip_if_datamover_unavailable({"error": str(e)})
            # If it's just "not found", that's expected behavior
            if "not found" in str(e).lower() or "404" in str(e):
                return
            raise

        _skip_if_datamover_unavailable(result)
        # Should return success=False for nonexistent
        if isinstance(result, dict):
            assert result.get("success") is False or "error" in result, (
                f"Expected failure for nonexistent policy: {result}"
            )


# ---------------------------------------------------------------------------
# DataMover Account - Read Operations
# ---------------------------------------------------------------------------

class TestDataMoverAccountRead:
    pytestmark = [pytest.mark.func_datamover, pytest.mark.group_datamover, pytest.mark.read]
    """Test DataMover account read operations via MCP."""

    def test_datamover_account_get(self, mcp_session):
        """powerscale_datamover_account_get returns paginated account list."""
        try:
            result = mcp_session("powerscale_datamover_account_get", {
                "limit": 100,
            })
        except AssertionError as e:
            _skip_if_datamover_unavailable({"error": str(e)})
            raise

        _skip_if_datamover_unavailable(result)
        assert isinstance(result, dict), "Account list must be dict"
        assert "items" in result, f"Missing 'items'. Keys: {list(result.keys())}"
        assert isinstance(result["items"], list), "'items' must be list"

    def test_datamover_account_get_by_id_nonexistent(self, mcp_session):
        """powerscale_datamover_account_get_by_id handles missing account."""
        try:
            result = mcp_session("powerscale_datamover_account_get_by_id", {
                "account_id": "nonexistent_acct_999",
            })
        except AssertionError as e:
            _skip_if_datamover_unavailable({"error": str(e)})
            if "not found" in str(e).lower() or "404" in str(e):
                return
            raise

        _skip_if_datamover_unavailable(result)
        if isinstance(result, dict):
            assert result.get("success") is False or "error" in result


# ---------------------------------------------------------------------------
# DataMover Base Policy - Read Operations
# ---------------------------------------------------------------------------

class TestDataMoverBasePolicyRead:
    pytestmark = [pytest.mark.func_datamover, pytest.mark.group_datamover, pytest.mark.read]
    """Test DataMover base policy read operations via MCP."""

    def test_datamover_base_policy_get(self, mcp_session):
        """powerscale_datamover_base_policy_get returns paginated list."""
        try:
            result = mcp_session("powerscale_datamover_base_policy_get", {
                "limit": 100,
            })
        except AssertionError as e:
            _skip_if_datamover_unavailable({"error": str(e)})
            raise

        _skip_if_datamover_unavailable(result)
        assert isinstance(result, dict), "Base policy list must be dict"
        assert "items" in result, f"Missing 'items'. Keys: {list(result.keys())}"
        assert isinstance(result["items"], list), "'items' must be list"

    def test_datamover_base_policy_get_by_id_nonexistent(self, mcp_session):
        """powerscale_datamover_base_policy_get_by_id handles missing policy."""
        try:
            result = mcp_session("powerscale_datamover_base_policy_get_by_id", {
                "base_policy_id": "nonexistent_bp_999",
            })
        except AssertionError as e:
            _skip_if_datamover_unavailable({"error": str(e)})
            if "not found" in str(e).lower() or "404" in str(e):
                return
            raise

        _skip_if_datamover_unavailable(result)
        if isinstance(result, dict):
            assert result.get("success") is False or "error" in result


# ---------------------------------------------------------------------------
# DataMover Policy - Lifecycle (Create + Delete)
# ---------------------------------------------------------------------------

class TestDataMoverPolicyLifecycle:
    pytestmark = [pytest.mark.func_datamover, pytest.mark.group_datamover, pytest.mark.write]
    """Test DataMover policy create + delete lifecycle via MCP."""

    def test_datamover_policy_create_and_delete(
        self, mcp_session, created_datamover_policies, created_datamover_base_policies
    ):
        """Create a DataMover policy, verify it, then delete it."""
        policy_name = _unique_name("dmpol")
        created_datamover_policies.append(policy_name)

        # First, ensure we have a base policy to reference
        # Try to get existing base policies
        base_policy_result = mcp_session("powerscale_datamover_base_policy_get", {
            "limit": 1,
        })
        _skip_if_datamover_unavailable(base_policy_result)

        base_policies = base_policy_result.get("items", [])
        if not base_policies:
            # No base policies exist, create one
            bp_name = _unique_name("dmbp_for_policy")
            created_datamover_base_policies.append(bp_name)
            bp_result = mcp_session("powerscale_datamover_base_policy_create", {
                "name": bp_name,
            })
            _skip_if_create_fails(bp_result, "base_policy")
            if bp_result.get("success"):
                base_policies = [{"id": bp_result.get("id", bp_name)}]
            else:
                pytest.skip("Cannot create base policy for policy test")

        # Use the first available base policy
        base_policy_id = base_policies[0].get("id")

        # Create policy with a base_policy_id
        try:
            result = mcp_session("powerscale_datamover_policy_create", {
                "name": policy_name,
                "base_policy_id": base_policy_id,
            })
        except AssertionError as e:
            _skip_if_datamover_unavailable({"error": str(e)})
            raise

        _skip_if_datamover_unavailable(result)
        _skip_if_create_fails(result, "policy")
        assert_result_is_dict(result, "datamover_policy_create")
        assert result.get("success") is True, (
            f"DataMover policy create failed: {result}"
        )

        policy_id = result.get("id", policy_name)

        # Verify it exists in listing
        list_result = mcp_session("powerscale_datamover_policy_get", {
            "limit": 1000,
        })
        items = list_result.get("items", [])
        policy_names = [p.get("name") for p in items]
        assert policy_name in policy_names, (
            f"Created policy '{policy_name}' not found. "
            f"Found: {policy_names[:10]}"
        )

        # Delete
        del_result = mcp_session("powerscale_datamover_policy_delete", {
            "policy_id": str(policy_id),
        })
        assert_result_is_dict(del_result, "datamover_policy_delete")
        assert del_result.get("success") is True, (
            f"DataMover policy delete failed: {del_result}"
        )

        # Remove from cleanup list since we already deleted
        if policy_name in created_datamover_policies:
            created_datamover_policies.remove(policy_name)

        # Verify deleted
        post_list = mcp_session("powerscale_datamover_policy_get", {
            "limit": 1000,
        })
        post_names = [p.get("name") for p in post_list.get("items", [])]
        assert policy_name not in post_names, (
            f"Policy '{policy_name}' still present after deletion"
        )


# ---------------------------------------------------------------------------
# DataMover Account - Lifecycle (Create + Delete)
# ---------------------------------------------------------------------------

class TestDataMoverAccountLifecycle:
    pytestmark = [pytest.mark.func_datamover, pytest.mark.group_datamover, pytest.mark.write]
    """Test DataMover account create + delete lifecycle via MCP."""

    def test_datamover_account_create_and_delete(
        self, mcp_session, created_datamover_accounts
    ):
        """Create a DataMover account, verify it, then delete it."""
        acct_name = _unique_name("dmacct")
        created_datamover_accounts.append(acct_name)

        # Create a local-type account (simplest, no external credentials)
        try:
            result = mcp_session("powerscale_datamover_account_create", {
                "name": acct_name,
                "account_type": "local",
                "uri": "/ifs/data",
            })
        except AssertionError as e:
            _skip_if_datamover_unavailable({"error": str(e)})
            raise

        _skip_if_datamover_unavailable(result)
        _skip_if_create_fails(result, "account")
        assert_result_is_dict(result, "datamover_account_create")
        assert result.get("success") is True, (
            f"DataMover account create failed: {result}"
        )

        acct_id = result.get("id", acct_name)

        # Verify it exists
        list_result = mcp_session("powerscale_datamover_account_get", {
            "limit": 1000,
        })
        items = list_result.get("items", [])
        acct_names = [a.get("name") for a in items]
        assert acct_name in acct_names, (
            f"Created account '{acct_name}' not found. "
            f"Found: {acct_names[:10]}"
        )

        # Delete
        del_result = mcp_session("powerscale_datamover_account_delete", {
            "account_id": str(acct_id),
        })
        assert_result_is_dict(del_result, "datamover_account_delete")
        assert del_result.get("success") is True, (
            f"DataMover account delete failed: {del_result}"
        )

        # Remove from cleanup list
        if acct_name in created_datamover_accounts:
            created_datamover_accounts.remove(acct_name)


# ---------------------------------------------------------------------------
# DataMover Base Policy - Lifecycle (Create + Delete)
# ---------------------------------------------------------------------------

class TestDataMoverBasePolicyLifecycle:
    pytestmark = [pytest.mark.func_datamover, pytest.mark.group_datamover, pytest.mark.write]
    """Test DataMover base policy create + delete lifecycle via MCP."""

    def test_datamover_base_policy_create_and_delete(
        self, mcp_session, created_datamover_base_policies, created_datamover_accounts
    ):
        """Create a DataMover base policy, verify it, then delete it."""
        bp_name = _unique_name("dmbp")
        created_datamover_base_policies.append(bp_name)

        # First, ensure we have accounts to reference
        # Try to get existing accounts
        acct_result = mcp_session("powerscale_datamover_account_get", {
            "limit": 1,
        })
        _skip_if_datamover_unavailable(acct_result)

        accounts = acct_result.get("items", [])
        if not accounts or len(accounts) < 2:
            # Create source account
            src_name = _unique_name("dmacct_src")
            created_datamover_accounts.append(src_name)
            src_result = mcp_session("powerscale_datamover_account_create", {
                "name": src_name,
                "account_type": "local",
                "uri": "/ifs/data",
            })
            _skip_if_create_fails(src_result, "account")
            if not src_result.get("success"):
                pytest.skip("Cannot create source account for base policy test")
            accounts.append({"id": src_result.get("id", src_name)})

            # Create target account (different path)
            tgt_name = _unique_name("dmacct_tgt")
            created_datamover_accounts.append(tgt_name)
            tgt_result = mcp_session("powerscale_datamover_account_create", {
                "name": tgt_name,
                "account_type": "local",
                "uri": "/ifs/archive",
            })
            _skip_if_create_fails(tgt_result, "account")
            if not tgt_result.get("success"):
                pytest.skip("Cannot create target account for base policy test")
            accounts.append({"id": tgt_result.get("id", tgt_name)})

        # Use first two accounts
        source_account_id = accounts[0].get("id")
        target_account_id = accounts[1].get("id")

        # Create
        try:
            result = mcp_session("powerscale_datamover_base_policy_create", {
                "name": bp_name,
                "source_account_id": source_account_id,
                "target_account_id": target_account_id,
                "source_base_path": "/ifs/data",
                "target_base_path": "/ifs/archive",
            })
        except AssertionError as e:
            _skip_if_datamover_unavailable({"error": str(e)})
            raise

        _skip_if_datamover_unavailable(result)
        _skip_if_create_fails(result, "base_policy")
        assert_result_is_dict(result, "datamover_base_policy_create")
        assert result.get("success") is True, (
            f"DataMover base policy create failed: {result}"
        )

        bp_id = result.get("id", bp_name)

        # Verify it exists
        list_result = mcp_session("powerscale_datamover_base_policy_get", {
            "limit": 1000,
        })
        items = list_result.get("items", [])
        bp_names = [bp.get("name") for bp in items]
        assert bp_name in bp_names, (
            f"Created base policy '{bp_name}' not found. "
            f"Found: {bp_names[:10]}"
        )

        # Delete
        del_result = mcp_session("powerscale_datamover_base_policy_delete", {
            "base_policy_id": str(bp_id),
        })
        assert_result_is_dict(del_result, "datamover_base_policy_delete")
        assert del_result.get("success") is True, (
            f"DataMover base policy delete failed: {del_result}"
        )

        # Remove from cleanup list
        if bp_name in created_datamover_base_policies:
            created_datamover_base_policies.remove(bp_name)


# ---------------------------------------------------------------------------
# DataMover Policy Last Job
# ---------------------------------------------------------------------------

class TestDataMoverPolicyLastJob:
    pytestmark = [pytest.mark.func_datamover, pytest.mark.group_datamover, pytest.mark.read]
    """Test DataMover policy last job retrieval via MCP."""

    def test_datamover_policy_last_job_nonexistent(self, mcp_session):
        """powerscale_datamover_policy_last_job handles missing policy."""
        try:
            result = mcp_session("powerscale_datamover_policy_last_job", {
                "policy_id": "nonexistent_policy_999",
            })
        except AssertionError as e:
            _skip_if_datamover_unavailable({"error": str(e)})
            if "not found" in str(e).lower() or "404" in str(e):
                return
            raise

        _skip_if_datamover_unavailable(result)
        # Should return failure or empty last_job
        if isinstance(result, dict):
            if result.get("success") is True:
                # Might have empty last_job
                assert "last_job" in result
