"""Tests for src/ Python package directory tree -- batch 1 (part 1/2)."""

import importlib
import inspect
import sys
from pathlib import Path

import pytest


def _find_project_root(start: Path) -> Path:
    """Find the project root by locating a valid pyproject.toml or falling back safely."""
    candidates = list(start.resolve().parents)

    valid_pyproject_found = None
    existing_pyproject_errors = []

    for p in candidates:
        pyproject = p / "pyproject.toml"
        if not pyproject.exists():
            continue
        try:
            text = pyproject.read_text(encoding="utf-8")
            # Validate TOML syntax in a lightweight way so malformed files do not
            # break test collection.
            if sys.version_info >= (3, 11):
                import tomllib

                tomllib.loads(text)
            else:
                try:
                    import tomli  # type: ignore
                except ModuleNotFoundError:
                    # Best-effort fallback for older Python when tomli is unavailable:
                    # accept the nearest existing pyproject.toml.
                    valid_pyproject_found = p
                    break
                tomli.loads(text)
            valid_pyproject_found = p
            break
        except Exception as exc:
            existing_pyproject_errors.append((pyproject, exc))

    if valid_pyproject_found is not None:
        return valid_pyproject_found

    # Fallback: prefer the nearest ancestor containing src/__init__.py
    for p in candidates:
        if (p / "src" / "__init__.py").is_file():
            return p

    # If no package root is found, surface the first pyproject parsing issue clearly.
    if existing_pyproject_errors:
        pyproject, exc = existing_pyproject_errors[0]
        raise RuntimeError(
            f"Found pyproject.toml but it is not valid TOML: {pyproject} ({exc})"
        ) from exc

    raise RuntimeError("Could not determine project root from test file location")


# Resolve project root robustly even if a parent pyproject.toml is malformed
PROJECT_ROOT = _find_project_root(Path(__file__))

# Ensure src/ is on sys.path so we can import the packages
SRC_DIR = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Packages expected to exist in this batch
EXPECTED_SUBPACKAGES = [
    "consensus",
    "build_pipeline",
    "github_integration",
    "document_store",
    "multi_agent",
    "holistic_review",
    "trd_workflow",
]

ALL_PACKAGES = ["src"] + [f"src.{sub}" for sub in EXPECTED_SUBPACKAGES]


class TestProjectRootResolution:
    """Tests covering robust project root discovery."""

    def test_project_root_contains_src_init(self):
        """Resolved project root should contain src/__init__.py."""
        assert PROJECT_ROOT.is_dir()
        assert (PROJECT_ROOT / "src" / "__init__.py").is_file()

    def test_nearest_invalid_pyproject_does_not_break_root_resolution(self, tmp_path):
        """A malformed nearer pyproject.toml should not prevent finding the real root."""
        real_root = tmp_path / "real_project"
        tests_dir = real_root / "tests"
        tests_dir.mkdir(parents=True)
        (real_root / "src").mkdir()
        (real_root / "src" / "__init__.py").write_text('"""src package."""\n', encoding="utf-8")
        (real_root / "pyproject.toml").write_text(
            "[project]\nname = 'demo'\nversion = '0.1.0'\n", encoding="utf-8"
        )

        nested = real_root / "nested" / "deeper"
        nested.mkdir(parents=True)
        (nested / "pyproject.toml").write_text("x y", encoding="utf-8")

        fake_test = nested / "test_file.py"
        fake_test.write_text("", encoding="utf-8")

        resolved = _find_project_root(fake_test)
        assert resolved == real_root

    def test_falls_back_to_src_init_when_no_valid_pyproject_exists(self, tmp_path):
        """If no valid pyproject.toml exists, src/__init__.py should anchor the root."""
        root = tmp_path / "repo"
        nested = root / "a" / "b" / "c"
        nested.mkdir(parents=True)
        (root / "src").mkdir()
        (root / "src" / "__init__.py").write_text('"""src package."""\n', encoding="utf-8")
        (root / "pyproject.toml").write_text("not = [valid", encoding="utf-8")

        fake_test = nested / "test_file.py"
        fake_test.write_text("", encoding="utf-8")

        resolved = _find_project_root(fake_test)
        assert resolved == root

    def test_invalid_pyproject_without_src_anchor_raises_clear_error(self, tmp_path):
        """A malformed pyproject.toml with no src anchor should raise a helpful error."""
        root = tmp_path / "repo"
        nested = root / "tests"
        nested.mkdir(parents=True)
        (root / "pyproject.toml").write_text("a b c", encoding="utf-8")
        fake_test = nested / "test_file.py"
        fake_test.write_text("", encoding="utf-8")

        with pytest.raises(RuntimeError, match="pyproject.toml.*not valid TOML"):
            _find_project_root(fake_test)


