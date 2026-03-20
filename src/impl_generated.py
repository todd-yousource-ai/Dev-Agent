#!/usr/bin/env python3
"""
forge-standards/paths/path_registry_validator.py

Validates PATH_REGISTRY.json against the canonical schema and verifies
that declared directories exist on disk.

Supports two schema shapes:
  - Array schema (schema_version string "X.Y.Z"): namespaces is a list of objects.
  - Object schema (registry_version integer): namespaces is a dict keyed by name.

Security assumptions:
- PATH_REGISTRY.json is treated as untrusted input; all fields validated.
- No path traversal allowed; all paths must be relative and within repo root.
- Fails closed: any validation error is a hard failure with context.
- No secrets involved; no external network access.
- OI-13: Minimal memory allocation. No caching. Stream-process entries.

Failure behavior:
- Returns non-zero exit code on any validation failure.
- Prints structured error messages to stderr with full context.
- Never silently passes; every check is explicit.
"""

import json
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


# OI-13: No large buffers. Schema defined as minimal frozen constants.
# --- Array-schema (schema_version string) ---
REQUIRED_TOP_LEVEL_KEYS_ARRAY = frozenset({"schema_version", "generated", "namespaces"})
REQUIRED_NAMESPACE_KEYS_ARRAY = frozenset({"path", "purpose", "owner", "mutability", "trd_authority"})

# --- Object-schema (registry_version integer) ---
REQUIRED_TOP_LEVEL_KEYS_OBJECT = frozenset({"registry_version", "namespaces"})
REQUIRED_NAMESPACE_KEYS_OBJECT = frozenset({"path", "purpose", "owner", "mutability"})

VALID_MUTABILITY_VALUES = frozenset({"operator-only", "ci-managed", "agent-writable", "generated", "append-only"})
VALID_OWNER_VALUES = frozenset({"operator", "agent", "ci", "shared"})
SCHEMA_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
# Maximum number of namespace entries to prevent resource exhaustion (OI-13)
MAX_NAMESPACE_ENTRIES = 200
# Maximum path length to prevent filesystem abuse
MAX_PATH_LENGTH = 256


class PathRegistryValidationError(Exception):
    """Raised when PATH_REGISTRY.json fails validation. Always includes context."""
    pass


def _resolve_repo_root() -> Path:
    """
    Walk up from this file to find the repository root.
    Repo root is identified by containing a .git directory or AGENTS.md file.
    Fails closed if root cannot be determined.
    """
    current = Path(__file__).resolve().parent
    for _ in range(10):  # OI-13: bounded traversal, no infinite loops
        if (current / ".git").exists() or (current / "AGENTS.md").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise PathRegistryValidationError(
        "Cannot determine repository root. "
        "Expected .git/ or AGENTS.md in an ancestor directory of "
        f"{Path(__file__).resolve()}"
    )


def _validate_path_safety(path_str: str, context: str) -> None:
    """
    Validate that a path string is safe: relative, no traversal, no null bytes.
    Fails closed on any suspicious input.

    Security: This is a defense-in-depth check. Even though PATH_REGISTRY.json
    is committed to the repo, we treat it as untrusted input per Forge standards.
    """
    if not isinstance(path_str, str):
        raise PathRegistryValidationError(
            f"[{context}] Path must be a string, got {type(path_str).__name__}"
        )

    if len(path_str) == 0:
        raise PathRegistryValidationError(f"[{context}] Path must not be empty")

    if len(path_str) > MAX_PATH_LENGTH:
        raise PathRegistryValidationError(
            f"[{context}] Path exceeds maximum length {MAX_PATH_LENGTH}: {len(path_str)}"
        )

    # Null byte injection
    if "\x00" in path_str:
        raise PathRegistryValidationError(f"[{context}] Path contains null byte")

    # Path traversal
    posix_path = PurePosixPath(path_str)
    if posix_path.is_absolute():
        raise PathRegistryValidationError(
            f"[{context}] Path must be relative, got absolute: {path_str}"
        )

    for part in posix_path.parts:
        if part == "..":
            raise PathRegistryValidationError(
                f"[{context}] Path traversal detected (..): {path_str}"
            )
        if part.startswith(".") and part != ".":
            # Allow dotfiles like .github but not hidden traversal tricks
            pass

    # No backslashes (Windows-style paths that could bypass posix checks)
    if "\\" in path_str:
        raise PathRegistryValidationError(
            f"[{context}] Backslash in path (use forward slashes): {path_str}"
        )


