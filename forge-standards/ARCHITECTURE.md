

# Architecture — Forge Platform

## System Overview

Forge is a native macOS AI coding agent that autonomously builds software from technical specifications. It operates as a **two-process architecture**: a **Swift/SwiftUI application shell** and a **Python backend engine**, communicating over an authenticated Unix domain socket using line-delimited JSON. The system ingests Technical Requirements Documents (TRDs), decomposes operator intent into ordered plans, generates implementation via a two-model consensus engine (Claude + GPT-4o), executes multi-pass review, runs CI validation, and opens GitHub pull requests for human review and merge.

The platform enforces a strict security invariant: **neither process ever executes generated code**. All trust boundaries are explicit. All control decisions are observable and reproducible. Policy is enforced, not suggested.

### Process Model

```
┌─────────────────────────────┐       Unix Socket (JSON-RPC)       ┌──────────────────────────────┐
│     Swift Application Shell │ ◄──────────────────────────────► │       Python Backend          │
│                             │       Authenticated + Nonce        │                              │
│  • UI (SwiftUI)             │                                    │  • Consensus Engine (TRD-2)  │
│  • Auth / Biometric Gate    │                                    │  • Pipeline Orchestration     │
│  • Keychain Secret Storage  │                                    │  • Document Store (TRD-10)   │
│  • Session Lifecycle        │                                    │  • GitHub Operations          │
│  • XPC Bridge (Swift side)  │                                    │  • XPC Server (Python side)  │
│  • Sparkle Auto-Update      │                                    │  • Review Engine (TRD-6)     │
│  • Menu Bar / Dock / Notif. │                                    │  • CI Orchestration (TRD-9)  │
└─────────────────────────────┘                                    └──────────────────────────────┘
```

**Minimum target:** macOS 13.0 (Ventura). Swift 5.9+, Python 3.12 (bundled inside .app).

---

## Subsystem Map

### 1. macOS Application Shell (TRD-1)

**What it does:** Native Swift/SwiftUI container that packages, installs, authenticates, and orchestrates all subsystems. Owns the .app bundle structure, drag-to-Applications installation, Sparkle auto-update, biometric authentication gate, Keychain-based secret storage, session lifecycle management, Swift module boundaries, concurrency model, and state ownership. Defines the SwiftUI view hierarchy root and menu bar / dock / notification integration.

**What it enforces:**
- Biometric authentication is the sole entry gate; no session begins without it.
- All secrets (API keys, tokens, engineer ID) are stored exclusively in Keychain via `SecretKey` enum — never in UserDefaults, files, or environment variables.
- Session tokens have explicit limits (OI-13 session limit blocks generation when exceeded).
- The Swift process never interprets, compiles, or executes any content received from the Python backend.
- Python 3.12 is bundled — the shell never relies on system Python or user PATH.

### 2. Consensus Engine (TRD-2)

**What it does:** Orchestrates dual-LLM generation using Claude and GPT-4o in parallel via provider adapters. For every generation task, both models produce output independently; Claude serves as the arbiter that reconciles and selects the final result. Implements `ConsensusEngine` and `ProviderAdapter` interfaces. Consumes context from the Document Store (TRD-10) via `auto_context()` on every generation call.

**What it enforces:**
- Every generated artifact is the product of two independent model outputs and an explicit arbitration step — no single-model output is ever shipped without consensus.
- Provider failures are isolated: if one provider fails, the system does NOT retry with the other provider. The failure is surfaced explicitly.
- All LLM responses are treated as untrusted external content (TRD-11).
- Token budgets and context windows are tracked and enforced per request.

### 3. Pipeline Orchestration (TRD-3)

**What it does:** Decomposes operator intent into an ordered PRD plan, decomposes each PRD into a sequence of pull requests, and manages the stage-gate execution of the full build pipeline. Stages include intent parsing, plan decomposition, PR sequencing, generation, review, CI, and PR opening. Implements `doc_filter` integration at Stages 1 and 5.

**What it enforces:**
- Each PR represents one logical unit of work — no multi-concern PRs.
- Stage transitions are gated: no stage advances without the prior stage's success criteria being met.
- Operator intent is the sole input; the pipeline does not invent requirements beyond what the TRDs and intent specify.
- The pipeline halts and surfaces errors rather than proceeding with partial or ambiguous state.

### 4. XPC Bridge / IPC Protocol (TRD-1, TRD-4)

**What it does:** Implements the authenticated Unix domain socket communication channel between the Swift shell and the Python backend. Uses line-delimited JSON messages. The Swift side (`XPCBridge.swift`) manages connection lifecycle, credential delivery, and progress message routing. The Python side (`xpc_server.py`) authenticates via a one-time nonce and processes commands.

**What it enforces:**
- Connection authentication via nonce — the Python process must present the correct nonce issued at launch or the connection is rejected.
- Credential delivery flows exclusively from Swift → Python over the authenticated socket; credentials never exist in environment variables, command-line arguments, or files.
- Message schema is strictly validated on both sides; malformed messages are dropped with error responses.
- Deadlock detection: if credential delivery does not complete within defined timeout, the session is terminated.

### 5. GitHub Integration (TRD-5)

**What it does:** Manages all GitHub API operations: repository access, branch creation, file read/write (content + SHA tracking), pull request creation (draft PRs), and conflict detection. Authenticates using tokens delivered from the Swift shell via XPC. Implements content-hash-based change detection.

