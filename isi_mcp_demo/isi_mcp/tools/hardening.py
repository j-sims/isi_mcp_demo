from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.hardening import Hardening


@safe_tool(group="hardening", mode="read")
def powerscale_hardening_profiles_get(cluster_name: str = None) -> dict:
    """
    List available security hardening profiles on the PowerScale cluster.

    Returns profile names, descriptions, and whether each is currently applied.
    Useful for security compliance auditing.

    Returns:
    - items: List of hardening profile objects
    """
    cluster = get_cluster(cluster_name)
    h = Hardening(cluster)
    return h.get_profiles()


@safe_tool(group="hardening", mode="read")
def powerscale_hardening_state_get(cluster_name: str = None) -> dict:
    """
    Get the current state of the hardening service.

    Returns whether the hardening service is 'Running' or 'Available' and
    which profiles are active.
    """
    cluster = get_cluster(cluster_name)
    h = Hardening(cluster)
    return h.get_state()


@safe_tool(group="hardening", mode="read")
def powerscale_hardening_reports_get(cluster_name: str = None) -> dict:
    """
    List compliance reports for all hardening rules.

    Returns a per-rule compliance status showing which hardening rules
    are passing or failing. Useful for security audit and remediation.

    Returns:
    - items: List of hardening report objects
    """
    cluster = get_cluster(cluster_name)
    h = Hardening(cluster)
    return h.get_reports()
