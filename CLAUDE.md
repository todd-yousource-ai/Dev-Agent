# CLAUDE.md

Crafted is a native macOS AI coding agent that autonomously builds software from technical specifications, using a two-process architecture (Swift shell + Python backend) with a two-model consensus engine, opening GitHub pull requests gated by human review.

## How to Use This File

This file is the authoritative baseline for every AI agent and human engineer working in this repository — read it completely before touching any code. For subsystem-specific detail, see `forge-docs/` for the full TRDs and `forge-standards/` for synthesised architecture and decision records.

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| AGENTS | MD | `forge-docs/AGENTS.md` | Instructions for AI agents: repo identity, pre-coding checklist, TRD lookup rules |
| CLAUDE | MD | `forge-docs/CLAUDE.md` | Baseline coding context: architecture summary, TRD authority table, error contracts |
| README | MD | `forge-docs/README.md` | Product overview, intent→PR workflow, TRD index, build/test/run instructions |
| TRD-1 macOS Application Shell | DOCX/MD | `forge-docs/TRD-1-macOS-Application-Shell-Crafted.md` / `.docx` | Swift shell: .app bundle, Keychain, biometric auth, XPC socket, session lifecycle, Sparkle updates |
| TRD-2 Consensus Engine | DOCX/MD | `forge-docs/TRD-2-Consensus-Engine-Crafted.md` / `.docx` | ConsensusEngine, ProviderAdapter, dual-model (Claude + GPT-4o) generation, arbitration logic |
| TRD-3 Build Pipeline | DOCX/MD | `forge-docs/TRD-3-Build-Pipeline-Crafted.md` / `.docx` | BuildPipeline orchestration, confidence gate, PR-type routing, stage sequencing |
| TRD-4 Multi-Agent Coordination | DOCX/MD | `forge-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` / `.docx` | PRD decomposition, ordered PR plan, multi-agent task assignment, concurrency model |
| TRD-5 GitHub Integration | DOCX/MD | `forge-docs/TRD-5-GitHub-Integration-Crafted.md` / `.docx` | GitHubTool, WebhookReceiver, PR creation, branch management, token handling |
| TRD-6 Holistic Code Review | DOCX/MD | `forge-docs/TRD-6-Holistic-Code-Review-Crafted.md` / `.docx` | Self-correction pass, lint gate, iterative fix loop, review criteria |
| TRD-7 TRD Development Workflow | DOCX/MD | `forge-docs/TRD-7-TRD-Development-Workflow-Crafted.md` / `.docx` | Spec-driven development, TRD authoring process, version control of specifications |
| TRD-8 UI/UX Design System | DOCX/MD | `forge-docs/TRD-8-UIUX-Design-System-Crafted.md` / `.docx` | SwiftUI views, BuildStreamView, build_card/gate_card rendering, panel layout |
| TRD-9 Mac CI Runner | DOCX/MD | `forge-docs/TRD-9-Mac-CI-Runner-Crafted.md` / `.docx` | Local CI execution, test runner, build validation, sandbox constraints |
| TRD-10 Document Store | DOCX/MD | `forge-docs/TRD-10-Document-Store-Crafted.md` / `.docx` | TRD ingestion, chunking, embedding, doc_status reporting, retrieval |
| TRD-11 Security & Threat Model | DOCX/MD | `forge-docs/TRD-11-Security-Threat-Model-Crafted.md` / `.docx` | Trust boundaries, credential handling, input validation, SECURITY_REFUSAL, threat mitigations |
| TRD-12 Backend Runtime & Startup | DOCX/MD | `forge-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` / `.docx` | Python process lifecycle, bundled Python 3.12, startup sequence, health checks |
| TRD-13 Recovery & State Management | DOCX/MD | `forge-docs/TRD-13-Recovery-State-Management-Crafted.md` / `.docx` | Crash recovery, per-PR stage checkpoints, state persistence, resume logic |
| TRD-14 Code Quality & CI Pipeline | DOCX/MD | `forge-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` / `.docx` | Linting, formatting, CI gates, quality thresholds |
| TRD-15 Agent Operational Runbook | DOCX/MD | `forge-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` / `.docx` | Operational procedures, diagnostics, failure triage, monitoring |
| TRD-16 Agent Testing & Validation | DOCX/MD | `forge-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` / `.docx` | Test strategy, unit/integration/negative-path tests, benchmark requirements |
| Forge Architecture Context | MD | `forge-docs/forge_architecture_context.md` | XPC wire format, protocol messages, build_card/gate_card schemas, file naming, key invariants |

