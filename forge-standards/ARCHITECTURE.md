

# Architecture — Forge Platform

## System Overview

Forge is a native macOS AI coding agent that builds software autonomously from technical specifications. The operator provides a repository, a set of Technical Requirements Documents (TRDs), and a plain-language intent. Forge decomposes that intent into an ordered plan, generates implementation and tests using a two-model consensus engine (Claude + GPT-4o with Claude as arbiter), runs a multi-pass review cycle, executes CI, and opens draft pull requests for human review. The operator gates every merge. The agent proceeds to the next unit of work while the operator reads the last one.

**Process Architecture:** Two cooperating processes.

| Process | Language | Owns | Communicates via |
|---------|----------|------|------------------|
| **Shell** (macOS Application Shell) | Swift 5.9+ / SwiftUI | UI, authentication, biometric gate, Keychain secrets, XPC bridge, auto-update, installation lifecycle | Authenticated Unix domain socket (line-delimited JSON) |
| **Backend** (Python Engine) | Python 3.12 (bundled) | Consensus engine, provider adapters, pipeline orchestration, document store, code review, GitHub operations, CI integration | Same Unix domain socket (inbound from Shell) |

Neither process ever executes generated code. All generated artifacts are committed to branches and validated through CI. The Shell process spawns the Python backend and owns its lifecycle. The Python backend never touches the Keychain, never renders UI, and never authenticates the user.

**Specification Authority:** 12 TRDs in `forge-docs/` are the single source of truth. Every interface, error contract, state machine, security control, and performance requirement is documented there. Code must match TRDs. TRD-11 governs all security-relevant decisions across every subsystem.

---

## Subsystem Map

### 1. macOS Application Shell (TRD-1)

**What it does:** Packages the entire product as a signed `.app` bundle (Developer ID). Manages drag-to-Applications installation, Sparkle-based auto-update, biometric authentication (Touch ID / Apple Watch), Keychain-based secret storage, session lifecycle, and the Swift module architecture. Owns the SwiftUI view hierarchy, the application state machine, and the XPC bridge that connects to the Python backend. Spawns, monitors, and terminates the Python process.

**What it enforces:**
- Biometric gate must complete before any backend communication occurs. Gate re-challenges on foreground return after timeout.
- All credentials (API keys, GitHub tokens) are stored exclusively in the macOS Keychain, never in files, environment variables, or user defaults.
- The Unix domain socket is authenticated: the Shell writes a per-session HMAC token into the socket handshake; the Python process must echo it back.
- Concurrency model is Swift structured concurrency (`async`/`await`, actors). No Combine, no Grand Central Dispatch queues for business logic.
- Minimum deployment target: macOS 13.0 (Ventura).

### 2. Consensus Engine (TRD-2)

**What it does:** The intelligence core. Takes a generation request (prompt + context), fans it out to two LLM providers (Claude as primary, GPT-4o as secondary) in parallel via provider adapters, collects both responses, and runs a Claude-arbitrated consensus pass that selects, merges, or rejects the outputs. Returns a single canonical result with provenance metadata (which provider contributed what, confidence score, arbitration rationale).

**What it enforces:**
- Every generation passes through consensus. There is no single-model fast path in production.
- Claude is always the arbiter. GPT-4o never arbitrates.
- Context injection from the Document Store (`auto_context()`) is called per generation request — the engine never generates without retrieving relevant specification context.
- Provider adapter failures are isolated: if one provider fails, the engine degrades to single-provider mode with a degradation flag on the result. It does not silently pretend consensus occurred.
- Token budgets and rate limits are enforced per provider adapter, not globally.

### 3. Pipeline Engine (TRD-3)

**What it does:** Orchestrates the end-to-end build pipeline: intent decomposition → PRD plan → PR sequence → per-PR generation → 3-pass review → CI execution → draft PR. Manages stage transitions, checkpointing, retry logic, and operator gates. Each stage produces a `StageResult` that determines whether the pipeline advances, retries, or stops.

**What it enforces:**
- Pipeline stages execute in strict sequence. No stage may be skipped.
- Operator gates are blocking: the pipeline halts and waits for explicit human approval (`"yes"` / `"approve"`) or rejection (`"no"` / `"stop"`). The agent never auto-answers a gate.
- Checkpointing occurs after every stage completion. On crash recovery: if mid-PR, retry from scratch; if between PRs, start the next PR; if between PRDs, start the next PRD.
- Document filter (`doc_filter`) is applied at Stage 1 and Stage 5 to scope which specifications are relevant to the current unit of work.
- Stage 1 (decomposition) and Stage 5 (review) both pull context from the Document Store (TRD-10).

### 4. XPC Bridge / IPC Protocol (TRD-1 §XPC, TRD-4)

**What it does:** Provides the bidirectional communication channel between the Swift shell and the Python backend. Implemented as an authenticated Unix domain socket using line-delimited JSON messages. Each message has a type discriminator, a correlation ID, and a payload. The Swift side is implemented in `ForgeAgent/XPCBridge.swift`; the Python side connects as a client after the Shell spawns it and passes the socket path and session token.

**What it enforces:**
- Every message must include a valid session HMAC token. Messages without valid tokens are dropped and logged.
- Message schema is strictly typed on both sides. Unknown message types are rejected, not ignored.
- Progress messages flow from Python → Swift for UI updates (stage transitions, generation progress, CI status).
- Credential delivery flows from Swift → Python: API keys are sent over the socket on demand, never written to disk or environment variables.
- Deadlock in the credential delivery path is treated as a fatal error (TRD-11 concern).

