docs/PRODUCT_IDENTITY.md:
# Product Identity -- Forge

> Authoritative product identity reference for the Consensus Dev Agent project.
> This document is normative for all user-facing naming decisions.

---

## Document Metadata

| Field       | Value                                      |
|-------------|--------------------------------------------|
| Status      | **Active**                                 |
| Created     | 2026-03-21                                 |
| Applies to  | All code, UI, CLI, docs, logs, CI, comms   |
| Authority   | PRD-001 § Product Identity                 |
| Owner       | Forge Platform Team                        |

---

## 1. Product Name Hierarchy

### 1.1 Primary Name -- **Forge**

**Forge** is the canonical, user-facing product name. It is used in all contexts unless a more specific form is explicitly required by this document.

- One word, capitalized: **Forge**
- No prefix, no suffix, no domain qualifier in general usage.
- This is the name users see, type, and say.

### 1.2 Subheader -- **Dev Agent**

**Dev Agent** is the descriptive subheader. It provides disambiguation when the audience may not know what Forge is, but it is **not** part of the short product name.

- Used in combination: **Forge -- Dev Agent** (em-dash separated)
- Used in taglines, landing pages, and first-mention contexts.
- Never used alone as a product name.
- Never concatenated: ~~ForgeDevAgent~~, ~~Forge Dev-Agent~~, ~~forge-dev-agent~~

### 1.3 Full Formal Name -- **Consensus Dev Agent**

**Consensus Dev Agent** is the full formal name. It appears **only** in:

- Legal and copyright notices
- LICENSE files and headers
- Formal attribution lines
- Internal architecture documentation where the consensus mechanism is the subject
- The `AGENTS.md` repository identity block (existing, legacy-compatible)

It is **never** used in user-facing UI, CLI output, marketing, or casual documentation.

---

## 2. Usage Rules by Context

| Context | Allowed Form(s) | Example |
|---|---|---|
| **UI chrome** (window titles, menu bar, About screen) | `Forge` or `Forge -- Dev Agent` | Window title: `Forge` · About: `Forge -- Dev Agent` |
| **CLI output** (banners, help text, version strings) | `Forge` or `forge` (lowercase in binary name) | `forge --version` → `Forge 1.2.0` |
| **CLI binary / command name** | `forge` (lowercase) | `$ forge build`, `$ forge status` |
| **Code comments & docstrings** | `Forge` | `# Forge consensus engine initialization` |
| **Python module / package names** | `forge_*` (snake_case prefix) | `forge_backend`, `forge_consensus` |
| **Swift module / target names** | `Forge*` (PascalCase prefix) | `ForgeShell`, `ForgeXPC` |
| **README and documentation** | `Forge` (first mention: `Forge -- Dev Agent`) | `# Forge -- Dev Agent\n\nForge is a native macOS AI coding agent.` |
| **External docs / blog posts** | `Forge` (first mention: `Forge (Dev Agent)`) | `Forge (Dev Agent) automates PR-driven development.` |
| **Error messages** | `Forge` | `Forge: authentication failed -- operator approval required` |
| **Log lines** | `forge` or `Forge` (logger name lowercase) | `forge.consensus: round completed` or `[Forge] Pipeline stage 3 done` |
| **Git tags** | `v<semver>` (no product prefix) | `v1.2.0` |
| **Artifact filenames** | `forge-<component>-<ver>-<arch>.<ext>` | `forge-backend-1.2.0-arm64.tar.gz` |
| **Environment variables** | `FORGE_` prefix, UPPER_SNAKE | `FORGE_BACKEND_PORT`, `FORGE_LOG_LEVEL` |
| **Configuration keys** | `forge.` prefix, dot-separated | `forge.backend.consensus.timeout` |
| **Copyright / legal** | `Consensus Dev Agent` | `© 2026 YouSource.ai -- Consensus Dev Agent` |

---

## 3. Prohibited Forms

The following forms are **explicitly prohibited** in all new code, documentation, UI text, and external communications. Existing occurrences are categorized as legacy (see §5).

