# Task Grouping Plan — PowerScale MCP Server

## Problem Statement

When an LLM is asked to perform bulk operations it calls single-item MCP tools in a loop:

| User request | Current behavior | Desired behavior |
|---|---|---|
| "Create 100 SMB shares" | 100 tool calls → 100 playbooks | 1 tool call → 1 playbook |
| "Create 10 shares each with a quota and snapshot schedule" | 30 tool calls → 30 playbooks | 1 tool call → 1 playbook |
| "Create 5 NFS exports and 5 S3 buckets" | 10 tool calls → 10 playbooks | 1 tool call → 1 playbook |

The root cause is that every existing MCP tool operates on a single resource. There is no mechanism for the LLM to express "do all of these at once."

---

## Design: Two Tiers

### Tier 1 — Type-Specific Batch Tools

For homogeneous bulk operations (many resources of the same type). Simple, predictable, and useful when the task involves only one resource type.

Each tool accepts a **JSON array** of resource configs and produces **one Ansible playbook** using `loop:`.

### Tier 2 — Universal Batch Executor

For heterogeneous operations across any combination of resource types in a single call. No predefined workflow assumptions — the LLM constructs a JSON object with only the resource types it needs.

Produces **one Ansible playbook** with conditional task blocks per resource type. Any combination of SMB shares, NFS exports, S3 buckets, quotas, snapshot schedules, and SyncIQ policies can be mixed freely.

---

## Tier 1: Type-Specific Batch Tools

### New MCP Tools (10 tools, all `mode: write`, `enabled: false` by default)

#### SMB Shares
```
powerscale_smb_create_batch(shares: str) -> dict
powerscale_smb_remove_batch(share_names: str) -> dict
```

`shares` — JSON array of share config objects. Each object:
- Required: `share_name` (str), `path` (str)
- Optional: `description`, `access_zone`, `create_path` (bool), `browsable` (bool), `ntfs_acl_support` (bool), `oplocks` (bool), `smb3_encryption_enabled` (bool), `permissions` (list of permission dicts), `host_acls` (list), `run_as_root` (list), `file_filter_extension` (dict), and all other params accepted by `powerscale_smb_create`

`share_names` — JSON array of share name strings

#### NFS Exports
```
powerscale_nfs_create_batch(exports: str) -> dict
powerscale_nfs_remove_batch(exports: str) -> dict
```

`exports` — JSON array of export config objects. Each object:
- Required: `path` (str)
- Optional: `access_zone`, `description`, `clients` (list), `read_only` (bool), `client_state`, `read_only_clients` (list), `read_write_clients` (list), `root_clients` (list), `security_flavors` (list), `sub_directories_mountable` (bool), `map_root` (dict), `map_non_root` (dict), `ignore_unresolvable_hosts` (bool)

Remove: each object needs `path` and optionally `access_zone`.

#### S3 Buckets
```
powerscale_s3_create_batch(buckets: str) -> dict
powerscale_s3_remove_batch(bucket_names: str) -> dict
```

`buckets` — JSON array of bucket config objects (same fields as `powerscale_s3_create`)
`bucket_names` — JSON array of bucket name strings

#### Quotas
```
powerscale_quota_create_batch(quotas: str) -> dict
powerscale_quota_remove_batch(quotas: str) -> dict
```

`quotas` — JSON array of quota config objects. Each object:
- Required: `path` (str), `quota_type` (`"hard"` | `"soft"` | `"advisory"`), `limit_size` (human-readable string, e.g. `"500GiB"`)
- Optional: `soft_grace_period` (int), `soft_grace_period_unit` (str), `include_overheads` (bool), `persona` (str, for user quotas)

Remove: each object needs `path` and `quota_type`, optionally `persona`.

#### Snapshot Schedules
```
powerscale_snapshot_schedule_create_batch(schedules: str) -> dict
powerscale_snapshot_schedule_remove_batch(schedule_names: str) -> dict
```

`schedules` — JSON array of schedule config objects. Each object:
- Required: `name` (str), `path` (str), `schedule` (isidate format str)
- Optional: `pattern` (str), `desired_retention` (int), `retention_unit` (str), `alias` (str)

`schedule_names` — JSON array of schedule name strings

