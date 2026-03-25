

# AGENTS.md

Crafted Dev Agent is a native macOS AI coding agent that autonomously builds software from technical specifications by decomposing intent into ordered pull requests using a two-model consensus engine (Claude + GPT-4o), with operator gates controlling every merge.

## How to Use This File

This file is the authoritative baseline for every AI agent and human engineer working in this repository — read it completely before touching any code. For subsystem-specific detail, see `crafted-docs/` for the full TRDs and `crafted-standards/` for synthesised architecture, interface, and decision records.

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| AGENTS | MD | `crafted-docs/AGENTS.md` | Instructions for AI agents working in this repo; component-to-TRD mapping; pre-coding checklist |
| CLAUDE | MD | `crafted-docs/CLAUDE.md` | Master context file for LLM coding tools; architecture summary; TRD authority table |
| GitHub-Integration-Lessons-Learned | DOCX/MD | `crafted-docs/GitHub-Integration-Lessons-Learned.md` / `.docx` | Production-discovered GitHub API behaviours; draft PR lifecycle; GraphQL vs REST pitfalls |
| README | MD | `crafted-docs/README.md` | Product overview; build instructions; operator workflow; version baseline |
| TRD-1 macOS Application Shell | DOCX/MD | `crafted-docs/TRD-1-macOS-Application-Shell-Crafted.md` / `.docx` | Swift shell process; UI ownership; Keychain; XPC socket protocol; auth flow |
| TRD-2 Consensus Engine | DOCX/MD | `crafted-docs/TRD-2-Consensus-Engine-Crafted.md` / `.docx` | Dual-provider generation; Claude arbitration; ProviderAdapter interface; confidence scoring |
| TRD-3 Build Pipeline | DOCX/MD | `crafted-docs/TRD-3-Build-Pipeline-Crafted.md` / `.docx` | BuildDirector orchestration; PR-type routing; stage checkpoints; confidence gates |
| TRD-4 Multi-Agent Coordination | DOCX/MD | `crafted-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` / `.docx` | Agent coordination; task decomposition; ordered PRD plans; concurrency model |
| TRD-5 GitHub Integration | DOCX/MD | `crafted-docs/TRD-5-GitHub-Integration-Crafted.md` / `.docx` | GitHubTool; webhook receiver; PR creation; branch management; API contract |
| TRD-6 Holistic Code Review | DOCX/MD | `crafted-docs/TRD-6-Holistic-Code-Review-Crafted.md` / `.docx` | Self-correction pass; lint gate; iterative fix loop; review criteria |
| TRD-7 TRD Development Workflow | DOCX/MD | `crafted-docs/TRD-7-TRD-Development-Workflow-Crafted.md` / `.docx` | TRD authoring; specification lifecycle; document embedding; TRD-driven development |
| TRD-8 UI/UX Design System | DOCX/MD | `crafted-docs/TRD-8-UIUX-Design-System-Crafted.md` / `.docx` | SwiftUI views; BuildStreamView; build_card / gate_card rendering; design tokens |
| TRD-9 Mac CI Runner | DOCX/MD | `crafted-docs/TRD-9-Mac-CI-Runner-Crafted.md` / `.docx` | macOS CI runner; build validation; test execution; hardware/sandbox requirements |
| TRD-10 Document Store | DOCX/MD | `crafted-docs/TRD-10-Document-Store-Crafted.md` / `.docx` | Document ingestion; chunking; embedding; vector search; doc_status reporting |
| TRD-11 Security & Threat Model | DOCX/MD | `crafted-docs/TRD-11-Security-Threat-Model-Crafted.md` / `.docx` | Trust boundaries; credential handling; prompt injection defence; generated code policy |
| TRD-12 Backend Runtime & Startup | DOCX/MD | `crafted-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` / `.docx` | Python process lifecycle; startup sequence; dependency validation; health checks |
| TRD-13 Recovery & State Management | DOCX/MD | `crafted-docs/TRD-13-Recovery-State-Management-Crafted.md` / `.docx` | Crash recovery; per-PR stage checkpoints; idempotent restart; state persistence |
| TRD-14 Code Quality & CI Pipeline | DOCX/MD | `crafted-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` / `.docx` | Lint rules; CI gate definitions; quality thresholds; pipeline configuration |
| TRD-15 Agent Operational Runbook | DOCX/MD | `crafted-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` / `.docx` | Operational procedures; failure triage; monitoring; escalation paths |
| TRD-16 Agent Testing & Validation | DOCX/MD | `crafted-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` / `.docx` | Test strategy; unit/integration/negative-path coverage; benchmark requirements |
| TRD-17 Self-Healing Software | DOCX/MD | `crafted-docs/TRD-17-Self-Healing-Software-Crafted.md` / `.docx` | Build memory; build rules; iterative self-correction; persistent learning systems |
| forge_architecture_context | MD | `crafted-docs/forge_architecture_context.md` | Architecture invariants; XPC wire format; protocol message schemas; file naming |