| Prohibited Form | Reason |
|---|---|
| `ConsensusDevAgent` (CamelCase, user-facing) | Internal formal name leaked into user context; not the product name |
| `Consensus Dev Agent` (user-facing UI/CLI/docs) | Full formal name is reserved for legal/copyright only (see §1.3) |
| `CDA` | Unapproved abbreviation; ambiguous, not recognizable |
| `forge.ai` | Unapproved domain-style name; implies a domain/URL that may not exist |
| `ForgeAI` | Unapproved concatenation; Forge is not branded as an "AI" product name |
| `Forge AI` (two words, as product name) | Unapproved variant; the product is `Forge`, not `Forge AI` |
| `forge-agent` (as product name) | Acceptable only as an artifact component or branch prefix, never as the product name |
| `The Forge` | Unapproved; do not add articles to the product name |
| `FORGE` (all-caps, in prose) | Acceptable only in environment variable prefixes (`FORGE_`), not in prose or UI |
| `Dev Agent` (standalone, as product name) | Subheader only; never used alone as the product name |
| `forgedev` / `forge-dev` (as product name) | Unapproved concatenation/hyphenation |

---

## 4. Canonical Descriptions

### 4.1 One-liner

> **Forge** is an enterprise AI coding agent that decomposes build intents into verified, operator-gated pull requests.

### 4.2 Tagline

> **Forge -- Dev Agent**: From intent to merged code, with a human at every gate.

### 4.3 Extended Description (one paragraph)

> Forge is a native macOS AI coding agent built for defense and financial sector clients. It takes a plain-language build intent, decomposes it into an ordered sequence of pull requests, generates implementation and tests using a multi-provider consensus engine, runs a three-pass review cycle with CI validation, and gates on explicit operator approval before merging. The human is in the loop at every decision point. Forge enforces deny-by-default security, fail-closed error handling, and full auditability across the entire pipeline.

---

## 5. Legacy and Internal References

### 5.1 Existing "Consensus Dev Agent" References

The repository was bootstrapped with the formal name "Consensus Dev Agent" in several foundational documents:

- `AGENTS.md` -- Repository identity block
- `forge-docs/` TRD documents (TRD-1 through TRD-16)
- Architecture context documents

These references are **legacy-compatible** and **not required to be renamed retroactively** in existing TRDs or `AGENTS.md`. However:

- **New documents** MUST use `Forge` as the product name per the rules in §2.
- **Updates to existing documents** SHOULD migrate references to `Forge` where practical.
- The `AGENTS.md` identity block MAY retain `Consensus Dev Agent` for continuity until a dedicated migration PR is scoped.

### 5.2 Internal Code Identifiers

Internal identifiers that predate this document (e.g., class names like `ConsensusEngine`, module paths like `src/consensus.py`) are **architectural names**, not product branding. They are governed by naming conventions (see `docs/NAMING_CONVENTIONS.md`), not by this product identity document. The class `ConsensusEngine` describes the consensus mechanism; it is not a user-facing product name.

---

## 6. Internal Code Reference Conventions

When the product name appears in code-level identifiers, follow these rules:

| Identifier Type | Convention | Example |
|---|---|---|
| Python package name | `forge_` prefix, snake_case | `forge_backend`, `forge_pipeline` |
| Python module name | `snake_case` (no prefix if inside forge package) | `consensus.py`, `build_director.py` |
| Python class name | `PascalCase`, no `Forge` prefix unless disambiguating | `ConsensusEngine`, `BuildPipeline` |
| Python constant | `UPPER_SNAKE_CASE` | `FORGE_DEFAULT_TIMEOUT` |
| Swift target/module | `Forge` prefix, PascalCase | `ForgeShell`, `ForgeXPCService` |
| Swift type name | `PascalCase` | `ConsensusRound`, `BuildStage` |
| Logger name | `forge.<subsystem>` | `forge.consensus`, `forge.pipeline` |
| Environment variable | `FORGE_` prefix | `FORGE_LOG_LEVEL` |

---

## 7. Attribution and Copyright Line

