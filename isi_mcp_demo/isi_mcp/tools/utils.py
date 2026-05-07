import re as _re
from datetime import datetime
from modules.tool_decorator import safe_tool


@safe_tool(group="utils", mode="read")
def current_time() -> dict:
    """
    Return the current local date and time from the PowerScale MCP server.

    This provides a real-time timestamp from the server hosting the MCP service,
    which may differ from the user's local time if the server is in a different
    timezone or geographic location.

    Response fields:
    - date: Current date in yyyy-mm-dd format
    - time: Current time in HH:MM:SS format (24-hour)
    - timezone: Timezone abbreviation (e.g. "UTC", "EST", "PST")
    - gmt_offset: Numeric offset from GMT (e.g. "+0000", "-0500")

    Use this tool to answer questions such as:
    - What time is it on the PowerScale management server?
    - What timezone is the MCP server running in?
    - What is today's date according to the cluster?
    - Is there a time difference between my location and the server?

    This is also useful for correlating timestamps in snapshot schedules,
    replication jobs, or event logs with the actual server clock.
    """
    now = datetime.now().astimezone()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": now.strftime("%Z"),
        "gmt_offset": now.strftime("%z"),
    }


@safe_tool(group="utils", mode="read")
def bytes_to_human(bytes_value: int) -> dict:
    """
    Convert a byte value to a human-readable IEC string (base-1024).

    IEC units use base-1024 (binary) prefixes: KiB, MiB, GiB, TiB, PiB, EiB.
    The tool automatically selects the most appropriate unit for readability.

    Only one value should be submitted per call.

    Arguments:
    - bytes_value: An integer number of bytes (e.g. 84079902720)

    Response fields:
    - bytes: The original byte value (echoed back for reference)
    - human_readable: The formatted string (e.g. "78.31GiB")

    Use this tool when you need to:
    - Present capacity, quota, or snapshot sizes in a readable format
    - Convert raw byte values from other PowerScale tools for the user
    - Format storage statistics before displaying them

    Example: 84079902720 bytes -> "78.31GiB"
    """
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB"]
    value = float(bytes_value)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return {"bytes": bytes_value, "human_readable": f"{value:.2f}{unit}"}
        value /= 1024


@safe_tool(group="utils", mode="read")
def human_to_bytes(human_value: str) -> dict:
    """
    Convert a human-readable IEC string (base-1024) to an integer byte value.

    This is the inverse of bytes_to_human. It parses a size string with an IEC
    unit suffix and returns the equivalent number of bytes.

    Supported units: B, KiB, MiB, GiB, TiB, PiB, EiB (base-1024).

    Only one value should be submitted per call.

    Arguments:
    - human_value: A size string with unit (e.g. "78.31GiB", "500MiB", "1TiB")

    Response fields:
    - human_readable: The original string (echoed back for reference)
    - bytes: The computed integer byte value

    Use this tool when you need to:
    - Convert a user-provided size (e.g. "500GiB") into bytes for quota tools
    - Prepare byte values for powerscale_quota_set, powerscale_quota_increment,
      or powerscale_quota_decrement which require sizes in bytes
    - Validate or normalize a user's size input

    Example: "78.31GiB" -> 84079902720 bytes
    """
    units = {"B": 0, "KiB": 1, "MiB": 2, "GiB": 3, "TiB": 4, "PiB": 5, "EiB": 6}
    match = _re.fullmatch(r"\s*([\d.]+)\s*(B|KiB|MiB|GiB|TiB|PiB|EiB)\s*", human_value)
    if not match:
        raise ValueError(f"Invalid human-readable value: {human_value}")
    value = float(match.group(1))
    unit = match.group(2)
    return {"human_readable": human_value, "bytes": int(value * (1024 ** units[unit]))}
