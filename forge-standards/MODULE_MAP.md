# Crafted Dev Agent -- Repository and Module Map

> **Document ID:** MODMAP-1
> **Version:** 1.0.0
> **Status:** Normative
> **Created:** 2025-01-15
> **Last Amended:** 2025-01-15
> **Authority:** This document is the **single authoritative repository and module map** for the Crafted Dev Agent project.
> **Scope:** All Swift targets, Python modules, CI workflows, test directories, standards documents, TRDs, generated documentation, scripts, schemas, and cross-process boundaries.

---

## 1. Purpose

This document is the **single source of truth** for repository layout, module ownership, and TRD traceability across the Crafted Dev Agent system. It answers four questions for every contributor (human and AI):

1. **What exists** -- every Swift target, Python module, workflow file, test directory, standards document, and generated artifact.
2. **Who owns what** -- which process (Swift shell vs. Python backend) owns each component and where the cross-process boundary lies.
3. **Which TRD governs what** -- the mapping from each module to its governing Technical Requirements Document.
4. **Where things live** -- canonical repository-relative paths so agents and humans resolve references unambiguously.

### 1.1 Maintenance Policy

**Any PR that adds, removes, renames, or moves a module, target, workflow, test directory, or standards document MUST update this document in the same PR.** This is a merge-blocking requirement. Failure to co-update this document will cause documentation drift and break TRD traceability.

---

## 2. Architecture Overview

Crafted Dev Agent is a **two-process macOS application**:

- **Swift Shell** -- owns the UI, authentication, Keychain, Touch ID, process lifecycle management, and user-facing rendering.
- **Python Backend** -- owns LLM calls, GitHub operations, build orchestration, consensus engine, document store, and self-review pipeline.

The two processes communicate over an **authenticated Unix domain socket** using **line-delimited JSON** as the wire protocol.

```
┌─────────────────────────────────┐     Unix Socket      ┌─────────────────────────────────┐
│         Swift Shell             │   (line-delimited     │        Python Backend            │
│                                 │       JSON)           │                                  │
│  • CraftedAppShell              │◄───────────────────►  │  • src/agent.py (entry point)    │
│  • CraftedAuthKit               │                       │  • src/runtime.py (main loop)    │
│  • CraftedKeychainKit           │  crafted.agent.sock   │  • src/consensus.py              │
│  • CraftedXPCBridge             │                       │  • src/workflow.py               │
│  • CraftedProcessManager        │                       │  • src/models.py                 │
│  • CraftedBuildStream           │                       │  • src/review.py                 │
│  • CraftedSettings              │                       │  • src/github_integration.py     │
│  • CraftedDocImport             │                       │  • src/document_store.py         │
│                                 │                       │  • ... (16 modules total)        │
└─────────────────────────────────┘                       └─────────────────────────────────┘
         │                                                           │
         ▼                                                           ▼
   macOS Keychain                                              GitHub API
   Touch ID / LAContext                                        LLM Providers
   User Interface                                              CI Pipeline
```

**Security invariants of this boundary:**

- Neither process executes generated code -- no `eval`, no `exec`, no subprocess of generated content.
- Secrets (API keys, tokens) stay in the Swift shell's Keychain -- they are injected into the Python backend only via secure environment variables or authenticated IPC, never logged.
- Unknown IPC message types are discarded and logged -- never raised as exceptions.
- Gates wait indefinitely for operator input -- no auto-approve, ever.

---

## 3. Swift Targets

All Swift targets reside under the `Crafted/` directory. The Swift shell is the **UI-owning process**.

