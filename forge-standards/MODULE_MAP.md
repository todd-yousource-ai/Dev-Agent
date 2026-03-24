# MODULE_MAP.md -- Crafted Dev Agent Repository and Module Map

> **Status:** Canonical · **Audience:** All engineers · **Last updated:** 2025-01-15

---

## Purpose

This is the **single authoritative repository and module map** for the Crafted Dev Agent codebase.

Every Swift target, Python module, workflow file, test directory, standards document, script, schema, and generated artifact in the repository is catalogued here with its owning process, purpose, implementing TRD(s), and dependencies. No other document supersedes this map for questions of module placement, ownership, or cross-process boundaries.

This document fulfils the PRD-001 (Foundation Architecture) mandate:

> Produces a single authoritative repository/module map covering Swift targets (AppShell, AuthKit, KeychainKit, XPCBridge, ProcessManager, BuildStream, Settings, DocImport), Python src modules, workflow files, tests, standards docs, and generated documents.

---

## Architecture Overview

Crafted Dev Agent is a **two-process** native macOS application:

```
┌─────────────────────────────────────┐      ┌─────────────────────────────────────┐
│         SWIFT SHELL (Process 1)     │      │      PYTHON BACKEND (Process 2)     │
│                                     │      │                                     │
│  CraftedAppShell                    │      │  src/runtime  (entry point)         │
│  ├── CraftedAuthKit                 │      │  ├── src/config                     │
│  ├── CraftedKeychainKit             │      │  ├── src/models                     │
│  ├── CraftedXPCBridge ◄──────────────────────► src/xpc                          │
│  ├── CraftedProcessManager ─────────────────► (spawns/monitors Python process)  │
│  ├── CraftedBuildStream             │      │  ├── src/contracts                  │
│  ├── CraftedSettings                │      │  ├── src/workflow                   │
│  └── CraftedDocImport               │      │  ├── src/agents                     │
│                                     │      │  ├── src/consensus                  │
│  UI, auth, Keychain, lifecycle      │      │  ├── src/review                     │
│                                     │      │  ├── src/github_integration         │
│                                     │      │  ├── src/document_store             │
│                                     │      │  ├── src/build_memory               │
│                                     │      │  └── src/figma                      │
└─────────────────────────────────────┘      └─────────────────────────────────────┘
              │                                            │
              └────────── Authenticated Unix Socket ───────┘
                         Line-delimited JSON envelopes
                         (TRD-1 §6 protocol)
```

**Ownership boundary:** The Swift shell owns the user interface, authentication, Keychain access, and process lifecycle. The Python backend owns all AI orchestration, consensus, build pipeline, GitHub integration, and document management. Communication crosses the process boundary exclusively via an authenticated Unix domain socket carrying line-delimited JSON envelopes as defined in TRD-1 §6.

---

## Swift Targets

All Swift targets reside under the `Crafted/` directory and compile as part of the Xcode project.

| Target | Path | Owning Process | Purpose | Implementing TRD(s) | Dependencies |
|---|---|---|---|---|---|
| **CraftedAppShell** | `Crafted/` | Swift Shell | Main application bundle. Window management, menu bar, application lifecycle, SwiftUI host. Entry point for the macOS app. | TRD-1 | CraftedAuthKit, CraftedKeychainKit, CraftedXPCBridge, CraftedProcessManager, CraftedBuildStream, CraftedSettings, CraftedDocImport |
| **CraftedAuthKit** | `Crafted/Auth/` | Swift Shell | OAuth device-flow authentication, token lifecycle management, Touch ID biometric gating for sensitive operations. | TRD-2 | CraftedKeychainKit |
| **CraftedKeychainKit** | `Crafted/Keychain/` | Swift Shell | Keychain Services wrapper. Secure storage and retrieval of secrets (OAuth tokens, API keys). Never exposes raw secrets to logs or UI. | TRD-2, TRD-11 | Security.framework |
| **CraftedXPCBridge** | `Crafted/XPCBridge/` | Swift Shell | Unix domain socket server. Implements JSON envelope framing, handshake protocol, message routing between Swift shell and Python backend. | TRD-1 §6 | Foundation |
| **CraftedProcessManager** | `Crafted/ProcessManager/` | Swift Shell | Python process lifecycle management. Spawns, monitors, health-checks, and crash-recovers the Python backend process. | TRD-1 | Foundation |
| **CraftedBuildStream** | `Crafted/BuildStream/` | Swift Shell | Real-time build output streaming. Receives build progress events from the Python backend and renders them in the UI. | TRD-1, TRD-7 | CraftedXPCBridge |
| **CraftedSettings** | `Crafted/Settings/` | Swift Shell | User preferences, feature flags, environment configuration. Syncs relevant flags to the Python backend via XPC envelope. | TRD-1 | CraftedXPCBridge |
| **CraftedDocImport** | `Crafted/DocImport/` | Swift Shell | TRD and PRD document ingestion. Parses .docx, .md, and other document formats for import into the document store. | TRD-14 | CraftedKeychainKit (optional, for authenticated fetches) |

