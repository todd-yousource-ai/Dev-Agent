# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data with immutable Data Trust Labels (DTL), and emits a tamper-evident TrustFlow audit stream — failing closed on any violation.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — before any parsing, any business logic, any I/O; validation failure is immediate rejection with zero partial processing. Missing CTX-ID means UNTRUSTED — never infer identity from session state, request context, or prior actions.
2. TrustFlow events MUST be emitted synchronously in the enforcement path for every action outcome (allow, restrict, block) — async buffering is forbidden, failed emission is a WARN-level audit event that MUST be surfaced, never silently skipped. Every TrustFlow event MUST include: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash`.
3. VTZ policy MUST be evaluated before execution of any agent action — VTZ boundaries are structural and cannot be bypassed by application code; cross-VTZ tool calls require explicit policy authorization or they are denied. Every agent session MUST be bound to exactly one VTZ at CTX-ID issuance; implicit cross-VTZ execution is denied.
4. DTL labels are assigned at data ingestion and are immutable — derived data inherits the HIGHEST classification of any source; unlabeled data is treated as CONFIDENTIAL; label stripping is a security event that MUST be audited. Labels MUST be verified before any trust-boundary crossing.
5. All trust, identity, policy, cryptographic, and label-verification failures MUST fail closed: reject the action, log the event, surface to caller — `try/except/pass` is BANNED in any enforcement code path.
6. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, audit records, or TrustFlow event payloads — error messages include `component`, `operation`, `failure_reason`, and `ctx_id` only.
7. Generated code is NEVER executed by the agent — no `eval()`, no `exec()`, no `shell=True`, no `subprocess` of generated content, no exceptions.
8. All external input (documents, PR comments, CI output, XPC messages) is untrusted — validate strictly before use; external document context goes in the USER prompt, never the SYSTEM prompt. Unknown XPC message types MUST be discarded with logging.
9. Gates wait indefinitely for operator input — no auto-approve, no timeout fallback, no implicit consent.
10. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions, no bypass.
11. CTX-ID tokens are IMMUTABLE once issued — rotation creates a new token and immediately invalidates the old one; expired CTX-ID is rejected; missing CTX-ID means UNTRUSTED, never infer identity from context.
12. SECURITY_REFUSAL output is terminal — never retry with a different provider, never rephrase, never bypass; stop, gate, log. No code may auto-approve, rephrase-around, or retry past a security refusal.

## Architecture Overview

Forge is a two-process architecture: a native macOS Swift frontend (UI, Keychain, XPC host) and a Python 3.12 backend (all LLM interaction, enforcement logic, GitHub operations). The Swift process NEVER calls LLM APIs directly. The Python process NEVER reads from Keychain directly. Credentials cross the boundary exactly once via authenticated XPC.

### Subsystem Map (enforcement order)

- `src/cal/` — Conversation Abstraction Layer enforcement entry points. MUST validate CTX-ID first, invoke VTZ before action execution, emit TrustFlow for outcomes. MUST NOT perform implicit identity inference or bypass enforcement order.
- `src/vtz/` — Virtual Trust Zone policy enforcement. MUST decide allow/restrict/block before protected actions. MUST NOT allow implicit cross-VTZ execution or mid-session policy mutation.
- `src/trustflow/` — Synchronous audit/event emission for enforcement outcomes. Every event MUST include `event_id` (string), `session_id` (string), `ctx_id` (string), `ts` (ISO-8601 UTC), `event_type` (enum: allow|restrict|block), `payload_hash` (SHA-256 hex). MUST NOT async-buffer enforcement-path events.
- `src/dtl/` — Data Trust Label assignment and verification. MUST assign labels at ingestion, verify labels before trust-boundary crossing. MUST NOT permit unlabeled data to be treated below CONFIDENTIAL.
- `src/trustlock/` — Cryptographic machine identity and TrustLock-backed CTX-ID validation. MUST validate against the TrustLock public key. MUST NOT accept software-only validation when hardware attestation is available.
- `src/mcp/` — MCP Policy Enforcement gateway. MUST enforce VTZ policy on all MCP tool invocations. MUST NOT allow unauthenticated or cross-VTZ MCP calls.
- `src/github/` — GitHub integration (PR, Issues, CI). All GitHub API calls MUST carry a valid CTX-ID and emit TrustFlow events. MUST NOT trust CI output or PR comments without strict validation.
- `src/path_security/` — Write-path validation. Exposes `validate_write_path()`. Every file write in the platform MUST call this before I/O. MUST NOT allow path traversal, symlink escape, or writes outside approved directories.

### Cross-Process Isolation Boundary

| Boundary Rule | Swift Frontend | Python Backend |
|---|---|---|
| LLM API calls | NEVER | ALL |
| Keychain reads | ALL | NEVER |
| Credential transfer | Sends via authenticated XPC | Receives via authenticated XPC |
| XPC message validation | Validates outbound schema | Validates inbound schema; discards unknown types with logging |
| Trust enforcement | Delegates to Python | Owns all enforcement logic |

Credentials cross the XPC boundary exactly once per session. The Python process MUST reject any XPC message that fails schema validation. The Swift process MUST NOT embed credentials in XPC message fields beyond the designated credential payload.

### Cross-TRD Precedence Rules

When Technical Reference Documents (TRDs) conflict, the following precedence order applies (highest priority first):

1. **CTX-ID / TrustLock (identity)** — Identity validation is always first; no other subsystem may act on an unvalidated identity.
2. **VTZ (policy)** — Policy evaluation is second; no action proceeds without a policy decision.
3. **DTL (data classification)** — Data labels constrain what policy-approved actions may access; higher classification always wins.
4. **TrustFlow (audit)** — Audit emission is mandatory for every decision but never overrides identity, policy, or classification decisions.
5. **CAL / MCP / GitHub (application)** — Application-layer subsystems are subordinate to all enforcement subsystems above.

If a TRD at a lower precedence level defines behavior that contradicts a higher-precedence TRD, the higher-precedence TRD wins unconditionally. Implementers MUST NOT resolve ambiguity by choosing the less restrictive interpretation.

### ADR Template

All Architecture Decision Records for Forge MUST use this template:

markdown
# ADR-NNNN: [Title]

## Status
[PROPOSED | ACCEPTED | DEPRECATED | SUPERSEDED by ADR-XXXX]

## Date
YYYY-MM-DD

## Context
[What is the issue? Which TRDs, subsystems, or enforcement boundaries are affected?]

## Decision
[What is the change that we are making? State imperatively.]

## Enforcement Impact
- CTX-ID: [affected | not affected]
- VTZ: [affected | not affected]
- DTL: [affected | not affected]
- TrustFlow: [affected | not affected]
- Cross-process boundary: [affected | not affected]

## TRD Precedence
[If this ADR touches multiple TRDs, state which TRD takes precedence per the cross-TRD precedence rules and why.]

## Consequences
[What becomes easier or harder? What enforcement invariants are preserved or newly introduced?]

## Compliance
- [ ] Fails closed on all error paths
- [ ] No secrets in logs or error messages
- [ ] TrustFlow events emitted for all outcomes
- [ ] CTX-ID validated before any processing
- [ ] VTZ policy evaluated before execution
- [ ] DTL labels propagated correctly