class TestImports:
    """Test that all expected packages can be imported."""

    def test_import_src_package(self):
        """``import src`` succeeds without error."""
        mod = importlib.import_module("src")
        assert mod is not None

    def test_import_consensus(self):
        """``import src.consensus`` succeeds."""
        mod = importlib.import_module("src.consensus")
        assert mod is not None

    def test_import_build_pipeline(self):
        """``import src.build_pipeline`` succeeds."""
        mod = importlib.import_module("src.build_pipeline")
        assert mod is not None

    def test_import_github_integration(self):
        """``import src.github_integration`` succeeds."""
        mod = importlib.import_module("src.github_integration")
        assert mod is not None

    def test_import_document_store(self):
        """``import src.document_store`` succeeds."""
        mod = importlib.import_module("src.document_store")
        assert mod is not None

    def test_import_multi_agent(self):
        """``import src.multi_agent`` succeeds."""
        mod = importlib.import_module("src.multi_agent")
        assert mod is not None

    def test_import_holistic_review(self):
        """``import src.holistic_review`` succeeds."""
        mod = importlib.import_module("src.holistic_review")
        assert mod is not None

    def test_import_trd_workflow(self):
        """``import src.trd_workflow`` succeeds."""
        mod = importlib.import_module("src.trd_workflow")
        assert mod is not None


class TestInitFilesExist:
    """Verify every expected __init__.py file exists on disk."""

    def test_all_init_files_exist(self):
        """Each expected ``__init__.py`` file exists at its path."""
        # src/__init__.py
        assert (SRC_DIR / "__init__.py").is_file(), "src/__init__.py missing"
        for sub in EXPECTED_SUBPACKAGES:
            init_path = SRC_DIR / sub / "__init__.py"
            assert init_path.is_file(), f"src/{sub}/__init__.py missing"

    def test_init_files_are_not_empty(self):
        """Each ``__init__.py`` file has > 0 bytes."""
        init_files = [SRC_DIR / "__init__.py"] + [
            SRC_DIR / sub / "__init__.py" for sub in EXPECTED_SUBPACKAGES
        ]
        for init_path in init_files:
            size = init_path.stat().st_size
            assert size > 0, f"{init_path} is empty (0 bytes)"


class TestDocstrings:
    """Verify each __init__.py has a non-empty docstring."""

    def test_all_init_files_have_docstring(self):
        """Each ``__init__.py`` has a non-empty ``__doc__``."""
        for pkg_name in ALL_PACKAGES:
            mod = importlib.import_module(pkg_name)
            assert mod.__doc__ is not None, f"{pkg_name} has no __doc__"
            assert (
                mod.__doc__.strip() != ""
            ), f"{pkg_name}.__doc__ is empty string"


class TestNoPublicSymbols:
    """Ensure init files define no public names beyond dunder attributes."""

    def test_no_init_files_define_symbols(self):
        """``dir()`` of each module contains no public names beyond dunder attributes."""
        for pkg_name in ALL_PACKAGES:
            mod = importlib.import_module(pkg_name)
            public_names = [
                name for name in dir(mod) if not name.startswith("_")
            ]
            assert public_names == [], (
                f"{pkg_name} exposes public symbols: {public_names}"
            )

    def test_no_runtime_attributes(self):
        """None of the packages expose classes, functions, or variables beyond dunder attrs."""
        for pkg_name in ALL_PACKAGES:
            mod = importlib.import_module(pkg_name)
            for name in dir(mod):
                if name.startswith("_"):
                    continue
                obj = getattr(mod, name)
                assert False, (
                    f"{pkg_name}.{name} is a {type(obj).__name__}; "
                    "no public attributes should exist"
                )


class TestNoImportStatements:
    """Ensure init files contain no import statements."""

    def test_init_contains_no_import_statements(self):
        """Reading each file's source confirms zero import statements."""
        init_files = [SRC_DIR / "__init__.py"] + [
            SRC_DIR / sub / "__init__.py" for sub in EXPECTED_SUBPACKAGES
        ]
        for init_path in init_files:
            source = init_path.read_text(encoding="utf-8")
            lines = source.splitlines()
            for lineno, line in enumerate(lines, start=1):
                stripped = line.strip()
                # Skip comments and empty lines
                if stripped.startswith("#") or stripped == "":
                    continue
                # Skip docstring lines (inside triple quotes)
                # We only check for actual import statements
                if stripped.startswith("import ") or stripped.startswith(
                    "from "
                ):
                    assert False, (
                        f"{init_path}:{lineno} contains import statement: {stripped!r}"
                    )


