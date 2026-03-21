docs/PRODUCT_IDENTITY.md
# Product Identity -- Forge

> **Status:** Active -- Normative  
> **Applies to:** All code, documentation, UI, CLI output, logs, error messages, and external communications  
> **Owner:** Forge Platform Team  
> **Last updated:** 2026-03-20  
> **Supersedes:** All prior informal naming usage

---

## 1. Product Name Hierarchy

| Level | Name | Usage |
|-------|------|-------|
| **Primary (short name)** | **Forge** | Default in all user-facing contexts. Use this unless a specific context requires more precision. |
| **Subheader (descriptive)** | **Dev Agent** | Appended for disambiguation when "Forge" alone is ambiguous (e.g., first mention in external docs, marketing headers). Rendered as: **Forge -- Dev Agent** |
| **Full formal name** | **Consensus Dev Agent** | Legal, copyright, and attribution contexts only. Never used as a standalone user-facing product name. |
| **Internal codebase identifier** | `consensus_dev_agent` / `ConsensusDevAgent` | Python package names, Swift module names, internal class prefixes. Not user-facing. |

### 1.1 Primary Name -- Forge

**Forge** is the canonical, user-facing product name. It is used:

- In all UI chrome (window titles, menu items, about dialogs)
- In all CLI output (banners, status lines, help text)
- In all documentation headings and body text (after first mention establishes context)
- In all log lines visible to operators
- In all error messages surfaced to users
- In repository README titles and descriptions
- In external communications, blog posts, release notes

### 1.2 Subheader -- Dev Agent

**Dev Agent** is a descriptive subheader. It is **not** part of the short product name. It is used:

- On first mention in a document to establish context: "**Forge -- Dev Agent**"
- In page titles or headers where disambiguation from other products named "Forge" is needed
- In marketing or landing page headers: "**Forge** -- Dev Agent"
- The separator is an em dash with spaces: ` -- `

**Dev Agent** is never used alone. It always appears after **Forge**.

### 1.3 Full Formal Name -- Consensus Dev Agent

**Consensus Dev Agent** is the full formal product name. Usage is restricted to:

- Copyright lines: `© 2026 YouSource.ai -- Consensus Dev Agent`
- LICENSE file attribution
- Legal documents and contracts
- Internal architecture documents where the consensus mechanism is the subject (e.g., TRDs)
- Package/module identifiers in code (see Section 5)

---

## 2. Usage Rules by Context

| Context | Allowed Forms | Example |
|---------|--------------|---------|
| **UI window title** | `Forge` | `Forge -- Build Pipeline` |
| **UI about dialog** | `Forge` with version, `Consensus Dev Agent` in fine print | `Forge v1.2.0` / `Consensus Dev Agent © 2026 YouSource.ai` |
| **CLI banner** | `Forge` | `Forge v1.2.0 -- ready` |
| **CLI help text** | `Forge` | `Usage: forge [command] [options]` |
| **Code comments** | `Forge` or full formal name for architectural context | `# Forge consensus engine -- see TRD-2` |
| **Docstrings** | `Forge` | `"""Forge build pipeline stage executor."""` |
| **README.md title** | `Forge -- Dev Agent` (first mention), then `Forge` | `# Forge -- Dev Agent` |
| **External documentation** | `Forge -- Dev Agent` (first mention), then `Forge` | "Forge -- Dev Agent is a native macOS AI coding agent. Forge takes a plain-language build intent..." |
| **Error messages** | `Forge` | `Forge: authentication failed -- check Keychain configuration` |
| **Log lines** | `forge` (lowercase) as logger name | `forge.pipeline: stage 3 complete` |
| **Log lines (structured)** | `forge` prefix | `{"service": "forge.backend", "level": "error", ...}` |
| **Artifact names** | `forge` (lowercase) | `forge-backend-1.2.0-arm64.tar.gz` |
| **Branch prefixes** | `forge-agent/` for agent-generated branches | `forge-agent/build/add-auth-module` |
| **Configuration keys** | `forge.` prefix | `forge.backend.consensus.timeout` |
| **Copyright/legal** | `Consensus Dev Agent` | `© 2026 YouSource.ai -- Consensus Dev Agent` |

