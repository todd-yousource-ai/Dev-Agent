"""
Tests for the Forge repository skeleton bootstrap PR.

Covers:
- .gitignore content validation
- scripts/validate_structure.py functionality
- Directory/file structure validation
- Security patterns in .gitignore
"""

import importlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap

import pytest


# ---------------------------------------------------------------------------
# Helpers to locate the repository root
# ---------------------------------------------------------------------------

def _find_repo_root() -> pathlib.Path:
    """Walk up from this file until we find a directory containing .git."""
    current = pathlib.Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    # Fallback: try CWD
    cwd = pathlib.Path.cwd()
    while cwd != cwd.parent:
        if (cwd / ".git").exists():
            return cwd
        cwd = cwd.parent
    raise RuntimeError("Cannot locate repository root (.git not found)")


REPO_ROOT = _find_repo_root()
GITIGNORE_PATH = REPO_ROOT / ".gitignore"
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate_structure.py"


# ---------------------------------------------------------------------------
# Lazy import of validate_structure module (only if the script exists)
# ---------------------------------------------------------------------------

_validate_mod = None


def _get_validate_module():
    global _validate_mod
    if _validate_mod is not None:
        return _validate_mod
    if not VALIDATE_SCRIPT.exists():
        pytest.skip("scripts/validate_structure.py not found on this branch")
    import importlib.util
    spec = importlib.util.spec_from_file_location("validate_structure", str(VALIDATE_SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _validate_mod = mod
    return mod


# ============================================================================
# Unit tests - .gitignore
# ============================================================================

class TestGitignoreExists:
    def test_gitignore_exists_and_is_nonempty(self):
        assert GITIGNORE_PATH.exists(), ".gitignore must exist at repo root"
        content = GITIGNORE_PATH.read_text(encoding="utf-8")
        assert len(content.strip()) > 0, ".gitignore must not be empty"

    def test_gitignore_contains_python_patterns(self):
        content = GITIGNORE_PATH.read_text(encoding="utf-8")
        python_patterns = ["__pycache__/", "*.py[cod]", "*.egg-info/", ".venv/", ".pytest_cache/"]
        for pat in python_patterns:
            assert pat in content, f".gitignore missing Python pattern: {pat}"

    def test_gitignore_contains_swift_patterns(self):
        content = GITIGNORE_PATH.read_text(encoding="utf-8")
        swift_patterns = [".build/", "DerivedData/", "*.xcuserdata/"]
        for pat in swift_patterns:
            assert pat in content, f".gitignore missing Swift pattern: {pat}"

    def test_gitignore_contains_macos_patterns(self):
        content = GITIGNORE_PATH.read_text(encoding="utf-8")
        macos_patterns = [".DS_Store", "._*"]
        for pat in macos_patterns:
            assert pat in content, f".gitignore missing macOS pattern: {pat}"

    def test_gitignore_preserves_gitkeep_files(self):
        """Ensure .gitignore does NOT contain a blanket !.gitkeep denial or
        a pattern that would ignore .gitkeep sentinel files."""
        content = GITIGNORE_PATH.read_text(encoding="utf-8")
        # .gitkeep should not be ignored
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
        for line in lines:
            assert line != ".gitkeep", ".gitignore must not ignore .gitkeep files"
            assert line != "*.gitkeep", ".gitignore must not ignore .gitkeep files"


class TestGitignoreSecurity:
    """Security: sensitive patterns must be present to prevent accidental secret commits."""

    def test_gitignore_excludes_sensitive_patterns(self):
        content = GITIGNORE_PATH.read_text(encoding="utf-8")
        required = [".env", "*.pem", "*.key", "secrets/"]
        for pat in required:
            assert pat in content, (
                f".gitignore MUST contain '{pat}' to prevent accidental secret commits"
            )

    def test_gitignore_contains_ide_patterns(self):
        content = GITIGNORE_PATH.read_text(encoding="utf-8")
        ide_patterns = [".vscode/", ".idea/"]
        for pat in ide_patterns:
            assert pat in content, f".gitignore missing IDE pattern: {pat}"


# ============================================================================
# Unit tests - validate_structure module
# ============================================================================

class TestCanonicalLists:
    """Test that the canonical lists in validate_structure are well-formed."""

    def test_canonical_dirs_list_is_not_empty(self):
        mod = _get_validate_module()
        dirs = getattr(mod, "CANONICAL_DIRS", None)
        assert dirs is not None, "Module must define CANONICAL_DIRS"
        assert len(dirs) > 0, "CANONICAL_DIRS must not be empty"

    def test_canonical_files_list_is_not_empty(self):
        mod = _get_validate_module()
        files = getattr(mod, "CANONICAL_FILES", None)
        assert files is not None, "Module must define CANONICAL_FILES"
        assert len(files) > 0, "CANONICAL_FILES must not be empty"

    def test_canonical_dirs_are_sorted_for_readability(self):
        mod = _get_validate_module()
        dirs = list(getattr(mod, "CANONICAL_DIRS"))
        assert dirs == sorted(dirs), "CANONICAL_DIRS should be sorted for readability"

    def test_canonical_files_are_sorted_for_readability(self):
        mod = _get_validate_module()
        files = list(getattr(mod, "CANONICAL_FILES"))
        assert files == sorted(files), "CANONICAL_FILES should be sorted for readability"

    def test_no_duplicate_entries_in_canonical_dirs(self):
        mod = _get_validate_module()
        dirs = list(getattr(mod, "CANONICAL_DIRS"))
        assert len(dirs) == len(set(dirs)), "CANONICAL_DIRS contains duplicates"

    def test_no_duplicate_entries_in_canonical_files(self):
        mod = _get_validate_module()
        files = list(getattr(mod, "CANONICAL_FILES"))
        assert len(files) == len(set(files)), "CANONICAL_FILES contains duplicates"


# ============================================================================
# Unit tests - validate_structure functions
# ============================================================================

class TestValidateStructureFunction:
    """Tests for the validate_structure() function itself."""

    def _make_complete_tree(self, tmp_path: pathlib.Path):
        """Create a complete tree in tmp_path based on canonical lists."""
        mod = _get_validate_module()
        # Create .git so find_repo_root works
        (tmp_path / ".git").mkdir()
        for d in getattr(mod, "CANONICAL_DIRS"):
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        for f in getattr(mod, "CANONICAL_FILES"):
            fp = tmp_path / f
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.touch()

    def test_validate_structure_passes_on_complete_tree(self, tmp_path):
        mod = _get_validate_module()
        self._make_complete_tree(tmp_path)
        validate = getattr(mod, "validate_structure", None)
        if validate is None:
            pytest.skip("validate_structure function not found")
        errors = validate(tmp_path)
        assert errors is not None  # must return something iterable
        assert len(list(errors)) == 0, f"Expected no errors but got: {list(errors)}"

    def test_validate_structure_detects_missing_directory(self, tmp_path):
        mod = _get_validate_module()
        self._make_complete_tree(tmp_path)
        dirs = list(getattr(mod, "CANONICAL_DIRS"))
        if not dirs:
            pytest.skip("No canonical dirs to test")
        victim = dirs[0]
        victim_path = tmp_path / victim
        if victim_path.exists():
            shutil.rmtree(victim_path)
        validate = getattr(mod, "validate_structure", None)
        if validate is None:
            pytest.skip("validate_structure function not found")
        errors = list(validate(tmp_path))
        assert len(errors) > 0, f"Should detect missing directory: {victim}"

    def test_validate_structure_detects_missing_file(self, tmp_path):
        mod = _get_validate_module()
        self._make_complete_tree(tmp_path)
        files = list(getattr(mod, "CANONICAL_FILES"))
        if not files:
            pytest.skip("No canonical files to test")
        victim = files[0]
        victim_path = tmp_path / victim
        if victim_path.exists():
            victim_path.unlink()
        validate = getattr(mod, "validate_structure", None)
        if validate is None:
            pytest.skip("validate_structure function not found")
        errors = list(validate(tmp_path))
        assert len(errors) > 0, f"Should detect missing file: {victim}"

    def test_validate_structure_detects_multiple_missing_items(self, tmp_path):
        mod = _get_validate_module()
        self._make_complete_tree(tmp_path)
        dirs = list(getattr(mod, "CANONICAL_DIRS"))
        files = list(getattr(mod, "CANONICAL_FILES"))
        removed = []
        # Remove up to 2 dirs and 2 files
        for d in dirs[:2]:
            dp = tmp_path / d
            if dp.exists():
                shutil.rmtree(dp)
                removed.append(d)
        for f in files[:2]:
            fp = tmp_path / f
            if fp.exists():
                fp.unlink()
                removed.append(f)
        if not removed:
            pytest.skip("Could not remove any items")
        validate = getattr(mod, "validate_structure", None)
        if validate is None:
            pytest.skip("validate_structure function not found")
        errors = list(validate(tmp_path))
        assert len(errors) >= len(removed), (
            f"Expected at least {len(removed)} errors, got {len(errors)}"
        )

    def test_validate_structure_reports_all_missing_not_just_first(self, tmp_path):
        mod = _get_validate_module()
        self._make_complete_tree(tmp_path)
        files = list(getattr(mod, "CANONICAL_FILES"))
        # Remove every other file to create gaps
        victims = files[::2][:3]  # up to 3 files
        for f in victims:
            fp = tmp_path / f
            if fp.exists():
                fp.unlink()
        validate = getattr(mod, "validate_structure", None)
        if validate is None:
            pytest.skip("validate_structure function not found")
        errors = list(validate(tmp_path))
        error_text = "\n".join(str(e) for e in errors)
        found = sum(1 for v in victims if v in error_text)
        assert found >= len(victims), (
            f"Validator should report ALL missing items, only found {found}/{len(victims)}"
        )

    def test_validate_structure_reports_missing_init_py_for_python_package_dir(self, tmp_path):
        mod = _get_validate_module()
        self._make_complete_tree(tmp_path)
        files = list(getattr(mod, "CANONICAL_FILES"))
        init_files = [f for f in files if f.endswith("__init__.py")]
        if not init_files:
            pytest.skip("No __init__.py in canonical files")
        victim = init_files[0]
        (tmp_path / victim).unlink()
        validate = getattr(mod, "validate_structure", None)
        if validate is None:
            pytest.skip("validate_structure function not found")
        errors = list(validate(tmp_path))
        error_text = "\n".join(str(e) for e in errors)
        assert victim in error_text or "__init__" in error_text, (
            f"Should specifically report missing {victim}"
        )


class TestFindRepoRoot:
    def test_find_repo_root_locates_git_directory(self):
        mod = _get_validate_module()
        find_root = getattr(mod, "find_repo_root", None)
        if find_root is None:
            pytest.skip("find_repo_root not found in module")
        root = find_root()
        assert (pathlib.Path(root) / ".git").exists()

    def test_find_repo_root_raises_when_no_git_dir(self):
        mod = _get_validate_module()
        find_root = getattr(mod, "find_repo_root", None)
        if find_root is None:
            pytest.skip("find_repo_root not found in module")
        with tempfile.TemporaryDirectory() as td:
            original = os.getcwd()
            try:
                os.chdir(td)
                with pytest.raises((RuntimeError, SystemExit, FileNotFoundError, Exception)):
                    find_root()
            finally:
                os.chdir(original)


class TestMainFunction:
    def _make_complete_tree(self, tmp_path: pathlib.Path):
        mod = _get_validate_module()
        (tmp_path / ".git").mkdir()
        for d in getattr(mod, "CANONICAL_DIRS"):
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        for f in getattr(mod, "CANONICAL_FILES"):
            fp = tmp_path / f
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.touch()

    def test_main_returns_zero_on_valid_structure(self, tmp_path):
        mod = _get_validate_module()
        self._make_complete_tree(tmp_path)
        main_fn = getattr(mod, "main", None)
        if main_fn is None:
            pytest.skip("main function not found")
        # main might accept a root argument or use sys.argv
        try:
            result = main_fn(tmp_path)
        except TypeError:
            # Try calling with string
            try:
                result = main_fn(str(tmp_path))
            except TypeError:
                # Try monkeypatching and calling with no args
                pytest.skip("Cannot determine main() signature")
        assert result == 0, f"main() should return 0 on valid structure, got {result}"

    def test_main_returns_one_on_invalid_structure(self, tmp_path):
        mod = _get_validate_module()
        self._make_complete_tree(tmp_path)
        # Remove a directory to make it invalid
        dirs = list(getattr(mod, "CANONICAL_DIRS"))
        if dirs:
            victim = tmp_path / dirs[0]
            if victim.exists():
                shutil.rmtree(victim)
        main_fn = getattr(mod, "main", None)
        if main_fn is None:
            pytest.skip("main function not found")
        try:
            result = main_fn(tmp_path)
        except TypeError:
            try:
                result = main_fn(str(tmp_path))
            except TypeError:
                pytest.skip("Cannot determine main() signature")
        assert result != 0, "main() should return non-zero on invalid structure"


# ============================================================================
# Unit tests - __init__.py importability
# ============================================================================

class TestInitPyImportability:
    def test_all_init_py_files_are_importable(self):
        """Every __init__.py under src/ should be valid Python (at minimum, parseable)."""
        src_dir = REPO_ROOT / "src"
        if not src_dir.exists():
            pytest.skip("src/ directory not found")
        init_files = list(src_dir.rglob("__init__.py"))
        if not init_files:
            pytest.skip("No __init__.py files found under src/")
        for init_file in init_files:
            content = init_file.read_text(encoding="utf-8")
            try:
                compile(content, str(init_file), "exec")
            except SyntaxError as exc:
                pytest.fail(f"{init_file} has a syntax error: {exc}")

    def test_forge_package_has_version_attribute(self):
        """If src/forge/__init__.py exists and defines __version__, verify it."""
        forge_init = REPO_ROOT / "src" / "forge" / "__init__.py"
        if not forge_init.exists():
            pytest.skip("src/forge/__init__.py not found")
        content = forge_init.read_text(encoding="utf-8")
        if "__version__" not in content:
            pytest.skip("__version__ not defined in src/forge/__init__.py")
        # Parse and execute to check
        ns = {}
        exec(compile(content, str(forge_init), "exec"), ns)
        assert "__version__" in ns
        assert isinstance(ns["__version__"], str)
        assert len(ns["__version__"]) > 0


# ============================================================================
# Unit tests - disk presence
# ============================================================================

class TestDiskPresence:
    def test_every_canonical_dir_exists_on_disk(self):
        mod = _get_validate_module()
        dirs = list(getattr(mod, "CANONICAL_DIRS"))
        missing = [d for d in dirs if not (REPO_ROOT / d).is_dir()]
        assert not missing, f"Missing canonical directories: {missing}"

    def test_every_canonical_file_exists_on_disk(self):
        mod = _get_validate_module()
        files = list(getattr(mod, "CANONICAL_FILES"))
        missing = [f for f in files if not (REPO_ROOT / f).is_file()]
        assert not missing, f"Missing canonical files: {missing}"


# ============================================================================
# Unit tests - --fix flag
# ============================================================================

class TestFixFlag:
    def _make_almost_complete_tree(self, tmp_path):
        """Create a tree missing one dir and one file."""
        mod = _get_validate_module()
        (tmp_path / ".git").mkdir()
        dirs = list(getattr(mod, "CANONICAL_DIRS"))
        files = list(getattr(mod, "CANONICAL_FILES"))
        skipped_dir = dirs[-1] if dirs else None
        skipped_file = files[-1] if files else None
        for d in dirs:
            if d != skipped_dir:
                (tmp_path / d).mkdir(parents=True, exist_ok=True)
        for f in files:
            if f != skipped_file:
                fp = tmp_path / f
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.touch()
        return skipped_dir, skipped_file

    def test_fix_flag_creates_missing_directory(self, tmp_path):
        mod = _get_validate_module()
        fix_fn = getattr(mod, "fix_structure", None)
        main_fn = getattr(mod, "main", None)
        skipped_dir, _ = self._make_almost_complete_tree(tmp_path)
        if skipped_dir is None:
            pytest.skip("No canonical dirs")

        if fix_fn is not None:
            fix_fn(tmp_path)
        elif main_fn is not None:
            # Try calling main with --fix
            original_argv = sys.argv[:]
            try:
                sys.argv = ["validate_structure.py", "--fix", str(tmp_path)]
                try:
                    main_fn(tmp_path, fix=True)
                except TypeError:
                    try:
                        main_fn(fix=True)
                    except TypeError:
                        main_fn()
            except SystemExit:
                pass
            finally:
                sys.argv = original_argv
        else:
            pytest.skip("No fix_structure or main function found")

        assert (tmp_path / skipped_dir).is_dir(), (
            f"--fix should have created missing directory: {skipped_dir}"
        )

    def test_fix_flag_creates_missing_file(self, tmp_path):
        mod = _get_validate_module()
        fix_fn = getattr(mod, "fix_structure", None)
        main_fn = getattr(mod, "main", None)
        _, skipped_file = self._make_almost_complete_tree(tmp_path)
        if skipped_file is None:
            pytest.skip("No canonical files")

        if fix_fn is not None:
            fix_fn(tmp_path)
        elif main_fn is not None:
            original_argv = sys.argv[:]
            try:
                sys.argv = ["validate_structure.py", "--fix", str(tmp_path)]
                try:
                    main_fn(tmp_path, fix=True)
                except TypeError:
                    try:
                        main_fn(fix=True)
                    except TypeError:
                        main_fn()
            except SystemExit:
                pass
            finally:
                sys.argv = original_argv
        else:
            pytest.skip("No fix_structure or main function found")

        assert (tmp_path / skipped_file).exists(), (
            f"--fix should have created missing file: {skipped_file}"
        )


# ============================================================================
# Negative cases
# ============================================================================

class TestNegativeCases:
    def _make_complete_tree(self, tmp_path):
        mod = _get_validate_module()
        (tmp_path / ".git").mkdir()
        for d in getattr(mod, "CANONICAL_DIRS"):
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        for f in getattr(mod, "CANONICAL_FILES"):
            fp = tmp_path / f
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.touch()

    def test_validate_structure_fails_when_python_package_init_missing(self, tmp_path):
        mod = _get_validate_module()
        self._make_complete_tree(tmp_path)
        validate = getattr(mod, "validate_structure", None)
        if validate is None:
            pytest.skip("validate_structure not found")

        # Find an __init__.py for a "consensus" package or any __init__.py
        files = list(getattr(mod, "CANONICAL_FILES"))
        target = None
        for f in files:
            if "consensus" in f and f.endswith("__init__.py"):
                target = f
                break
        if target is None:
            # Fall back to any __init__.py
            for f in files:
                if f.endswith("__init__.py"):
                    target = f
                    break
        if target is None:
            pytest.skip("No __init__.py in canonical files")

        (tmp_path / target).unlink()
        errors =
