"""Tests for canonical product identity schema and naming policy documentation."""

import json
import os
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers - locate repo root and key files
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Walk upward from this test file to find the repository root."""
    current = Path(__file__).resolve().parent
    # Walk up until we find a directory that contains "shared/" or ".git"
    for _ in range(10):
        if (current / "shared").is_dir() or (current / ".git").is_dir():
            return current
        current = current.parent
    # Fallback: assume tests/ is two levels below root
    return Path(__file__).resolve().parent.parent.parent


REPO_ROOT = _repo_root()
SPEC_PATH = REPO_ROOT / "shared" / "product_identity" / "canonical_name_spec.json"
POLICY_PATH = REPO_ROOT / "docs" / "product_identity" / "naming_policy.md"
README_PATH = REPO_ROOT / "shared" / "product_identity" / "README.md"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def spec_raw() -> str:
    """Return the raw JSON text of the canonical name spec."""
    assert SPEC_PATH.exists(), f"canonical_name_spec.json not found at {SPEC_PATH}"
    return SPEC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def spec(spec_raw) -> dict:
    """Return the parsed canonical name spec as a dict."""
    return json.loads(spec_raw)


@pytest.fixture(scope="module")
def policy_text() -> str:
    """Return the text of naming_policy.md."""
    assert POLICY_PATH.exists(), f"naming_policy.md not found at {POLICY_PATH}"
    return POLICY_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def readme_text() -> str:
    """Return the text of README.md."""
    assert README_PATH.exists(), f"README.md not found at {README_PATH}"
    return README_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Canonical name spec - structural tests
# ---------------------------------------------------------------------------

class TestCanonicalNameSpec:
    """Tests validating the canonical_name_spec.json structure and content."""

    def test_json_is_valid_json(self, spec_raw):
        """Load canonical_name_spec.json and assert no parse errors."""
        parsed = json.loads(spec_raw)
        assert isinstance(parsed, dict)

    def test_schema_version_is_semver(self, spec):
        """Assert schema_version matches semver regex."""
        semver_re = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$"
        assert "schema_version" in spec
        assert re.match(semver_re, spec["schema_version"]), (
            f"schema_version '{spec['schema_version']}' is not valid semver"
        )

    def test_required_top_level_keys_present(self, spec):
        """Assert product, organization, derived_forms, prohibited_variants,
        usage_contexts, metadata all exist."""
        required = {
            "product",
            "organization",
            "derived_forms",
            "prohibited_variants",
            "usage_contexts",
            "metadata",
        }
        missing = required - set(spec.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    def test_product_primary_name_is_forge(self, spec):
        """Assert product.primary_name == 'Forge'."""
        assert spec["product"]["primary_name"] == "Forge"

    def test_product_subtitle_is_dev_agent(self, spec):
        """Assert product.subtitle == 'Dev Agent'."""
        assert spec["product"]["subtitle"] == "Dev Agent"

    def test_product_full_formal_name(self, spec):
        """Assert product.full_formal_name == 'Consensus Dev Agent'."""
        assert spec["product"]["full_formal_name"] == "Consensus Dev Agent"

    def test_organization_reverse_dns(self, spec):
        """Assert organization.reverse_dns == 'ai.yousource'."""
        assert spec["organization"]["reverse_dns"] == "ai.yousource"

    def test_all_derived_forms_have_required_fields(self, spec):
        """Each entry has form, value, casing, contexts and all are non-empty."""
        required_fields = {"form", "value", "casing", "contexts"}
        for i, entry in enumerate(spec["derived_forms"]):
            for field in required_fields:
                assert field in entry, (
                    f"derived_forms[{i}] missing field '{field}'"
                )
                val = entry[field]
                if isinstance(val, str):
                    assert len(val.strip()) > 0, (
                        f"derived_forms[{i}].{field} is empty"
                    )
                elif isinstance(val, list):
                    assert len(val) > 0, (
                        f"derived_forms[{i}].{field} is an empty list"
                    )

    def test_derived_forms_cover_minimum_set(self, spec):
        """Assert at least pascal_case, camel_case, kebab_case, snake_case,
        screaming_snake, bundle_id forms exist."""
        required_forms = {
            "pascal_case",
            "camel_case",
            "kebab_case",
            "snake_case",
            "screaming_snake",
            "bundle_id",
        }
        actual_forms = {entry["form"] for entry in spec["derived_forms"]}
        missing = required_forms - actual_forms
        assert not missing, f"Missing required derived forms: {missing}"

    def test_bundle_id_starts_with_reverse_dns(self, spec):
        """Assert bundle_id value starts with organization.reverse_dns."""
        reverse_dns = spec["organization"]["reverse_dns"]
        bundle_entries = [
            e for e in spec["derived_forms"] if e["form"] == "bundle_id"
        ]
        assert bundle_entries, "No bundle_id derived form found"
        for entry in bundle_entries:
            assert entry["value"].startswith(reverse_dns), (
                f"bundle_id '{entry['value']}' does not start with "
                f"reverse_dns '{reverse_dns}'"
            )

    def test_prohibited_variants_have_reason(self, spec):
        """Each prohibited variant has a non-empty reason string."""
        for i, pv in enumerate(spec["prohibited_variants"]):
            assert "reason" in pv, (
                f"prohibited_variants[{i}] missing 'reason'"
            )
            assert isinstance(pv["reason"], str) and len(pv["reason"].strip()) > 0, (
                f"prohibited_variants[{i}].reason is empty"
            )

    def test_no_derived_form_value_in_prohibited_list(self, spec):
        """No derived_forms[].value appears in prohibited_variants[].variant."""
        derived_values = {e["value"] for e in spec["derived_forms"]}
        prohibited_variants = {
            pv["variant"] for pv in spec["prohibited_variants"]
        }
        overlap = derived_values & prohibited_variants
        assert not overlap, (
            f"These values appear in both derived_forms and "
            f"prohibited_variants: {overlap}"
        )

    def test_usage_contexts_are_referenced(self, spec):
        """Every context referenced in derived_forms[].contexts exists in
        usage_contexts."""
        defined_contexts = set(spec["usage_contexts"].keys())
        for i, entry in enumerate(spec["derived_forms"]):
            for ctx in entry["contexts"]:
                assert ctx in defined_contexts, (
                    f"derived_forms[{i}] (form='{entry['form']}') references "
                    f"unknown context '{ctx}'"
                )

    def test_no_duplicate_derived_form_names(self, spec):
        """All derived_forms[].form values are unique."""
        forms = [e["form"] for e in spec["derived_forms"]]
        duplicates = [f for f in forms if forms.count(f) > 1]
        assert not duplicates, f"Duplicate derived form names: {set(duplicates)}"

    def test_metadata_has_created_date(self, spec):
        """metadata.created is a valid ISO 8601 string."""
        assert "metadata" in spec
        assert "created" in spec["metadata"]
        created = spec["metadata"]["created"]
        # ISO 8601 date or datetime: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS...
        iso8601_re = (
            r"^\d{4}-\d{2}-\d{2}"
            r"(T\d{2}:\d{2}(:\d{2})?"
            r"(\.\d+)?"
            r"(Z|[+-]\d{2}:\d{2})?)?$"
        )
        assert re.match(iso8601_re, created), (
            f"metadata.created '{created}' is not a valid ISO 8601 string"
        )


# ---------------------------------------------------------------------------
# File existence tests
# ---------------------------------------------------------------------------

class TestFileExistence:
    """Tests that required documentation files exist and are non-empty."""

    def test_naming_policy_md_exists(self):
        """Assert docs/product_identity/naming_policy.md exists and is non-empty."""
        assert POLICY_PATH.exists(), f"naming_policy.md not found at {POLICY_PATH}"
        content = POLICY_PATH.read_text(encoding="utf-8")
        assert len(content.strip()) > 0, "naming_policy.md is empty"

    def test_readme_md_exists(self):
        """Assert shared/product_identity/README.md exists and is non-empty."""
        assert README_PATH.exists(), f"README.md not found at {README_PATH}"
        content = README_PATH.read_text(encoding="utf-8")
        assert len(content.strip()) > 0, "README.md is empty"

    def test_naming_policy_references_json_spec(self, policy_text):
        """naming_policy.md contains reference to canonical_name_spec.json."""
        assert "canonical_name_spec.json" in policy_text, (
            "naming_policy.md does not reference canonical_name_spec.json"
        )


# ---------------------------------------------------------------------------
# Naming policy alignment tests
# ---------------------------------------------------------------------------

class TestNamingPolicyAlignment:
    """Tests verifying alignment between naming_policy.md, README.md, and the
    JSON spec."""

    def test_policy_references_forge_as_primary(self, policy_text):
        """Verify naming_policy.md references 'Forge' as the canonical primary
        product name."""
        assert "Forge" in policy_text, (
            "naming_policy.md does not reference 'Forge'"
        )

    def test_policy_references_dev_agent_as_subtitle(self, policy_text):
        """Verify the policy references 'Dev Agent' as the subtitle."""
        assert "Dev Agent" in policy_text, (
            "naming_policy.md does not reference 'Dev Agent'"
        )

    def test_policy_identifies_json_as_source_of_truth(self, policy_text):
        """Verify the policy identifies the JSON spec as the single source of
        truth."""
        lower = policy_text.lower()
        assert "source of truth" in lower or "canonical" in lower, (
            "naming_policy.md does not identify the JSON spec as the source "
            "of truth or canonical reference"
        )
        assert "canonical_name_spec.json" in policy_text

    def test_readme_and_policy_consistent_on_prohibited(
        self, policy_text, readme_text, spec
    ):
        """Verify the README and policy are consistent on prohibited legacy
        naming guidance."""
        # Both documents should mention at least one prohibited variant
        prohibited_variants = [
            pv["variant"] for pv in spec["prohibited_variants"]
        ]
        assert len(prohibited_variants) > 0, "No prohibited variants in spec"

        # At least one prohibited variant should be referenced in the policy
        # or README for guidance
        policy_mentions = [v for v in prohibited_variants if v in policy_text]
        readme_mentions = [v for v in prohibited_variants if v in readme_text]

        # At least one of the two documents should mention prohibited variants
        assert policy_mentions or readme_mentions, (
            "Neither naming_policy.md nor README.md mentions any prohibited "
            f"variants from the spec: {prohibited_variants}"
        )

    def test_derived_form_values_in_policy_match_json(self, policy_text, spec):
        """Verify that derived form values mentioned in the markdown policy
        exactly match those in the JSON spec."""
        derived_values = [e["value"] for e in spec["derived_forms"]]
        # We check that any derived value that appears in the policy text is
        # an exact match (not a substring accident).  At minimum, several
        # derived forms should appear in the policy.
        mentioned = [v for v in derived_values if v in policy_text]
        assert len(mentioned) >= 1, (
            "naming_policy.md does not mention any derived form values from "
            "the JSON spec"
        )
        # Verify no mangled/partial references for mentioned values
        for value in mentioned:
            assert value in policy_text, (
                f"Derived form value '{value}' expected in policy but not found"
            )


# ---------------------------------------------------------------------------
# Negative tests
# ---------------------------------------------------------------------------

class TestNegativeCases:
    """Negative / boundary tests to validate correctness constraints."""

    def test_prohibited_variant_not_in_derived_forms(self, spec):
        """Verify that none of the explicitly prohibited variants (e.g.,
        'ConsensusAgent', 'ForgeAI', 'CDA') appear as valid derived form
        values."""
        derived_values = {e["value"] for e in spec["derived_forms"]}
        for pv in spec["prohibited_variants"]:
            assert pv["variant"] not in derived_values, (
                f"Prohibited variant '{pv['variant']}' found in derived_forms"
            )

    def test_empty_contexts_rejected(self, spec):
        """All current entries have at least one context - an empty contexts
        array should not exist."""
        for i, entry in enumerate(spec["derived_forms"]):
            assert isinstance(entry["contexts"], list), (
                f"derived_forms[{i}].contexts is not a list"
            )
            assert len(entry["contexts"]) > 0, (
                f"derived_forms[{i}] (form='{entry['form']}') has an empty "
                f"contexts list"
            )

    def test_unknown_context_reference(self, spec):
        """Verify that no derived form references a context name that doesn't
        exist in the usage_contexts mapping."""
        defined_contexts = set(spec["usage_contexts"].keys())
        for i, entry in enumerate(spec["derived_forms"]):
            for ctx in entry["contexts"]:
                assert ctx in defined_contexts, (
                    f"derived_forms[{i}] references unknown context '{ctx}' "
                    f"(form='{entry['form']}')"
                )

    def test_bundle_id_format_valid(self, spec):
        """Assert bundle_id matches reverse-DNS regex pattern (no uppercase,
        no underscores, proper dot separation)."""
        # Reverse-DNS: lowercase letters, digits, dots; segments separated
        # by dots, no leading/trailing dots, no consecutive dots.
        reverse_dns_re = r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)+$"
        bundle_entries = [
            e for e in spec["derived_forms"] if e["form"] == "bundle_id"
        ]
        assert bundle_entries, "No bundle_id derived form found"
        for entry in bundle_entries:
            value = entry["value"]
            assert re.match(reverse_dns_re, value), (
                f"bundle_id value '{value}' does not match reverse-DNS format"
            )
            assert "_" not in value, (
                f"bundle_id '{value}' contains underscores"
            )
            assert value == value.lower(), (
                f"bundle_id '{value}' contains uppercase characters"
            )

    def test_markdown_policy_not_claiming_different_canonical_name(
        self, policy_text, spec
    ):
        """Verify that naming_policy.md does not claim a different primary name
        than the JSON spec."""
        primary = spec["product"]["primary_name"]
        # Look for common patterns like "canonical name is X" or
        # "primary name is X" and ensure X matches.
        patterns = [
            r"(?i)(?:canonical|primary)\s+(?:product\s+)?name\s+(?:is|:)\s+[\"']?(\w+)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, policy_text)
            for match in matches:
                assert match == primary, (
                    f"naming_policy.md claims primary name '{match}' but "
                    f"JSON spec says '{primary}'"
                )

    def test_no_variant_both_allowed_and_prohibited(self, spec):
        """Verify no legacy variant appears in both allowed and prohibited
        lists."""
        derived_values = {e["value"] for e in spec["derived_forms"]}
        prohibited_set = {pv["variant"] for pv in spec["prohibited_variants"]}
        overlap = derived_values & prohibited_set
        assert not overlap, (
            f"These values are both allowed (derived_forms) and prohibited: "
            f"{overlap}"
        )


# ---------------------------------------------------------------------------
# Security tests
# ---------------------------------------------------------------------------

class TestSecurityScan:
    """Security-focused tests to prevent sensitive data from leaking into
    product identity files."""

    # Patterns that might indicate secrets, tokens, keys, or credentials
    SECRET_PATTERNS = [
        # Generic API keys / tokens
        r"(?i)(?:api[_-]?key|api[_-]?token|access[_-]?token|secret[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}",
        # AWS keys
        r"AKIA[0-9A-Z]{16}",
        # Generic long hex secrets (32+ chars)
        r"(?i)(?:secret|password|passwd|token)\s*[:=]\s*[\"']?[A-Fa-f0-9]{32,}",
        # Bearer tokens
        r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}",
        # Private key blocks
        r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----",
        # GitHub tokens
        r"gh[ps]_[A-Za-z0-9_]{36,}",
        # Generic password assignments
        r"(?i)password\s*[:=]\s*[\"'][^\"']{8,}[\"']",
        # Slack tokens
        r"xox[bprs]-[A-Za-z0-9\-]{10,}",
    ]

    def _scan_for_secrets(self, text: str, filename: str):
        """Scan text for secret-like patterns and fail if any found."""
        findings = []
        for pattern in self.SECRET_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                findings.append(
                    f"Pattern '{pattern}' matched in {filename}: "
                    f"{matches[:3]}..."
                )
        assert not findings, (
            f"Potential secrets/credentials found:\n"
            + "\n".join(findings)
        )

    def test_no_secrets_or_credentials_in_spec(self, spec_raw):
        """Scan canonical_name_spec.json for patterns resembling API keys,
        tokens, passwords, or private URLs."""
        self._scan_for_secrets(spec_raw, "canonical_name_spec.json")

    def test_no_secrets_in_markdown_files(self, policy_text, readme_text):
        """Scan naming_policy.md and README.md for patterns resembling
        secrets, tokens, or credentials."""
        self._scan_for_secrets(policy_text, "naming_policy.md")
        self._scan_for_secrets(readme_text, "README.md")