---

## 3. Prohibited Forms

The following forms are **prohibited** in all user-facing contexts (UI, CLI, docs, error messages, release notes, external communications). Their use in code identifiers is governed by Section 5.

| Prohibited Form | Reason |
|-----------------|--------|
| `ConsensusDevAgent` (as user-facing text) | Internal code identifier only. Not a user-facing product name. |
| `Consensus Dev Agent` (as primary product name) | Full formal name; restricted to legal/copyright/attribution. Use **Forge** instead. |
| `forge.ai` | Not an approved domain or product variant. Creates confusion with unrelated services. |
| `ForgeAI` | Implies an "AI" product sub-brand that does not exist. Use **Forge** alone. |
| `Forge AI` | Same as above. The product is **Forge**, not **Forge AI**. |
| `CDA` | Unauthorized abbreviation. Opaque to users and new team members. |
| `cda` | Lowercase variant of the above. Equally prohibited. |
| `The Forge` | Adding an article changes the product name. The name is **Forge**, not **The Forge**. |
| `FORGE` (all caps, in prose) | All-caps is not a branding style. Use `Forge` (title case) in prose, `forge` (lowercase) in code/logs/artifacts. |
| `forge-agent` (as product name) | `forge-agent/` is a branch prefix only. Not a product name or component name. |
| `Dev Agent` (standalone) | Subheader only. Never used without **Forge** preceding it. |
| `Consensus Engine` (as product name) | This is an internal subsystem (TRD-2), not the product. The product is **Forge**. |

---

## 4. Canonical Descriptions

### 4.1 One-Liner

> **Forge** is an enterprise AI agent runtime that decomposes build intent into sequenced pull requests with consensus-driven code generation and human-gated merges.

### 4.2 Tagline

> **Forge -- Build with consensus, ship with confidence.**

### 4.3 Short Paragraph (for READMEs and external docs)

> **Forge -- Dev Agent** is a native macOS AI coding agent. It takes a plain-language build intent, decomposes it into an ordered sequence of pull requests, generates implementation and tests using two LLM providers in parallel (Claude arbitrates), runs a 3-pass review cycle, executes CI, and gates on operator approval before merging. The human is in the loop at every gate.

### 4.4 Architecture Summary (for technical docs)

> Forge is a two-process system: a Swift shell (UI, authentication, Keychain, XPC) and a Python backend (consensus engine, build pipeline, GitHub integration). Twelve TRDs define the specification. Code must match them.

---

## 5. Internal Code References

Code identifiers follow language conventions, **not** branding rules. The following internal identifiers are approved:

| Context | Approved Identifier | Example |
|---------|-------------------|---------|
| Python package name | `consensus_dev_agent` | `import consensus_dev_agent` |
| Python module logger | `forge` prefix (dot-separated) | `logging.getLogger("forge.pipeline")` |
| Swift module name | `ConsensusDevAgent` | `import ConsensusDevAgent` |
| Swift app bundle ID | `ai.yousource.forge` | `ai.yousource.forge` |
| Python class prefix | Context-dependent (no mandatory prefix) | `ConsensusEngine`, `BuildPipeline` |
| Environment variable prefix | `FORGE_` | `FORGE_BACKEND_PORT` |
| Configuration key prefix | `forge.` | `forge.backend.consensus.timeout` |

These identifiers are **internal**. They do not appear in user-facing text. When referencing these components in documentation, use the product name **Forge** followed by the component name in natural language (e.g., "Forge's consensus engine", not "the ConsensusEngine").

---

## 6. Legacy and Internal References

### 6.1 Existing References

The codebase, TRDs, and repository documents created before this standard contain references to "Consensus Dev Agent" as a product name. These are **legacy references**.

