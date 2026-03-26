"""Core versioning module for the Crafted Dev Agent Python backend.

Reads the repository-root VERSION file at import time, validates its content
against strict semver, and exposes four public constants:

    VERSION_STRING          -- e.g. "0.1.0"
    VERSION_TUPLE           -- e.g. (0, 1, 0)  (all int)
    COMPATIBILITY_VERSION   -- e.g. "0.1"       (major.minor)
    MIN_COMPATIBLE_VERSION  -- e.g. "0.1"       (minimum compatible major.minor)

Security assumptions:
    - The VERSION file is project-internal data committed to the repository.
      Its content is treated as inert data -- never evaluated or executed.
    - No fallback values are used. If the VERSION file is missing or contains
      invalid content, import fails immediately with a descriptive exception.
    - The module never calls eval/exec on any file content.

Failure behavior:
    - FileNotFoundError: raised if the VERSION file cannot be found within
      a bounded parent traversal (max 5 levels from this file).
    - ValueError: raised if the VERSION file is empty, contains only
      whitespace, or does not match strict semver (MAJOR.MINOR.PATCH with
      no pre-release or build metadata).
    - No silent defaults. The agent must never run with an unknown version.
"""

from __future__ import annotations

import re
from pathlib import Path

# Strict semver pattern: MAJOR.MINOR.PATCH, numeric only, no leading zeros
# except for the value 0 itself. No pre-release or build metadata for now.
_SEMVER_PATTERN: re.Pattern[str] = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"
)

# Maximum number of parent directory levels to traverse when searching
# for the VERSION file from this module's location.
# This file lives at crafted_agent_backend/versioning/version.py, so the
# VERSION file at the repository root is exactly 2 levels up. A limit of 5
# provides reasonable headroom without risking escape from the project tree.
_MAX_PARENT_TRAVERSAL: int = 5


def _resolve_version_file_path() -> Path:
    """Locate the VERSION file by traversing parent directories from this module.

    Walks up from the directory containing this file, checking each ancestor
    for a file named ``VERSION``. Stops after ``_MAX_PARENT_TRAVERSAL`` levels.

    Returns:
        Path to the VERSION file.

    Raises:
        FileNotFoundError: If no VERSION file is found within the traversal limit.
    """
    current = Path(__file__).resolve().parent

    for _level in range(_MAX_PARENT_TRAVERSAL):
        candidate = current / "VERSION"
        if candidate.is_file():
            return candidate
        parent = current.parent
        # Stop if we've hit the filesystem root (parent == self)
        if parent == current:
            break
        current = parent

    raise FileNotFoundError(
        f"VERSION file not found within {_MAX_PARENT_TRAVERSAL} parent levels "
        f"of {Path(__file__).resolve()}. The VERSION file must exist at the "
        f"repository root."
    )


def _read_version_file(path: Path) -> str:
    """Read and return the stripped content of the VERSION file.

    Args:
        path: Absolute path to the VERSION file.

    Returns:
        The version string with leading/trailing whitespace removed.

    Raises:
        FileNotFoundError: If the file does not exist at the given path.
        ValueError: If the file is empty or contains only whitespace.
    """
    try:
        raw_content = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise FileNotFoundError(
            f"Could not read VERSION file at {path}: {exc}"
        ) from exc

    if not raw_content:
        raise ValueError(
            f"VERSION file at {path} is empty or contains only whitespace. "
            f"It must contain a valid semver string (e.g. '0.1.0')."
        )

    return raw_content


def _parse_semver(version_str: str) -> tuple[int, int, int]:
    """Parse a strict semver string into a (major, minor, patch) integer tuple.

    Args:
        version_str: A string expected to match MAJOR.MINOR.PATCH format.

    Returns:
        Tuple of (major, minor, patch) as integers.

    Raises:
        ValueError: If the string does not match strict semver format.
    """
    match = _SEMVER_PATTERN.match(version_str)

    if match is None:
        raise ValueError(
            f"VERSION content '{version_str}' is not a valid semver string. "
            f"Expected format: MAJOR.MINOR.PATCH (e.g. '0.1.0'). "
            f"Pre-release and build metadata are not supported."
        )

    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )


#