forge/__init__.py:

"""forge package -- Forge platform Python backend."""

forge/branding.py:

"""Forge branding constants module.

Single source of truth for all product identity constants in the Python backend.
All values are loaded from shared/product_identity/canonical_name_spec.json at
import time. No branding strings are hardcoded in this module.

Security assumptions:
    - The canonical JSON spec file is trusted (it lives in the repo and is
      reviewed via PR). However, all fields are still validated for type and
      non-emptiness to catch accidental corruption or merge conflicts.
    - The module fails closed: if the JSON file is missing, malformed, or
      contains unexpected values, import raises immediately with an actionable
      diagnostic. No partial or default branding is ever exposed.

Failure behavior:
    - Missing JSON file: FileNotFoundError with path and remediation hint.
    - Malformed JSON: json.JSONDecodeError propagates with full context.
    - Missing keys: ValueError listing every missing field.
    - Non-string values: ValueError listing every offending field.
    - Empty/whitespace values: ValueError listing every offending field.

Thread safety:
    The Branding dataclass is frozen. The BRANDING singleton is set at module
    level during import (GIL-protected). Concurrent reads are safe.

Public API:
    Branding       -- frozen dataclass with 17 str fields
    BRANDING       -- module-level singleton instance
    get_branding() -- accessor returning the singleton (test-patching friendly)
"""

import dataclasses
import json
import pathlib
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Frozen dataclass -- 17 str fields, one per branding surface
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Branding:
    """Immutable product identity constants.

    Every field corresponds to a key in canonical_name_spec.json (specifically
    within the flattened branding mapping produced by the loader). The dataclass
    is frozen to prevent any runtime mutation of identity strings.

    Fields:
        primary_name: Short user-facing product name (e.g. "Forge").
        subtitle: Product qualifier (e.g. "Dev Agent").
        full_display_name: Full name with em-dash (e.g. "Forge -- Dev Agent").
        pascal_case: PascalCase form for Swift types / class prefixes.
        kebab_case: kebab-case form for CLI, URLs, package names.
        screaming_snake_case: SCREAMING_SNAKE for env vars and constants.
        bundle_id_prefix: Reverse-DNS bundle identifier prefix.
        keychain_service_id: Reverse-DNS Keychain service identifier.
        branch_prefix: Git branch prefix for agent-created branches.
        commit_prefix: Prefix for agent-authored commit messages.
        ci_workflow_prefix: Prefix for CI workflow names.
        sparkle_appcast_name: Sparkle framework appcast filename stem.
        notification_title: macOS notification title string.
        dock_label: macOS Dock icon label.
        menu_bar_label: macOS menu bar label.
        log_prefix: Prefix for structured log entries.
        bootstrap_signal: Signal string emitted when agent is ready.
    """

    primary_name: str
    subtitle: str
    full_display_name: str
    pascal_case: str
    kebab_case: str
    screaming_snake_case: str
    bundle_id_prefix: str
    keychain_service_id: str
    branch_prefix: str
    commit_prefix: str
    ci_workflow_prefix: str
    sparkle_appcast_name: str
    notification_title: str
    dock_label: str
    menu_bar_label: str
    log_prefix: str
    bootstrap_signal: str


# ---------------------------------------------------------------------------
# Expected field names -- derived from the dataclass itself so it stays in sync
# ---------------------------------------------------------------------------

_EXPECTED_FIELDS: frozenset = frozenset(
    f.name for f in dataclasses.fields(Branding)
)


# ---------------------------------------------------------------------------
# Private helpers -- each does one thing, fails loudly
# ---------------------------------------------------------------------------

def _canonical_spec_path() -> pathlib.Path:
    """Resolve the absolute path to canonical_name_spec.json.

    Navigates from this file (forge/branding.py) up to the repository root,
    then into shared/product_identity/canonical_name_spec.json. This avoids
    any dependency on the working directory.

    Returns:
        Absolute Path to the canonical JSON spec.
    """
    # forge/branding.py -> forge/ -> repo_root/
    module_dir = pathlib.Path(__file__).resolve().parent
    repo_root = module_dir.parent
    return repo_root / "shared" / "product_identity" / "canonical_name_spec.json"


