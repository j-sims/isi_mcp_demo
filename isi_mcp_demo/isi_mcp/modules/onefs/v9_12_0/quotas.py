import re
import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.models.quota_quota import QuotaQuota
from modules.ansible.runner import AnsibleRunner
from modules.utils.kwargs import drop_none
from modules.utils.paging import page_kwargs
from isilon_sdk.v9_12_0.models.quota_quotas_extended import QuotaQuotasExtended
from isilon_sdk.v9_12_0.models.quota_quota_thresholds import QuotaQuotaThresholds

# dellemc.powerscale.smartquota only accepts cap_unit of 'GB' or 'TB'.
# Internally "GB" means GiB (base-1024) and "TB" means TiB.
# Smaller units are converted to their GB equivalent.
_UNIT_TO_GB = {
    'KB': 1 / (1024 * 1024), 'KIB': 1 / (1024 * 1024),
    'MB': 1 / 1024,          'MIB': 1 / 1024,
    'GB': 1,                  'GIB': 1,
    'TB': 1024,               'TIB': 1024,
}

def _parse_size(size_str: str) -> tuple:
    """Parse a human-readable size string into (number, cap_unit) for Ansible.

    The module only accepts 'GB' or 'TB' as cap_unit.  Smaller units are
    converted to a GB value.  Example: '10GiB' -> (10.0, 'GB')
    """
    m = re.match(r'^([\d.]+)\s*([A-Za-z]+)$', size_str.strip())
    if not m:
        raise ValueError(f"Cannot parse size: {size_str}")
    number, unit = float(m.group(1)), m.group(2).upper()
    factor = _UNIT_TO_GB.get(unit)
    if factor is None:
        raise ValueError(f"Unknown unit: {unit}. Use KB, MB, GB, or TB (IEC variants accepted).")
    gb_value = number * factor
    if gb_value >= 1024:
        return gb_value / 1024, 'TB'
    return gb_value, 'GB'

class Quotas:
    """holds all functions related to Quotas shares on a powerscale cluster."""
    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    def get(self, qpath=None, limit=1000, resume=None):
        quota_api = isi_sdk.QuotaApi(self.cluster.api_client)
        quotas = quota_api.list_quota_quotas(**page_kwargs(limit, resume, path=qpath))

        items = [q.to_dict() for q in quotas.quotas] if quotas.quotas else []

        return {
            "items": items,
            "resume": quotas.resume
        }
        
    def _update_hard_quota(self, path, new_limit_fn):
        """Look up the single quota at `path` and update its hard limit.

        new_limit_fn receives the current hard limit and returns the new one
        (or a string starting with 'Error:' to abort with that message).
        """
        quota_api = isi_sdk.QuotaApi(self.cluster.api_client)
        quotas = quota_api.list_quota_quotas(path=path).quotas
        if not quotas:
            return f"Error: No quota found on {path}"
        if len(quotas) > 1:
            return f"Error: More than one quota on {path}"

        quota = quotas[0]
        new_limit = new_limit_fn(quota.thresholds.hard)
        if isinstance(new_limit, str) and new_limit.startswith("Error:"):
            return new_limit

        quota_api.update_quota_quota(
            QuotaQuota(thresholds=QuotaQuotaThresholds(hard=new_limit)),
            quota.id,
        )
        return new_limit

    def increment_hard_quota(self, PATH, INCREMENT):
        result = self._update_hard_quota(PATH, lambda current: current + INCREMENT)
        if isinstance(result, str):
            return result
        return f"Quota on {PATH} increased by {INCREMENT}"

    def decrement_hard_quota(self, PATH, INCREMENT):
        def new_limit(current):
            value = current - INCREMENT
            return value if value > 0 else "Error: Quota must be greater than zero"
        result = self._update_hard_quota(PATH, new_limit)
        if isinstance(result, str):
            return result
        return f"Quota on {PATH} decreased by {INCREMENT}"

    def set_hard_quota(self, PATH, SIZE):
        result = self._update_hard_quota(PATH, lambda _current: SIZE)
        if isinstance(result, str):
            return result
        return f"Quota on {PATH} set to {SIZE}"

    def add_quota(self, path: str, quota_type: str, limit_size: str,
                  soft_grace_period: str = None, soft_grace_period_unit: str = "days",
                  include_overheads: bool = False, persona: str = None) -> dict:
        """Create a quota (hard, soft, or advisory) via Ansible.

        Args:
            quota_type: Threshold type — 'hard', 'soft', or 'advisory'
            soft_grace_period: Grace period value for soft quotas
            soft_grace_period_unit: Unit for grace period ('hours', 'days', 'weeks', 'months')
            persona: If set, creates a user quota; otherwise a directory quota
        """
        runner = AnsibleRunner(self.cluster)

        # Ansible's quota_type is the scope (directory/user/group),
        # threshold_type is the enforcement level (hard/soft/advisory)
        ansible_quota_type = "user" if persona else "directory"

        size_value, cap_unit = _parse_size(limit_size)

        variables = {
            "path": path,
            "quota_type": ansible_quota_type,
            "threshold_type": quota_type,
            "cap_unit": cap_unit,
            "include_overheads": str(include_overheads).lower(),
        }

        # Map size to the correct template variable based on threshold type
        if quota_type == "hard":
            variables["hard_limit_size"] = size_value
        elif quota_type == "soft":
            variables["soft_limit_size"] = size_value
            variables["soft_grace_period"] = soft_grace_period or "7"
            variables["soft_grace_period_unit"] = soft_grace_period_unit
        elif quota_type == "advisory":
            variables["advisory_limit_size"] = size_value
        else:
            return {"success": False, "status": "failed",
                    "error": f"Invalid quota_type: {quota_type}. Must be 'hard', 'soft', or 'advisory'."}

        variables.update(drop_none(user_name=persona))
        return runner.execute("quota_create.yml.j2", variables)

    def remove_quota(self, path: str, quota_type: str, persona: str = None) -> dict:
        """Remove a quota via Ansible.

        Args:
            quota_type: Threshold type — 'hard', 'soft', or 'advisory'
            persona: If set, removes a user quota; otherwise a directory quota
        """
        runner = AnsibleRunner(self.cluster)
        ansible_quota_type = "user" if persona else "directory"
        variables = {
            "path": path,
            "quota_type": ansible_quota_type,
            "threshold_type": quota_type,
        }
        return runner.execute("quota_remove.yml.j2", variables)