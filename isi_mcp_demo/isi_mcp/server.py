import asyncio
import fcntl
import inspect as _inspect
import json
import logging
import os
import re as _re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP
from fastmcp.tools import Tool as _FMCPTool
from fastmcp.server.providers.skills import SkillsDirectoryProvider
try:
    from fastmcp.server.auth import RemoteAuthProvider
    from fastmcp.server.auth.providers.jwt import JWTVerifier
    _FASTMCP_AUTH_AVAILABLE = True
except ImportError:
    _FASTMCP_AUTH_AVAILABLE = False
from modules.logging_config import configure_logging
from modules.onefs.v9_12_0.cluster import Cluster
from modules.ansible.vault_manager import VaultManager
from modules.tool_decorator import safe_tool, TOOL_METADATA, bind as _bind_tool_decorator, bind_get_cluster as _bind_get_cluster
from modules.middleware import _FASTMCP_AUTH_AVAILABLE as _MW_AUTH_AVAILABLE
if _MW_AUTH_AVAILABLE:
    from modules.middleware import RoleEnforcementMiddleware, AuditMiddleware, TimeoutMiddleware

configure_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Authentication (optional — disabled when AUTH_ENABLED != "true")
# ---------------------------------------------------------------------------
_auth_provider = None
if os.environ.get("AUTH_ENABLED", "").lower() == "true":
    if _FASTMCP_AUTH_AVAILABLE:
        _keycloak_url = os.environ.get("KEYCLOAK_URL", "http://keycloak:8080")
        _keycloak_realm = os.environ.get("KEYCLOAK_REALM", "powerscale")
        _public_url = os.environ.get("MCP_PUBLIC_URL", "https://localhost")
        _internal_issuer = f"{_keycloak_url}/realms/{_keycloak_realm}"
        _public_issuer = f"{_public_url}/auth/realms/{_keycloak_realm}"

        _auth_provider = RemoteAuthProvider(
            token_verifier=JWTVerifier(
                jwks_uri=f"{_internal_issuer}/protocol/openid-connect/certs",
                issuer=_public_issuer,
            ),
            authorization_servers=[_public_issuer],
            base_url=_public_url,
        )
        logger.info("FastMCP auth enabled (Keycloak realm: %s)", _keycloak_realm)
    else:
        logger.warning("AUTH_ENABLED=true but fastmcp auth modules not available — running without auth")

mcp = FastMCP(
    "powerscale",
    instructions=(
        "This server provides tools for managing a PowerScale (Isilon) cluster."
    ),
    auth=_auth_provider,
)

_bind_tool_decorator(mcp)

# ---------------------------------------------------------------------------
# Tool timeout
# ---------------------------------------------------------------------------
TOOL_TIMEOUT = int(os.environ.get("TOOL_TIMEOUT", 60))

# ---------------------------------------------------------------------------
# Tool config — loaded from config/tools.json at startup
# ---------------------------------------------------------------------------
TOOLS_CONFIG_PATH = os.environ.get("TOOLS_CONFIG_PATH", "/app/config/tools.json")


def _load_tools_config() -> dict:
    with open(TOOLS_CONFIG_PATH, "r") as f:
        return json.load(f)