### Swift Target Details

#### CraftedAppShell

The root application target. Contains `@main` entry point, `AppDelegate`/SwiftUI `App` struct, window management, main menu configuration, and coordinates all other Swift targets. Responsible for startup sequencing: initialize Keychain → authenticate → launch Python backend → establish XPC connection.

#### CraftedAuthKit

Implements the OAuth 2.0 device authorization grant flow for GitHub authentication. Manages token refresh, expiration tracking, and enforces Touch ID/biometric gating before releasing tokens for sensitive operations (e.g., repository write access). All token storage delegates to CraftedKeychainKit. Tokens are never held in memory longer than the active operation requires.

#### CraftedKeychainKit

Thin, auditable wrapper around macOS Keychain Services. Provides typed `store`, `retrieve`, and `delete` operations for secrets. All errors fail closed -- a Keychain read failure returns `nil`, never a stale or default value. Secrets never appear in log output. Governed by TRD-11 security requirements.

#### CraftedXPCBridge

Implements the server side of the authenticated Unix domain socket defined in TRD-1 §6. Responsibilities: socket creation with restrictive file permissions, handshake validation (shared-secret challenge-response), JSON envelope framing (line-delimited), message dispatch to appropriate Swift targets, and unknown message type discard with logging. Unknown message types are **discarded and logged** -- never raised as exceptions.

#### CraftedProcessManager

Owns the full lifecycle of the Python backend process. Spawns the Python interpreter with the correct virtualenv and `src/runtime` entry point. Implements health-check pings over the XPC socket, exponential-backoff restart on crash, and clean shutdown signaling. If the Python process fails to start after configured retries, surfaces an explicit error to the UI -- never silently degrades.

#### CraftedBuildStream

Subscribes to build-progress event envelopes from the Python backend (routed through CraftedXPCBridge). Parses structured build events (compilation start, test results, lint output, fix-loop iteration) and drives the real-time build output view in the UI. Handles malformed events by logging and discarding -- never crashes the UI layer.

#### CraftedSettings

Manages the user-facing preferences pane and internal feature-flag store. Persists settings to `UserDefaults` and/or a JSON configuration file. When feature flags change that affect the Python backend, sends a `settings_sync` envelope over XPC. The Python backend's `src/config` module is the consumer.

#### CraftedDocImport

Provides document ingestion UI and parsing for TRDs, PRDs, and supplementary specifications. Supports `.docx` (via CoreText/third-party parser), `.md`, and plain text. Parsed content is handed to the Python backend's `src/document_store` module via XPC envelope for indexing and retrieval.

---

## Python Modules

All Python modules reside under the `src/` directory. The Python backend runs as a separate process spawned by CraftedProcessManager.

