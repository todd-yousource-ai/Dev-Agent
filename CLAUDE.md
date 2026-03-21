# CLAUDE.md - Forge Platform

Forge is a security-first trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels all data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) for every outcome.

## Critical Rules — Read Before Writing Any Code

1. Validate CTX-ID FIRST at every enforcement entry point — reject immediately on failure with zero partial processing.
2. Check VTZ policy BEFORE executing any agent action — emit a `VTZEnforcementDecision` record with `verdict=block` on denial. VTZ boundaries are structural, not advisory. Implicit cross-VTZ access is denied unless policy explicitly authorizes it.
3. Bind every agent session to exactly one VTZ at CTX-ID issuance time — never infer identity or zone from ambient context.
4. Emit a synchronous TrustFlow event in the enforcement path for every action outcome (`allow`, `restrict`, `block`) — async buffering is forbidden. Failed emission is a WARN-level audit event that MUST be surfaced.
5. Treat missing, expired, rotated, or invalid CTX-ID as `UNTRUSTED` — CTX-ID tokens are immutable once issued; rotation creates a new token and immediately invalidates the old one.
6. Assign DTL labels at data ingestion — labels are immutable after assignment. Derived data inherits the HIGHEST classification of any source. Unlabeled data is `CONFIDENTIAL` until explicitly reclassified.
7. Fail closed on ALL trust, identity, policy, and cryptographic failures — reject the action, log the event, surface to the caller, never silently continue.
8. All external input (documents, PR comments, CI output, XPC messages, agent payloads, generated code artifacts) is untrusted — validate strictly before use. Context from external documents goes in the USER prompt, NEVER the SYSTEM prompt.
9. Never execute generated content — no `eval()`, no `exec()`, no dynamic loading, no subprocess execution of generated code. `shell=True` is banned.
10. Validate every file write path with `path_security.validate_write_path()` before any write to disk — no exceptions.
11. Stop immediately on `SECURITY_REFUSAL` — never bypass by rephrasing or retrying another model path. Log the gateable security event.
12. Gate cards (`gate_card`) block indefinitely for operator input — no auto-approve, no auto-merge, no silent continuation past a required human decision.
13. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, or generated code — error messages include `component`, `operation`, `failure_reason`, and `ctx_id` only.
14. Audit records are append-only, generated BEFORE execution, and MUST NOT contain secrets, keys, tokens, or cleartext sensitive data — replay MUST be possible from the audit stream alone.

## Enforcement Order

Every agent action follows this sequence with no exceptions:

**CTX-ID validation → VTZ policy check → Action execution → DTL label verification → TrustFlow emission → Audit record**

## Architecture Overview

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Processes agent actions; calls CTX-ID validation first on every entry point; orchestrates enforcement order | Must NOT execute any action before CTX-ID validation and VTZ policy check complete |
| **TrustLock** (Cryptographic Machine Identity) | `src/trustlock/` | TrustLock-backed CTX-ID validation using the TrustLock public key; hardware-rooted identity verification | Must NOT accept software-only validation when TrustLock hardware attestation is required |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Binds sessions to one VTZ; evaluates policy before execution; emits `VTZEnforcementDecision` with `verdict` field (`allow`, `restrict`, `block`) | Must NOT allow implicit cross-VTZ access; Must NOT treat boundaries as advisory |
| **DTL** (Data Trust Labels) | `src/dtl/` | Assigns classification labels at ingestion; enforces immutability; verifies boundary compliance | Must NOT mutate labels after assignment; Must NOT allow unlabeled data to pass as unclassified |
| **TrustFlow** (Audit Stream) | `src/trustflow/` | Emits synchronous immutable audit events for every action outcome; required fields: `ctx_id`, `vtz_id`, `action`, `outcome`, `timestamp`, `component` | Must NOT buffer events asynchronously; Must NOT silently skip emission failures |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Evaluates policy decisions for tools, boundaries, and controls; enforces action-level authorization | Must NOT act as advisory-only logic when enforcement is required |
| **Rewind** (Forge Rewind) | `src/rewind/` | Reconstructs events and decisions from the TrustFlow audit stream; validates replay integrity | Must NOT depend on state outside the audit stream; replay MUST reproduce the same enforcement decisions |

## TrustFlow Event Required Fields

Every TrustFlow event MUST include:

| Field | Type | Description |
|---|---|---|
| `ctx_id` | `string` | The validated CTX-ID of the acting agent |
| `vtz_id` | `string` | The VTZ in which the action executes |
| `action` | `string` | The action being performed |
| `outcome` | `enum` | One of `allow`, `restrict`, `block` |
| `timestamp` | `ISO 8601 string` | Time of event emission |
| `component` | `string` | Subsystem emitting the event |
| `failure_reason` | `string \| null` | Reason for restriction or block; null on allow |

## VTZEnforcementDecision Record

| Field | Type | Description |
|---|---|---|
| `ctx_id` | `string` | CTX-ID of the requesting agent |
| `vtz_id` | `string` | Target VTZ |
| `verdict` | `enum` | One of `allow`, `restrict`, `block` |
| `policy_ref` | `string` | Policy identifier that produced the verdict |
| `timestamp` | `ISO 8601 string` | Time of decision |

## File and Path Security

- Every file write MUST call `path_security.validate_write_path(target_path)` and receive `True` before proceeding.
- Path traversal, symlink escape, and writes outside the designated workspace are rejected.
- Violation is a `SECURITY_REFUSAL` event — stop, gate, log.

## Gate Card Protocol

- Any `gate_card` event blocks execution indefinitely until an authorized operator provides input.
- No timeout, no auto-approve, no fallback path.
- Gate decisions are logged as audit records with the operator's identity and decision.

## Error Message Format

All error messages MUST follow this structure and MUST NOT include secrets, keys, or tokens:


{
  "component": "<subsystem name>",
  "operation": "<action attempted>",
  "failure_reason": "<why it failed>",
  "ctx_id": "<agent CTX-ID or UNTRUSTED>"
}
