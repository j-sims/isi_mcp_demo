import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class SnapshotChangelists:
    """Provides access to snapshot changelist history via the SnapshotChangelistsApi.

    Changelists track changes between two snapshots, providing LIN (Logical Inode
    Number) entries and directory/file change details.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get_entries(self, changelist_id: str, resume: str = None, limit: int = 100):
        """List all entries in a snapshot changelist.

        Arguments:
        - changelist_id: The changelist identifier
        - resume: Pagination token from a previous call
        - limit: Maximum number of results (default 100)
        """
        api = isi_sdk.SnapshotChangelistsApi(self.cluster.api_client)
        try:
            kwargs = {}
            if resume:
                kwargs["resume"] = resume
            else:
                kwargs["limit"] = limit
            result = api.get_changelist_entries(changelist_id, **kwargs)
            entries = result.entries if hasattr(result, "entries") and result.entries else []
            return {
                "items": [e.to_dict() for e in entries],
                "resume": getattr(result, "resume", None),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_entry(self, changelist_id: str, entry_id: str):
        """Get a specific entry from a snapshot changelist.

        Arguments:
        - changelist_id: The changelist identifier
        - entry_id: The entry ID within the changelist
        """
        api = isi_sdk.SnapshotChangelistsApi(self.cluster.api_client)
        try:
            result = api.get_changelist_entry(changelist_id, entry_id)
            entries = result.entries if hasattr(result, "entries") and result.entries else []
            if entries:
                return entries[0].to_dict()
            return {"error": f"Entry '{entry_id}' not found in changelist '{changelist_id}'"}
        except ApiException as e:
            return {"error": str(e)}

    def get_lins(self, changelist_id: str, resume: str = None, limit: int = 100):
        """List LIN (Logical Inode Number) entries for a snapshot changelist.

        Arguments:
        - changelist_id: The changelist identifier
        - resume: Pagination token from a previous call
        - limit: Maximum number of results (default 100)
        """
        api = isi_sdk.SnapshotChangelistsApi(self.cluster.api_client)
        try:
            kwargs = {}
            if resume:
                kwargs["resume"] = resume
            else:
                kwargs["limit"] = limit
            result = api.get_changelist_lins(changelist_id, **kwargs)
            lins = result.lins if hasattr(result, "lins") and result.lins else []
            return {
                "items": [ln.to_dict() for ln in lins],
                "resume": getattr(result, "resume", None),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_lin(self, changelist_id: str, lin_id: str):
        """Get a specific LIN entry from a snapshot changelist.

        Arguments:
        - changelist_id: The changelist identifier
        - lin_id: The LIN (Logical Inode Number)
        """
        api = isi_sdk.SnapshotChangelistsApi(self.cluster.api_client)
        try:
            result = api.get_changelist_lin(changelist_id, lin_id)
            lins = result.lins if hasattr(result, "lins") and result.lins else []
            if lins:
                return lins[0].to_dict()
            return {"error": f"LIN '{lin_id}' not found in changelist '{changelist_id}'"}
        except ApiException as e:
            return {"error": str(e)}
