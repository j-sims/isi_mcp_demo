"""Helpers for shuffling kwargs into Ansible variable dicts.

Domain modules accept many optional parameters that must be forwarded to
Ansible only when explicitly set. These helpers replace the manual
``if val is not None: variables[k] = val`` loops that were duplicated across
every ``add()`` and ``set_global_settings()`` method.
"""

import json
from typing import Any, Dict, Optional


def parse_json_param(name: str, value: Optional[str], default: Any = None) -> Any:
    """Parse a single JSON-string tool parameter, naming it on failure.

    Returns ``default`` when *value* is None/empty. On malformed JSON raises
    ValueError naming *name*, so the caller sees an actionable message instead
    of a bare ``json.JSONDecodeError`` that doesn't say which argument was bad.
    """
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"Parameter '{name}' must be a valid JSON string: {e}") from e


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

    Raises ValueError naming the offending parameter when a value is not valid
    JSON, so the caller gets an actionable message instead of a bare
    ``json.JSONDecodeError`` that doesn't say which argument was malformed.
    """
    result: Dict[str, Any] = {}
    for k, v in kwargs.items():
        if not v:
            continue
        try:
            result[k] = json.loads(v)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(
                f"Parameter '{k}' must be a valid JSON string: {e}"
            ) from e
    return result
