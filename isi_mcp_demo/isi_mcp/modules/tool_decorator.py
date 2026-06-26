"""``safe_tool`` — single decorator for MCP tool registration.

Replaces the ``@mcp.tool()`` + per-tool try/except boilerplate that was
duplicated across 200+ tools. Also co-locates tool metadata (group, mode)
with the function instead of in a separate ``config/tools.json`` registry.

Usage::

    @safe_tool(group="quotas", mode="read")
    def powerscale_quota_get(cluster_name: str = None) -> dict:
        '''docstring'''
        cluster = _get_cluster(cluster_name)
        return Quotas(cluster).get()

The decorator:
  1. Registers metadata (group, mode) in ``TOOL_METADATA`` so the server can
     build ``TOOL_GROUPS`` and ``_TOOL_TO_MODE`` without re-reading a JSON file.
  2. Wraps the body in try/except returning ``{"error": str(e)}`` on failure.
  3. Calls ``mcp.tool()`` to register with FastMCP.

The MCP instance is injected via ``bind(mcp)`` at module-import time in
server.py to avoid a circular import.
"""

import functools
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Imported at module load so a missing SDK never breaks tool registration.
try:
    from isilon_sdk.v9_12_0.rest import ApiException as _ApiException
except Exception:  # pragma: no cover - SDK always present in container
    _ApiException = None


def _sanitize_exception(fn_name: str, exc: Exception) -> str:
    """Build a client-safe error string for an exception.

    SDK ``ApiException`` objects carry the full HTTP response body — which can
    include internal IPs, node names, stack traces and auth specifics. We return
    only the status line to the client and log the full detail server-side.
    """
    if _ApiException is not None and isinstance(exc, _ApiException):
        status = getattr(exc, "status", None)
        reason = getattr(exc, "reason", None) or "API error"
        # Full body (incl. headers) goes to the server log only.
        logger.warning(
            "Tool %s ApiException: status=%s reason=%s body=%s",
            fn_name, status, reason, getattr(exc, "body", None),
        )
        return f"{status} {reason}".strip() if status else str(reason)
    return str(exc)

# Populated by every @safe_tool() decoration:
#   {tool_name: {"group": ..., "mode": ...}}
TOOL_METADATA: Dict[str, Dict[str, str]] = {}

_VALID_MODES = {"read", "write"}

# Set by bind() at server-module import time.
_mcp_instance = None

# Set by bind_get_cluster() after _get_cluster is defined in server.py.
_get_cluster_fn = None


def bind(mcp) -> None:
    """Bind the FastMCP instance the decorator should register tools against."""
    global _mcp_instance
    _mcp_instance = mcp


def bind_get_cluster(fn: Callable) -> None:
    """Bind the _get_cluster factory so tools/ files can call get_cluster()."""
    global _get_cluster_fn
    _get_cluster_fn = fn


def get_cluster(cluster_name: Optional[str] = None):
    """Create a Cluster from vault credentials.

    Delegates to the _get_cluster function bound by server.py at startup.
    Raises RuntimeError if called before bind_get_cluster() runs.
    """
    if _get_cluster_fn is None:
        raise RuntimeError(
            "get_cluster used before bind_get_cluster() was called — import order issue"
        )
    return _get_cluster_fn(cluster_name)


def safe_tool(*, group: str, mode: str) -> Callable:
    """Register an MCP tool with co-located metadata and standard error handling.

    Args:
        group: Functional group name (e.g. "quotas", "smb"). Used by the tool
            toggle and Keycloak group RBAC.
        mode: "read" (non-destructive) or "write" (mutating). Used by Keycloak
            mode RBAC and by the audit middleware.
    """
    if mode not in _VALID_MODES:
        raise ValueError(f"safe_tool mode must be one of {_VALID_MODES}, got {mode!r}")

    def decorator(fn: Callable) -> Callable:
        TOOL_METADATA[fn.__name__] = {"group": group, "mode": mode}

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                logger.exception("Tool %s failed", fn.__name__)
                return {"error": _sanitize_exception(fn.__name__, e)}

        if _mcp_instance is None:
            raise RuntimeError(
                "safe_tool used before bind(mcp) was called — import order issue"
            )
        return _mcp_instance.tool()(wrapper)

    return decorator
