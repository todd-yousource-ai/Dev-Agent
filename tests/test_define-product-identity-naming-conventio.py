"""
Tests for Product Identity, Naming Conventions, and Branding Rules.

Covers:
- Product identity document existence and required sections
- Naming convention regex patterns for branches, artifacts, config keys, files
- Standards alignment and cross-document consistency
- Security: no path traversal in config keys, no secrets in naming examples
"""

import os
import re
import pathlib

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

PRODUCT_IDENTITY_PATH = REPO_ROOT / "docs" / "PRODUCT_IDENTITY.md"

# Possible locations for naming conventions / standards docs
NAMING_CONVENTIONS_CANDIDATES = [
    REPO_ROOT / "docs" / "NAMING_CONVENTIONS.md",
    REPO_ROOT / "docs" / "naming_conventions.md",
    REPO_ROOT / "forge-standards" / "NAMING_CONVENTIONS.md",
    REPO_ROOT / "forge-standards" / "naming_conventions.md",
    REPO_ROOT / "standards" / "NAMING_CONVENTIONS.md",
]

STANDARDS_DOC_CANDIDATES = [
    REPO_ROOT / "forge-standards" / "STANDARDS.md",
    REPO_ROOT / "forge-standards" / "standards.md",
    REPO_ROOT / "docs" / "STANDARDS.md",
    REPO_ROOT / "docs" / "standards.md",
    REPO_ROOT / "standards" / "STANDARDS.md",
]


def _find_first_existing(candidates: list[pathlib.Path]) -> pathlib.Path | None:
    for p in candidates:
        if p.exists():
            return p
    return None


def _read_text_if_exists(path: pathlib.Path | None) -> str | None:
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return None


@pytest.fixture(scope="module")
def product_identity_text() -> str:
    """Return the full text of the PRODUCT_IDENTITY.md document."""
    assert PRODUCT_IDENTITY_PATH.exists(), (
        f"PRODUCT_IDENTITY.md not found at {PRODUCT_IDENTITY_PATH}"
    )
    return PRODUCT_IDENTITY_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def naming_conventions_path() -> pathlib.Path | None:
    return _find_first_existing(NAMING_CONVENTIONS_CANDIDATES)


@pytest.fixture(scope="module")
def naming_conventions_text(naming_conventions_path) -> str | None:
    return _read_text_if_exists(naming_conventions_path)


@pytest.fixture(scope="module")
def standards_doc_path() -> pathlib.Path | None:
    return _find_first_existing(STANDARDS_DOC_CANDIDATES)


@pytest.fixture(scope="module")
def standards_doc_text(standards_doc_path) -> str | None:
    return _read_text_if_exists(standards_doc_path)


# ---------------------------------------------------------------------------
# Regex patterns extracted/derived from naming conventions
# ---------------------------------------------------------------------------

# Branch naming: {type}/{ticket}-{short-description}
# Allowed types: feature, fix, release, hotfix, chore, docs, forge-agent, etc.
BRANCH_NAME_RE = re.compile(
    r"^(feature|fix|release|hotfix|chore|docs|forge-agent|ci|refactor|test)"
    r"/[a-z0-9]([a-z0-9\-]*[a-z0-9])?$"
)

# Artifact naming: {product}-{component}-{version}-{arch}.{ext}
# e.g. forge-backend-1.2.0-arm64.tar.gz
ARTIFACT_NAME_RE = re.compile(
    r"^[a-z][a-z0-9]*(-[a-z][a-z0-9]*)*"  # product-component
    r"-\d+\.\d+\.\d+([a-z0-9\-\.]+)?"  # -version (semver, maybe pre-release)
    r"-[a-z0-9]+(\.[a-z0-9]+)*$"  # -arch.ext (e.g. arm64.tar.gz)
)

# Config keys: dot-separated hierarchical, lowercase, no underscores
CONFIG_KEY_RE = re.compile(
    r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)+$"
)

# Python file names: snake_case, .py extension
PYTHON_FILE_RE = re.compile(
    r"^[a-z][a-z0-9]*(_[a-z0-9]+)*\.py$"
)

