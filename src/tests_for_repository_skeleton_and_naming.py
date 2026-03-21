tests/__init__.py:
# Copyright 2026 YouSource.ai -- Consensus Dev Agent
# SPDX-License-Identifier: PROPRIETARY
"""Forge test suite root package.

This file marks tests/ as a Python package to enable pytest discovery
and relative imports within the test hierarchy.

Security assumptions:
    - Test code is never deployed to production.
    - Test fixtures never contain real secrets or credentials.

Failure behavior:
    - N/A -- no runtime behavior.
"""

tests/test_repo_structure/__init__.py:
# Copyright 2026 YouSource.ai -- Consensus Dev Agent
# SPDX-License-Identifier: PROPRIETARY
"""Forge repository structure test package.

Tests that validate the bootstrapped repository layout, naming conventions,
canonical document presence, and the validate_structure.py script itself.

All tests in this package are pure filesystem-inspection tests with no
application imports. They are safe to run in any environment.

Security assumptions:
    - Tests perform read-only filesystem operations (except tmp_path usage).
    - No application code is imported or executed.

Failure behavior:
    - Test failures indicate structural regressions in the repository layout.
"""

tests/test_repo_structure/conftest.py:
# Copyright 2026 YouSource.ai -- Consensus Dev Agent
# SPDX-License-Identifier: PROPRIETARY
"""Shared fixtures for repository structure tests.

Provides the single source of truth for which directories, packages, and
documents are required -- derived from the repository skeleton established
in PRs 1-4 and the PRD-001 specification.

Security assumptions:
    - All fixtures return hardcoded values; no external input is consumed.
    - Path operations use pathlib for cross-platform safety.

Failure behavior:
    - Fixture failures cause dependent tests to error with full context.
    - repo_root fixture fails explicitly if .git directory cannot be found.
"""

