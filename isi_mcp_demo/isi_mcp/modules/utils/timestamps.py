from datetime import datetime, timezone
from typing import Optional, Union


def epoch_to_iso(ts: Optional[int]) -> Optional[str]:
    """Convert a Unix epoch integer to an ISO 8601 string (UTC).

    Returns None if ts is None or 0.
    """
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def add_iso_timestamps(data: Union[list, dict], fields: list) -> None:
    """Add ``{field}_iso`` companion keys alongside raw Unix timestamp fields.

    Mutates *data* in-place.  Works on a single dict or a list of dicts.
    For each field name in *fields*, if the key exists in the dict and its
    value is a non-None integer, a new ``{field}_iso`` key is added with the
    equivalent ISO 8601 string (e.g. ``"2024-01-01T00:00:00+00:00"``).

    Skips items that are not dicts (e.g. None entries in a list).
    """
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                add_iso_timestamps(item, fields)
    elif isinstance(data, dict):
        for field in fields:
            val = data.get(field)
            if val is not None:
                data[f"{field}_iso"] = epoch_to_iso(val)