| Module Path | Owning Process | Purpose | Implementing TRD(s) | Key Exports |
|---|---|---|---|---|
| **`src/config`** | Python Backend | Environment variables, feature flags, path constants, runtime configuration. Single source of truth for all Python-side configuration. | TRD-1 | `get_config()`, `FeatureFlags`, path constants |
| **`src/models`** | Python Backend | Data models for PRs, specs, build artifacts, code generation requests, and pipeline state. | TRD-3, TRD-4 | `PRSpec`, `BuildArtifact`, `PipelineState`, `CodeGenRequest` |
| **`src/contracts`** | Python Backend | Shared JSON envelope schemas, message type constants, and validation functions for the XPC protocol. | TRD-1 §6 | `Envelope`, `MessageType`, `validate_envelope()` |
| **`src/xpc`** | Python Backend | Unix domain socket client. Implements handshake, message send/receive, connection lifecycle, and reconnection logic. | TRD-1 §6 | `XPCClient`, `connect()`, `send_message()`, `receive_message()` |
| **`src/workflow`** | Python Backend | PR decomposition engine. Takes a build intent, decomposes into ordered PRs, manages dependency graph, enforces ordering constraints. | TRD-3 | `decompose_intent()`, `PRDependencyGraph`, `order_prs()` |
| **`src/agents`** | Python Backend | LLM provider abstraction. Prompt construction, provider-specific API calls (Claude, GPT-4o), response parsing, token management. | TRD-4 | `LLMProvider`, `ClaudeProvider`, `GPT4oProvider`, `build_prompt()` |
| **`src/consensus`** | Python Backend | Two-model consensus engine. Runs Claude and GPT-4o in parallel, compares outputs, Claude arbitrates disagreements. | TRD-4 | `ConsensusEngine`, `run_consensus()`, `arbitrate()` |
| **`src/review`** | Python Backend | Self-review pass, lint gate integration, and the 20-pass fix loop. Iteratively improves generated code until it passes all quality gates or exhausts attempts. | TRD-6 | `SelfReview`, `LintGate`, `run_fix_loop()` |
| **`src/github_integration`** | Python Backend | GitHub API client. Branch management, PR creation/update, CI status polling, merge operations. All operations require authenticated tokens relayed from Swift shell. | TRD-5 | `GitHubClient`, `create_pr()`, `poll_ci()`, `merge_pr()` |
| **`src/document_store`** | Python Backend | TRD/PRD loading, indexing, chunking, and context retrieval. Maintains a document registry for specification lookup during code generation. | TRD-14 | `DocumentStore`, `load_document()`, `search()`, `get_context()` |
| **`src/build_memory`** | Python Backend | Persistent build history and error-pattern database. Records build outcomes, extracts error patterns, generates self-improving build rules. Build memory is **never cleared automatically** -- it is a persistent learning system. | TRD-8 | `BuildMemory`, `record_outcome()`, `query_patterns()`, `build_rules` |
| **`src/figma`** | Python Backend | Figma API integration. Design token extraction, component mapping, style-guide synchronization for UI-aware code generation. | TRD-13 | `FigmaClient`, `extract_tokens()`, `map_components()` |
| **`src/runtime`** | Python Backend | Python process entry point. Establishes socket connection to Swift shell, runs the main event loop, dispatches incoming messages to appropriate modules. | TRD-1 | `main()`, `EventLoop`, `dispatch()` |

### Module Dependency Summary (Python)

```
src/runtime
├── src/xpc           (socket communication)
├── src/config        (configuration)
├── src/contracts     (message validation)
├── src/workflow      (PR decomposition)
│   └── src/models
├── src/agents        (LLM providers)
│   └── src/models
├── src/consensus     (two-model engine)
│   └── src/agents
├── src/review        (self-review / fix loop)
│   ├── src/agents
│   └── src/github_integration
├── src/github_integration
│   └── src/models
├── src/document_store
│   └── src/models
├── src/build_memory
│   └── src/models
└── src/figma
```

---

## Workflow Files

All GitHub Actions workflow files reside in `.github/workflows/`.

