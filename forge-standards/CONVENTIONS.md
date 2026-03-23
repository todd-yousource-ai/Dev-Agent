# Code Conventions — Forge Platform

> Authoritative coding conventions for the Forge platform and the **CraftedDevAgent** subsystem.
> Every rule is mandatory unless explicitly marked **(advisory)**.

---

## 1. File and Directory Naming

| # | Rule |
|---|------|
| 1.1 | Python source files use **snake_case** with no abbreviations longer than four letters: `build_director.py`, `ci_workflow.py`. |
| 1.2 | Swift source files use **PascalCase** matching the primary type: `StreamGateCard.swift`, `TouchIDAuthView.swift`. |
| 1.3 | Test files mirror the `src/` tree exactly under `tests/`. A module at `src/cal/router.py` is tested at `tests/cal/test_router.py`. |
| 1.4 | Subsystem directories use the canonical short names. Never alias or abbreviate further. |

```
src/cal/           — Conversation Abstraction Layer
src/dtl/           — Data Trust Label
src/trustflow/     — TrustFlow audit stream
src/vtz/           — Virtual Trust Zone enforcement
src/trustlock/     — Cryptographic machine identity (TPM-anchored)
src/mcp/           — MCP Policy Engine
src/rewind/        — Forge Rewind replay engine
sdk/connector/     — Forge Connector SDK
```

| # | Rule (continued) |
|---|------|
| 1.5 | CI workflow files are named `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS / Swift). No other names are accepted by the pipeline. |
| 1.6 | `conftest.py` at the repo root is **auto-committed** by `ci_workflow.ensure()` to wire `src/` imports. Never hand-edit this file. |
| 1.7 | Key backend modules keep their canonical names. Do not rename or relocate without a TRD amendment: |

```
src/consensus.py        — ConsensusEngine, GENERATION_SYSTEM, SWIFT_GENERATION_SYSTEM + UI_ADDENDUM
src/build_director.py   — BuildPipeline orchestration, confidence gate, pr_type routing
src/github_tools.py     — GitHubTool, WebhookReceiver
src/build_ledger.py     — BuildLedger, claim/release, heartbeat
src/document_store.py   — DocumentStore, chunk(), embed(), retrieve()
src/ci_workflow.py      — CI workflow generation and conftest management
```

---

## 2. Branch Naming

| # | Rule |
|---|------|
| 2.1 | All agent-created branches **must** follow this pattern exactly: |

```
forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
```

| # | Rule (continued) |
|---|------|
| 2.2 | `engineer_id` — the lowercase Forge engineer handle, no underscores (use hyphens). |
| 2.3 | `subsystem_slug` — one of the canonical directory short names from §1.4 or a feature slug (lowercase, hyphen-separated). |
| 2.4 | `N` — zero-padded to three digits (`001`, `042`). Monotonically increasing per engineer per subsystem. |
| 2.5 | `title_slug` — lowercase, hyphens only, max 48 characters, no trailing hyphen. |
| 2.6 | The `forge-agent` prefix is **intentional and must not change** — external CI filters and compatibility tooling depend on it. |

---

## 3. Class and Function Naming

| # | Rule |
|---|------|
| 3.1 | **Python classes** — `PascalCase`. Suffix with role when ambiguous: `BuildLedger`, `WebhookReceiver`, `ConsensusEngine`. |
| 3.2 | **Python functions / methods** — `snake_case`. Prefix with verb: `validate_write_path()`, `retrieve_chunks()`, `ensure_workflow()`. |
| 3.3 | **Python constants** — `UPPER_SNAKE_CASE`. Group related constants at module top: `GENERATION_SYSTEM`, `MAX_RETRIES`. |
| 3.4 | **Swift types** — `PascalCase`. Views are suffixed `View`; view-models suffixed `ViewModel`: `StreamGateCardView`, `ProjectListViewModel`. |
| 3.5 | **Swift methods / properties** — `camelCase`, verb-first for mutating methods: `loadProjects()`, `dismissGate()`. |
| 3.6 | Private helpers are prefixed with a single underscore in Python (`_emit_event`) and marked `private` in Swift. |
| 3.7 | Boolean variables and properties start with `is_`, `has_`, or `should_`: `is_docs_pr`, `has_quorum`, `should_retry`. |

---

## 4. Accessibility Identifier Naming (axIdentifier — Swift / macOS)

| # | Rule |
|---|------|
| 4.1 | Every interactive SwiftUI element **must** have `.accessibilityIdentifier()` set. |
| 4.2 | Format: `{module}-{component}-{role}-{context?}` — all lowercase, hyphen-separated. |
| 4.3 | Dynamic suffixes use a variable id: `navigator-project-row-{projectId}`. |
| 4.4 | Reference examples (canonical): |

```
"auth-touchid-button"
"auth-passcode-button"
"settings-anthropic-key-field"
"settings-anthropic-key-test-button"
"settings-anthropic-key-reveal-button"
"navigator-project-row-{projectId}"
"stream-gate-card-{gateId}"
"stream-gate-yes-button-{gateId}"
"stream-gate-skip-button-{gateId}"
"stream-gate-stop-button-{gateId}"
```

| 4.5 | UI tests must locate elements **only** by `axIdentifier`, never by label text or frame position. |

---

## 5. Error and Exception Patterns

| # | Rule |
|---|------|
| 5.1 | Define a per-subsystem base exception inheriting `Exception`: `class CalError(Exception)`, `class TrustFlowError(Exception)`. |
| 5.2 | Concrete exceptions subclass the base and carry a machine-readable `code` attribute: |

```python
class PathTraversalError(VtzError):
    code = "VTZ_PATH_TRAVERSAL"
```

| 5.3 | Never catch bare `Exception` or `BaseException` outside top-level entry points. Catch the narrowest subsystem exception. |
| 5.4 | All agent-facing errors must include a one-line `detail` string safe for logging (no secrets, no PII). |
| 5.5 | In Swift, prefer typed `Error` enums per module. Always include an associated `String` context value: |

```swift
enum AuthError: Error {
    case biometricUnavailable(reason: String)
    case keychainWriteFailed(status: OSStatus)
}
```

| 5.6 | Retryable operations must use an explicit retry policy (`max_retries`, `backoff_seconds`) — never open-ended loops. |

---

## 6. Import and Module Organisation

| # | Rule |
|---|------|
| 6.1 | Python imports are grouped in this order, separated by a blank line: (1) stdlib, (2) third-party, (3) `src.*` project imports. |
| 6.2 | Use absolute imports from the `src` package root: `from src.build_ledger import BuildLedger`. Relative imports are prohibited. |
| 6.3 | Circular imports are a build-breaking defect. If two modules need each other, extract shared types into a `_types.py` in the same package. |
| 6.4 | Swift imports are ordered: