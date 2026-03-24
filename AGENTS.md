# AGENTS.md

Crafted is a native macOS AI coding agent that builds software autonomously from technical specifications, using a two-process architecture (Swift shell + Python backend) with a two-model consensus engine to decompose intent into ordered pull requests that are gated, reviewed, and merged by a human operator.

## How to Use This File

This file is the authoritative baseline for every AI agent and human engineer working in this repository — read it completely before modifying any file. For subsystem-specific detail, see `forge-docs/` for the 16 source TRDs and `forge-standards/` for synthesised architecture and decision records.

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| AGENTS | MD | `forge-docs/AGENTS.md` | Agent operating instructions, TRD lookup rules, pre-coding checklist |
| CLAUDE | MD | `forge-docs/CLAUDE.md` | Baseline context file for LLM agents working in this repo |
| README | MD | `forge-docs/README.md` | Product overview, build/run instructions, TRD index |
| TRD-1: macOS Application Shell | DOCX/MD | `forge-docs/TRD-1-macOS-Application-Shell-Crafted.md` / `.docx` | Swift shell, .app bundle, Keychain, auth, XPC, module architecture, Sparkle updates |
| TRD-2: Consensus Engine | DOCX/MD | `forge-docs/TRD-2-Consensus-Engine-Crafted.md` / `.docx` | Two-model generation (Claude + GPT-4o), arbitration, provider adapters |
| TRD-3: Build Pipeline | DOCX/MD | `forge-docs/TRD-3-Build-Pipeline-Crafted.md` / `.docx` | BuildDirector, PR-type routing, confidence gate, stage orchestration |
| TRD-4: Multi-Agent Coordination | DOCX/MD | `forge-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` / `.docx` | Agent coordination, PRD decomposition, ordered PR sequencing |
| TRD-5: GitHub Integration | DOCX/MD | `forge-docs/TRD-5-GitHub-Integration-Crafted.md` / `.docx` | GitHubTool, webhooks, PR lifecycle, branch management |
| TRD-6: Holistic Code Review | DOCX/MD | `forge-docs/TRD-6-Holistic-Code-Review-Crafted.md` / `.docx` | Self-correction pass, lint gate, iterative fix loop, review automation |
| TRD-7: TRD Development Workflow | DOCX/MD | `forge-docs/TRD-7-TRD-Development-Workflow-Crafted.md` / `.docx` | How TRDs are authored, versioned, and used as build specifications |
| TRD-8: UI/UX Design System | DOCX/MD | `forge-docs/TRD-8-UIUX-Design-System-Crafted.md` / `.docx` | SwiftUI views, BuildStreamView, build cards, gate cards, panels |
| TRD-9: Mac CI Runner | DOCX/MD | `forge-docs/TRD-9-Mac-CI-Runner-Crafted.md` / `.docx` | Local CI execution, test running, CI result parsing |
| TRD-10: Document Store | DOCX/MD | `forge-docs/TRD-10-Document-Store-Crafted.md` / `.docx` | TRD ingestion, embedding, chunk retrieval, doc status tracking |
| TRD-11: Security & Threat Model | DOCX/MD | `forge-docs/TRD-11-Security-Threat-Model-Crafted.md` / `.docx` | Trust boundaries, credential handling, generated code safety, injection prevention |
| TRD-12: Backend Runtime & Startup | DOCX/MD | `forge-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` / `.docx` | Python process lifecycle, bundled runtime, startup sequence, health checks |
| TRD-13: Recovery & State Management | DOCX/MD | `forge-docs/TRD-13-Recovery-State-Management-Crafted.md` / `.docx` | Crash recovery, per-PR stage checkpoints, state persistence |
| TRD-14: Code Quality & CI Pipeline | DOCX/MD | `forge-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` / `.docx` | Lint, format, quality gates, CI pipeline configuration |
| TRD-15: Agent Operational Runbook | DOCX/MD | `forge-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` / `.docx` | Operational procedures, diagnostics, failure response |
| TRD-16: Agent Testing & Validation | DOCX/MD | `forge-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` / `.docx` | Test strategy, validation criteria, coverage requirements |
| TRD-17: Self-Healing Software | DOCX/MD | `forge-docs/TRD-17-Self-Healing-Software-Crafted.md` / `.docx` | Build memory, build rules, persistent learning, self-correction |
| Forge Architecture Context | MD | `forge-docs/forge_architecture_context.md` | XPC wire format, protocol references, file naming, system invariants |

