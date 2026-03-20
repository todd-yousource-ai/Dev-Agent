

```python
# VERSION
```

Let me implement all the files for this PR:

```
0.1.0
```

That's the VERSION file content. Now let me produce all files properly:

**VERSION**
```
0.1.0
```

Let me start over and produce clean implementation code for each file:

```python
# File: VERSION
# Content: 0.1.0
```

I'll implement each file in sequence.

---

**File: VERSION**

```
0.1.0
```

---

**File: version.py**

```python
"""
Forge version utility module — single-source-of-truth version reader and validator.

Security assumptions:
- The VERSION file is trusted repository content (not external input), but we
  still validate its format strictly to fail closed on corruption or tampering.
- No secrets are involved in version handling.
- All parse failures raise explicit exceptions with context — no silent fallback
  to potentially wrong version strings.
- Memory allocation: one short string read (<32 bytes expected). # OI-13

Failure behavior:
- If VERSION file is missing or unreadable: raises VersionFileError with path context.
- If VERSION file content does not match semver: raises VersionFormatError with the
  offending content (truncated to prevent log flooding).
- If compatibility check fails structurally: raises VersionCompatError.
- No silent defaults, no fallback versions — fail closed.
"""

import json
import re
from pathlib import Path
from typing import NamedTuple, Optional


# OI-13: Single compiled regex, ~200 bytes — minimal allocation
_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z\-]+(?:\.[0-9A-Za-z\-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z\-]+(?:\.[0-9A-Za-z\-]+)*))?$"
)

# OI-13: Max bytes we will read from VERSION file to prevent DoS on corrupted file
_MAX_VERSION_FILE_BYTES = 128

# OI-13: Max bytes we will read from VERSION_MANIFEST.json
_MAX_MANIFEST_FILE_BYTES = 8192


class VersionFileError(Exception):
    """Raised when the VERSION file cannot be read."""
    pass


class VersionFormatError(Exception):
    """Raised when a version string does not conform to semver."""
    pass


class VersionCompatError(Exception):
    """Raised when version compatibility check encounters a structural error."""
    pass


class SemVer(NamedTuple):
    """Parsed semantic version components."""
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    def __str__(self) -> str:
        """Reconstruct the canonical semver string."""
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base = f"{base}-{self.prerelease}"
        if self.build:
            base = f"{base}+{self.build}"
        return base


def _repo_root() -> Path:
    """
    Resolve the repository root by walking up from this file's directory.

    Security: We look for the VERSION file as an anchor. If not found within
    5 levels, we fail closed rather than guessing.

    OI-13: No allocation beyond Path objects.
    """
    current = Path(__file__).resolve().parent
    # Walk up at most 5 levels to find VERSION file
    for _ in range(6):  # OI-13: bounded iteration
        if (current / "VERSION").is_file():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise VersionFileError(
        f"Cannot locate repository root (no VERSION file found walking up from {Path(__file__).parent})"
    )


def parse_semver(version_string: str) -> SemVer:
    """
    Parse and validate a semantic version string.

    Args:
        version_string: The version string to parse (e.g., "0.1.0", "1.2.3-beta.1+build.42")

    Returns:
        SemVer named tuple with parsed components.

    Raises:
        VersionFormatError: If the string does not match semver spec.

    Security:
        Input is truncated to _MAX_VERSION_FILE_BYTES before matching to prevent
        ReDoS on pathological input. The regex is anchored (^ and $).
    """
    if not isinstance(version_string, str):
        raise VersionFormatError(
            f"Version must be a string, got {type(version_string).__name__}"
        )

    # OI-13: Truncate to prevent regex DoS on oversized input
    cleaned = version_string.strip()[:_MAX_VERSION_FILE_BYTES]

    match = _SEMVER_RE.match(cleaned)
    if not match:
        # Truncate in error message to prevent log flooding
        display = cleaned[:64] + ("..." if len(cleaned) > 64 else "")
        raise VersionFormatError(
            f"Invalid semver string: '{display}'"
        )

    return SemVer(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        prerelease=match.group("prerelease"),
        build=match.group("build"),
    )


def read_version_file(version_file_path: Optional[Path] = None) -> str:
    """
    Read the canonical VERSION file and return the validated semver string.

    Args:
        version_file_path: Override path to VERSION file. If None, auto-discovers
                          from repository root.

    Returns:
        Validated semver string (stripped, no trailing newline).

    Raises:
        VersionFileError: If the file cannot be read.
        VersionFormatError: If the file content is not valid semver.

    Security:
        - Reads at most _MAX_VERSION_FILE_BYTES to bound memory allocation.
        - Validates format strictly before returning.
        - No fallback to hardcoded values — fail closed.
    """
    if version_file_path is None:
        version_file_path = _repo_root() / "VERSION"

    if not version_file_path.is_file():
        raise VersionFileError(
            f"VERSION file not found at: {version_file_path}"
        )

    try:
        # OI-13: Bounded read — no unbounded allocation
        raw = version_file_path.read_text(encoding="utf-8")[:_MAX_VERSION_FILE_BYTES]
    except OSError as exc:
        raise VersionFileError(
            f"Failed to read VERSION file at {version_file_path}: {exc}"
        ) from exc

    version_string = raw.strip()

    if not version_string:
        raise VersionFormatError(
            f"VERSION file at {version_file_path} is empty"
        )

    # Validate before returning — fail closed on malformed content
    parse_semver(version_string)

    return version_string


def get_version() -> SemVer:
    """
    Read and parse the canonical project version.

    Returns:
        SemVer named tuple from the root VERSION file.

    Raises:
        VersionFileError: If VERSION file cannot be located or read.
        VersionFormatError: If content is not valid semver.
    """
    return parse_semver(read_version_file())


def is_compatible(version_a: str, version_b: str) -> bool:
    """
    Check if two versions are compatible per semver rules.

    Compatibility contract:
    - MAJOR must match (breaking changes boundary)
    - For MAJOR == 0 (development): MINOR must also match (0.x is unstable)
    - Pre-release versions are only compatible with the same pre-release

    Args:
        version_a: First semver string.
        version_b: Second semver string.

    Returns:
        True if versions are compatible, False otherwise.

    Raises:
        VersionFormatError: If either version string is invalid.

    Security:
        Both inputs are validated through parse_semver (untrusted input safe).
    """
    a = parse_semver(version_a)
    b = parse_semver(version_b)

    # Major version must always match
    if a.major != b.major:
        return False

    # During 0.x development, minor version is the compatibility boundary
    if a.major == 0:
        if a.minor != b.minor:
            return False

    # Pre-release compatibility: both must have same pre-release or both none
    if a.prerelease != b.prerelease:
        return False

    return True


def check_manifest_compatibility(
    component: str,
    component_version: str,
    manifest_path: Optional[Path] = None,
) -> bool:
    """
    Check if a component version falls within the allowed range defined in VERSION_MANIFEST.json.

    Args:
        component: Component name (e.g., "swift_shell", "python_backend").
        component_version: The version string to check.
        manifest_path: Override path to manifest file. If None, auto-discovers.

    Returns:
        True if the component version is within the manifest's allowed range.

    Raises:
        VersionFileError: If manifest cannot be read.
        VersionFormatError: If any version string in the manifest or input is invalid.
        VersionCompatError: If the manifest structure is malformed or component not found.

    Security:
        - Manifest file is repository content but validated structurally.
        - JSON parsing uses stdlib json (no eval).
        - Bounded file read via _MAX_MANIFEST_FILE_BYTES.
        - Component name validated against manifest keys — no injection vector.
    """
    if manifest_path is None:
        manifest_path = _repo_root() / "VERSION_MANIFEST.json"

    if not manifest_path.is_file():
        raise VersionFileError(
            f"VERSION_MANIFEST.json not found at: {manifest_path}"
        )

    try:
        # OI-13: Bounded read
        raw = manifest_path.read_text(encoding="utf-8")[:_MAX_MANIFEST_FILE_BYTES]
    except OSError as exc:
        raise VersionFileError(
            f"Failed to read VERSION_MANIFEST.json at {manifest_path}: {exc}"
        ) from exc

    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VersionCompatError(
            f"VERSION_MANIFEST.json is not valid JSON: {exc}"
        ) from exc

    if not isinstance(manifest, dict):
        raise VersionCompatError(
            "VERSION_MANIFEST.json root must be a JSON object"
        )

    compat_matrix = manifest.get("compatibility_matrix")
    if not isinstance(compat_matrix, dict):
        raise VersionCompatError(
            "VERSION_MANIFEST.json must contain a 'compatibility_matrix' object"
        )

    component_entry = compat_matrix.get(component)
    if not isinstance(component_entry, dict):
        raise VersionCompatError(
            f"Component '{component[:64]}' not found in compatibility_matrix"
        )

    min_version_str = component_entry.get("min_version")
    max_version_str = component_entry.get("max_version")

    if not isinstance(min_version_str, str) or not isinstance(max_version_str, str):
        raise VersionCompatError(
            f"Component '{component[:64]}' must define 'min_version' and 'max_version' as strings"
        )

    target = parse_semver(component_version)
    min_ver = parse_semver(min_version_str)
    max_ver = parse_semver(max_version_str)

    # Compare as tuples (major, minor, patch) — pre-release ordering is not
    # implemented here; for pre-release range checks, extend as needed.
    target_tuple = (target.major, target.minor, target.patch)
    min_tuple = (min_ver.major, min_ver.minor, min_ver.patch)
    max_tuple = (max_ver.major, max_ver.minor, max_ver.patch)

    return min_tuple <= target_tuple <= max_tuple


# --- Module-level version constant ---
# OI-13: Single string allocation (~12 bytes). Read once at import time.
# If this fails, the module cannot be imported — fail closed is intentional.
# Callers that need graceful handling should use read_version_file() / get_version() directly.
try:
    __version__: str = read_version_file()
except (VersionFileError, VersionFormatError):
    # During package builds or isolated test environments the VERSION file may
    # not be reachable from the installed package location.  In that narrow case
    # we fall back to the value baked into the package metadata (if available).
    # This is NOT a silent fallback — we attempt one explicit alternative source.
    try:
        from importlib.metadata import version as _pkg_version
        _meta_ver = _pkg_version("consensus-dev-agent")
        parse_semver(_meta_ver)  # validate — fail closed if bad
        __version__ = _meta_ver
    except Exception:
        # Absolute last resort: no version can be determined.
        # Fail loud at import time so no subsystem runs with unknown version.
        raise VersionFileError(
            "Cannot determine project version: VERSION file not found and package metadata unavailable. "
            "Ensure the VERSION file exists at the repository root or the package is properly installed."
        )
```

