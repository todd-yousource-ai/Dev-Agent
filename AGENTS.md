# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels all data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) for every outcome.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — validation failure means immediate rejection, no partial processing, no fallback. Missing CTX-ID MUST be treated as `UNTRUSTED`; never infer identity from session state, UI state, or context.
2. TrustFlow events MUST be emitted synchronously in the enforcement path for every action outcome (allow, restrict, block) — each event MUST include `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, and `payload_hash`. Async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
3. VTZ policy MUST be checked BEFORE execution of any agent action — VTZ boundaries are structural, not advisory, and cannot be bypassed by application code. Exactly one VTZ per session; implicit cross-VTZ tool calls are denied.
4. DTL labels are assigned at data ingestion and are immutable — derived data inherits the HIGHEST classification of any source; unlabeled data is `CONFIDENTIAL` until explicitly reclassified. DTL labels MUST be verified before any trust-boundary crossing.
5. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to caller — `try/except/pass` is BANNED in enforcement code.
6. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, or XPC payloads beyond the initial `credentials` delivery — Python stores credentials in memory only.
7. All external input (documents, PR comments, CI output, LLM responses) is untrusted — validate strictly before use; context from external documents goes in the USER prompt, never the SYSTEM prompt.
8. Generated code is NEVER executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True`.
9. Gates wait indefinitely for operator input — no auto-approve, no auto-merge, no auto-resume past a human gate ever; `SECURITY_REFUSAL` output is never bypassed by rephrasing, retrying another model, or continuing the workflow — stop, gate, log.
10. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions.
11. CTX-ID tokens are IMMUTABLE once issued — rotation creates a new token and immediately invalidates the old one; expired CTX-ID MUST be rejected.
12. Audit records are APPEND-ONLY — no modification or deletion; every security-relevant action generates an audit record BEFORE execution; replay MUST be possible from the audit stream alone.
13. Keep the Swift shell and Python backend separated: Swift owns UI, Touch ID, Keychain, and XPC; Python owns generation, pipeline, GitHub, ledger, and document processing. Never mix these responsibilities.
14. Discard and log unknown XPC message types — never raise them as unhandled exceptions across the protocol boundary.

## Architecture Overview

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; action processing pipeline: validate CTX-ID → check VTZ → execute → emit TrustFlow | Process any action before CTX-ID validation succeeds; bypass identity or policy checks |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Policy boundaries per agent session; exactly one VTZ per session; cross-VTZ authorization requires explicit policy grant | Allow implicit cross-VTZ tool calls; apply policy changes mid-session; allow application code to override VTZ boundaries |
| **TrustFlow** | `src/trustflow/` | Synchronous audit/event emission for every action outcome (allow, restrict, block); each record includes `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash` | Silently buffer, skip, or downgrade failed emissions; allow async-only emission; permit modification or deletion of emitted records |
| **DTL** (Data Trust Labels) | `src/dtl/` | Label assignment at ingestion; highest-classification inheritance on derivation; label verification before trust-boundary crossing | Relabel or strip labels without policy control and audit; allow unlabeled data to cross trust boundaries as anything other than `CONFIDENTIAL` |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity; CTX-ID validation against TrustLock public key; immutable issued tokens; immediate invalidation on rotation | Accept software-only validation when hardware attestation is available; accept expired or revoked CTX-ID tokens |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Policy evaluation and authorization decisions; explainable, reproducible control decisions | Mutate identity state or issue CTX-ID tokens; make authorization decisions without full policy context |

## Enforcement Path (CAL Pipeline)

Every agent action follows this exact sequence:

1. **CTX-ID Validation** — Authenticate caller identity. Reject immediately on failure.
2. **VTZ Policy Check** — Evaluate action against session VTZ boundaries. Reject if outside policy.
3. **DTL Label Verification** — Verify data labels are present and classification permits the action.
4. **Execution** — Perform the agent action.
5. **TrustFlow Emission** — Emit synchronous audit event with outcome. Failed emission is WARN-level audit event.

No step may be skipped. No step may execute out of order. Failure at any step halts the pipeline and emits a TrustFlow event recording the failure.

## XPC Protocol (Swift ↔ Python)

- Swift shell sends XPC messages to Python backend for all generation, pipeline, and document processing.
- Python backend sends XPC messages to Swift shell for UI updates, credential requests, and gate prompts.
- Unknown XPC message types MUST be discarded and logged — never raised as unhandled exceptions.
- Credentials are delivered via XPC `credentials` message type only and MUST NOT appear in any subsequent XPC payload.

## File Write Security

Every file write operation MUST:
1. Call `path_security.validate_write_path(target_path)` before any I/O.
2. Reject writes outside approved directories.
3. Emit a TrustFlow event recording the write attempt and outcome.

## Secrets Management

- Credentials are stored in macOS Keychain (Swift shell) and passed to Python backend via XPC `credentials` message.
- Python backend holds credentials in memory only — never written to disk, logs, error messages, or generated output.
- Credential rotation invalidates all in-memory copies immediately.

## Data Classification Hierarchy

`PUBLIC` < `INTERNAL` < `CONFIDENTIAL` < `RESTRICTED`

- Unlabeled data defaults to `CONFIDENTIAL`.
- Derived data inherits the HIGHEST classification of all source data.
- Reclassification requires explicit policy authorization and emits a TrustFlow audit event.