## Critical Rules — Non-Negotiable

1. **Never execute generated code.** No `eval`, no `exec`, no `subprocess` of any code the agent produces — in either the Swift or Python process.
2. **Fail closed on every auth, crypto, identity, and credential error.** Reject the action, log the event, surface to caller. Never degrade silently into permissive behaviour.
3. **Never expose secrets in logs, error messages, or generated code.** API keys, tokens, credentials, and Keychain material must never appear in any output stream.
4. **All external input is untrusted.** Documents, PR comments, CI output, webhook payloads, and user-provided content must be validated strictly before use. External document context goes in the USER prompt — never the SYSTEM prompt.
5. **Gates wait indefinitely for operator input.** No auto-approve, no timeout-to-approve, no implicit acceptance — ever.
6. **Every file write must be path-validated via `path_security.validate_write_path()` before execution.** No exceptions.
7. **XPC unknown message types are discarded and logged — never raised as exceptions.** The socket protocol is line-delimited JSON, nonce-authenticated, max 16 MB per message.
8. **Per-PR stage checkpoints are mandatory.** After a crash, the pipeline resumes from the last completed stage — it never re-runs completed work.
9. **Build memory and build rules are never cleared automatically.** They are persistent learning systems that survive across sessions.
10. **SECURITY_REFUSAL output is terminal.** It is never bypassed by rephrasing, re-prompting, or retry logic. Stop, gate, log.
11. **The 16 TRDs in `forge-docs/` are the source of truth.** Code must match the TRDs. Do not invent requirements. When a TRD and code disagree, the TRD wins until formally amended.
12. **Read TRD-11 before touching any security-relevant code.** This includes credential flows, external content handling, prompt construction, and CI integration.
13. **Claude arbitrates every consensus result.** The Consensus Engine runs Claude and GPT-4o in parallel; Claude is always the final arbiter. Do not change the arbitration hierarchy.
14. **Draft PRs use GraphQL `markPullRequestReadyForReview` mutation to convert to ready.** The REST PATCH `{"draft": false}` is silently ignored by GitHub. Do not use it.
15. **No silent failure paths anywhere in the codebase.** Every error must surface with component, operation, failure reason, and context ID where available.

## Architecture Overview

Crafted Dev Agent is a **two-process architecture**: a Swift shell and a Python backend communicating over an authenticated Unix domain socket (XPC).

### Swift Shell (macOS Application — TRD-1, TRD-8)
- **What it does:** Owns the native macOS UI (SwiftUI), Keychain credential storage, authentication, and the XPC server socket.
- **What calls it:** The operator (via UI); the Python backend (via XPC messages).
- **What it calls:** macOS Keychain; the Python backend process (launches and monitors it); SwiftUI rendering.
- **Must NEVER:** Execute generated code. Store secrets outside Keychain. Process LLM prompts directly. Auto-approve any gate.

### Python Backend (TRD-12, TRD-3, TRD-2, TRD-4)
- **What it does:** Runs the Consensus Engine, Build Pipeline (BuildDirector), multi-agent coordination, code generation, self-correction, and GitHub operations.
- **What calls it:** The Swift shell (via XPC socket messages).
- **What it calls:** LLM provider APIs (Anthropic, OpenAI); GitHub REST/GraphQL APIs; Document Store; local file system (path-validated).
- **Must NEVER:** Execute generated code. Access Keychain directly. Render UI. Auto-approve gates. Clear build memory.

### Consensus Engine (TRD-2)
- **What it does:** Sends identical prompts to Claude and GPT-4o in parallel; Claude arbitrates the final result; produces confidence scores.
- **What calls it:** BuildDirector.
- **What it calls:** ProviderAdapter (Anthropic), ProviderAdapter (OpenAI).
- **Must NEVER:** Let GPT-4o override Claude's arbitration. Return results without a confidence score. Swallow provider errors silently.

