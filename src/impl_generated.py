"""Package initialization for the crafted_dev_agent scaffold utilities.

Security assumptions:
- This module performs local filesystem writes only under a caller-supplied base path.
- All paths are resolved relative to the provided base path and created explicitly.
- Invalid inputs raise exceptions rather than being silently coerced.

Failure behavior:
- Filesystem and validation errors are not swallowed.
- Callers receive explicit exceptions with context so failures are visible and fail closed.
"""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0"


def create_scaffold(base_path: str = ".") -> None:
    """Create the repository scaffold with required directories and files.

    Args:
        base_path: Root path under which the scaffold will be created.

    Raises:
        TypeError: If base_path is not a string.
        ValueError: If base_path is empty or whitespace only.
        OSError: If filesystem operations fail.
    """
    if not isinstance(base_path, str):
        raise TypeError("base_path must be a string")
    if not base_path.strip():
        raise ValueError("base_path must not be empty")

    base = Path(base_path).resolve()

    directories = [
        "src",
        "src/crafted_dev_agent",
        "src/crafted_dev_agent/agents",
        "src/crafted_dev_agent/tools",
        "src/crafted_dev_agent/utils",
        "tests",
        "tests/unit",
        "tests/integration",
        "docs",
        "config",
        ".github",
        ".github/workflows",
    ]

    init_files = [
        "src/__init__.py",
        "src/crafted_dev_agent/__init__.py",
        "src/crafted_dev_agent/agents/__init__.py",
        "src/crafted_dev_agent/tools/__init__.py",
        "src/crafted_dev_agent/utils/__init__.py",
        "tests/__init__.py",
        "tests/unit/__init__.py",
        "tests/integration/__init__.py",
    ]

    gitkeep_dirs = [
        "docs",
        "config",
        ".github/workflows",
    ]

    for directory in directories:
        dir_path = base / directory
        dir_path.mkdir(parents=True, exist_ok=True)

    for init_file in init_files:
        file_path = base / init_file
        if not file_path.exists():
            file_path.write_text('"""Package."""\n', encoding="utf-8")

    for gitkeep_dir in gitkeep_dirs:
        gitkeep_path = base / gitkeep_dir / ".gitkeep"
        if not gitkeep_path.exists():
            gitkeep_path.write_text("", encoding="utf-8")


def get_scaffold_paths() -> dict[str, list[str]]:
    """Return the expected scaffold layout.

    Returns:
        A mapping containing directories, init_files, and gitkeep_files.
    """
    return {
        "directories": [
            "src",
            "src/crafted_dev_agent",
            "src/crafted_dev_agent/agents",
            "src/crafted_dev_agent/tools",
            "src/crafted_dev_agent/utils",
            "tests",
            "tests/unit",
            "tests/integration",
            "docs",
            "config",
            ".github",
            ".github/workflows",
        ],
        "init_files": [
            "src/__init__.py",
            "src/crafted_dev_agent/__init__.py",
            "src/crafted_dev_agent/agents/__init__.py",
            "src/crafted_dev_agent/tools/__init__.py",
            "src/crafted_dev_agent/utils/__init__.py",
            "tests/__init__.py",
            "tests/unit/__init__.py",
            "tests/integration/__init__.py",
        ],
        "gitkeep_files": [
            "docs/.gitkeep",
            "config/.gitkeep",
            ".github/workflows/.gitkeep",
        ],
    }