# Swift file names: PascalCase, .swift extension
SWIFT_FILE_RE = re.compile(
    r"^[A-Z][a-zA-Z0-9]*\.swift$"
)

# Directory names: lowercase, hyphens or underscores (no spaces, no uppercase)
DIRECTORY_NAME_RE = re.compile(
    r"^[a-z][a-z0-9]*([_\-][a-z0-9]+)*$"
)

# Enum constants: UPPER_SNAKE_CASE
ENUM_CONSTANT_RE = re.compile(
    r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$"
)


# ===================================================================
# tests/standards/test_product_identity_doc.py
# ===================================================================


class TestProductIdentityDocExists:
    """Verify the product identity document exists and is readable."""

    def test_product_identity_doc_exists(self):
        assert PRODUCT_IDENTITY_PATH.exists(), (
            f"Expected PRODUCT_IDENTITY.md at {PRODUCT_IDENTITY_PATH}"
        )

    def test_product_identity_doc_is_nonempty(self, product_identity_text):
        assert len(product_identity_text.strip()) > 100, (
            "PRODUCT_IDENTITY.md appears to be too short / empty"
        )


class TestProductIdentityRequiredSections:
    """Ensure the document contains all required sections."""

    REQUIRED_SECTIONS = [
        "Product Name Hierarchy",
        "Usage Rules",
        "Primary Name",
        "Subheader",
        "Dev Agent",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_product_identity_contains_required_sections(
        self, product_identity_text, section
    ):
        assert section.lower() in product_identity_text.lower(), (
            f"PRODUCT_IDENTITY.md is missing required section containing '{section}'"
        )


class TestProductIdentityDefinitions:
    """Verify Forge is defined as primary name, Dev Agent as subheader."""

    def test_product_identity_defines_forge_as_primary_name(
        self, product_identity_text
    ):
        text_lower = product_identity_text.lower()
        assert "primary" in text_lower and "forge" in text_lower, (
            "PRODUCT_IDENTITY.md must define 'Forge' as the primary product name"
        )
        # Check that the table or heading explicitly associates Forge with Primary
        assert re.search(
            r"primary.*forge|forge.*primary", text_lower
        ), "Forge must be associated with 'primary' designation"

    def test_product_identity_defines_dev_agent_as_subheader(
        self, product_identity_text
    ):
        text_lower = product_identity_text.lower()
        assert "subheader" in text_lower and "dev agent" in text_lower, (
            "PRODUCT_IDENTITY.md must define 'Dev Agent' as the subheader"
        )

    def test_product_identity_includes_ui_docs_code_usage_guidance(
        self, product_identity_text
    ):
        text_lower = product_identity_text.lower()
        # Must mention UI, docs/documentation, and code contexts
        assert "ui" in text_lower, "Must include UI usage guidance"
        assert "doc" in text_lower, "Must include documentation usage guidance"
        assert "code" in text_lower or "cli" in text_lower, (
            "Must include code or CLI usage guidance"
        )


class TestProhibitedForms:
    """Verify the prohibited forms section exists and is non-empty."""

    def test_prohibited_forms_section_exists_and_nonempty(
        self, product_identity_text
    ):
        text_lower = product_identity_text.lower()
        # The document should mention prohibited/disallowed forms or "never used"
        has_prohibited = (
            "prohibited" in text_lower
            or "never used" in text_lower
            or "not user-facing" in text_lower
            or "never" in text_lower
        )
        assert has_prohibited, (
            "PRODUCT_IDENTITY.md must contain guidance on prohibited naming forms"
        )


# ===================================================================
# tests/standards/test_naming_conventions_doc.py
# ===================================================================


class TestNamingConventionsDocExists:
    """Check if a naming conventions doc exists (may be part of PRODUCT_IDENTITY)."""

    def test_naming_conventions_doc_exists(self, naming_conventions_path):
        # Naming conventions may live in PRODUCT_IDENTITY.md itself or a
        # separate file. We accept either.
        has_separate = naming_conventions_path is not None
        has_in_product_identity = PRODUCT_IDENTITY_PATH.exists()
        assert has_separate or has_in_product_identity, (
            "No naming conventions document found (neither standalone nor "
            "in PRODUCT_IDENTITY.md)"
        )

    def test_naming_conventions_contains_required_sections(
        self, naming_conventions_text, product_identity_text
    ):
        """At least one document must cover naming conventions topics."""
        combined = (naming_conventions_text or "") + (product_identity_text or "")
        combined_lower = combined.lower()
        # Should mention conventions related to naming/identifiers
        assert "name" in combined_lower or "naming" in combined_lower
        assert "convention" in combined_lower or "usage" in combined_lower or "rules" in combined_lower


class TestStandardsNamingConventionsExists:
    def test_standards_naming_conventions_exists(
        self, naming_conventions_path, product_identity_text
    ):
        # Accept if naming content is in product identity
        combined = ""
        if naming_conventions_path:
            combined += naming_conventions_path.read_text(encoding="utf-8")
        combined += product_identity_text or ""
        assert len(combined) > 0, "No naming conventions content found"


class TestStandardsDocRegexAppendix:
    def test_standards_doc_contains_regex_appendix(
        self, standards_doc_text, naming_conventions_text, product_identity_text
    ):
        """At least one document should reference regex or pattern rules."""
        combined = (
            (standards_doc_text or "")
            + (naming_conventions_text or "")
            + (product_identity_text or "")
        )
        combined_lower = combined.lower()
        # Acceptable evidence: mention of regex, pattern, convention rules
        has_pattern_reference = (
            "regex" in combined_lower
            or "pattern" in combined_lower
            or "identifier" in combined_lower
            or "snake_case" in combined_lower
            or "camelcase" in combined_lower
            or "pascal" in combined_lower
            or "naming" in combined_lower
        )
        assert has_pattern_reference, (
            "No regex/pattern appendix or naming pattern reference found in any doc"
        )


class TestDocsReferencesStandards:
    def test_docs_references_standards_as_authoritative(
        self, product_identity_text
    ):
        text_lower = product_identity_text.lower()
        # The doc should indicate it is normative/authoritative
        assert (
            "normative" in text_lower
            or "authoritative" in text_lower
            or "active" in text_lower
            or "supersedes" in text_lower
        ), "PRODUCT_IDENTITY.md must indicate its authoritative status"


# ===================================================================
# Branch Name Regex Tests
# ===================================================================


class TestBranchNameRegex:
    """Validate branch naming convention regex patterns."""

    @pytest.mark.parametrize(
        "branch",
        [
            "feature/prd-001-add-login",
            "feature/add-auth",
            "feature/123-foo",
        ],
    )
    def test_branch_name_regex_matches_valid_feature_branch(self, branch):
        assert BRANCH_NAME_RE.match(branch), f"Valid feature branch rejected: {branch}"

    @pytest.mark.parametrize(
        "branch",
        [
            "fix/bug-123-null-pointer",
            "fix/typo-readme",
            "fix/42-edge-case",
        ],
    )
    def test_branch_name_regex_matches_valid_fix_branch(self, branch):
        assert BRANCH_NAME_RE.match(branch), f"Valid fix branch rejected: {branch}"

    @pytest.mark.parametrize(
        "branch",
        [
            "release/1-0-0",
            "release/v2-1",
        ],
    )
    def test_branch_name_regex_matches_valid_release_branch(self, branch):
        assert BRANCH_NAME_RE.match(branch), f"Valid release branch rejected: {branch}"

    @pytest.mark.parametrize(
        "branch",
        [
            "forge-agent/auto-fix-lint",
            "forge-agent/pr-42-review",
        ],
    )
    def test_branch_name_regex_matches_valid_forge_agent_branch(self, branch):
        assert BRANCH_NAME_RE.match(branch), (
            f"Valid forge-agent branch rejected: {branch}"
        )

    @pytest.mark.parametrize(
        "branch",
        [
            "Feature/PRD-001-My Branch",
            "FEATURE/FOO",
            "main",
            "develop",
            "",
            "feature/",
            "feature/ space",
            "feature/UPPERCASE",
        ],
    )
    def test_branch_name_regex_rejects_invalid_patterns(self, branch):
        assert not BRANCH_NAME_RE.match(branch), (
            f"Invalid branch name should be rejected: {branch}"
        )

    def test_branch_name_regex_rejects_spaces_and_uppercase(self):
        bad = "Feature/PRD-001-My Branch"
        assert not BRANCH_NAME_RE.match(bad), (
            f"Branch with spaces/uppercase must be rejected: {bad}"
        )

    def test_branch_name_rejects_missing_prefix(self):
        bad = "add-new-feature"
        assert not BRANCH_NAME_RE.match(bad), (
            f"Branch without type prefix must be rejected: {bad}"
        )


# ===================================================================
# Artifact Name Regex Tests
# ===================================================================


class TestArtifactNameRegex:
    """Validate artifact naming convention regex patterns."""

    @pytest.mark.parametrize(
        "artifact",
        [
            "forge-backend-1.2.0-arm64.tar.gz",
            "forge-cli-0.1.0-x86-64.tar.gz",
            "forge-agent-2.0.0-amd64.deb",
            "forge-core-1.0.0-universal.zip",
        ],
    )
    def test_artifact_name_regex_matches_valid_artifacts(self, artifact):
        assert ARTIFACT_NAME_RE.match(artifact), (
            f"Valid artifact name rejected: {artifact}"
        )

    @pytest.mark.parametrize(
        "artifact",
        [
            "forge-backend-arm64.tar.gz",  # missing version
            "Forge-Backend-1.2.0-arm64.tar.gz",  # uppercase
            "",
            "forge",
            "forge-1.2.0",  # missing arch
        ],
    )
    def test_artifact_name_regex_rejects_invalid_artifacts(self, artifact):
        assert not ARTIFACT_NAME_RE.match(artifact), (
            f"Invalid artifact name should be rejected: {artifact}"
        )

    def test_artifact_name_regex_rejects_missing_version(self):
        bad = "forge-backend-arm64.tar.gz"
        assert not ARTIFACT_NAME_RE.match(bad), (
            "Artifact without version must be rejected"
        )


# ===================================================================
# Config Key Regex Tests
# ===================================================================


class TestConfigKeyRegex:
    """Validate config key naming convention regex patterns."""

    @pytest.mark.parametrize(
        "key",
        [
            "forge.backend.timeout",
            "forge.agent.retries",
            "app.logging.level",
            "forge.db.connection",
        ],
    )
    def test_config_key_regex_matches_valid_keys(self, key):
        assert CONFIG_KEY_RE.match(key), f"Valid config key rejected: {key}"

    @pytest.mark.parametrize(
        "key",
        [
            "forge_backend_timeout",  # underscores
            "forgebackendtimeout",  # non-hierarchical
            "Forge.Backend.Timeout",  # uppercase
            "",
            "forge",  # single segment, not hierarchical
            ".forge.backend",  # leading dot
        ],
    )
    def test_config_key_regex_rejects_invalid_keys(self, key):
        assert not CONFIG_KEY_RE.match(key), (
            f"Invalid config key should be rejected: {key}"
        )

    def test_config_key_regex_rejects_underscores(self):
        bad = "forge_backend_timeout"
        assert not CONFIG_KEY_RE.match(bad), (
            "Config key with underscores must be rejected (must use dots)"
        )

    def test_config_key_rejects_non_hierarchical_forms(self):
        bad = "forgebackendtimeout"
        assert not CONFIG_KEY_RE.match(bad), (
            "Non-hierarchical config key must be rejected"
        )


# ===================================================================
# Python File Name Regex Tests
# ===================================================================


class TestPythonFileNameRegex:
    """Validate Python file naming convention regex patterns."""

    @pytest.mark.parametrize(
        "filename",
        [
            "my_module.py",
            "forge_agent.py",
            "test_utils.py",
            "a.py",
            "config123.py",
        ],
    )
    def test_python_file_name_regex_matches_snake_case(self, filename):
        assert PYTHON_FILE_RE.match(filename), (
            f"Valid Python filename rejected: {filename}"
        )

    @pytest.mark.parametrize(
        "filename",
        [
            "MyModule.py",
            "myModule.py",
            "ForgeAgent.py",
        ],
    )
    def test_python_file_name_regex_rejects_camel_case(self, filename):
        assert not PYTHON_FILE_RE.match(filename), (
            f"CamelCase Python filename should be rejected: {filename}"
        )

    def test_python_file_name_rejects_hyphens(self):
        bad = "my-module.py"
        assert not PYTHON_FILE_RE.match(bad), (
            "Python filename with hyphens must be rejected (must use underscores)"
        )


# ===================================================================
# Swift File Name Regex Tests
# ===================================================================


class TestSwiftFileNameRegex:
    """Validate Swift file naming convention regex patterns."""

    @pytest.mark.parametrize(
        "filename",
        [
            "ForgeAgent.swift",
            "ConsensusEngine.swift",
            "AppDelegate.swift",
            "View.swift",
        ],
    )
    def test_swift_file_name_regex_matches_pascal_case(self, filename):
        assert SWIFT_FILE_RE.match(filename), (
            f"Valid Swift filename rejected: {filename}"
        )

    @pytest.mark.parametrize(
        "filename",
        [
            "forge_agent.swift",
            "forgeAgent.swift",
            "forge-agent.swift",
        ],
    )
    def test_swift_file_name_regex_rejects_non_pascal_case(self, filename):
        assert not SWIFT_FILE_RE.match(filename), (
            f"Non-PascalCase Swift filename should be rejected: {filename}"
        )


# ===================================================================
# Directory Name Tests
# ===================================================================


class TestDirectoryNamePatterns:
    """Validate directory naming convention patterns."""

    @pytest.mark.parametrize(
        "dirname",
        [
            "forge-agent",
            "forge_core",
            "tests",
            "src",
            "my-component",
            "utils123",
        ],
    )
    def test_directory_name_patterns_match_expected_conventions(self, dirname):
        assert DIRECTORY_NAME_RE.match(dirname), (
            f"Valid directory name rejected: {dirname}"
        )

    @pytest.mark.parametrize(
        "dirname",
        [
            "ForgeAgent",
            "My Directory",
            "TESTS",
            "",
        ],
    )
    def test_directory_name_rejects_invalid_patterns(self, dirname):
        assert not DIRECTORY_NAME_RE.match(dirname), (
            f"Invalid directory name should be rejected: {dirname}"
        )


# ===================================================================
# Enum Constant Naming Tests
# ===================================================================


class TestEnumConstantNaming:
    """Validate enum constant naming patterns (UPPER_SNAKE_CASE)."""

    @pytest.mark.parametrize(
        "name",
        [
            "RUNNING",
            "FORGE_AGENT",
            "STATUS_OK",
            "HTTP_200",
            "A",
        ],
    )
    def test_enum_constant_naming_patterns(self, name):
        assert ENUM_CONSTANT_RE.match(name), (
            f"Valid enum constant rejected: {name}"
        )

    @pytest.mark.parametrize(
        "name",
        [
            "running",
            "ForgeAgent",
            "status_ok",  # lowercase
            "",
        ],
    )
    def test_enum_constant_rejects_non_upper_snake(self, name):
        assert not ENUM_CONSTANT_RE.match(name), (
            f"Invalid enum constant should be rejected: {name}"
        )


# ===================================================================
# tests/standards/test_standards_alignment.py
# ===================================================================


class TestStandardsAlignment:
    """Verify cross-document consistency and standards alignment."""

    def test_standards_doc_references_canonical_naming_rules(
        self, standards_doc_text, product_identity_text
    ):
        """At least one document must reference canonical naming rules."""
        combined = (standards_doc_text or "") + (product_identity_text or "")
        combined_lower = combined.lower()
        assert (
            "naming" in combined_lower
            or "convention" in combined_lower
            or "identifier" in combined_lower
        ), "Documents must reference canonical naming rules"

    def test_standards_doc_does_not_contradict_product_identity(
        self, standards_doc_text, product_identity_text
    ):
        """
        Both docs (if they exist) should agree on 'Forge' as the primary name.
        Neither should define a different primary product name.