- **TRDs (TRD-1 through TRD-16):** Use "Consensus Dev Agent" as the product name in headers and field tables. These are retained as-is until their next revision cycle. They remain valid and authoritative for their technical content.
- **AGENTS.md:** Contains "Consensus Dev Agent" in the Repository Identity section. This will be updated in a future PR to align with this standard.
- **Code identifiers** (`ConsensusDevAgent`, `consensus_dev_agent`): These are approved internal identifiers (Section 5) and are **not** legacy -- they are correct per language conventions.

### 6.2 Forward-Looking Rule

All **new** documents, UI strings, CLI output, error messages, log formats, README content, and external communications created after this document's effective date **MUST** use the naming hierarchy defined in Section 1.

Existing documents are updated opportunistically -- when a document is revised for any reason, its product naming is brought into compliance with this standard.

### 6.3 Conflict Resolution

If a naming conflict arises:

1. This document (`docs/PRODUCT_IDENTITY.md`) is authoritative for product identity.
2. `forge-standards/naming-conventions.md` is authoritative for naming patterns.
3. TRD-11 (Security Threat Model) overrides all documents on security-relevant naming (e.g., log field names that could leak identity information).

---

## 7. Attribution and Copyright

### 7.1 Standard Copyright Line

```
© 2026 YouSource.ai -- Consensus Dev Agent
```

### 7.2 Standard License Header (Python)

```python
# Copyright 2026 YouSource.ai -- Consensus Dev Agent
# SPDX-License-Identifier: [LICENSE_ID]
```

### 7.3 Standard License Header (Swift)

```swift
// Copyright 2026 YouSource.ai -- Consensus Dev Agent
// SPDX-License-Identifier: [LICENSE_ID]
```

### 7.4 Attribution in Documentation

When attribution is required in documentation footers or about pages:

