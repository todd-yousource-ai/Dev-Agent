# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data via DTL, and emits an immutable TrustFlow audit stream — all enforced locally on macOS via a native Swift shell orchestrating a Python consensus backend over authenticated XPC.

## Critical Rules - Read Before Writing Any Code

1. **Fail closed on every trust, identity, policy, and cryptographic error** — reject the action, log the event, surface to caller; never silently degrade or continue.
2. **Validate CTX-ID first at every enforcement entry point** — validation failure means immediate rejection with zero partial processing; missing CTX-ID is UNTRUSTED, never inferred from session state, transport context, or prior requests.
3. **CTX-ID tokens are immutable once issued** — rotation creates a new token and invalidates the old one immediately; validate against TrustLock public key only (software-only validation is rejected); respect per-deployment clock-skew tolerance for expiry.
4. **Emit a TrustFlow event for every action outcome (allow, restrict, block)** — emission is synchronous in the enforcement path; async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
5. **Every TrustFlow event must include `event_id` (CSPRNG), `session_id`, `ctx_id`, `ts` (UTC ms), `event_type`, `payload_hash` (SHA-256)** — no optional fields, no exceptions.
6. **Check VTZ policy before execution of every action** — cross-VTZ tool calls require explicit policy authorization; implicit cross-VTZ access is denied; VTZ boundaries are structural, not advisory; policy changes take effect at next CTX-ID issuance, not mid-session.
7. **Secrets, keys, tokens, and credentials must never appear in logs, error messages, generated code, audit records, prompts, or cleartext payloads** — store in Keychain, protect in memory, encrypt in transit and at rest.
8. **All external input (documents, PR comments, CI output, XPC messages, tool output) is untrusted** — validate strictly before use; external document context goes in USER prompt, never SYSTEM prompt; unknown XPC message types are discarded and logged, never raised as exceptions.
9. **Generated code is never executed by the agent** — no `eval`, no `exec`, no `subprocess` of generated content; `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log.
10. **DTL labels are assigned at data ingestion and are immutable** — derived data inherits the highest classification of any source; unlabeled data is CONFIDENTIAL until explicitly reclassified; label stripping is a security event requiring audit and policy control.
11. **Gates wait indefinitely for operator input — no auto-approve ever** — build memory and build rules are never cleared automatically; per-PR stage checkpoints prevent re-running completed work after a crash.
12. **All file writes are path-validated via `path_security.validate_write_path()` before execution** — reject path traversal or unapproved destinations immediately.

## Architecture Overview

- `src/cal/` — **Conversation Abstraction Layer** enforces action entry, CTX-ID validation first, and handoff into policy; it must NOT execute actions before identity and VTZ checks.
- `src/vtz/` — **Virtual Trust Zone** enforcement binds each agent session to exactly one VTZ and decides cross-VTZ access; it must NOT allow implicit cross-zone execution.
- `src/dtl/` — **Data Trust Label** enforcement assigns labels at ingestion and verifies labels before boundary crossing; it must NOT mutate labels after assignment except via explicit audited reclassification flow.
- `src/trustflow/` — **TrustFlow** audit stream emits synchronous enforcement-path events with required fields and replayability; it must NOT buffer asynchronously or drop failures silently.
- `src/trustlock/` — **TrustLock** provides cryptographic machine identity and CTX-ID validation against public-key-backed hardware trust; it must NOT accept software-only validation for CTX-ID.
- `src/mcp/` — **MCP Policy Engine** evaluates policy for tools, boundaries, and execution requests; it must NOT act as advisory-only logic when enforcement is required.
- `src/keychain/` — **KeychainKit** provides secret storage abstractions; all secrets, keys, tokens, and credentials are stored and retrieved exclusively through KeychainKit; direct file-based or in-memory secret storage is forbidden.
- `src/xpc/` — **XPC Bridge** handles authenticated inter-process communication between the Swift shell and Python backend; unknown message types are discarded and logged; all XPC payloads are validated against schema before dispatch.

## Enforcement Sequencing

Every action request follows this mandatory sequence:

1. **CTX-ID Validation** — verify token signature against TrustLock public key, check expiry with clock-skew tolerance, confirm token is not revoked.
2. **VTZ Policy Check** — resolve the agent's bound VTZ, evaluate the requested action against VTZ policy, reject cross-VTZ calls without explicit authorization.
3. **DTL Boundary Check** — verify DTL labels on all data involved in the action; block data from crossing trust boundaries without matching label clearance.
4. **MCP Policy Evaluation** — evaluate tool-specific and action-specific policy constraints.
5. **Action Execution** — only after steps 1–4 pass.
6. **TrustFlow Emission** — emit a synchronous TrustFlow event recording the outcome (allow, restrict, block) with all required fields.

No step may be reordered, skipped, or deferred.

## TrustFlow Event Wire Format

Every TrustFlow event is a JSON object with the following required fields:

| Field | Type | Constraints |
|---|---|---|
| `event_id` | `string` | CSPRNG-generated unique identifier |
| `session_id` | `string` | Bound to the active VTZ session |
| `ctx_id` | `string` | The validated CTX-ID token identifier |
| `ts` | `integer` | UTC milliseconds since epoch |
| `event_type` | `string` | One of: `allow`, `restrict`, `block`, `security_refusal`, `gate_wait`, `audit` |
| `payload_hash` | `string` | SHA-256 hex digest of the action payload |

All fields are required. Omitting any field is a schema violation that must be rejected before persistence.

## CTX-ID Lifecycle

- **Issuance**: CTX-ID tokens are issued by TrustLock, signed with the machine's hardware-backed private key.
- **Validation**: Every enforcement entry point validates the CTX-ID signature against the TrustLock public key. Software-only key validation is rejected.
- **Immutability**: Issued tokens are never modified.
- **Rotation**: Rotation creates a new token and immediately invalidates the old one. There is no grace period for old tokens.
- **Expiry**: Tokens have a fixed expiry. Validation must respect per-deployment clock-skew tolerance. Expired tokens are rejected.
- **Policy binding**: Policy changes take effect at next CTX-ID issuance, not mid-session.

## DTL Classification Rules

- Labels are assigned at data ingestion and are immutable after assignment.
- Unlabeled data is classified as `CONFIDENTIAL` until explicitly reclassified via audited reclassification flow.
- Derived data inherits the highest classification of any source input.
- Label stripping is a security event that must be audited and requires explicit policy authorization.
- Data must not cross a trust boundary unless DTL labels are verified against the destination's clearance policy.

## KeychainKit Contract

- All secrets, keys, tokens, and credentials are stored exclusively via KeychainKit abstractions.
- KeychainKit wraps macOS Keychain Services; direct `Security.framework` calls from application code are forbidden.
- Secret retrieval returns opaque handles; raw secret bytes must never be logged, serialized to disk outside Keychain, or included in error messages.
- KeychainKit operations that fail must fail closed — the caller receives an error, never a fallback or default value.
- Key deletion is immediate and audited via TrustFlow.

## XPC Security Contract

- All XPC connections are authenticated before any message is processed.
- XPC message payloads are validated against a strict schema; unknown message types are discarded and logged.
- XPC transport errors are logged and surfaced to the caller; they never cause silent fallback to an unauthenticated channel.
- XPC messages must never contain cleartext secrets; use KeychainKit references.

## Forbidden Patterns

- `eval()`, `exec()`, `subprocess` of generated content — always forbidden.
- `async` TrustFlow buffering or batching — always forbidden.
- Auto-approve, auto-merge, or timeout-based gate resolution — always forbidden.
- Inferring identity from session state or transport context — always forbidden.
- Storing secrets in environment variables, config files, or log output — always forbidden.
- Implicit cross-VTZ access — always forbidden.
- Mutable DTL labels outside audited reclassification — always forbidden.
- Software-only CTX-ID validation without hardware-backed key — always forbidden.