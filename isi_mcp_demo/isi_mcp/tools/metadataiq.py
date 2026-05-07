from modules.tool_decorator import safe_tool, get_cluster
from modules.onefs.v9_12_0.metadataiq import MetadataIQ


@safe_tool(group="metadataiq", mode="read")
def powerscale_metadataiq_settings_get(cluster_name: str = None) -> dict:
    """
    Get MetadataIQ configuration settings.

    Returns settings for the MetadataIQ service that indexes filesystem
    metadata for analytical querying.
    """
    cluster = get_cluster(cluster_name)
    miq = MetadataIQ(cluster)
    return miq.get_settings()


@safe_tool(group="metadataiq", mode="read")
def powerscale_metadataiq_status_get(cluster_name: str = None) -> dict:
    """
    Get MetadataIQ current cycle status.

    Returns the state of the current metadata indexing cycle (running,
    idle, completing, etc.) and progress information.
    """
    cluster = get_cluster(cluster_name)
    miq = MetadataIQ(cluster)
    return miq.get_status()


@safe_tool(group="metadataiq", mode="read")
def powerscale_metadataiq_certificate_get(cluster_name: str = None) -> dict:
    """
    Get MetadataIQ CA certificate information.
    """
    cluster = get_cluster(cluster_name)
    miq = MetadataIQ(cluster)
    return miq.get_certificate()