def _save_tools_config(tools: dict) -> None:
    with open(TOOLS_CONFIG_PATH, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(tools, f, indent=2)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _update_tool_enabled(name: str, enabled: bool) -> None:
    tools = _load_tools_config()
    if name in tools:
        tools[name]["enabled"] = enabled
        _save_tools_config(tools)


_tools_raw = _load_tools_config()

TOOL_GROUPS: Dict[str, List[str]] = {}
_TOOL_TO_MODE: Dict[str, str] = {}
for _name, _meta in _tools_raw.items():
    _grp = _meta["tool_group"]
    TOOL_GROUPS.setdefault(_grp, []).append(_name)
    _TOOL_TO_MODE[_name] = _meta["tool_mode"]

MANAGEMENT_TOOLS = {
    "powerscale_tools_list",
    "powerscale_tools_list_by_group",
    "powerscale_tools_list_by_mode",
    "powerscale_tools_toggle",
    "powerscale_cluster_list",
    "powerscale_cluster_setdefault",
    "powerscale_cluster_add",
    "powerscale_cluster_remove",
    "powerscale_cluster_modify",
}

_TOOL_TO_GROUP: Dict[str, str] = {}
for _grp, _tools in TOOL_GROUPS.items():
    for _t in _tools:
        _TOOL_TO_GROUP[_t] = _grp

_disabled_tools: Dict[str, Any] = {}


def _local_tools() -> Dict[str, Any]:
    return {t.name: t for t in mcp.local_provider._components.values() if isinstance(t, _FMCPTool)}


def _resolve_names_to_tools(names: List[str]) -> List[str]:
    result = []
    for name in names:
        if name in TOOL_GROUPS:
            result.extend(TOOL_GROUPS[name])
        elif name in ("read", "write"):
            result.extend(t for t, m in _TOOL_TO_MODE.items() if m == name)
        elif name in _TOOL_TO_GROUP or name in _disabled_tools:
            result.append(name)
    return result


# ---------------------------------------------------------------------------
# Tool state refresh — sync in-process state with tools.json (for scaling)
# ---------------------------------------------------------------------------
_TOOL_STATE_TTL = 5
_tool_state_last_refresh: float = 0.0


def _refresh_tool_state() -> None:
    global _tool_state_last_refresh
    now = time.monotonic()
    if now - _tool_state_last_refresh < _TOOL_STATE_TTL:
        return
    _tool_state_last_refresh = now

    if os.environ.get("ENABLE_ALL_TOOLS", "").lower() == "true":
        return

    config = _load_tools_config()
    current_tools = _local_tools()
    for name, meta in config.items():
        if name in MANAGEMENT_TOOLS:
            continue
        should_be_enabled = meta.get("enabled", True)
        is_enabled = name in current_tools

        if should_be_enabled and not is_enabled and name in _disabled_tools:
            tool_obj = _disabled_tools.pop(name)
            mcp.add_tool(tool_obj)
            logger.debug("Refresh: re-enabled tool %s", name)
        elif not should_be_enabled and is_enabled:
            _disabled_tools[name] = current_tools[name]
            mcp.local_provider.remove_tool(name)
            logger.debug("Refresh: disabled tool %s", name)


def _get_cluster(cluster_name: str = None) -> Cluster:
    _refresh_tool_state()
    if cluster_name:
        c = Cluster.from_vault_by_name(cluster_name)
    else:
        c = Cluster.from_vault()
    if not c.host:
        raise RuntimeError("No cluster host configured.")
    return c


_bind_get_cluster(_get_cluster)
import tools as _domain_tools  # noqa: F401 — registers @safe_tool decorations

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
_AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "").lower() == "true"

if _MW_AUTH_AVAILABLE:
    if _AUTH_ENABLED and _auth_provider is not None:
        mcp.add_middleware(RoleEnforcementMiddleware(TOOL_GROUPS, _TOOL_TO_MODE, _TOOL_TO_GROUP, MANAGEMENT_TOOLS))
        logger.info("Role enforcement middleware enabled (mcp-read/write/admin + group RBAC)")

    mcp.add_middleware(AuditMiddleware(_TOOL_TO_MODE))
    logger.info("Audit middleware enabled (rotating NDJSON log at /app/audit/audit.log)")

    mcp.add_middleware(TimeoutMiddleware(TOOL_TIMEOUT))
    logger.info("Timeout middleware enabled (%ds wall-clock limit per tool call)", TOOL_TIMEOUT)

# ---------------------------------------------------------------------------
# Skills provider
# ---------------------------------------------------------------------------
_skills_dir = Path(__file__).parent / "skills"
if _skills_dir.exists():
    try:
        mcp.add_provider(SkillsDirectoryProvider(roots=_skills_dir, reload=True))
        logger.info("Skills provider enabled (loaded from %s)", _skills_dir)
    except Exception as e:
        logger.warning("Failed to load skills from %s: %s", _skills_dir, e)
else:
    logger.debug("Skills directory not found at %s (optional)", _skills_dir)

# ---------------------------------------------------------------------------
# Tool management tools and cluster management tools
# ---------------------------------------------------------------------------
import tools.management as _mgmt_tools  # noqa: E402 — must be after bind(mcp)
import tools.clusters as _cluster_tools  # noqa: E402
_mgmt_tools.register(
    mcp,
    local_tools_fn=_local_tools,
    load_config_fn=_load_tools_config,
    update_enabled_fn=_update_tool_enabled,
    tool_groups=TOOL_GROUPS,
    tool_to_mode=_TOOL_TO_MODE,
    disabled_tools=_disabled_tools,
    resolve_names_fn=_resolve_names_to_tools,
    management_tools=MANAGEMENT_TOOLS,
)
_cluster_tools.register(mcp, VaultManager)

# ---------------------------------------------------------------------------
# Utility tools
# ---------------------------------------------------------------------------

