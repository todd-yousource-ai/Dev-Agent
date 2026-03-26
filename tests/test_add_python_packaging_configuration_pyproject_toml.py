"""Tests for Python packaging configuration (pyproject.toml, requirements.txt, conftest.py)."""

import ast
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

# Resolve project root by walking up from this file until we find pyproject.toml
PROJECT_ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists()
)


@pytest.fixture
def pyproject_data():
    """Parse and return pyproject.toml data."""
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)


@pytest.fixture
def requirements_lines():
    """Return non-blank, non-comment lines from requirements.txt."""
    req_path = PROJECT_ROOT / "requirements.txt"
    text = req_path.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


# =============================================================================
# pyproject.toml tests
# =============================================================================


class TestPyprojectToml:
    def test_pyproject_toml_is_valid_toml(self, pyproject_data):
        """Parse with tomllib, assert no exception."""
        assert isinstance(pyproject_data, dict)

    def test_pyproject_project_name_is_crafted_dev_agent(self, pyproject_data):
        """Assert project.name equals 'crafted-dev-agent'."""
        assert pyproject_data["project"]["name"] == "crafted-dev-agent"

    def test_pyproject_version_is_38_153_0(self, pyproject_data):
        """Assert project.version equals '38.153.0'."""
        assert pyproject_data["project"]["version"] == "38.153.0"

    def test_pyproject_requires_python_gte_312(self, pyproject_data):
        """Assert requires-python contains '>= 3.12' or '>=3.12'."""
        requires_python = pyproject_data["project"]["requires-python"]
        # Normalize spaces for comparison
        normalized = requires_python.replace(" ", "")
        assert ">=3.12" in normalized

    def test_pyproject_build_system_is_setuptools(self, pyproject_data):
        """Assert build-system.build-backend equals 'setuptools.build_meta'."""
        assert (
            pyproject_data["build-system"]["build-backend"] == "setuptools.build_meta"
        )

    def test_pyproject_pytest_testpaths_includes_tests(self, pyproject_data):
        """Assert tool.pytest.ini_options.testpaths contains 'tests'."""
        testpaths = pyproject_data["tool"]["pytest"]["ini_options"]["testpaths"]
        if isinstance(testpaths, list):
            assert "tests" in testpaths
        else:
            assert "tests" in str(testpaths)

    def test_pyproject_ruff_target_version_is_py312(self, pyproject_data):
        """Assert tool.ruff.target-version equals 'py312'."""
        assert pyproject_data["tool"]["ruff"]["target-version"] == "py312"

    def test_pyproject_ruff_line_length_is_100(self, pyproject_data):
        """Assert tool.ruff.line-length equals 100."""
        assert pyproject_data["tool"]["ruff"]["line-length"] == 100

    def test_pyproject_no_unknown_top_level_keys(self, pyproject_data):
        """Parse TOML and assert only standard PEP 621 and tool keys exist."""
        # Standard top-level keys per PEP 621 and PEP 518
        allowed_top_level_keys = {
            "build-system",
            "project",
            "tool",
            # PEP 621 also allows these less common ones
            "dependency-groups",
        }
        actual_keys = set(pyproject_data.keys())
        unknown_keys = actual_keys - allowed_top_level_keys
        assert not unknown_keys, f"Unknown top-level keys in pyproject.toml: {unknown_keys}"


# =============================================================================
# requirements.txt tests
# =============================================================================


class TestRequirementsTxt:
    def test_requirements_txt_exists_and_nonempty(self):
        """Assert file exists and has > 0 lines."""
        req_path = PROJECT_ROOT / "requirements.txt"
        assert req_path.exists(), "requirements.txt does not exist"
        content = req_path.read_text(encoding="utf-8").strip()
        assert len(content) > 0, "requirements.txt is empty"
        # Count non-blank lines
        non_blank = [l for l in content.splitlines() if l.strip()]
        assert len(non_blank) > 0, "requirements.txt has no non-blank lines"

    def test_requirements_txt_contains_all_trd_dependencies(self, requirements_lines):
        """Check each of the 11 package names appears."""
        # Extract package names (before any version specifier)
        import re

        pkg_names = set()
        for line in requirements_lines:
            # Package name is everything before the first version specifier
            match = re.match(r"^([a-zA-Z0-9_\-\.]+)", line)
            if match:
                pkg_names.add(match.group(1).lower().replace("-", "_").replace(".", "_"))

        # The 11 expected TRD dependencies -- we normalize names for comparison
        expected_packages = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "httpx",
            "sqlalchemy",
            "alembic",
            "celery",
            "redis",
            "structlog",
            "tenacity",
            "cryptography",
        ]

        for pkg in expected_packages:
            normalized = pkg.lower().replace("-", "_").replace(".", "_")
            assert normalized in pkg_names, (
                f"Expected package '{pkg}' not found in requirements.txt. "
                f"Found: {sorted(pkg_names)}"
            )

    def test_requirements_txt_all_lines_have_version_constraint(self, requirements_lines):
        """Every non-blank non-comment line contains >=, ==, or ~=."""
        import re

        for line in requirements_lines:
            assert re.search(r"(>=|==|~=|<=|!=|>|<)", line), (
                f"Line missing version constraint: '{line}'"
            )

    def test_requirements_txt_no_duplicate_packages(self, requirements_lines):
        """Assert each package name appears exactly once."""
        import re

        pkg_names = []
        for line in requirements_lines:
            match = re.match(r"^([a-zA-Z0-9_\-\.]+)", line)
            if match:
                pkg_names.append(match.group(1).lower().replace("-", "_").replace(".", "_"))

        seen = set()
        duplicates = set()
        for name in pkg_names:
            if name in seen:
                duplicates.add(name)
            seen.add(name)

        assert not duplicates, f"Duplicate packages in requirements.txt: {duplicates}"

    def test_requirements_txt_no_unpinned_dependencies(self, requirements_lines):
        """Assert no line contains a bare package name without a version specifier."""
        import re

        for line in requirements_lines:
            # A bare package name would be just letters/digits/hyphens/underscores/dots
            # with no version specifier following
            assert re.search(r"(>=|==|~=|<=|!=|>|<)", line), (
                f"Unpinned dependency found: '{line}'"
            )


