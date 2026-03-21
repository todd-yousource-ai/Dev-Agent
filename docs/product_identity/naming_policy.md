I need to produce three files. Let me output them sequentially with clear file separators.

--- FILE: docs/product_identity/naming_policy.md ---

# Forge -- Product Naming Policy

**Document ID:** naming-policy-v1
**Status:** Normative
**PRD Reference:** PRD-001 (Product Identity, Branding, and Canonical Naming)
**Effective Date:** 2025-07-13
**Owner:** Platform Engineering

---

## 1. Purpose

This document defines the canonical product naming rules for the Forge Dev Agent project. Every surface -- UI labels, documentation headers, CLI binaries, environment variables, Swift types, Python modules, package identifiers, PR titles, and CI tags -- **MUST** derive its product name from the single source of truth at `shared/product_identity/canonical_name_spec.json`.

This policy eliminates naming drift, provides clear decision rules for every naming context, and defines the migration path from the legacy "Consensus Dev Agent" identity.

---

## 2. Product Name Hierarchy

| Level | Value | Role |
|---|---|---|
| **Product Name** | `Forge` | Primary customer-facing name. Used in marketing, the UI title bar, and conversational references. |
| **Subtitle** | `Dev Agent` | Descriptive subtitle clarifying product category. Appears in secondary UI placement and formal references. |
| **Full Name** | `Forge Dev Agent` | Combined formal product name. Used in documentation headers, legal text, PR titles, and any context requiring unambiguous identification. |
| **Vendor** | `YouSource.ai` | Organization name. Used in bundle identifiers, copyright notices, and vendor metadata fields. |

### 2.1 Decision Rules

- **When space is limited** (menu bar, tab title, conversational prose): use `Forge`.
- **When the reader needs disambiguation** (documentation headers, formal references, About dialog): use `Forge Dev Agent`.
- **Never use the subtitle alone** without the product name. "Dev Agent" by itself is not a valid product reference.
- **Never invent new combined forms** (e.g., "Forge Agent", "The Forge", "ForgeAI"). All permitted forms are enumerated in the canonical spec.

---

## 3. Derived Forms and Usage Contexts

All derived forms are defined authoritatively in `shared/product_identity/canonical_name_spec.json`. The following table is informational.

### 3.1 Derived Forms

| Form Key | Value | Typical Usage |
|---|---|---|
| `display_full` | `Forge Dev Agent` | UI, documentation, PR titles |
| `display_short` | `Forge` | Conversational, compact UI |
| `pascal_case` | `ForgeDevAgent` | Swift types, class names |
| `camel_case` | `forgeDevAgent` | JavaScript/TypeScript identifiers |
| `kebab_case` | `forge-dev-agent` | CLI binary names, npm packages, URLs |
| `snake_case` | `forge_dev_agent` | Python modules, file paths |
| `screaming_snake` | `FORGE_DEV_AGENT` | Environment variables, constants |
| `bundle_id` | `ai.yousource.forge` | macOS bundle identifier |
| `reverse_dns` | `ai.yousource.forge-dev-agent` | Reverse-DNS contexts (entitlements, XPC service names) |

### 3.2 Context-to-Form Mapping

Every naming context maps to exactly one derived form. If your context is not listed, request an addition through the update process described in Section 7.

| Context | Derived Form Key | Resolved Value |
|---|---|---|
| UI title bar | `display_full` | `Forge Dev Agent` |
| UI subtitle area | `display_short` | `Forge` |
| CLI binary name | `kebab_case` | `forge-dev-agent` |
| Python module | `snake_case` | `forge_dev_agent` |
| Swift type prefix | `pascal_case` | `ForgeDevAgent` |
| Environment variable prefix | `screaming_snake` | `FORGE_DEV_AGENT` |
| GitHub PR prefix | `display_full` | `Forge Dev Agent` |
| npm package name | `kebab_case` | `forge-dev-agent` |
| macOS bundle identifier | `bundle_id` | `ai.yousource.forge` |
| Documentation header | `display_full` | `Forge Dev Agent` |

---

## 4. Prohibited Variants