### Ansible Templates (Tier 1)

Ten new templates in `isi_mcp/Templates/` following the Ansible `loop:` pattern:

```yaml
# Example: smb_create_batch.yml.j2
---
- name: Create SMB shares (batch) on PowerScale
  hosts: localhost
  connection: local
  gather_facts: false
  collections:
    - dellemc.powerscale

  tasks:
    - name: Create SMB share "{{ item.share_name }}"
      dellemc.powerscale.smb:
        onefs_host: "{{ onefs_host }}"
        port_no: "{{ port_no }}"
        verify_ssl: {{ verify_ssl }}
        api_user: "{{ api_user }}"
        api_password: "{{ api_password }}"
        share_name: "{{ item.share_name }}"
        path: "{{ item.path }}"
        description: "{{ item.description | default(omit) }}"
        access_zone: "{{ item.access_zone | default(omit) }}"
        create_path: "{{ item.create_path | default(omit) }}"
        browsable: "{{ item.browsable | default(omit) }}"
        ntfs_acl_support: "{{ item.ntfs_acl_support | default(omit) }}"
        oplocks: "{{ item.oplocks | default(omit) }}"
        smb3_encryption_enabled: "{{ item.smb3_encryption_enabled | default(omit) }}"
        permissions: "{{ item.permissions | default(omit) }}"
        host_acls: "{{ item.host_acls | default(omit) }}"
        run_as_root: "{{ item.run_as_root | default(omit) }}"
        file_filter_extension: "{{ item.file_filter_extension | default(omit) }}"
        file_filtering_enabled: "{{ item.file_filtering_enabled | default(omit) }}"
        state: present
      loop: "{{ shares }}"
      loop_control:
        label: "{{ item.share_name }}"
```

All 10 templates follow the same pattern. The quota template uses all three limit size keys with `| default(omit)` so each item only populates the relevant one.

Key: `| default(omit)` removes the parameter from the Ansible module call entirely when the key is absent from the item dict — no need for `{% if %}` blocks per field.

### Domain Module Methods (Tier 1)

Each existing domain module gets `add_batch()` and `remove_batch()` methods:

```python
# Example: smb.py
def add_batch(self, shares: list) -> dict:
    runner = AnsibleRunner(self.cluster)
    processed = []
    for share in shares:
        item = dict(share)
        # Pre-parse JSON string fields to native objects (mirrors add() logic)
        for field in ("permissions", "host_acls", "run_as_root", "file_filter_extension"):
            if field in item and isinstance(item[field], str):
                item[field] = json.loads(item[field])
        processed.append(item)
    return runner.execute("smb_create_batch.yml.j2", {"shares": processed})

def remove_batch(self, share_names: list) -> dict:
    runner = AnsibleRunner(self.cluster)
    shares = [{"share_name": name} for name in share_names]
    return runner.execute("smb_remove_batch.yml.j2", {"shares": shares})
```

The same pattern applies to `Quotas`, `SnapshotSchedules`, `Nfs`, and `S3`. The quota `add_quota_batch()` calls `_parse_size()` for each config and populates only the relevant limit key.

---

## Tier 2: Universal Batch Executor

### New MCP Tools (2 tools, `mode: write`, `enabled: false` by default, group: `batch`)

#### `powerscale_batch_create(operations: str) -> dict`

Accepts a single JSON object whose keys are resource types and values are arrays of resource configs. Any subset of keys may be present. The playbook is generated with only the task blocks needed for the keys provided.

**Input schema:**
```json
{
  "smb_shares": [
    {"share_name": "marketing", "path": "/ifs/shares/marketing", "description": "Marketing team", "create_path": true},
    {"share_name": "finance", "path": "/ifs/shares/finance"}
  ],
  "nfs_exports": [
    {"path": "/ifs/data/linux", "clients": ["10.0.1.0/24"], "read_write_clients": ["10.0.1.10"]}
  ],
  "s3_buckets": [
    {"bucket_name": "archive", "path": "/ifs/s3/archive"}
  ],
  "quotas": [
    {"path": "/ifs/shares/marketing", "quota_type": "hard", "limit_size": "500GiB"},
    {"path": "/ifs/shares/finance", "quota_type": "soft", "limit_size": "1TiB", "soft_grace_period": 7}
  ],
  "snapshot_schedules": [
    {"name": "marketing-daily", "path": "/ifs/shares/marketing", "schedule": "Every day at 2:00 AM", "desired_retention": 30},
    {"name": "finance-daily", "path": "/ifs/shares/finance", "schedule": "Every day at 3:00 AM", "desired_retention": 90}
  ],
  "synciq_policies": [
    {"policy_name": "dr-marketing", "source_path": "/ifs/shares/marketing", "target_host": "192.168.10.5", "target_path": "/ifs/dr/marketing"}
  ]
}
```

