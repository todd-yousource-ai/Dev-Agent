# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) — all fail-closed by default.

## Critical Rules — Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — before any other processing occurs; validation failure means immediate rejection with no partial work.
2. TrustFlow events MUST be emitted synchronously in the enforcement path for every action outcome (`allow`, `restrict`, `block`) — async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
3. VTZ policy MUST be checked BEFORE execution of any agent action — emit a `VTZEnforcementDecision` record with `verdict=block` on denial; cross-VTZ tool calls require explicit policy authorization; implicit cross-boundary access is denied unconditionally.
4. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to the caller with context — never silently continue, never degrade to permissive mode.
5. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, audit records, generated code, or cleartext payloads — no exceptions.
6. Generated code is NEVER executed by the agent — no `eval`, no `exec`, no `subprocess` of generated content, ever.
7. All external input (documents, PR comments, CI output, user prompts, XPC messages, serialized payloads) is UNTRUSTED and MUST be validated strictly before use; external document context goes in the USER prompt, never the SYSTEM prompt.
8. DTL labels are assigned at data ingestion and are IMMUTABLE thereafter; derived data inherits the HIGHEST classification of any source; unlabeled data is treated as `CONFIDENTIAL` until explicit reclassification.
9. CTX-ID tokens are IMMUTABLE once issued — rotation creates a new token and invalidates the old one immediately; CTX-ID MUST be validated against TrustLock public key; missing CTX-ID means `UNTRUSTED`; identity MUST never be inferred from session context, request origin, or prior state.
10. Gates (operator approval points) wait indefinitely — no auto-approve, no timeout-based bypass, ever; `SECURITY_REFUSAL` output is terminal and is never bypassed by rephrasing — stop, gate, log.
11. All file writes MUST be path-validated via `path_security.validate_write_path()` before execution; no code may suppress or bypass path validation.
12. Build memory and build rules are persistent learning systems — they are NEVER cleared automatically; per-PR stage checkpoints prevent re-running completed work after a crash.
13. Every agent session MUST be bound to exactly one VTZ at CTX-ID issuance time.

## Architecture Overview

### Subsystem Map (enforcement order: CTX-ID → VTZ → CAL → DTL → TrustFlow → Audit)

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity (TPM-anchored); CTX-ID issuance and validation against hardware key | Issue a CTX-ID without TPM-anchored key verification; accept software-only validation |
| **VTZ** | `src/vtz/` | Virtual Trust Zone boundary enforcement; policy binding at CTX-ID issuance; emits `VTZEnforcementDecision` with `verdict` field (`allow`, `restrict`, `block`) | Allow implicit cross-VTZ access; apply policy changes retroactively to active sessions |
| **CAL** | `src/cal/` | Conversation Abstraction Layer enforcement entry points; validates CTX-ID first, enforces VTZ before action execution | Process agent actions before identity and policy checks complete |
| **DTL** | `src/dtl/` | Data Trust Label assignment at ingestion; label verification before trust-boundary crossings; highest-classification inheritance for derived data | Mutate labels after assignment; allow unlabeled data to cross trust boundaries as non-confidential |
| **TrustFlow** | `src/trustflow/` | Immutable audit stream; synchronous emission of enforcement-path events with required fields (`ctx_id`, `vtz_id`, `action`, `verdict`, `timestamp`, `dtl_label`) | Async-buffer events; silently skip or downgrade failed emission; omit required fields |
| **MCP** | `src/mcp/` | MCP Policy Engine; deterministic policy evaluation before execution | Act as advisory-only; allow non-deterministic policy outcomes; skip evaluation for any action type |
| **Audit** | `src/audit/` | Persistent, tamper-evident audit log consuming TrustFlow events | Drop events; allow log mutation or deletion; expose secrets in audit records |

### Enforcement Flow


Request → CTX-ID Validation (TrustLock)
  ↓ (fail → reject immediately, emit TrustFlow block event)
VTZ Policy Check
  ↓ (fail → reject, emit VTZEnforcementDecision verdict=block)
CAL Action Processing
  ↓
DTL Label Verification
  ↓ (label mismatch or missing → treat as CONFIDENTIAL, restrict)
TrustFlow Event Emission (synchronous)
  ↓
Audit Persistence


### TrustFlow Event Required Fields

| Field | Type | Description |
|---|---|---|
| `ctx_id` | `string` | The validated CTX-ID bound to this action |
| `vtz_id` | `string` | The Virtual Trust Zone in which the action executes |
| `action` | `string` | The agent action being evaluated |
| `verdict` | `enum[allow, restrict, block]` | The enforcement outcome |
| `timestamp` | `ISO-8601 string` | Time of enforcement decision |
| `dtl_label` | `string` | The DTL classification of data involved |
| `reason` | `string` | Human-readable enforcement rationale |

### VTZEnforcementDecision Record

| Field | Type | Description |
|---|---|---|
| `ctx_id` | `string` | The CTX-ID of the requesting agent |
| `vtz_id` | `string` | The target VTZ |
| `verdict` | `enum[allow, restrict, block]` | Policy decision |
| `policy_ref` | `string` | Reference to the policy rule that produced this decision |
| `timestamp` | `ISO-8601 string` | Time of decision |

### CTX-ID Token Contract

- Issued by TrustLock after TPM-anchored key verification.
- IMMUTABLE once issued — no field mutation.
- Rotation: new token issued, old token invalidated immediately.
- Validation: MUST verify against TrustLock public key on every enforcement entry point.
- Missing CTX-ID: action is classified `UNTRUSTED` and rejected.

### DTL Classification Hierarchy

`PUBLIC` < `INTERNAL` < `CONFIDENTIAL` < `RESTRICTED`

- Unlabeled data defaults to `CONFIDENTIAL`.
- Derived data inherits the HIGHEST classification of all source data.
- Labels are IMMUTABLE after assignment.
- Cross-VTZ data transfer MUST verify DTL labels at both source and destination boundaries.

### Build Memory & Stage Checkpoints

- Build memory and build rules are persistent — NEVER cleared automatically.
- Per-PR stage checkpoints record completed stages and prevent re-execution after crash recovery.
- Checkpoint state MUST be validated before resuming any build stage.

### Security Boundaries

- External input (documents, PR comments, CI output, XPC messages, serialized payloads) is UNTRUSTED.
- External document context MUST be placed in the USER prompt, NEVER in the SYSTEM prompt.
- `path_security.validate_write_path()` MUST be called before every file write.
- `SECURITY_REFUSAL` is a terminal state: no retry, no rephrase, no suppression.
- Gates wait indefinitely for operator approval — no auto-approve, no timeout bypass.