| Workflow File | Trigger Conditions | Purpose | Related TRD(s) |
|---|---|---|---|
| **`ci.yml`** | `push` to `main`, `pull_request` to `main` | Primary CI pipeline. Runs Python tests, linting (ruff/mypy), and Swift build verification. Gates PR merges on passing status. | TRD-5, TRD-9 |
| **`swift-build.yml`** | `push` to `main`, `pull_request` -- paths: `Crafted/**` | Builds the Xcode project on macOS runners. Runs XCTest suites. Validates Swift shell compilation and test pass. | TRD-9 |
| **`python-tests.yml`** | `push` to `main`, `pull_request` -- paths: `src/**`, `tests/**` | Runs the Python test suite (`pytest`), coverage reporting, and type checking. | TRD-9 |
| **`lint.yml`** | `push` to `main`, `pull_request` | Runs `ruff`, `mypy`, and `swiftlint` across the codebase. Enforces code-quality gates. | TRD-6, TRD-9 |
| **`release.yml`** | `push` tags: `v*` | Builds release artifacts, signs the macOS app bundle, and publishes to the configured distribution channel. | TRD-9 |
| **`docs-check.yml`** | `pull_request` -- paths: `forge-standards/**`, `forge-docs/**`, `crafted-docs/**` | Validates documentation structure, checks for broken internal links, and optionally lints Markdown. | TRD-7 |

---

## Test Directories

| Test Directory | Covers Module(s) | Test Framework | Purpose |
|---|---|---|---|
| **`tests/`** | All `src/` Python modules | pytest | Python backend unit and integration tests. Mirrors `src/` module structure. |
| **`tests/config/`** | `src/config` | pytest | Configuration loading, feature flag parsing, path resolution. |
| **`tests/models/`** | `src/models` | pytest | Data model validation, serialization, edge cases. |
| **`tests/contracts/`** | `src/contracts` | pytest | Envelope schema validation, message type coverage, malformed input rejection. |
| **`tests/xpc/`** | `src/xpc` | pytest | Socket client handshake, message framing, reconnection logic. |
| **`tests/workflow/`** | `src/workflow` | pytest | PR decomposition correctness, dependency graph ordering, cycle detection. |
| **`tests/agents/`** | `src/agents` | pytest | LLM provider abstraction, prompt construction, response parsing. |
| **`tests/consensus/`** | `src/consensus` | pytest | Two-model consensus logic, arbitration rules, disagreement handling. |
| **`tests/review/`** | `src/review` | pytest | Self-review pass, lint gate integration, fix-loop termination conditions. |
| **`tests/github_integration/`** | `src/github_integration` | pytest | GitHub API client mocking, branch management, PR lifecycle. |
| **`tests/document_store/`** | `src/document_store` | pytest | Document loading, indexing, chunking, context retrieval accuracy. |
| **`tests/build_memory/`** | `src/build_memory` | pytest | Build outcome recording, pattern extraction, rule persistence. |
| **`tests/figma/`** | `src/figma` | pytest | Figma API mocking, token extraction, component mapping. |
| **`tests/runtime/`** | `src/runtime` | pytest | Entry point initialization, event loop dispatch, graceful shutdown. |
| **`CraftedTests/`** | All `Crafted/` Swift targets | XCTest | Swift shell unit and integration tests. |
| **`CraftedTests/Auth/`** | `CraftedAuthKit` | XCTest | OAuth flow, token lifecycle, Touch ID gating. |
| **`CraftedTests/Keychain/`** | `CraftedKeychainKit` | XCTest | Keychain read/write/delete, error handling, fail-closed behavior. |
| **`CraftedTests/XPCBridge/`** | `CraftedXPCBridge` | XCTest | Socket creation, handshake, envelope framing, unknown type discard. |
| **`CraftedTests/ProcessManager/`** | `CraftedProcessManager` | XCTest | Process spawn, health checks, crash recovery, clean shutdown. |
| **`CraftedTests/BuildStream/`** | `CraftedBuildStream` | XCTest | Event parsing, malformed event handling, UI state updates. |
| **`CraftedTests/Settings/`** | `CraftedSettings` | XCTest | Preference persistence, feature flag sync, defaults handling. |
| **`CraftedTests/DocImport/`** | `CraftedDocImport` | XCTest | Document parsing formats, import validation, error reporting. |

---

## Standards and Specification Documents

### `forge-standards/` -- Engineering Standards

