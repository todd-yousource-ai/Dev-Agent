# CLAUDE.md - Forge Platform

Forge is a security-first, policy-enforcing platform that binds every agent action to a cryptographically verified identity (CTX-ID), enforces Virtual Trust Zone (VTZ) boundaries, labels data at ingestion with Data Trust Labels (DTL), and emits synchronous TrustFlow audit events for every security-relevant action — with all failures failing closed.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID **first** at every enforcement entry point and reject immediately on failure with no partial processing.
2. Check VTZ policy **before** executing any action and never allow implicit cross-VTZ access; cross-VTZ tool calls require explicit policy authorization.
3. Emit a TrustFlow event synchronously in the enforcement path for every action outcome (`allow`, `restrict`, `block`) and never silently skip emission failures; failed emission is a WARN-level audit event, never a silent skip.
4. Treat missing CTX-ID as `UNTRUSTED` and never infer identity from session context, transport state, or caller location; expired CTX-ID MUST be rejected.
5. Fail closed on all trust, identity, policy, and cryptographic errors and never degrade into permissive behavior.
6. Treat unlabeled data as `CONFIDENTIAL` and verify DTL labels before any trust-boundary crossing; derived data MUST inherit the highest classification of any source.
7. Never modify a CTX-ID after issuance; rotation MUST mint a new token and invalidate the old token immediately.
8. Validate every file write with `path_security.validate_write_path()` before execution and reject invalid paths.
9. Never execute generated code; no `eval`, no `exec`, and no subprocess execution of generated content.
10. Never place secrets, keys, tokens, credentials, or cleartext sensitive payloads in logs, errors, audit records, or generated code.
11. Discard and log unknown XPC message types and never raise them as uncaught exceptions.
12. Gates MUST wait indefinitely for operator input and MUST never auto-approve, bypass, or infer approval; `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log.
13. All external input (documents, PR comments, CI output, XPC messages) is **untrusted** — validate strictly before use; context from external documents goes in the USER prompt, never the SYSTEM prompt.
14. Audit records are **append-only** (no modification or deletion), MUST be generated **before** execution, and MUST NOT contain secrets, keys, tokens, or cleartext sensitive data.
15. DTL labels are assigned at data ingestion and are **immutable**; post-ingestion relabeling MUST NOT occur without an explicit audited policy flow.

## Enforcement Pipeline Order

Every agent action MUST pass through this sequence in order:

**CTX-ID validation → VTZ policy check → DTL label verification → action execution → TrustFlow emission → audit record**

No step may be skipped. Failure at any step MUST halt the pipeline and fail closed.

## Architecture Overview

| Subsystem | Path | Enforces | MUST NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Calls CTX-ID validation first on every agent action entry point; orchestrates the enforcement pipeline | Never process an action without CTX-ID validation; never skip VTZ check |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Binds each session to exactly one VTZ; enforces zone boundaries on every tool call | Never permit implicit cross-VTZ tool calls; never allow zone escalation without policy authorization |
| **DTL** (Data Trust Labels) | `src/dtl/` | Assigns immutable labels at data ingestion; verifies labels before trust-boundary crossings | Never permit mutable post-ingestion relabeling without explicit audited policy flow; never treat unlabeled data as anything other than CONFIDENTIAL |
| **TrustFlow** | `src/trustflow/` | Synchronous emission of audit events for every action outcome (allow, restrict, block) in the enforcement path | Never async-buffer events; never silently drop or skip emission |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity and CTX-ID validation using TrustLock public key material; verifies hardware-anchored identity | Never allow software-only validation; never accept expired or tampered CTX-ID |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Evaluates policy decisions before action execution; returns enforceable allow/restrict/block verdicts | Never produce advisory-only results where enforcement is required; never permit action before policy evaluation completes |
| **Rewind** | `src/rewind/` | Replay engine for audit reconstruction from append-only audit data | Never require hidden external state to reconstruct security-relevant flows; never modify audit records during replay |
| **Forge Connector SDK** | `sdk/connector/` | Preserves Forge security contracts at integration boundaries; propagates CTX-ID, VTZ, and DTL through external connectors | Never strip or downgrade security context during cross-system calls; never allow unauthenticated connector sessions |

## AuthKit Session State Machine

AuthKit manages session lifecycle through the following state machine:

### States

| State | Description |
|---|---|
| `UNINITIALIZED` | No session exists; CTX-ID has not been presented |
| `VALIDATING` | CTX-ID presented and undergoing cryptographic verification via TrustLock |
| `ACTIVE` | CTX-ID validated; session is bound to a VTZ; actions may proceed through the enforcement pipeline |
| `EXPIRED` | Session timeout has elapsed; all actions MUST be rejected; re-authentication is required |
| `REVOKED` | CTX-ID has been explicitly invalidated (rotation or administrative action); all actions MUST be rejected |
| `FAILED` | Validation failed (invalid signature, unknown key, tampered token); session MUST NOT be created; fail closed |

### Transitions

| From | To | Trigger | Action |
|---|---|---|---|
| `UNINITIALIZED` | `VALIDATING` | CTX-ID presented at enforcement entry point | Begin TrustLock cryptographic verification |
| `VALIDATING` | `ACTIVE` | TrustLock verification succeeds and VTZ binding completes | Emit TrustFlow `session.activated` event; start timeout clock |
| `VALIDATING` | `FAILED` | TrustLock verification fails (invalid signature, expired token, unknown key) | Emit TrustFlow `session.failed` event; reject action; fail closed |
| `ACTIVE` | `EXPIRED` | Session timeout elapses with no valid activity | Emit TrustFlow `session.expired` event; reject all subsequent actions |
| `ACTIVE` | `REVOKED` | CTX-ID rotation or administrative revocation | Emit TrustFlow `session.revoked` event; invalidate immediately; reject all subsequent actions |
| `ACTIVE` | `ACTIVE` | Valid action processed within timeout window | Reset timeout clock; emit TrustFlow action event |
| `EXPIRED` | `VALIDATING` | New CTX-ID presented for re-authentication | Begin fresh TrustLock verification; old session context MUST NOT carry over |
| `FAILED` | `UNINITIALIZED` | Caller retries with new CTX-ID | Previous failure context MUST NOT influence new validation |
| `REVOKED` | `UNINITIALIZED` | New CTX-ID presented after rotation | Old token MUST remain permanently invalid |

### Timeout Contracts

- `session.idle_timeout_ms`: Maximum milliseconds of inactivity before an `ACTIVE` session transitions to `EXPIRED`. MUST be configured per-VTZ policy. MUST NOT be zero or negative. MUST NOT be silently extended.
- `session.absolute_timeout_ms`: Maximum milliseconds from session activation to mandatory expiration regardless of activity. MUST be configured per-VTZ policy. MUST be greater than or equal to `idle_timeout_ms`. When reached, session transitions to `EXPIRED` unconditionally.
- `session.validation_timeout_ms`: Maximum milliseconds allowed for TrustLock cryptographic verification in the `VALIDATING` state. If exceeded, session transitions to `FAILED` — never to `ACTIVE`.
- All timeout values MUST be positive integers. Missing timeout configuration MUST cause session creation to fail closed — never default to permissive values.
- Timeout expiration MUST emit a TrustFlow event **before** rejecting the action.
- Expired or revoked sessions MUST NOT be reactivated — a new session MUST be created through full re-authentication.

### Invariants

- A session MUST NOT reach `ACTIVE` without successful TrustLock CTX-ID verification.
- A session MUST be bound to exactly one VTZ upon entering `ACTIVE`; VTZ binding MUST NOT change for the lifetime of the session.
- Every state transition MUST emit a TrustFlow event synchronously.
- No action MUST proceed through the enforcement pipeline unless the session is in `ACTIVE` state.
- `FAILED`, `EXPIRED`, and `REVOKED` are terminal for the current session — no transition back to `ACTIVE` is permitted.
- Session state MUST NOT be inferred from transport state, cookies, or caller network location — only from validated CTX-ID.