### Build Pipeline / BuildDirector (TRD-3)
- **What it does:** Orchestrates the full PR lifecycle: confidence assessment → decomposition → generation → self-correction → lint gate → fix loop → PR creation. Routes by `pr_type`. Manages stage checkpoints.
- **What calls it:** Multi-agent coordinator; operator intent.
- **What it calls:** Consensus Engine; Holistic Code Review; GitHub Integration; Document Store.
- **Must NEVER:** Skip the confidence gate. Re-run completed stages after recovery. Proceed past a failed lint gate without fix attempts.

### Multi-Agent Coordination (TRD-4)
- **What it does:** Decomposes high-level intent into ordered PRD plans, then into sequences of typed PRs. Manages task ordering and dependencies.
- **What calls it:** Operator intent via the Swift shell.
- **What it calls:** BuildDirector (one invocation per PR).
- **Must NEVER:** Execute PRs out of dependency order. Proceed if a predecessor PR fails its gate.

### GitHub Integration / GitHubTool (TRD-5)
- **What it does:** Creates branches, opens draft PRs, converts drafts to ready-for-review (GraphQL only), receives webhooks, manages PR lifecycle.
- **What calls it:** BuildDirector.
- **What it calls:** GitHub REST API; GitHub GraphQL API.
- **Must NEVER:** Use REST PATCH to convert draft PRs. Merge without operator gate approval. Store GitHub tokens outside the credential flow.

### Holistic Code Review (TRD-6)
- **What it does:** Runs self-correction pass, lint gate, and iterative fix loop on generated code before PR creation.
- **What calls it:** BuildDirector.
- **What it calls:** Consensus Engine (for review generation); linting tools.
- **Must NEVER:** Mark review as passed if lint gate fails. Skip negative-path analysis.

### TRD Development Workflow (TRD-7)
- **What it does:** Manages the TRD authoring lifecycle; ensures specifications are embedded and searchable.
- **What calls it:** Document Store (for embedding); operator (for authoring).
- **What it calls:** Document Store.
- **Must NEVER:** Modify TRD content automatically without operator approval.

### UI/UX Design System (TRD-8)
- **What it does:** Defines SwiftUI components: `BuildStreamView`, `build_card`, `gate_card` rendering, design tokens, panel layouts.
- **What calls it:** Swift shell (renders cards from XPC messages).
- **What it calls:** SwiftUI framework.
- **Must NEVER:** Display raw JSON to the operator. Auto-dismiss gate cards. Render untrusted content without sanitisation.

### Mac CI Runner (TRD-9)
- **What it does:** Runs builds and tests on macOS hardware; validates generated code compiles and passes CI.
- **What calls it:** GitHub Actions (via webhook); BuildDirector (for local validation).
- **What it calls:** `xcodebuild`; `pytest`; linting tools.
- **Must NEVER:** Execute in an unsandboxed environment. Cache credentials between runs.

### Document Store (TRD-10)
- **What it does:** Ingests documents (TRDs, PRDs), chunks them, generates embeddings, provides vector search for context retrieval.
- **What calls it:** BuildDirector; Consensus Engine (for context); TRD workflow.
- **What it calls:** Embedding model APIs; local vector storage.
- **Must NEVER:** Inject retrieved document content into the SYSTEM prompt. Return results without `doc_status` tracking.

### Security & Threat Model (TRD-11)
- **What it does:** Defines trust boundaries, credential handling, prompt injection defences, and generated code policy across all components.
- **What calls it:** Referenced by every component — this is a cross-cutting concern.
- **What it calls:** N/A (policy document).
- **Must NEVER:** Be overridden by convenience. Be treated as optional.

### Backend Runtime & Startup (TRD-12)
- **What it does:** Manages Python process lifecycle: startup sequence, dependency validation, health checks, readiness signaling via XPC `ready` message.
- **What calls it:** Swift shell (launches the process).
- **What it calls:** All Python subsystems during initialisation.
- **Must NEVER:** Signal ready before all dependencies are validated. Start accepting XPC commands before health checks pass.

### Recovery & State Management (TRD-13)
- **What it does:** Persists per-PR stage checkpoints; enables idempotent restart after crashes; manages state files.
- **What calls it:** BuildDirector (writes checkpoints); startup sequence (reads checkpoints).
- **What it calls:** Local file system (path-validated).
- **Must NEVER:** Auto-clear checkpoints. Resume from a corrupted state file without validation.

### Code Quality & CI Pipeline (TRD-14)
- **What it does:** Defines lint rules, CI gate definitions, quality thresholds, and pipeline configuration.
- **What calls it:** BuildDirector (lint gate); CI runner.
- **What it calls:** Linting and static analysis tools.
- **Must NEVER:** Allow a PR to pass CI with unresolved lint errors above the configured threshold.