**What it enforces:**
- Every file write includes the current SHA to prevent silent overwrites (optimistic concurrency via GitHub API).
- Conflict detection is explicit (TRD-5 §10): before committing, the system fetches current file state and compares content hashes.
- GitHub tokens are never persisted by the Python process; they are held in memory for the session duration only.
- All GitHub-sourced content (file contents, PR descriptions, comments) is treated as untrusted external input.

### 6. Review Engine (TRD-6)

**What it does:** Executes a 3-pass review cycle on every generated PR before it is opened. Review passes validate correctness, consistency with TRDs, test coverage, and security properties. Consumes context from the Document Store. Supports operator review gate with interactive commands (`/review start`, `/review exclude`).

**What it enforces:**
- No PR is opened without completing all three review passes.
- Review context is injected from the Document Store, ensuring reviews are grounded in the project's specifications.
- Operator has explicit gate authority: the system halts and waits for operator approval before finalizing.
- Review findings are scored: `+2` for each failing assertion identifier found in the fix, `+1` for each failed test name mentioned.
- Security lens review is mandatory and cannot be excluded except by explicit operator command with directory/file scope.

### 7. Product Context and Intent Engine (TRD-7)

**What it does:** Manages the `PRODUCT_CONTEXT` auto-load mechanism that provides every LLM call with the project's identity, constraints, and architectural rules. Loads TRDs, README, and project-specific configuration into a structured context payload.

**What it enforces:**
- Every LLM generation call includes product context — there is no "bare" generation without project grounding.
- Context is read-only during generation; no LLM output can modify the product context.
- TRD authority is preserved: when LLM output contradicts a TRD, the TRD wins.

### 8. SwiftUI View Layer (TRD-8)

**What it does:** Implements the complete SwiftUI view hierarchy: cards, panels, progress indicators, operator REPL interface, project selection, and status displays. Consumes state from the Shell's state model and XPC progress messages.

**What it enforces:**
- Views are pure projections of state — no business logic in view code.
- All state mutations flow through the defined state ownership model (TRD-1).
- Progress messages from the Python backend are displayed in real time via XPC bridge routing.
- UI never blocks on backend operations; all backend communication is async.

### 9. CI Orchestration (TRD-9)

**What it does:** Manages continuous integration execution for generated code. Triggers CI runs, monitors status, and gates PR opening on CI success. Implements two CI workflows: Python test suite (`crafted-ci.yml`) and macOS build + unit test + XPC integration test (`crafted-ci-macos.yml`).

**What it enforces:**
- No PR is opened if CI fails — CI is a hard gate, not advisory.
- CI runs in isolated environments; generated code is never executed in the agent's own process.
- Python bundling in CI uses the same bundled Python version as the .app to prevent environment drift.
- CI triggers on pushes to main and on PR paths matching defined file globs (`src/**`, `tests/**`, `Crafted/**`, etc.).

### 10. Document Store and Retrieval Engine (TRD-10)

**What it does:** Ingests, indexes, and retrieves project documents (TRDs, specs, code files) for context injection into LLM calls and review passes. Uses FAISS for vector indexing with embeddings. Stores indices in `~/Library/Application Support/Crafted/cache/{project_id}/`. Implements content-hash-based change detection for incremental re-indexing.

**What it enforces:**
- BLOCKING priority: must be operational before any Python backend generation begins.
- `auto_context()` is called on every generation request (TRD-2 integration) — no generation proceeds without document retrieval.
- Content hashes determine re-embedding: only changed documents are re-indexed.
- Embedding model changes require full re-embedding of all documents (explicitly documented constraint).
- Index size is bounded: 10 projects ≈ 3MB total. Indices remain loaded in memory (no explicit unload).
- All ingested document content is validated against prompt injection patterns before indexing.

### 11. Security Model (TRD-11)

**What it does:** Defines and enforces the security architecture across all components. Governs credential handling, external content treatment, generated code sandboxing, prompt injection defense, adversarial LLM output mitigation, transport security, code signing, and CI security.

**What it enforces:**
- **Credential isolation:** All secrets in Keychain. Credentials delivered via authenticated XPC only. Never in env vars, CLI args, logs, or files.
- **Generated code is never executed** by any Forge process — the fundamental security invariant.
- **Prompt injection defense (§10):** All external content (GitHub file contents, LLM responses, user documents) is treated as untrusted. Injection pattern detection is applied to document chunks before indexing.
- **Adversarial LLM output (§10):** LLM output is validated against expected schema before use. No LLM output is interpreted as a command.
- **Code signing:** Application is signed with Developer ID (`Developer ID Application: YouSource.ai ({TEAM_ID})`). Notarized for distribution.
- **Transport:** All external API calls use TLS. Local IPC uses authenticated Unix socket (not network-exposed).
- **Certificate hygiene:** Expiry checking via scheduled job (`check_cert_expiry.sh`, cron: `0 9 1 * *`).

### 12. Operator REPL and Ledger (TRD-7, TRD-8)

**What it does:** Provides the interactive operator interface for issuing commands, adjusting scope, excluding files, selecting review lenses, and annotating the build ledger. Supports commands like `/ledger note <text>`, `/review start`, `/review exclude`, `adjust scope`, `exclude files`, `select lenses`.

**What it enforces:**
- Operator commands are the sole mechanism for runtime scope adjustment — the system never auto-adjusts scope without operator input.
- Ledger