# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographic identity (CTX-ID), enforces policy boundaries (VTZ), labels data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) — all failing closed on any violation.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID FIRST at every enforcement entry point — before any processing, parsing, or side effects occur. Reject immediately on failure with no partial processing.
2. Treat missing or expired CTX-ID as `UNTRUSTED` and NEVER infer identity from session context, transport context, or prior state.
3. CTX-ID tokens are IMMUTABLE once issued. Rotation creates a new token and immediately invalidates the old one.
4. Check VTZ policy BEFORE any action execution. VTZ boundaries are structural and CANNOT be bypassed by application code. Deny all implicit cross-VTZ access; cross-VTZ calls require explicit policy authorization.
5. Bind every agent session to exactly one VTZ at CTX-ID issuance. NEVER change VTZ policy mid-session.
6. Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path. Async buffering is forbidden. Failed emission is a WARN-level audit event, NEVER a silent skip.
7. Assign DTL labels at data ingestion. Labels are IMMUTABLE. Derived data inherits the HIGHEST classification of any source. Unlabeled data MUST be treated as `CONFIDENTIAL`.
8. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface the failure to the caller with context — NEVER silently continue.
9. NEVER log, return, or embed secrets, keys, tokens, credentials, or cleartext sensitive payloads in errors, audit records, generated code, or log output.
10. All external input (documents, PR comments, CI output, XPC messages, line-delimited JSON payloads) is untrusted and MUST be validated strictly before use. Context from external documents goes in the USER prompt, NEVER the SYSTEM prompt.
11. Generated code is NEVER executed by the agent — no `eval()`, no `exec()`, no subprocess of generated content.
12. NEVER bypass a `SECURITY_REFUSAL` output by retrying, rephrasing, or falling back to another provider. The agent MUST stop, gate, and log.
13. Gates wait indefinitely for operator input — no auto-approve, no auto-merge, no timeout-to-allow, NEVER silently continue past a blocked decision.
14. All file writes MUST pass `path_security.validate_write_path()` before execution.

## Architecture Overview

Forge uses a strict two-process model:
- **Swift/SwiftUI process** — owns UI, authentication, Keychain secrets, and XPC.
- **Bundled Python 3.12 process** — owns all build intelligence and enforcement logic.

### Shell Concurrency Model

The Swift process uses a `@MainActor`-bound shell that serializes all UI and authentication work on the main actor. Background actors handle network, cryptographic validation, and XPC dispatch. Rules:
- All Keychain access and UI state mutation MUST occur on `@MainActor`.
- Background actors MUST NOT touch UI state or Keychain directly; they send results back to `@MainActor` via structured concurrency (`async let`, `TaskGroup`, or actor-isolated callbacks).
- XPC connections MUST be dispatched from a dedicated background actor, NEVER from `@MainActor`.
- Every cross-actor boundary MUST carry the active CTX-ID; actors MUST NOT cache or reconstruct CTX-ID from local state.

### Subsystem Map

| Subsystem | Path | Enforces | MUST NOT Do |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; action lifecycle gating | Process any agent action before identity and policy checks |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Session-bound policy boundaries; cross-zone authorization checks | Allow implicit cross-VTZ tool calls; change policy mid-session |
| **DTL** (Data Trust Labels) | `src/dtl/` | Immutable label assignment at ingestion; label inheritance on derived data | Permit unlabeled data to cross boundaries without treating it as `CONFIDENTIAL` |
| **TrustFlow** | `src/trustflow/` | Synchronous audit event emission for every action outcome | Buffer events asynchronously; silently drop failed emissions |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity rooted in hardware-backed trust material; CTX-ID public key validation | Accept software-only validation when hardware-backed trust is available |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Explainable, reproducible policy decisions; enforcement-mode operation | Act as advisory-only logic when enforcement is required |
| **Rewind** | `src/rewind/` | Replay engine for audit reconstruction from append-only TrustFlow records | Depend on external state beyond the append-only audit log for replay; mutate audit records |

### Wire Formats

#### CTX-ID Token
| Field | Type | Constraint |
|---|---|---|
| `ctx_id` | `string` (UUID v4) | Immutable after issuance |
| `issued_at` | `int64` (Unix epoch ms) | Set once at creation |
| `expires_at` | `int64` (Unix epoch ms) | MUST be checked on every validation call |
| `vtz_id` | `string` | Bound at issuance; NEVER changes |
| `public_key` | `string` (PEM) | Hardware-backed when available |
| `status` | `enum`: `ACTIVE`, `ROTATED`, `REVOKED` | `ROTATED` and `REVOKED` tokens MUST be rejected |

#### TrustFlow Event
| Field | Type | Constraint |
|---|---|---|
| `event_id` | `string` (UUID v4) | Unique per event |
| `ctx_id` | `string` | MUST reference a valid CTX-ID |
| `vtz_id` | `string` | Zone in which action was evaluated |
| `action` | `string` | The agent action being audited |
| `outcome` | `enum`: `allow`, `restrict`, `block` | MUST be one of the three values |
| `timestamp` | `int64` (Unix epoch ms) | Set at emission time |
| `dtl_label` | `string` | Classification level of data involved |
| `reason` | `string` | Human-readable policy justification |

#### DTL Label
| Field | Type | Constraint |
|---|---|---|
| `label_id` | `string` (UUID v4) | Immutable after assignment |
| `classification` | `enum`: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED` | Unlabeled defaults to `CONFIDENTIAL` |
| `assigned_at` | `int64` (Unix epoch ms) | Set once at ingestion |
| `source_labels` | `array[string]` | For derived data; inherited label is MAX of sources |