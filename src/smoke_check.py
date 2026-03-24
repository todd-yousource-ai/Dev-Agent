"""Minimal smoke-check module.

Security assumptions:
- This module is intentionally side-effect free and does not process external input.
- The function returns a constant value and therefore has no failure paths.

Failure behavior:
- No exceptions are expected under normal interpreter operation.
- Any import/runtime failure outside this function should be surfaced by Python directly.
"""


def smoke_check() -> bool:
    """Return True to indicate the smoke check passed."""
    return True
