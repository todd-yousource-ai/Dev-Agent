import os
import pathlib

import pytest

# Resolve the repository root (assumes tests/ is one level below root)
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestVersionFile:
    """Tests for the VERSION sentinel file."""

    def test_version_file_exists_and_contains_38_153_0(self):
        version_path = REPO_ROOT / "VERSION"
        assert version_path.exists(), "VERSION file must exist at repo root"
        content = version_path.read_text(encoding="utf-8").strip()
        assert content == "38.153.0", f"Expected '38.153.0', got '{content}'"

    def test_version_file_has_exactly_one_line(self):
        version_path = REPO_ROOT / "VERSION"
        lines = version_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1, f"VERSION must have exactly 1 line, got {len(lines)}"

    def test_version_file_does_not_contain_trailing_whitespace_beyond_newline(self):
        version_path = REPO_ROOT / "VERSION"
        raw = version_path.read_text(encoding="utf-8")
        # The file should be either "38.153.0" or "38.153.0\n" -- no other whitespace
        assert raw in ("38.153.0", "38.153.0\n"), (
            f"VERSION contains unexpected trailing whitespace: {raw!r}"
        )


class TestLicenseFile:
    """Tests for the LICENSE file."""

    def test_license_file_exists_and_is_nonempty(self):
        license_path = REPO_ROOT / "LICENSE"
        assert license_path.exists(), "LICENSE file must exist at repo root"
        content = license_path.read_text(encoding="utf-8")
        assert len(content.strip()) > 0, "LICENSE file must not be empty"


class TestGitignore:
    """Tests for the .gitignore file."""

    def test_gitignore_file_exists_and_is_nonempty(self):
        gitignore_path = REPO_ROOT / ".gitignore"
        assert gitignore_path.exists(), ".gitignore must exist at repo root"
        content = gitignore_path.read_text(encoding="utf-8")
        assert len(content.strip()) > 0, ".gitignore must not be empty"

    def _gitignore_lines(self):
        return (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    def test_gitignore_contains_pycache_pattern(self):
        lines = self._gitignore_lines()
        assert any("__pycache__" in line for line in lines), (
            "__pycache__ pattern missing from .gitignore"
        )

    def test_gitignore_contains_ds_store_pattern(self):
        lines = self._gitignore_lines()
        assert any(".DS_Store" in line for line in lines), (
            ".DS_Store pattern missing from .gitignore"
        )

    def test_gitignore_contains_deriveddata_pattern(self):
        lines = self._gitignore_lines()
        assert any("DerivedData" in line for line in lines), (
            "DerivedData pattern missing from .gitignore"
        )

    def test_gitignore_excludes_env_and_secrets_patterns(self):
        """Security: .gitignore must exclude .env, *.pem, and *.key files."""
        content = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        lines = content.splitlines()

        # Check for .env pattern
        assert any(
            line.strip() == ".env" or line.strip().startswith(".env") 
            for line in lines
        ), ".env pattern missing from .gitignore -- secrets may leak"

        # Check for *.pem pattern
        assert any("*.pem" in line for line in lines), (
            "*.pem pattern missing from .gitignore -- private keys may leak"
        )

        # Check for *.key pattern
        assert any("*.key" in line for line in lines), (
            "*.key pattern missing from .gitignore -- private keys may leak"
        )


class TestDirectorySkeleton:
    """Tests for the expected directory structure."""

    EXPECTED_DIRS = [
        "src",
        "tests",
        "docs",
        "infra",
        "scripts",
    ]

    def test_all_expected_directories_exist(self):
        for dirname in self.EXPECTED_DIRS:
            dirpath = REPO_ROOT / dirname
            assert dirpath.is_dir(), f"Expected directory '{dirname}/' to exist at repo root"

    def test_src_init_py_exists_and_is_empty(self):
        init_path = REPO_ROOT / "src" / "__init__.py"
        assert init_path.exists(), "src/__init__.py must exist"
        assert init_path.stat().st_size == 0, (
            f"src/__init__.py must be empty (0 bytes), got {init_path.stat().st_size}"
        )

    def test_tests_init_py_exists_and_is_empty(self):
        init_path = REPO_ROOT / "tests" / "__init__.py"
        assert init_path.exists(), "tests/__init__.py must exist"
        assert init_path.stat().st_size == 0, (
            f"tests/__init__.py must be empty (0 bytes), got {init_path.stat().st_size}"
        )

    def test_no_python_logic_in_init_files(self):
        """Assert all __init__.py files in the repo skeleton are exactly 0 bytes."""
        for init_file in REPO_ROOT.rglob("__init__.py"):
            # Only check files that are direct children of our skeleton dirs
            rel = init_file.relative_to(REPO_ROOT)
            # Skip anything inside hidden dirs or venvs
            parts = rel.parts
            if any(p.startswith(".") or p in ("venv", ".venv", "node_modules") for p in parts):
                continue
            assert init_file.stat().st_size == 0, (
                f"{rel} must be empty (0 bytes), got {init_file.stat().st_size} bytes"
            )

    def test_gitkeep_sentinels_exist_in_nonsrc_dirs(self):
        """Directories that don't have __init__.py should have .gitkeep."""
        nonsrc_dirs = ["docs", "infra", "scripts"]
        for dirname in nonsrc_dirs:
            gitkeep = REPO_ROOT / dirname / ".gitkeep"
            assert gitkeep.exists(), (
                f"{dirname}/.gitkeep must exist as a sentinel file"
            )

    def test_gitkeep_files_contain_no_nonwhitespace_content(self):
        """All .gitkeep files must be exactly zero bytes."""
        for gitkeep in REPO_ROOT.rglob(".gitkeep"):
            rel = gitkeep.relative_to(REPO_ROOT)
            parts = rel.parts
            if any(p.startswith(".") and p != ".gitkeep" for p in parts):
                continue
            assert gitkeep.stat().st_size == 0, (
                f"{rel} must be 0 bytes, got {gitkeep.stat().st_size}"
            )

    def test_no_unexpected_top_level_directories(self):
        """Only the canonical set of directories should exist at the repo root."""
        canonical = {
            "src", "tests", "docs", "infra", "scripts",
            # Common repo-level hidden dirs that are acceptable
            ".git", ".github", ".vscode", ".idea",
            # Build / env artifacts that might exist in CI
            "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
            "venv", ".venv", ".tox", "node_modules",
            # Egg-info or dist dirs
            "dist", "build",
        }
        actual_dirs = {
            entry.name
            for entry in REPO_ROOT.iterdir()
            if entry.is_dir()
        }
        unexpected = actual_dirs - canonical
        assert not unexpected, (
            f"Unexpected top-level directories found: {unexpected}. "
            f"Only these are allowed: {sorted(canonical & actual_dirs)}"
        )