Any combination of keys is valid. Omitting a key means that resource type is not touched.

**Scenarios and playbook counts:**

| Operations dict | Playbooks generated |
|---|---|
| `{"smb_shares": [100 items]}` | 1 |
| `{"smb_shares": [10], "quotas": [10], "snapshot_schedules": [10]}` | 1 |
| `{"nfs_exports": [5], "s3_buckets": [5], "quotas": [10]}` | 1 |
| `{"smb_shares": [50], "nfs_exports": [50], "synciq_policies": [50]}` | 1 |

#### `powerscale_batch_remove(operations: str) -> dict`

Same structure as `powerscale_batch_create` but for removals. Only the minimum fields needed to identify each resource are required per type:

```json
{
  "smb_shares":         [{"share_name": "marketing"}, {"share_name": "finance"}],
  "nfs_exports":        [{"path": "/ifs/data/linux"}],
  "s3_buckets":         [{"bucket_name": "archive"}],
  "quotas":             [{"path": "/ifs/shares/marketing", "quota_type": "hard"}],
  "snapshot_schedules": [{"name": "marketing-daily"}, {"name": "finance-daily"}],
  "synciq_policies":    [{"policy_name": "dr-marketing"}]
}
```

### Ansible Templates (Tier 2)

Two new templates: `batch_create.yml.j2` and `batch_remove.yml.j2`.

The create template uses `{% if X is defined %}...{% endif %}` blocks with Ansible `loop:` inside each:

