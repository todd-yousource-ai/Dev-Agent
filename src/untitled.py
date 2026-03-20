#!/usr/bin/env python3
"""
Forge Repository Structure Bootstrap
=====================================

Establishes the canonical directory layout, machine-readable path registry,
and human-readable namespace reference for the Consensus Dev Agent repository.

Security Model:
- All file writes are path-validated before execution via validate_path_component()
  and resolved-path containment checks.
- No secrets are embedded in any generated file.
- No external input is trusted; this script generates only static content.
- Fails closed: any path validation or I/O error aborts the entire operation
  with a non-zero exit code. Partial writes are not silently accepted.
- Symlink resolution is checked to prevent escaping the repository root.

Failure Behavior:
- Any OSError during directory creation or file write raises immediately with context.
- Invalid paths (traversal, symlinks to outside repo, absolute paths) are rejected.
- The script exits non-zero on any failure; no partial state is considered valid.

OI-13 Allocation Note:
- No caches or buffers. All strings are small inline constants (<4KB each).
- path_registry.json is <2KB. No dynamic allocation beyond file I/O.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- OI-13: Minimal allocation. Each constant is <4KB. ---

# Canonical directory structure: (path, description, governing_trd, owner)
# Each tuple is ~200 bytes. Total registry < 2KB.
CANONICAL_DIRECTORIES: List[Tuple[str, str, Optional[str], str]] = [
    ("forge-docs/", "TRDs, PRDs, and operator documentation. NOT runtime data.", "TRD-5", "forge-docs-owner"),
    ("forge-standards/", "Repository contracts: ARCHITECTURE.md, INTERFACES.md, DECISIONS.md, CONVENTIONS.md, path registry.", None, "forge-standards-owner"),
    ("forge-standards/paths/", "Path namespace registry and conventions.", None, "forge-standards-owner"),
    ("src/", "Python backend implementation modules.", "TRD-2", "backend-owner"),
    ("src/consensus/", "Consensus engine core.", "TRD-2", "backend-owner"),
    ("src/pipeline/", "Build pipeline orchestration.", "TRD-3", "backend-owner"),
    ("src/github/", "GitHub integration tools.", "TRD-5", "backend-owner"),
    ("src/security/", "Security enforcement modules (TRD-11).", "TRD-11", "security-owner"),
    ("ForgeAgent/", "Swift/SwiftUI application shell.", "TRD-1", "swift-owner"),
    ("ForgeAgent/XPC/", "XPC service definitions and protocol contracts.", "TRD-4", "swift-owner"),
    ("ForgeAgentTests/", "XCTest suites for Swift shell.", "TRD-1", "swift-owner"),
    ("tests/", "Python test suite (pytest). Mirrors src/ structure.", "TRD-3", "backend-owner"),
    ("tests/consensus/", "Tests for consensus engine.", "TRD-2", "backend-owner"),
    ("tests/pipeline/", "Tests for build pipeline.", "TRD-3", "backend-owner"),
    ("tests/github/", "Tests for GitHub integration.", "TRD-5", "backend-owner"),
    ("tests/security/", "Tests for security modules.", "TRD-11", "security-owner"),
    (".github/workflows/", "CI workflow definitions (forge-ci.yml).", "TRD-3", "ci-owner"),
    ("forge-runtime/", "Mutable operational state. NOT standards or specs. Gitignored except schema.", "TRD-4", "runtime-owner"),
    ("forge-runtime/state/", "Runtime state files (ledger, locks, heartbeats).", "TRD-4", "runtime-owner"),
    ("forge-runtime/logs/", "Operational logs. Gitignored.", "TRD-4", "runtime-owner"),
    ("scripts/", "Developer and CI utility scripts.", None, "ci-owner"),
]

# Files that must never exist in certain directories (collision guards)
COLLISION_RULES: List[Dict[str, str]] = [
    {
        "rule": "no-runtime-in-docs",
        "description": "forge-docs/ must never contain mutable runtime state, logs, or operational data.",
        "directory": "forge-docs/",
        "forbidden_patterns": "*.log, *.state, *.lock, *.pid",
    },
    {
        "rule": "no-specs-in-runtime",
        "description": "forge-runtime/ must never contain TRDs, PRDs, architecture docs, or standards.",
        "directory": "forge-runtime/",
        "forbidden_patterns": "*.md (except schema docs), *.docx, TRD-*, PRD-*",
    },
    {
        "rule": "no-standards-in-src",
        "description": "forge-standards/ content must not be duplicated into src/.",
        "directory": "src/",
        "forbidden_patterns": "ARCHITECTURE.md, INTERFACES.md, DECISIONS.md, CONVENTIONS.md",
    },
]


def validate_path_component(path_str: str) -> str:
    """
    Validate a path component against traversal and injection attacks.

    Security: Rejects any path containing '..', absolute paths, null bytes,
    or characters outside the allowed set. Fails closed on any violation.

    OI-13: No allocation beyond the input string validation.

    Args:
        path_str: Relative path string to validate.

    Returns:
        The validated path string (unchanged).

    Raises:
        ValueError: If the path fails any security check, with context.
    """
    if not path_str:
        raise ValueError("validate_path_component: empty path rejected")

    if '\x00' in path_str:
        raise ValueError("validate_path_component: null byte in path rejected")

    if os.path.isabs(path_str):
        raise ValueError(f"validate_path_component: absolute path rejected: {path_str}")

    # Normalize and check for traversal
    normalized = os.path.normpath(path_str)
    if '..' in normalized.split(os.sep):
        raise ValueError(f"validate_path_component: path traversal rejected: {path_str}")

    # Allow only alphanumeric, hyphen, underscore, dot, forward slash
    allowed_extra = set('-_./')
    for ch in path_str:
        if not (ch.isalnum() or ch in allowed_extra):
            raise ValueError(
                f"validate_path_component: illegal character '{ch}' (ord={ord(ch)}) in path: {path_str}"
            )

    return path_str


def validate_resolved_path(target: Path, repo_root: Path) -> None:
    """
    Validate that a resolved path is strictly contained within the repository root.

    Security: Prevents symlink escapes and path traversal after resolution.
    Fails closed if the target is not under repo_root.

    Args:
        target: Resolved absolute path to validate.
        repo_root: Resolved absolute path to repository root.

    Raises:
        ValueError: If target escapes repo_root.
    """
    try:
        target.relative_to(repo_root)
    except ValueError:
        raise ValueError(
            f"validate_resolved_path: resolved path escapes repo root: "
            f"{target} is not under {repo_root}"
        )


def enforce_collision_rules(repo_root: Path) -> List[str]:
    """
    Programmatically enforce collision rules against the current repository state.

    Scans each constrained directory for forbidden patterns and returns a list
    of violations. Callers SHOULD treat any non-empty return as a failure.

    Security: This provides active enforcement, not just documentation.
    OI-13: Scans only directories listed in COLLISION_RULES; no recursive walks
    beyond one level.

    Args:
        repo_root: Resolved absolute path to repository root.

    Returns:
        List of violation description strings. Empty list means all rules pass.
    """
    import fnmatch

    violations: List[str] = []

    # Parse the forbidden_patterns strings into individual glob patterns
    for rule in COLLISION_RULES:
        directory = rule["directory"]
        dir_path = (repo_root / directory).resolve()

        if not dir_path.is_dir():
            continue

        # Parse comma-separated patterns, stripping parenthetical notes
        raw_patterns = rule["forbidden_patterns"]
        patterns: List[str] = []
        for segment in raw_patterns.split(","):
            segment = segment.strip()
            # Remove parenthetical notes like "(except schema docs)"
            paren_idx = segment.find("(")
            if paren_idx != -1:
                segment = segment[:paren_idx].strip()
            if segment:
                patterns.append(segment)

        # Scan directory (non-recursive, one level) for violations
        try:
            for entry in dir_path.iterdir():
                entry_name = entry.name
                for pattern in patterns:
                    if fnmatch.fnmatch(entry_name, pattern):
                        violations.append(
                            f"[{rule['rule']}] Forbidden file '{entry_name}' "
                            f"in '{directory}' matches pattern '{pattern}'"
                        )
        except OSError:
            # Directory not readable -- not a collision violation, but note it
            pass

    return violations


def build_path_registry() -> Dict:
    """
    Build the machine-readable path registry as a dict suitable for JSON serialization.

    Security: All paths are validated. No external input is consumed.
    OI-13: Registry dict is <2KB serialized. No caching.

    Returns:
        Dict containing the canonical path registry with version and collision rules.

    Raises:
        ValueError: If any canonical path fails validation.
    """
    directories = []
    for dir_path, description, governing_trd, owner in CANONICAL_DIRECTORIES:
        # Validate every path -- fail closed on any violation
        validate_path_component(dir_path)
        directories.append({
            "path": dir_path,
            "description": description,
            "governing_trd": governing_trd,
            "owner": owner,
        })

    registry = {
        "schema_version": "1.0.0",
        "description": "Canonical path registry for Consensus Dev Agent repository. Machine-readable source of truth.",
        "security_note": "All paths are relative to repository root. Absolute paths and traversal are forbidden. Consumers MUST validate paths against this registry using validate_path_component() and validate_resolved_path().",
        "directories": directories,
        "collision_rules": COLLISION_RULES,
        "trd4_trd5_resolution": {
            "summary": "forge-docs/ is for TRDs and operator documentation (TRD-5 scope). forge-runtime/ is for mutable operational state (TRD-4 scope). These namespaces are mutually exclusive in content type.",
            "forge_docs": "Static documentation only: TRDs, PRDs, operator guides.",
            "forge_runtime": "Mutable state only: ledger, locks, logs, heartbeats.",
        },
    }
    return registry


def generate_repository_namespace_md() -> str:
    """
    Generate the human-readable REPOSITORY_NAMESPACE.md content.

    Security: Pure string generation from validated constants. No external input.
    OI-13: Output string is <4KB. No buffering.

    Returns:
        Markdown string for REPOSITORY_NAMESPACE.md.
    """
    lines = [
        "# Repository Namespace Reference",
        "",
        "> **Source of truth:** `forge-standards/paths/path_registry.json`",
        "> **This document is generated.** Do not edit manually.",
        "",
        "## TRD-4 / TRD-5 Collision Resolution",
        "",
        "The PRD identified a path collision between `forge-docs/` (TRD-5) and `forge-runtime/` (TRD-4).",
        "This is resolved as follows:",
        "",
        "| Namespace | Content Type | Governing TRD | Mutable? |",
        "|-----------|-------------|---------------|----------|",
        "| `forge-docs/` | TRDs, PRDs, operator documentation | TRD-5 | No (static) |",
        "| `forge-runtime/` | Operational state: ledger, locks, logs, heartbeats | TRD-4 | Yes (mutable) |",
        "| `forge-standards/` | Repository contracts, path registry, conventions | N/A | No (static) |",
        "",
        "**Rule:** `forge-docs/` never contains runtime data. `forge-runtime/` never contains specs or standards.",
        "",
        "## Canonical Directory Layout",
        "",
        "| Path | Purpose | Governing TRD | Owner |",
        "|------|---------|---------------|-------|",
    ]

    for dir_path, description, governing_trd, owner in CANONICAL_DIRECTORIES:
        trd_display = governing_trd if governing_trd else "--"
        lines.append(f"| `{dir_path}` | {description} | {trd_display} | {owner} |")

    lines.extend([
        "",
        "## Naming Conventions",
        "",
        "- **Python modules:** `snake_case.py` under `src/`.",
        "- **Swift files:** `PascalCase.swift` under `ForgeAgent/`.",
        "- **Tests mirror source:** `tests/consensus/` tests `src/consensus/`, etc.",
        "- **TRDs:** `TRD-{N}-{Title}.docx` under `forge-docs/`.",
        "- **No dotfiles in content dirs:** Configuration dotfiles live at repo root only.",
        "- **No spaces in paths.** Hyphens for multi-word directory names.",
        "",
        "## Collision Rules",
        "",
    ])

    for rule in COLLISION_RULES:
        lines.append(f"### `{rule['rule']}`")
        lines.append("")
        lines.append(f"**Directory:** `{rule['directory']}`")
        lines.append(f"**Description:** {rule['description']}")
        lines.append(f"**Forbidden patterns:** `{rule['forbidden_patterns']}`")
        lines.append("")

    lines.extend([
        "## Security",
        "",
        "- All paths are relative to repository root.",
        "- Absolute paths, path traversal (`..`), null bytes, and symlinks outside the repo are forbidden.",
        "- Path validation is enforced programmatically by `validate_path_component()` and",
        "  `validate_resolved_path()` at both bootstrap time and runtime.",
        "- Collision rules are enforced by `enforce_collision_rules()` which scans directories",
        "  for forbidden file patterns and returns actionable violations.",
        "- The `path_registry.json` is the machine-readable contract; tooling MUST validate against it.",
        "",
    ])

    return "\n".join(lines)


def generate_forge_standards_readme() -> str:
    """
    Generate the forge-standards/README.md content.

    OI-13: Output <1KB.
    """
    return """# forge-standards/

Canonical repository contracts for the Consensus Dev Agent.

## Contents

| File / Directory | Purpose |
|-----------------|---------|
| `ARCHITECTURE.md` | System architecture reference |
| `INTERFACES.md` | Interface contracts between subsystems |
| `DECISIONS.md` | Architectural decision records |
| `CONVENTIONS.md` | Code and naming conventions |
| `paths/` | Path namespace registry and conventions |
| `paths/path_registry.json` | Machine-readable canonical path registry |
| `paths/REPOSITORY_NAMESPACE.md` | Human-readable namespace reference |

## Governance

This directory is the canonical location for repository-level contracts.
No runtime data, logs, or mutable state belongs here.

All paths referenced in this namespace are validated against
`paths/path_registry.json` -- the machine-readable source of truth.

See `paths/REPOSITORY_NAMESPACE.md` for the full namespace reference
and the TRD-4/TRD-5 collision resolution rationale.
"""


def generate_gitkeep_content() -> str:
    """
    Content for .gitkeep files in empty directories.
    OI-
