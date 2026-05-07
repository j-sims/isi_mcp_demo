from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.events import Events
from modules.utils.paging import normalize_resume, paginated_result
from typing import Dict, Any, Optional


@safe_tool(group="events", mode="read")
def powerscale_event_get(
    limit: int = 100,
    resume: Optional[str] = None,
    begin: Optional[int] = None,
    end: Optional[int] = None,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    ignore: Optional[bool] = None,
    sort: Optional[str] = None,
    dir: Optional[str] = None,
    cause: Optional[str] = None,
    event_count: Optional[int] = None,
    cluster_name: str = None,
) -> Dict[str, Any]:
    """
    Retrieve event group occurrences from the PowerScale cluster with optional
    filtering, sorting, and pagination.

    Each result item represents an "event group occurrence" — a logical cluster
    of related individual events (e.g. all occurrences of a particular hardware
    fault are grouped together). Key fields in each item include:
    - id: Unique event group identifier (use with powerscale_event_get_by_id)
    - severity: "emergency", "critical", "warning", or "information"
    - cause: Short description of the event type
    - cause_string: Human-readable description
    - begin: Unix timestamp when the event group started
    - end: Unix timestamp when it ended (null if still active)
    - resolved: Whether the event group has been resolved
    - ignore: Whether the event group has been ignored/suppressed
    - event_count: Number of individual events in this group
    - last_event_begin: Timestamp of the most recent event in the group

    Pagination:
    - Use 'limit' to control the number of results per page (default 100).
    - If 'has_more' is True in the response, pass the returned 'resume' token
      to the next call to fetch the next page.
    - IMPORTANT: When 'resume' is provided, all other filter/sort parameters
      are ignored by the API. Use the same filters for subsequent pages by
      relying on the resume token chain.

    Date range filtering (Unix epoch timestamps):
    - 'begin': Return events that were active after this time.
    - 'end': Return events that were active before this time.
    - To get events from the last 24 hours: begin=<current_epoch - 86400>.
      Use the 'current_time' tool (utils group) to get the current epoch.
    - To get events from the last 7 days: begin=<current_epoch - 604800>.

    Arguments:
    - limit: Maximum results per page (default 100, max 4294967295)
    - resume: Pagination token from a previous call
    - begin: Unix timestamp — events active after this time
    - end: Unix timestamp — events active before this time
    - severity: Comma-separated severity levels to filter by, e.g. "critical"
                or "critical,warning". Valid: emergency, critical, warning,
                information
    - resolved: True to return only resolved events, False for unresolved only
    - ignore: True to return only ignored events, False for non-ignored only
    - sort: Field to sort by — e.g. "severity", "begin", "last_event_begin",
            "event_count", "cause"
    - dir: Sort direction — "ASC" or "DESC"
    - cause: Filter by cause text (substring match)
    - event_count: Return only event groups with more than this many occurrences
                   (useful for finding frequently recurring events)

    Use this tool when the user wants to:
    - See current active or unresolved cluster events/alerts
    - Find critical or warning events on the cluster
    - Investigate events within a specific date range
    - Search for events by cause description
    - Find high-frequency recurring events
    - Page through a large event history
    """
    resume = normalize_resume(resume)
    cluster = get_cluster(cluster_name)
    page = Events(cluster).get(
        limit=limit, resume=resume, begin=begin, end=end,
        severity=severity, resolved=resolved, ignore=ignore,
        sort=sort, dir=dir, cause=cause, event_count=event_count,
    )
    result = paginated_result(page, limit)
    if "error" in page:
        result["error"] = page["error"]
    return result


@safe_tool(group="events", mode="read")
def powerscale_event_get_by_id(event_id: str, cluster_name: str = None) -> Dict[str, Any]:
    """
    Retrieve a single event group occurrence by its ID.

    Returns the full detail of one event group occurrence, including all fields
    such as severity, cause, cause_string, begin/end timestamps, event_count,
    resolved status, and associated devids (node IDs).

    Arguments:
    - event_id: The event group occurrence ID. Obtain IDs from the 'id' field
                of results returned by powerscale_event_get.

    Use this tool when the user wants to:
    - Inspect the full details of a specific event
    - Get the complete cause description and resolution information for an alert
    - Check whether a specific event has been resolved
    """
    cluster = get_cluster(cluster_name)
    events = Events(cluster)
    return events.get_by_id(event_id)