| Document | Purpose |
|---|---|
| **`ARCHITECTURE.md`** | High-level architecture decisions, two-process model rationale, technology choices. |
| **`INTERFACES.md`** | API contracts, XPC envelope schema reference, module interface specifications. |
| **`DECISIONS.md`** | Architecture Decision Records (ADRs). Chronological log of significant design decisions with context and rationale. |
| **`CONVENTIONS.md`** | Code style, naming conventions, commit message format, PR structure requirements. |
| **`MODULE_MAP.md`** | **This document.** Single authoritative repository and module map. |
| **`build_rules.md`** | Auto-generated build rules derived from `src/build_memory`. **Do not delete** -- this is a persistent learning artifact. |

### `forge-docs/` -- TRDs and PRDs (Source of Truth)

All Technical Requirements Documents (TRDs) and Product Requirements Documents (PRDs) reside here. These are the **source of truth** for all implementation. Code must match specifications.

| Document | Title | Scope |
|---|---|---|
| **TRD-1** | macOS Application Shell | Two-process architecture, Swift shell, XPC protocol, process lifecycle |
| **TRD-2** | Authentication & Secrets | OAuth device flow, Keychain integration, Touch ID, token lifecycle |
| **TRD-3** | Build Pipeline | PR decomposition, ordering, dependency management, pipeline orchestration |
| **TRD-4** | Multi-Agent Coordination | Consensus engine, LLM provider abstraction, two-model arbitration |
| **TRD-5** | GitHub Integration | GitHub API, branch management, PR creation, CI status, merge operations |
| **TRD-6** | Holistic Code Review | Self-review pass, lint gate, 20-pass fix loop, quality enforcement |
| **TRD-7** | TRD Development Workflow | Specification authoring process, review gates, build stream integration |
| **TRD-8** | Build Memory | Persistent build history, error patterns, self-improving rules |
| **TRD-9** | Mac CI Runner | macOS CI infrastructure, runner configuration, workflow definitions |
| **TRD-10** | Document Store | Document parsing, indexing, chunking, registry, context retrieval |
| **TRD-11** | Security Model | Security architecture, Keychain policy, secret handling, threat model |
| **TRD-12** | Observability | Logging, metrics, tracing, health checks, diagnostic tooling |
| **TRD-13** | Figma Integration | Design token extraction, component mapping, style synchronization |
| **TRD-14** | Document Import | TRD/PRD ingestion, parsing formats, import pipeline |
| **TRD-15** | Agent Operational Runbook | Process ownership, startup model, operational procedures, recovery |
| **TRD-16** | Deployment & Distribution | App signing, notarization, update mechanism, release pipeline |
| **PRD-001** | Foundation Architecture | Naming migration, repository skeleton, module map mandate |

### `crafted-docs/` -- Product Documentation

| Document | Purpose |
|---|---|
| **User guides** | End-user documentation for operating the Crafted Dev Agent. |
| **Onboarding** | New engineer onboarding materials and environment setup instructions. |
| **Changelog** | Release notes and version history. |

---

## Scripts, Schemas, and Generated Documents

### Scripts

| Path | Purpose | Related TRD(s) |
|---|---|---|
| **`scripts/setup.sh`** | Development environment setup. Creates virtualenv, installs dependencies, validates Xcode toolchain. | -- |
| **`scripts/bootstrap.sh`** | Repository bootstrap for new clones. Initializes configuration, runs first-time checks. | TRD-5 §10 |
| **`scripts/run_tests.sh`** | Unified test runner. Executes both Python (pytest) and Swift (xcodebuild test) suites. | TRD-9 |
| **`scripts/lint.sh`** | Runs all linters (ruff, mypy, swiftlint) with project configuration. | TRD-6 |
| **`scripts/release.sh`** | Builds, signs, and packages the macOS application for distribution. | TRD-16 |

### Schemas

| Path | Purpose | Related TRD(s) |
|---|---|---|
| **`schemas/envelope.json`** | JSON Schema for the XPC message envelope format. Validates all messages crossing the Swift↔Python boundary. | TRD-1 §6 |
| **`schemas/pr_spec.json`** | JSON Schema for PR specification objects produced by the decomposition engine. | TRD-3 |
| **`schemas/build_artifact.json`** | JSON Schema for build artifact metadata stored by build memory. | TRD-8 |
| **`schemas/doc_registry.json`** | JSON Schema for the document registry used by the document store. | TRD-10, TRD-14 |
| **`schemas/doc_record.json`** | JSON Schema for individual document records and chunk metadata. | TRD-10 |

