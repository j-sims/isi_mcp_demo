import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException


class Jobs:
    """Provides access to the PowerScale Job Engine via the JobApi.

    Covers running/paused jobs, recently completed jobs, job types,
    impact policies, job events, reports, statistics, and settings.
    """

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def list_jobs(self):
        """List running and paused jobs."""
        api = isi_sdk.JobApi(self.cluster.api_client)
        try:
            result = api.list_job_jobs()
            jobs = result.jobs if hasattr(result, "jobs") and result.jobs else []
            return {
                "items": [j.to_dict() for j in jobs],
                "resume": getattr(result, "resume", None),
                "total": getattr(result, "total", len(jobs)),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_job(self, job_id: int):
        """Get details for a specific running or paused job.

        Arguments:
        - job_id: The job instance ID
        """
        api = isi_sdk.JobApi(self.cluster.api_client)
        try:
            result = api.get_job_job(job_id)
            jobs = result.jobs if hasattr(result, "jobs") and result.jobs else []
            if jobs:
                return jobs[0].to_dict()
            return {"error": f"Job {job_id} not found"}
        except ApiException as e:
            return {"error": str(e)}

    def get_recent(self, limit: int = 50):
        """List recently completed jobs.

        Arguments:
        - limit: Maximum number of recent jobs to return (default 50)
        """
        api = isi_sdk.JobApi(self.cluster.api_client)
        try:
            result = api.get_job_recent()
            jobs = result.jobs if hasattr(result, "jobs") and result.jobs else []
            items = [j.to_dict() for j in jobs]
            return {"items": items[:limit], "total": len(items)}
        except ApiException as e:
            return {"error": str(e)}

    def get_summary(self):
        """Get job engine status summary."""
        api = isi_sdk.JobApi(self.cluster.api_client)
        try:
            result = api.get_job_job_summary()
            return result.summary.to_dict() if hasattr(result, "summary") and result.summary else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_types(self):
        """List all available job types."""
        api = isi_sdk.JobApi(self.cluster.api_client)
        try:
            result = api.get_job_types()
            types = result.types if hasattr(result, "types") and result.types else []
            return {"items": [t.to_dict() for t in types]}
        except ApiException as e:
            return {"error": str(e)}

    def get_type(self, job_type_id: str):
        """Get details for a specific job type.

        Arguments:
        - job_type_id: The job type name (e.g. 'TreeDelete', 'SmartPools', 'Collect')
        """
        api = isi_sdk.JobApi(self.cluster.api_client)
        try:
            result = api.get_job_type(job_type_id)
            types = result.types if hasattr(result, "types") and result.types else []
            if types:
                return types[0].to_dict()
            return {"error": f"Job type '{job_type_id}' not found"}
        except ApiException as e:
            return {"error": str(e)}

    def get_events(self, resume: str = None, limit: int = 100, job_id: int = None,
                   job_type: str = None):
        """Retrieve job events with optional filtering.

        Arguments:
        - resume: Pagination token from a previous call
        - limit: Maximum number of results (default 100)
        - job_id: Filter events by job instance ID
        - job_type: Filter events by job type name
        """
        api = isi_sdk.JobApi(self.cluster.api_client)
        try:
            kwargs = {}
            if resume:
                kwargs["resume"] = resume
            else:
                kwargs["limit"] = limit
                if job_id is not None:
                    kwargs["job_id"] = job_id
                if job_type is not None:
                    kwargs["job_type"] = job_type
            result = api.get_job_events(**kwargs)
            events = result.events if hasattr(result, "events") and result.events else []
            return {
                "items": [e.to_dict() for e in events],
                "resume": getattr(result, "resume", None),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_reports(self, resume: str = None, limit: int = 100, job_id: int = None,
                    job_type: str = None):
        """List job reports with optional filtering.

        Arguments:
        - resume: Pagination token from a previous call
        - limit: Maximum number of results (default 100)
        - job_id: Filter reports by job instance ID
        - job_type: Filter reports by job type name
        """
        api = isi_sdk.JobApi(self.cluster.api_client)
        try:
            kwargs = {}
            if resume:
                kwargs["resume"] = resume
            else:
                kwargs["limit"] = limit
                if job_id is not None:
                    kwargs["job_id"] = job_id
                if job_type is not None:
                    kwargs["job_type"] = job_type
            result = api.get_job_reports(**kwargs)
            reports = result.reports if hasattr(result, "reports") and result.reports else []
            return {
                "items": [r.to_dict() for r in reports],
                "resume": getattr(result, "resume", None),
            }
        except ApiException as e:
            return {"error": str(e)}

    def get_statistics(self):
        """Get job engine statistics."""
        api = isi_sdk.JobApi(self.cluster.api_client)
        try:
            result = api.get_job_statistics()
            return result.statistics.to_dict() if hasattr(result, "statistics") and result.statistics else {}
        except ApiException as e:
            return {"error": str(e)}

    def get_policies(self):
        """List all job impact policies."""
        api = isi_sdk.JobApi(self.cluster.api_client)
        try:
            result = api.list_job_policies()
            policies = result.policies if hasattr(result, "policies") and result.policies else []
            return {"items": [p.to_dict() for p in policies]}
        except ApiException as e:
            return {"error": str(e)}

    def get_policy(self, policy_id: str):
        """Get details for a specific job impact policy.

        Arguments:
        - policy_id: The impact policy name (e.g. 'LOW', 'MEDIUM', 'HIGH', 'OFF_HOURS')
        """
        api = isi_sdk.JobApi(self.cluster.api_client)
        try:
            result = api.get_job_policy(policy_id)
            policies = result.policies if hasattr(result, "policies") and result.policies else []
            if policies:
                return policies[0].to_dict()
            return {"error": f"Job policy '{policy_id}' not found"}
        except ApiException as e:
            return {"error": str(e)}

    def get_settings(self):
        """Get Job Engine generic settings."""
        api = isi_sdk.JobApi(self.cluster.api_client)
        try:
            result = api.get_job_settings()
            return result.settings.to_dict() if hasattr(result, "settings") and result.settings else {}
        except ApiException as e:
            return {"error": str(e)}
