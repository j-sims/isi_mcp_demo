"""Helpers for shuffling kwargs into Ansible variable dicts.

Domain modules accept many optional parameters that must be forwarded to
Ansible only when explicitly set. These helpers replace the manual
``if val is not None: variables[k] = val`` loops that were duplicated across
every ``add()`` and ``set_global_settings()`` method.
"""

import json
from typing import Any, Dict


def drop_none(**kwargs: Any) -> Dict[str, Any]:
    """Return a dict containing only keys whose value is not None.

    Use for forwarding optional parameters to Ansible templates where the
    template should fall back to module/cluster defaults for omitted values.
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def drop_falsy(**kwargs: Any) -> Dict[str, Any]:
    """Return a dict containing only keys whose value is truthy.

    Use when empty strings should be treated the same as None — typical for
    string parameters where "" is meaningless but None means "not provided".
    """
    return {k: v for k, v in kwargs.items() if v}


def parse_json_kwargs(**kwargs: Any) -> Dict[str, Any]:
    """Parse each non-empty value as JSON and return the resulting dict.

    Use for complex parameters (lists/dicts) that arrive as JSON strings from
    MCP tool inputs and must be deserialised before being passed to Ansible.
    Empty/None values are dropped.
    """
    return {k: json.loads(v) for k, v in kwargs.items() if v}