## Critical Rules — Non-Negotiable

1. Find and read the TRD that owns the component you are modifying before writing any code — the 16 TRDs in `forge-docs/` are the source of truth, not the code.
2. Read TRD-11 before any change that touches credentials, external content, generated code, or CI — it governs the entire security model.
3. Never execute generated code — no `eval`, no `exec`, no subprocess invocation of agent-produced content, in either process.
4. Fail closed on every auth, crypto, identity, and policy error — never degrade silently into an insecure or partially-processed state.
5. Never log, surface in error messages, or embed in generated code any secret, token, key, or credential.
6. Treat all external input (documents, PR comments, CI output, webhook payloads) as untrusted — validate strictly before use.
7. Place external document context in the USER prompt only — never inject it into the SYSTEM prompt.
8. Gate cards wait indefinitely for operator input — never auto-approve any gate, under any condition.
9. Validate every file write path via `path_security.validate_write_path()` before execution — no exceptions.
10. When the agent emits a `SECURITY_REFUSAL` output, stop processing — do not rephrase, retry, or bypass.
11. Discard and log unknown XPC message types — never raise them as exceptions or pass them to handlers.
12. Per-PR stage checkpoints are mandatory — completed stages must not re-run after a crash or restart.
13. Build memory and build rules are persistent learning systems — never clear them automatically.
14. All XPC messages must conform to the wire format: line-delimited JSON, nonce-authenticated, max 16 MB per message.
15. Every material code path must be traceable to a TRD requirement, design decision, security need, or bug fix — no orphan code.

## Architecture Overview

Crafted is a two-process native macOS application. The **Swift shell** and **Python backend** communicate over an authenticated Unix domain socket using line-delimited JSON (XPC protocol).

### Swift Shell (TRD-1, TRD-8)
- **What it does:** Owns the .app bundle, macOS lifecycle, SwiftUI UI, biometric authentication, Keychain secret storage, session management, Sparkle auto-update, and XPC socket server.
- **Called by:** macOS (launch), user interaction (UI events).
- **Calls:** Python backend (via XPC socket), Keychain Services, Sparkle framework.
- **Must NEVER:** Execute generated code, store secrets outside Keychain, send credentials in plaintext outside the XPC socket, auto-approve gates.

### Python Backend — Consensus Engine (TRD-2)
- **What it does:** Runs dual-model generation (Claude as primary/arbiter, GPT-4o as secondary), merges and arbitrates outputs, produces final code artifacts.
- **Called by:** Build Pipeline (via internal API).
- **Calls:** Claude API, OpenAI API (GPT-4o).
- **Must NEVER:** Execute generated code, bypass arbitration, return un-arbitrated output as final.

### Python Backend — Build Pipeline (TRD-3)
- **What it does:** Orchestrates the full PR lifecycle: confidence assessment → PRD decomposition → PR sequencing → generation → self-correction → lint → fix loop → CI → draft PR.
- **Called by:** XPC command from Swift shell.
- **Calls:** Consensus Engine, Holistic Code Review, GitHub Integration, Document Store, CI Runner.
- **Must NEVER:** Skip confidence gate, proceed past a gate without operator approval, re-run a checkpointed stage.

### Python Backend — Multi-Agent Coordination (TRD-4)
- **What it does:** Decomposes intents into ordered PRD plans, assigns tasks to agent workers, manages concurrency and dependency ordering.
- **Called by:** Build Pipeline.
- **Calls:** Consensus Engine, Build Pipeline (per-PR).
- **Must NEVER:** Execute tasks out of dependency order, silently drop a failed task.

### Python Backend — GitHub Integration (TRD-5)
- **What it does:** Creates branches, commits files, opens draft PRs, receives webhooks, manages GitHub token lifecycle.
- **Called by:** Build Pipeline.
- **Calls:** GitHub REST/GraphQL APIs.
- **Must NEVER:** Store tokens outside the credential flow from the Swift shell, commit secrets to repositories.