def _validate_string_field(obj: dict, key: str, context: str, allowed: frozenset | None = None) -> str:
    """Validate a required string field. Fails closed if missing or wrong type."""
    if key not in obj:
        raise PathRegistryValidationError(f"[{context}] Missing required field: {key}")
    value = obj[key]
    if not isinstance(value, str):
        raise PathRegistryValidationError(
            f"[{context}] Field '{key}' must be string, got {type(value).__name__}"
        )
    if len(value.strip()) == 0:
        raise PathRegistryValidationError(f"[{context}] Field '{key}' must not be empty/blank")
    if allowed is not None and value not in allowed:
        raise PathRegistryValidationError(
            f"[{context}] Field '{key}' value '{value}' not in allowed set: {sorted(allowed)}"
        )
    return value


def _validate_optional_string_field(obj: dict, key: str, context: str) -> str | None:
    """Validate an optional string field if present. Returns None if absent."""
    if key not in obj:
        return None
    value = obj[key]
    if not isinstance(value, str):
        raise PathRegistryValidationError(
            f"[{context}] Field '{key}' must be string, got {type(value).__name__}"
        )
    return value


def _detect_schema_shape(data: dict) -> str:
    """
    Detect which schema shape the registry uses.

    Returns:
        "array" for schema_version (string semver) + namespaces-as-list
        "object" for registry_version (integer) + namespaces-as-dict

    Fails closed if shape is ambiguous or unrecognized.
    """
    has_schema_version = "schema_version" in data
    has_registry_version = "registry_version" in data

    if has_schema_version and has_registry_version:
        raise PathRegistryValidationError(
            "Registry contains both 'schema_version' and 'registry_version'. "
            "Ambiguous schema shape -- must use exactly one."
        )

    if has_schema_version:
        return "array"
    elif has_registry_version:
        return "object"
    else:
        raise PathRegistryValidationError(
            "Registry must contain either 'schema_version' (string, X.Y.Z) "
            "or 'registry_version' (integer). Neither found."
        )


def _validate_schema_version_string(data: dict) -> None:
    """Validate schema_version as a semver string (array schema)."""
    schema_version = data["schema_version"]
    if not isinstance(schema_version, str):
        raise PathRegistryValidationError(
            f"schema_version must be a string, got {type(schema_version).__name__}"
        )
    if not SCHEMA_VERSION_PATTERN.match(schema_version):
        raise PathRegistryValidationError(
            f"schema_version must match X.Y.Z semver pattern, got: {schema_version!r}"
        )


def _validate_registry_version_integer(data: dict) -> None:
    """Validate registry_version as a positive integer (object schema)."""
    registry_version = data["registry_version"]
    # JSON integers deserialize as int; reject floats, bools, strings
    if isinstance(registry_version, bool) or not isinstance(registry_version, int):
        raise PathRegistryValidationError(
            f"registry_version must be an integer, got {type(registry_version).__name__}: {registry_version!r}"
        )
    if registry_version < 1:
        raise PathRegistryValidationError(
            f"registry_version must be a positive integer, got: {registry_version}"
        )


def _validate_namespaces_array(
    namespaces: list,
    repo_root: Path,
    check_dirs: bool,
) -> list[str]:
    """Validate namespaces when shaped as a list of objects (array schema)."""
    if len(namespaces) == 0:
        raise PathRegistryValidationError("'namespaces' array must not be empty")

    if len(namespaces) > MAX_NAMESPACE_ENTRIES:
        raise PathRegistryValidationError(
            f"'namespaces' has {len(namespaces)} entries (max {MAX_NAMESPACE_ENTRIES}). OI-13 constraint."
        )

    validated_paths: list[str] = []
    seen_paths: set[str] = set()

    for idx, ns in enumerate(namespaces):
        ctx = f"namespaces[{idx}]"

        if not isinstance(ns, dict):
            raise PathRegistryValidationError(f"[{ctx}] Entry must be an object, got {type(ns).__name__}")

        missing_ns_keys = REQUIRED_NAMESPACE_KEYS_ARRAY - set(ns.keys())
        if missing_ns_keys:
            raise PathRegistryValidationError(f"[{ctx}] Missing required keys: {sorted(missing_ns_keys)}")

        path_val = _validate_string_field(ns, "path", ctx)
        _validate_path_safety(path_val, ctx)

        normalized = path_val.rstrip("/")
        if normalized in seen_paths:
            raise PathRegistryValidationError(f"[{ctx}] Duplicate path: {path_val}")
        seen_paths.add(normalized)

        _validate_string_field(ns, "purpose", ctx)
        _validate_string_field(ns, "owner", ctx, allowed=VALID_OWNER_VALUES)
        _validate_string_field(ns, "mutability", ctx, allowed=VALID_MUTABILITY_VALUES)
        _validate_string_field(ns, "trd_authority", ctx)

        if check_dirs:
            dir_path = repo_root / normalized
            if not dir_path.exists():
                raise PathRegistryValidationError(
                    f"[{ctx}] Declared directory does not exist: {dir_path}"
                )
            if not dir_path.is_dir():
                raise PathRegistryValidationError(
                    f"[{ctx}] Declared path exists but is not a directory: {dir_path}"
                )

        validated_paths.append(path_val)

    return validated_paths


