"""Minimal smoke check module.

Security assumptions:
- No I/O, authentication, or external interaction.
- No external input; no input validation surface.

Failure behavior:
- No failure path under normal execution; returns a constant boolean.
"""


def smoke_check() -> bool:
    """Return True to indicate a successful smoke check."""
    return True
