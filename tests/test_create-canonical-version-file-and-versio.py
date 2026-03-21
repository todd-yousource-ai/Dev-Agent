import os
import re
import pathlib

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
VERSION_FILE = REPO_ROOT / "VERSION"
VERSIONING_DOC = REPO_ROOT / "docs" / "VERSIONING.md"

SEMVER_REGEX = re.compile(
    r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$"
)

REQUIRED_SECTIONS = [
    "Canonical Source",
    "Propagation Targets",
    "Version Handshake Protocol",
    "Semantic Versioning Rules",
    "Pre-release Tag Format",
    "CI Enforcement",
    "Version Bump Procedure",
]

REQUIRED_TARGETS = [
    "CFBundleShortVersionString",
    "AGENT_VERSION",
    "pyproject.toml",
    "git tag",
]


def _read_version_raw() -> str:
    """Return the raw bytes-decoded content of VERSION (no stripping)."""
    return VERSION_FILE.read_text(encoding="utf-8")


def _read_version() -> str:
    """Return the stripped version string from VERSION."""
    return _read_version_raw().strip()


def _read_versioning_doc() -> str:
    return VERSIONING_DOC.read_text(encoding="utf-8")


# ===========================================================================
# VERSION file tests
# ===========================================================================


class TestVersionFileExists:
    def test_version_file_exists(self):
        assert VERSION_FILE.exists(), f"VERSION file not found at {VERSION_FILE}"
        assert VERSION_FILE.is_file(), "VERSION must be a regular file"


class TestVersionFileSemver:
    def test_version_file_is_valid_semver(self):
        version = _read_version()
        assert SEMVER_REGEX.match(version), (
            f"VERSION content '{version}' is not valid semver "
            f"(must match {SEMVER_REGEX.pattern})"
        )


class TestVersionFileNoVPrefix:
    def test_version_file_no_v_prefix(self):
        version = _read_version()
        assert not version.startswith("v"), (
            f"VERSION must not start with 'v', got '{version}'"
        )


class TestVersionFileSingleLine:
    def test_version_file_single_line(self):
        raw = _read_version_raw()
        # Split into non-empty lines
        non_empty_lines = [l for l in raw.splitlines() if l.strip()]
        assert len(non_empty_lines) == 1, (
            f"VERSION must contain exactly one non-empty line, "
            f"found {len(non_empty_lines)}: {non_empty_lines!r}"
        )


class TestVersionFileNoTrailingWhitespace:
    def test_version_file_no_trailing_whitespace(self):
        raw = _read_version_raw()
        for i, line in enumerate(raw.splitlines()):
            assert line == line.rstrip(" \t"), (
                f"Line {i} in VERSION has trailing whitespace: {line!r}"
            )


class TestVersionFileInitialValue:
    def test_version_file_initial_value(self):
        version = _read_version()
        assert version == "0.1.0", (
            f"Initial VERSION must be '0.1.0', got '{version}'"
        )


# ===========================================================================
# docs/VERSIONING.md tests
# ===========================================================================


class TestVersioningDocExists:
    def test_versioning_doc_exists(self):
        assert VERSIONING_DOC.exists(), (
            f"docs/VERSIONING.md not found at {VERSIONING_DOC}"
        )
        assert VERSIONING_DOC.is_file()


class TestVersioningDocRequiredSections:
    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_versioning_doc_contains_required_sections(self, section):
        doc = _read_versioning_doc()
        assert section in doc, (
            f"docs/VERSIONING.md must contain section header '{section}'"
        )


class TestVersioningDocReferencesAllTargets:
    @pytest.mark.parametrize("target", REQUIRED_TARGETS)
    def test_versioning_doc_references_all_targets(self, target):
        doc = _read_versioning_doc()
        assert target in doc, (
            f"docs/VERSIONING.md must mention propagation target '{target}'"
        )


class TestVersioningDocFailClosed:
    def test_versioning_doc_states_fail_closed(self):
        doc = _read_versioning_doc()
        assert "fail closed" in doc.lower() or "fail-closed" in doc.lower(), (
            "docs/VERSIONING.md must specify that version mismatches fail closed"
        )


# ===========================================================================
# Negative / rejection tests
# ===========================================================================