| # | Target | Path | Process Owner | Governing TRD | Purpose |
|---|--------|------|---------------|---------------|---------|
| 1 | CraftedAppShell | `Crafted/AppShell/` | Swift Shell | TRD-1 | Main application entry point, window management, menu bar, and top-level SwiftUI view hierarchy |
| 2 | CraftedAuthKit | `Crafted/AuthKit/` | Swift Shell | TRD-11 | Touch ID / biometric authentication via `LAContext`, credential validation, auth session lifecycle |
| 3 | CraftedKeychainKit | `Crafted/KeychainKit/` | Swift Shell | TRD-11 | Keychain CRUD operations for API keys and secrets; fail-closed on all Keychain errors |
| 4 | CraftedXPCBridge | `Crafted/XPCBridge/` | Swift Shell | TRD-1 §6 | Unix socket wire protocol implementation; line-delimited JSON serialization/deserialization; message routing |
| 5 | CraftedProcessManager | `Crafted/ProcessManager/` | Swift Shell | TRD-1 | Python backend process lifecycle -- spawn, monitor, heartbeat, graceful shutdown, crash recovery |
| 6 | CraftedBuildStream | `Crafted/BuildStream/` | Swift Shell | TRD-1 | Real-time build output streaming to UI; progressive rendering of agent pipeline stages and gate cards |
| 7 | CraftedSettings | `Crafted/Settings/` | Swift Shell | TRD-1 | User preferences, model selection, API key management UI, and configuration persistence |
| 8 | CraftedDocImport | `Crafted/DocImport/` | Swift Shell | TRD-1 | TRD and specification file import into the application; document picker, validation, and handoff to backend |

### 3.1 Swift Target Notes

- All Swift targets use the `Crafted` prefix per the naming conventions in `forge-standards/CONVENTIONS.md` §2.1.
- Bundle identifier: `com.crafted.dev-agent` (TRD-1 §2.1).
- All targets share the `com.crafted.dev-agent` `os_log` subsystem with per-module categories (see CONVENTIONS.md §3.3).
- Auth and Keychain targets fail closed on every error -- no fallback to unencrypted storage or default values.

---

## 4. Python Modules (src/)

All Python modules reside under the `src/` directory. The Python backend is the **intelligence-owning process**.

| # | Module | Path | Governing TRD | Purpose |
|---|--------|------|---------------|---------|
| 1 | config | `src/config.py` | TRD-15 | Runtime configuration loading, environment variable parsing, validation, and default resolution |
| 2 | models | `src/models.py` | TRD-3 | LLM provider abstraction layer -- Claude (Anthropic) and GPT-4o (OpenAI) API clients, response normalization |
| 3 | contracts | `src/contracts.py` | TRD-4 | PR contract schema definition, validation, and enforcement; ensures every PR has a well-formed specification |
| 4 | xpc | `src/xpc.py` | TRD-1 §6 | Python side of the Unix socket protocol; line-delimited JSON reading/writing; message dispatch and marker handling |
| 5 | workflow | `src/workflow.py` | TRD-2 | PR decomposition and sequencing; transforms a build intent into an ordered queue of implementable PRs |
| 6 | agents | `src/agents.py` | TRD-2 | Agent orchestration and intent decomposition; coordinates multi-step reasoning across the pipeline |
| 7 | consensus | `src/consensus.py` | TRD-3 | Two-model consensus engine -- runs Claude and GPT-4o in parallel, Claude arbitrates disagreements |
| 8 | review | `src/review.py` | TRD-6 | Self-review pipeline, lint gate enforcement, and 20-pass fix loop for generated code |
| 9 | github_integration | `src/github_integration.py` | TRD-5 | GitHub API operations -- repository access, branch creation, PR creation, commit pushing, CI status polling |
| 10 | document_store | `src/document_store.py` | TRD-7 | TRD ingestion, FAISS vector store management, semantic retrieval, and document chunking |
| 11 | build_memory | `src/build_memory.py` | TRD-8 | Cross-build learning and pattern memory; persistent storage of build outcomes for future reference |
| 12 | figma | `src/figma.py` | TRD-10 | Figma design token import; translates Figma design specifications into actionable UI parameters |
| 13 | runtime | `src/runtime.py` | TRD-15 | Agent main loop, startup sequence, shutdown handling, and signal management |
| 14 | build_rules | `src/build_rules.py` | TRD-8 | Self-improving build rules; learns from CI outcomes to refine future build strategies |
| 15 | context_manager | `src/context_manager.py` | TRD-3 | Context window management, conversation history trimming, and token budget allocation |
| 16 | agent | `src/agent.py` | TRD-15 | Main entry point for the Python backend process; bootstraps runtime and begins accepting commands |

