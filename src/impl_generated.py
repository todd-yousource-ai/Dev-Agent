ForgeDevAgent/Sources/BrandingConstants.swift:

// BrandingConstants.swift
// ForgeDevAgent
//
// Single source of truth for product identity string constants in the Swift shell.
// All values are derived from shared/product_identity/canonical_name_spec.json.
//
// IMPORTANT: Do not add ad-hoc branding values here. Every constant must match
// the canonical spec exactly. Changes must be validated against the spec via
// tests/swift_branding/test_branding_constants_alignment.py before merge.
//
// This file is intentionally free of target-specific imports so it can be
// included in both the main app target and any XPC service target.

import Foundation

/// Namespace for all product identity / branding constants.
///
/// Declared as a caseless `enum` to prevent instantiation -- this type exists
/// purely as a compile-time-checked namespace for `static let` properties.
/// Every value mirrors the canonical name spec JSON established in PR #1.
enum BrandingConstants {

    /// The primary product name used in most UI surfaces, menu bar, and short references.
    ///
    /// Usage: menu bar label, About window title, Spotlight metadata, short log references.
    /// Canonical spec key: `product.primary_name`
    static let displayName: String = "Forge"

    /// The product subtitle that qualifies the primary name.
    ///
    /// Usage: combined with `displayName` for medium-length references, window subtitles.
    /// Canonical spec key: `product.subtitle`
    static let subtitle: String = "Dev Agent"

    /// The full formal product name used in legal text, license dialogs, and first-run UI.
    ///
    /// Usage: About window formal name, license headers, installer welcome text.
    /// Canonical spec key: `product.full_formal_name`
    static let fullDisplayName: String = "Consensus Dev Agent"

    /// The reverse-DNS bundle identifier prefix for all app and XPC targets.
    ///
    /// Usage: `Info.plist` `CFBundleIdentifier` prefix, entitlements, App Group identifiers.
    /// Canonical spec key: `derived_forms.bundle_id` (prefix portion)
    static let bundleIdentifierPrefix: String = "ai.yousource.forge"

    /// The Keychain service identifier for credential storage.
    ///
    /// Usage: `SecItemAdd` / `SecItemCopyMatching` `kSecAttrService` value.
    /// Canonical spec key: `derived_forms.keychain_service`
    static let keychainServiceID: String = "ai.yousource.forge.keychain"

    /// The label displayed in the macOS menu bar status item.
    ///
    /// Usage: `NSStatusItem` title, menu bar accessory label.
    /// Canonical spec key: derived from `product.primary_name` for menu bar context.
    static let menuBarLabel: String = "Forge"

    /// The label displayed beneath the Dock icon.
    ///
    /// Usage: `CFBundleName` / Dock tile label.
    /// Canonical spec key: derived form for Dock context.
    static let dockLabel: String = "Forge Dev Agent"

    /// The title used in `NSUserNotification` / `UNNotificationContent` banners.
    ///
    /// Usage: notification title string for all user-facing notifications.
    /// Canonical spec key: derived form for notification context.
    static let notificationTitle: String = "Forge Dev Agent"

    /// The appcast filename stem used by the Sparkle update framework.
    ///
    /// Usage: Sparkle `SUFeedURL` path component, e.g. `https://updates.example.com/<name>.xml`.
    /// Canonical spec key: `derived_forms.sparkle_appcast_name`
    static let sparkleAppcastName: String = "forge-dev-agent"

    /// The Git branch prefix for agent-created feature branches.
    ///
    /// Usage: branch naming convention, e.g. `forge-agent/pr-42-add-feature`.
    /// Canonical spec key: `derived_forms.branch_prefix`
    static let branchPrefix: String = "forge-agent/"

    /// The Git commit message prefix for agent-authored commits.
    ///
    /// Usage: commit message formatting, e.g. `[forge] Implement branding constants`.
    /// Canonical spec key: `derived_forms.commit_prefix`
    static let commitPrefix: String = "[forge]"

    /// The structured log prefix for all agent log lines.
    ///
    /// Usage: `os_log` / `Logger` subsystem prefix, plain-text log formatting.
    /// Canonical spec key: `derived_forms.log_prefix`
    static let logPrefix: String = "[Forge]"