### 7.1 Standard Copyright

```
© 2026 YouSource.ai -- Consensus Dev Agent
```

This is the **only** context where the full formal name "Consensus Dev Agent" is required.

### 7.2 File Header (Python)

```python
# Forge -- Dev Agent
# © 2026 YouSource.ai -- Consensus Dev Agent
# SPDX-License-Identifier: Proprietary
```

### 7.3 File Header (Swift)

```swift
// Forge -- Dev Agent
// © 2026 YouSource.ai -- Consensus Dev Agent
// SPDX-License-Identifier: Proprietary
```

---

## 8. Decision Authority

Product identity disputes are resolved by the following hierarchy (highest priority first):

1. This document (`docs/PRODUCT_IDENTITY.md`)
2. PRD-001 § Product Identity
3. TRD-11 (security-relevant naming only)
4. Platform team decision logged in PR review

---

*This document is maintained under version control. Changes require PR review and platform team approval.*

docs/NAMING_CONVENTIONS.md:
# Naming Conventions -- Forge

> Human-readable guide to naming conventions across the Forge project.
> For the normative, machine-parseable specification, see [`forge-standards/naming-conventions.md`](../forge-standards/naming-conventions.md) (authoritative).

---

## Document Metadata

| Field       | Value                                                             |
|-------------|-------------------------------------------------------------------|
| Status      | **Active -- Informative**                                         |
| Authoritative Copy | `forge-standards/naming-conventions.md`                  |
| Created     | 2026-03-21                                                       |
| Applies to  | All code, docs, CI, artifacts in the Forge repository            |
| Authority   | PRD-001 § Naming Conventions                                     |

> **Note:** If this document and `forge-standards/naming-conventions.md` conflict, the `forge-standards/` copy is authoritative. This document is the friendly guide; that document is the enforceable specification.

---

## Quick Reference Table

| Domain | Convention | Example |
|---|---|---|
| Branch (feature) | `feature/<prd>-<pr>-<slug>` | `feature/prd001-03-product-identity` |
| Branch (fix) | `fix/<issue>-<slug>` | `fix/142-consensus-timeout` |
| Branch (release) | `release/<semver>` | `release/1.2.0` |
| Branch (agent) | `forge-agent/build/<slug>` | `forge-agent/build/prd001-pr03` |
| Python file | `snake_case.py` | `build_director.py` |
| Swift type file | `PascalCase.swift` | `ConsensusRound.swift` |
| Docs directory | `lowercase-hyphenated/` | `forge-docs/`, `forge-standards/` |
| Python package dir | `snake_case/` | `forge_backend/` |
| Swift group/folder | `PascalCase/` | `ForgeShell/`, `Services/` |
| Artifact | `forge-<component>-<ver>-<arch>.<ext>` | `forge-backend-1.2.0-arm64.tar.gz` |
| Python constant | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Python enum member | `UPPER_SNAKE_CASE` | `BuildStage.CODE_GENERATION` |
| Python enum type | `PascalCase` | `BuildStage` |
| Swift enum type | `PascalCase` | `PipelineState` |
| Swift enum case | `camelCase` | `.codeGeneration` |
| Config key | `dot.separated.hierarchical` | `forge.backend.consensus.timeout` |
| Environment var | `FORGE_UPPER_SNAKE` | `FORGE_LOG_LEVEL` |

---

## 1. Branch Naming

All branch names use lowercase with forward-slash separators. No spaces, no uppercase.

### 1.1 Feature Branches

```
feature/<prd>-<pr>-<slug>
```

- `<prd>`: PRD identifier, lowercase, no punctuation (e.g., `prd001`)
- `<pr>`: PR sequence number, zero-padded to 2 digits (e.g., `03`)
- `<slug>`: lowercase-hyphenated short description (e.g., `product-identity`)

**Examples:**
- `feature/prd001-03-product-identity`
- `feature/prd002-01-consensus-engine-init`

### 1.2 Fix Branches

```
fix/<issue>-<slug>
```

