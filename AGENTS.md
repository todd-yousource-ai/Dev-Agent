# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data via DTL, and emits an immutable TrustFlow audit stream — rejecting any action that fails identity, policy, or integrity checks.

## Critical Rules — Read Before Writing Any Code

1. Validate CTX-ID **first** at every enforcement entry point — validation failure is immediate rejection with no partial processing. Missing, expired, invalid, or unverifiable CTX-ID is `UNTRUSTED`; never infer identity from session context, UI state, or prior requests.
2. Check VTZ policy **before** executing any agent action — VTZ boundaries are structural and cannot be bypassed by application code. Cross-VTZ tool calls require explicit policy authorization or they are denied.
3. Emit a synchronous TrustFlow event for every action outcome (allow, restrict, block) in the enforcement path with required fields: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash`. Async buffering is forbidden. Emission failure is a WARN-level audit event, never a silent skip.
4. All trust, identity, policy, and cryptographic failures MUST fail **closed**: reject the action, log the event, surface to the caller — never silently continue, never degrade into insecure behavior.
5. Secrets, keys, tokens, credentials, and cleartext sensitive payloads MUST never appear in logs, error messages, audit records, prompts, generated code, or cleartext payloads — error messages include `component`, `operation`, `failure_reason`, `ctx_id` only.
6. All external input (documents, PR comments, CI output, XPC messages) is **untrusted** — validate strictly before use. Injection scanning is mandatory for loaded document chunks before prompt inclusion. External document context goes in the **USER** prompt, never the SYSTEM prompt.
7. Generated code is **never** executed by the agent — no `eval()`, no `exec()`, no dynamic subprocess execution, no equivalent code-loading mechanisms. `shell=True` is banned in all subprocess calls.
8. If a model returns `SECURITY_REFUSAL`, stop, gate, and log — never retry with rephrasing, never retry with another model, never continue execution.
9. DTL labels are assigned at data ingestion and are **immutable** thereafter — derived data inherits the highest classification of any source (high-water-mark). Unlabeled data is treated as `CONFIDENTIAL` until explicitly reclassified through policy-controlled reclassification.
10. CTX-ID tokens are **immutable** once issued — rotation creates a new token and immediately invalidates the old one. Expired CTX-ID is rejected. Missing CTX-ID is `UNTRUSTED`.
11. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions, no bypass.
12. Gates wait **indefinitely** for explicit operator input — no auto-approve, no auto-merge, no inferred approval from timeout or context. The human is in the loop at every gate.
13. Discard and log unknown XPC message types without raising transport-crashing exceptions.

## Architecture Overview

Forge is a two-process system:

- **Swift frontend** (native macOS): UI, Keychain access, XPC transport. The Swift process MUST never make LLM API calls directly.
- **Python 3.12 backend**: LLM orchestration, enforcement, GitHub operations. The Python process MUST never read from the macOS Keychain directly.

Credentials cross the process boundary exactly once via authenticated XPC. All XPC messages are validated on receipt; unknown message types are discarded and logged.

### Module Contracts

- `src/cal/` — **Conversation Abstraction Layer**: enforcement entry points. MUST validate CTX-ID first, apply VTZ policy second, emit TrustFlow third. MUST NOT execute actions before enforcement completes.
- `src/vtz/` — **Virtual Trust Zone** policy enforcement. MUST bind each session to exactly one VTZ. MUST NOT permit implicit cross-VTZ tool calls.
- `src/dtl/` — **Data Trust Label** enforcement. MUST assign labels at ingestion and verify labels before trust-boundary crossing. MUST NOT allow mutable post-ingestion relabeling without policy-controlled reclassification.
- `src/trustflow/` — **TrustFlow** append-only audit emission. MUST synchronously emit all required fields (`event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash`) in the enforcement path. MUST NOT silently buffer, skip, or downgrade failed emission.
- `src/trustlock/` — **TrustLock** cryptographic machine identity and CTX-ID validation. MUST validate CTX-ID against the TrustLock public key. MUST NOT rely on software-only validation when hardware-backed keys are available.
- `src/mcp/` — **MCP Policy Engine**. MUST make explainable, reproducible policy decisions. MUST log every policy evaluation with inputs and result. MUST NOT permit policy bypass via fallback or default-allow.

## Cross-TRD Precedence Rules

When Technical Requirements Documents conflict, the following precedence applies (highest to lowest):

1. **TRD-SEC (Security & Cryptographic Identity)** — CTX-ID validation, TrustLock, fail-closed behavior. Security requirements override all other TRDs.
2. **TRD-VTZ (Virtual Trust Zones)** — Boundary enforcement and isolation policy. VTZ constraints override operational and functional requirements.
3. **TRD-DTL (Data Trust Labels)** — Classification, labeling, and data-flow constraints. DTL rules override audit and functional requirements when label integrity is at stake.
4. **TRD-TF (TrustFlow Audit)** — Audit completeness and emission requirements. Audit requirements override functional convenience but yield to security, VTZ, and DTL.
5. **TRD-MCP (MCP Policy Engine)** — Policy evaluation logic. MCP implements decisions but defers to higher-precedence TRDs for constraint definition.
6. **TRD-CAL (Conversation Abstraction Layer)** — Orchestration and functional behavior. CAL is the lowest precedence; it MUST NOT override any constraint from a higher-precedence TRD.

When a conflict is detected and cannot be resolved by precedence alone, the developer MUST file an Architecture Decision Record (ADR) and gate on operator approval before proceeding.

## ADR Template

All architecture decisions that resolve cross-TRD conflicts, introduce new trust boundaries, or modify enforcement behavior MUST be recorded as an ADR in `docs/adr/` with the following structure:

markdown
# ADR-NNNN: <Title>

## Status
<!-- PROPOSED | ACCEPTED | SUPERSEDED by ADR-XXXX | REJECTED -->

## Date
<!-- YYYY-MM-DD -->

## Context
<!-- What conflict, ambiguity, or architectural question triggered this decision? Reference specific TRD sections. -->

## TRDs Involved
<!-- List all TRDs that apply, in precedence order. -->

## Decision
<!-- What was decided, and which TRD precedence rule resolved it? Be specific about the enforcement behavior chosen. -->

## Consequences
<!-- What changes in enforcement behavior, module contracts, or audit emissions result from this decision? -->

## Compliance
<!-- How is this decision verified? Reference specific tests, audit events, or CI checks. -->


ADR filenames follow the pattern `docs/adr/ADR-NNNN-kebab-case-title.md`. The sequence number MUST be monotonically increasing. ADRs are append-only; superseded ADRs are marked `SUPERSEDED by ADR-XXXX` but never deleted.

## Two-Process Isolation Boundary

### Boundary Definition

The isolation boundary between the Swift frontend and Python backend is enforced via XPC. The following invariants MUST hold:

| Constraint | Swift Frontend | Python Backend |
|---|---|---|
| LLM API calls | NEVER | EXCLUSIVE |
| Keychain access | EXCLUSIVE | NEVER |
| Credential lifetime | Read from Keychain, transmit once via XPC | Receive via XPC, hold in memory only, never persist to disk |
| XPC message validation | Validate all outbound messages against schema | Validate all inbound messages against schema |
| Unknown message types | Discard and log | Discard and log |
| CTX-ID validation | Attach CTX-ID to every XPC request | Validate CTX-ID on every XPC message before processing |
| TrustFlow emission | NEVER (no direct audit writes) | EXCLUSIVE |
| File system writes | NEVER (except UI state) | All writes pass `path_security.validate_write_path()` |

### XPC Message Schema

Every XPC message MUST include:
- `msg_type` (string): registered message type identifier
- `ctx_id` (string): valid CTX-ID token
- `ts` (string, ISO 8601): message timestamp
- `payload` (object): type-specific payload
- `payload_hash` (string, SHA-256): hex-encoded hash of the canonical payload serialization

Messages missing any required field are rejected. Messages with an invalid `ctx_id` are rejected. Messages with a `payload_hash` mismatch are rejected and logged as a integrity violation.

### Credential Flow

1. Swift frontend reads credential from macOS Keychain.
2. Swift frontend sends credential to Python backend via authenticated XPC exactly once per session.
3. Python backend holds credential in memory only — never written to disk, never logged, never included in audit payloads.
4. On session termination or CTX-ID rotation, the in-memory credential is zeroed.

No other credential flow is permitted.