> Built by [YouSource.ai](https://yousource.ai) -- Consensus Dev Agent

The full formal name is used in attribution because it establishes the product's technical identity for legal and intellectual property purposes.

---

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2026-03-20 | Forge Platform Team | Initial product identity definition |

docs/NAMING_CONVENTIONS.md
# Naming Conventions -- Forge

> **Status:** Active -- Informative  
> **Authoritative source:** [`forge-standards/naming-conventions.md`](../forge-standards/naming-conventions.md) (normative)  
> **This document:** Human-readable guide. If this document conflicts with the standards-track copy, the standards-track copy wins.  
> **Owner:** Forge Platform Team  
> **Last updated:** 2026-03-20

---

## Overview

This document defines naming conventions for all artifacts in the Forge project: branches, files, directories, build artifacts, state/enum values, configuration keys, and the repository layout. These conventions apply to both the Swift shell and the Python backend.

All examples assume the two-process architecture described in the TRDs: a Swift shell (UI, auth, Keychain, XPC) and a Python backend (consensus, pipeline, GitHub).

---

## 1. Branch Naming

Branches follow a prefix-based scheme that encodes intent and enables CI automation.

### 1.1 Patterns

| Prefix | Pattern | Example | Usage |
|--------|---------|---------|-------|
| `feature/` | `feature/<prd>-<pr>-<slug>` | `feature/prd001-3-product-identity` | Human-authored feature branches tied to a PRD and PR number |
| `fix/` | `fix/<issue>-<slug>` | `fix/142-keychain-timeout` | Bug fixes tied to an issue number |
| `release/` | `release/<semver>` | `release/1.2.0` | Release preparation branches |
| `forge-agent/build/` | `forge-agent/build/<slug>` | `forge-agent/build/add-auth-module` | Agent-generated branches (created by the Forge build pipeline) |
| `hotfix/` | `hotfix/<issue>-<slug>` | `hotfix/199-crash-on-launch` | Emergency fixes against a release branch |

### 1.2 Rules

- All branch names are lowercase with hyphens separating words in the slug.
- The `<prd>` segment uses the form `prd001` (lowercase, zero-padded to 3 digits).
- The `<pr>` segment is the PR sequence number (integer, no padding).
- The `<slug>` is a short kebab-case description (2-5 words).
- The `<issue>` segment is the GitHub issue number (integer).
- The `<semver>` segment follows strict Semantic Versioning: `MAJOR.MINOR.PATCH`.

### 1.3 Examples and Anti-Examples

| ✅ Correct | ❌ Incorrect | Why |
|-----------|-------------|-----|
| `feature/prd001-3-product-identity` | `feature/PRD001-3-product-identity` | PRD prefix must be lowercase |
| `fix/142-keychain-timeout` | `fix/keychain-timeout` | Missing issue number |
| `release/1.2.0` | `release/v1.2.0` | No `v` prefix in branch names |
| `forge-agent/build/add-auth-module` | `agent/add-auth-module` | Agent branches must use the `forge-agent/build/` prefix |
| `hotfix/199-crash-on-launch` | `hotfix/crash` | Missing issue number and slug is too vague |

---

## 2. File Naming

### 2.1 Python Files

| Rule | Pattern | Example |
|------|---------|---------|
| Module files | `snake_case.py` | `build_director.py`, `consensus_engine.py` |
| Test files | `test_<module>.py` | `test_build_director.py` |
| Configuration files | `snake_case.{json,yaml,toml}` | `forge_config.yaml` |
| Constants/enums files | `snake_case.py` | `pipeline_states.py` |

### 2.2 Swift Files

| Rule | Pattern | Example |
|------|---------|---------|
| Type definitions (class, struct, enum, protocol) | `PascalCase.swift` | `ConsensusEngine.swift`, `BuildPipeline.swift` |
| Extensions | `<Type>+<Extension>.swift` | `String+Validation.swift` |
| SwiftUI views | `<ViewName>View.swift` | `PipelineStatusView.swift` |
| Test files | `<Type>Tests.swift` | `ConsensusEngineTests.swift` |

### 2.3 Swift Identifiers (within files)

| Kind | Convention | Example |
|------|-----------|---------|
| Types (class, struct, enum, protocol) | `PascalCase` | `BuildPipeline`, `ConsensusResult` |
| Variables and functions | `camelCase` | `buildStage`, `runConsensus()` |
| Constants (static/global) | `camelCase` or `PascalCase` for type-level | `defaultTimeout`, `MaxRetries` |
| Enum cases | `camelCase` | `.waitingForApproval`, `.buildFailed` |

### 2.4 Documentation Files

| Rule | Pattern | Example |
|------|---------|---------|
| Guides and references | `UPPER_SNAKE_CASE.md` or `lowercase-hyphenated.md` | `PRODUCT_IDENTITY.md`, `naming-conventions.md` |
| TRDs | `TRD-<number>-<Title>.md` | `TRD-11-Security-Threat-Model.md` |
| Root-level docs | `UPPER_CASE.md` | `README.md`, `CONTRIBUTING.md`, `LICENSE` |

### 2.5 Examples and Anti-Examples

| ✅ Correct | ❌ Incorrect | Why |
|-----------|-------------|-----|
| `build_director.py` | `BuildDirector.py` | Python files use snake_case |
| `ConsensusEngine.swift` | `consensus_engine.swift` | Swift type files use PascalCase |
| `test_build_director.py` | `build_director_test.py` | Test files use `test_` prefix (pytest convention) |
| `String+Validation.swift` | `StringValidation.swift` | Extensions use the `+` separator |

---

## 3. Directory Naming

### 3.1 Rules by Context

| Context | Convention | Example |
|---------|-----------|---------|
| Documentation directories | `lowercase-hyphenated` | `forge-docs/`, `forge-standards/` |
| Configuration directories | `lowercase-hyphenated` | `forge-config/`, `ci-scripts/` |
| Python packages | `snake_case` | `consensus_engine/`, `build_pipeline/` |
| Swift source groups/folders | `PascalCase` | `ConsensusEngine/`, `BuildPipeline/` |
| Test directories | Match source convention | `tests/` (Python), `Tests/` (Swift) |
| Root-level tooling | `lowercase-hyphenated` | `forge-standards/`, `forge-docs/` |

### 3.2 Examples and Anti-Examples

| ✅ Correct | ❌ Incorrect | Why |
|-----------|-------------|-----|
| `forge-docs/` | `ForgeDocs/` | Documentation directories use lowercase-hyphenated |
| `consensus_engine/` | `consensus-engine/` | Python packages use snake_case (must be valid Python identifiers) |
| `BuildPipeline/` (Swift) | `build_pipeline/` (Swift) | Swift source folders use PascalCase |
| `tests/` (Python) | `Tests/` (Python) | Python test directories are lowercase |

---

## 4. Artifact Naming

Build artifacts follow a structured pattern for traceability and automated processing.

### 4.1 Pattern

```
forge-<component>-<version>-<arch>.<ext>
```

### 4.2 Components

| Segment | Values | Example |
|---------|--------|---------|
| `forge` | Literal prefix (always) | `forge` |
| `<component>` | `backend`, `shell`, `agent`, `cli`, `docs` | `backend` |
| `<version>` | Semantic version (no `v` prefix) | `1.2.0` |
| `<arch>` | `arm64`, `x86_64`, `universal` | `arm64` |
| `<ext>` | `tar.gz`, `zip`, `dmg`, `pkg` | `tar.gz` |

### 4.3 Examples

| Artifact | Description |
|----------|-------------|
| `forge-backend-1.2.0-arm64.tar.gz` | Python backend, ARM64, gzipped tarball |
| `forge-shell-1.2.0-universal.dmg` | Swift shell, universal binary, disk image |
| `forge-cli-1.2.0-arm64.pkg` | CLI tool, ARM64, macOS installer package |
| `forge-docs-1.2.0.tar.gz` | Documentation bundle (no arch for docs) |

### 4.4 Anti-Examples

| ❌ Incorrect | Why |
|-------------|-----|
| `Forge-Backend-1.2.0-arm64.tar.gz` | Artifact names are all lowercase |
| `forge-backend-v1.2.0-arm64.tar.gz` | No `v` prefix on version |
| `backend-1.2.0-arm64.tar.gz` | Missing `forge-` prefix |
| `forge_backend_1.2.0_arm64.tar.gz` | Uses underscores; artifacts use hyphens |

---

## 5. State and Enum Naming

### 5.1 Python

| Kind | Convention | Example |
|------|-----------|---------|
| Enum type names | `PascalCase` | `PipelineStage`, `ConsensusState` |
| Enum members | `UPPER_SNAKE_CASE` | `PipelineStage.WAITING_FOR_APPROVAL` |
| Module-level constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES = 3`, `DEFAULT_TIMEOUT = 30` |
| Class-level constants | `UPPER_SNAKE_CASE` | `ConsensusEngine.MAX_PROVIDERS = 3` |

### 5.2 Swift

| Kind | Convention | Example |
|------|-----------|---------|
| Enum type names | `PascalCase` | `PipelineStage`, `ConsensusState` |
| Enum cases | `camelCase` | `.waitingForApproval`, `.buildFailed` |
| Static constants | `camelCase` or `PascalCase` | `static let maxRetries = 3` |
| Global constants | `camelCase` | `let defaultTimeout: TimeInterval = 30` |

### 5.3 Examples and Anti-Examples

| ✅ Correct | ❌ Incorrect | Why |
|-----------|-------------|-----|
| `PipelineStage.WAITING_FOR_APPROVAL` (Python) | `PipelineStage.waitingForApproval` (Python) | Python enum members use UPPER_SNAKE_CASE |
| `.waitingForApproval` (Swift) | `.WAITING_FOR_APPROVAL` (Swift) | Swift enum cases use camelCase |
| `MAX_RETRIES = 3` (Python) | `maxRetries = 3` (Python module-level) | Python module constants use UPPER_SNAKE_CASE |
| `ConsensusState` | `CONSENSUS_STATE` (as type name) | Type names are PascalCase in both languages |

---

## 6. Configuration Key Naming

### 6.1 Pattern

Configuration keys use dot-separated hierarchical naming with lowercase segments:

```
forge.<subsystem>.<component>.<parameter>
```

### 6.2 Rules

- All segments are lowercase.
- Words within a segment are separated by underscores only if necessary for clarity (prefer single words).
- The `forge.` prefix is mandatory for all Forge configuration keys.
- Hierarchy depth is 2-5 segments.

### 6.3 Examples

| Key | Description |
|-----|-------------|
| `forge.backend.port` | Python backend server port |
| `forge.backend.consensus.timeout` | Consensus engine timeout in seconds |
| `forge.backend.consensus.max_providers` | Maximum LLM providers for consensus |
| `forge.shell.xpc.service_name` | XPC service identifier |
| `forge.pipeline.review.max_passes` | Maximum review cycle passes |
| `forge.security.keychain.access_group` | Keychain access group identifier |

### 6.4 Anti-Examples

| ❌ Incorrect | Why |
|-------------|-----|
| `backend.port` | Missing `forge.` prefix |
| `forge.Backend.Port` | Segments must be lowercase |
| `forge-backend-port` | Use dots, not hyphens, for hierarchy |
| `FORGE_BACKEND_PORT` (as config key) | This is the environment variable form, not the config key form |

> **Note:** Environment variables derived from config keys use `FORGE_` prefix with `UPPER_SNAKE_CASE`: `forge.backend.port` → `FORGE_BACKEND_PORT`. This transformation is mechanical and handled by the configuration loader.

---

## 7. Repository Layout

The canonical repository structure reflects the two-process architecture (Swift shell + Python backend):

```
forge/                              # Repository root
├── README.md                       # Project overview (uses "Forge -- Dev Agent" branding)
├── LICENSE                         # License file
├── CONTRIBUTING.md                 # Contribution guidelines
├── AGENTS.md                       # Agent instructions (normative for AI agents)
├── .github/                        # GitHub configuration
│   ├── workflows/                  # CI/CD workflow definitions
│   └── PULL_REQUEST_TEMPLATE.md    # PR template
├── docs/                           # Human-readable documentation
│   ├── PRODUCT_IDENTITY.md         # Product identity and branding rules
│   ├── NAMING_CONVENTIONS.md       # This file (informative naming guide)
│   ├── PRD/                        # Product Requirements Documents
│   └── architecture/               # Architecture decision records
├── forge-docs/                     # TRDs (Technical Requirements Documents)
│   ├── TRD-1-macOS-Application-Shell.md
│   ├── TRD-2-Consensus-Engine.md
│   ├── ...
│   └── TRD-16-Agent-Testing-and-Validation.md
├── forge-standards/                # Normative standards (machine-parseable)
│   └── naming-conventions.md       # Authoritative naming conventions
├── src/                            # Python backend source
│   ├── __init__.py
│   ├── consensus.py                # ConsensusEngine
│   ├── build_director.py           # BuildPipeline orchestration
│   ├── github_tools.py             # GitHubTool
│   ├── build_ledger.py             # BuildLedger
│   ├── document_store.py           # DocumentStore
│   └── ...
├── tests/                          # Python backend tests
│   ├── __init__.py
│   ├── test_consensus.py
│   ├── test_build_director.py
│   └── ...
├── ForgeShell/                     # Swift shell (macOS app)
│   ├── ForgeShell.xcodeproj/
│   ├── Sources/
│   │   ├── App/
│   │   ├── Views/
│   │   ├── XPC/
│   │   └── Auth/
│   └── Tests/
├── scripts/                        # Build and utility scripts
│   ├── ci/                         # CI-specific scripts
│   └── dev/                        # Developer utility scripts
└── config/                         # Configuration templates and defaults
    ├── forge_config.yaml           # Default configuration
    └── forge_config.schema.json    # Configuration schema
```

### 7.1 Key Layout Rules

- Python source lives in `src/` at the repository root.
- Python tests live in `tests/` at the repository root.
- Swift source lives in `ForgeShell/` (PascalCase, matching Xcode conventions).
- TRDs live in `forge-docs/` (the historical location; these are the source of truth for specifications).
- Human-readable guides live in `docs/`.
- Normative standards live in `forge-standards/`.
- CI workflows live in `.github/workflows/`.

---

## 8. Quick Reference Table

| Domain | Convention | Example |
|--------|-----------|---------|
| Branch (feature) | `feature/<prd>-<pr>-<slug>` | `feature/prd001-3-product-identity` |
| Branch (fix) | `fix/<issue>-<slug>` | `fix/142-keychain-timeout` |
| Branch (release) | `release/<semver>` | `release/1.2.0` |
| Branch (agent) | `forge-agent/build/<slug>` | `forge-agent/build/add-auth-module` |
| Python file | `snake_case.py` | `build_director.py` |
| Python test file | `test_<module>.py` | `test_build_director.py` |
| Swift type file | `PascalCase.swift` | `ConsensusEngine.swift` |
| Swift variable | `camelCase` | `buildStage` |
| Python package dir | `snake_case` | `consensus_engine/` |
| Swift source dir | `PascalCase` | `BuildPipeline/` |
| Docs/config dir | `lowercase-hyphenated` | `forge-docs/` |
| Artifact | `forge-<comp>-<ver>-<arch>.<ext>` | `forge-backend-1.2.0-arm64.tar.gz` |
| Python enum member | `UPPER_SNAKE_CASE` | `PipelineStage.WAITING_FOR_APPROVAL` |
| Swift enum case | `camelCase` | `.waitingForApproval` |
| Python constant | `UPPER_SNAKE_CASE` | `MAX_RETRIES = 3` |
| Config key | `forge.<sub>.<comp>.<param>` | `forge.backend.consensus.timeout` |
| Environment variable | `FORGE_UPPER_SNAKE` | `FORGE_BACKEND_PORT` |

---

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2026-03-20 | Forge Platform Team | Initial naming conventions guide |

forge-standards/naming-conventions.md
# Naming Conventions -- Standards Track

> **Document type:** Normative Specification  
> **Status:** Active  
> **Authority:** This document is the authoritative source for naming conventions in the Forge project. The informative copy at [`docs/NAMING_CONVENTIONS.md`](../docs/NAMING_CONVENTIONS.md) provides a human-readable guide; in case of conflict, this document prevails.  
> **RFC 2119:** The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).  
> **Owner:** Forge Platform Team  
> **Last updated:** 2026-03-20

---

## 1. Branch Names

### 1.1 Feature Branches

Branch names for feature work MUST match the following pattern:

```
feature/<prd>-<pr>-<slug>
```

- `<prd>` MUST be lowercase `prd` followed by a zero-padded 3-digit number.
- `<pr>` MUST be an integer (PR sequence number, no padding).
- `<slug>` MUST be lowercase kebab-case, 2-5 words.

**Regex:**
```
^feature/prd[0-9]{3}-[0-9]+-[a-z][a-z0-9-]{1,48}[a-z0-9]$
```

### 1.2 Fix Branches

Branch names for bug fixes MUST match:

```
fix/<issue>-<slug>
```

- `<issue>` MUST be an integer (GitHub issue number).
- `<slug>` MUST be lowercase kebab-case, 2-5 words.

**Regex:**
```
^fix/[0-9]+-[a-z][a-z0-9-]{1,48}[a-z0-9]$
```

### 1.3 Release Branches

Release branch names MUST match:

```
release/<semver>
```

- `<semver>` MUST be a valid Semantic Version (`MAJOR.MINOR.PATCH`).
- The version MUST NOT include a `v` prefix.

**Regex:**
```
^release/[0-9]+\.[0-9]+\.[0-9]+$
```

### 1.4 Agent-Generated Branches

Branches created by the Forge build pipeline agent MUST match:

```
forge-agent/build/<slug>
```

- `<slug>` MUST be lowercase kebab-case, 2-5 words.

**Regex:**
```
^forge-agent/build/[a-z][a-z0-9-]{1,48}[a-z0-9]$
```

### 1.5 Hotfix Branches

Hotfix branch names
