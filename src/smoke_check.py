"""Smoke check module for Forge platform health verification.

Fail-closed behavior: function is pure and deterministic with no failure path.
No secrets, credentials, or external input involved.
"""


def smoke_check() -> bool:
    """Return True to indicate the system is alive and responsive.

    Returns:
        bool: Always True as a basic health/liveness signal.
    """
    return True
