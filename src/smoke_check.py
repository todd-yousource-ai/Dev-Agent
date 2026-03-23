"""Smoke check module for Forge platform health verification.

Trace: FORGE-SMOKE-001 -- Minimal liveness signal for platform health checks.

Security assumptions:
- No external input is accepted or processed.
- No secrets, credentials, or sensitive data are involved.
- Pure, deterministic function with no side effects.

Fail-closed rationale:
- The function body is a single literal return; there is no code path
  that can silently degrade or return an ambiguous result.  Any import-
  or runtime-level failure will propagate as an unhandled exception,
  satisfying fail-closed requirements by default.
"""


def smoke_check() -> bool:
    """Return True to indicate the system is alive and operational."""
    return True