def _validate_namespaces_object(
    namespaces: dict,
    repo_root: Path,
    check_dirs: bool,
) -> list[str]:
    """Validate namespaces when shaped as an object keyed by namespace name (object schema)."""
    if len(namespaces) == 0:
        raise PathRegistryValidationError("'namespaces' object must not be empty")

    if len(namespaces) > MAX_NAMESPACE_ENTRIES:
        raise PathRegistryValidationError(
            f"'namespaces' has {len(namespaces)} entries (max {MAX_NAMESPACE_ENTRIES}). OI-13 constraint."
        )

    validated_paths: list[str] = []
    seen_paths: set[str] = set()

    for ns_key, ns in namespaces.items():
        ctx = f"namespaces[{ns_key!r}]"

        if not isinstance(ns_key, str) or len(ns_key.strip()) == 0:
            raise PathRegistryValidationError(f"[{ctx}] Namespace key must be a non-empty string")

        if not isinstance(ns, dict):
            raise PathRegistryValidationError(f"[{ctx}] Entry must be an object, got {type(ns).__name__}")

        missing_ns_keys = REQUIRED_NAMESPACE_KEYS_OBJECT - set(ns.keys())
        if missing_ns_keys:
            raise PathRegistryValidationError(f"[{ctx}] Missing required keys: {sorted(missing_ns_keys)}")

        path_val = _validate_string_field(ns, "path", ctx)
        _validate_path_safety(path_val, ctx)

        normalized = path_val.rstrip("/")
        if normalized in seen_paths:
            raise PathRegistryValidationError(f"[{ctx}] Duplicate path: {path_val}")
        seen_paths.add(normalized)

        _validate_string_field(ns, "purpose", ctx)
        _validate_string_field(ns, "owner", ctx, allowed=VALID_OWNER_VALUES)
        _validate_string_field(ns, "mutability", ctx, allowed=VALID_MUTABILITY_VALUES)

        # trd_authority is optional in object schema but validated if present
        _validate_optional_string_field(ns, "trd_authority", ctx)

        if check_dirs:
            dir_path = repo_root / normalized
            if not dir_path.exists():
                raise PathRegistryValidationError(
                    f"[{ctx}] Declared directory does not exist: {dir_path}"
                )
            if not dir_path.is_dir():
                raise PathRegistryValidationError(
                    f"[{ctx}] Declared path exists but is not a directory: {dir_path}"
                )

        validated_paths.append(path_val)

    return validated_paths


def _check_json_truncation(raw: str) -> None:
    """
    Detect truncated JSON content. Fails closed if the file appears incomplete.

    Heuristic checks beyond what json.loads catches:
    - Unbalanced braces/brackets (crude but effective for obvious truncation).
    - Missing closing structure.
    """
    stripped = raw.rstrip()
    if len(stripped) == 0:
        raise PathRegistryValidationError("Registry file is empty")

    # A well-formed JSON object must end with '}'; array with ']'
    if stripped[0] == '{' and stripped[-1] != '}':
        raise PathRegistryValidationError(
            "Registry file appears truncated: starts with '{' but does not end with '}'. "
            "Ensure the file is complete and not cut off."
        )
    if stripped[0] == '[' and stripped[-1] != ']':
        raise PathRegistryValidationError(
            "Registry file appears truncated: starts with '[' but does not end with ']'. "
            "Ensure the file is complete and not cut off."
        )

    # Count braces/brackets as a secondary truncation signal
    open_braces = raw.count('{')
    close_braces = raw.count('}')
    open_brackets = raw.count('[')
    close_brackets = raw.count(']')

    if open_braces != close_braces:
        raise PathRegistryValidationError(
            f"Registry file has mismatched braces: {open_braces} '{{' vs {close_braces} '}}'. "
            "File may be truncated or malformed."
        )
    if open_brackets != close_brackets:
        raise PathRegistryValidationError(
            f"Registry file has mismatched brackets: {open_brackets} '[