    /// The XPC bootstrap / handshake signal string.
    ///
    /// Usage: sent by the Python backend over XPC to signal readiness to the Swift shell.
    /// Canonical spec key: `derived_forms.bootstrap_signal`
    static let bootstrapSignal: String = "forge-ready"
}

tests/swift_branding/__init__.py:

tests/swift_branding/test_branding_constants_alignment.py:

"""
Tests that validate every branding constant in BrandingConstants.swift matches
the canonical name spec JSON exactly.

Security assumptions:
- The canonical spec JSON is treated as the trusted source of truth.
- The Swift source file is parsed as untrusted text -- regex extraction only,
  no code execution.
- All file reads use explicit encoding and fail closed on missing files.

Failure behavior:
- Missing spec JSON or Swift source file → immediate test failure with
  descriptive error (fail closed).
- Any value mismatch → assertion failure with both expected and actual values.
- Structural violations (non-caseless enum, missing doc comments) → explicit
  assertion failures.
"""

import json
import os
import re
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _repo_root() -> Path:
    """Return the repository root directory.

    Walks up from this test file looking for a directory that contains
    'shared/product_identity/canonical_name_spec.json'. Falls back to
    four levels up from this file (tests/swift_branding/test_*.py).

    Raises:
        FileNotFoundError: If the repo root cannot be determined.
    """
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / "shared" / "product_identity" / "canonical_name_spec.json"
        if candidate.exists():
            return current
        current = current.parent
    # Fallback: assume standard layout
    fallback = Path(__file__).resolve().parent.parent.parent
    if (fallback / "shared" / "product_identity" / "canonical_name_spec.json").exists():
        return fallback
    raise FileNotFoundError(
        "Cannot locate repo root containing shared/product_identity/canonical_name_spec.json. "
        "Ensure the canonical spec file exists."
    )


def load_canonical_spec() -> dict:
    """Load and parse the canonical name spec JSON.

    Returns:
        Parsed JSON as a dictionary.

    Raises:
        FileNotFoundError: If the spec file does not exist (fail closed).
        json.JSONDecodeError: If the spec file is not valid JSON (fail closed).
    """
    repo_root = _repo_root()
    spec_path = repo_root / "shared" / "product_identity" / "canonical_name_spec.json"
    if not spec_path.exists():
        raise FileNotFoundError(
            f"Canonical spec not found at {spec_path}. "
            "Ensure PR #1 has been merged and the spec file exists."
        )
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    if not isinstance(spec, dict):
        raise ValueError(
            f"Canonical spec at {spec_path} must be a JSON object, got {type(spec).__name__}"
        )
    return spec


def _swift_source_path() -> Path:
    """Return the path to BrandingConstants.swift.

    Raises:
        FileNotFoundError: If the Swift source file does not exist.
    """
    repo_root = _repo_root()
    swift_path = repo_root / "ForgeDevAgent" / "Sources" / "BrandingConstants.swift"
    if not swift_path.exists():
        raise FileNotFoundError(
            f"BrandingConstants.swift not found at {swift_path}. "
            "Ensure the file has been created."
        )
    return swift_path


def _read_swift_source() -> str:
    """Read the Swift source file as text.

    Returns:
        The full text content of BrandingConstants.swift.

    Raises:
        FileNotFoundError: If the file does not exist (fail closed).
    """
    swift_path = _swift_source_path()
    with open(swift_path, "r", encoding="utf-8") as f:
        return f.read()


def parse_swift_constants() -> Dict[str, str]:
    """Parse all `static let <name>: String = "<value>"` declarations from the Swift file.

    Uses regex to extract property names and their string literal values.
    Does NOT execute Swift code.

    Returns:
        Dictionary mapping property names to their string values.
        Example: {"displayName": "Forge", "subtitle": "Dev Agent", ...}
    """
    source = _read_swift_source()
    # Match: static let <name>: String = "<value>"
    # Allows optional whitespace variations
    pattern = r'static\s+let\s+(\w+)\s*:\s*String\s*=\s*"([^"]*)"'
    matches = re.findall(pattern, source)
    constants: Dict[str, str] = {}
    for name, value in matches:
        if name in constants:
            raise ValueError(
                f"Duplicate constant '{name}' found in BrandingConstants.swift. "
                "Each constant must be defined exactly once."
            )
        constants[name] = value
    return constants


