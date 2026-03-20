#!/usr/bin/env python3
"""
Forge Repository Structure Bootstrap
=====================================

Establishes the canonical directory layout and path namespace conventions
for the Consensus Dev Agent repository.

Owner TRD: TRD-5 (GitHub Integration -- repository bootstrap)
Co-governing: TRD-4 (Multi-Agent Coordination -- namespace ownership)

Security Assumptions:
- This script is run by a trusted operator or CI pipeline during repo bootstrap.
- All paths are validated against an allowlist before any filesystem operation.
- No external input is consumed; all paths are hardcoded constants derived from
  TRD-4/TRD-5 specifications and AGENTS.md conventions.
- No secrets are involved in directory structure creation.

Failure Behavior:
- Fails closed: if any path validation fails, the entire operation aborts.
- Every error surfaces with full context (path, reason, phase).
- No silent failures: all operations return explicit status or raise.

OI-13 Memory Budget Compliance:
- No caches or buffers allocated. All data structures are minimal constant-size
  dicts/lists defined at module scope and not duplicated.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants -- canonical directory list (TRD-5 §15 bootstrap set)
# ---------------------------------------------------------------------------

# Owner TRD for this module's bootstrap responsibilities
_OWNER_TRD = "TRD-5"

# Every directory the bootstrap must ensure exists, keyed by relative path.
# Each tuple: (owner_trd, mutable_at_runtime, purpose)
_CANONICAL_DIRS: dict[str, tuple[str, bool, str]] = {
    "forge-standards/": ("TRD-4, TRD-5", False, "Architecture contracts, ADRs, schemas, policies"),
    "forge-standards/paths/": ("TRD-4, TRD-5", False, "Path registry and namespace documentation"),
    "forge-runtime/": ("TRD-3", True, "Operational state for build pipeline"),
    "forge-runtime/ledger/": ("TRD-3", True, "Build ledger JSON state files"),
    "forge-runtime/journals/": ("TRD-3", True, "Agent operation journals and audit logs"),
    "forge-docs/": ("TRD-7", False, "Operator TRD documents"),
    "src/": ("TRD-2", False, "Python backend implementation root"),
    "src/consensus_engine/": ("TRD-2", False, "Python 3.12 backend packages"),
    "src/consensus_engine/core/": ("TRD-2", False, "Core consensus, pipeline, and ledger logic"),
    "src/consensus_engine/integrations/": ("TRD-2, TRD-5", False, "GitHub, LLM provider adapters"),
    "src/consensus_engine/security/": ("TRD-11", False, "Auth, crypto, path validation"),
    "ConsensusShell/": ("TRD-1", False, "Swift macOS application shell"),
    "tests/": ("TRD-6", False, "Test tree root"),
    "tests/consensus_engine/": ("TRD-6", False, "Tests for consensus_engine"),
    "tests/consensus_engine/core/": ("TRD-6", False, "Tests for consensus_engine/core"),
    "tests/consensus_engine/integrations/": ("TRD-6", False, "Tests for consensus_engine/integrations"),
    "tests/consensus_engine/security/": ("TRD-6", False, "Tests for consensus_engine/security"),
    ".github/": ("TRD-5", False, "GitHub configuration root"),
    ".github/workflows/": ("TRD-3", False, "CI pipeline workflow definitions"),
}

# Directories that need .gitkeep files because they are runtime-mutable and
# may start empty (Git does not track empty directories).
_GITKEEP_DIRS: frozenset[str] = frozenset({
    "forge-runtime/ledger/",
    "forge-runtime/journals/",
})

# Allowlist of path prefixes -- any path we create must start with one of these.
_ALLOWED_PREFIXES: tuple[str, ...] = (
    "forge-standards/",
    "forge-runtime/",
    "forge-docs/",
    "src/",
    "ConsensusShell/",
    "tests/",
    ".github/",
)


# ---------------------------------------------------------------------------
# Path validation (fail-closed)
# ---------------------------------------------------------------------------

class PathValidationError(Exception):
    """Raised when a path fails allowlist validation."""


def _validate_path(relative_path: str) -> None:
    """Validate that *relative_path* is within the allowed namespace.

    Raises PathValidationError with full context on failure.
    """
    # Reject empty or absolute paths
    if not relative_path:
        raise PathValidationError(f"Empty path supplied (phase=validation)")
    if os.path.isabs(relative_path):
        raise PathValidationError(
            f"Absolute path rejected: {relative_path!r} (phase=validation)"
        )
    # Reject traversal components
    normalised = os.path.normpath(relative_path)
    if ".." in normalised.split(os.sep):
        raise PathValidationError(
            f"Path traversal detected: {relative_path!r} (phase=validation)"
        )
    # Allowlist check
    if not relative_path.startswith(_ALLOWED_PREFIXES):
        raise PathValidationError(
            f"Path outside allowed namespace: {relative_path!r} "
            f"(allowed_prefixes={_ALLOWED_PREFIXES}, phase=validation)"
        )


# ---------------------------------------------------------------------------
# Directory creation
# ---------------------------------------------------------------------------

def _ensure_directory(repo_root: Path, relative_path: str) -> Path:
    """Create a single directory, returning its absolute path.

    Validates the path first; raises on any failure.
    """
    _validate_path(relative_path)
    target = repo_root / relative_path
    target.mkdir(parents=True, exist_ok=True)
    return target


def _ensure_gitkeep(repo_root: Path, relative_dir: str) -> Path:
    """Create a .gitkeep inside the given directory so Git tracks it."""
    _validate_path(relative_dir)
    gitkeep = repo_root / relative_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    return gitkeep


# ---------------------------------------------------------------------------
# Bootstrap entry point
# ---------------------------------------------------------------------------

def bootstrap_repository_structure(repo_root: Path | str) -> dict[str, Any]:
    """Create all canonical directories under *repo_root*.

    Returns a summary dict with counts and any errors (empty on success).
    Fails closed: if **any** path validation fails, raises immediately.
    """
    repo_root = Path(repo_root).resolve()
    created: list[str] = []
    gitkeeps: list[str] = []

    # Phase 1: create directories
    for rel_path in _CANONICAL_DIRS:
        abs_path = _ensure_directory(repo_root, rel_path)
        created.append(str(abs_path))

    # Phase 2: place .gitkeep in runtime-mutable empty dirs
    for rel_dir in sorted(_GITKEEP_DIRS):
        gk = _ensure_gitkeep(repo_root, rel_dir)
        gitkeeps.append(str(gk))

    return {
        "repo_root": str(repo_root),
        "directories_created": len(created),
        "gitkeep_files_created": len(gitkeeps),
        "status": "ok",
    }


# ---------------------------------------------------------------------------
# PATH_REGISTRY.json generation helper
# ---------------------------------------------------------------------------

def generate_path_registry() -> dict[str, Any]:
    """Return the PATH_REGISTRY data structure (without JSON-Schema mixed in).

    The registry is a pure data document. Schema validation, if desired,
    should reference an external schema file.
    """
    entries: list[dict[str, Any]] = []
    for rel_path, (owner_trd, mutable, purpose) in _CANONICAL_DIRS.items():
        is_file = not rel_path.endswith("/")
        entries.append({
            "path": rel_path,
            "type": "file" if is_file else "directory",
            "purpose": purpose,
            "owner_trd": owner_trd,
            "mutable_at_runtime": mutable,
        })
    return {
        "_meta": {
            "description": (
                "Machine-readable registry of all canonical repository paths. "
                "Each entry defines ownership, mutability, and content constraints. "
                "This file is the authoritative allowlist for path validation."
            ),
            "version": "1.0.0",
            "governing_trds": ["TRD-4", "TRD-5"],
            "immutable_at_runtime": True,
            "schema": "forge-standards/paths/PATH_REGISTRY.schema.json",
        },
        "paths": entries,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entry point for bootstrapping the repo structure."""
    repo_root = Path.cwd() if len(sys.argv) < 2 else Path(sys.argv[1])
    try:
        result = bootstrap_repository_structure(repo_root)
    except (PathValidationError, OSError) as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