import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Return the absolute path to the repository root.

    Walks up from this file's location looking for a .git directory.
    Fails explicitly if the repository root cannot be determined.

    Returns:
        Path: Absolute path to the repository root directory.

    Raises:
        RuntimeError: If no .git directory is found in any ancestor.
    """
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    if (current / ".git").exists():
        return current
    raise RuntimeError(
        f"Could not find repository root (.git directory) starting from "
        f"{Path(__file__).resolve().parent}. Ensure tests are run from "
        f"within the repository."
    )


@pytest.fixture(scope="session")
def required_directories() -> list:
    """Return the list of all required directories from the PR 1-4 skeleton.

    These are relative paths from the repository root that MUST exist
    as directories.

    Returns:
        list[str]: Sorted list of required directory relative paths.
    """
    return sorted([
        ".github",
        ".github/workflows",
        "ForgeApp",
        "ForgeApp/ForgeAgent",
        "ForgeApp/ForgeAgentTests",
        "ForgeApp/Resources",
        "ForgeApp/Sources",
        "ForgeApp/Sources/ForgeApp",
        "ForgeApp/Sources/ForgeApp/App",
        "ForgeApp/Sources/ForgeApp/IPC",
        "ForgeApp/Sources/ForgeApp/Services",
        "ForgeApp/Sources/ForgeApp/UI",
        "artifacts",
        "config",
        "config/defaults",
        "contracts",
        "docs",
        "docs/architecture",
        "docs/prds",
        "docs/runbooks",
        "docs/trds",
        "forge-standards",
        "scripts",
        "scripts/ci",
        "scripts/dev",
        "scripts/setup",
        "src",
        "src/forge",
        "src/forge/agents",
        "src/forge/config",
        "src/forge/consensus",
        "src/forge/contracts",
        "src/forge/document_store",
        "src/forge/errors",
        "src/forge/github_integration",
        "src/forge/pipeline",
        "src/forge/recovery",
        "src/forge/review",
        "src/forge/utils",
        "state",
        "tests",
        "tests/e2e",
        "tests/fixtures",
        "tests/integration",
        "tests/unit",
    ])


@pytest.fixture(scope="session")
def required_python_packages() -> list:
    """Return the list of directories that must contain __init__.py.

    These are Python package directories that require an __init__.py
    to be valid importable packages.

    Returns:
        list[str]: Sorted list of Python package directory relative paths.
    """
    return sorted([
        "src",
        "src/forge",
        "src/forge/agents",
        "src/forge/config",
        "src/forge/consensus",
        "src/forge/contracts",
        "src/forge/document_store",
        "src/forge/errors",
        "src/forge/github_integration",
        "src/forge/pipeline",
        "src/forge/recovery",
        "src/forge/review",
        "src/forge/utils",
    ])


@pytest.fixture(scope="session")
def required_documents() -> list:
    """Return the list of canonical documents that must exist and be non-empty.

    Each entry is a dict with 'path' (relative to repo root) and 'description'.

    Returns:
        list[dict]: List of document descriptors.
    """
    return [
        {
            "path": "VERSION",
            "description": "Canonical version file (single source of truth)",
        },
        {
            "path": "docs/VERSIONING.md",
            "description": "Versioning contract specification",
        },
        {
            "path": "docs/CONFLICT_RESOLUTION.md",
            "description": "Cross-TRD conflict resolution hierarchy",
        },
        {
            "path": "docs/NAMING_CONVENTIONS.md",
            "description": "Naming conventions guide",
        },
        {
            "path": "docs/PRODUCT_IDENTITY.md",
            "description": "Product identity and branding rules",
        },
    ]


@pytest.fixture(scope="session")
def allowed_top_level_entries() -> set:
    """Return the set of allowed top-level entries in the repository root.

    Includes both directories and files that are expected at the top level.
    Anything not in this set is flagged as unexpected by the allowlist test.

    Returns:
        set[str]: Set of allowed top-level entry names.
    """
    return {
        # Directories from the skeleton
        ".git",
        ".github",
        "ForgeApp",
        "artifacts",
        "config",
        "contracts",
        "docs",
        "forge-docs",
        "forge-standards",
        "scripts",
        "src",
        "state",
        "tests",
        # Root-level files
        ".gitignore",
        "VERSION",
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "AGENTS.md",
        "CLAUDE.md",
        "pyproject.toml",
        # Common tooling files that may appear
        ".python-version",
        ".env.example",
        "requirements.txt",
        "setup.py",
        "setup.cfg",
        "Makefile",
        "Dockerfile",
        "docker-compose.yml",
        ".dockerignore",
        ".pre-commit-config.yaml",
        ".flake8",
        ".ruff.toml",
        "ruff.toml",
        "mypy.ini",
        ".mypy.ini",
        "tox.ini",
        "noxfile.py",
        "conftest.py",
        "pytest.ini",
        # Hidden directories from tooling
        ".venv",
        ".vscode",
        ".idea",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".cache",
        ".eggs",
        "__pycache__",
        # Build/dist artifacts (gitignored but may exist locally)
        "build",
        "dist",
        "*.egg-info",
    }

tests/test_repo_structure/test_directory_completeness.py:
# Copyright 2026 YouSource.ai -- Consensus Dev Agent
# SPDX-License-Identifier: PROPRIETARY
"""Tests for repository directory completeness.

Validates that every required directory from the PR 1-4 skeleton exists,
every Python package has __init__.py, and no unexpected top-level
directories have appeared.

Security assumptions:
    - All operations are read-only filesystem checks.
    - No application code is imported or executed.

Failure behavior:
    - Each failing assertion includes the specific path and violated rule
      to make CI failures actionable.