### Generated Documents

| Path | Purpose | Generated By | Persistence Policy |
|---|---|---|---|
| **`forge-standards/build_rules.md`** | Accumulated build rules extracted from build memory error patterns. | `src/build_memory` | **Never cleared automatically.** Persistent learning artifact. |
| **`generated/doc_registry.json`** | Runtime document registry. Lists all ingested TRDs/PRDs with chunk indices. | `src/document_store` | Regenerated on document import; previous version archived. |
| **`generated/coverage_report.html`** | Test coverage report from most recent CI run. | CI workflow (`python-tests.yml`) | Overwritten each CI run. |

---

## Cross-Process Boundary Map

Every communication path that crosses the Swift shell ↔ Python backend process boundary is documented below. **No other cross-process communication paths exist.** Any new boundary must be added to this table in the same PR that introduces it.

| Swift Module | Direction | Python Module | Protocol | Data Exchanged | Governing TRD Section |
|---|---|---|---|---|---|
| **CraftedXPCBridge** | ↔ | **src/xpc** | Authenticated Unix domain socket, line-delimited JSON envelopes | All message types: commands, responses, events, errors | TRD-1 §6 |
| **CraftedKeychainKit** | → | **src/github_integration** | Token relay via XPC envelope (`token_grant` message type) | OAuth tokens for GitHub API authentication. Tokens are transmitted in-envelope, never persisted on the Python side beyond the active operation. | TRD-1 §6, TRD-2, TRD-11 |
| **CraftedBuildStream** | ← | **src/runtime** | Build progress event envelopes via XPC socket | Structured build events: compilation start/end, test results, lint output, fix-loop iteration status, error details | TRD-1 §6, TRD-7 |
| **CraftedSettings** | ↔ | **src/config** | Feature-flag sync envelope (`settings_sync` message type) via XPC socket | Feature flags, environment overrides, user preferences relevant to backend behavior | TRD-1 §6 |
| **CraftedDocImport** | → | **src/document_store** | Document payload envelope (`doc_import` message type) via XPC socket | Parsed document content, metadata, format indicators for indexing | TRD-1 §6, TRD-14 |
| **CraftedProcessManager** | → | **src/runtime** | Process signals (spawn, SIGTERM, health-check ping via XPC) | Lifecycle control: start, shutdown, health-check request/response | TRD-1 |

### Boundary Security Invariants

1. **Authentication:** The Unix socket handshake uses a shared-secret challenge-response. No messages are processed before handshake completion.
2. **Unknown message types:** Discarded and logged on both sides. Never raised as exceptions.
3. **Token handling:** OAuth tokens relayed from CraftedKeychainKit are envelope-wrapped, used for the immediate API call, and not persisted by the Python backend.
4. **Fail closed:** Any handshake failure, authentication error, or envelope validation failure terminates the connection. No fallback to unauthenticated communication.
5. **Input validation:** All envelopes are validated against `schemas/envelope.json` before dispatch. Malformed envelopes are rejected with logged context.

---

## TRD Coverage Matrix

Maps every TRD (1-16) to the Swift targets and Python modules that implement its requirements.

| TRD | Title | Swift Targets | Python Modules |
|---|---|---|---|
| **TRD-1** | macOS Application Shell | CraftedAppShell, CraftedXPCBridge, CraftedProcessManager, CraftedBuildStream, CraftedSettings | src/runtime, src/xpc, src/contracts, src/config |
| **TRD-2** | Authentication & Secrets | CraftedAuthKit, CraftedKeychainKit | -- (tokens relayed via envelope) |
| **TRD-3** | Build Pipeline | -- | src/workflow, src/models |
| **TRD-4** | Multi-Agent Coordination | -- | src/agents, src/consensus, src/models |
| **TRD-5** | GitHub Integration | -- | src/github_integration |
| **TRD-6** | Holistic Code Review | -- | src/review |
| **TRD-7** | TRD Development Workflow | CraftedBuildStream | src/workflow |
| **TRD-8** | Build Memory | -- | src/build_memory |
| **TRD-9** | Mac CI Runner | -- (CI infrastructure) | -- (CI infrastructure) |
| **TRD-10** | Document Store | -- | src/document_store |
| **TRD-11** | Security Model | CraftedKeychainKit, CraftedAuthKit, CraftedXPCBridge | src/xpc, src/contracts, src/github_integration |
| **TRD-12** | Observability | CraftedAppShell | src/runtime, src/config |
| **TRD-13** | Figma Integration | -- | src/figma |
| **TRD-14** | Document Import | CraftedDocImport | src/document_store |
| **TRD-15** | Agent Operational Runbook | CraftedProcessManager, CraftedAppShell | src/runtime |
| **TRD-16** | Deployment & Distribution | CraftedAppShell | -- (release infrastructure) |