### 4.1 Python Module Notes

- All Python modules are imported under the `src` package namespace.
- No module executes generated code -- this is a system-wide invariant enforced by design.
- Secrets are received via environment variables (`CRAFTED_GITHUB_TOKEN`, `CRAFTED_ANTHROPIC_TOKEN`) or secure IPC -- never hardcoded, never logged.
- Build memory (`src/build_memory.py`) and build rules (`src/build_rules.py`) are **never cleared automatically** -- they are persistent learning systems.
- All external input (documents, PR comments, CI output) is treated as untrusted and validated before processing.

---

## 5. Cross-Process Boundary

This section documents the communication boundary between the Swift shell and the Python backend.

### 5.1 Communication Mechanism

| Property | Value |
|----------|-------|
| Transport | Unix domain socket |
| Socket path | `~/.crafted/run/crafted.agent.sock` |
| Wire format | Line-delimited JSON (one JSON object per `\n`-terminated line) |
| Protocol specification | TRD-1 §6 |
| Naming reference | CONVENTIONS.md §3.5 |

### 5.2 Ownership Split

| Responsibility | Owning Process | Rationale |
|----------------|----------------|-----------|
| User interface rendering | Swift Shell | Native macOS SwiftUI; hardware-accelerated |
| Authentication (Touch ID, biometrics) | Swift Shell | Requires `LAContext` which must run in the UI process |
| Keychain CRUD | Swift Shell | macOS Keychain is process-scoped; secrets must not leave the shell |
| Process lifecycle management | Swift Shell | Shell spawns, monitors, and terminates the backend |
| Build output streaming to UI | Swift Shell | Renders progressive output from backend into SwiftUI views |
| LLM API calls | Python Backend | Complex prompt management, token counting, and provider abstraction |
| GitHub API operations | Python Backend | Branch creation, PR management, commit pushing, CI polling |
| Build orchestration and sequencing | Python Backend | PR decomposition, dependency ordering, queue management |
| Consensus engine | Python Backend | Dual-model inference, arbitration, and merge |
| Self-review and fix loops | Python Backend | 20-pass automated fix cycle, lint gate enforcement |
| Document store and retrieval | Python Backend | FAISS indexing, semantic search, TRD ingestion |
| Build memory and learning | Python Backend | Persistent cross-build pattern storage |

### 5.3 Security Invariants

These invariants are **non-negotiable** and must hold at all times across the process boundary:

1. **No code execution** -- Neither process executes generated code. No `eval`, no `exec`, no subprocess invocation of LLM-generated content.
2. **Secrets stay in Swift** -- API keys and tokens are stored in the macOS Keychain, managed by `CraftedKeychainKit`. They are injected into the Python backend only via secure environment variables or authenticated IPC messages. They are **never** logged, included in error messages, or written to disk outside the Keychain.
3. **Unknown messages are discarded** -- Any IPC message with an unrecognized type is logged at warning level and discarded. It is never raised as an exception, never interpreted as a command, and never forwarded.
4. **Gates wait indefinitely** -- When the Python backend sends a `CRAFTED_GATE` signal requesting operator approval, the Swift shell displays the gate card and waits indefinitely. There is no timeout and no auto-approve mechanism.
5. **Fail closed on auth errors** -- If authentication, Keychain access, or credential validation fails for any reason, the system denies the operation and surfaces the error with context. There is no degraded-access fallback.
6. **Path validation** -- All file write operations are validated via `path_security.validate_write_path()` before execution. Path traversal attacks are prevented at the boundary.
7. **External input is untrusted** -- All data received from documents, PR comments, CI output, and LLM responses is treated as untrusted input and validated before use. Context from external documents is placed in the USER prompt, never the SYSTEM prompt.

### 5.4 IPC Marker Reference

The following signals cross the process boundary (see CONVENTIONS.md §3.11 for the complete registry):