### Python Backend — Holistic Code Review (TRD-6)
- **What it does:** Self-correction pass, lint gate, iterative fix loop — validates generated code against TRD requirements and quality thresholds.
- **Called by:** Build Pipeline.
- **Calls:** Consensus Engine (for fix generation), linters, CI Runner.
- **Must NEVER:** Auto-pass a failing lint gate, suppress review findings.

### Python Backend — TRD Development Workflow (TRD-7)
- **What it does:** Manages the lifecycle of TRD documents — authoring, versioning, validation against implementation.
- **Called by:** Operator (via intent), Build Pipeline.
- **Calls:** Document Store.
- **Must NEVER:** Modify a TRD without version increment, treat code as authoritative over a TRD.

### Python Backend — Document Store (TRD-10)
- **What it does:** Ingests TRDs and specifications, chunks them, generates embeddings, provides retrieval for the Consensus Engine.
- **Called by:** Build Pipeline, Consensus Engine, XPC (doc_status reporting).
- **Calls:** Embedding APIs, local vector store.
- **Must NEVER:** Inject retrieved document content into the SYSTEM prompt, return unchunked raw documents as context.

### Mac CI Runner (TRD-9)
- **What it does:** Executes tests and builds locally in a sandboxed environment, reports results back to the Build Pipeline.
- **Called by:** Build Pipeline, Holistic Code Review.
- **Calls:** Xcode toolchain, pytest, local build tools.
- **Must NEVER:** Execute generated code outside the sandbox, grant network access to test subjects beyond what policy allows.

### Recovery & State Management (TRD-13)
- **What it does:** Persists per-PR stage checkpoints, enables crash recovery and session resume without re-running completed work.
- **Called by:** Build Pipeline (at every stage boundary).
- **Calls:** Local persistence layer.
- **Must NEVER:** Auto-clear checkpoints, resume into a stage that already completed successfully.

### XPC Protocol (TRD-1, forge_architecture_context)
- **What it does:** Authenticated Unix domain socket carrying line-delimited JSON messages between Swift shell and Python backend.
- **Message types:** `ready`, `credentials`, `build_card`, `gate_card`, `doc_status`, commands.
- **Must NEVER:** Accept messages > 16 MB, process unknown message types (discard + log), transmit credentials without nonce authentication.

## Interface Contracts

Every component MUST implement these contracts. They are hard requirements enforced at code review.

### CAL Enforcement Contract
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection — no partial processing.
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a VTZEnforcementDecision record with `verdict=block`.
- Every action outcome (allow, restrict, block) MUST emit a TrustFlow event.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

