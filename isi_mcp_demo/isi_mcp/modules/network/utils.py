import subprocess
import shlex

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
    print(f"Debug Mode: {debug}")
    try:
        completed = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Return Code: {completed.returncode}")
        return completed.returncode == 0
    except FileNotFoundError:
        if debug:
            print("File Not Found Error")
        return False
    except Exception as err:
        if debug:
            print(f"Error: {err}")
        return False