---

**File: VERSION_MANIFEST.json**

```json
{
  "schema_version": "1.0.0",
  "description": "Consensus Dev Agent version compatibility matrix. Defines allowed version ranges for each component. All version strings must be valid semver.",
  "canonical_version_file": "VERSION",
  "compatibility_matrix": {
    "swift_shell": {
      "component": "Consensus Dev Agent macOS Shell (Swift)",
      "min_version": "0.1.0",
      "max_version": "0.1.99",
      "notes": "Swift shell must be within the same 0.1.x range as the Python backend during 0.x development."
    },
    "python_backend": {
      "component": "Consensus Dev Agent Python Backend",
      "min_version": "0.1.0",
      "max_version": "0.1.99",
      "notes": "Python backend version is read from the root VERSION file."
    },
    "xpc_protocol": {
      "component": "XPC Protocol Version",
      "min_version": "0.1.0",
      "max_version": "0.1.99",
      "notes": "XPC protocol changes require coordinated version bumps in both shell and backend."
    }
  }
}
```

---

**File: forge-standards/versioning/SEMVER_POLICY.md**

```markdown
# Semantic Versioning Policy — Consensus Dev Agent

**Status:** Active
**Applies to:** All components (Swift shell, Python backend, XPC protocol)
**Authority:** This document is normative. Version bumps that violate this policy MUST be rejected in review.

---

## 1. Version Source of Truth

The file `VERSION` at the repository root is the **single source of truth** for the project version. All other version references (Info.plist, pyproject.toml, runtime constants) MUST be derived from this file.

- The `VERSION` file contains exactly one line: a valid [Semantic Versioning 2.0.0](https://semver.org/) string.
- No trailing newline ambiguity: tooling strips whitespace. The canonical form is `MAJOR.MINOR.PATCH` with optional `-prerelease` and `+build` suffixes.
- CI enforces that `VERSION` and `pyproject.toml` version fields match (`TestVersionConsistency`).

---

## 2. What Constitutes Each Bump

### MAJOR (X.0.0)
Increment MAJOR when making **incompatible