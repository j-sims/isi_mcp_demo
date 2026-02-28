import logging
import subprocess

logger = logging.getLogger(__name__)

def pingable(host: str, debug=False, timeout=1) -> bool:
    """
    Return True if host responds to a single ICMP ping within timeout seconds (Linux).

    Args:
        host: IP address or hostname to ping
        debug: Print debug messages if True
        timeout: Timeout in seconds for ping response (default: 1)
    """
    # Use ping with timeout (-W timeout in milliseconds)
    timeout_ms = int(timeout * 1000)
    cmd = ["ping", "-c", "1", "-W", str(timeout_ms), host]
    try:
        completed = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.debug("ping %s → rc=%d", host, completed.returncode)
        return completed.returncode == 0
    except FileNotFoundError:
        logger.debug("ping command not found")
        return False
    except Exception as err:
        logger.debug("ping %s failed: %s", host, err)
        return False
