"""Pagination helpers shared across tools and domain modules."""

from typing import Any, Dict, Optional


def page_kwargs(limit: int, resume: Optional[str], **extra: Any) -> Dict[str, Any]:
    """Build the kwargs dict for a paginated SDK list call.

    When resuming, only the resume token is passed (limit and extras are ignored
    by the API). On the first page, limit and any non-None extra filters are included.
    """
    if resume:
        return {"resume": resume}
    return {"limit": limit, **{k: v for k, v in extra.items() if v is not None}}


def normalize_resume(resume) -> Optional[str]:
    """Coerce the resume token strings "null" and "None" (which LLMs sometimes
    pass) to None so the API treats them as a first-page request."""
    return None if resume in (None, "null", "None") else resume


def paginated_result(page: dict, limit: int) -> dict:
    """Build the standard paginated response dict from a module page result.

    Expects the page dict to contain "items" and optionally "resume".
    Returns {"items": [...], "resume": token|None, "limit": N, "has_more": bool}.
    """
    items = page.get("items") or []
    resume = page.get("resume") or None
    result = {"items": items, "resume": resume, "limit": limit, "has_more": bool(resume)}
    # Propagate an error reported by the module's page result so a failed list call
    # isn't flattened into an indistinguishable empty page at the tool layer.
    if page.get("error") is not None:
        result["error"] = page["error"]
    return result
