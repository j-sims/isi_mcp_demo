"""Tests for NFS client validation in Nfs module."""
import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add the isi_mcp_demo module and modules directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'isi_mcp_demo'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'isi_mcp_demo', 'isi_mcp'))

# Mock the AnsibleRunner before importing Nfs
sys.modules['modules.ansible.runner'] = Mock()
sys.modules['modules'] = Mock()
sys.modules['modules.ansible'] = Mock()

from isi_mcp.modules.onefs.v9_12_0.nfs import Nfs


class MockCluster:
    """Mock cluster for testing without API calls."""
    def __init__(self):
        self.debug = False
        self.api_client = None


class TestNfsClientValidation:
    """Test suite for NFS client validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.nfs = Nfs(MockCluster())

    # --- Single client validation tests ---

    def test_validate_client_valid_ip(self):
        """Test valid IPv4 address."""
        assert self.nfs._validate_client("192.168.1.100") is True
        assert self.nfs._validate_client("10.0.0.1") is True
        assert self.nfs._validate_client("172.16.0.1") is True

    def test_validate_client_valid_cidr(self):
        """Test valid CIDR notation."""
        assert self.nfs._validate_client("192.168.0.0/24") is True
        assert self.nfs._validate_client("10.0.0.0/8") is True
        assert self.nfs._validate_client("172.16.0.0/16") is True

    def test_validate_client_valid_hostname(self):
        """Test valid hostnames."""
        assert self.nfs._validate_client("server.example.com") is True
        assert self.nfs._validate_client("nfs-client") is True
        assert self.nfs._validate_client("storage") is True

    def test_validate_client_wildcard_hostname(self):
        """Test wildcard hostnames."""
        assert self.nfs._validate_client("*.example.com") is True
        assert self.nfs._validate_client("*.datacenter.example.com") is True

    def test_validate_client_invalid_ip_octet(self):
        """Test invalid IP with out-of-range octet."""
        assert self.nfs._validate_client("192.168.1.256") is False
        assert self.nfs._validate_client("300.0.0.1") is False
        assert self.nfs._validate_client("10.0.0.") is False

    def test_validate_client_invalid_cidr_notation(self):
        """Test invalid CIDR notation."""
        assert self.nfs._validate_client("192.168.0.0/33") is False
        assert self.nfs._validate_client("192.168.0.0/") is False

    def test_validate_client_empty(self):
        """Test empty client string."""
        assert self.nfs._validate_client("") is False

    def test_validate_client_none(self):
        """Test None client."""
        assert self.nfs._validate_client(None) is False

    def test_validate_client_invalid_format(self):
        """Test invalid client formats."""
        assert self.nfs._validate_client("invalid!client") is False
        assert self.nfs._validate_client("client@example.com") is False
        assert self.nfs._validate_client("client#1") is False

    # --- Client list validation tests ---

    def test_validate_clients_empty_list(self):
        """Test empty client list returns valid."""
        is_valid, error = self.nfs._validate_clients(None)
        assert is_valid is True
        assert error is None

    def test_validate_clients_single_valid(self):
        """Test list with single valid client."""
        is_valid, error = self.nfs._validate_clients(["192.168.1.100"])
        assert is_valid is True
        assert error is None

    def test_validate_clients_multiple_valid(self):
        """Test list with multiple valid clients."""
        clients = ["192.168.1.100", "10.0.0.0/24", "server.example.com"]
        is_valid, error = self.nfs._validate_clients(clients)
        assert is_valid is True
        assert error is None

    def test_validate_clients_mixed_valid_invalid(self):
        """Test list with both valid and invalid clients."""
        clients = ["192.168.1.100", "invalid!client", "10.0.0.0/24"]
        is_valid, error = self.nfs._validate_clients(clients)
        assert is_valid is False
        assert "Invalid client format" in error
        assert "invalid!client" in error

    def test_validate_clients_not_list(self):
        """Test non-list client parameter."""
        is_valid, error = self.nfs._validate_clients("192.168.1.100", "clients")
        assert is_valid is False
        assert "must be a list" in error

    def test_validate_clients_custom_param_name(self):
        """Test error message includes custom parameter name."""
        is_valid, error = self.nfs._validate_clients(["invalid!client"], "read_only_clients")
        assert is_valid is False
        assert "read_only_clients" in error

    def test_validate_clients_error_message_format(self):
        """Test error message includes helpful format guidance."""
        is_valid, error = self.nfs._validate_clients(["invalid!client"])
        assert is_valid is False
        assert "Valid formats:" in error
        assert "IP address" in error
        assert "CIDR" in error
        assert "hostname" in error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
