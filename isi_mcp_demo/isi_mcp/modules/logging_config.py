"""Centralized logging configuration for the isi_mcp server.

Usage in any module:
    import logging
    logger = logging.getLogger(__name__)

Call ``configure_logging()`` once at startup (server.py) to set the
format and level.  The LOG_LEVEL env var controls verbosity
(default: INFO).
"""

import logging
import os


def configure_logging() -> None:
    """Configure the root logger with a structured format.

    Level is controlled by the LOG_LEVEL environment variable
    (DEBUG, INFO, WARNING, ERROR, CRITICAL).  Defaults to INFO.
    """
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )
