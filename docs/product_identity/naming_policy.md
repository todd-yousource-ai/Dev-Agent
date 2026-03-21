I'll implement all three target files, ensuring every acceptance criterion is met.

--- FILE: shared/product_identity/canonical_name_spec.json ---

{
  "schema_version": "1.0.0",
  "organization": {
    "name": "YouSource.ai",
    "reverse_dns": "ai.yousource",
    "website": "https://yousource.ai"
  },
  "product": {
    "primary_name": "Forge",
    "subtitle": "Dev Agent",
    "full_formal_name": "Consensus Dev Agent",
    "tagline": "A native macOS AI coding agent that decomposes build intent into reviewed, gated pull requests."
  },
  "derived_forms": [
    {
      "form": "pascal_case",
      "value": "ConsensusDevAgent",
      "casing": "PascalCase -- each word capitalized, no separators",
      "contexts": [
        "swift_types",
        "class_prefixes",
        "documentation_anchors"
      ]
    },
    {
      "form": "camel_case",
      "value": "consensusDevAgent",
      "casing": "camelCase -- first word lowercase, subsequent words capitalized, no separators",
      "contexts": [
        "swift_variables",
        "json_keys",
        "javascript_identifiers"
      ]
    },
    {
      "form": "kebab_case",
      "value": "consensus-dev-agent",
      "casing": "kebab-case -- all lowercase, hyphen-separated",
      "contexts": [
        "cli_tool_name",
        "url_slugs",
        "npm_package",
        "github_repo"
      ]
    },
    {
      "form": "snake_case",
      "value": "consensus_dev_agent",
      "casing": "snake_case -- all lowercase, underscore-separated",
      "contexts": [
        "python_modules",
        "python_packages",
        "file_names",
        "database_identifiers"
      ]
    },
    {
      "form": "screaming_snake",
      "value": "CONSENSUS_DEV_AGENT",
      "casing": "SCREAMING_SNAKE_CASE -- all uppercase, underscore-separated",
      "contexts": [
        "environment_variables",
        "compile_time_constants",
        "preprocessor_macros"
      ]
    },
    {
      "form": "title_case",
      "value": "Consensus Dev Agent",
      "casing": "Title Case -- each word capitalized, space-separated",
      "contexts": [
        "ui_headings",
        "documentation_titles",
        "about_dialog",
        "marketing_copy"
      ]
    },
    {
      "form": "bundle_id",
      "value": "ai.yousource.forge",
      "casing": "Reverse-DNS notation -- lowercase, dot-separated, organization prefix first",
      "contexts": [
        "macos_app_bundle",
        "info_plist"
      ]
    },
    {
      "form": "reverse_dns_service",
      "value": "ai.yousource.forge.agent",
      "casing": "Reverse-DNS notation -- lowercase, dot-separated, with service suffix",
      "contexts": [
        "xpc_service_name",
        "launchd_label",
        "service_discovery"
      ]
    },
    {
      "form": "xpc_service",
      "value": "ai.yousource.forge.xpc",
      "casing": "Reverse-DNS notation -- lowercase, dot-separated, with xpc suffix",
      "contexts": [
        "xpc_mach_service",
        "entitlements"
      ]
    },
    {
      "form": "keychain_service",
      "value": "ai.yousource.forge",
      "casing": "Reverse-DNS notation -- matches bundle_id for Keychain access group consistency",
      "contexts": [
        "keychain_service_name",
        "keychain_access_group"
      ]
    },
    {
      "form": "cli_short",
      "value": "forge",
      "casing": "All lowercase, single word -- primary CLI invocation name",
      "contexts": [
        "cli_invocation",
        "shell_alias",
        "path_binary_name"
      ]
    },
    {
      "form": "ui_primary",
      "value": "Forge",
      "casing": "Capitalized single word -- primary UI-facing product name",
      "contexts": [
        "ui_app_name",
        "menu_bar",
        "dock_icon_label",
        "about_dialog"
      ]
    },
    {
      "form": "package_name",
      "value": "forge-agent",
      "casing": "kebab-case -- lowercase, hyphen-separated, with agent qualifier",
      "contexts": [
        "github_repo",
        "package_registry",
        "homebrew_formula"
      ]
    }
  ],
  "prohibited_variants": [
    {
      "variant": "ConsensusAgent",
      "reason": "Drops 'Dev' qualifier -- ambiguous, does not match any approved derived form"
    },
    {
      "variant": "ForgeAI",
      "reason": "Appends 'AI' to primary name -- not an approved form, conflates product name with technology descriptor"
    },
    {
      "variant": "forge_dev_agent",
      "reason": "Incorrect snake_case form -- approved snake_case is 'consensus_dev_agent'. Mixing 'forge' primary name with snake_case full name creates hybrid form."
    },
    {
      "variant": "CDA",
      "reason": "Unofficial acronym -- ambiguous, not searchable, not approved for any context"
    },
    {
      "variant": "cda",
      "reason": "Lowercase unofficial acronym -- same issues as 'CDA', additionally confusable with unrelated tools"
    },
    {
      "variant": "Forge AI Agent",
      "reason": "Invented multi-word form -- not an approved title case variant, adds 'AI' qualifier not present in formal name"
    },
    {
      "variant": "consensus-agent",
      "reason": "Drops 'dev' from kebab-case form -- approved kebab-case is 'consensus-dev-agent'"
    },
    {
      "variant": "FORGE_DEV_AGENT",
      "reason": "Incorrect screaming snake form -- approved SCREAMING_SNAKE is 'CONSENSUS_DEV_AGENT'. Do not mix primary name with full name casing."
    },
    {
      "variant": "forgeAgent",
      "reason": "Hybrid camelCase mixing primary name with qualifier -- approved camelCase is 'consensusDevAgent'"
    },
    {
      "variant": "Consensus_Dev_Agent",
      "reason": "Mixed case with underscores -- not a valid casing convention in any approved form"
    }
  ],
  "usage_contexts": {
    "swift_types": {
      "description": "Swift struct, class, enum, and protocol type names",
      "rules": "Use PascalCase derived form. Prefix internal types with the PascalCase form when namespacing is needed."
    },
    "class_prefixes": {
      "description": "Objective-C class prefixes and Swift type namespace prefixes",
      "rules": "Use PascalCase derived form as the prefix root."
    },
    "documentation_anchors": {
      "description": "Markdown heading anchors and cross-reference identifiers in documentation",
      "rules": "Use PascalCase derived form for programmatic anchors. Use title_case for human-readable headings."
    },
    "swift_variables": {
      "description": "Swift variable, constant, and function parameter names",
      "rules": "Use camelCase derived form."
    },
    "json_keys": {
      "description": "Keys in JSON configuration files and API payloads",
      "rules": "Use camelCase derived form for product identity references in JSON."
    },
    "javascript_identifiers": {
      "description": "JavaScript/TypeScript variable and function names",
      "rules": "Use camelCase derived form."
    },
    "cli_tool_name": {
      "description": "The name of the CLI binary as invoked from a shell",
      "rules": "Use kebab-case derived form for the full name. Use cli_short form ('forge') for the primary invocation command."
    },
    "url_slugs": {
      "description": "URL path segments in documentation sites, package registries, or APIs",
      "rules": "Use kebab-case derived form."
    },
    "npm_package": {
      "description": "npm or similar JavaScript package registry name",
      "rules": "Use kebab-case derived form."
    },
    "github_repo": {
      "description": "GitHub repository name",
      "rules": "Use package_name form ('forge-agent') or kebab-case form ('consensus-dev-agent') depending on organizational preference."
    },
    "python_modules": {
      "description": "Python module names (importable identifiers)",
      "rules": "Use snake_case derived form. All Python imports referencing the product must use this exact form."
    },
    "python_packages": {
      "description": "Python package directory names and PyPI package identifiers",
      "rules": "Use snake_case derived form."
    },
    "file_names": {
      "description": "Source file and configuration file names on disk",
      "rules": "Use snake_case derived form for Python files. Use PascalCase for Swift files."
    },
    "database_identifiers": {
      "description": "Database table names, column prefixes, or schema identifiers",
      "rules": "Use snake_case derived form."
    },
    "environment_variables": {
      "description": "Shell environment variables and .env file keys",
      "rules": "Use SCREAMING_SNAKE derived form as prefix. Example: CONSENSUS_DEV_AGENT_LOG_LEVEL."
    },
    "compile_time_constants": {
      "description": "Compile-time constants in Swift (#if) or C preprocessor macros",
      "rules": "Use SCREAMING_SNAKE derived form."
    },
    "preprocessor_macros": {
      "description": "C/Objective-C preprocessor macro names",
      "rules": "Use SCREAMING_SNAKE derived form."
    },
    "ui_headings": {
      "description": "Section headings in the application UI",
      "rules": "Use title_case derived form for the full name. Use ui_primary form ('Forge') for short references."
    },
    "documentation_titles": {
      "description": "Document titles, page headings, and README headers",
      "rules": "Use title_case derived form."
    },
    "about_dialog": {
      "description": "macOS About dialog and application info panels",
      "rules": "Display ui_primary form ('Forge') as app name. Display title_case form as full product name. Display tagline below."
    },
    "marketing_copy": {
      "description": "External marketing materials, website copy, press references",
      "rules": "Use title_case derived form for the full name. Use ui_primary form ('Forge') for short references."
    },
    "macos_app_bundle": {
      "description": "macOS application bundle identifier in Info.plist",
      "rules": "Use bundle_id derived form exactly. Must start with organization reverse-DNS prefix."
    },
    "info_plist": {
      "description": "Info.plist CFBundleIdentifier and related keys",
      "rules": "Use bundle_id derived form for CFBundleIdentifier. Use ui_primary form for CFBundleDisplayName."
    },
    "xpc_service_name": {
      "description": "XPC service name for the Python backend agent process",
      "rules": "Use reverse_dns_service derived form."
    },
    "launchd_label": {
      "description": "launchd job label for background agent process",
      "rules": "Use reverse_dns_service derived form."
    },
    "service_discovery": {
      "description": "Bonjour or mDNS service type identifiers",
      "rules": "Use reverse_dns_service derived form."
    },
    "xpc_mach_service": {
      "description": "Mach service name registered for XPC communication",
      "rules": "Use xpc_service derived form exactly. Must match entitlements."
    },
    "entitlements": {
      "description": "macOS entitlements plist entries for XPC and Keychain",
      "rules": "Use xpc_service derived form for Mach service entitlements. Use keychain_service form for Keychain access groups."
    },
    "keychain_service_name": {
      "description": "Keychain Services kSecAttrService value",
      "rules": "Use keychain_service derived form exactly."
    },
    "keychain_access_group": {
      "description": "Keychain access group identifier",
      "rules": "Use keychain_service derived form as the base. Append qualifiers only if multiple access groups are needed."
    },
    "cli_invocation": {
      "description": "The primary command users type in a terminal to invoke the tool",
      "rules": "Use cli_short form ('forge')."
    },
    "shell_alias": {
      "description": "Recommended shell alias for the CLI tool",
      "rules": "Use cli_short form ('forge')."
    },
    "path_binary_name": {
      "description": "Binary name installed in PATH",
      "rules": "Use cli_short form ('forge')."
    },
    "ui_app_name": {
      "description": "Application name displayed in Dock, menu bar, and window title",
      "rules": "Use ui_primary form ('Forge')."
    },
    "menu_bar": {
      "description": "macOS menu bar application menu title",
      "rules": "Use ui_primary form ('Forge')."
    },
    "dock_icon_label": {
      "description": "Label shown under the macOS Dock icon",
      "rules": "Use ui_primary form ('Forge')."
    },
    "package_registry": {
      "description": "Package name on Homebrew, PyPI, or other registries",
      "rules": "Use package_name form ('forge-agent')."
    },
    "homebrew_formula": {
      "description": "Homebrew formula name",
      "rules": "Use package_name form ('forge-agent')."
    }
  },
  "metadata": {
    "created": "2025-01-15T00:00:00Z",
    "maintainer": "Forge Platform Team / YouSource.ai",
    "purpose": "Single source of truth for all product identity strings. Consumed by code generators to produce ProductIdentity.swift and product_identity.py constants modules.",
    "spec_url": "shared/product_identity/canonical_name_spec.json"
  }
}