- `<issue>`: GitHub issue number (e.g., `142`)
- `<slug>`: lowercase-hyphenated short description

**Examples:**
- `fix/142-consensus-timeout`
- `fix/87-xpc-handshake-race`

### 1.3 Release Branches

```
release/<semver>
```

- `<semver>`: Semantic version (e.g., `1.2.0`)
- No pre-release suffixes on branch names; use tags for pre-release identifiers.

**Examples:**
- `release/1.0.0`
- `release/1.2.0`

### 1.4 Agent-Generated Branches

```
forge-agent/build/<slug>
```

- Used exclusively by automated agent processes (the Forge build pipeline).
- `<slug>`: lowercase-hyphenated description of the automated work.

**Examples:**
- `forge-agent/build/prd001-pr03`
- `forge-agent/build/trd02-consensus-tests`

### 1.5 Anti-Examples (Branch Naming)

| ❌ Wrong | ✅ Correct | Reason |
|---|---|---|
| `Feature/PRD001-03-ProductIdentity` | `feature/prd001-03-product-identity` | Must be all lowercase, hyphenated slug |
| `fix-142-consensus-timeout` | `fix/142-consensus-timeout` | Must use `/` separator after prefix |
| `todd/my-branch` | `feature/prd001-03-my-feature` | Personal prefixes not allowed |
| `forge-agent-build-something` | `forge-agent/build/something` | Must use `/` separator hierarchy |

---

## 2. File Naming

### 2.1 Python Files

All Python files use `snake_case` with the `.py` extension.

| ✅ Correct | ❌ Wrong |
|---|---|
| `build_director.py` | `BuildDirector.py` |
| `consensus_engine.py` | `consensusEngine.py` |
| `test_build_pipeline.py` | `TestBuildPipeline.py` |
| `__init__.py` | `init.py` |

### 2.2 Swift Files

Swift source files are named after the primary type they contain, using `PascalCase`.

| ✅ Correct | ❌ Wrong |
|---|---|
| `ConsensusRound.swift` | `consensus_round.swift` |
| `BuildPipeline.swift` | `buildPipeline.swift` |
| `ForgeApp.swift` | `forge_app.swift` |

Swift variables and function names use `camelCase`:

```swift
// ✅ Correct
let consensusTimeout = 30
func startBuildPipeline() { }

// ❌ Wrong
let ConsensusTimeout = 30
let consensus_timeout = 30
func StartBuildPipeline() { }
```

### 2.3 Documentation Files

- Markdown files: `UPPER_SNAKE_CASE.md` for top-level docs (e.g., `PRODUCT_IDENTITY.md`, `NAMING_CONVENTIONS.md`)
- Markdown files in subdirectories: `lowercase-hyphenated.md` (e.g., `naming-conventions.md` in `forge-standards/`)
- TRD documents: `TRD-<number>-<PascalSlug>.md` (e.g., `TRD-11-Security-Threat-Model.md`)

### 2.4 Configuration / YAML / TOML Files

- `lowercase-hyphenated.ext` or `snake_case.ext`
- Examples: `pyproject.toml`, `.github/workflows/ci-build.yml`

### 2.5 Anti-Examples (File Naming)

| ❌ Wrong | ✅ Correct | Reason |
|---|---|---|
| `BuildDirector.py` | `build_director.py` | Python files must be snake_case |
| `consensus_round.swift` | `ConsensusRound.swift` | Swift type files must be PascalCase |
| `product identity.md` | `PRODUCT_IDENTITY.md` | No spaces in filenames |
| `CI-Build.yml` | `ci-build.yml` | Config files must be lowercase |

---

## 3. Directory Naming

### 3.1 Documentation and Configuration Directories

Use `lowercase-hyphenated`:

```
docs/
forge-docs/
forge-standards/
.github/workflows/
```

### 3.2 Python Package Directories

Use `snake_case`:

```
forge_backend/
forge_consensus/
test_utils/
```

### 3.3 Swift Group / Folder Directories

Use `PascalCase`:

```
ForgeShell/
Services/
Views/
Models/
XPCService/
```