| Marker | Direction | Purpose |
|--------|-----------|---------|
| `CRAFTED_READY` | Python → Swift | Backend initialization complete; safe to send commands |
| `CRAFTED_SHUTDOWN` | Swift → Python | Initiate graceful shutdown |
| `CRAFTED_SHUTDOWN_ACK` | Python → Swift | Shutdown sequence begun; Swift may send SIGTERM after timeout |
| `CRAFTED_HEARTBEAT` | Python → Swift | Periodic liveness signal |
| `CRAFTED_ERROR` | Bidirectional | Fatal error requiring operator attention |
| `CRAFTED_GATE` | Python → Swift | Request operator approval via UI gate card |

---

## 6. CI / Workflow Files

All CI workflow files reside in `.github/workflows/`.

| # | Workflow File | Path | Governing TRD | Trigger Conditions | Purpose |
|---|---------------|------|---------------|--------------------|---------|
| 1 | crafted-ci.yml | `.github/workflows/crafted-ci.yml` | TRD-9 | Push to `forge-agent/build/*` and `crafted/*` branches; pull request events | Main CI pipeline -- Python tests, linting, unit tests |
| 2 | crafted-ci-macos.yml | `.github/workflows/crafted-ci-macos.yml` | TRD-9, TRD-5 §9.2 | Push to `forge-agent/build/*` and `crafted/*` branches; changes to `Crafted/**` | Swift build and test on self-hosted macOS runner; XCTest execution |

### 6.1 CI Notes

- The `forge-agent/build/` branch prefix is a **legacy exception** documented in CONVENTIONS.md §4.1. It is retained to avoid CI trigger breakage.
- CI mode is indicated by the `CRAFTED_CI_MODE=1` environment variable (CONVENTIONS.md §3.6).
- All CI workflows must pass before an agent-generated PR can be presented for operator approval.
- CI output is treated as untrusted external input by the Python backend.

---

## 7. Test Directories

### 7.1 Python Tests

| Test Directory | Path | Corresponding Source Module(s) | Governing TRD |
|----------------|------|-------------------------------|---------------|
| Python test root | `tests/` | All `src/` modules | TRD-9 |
| Config tests | `tests/test_config.py` | `src/config.py` | TRD-15 |
| Models tests | `tests/test_models.py` | `src/models.py` | TRD-3 |
| Contracts tests | `tests/test_contracts.py` | `src/contracts.py` | TRD-4 |
| XPC tests | `tests/test_xpc.py` | `src/xpc.py` | TRD-1 §6 |
| Workflow tests | `tests/test_workflow.py` | `src/workflow.py` | TRD-2 |
| Agents tests | `tests/test_agents.py` | `src/agents.py` | TRD-2 |
| Consensus tests | `tests/test_consensus.py` | `src/consensus.py` | TRD-3 |
| Review tests | `tests/test_review.py` | `src/review.py` | TRD-6 |
| GitHub integration tests | `tests/test_github_integration.py` | `src/github_integration.py` | TRD-5 |
| Document store tests | `tests/test_document_store.py` | `src/document_store.py` | TRD-7 |
| Build memory tests | `tests/test_build_memory.py` | `src/build_memory.py` | TRD-8 |
| Figma tests | `tests/test_figma.py` | `src/figma.py` | TRD-10 |
| Runtime tests | `tests/test_runtime.py` | `src/runtime.py` | TRD-15 |
| Build rules tests | `tests/test_build_rules.py` | `src/build_rules.py` | TRD-8 |
| Context manager tests | `tests/test_context_manager.py` | `src/context_manager.py` | TRD-3 |
| Agent tests | `tests/test_agent.py` | `src/agent.py` | TRD-15 |

### 7.2 Swift Tests

| Test Target | Path | Corresponding Swift Target(s) | Governing TRD |
|-------------|------|-------------------------------|---------------|
| CraftedTests | `CraftedTests/` | All Swift targets under `Crafted/` | TRD-9, TRD-1 |

### 7.3 Test Notes

- Python tests are executed by the `crafted-ci.yml` workflow on push and PR events.
- Swift tests (XCTest) are executed by the `crafted-ci-macos.yml` workflow on a self-hosted macOS runner.
- Test files follow the `test_{module}.py` naming convention corresponding to `src/{module}.py`.
- All tests must pass before a PR can proceed to operator gate approval.