--- FILE: docs/product_identity/naming_policy.md ---

# Consensus Dev Agent -- Naming Policy

> **Status:** Authoritative · **Version:** 1.0 · **Maintainer:** Forge Platform Team / YouSource.ai
>
> This document defines the canonical product naming policy for the Consensus Dev Agent project. All new code, documentation, configuration, and external references **must** conform to this policy. The machine-readable counterpart lives at `shared/product_identity/canonical_name_spec.json`.

---

## 1. Product Name Hierarchy

The product identity is structured as a three-level hierarchy:

| Level | Value | Usage |
|---|---|---|
| **Organization** | YouSource.ai | Legal entity, copyright holder, reverse-DNS prefix (`ai.yousource`) |
| **Primary Product Name** | Forge | The short, user-facing product name. Used in UI, CLI invocation, Dock, menu bar. |
| **Subtitle** | Dev Agent | Qualifier distinguishing this product within the organization portfolio. |
| **Full Formal Name** | Consensus Dev Agent | The complete product name used in documentation titles, legal text, and formal references. |
| **Tagline** | A native macOS AI coding agent that decomposes build intent into reviewed, gated pull requests. | Descriptive sentence for about dialogs, README headers, and marketing copy. |

### Key Principles

- **"Forge"** is the primary name. When space or context is limited, use "Forge" alone.
- **"Consensus Dev Agent"** is the full formal name. Use it in document titles, README headers, legal notices, and first references in long-form documentation.
- **"Dev Agent"** is the subtitle -- it never appears alone without "Forge" or "Consensus" preceding it.
- The organization reverse-DNS prefix **`ai.yousource`** is the root for all bundle identifiers, XPC service names, Keychain service names, and entitlements.

