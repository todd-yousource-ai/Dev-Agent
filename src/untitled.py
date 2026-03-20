

```
0.1.0
```

```markdown
# ADR-003: Version Policy and Cross-Process Compatibility Contract

## Status: Accepted

**Date:** 2025-01-15
**Deciders:** Forge Platform Engineering
**Compliance:** PRD-001, TRD-12 §5

---

## Context

Consensus Dev Agent is a two-process architecture: a Swift shell (macOS native UI and XPC host) and a Python backend (LLM orchestration, code generation, CI integration). These processes are independently buildable and potentially independently updatable.

Without a formal version alignment policy:

1. A Swift shell update could ship with an incompatible Python backend, causing silent data corruption or undefined behavior in the XPC bridge.
2. Operators cannot verify that a running system is internally consistent.
3. CI cannot gate on compatibility, allowing broken combinations to reach production.
4. There is no contract for when breaking changes require coordinated updates.

The VERSION file is the single source of truth. All other version declarations (Info.plist, pyproject.toml, Python constants) derive from or must match this file.

---

## Decision

### 1. Single VERSION File at Repository Root

- Location: `./VERSION`
- Format: Exactly one line containing `MAJOR.MINOR.PATCH` (strict semver, no pre-release suffixes, no build metadata).
- Regex validation: `^\d+\.\d+\.\d+$`
- No trailing newline beyond the single terminating `\n`.
- This file is the **canonical** version. All other version references must match exactly.

### 2. Semantic Versioning Rules

| Increment | When |
|-----------|------|
| **MAJOR** | Breaking change to XPC message schema, Python backend CLI contract, or any public API consumed cross-process. |
| **MINOR** | New capability added in a backward-compatible manner. New XPC message types (old ones unchanged). New CLI subcommands. |
| **PATCH** | Bug fixes, security patches, documentation, internal refactors with no cross-process contract change. |

### 3. Compatibility Rule

**MAJOR.MINOR must match between Swift shell and Python backend.**

- A Swift shell at version `1.3.x` is compatible with a Python backend at version `1.3.y` for any `x`, `y`.
- A Swift shell at version `1.3.x` is **NOT compatible** with a Python backend at version `1.4.y` or `2.0.y`.
- PATCH-level mismatches are tolerated. MINOR or MAJOR mismatches are fatal.

This is enforced at startup via the Handshake Protocol.

### 4. Handshake Protocol

Per TRD-12 §5, on backend startup the Swift shell sends a `version_handshake` XPC message containing its own version string. The Python backend:

1. Reads `VERSION` file (or falls back to compiled constant).
2. Parses both versions with strict semver validation.
3. Compares MAJOR and MINOR components.
4. If MAJOR.MINOR matches → responds with `handshake_ack { compatible: true, backend_version: "X.Y.Z" }`.
5. If MAJOR.MINOR does NOT match → responds with `handshake_ack { compatible: false, reason: "..." }` and the Swift shell **must** refuse to proceed (fail closed).
6. If either version string fails validation → fail closed, log error with context, do not proceed.

Unknown XPC message types during handshake are discarded and logged per Forge invariants.

### 5. Synchronization Points

All of the following must contain the **exact same** version string as `./VERSION`:

| Location | Format | Enforcement |
|----------|--------|-------------|
| `./VERSION` | Plain text | Canonical source |
| `pyproject.toml` `[project].version` | TOML string | CI test: `TestVersionConsistency` |
| `Info.plist` `CFBundleShortVersionString` | Plist string | CI test: `TestVersionConsistency` |
| Python `AGENT_VERSION` constant | String literal | Runtime read from VERSION file |

### 6. Version Bump Procedure

```bash
# 1. Update the canonical source
echo "X.Y.Z" > VERSION

# 2. Update pyproject.toml
sed -i '' 's/version = ".*"/version = "X.Y.Z"/' pyproject.toml

# 3. Update Info.plist (if present)
# Use PlistBuddy or equivalent