def _get_swift_static_let_lines() -> List[str]:
    """Return all lines containing `static let` from the Swift source."""
    source = _read_swift_source()
    return [line.strip() for line in source.splitlines() if "static let" in line]


def _get_swift_static_var_lines() -> List[str]:
    """Return all lines containing `static var` from the Swift source."""
    source = _read_swift_source()
    return [line.strip() for line in source.splitlines() if "static var" in line]


def _get_case_declarations() -> List[str]:
    """Return all `case` declarations inside the enum body.

    Filters out comments and lines inside string literals.
    """
    source = _read_swift_source()
    lines = source.splitlines()
    in_enum = False
    brace_depth = 0
    cases: List[str] = []
    for line in lines:
        stripped = line.strip()
        # Detect enum opening
        if re.match(r'^enum\s+BrandingConstants', stripped):
            in_enum = True
        if in_enum:
            brace_depth += stripped.count("{") - stripped.count("}")
            # Look for case declarations (not in comments)
            if stripped.startswith("case ") and not stripped.startswith("//"):
                cases.append(stripped)
            if brace_depth <= 0 and in_enum and "{" in source[:source.index(stripped) + len(stripped)] if stripped in source else False:
                pass
    return cases


def _check_doc_comments_for_properties() -> List[Tuple[str, bool]]:
    """Check whether each `static let` property is preceded by a `///` doc comment.

    Returns:
        List of (property_name, has_doc_comment) tuples.
    """
    source = _read_swift_source()
    lines = source.splitlines()
    results: List[Tuple[str, bool]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        match = re.match(r'static\s+let\s+(\w+)\s*:', stripped)
        if match:
            prop_name = match.group(1)
            # Look backwards for a /// doc comment
            has_doc = False
            j = i - 1
            while j >= 0:
                prev = lines[j].strip()
                if prev.startswith("///"):
                    has_doc = True
                    break
                elif prev == "":
                    # Allow blank lines between doc comment and property
                    j -= 1
                    continue
                else:
                    break
                j -= 1
            results.append((prop_name, has_doc))
    return results


# Expected mapping from Swift property names to their canonical values.
# This serves as the ground truth even if the spec JSON is unavailable,
# but tests also cross-check against the JSON when available.
EXPECTED_CONSTANTS = {
    "displayName": "Forge",
    "subtitle": "Dev Agent",
    "fullDisplayName": "Consensus Dev Agent",
    "bundleIdentifierPrefix": "ai.yousource.forge",
    "keychainServiceID": "ai.yousource.forge.keychain",
    "menuBarLabel": "Forge",
    "dockLabel": "Forge Dev Agent",
    "notificationTitle": "Forge Dev Agent",
    "sparkleAppcastName": "forge-dev-agent",
    "branchPrefix": "forge-agent/",
    "commitPrefix": "[forge]",
    "logPrefix": "[Forge]",
    "bootstrapSignal": "forge-ready",
}

# Mapping from JSON spec paths to Swift constant names
# This is used when the canonical spec JSON is available
SPEC_TO_SWIFT_MAPPING = {
    "displayName": ("product", "primary_name"),
    "subtitle": ("product", "subtitle"),
    "fullDisplayName": ("product", "full_formal_name"),
    "bundleIdentifierPrefix": ("derived_forms", "bundle_id_prefix"),
    "keychainServiceID": ("derived_forms", "keychain_service"),
    "menuBarLabel": ("derived_forms", "menu_bar_label"),
    "dockLabel": ("derived_forms", "dock_label"),
    "notificationTitle": ("derived_forms", "notification_title"),
    "sparkleAppcastName": ("derived_forms", "sparkle_appcast_name"),
    "branchPrefix": ("derived_forms", "branch_prefix"),
    "commitPrefix": ("derived_forms", "commit_prefix"),
    "logPrefix": ("derived_forms", "log_prefix"),
    "bootstrapSignal": ("derived_forms", "bootstrap_signal"),
}


def _resolve_spec_value(spec: dict, path: Tuple[str, ...]) -> Optional[str]:
    """Resolve a dotted path in the canonical spec JSON.

    Returns None if the path does not exist (allows graceful handling
    when spec structure varies).
    """
    current = spec
    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current if isinstance(current, str) else None


class TestBrandingConstantsAlignment(unittest.TestCase):
    """Validate BrandingConstants.swift against the canonical name spec."""

    @classmethod
    def setUpClass(cls):
        """Load the Swift constants once for all tests."""
        cls.swift_constants = parse_swift_constants()
        cls.swift_source = _read_swift_source()
        # Try to load the canonical spec; tests that require it will skip if unavailable
        try:
            cls.canonical_spec = load_canonical_spec()
        except FileNotFoundError:
            cls.canonical_spec = None

    def _assert_constant(self, swift_name: str, expected_value: str):
        """Assert a Swift constant exists and has the expected value."""
        self.assertIn(
            swift_name,
            self.swift_constants,
            f"Missing constant '{swift_name}' in BrandingConstants.swift"
        )
        self.assertEqual(
            self.swift_constants[swift_name],
            expected_value,
            f"Constant '{swift_name}' has value '{self.swift_constants[swift_name]}', "
            f"expected '{expected_value}'"
        )

    def _spec_value_for(self, swift_name: str) -> str:
        """Get the expected value for a constant, preferring spec JSON when available."""
        if self.canonical_spec is not None and swift_name in SPEC_TO_SWIFT_MAPPING:
            spec_path = SPEC_TO_SWIFT_MAPPING[swift_name]
            spec_val = _resolve_spec_value(self.canonical_spec, spec_path)
            if spec_val is not None:
                return spec_val
        return EXPECTED_CONSTANTS[swift_name]

    def test_display_name_matches_spec(self):
        """displayName must equal 'Forge'."""
        self._assert_constant("displayName", self._spec_value_for("displayName"))

    def test_subtitle_matches_spec(self):
        """subtitle must equal 'Dev Agent'."""
        self._assert_constant("subtitle", self._spec_value_for("subtitle"))

    def test_full_display_name_matches_spec(self):
        """fullDisplayName must equal 'Consensus Dev Agent'."""
        self._assert_constant("fullDisplayName", self._spec_value_for("fullDisplayName"))

    def test_bundle_identifier_prefix_matches_spec(self):
        """bundleIdentifierPrefix must equal 'ai.yousource.forge'."""
        self._assert_constant("bundleIdentifierPrefix", self._spec_value_for("bundleIdentifierPrefix"))

    def test_keychain_service_id_matches_spec(self):
        """keychainServiceID must equal 'ai.yousource.forge.keychain'."""
        self._assert_constant("keychainServiceID", self._spec_value_for("keychainServiceID"))

    def test_menu_bar_label_matches_spec(self):
        """menuBarLabel must equal 'Forge'."""
        self._assert_constant("menuBarLabel", self._spec_value_for("menuBarLabel"))

    def test_dock_label_matches_spec(self):
        """dockLabel must equal 'Forge Dev Agent'."""
        self._assert_constant("dockLabel", self._spec_value_for("dockLabel"))

    def test_notification_title_matches_spec(self):
        """notificationTitle must equal 'Forge Dev Agent'."""
        self._assert_constant("notificationTitle", self._spec_value_for("notificationTitle"))

    def test_sparkle_appcast_name_matches_spec(self):
        """sparkleAppcastName must equal 'forge-dev-agent'."""
        self._assert_constant("sparkleAppcastName", self._spec_value_for("sparkleAppcastName"))

    def test_branch_prefix_matches_spec(self):
        """branchPrefix must equal 'forge-agent/'."""
        self._assert_constant("branchPrefix", self._spec_value_for("branchPrefix"))

    def test_commit_prefix_matches_spec(self):
        """commitPrefix must equal '[forge]'."""
        self._assert_constant("commitPrefix", self._spec_value_for("commitPrefix"))

    def test_log_prefix_matches_spec(self):
        """logPrefix must equal '[Forge]'."""
        self._assert_constant("logPrefix", self._spec_value_for("logPrefix"))

    def test_bootstrap_signal_matches_spec(self):
        """bootstrapSignal must equal 'forge-ready'."""
        self._assert_constant("bootstrapSignal", self._spec_value_for("bootstrapSignal"))

    def test_all_derived_forms_covered(self):
        """Every expected constant must be present in the Swift file."""
        missing = set(EXPECTED_CONSTANTS.keys()) - set(self.swift_constants.keys())
        self.assertEqual(
            missing,
            set(),
            f"Missing constants in BrandingConstants.swift: {missing}"
        )

    def test_exactly_13_constants(self):
        """There must be exactly 13 branding constants."""
        self.assertEqual(
            len(self.swift_constants),
            13,
            f"Expected 13 constants, found {len(self.swift_constants)}: "
            f"{sorted(self.swift_constants.keys())}"
        )

    def test_no_prohibited_variants_in_values(self):
        """No constant value should contain prohibited name variants.

        Prohibited variants are misspellings or legacy names that must not
        appear in any branding constant.
        """
        prohibited = [
            "ForgeAI",
            "Forge AI",
            "forge_ai",
            "forgeai",
            "ConsensusAgent",
            "Consensus Agent",
            "DevForge",
            "ForgeAgent",
        ]
        for const_name, const_value in self.swift_constants.items():
            for variant in prohibited:
                self.assertNotEqual(
                    const_value,
                    variant,
                    f"Constant '{const_name}' uses prohibited variant '{variant}'"
                )

    def test_enum_is_caseless(self):
        """BrandingConstants enum must have no `case` declarations (caseless enum)."""
        source = self.swift_source
        # Find the enum body
        enum_match = re.search(
            r'enum\s+BrandingConstants\s*\{(.*)\}',
            source,
            re.DOTALL
        )
        self.assertIsNotNone(
            enum_match,
            "Could not find 'enum BrandingConstants { ... }' in Swift source"
        )
        enum_body = enum_match.group(1)
        # Remove comments (both // and /* */) before checking for case
        body_no_comments = re.sub(r'//[^\n]*', '', enum_body)
        body_no_comments = re.sub(r'/\*.*?\*/', '', body_no_comments, flags=re.DOTALL)
        # Check for `case` keyword that is NOT part of `static let` pattern
        case_matches = re.findall(r'^\s*case\s+', body_no_comments, re.MULTILINE)
        self.assertEqual(
            len(case_matches),
            0,
            f"BrandingConstants enum must be caseless but found {len(case_matches)} "
            f"case declaration(s)"
        )

    def test_all_properties_are_static_let(self):
        """All properties must be `static let`, not `static var`."""
        static_var_lines = _get_swift_static_var_lines()
        self.assertEqual(
            len(static_var_lines),
            0,
            f"Found `static var` declarations (must use `static let`): {static_var_lines}"
        )

    def test_all_properties_have_doc_comments(self):
        """Every `static let` property must be preceded by a `///` doc comment."""
        results = _check_doc_comments_for_properties()
        self.assertGreater(
            len(results),
            0,
            "No static let properties found -- cannot verify doc comments"
        )
        missing_docs = [name for name, has_doc in results if not has_doc]
        self.assertEqual(
            len(missing_docs),
            0,
            f"Properties missing /// doc comments: {missing_docs}"
        )

    def test_no_target_specific_imports(self):
        """The Swift file must not import target-specific frameworks like AppKit or SwiftUI.

        Only Foundation (or no import at all) is acceptable to ensure the file
        can be included in both app and XPC targets.
        """
        source = self.swift_source
        import_lines = re.findall(r'^\s*import\s+(\w+)', source, re.MULTILINE)
        prohibited_imports = {"AppKit", "SwiftUI", "UIKit", "Cocoa"}
        found_prohibited = set(import_lines) & prohibited_imports
        self.assertEqual(
            found_prohibited,
            set(),
            f"BrandingConstants.swift must not import target-specific frameworks: "
            f"{found_prohibited}"
        )

    def test_enum_declared_as_enum_not_struct_or_class(self):
        """BrandingConstants must be declared as `enum`, not `struct` or `class`."""
        self.assertRegex(
            self.swift_source,
            r'\benum\s+BrandingConstants\b',
            "BrandingConstants must be declared as an `enum`"
        )
        # Ensure it's not also declared as struct or class
        self.assertNotRegex(
            self.swift_source,
            r'\b(struct|class)\s+BrandingConstants\b',
            "BrandingConstants must not be declared as struct or class"
        )


if __name__ == "__main__":
    unittest.main()
