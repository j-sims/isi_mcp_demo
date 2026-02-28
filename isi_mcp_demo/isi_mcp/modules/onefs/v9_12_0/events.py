import logging
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException

logger = logging.getLogger(__name__)


class Events:
    """Provides access to PowerScale event group occurrences via the EventApi."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self, limit=100, resume=None, begin=None, end=None,
            severity=None, resolved=None, ignore=None,
            sort=None, dir=None, cause=None, event_count=None):
        """Retrieve event group occurrences with optional filtering, sorting, and pagination.

        Args:
            limit: Maximum number of results to return (default 100).
            resume: Pagination token from a previous call. When provided, all
                    other filter/sort parameters are ignored by the API.
            begin: Unix epoch timestamp — return events active after this time.
            end: Unix epoch timestamp — return events active before this time.
            severity: Comma-separated severity levels to filter by
                      (e.g. "critical,warning"). Valid values: emergency,
                      critical, warning, information.
            resolved: If True, return only resolved events; False for unresolved.
            ignore: If True, return only ignored events; False for non-ignored.
            sort: Field name to sort results by (e.g. "severity", "begin",
                  "last_event_begin", "event_count").
            dir: Sort direction — "ASC" or "DESC".
            cause: Filter by cause text (substring match, max 255 chars).
            event_count: Return only eventgroups with more than this many
                         occurrences (useful for finding recurring events).

        Returns:
            dict with 'items' (list of eventgroup dicts) and 'resume' token.
        """
        event_api = isi_sdk.EventApi(self.cluster.api_client)
        try:
            if resume:
                # When resume provided, only pass resume — API rejects other params
                kwargs = {"resume": resume}
            else:
                kwargs = {"limit": limit}
                if begin is not None:
                    kwargs["begin"] = begin
                if end is not None:
                    kwargs["end"] = end
                if severity is not None:
                    kwargs["severity"] = [s.strip() for s in severity.split(",")]
                if resolved is not None:
                    kwargs["resolved"] = str(resolved).lower()
                if ignore is not None:
                    kwargs["ignore"] = str(ignore).lower()
                if sort is not None:
                    kwargs["sort"] = sort
                if dir is not None:
                    kwargs["dir"] = dir
                if cause is not None:
                    kwargs["cause"] = cause
                if event_count is not None:
                    kwargs["event_count"] = event_count
            result = event_api.get_event_eventgroup_occurrences(**kwargs)
        except ApiException as e:
            logger.error("API error: %s", e)
            return {"items": [], "resume": None, "error": str(e)}

        items = [eg.to_dict() for eg in result.eventgroups] if result.eventgroups else []
        return {
            "items": items,
            "resume": getattr(result, "resume", None),
        }

    def get_by_id(self, event_id: str):
        """Retrieve a single event group occurrence by its ID.

        Args:
            event_id: The eventgroup occurrence ID (obtained from get() results).

        Returns:
            dict representation of the eventgroup, or dict with 'error' key.
        """
        event_api = isi_sdk.EventApi(self.cluster.api_client)
        try:
            result = event_api.get_event_eventgroup_occurrence(event_id)
            eventgroups = getattr(result, "eventgroups", None)
            if eventgroups:
                return eventgroups[0].to_dict()
            return {"error": f"Event group '{event_id}' not found"}
        except ApiException as e:
            return {"error": str(e)}