"""

from pathlib import Path


def test_required_directories_exist(repo_root: Path, required_directories: list) -> None:
    """Every required directory from the skeleton MUST exist.

    Iterates through all directories defined in the required_directories
    fixture and asserts each one exists as a directory.
    """
    missing = []
    for rel_dir in required_directories:
        dir_path = repo_root / rel_dir
        if not dir_path.is_dir():
            missing.append(rel_dir)

    assert not missing, (
        f"Required directories missing from repository skeleton:\n"
        + "\n".join(f"  - {d}/" for d in missing)
        + f"\n\nRepository root: {repo_root}"
        + "\nThese directories are required by PRs 1-4 and PRD-001."
    )


def test_python_packages_have_init(repo_root: Path, required_python_packages: list) -> None:
    """Every Python package directory MUST contain __init__.py.

    Without __init__.py, Python cannot import from these directories,
    breaking the package structure.
    """
    missing_init = []
    for pkg_dir in required_python_packages:
        init_path = repo_root / pkg_dir / "__init__.py"
        if not init_path.is_file():
            missing_init.append(pkg_dir)

    assert not missing_init, (
        f"Python package directories missing __init__.py:\n"
        + "\n".join(f"  - {d}/__init__.py" for d in missing_init)
        + f"\n\nRepository root: {repo_root}"
        + "\nEvery Python package directory must contain __init__.py."
    )


def test_no_unexpected_top_level_directories(
    repo_root: Path, allowed_top_level_entries: set
) -> None:
    """No unexpected top-level directories should exist.

    This is an allowlist check. Directories at the repository root that
    are not in the allowed set are flagged. This prevents uncontrolled
    growth of the top-level namespace.

    Note: This test logs warnings for unexpected entries but does not fail
    for hidden directories (prefixed with .) that are common tooling artifacts,
    or for entries matching common build artifact patterns.
    """
    unexpected = []
    for entry in sorted(repo_root.iterdir()):
        name = entry.name
        if name in allowed_top_level_entries:
            continue
        # Allow entries that match wildcard patterns in the allowlist
        # (e.g., *.egg-info)
        if name.endswith(".egg-info"):
            continue
        # Hidden files/dirs not in allowlist are still flagged
        unexpected.append(name)

    assert not unexpected, (
        f"Unexpected top-level entries found in repository root:\n"
        + "\n".join(f"  - {e}" for e in unexpected)
        + f"\n\nRepository root: {repo_root}"
        + "\nIf these are intentional, add them to the allowed_top_level_entries "
        + "fixture in conftest.py."
    )


def test_nested_package_dirs_have_init(repo_root: Path) -> None:
    """All directories under src/ containing .py files MUST have __init__.py.

    This is a dynamic discovery check that catches Python package directories
    added after the initial skeleton that lack __init__.py.
    """
    src_dir = repo_root / "src"
    if not src_dir.is_dir():
        # src/ absence is caught by test_required_directories_exist
        return

    missing_init = []
    for dir_path in sorted(src_dir.rglob("*")):
        if not dir_path.is_dir():
            continue
        # Skip __pycache__ and hidden directories
        if "__pycache__" in dir_path.parts or any(
            part.startswith(".") for part in dir_path.relative_to(repo_root).parts
        ):
            continue
        # Check if this directory contains any .py files (other than __init__.py)
        py_files = [
            f for f in dir_path.iterdir()
            if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"
        ]
        # Also check if it has subdirectories with .py files (making it a namespace)
        has_py_subdirs = any(
            (sub / "__init__.py").is_file()
            for sub in dir_path.iterdir()
            if sub.is_dir()
        )
        if (py_files or has_py_subdirs) and not (dir_path / "__init__.py").is_file():
            rel_path = dir_path.relative_to(repo_root)
            missing_init.append(str(rel_path))

    assert not missing_init, (
        f"Directories under src/ contain Python files but lack __init__.py:\n"
        + "\n".join(f"  - {d}/" for d in missing_init)
        + f"\n\nRepository root: {repo_root}"
        + "\nAll Python package directories must contain __init__.py."
    )

tests/test_repo_structure/test_naming_conventions.py:
# Copyright 2026 YouSource.ai -- Consensus Dev Agent
# SPDX-License-Identifier: PROPRIETARY
"""Tests for naming convention compliance.

Validates that all Python files use snake_case names, directories follow
naming patterns, and no violations of the naming rules defined in
NAMING_CONVENTIONS.md exist.

Security assumptions:
    - All operations are read-only filesystem checks.
    - No application code is imported or executed.

Failure behavior:
    - Each failing assertion includes the offending path/name and the
      specific violated rule to ensure actionable CI failure messages.