---

## 2. Approved Derived Forms

Every derived form is defined in `canonical_name_spec.json` and must be used exactly as specified. No ad-hoc variants are permitted.

| Form ID | Value | Casing Convention | Permitted Contexts |
|---|---|---|---|
| `pascal_case` | `ConsensusDevAgent` | PascalCase | Swift types, class prefixes, documentation anchors |
| `camel_case` | `consensusDevAgent` | camelCase | Swift variables, JSON keys, JavaScript identifiers |
| `kebab_case` | `consensus-dev-agent` | kebab-case | CLI tool name, URL slugs, npm package, GitHub repo |
| `snake_case` | `consensus_dev_agent` | snake_case | Python modules, Python packages, file names, database identifiers |
| `screaming_snake` | `CONSENSUS_DEV_AGENT` | SCREAMING_SNAKE_CASE | Environment variables, compile-time constants, preprocessor macros |
| `title_case` | `Consensus Dev Agent` | Title Case | UI headings, documentation titles, about dialog, marketing copy |
| `bundle_id` | `ai.yousource.forge` | Reverse-DNS | macOS app bundle, Info.plist |
| `reverse_dns_service` | `ai.yousource.forge.agent` | Reverse-DNS + service suffix | XPC service name, launchd label, service discovery |
| `xpc_service` | `ai.yousource.forge.xpc` | Reverse-DNS + xpc suffix | XPC Mach service, entitlements |
| `keychain_service` | `ai.yousource.forge` | Reverse-DNS | Keychain service name, Keychain access group |
| `cli_short` | `forge` | All lowercase | CLI invocation, shell alias, PATH binary name |
| `ui_primary` | `Forge` | Capitalized single word | UI app name, menu bar, Dock icon label, about dialog |
| `package_name` | `forge-agent` | kebab-case + agent qualifier | GitHub repo, package registry, Homebrew formula |

