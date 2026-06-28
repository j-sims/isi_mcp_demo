"""Tool management MCP tools: list, list-by-group, list-by-mode, toggle.

These tools are always registered and cannot be disabled via the toggle.
Call register(mcp, ...) from server.py after all state is initialised.
"""

from typing import Any, Dict, List


def register(mcp, local_tools_fn, load_config_fn, update_enabled_fn,
             tool_groups, tool_to_mode, disabled_tools, resolve_names_fn,
             management_tools):
    """Register the four tool-management tools against the given FastMCP instance."""

    @mcp.tool()
    def powerscale_tools_list() -> List[Dict[str, Any]]:
        """
        List all PowerScale MCP tools alphabetically by name.

        Returns a flat list of every tool with its name, group, mode (read/write),
        and whether it is currently enabled or disabled.

        Use this tool to:
        - Get a complete inventory of all available tools
        - See each tool's group and mode at a glance
        - Check which individual tools are currently enabled or disabled

        Each entry contains:
        - name: Tool function name
        - group: Tool group (e.g. "quotas", "filemgmt", "management")
        - mode: "read" (non-destructive) or "write" (modifies cluster state)
        - enabled: true if the tool is currently registered with the MCP server
        """
        enabled_set = set(local_tools_fn().keys())
        config = load_config_fn()
        _tool_to_group = {t: g for g, ts in tool_groups.items() for t in ts}
        return sorted(
            [
                {
                    "name": name,
                    "group": _tool_to_group.get(name, "management"),
                    "mode": tool_to_mode.get(name, "read"),
                    "enabled": name in enabled_set,
                }
                for name in config
            ],
            key=lambda x: x["name"],
        )

    @mcp.tool()
    def powerscale_tools_list_by_group() -> Dict[str, Any]:
        """
        List all PowerScale MCP tools organised by group.

        Returns a dict with each group mapped to its tools, showing the mode
        (read/write) and enabled status of every tool in that group.

        Use this tool to:
        - See which tools belong to each functional area
        - Compare enabled/disabled counts across groups
        - Decide which group to enable or disable with powerscale_tools_toggle

        Response fields:
        - groups: Dict mapping group name to a list of tool entries, each with
          "name", "mode", and "enabled"
        - total_enabled: Total number of currently enabled tools
        - total_disabled: Total number of currently disabled tools
        """
        enabled_set = set(local_tools_fn().keys())
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for group_name, tool_names in tool_groups.items():
            groups[group_name] = [
                {
                    "name": t,
                    "mode": tool_to_mode.get(t, "read"),
                    "enabled": t in enabled_set,
                }
                for t in tool_names
            ]
        return {
            "groups": groups,
            "total_enabled": len(enabled_set),
            "total_disabled": len(disabled_tools),
        }

    @mcp.tool()
    def powerscale_tools_list_by_mode() -> Dict[str, Any]:
        """
        List all PowerScale MCP tools organised by mode (read or write).

        Read tools only retrieve information from the cluster without making changes.
        Write tools modify cluster state (create, update, or delete resources).

        Use this tool to:
        - See all read-only tools vs all write (mutating) tools at a glance
        - Decide whether to restrict the LLM to read-only operations by disabling
          all write tools via powerscale_tools_toggle(["write"], "disable")
        - Check how many write tools are currently enabled

        Response fields:
        - by_mode: Dict with "read" and "write" keys, each containing a list of
          tool entries with "name", "group", and "enabled"
        - read_count: Total number of read tools
        - write_count: Total number of write tools
        """
        enabled_set = set(local_tools_fn().keys())
        config = load_config_fn()
        _tool_to_group = {t: g for g, ts in tool_groups.items() for t in ts}
        by_mode: Dict[str, List[Dict[str, Any]]] = {"read": [], "write": []}
        for name in sorted(config):
            mode = tool_to_mode.get(name, "read")
            by_mode[mode].append(
                {
                    "name": name,
                    "group": _tool_to_group.get(name, "management"),
                    "enabled": name in enabled_set,
                }
            )
        return {
            "by_mode": by_mode,
            "read_count": len(by_mode["read"]),
            "write_count": len(by_mode["write"]),
        }

    @mcp.tool()
    def powerscale_tools_toggle(names: List[str], action: str) -> Dict[str, Any]:
        """
        Enable or disable PowerScale MCP tools at runtime.

        IMPORTANT: This is a MUTATING operation that changes which tools are
        available to the LLM. After toggling, the MCP client will be notified
        that the tool list has changed and will re-fetch it automatically.

        You can pass group names (e.g. "filemgmt", "synciq") to toggle all tools
        in that group at once, individual tool names for fine-grained control, or
        the special mode targets "read" or "write" to toggle all read-only or all
        write tools at once.

        To see the full, current set of group names (and which tools each contains),
        call powerscale_tools_list_by_group — that is the authoritative source and
        never drifts as groups are added.

        Arguments:
        - names: List of group names, individual tool names, and/or mode targets.
          Examples: ["filemgmt"], ["synciq", "s3"], ["powerscale_quota_remove"],
          ["write"] to disable all write tools, ["read"] to enable all read tools.
        - action: "disable" to remove tools from the tool list, or "enable" to
          restore them.

        Note: management/cluster tools (powerscale_tools_* and powerscale_cluster_*)
        are operator-controlled and cannot be enabled or disabled here in either
        direction. They are governed by config/tools.json (and, when auth is enabled,
        the Keycloak mcp-admin role). Names that resolve to management tools are
        reported under "refused_management" and left unchanged.

        Use this tool when:
        - The user wants to reduce token usage by disabling unused tool groups
        - The user wants to re-enable previously disabled tools
        - You need to streamline the tool list for a specific task

        Returns:
        - action: The action performed ("disable" or "enable")
        - toggled: List of tool names that were actually toggled
        - skipped: List of names that were already in the requested state
        - total_enabled: Updated count of enabled tools
        - total_disabled: Updated count of disabled tools
        - refused_management: (only present when applicable) management/cluster
          tool names that were left unchanged because they are operator-controlled
        """
        if action not in ("enable", "disable"):
            return {"error": f"Invalid action '{action}'. Must be 'enable' or 'disable'."}

        tool_names = resolve_names_fn(names)
        toggled = []
        skipped = []
        refused_management = []

        current_tools = local_tools_fn()
        if action == "disable":
            for name in tool_names:
                # Management tools are operator-controlled: never disable them here.
                if name in management_tools:
                    refused_management.append(name)
                    continue
                if name in current_tools:
                    disabled_tools[name] = current_tools[name]
                    mcp.local_provider.remove_tool(name)
                    toggled.append(name)
                else:
                    skipped.append(name)
        else:  # enable
            for name in tool_names:
                # Management tools are operator-controlled: the LLM must never be
                # able to re-register one an operator disabled via tools.json.
                if name in management_tools:
                    refused_management.append(name)
                    continue
                if name in disabled_tools:
                    tool_obj = disabled_tools.pop(name)
                    mcp.add_tool(tool_obj)
                    toggled.append(name)
                else:
                    skipped.append(name)

        # Only non-management toggles reach here, so management entries in
        # tools.json are never rewritten by this tool.
        for name in toggled:
            update_enabled_fn(name, enabled=(action == "enable"))

        result = {
            "action": action,
            "toggled": toggled,
            "skipped": skipped,
            "total_enabled": len(local_tools_fn()),
            "total_disabled": len(disabled_tools),
        }
        if refused_management:
            result["refused_management"] = sorted(set(refused_management))
            result["message"] = (
                "Management tools are operator-controlled and cannot be enabled or "
                "disabled with this tool. To change them, edit config/tools.json "
                "directly (the change is applied within a few seconds)."
            )
        return result
