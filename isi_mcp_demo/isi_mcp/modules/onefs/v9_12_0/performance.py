import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class Performance:
    """Provides access to PowerScale performance datasets and metrics via the PerformanceApi.

    Covers performance datasets, metrics catalog, and performance settings.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def list_datasets(self):
        """List all performance datasets."""
        api = isi_sdk.PerformanceApi(self.cluster.api_client)
        try:
            result = api.list_performance_datasets()
            datasets = result.datasets if hasattr(result, "datasets") and result.datasets else []
            return {
                "items": [d.to_dict() for d in datasets],
                "resume": getattr(result, "resume", None),
                "total": getattr(result, "total", len(datasets)),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_dataset(self, dataset_id: int):
        """Get details for a specific performance dataset.

        Arguments:
        - dataset_id: The dataset ID
        """
        api = isi_sdk.PerformanceApi(self.cluster.api_client)
        try:
            result = api.get_performance_dataset(dataset_id)
            datasets = result.datasets if hasattr(result, "datasets") and result.datasets else []
            if datasets:
                return datasets[0].to_dict()
            return {"error": f"Dataset {dataset_id} not found"}
        except ApiException as e:
            return {"error": str(e)}

    def get_metrics(self):
        """List all available performance metrics."""
        api = isi_sdk.PerformanceApi(self.cluster.api_client)
        try:
            result = api.get_performance_metrics()
            metrics = result.metrics if hasattr(result, "metrics") and result.metrics else []
            return {"items": [m.to_dict() for m in metrics]}
        except ApiException as e:
            return {"error": str(e)}

    def get_metric(self, metric_id: str):
        """Get details for a specific performance metric.

        Arguments:
        - metric_id: The metric name/ID
        """
        api = isi_sdk.PerformanceApi(self.cluster.api_client)
        try:
            result = api.get_performance_metric(metric_id)
            metrics = result.metrics if hasattr(result, "metrics") and result.metrics else []
            if metrics:
                return metrics[0].to_dict()
            return {"error": f"Metric '{metric_id}' not found"}
        except ApiException as e:
            return {"error": str(e)}

    def get_settings(self):
        """Get performance monitoring settings."""
        api = isi_sdk.PerformanceApi(self.cluster.api_client)
        try:
            result = api.get_performance_settings()
            return result.settings.to_dict() if hasattr(result, "settings") and result.settings else {}
        except ApiException as e:
            return {"error": str(e)}

    def list_dataset_filters(self, dataset_id: int):
        """List all filters for a specific performance dataset.

        Arguments:
        - dataset_id: The dataset ID
        """
        api = isi_sdk.PerformanceDatasetsApi(self.cluster.api_client)
        try:
            result = api.list_dataset_filters(dataset_id)
            filters = result.filters if hasattr(result, "filters") and result.filters else []
            return {"items": [f.to_dict() for f in filters]}
        except ApiException as e:
            return {"error": str(e)}

    def get_dataset_filter(self, dataset_id: int, filter_id: int):
        """Get a specific filter for a performance dataset.

        Arguments:
        - dataset_id: The dataset ID
        - filter_id: The filter ID
        """
        api = isi_sdk.PerformanceDatasetsApi(self.cluster.api_client)
        try:
            result = api.get_dataset_filter(dataset_id, filter_id)
            filters = result.filters if hasattr(result, "filters") and result.filters else []
            if filters:
                return filters[0].to_dict()
            return {"error": f"Filter {filter_id} not found in dataset {dataset_id}"}
        except ApiException as e:
            return {"error": str(e)}

    def list_dataset_workloads(self, dataset_id: int):
        """List all workloads for a specific performance dataset.

        Arguments:
        - dataset_id: The dataset ID
        """
        api = isi_sdk.PerformanceDatasetsApi(self.cluster.api_client)
        try:
            result = api.list_dataset_workloads(dataset_id)
            workloads = result.workloads if hasattr(result, "workloads") and result.workloads else []
            return {"items": [w.to_dict() for w in workloads]}
        except ApiException as e:
            return {"error": str(e)}

    def get_dataset_workload(self, dataset_id: int, workload_id: int):
        """Get a specific workload for a performance dataset.

        Arguments:
        - dataset_id: The dataset ID
        - workload_id: The workload ID
        """
        api = isi_sdk.PerformanceDatasetsApi(self.cluster.api_client)
        try:
            result = api.get_dataset_workload(dataset_id, workload_id)
            workloads = result.workloads if hasattr(result, "workloads") and result.workloads else []
            if workloads:
                return workloads[0].to_dict()
            return {"error": f"Workload {workload_id} not found in dataset {dataset_id}"}
        except ApiException as e:
            return {"error": str(e)}