### 3.4 Anti-Examples (Directory Naming)

| ❌ Wrong | ✅ Correct | Reason |
|---|---|---|
| `ForgeStandards/` (for docs) | `forge-standards/` | Docs/config dirs must be lowercase-hyphenated |
| `forge-backend/` (Python pkg) | `forge_backend/` | Python packages must be snake_case (hyphen breaks imports) |
| `services/` (Swift) | `Services/` | Swift groups use PascalCase |
| `Forge Docs/` | `forge-docs/` | No spaces; use hyphens |

---

## 4. Artifact Naming

All build artifacts follow the pattern:

```
forge-<component>-<version>-<arch>.<ext>
```

| Component | Description |
|---|---|
| `<component>` | Lowercase-hyphenated subsystem name (e.g., `backend`, `shell`, `xpc-service`) |
| `<version>` | Semantic version (e.g., `1.2.0`) |
| `<arch>` | Target architecture (e.g., `arm64`, `x86-64`, `universal`) |
| `<ext>` | File extension (e.g., `tar.gz`, `dmg`, `zip`, `pkg`) |

**Examples:**
- `forge-backend-1.2.0-arm64.tar.gz`
- `forge-shell-1.2.0-universal.dmg`
- `forge-xpc-service-1.2.0-arm64.pkg`

**Anti-Examples:**

| ❌ Wrong | ✅ Correct | Reason |
|---|---|---|
| `ForgeBackend-1.2.0.tar.gz` | `forge-backend-1.2.0-arm64.tar.gz` | Must be lowercase, must include arch |
| `backend-v1.2.0-arm64.tar.gz` | `forge-backend-1.2.0-arm64.tar.gz` | Must include `forge-` prefix; no `v` in version |
| `forge_backend_1.2.0_arm64.tar.gz` | `forge-backend-1.2.0-arm64.tar.gz` | Must use hyphens, not underscores |

---

## 5. State and Enum Naming

### 5.1 Python

| Identifier | Convention | Example |
|---|---|---|
| Enum type name | `PascalCase` | `BuildStage`, `PipelineState` |
| Enum member | `UPPER_SNAKE_CASE` | `BuildStage.CODE_GENERATION`, `PipelineState.WAITING_FOR_GATE` |
| Module-level constant | `UPPER_SNAKE_CASE` | `MAX_CONSENSUS_ROUNDS`, `DEFAULT_TIMEOUT_SECONDS` |
| Boolean flag constant | `UPPER_SNAKE_CASE` | `ENABLE_AUDIT_LOG` |

```python
# ✅ Correct
class BuildStage(enum.Enum):
    PLANNING = "planning"
    CODE_GENERATION = "code_generation"
    REVIEW = "review"
    CI_VALIDATION = "ci_validation"
    GATE_APPROVAL = "gate_approval"
    MERGE = "merge"

MAX_CONSENSUS_ROUNDS = 3
DEFAULT_TIMEOUT_SECONDS = 300

# ❌ Wrong
class buildStage(enum.Enum):    # type name must be PascalCase
    Planning = "planning"        # members must be UPPER_SNAKE_CASE
    codeGeneration = "codegen"   # members must be UPPER_SNAKE_CASE
```

### 5.2 Swift

| Identifier | Convention | Example |
|---|---|---|
| Enum type name | `PascalCase` | `PipelineState`, `ConsensusResult` |
| Enum case | `camelCase` | `.codeGeneration`, `.waitingForGate` |
| Static constant | `camelCase` (on type) or `UPPER_SNAKE` (global) | `PipelineConfig.defaultTimeout` |
| Global constant | `let kConstantName` or `UPPER_SNAKE_CASE` | `let kMaxRetryCount = 3` |

```swift
// ✅ Correct
enum PipelineState {
    case idle
    case codeGeneration
    case waitingForGate
    case merging
    case failed(Error)
}

// ❌ Wrong
enum pipelineState {           // type name must be PascalCase
    case CodeGeneration        // cases must be camelCase
    case WAITING_FOR_GATE      // cases must be camelCase
}
```

