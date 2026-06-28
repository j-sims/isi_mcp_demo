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


def parse_json_list_param(name: str, value: Optional[str], default: Any = None) -> Any:
    """Parse a JSON-string parameter that must decode to a list of objects.

    Like :func:`parse_json_param`, but enforces the expected shape for tool
    parameters such as ``conditions``/``attrs``/``acl`` that are documented as a
    JSON *array* of objects. A lone object is wrapped into a one-element list as a
    convenience. Anything else (a scalar, or a list whose elements are not
    objects) raises a clear ValueError naming *name*, instead of letting the
    domain layer blow up later with an opaque ``'str' object has no attribute
    'get'`` AttributeError.

    Returns ``default`` when *value* is None/empty.
    """
    if not value:
        return default
    parsed = parse_json_param(name, value, default)
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise ValueError(
            f"Parameter '{name}' must be a JSON array of objects, "
            f"e.g. '[{{\"key\": \"value\"}}]'."
        )
    return parsed


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