```yaml
# batch_create.yml.j2
---
- name: Batch create resources on PowerScale
  hosts: localhost
  connection: local
  gather_facts: false
  collections:
    - dellemc.powerscale

  tasks:
{% if smb_shares is defined %}
    - name: Create SMB share "{{ item.share_name }}"
      dellemc.powerscale.smb:
        onefs_host: "{{ onefs_host }}"
        port_no: "{{ port_no }}"
        verify_ssl: {{ verify_ssl }}
        api_user: "{{ api_user }}"
        api_password: "{{ api_password }}"
        share_name: "{{ item.share_name }}"
        path: "{{ item.path }}"
        description: "{{ item.description | default(omit) }}"
        access_zone: "{{ item.access_zone | default(omit) }}"
        create_path: "{{ item.create_path | default(omit) }}"
        browsable: "{{ item.browsable | default(omit) }}"
        permissions: "{{ item.permissions | default(omit) }}"
        host_acls: "{{ item.host_acls | default(omit) }}"
        run_as_root: "{{ item.run_as_root | default(omit) }}"
        file_filter_extension: "{{ item.file_filter_extension | default(omit) }}"
        file_filtering_enabled: "{{ item.file_filtering_enabled | default(omit) }}"
        state: present
      loop: "{{ smb_shares }}"
      loop_control:
        label: "{{ item.share_name }}"
{% endif %}

{% if nfs_exports is defined %}
    - name: Create NFS export for "{{ item.path }}"
      dellemc.powerscale.nfs:
        onefs_host: "{{ onefs_host }}"
        port_no: "{{ port_no }}"
        verify_ssl: {{ verify_ssl }}
        api_user: "{{ api_user }}"
        api_password: "{{ api_password }}"
        path: "{{ item.path }}"
        access_zone: "{{ item.access_zone | default('System') }}"
        description: "{{ item.description | default(omit) }}"
        clients: "{{ item.clients | default(omit) }}"
        read_only: "{{ item.read_only | default(omit) }}"
        client_state: "{{ item.client_state | default(omit) }}"
        read_only_clients: "{{ item.read_only_clients | default(omit) }}"
        read_write_clients: "{{ item.read_write_clients | default(omit) }}"
        root_clients: "{{ item.root_clients | default(omit) }}"
        security_flavors: "{{ item.security_flavors | default(omit) }}"
        sub_directories_mountable: "{{ item.sub_directories_mountable | default(omit) }}"
        map_root: "{{ item.map_root | default(omit) }}"
        map_non_root: "{{ item.map_non_root | default(omit) }}"
        ignore_unresolvable_hosts: "{{ item.ignore_unresolvable_hosts | default(omit) }}"
        state: present
      loop: "{{ nfs_exports }}"
      loop_control:
        label: "{{ item.path }}"
{% endif %}

{% if s3_buckets is defined %}
    - name: Create S3 bucket "{{ item.bucket_name }}"
      dellemc.powerscale.s3_bucket:
        onefs_host: "{{ onefs_host }}"
        port_no: "{{ port_no }}"
        verify_ssl: {{ verify_ssl }}
        api_user: "{{ api_user }}"
        api_password: "{{ api_password }}"
        bucket_name: "{{ item.bucket_name }}"
        path: "{{ item.path }}"
        access_zone: "{{ item.access_zone | default(omit) }}"
        description: "{{ item.description | default(omit) }}"
        object_acl_policy: "{{ item.object_acl_policy | default(omit) }}"
        acl: "{{ item.acl | default(omit) }}"
        state: present
      loop: "{{ s3_buckets }}"
      loop_control:
        label: "{{ item.bucket_name }}"
{% endif %}

{% if quotas is defined %}
    - name: Create quota on "{{ item.path }}"
      dellemc.powerscale.smartquota:
        onefs_host: "{{ onefs_host }}"
        port_no: "{{ port_no }}"
        verify_ssl: {{ verify_ssl }}
        api_user: "{{ api_user }}"
        api_password: "{{ api_password }}"
        path: "{{ item.path }}"
        quota_type: "{{ item.quota_type }}"
        quota:
          include_overheads: "{{ item.include_overheads | default(false) }}"
          cap_unit: "{{ item.cap_unit }}"
          hard_limit_size: "{{ item.hard_limit_size | default(omit) }}"
          soft_limit_size: "{{ item.soft_limit_size | default(omit) }}"
          soft_grace_period: "{{ item.soft_grace_period | default(omit) }}"
          period_unit: "{{ item.soft_grace_period_unit | default(omit) }}"
          advisory_limit_size: "{{ item.advisory_limit_size | default(omit) }}"
        user_name: "{{ item.user_name | default(omit) }}"
        state: present
      loop: "{{ quotas }}"
      loop_control:
        label: "{{ item.path }}"
{% endif %}

{% if snapshot_schedules is defined %}
    - name: Create snapshot schedule "{{ item.name }}"
      dellemc.powerscale.snapshotschedule:
        onefs_host: "{{ onefs_host }}"
        port_no: "{{ port_no }}"
        verify_ssl: {{ verify_ssl }}
        api_user: "{{ api_user }}"
        api_password: "{{ api_password }}"
        name: "{{ item.name }}"
        path: "{{ item.path }}"
        pattern: "{{ item.pattern | default(item.name + '_%Y-%m-%d_%H:%M') }}"
        schedule: "{{ item.schedule }}"
        desired_retention: "{{ item.desired_retention | default(omit) }}"
        retention_unit: "{{ item.retention_unit | default('days') }}"
        alias: "{{ item.alias | default(omit) }}"
        state: present
      loop: "{{ snapshot_schedules }}"
      loop_control:
        label: "{{ item.name }}"
{% endif %}

{% if synciq_policies is defined %}
    - name: Create SyncIQ policy "{{ item.policy_name }}"
      dellemc.powerscale.synciqpolicy:
        onefs_host: "{{ onefs_host }}"
        port_no: "{{ port_no }}"
        verify_ssl: {{ verify_ssl }}
        api_user: "{{ api_user }}"
        api_password: "{{ api_password }}"
        policy_name: "{{ item.policy_name }}"
        action: "{{ item.action | default('sync') }}"
        source_path: "{{ item.source_path }}"
        target_host: "{{ item.target_host }}"
        target_path: "{{ item.target_path }}"
        schedule: "{{ item.schedule | default(omit) }}"
        description: "{{ item.description | default(omit) }}"
        enabled: "{{ item.enabled | default(omit) }}"
        state: present
      loop: "{{ synciq_policies }}"
      loop_control:
        label: "{{ item.policy_name }}"
{% endif %}
```