---

## 8. Standards Documents (forge-standards/)

The `forge-standards/` directory contains normative engineering standards and conventions that govern the Crafted Dev Agent project.

| # | Document | Path | Purpose |
|---|----------|------|---------|
| 1 | ARCHITECTURE.md | `forge-standards/ARCHITECTURE.md` | System architecture overview, component relationships, and architectural decision records |
| 2 | INTERFACES.md | `forge-standards/INTERFACES.md` | Interface contracts between subsystems, API boundaries, and protocol specifications |
| 3 | DECISIONS.md | `forge-standards/DECISIONS.md` | Architectural Decision Records (ADRs) capturing key design decisions and their rationale |
| 4 | CONVENTIONS.md | `forge-standards/CONVENTIONS.md` | Canonical naming conventions and identifier registry (CONV-1); single authoritative naming registry |
| 5 | BUILD_ORDER.md | `forge-standards/BUILD_ORDER.md` | TRD build prioritization order and gap analysis; implementation sequencing guide |
| 6 | build_rules.md | `forge-standards/build_rules.md` | Auto-generated build rules -- self-improving rules learned from CI outcomes. **Do not delete.** |
| 7 | MODULE_MAP.md | `forge-standards/MODULE_MAP.md` | This document -- the single authoritative repository and module map |

### 8.1 Standards Notes

- `build_rules.md` is **auto-generated** by the build memory system (`src/build_rules.py`). It must not be manually edited or deleted. It is a persistent learning artifact per Forge invariants.
- `CONVENTIONS.md` is the naming authority. All identifier decisions defer to it (see CONVENTIONS.md §1.1 for the authority chain).
- This document (`MODULE_MAP.md`) is the structural authority. All path and ownership questions defer to it.

---

## 9. Technical Requirements Documents (forge-docs/)

The `forge-docs/` directory contains all 16 TRDs that are the **normative source of truth** for the Crafted Dev Agent system. Code must match TRDs. Where TRDs and code disagree, the TRD is authoritative.

| # | TRD | Filename | Scope |
|---|-----|----------|-------|
| 1 | TRD-1 | `forge-docs/TRD-1-macOS-Application-Shell.docx` | macOS application shell architecture, two-process model, XPC bridge, UI framework, window management, and process lifecycle |
| 2 | TRD-2 | `forge-docs/TRD-2-Consensus-Engine.docx` | PR decomposition, intent sequencing, workflow orchestration, and agent coordination |
| 3 | TRD-3 | `forge-docs/TRD-3-Build-Pipeline.docx` | LLM provider abstraction, dual-model consensus, context window management, and token budgeting |
| 4 | TRD-4 | `forge-docs/TRD-4-Multi-Agent-Coordination.docx` | PR contract schema, multi-agent coordination protocols, and contract validation |
| 5 | TRD-5 | `forge-docs/TRD-5-GitHub-Integration.docx` | GitHub API integration, branch management, PR creation, CI status polling, and repository bootstrap |
| 6 | TRD-6 | `forge-docs/TRD-6-Holistic-Code-Review.docx` | Self-review pipeline, lint gate enforcement, 20-pass fix loop, and code quality assurance |
| 7 | TRD-7 | `forge-docs/TRD-7-TRD-Development-Workflow.docx` | TRD ingestion, document store, vector indexing, semantic retrieval, and specification management |
| 8 | TRD-8 | `forge-docs/TRD-8-UIUX-Design-System.docx` | UI/UX design system, build memory, self-improving build rules, and cross-build learning |
| 9 | TRD-9 | `forge-docs/TRD-9-Mac-CI-Runner.docx` | macOS CI runner configuration, GitHub Actions workflows, test execution, and CI pipeline design |
| 10 | TRD-10 | `forge-docs/TRD-10-Document-Store.docx` | Document parsing, FAISS vector store, chunking strategies, design token import, and document registry schema |
| 11 | TRD-11 | `forge-docs/TRD-11-Security-Auth.docx` | Security architecture, authentication (Touch ID/biometrics), Keychain management, credential lifecycle, and threat model |
| 12 | TRD-12 | `forge-docs/TRD-12-Error-Handling.docx` | Error handling strategy, fail-closed behavior, error surfacing, and recovery procedures |
| 13 | TRD-13 | `forge-docs/TRD-13-Testing-Strategy.docx` | Testing strategy, test coverage requirements, test isolation, and quality gates |
| 14 | TRD-14 | `forge-docs/TRD-14-Deployment.docx` | Deployment procedures, code signing, notarization, update mechanisms, and release management |
| 15 | TRD-15 | `forge-docs/TRD-15-Runtime-Config.docx` | Runtime configuration, environment variable management, startup/shutdown sequencing, and agent entry point |
| 16 | TRD-16 | `forge-docs/TRD-16-Observability.docx` | Observability, logging, metrics, diagnostics, and operational monitoring |