## Critical Rules — Non-Negotiable

1. **Find and read the owning TRD before modifying any component.** The 16 TRDs in `forge-docs/` are the source of truth. Do not invent requirements.
2. **Read TRD-11 before touching any code that handles credentials, external content, generated code, or CI output.** No exceptions.
3. **Never execute generated code.** No `eval`, no `exec`, no `subprocess` of agent-generated content — in either the Swift shell or Python backend.
4. **All external input is untrusted.** Documents, PR comments, CI output, webhook payloads — validate strictly before use.
5. **Fail closed on all auth, crypto, identity, and policy errors.** Reject the action, log the event, surface to caller. Never degrade silently into insecure behavior.
6. **No silent failure paths.** Every error must surface with component, operation, failure reason, and context ID where available.
7. **Secrets never appear in logs, error messages, or generated code.** Credentials live in Keychain (Swift side) and are passed to the backend only via the authenticated XPC channel.
8. **Gates wait indefinitely for operator input.** No auto-approve, no timeout-to-approve. The human gates every merge decision.
9. **Context from external documents goes in the USER prompt — never the SYSTEM prompt.** Prevents injection from attacker-controlled content.
10. **SECURITY_REFUSAL output is never bypassed by rephrasing.** Stop, gate, log.
11. **All file writes must be path-validated via `path_security.validate_write_path()` before execution.** No file I/O without path validation.
12. **XPC unknown message types are discarded and logged — never raised as exceptions.** The XPC wire format is line-delimited JSON, nonce-authenticated, max 16 MB per message.
13. **Per-PR stage checkpoints prevent re-running completed work after a crash.** Recovery resumes from the last completed stage, not from scratch.
14. **Build memory and build rules are never cleared automatically.** They are persistent learning systems (TRD-17).
15. **Run existing tests before making changes.** `cd src && pytest ../tests/ -v --tb=short`. All tests must pass before and after your change.

## Architecture Overview

Crafted is a two-process macOS application. The Swift shell and Python backend communicate over an authenticated Unix socket using line-delimited JSON (XPC protocol).

### Swift Shell (TRD-1, TRD-8)
- **What it does:** Owns the .app bundle, SwiftUI UI, biometric authentication, Keychain secret storage, session lifecycle, XPC server, and Sparkle auto-update.
- **What calls it:** The user (via UI) and the Python backend (via XPC responses).
- **What it calls:** The Python backend (via XPC commands), macOS Keychain, Sparkle framework.
- **Must NEVER:** Execute generated code, store secrets outside Keychain, send credentials in logs or error messages, auto-approve gates.

### Python Backend — Consensus Engine (TRD-2)
- **What it does:** Runs two LLM providers (Claude as primary/arbitrator, GPT-4o as secondary) in parallel, arbitrates results, produces final generation output.
- **What calls it:** BuildDirector (TRD-3).
- **What it calls:** Anthropic API, OpenAI API.
- **Must NEVER:** Execute generated code, cache API keys on disk, fall back to a single model without surfacing the degradation.

### Python Backend — Build Pipeline / BuildDirector (TRD-3)
- **What it does:** Orchestrates the full PR lifecycle: confidence assessment, PRD decomposition, PR-type routing, stage sequencing (generate → self-correct → lint → fix loop → CI → PR).
- **What calls it:** XPC command from Swift shell (user intent).
- **What it calls:** ConsensusEngine, GitHubTool, CI Runner, Document Store, Code Review.
- **Must NEVER:** Skip confidence gate, merge without operator approval, proceed past a failed gate without explicit operator override.

