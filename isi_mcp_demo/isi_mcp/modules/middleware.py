"""FastMCP middleware: RBAC, audit, and timeout.

Instantiate each class with its dependencies and add to mcp via mcp.add_middleware().
All three classes require _FASTMCP_AUTH_AVAILABLE; check that flag before use.
"""

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

try:
    from fastmcp.server.middleware import Middleware
    from fastmcp.server.dependencies import get_access_token
    from fastmcp.exceptions import ToolError
    _FASTMCP_AUTH_AVAILABLE = True
except ImportError:
    _FASTMCP_AUTH_AVAILABLE = False


if _FASTMCP_AUTH_AVAILABLE:
    class RoleEnforcementMiddleware(Middleware):
        """Enforce Keycloak realm roles on tool calls and tool listing.

        Two-dimensional authorization:
          1. Mode check: mcp-read / mcp-write / mcp-admin
          2. Group check: mcp-group-{name} roles restrict visibility to specific
             tool groups. No group roles = all groups accessible (backward compat).
             mcp-admin always bypasses group filtering.
        """

        def __init__(self, tool_groups, tool_to_mode, tool_to_group, management_tools):
            self._tool_groups = tool_groups
            self._tool_to_mode = tool_to_mode
            self._tool_to_group = tool_to_group
            self._management_tools = management_tools

        def _get_user_roles(self) -> set:
            token = get_access_token()
            if token is None:
                return set()
            return set(token.claims.get("realm_access", {}).get("roles", []))

        def _required_role(self, tool_name: str) -> str:
            if tool_name in self._management_tools:
                return "mcp-admin"
            if self._tool_to_mode.get(tool_name) == "write":
                return "mcp-write"
            return "mcp-read"

        def _allowed_groups(self, user_roles: set):
            groups = set()
            for role in user_roles:
                if role.startswith("mcp-group-"):
                    group_name = role[len("mcp-group-"):]
                    if group_name in self._tool_groups:
                        groups.add(group_name)
            return groups if groups else None

        async def on_call_tool(self, context, call_next):
            tool_name = context.message.name
            required = self._required_role(tool_name)
            user_roles = self._get_user_roles()
            if required not in user_roles:
                raise ToolError(
                    f"Access denied: '{tool_name}' requires the '{required}' role. "
                    f"Your roles: {sorted(user_roles) or ['none']}"
                )
            if "mcp-admin" not in user_roles and tool_name not in self._management_tools:
                allowed = self._allowed_groups(user_roles)
                if allowed is not None:
                    tool_group = self._tool_to_group.get(tool_name)
                    if tool_group not in allowed:
                        raise ToolError(
                            f"Access denied: '{tool_name}' (group '{tool_group}') "
                            f"is not in your allowed groups. "
                            f"Your group roles: {sorted(f'mcp-group-{g}' for g in allowed)}"
                        )
            return await call_next(context)

        async def on_list_tools(self, context, call_next):
            tools = await call_next(context)
            user_roles = self._get_user_roles()
            filtered = [t for t in tools if self._required_role(t.name) in user_roles]
            if "mcp-admin" not in user_roles:
                allowed = self._allowed_groups(user_roles)
                if allowed is not None:
                    filtered = [
                        t for t in filtered
                        if t.name in self._management_tools
                        or self._tool_to_group.get(t.name) in allowed
                    ]
            return filtered

    class AuditMiddleware(Middleware):
        """Record every tool call as a single NDJSON line in the rotating audit log.

        Always active regardless of AUTH_ENABLED — uses anonymous/local when no
        JWT token is present.
        """

        def __init__(self, tool_to_mode):
            from modules.audit.logger import AuditLogger
            self._audit = AuditLogger()
            self._tool_to_mode = tool_to_mode

        def _caller_info(self) -> tuple:
            try:
                token = get_access_token()
            except Exception:
                token = None
            if token is not None:
                username = token.claims.get("preferred_username", "unknown")
                issuer = token.claims.get("iss", "")
                parts = issuer.rstrip("/").split("/")
                domain = parts[-1] if parts else "unknown"
            else:
                username = "anonymous"
                domain = "local"
            return username, domain

        @staticmethod
        def _extract_output(result) -> Any:
            if result is None:
                return None
            structured = getattr(result, "structured_content", None)
            if structured is not None:
                return structured
            content = getattr(result, "content", None)
            if not content:
                return None
            texts = [getattr(block, "text", None) for block in content]
            texts = [t for t in texts if t is not None]
            if not texts:
                return None
            combined = "\n".join(texts)
            try:
                return json.loads(combined)
            except (json.JSONDecodeError, ValueError):
                return combined

        async def on_call_tool(self, context, call_next):
            tool_name = context.message.name
            mode = self._tool_to_mode.get(tool_name, "read")
            inputs = getattr(context.message, "arguments", {}) or {}
            username, domain = self._caller_info()
            error = None
            result = None
            try:
                result = await call_next(context)
                return result
            except Exception as exc:
                error = str(exc)
                raise
            finally:
                self._audit.log(username, domain, tool_name, mode, inputs,
                                self._extract_output(result), error)

    class TimeoutMiddleware(Middleware):
        """Enforce a hard wall-clock deadline on every tool call.

        Registered last so it wraps the actual tool execution (innermost middleware).
        Uses asyncio.shield so the underlying thread drains via API_TIMEOUT rather
        than being forcibly cancelled.
        """

        _thread_capacity_configured: bool = False

        def __init__(self, timeout: int):
            self._timeout = timeout

        async def on_call_tool(self, context, call_next):
            if not TimeoutMiddleware._thread_capacity_configured:
                import anyio
                limiter = anyio.to_thread.current_default_thread_limiter()
                limiter.total_tokens = int(os.environ.get("TOOL_THREADS", 200))
                TimeoutMiddleware._thread_capacity_configured = True
                logger.info("anyio thread capacity set to %d", limiter.total_tokens)

            tool_name = context.message.name
            loop = asyncio.get_running_loop()
            inner_task = loop.create_task(call_next(context))

            def _drain(task):
                if not task.cancelled():
                    try:
                        task.exception()
                    except Exception:
                        pass

            try:
                return await asyncio.wait_for(asyncio.shield(inner_task), timeout=self._timeout)
            except asyncio.TimeoutError:
                inner_task.add_done_callback(_drain)
                raise TimeoutError(
                    f"Tool '{tool_name}' exceeded the {self._timeout}s timeout. "
                    "The cluster may be slow or unreachable."
                )
            except asyncio.CancelledError:
                inner_task.add_done_callback(_drain)
                raise