### 5. GitHub Operations (TRD-5)

**What it does:** Manages all interactions with GitHub: repository cloning, branch creation, commit authoring, push, pull request creation (draft mode), PR status polling, and merge-after-approval. Handles OAuth token lifecycle and repository permissions validation.

**What it enforces:**
- One PR per logical unit of work. The agent never creates monolithic PRs spanning multiple concerns.
- All PRs are opened as drafts. The operator must explicitly promote and merge.
- Commit messages follow a structured format: `"forge-agent[{engineer_id}]: {message}"` for PR-scoped commits, and `"forge-agent: {message}"` for bootstrap operations.
- Branch naming is deterministic and collision-resistant: `{product_slug}-{YYYY-MM-DD}` prefix.
- GitHub tokens are received from the Shell over the XPC bridge, never read from disk.

### 6. Code Review Engine (TRD-6)

**What it does:** Runs a 3-pass automated review cycle on every generated PR before it reaches the operator. Pass 1: structural lint and formatting. Pass 2: semantic review against the relevant TRD specification (context from TRD-10). Pass 3: security-focused review against TRD-11 controls. Each pass produces findings with severity, location, and suggested fixes. Critical findings block PR creation.

**What it enforces:**
- All three review passes must complete before a PR is opened. No pass may be skipped.
- Review context is injected from the Document Store (TRD-10) — the reviewer always has the specification available.
- Security review (Pass 3) is mandatory and cannot be disabled by configuration.
- Findings are attached to the PR as structured metadata, not just inline comments.

### 7. PRD Planner / Intent Decomposition (TRD-7)

**What it does:** Takes the operator's plain-language intent and the loaded TRDs, decomposes the intent into an ordered sequence of PRDs (Product Requirement Documents), then decomposes each PRD into an ordered sequence of PRs. Manages the planning conversation with the operator, including scope adjustment, file/directory exclusions, and TRD boundary management (add, remove, merge, split, transfer ownership).

**What it enforces:**
- `PRODUCT_CONTEXT` is auto-loaded from the Document Store at planning start.
- The operator can adjust scope at any point during planning: `"adjust scope"`, `"exclude files"`, `"select lenses"`.
- TRD boundary operations are explicit and operator-confirmed: `"add a TRD for X"`, `"merge TRD-2 and TRD-3"`, `"split TRD-3 into auth and RBAC"`, `"move X from TRD-2 to TRD-3"`, `"remove TRD-5"`.
- Each decomposition step requires operator approval before proceeding. The planner never silently commits to a plan.
- Estimated sections are tracked per TRD: `"TRD-4 needs a section on caching" — add section to estimated_sections`.

### 8. SwiftUI Interface Layer (TRD-8)

**What it does:** Renders the operator-facing UI: project cards, pipeline progress panels, stage detail views, gate prompts, review findings display, and settings. Implemented entirely in SwiftUI with the Shell's state machine driving view transitions.

**What it enforces:**
- UI is read-only with respect to backend state: all mutations flow through the Shell's state machine and XPC bridge. Views never directly call Python.
- Gate prompts are modal and blocking. The UI does not allow the operator to navigate away from an active gate without responding.
- Progress updates arrive via XPC messages and are rendered reactively.
- The UI never displays raw LLM output without the consensus provenance metadata.

### 9. Security Model (TRD-11)

**What it does:** Cross-cutting security specification that governs all subsystems. Defines threat model, trust boundaries, credential lifecycle, input sanitization, output validation, injection detection, and CI security controls.

**What it enforces:**
- **Credentials:** Keychain-only storage. No files, no environment variables, no hardcoded secrets. Delivery over authenticated XPC socket only.
- **Generated code:** Never executed by the agent. All generated artifacts go to branches and are validated through CI in isolated environments.
- **Injection detection:** All external content (TRDs, repository files, LLM responses) is scanned for prompt injection patterns. Detected injections are flagged: `"[NOTE: this chunk triggered injection pattern detection]"`.
- **Trust boundaries:** The Shell trusts the Keychain and biometric subsystem. The Python backend trusts the Shell's authenticated socket. Neither trusts LLM output — it is always validated, never eval'd.
- **CI isolation:** CI workflows run in ephemeral environments. Generated code is sandboxed. CI credentials are scoped to the minimum required permissions.
- **Session lifecycle:** Biometric session expires on timeout, on sleep, and on app background. Re-authentication is required before the backend receives any further credentials.

### 10. Document Store and Retrieval Engine (TRD-10)

**What it does:** Ingests, indexes, and retrieves specification documents (TRDs, PRDs, README, supporting docs). Builds a vector index (FAISS) using embeddings for semantic retrieval. Provides `auto_context()` — the function called by the Consensus Engine on every generation request to inject relevant specification fragments into the LLM prompt.

**What it enforces:**
- Storage location: `~/Library/Application Support/ForgeAgent/cache/{project_id}/`.
- Embedding model changes require re-embedding all documents. The index stores the model version and invalidates on mismatch.
- FAISS indices are kept in memory once loaded (indices are small enough). No explicit unload.
- Retrieved chunks are scanned for injection patterns before inclusion in prompts (TRD-11).
- The Document Store is the single source of specification context for generation (TRD-2), review (TRD-6), planning (TRD-7), and pipeline filtering (TRD-3).

### 11. CI Integration (TRD-9 / forge-ci.yml, forge-ci-macos.yml)

**What it does:** Defines and executes continuous integration workflows for both the Python backend and the macOS Shell. Python CI (`forge-ci.yml`: `"Forge CI — Python / test"