class TestNegativeCases:
    """Negative test cases -- packages not in this batch should not exist."""

    def test_import_recovery_not_yet_available(self):
        """``import src.recovery`` raises ``ImportError`` (not created in this batch)."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            importlib.import_module("src.recovery")


class TestSecurity:
    """Security-related tests for the package scaffold."""

    def test_no_exec_or_eval_in_init_files(self):
        """No ``__init__.py`` contains ``exec(`` or ``eval(`` calls."""
        init_files = [SRC_DIR / "__init__.py"] + [
            SRC_DIR / sub / "__init__.py" for sub in EXPECTED_SUBPACKAGES
        ]
        dangerous_patterns = ["exec(", "eval(", "compile(", "__import__("]
        for init_path in init_files:
            source = init_path.read_text(encoding="utf-8")
            for pattern in dangerous_patterns:
                assert pattern not in source, (
                    f"{init_path} contains dangerous call: {pattern}"
                )

    def test_no_os_or_subprocess_usage(self):
        """No ``__init__.py`` references ``os.system``, ``subprocess``, or ``shutil``."""
        init_files = [SRC_DIR / "__init__.py"] + [
            SRC_DIR / sub / "__init__.py" for sub in EXPECTED_SUBPACKAGES
        ]
        dangerous_refs = ["os.system", "subprocess", "shutil", "os.popen"]
        for init_path in init_files:
            source = init_path.read_text(encoding="utf-8")
            for ref in dangerous_refs:
                assert ref not in source, (
                    f"{init_path} contains dangerous reference: {ref}"
                )

    def test_no_network_or_io_in_init_files(self):
        """No ``__init__.py`` contains socket, urllib, or requests references."""
        init_files = [SRC_DIR / "__init__.py"] + [
            SRC_DIR / sub / "__init__.py" for sub in EXPECTED_SUBPACKAGES
        ]
        network_refs = ["socket", "urllib", "requests", "http.client", "ftplib"]
        for init_path in init_files:
            source = init_path.read_text(encoding="utf-8")
            for ref in network_refs:
                assert ref not in source, (
                    f"{init_path} contains network reference: {ref}"
                )

    def test_no_pickle_or_marshal_usage(self):
        """No ``__init__.py`` uses pickle or marshal (deserialization attacks)."""
        init_files = [SRC_DIR / "__init__.py"] + [
            SRC_DIR / sub / "__init__.py" for sub in EXPECTED_SUBPACKAGES
        ]
        for init_path in init_files:
            source = init_path.read_text(encoding="utf-8")
            assert "pickle" not in source, f"{init_path} references pickle"
            assert "marshal" not in source, f"{init_path} references marshal"

    def test_init_files_are_valid_python(self):
        """Each ``__init__.py`` compiles without syntax errors."""
        init_files = [SRC_DIR / "__init__.py"] + [
            SRC_DIR / sub / "__init__.py" for sub in EXPECTED_SUBPACKAGES
        ]
        for init_path in init_files:
            source = init_path.read_text(encoding="utf-8")
            try:
                compile(source, str(init_path), "exec")
            except SyntaxError as exc:
                pytest.fail(f"{init_path} has syntax error: {exc}")

    def test_no_global_side_effects_on_import(self):
        """Importing each package does not modify sys.path or sys.modules unexpectedly."""
        # Record state before imports
        path_before = list(sys.path)
        # All modules should already be imported from earlier tests; re-import
        for pkg_name in ALL_PACKAGES:
            importlib.import_module(pkg_name)
        # sys.path should not have been modified by any of the package imports
        # (We added entries ourselves at the top, but the packages shouldn't add more)
        # Just verify no package-added entries
        path_after = list(sys.path)
        assert len(path_after) == len(path_before), (
            f"sys.path length changed from {len(path_before)} to {len(path_after)}"
        )

    def test_no_writable_bytecode_injection_paths(self):
        """Verify __init__.py files don't set __path__ to unusual directories."""
        for pkg_name in ALL_PACKAGES:
            mod = importlib.import_module(pkg_name)
            if hasattr(mod, "__path__"):
                for p in mod.__path__:
                    resolved = Path(p).resolve()
                    # Must be under the project source tree
                    assert str(resolved).startswith(
                        str(SRC_DIR)
                    ), f"{pkg_name}.__path__ points outside src/: {resolved}"

    def test_files_contain_only_ascii_or_utf8(self):
        """Each ``__init__.py`` is valid UTF-8 with no null bytes."""
        init_files = [SRC_DIR / "__init__.py"] + [
            SRC_DIR / sub / "__init__.py" for sub in EXPECTED_SUBPACKAGES
        ]
        for init_path in init_files:
            raw = init_path.read_bytes()
            assert b"\x00" not in raw, f"{init_path} contains null bytes"
            # Should be decodable as UTF-8
            try:
                raw.decode("utf-8")
            except UnicodeDecodeError:
                pytest.fail(f"{init_path} is not valid UTF-8")