@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
def powerscale_mcp_resources_list() -> dict:
    """
    List all available MCP resources (including skills) exposed by this server.

    This diagnostic tool shows what resources are available for MCP clients to
    read. Resources include:
    - Skills (skill://name/SKILL.md) — instruction templates for the LLM
    - Manifests (skill://name/_manifest) — file listings for each skill

    Use this to verify that skills have been properly loaded and exposed.

    Response fields:
    - resources: List of available resources with uri, name, and description
    - total: Total number of resources
    """
    async def _list_resources():
        return await mcp.list_resources()

    try:
        resources = asyncio.new_event_loop().run_until_complete(_list_resources())
        return {
            "resources": [
                {
                    "uri": str(r.uri),
                    "name": r.name,
                    "description": r.description or "",
                    "mime_type": r.mime_type or "text/plain",
                }
                for r in resources
            ],
            "total": len(resources),
        }
    except Exception as e:
        return {"error": str(e), "resources": [], "total": 0}


# ---------------------------------------------------------------------------
# Startup: apply enabled flags from tools.json
# ---------------------------------------------------------------------------

def _apply_startup_config() -> None:
    current_tools = _local_tools()
    if os.environ.get("ENABLE_ALL_TOOLS", "").lower() == "true":
        logger.info("ENABLE_ALL_TOOLS set — all %d tools enabled", len(current_tools))
        return

    config = _load_tools_config()
    for name, meta in config.items():
        if meta.get("enabled", True):
            continue
        if name in MANAGEMENT_TOOLS:
            continue
        if name in current_tools:
            _disabled_tools[name] = current_tools[name]
            mcp.local_provider.remove_tool(name)
            logger.info("Disabled tool: %s", name)

    enabled = len(_local_tools())
    disabled = len(_disabled_tools)
    logger.info("%d tools enabled, %d tools disabled", enabled, disabled)


_apply_startup_config()


# ---------------------------------------------------------------------------
# Inject per-parameter descriptions into FastMCP tool input schemas
# ---------------------------------------------------------------------------

def _parse_docstring_args(fn) -> dict:
    """Parse the 'Arguments:' section of a docstring into {param_name: description}."""
    doc = _inspect.getdoc(fn) or ""
    params = {}
    in_args = False
    current_param = None
    current_desc = []

    for line in doc.split('\n'):
        stripped = line.strip()
        if _re.match(r'^(Arguments|Args|Parameters)\s*:', stripped, _re.IGNORECASE):
            in_args = True
            continue
        if not in_args:
            continue
        if stripped and stripped.endswith(':') and not stripped.startswith('-'):
            break
        m = _re.match(r'^-\s+(\w+)\s*:\s*(.*)', stripped)
        if m:
            if current_param:
                params[current_param] = ' '.join(current_desc).strip()
            current_param = m.group(1)
            current_desc = [m.group(2)] if m.group(2) else []
        elif current_param and stripped:
            current_desc.append(stripped)
        elif not stripped and current_param:
            params[current_param] = ' '.join(current_desc).strip()
            current_param = None
            current_desc = []

    if current_param:
        params[current_param] = ' '.join(current_desc).strip()
    return params


_MAX_PARAM_DESC = 200

for _tool in _local_tools().values():
    _fn = getattr(_tool, 'fn', None)
    if _fn is None:
        continue
    _param_docs = _parse_docstring_args(_fn)
    if not _param_docs:
        continue
    _props = _tool.parameters.get("properties", {}) if isinstance(_tool.parameters, dict) else {}
    for _pname, _pdesc in _param_docs.items():
        if _pname in _props and _pdesc:
            _props[_pname]["description"] = _pdesc[:_MAX_PARAM_DESC]


app = mcp.http_app(json_response=True)


# ---------------------------------------------------------------------------
# Health and version endpoints
# ---------------------------------------------------------------------------
from starlette.responses import JSONResponse
from starlette.routing import Route


async def _health_handler(request):
    tool_count = len(_local_tools())
    return JSONResponse({"status": "ok", "tools_loaded": tool_count})


app.routes.insert(0, Route("/health", _health_handler, methods=["GET"]))


async def _version_handler(request):
    version_file = "/app/VERSION"
    try:
        with open(version_file, "r") as f:
            version = f.read().strip()
        return JSONResponse({"version": version})
    except FileNotFoundError:
        return JSONResponse({"error": "VERSION file not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


app.routes.insert(0, Route("/version", _version_handler, methods=["GET"]))
