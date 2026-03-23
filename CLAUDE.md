# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels data at ingestion (DTL), and emits an append-only audit stream (TrustFlow) — all enforced locally on macOS through a two-process architecture (Swift shell + Python backend) connected via XPC.

## Critical Rules - Read Before Writing Any Code

1. **Fail closed on all trust, identity, policy, and cryptographic errors** — never degrade silently into insecure behavior; reject the action, log the event, surface to caller with context.
2. **Validate CTX-ID FIRST at every enforcement entry point** — validation failure means immediate rejection with no partial processing; missing CTX-ID is UNTRUSTED, never infer identity from session state, UI state, or surrounding context.
3. **Check VTZ policy BEFORE execution of every agent action** — VTZ boundaries are structural, not advisory; cross-VTZ tool calls require explicit policy authorization; implicit access is denied. Emit a `VTZEnforcementDecision` record with `verdict=block` on denial.
4. **Bind every agent session to exactly one VTZ at CTX-ID issuance** — cross-VTZ tool calls are denied unless explicitly authorized by policy.
5. **Emit a TrustFlow event for every action outcome (allow, restrict, block)** — emission is synchronous in the enforcement path; async buffering is not permitted; failed emission is a WARN-level audit event, never a silent skip.
6. **Assign DTL labels at data ingestion; labels are immutable thereafter** — derived data inherits the HIGHEST classification of any source; unlabeled data is CONFIDENTIAL until explicitly reclassified; label verification occurs before any trust boundary crossing.
7. **Secrets never appear in logs, error messages, or generated code** — credentials flow from Keychain → XPC → Python memory only; never in env vars, never on disk, never in error payloads.
8. **Generated code is never executed by the agent** — no `eval`, no `exec`, no shell interpolation, no `subprocess` of generated content, ever.
9. **Gates wait indefinitely for operator input** — no auto-approve, no auto-merge, no auto-dismiss, no timeout-based approval, no bypass by rephrasing a SECURITY_REFUSAL. Never bypass `SECURITY_REFUSAL`; stop processing, gate for operator input, and log the refusal event.
10. **All external input (documents, PR comments, CI output, XPC messages, generated artifacts) is untrusted** — validate strictly; external document context goes in the USER prompt, never the SYSTEM prompt.
11. **All file writes are path-validated via `path_security.validate_write_path()` before execution** — no exceptions, no bypass.
12. **Build memory and build rules are never cleared automatically** — they are persistent learning systems; per-PR stage checkpoints prevent re-running completed work after a crash.
13. **XPC unknown message types are discarded and logged** — never raised as exceptions; never processed; the wire format is line-delimited JSON, nonce-authenticated, max 16 MB per message.

## Architecture Overview

Forge is a two-process architecture. Always. No exceptions.

### Swift Shell (macOS app)
- **Owns:** SwiftUI interface (Navigator + BuildStream + ContextPanel), Touch ID biometric gate, Keychain storage for all credentials, XPC channel, Python process lifecycle.
- **Must NOT:** call LLM APIs, read Keychain on behalf of Python without XPC mediation, execute any agent logic directly.

### Python Backend
- **Owns:** LLM orchestration, tool execution, CTX-ID validation, VTZ policy enforcement, DTL label management, TrustFlow event emission, all agent reasoning.
- **Must NOT:** access Keychain directly, spawn UI, bypass the XPC channel for any credential or biometric operation.

### XPC Channel
- **Wire format:** line-delimited JSON, nonce-authenticated, max 16 MB per message.
- **Unknown message types:** discard and log; never raise as exceptions; never process.
- **Credential flow:** Keychain → XPC → Python memory only. Never env vars, never disk, never error payloads.

## Module Map

- `src/cal/` — Conversation Abstraction Layer enforcement entry points. Must validate CTX-ID first, call VTZ policy before execution, emit TrustFlow for every outcome. Must NOT perform partial processing before trust validation.
- `src/vtz/` — Virtual Trust Zone enforcement and policy boundary control. Must decide authorization before cross-boundary execution. Must NOT allow implicit cross-VTZ access. Emits `VTZEnforcementDecision` records.
- `src/dtl/` — Data Trust Label assignment and verification. Must assign labels at ingestion, enforce immutable inheritance (highest classification propagates), verify labels before boundary crossing. Must NOT permit unlabeled or downgraded data to flow silently.
- `src/trustflow/` — TrustFlow audit stream emission. Must synchronously emit events with required fields (`ctx_id`, `vtz_id`, `action`, `verdict`, `timestamp`, `dtl_label`) in the enforcement path. Must NOT async-buffer or silently drop events.
- `src/trustlock/` — Cryptographic machine identity and CTX-ID validation anchored to TrustLock public key or TPM-backed identity. Must validate issued identity material. Must NOT accept software-only validation when hardware attestation is available.
- `src/mcp/` — MCP Policy Engine. Must evaluate policy inputs deterministically before action execution. Must NOT act as advisory-only logic; decisions are structural and binding.
- `src/rewind/` — Rewind subsystem for session recovery and state rollback. Must preserve trust invariants across rewind operations. Must NOT restore a session to a state that bypasses CTX-ID validation or VTZ policy.

## TrustFlow Event Required Fields

Every TrustFlow event must include:
- `ctx_id` — the validated cryptographic identity of the acting agent
- `vtz_id` — the Virtual Trust Zone in which the action occurs
- `action` — the tool or operation invoked
- `verdict` — one of `allow`, `restrict`, `block`
- `timestamp` — ISO 8601 UTC, set at emission time
- `dtl_label` — the Data Trust Label of the data involved

## VTZEnforcementDecision Record

Emitted on every VTZ policy evaluation:
- `ctx_id` — requesting agent identity
- `source_vtz` — origin VTZ
- `target_vtz` — destination VTZ (same as source for intra-zone actions)
- `action` — requested operation
- `verdict` — `allow` or `block`
- `policy_ref` — the policy rule that produced the verdict
- `timestamp` — ISO 8601 UTC

## DTL Classification Hierarchy

`PUBLIC` < `INTERNAL` < `CONFIDENTIAL` < `RESTRICTED`

- Unlabeled data defaults to `CONFIDENTIAL`.
- Derived data inherits the highest classification of any source.
- Labels are immutable after assignment.
- Label verification occurs before any trust boundary crossing.
- Downgrade is never automatic; requires explicit operator action through a gate.

## Coding Conventions

- All enforcement logic uses `must` and `never` — no `should`, no `consider`, no `may want to`.
- Every function that crosses a trust boundary must accept a `ctx_id` parameter and validate it before any other logic.
- Every function that performs a write must call `path_security.validate_write_path()` before I/O.
- Every function that invokes a tool must check VTZ policy before invocation and emit a TrustFlow event after.
- Error messages must never contain secrets, credentials, key material, or raw Keychain data.
- Tests must cover the fail-closed path for every enforcement point.