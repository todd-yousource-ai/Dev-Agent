"""Tests for forge/branding.py -- canonical product branding constants."""

from __future__ import annotations

import dataclasses
import json
import copy
from pathlib import Path
from typing import Any, Dict

import pytest

from forge.branding import (
    Branding,
    BRANDING,
    get_branding,
    _canonical_spec_path,
    _load_and_validate,
    _REQUIRED_DERIVED_FORMS,
    _REQUIRED_USAGE_CONTEXTS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_canonical_json() -> Dict[str, Any]:
    """Load the canonical branding JSON spec independently of the module."""
    spec_path = _canonical_spec_path()
    with open(spec_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: Path, data: Any) -> None:
    """Write JSON data to *path*."""
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_valid_spec() -> Dict[str, Any]:
    """Return a deep copy of the canonical spec for mutation in tests."""
    return copy.deepcopy(_load_canonical_json())


def _tmp_spec_file(tmp_path: Path, data: Any) -> Path:
    """Write *data* as JSON to a temp file and return its path."""
    p = tmp_path / "branding_spec.json"
    _write_json(p, data)
    return p


def _tmp_raw_file(tmp_path: Path, content: str) -> Path:
    """Write raw string content to a temp file and return its path."""
    p = tmp_path / "branding_spec.json"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Happy-path field value tests
# ---------------------------------------------------------------------------

class TestBrandingFieldValues:
    def test_branding_primary_name(self) -> None:
        assert BRANDING.primary_name == "Forge"

    def test_branding_subtitle(self) -> None:
        assert BRANDING.subtitle == "Dev Agent"

    def test_branding_full_display_name(self) -> None:
        # Uses em dash (U+2014), not double hyphen
        assert BRANDING.full_display_name == "Forge \u2014 Dev Agent"

    def test_branding_full_formal_name(self) -> None:
        assert BRANDING.full_formal_name == "Consensus Dev Agent"

    def test_branding_pascal_case(self) -> None:
        assert BRANDING.pascal_case == "ForgeDevAgent"

    def test_branding_kebab_case(self) -> None:
        assert BRANDING.kebab_case == "forge-dev-agent"

    def test_branding_snake_case(self) -> None:
        assert BRANDING.snake_case == "forge_dev_agent"

    def test_branding_screaming_snake(self) -> None:
        assert BRANDING.screaming_snake == "FORGE_DEV_AGENT"

    def test_branding_camel_case(self) -> None:
        assert BRANDING.camel_case == "forgeDevAgent"

    def test_branding_bundle_id_prefix(self) -> None:
        assert BRANDING.bundle_id_prefix.startswith("ai.yousource")

    def test_branding_keychain_service(self) -> None:
        assert isinstance(BRANDING.keychain_service, str)
        assert len(BRANDING.keychain_service) > 0


# ---------------------------------------------------------------------------
# Usage-context field tests
# ---------------------------------------------------------------------------

class TestBrandingUsageContexts:
    def test_branding_branch_prefix(self) -> None:
        spec = _load_canonical_json()
        expected = spec["usage_contexts"]["git_branch"]
        assert BRANDING.branch_prefix == expected

    def test_branding_commit_prefix(self) -> None:
        spec = _load_canonical_json()
        expected = spec["usage_contexts"]["git_commit"]
        assert BRANDING.commit_prefix == expected

    def test_branding_ci_workflow_prefix(self) -> None:
        spec = _load_canonical_json()
        expected = spec["usage_contexts"]["ci_workflow"]
        assert BRANDING.ci_workflow_prefix == expected

    def test_branding_sparkle_appcast_name(self) -> None:
        spec = _load_canonical_json()
        expected = spec["usage_contexts"]["sparkle_appcast"]
        assert BRANDING.sparkle_appcast_name == expected

    def test_branding_notification_title(self) -> None:
        spec = _load_canonical_json()
        expected = spec["usage_contexts"]["notification"]
        assert BRANDING.notification_title == expected

    def test_branding_dock_label(self) -> None:
        spec = _load_canonical_json()
        expected = spec["usage_contexts"]["dock"]
        assert BRANDING.dock_label == expected

    def test_branding_menu_bar_label(self) -> None:
        spec = _load_canonical_json()
        expected = spec["usage_contexts"]["menu_bar"]
        assert BRANDING.menu_bar_label == expected

    def test_branding_log_prefix(self) -> None:
        spec = _load_canonical_json()
        expected = spec["usage_contexts"]["log"]
        assert BRANDING.log_prefix == expected

    def test_branding_bootstrap_signal(self) -> None:
        spec = _load_canonical_json()
        expected = spec["usage_contexts"]["bootstrap"]
        assert BRANDING.bootstrap_signal == expected


# ---------------------------------------------------------------------------
# Singleton / immutability tests
# ---------------------------------------------------------------------------

class TestBrandingSingleton:
    def test_get_branding_returns_singleton(self) -> None:
        assert get_branding() is BRANDING

    def test_branding_singleton_is_frozen(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            BRANDING.primary_name = "X"  # type: ignore[misc]

    def test_branding_is_immutable(self) -> None:
        attrs_to_try = ["primary_name", "subtitle", "kebab_case", "bundle_id_prefix"]
        for attr in attrs_to_try:
            with pytest.raises(dataclasses.FrozenInstanceError):
                object.__setattr__(BRANDING, attr, "tampered")


# ---------------------------------------------------------------------------
# Cross-validation against canonical JSON
# ---------------------------------------------------------------------------

class TestBrandingCanonicalJson:
    def test_branding_matches_canonical_json(self) -> None:
        spec = _load_canonical_json()
        derived_forms = {d["form"]: d["value"] for d in spec["derived_forms"]}

        # Product-level fields
        assert BRANDING.primary_name == spec["product"]["primary_name"]
        assert BRANDING.subtitle == spec["product"]["subtitle"]
        assert BRANDING.full_display_name == spec["product"]["full_display_name"]
        assert BRANDING.full_formal_name == spec["product"]["full_formal_name"]

        # Derived forms
        assert BRANDING.pascal_case == derived_forms["PascalCase"]
        assert BRANDING.camel_case == derived_forms["camelCase"]
        assert BRANDING.kebab_case == derived_forms["kebab-case"]
        assert BRANDING.snake_case == derived_forms["snake_case"]
        assert BRANDING.screaming_snake == derived_forms["SCREAMING_SNAKE"]
        assert BRANDING.bundle_id_prefix == derived_forms["bundle_id"]
        assert BRANDING.keychain_service == derived_forms["keychain_service"]

    def test_all_fields_are_non_empty_strings(self) -> None:
        for field in dataclasses.fields(BRANDING):
            value = getattr(BRANDING, field.name)
            assert isinstance(value, str), f"{field.name} is not str: {type(value)}"
            assert len(value) > 0, f"{field.name} is empty"

    def test_derived_forms_indexed_by_form_key_not_position(self) -> None:
        """Verify the loader uses form names, not list indices."""
        spec = _load_canonical_json()
        derived_forms = {d["form"]: d["value"] for d in spec["derived_forms"]}
        for form_name in _REQUIRED_DERIVED_FORMS:
            assert form_name in derived_forms, f"Missing derived form: {form_name}"


# ---------------------------------------------------------------------------
# Security tests
# ---------------------------------------------------------------------------

class TestBrandingSecurity:
    def test_no_field_contains_prohibited_variant(self) -> None:
        spec = _load_canonical_json()
        prohibited = set(spec.get("prohibited_variants", []))
        if not prohibited:
            pytest.skip("No prohibited_variants in canonical spec")
        for field in dataclasses.fields(BRANDING):
            value = getattr(BRANDING, field.name)
            assert value not in prohibited, (
                f"Field {field.name!r} value {value!r} is in prohibited_variants"
            )

    def test_canonical_spec_path_resolves_expected_file(self) -> None:
        spec_path = _canonical_spec_path()
        assert spec_path.exists(), f"Spec path does not exist: {spec_path}"
        assert spec_path.is_file(), f"Spec path is not a file: {spec_path}"
        # Must be within the repository tree (relative to forge package)
        forge_pkg = Path(__file__).resolve().parent.parent / "forge"
        # spec_path should be relative to the repo root
        try:
            spec_path.resolve().relative_to(forge_pkg.parent)
        except ValueError:
            pytest.fail(
                f"Spec path {spec_path} is outside the repository root"
            )

    def test_bundle_id_starts_with_org_prefix(self) -> None:
        assert BRANDING.bundle_id_prefix.startswith("ai.yousource")


# ---------------------------------------------------------------------------
# Negative / failure-mode tests
# ---------------------------------------------------------------------------

class TestBrandingLoadFailures:
    def test_load_fails_on_missing_json(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        nonexistent = tmp_path / "does_not_exist.json"
        monkeypatch.setattr("forge.branding._canonical_spec_path", lambda: nonexistent)
        with pytest.raises(FileNotFoundError):
            _load_and_validate()

    def test_load_fails_on_malformed_json(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        bad_file = _tmp_raw_file(tmp_path, '{"truncated": ')
        monkeypatch.setattr("forge.branding._canonical_spec_path", lambda: bad_file)
        with pytest.raises((json.JSONDecodeError, ValueError)):
            _load_and_validate()

    def test_load_fails_on_missing_required_key(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        spec = _make_valid_spec()
        del spec["product"]
        p = _tmp_spec_file(tmp_path, spec)
        monkeypatch.setattr("forge.branding._canonical_spec_path", lambda: p)
        with pytest.raises((KeyError, ValueError)):
            _load_and_validate()

    def test_load_fails_on_missing_required_derived_form(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        spec = _make_valid_spec()
        # Remove PascalCase from derived_forms
        spec["derived_forms"] = [
            d for d in spec["derived_forms"] if d.get("form") != "PascalCase"
        ]
        p = _tmp_spec_file(tmp_path, spec)
        monkeypatch.setattr("forge.branding._canonical_spec_path", lambda: p)
        with pytest.raises(ValueError, match="(?i)pascalcase|PascalCase"):
            _load_and_validate()

    def test_load_fails_on_empty_string_value(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        spec = _make_valid_spec()
        spec["product"]["primary_name"] = ""
        p = _tmp_spec_file(tmp_path, spec)
        monkeypatch.setattr("forge.branding._canonical_spec_path", lambda: p)
        with pytest.raises(ValueError):
            _load_and_validate()

    def test_load_fails_on_non_string_value(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        spec = _make_valid_spec()
        spec["product"]["primary_name"] = 42
        p = _tmp_spec_file(tmp_path, spec)
        monkeypatch.setattr("forge.branding._canonical_spec_path", lambda: p)
        with pytest.raises(ValueError):
            _load_and_validate()

    def test_load_fails_on_wrong_canonical_values(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        spec = _make_valid_spec()
        spec["product"]["primary_name"] = "NotForge"
        p = _tmp_spec_file(tmp_path, spec)
        monkeypatch.setattr("forge.branding._canonical_spec_path", lambda: p)
        with pytest.raises(ValueError):
            _load_and_validate()