### TrustFlow Emission Contract
- Every TrustFlow event MUST include: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash`.
- `event_id` MUST be globally unique (CSPRNG, not sequential).
- `ts` MUST be UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path — async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.

### CTX-ID Contract
- CTX-ID tokens are IMMUTABLE once issued — no field modification after issuance.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected — clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against TrustLock public key — software-only validation is rejected.
- Missing CTX-ID MUST be treated as UNTRUSTED — never infer identity from context.

### VTZ Enforcement Contract
- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization — implicit is denied.
- VTZ boundaries are structural, not advisory — enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

### DTL Label Contract
- Labels are assigned at DATA INGESTION and are immutable thereafter.
- Label inheritance: derived data inherits the HIGHEST classification of any source.
- Unlabeled data MUST be treated as CONFIDENTIAL until explicitly reclassified.
- Label verification MUST occur before any data crosses a trust boundary.
- Label stripping is a security event that MUST be audited and policy-controlled.

### XPC Wire Protocol Contract
- Format: line-delimited JSON, nonce-authenticated, max 16 MB per message.
- `ready` message: `{ agent_version, min_swift_version, capabilities[], doc_store_status }`.
- `build_card`: `{ card_type, stage, content, progress }` — streamed to BuildStreamView.
- `gate_card`: `{ gate_type, options[], description }` — blocks until operator responds.
- `credentials`: `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`.
- `doc_status`: `{ doc_id, doc_name, status, chunk_count, embedded_count }`.
- Unknown message types: discard and log — never raise as exceptions.

### Audit Contract
- Every security-relevant action MUST generate an audit record BEFORE execution.
- Audit records are APPEND-ONLY — no modification or deletion.
- Audit failures are NON-FATAL to agent operation but MUST be surfaced immediately.
- Audit records MUST NOT contain: secrets, keys, tokens, or cleartext sensitive data.
- Replay MUST be possible from the audit stream alone (no external state required).

## Error Handling Rules

### Fail-Closed Requirement
- All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to caller.
- No silent continuation after a security-relevant error.

### Banned Patterns
- `try/except/pass` (or equivalent swallowed exceptions) is **BANNED** in any enforcement, trust, crypto, or policy code path.
- `eval()`, `exec()`, `subprocess` on generated content is **BANNED** everywhere.
- Auto-approve on timeout is **BANNED** — gates wait forever.
- Inferring identity from context when CTX-ID is missing is **BANNED**.

### Error Content Requirements
- All errors MUST include: `component`, `operation`, `failure_reason`, `ctx_id` (if available).
- Error messages MUST NOT include: keys, tokens, secrets, or cleartext payloads.

### XPC Error Handling
- Unknown message types: discard and log at WARN level — do not raise exceptions.
- Messages exceeding 16 MB: reject and log — do not attempt to parse.
- Nonce validation failure: reject the message, log as a security event, do not process.

### Recovery Behavior
- On crash or restart, resume from the last completed per-PR stage checkpoint.
- Never re-run a stage that completed successfully.
- Build memory and build rules persist across restarts — never auto-clear.

## Testing Requirements

### Coverage Rules
- Test coverage for all enforcement paths MUST be ≥ 90%.
- Every security boundary MUST have at least one negative-path test (what happens on rejection).
- Every cryptographic operation MUST have a test with invalid/expired material.

### Mandatory Test Categories
- **Unit tests:** All security-critical logic, all parsing, all policy evaluation.
- **Integration tests:** XPC round-trips, Build Pipeline stage transitions, GitHub API interactions.
- **Negative-path tests:** Malformed XPC messages, expired credentials, invalid tokens, oversized payloads, unknown message types.
- **Regression tests:** Add a regression test for every material bug fix.
- **Benchmark tests:** Consensus Engine response time, XPC message throughput, document embedding latency.
- **Fuzz tests:** Use fuzzing where inputs are complex, attacker-controlled, or parser-driven (XPC messages, document ingestion, webhook payloads).

### Test Integrity Rules
- Tests MUST NOT mock the enforcement decision — they may mock the external call, but the enforcement logic must execute.
- Tests MUST verify that `SECURITY_REFUSAL` outputs are terminal — no retry, no rephrase.
- Tests MUST verify that gate cards block indefinitely without operator input.

### Running Tests
```bash
cd src && pytest ../tests/ -v --tb=short
```

## File Naming and Directory Layout

### Swift Shell (TRD-1, TRD-8)
```
Crafted/
├── CraftedApp.swift              — App entry point, lifecycle
├── Models/                       — Data models, XPC message types
├── Views/                        — SwiftUI views (BuildStreamView, gate cards, panels)
├── Services/                     — Keychain, auth, session management
├── XPC/                          — XPC socket server, message parsing, nonce auth
└── Updates/                      — Sparkle auto-update integration
```

### Python Backend
```
src/
├── consensus.py                  — ConsensusEngine, GENERATION_SYSTEM, SWIFT_GENERATION_SYSTEM+UI_ADDENDUM
├── build_director.py             — BuildPipeline orchestration, confidence gate, PR-type routing
├── github_tools.py               — GitHubTool, WebhookReceiver
├── build_ledger.py               — Build memory, persistent build rules
├── path_security.py              — validate_write_path() and path enforcement
├── xpc_server.py                 — Unix socket server, message dispatch
├── doc_store.py                  — Document ingestion, chunking, embedding, retrieval
├── review.py                     — Holistic code review, self-correction, lint gate
├── ci_runner.py                  — Local CI execution, sandbox management
├── recovery.py                   — Checkpoint persistence, crash recovery, resume logic
└── ...
```

### Forge Subsystem Paths (Standards Layer)
```
src/cal/           — Conversation Abstraction Layer components