### TRD-9 Note

TRD-9 (Mac CI Runner) is primarily implemented by GitHub Actions workflow files (`.github/workflows/`) and runner infrastructure configuration, not by application modules. The workflow files listed in the [Workflow Files](#workflow-files) section are the primary implementation artifacts.

### TRD-12 Note

TRD-12 (Observability) is cross-cutting. While `src/runtime` and `CraftedAppShell` are the primary integration points for logging and health-check infrastructure, all modules participate by emitting structured log output and surfacing errors with context.

---

## Naming and Placement Rules

### Crafted-First Naming (PRD-001)

All **new** modules, targets, classes, and user-facing references use `Crafted` as the product name:

- Swift targets: `CraftedAppShell`, `CraftedAuthKit`, `CraftedXPCBridge`, etc.
- Swift test targets: `CraftedTests/`
- Product references in UI, docs, and logs: "Crafted Dev Agent" or "Crafted"
- Python module names under `src/` do not carry a product prefix (they are namespaced by directory)

### Legacy Compatibility Exceptions

The following paths retain the `forge` prefix because they are **existing canonical paths** established before the naming migration and referenced by tooling, CI, and cross-repository links:

| Path | Reason for Retention |
|---|---|
| **`forge-standards/`** | Established standards directory. Referenced by CI workflows, linting tools, and external documentation links. |
| **`forge-docs/`** | Canonical TRD/PRD storage directory. Referenced by all 16 TRDs and PRD-001. Renaming would break document cross-references. |

### Placement Rules

| Artifact Type | Canonical Path | Notes |
|---|---|---|
| Swift application code | `Crafted/` | Organized by target subdirectories |
| Swift tests | `CraftedTests/` | Mirrors `Crafted/` target structure |
| Python backend code | `src/` | One subdirectory per module |
| Python tests | `tests/` | Mirrors `src/` module structure |
| TRDs and PRDs | `forge-docs/` | Source of truth. Do not duplicate. |
| Engineering standards | `forge-standards/` | Architecture, interfaces, decisions, conventions, this module map |
| Product documentation | `crafted-docs/` | User guides, onboarding, changelog |
| GitHub Actions workflows | `.github/workflows/` | All CI/CD workflow definitions |
| JSON schemas | `schemas/` | Envelope, PR spec, build artifact, document registry schemas |
| Utility scripts | `scripts/` | Setup, bootstrap, test runners, release tooling |
| Generated artifacts | `generated/` | Runtime-generated files (registries, reports). Not committed to main except `build_rules.md`. |

### Naming Violations

If you encounter a module, target, or path that does not conform to these rules:

1. File an issue referencing this document
2. Do **not** rename without a dedicated migration PR
3. Update this document in the same PR that performs the rename

---

## Maintenance Policy

### When to Update

This document **must** be updated in the **same PR** that performs any of the following:

- Adds a new Swift target
- Adds a new Python module under `src/`
- Removes or renames any module or target
- Adds a new GitHub Actions workflow file
- Adds a new JSON schema
- Changes cross-process communication paths or protocols
- Changes the directory structure for tests, docs, or scripts
- Introduces a new TRD or retires an existing one

### How to Update

1. Edit `forge-standards/MODULE_MAP.md` (this file)
2. Update the relevant table(s) and section(s)
3. Update the "Last updated" date in the document header
4. If adding a cross-process boundary, update both the