The following product name variants are **prohibited in all new content**. CI lint rules (planned in PR #4) will flag these automatically.

| Prohibited Variant | Reason |
|---|---|
| `Consensus Dev Agent` | Legacy product name replaced by Forge per PRD-001. Use `Forge Dev Agent` instead. |
| `ConsensusDevAgent` | Legacy PascalCase form of the old product name. Use `ForgeDevAgent` instead. |
| `consensus-dev-agent` | Legacy kebab-case form of the old product name. Use `forge-dev-agent` instead. |
| `consensus_dev_agent` | Legacy snake_case form of the old product name. Use `forge_dev_agent` instead. |
| `CONSENSUS_DEV_AGENT` | Legacy screaming snake form of the old product name. Use `FORGE_DEV_AGENT` instead. |
| `CDA` | Ambiguous abbreviation of legacy product name. Do not use. |
| `cda` | Lowercase form of ambiguous legacy abbreviation. Do not use. |
| `Forge Agent` | Incorrect truncation. Use `Forge` (short) or `Forge Dev Agent` (full). |
| `The Forge` | Incorrect article-prefixed form. Use `Forge`. |
| `ForgeAI` | Invented combined form not in the canonical spec. Do not use. |

### 4.1 When "consensus" Is Still Permitted

The word **"consensus"** (lowercase) remains a valid technical term when referring to the **consensus engine** -- the architectural component responsible for arbitrating between parallel LLM provider outputs (see TRD-3, TRD-6).

**Permitted examples:**
- "The consensus engine resolves disagreements between Claude and the secondary provider."
- "consensus_engine.py implements the arbitration logic."
- "The `ConsensusResult` type represents the merged output."

**Prohibited examples:**
- "The Consensus Dev Agent runs on macOS." → Use "Forge Dev Agent"
- "Open the Consensus app." → Use "Forge"
- "CONSENSUS_DEV_AGENT_HOME environment variable" → Use "FORGE_DEV_AGENT_HOME"

**Rule of thumb:** If "consensus" is describing the *product*, it is prohibited. If it is describing the *arbitration algorithm or engine*, it is permitted.

---

## 5. Migration Policy

### 5.1 Rationale

The rename from "Consensus Dev Agent" to "Forge Dev Agent" was mandated by PRD-001 to establish a distinct, trademarkable product identity. The legacy name created confusion with the consensus engine subsystem and lacked brand distinctiveness.

### 5.2 Migration Rules

1. **New content**: All new files, documentation, UI strings, variable names, and CI configurations MUST use the canonical Forge naming from day one.
2. **Existing code**: Will be migrated incrementally across PRs #4 and #5+. Do not block new work on legacy references in files not yet migrated.
3. **Historical documents**: Git history, archived release notes, and documents explicitly marked as historical may retain the legacy name without modification. Add a migration note at the top where practical.
4. **External references**: Links to third-party articles or external documentation that use the legacy name are acceptable when quoting but should include a parenthetical clarification: `"Consensus Dev Agent" (now Forge Dev Agent)`.

### 5.3 Legacy Aliases

The following values are recognized as legacy aliases for **migration tooling only**. They are NOT permitted in new content but may appear in migration scripts, search-and-replace tooling, and backward-compatibility mapping tables.

| Legacy Alias | Replacement | Status |
|---|---|---|
| `Consensus Dev Agent` | `Forge Dev Agent` | Recognition only -- not for new use |
| `consensus-dev-agent` | `forge-dev-agent` | Recognition only -- not for new use |

---

## 6. Canonical Spec as Single Source of Truth

The machine-readable specification at `shared/product_identity/canonical_name_spec.json`:

- Is the **single source of truth** for all product identity values.
- Is consumed by code generators (Swift `ProductIdentity` constants, Python `product_identity` module).
- Is validated by CI lint rules.
- Takes precedence over this document in case of any discrepancy. (If a discrepancy is found, file a bug -- both must be synchronized.)

---

## 7. Adding New Derived Forms

To add a new naming context or derived form:

1. Open a PR modifying `shared/product_identity/canonical_name_spec.json`.
2. Add the new key to `derived_forms` and/or a new entry to `contexts`.
3. Update this policy document with the new form in Section 3.
4. Bump `schema_version` patch number (e.g., `1.0.0` → `1.0.1`).
5. Ensure all existing tests pass and add a test for the new form.
6. Obtain review from Platform Engineering.

---

## 8. Governance

| Role | Responsibility |
|---|---|
| Platform Engineering | Owns the canonical spec and this policy document |
| All contributors | Must follow this policy for new content |
| CI lint (PR #4) | Automated enforcement of prohibited variants |
| Code generators (PRs #2, #3) | Derive constants from canonical spec -- never hardcode |

---

## 9. References

- **PRD-001**: Product Identity, Branding, and Canonical Naming
- **Canonical Spec**: `shared/product_identity/canonical_name_spec.json`
- **Developer README**: `shared/product_identity/README.md`
- **TRD-3**: Build Pipeline (consensus engine references)
- **TRD-6**: Holistic Code Review (consensus engine references)

--- FILE: shared/product_identity/canonical_name_spec.json ---

{
  "schema_version": "1.0.0",
  "spec_id": "product-identity-canonical",
  "identity": {
    "product_name": "Forge",
    "subtitle": "Dev Agent",
    "full_name": "Forge Dev Agent",
    "vendor": "YouSource.ai"
  },
  "derived_forms": {
    "display_full": "Forge Dev Agent",
    "display_short": "Forge",
    "pascal_case": "ForgeDevAgent",
    "camel_case": "forgeDevAgent",
    "kebab_case": "forge-dev-agent",
    "snake_case": "forge_dev_agent",
    "screaming_snake": "FORGE_DEV_AGENT",
    "bundle_id": "ai.yousource.forge",
    "reverse_dns": "ai.yousource.forge-dev-agent"
  },
  "prohibited": [
    {
      "variant": "Consensus Dev Agent",
      "reason": "Legacy product name replaced by 'Forge Dev Agent' per PRD-001. Use 'Forge Dev Agent' in all new content."
    },
    {
      "variant": "ConsensusDevAgent",
      "reason": "Legacy PascalCase form of the old product name. Use 'ForgeDevAgent' instead."
    },
    {
      "variant": "consensus-dev-agent",
      "reason": "Legacy kebab-case form of the old product name. Use 'forge-dev-agent' instead."
    },
    {
      "variant": "consensus_dev_agent",
      "reason": "Legacy snake_case form of the old product name. Use 'forge_dev_agent' instead."
    },
    {
      "variant": "CONSENSUS_DEV_AGENT",
      "reason": "Legacy screaming snake case form of the old product name. Use 'FORGE_DEV_AGENT' instead."
    },
    {
      "variant": "CDA",
      "reason": "Ambiguous abbreviation of the legacy product name. Do not use in any context."
    },
    {
      "variant": "cda",
      "reason": "Lowercase form of ambiguous legacy abbreviation. Do not use in any context."
    },
    {
      "variant": "Forge Agent",
      "reason": "Incorrect truncation of the full product name. Use 'Forge' (short) or 'Forge Dev Agent' (full)."
    },
    {
      "variant": "The Forge",
      "reason": "Incorrect article-prefixed form. Use 'Forge' without a definite article."
    },
    {
      "variant": "ForgeAI",
      "reason": "Invented combined form not defined in the canonical spec. Do not use."
    }
  ],
  "legacy_aliases": [
    {
      "value": "Consensus Dev Agent",
      "status": "deprecated",
      "allowed_for_recognition_only": true,
      "replacement": "Forge Dev Agent"
    },
    {
      "value": "consensus-dev-agent",
      "status": "deprecated",
      "allowed_for_recognition_only": true,
      "replacement": "forge-dev-agent"
    }
  ],
  "contexts": {
    "ui_title_bar": "display_full",
    "ui_subtitle": "display_short",
    "cli_binary_name": "kebab_case",
    "python_module": "snake_case",
    "swift_type_prefix": "pascal_case",
    "env_var_prefix": "screaming_snake",
    "github_pr_prefix": "display_full",
    "npm_package": "kebab_case",
    "macos_bundle": "bundle_id",
    "documentation_header": "display_full"
  },
  "metadata": {
    "created": "2025-07-13",
    "prd_reference": "PRD-001",
    "spec_id": "product-identity-canonical"
  }
}

--- FILE: shared/product_identity/README.md ---

# Product Identity -- Shared Canonical Specification

## Overview

This directory contains the **single source of truth** for the Forge Dev Agent product identity. Every product name, derived form, and naming context is defined here in a machine-readable JSON specification.

All downstream consumers -- Swift constants, Python modules, CI lint rules, UI string tables, and documentation templates -- **MUST** derive their product identity values from the canonical spec in this directory. Hardcoding product names elsewhere in the codebase is prohibited.

---

## Canonical Hierarchy

| Level | Value | Description |
|---|---|---|
| **Product Name** | `Forge` | Primary brand name |
| **Subtitle** | `Dev Agent` | Descriptive category subtitle |
| **Full Name** | `Forge Dev Agent` | Combined formal product name |
| **Vendor** | `YouSource.ai` | Organization / publisher |

---

## File Layout

```
shared/product_identity/
├── README.md                    # This file -- developer guide
└── canonical_name_spec.json     # Machine-readable canonical spec (single source of truth)
```

**Related documentation:**

```
docs/product_identity/
└── naming_policy.md             # Human-readable normative naming policy
```

---

## Consuming the Spec

### General Principle

Read `canonical_name_spec.json` at build time or code-generation time. Never copy values by hand into source files.

### Python

A Python `product_identity` module (PR #3) will be generated from the spec. Until then, consume the JSON directly:

```python
import json
from pathlib import Path

spec_path = Path(__file__).parent.parent / "shared" / "product_identity" / "canonical_name_spec.json"
with spec_path.open() as f:
    spec = json.load(f)

product_name = spec["identity"]["product_name"]  # "Forge"
snake_form = spec["derived_forms"]["snake_case"]  # "forge_dev_agent"
```

### Swift

A Swift `ProductIdentity` constants file (PR #2) will be generated from the spec. The generator reads the JSON and emits a Swift source file with static constants.

### CI Lint

PR #4 will add a CI lint rule that:
1. Parses `canonical_name_spec.json`
2. Scans changed files for any string in the `prohibited` list
3. Fails the build with the corresponding `reason` from the spec

### Context Resolution

To determine the correct product name form for a specific usage context:

1. Look up your context in `$.contexts` (e.g., `"cli_binary_name"`)
2. Get the derived form key (e.g., `"kebab_case"`)
3. Resolve the value from `$.derived_forms` (e.g., `"forge-dev-agent"`)

---

## Adding a New Derived Form

1. **Edit `canonical_name_spec.json`:**
   - Add the new key and value to the `derived_forms` object.
   - If the form serves a specific usage context, add a corresponding entry to the `contexts` object mapping the context name to your new derived form key.

2. **Update the naming policy:**
   - Add the new form to the tables in `docs/product_identity/naming_policy.md`, Sections 3.1 and 3.2.

3. **Bump the schema version:**
   - Increment the patch version in `schema_version` (e.g., `"1.0.0"` → `"1.0.1"` for additive changes).
   - Increment the minor version for structural changes to the schema (e.g., new top-level keys).

4. **Add tests:**
   - Extend `tests/shared/test_canonical_name_spec.py` to validate the new form.

5. **Open a PR** and obtain review from Platform Engineering.

---

## Legacy Variants

The spec distinguishes two categories:

### Prohibited Variants (`$.prohibited`)

These forms **MUST NOT** appear in any new content. Each entry includes a `reason` string suitable for use as a CI lint error message.

Examples: `Consensus Dev Agent`, `ConsensusDevAgent`, `consensus-dev-agent`, `consensus_dev_agent`, `CONSENSUS_DEV_AGENT`

### Legacy Aliases (`$.legacy_aliases`)

These are the same legacy values but marked with `allowed_for_recognition_only: true`. They exist so that migration tooling can recognize and replace them. They are **NOT** permitted in new content.

### When "consensus" Is Permitted

The word "consensus" (lowercase) remains valid when referring to the **consensus engine** -- the architectural component that arbitrates between parallel LLM outputs. It is prohibited only when used as part of the **product name**. See the full policy in `docs/product_identity/naming_policy.md`, Section 4.1.

---

## Validation

Run the spec validation tests:

```bash
python -m pytest tests/shared/test_canonical_name_spec.py -v
python -m pytest tests/shared/test_naming_policy_docs.py -v
```

These tests verify:
- The JSON is valid and parseable
- All required top-level keys are present
- All nine derived forms exist with correct values
- Every context resolves to a valid derived form key
- All required prohibited variants are present with non-empty reasons
- Documentation and JSON values are internally consistent

---

## Update Process and Ownership

| Aspect | Detail |
|---|---|
| **Owner** | Platform Engineering |
| **Review required** | Any change to the canonical spec requires Platform Engineering approval |
| **Schema versioning** | Semver in `$.schema_version` -- patch for additive, minor for structural, major for breaking |
| **Downstream impact** | Changes trigger regeneration of Swift constants (PR #2), Python module (PR #3), and CI lint rules (PR #4) |
| **Conflict resolution** | The JSON spec takes precedence. If docs disagree with the spec, the spec wins and docs must be updated. |

---

## Related PRDs and TRDs

| Reference | Relevance |
|---|---|
| **PRD-001** | Product Identity, Branding, and Canonical Naming -- the mandate for this spec |
| **TRD-3** | Build Pipeline -- references to consensus engine (permitted use of "consensus") |
| **TRD-6** | Holistic Code Review -- references to consensus engine (permitted use of "consensus") |
| **TRD-11** | Security Threat Model -- identity validation context |
