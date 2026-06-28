import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException

from modules.utils.errors import safe_api_error
from modules.utils.paging import page_kwargs

_ID_HINT = (
    "Changelist ids are of the form '<begin_snapshot_id>_<end_snapshot_id>' "
    "and are produced by running a ChangelistCreate job between two snapshots; "
    "'1' is not a valid changelist id."
)


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
        try:
            api = isi_sdk.SnapshotChangelistsApi(self.cluster.api_client)
            result = api.get_changelist_entries(changelist_id, **page_kwargs(limit, resume))
        except ApiException as e:
            if getattr(e, "status", None) == 400:
                return {"error": f"{safe_api_error(e)} — {_ID_HINT}", "status": 400}
            raise
        entries = result.entries if hasattr(result, "entries") and result.entries else []
        return {
            "items": [e.to_dict() for e in entries],
            "resume": getattr(result, "resume", None),
        }

    def get_entry(self, changelist_id: str, entry_id: str):
        """Get a specific entry from a snapshot changelist.

        Arguments:
        - changelist_id: The changelist identifier
        - entry_id: The entry ID within the changelist
        """
        api = isi_sdk.SnapshotChangelistsApi(self.cluster.api_client)
        result = api.get_changelist_entry(changelist_id, entry_id)
        entries = result.entries if hasattr(result, "entries") and result.entries else []
        if entries:
            return entries[0].to_dict()
        return {"error": f"Entry '{entry_id}' not found in changelist '{changelist_id}'"}

    def get_lins(self, changelist_id: str, resume: str = None, limit: int = 100):
        """List LIN (Logical Inode Number) entries for a snapshot changelist.

        Arguments:
        - changelist_id: The changelist identifier
        - resume: Pagination token from a previous call
        - limit: Maximum number of results (default 100)
        """
        api = isi_sdk.SnapshotChangelistsApi(self.cluster.api_client)
        result = api.get_changelist_lins(changelist_id, **page_kwargs(limit, resume))
        lins = result.lins if hasattr(result, "lins") and result.lins else []
        return {
            "items": [ln.to_dict() for ln in lins],
            "resume": getattr(result, "resume", None),
        }

    def get_lin(self, changelist_id: str, lin_id: str):
        """Get a specific LIN entry from a snapshot changelist.

        Arguments:
        - changelist_id: The changelist identifier
        - lin_id: The LIN (Logical Inode Number)
        """
        api = isi_sdk.SnapshotChangelistsApi(self.cluster.api_client)
        result = api.get_changelist_lin(changelist_id, lin_id)
        lins = result.lins if hasattr(result, "lins") and result.lins else []
        if lins:
            return lins[0].to_dict()
        return {"error": f"LIN '{lin_id}' not found in changelist '{changelist_id}'"}