def _read_canonical_spec(path: pathlib.Path) -> Dict[str, Any]:
    """Read and parse the canonical JSON spec file.

    Args:
        path: Absolute path to canonical_name_spec.json.

    Returns:
        Parsed JSON as a dict.

    Raises:
        FileNotFoundError: If the JSON file does not exist. The message
            includes the expected path and a remediation hint.
        json.JSONDecodeError: If the file contents are not valid JSON.
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"Canonical branding spec not found at: {path}\n"
            f"This file is expected to exist from PR #1. Ensure "
            f"shared/product_identity/canonical_name_spec.json is present "
            f"in the repository root."
        )
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _extract_branding_payload(spec: Dict[str, Any]) -> Dict[str, str]:
    """Extract a flat branding dict from the canonical spec structure.

    The canonical spec has a nested structure (organization, product,
    derived_forms array). This function flattens it into the 17-key dict
    that maps directly to Branding dataclass fields.

    Args:
        spec: The full parsed canonical_name_spec.json dict.

    Returns:
        A flat dict with exactly the keys expected by the Branding dataclass.

    Raises:
        ValueError: If required top-level sections are missing from the spec.
    """
    missing_sections = []
    if "product" not in spec:
        missing_sections.append("product")
    if "derived_forms" not in spec:
        missing_sections.append("derived_forms")
    if "organization" not in spec:
        missing_sections.append("organization")
    if missing_sections:
        raise ValueError(
            f"Canonical spec is missing required top-level sections: "
            f"{', '.join(sorted(missing_sections))}"
        )

    product = spec["product"]
    org = spec["organization"]

    # Build a lookup from derived_forms array: form -> value
    derived: Dict[str, str] = {}
    for entry in spec["derived_forms"]:
        form_id = entry.get("form", "")
        form_value = entry.get("value", "")
        derived[form_id] = form_value

    # Map canonical spec structure to flat branding fields
    payload: Dict[str, str] = {
        "primary_name": product.get("primary_name", ""),
        "subtitle": product.get("subtitle", ""),
        "full_display_name": f"{product.get('primary_name', '')} \u2014 {product.get('subtitle', '')}",
        "pascal_case": derived.get("pascal_case", ""),
        "kebab_case": derived.get("kebab_case", ""),
        "screaming_snake_case": derived.get("screaming_snake", ""),
        "bundle_id_prefix": derived.get("bundle_id", ""),
        "keychain_service_id": f"{derived.get('keychain_service', '')}.keychain",
        "branch_prefix": f"{derived.get('cli_short', '')}-agent/",
        "commit_prefix": f"[{product.get('primary_name', '')}]",
        "ci_workflow_prefix": f"{derived.get('cli_short', '')}-",
        "sparkle_appcast_name": f"{derived.get('kebab_case', '')}-appcast",
        "notification_title": f"{product.get('primary_name', '')} \u2014 {product.get('subtitle', '')}",
        "dock_label": derived.get("ui_primary", ""),
        "menu_bar_label": derived.get("ui_primary", ""),
        "log_prefix": f"[{product.get('primary_name', '')}]",
        "bootstrap_signal": f"{product.get('primary_name', '').upper()}_READY",
    }

    return payload


def _validate_spec_payload(payload: Dict[str, Any]) -> None:
    """Validate that the payload contains all expected keys with valid values.

    Checks:
        1. Every expected field is present in the payload.
        2. Every value is a str.
        3. No value is empty or whitespace-only.

    Args:
        payload: Flat dict to validate against Branding fields.

    Raises:
        ValueError: With actionable message identifying all offending fields.
            Lists missing keys, non-string values, and empty/whitespace values
            in a single pass so the developer can fix all issues at once.
    """
    errors = []

    # 1. Check for missing keys
    missing_keys = _EXPECTED_FIELDS - set(payload.keys())
    if missing_keys:
        errors.append(
            f"Missing required branding keys: {', '.join(sorted(missing_keys))}"
        )

    # 2. Check for non-string values (only among keys that exist)
    present_keys = _EXPECTED_FIELDS & set(payload.keys())
    non_string_keys = sorted(
        k for k in present_keys if not isinstance(payload[k], str)
    )
    if non_string_keys:
        errors.append(
            f"Non-string values for branding keys: "
            f"{', '.join(f'{k} (type={type(payload[k]).__name__})' for k in non_string_keys)}"
        )

    # 3. Check for empty or whitespace-only values (only among str values)
    string_keys = sorted(
        k for k in present_keys
        if isinstance(payload[k], str) and not payload[k].strip()
    )
    if string_keys:
        errors.append(
            f"Empty or whitespace-only branding values: {', '.join(string_keys)}"
        )

    if errors:
        raise ValueError(
            "Branding spec validation failed:\n  - " + "\n  - ".join(errors)
        )


def _build_branding(payload: Dict[str, Any]) -> Branding:
    """Construct a frozen Branding instance from a validated payload.

    Only the fields defined on the Branding dataclass are passed to the
    constructor. Any extra keys in the payload are silently ignored -- this
    is intentional to allow forward-compatible JSON specs that add fields
    before the Python module is updated (though validation ensures all
    *required* fields are present).

    Args:
        payload: Validated dict with at least all Branding field keys.

    Returns:
        A frozen Branding instance.
    """
    # Extract only the fields the dataclass expects
    field_values = {k: payload[k] for k in _EXPECTED_FIELDS}
    return Branding(**field_values)


def _load_branding() -> Branding:
    """Orchestrate loading, extraction, validation, and construction.

    Pipeline:
        1. Resolve canonical spec path.
        2. Read and parse JSON.
        3. Extract flat branding payload from nested spec.
        4. Validate all fields.
        5. Construct frozen Branding instance.

    Returns:
        A frozen Branding singleton.

    Raises:
        FileNotFoundError: If canonical JSON is missing.
        json.JSONDecodeError: If JSON is malformed.
        ValueError: If any field is missing, non-string, or empty.
    """
    path = _canonical_spec_path()
    spec = _read_canonical_spec(path)
    payload = _extract_branding_payload(spec)
    _validate_spec_payload(payload)
    return _build_branding(payload)


# ---------------------------------------------------------------------------
# Module-level singleton -- instantiated once at import time
# ---------------------------------------------------------------------------

BRANDING: Branding = _load_branding()


def get_branding() -> Branding:
    """Return the module-level Branding singleton.

    This accessor exists for dependency-injection-friendly code and to
    facilitate test patching (e.g., ``monkeypatch.setattr``).

    Returns:
        The same Branding instance as the module-level BRANDING constant.
    """
    return BRANDING

tests/__init__.py:

"""tests package -- Forge platform test suite."""

tests/test_branding.py:

"""Unit and integration tests for forge.branding.

