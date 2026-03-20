# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) — rejecting any action that fails verification.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID first at every enforcement entry point; reject immediately on any CTX-ID failure with zero partial processing.
2. Check VTZ policy before execution of every agent action; never allow implicit cross-VTZ access; deny by default.
3. Emit a synchronous TrustFlow event for every action outcome (allow, restrict, block); never buffer asynchronously in the enforcement path; never silently skip emission.
4. Treat missing CTX-ID as UNTRUSTED; never infer identity from session context, UI state, or prior calls.
5. Enforce DTL labels at ingestion; labels are immutable after assignment; unlabeled data MUST be treated as CONFIDENTIAL; derived data inherits the HIGHEST classification of any source.
6. Fail closed on all trust, identity, policy, and cryptographic errors — reject the action, log the event, surface the failure to the caller; never silently continue.
7. Never execute generated or external content — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True`.
8. Validate every write path with `path_security.validate_write_path()` before any file write.
9. Never bypass `SECURITY_REFUSAL` output by rephrasing or retrying with a different provider — stop processing, gate, and log the refusal event.
10. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, or cleartext payloads. Python stores credentials in memory only — never in env vars or on disk.
11. All external input (documents, PR comments, CI output, user prompts) is untrusted; validate strictly before use; external document context goes in USER prompt, never SYSTEM prompt.
12. Gates wait indefinitely for operator input — never auto-approve, never auto-merge, never auto-resolve security-significant conflicts.
13. Unknown XPC message types MUST be discarded and logged — never raised as uncaught exceptions and never treated as valid input.

## Architecture Overview

Forge is a two-process architecture. Always. No exceptions.

### Swift Shell (macOS app)
- **Owns:** SwiftUI interface (Navigator + BuildStream + ContextPanel), Touch ID biometric gate, Keychain storage for all credentials, XPC channel, Python process lifecycle.
- **MUST NOT:** call LLM APIs, read Keychain for the backend's use, execute generated code.

### Python Backend
- **Owns:** ConsensusEngine, BuildPipeline, GitHubTool, BuildLedger, DocumentStore, HolisticReview, TRDWorkflow, CommandRouter.
- **MUST NOT:** read Keychain directly, access the UI, persist credentials to disk.

### Credential Flow (strictly enforced)
Touch ID → Swift reads Keychain → delivers via XPC `credentials` message → Python stores in memory only.

### Enforcement Order
Every agent action follows this exact sequence — no step may be skipped or reordered:
1. **CTX-ID validation** — reject if missing, expired, or fails TrustLock public-key verification.
2. **VTZ policy check** — reject if action violates zone boundary or cross-VTZ access is not explicitly authorized.
3. **DTL label check** — reject if data crosses a boundary without valid label or if label would be downgraded.
4. **Execute action** — only after steps 1–3 pass.
5. **Emit TrustFlow event** — synchronous, on the enforcement path, recording the outcome (allow, restrict, block) with CTX-ID, VTZ, DTL, timestamp, and action descriptor.

## Module Contracts

### `src/consensus.py` — ConsensusEngine
- Owns prompt construction, multi-LLM arbitration, and generation policy.
- MUST NOT execute generated code.
- MUST NOT bypass `SECURITY_REFUSAL`.
- MUST NOT place external document context in the SYSTEM prompt.

### `src/build_director.py` — BuildPipeline
- Orchestrates stage dispatch, PR sequencing, gates, CI polling, and recovery.
- MUST NOT skip operator gates.
- MUST NOT reorder trust checks.
- MUST NOT merge without explicit operator approval.

### `src/github_tools.py` — GitHubTool
- Manages PRs, comments, CI status, and remote recovery state.
- MUST NOT trust GitHub remote state over local state without divergence handling.
- MUST gate on operator resolution when local/remote state conflicts.

### `src/cal/` — Conversation Abstraction Layer
- Every CAL enforcement entry point validates CTX-ID first, then VTZ policy, then audit context, then executes, then emits TrustFlow.
- MUST NOT partially process any action before CTX-ID validation completes.

### `src/vtz/` — Virtual Trust Zone Policy Enforcement
- Binds each session to exactly one VTZ.
- Cross-boundary access MUST be explicitly authorized; implicit access is always denied.
- Application code MUST NOT bypass VTZ structural boundaries.

### `src/dtl/` — Data Trust Label Enforcement
- Assigns labels at data ingestion.
- Labels are immutable after assignment.
- MUST validate labels before any boundary crossing.
- MUST NOT mutate labels after assignment.
- MUST NOT downgrade derived data below the highest source classification.

### `src/trustflow/` — TrustFlow Audit Stream
- Emits synchronous enforcement-path events for every action outcome.
- Each event MUST include: `ctx_id`, `vtz_id`, `dtl_label`, `action`, `outcome` (allow | restrict | block), `timestamp` (ISO 8601 UTC), `reason`.
- MUST NOT buffer, batch, or defer event emission on the enforcement path.
- MUST NOT silently drop events on serialization or transport failure — fail closed and surface the error.

## Versioning Policy

Forge follows strict Semantic Versioning (SemVer 2.0.0).

### VERSION File Contract
- A single plaintext file `VERSION` at the repository root contains the current version string.
- Format: `MAJOR.MINOR.PATCH` (e.g., `1.4.2`). No prefix, no suffix, no trailing newline.
- `MAJOR` increments when any enforcement contract (CTX-ID, VTZ, DTL, TrustFlow), wire format, XPC message schema, or audit event schema changes in a backward-incompatible way.
- `MINOR` increments when new enforcement capabilities, new TrustFlow event types, new VTZ policy predicates, or new DTL label categories are added in a backward-compatible way.
- `PATCH` increments for bug fixes, documentation corrections, and internal refactors that change no contract or external behavior.
- The `VERSION` file is the single source of truth; build scripts, CI, and release tooling MUST read from it and MUST NOT maintain independent version state.
- Every tagged release commit MUST update `VERSION` atomically with the changelog entry.
- Pre-release versions (e.g., `2.0.0-rc.1`) are permitted only on non-main branches and MUST NOT be shipped to production.