### Form Selection Rules

1. **Choose the form matching your context.** If you are writing a Python import, use `consensus_dev_agent`. If you are defining an environment variable prefix, use `CONSENSUS_DEV_AGENT`.
2. **Never mix forms.** Do not write `forge_dev_agent` or `ForgeAgent` -- these are not approved.
3. **Qualify when ambiguous.** In contexts where "Forge" alone could be confused with other tools, use the full formal name or the context-appropriate derived form.

---

## 3. Usage Context Rules

### 3.1 User Interface Strings

- **App name** (Dock, menu bar, window title): Use `Forge` (`ui_primary`).
- **About dialog**: Display `Forge` as the app name, `Consensus Dev Agent` as the full product name, and the tagline below.
- **Section headings in-app**: Use `Consensus Dev Agent` (`title_case`) for formal sections; `Forge` for casual/compact UI.

### 3.2 Code Identifiers

- **Swift types** (structs, classes, enums, protocols): Prefix or name with `ConsensusDevAgent` (`pascal_case`). Example: `ConsensusDevAgentConfiguration`.
- **Swift variables and properties**: Use `consensusDevAgent` (`camel_case`). Example: `let consensusDevAgentVersion = "1.0.0"`.
- **Python modules and packages**: Use `consensus_dev_agent` (`snake_case`). Example: `from consensus_dev_agent.identity import PRODUCT_NAME`.
- **Python constants**: Use `CONSENSUS_DEV_AGENT` (`screaming_snake`) as a prefix. Example: `CONSENSUS_DEV_AGENT_VERSION`.

