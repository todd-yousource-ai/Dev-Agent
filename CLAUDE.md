# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels data at ingestion (DTL), and emits an append-only audit stream (TrustFlow) — failing closed on every violation.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — before any other processing occurs; validation failure means immediate rejection with zero partial work.
2. TrustFlow events MUST be emitted synchronously in the enforcement path for every action outcome (allow, restrict, block) — async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
3. VTZ policy MUST be checked BEFORE execution of any agent action — cross-VTZ tool calls require explicit policy authorization; implicit access is denied.
4. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to caller — never silently continue.
5. Secrets, keys, tokens, and cleartext payloads MUST never appear in logs, error messages, generated code, or audit records.
6. Generated code is NEVER executed by the agent — no `eval`, no `exec`, no `subprocess` of generated content, no shell execution, no exceptions.
7. All external input (documents, PR comments, CI output, XPC messages, serialized payloads) is untrusted — context from external documents goes in the USER prompt, never the SYSTEM prompt.
8. DTL labels are assigned at data ingestion and are immutable; derived data inherits the HIGHEST classification of any source; unlabeled data is treated as CONFIDENTIAL.
9. Gates wait indefinitely for explicit operator input — no auto-approve, no auto-merge, ever.
10. CTX-ID tokens are immutable once issued; rotation creates a new token and invalidates the old one immediately; expired CTX-ID is rejected; missing CTX-ID means UNTRUSTED. Never infer identity from session context, source, or prior state.
11. All file writes MUST be path-validated via `path_security.validate_write_path()` before execution.
12. Build memory and build rules are never cleared automatically — they are persistent learning systems; SECURITY_REFUSAL output is never bypassed by rephrasing — stop, gate, log.
13. Every agent session is bound to exactly one VTZ at CTX-ID issuance; cross-VTZ tool calls are denied unless explicitly authorized by policy.

## Architecture Overview

Enforcement order: **CTX-ID validation → VTZ policy check → Action execution → DTL label verification → TrustFlow emission → Audit record**.

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Processes agent actions; calls CTX-ID validation first, VTZ policy before execution, TrustFlow after | Never process an action without CTX-ID validation; never skip VTZ check |
| **TrustFlow** | `src/trustflow/` | Append-only audit event stream with globally unique event IDs, SHA-256 payload hashes, millisecond UTC timestamps; synchronous emission on enforcement path | Never buffer async in enforcement path; never omit required fields; never silently skip emission |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Structural policy boundaries per agent session; one VTZ per CTX-ID; decides boundary permissions before execution | Never allow implicit cross-VTZ access; never permit action before policy evaluation |
| **TrustLock** | `src/trustlock/` | TPM-anchored machine identity and CTX-ID validation; validates against TrustLock public key | Never accept software-only validation; never issue CTX-ID without hardware-anchored verification |
| **DTL** (Data Trust Labels) | `src/dtl/` | Data classification labels assigned at ingestion; verified before any boundary crossing; derived data inherits highest source classification | Never mutate labels after issuance; never allow unlabeled data to cross boundaries without CONFIDENTIAL default |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Policy enforcement as a control plane input; policies are authoritative | Never degrade into advisory-only behavior; never allow action when policy is unavailable |
| **Forge Rewind** | `src/rewind/` | Replay engine that reconstructs state from audit stream alone | Never require external mutable state for reconstruction; never replay without TrustFlow integrity verification |
| **Forge Connector SDK** | `sdk/connector/` | Preserves enforcement guarantees at integration boundaries | Never bypass policy, identity, or audit requirements at integration points |
| **Tests** | `tests/<subsystem>/` | Validates enforcement invariants per subsystem | Never mock enforcement logic; never skip CTX-ID/VTZ/TrustFlow assertions in integration tests |

## TrustFlow Event Wire Format

Every TrustFlow event record MUST contain:

| Field | Type | Constraint |
|---|---|---|
| `event_id` | `string` (UUID v4) | Globally unique; never reused |
| `timestamp` | `string` (ISO 8601, millisecond UTC) | Set at emission time; never backdated |
| `ctx_id` | `string` | The CTX-ID of the acting agent; MUST be present and validated |
| `vtz_id` | `string` | The VTZ boundary in which the action occurred |
| `action` | `string` | The action attempted |
| `outcome` | `enum`: `allow`, `restrict`, `block` | The enforcement decision |
| `payload_hash` | `string` (SHA-256 hex) | Hash of the action payload; never the payload itself |
| `dtl_label` | `string` | The DTL classification of involved data |
| `reason` | `string` | Human-readable enforcement rationale |

## CTX-ID Lifecycle

- **Issuance**: CTX-ID is issued with TrustLock hardware-anchored verification; bound to exactly one VTZ.
- **Validation**: Every enforcement entry point validates CTX-ID before any processing; validation checks signature, expiry, and revocation status.
- **Immutability**: CTX-ID tokens are immutable once issued.
- **Rotation**: Creates a new CTX-ID and immediately invalidates the old one; no grace period.
- **Expiry/Missing**: Expired CTX-ID is rejected; missing CTX-ID is treated as UNTRUSTED.

## DTL Classification Hierarchy

- Labels are assigned at ingestion and are immutable.
- Derived data inherits the HIGHEST classification of any source input.
- Unlabeled data MUST be treated as CONFIDENTIAL.
- DTL labels MUST be verified before any data crosses a VTZ boundary.

## Fail-Closed Invariants

- CTX-ID validation failure → reject action, emit TrustFlow block event.
- VTZ policy unavailable → reject action, emit TrustFlow block event.
- TrustFlow emission failure → WARN-level audit event; never silent skip; action still subject to enforcement outcome.
- DTL label missing → treat as CONFIDENTIAL; apply highest-restriction policy.
- TrustLock verification failure → reject CTX-ID issuance.
- Gate requiring operator input → wait indefinitely; never auto-approve.
- SECURITY_REFUSAL → stop, gate, log; never bypass by rephrasing.

## Development Workflow

- All external input is untrusted and goes in USER prompt context, never SYSTEM prompt.
- All file writes require `path_security.validate_write_path()` before execution.
- No generated code execution — no `eval`, `exec`, `subprocess`, or shell execution of generated content.
- Build memory and build rules persist across sessions and are never cleared automatically.
- Tests MUST validate enforcement invariants: CTX-ID present and valid, VTZ checked, TrustFlow emitted, DTL labels correct, fail-closed on every error path.