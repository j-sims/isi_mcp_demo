import logging
import socket

logger = logging.getLogger(__name__)

def pingable(host: str, debug=False, timeout=1, port=8080) -> bool:
    """
    Return True if host accepts a TCP connection on the given port within timeout.

    Uses a non-forking socket check instead of subprocess ping to avoid
    deadlocks in multi-threaded async servers (uvicorn).

    Args:
        host: IP address or hostname to check
        debug: Print debug messages if True
        timeout: Timeout in seconds for connection attempt (default: 1)
        port: TCP port to connect to (default: 8080, the PowerScale API port)
    """
    try:
        conn = socket.create_connection((host, port), timeout=timeout)
        conn.close()
        logger.debug("TCP connect %s:%d succeeded", host, port)
        return True
    except (OSError, socket.timeout) as err:
        logger.debug("TCP connect %s:%d failed: %s", host, port, err)
        return False
