import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class FSA:
    """Provides access to PowerScale File System Analytics via FsaApi and FsaResultsApi.

    Covers FSA result sets, index tables, settings, and detailed result analysis
    (top dirs/files, histograms, pool usage).
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    # -----------------------------------------------------------------------
    # FsaApi methods
    # -----------------------------------------------------------------------

    def get_results(self):
        """List all available FSA result sets."""
        api = isi_sdk.FsaApi(self.cluster.api_client)
        try:
            result = api.get_fsa_results()
            results = result.results if hasattr(result, "results") and result.results else []
            return {"items": [r.to_dict() for r in results]}
        except ApiException as e:
            return {"error": str(e)}

    def get_result(self, result_id: int):
        """Get details for a specific FSA result set.

        Arguments:
        - result_id: The result set ID
        """
        api = isi_sdk.FsaApi(self.cluster.api_client)
        try:
            result = api.get_fsa_result(result_id)
            results = result.results if hasattr(result, "results") and result.results else []
            if results:
                return results[0].to_dict()
            return {"error": f"FSA result {result_id} not found"}
        except ApiException as e:
            return {"error": str(e)}

    def get_index(self):
        """Get available FSA index table names."""
        api = isi_sdk.FsaApi(self.cluster.api_client)
        try:
            result = api.get_fsa_index()
            return result.to_dict() if result else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_settings(self, scope: str = None):
        """Get FSA configuration settings.

        Arguments:
        - scope: Optional scope filter for settings
        """
        api = isi_sdk.FsaApi(self.cluster.api_client)
        try:
            kwargs = {}
            if scope:
                kwargs["scope"] = scope
            result = api.get_fsa_settings(**kwargs)
            return result.settings.to_dict() if hasattr(result, "settings") and result.settings else {}
        except ApiException as e:
            return {"error": str(e)}

    # -----------------------------------------------------------------------
    # FsaResultsApi methods
    # -----------------------------------------------------------------------

    def get_top_dirs(self, result_id: int):
        """Get top directories for an FSA result set.

        Arguments:
        - result_id: The result set ID
        """
        api = isi_sdk.FsaResultsApi(self.cluster.api_client)
        try:
            result = api.get_result_top_dirs(result_id)
            dirs = result.top_dirs if hasattr(result, "top_dirs") and result.top_dirs else []
            return {"items": [d.to_dict() for d in dirs]}
        except ApiException as e:
            return {"error": str(e)}

    def get_top_dir(self, result_id: int, top_dir_id: int):
        """Get a specific top directory entry from an FSA result set.

        Arguments:
        - result_id: The result set ID
        - top_dir_id: The top directory entry ID
        """
        api = isi_sdk.FsaResultsApi(self.cluster.api_client)
        try:
            result = api.get_result_top_dir(result_id, top_dir_id)
            dirs = result.top_dirs if hasattr(result, "top_dirs") and result.top_dirs else []
            if dirs:
                return dirs[0].to_dict()
            return {"error": f"Top dir {top_dir_id} not found in result {result_id}"}
        except ApiException as e:
            return {"error": str(e)}

    def get_top_files(self, result_id: int):
        """Get top files for an FSA result set.

        Arguments:
        - result_id: The result set ID
        """
        api = isi_sdk.FsaResultsApi(self.cluster.api_client)
        try:
            result = api.get_result_top_files(result_id)
            files = result.top_files if hasattr(result, "top_files") and result.top_files else []
            return {"items": [f.to_dict() for f in files]}
        except ApiException as e:
            return {"error": str(e)}

    def get_top_file(self, result_id: int, top_file_id: int):
        """Get a specific top file entry from an FSA result set.

        Arguments:
        - result_id: The result set ID
        - top_file_id: The top file entry ID
        """
        api = isi_sdk.FsaResultsApi(self.cluster.api_client)
        try:
            result = api.get_result_top_file(result_id, top_file_id)
            files = result.top_files if hasattr(result, "top_files") and result.top_files else []
            if files:
                return files[0].to_dict()
            return {"error": f"Top file {top_file_id} not found in result {result_id}"}
        except ApiException as e:
            return {"error": str(e)}

    def get_histogram(self, result_id: int):
        """Get histogram of file counts for an FSA result set.

        Arguments:
        - result_id: The result set ID
        """
        api = isi_sdk.FsaResultsApi(self.cluster.api_client)
        try:
            result = api.get_result_histogram(result_id)
            return result.to_dict() if result else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_histogram_stat(self, result_id: int, stat: str):
        """Get histogram filtered by a specific statistic.

        Arguments:
        - result_id: The result set ID
        - stat: The statistic name to filter by
        """
        api = isi_sdk.FsaResultsApi(self.cluster.api_client)
        try:
            result = api.get_result_histogram_stat(result_id, stat)
            return result.to_dict() if result else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_directories(self, result_id: int):
        """Get directory information for an FSA result set.

        Arguments:
        - result_id: The result set ID
        """
        api = isi_sdk.FsaResultsApi(self.cluster.api_client)
        try:
            result = api.get_result_directories(result_id)
            dirs = result.directories if hasattr(result, "directories") and result.directories else []
            return {
                "items": [d.to_dict() for d in dirs],
                "resume": getattr(result, "resume", None),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_directory(self, result_id: int, directory_id: int):
        """Get specific directory information from an FSA result set.

        Arguments:
        - result_id: The result set ID
        - directory_id: The directory entry ID
        """
        api = isi_sdk.FsaResultsApi(self.cluster.api_client)
        try:
            result = api.get_result_directory(result_id, directory_id)
            dirs = result.directories if hasattr(result, "directories") and result.directories else []
            if dirs:
                return dirs[0].to_dict()
            return {"error": f"Directory {directory_id} not found in result {result_id}"}
        except ApiException as e:
            return {"error": str(e)}