### 9.1 TRD Notes

- TRDs are stored as `.docx` files in `forge-docs/`.
- TRDs are the highest authority in the precedence chain (see CONVENTIONS.md §1.1).
- The build prioritization order for implementing TRDs is documented in `forge-standards/BUILD_ORDER.md`.
- TRD amendments follow the change control process defined within each TRD.

---

## 10. Generated Documentation (crafted-docs/)

The `crafted-docs/` directory contains **generated documentation** produced by the agent pipeline and build processes.

| # | Content | Path | Purpose |
|---|---------|------|---------|
| 1 | Generated documentation root | `crafted-docs/` | Output directory for all documentation generated by the Crafted Dev Agent |

### 10.1 crafted-docs/ Notes

- This directory contains documentation artifacts **generated** during build and agent operations -- it is not a source-of-truth directory.
- Source-of-truth specifications live in `forge-docs/` (TRDs) and `forge-standards/` (engineering standards).
- Contents may include generated API references, build reports, PR summaries, and pipeline output documentation.
- Generated content in this directory may be regenerated at any time from source materials -- it should not be manually edited as edits will be overwritten.
- The generation process is governed by the Python backend's document store and build pipeline modules.

---

## 11. Scripts

The `scripts/` directory contains operational and build automation scripts.

| # | Script / Directory | Path | Purpose |
|---|-------------------|------|---------|
| 1 | Scripts root | `scripts/` | Operational scripts for build automation, setup, CI support, and development workflows |

### 11.1 Script Notes

- All scripts must validate paths via `path_security.validate_write_path()` before any filesystem write operation.
- Scripts must not contain hardcoded secrets or credentials.
- Scripts that interact with external services must use environment variables or Keychain-sourced credentials.

---

## 12. Schemas

Schema files define the data contracts used across the system.

| # | Schema | Location | Governing TRD | Purpose |
|---|--------|----------|---------------|---------|
| 1 | PR Contract Schema | Defined in `src/contracts.py` | TRD-4 | Validates PR contract structure -- ensures every PR specification is well-formed |
| 2 | DocumentRecord Schema | Defined in `src/document_store.py` | TRD-10 §14 | Schema for ingested document records, metadata, and chunk structures |
| 3 | doc_registry.json Schema | Defined per TRD-10 §14.3 | TRD-10 §14.3 | Registry schema for document tracking and versioning in the document store |
| 4 | IPC Message Schema | Defined in `src/xpc.py` | TRD-1 §6 | Line-delimited JSON message format for cross-process communication |

### 12.1 Schema Notes

- Schemas are defined inline within their governing Python modules rather than as standalone JSON Schema files, unless a TRD specifies otherwise.
- All schema validation must reject unknown fields and fail closed on malformed input.
- Schema definitions must match their governing TRD specifications exactly.

---

## 13. Generated Artifacts

These are files and directories produced by the system at runtime. They are **not source-controlled** (or are auto-generated and should not be manually edited).

