# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) for every outcome.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — validation failure means immediate rejection with zero partial processing.
2. Treat missing CTX-ID as `UNTRUSTED` — never infer identity from process state, UI state, session context, or surrounding metadata.
3. VTZ policy MUST be checked BEFORE execution of any agent action — VTZ boundaries are structural and cannot be bypassed by application code; deny implicitly unless explicit authorization exists.
4. TrustFlow events MUST be emitted synchronously in the enforcement path for every action outcome (`allow`, `restrict`, `block`) — async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
5. All trust, identity, policy, cryptographic, parsing, and auth failures MUST fail closed — reject the action, log the event, surface to caller.
6. Never hardcode secrets, tokens, credentials, or cryptographic material — secrets never appear in logs, error messages, audit records, exceptions, prompts, or generated code.
7. DTL labels are assigned at data ingestion and are immutable — unlabeled data MUST be treated as `CONFIDENTIAL`; derived data inherits the highest classification of any source.
8. All external input (documents, PR comments, CI output, XPC messages, agent payloads, generated code) is untrusted — validate strictly before use.
9. Generated code is never executed by the agent — no `eval()`, no `exec()`, no shell interpolation, no subprocess invocation of generated content.
10. All file writes MUST pass `path_security.validate_write_path()` before execution.
11. Context from external documents goes in the USER prompt — never the SYSTEM prompt.
12. If output contains `SECURITY_REFUSAL`, stop, gate, and log — never retry by rephrasing or switching providers to bypass the refusal.
13. Gate cards wait indefinitely for operator input — no auto-approve ever.
14. XPC unknown message types MUST be discarded and logged — never processed.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → VTZ policy check → Action execution → DTL label verification (if data crosses boundary) → TrustFlow event emission → Audit record**.

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Processes agent actions; calls CTX-ID validation first on every entry point | Never execute an action before VTZ policy check completes; never partially process before trust checks |
| **TrustFlow** | `src/trustflow/` | Emits append-only audit events with `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash` | Never buffer asynchronously in the enforcement path; never omit failed emissions silently |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Enforces structural policy boundaries per agent session; one VTZ per session | Never allow cross-VTZ tool calls without explicit policy authorization; never apply policy changes mid-session |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity anchored to TPM; validates CTX-ID tokens against TrustLock public key | Never accept software-only validation shortcuts; never skip TPM attestation |
| **DTL** (Data Trust Labels) | `src/dtl/` | Assigns immutable classification labels at data ingestion; enforces label inheritance on derived data | Never downgrade, strip, or mutate labels after assignment; never ignore labels without audited policy control |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Evaluates policy decisions used by enforcement subsystems | Never act as advisory-only when an enforcement decision is required; decisions are binding |
| **Rewind** (Forge Rewind) | `src/rewind/` | Replay and audit reconstruction from TrustFlow event stream | Never modify or delete events during replay; replay is read-only |

## TrustFlow Event Wire Format

Every TrustFlow event MUST contain these fields:

| Field | Type | Description |
|---|---|---|
| `event_id` | `string (UUID)` | Unique identifier for this event |
| `session_id` | `string (UUID)` | Session that produced this event |
| `ctx_id` | `string` | Cryptographically verified CTX-ID of the acting agent |
| `ts` | `string (ISO 8601)` | Timestamp of event emission |
| `event_type` | `string enum` | One of: `allow`, `restrict`, `block`, `error`, `gate` |
| `payload_hash` | `string (SHA-256)` | Hash of the action payload for integrity verification |

## Fail-Closed Behavior

- If CTX-ID validation fails → reject immediately, emit `block` TrustFlow event.
- If VTZ policy check fails → reject immediately, emit `block` TrustFlow event.
- If TrustFlow emission fails → log WARN-level audit event, never silently skip; the original action result stands but the failure is surfaced.
- If DTL label is missing → treat data as `CONFIDENTIAL`, assign label, emit TrustFlow event.
- If TrustLock attestation fails → reject, fail closed, emit `block` TrustFlow event.
- If MCP policy evaluation is unavailable → deny by default, emit `block` TrustFlow event.

## Development Constraints

- Never commit secrets, tokens, or credentials to the repository.
- All tests MUST assert TrustFlow event emission for both success and failure paths.
- All tests MUST assert fail-closed behavior for every enforcement subsystem.
- PRs that modify enforcement paths require explicit security review before merge.