The remove template follows the same structure with `state: absent` and only the minimum identification fields per resource type.

### New `batch.py` Domain Module

A new file `modules/onefs/v9_12_0/batch.py` handles input validation and variable preparation for the Tier 2 tools. It mirrors the per-type logic that exists in each domain module's `add()` method:

```python
class BatchProvisioner:
    def __init__(self, cluster):
        self.cluster = cluster

    def create(self, operations: dict) -> dict:
        """
        Validate and prepare variables for batch_create.yml.j2.
        operations keys: smb_shares, nfs_exports, s3_buckets, quotas,
                         snapshot_schedules, synciq_policies
        """
        variables = {}

        if "smb_shares" in operations:
            variables["smb_shares"] = self._prepare_smb_shares(operations["smb_shares"])

        if "nfs_exports" in operations:
            variables["nfs_exports"] = self._prepare_nfs_exports(operations["nfs_exports"])

        if "s3_buckets" in operations:
            variables["s3_buckets"] = operations["s3_buckets"]  # pass through, simple fields

        if "quotas" in operations:
            variables["quotas"] = self._prepare_quotas(operations["quotas"])

        if "snapshot_schedules" in operations:
            variables["snapshot_schedules"] = operations["snapshot_schedules"]  # pass through

        if "synciq_policies" in operations:
            variables["synciq_policies"] = operations["synciq_policies"]  # pass through

        if not variables:
            return {"success": False, "error": "No operations specified"}

        runner = AnsibleRunner(self.cluster)
        return runner.execute("batch_create.yml.j2", variables)

    def remove(self, operations: dict) -> dict:
        """Validate and prepare variables for batch_remove.yml.j2."""
        variables = {}
        # Similar structure — map keys to variables dict
        # Quota remove: map quota_type "hard"/"soft"/"advisory" to Ansible quota_type
        ...
        runner = AnsibleRunner(self.cluster)
        return runner.execute("batch_remove.yml.j2", variables)

    def _prepare_smb_shares(self, shares: list) -> list:
        """Pre-parse JSON string fields (permissions, host_acls, etc.) to native objects."""
        ...

    def _prepare_nfs_exports(self, exports: list) -> list:
        """Validate client IPs/hostnames per export."""
        ...

    def _prepare_quotas(self, quotas: list) -> list:
        """Call _parse_size() per quota, set the correct limit key, map quota_type."""
        ...
```

---

## Implementation Checklist

### Phase 1 — Tier 1 Templates
- [ ] `smb_create_batch.yml.j2`
- [ ] `smb_remove_batch.yml.j2`
- [ ] `nfs_create_batch.yml.j2`
- [ ] `nfs_remove_batch.yml.j2`
- [ ] `s3_create_batch.yml.j2`
- [ ] `s3_remove_batch.yml.j2`
- [ ] `quota_create_batch.yml.j2`
- [ ] `quota_remove_batch.yml.j2`
- [ ] `snapshot_schedule_create_batch.yml.j2`
- [ ] `snapshot_schedule_remove_batch.yml.j2`

### Phase 2 — Tier 2 Templates
- [ ] `batch_create.yml.j2`
- [ ] `batch_remove.yml.j2`

### Phase 3 — Domain Module Methods
- [ ] `smb.py` — `add_batch()`, `remove_batch()`
- [ ] `quotas.py` — `add_quota_batch()`, `remove_quota_batch()`
- [ ] `snapshotschedules.py` — `add_batch()`, `remove_batch()`
- [ ] `nfs.py` — `add_batch()`, `remove_batch()`
- [ ] `s3.py` — `add_batch()`, `remove_batch()`
- [ ] `synciq.py` — `add_batch()`, `remove_batch()`
- [ ] `batch.py` — new `BatchProvisioner` class