| # | Artifact | Typical Location | Governing TRD | Purpose |
|---|----------|------------------|---------------|---------|
| 1 | Build rules | `forge-standards/build_rules.md` | TRD-8 | Auto-generated self-improving build rules. **Never cleared automatically.** |
| 2 | FAISS indices | `~/.crafted/cache/` | TRD-10 | Vector store indices for document retrieval. Safe to delete; rebuilt on demand. |
| 3 | Build ledger | `~/.crafted/ledger/` | TRD-8 | SQLite database tracking build outcomes and cross-build learning. **Never cleared automatically.** |
| 4 | Stage checkpoints | `~/.crafted/projects/` | TRD-15 | Per-PR stage completion records preventing re-running completed work after a crash. |
| 5 | Socket file | `~/.crafted/run/crafted.agent.sock` | TRD-1 §6 | Unix domain socket for Swift-Python IPC. Cleaned on graceful shutdown. |
| 6 | Log files | `~/.crafted/logs/` | TRD-16 | Rotating log files for both processes. Retained across restarts. |
| 7 | Generated docs | `crafted-docs/` | -- | Generated documentation artifacts. Regenerated from source materials. |

---

## 14. Module-to-TRD Traceability Matrix

This is the **inverse lookup** -- from TRD number to all modules and components it governs. Use this table when a TRD is amended and you need to identify all affected code.

| TRD | Title | Governed Modules and Components |
|-----|-------|---------------------------------|
| TRD-1 | macOS Application Shell | `Crafted/AppShell/` (CraftedAppShell), `Crafted/XPCBridge/` (CraftedXPCBridge), `Crafted/ProcessManager/` (CraftedProcessManager), `Crafted/BuildStream/` (CraftedBuildStream), `Crafted/Settings/` (CraftedSettings), `Crafted/DocImport/` (CraftedDocImport), `src/xpc.py`, `CraftedTests/` |
| TRD-2 | Consensus Engine | `src/workflow.py`, `src/agents.py` |
| TRD-3 | Build Pipeline | `src/models.py`, `src/consensus.py`, `src/context_manager.py` |
| TRD-4 | Multi-Agent Coordination | `src/contracts.py` |
| TRD-5 | GitHub Integration | `src/github_integration.py`, `.github/workflows/crafted-ci-macos.yml` |
| TRD-6 | Holistic Code Review | `src/review.py` |
| TRD-7 | TRD Development Workflow | `src/document_store.py` |
| TRD-8 | UI/UX Design System | `src/build_memory.py`, `src/build_rules.py`, `forge-standards/build_rules.md` |
| TRD-9 | Mac CI Runner | `.github/workflows/crafted-ci.yml`, `.github/workflows/crafted-ci-macos.yml`, `CraftedTests/`, `tests/` |
| TRD-10 | Document Store | `src/figma.py`, `src/document_store.py` (schemas §14) |
| TRD-11 | Security & Auth | `Crafted/AuthKit/` (CraftedAuthKit), `Crafted/KeychainKit/` (CraftedKeychainKit) |
| TRD-12 | Error Handling | Cross-cutting -- applies to all modules; no single module exclusively governed |
| TRD-13 | Testing Strategy | Cross-cutting -- governs `tests/`, `CraftedTests/`, and test practices across all modules |
| TRD-14 | Deployment | Cross-cutting -- governs release workflows, code signing, and distribution |
| TRD-15 | Runtime Config | `src/config.py`, `src/runtime.py`, `src/agent.py` |
| TRD-16 | Observability | Cross-cutting -- governs logging, metrics, and diagnostics across all modules |

### 14.1 Traceability Notes

- **Cross-cutting TRDs** (TRD-12, TRD-13, TRD-14, TRD-16) apply to all modules and do not have exclusive module ownership. When these TRDs are amended, all modules must be reviewed for compliance.
- **TRD-10** governs both the document store module (`src/document_store.py`) for its schema definitions (§14) and the Figma module (`src/figma.py`) for design token import.
- **TRD-9** governs all test infrastructure including both Python (`tests/`) and Swift (`CraftedTests/`) test directories, plus the CI workflow files.
- **TRD-1** has the broadest scope among non-cross-cutting TRDs, governing the majority of Swift targets plus the Python-side XPC module