"""

import re
from pathlib import Path
from typing import List

# Pattern for valid snake_case names:
# - Starts with a lowercase letter
# - Contains only lowercase letters, digits, and underscores
# - Does not start or end with underscore (except dunder names handled separately)
_SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# Directories to exclude from naming checks (not Python packages, or follow
# different conventions by design)
_EXCLUDED_DIRS = {
    ".git",
    ".github",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".eggs",
    ".cache",
    "node_modules",
    ".idea",
    ".vscode",
    "ForgeApp",  # Swift -- PascalCase by convention
    "ForgeAgent",
    "ForgeAgentTests",
    "DerivedData",
    ".build",
    "build",
    "dist",
}

# File names to exclude from snake_case checks
_EXCLUDED_FILES = {
    "__init__.py",
    "__main__.py",
    "conftest.py",
    "setup.py",
    "noxfile.py",
    "Makefile",
    "Dockerfile",
}


def _is_snake_case(name: str) -> bool:
    """Check if a name follows snake_case convention.

    A valid snake_case name:
    - Starts with a lowercase letter
    - Contains only lowercase letters, digits, and underscores
    - Is not empty

    Args:
        name: The name to validate (without file extension).

    Returns:
        True if the name is valid snake_case, False otherwise.

    Examples:
        >>> _is_snake_case("build_director")
        True
        >>> _is_snake_case("test_consensus")
        True
        >>> _is_snake_case("a")
        True
        >>> _is_snake_case("BuildDirector")
        False
        >>> _is_snake_case("build-director")
        False
        >>> _is_snake_case("")
        False
    """
    if not name:
        return False
    return bool(_SNAKE_CASE_PATTERN.match(name))


def _collect_python_files(root: Path) -> List[Path]:
    """Collect all Python files under root, excluding known non-Python areas.

    Walks the directory tree starting from root, collecting all .py files
    while skipping directories that are known to follow different conventions
    (Swift, hidden dirs, caches, etc.).

    Args:
        root: The root directory to search from.

    Returns:
        Sorted list of Path objects for all discovered .py files.
    """
    py_files = []
    for path in sorted(root.rglob("*.py")):
        # Skip if any parent directory is in the exclusion set
        parts = path.relative_to(root).parts
        if any(part in _EXCLUDED_DIRS for part in parts):
            continue
        # Skip if inside a hidden directory
        if any(part.startswith(".") and part not in {".github"} for part in parts):
            continue
        py_files.append(path)
    return py_files


def _collect_directories(root: Path, exclude: set) -> List[Path]:
    """Collect all directories under root, excluding specified names.

    Args:
        root: The root directory to search from.
        exclude: Set of directory names to skip.

    Returns:
        Sorted list of Path objects for all discovered directories.
    """
    dirs = []
    for path in sorted(root.rglob("*")):
        if not path.is_dir():
            continue
        parts = path.relative_to(root).parts
        if any(part in exclude for part in parts):
            continue
        # Skip hidden directories
        if any(part.startswith(".") and part not in {".github"} for part in parts):
            continue
        dirs.append(path)
    return dirs


def test_python_files_are_snake_case(repo_root: Path) -> None:
    """All Python files in src/ MUST have snake_case names.

    Validates that every .py file under the src/ directory follows the
    snake_case naming convention. Excludes __init__.py, __main__.py,
    and other special Python files.
    """
    src_dir = repo_root / "src"
    if not src_dir.is_dir():
        return

    violations = []
    for py_file in _collect_python_files(src_dir):
        stem = py_file.stem
        if py_file.name in _EXCLUDED_FILES:
            continue
        # Allow dunder names like __init__, __main__
        if stem.startswith("__") and stem.endswith("__"):
            continue
        if not _is_snake_case(stem):
            rel_path = py_file.relative_to(repo_root)
            violations.append(
                f"  - {rel_path} (stem '{stem}' is not snake_case)"
            )

    assert not violations, (
        f"Python files in src/ with non-snake_case names:\n"
        + "\n".join(violations)
        + "\n\nAll Python module files must use snake_case naming "
        + "(e.g., build_director.py, not BuildDirector.py)."
    )


def test_directories_are_snake_case(repo_root: Path) -> None:
    """All directories in src/ MUST have snake_case names.

    Python package directories must be valid Python identifiers,
    which means snake_case.
    """
    src_dir = repo_root / "src"
    if not src_dir.is_dir():
        return

    violations = []
    for dir_path in _collect_directories(src_dir, _EXCLUDED_DIRS):
        name = dir_path.name
        # Skip __pycache__
        if name == "__pycache__":
            continue
        if not _is_snake_case(name):
            rel_path = dir_path.relative_to(repo_root)
            violations.append(
                f"  - {rel_path}/ (name '{name}' is not snake_case)"
            )

    assert not violations, (
        f"Directories in src/ with non-snake_case names:\n"
        + "\n".join(violations)
        + "\n\nAll Python package directories must use snake_case naming "
        + "(e.g., document_store/, not DocumentStore/)."
    )


def test_no_camel_case_python_modules(repo_root: Path) -> None:
    """No Python files in src/ should use camelCase or PascalCase names.

    This is a specific check for the most common naming violation pattern.
    """
    camel_case_pattern = re.compile(r"[a-z][A-Z]")
    pascal_case_pattern = re.compile(r"^[A-Z][a-z]")

    src_dir = repo_root / "src"
    if not src_dir.is_dir():
        return

    violations = []
    for py_file in _collect_python_files(src_dir):
        stem = py_file.stem
        if py_file.name in _EXCLUDED_FILES:
            continue
        if stem.startswith("__") and stem.endswith("__"):
            continue
        if camel_case_pattern.search(stem) or pascal_case_pattern.match(stem):
            rel_path = py_file.relative_to(repo_root)
            violations.append(
                f"  - {rel_path} (stem '{stem}' contains camelCase/PascalCase)"
            )

    assert not violations, (
        f"Python files in src/ with camelCase/PascalCase names:\n"
        + "\n".join(violations)
        + "\n\nPython modules must use snake_case, not camelCase or PascalCase."
    )


def test_no_hyphenated_python_modules(repo_root: Path) -> None:
    """No Python files in src/ should use hyphenated names.

    Hyphens are not valid in Python identifiers and prevent importing
    the module by name.
    """
    src_dir = repo_root / "src"
    if not src_dir.is_dir():
        return

    violations = []
    for py_file in _collect_python_files(src_dir):
        stem = py_file.stem
        if py_file.name in _EXCLUDED_FILES:
            continue
        if "-" in stem:
            rel_path = py_file.relative_to(repo_root)
            violations.append(
                f"  - {rel_path} (stem '{stem}' contains hyphens)"
            )

    assert not violations, (
        f"Python files in src/ with hyphenated names:\n"
        + "\n".join(violations)
        + "\n\nPython modules must use underscores, not hyphens "
        + "(e.g., build_director.py, not build-director.py)."
    )


def test_test_files_follow_test_prefix_convention(repo_root: Path) -> None:
    """Test files in tests/ MUST follow the test_ prefix convention.

    pytest discovers test files by the test_ prefix. Files that appear
    to be tests but lack the prefix will not be discovered.
    """
    tests_dir = repo_root / "tests"
    if not tests_dir.is_dir():
        return

    violations = []
    for py_file in _collect_python_files(tests_dir):
        name = py_file.name
        # Skip known non-test files
        if name in _EXCLUDED_FILES or name == "conftest.py":
            continue
        # Skip __init__.py and dunder files
        if name.startswith("__"):
            continue
        # All other .py files in tests/ should start with test_
        if not name.startswith("test_"):
            rel_path = py_file.relative_to(repo_root)
            violations.append(
                f"  - {rel_path} (file name '{name}' does not start with 'test_')"
            )

    assert not violations, (
        f"Python files in tests/ that don't follow test_ prefix convention:\n"
        + "\n".join(violations)
        + "\n\nAll test files must use the test_ prefix for pytest discovery "
        + "(e.g., test_build_director.py, not build_director_test.py)."
    )


# =============================================================================
# Unit tests for the _is_snake_case helper
# =============================================================================


def test_is_snake_case_rejects_camelCase() -> None:
    """_is_snake_case must reject camelCase names."""
    assert not _is_snake_case("buildDirector"), (
        "_is_snake_case should reject 'buildDirector' (camelCase)"
    )
    assert not _is_snake_case("myVariable"), (
        "_is_snake_case should reject 'myVariable' (camelCase)"
    )
    assert not _is_snake_case("consensusEngine"), (
        "_is_snake_case should reject 'consensusEngine' (camelCase)"
    )


def test_is_snake_case_rejects_hyphenated() -> None:
    """_is_snake_case must reject hyphenated names."""
    assert not _is_snake_case("build-director"), (
        "_is_snake_case should reject 'build-director' (hyphenated)"
    )
    assert not _is_snake_case("my-module"), (
        "_is_snake_case should reject 'my-module' (hyphenated)"
    )
    assert not _is_snake_case("forge-utils"), (
        "_is_snake_case should reject 'forge-utils' (hyphenated)"
    )


def test_is_snake_case_rejects_leading_uppercase() -> None:
    """_is_snake_case must reject PascalCase / leading uppercase names."""
    assert not _is_snake_case("BuildDirector"), (
        "_is_snake_case should reject 'BuildDirector' (PascalCase)"
    )
    assert not _is_snake_case("Consensus"), (
        "_is_snake_case should reject 'Consensus' (leading uppercase)"
    )
    assert not _is_snake_case("MyModule"), (
        "_is_snake_case should reject 'MyModule' (PascalCase)"
    )


def test_is_snake_case_rejects_spaces() -> None:
    """_is_snake_case must reject names containing spaces."""
    assert not _is_snake_case("build director"), (
        "_is_snake_case should reject 'build director' (contains space)"
    )
    assert not _is_snake_case(" leading"), (
        "_is_snake_case should reject ' leading' (leading space)"
    )
    assert not _is_snake_case("trailing "), (
        "_is_snake_case should reject 'trailing ' (trailing space)"
    )


def test_is_snake_case_accepts_valid_names() -> None:
    """_is_snake_case must accept valid snake_case names."""
    valid_names = [
        "build_director",
        "consensus",
        "test_something",
        "a",
        "x1",
        "my_module_v2",
        "forge",
        "validate_structure",
    ]
    for name in valid_names:
        assert _is_snake_case(name), (
            f"_is_snake_case should accept '{name}' as valid snake_case"
        )


def test_is_snake_case_rejects_empty_string() -> None:
    """_is_snake_case must reject empty strings."""
    assert not _is_snake_case(""), (
        "_is_snake_case should reject empty string"
    )


def test_is_snake_case_rejects_digit_start() -> None:
    """_is_snake_case must reject names starting with a digit."""
    assert not _is_snake_case("1module"), (
        "_is_snake_case should reject '1module' (starts with digit)"
    )
    assert not _is_snake_case("2nd_attempt"), (
        "_is_snake_case should reject '2nd_attempt' (starts with digit)"
    )

tests/test_repo_structure/test_validate_structure.py:
# Copyright 2026 YouSource.ai -- Consensus Dev Agent
# SPDX-License-Identifier: PROPRIETARY
"""Integration tests for the validate_structure.py script.

