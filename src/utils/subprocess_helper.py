"""
Safe subprocess execution with consistent error handling.
"""
import subprocess
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Default timeouts (seconds)
DEFAULT_TIMEOUT = 10
SHORT_TIMEOUT = 5
LONG_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 600


class SubprocessError(Exception):
    """Custom subprocess error."""

    def __init__(self, message: str, returncode: int = None, stderr: str = None):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def run_command(
    cmd: List[str],
    timeout: int = DEFAULT_TIMEOUT,
    capture: bool = True,
    check: bool = True,
    text: bool = True
) -> subprocess.CompletedProcess:
    """
    Run subprocess with consistent error handling.

    Args:
        cmd: Command and arguments
        timeout: Timeout in seconds
        capture: Capture stdout/stderr
        check: Raise exception on non-zero exit
        text: Return as text (not bytes)

    Returns:
        CompletedProcess result

    Raises:
        FileNotFoundError: If command not found
        SubprocessError: On error (if check=True)
        subprocess.TimeoutExpired: On timeout
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            timeout=timeout,
            check=check,
            text=text
        )
        logger.debug(f"Command succeeded: {' '.join(cmd)}")
        return result

    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed: {' '.join(cmd)}"
        logger.error(f"{error_msg} (exit {e.returncode}): {e.stderr}")
        raise SubprocessError(error_msg, e.returncode, e.stderr) from e

    except FileNotFoundError:
        error_msg = f"Command not found: {cmd[0]}"
        logger.error(error_msg)
        raise

    except subprocess.TimeoutExpired:
        error_msg = f"Command timeout after {timeout}s: {' '.join(cmd)}"
        logger.error(error_msg)
        raise
