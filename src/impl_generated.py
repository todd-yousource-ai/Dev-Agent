"""Canonical product branding constants for Forge backend code.

Security assumptions:
- The canonical JSON specification is untrusted input until validated.
- This module fails closed at import time if the specification is missing,
  malformed, incomplete, or inconsistent with required canonical values.
- No fallback values are used; callers either receive a fully validated,
  immutable Branding singleton or import fails with explicit context.

Failure behavior:
- Raises FileNotFoundError when the canonical specification file does not exist.
- Raises ValueError when JSON is malformed, schema is unsupported, fields are
  missing/empty/wrongly typed, or canonical values do not match expectations.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, FrozenSet


_SUPPORTED_SCHEMA_VERSION = "1.0"

_REQUIRED_DERIVED_FORMS: FrozenSet[str] = frozenset(
    {
        "PascalCase",
        "camelCase",
        "kebab-case",
        "snake_case",
        "SCREAMING_SNAKE",
        "bundle_id",
        "keychain_service",
    }
)

_REQUIRED_USAGE_CONTEXTS: FrozenSet[str] = frozenset(
    {
        "git_branch",
        "git_commit",
        "ci_workflow",
        "sparkle_appcast",
        "notification",
        "dock",
        "menu_bar",
        "log",
        "bootstrap",
    }
)

_EXPECTED_PRODUCT_VALUES: Dict[str, str] = {
    "primary_name": "Forge",
    "subtitle": "Dev Agent",
    "full_display_name": "Forge -- Dev Agent",
    "full_formal_name": "Consensus Dev Agent",
}

_EXPECTED_DERIVED_VALUES: Dict[str, str] = {
    "PascalCase": "ForgeDevAgent",
    "kebab-case": "forge-dev-agent",
}


@dataclass(frozen=True, slots=True)
class Branding:
    """Immutable, validated product identity constants.

    Security assumptions:
    - Every field is sourced from the canonical JSON specification and validated
      as a non-empty string before object construction.
    - Instances are immutable (`frozen=True`) and slot-based (`slots=True`) to
      prevent runtime mutation and accidental attribute injection.

    Failure behavior:
    - This dataclass performs no internal recovery. Invalid inputs must be
      rejected by `_load_and_validate()` before instantiation.
    """

    primary_name: str
    subtitle: str
    full_display_name: str
    full_formal_name: str
    pascal_case: str
    camel_case: str
    kebab_case: str
    snake_case: str
    screaming_snake: str
    bundle_id_prefix: str
    keychain_service: str
    branch_prefix: str
    commit_prefix: str
    ci_workflow_prefix: str
    sparkle_appcast_name: str
    notification_title: str
    dock_label: str
    menu_bar_label: str
    log_prefix: str
    bootstrap_signal: str


def _canonical_spec_path() -> Path:
    """Return the resolved canonical branding specification path.

    Security assumptions:
    - Path resolution is deterministic and rooted relative to this package to
      avoid dependence on process working directory.
    - The returned path is not trusted until opened and validated.

    Failure behavior:
    - Returns a resolved Path object. File existence is checked by callers.
    """
    return (
        Path(__file__).resolve().parent.parent
        / "shared"
        / "product_identity"
        / "canonical_name_spec.json"
    )


def _require_mapping(value: object, field_name: str) -> Dict[str, Any]:
    """Validate that a value is a JSON object-like mapping.

    Security assumptions:
    - External JSON content is untrusted and must be type-checked before field
      access to prevent ambiguous failures and schema confusion.

    Failure behavior:
    - Raises ValueError with field context if the value is not a dict.
    """
    if not isinstance(value, dict):
        raise ValueError(
            f"Expected {field_name} to be an object/dict, got {type(value).__name__}"
        )
    return value


def _require_string(value: object, field_name: str) -> str:
    """Validate that a value is a non-empty string.

    Security assumptions:
    - Identity constants must be explicit strings; empty values are rejected to
      prevent silent degradation or fallback behavior in downstream consumers.

    Failure behavior:
    - Raises ValueError with field context if the value is not a string or is
      empty/whitespace-only.
    """
    if not isinstance(value, str):
        raise ValueError(
            f"Expected {field_name} to be a non-empty string, got {type(value).__name__}"
        )
    if value.strip() == "":
        raise ValueError(f"Expected {field_name} to be a non-empty string, got empty value")
    return value


def _build_derived_forms_index(spec: Dict[str, Any]) -> Dict[str, str]:
    """Build an index of derived form name to value, strictly requiring a list.

    Security assumptions:
    - The canonical specification requires derived_forms to be a list of objects.
      Dict input is rejected to enforce strict schema compliance and reduce
      the accepted input surface.

    Failure behavior:
    - Raises ValueError if derived_forms is missing, not a list, or contains
      entries with invalid structure/types.
    """
    derived_forms = spec.get("derived_forms")
    if not isinstance(derived_forms, list):
        raise ValueError(
            f"Expected derived_forms to be a list, got {type(derived_forms).__name__}"
        )

    index: Dict[str, str] = {}
    for i, entry in enumerate(derived_forms):
        entry_mapping = _require_mapping(entry, f"derived_forms[{i}]")
        form = _require_string(entry_mapping.get("form"), f"derived_forms[{i}].form")
        value = _require_string(entry_mapping.get("value"), f"derived_forms[{i}].value")
        if form in index:
            raise ValueError(f"Duplicate derived form: {form!r} at derived_forms[{i}]")
        index[form] = value

    return index


def _extract_usage_context(
    usage_contexts: Dict[str, Any], context_name: str, field: str = "display_value"
) -> str:
    """Extract a usage context field by context name.

    Security assumptions:
    - Usage contexts are untrusted mappings and must be validated before use.
    - The requested field defaults to `display_value` per canonical contract.

    Failure behavior:
    - Raises ValueError if the named context is absent or the requested field
      is not a non-empty string.
    """
    if context_name not in usage_contexts:
        raise ValueError(f"Missing required usage context: usage_contexts.{context_name}")
    context_mapping = _require_mapping(
        usage_contexts[context_name], f"usage_contexts.{context_name}"
    )
    return _require_string(
        context_mapping.get(field), f"usage_contexts.{context_name}.{field}"
    )


def _validate_expected_value(actual: str, expected: str, field_name: str) -> None:
    """Enforce required canonical values for drift-sensitive identity fields.

    Security assumptions:
    - Certain identity constants are contractual and must never drift, even if
      the JSON file is modified unexpectedly.

    Failure behavior:
    - Raises ValueError with explicit expected/actual context on mismatch.
    """
    if actual != expected:
        raise ValueError(f"Expected {field_name}={expected!r}, got {actual!r}")


def _load_and_validate() -> Branding:
    """Load, validate, and construct the immutable Branding singleton.

    Security assumptions:
    - The canonical JSON file is the single source of truth but is treated as
      untrusted until schema, structure, types, and canonical values are
      validated.
    - No fallback defaults are permitted. Any inconsistency causes immediate
      import-time failure.

    Failure behavior:
    - Raises FileNotFoundError if the spec file is absent.
    - Raises ValueError if JSON is malformed or violates schema/value rules.
    - Propagates contextual exceptions without silent recovery.
    """
    spec_path = _canonical_spec_path()
    if not spec_path.is_file():
        raise FileNotFoundError(
            f"Canonical branding specification not found at path: {spec_path}"
        )

    try:
        with spec_path.open("r", encoding="utf-8") as handle:
            raw_spec = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Malformed JSON in canonical branding specification at {spec_path}: {exc}"
        ) from exc

    spec = _require_mapping(raw_spec, "root")

    schema_version = _require_string(spec.get("schema_version"), "schema_version")
    if schema_version != _SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported schema_version {schema_version!r} in {spec_path}; "
            f"expected {_SUPPORTED_SCHEMA_VERSION!r}"
        )

    product = _require_mapping(spec.get("product"), "product")

    # -- Extract and validate product fields ----------------------------------
    primary_name = _require_string(product.get("primary_name"), "product.primary_name")
    subtitle = _require_string(product.get("subtitle"), "product.subtitle")
    full_display_name = _require_string(
        product.get("full_display_name"), "product.full_display_name"
    )
    full_formal_name = _require_string(
        product.get("full_formal_name"), "product.full_formal_name"
    )

    for field_key, expected in _EXPECTED_PRODUCT_VALUES.items():
        actual = _require_string(product.get(field_key), f"product.{field_key}")
        _validate_expected_value(actual, expected, f"product.{field_key}")

    # -- Build derived forms index and validate -------------------------------
    derived_index = _build_derived_forms_index(spec)

    for form_name in _REQUIRED_DERIVED_FORMS:
        if form_name not in derived_index:
            raise ValueError(f"Missing required derived form: {form_name}")

    for form_name, expected in _EXPECTED_DERIVED_VALUES.items():
        _validate_expected_value(
            derived_index[form_name], expected, f"derived_forms.{form_name}"
        )

    pascal_case = derived_index["PascalCase"]
    camel_case = derived_index["camelCase"]
    kebab_case = derived_index["kebab-case"]
    snake_case = derived_index["snake_case"]
    screaming_snake = derived_index["SCREAMING_SNAKE"]
    bundle_id_prefix = derived_index["bundle_id"]
    keychain_service = derived_index["keychain_service"]

    # -- Validate usage contexts ----------------------------------------------
    usage_contexts = _require_mapping(spec.get("usage_contexts"), "usage_contexts")

    for context_name in _REQUIRED_USAGE_CONTEXTS:
        _extract_usage_context(usage_contexts, context_name)

    branch_prefix = _extract_usage_context(usage_contexts, "git_branch")
    commit_prefix = _extract_usage_context(usage_contexts, "git_commit")
    ci_workflow_prefix = _extract_usage_context(usage_contexts, "ci_workflow")
    sparkle_appcast_name = _extract_usage_context(usage_contexts, "sparkle_appcast")
    notification_title = _extract_usage_context(usage_contexts, "notification")
    dock_label = _extract_usage_context(usage_contexts, "dock")
    menu_bar_label = _extract_usage_context(usage_contexts, "menu_bar")
    log_prefix = _extract_usage_context(usage_contexts, "log")
    bootstrap_signal = _extract_usage_context(usage_contexts, "bootstrap")

    if not bundle_id_prefix.startswith("ai.yousource."):
        raise ValueError(
            f"Expected derived_forms.bundle_id to start with 'ai.yousource.', got {bundle_id_prefix!r}"
        )

    return Branding(
        primary_name=primary_name,
        subtitle=subtitle,
        full_display_name=full_display_name,
        full_formal_name=full_formal_name,
        pascal_case=pascal_case,
        camel_case=camel_case,
        kebab_case=kebab_case,
        snake_case=snake_case,
        screaming_snake=screaming_snake,
        bundle_id_prefix=bundle_id_prefix,
        keychain_service=keychain_service,
        branch_prefix=branch_prefix,
        commit_prefix=commit_prefix,
        ci_workflow_prefix=ci_workflow_prefix,
        sparkle_appcast_name=sparkle_appcast_name,
        notification_title=notification_title,
        dock_label=dock_label,
        menu_bar_label=menu_bar_label,
        log_prefix=log_prefix,
        bootstrap_signal=bootstrap_signal,
    )


BRANDING: Branding = _load_and_validate()


def get_branding() -> Branding:
    """Return the validated module-level Branding singleton.

    Security assumptions:
    - The singleton was fully validated at import time and is immutable.

    Failure behavior:
    - Returns the exact BRANDING object by identity. No copying or fallback.
    """
    return BRANDING