---

## 6. Configuration Key Naming

All configuration keys use **dot-separated hierarchical** notation with lowercase segments.

### 6.1 Pattern

```
forge.<subsystem>.<component>.<parameter>
```

### 6.2 Examples

| Key | Description |
|---|---|
| `forge.backend.consensus.timeout` | Consensus engine timeout in seconds |
| `forge.backend.consensus.max_rounds` | Maximum consensus rounds (underscore within segment is acceptable) |
| `forge.backend.pipeline.stage_timeout` | Per-stage timeout |
| `forge.shell.ui.theme` | UI theme selection |
| `forge.security.gate.auto_approve` | Gate auto-approve setting (always `false` -- see TRD-11) |
| `forge.github.api.base_url` | GitHub API base URL |

### 6.3 Rules

- All keys start with `forge.` prefix.
- Segments are lowercase.
- Multi-word segments use `snake_case` (underscore within a segment).
- Segments are separated by dots (`.`).
- No uppercase, no hyphens, no camelCase in key segments.

### 6.4 Anti-Examples

| ❌ Wrong | ✅ Correct | Reason |
|---|---|---|
| `FORGE_BACKEND_TIMEOUT` | `forge.backend.consensus.timeout` | That's env var format, not config key format |
| `forge.Backend.Consensus.Timeout` | `forge.backend.consensus.timeout` | Segments must be lowercase |
| `forge-backend-consensus-timeout` | `forge.backend.consensus.timeout` | Must use dot separators |
| `consensus.timeout` | `forge.backend.consensus.timeout` | Must include `forge.` prefix |

---

## 7. Repository Layout Specification

The canonical directory structure for the Forge repository, reflecting the two-process architecture (Swift shell + Python backend):

```
forge/                              # Repository root
├── .github/
│   └── workflows/                  # CI workflow definitions
│       ├── ci-build.yml
│       └── ci-test.yml
├── docs/                           # Human-readable project documentation
│   ├── PRODUCT_IDENTITY.md         # Product identity (this project)
│   ├── NAMING_CONVENTIONS.md       # Naming guide (this document)
│   ├── PRD-001.md                  # Product requirements
│   └── ...
├── forge-docs/                     # TRD specifications (source of truth)
│   ├── TRD-1-macOS-Application-Shell.md
│   ├── TRD-2-Consensus-Engine.md
│   ├── ...
│   └── TRD-16-Agent-Testing-and-Validation.md
├── forge-standards/                # Normative standards for CI enforcement
│   └── naming-conventions.md       # Authoritative naming spec
├── ForgeShell/                     # Swift macOS application shell
│   ├── ForgeApp.swift
│   ├── Views/
│   ├── Services/
│   ├── XPCService/
│   └── Models/
├── src/                            # Python backend source
│   ├── __init__.py
│   ├── consensus.py
│   ├── build_director.py
│   ├── github_tools.py
│   ├── build_ledger.py
│   ├── document_store.py
│   └── ...
├── tests/                          # Python test suite
│   ├── __init__.py
│   ├── test_consensus.py
│   ├── test_build_director.py
│   └── ...
├── scripts/                        # Build and utility scripts
├── AGENTS.md                       # Agent instructions
├── README.md                       # Project README
├── pyproject.toml                  # Python project configuration
└── .gitignore
```

### Layout Rules

- Top-level documentation directories use `lowercase-hyphenated` names.
- The Swift shell lives in `ForgeShell/` (PascalCase).
- The Python backend lives in `src/` (established convention).
- Tests mirror source structure in `tests/`.
- Standards documents live in `forge-standards/` (normative, for tooling).
- Human-readable docs live in `docs/` (informative, for humans).
- TRD specifications live in `forge-docs/` (source of truth for architecture).

---

## 8. Examples and Anti-Examples Summary

### Naming a New Python Module

You're adding a module for audit logging.