### Agent Operational Runbook (TRD-15)
- **What it does:** Documents operational procedures, failure triage, monitoring, and escalation paths.
- **What calls it:** Operators during incidents.
- **What it calls:** N/A (operational document).
- **Must NEVER:** Be out of sync with actual system behaviour.

### Agent Testing & Validation (TRD-16)
- **What it does:** Defines test strategy: unit, integration, negative-path coverage, benchmark requirements.
- **What calls it:** CI pipeline; developers writing tests.
- **What it calls:** `pytest`; benchmark harness.
- **Must NEVER:** Allow enforcement paths to ship with <90% test coverage. Allow tests to mock enforcement decisions.

### Self-Healing Software (TRD-17)
- **What it does:** Implements build memory and build rules — persistent learning systems that improve generation quality over time through iterative self-correction.
- **What calls it:** BuildDirector (during fix loops); Consensus Engine (for rule application).
- **What it calls:** Build memory store; build rules store.
- **Must NEVER:** Clear build memory automatically. Discard build rules without operator action.

## Interface Contracts

### XPC Wire Protocol (TRD-1)
- Format: line-delimited JSON over authenticated Unix domain socket.
- Max message size: 16 MB.
- Authentication: nonce-based handshake.
- Key message types:
  - `ready`: `{ agent_version, min_swift_version, capabilities[], doc_store_status }` — sent by Python after startup completes.
  - `credentials`: `{ anthropic_api_key, openai_api_key, github_token, engineer_id }` — sent by Swift shell after auth.
  - `build_card`: `{ card_type, stage, content, progress }` — streamed to `BuildStreamView`.
  - `gate_card`: `{ gate_type, options[], description }` — blocks pipeline until operator responds.
  - `doc_status`: `{ doc_id, doc_name, status, chunk_count, embedded_count }` — embedding progress.
- Unknown message types: discard and log. Never raise as exceptions.

### Consensus Engine Interface (TRD-2)
- Input: prompt + context + `pr_type`.
- Output: `{ generated_code, confidence_score, provider_results[], arbitration_rationale }`.
- Claude is always the arbitrator. GPT-4o provides a competing result for comparison.
- Confidence score must be present on every result. Sub-threshold confidence triggers a gate.

### BuildDirector Pipeline Stages (TRD-3)
- Stages execute in strict order: `assess` → `decompose` → `generate` → `review` → `lint` → `fix` → `pr_create`.
- Each stage writes a checkpoint on completion.
- A failed stage halts the pipeline and surfaces a `gate_card` for operator decision.
- `pr_type` determines routing logic within `generate` and `review`.

### GitHub Integration (TRD-5)
- PRs are always opened as drafts first.
- Draft → ready conversion: use **GraphQL `markPullRequestReadyForReview`** mutation only.
- Branch naming, commit messages, and PR descriptions follow the format specified in TRD-5.
- Webhook payloads are untrusted external input — validate before processing.

### Document Store (TRD-10)
- Documents are chunked and embedded at ingestion.
- `doc_status` messages track ingestion progress and are sent to the Swift shell via XPC.
- Retrieved context is placed in the USER prompt — never in the SYSTEM prompt.

## Error Handling Rules

### Fail Closed — Mandatory
- All errors involving authentication, credentials, identity, cryptography, and policy enforcement must fail closed.
- Fail closed means: **reject the action, log the event with full context, surface to the caller**. Never silently continue.

### Banned Patterns
- `try/except/pass` in any enforcement, security, or pipeline-critical code path is **banned**.
- Silent swallowing of exceptions anywhere is banned.
- Returning default/fallback values on security-relevant errors is banned.
- Logging an error and then proceeding as if it didn't happen is banned.

### Error Context Requirements
- Every error must include: **component name, operation, failure reason, and context ID** (PR ID, session ID, or equivalent) where available.
- Error messages must **never** include: keys, tokens, secrets, cleartext credentials, or sensitive payloads.

### XPC Errors
- Malformed messages: log and discard. Do not propagate.
- Unknown message types: discard and log. Never raise.
- Connection loss: the Swift shell restarts the Python backend. The backend resumes from the last stage checkpoint.

### Provider Errors (LLM APIs)
- Timeout or rate limit: retry with backoff per TRD-2 contract.
- Authentication failure: fail closed, surface to