### Phase 4 — MCP Tools
- [ ] `server.py` — 10 Tier 1 tools
- [ ] `server.py` — 2 Tier 2 tools (`powerscale_batch_create`, `powerscale_batch_remove`)

### Phase 5 — Configuration
- [ ] `config/tools.json` — 12 new entries (write, disabled by default)
  - Tier 1: groups match existing (`smb`, `nfs`, `s3`, `quotas`, `snapshots`)
  - Tier 2: new group `batch`

---

## Key Design Decisions

### Why `{% if %}` in Jinja2 rather than `when:` in Ansible for Tier 2?

`{% if smb_shares is defined %}` removes the entire task block from the rendered YAML. Using `when: smb_shares is defined` keeps the task in the playbook but marks it skipped at runtime. The Jinja2 approach produces cleaner, smaller playbooks in the audit trail.

### Why not Python-level batching across tool calls?

A stateful queue ("collect operations, then execute") would require session state, complicating the stateless HTTP server design (`stateless_http=True`). The current approach keeps each tool call self-contained.

### Why keep Tier 1 when Tier 2 is more powerful?

Tier 1 is simpler for the LLM to use when working with a single resource type. The JSON schema for Tier 1 tools is a flat array; for Tier 2 it's a nested object. Both are useful.

### Credential security

No changes to the credential injection pattern. `AnsibleRunner._get_connection_vars()` returns placeholder strings. Real credentials are injected via `extravars` at ansible-runner execution time. Batch playbooks in the audit trail contain all resource parameters but no actual credentials — identical to the existing single-resource playbooks.

### Backward compatibility

All existing single-item tools (`powerscale_smb_create`, `powerscale_quota_create`, etc.) remain unchanged. Batch tools are additions only.

### Future extension

Adding a new resource type to `powerscale_batch_create`/`powerscale_batch_remove` requires:
1. Adding a `{% if new_type is defined %}...{% endif %}` block to both Tier 2 templates
2. Adding a `_prepare_new_type()` method to `BatchProvisioner`
3. Adding a `tools.json` entry

No changes to `AnsibleRunner` or the MCP tool signatures.

---

## Verification

After implementation, verify with the Docker container:

```bash
# 1. Rebuild
cd /docker/isi_mcp_demo && VAULT_PASSWORD=<pass> docker-compose up -d --build

# 2. Verify imports
docker-compose exec isi_mcp python -c "
from modules.onefs.v9_12_0.batch import BatchProvisioner
from modules.onefs.v9_12_0.smb import Smb
print('imports OK')
"

# 3. Enable batch tools
# Via MCP client:
powerscale_tools_toggle(names=["batch"], action="enable")
powerscale_tools_toggle(names=["smb"], action="enable")

# 4. Test Tier 1 — 3 shares, 1 playbook
powerscale_smb_create_batch(shares='[
  {"share_name": "test-batch-1", "path": "/ifs/test/batch1", "create_path": true},
  {"share_name": "test-batch-2", "path": "/ifs/test/batch2", "create_path": true},
  {"share_name": "test-batch-3", "path": "/ifs/test/batch3", "create_path": true}
]')
# Expected: success, 1 playbook file in playbooks/

# 5. Test Tier 2 — mixed types, 1 playbook
powerscale_batch_create(operations='{
  "smb_shares": [
    {"share_name": "test-mixed-1", "path": "/ifs/test/mixed1", "create_path": true}
  ],
  "quotas": [
    {"path": "/ifs/test/mixed1", "quota_type": "hard", "limit_size": "100GiB"}
  ],
  "snapshot_schedules": [
    {"name": "mixed1-daily", "path": "/ifs/test/mixed1", "schedule": "Every day at 1:00 AM"}
  ]
}')
# Expected: success, 1 playbook file in playbooks/, 3 resources created

# 6. Test Tier 2 — NFS + S3 combination
powerscale_batch_create(operations='{
  "nfs_exports": [
    {"path": "/ifs/test/nfs1", "clients": ["10.0.0.0/24"]}
  ],
  "s3_buckets": [
    {"bucket_name": "test-batch-s3", "path": "/ifs/test/s3"}
  ]
}')
# Expected: success, 1 playbook

# 7. Verify only 1 playbook per batch call
ls -lt /app/playbooks/ | head -5
```