### 3.3 Command Line Interface

- **Primary CLI command**: `forge` (`cli_short`).
- **Subcommand namespacing**: `forge <subcommand>`. Never `consensus-dev-agent <subcommand>` as the primary invocation.
- **Package/formula name**: `forge-agent` (`package_name`). Example: `brew install forge-agent`.

### 3.4 Environment Variables

- **Prefix all environment variables** with `CONSENSUS_DEV_AGENT_`. Example: `CONSENSUS_DEV_AGENT_LOG_LEVEL`, `CONSENSUS_DEV_AGENT_API_KEY`.
- Do not use `FORGE_` as a prefix -- it is too generic and risks collision with unrelated tools.

### 3.5 Bundle Identifiers and System Services

- **macOS bundle ID**: `ai.yousource.forge` (`bundle_id`). This appears in `Info.plist` as `CFBundleIdentifier`.
- **XPC service name**: `ai.yousource.forge.agent` (`reverse_dns_service`). Used for the Python backend XPC endpoint.
- **XPC Mach service**: `ai.yousource.forge.xpc` (`xpc_service`). Registered Mach service for XPC communication.
- **Keychain service**: `ai.yousource.forge` (`keychain_service`). Used as `kSecAttrService` for credential storage.
- All system service identifiers **must** start with the organization reverse-DNS prefix `ai.yousource`.

### 3.6 Documentation

- **Document titles and H1 headings**: Use `Consensus Dev Agent` (`title_case`).
- **Inline references after first mention**: May use `Forge` (`ui_primary`) for brevity.
- **File names**: Use `snake_case` for Python-related docs, `kebab-case` for web-published docs.

---

## 4. Prohibited Variants