class TestVersionFileRejectsVPrefix:
    def test_version_file_rejects_v_prefix(self):
        """A value like 'v0.1.0' must NOT match our semver regex (no v-prefix allowed)."""
        bad = "v0.1.0"
        assert not SEMVER_REGEX.match(bad), (
            f"Semver regex must reject v-prefixed strings, but matched '{bad}'"
        )


class TestVersionFileRejectsMultiline:
    def test_version_file_rejects_multiline(self):
        """Two version lines must be detected as invalid."""
        fake_content = "0.1.0\n0.2.0\n"
        non_empty = [l for l in fake_content.splitlines() if l.strip()]
        assert len(non_empty) != 1, (
            "Multi-version content must fail the single-line assertion"
        )


class TestVersionFileRejectsInvalidSemver:
    @pytest.mark.parametrize(
        "bad_version",
        ["0.1", "1", "0.1.0.0", "abc", "", "1.2.3.4", "v1.0.0", "01.02.03"],
    )
    def test_version_file_rejects_invalid_semver(self, bad_version):
        assert not SEMVER_REGEX.match(bad_version), (
            f"Semver regex must reject '{bad_version}'"
        )


class TestVersionFileRejectsTrailingNewlines:
    def test_version_file_rejects_trailing_newlines_beyond_one(self):
        """VERSION file must have at most one trailing newline (POSIX)."""
        raw = _read_version_raw()
        # After removing one trailing newline (POSIX), there should be no more
        if raw.endswith("\n"):
            without_final = raw[:-1]
        else:
            without_final = raw
        assert not without_final.endswith("\n"), (
            "VERSION has multiple trailing newlines; at most one is allowed"
        )


class TestVersioningDocRejectsMissingMapping:
    """If any required target is absent, the check must fail."""

    @pytest.mark.parametrize(
        "target",
        ["CFBundleShortVersionString", "AGENT_VERSION", "pyproject.toml"],
    )
    def test_versioning_doc_rejects_missing_mapping(self, target):
        # Simulate a doc without this target
        doc = _read_versioning_doc()
        censored = doc.replace(target, "")
        assert target not in censored, (
            f"Censored doc should not contain '{target}'"
        )
        # The real doc MUST contain it
        assert target in doc, (
            f"docs/VERSIONING.md must mention '{target}'"
        )


# ===========================================================================
# Security tests
# ===========================================================================


class TestVersionFileNoExecutableContent:
    """VERSION is consumed by shell scripts and CI -- must be inert."""

    def test_no_null_bytes(self):
        raw_bytes = VERSION_FILE.read_bytes()
        assert b"\x00" not in raw_bytes, "VERSION contains null bytes"

    def test_no_shell_interpolation_dollar_brace(self):
        raw = _read_version_raw()
        assert "${" not in raw, "VERSION contains '${' shell interpolation syntax"

    def test_no_shell_interpolation_dollar_paren(self):
        raw = _read_version_raw()
        assert "$(" not in raw, "VERSION contains '$(' shell interpolation syntax"

    def test_no_backticks(self):
        raw = _read_version_raw()
        assert "`" not in raw, "VERSION contains backtick command substitution"

    def test_no_shell_metacharacters(self):
        raw = _read_version_raw()
        # Only allow: digits, dots, hyphens, lowercase/uppercase alpha, newline
        dangerous = set()
        allowed = set("0123456789.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-\n")
        for ch in raw:
            if ch not in allowed:
                dangerous.add(ch)
        assert not dangerous, (
            f"VERSION contains disallowed characters: {dangerous!r}"
        )

    def test_only_printable_ascii_on_version_line(self):
        version = _read_version()
        for ch in version:
            code = ord(ch)
            assert 0x20 <= code <= 0x7E, (
                f"VERSION contains non-printable-ASCII char: {ch!r} (ord={code})"
            )


class TestVersioningDocNotPermissiveMismatch:
    """Ensure the doc does not encourage ignoring version mismatches."""

    @pytest.mark.parametrize(
        "phrase",
        [
            "can be ignored",
            "may be ignored",
            "warn only",
            "warn-only",
            "non-fatal",
            "non fatal",
            "best effort",
            "best-effort",
            "optional enforcement",
            "soft fail",
            "soft-fail",
        ],
    )
    def test_versioning_doc_does_not_encourage_permissive_mismatch(self, phrase):
        doc = _read_versioning_doc().lower()
        assert phrase not in doc, (
            f"docs/VERSIONING.md contains permissive language: '{phrase}'. "
            "Version mismatches must fail closed, not be treated as warnings."
        )
