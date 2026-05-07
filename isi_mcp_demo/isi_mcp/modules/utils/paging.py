"""Pagination helpers shared across tools."""

from typing import Optional


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
    return {"items": items, "resume": resume, "limit": limit, "has_more": bool(resume)}