The following forms are **explicitly banned** in all new code, documentation, and configuration. Automated linting (planned in PR #4) will enforce this.

| Prohibited Variant | Reason |
|---|---|
| `ConsensusAgent` | Drops 'Dev' qualifier -- ambiguous, does not match any approved derived form |
| `ForgeAI` | Appends 'AI' to primary name -- not approved, conflates product with technology descriptor |
| `forge_dev_agent` | Incorrect snake_case -- mixes primary name 'forge' into the full-name snake_case slot |
| `CDA` | Unofficial acronym -- ambiguous, not searchable, not approved for any context |
| `cda` | Lowercase unofficial acronym -- same issues as 'CDA', confusable with unrelated tools |
| `Forge AI Agent` | Invented multi-word form -- adds 'AI' qualifier not present in formal name |
| `consensus-agent` | Drops 'dev' from kebab-case -- approved form is `consensus-dev-agent` |
| `FORGE_DEV_AGENT` | Incorrect screaming snake -- mixes primary name into full-name casing convention |
| `forgeAgent` | Hybrid camelCase -- mixes primary name with qualifier, approved form is `consensusDevAgent` |
| `Consensus_Dev_Agent` | Mixed case with underscores -- not a valid casing convention in any approved form |

### Legacy References

Some existing files (e.g., early README drafts, prototype scripts) may contain non-canonical forms. These are **legacy** and should be migrated to canonical forms when the containing file is next modified. Legacy references are not the same as prohibited variants -- legacy means "historically present but not forward-looking"; prohibited means "never use in new work."

---

## 5. Migration Rationale

### Why formalize naming now?

The project grew from a prototype where naming was ad-hoc. As the codebase expanded to include a Swift shell, Python backend, XPC boundary, Keychain integration, and CI pipelines, inconsistencies multiplied:

- The README says "Consensus Dev Agent" but some code uses "ConsensusAgent".
- Environment variable prefixes vary between files.
- Bundle identifiers and XPC service names were defined independently without a shared root.
- Searching the codebase for all references to the product requires knowing every variant.

### What this policy enables

1. **Single source of truth**: `canonical_name_spec.json` is machine-readable. Code generators in PR #2 (Python) and PR #3 (Swift) will produce constants modules from it.
2. **Cross-process consistency**: The Swift shell and Python backend reference the same identifiers for XPC, Keychain, and bundle operations.
3. **Grepability**: With a fixed set of approved forms, `grep` / `rg` searches reliably find all product references.
4. **CI enforcement**: PR #4 will add a lint rule that flags any prohibited variant in source, ensuring the policy is maintained automatically.

### Migration approach

- **Do not bulk-rename** in a single PR. Migrate files as they are touched in normal development.
- **Update constants first**: Once the Python and Swift constants modules exist (PRs #2-3), import from them instead of using string literals.
- **Tag legacy references** with `# LEGACY: migrate to canonical form` comments if immediate migration is not practical.

---

## 6. Governance

### Proposing changes

To add a new derived form or modify an existing one:

1. Open a PR modifying `shared/product_identity/canonical_name_spec.json`.
2. Update this policy document (`docs/product_identity/naming_policy.md`) to reflect the change.
3. Update `shared/product_identity/README.md` if the schema structure changes.
4. Regenerate downstream constants modules (Python and Swift) in the same PR or a follow-up.
5. Obtain review from at least one platform team member.

### Exceptions

There are **no exceptions** to the prohibited variants list. If a form is listed as prohibited, it must not appear in new code under any circumstances. If you believe a prohibited form should be rehabilitated, propose its addition to the approved derived forms through the governance process above.

---

## 7. Reference

- **Machine-readable spec**: [`shared/product_identity/canonical_name_spec.json`](../../shared/product_identity/canonical_name_spec.json)
- **Developer README**: [`shared/product_identity/README.md`](../../shared/product_identity/README.md)
- **Python constants module** (planned): PR #2
- **Swift constants module** (planned): PR #3
- **CI lint enforcement** (planned): PR #4

--- FILE: shared/product_identity/README.md ---

# Product Identity -- Shared Specification

> **Purpose:** This directory contains the canonical, machine-readable product identity specification for the Consensus Dev Agent project. It is the **single source of truth** from which all downstream constants modules, configuration templates, and naming validations are derived.

---

## Overview

The Consensus Dev Agent project spans two processes (Swift shell + Python backend) communicating over XPC, with shared references to Keychain services, bundle identifiers, environment variables, and user-facing strings. Naming consistency across this boundary is not cosmetic -- it is a correctness requirement. A mismatched XPC service name or Keychain identifier causes silent runtime failures.

This directory solves that problem by defining every approved product name variant in a single JSON file: **`canonical_name_spec.json`**.

### Contents

| File | Purpose |
|---|---|
| `canonical_name_spec.json` | Machine-readable spec defining all product identity strings, derived forms, prohibited variants, and usage contexts. |
| `README.md` | This file -- developer documentation for the naming spec. |

---

## Schema Structure

The JSON spec has the following top-level keys:

### `schema_version`

A semantic version string (e.g., `"1.0.0"`) identifying the spec format. Downstream generators should check this value and fail explicitly if it encounters an unexpected major version.

### `organization`

```json
{
  "name": "YouSource.ai",
  "reverse_dns": "ai.yousource",
  "website": "https://yousource.ai"
}
```

The legal entity and reverse-DNS prefix. All bundle IDs, XPC service names, and Keychain identifiers must start with the `reverse_dns` value.

### `product`

```json
{
  "primary_name": "Forge",
  "subtitle": "Dev Agent",
  "full_formal_name": "Consensus Dev Agent",
  "tagline": "..."
}
```

- **`primary_name`** -- The short product name. Used in UI, CLI, and informal references.
- **`subtitle`** -- The qualifier. Never appears alone.
- **`full_formal_name`** -- The complete product name for formal contexts.
- **`tagline`** -- Descriptive sentence for about dialogs and README headers.

### `derived_forms`

An array of objects, each defining one approved string variant:

```json
{
  "form": "snake_case",
  "value": "consensus_dev_agent",
  "casing": "snake_case -- all lowercase, underscore-separated",
  "contexts": ["python_modules", "python_packages", "file_names", "database_identifiers"]
}
```

- **`form`** -- A unique identifier for this variant (enum-like).
- **`value`** -- The exact string to use. No deviations permitted.
- **`casing`** -- Human-readable description of the casing convention.
- **`contexts`** -- Array of context identifiers where this form is permitted. Every context listed here must have a corresponding entry in `usage_contexts`.

### `prohibited_variants`

An array of objects defining strings that must **never** appear in new code or documentation:

```json
{
  "variant": "ForgeAI",
  "reason": "Appends 'AI' to primary name -- not approved, conflates product with technology descriptor"
}
```

### `usage_contexts`

An object mapping context identifiers to their descriptions and rules:

```json
{
  "python_modules": {
    "description": "Python module names (importable identifiers)",
    "rules": "Use snake_case derived form. All Python imports referencing the product must use this exact form."
  }
}
```

Every context referenced in any `derived_forms[].contexts` array must exist as a key in this object.

### `metadata`

```json
{
  "created": "2025-01-15T00:00:00Z",
  "maintainer": "Forge Platform Team / YouSource.ai",
  "purpose": "Single source of truth for all product identity strings.",
  "spec_url": "shared/product_identity/canonical_name_spec.json"
}
```

---

## How Constants Are Generated

This PR (PR #1) establishes the spec only. Subsequent PRs generate code from it:

### PR #2: Python Constants Module

A Python script reads `canonical_name_spec.json` and generates `product_identity.py` containing:

- String constants for every derived form (e.g., `PASCAL_CASE = "ConsensusDevAgent"`)
- The `PRODUCT_PRIMARY_NAME`, `PRODUCT_SUBTITLE`, `PRODUCT_FULL_FORMAL_NAME` constants
- Organization constants (`ORG_NAME`, `ORG_REVERSE_DNS`)
- A `PROHIBITED_VARIANTS` frozenset for runtime validation
- A `USAGE_CONTEXTS` dict for programmatic context lookup

The generated module includes a header comment linking back to the JSON spec and warning against manual edits.

### PR #3: Swift Constants Module

A Swift code generator reads the same JSON and produces `ProductIdentity.swift` containing:

- A `ProductIdentity` enum with static string constants
- Bundle ID, XPC service name, and Keychain service constants
- Compile-time assertions where possible

### PR #4: CI Lint Rule

A CI check scans all source files for any string in the `prohibited_variants` list and fails the build if found. This ensures the naming policy is enforced automatically, not just by convention.

### Generation Pipeline Diagram

```
canonical_name_spec.json
        │
        ├──▶ generate_python_constants.py ──▶ product_identity.py
        │
        ├──▶ generate_swift_constants.py  ──▶ ProductIdentity.swift
        │
        └──▶ lint_prohibited_variants.py  ──▶ CI pass/fail
```

All generators
