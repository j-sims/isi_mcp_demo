import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.rest import ApiException
from modules.ansible.runner import AnsibleRunner

class S3:
    """holds all functions related to S3 buckets on a powerscale cluster."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self, limit=1000, resume=None):
        protocols_api = isi_sdk.ProtocolsApi(self.cluster.api_client)
        kwargs = {"limit": limit}
        if resume:
            kwargs["resume"] = resume
        result = protocols_api.list_s3_buckets(**kwargs)

        items = [b.to_dict() for b in result.buckets] if result.buckets else []

        return {
            "items": items,
            "resume": result.resume
        }

    def add(self, s3_bucket_name: str, path: str, owner: str = "root",
            description: str = None, create_path: bool = None) -> dict:
        """Create an S3 bucket via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {
            "s3_bucket_name": s3_bucket_name,
            "path": path,
            "owner": owner,
        }
        if description:
            variables["description"] = description
        if create_path is not None:
            variables["create_path"] = str(create_path).lower()
        return runner.execute("s3_create.yml.j2", variables)

    def remove(self, s3_bucket_name: str) -> dict:
        """Remove an S3 bucket via Ansible."""
        runner = AnsibleRunner(self.cluster)
        variables = {
            "s3_bucket_name": s3_bucket_name,
        }
        return runner.execute("s3_remove.yml.j2", variables)
