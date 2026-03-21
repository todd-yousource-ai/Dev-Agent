# AGENTS.md - Forge Platform

Forge is a security-first trust-enforcement platform and autonomous build agent runtime that binds every agent action to a cryptographically verified identity (CTX-ID), enforces structural policy boundaries (VTZ), labels data classifications (DTL), emits an immutable audit stream (TrustFlow), and fails closed on any trust, crypto, policy, or path-safety violation.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID first at every enforcement entry point — before any processing, before any side effect — and reject immediately on failure with fail-closed semantics and no partial processing.
2. Treat missing CTX-ID as `UNTRUSTED` — never infer identity from ambient context, session state, or transport metadata.
3. Check VTZ policy before executing any action, tool call, cross-boundary operation, or external side effect — VTZ boundaries are structural, not advisory.
4. Emit a synchronous TrustFlow event for every action outcome in the enforcement path. Each event MUST include `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, and `payload_hash`. Async buffering is forbidden.
5. TrustFlow emission failure MUST NOT silently continue — log at WARN level, surface the failure, never skip the record.
6. Enforce DTL labels at ingestion; labels are immutable once assigned. Unlabeled data MUST be treated as `CONFIDENTIAL` until explicitly reclassified. On derivation, inherit the highest classification of all inputs.
7. Fail closed on all trust, identity, policy, cryptographic, and path-validation errors — reject the action, log the event, surface the failure to the caller.
8. Validate every write path with `path_security.validate_write_path()` before any file write, rename, or generated artifact save.
9. Never execute generated or external content — no `eval()`, no `exec()`, no `subprocess` of generated code or text, no `shell=True`.
10. Never bypass `SECURITY_REFUSAL` — stop processing, gate for operator review, and log the event. Rephrasing MUST NOT circumvent a refusal.
11. Treat all external input as untrusted — documents, PR comments, CI output, user prompts, XPC messages, and streamed JSON payloads. Validate strictly before use.
12. Discard and log unknown XPC message types — never raise them as uncaught exceptions and never process them optimistically.
13. Gates wait indefinitely for operator input — there is never any auto-approve path for merge, policy override, or security-sensitive continuation.
14. Never hardcode secrets, tokens, credentials, or cryptographic material — never log them, never include them in error messages or audit records.
15. Audit records are append-only, MUST NOT contain secrets or cleartext sensitive data, and MUST support full replay reconstruction without external state.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID → VTZ → CAL → DTL check → Execute → TrustFlow emit → Audit record**.

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Processes agent actions only after CTX-ID validation and VTZ policy check complete | Never perform partial action processing before trust checks complete |
| **CTX-ID** (Contextual Identity) | `src/trustlock/ctx_id.py` | Immutable cryptographic identity tokens, validated against TrustLock public key; missing token → `UNTRUSTED` | Never infer identity from context; never modify a token after issuance |
| **TrustLock** | `src/trustlock/` | TPM-anchored machine identity, key generation/rotation/destruction | Never accept software-only validation; never expose key material |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Structural policy boundaries per agent session; exactly one VTZ per CTX-ID | Never allow implicit cross-VTZ tool calls; never apply policy changes mid-session |
| **DTL** (Data Trust Labels) | `src/dtl/` | Classification labels assigned at ingestion, immutable thereafter; unlabeled → `CONFIDENTIAL` | Never strip labels; never silently downgrade classification; never allow mutable downgrade in normal flows |
| **TrustFlow** | `src/trustflow/` | Synchronous audit event emission for every action outcome; fields: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash` | Never buffer asynchronously; never silently skip a failed emission |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Evaluates policy inputs deterministically before action execution; feeds VTZ and CAL decisions | Never evaluate policy non-deterministically; never allow side effects during evaluation |
| **Path Security** | `src/path_security/` | Validates all write paths via `path_security.validate_write_path()` before file writes, renames, or artifact saves | Never write to an unvalidated path; never skip validation for generated artifacts |

## TrustFlow Event Wire Format

Every TrustFlow event is a JSON object with these required fields:

| Field | Type | Description |
|---|---|---|
| `event_id` | `string (UUID)` | Unique identifier for this event |
| `session_id` | `string (UUID)` | Session that produced the event |
| `ctx_id` | `string` | CTX-ID of the acting agent identity |
| `ts` | `string (ISO 8601)` | Timestamp of event emission |
| `event_type` | `string` | One of: `ACTION_ALLOWED`, `ACTION_RESTRICTED`, `ACTION_BLOCKED`, `SECURITY_REFUSAL`, `TRUST_FAILURE`, `AUDIT_ERROR` |
| `payload_hash` | `string (SHA-256 hex)` | Hash of the action payload for tamper evidence |

All fields are REQUIRED. Events with missing fields MUST be rejected at the emitter. Events MUST be emitted synchronously in the enforcement path before returning control to the caller.

## Enforcement Contracts

### CTX-ID Validation Contract
- Every public entry point MUST call `validate_ctx_id(token)` as its first operation.
- `validate_ctx_id` MUST verify the token signature against the TrustLock public key.
- On failure, return an error immediately — no partial work, no side effects.
- A missing token MUST be treated as `UNTRUSTED`, not as an anonymous session.

### VTZ Policy Contract
- After CTX-ID validation, every action MUST be checked against the VTZ bound to that CTX-ID.
- Each CTX-ID is bound to exactly one VTZ for the duration of a session.
- Cross-VTZ calls MUST be explicit and policy-gated — implicit cross-boundary access is forbidden.
- Policy MUST NOT mutate mid-session.

### DTL Labeling Contract
- Labels MUST be assigned at data ingestion and are immutable thereafter.
- Unlabeled data MUST be classified as `CONFIDENTIAL`.
- Derived data MUST inherit the highest classification of all source inputs.
- Labels MUST be verified before any trust-boundary crossing.
- Silent label stripping or downgrade is forbidden.

### Audit Contract
- Audit records are append-only.
- Records MUST NOT contain secrets, tokens, credentials, or cleartext sensitive data.
- The audit log MUST support full replay reconstruction without external state.
- Every enforcement decision (allow, restrict, block, refusal) MUST produce an audit record.

### XPC Message Handling Contract
- Known message types are processed per their defined handler.
- Unknown message types MUST be discarded and logged — never raised as uncaught exceptions, never processed optimistically.

### Gate Contract
- Gates MUST wait indefinitely for operator input.
- There is never an auto-approve path for merge, policy override, or security-sensitive continuation.

## Python Branding Constants

The `forge/branding.py` module provides canonical branding constants for the Forge platform:

python
# forge/branding.py
PLATFORM_NAME: str = "Forge"
PLATFORM_DESCRIPTION: str = "Trust-enforcement platform for AI agent operations"
VERSION_PREFIX: str = "forge"
AUDIT_STREAM_NAME: str = "TrustFlow"
IDENTITY_SCHEME: str = "CTX-ID"
POLICY_ZONE: str = "VTZ"
DATA_LABEL: str = "DTL"
MACHINE_IDENTITY: str = "TrustLock"


All user-facing strings, log prefixes, audit stream identifiers, and documentation references MUST use these constants — never hardcode platform names or subsystem identifiers as string literals elsewhere in the codebase.

## Build & Test

- Run all tests: `pytest`
- Run enforcement tests only: `pytest tests/enforcement/`
- Lint: `ruff check .`
- Type check: `mypy src/`
- Every PR MUST pass all enforcement tests before merge.
- Test coverage MUST include fail-closed paths for every enforcement subsystem.