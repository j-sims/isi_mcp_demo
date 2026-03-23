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
    def _make_uuid(unix_ts: float, username: str, domain: str, mode: str) -> str:
        """Deterministic UUID5 derived from event identity fields.

        Inputs: unix timestamp (6 decimal places), username, domain, mode (read|write).
        Same inputs always produce the same UUID — useful for deduplication auditing.
        """
        name = f"{unix_ts:.6f}:{username}:{domain}:{mode}"
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

        output_str = json.dumps(output, default=str)
        if len(output_str) > _MAX_OUTPUT_CHARS:
            output_str = output_str[:_MAX_OUTPUT_CHARS] + "...[truncated]"

        entry = {
            "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            "uuid":      self._make_uuid(ts, username, domain, mode),
            "username":  username,
            "domain":    domain,
            "tool":      tool_name,
            "mode":      mode,
            "inputs":    inputs,
            "output":    output_str,
            "error":     error,
        }
        self._logger.info(json.dumps(entry, default=str))
