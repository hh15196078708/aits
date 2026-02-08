"""
system_tools.py - Cross-platform System Utilities
System info retrieval, command execution, and path handling.
"""

import os
import platform
import subprocess
import uuid


def get_system_info() -> dict:
    """Gather basic system information."""
    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
    }


def get_device_code() -> str:
    """Generate a unique device identifier."""
    mac = uuid.getnode()
    return f"{platform.node()}-{mac:012x}"


def get_base_dir() -> str:
    """Return the project base directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_command(cmd: str, timeout: int = 30) -> tuple:
    """Execute a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