### Python Backend — Multi-Agent Coordination (TRD-4)
- **What it does:** Decomposes high-level intent into an ordered PRD plan, sequences PRs with dependency tracking, manages parallel agent coordination.
- **What calls it:** BuildDirector.
- **What it calls:** ConsensusEngine, Document Store.
- **Must NEVER:** Reorder PRs in violation of dependency constraints, execute PRs concurrently when they have sequential dependencies.

### Python Backend — GitHub Integration (TRD-5)
- **What it does:** Creates branches, commits files, opens draft PRs, receives webhook events, manages PR lifecycle.
- **What calls it:** BuildDirector.
- **What it calls:** GitHub REST/GraphQL API.
- **Must NEVER:** Push to protected branches directly, use hardcoded tokens, merge PRs without operator gate.

### Python Backend — Holistic Code Review (TRD-6)
- **What it does:** Runs self-correction pass, lint gate, iterative fix loop on generated code before PR creation.
- **What calls it:** BuildDirector (post-generation stage).
- **What it calls:** ConsensusEngine (for correction), linters, CI Runner.
- **Must NEVER:** Approve its own output without the lint/review gate, suppress lint errors.

### Python Backend — TRD Development Workflow (TRD-7)
- **What it does:** Manages how TRDs are authored, versioned, loaded, and used as build specifications.
- **What calls it:** Document Store, BuildDirector (for spec resolution).
- **What it calls:** File system, Document Store.
- **Must NEVER:** Modify TRDs during a build — TRDs are read-only inputs to the pipeline.

### Swift Shell — UI/UX Design System (TRD-8)
- **What it does:** Renders BuildStreamView, build cards, gate cards, side panels, and all operator-facing UI.
- **What calls it:** Swift shell (receives build_card and gate_card XPC messages).
- **What it calls:** SwiftUI framework.
- **Must NEVER:** Auto-dismiss gate cards, hide error states, render unsanitized external content.

### Python Backend — Mac CI Runner (TRD-9)
- **What it does:** Executes CI locally (tests, builds), parses CI output, returns structured results.
- **What calls it:** BuildDirector (CI stage), Code Review (fix loop).
- **What it calls:** Local shell (sandboxed), test frameworks.
- **Must NEVER:** Execute generated code directly — only executes pre-existing test/build commands against committed code.

### Python Backend — Document Store (TRD-10)
- **What it does:** Ingests TRDs, chunks them, generates embeddings, provides retrieval for context injection.
- **What calls it:** BuildDirector, ConsensusEngine (for context), Multi-Agent Coordination.
- **What it calls:** Embedding provider APIs, local vector store.
- **Must NEVER:** Inject document content into the SYSTEM prompt, return unvalidated chunks.

### Python Backend — Backend Runtime & Startup (TRD-12)
- **What it does:** Manages Python process lifecycle, bundled runtime, startup sequence, health checks, XPC client connection.
- **What calls it:** Swift shell (process launch).
- **What it calls:** All Python subsystems during initialization.
- **Must NEVER:** Start processing before XPC authentication completes, expose the Unix socket externally.

### Python Backend — Recovery & State Management (TRD-13)
- **What it does:** Persists per-PR stage checkpoints, enables crash recovery from last completed stage.
- **What calls it:** BuildDirector (at each stage boundary).
- **What it calls:** Local file system (checkpoint storage).
- **Must NEVER:** Clear checkpoints automatically, resume from a corrupted checkpoint without validation.

### Python Backend — Self-Healing Software (TRD-17)
- **What it does:** Maintains build memory and build rules as persistent learning systems, enables self-correction across sessions.
- **What calls it:** BuildDirector (post-build), Code Review.
- **What it calls:** Local persistence, ConsensusEngine.
- **Must NEVER:** Auto-clear build memory or build rules, apply learned rules without traceability.