| Decision | Correct | Wrong |
|---|---|---|
| Filename | `audit_logger.py` | `AuditLogger.py`, `audit-logger.py` |
| Class name | `AuditLogger` | `audit_logger`, `AUDIT_LOGGER` |
| Constants | `MAX_LOG_RETENTION_DAYS` | `maxLogRetentionDays`, `MaxLogRetentionDays` |
| Config key | `forge.backend.audit.retention_days` | `forge.audit.RetentionDays` |
| Env var | `FORGE_AUDIT_RETENTION_DAYS` | `forge_audit_retention_days` |

### Naming a New Swift View

You're adding a consensus status view.

| Decision | Correct | Wrong |
|---|---|---|
| Filename | `ConsensusStatusView.swift` | `consensus_status_view.swift` |
| Type name | `ConsensusStatusView` | `consensusStatusView` |
| Folder | `Views/` | `views/` |
| Enum case | `.waitingForConsensus` | `.WaitingForConsensus`, `.WAITING` |

### Creating a Feature Branch

You're starting PR #5 for PRD-002.

| Decision | Correct | Wrong |
|---|---|---|
| Branch name | `feature/prd002-05-audit-logging` | `feature/PRD002-5-AuditLogging` |

---

## 9. Enforcement

These conventions will be enforced by:

1. **PR review** -- Reviewers check naming compliance.
2. **CI linters** -- Automated checks against regex patterns defined in `forge-standards/naming-conventions.md`.
3. **Agent validation** -- The Forge agent validates naming during code generation (TRD-14, TRD-16).

---

## 10. References

- **Authoritative specification:** [`forge-standards/naming-conventions.md`](../forge-standards/naming-conventions.md)
- **Product identity:** [`docs/PRODUCT_IDENTITY.md`](./PRODUCT_IDENTITY.md)
- **Repository identity:** [`AGENTS.md`](../AGENTS.md)
- **Architecture context:** [`forge-docs/`](../forge-docs/)

---

*This document is the informative guide. For normative rules with RFC 2119 keywords and regex patterns, see `forge-standards/naming-conventions.md`.*

forge-standards/naming-conventions.md:
# Naming Conventions -- Normative Specification

> **Status: Active -- Normative**
>
> This is the authoritative, standards-track naming conventions document for the Forge project.
> It uses RFC 2119 keywords (MUST, MUST NOT, SHOULD, SHOULD NOT, MAY) to indicate requirement levels.
> CI linters and automated tooling SHOULD reference this document for enforcement patterns.

---

## Document Metadata

| Field              | Value                                       |
|--------------------|---------------------------------------------|
| Status             | **Active -- Normative**                      |
| Created            | 2026-03-21                                  |
| Informative Copy   | `docs/NAMING_CONVENTIONS.md`                |
| Authority          | PRD-001 § Naming Conventions                |
| RFC 2119 Keywords  | Per [RFC 2119](https://tools.ietf.org/html/rfc2119) |
| Owner              | Forge Platform Team                         |

---

## Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).

---

## 1. Branch Names

### 1.1 Feature Branches

Branch names for feature work MUST match:

```
feature/<prd>-<pr>-<slug>
```

**Regex:**
```regex
^feature\/[a-z]+[0-9]+-[0-9]{2,}-[a-z0-9]+(-[a-z0-9]+)*$
```

**Constraints:**
- `<prd>` MUST be a lowercase PRD identifier (e.g., `prd001`).
- `<pr>` MUST be a zero-padded PR sequence number with at least 2 digits (e.g., `03`).
- `<slug>` MUST be lowercase-hyphenated, containing only `[a-z0-9-]`.
- The entire branch name MUST be lowercase.
- Spaces MUST NOT appear in branch names.

### 1.2 Fix Branches

Branch names for bug fixes MUST match:

```
fix/<issue>-<slug>
```

**Regex:**
```regex
^fix\/[0-9]+-[a-z0-9]+(-[a-z0-9]+)*$
```

**Constraints:**
- `<issue>` MUST be a numeric GitHub issue number.
- `<slug>` MUST be lowercase-hyphenated.

### 1.3 Release Branches

Branch names for releases MUST match:

```
release/
