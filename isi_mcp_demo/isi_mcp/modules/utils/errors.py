"""Shared helpers for turning exceptions into client-safe messages.

Mirrors the sanitisation that ``tool_decorator._sanitize_exception`` applies to
exceptions that propagate up to ``@safe_tool``: SDK ``ApiException`` objects carry
the full HTTP response body (internal IPs, node names, auth specifics) in their
``str()``, so domain modules that *catch* an ApiException and place it into a
returned dict must sanitise it the same way — otherwise that detail leaks to the
client. Full detail is still available server-side via the caller's own logging.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from isilon_sdk.v9_12_0.rest import ApiException as _ApiException
except Exception:  # pragma: no cover - SDK always present in container
    _ApiException = None


def safe_api_error(exc) -> str:
    """Return a client-safe ``"API error: ..."`` string for *exc*.

    For an SDK ``ApiException`` only the ``status``/``reason`` line is returned
    (never the response body/headers). Other exceptions fall back to their plain
    string, which does not carry the SDK response body.
    """
    if _ApiException is not None and isinstance(exc, _ApiException):
        status = getattr(exc, "status", None)
        reason = getattr(exc, "reason", None) or "API error"
        return f"API error: {status} {reason}".strip() if status else f"API error: {reason}"
    return f"API error: {exc}"
