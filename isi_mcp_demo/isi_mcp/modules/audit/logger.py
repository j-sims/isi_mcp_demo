import hashlib
import json
import logging
import logging.handlers
import os
import time
import uuid
from datetime import datetime, timezone

# Custom UUID namespace for audit event UUIDs (fixed, project-specific)
_AUDIT_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# Truncate large tool outputs in the log to keep entries reasonable
_MAX_OUTPUT_CHARS = 4096

# Input keys whose values are redacted before an audit entry is written. Matched
# case-insensitively as substrings, so 'password' also covers 'api_password' and
# 'new_password', etc. Extend via the AUDIT_REDACT_KEYS env var (comma-separated).
_DEFAULT_REDACT_KEYS = ("password", "passwd", "secret", "token")
_REDACTED = "***"


def _resolve_redact_keys() -> tuple:
    extra = os.environ.get("AUDIT_REDACT_KEYS", "")
    tokens = {t.strip().lower() for t in extra.split(",") if t.strip()}
    return tuple({*_DEFAULT_REDACT_KEYS, *tokens})


def _redact(value, keys):
    """Recursively replace values of sensitive keys with a redaction marker.

    Walks dicts (matching keys by case-insensitive substring) and lists/tuples;
    scalars and non-matching values are returned unchanged.
    """
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            if isinstance(k, str) and any(tok in k.lower() for tok in keys):
                result[k] = _REDACTED
            else:
                result[k] = _redact(v, keys)
        return result
    if isinstance(value, (list, tuple)):
        return [_redact(v, keys) for v in value]
    return value


class AuditLogger:
    """Singleton rotating-file audit logger. One JSON object per line (NDJSON).

    Reads configuration from environment variables:
      MAX_AUDIT_LOGFILE_SIZE  - max bytes per file before rotation (default: 10 MiB)
      MAX_AUDIT_LOGFILE_COUNT - number of rotated backup files to keep (default: 10)
      AUDIT_LOG_DIR           - directory for log files (default: /app/audit)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        max_bytes = int(os.environ.get("MAX_AUDIT_LOGFILE_SIZE", 10 * 1024 * 1024))
        backup_count = int(os.environ.get("MAX_AUDIT_LOGFILE_COUNT", 10))
        audit_dir = os.environ.get("AUDIT_LOG_DIR", "/app/audit")
        os.makedirs(audit_dir, exist_ok=True)

        # Resolved once at startup; sensitive input values are redacted in log().
        self._redact_keys = _resolve_redact_keys()

        self._logger = logging.getLogger("isi_mcp.audit")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        if not self._logger.handlers:
            handler = logging.handlers.RotatingFileHandler(
                os.path.join(audit_dir, "audit.log"),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    @staticmethod
    def _make_uuid(unix_ts: float, username: str, domain: str, tool_name: str,
                   mode: str, inputs) -> str:
        """Deterministic UUID5 derived from the full event identity.

        Inputs: unix timestamp (6 decimal places), username, domain, tool name,
        mode (read|write), and a hash of the (already-redacted) arguments. Including
        the tool name and arguments means two distinct calls in the same microsecond
        no longer collide, while identical calls still produce the same UUID — so the
        value remains useful for deduplication auditing.
        """
        inputs_hash = hashlib.sha256(
            json.dumps(inputs, default=str, sort_keys=True).encode("utf-8")
        ).hexdigest()
        name = f"{unix_ts:.6f}:{username}:{domain}:{tool_name}:{mode}:{inputs_hash}"
        return str(uuid.uuid5(_AUDIT_NAMESPACE, name))

    def log(
        self,
        username: str,
        domain: str,
        tool_name: str,
        mode: str,
        inputs: dict,
        output,
        error: str | None = None,
    ) -> None:
        ts = time.time()

        # Redact sensitive input values (passwords, tokens, secrets) before the
        # entry is written so credentials never persist in the on-disk audit log.
        inputs = _redact(inputs, self._redact_keys)

        # Truncate oversized outputs to keep audit entries bounded. We must NOT
        # json.loads() the sliced JSON back — cutting a JSON string at an arbitrary
        # offset almost always yields invalid JSON and raises. Instead, replace the
        # output with a string marker that still serializes cleanly.
        output_json = json.dumps(output, default=str)
        if len(output_json) > _MAX_OUTPUT_CHARS:
            output = output_json[:_MAX_OUTPUT_CHARS] + "...[truncated]"

        entry = {
            "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            "uuid":      self._make_uuid(ts, username, domain, tool_name, mode, inputs),
            "username":  username,
            "domain":    domain,
            "tool":      tool_name,
            "mode":      mode,
            "inputs":    inputs,
            "output":    output,
            "error":     error,
        }
        self._logger.info(json.dumps(entry, default=str))