# 4. Run version consistency tests
python -m pytest tests/ -k "test_version"
```

---

## Consequences

### Positive
- Single source of truth eliminates version drift.
- MAJOR.MINOR compatibility rule is simple to understand and enforce.
- Handshake protocol catches incompatibilities at startup, not at runtime failure.
- Fail-closed behavior prevents undefined cross-process interactions.

### Negative
- Any MINOR bump requires coordinated release of both Swift shell and Python backend.
- VERSION file must be readable at runtime, adding a (minimal) filesystem dependency.

---

## Rejected Alternatives

### Alternative 1: Independent Versioning per Component
Each component (Swift shell, Python backend) has its own version number. A compatibility matrix maps which versions work together.

**Rejected because:** Compatibility matrices are error-prone, hard to maintain, and create a combinatorial testing burden. The system is always deployed as a unit.

### Alternative 2: Semver with Pre-release Suffixes
Allow versions like `1.0.0-beta.1` or `1.0.0-rc.2`.

**Rejected because:** Pre-release suffixes complicate parsing, comparison, and the handshake protocol. They can be introduced later if needed; starting simple is preferred.

### Alternative 3: Build Metadata in VERSION File
Include build hashes or timestamps, e.g., `1.0.0+abc123`.

**Rejected because:** Build metadata is not relevant to compatibility decisions and adds parsing complexity. Git commit hashes are available separately.

### Alternative 4: No Handshake — Trust CI
Rely entirely on CI to prevent incompatible versions from shipping.

**Rejected because:** CI is a safety net, not a guarantee. Defense-in-depth requires runtime verification. Fail closed at startup is the correct behavior for security-critical deployments.

---

## Compliance Mapping

| Requirement | Source | How Addressed |
|-------------|--------|---------------|
| Single version source of truth | PRD-001 | `./VERSION` file |
| Cross-process version alignment | TRD-12 §5 | Handshake protocol with MAJOR.MINOR match |
| Fail closed on mismatch | Forge Security Standards | Handshake rejects and halts on incompatibility |
| No silent failures | Forge Engineering Standards | All validation errors surface with context |
```

```markdown
# Semantic Versioning Policy — Consensus Dev Agent

## Overview

This document specifies the concrete semver rules for the Consensus Dev Agent repository.
For architectural rationale, see [ADR-003](../adrs/ADR-003-version-policy.md).

## VERSION File Contract

| Property | Specification |
|----------|---------------|
| **Location** | Repository root: `./VERSION` |
| **Encoding** | UTF-8, no BOM |
| **Content** | Exactly one line: `MAJOR.MINOR.PATCH` |
| **Regex** | `^\d+\.\d+\.\d+$` |
| **Line ending** | Single `\n` (Unix) |
| **Maximum size** | 32 bytes (OI-13 memory budget compliance) |

## What Constitutes a Breaking Change (MAJOR bump)

- Removing or renaming an XPC message type
- Changing the schema of an existing XPC message
- Removing or changing the signature of a Python backend CLI command consumed by the Swift shell
- Changing the handshake protocol itself
- Removing a public Python API consumed by external integrations

## What Constitutes a Feature Addition (MINOR bump)

- Adding a new XPC message type (existing ones unchanged)
- Adding a new CLI subcommand
- Adding new fields to XPC messages that have safe defaults (additive only)
- New Python modules or public APIs

## What Constitutes a Patch (PATCH bump)

- Bug fixes with no contract changes
- Security patches
- Performance improvements
- Documentation updates
- Internal refactors

## Cross-Process Compatibility

**Rule: MAJOR.MINOR must be identical between Swift shell and Python backend.**

```
Swift 1.3.2 + Python 1.3.5 → ✅ Compatible (PATCH difference OK)
Swift 1.3.2 + Python 1.4.0 → ❌ Incompatible (MINOR mismatch)
Swift 1.3.2 + Python 2.0.0 → ❌ Incompatible (MAJOR mismatch)
```

## Enforcement

1. **CI:** `TestVersionConsistency` validates VERSION ↔ pyproject.toml ↔ Info.plist.
2. **Runtime:** Python backend validates VERSION file format on startup.
3. **Handshake:** Swift shell and Python backend exchange versions before any work begins.
4. **Code review:** Version bumps require explicit justification in PR description.

## Initial Version

The repository starts at `0.1.0`, indicating:
- Pre-1.0: API stability is not yet guaranteed.
- MINOR and PATCH rules still apply for change classification.
- The handshake protocol is still enforced.
```

```markdown
# Version Compatibility Manifest

## Current Version

```
0.1.0
```

## Compatibility Matrix

| Swift Shell Version | Python Backend Version | Status |
|--------------------|-----------------------|--------|
| 0.1.x | 0.1.x | ✅ Compatible |

## Compatibility Rule

Two components are compatible if and only if their `MAJOR.MINOR` values are identical.
PATCH-level differences are always tolerated.

## Handshake Contract

The Swift shell initiates a version handshake on every backend launch:

```
Shell → Backend: { "type": "version_handshake", "shell_version": "0.1.0" }
Backend → Shell: { "type": "handshake_ack", "compatible": true, "backend_version": "0.1.0" }
```

On incompatibility:

```
Backend → Shell: { "type": "handshake_ack", "compatible": false, "reason": "MINOR version mismatch: shell=0.1, backend=0.2" }
```

The shell MUST fail closed and refuse to proceed if `compatible` is `false` or if the handshake response is malformed.

## Minimum Supported Versions

| Component | Minimum Version | Notes |
|-----------|----------------|-------|
| Swift Shell | 0.1.0 | Initial release |
| Python Backend | 0.1.0 | Initial release |
| macOS | 14.0 | Required for XPC features |
| Python | 3.11 | Runtime requirement |
```