Tests that the validation script passes on the current repository,
and correctly detects synthetically introduced structural violations.

Security assumptions:
    - subprocess.run is called with shell=False (never shell=True).
    - No user-supplied input is passed to subprocess arguments.
    - Temporary directories are managed by pytest's tmp_path fixture.

Failure behavior:
    - Tests that depend on validate_structure.py existing are skipped
      if the script is not found.
    - All subprocess failures capture stdout/stderr for debugging.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Path to the validate_structure.py script relative to repo root
_SCRIPT_REL_PATH = "scripts/validate_structure.py"


def _get_script_path(repo_root: Path) -> Path:
    """Get the absolute path to validate_structure.py.

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        Path to the validation script.
    """
    return repo_root / _SCRIPT_REL_PATH


def _script_exists(repo_root: Path) -> bool:
    """Check if validate_structure.py exists.

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        True if the script exists, False otherwise.
    """
    return _get_script_path(repo_root).is_file()


def _run_validator(
    repo_root: Path,
    *,
    working_dir: Path = None,
    extra_args: list = None,
    env_override: dict = None,
) -> subprocess.CompletedProcess:
    """Run validate_structure.py safely via subprocess.

    Uses shell=False (security: no shell injection possible).
    Captures stdout and stderr for assertion inspection.

    Args:
        repo_root: Absolute path to the repository root (for locating script).
        working_dir: Working directory for the subprocess. Defaults to repo_root.
        extra_args: Additional command-line arguments to pass to the script.
        env_override: Optional environment variable overrides.

    Returns:
        CompletedProcess with captured stdout and stderr.

    Security note:
        - shell=False prevents shell injection
        - All arguments are Python strings, not user input
        - Environment is inherited from the parent process with optional overrides
    """
    script_path = _get_script_path(repo_root)
    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    # Disable color output for deterministic test assertions
    env["NO_COLOR"] = "1"
    if env_override:
        env.update(env_override)

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(working_dir or repo_root),
        env=env,
        timeout=30,  # Fail fast if script hangs
    )


def _create_minimal_repo_copy(repo_root: Path, dest: Path) -> Path:
    """Create a minimal copy of the repository structure for testing.

    Copies the .git marker (as a file, not the full git database),
    the validate_structure.py script, and creates all canonical directories
    and files. This provides a controlled environment for mutation testing.

    Args:
        repo_root