### Cross-Cutting: Security & Threat Model (TRD-11)
- Governs all components. Defines trust boundaries, credential handling, injection prevention, generated code safety.

### Cross-Cutting: Code Quality & CI Pipeline (TRD-14)
- Defines lint, format, quality gates, and CI pipeline configuration for the Crafted codebase itself.

### Cross-Cutting: Agent Operational Runbook (TRD-15)
- Operational procedures, diagnostics, failure response for production operation.

### Cross-Cutting: Agent Testing & Validation (TRD-16)
- Test strategy, validation criteria, coverage requirements for the agent.

## Interface Contracts

### XPC Wire Protocol Contract
- Wire format: line-delimited JSON over authenticated Unix socket.
- Every message is nonce-authenticated. Max 16 MB per message.
- `ready` message: `{ agent_version, min_swift_version, capabilities[], doc_store_status }`.
- `build_card`: `{ card_type, stage, content, progress }` — streamed to BuildStreamView.
- `gate_card`: `{ gate_type, options[], description }` — blocks until operator responds.
- `credentials`: `{ anthropic_api_key, openai_api_key, github_token, engineer_id }` — sent once per session from Swift shell.
- `doc_status`: `{ doc_id, doc_name, status, chunk_count, embedded_count }`.
- Unknown message types MUST be discarded and logged — never raised as exceptions.

### CAL Enforcement Contract
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection — no partial processing.
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a VTZEnforcementDecision record with verdict=block.
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

### Audit Contract
- Every security-relevant action MUST generate an audit record BEFORE execution.
- Audit records are APPEND-ONLY — no modification or deletion.
- Audit failures are NON-FATAL to agent operation but MUST be surfaced immediately.
- Audit records MUST NOT contain: secrets, keys, tokens, or cleartext sensitive data.
- Replay MUST be possible from the audit stream alone (no external state required).

## Error Handling Rules

### Fail-Closed Requirement
- All trust, identity, policy, and cryptographic failures MUST fail CLOSED.
- Fail closed means: reject the action, log the event, surface to caller — never silently continue.

### Banned Patterns
- `try/except/pass` is **BANNED** in any enforcement, security, auth, crypto, or policy code path.
- No swallowed exceptions in enforcement paths.
- No `except Exception` without specific handling and logging.
- No fallback to insecure defaults on crypto or auth failure.
- No auto-approve on gate timeout.

### Error Message Requirements
- All errors MUST include: component name, operation, failure reason, `ctx_id` (if available).
- Error messages MUST NOT include: keys, tokens, secrets, or cleartext payloads.

### Specific Failure Behaviors
| Failure Type | Required Behavior |
|---|---|
| XPC authentication failure | Reject connection, log, do not retry automatically |
| Credential missing/invalid | Surface to operator via gate card, block pipeline |
| LLM provider timeout/error | Retry with backoff per TRD-2, surface after max retries |
| CI execution failure | Log full output, surface to operator, block PR creation |
| Checkpoint corruption | Reject resume, require operator decision |
| Unknown XPC message type | Discard silently, log at DEBUG level |
| Path validation failure | Reject file write, log path attempted, surface error |
| SECURITY_REFUSAL from LLM | Stop pipeline, gate, log — never rephrase and retry |

## Testing Requirements

### Coverage Rules
- Enforcement paths MUST have ≥ 90% test coverage.
- Every security boundary MUST have at least one negative-path test (what happens on rejection).
- Every cryptographic operation MUST have a test with invalid/expired material.

### Mandatory Test Types
- **Unit tests:** All security-critical logic, all parsing, all policy evaluation.
- **Integration tests:** XPC round-trip, GitHub API interaction (mocked), CI execution flow.
- **Negative-path tests:** Malformed input, expired credentials, corrupted state, injection attempts.
- **Regression tests:** Add a regression test for every material bug fix.
- **Benchmark tests:** Performance-sensitive paths (consensus generation, document retrieval, XPC throughput).

### Test Integrity Rules
- Tests