```python
"""
forge_version.py — Version reading, validation, comparison, and compatibility checking.

Forge Platform utility for the Consensus Dev Agent version contract.

Security Assumptions:
    - The VERSION file is located at a known, path-validated repository root location.
    - The VERSION file is treated as untrusted input: its content is strictly validated
      against the semver regex before any use.
    - No secrets are involved in version operations.
    - All validation failures raise explicit exceptions with context (no silent failures).
    - This module never executes generated content (no eval/exec/subprocess).

Failure Behavior:
    - Invalid VERSION file content → VersionValidationError with context
    - Missing VERSION file → VersionFileNotFoundError with path context
    - VERSION file exceeding size budget → VersionValidationError (OI-13 compliance)
    - Incompatible versions → VersionIncompatibleError with mismatch details
    - All errors are typed exceptions; callers must handle or propagate (fail closed).

Memory Budget (OI-13):
    - VERSION file read limited to 32 bytes max (semver "999.999.999" = 11 chars + newline).
    - No caches or buffers beyond the single version string in memory.
    - VersionInfo is a lightweight NamedTuple (3 ints, ~72 bytes).

Compliance:
    - PRD-001: Cross-TRD Architecture Baseline
    - TRD-12 §5: Version Compatibility Rules
    - ADR-003: Version Policy
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple, Optional, Union

# OI-13: Maximum bytes to read from VERSION file. "999.999.999\n" = 12 bytes.
# 32 bytes provides margin without unbounded allocation.
_VERSION_FILE_MAX_BYTES: int = 32  # OI-13 explicit allocation: 32 bytes max read

# Strict semver regex: MAJOR.MINOR.PATCH, digits only, no leading zeros except "0" itself.
# Per ADR-003: no pre-release suffixes, no build metadata.
_SEMVER_PATTERN: re.Pattern[str] = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"
)


class VersionError(Exception):
    """Base exception for all version-related errors. Never caught silently."""
    pass


class VersionValidationError(VersionError):
    """Raised when a version string fails strict semver validation."""
    pass


class VersionFileNotFoundError(VersionError):
    """Raised when the VERSION file cannot be located."""
    pass


class VersionFileReadError(VersionError):
    """Raised when the VERSION file exists but cannot be read."""
    pass


class VersionIncompatibleError(VersionError):
    """Raised when two versions fail the MAJOR.MINOR compatibility check."""
    pass


class VersionInfo(NamedTuple):
    """
    Parsed semantic version. Immutable, lightweight (3 ints).
    OI-13: ~72 bytes per instance, no dynamic allocations.
    """
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def validate_version_string(version: str) -> str:
    """
    Validate a version string against strict semver (MAJOR.MINOR.PATCH).

    Args:
        version: The version string to validate. Treated as untrusted input.

    Returns:
        The validated, stripped version string.

    Raises:
        VersionValidationError: If the string does not match strict semver format.
            Includes the invalid input (truncated to 50 chars) for diagnostics.
    """
    if not isinstance(version, str):
        raise VersionValidationError(
            f"Version must be a string, got {type(version).__name__}"
        )

    stripped = version.strip()

    if not stripped:
        raise VersionValidationError("Version string is empty after stripping whitespace")

    # OI-13: reject unreasonably long strings before regex matching
    if len(stripped) > _VERSION_FILE_MAX_BYTES:
        raise VersionValidationError(
            f"Version string exceeds maximum length ({len(stripped)} > {_VERSION_FILE_MAX_BYTES}): "
            f"'{stripped[:50]}...'"
        )

    if not _SEMVER_PATTERN.match(stripped):
        raise VersionValidationError(
            f"Version string does not match strict semver (MAJOR.MINOR.PATCH): '{stripped[:50]}'"
        )

    return stripped


def parse_version(version: str) -> VersionInfo:
    """
    Parse a version string into a VersionInfo tuple.

    Args:
        version: A semver string (e.g., "1.2.3"). Treated as untrusted input.

    Returns:
        VersionInfo with major, minor, patch as integers.

    Raises:
        VersionValidationError: If the string is not valid strict semver.
    """
    validated = validate_version_string(version)
    match = _SEMVER_PATTERN.match(validated)
    # match is guaranteed non-None because validate_version_string already checked
    assert match is not None  # defensive: validate_version_string guarantees this
    return VersionInfo(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
    )


def find_version_file(search_from: Optional[Path]