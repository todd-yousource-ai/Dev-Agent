"""Smoke check module for Forge platform health verification.

Security assumptions:
- This module provides a minimal liveness/health signal.
- No external input is consumed; no secrets are involved.
- Failure behavior: function is pure and cannot fail under normal execution.
"""


def smoke_check() -> bool:
    """Return True to indicate the system is alive and responsive.

    Returns:
        bool: Always returns True as a baseline health signal.
    """
    return True
