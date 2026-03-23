# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) — failing closed on every violation.

## Critical Rules — Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — before any processing, branching, or side effects occur.
2. CTX-ID tokens are IMMUTABLE once issued; expired or missing CTX-ID MUST be rejected as UNTRUSTED — never infer identity from session context, transport metadata, or prior requests.
3. Every agent action MUST be checked against VTZ policy BEFORE execution; VTZ boundaries are structural and cannot be bypassed by application code. On denial, emit a `VTZEnforcementDecision` record with `verdict=block`.
4. Every action outcome (`allow`, `restrict`, `block`) MUST emit a synchronous TrustFlow event — async buffering is forbidden in the enforcement path.
5. All trust, identity, policy, and cryptographic failures MUST fail CLOSED: reject the action, log the event, surface to the caller — never silently continue.
6. Secrets, keys, tokens, and credentials MUST NOT appear in logs, error messages, generated code, or TrustFlow payloads — ever.
7. Generated code is never executed by the agent — no `eval`, no `exec`, no `subprocess`, no shell expansion of generated content.
8. All external input (documents, PR comments, CI output, XPC messages, LLM responses) is untrusted and MUST be validated strictly before use.
9. DTL labels are assigned at data ingestion and are immutable; unlabeled data MUST be treated as CONFIDENTIAL; derived data inherits the HIGHEST classification of any source. Unlabeled or downgraded data MUST NOT cross trust boundaries without policy control.
10. Gates wait indefinitely for operator input — no auto-approve, no timeout-based approval, ever.
11. All file writes MUST be path-validated via `path_security.validate_write_path()` before execution; context from external documents goes in the USER prompt — never the SYSTEM prompt.
12. Build memory and build rules are never cleared automatically — they are persistent learning systems; per-PR stage checkpoints prevent re-running completed work after a crash.
13. Stop, gate, and log on `SECURITY_REFUSAL` output — never bypass it by rephrasing, retrying around it, or downgrading the refusal.
14. Discard and log unknown XPC message types — never raise them as uncaught exceptions on the wire path.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID → VTZ → CAL → DTL → Action → TrustFlow → Audit**.

| Subsystem | Path | Enforces | Must NOT |
|-----------|------|----------|----------|
| **CTX-ID / TrustLock** | `src/trustlock/` | Cryptographic machine identity anchored to TPM; issues and validates CTX-ID tokens; validates against TrustLock public key material | Modify tokens after issuance; accept software-only validation; infer identity from context |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Structural policy boundaries per agent session; one VTZ per session bound at CTX-ID issuance | Allow implicit cross-VTZ tool calls; apply policy changes mid-session; permit cross-VTZ access without explicit policy |
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Processes agent actions only after CTX-ID validation and VTZ policy check | Execute actions before policy evaluation; swallow enforcement failures |
| **DTL** (Data Trust Labels) | `src/dtl/` | Classification labels assigned at ingestion; immutable; inheritance follows highest-classification-wins rule | Allow unlabeled data past ingestion without CONFIDENTIAL default; permit label downgrade; allow unlabeled or downgraded data to cross trust boundaries without policy control |
| **TrustFlow** | `src/trustflow/` | Synchronous forensic audit event emission on every enforcement decision in the enforcement path | Buffer asynchronously; silently drop events; include secrets or keys in payloads |
| **MCP Policy Engine** | `src/mcp/` | Deterministic and explainable policy decisions | Mutate enforcement state mid-decision; produce non-deterministic results for identical inputs |
| **Forge Rewind** | `src/rewind/` | Replay from append-only audit records alone | Depend on external mutable state for replay correctness |

## Cross-TRD Interface Contracts

### CTX-ID Issuance and Validation
- CTX-ID issuance MUST be TPM-anchored via TrustLock (`src/trustlock/`).
- Every subsystem receiving a request MUST call CTX-ID validation before any processing.
- CTX-ID tokens MUST contain: agent identity, issuance timestamp, VTZ binding, and cryptographic signature.
- Expired, malformed, or missing CTX-ID MUST result in immediate rejection with a TrustFlow event emitted.

### VTZ ↔ CAL Contract
- CAL MUST pass the validated CTX-ID and requested action to VTZ for policy evaluation before execution.
- VTZ MUST return a deterministic `VTZEnforcementDecision` (`allow`, `restrict`, or `block`) with `verdict`, `policy_id`, and `timestamp` fields.
- CAL MUST NOT proceed on `block`; MUST constrain scope on `restrict`; MUST emit the decision to TrustFlow regardless of verdict.

### DTL ↔ VTZ Contract
- VTZ policy evaluation MUST include DTL classification of all data operands.
- Data crossing a VTZ boundary MUST have its DTL label verified against the target VTZ's allowed classification set.
- Derived data MUST inherit the highest DTL classification of all source inputs — no exceptions.

### TrustFlow Emission Contract
- Every enforcement decision (CTX-ID validation, VTZ policy check, DTL classification check, action execution, gate decision) MUST emit a TrustFlow event synchronously before returning control.
- TrustFlow events MUST contain: `event_type`, `ctx_id`, `vtz_id`, `verdict`, `timestamp`, `policy_id`, and `dtl_label` fields.
- TrustFlow records are append-only and MUST be sufficient for Forge Rewind replay without external state.
- TrustFlow payloads MUST NOT contain secrets, keys, tokens, or credentials.

### XPC Wire Path Contract
- All XPC messages MUST carry a valid CTX-ID; messages without CTX-ID MUST be rejected at the wire boundary.
- Unknown XPC message types MUST be discarded and logged — never raised as uncaught exceptions.
- XPC message validation failures MUST emit a TrustFlow event and fail closed.

### Forge Rewind Contract
- Replay MUST be reconstructable from append-only TrustFlow audit records alone.
- Rewind MUST NOT depend on mutable external state for replay correctness.
- Rewind MUST verify CTX-ID chain integrity during replay and halt on any broken link.

### MCP Policy Engine Contract
- Policy evaluation MUST be deterministic: identical inputs MUST produce identical verdicts.
- Policy engine MUST NOT mutate enforcement state during evaluation.
- All policy decisions MUST be explainable — the decision record MUST reference the specific policy rule(s) applied.