# =============================================================================
# conftest.py tests
# =============================================================================


class TestConftest:
    def test_conftest_exists_at_repo_root(self):
        """Assert conftest.py exists at the repo root."""
        conftest_path = PROJECT_ROOT / "conftest.py"
        assert conftest_path.exists(), (
            f"conftest.py not found at {conftest_path}"
        )

    def test_conftest_is_importable(self):
        """Import conftest module without error."""
        conftest_path = PROJECT_ROOT / "conftest.py"
        assert conftest_path.exists()

        # Use importlib to import from path
        spec = importlib.util.spec_from_file_location("conftest", str(conftest_path))
        assert spec is not None, "Could not create module spec for conftest.py"
        module = importlib.util.module_from_spec(spec)
        # This should not raise
        spec.loader.exec_module(module)
        assert module is not None

    def test_conftest_no_side_effects(self):
        """Verify conftest.py performs no environment mutation, network access,
        or secret-loading during pytest startup.

        Static analysis: no os.environ writes, no socket/http imports,
        no open() calls on sensitive paths.
        """
        conftest_path = PROJECT_ROOT / "conftest.py"
        assert conftest_path.exists()

        source = conftest_path.read_text(encoding="utf-8")

        # Parse the AST
        tree = ast.parse(source, filename="conftest.py")

        dangerous_imports = {"socket", "http", "urllib", "requests", "httpx", "aiohttp"}
        sensitive_patterns = {
            "os.environ",
            ".env",
            "/etc/passwd",
            "/etc/shadow",
            "secrets",
        }

        issues = []

        for node in ast.walk(tree):
            # Check for dangerous imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base_module = alias.name.split(".")[0]
                    if base_module in dangerous_imports:
                        issues.append(
                            f"Dangerous import found: 'import {alias.name}' at line {node.lineno}"
                        )

            if isinstance(node, ast.ImportFrom):
                if node.module:
                    base_module = node.module.split(".")[0]
                    if base_module in dangerous_imports:
                        issues.append(
                            f"Dangerous import found: 'from {node.module}' at line {node.lineno}"
                        )

            # Check for os.environ assignments (subscript assignment)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript):
                        if isinstance(target.value, ast.Attribute):
                            attr_src = ast.dump(target.value)
                            if "environ" in attr_src:
                                issues.append(
                                    f"os.environ write detected at line {node.lineno}"
                                )

            # Check for string literals containing sensitive paths
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for pattern in sensitive_patterns:
                    if pattern in node.value:
                        # Allow benign references (e.g., comments or documentation)
                        # but flag actual usage in open() calls etc.
                        pass  # We'll check open() calls separately

            # Check for open() calls on sensitive paths
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name == "open" and node.args:
                    first_arg = node.args[0]
                    if isinstance(first_arg, ast.Constant) and isinstance(
                        first_arg.value, str
                    ):
                        for pattern in [
                            "/etc/passwd",
                            "/etc/shadow",
                            ".env",
                            "secrets",
                        ]:
                            if pattern in first_arg.value:
                                issues.append(
                                    f"Sensitive file access: open('{first_arg.value}') "
                                    f"at line {node.lineno}"
                                )

        assert not issues, (
            f"conftest.py has side effects or security concerns:\n"
            + "\n".join(f"  - {issue}" for issue in issues)
        )


# =============================================================================
# Pytest collection test
# =============================================================================


class TestPytestCollection:
    def test_pytest_collection_succeeds_without_src_directory(self):
        """pytest collection completes successfully when no src/ directory exists."""
        # Run pytest --collect-only to verify collection works
        # This tests that the configuration doesn't hard-depend on src/ existing
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        # pytest --collect-only returns 0 if collection succeeds (even with 0 tests from src/)
        # It may return 5 if no tests are found, which is also acceptable
        # It should NOT return 1 or 2 (errors/interrupts)
        assert result.returncode in (0, 5), (
            f"pytest collection failed with return code {result.returncode}.\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