Tests cover:
    - Frozen dataclass behavior (immutability)
    - Field type and content validation
    - Singleton identity guarantees
    - JSON-to-dataclass mapping correctness
    - Specific field value format assertions
    - Validation error paths (missing keys, bad types, empty strings, etc.)
    - File-not-found and malformed JSON error paths

Security notes:
    - Tests that exercise error paths use monkeypatching to simulate missing
      files and corrupt data without modifying actual repo files.
    - No secrets or credentials are involved in branding tests.
"""

import dataclasses
import json
import pathlib
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def branding():
    """Return the live BRANDING singleton."""
    from forge.branding import BRANDING
    return BRANDING


@pytest.fixture
def canonical_json():
    """Load and return the canonical JSON spec as a dict."""
    from forge.branding import _canonical_spec_path, _read_canonical_spec
    path = _canonical_spec_path()
    return _read_canonical_spec(path)


@pytest.fixture
def branding_payload():
    """Return the flat branding payload extracted from the canonical spec."""
    from forge.branding import (
        _canonical_spec_path,
        _read_canonical_spec,
        _extract_branding_payload,
    )
    path = _canonical_spec_path()
    spec = _read_canonical_spec(path)
    return _extract_branding_payload(spec)


# ---------------------------------------------------------------------------
# 1. Frozen dataclass behavior
# ---------------------------------------------------------------------------

class TestBrandingFrozen:
    def test_branding_is_frozen(self, branding):
        """Attribute assignment on the frozen dataclass raises FrozenInstanceError."""
        with pytest.raises(dataclasses.FrozenInstanceError):
            branding.primary_name = "Tampered"


# ---------------------------------------------------------------------------
# 2. Field types and content
# ---------------------------------------------------------------------------

class TestFieldTypes:
    def test_all_fields_are_strings(self, branding):
        """Every field on the Branding instance is a str."""
        for field in dataclasses.fields(branding):
            value = getattr(branding, field.name)
            assert isinstance(value, str), (
                f"Field '{field.name}' is {type(value).__name__}, expected str"
            )

    def test_all_fields_are_non_empty(self, branding):
        """No field is empty or whitespace-only."""
        for field in dataclasses.fields(branding):
            value = getattr(branding, field.name)
            assert value.strip(), (
                f"Field '{field.name}' is empty or whitespace-only"
            )


# ---------------------------------------------------------------------------
# 3. Singleton identity
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_singleton_identity(self):
        """BRANDING is the same object across imports."""
        from forge.branding import BRANDING as b1
        from forge.branding import BRANDING as b2
        assert b1 is b2

    def test_get_branding_returns_singleton(self):
        """get_branding() returns the exact same object as BRANDING."""
        from forge.branding import BRANDING, get_branding
        assert get_branding() is BRANDING


# ---------------------------------------------------------------------------
# 4. Fields match canonical JSON
# ---------------------------------------------------------------------------

class TestFieldsMatchCanonical:
    def test_fields_match_canonical_json(self, branding, branding_payload):
        """Every Branding field matches the value derived from the canonical JSON."""
        for field in dataclasses.fields(branding):
            actual = getattr(branding, field.name)
            expected = branding_payload[field.name]
            assert actual == expected, (
                f"Field '{field.name}': got {actual!r}, expected {expected!r}"
            )


# ---------------------------------------------------------------------------
# 5. Specific field value format assertions
# ---------------------------------------------------------------------------

class TestSpecificFieldFormats:
    def test_primary_name_value(self, branding):
        """primary_name is 'Forge'."""
        assert branding.primary_name == "Forge"

    def test_full_display_name_contains_em_dash(self, branding):
        """full_display_name contains an em-dash (U+2014)."""
        assert "\u2014" in branding.full_display_name

    def test_kebab_case_format(self, branding):
        """kebab_case is all lowercase with hyphens, no underscores or spaces."""
        value = branding.kebab_case
        assert value == value.lower(), "kebab_case must be lowercase"
        assert " " not in value, "kebab_case must not contain spaces"
        assert "_" not in value, "kebab_case must not contain underscores"
        assert "-" in value, "kebab_case must contain at least one hyphen"

    def test_screaming_snake_format(self, branding):
        """screaming_snake_case is all uppercase with underscores."""
        value = branding.screaming_snake_case
        assert value == value.upper(), "screaming_snake_case must be uppercase"
        assert "_" in value, "screaming_snake_case must contain underscores"
        assert "-" not in value, "screaming_snake_case must not contain hyphens"
        assert " " not in value, "screaming_snake_case must not contain spaces"

    def test_bundle_id_prefix_format(self, branding):
        """bundle_id_prefix is a valid reverse-DNS identifier."""
        value = branding.bundle_id_prefix
        assert value.count(".") >= 2, (
            f"bundle_id_prefix must have at least 2 dots: {value!r}"
        )
        assert value == value.lower(), "bundle_id_prefix must be lowercase"
        assert " " not in value, "bundle_id_prefix must not contain spaces"

    def test_branch_prefix_ends_with_slash(self, branding):
        """branch_prefix ends with '/' for clean branch naming."""
        assert branding.branch_prefix.endswith("/"), (
            f"branch_prefix must end with '/': {branding.branch_prefix!r}"
        )


# ---------------------------------------------------------------------------
# 6. Validation error paths
# ---------------------------------------------------------------------------

class TestValidationErrors:
    def test_missing_json_key_raises_value_error(self):
        """_validate_spec_payload raises ValueError if a required key is missing."""
        from forge.branding import _validate_spec_payload, _EXPECTED_FIELDS
        # Build a payload missing one key
        payload = {k: "dummy" for k in _EXPECTED_FIELDS}
        key_to_remove = sorted(_EXPECTED_FIELDS)[0]
        del payload[key_to_remove]

        with pytest.raises(ValueError, match=r"Missing required branding keys"):
            _validate_spec_payload(payload)

    def test_non_string_value_raises_value_error(self):
        """_validate_spec_payload raises ValueError if any value is not a str."""
        from forge.branding import _validate_spec_payload, _EXPECTED_FIELDS
        payload = {k: "valid" for k in _EXPECTED_FIELDS}
        # Set one value to an int
        first_key = sorted(_EXPECTED_FIELDS)[0]
        payload[first_key] = 42

        with pytest.raises(ValueError, match=r"Non-string values"):
            _validate_spec_payload(payload)

    def test_empty_string_value_raises_value_error(self):
        """_validate_spec_payload raises ValueError if any value is empty."""
        from forge.branding import _validate_spec_payload, _EXPECTED_FIELDS
        payload = {k: "valid" for k in _EXPECTED_FIELDS}
        first_key = sorted(_EXPECTED_FIELDS)[0]
        payload[first_key] = ""

        with pytest.raises(ValueError, match=r"Empty or whitespace-only"):
            _validate_spec_payload(payload)

    def test_whitespace_only_value_raises_value_error(self):
        """_validate_spec_payload raises ValueError if any value is whitespace-only."""
        from forge.branding import _validate_spec_payload, _EXPECTED_FIELDS
        payload = {k: "valid" for k in _EXPECTED_FIELDS}
        first_key = sorted(_EXPECTED_FIELDS)[0]
        payload[first_key] = "   \t\n  "

        with pytest.raises(ValueError, match=r"Empty or whitespace-only"):
            _validate_spec_payload(payload)


# ---------------------------------------------------------------------------
# 7. File and JSON error paths
# ---------------------------------------------------------------------------

class TestFileErrors:
    def test_missing_json_file_raises_file_not_found(self, tmp_path):
        """_read_canonical_spec raises FileNotFoundError for a missing file."""
        from forge.branding import _read_canonical_spec
        bogus_path = tmp_path / "nonexistent" / "canonical_name_spec.json"

        with pytest.raises(FileNotFoundError, match=r"Canonical branding spec not found"):
            _read_canonical_spec(bogus_path)

    def test_malformed_json_raises_error(self, tmp_path):
        """_read_canonical_spec raises json.JSONDecodeError for invalid JSON."""
        from forge.branding import _read_canonical_spec
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{not valid json!!!", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            _read_canonical_spec(bad_file)


# ---------------------------------------------------------------------------
# 8. Extra fields and field count
# ---------------------------------------------------------------------------

class TestSchemaIntegrity:
    def test_no_extra_fields_in_json_ignored_silently(self, branding_payload):
        """Extra keys in the payload beyond the 17 expected do not cause errors.

        This test adds an extra key to a valid payload and confirms that
        _validate_spec_payload and _build_branding still succeed.
        """
        from forge.branding import _validate_spec_payload, _build_branding

        # Add an extra key not in the dataclass
        extended_payload = dict(branding_payload)
        extended_payload["future_field"] = "something_new"

        # Validation should pass (it only checks expected fields)
        _validate_spec_payload(extended_payload)

        # Build should succeed and ignore the extra key
        result = _build_branding(extended_payload)
        assert not hasattr(result, "future_field")

    def test_dataclass_field_count_matches_expected(self):
        """Branding has exactly 17 fields."""
        from forge.branding import Branding
        fields = dataclasses.fields(Branding)
        assert len(fields) == 17, (
            f"Expected 17 fields on Branding, got {len(fields)}: "
            f"{[f.name for f in fields]}"
        )
