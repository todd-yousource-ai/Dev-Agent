"""Smoke check module.

Security: no I/O, networking, or secret handling. Deterministic and side-effect free.
Failure: cannot fail under normal execution; always returns ``True``.
"""


def smoke_check() -> bool:
    """Return ``True`` for basic smoke-test validation."""
    return True
