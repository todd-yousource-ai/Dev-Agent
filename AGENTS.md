# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that guarantees every agent action is identity-bound (CTX-ID), policy-checked (VTZ), data-classified (DTL), and audit-recorded (TrustFlow) before execution proceeds.

## Naming Conventions and Glossary

| Term | Canonical Name | Definition |
|---|---|---|
| **CTX-ID** | Context Identity Token | Immutable, cryptographically issued identity token bound to every agent session. Validated at every enforcement entry point. Missing CTX-ID means the actor is `UNTRUSTED`. Rotation creates a new token and immediately invalidates the old one. |
| **VTZ** | Virtual Trust Zone | Policy boundary that defines what actions a session may perform. Every agent action MUST be checked against VTZ policy before execution. Implicit cross-VTZ access is always denied. Sessions are exactly bound to a single VTZ. |
| **DTL** | Data Trust Label | Classification label assigned at data ingestion and immutable thereafter. Derived data inherits the HIGHEST classification of any source. Unlabeled data is treated as `CONFIDENTIAL`. Labels MUST be verified before any trust-boundary crossing. |
| **TrustFlow** | TrustFlow Audit Stream | Synchronous audit event emitted inline in the enforcement path for every action outcome (allow, restrict, block). Async buffering is forbidden. Every event MUST include: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash` (SHA-256). |
| **TrustLock** | TrustLock Machine Identity | Cryptographic machine identity subsystem. Validates CTX-ID tokens using the TrustLock public key. Rejects expired or rotated tokens. MUST NOT use software-only validation when hardware-backed validation is available. |
| **CAL** | Conversation Abstraction Layer | Enforcement entry point that orchestrates the full enforcement sequence: CTX-ID validation → VTZ policy check → action execution → TrustFlow emission → DTL verification on data crossing trust boundaries. |
| **MCP** | MCP Policy Engine | Policy evaluation integration point. Evaluates action requests against registered policies before execution is permitted. |
| **SECURITY_REFUSAL** | Security Refusal Signal | Terminal output from any enforcement check indicating the action is denied. On receipt: stop, do not retry, do not rephrase, do not route to another provider. Gate and log. |
| **XPC** | XPC Message Transport | Inter-process communication layer between the Swift shell and Python backend. Unknown message types MUST be discarded and logged — never raised as uncaught exceptions, never treated as trusted input. |

## Critical Rules — Read Before Writing Any Code

1. **CTX-ID first.** Every enforcement entry point MUST call CTX-ID validation FIRST. Validation failure means immediate rejection with zero partial processing.
2. **VTZ before execution.** Every agent action MUST be checked against VTZ policy BEFORE execution. Implicit cross-VTZ access is always denied.
3. **TrustFlow inline.** Every action outcome (allow, restrict, block) MUST emit a TrustFlow event synchronously in the enforcement path. Every event MUST include `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, and `payload_hash` (SHA-256). Async buffering is forbidden.
4. **Fail closed.** All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to the caller. Never silently continue.
5. **No identity inference.** Treat missing CTX-ID as `UNTRUSTED`. Never infer identity from process state, UI state, or execution context.
6. **DTL immutability.** DTL labels are assigned at data ingestion and are IMMUTABLE. Derived data inherits the HIGHEST classification of any source. Unlabeled data is treated as `CONFIDENTIAL`. Any label stripping event MUST be audited.
7. **No secrets in output.** Secrets, keys, tokens, credentials, and cleartext sensitive payloads MUST never appear in logs, error messages, generated code, or cleartext payloads — not in any environment.
8. **No execution of generated content.** Never execute generated or external content with `eval()`, `exec()`, shell interpolation, `shell=True`, or subprocess execution of generated content.
9. **Write-path validation.** All file writes MUST pass `path_security.validate_write_path()` before any write operation.
10. **Gates never auto-approve.** Gates MUST wait indefinitely for operator input. No auto-approve, no auto-merge, no bypass of `SECURITY_REFUSAL`.
11. **XPC unknown messages.** Unknown XPC message types MUST be discarded and logged. Never raise as uncaught exceptions. Never treat as trusted input.
12. **CTX-ID token immutability.** CTX-ID tokens are IMMUTABLE once issued. Rotation creates a new token and immediately invalidates the old one.
13. **External input is untrusted.** All external input (documents, PR comments, CI output, agent payloads) is UNTRUSTED. Validate strictly before use. Context from external documents goes in the USER prompt, never the SYSTEM prompt.
14. **SECURITY_REFUSAL is terminal.** If a SECURITY_REFUSAL output is returned, stop. Do not retry. Do not rephrase. Do not route to another provider. Gate and log.

## Architecture Overview

Forge is a two-process architecture with strict separation of concerns:

- **Swift shell** owns: UI, Touch ID, Keychain, XPC transport, and process lifecycle.
- **Python backend** owns: consensus generation, pipeline orchestration, GitHub integration, ledger, and document processing.

Enforcement order for every agent action:

**CTX-ID validation → VTZ policy check → Action execution → TrustFlow emission → DTL label verification on any data crossing a trust boundary**

### Subsystem Map

| Path | Subsystem | Enforces | MUST NOT Do |
|---|---|---|---|
| `src/cal/` | Conversation Abstraction Layer (CAL) | CTX-ID validation at every entry point; orchestrates full enforcement sequence | Never process an action without CTX-ID validation completing first; never silently continue on TrustFlow emission failure |
| `src/dtl/` | Data Trust Labels (DTL) | Data classification at ingestion; label inheritance (highest source wins); label verification at trust boundaries | Never strip or mutate a label without audit; never treat unlabeled data as public; never permit unlabeled outbound data without treating it as `CONFIDENTIAL` |
| `src/trustflow/` | TrustFlow Audit Stream | Synchronous audit event emission for every action outcome; required fields: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash` (SHA-256) | Never buffer asynchronously; never emit events missing required fields; never silently drop events |
| `src/vtz/` | Virtual Trust Zones (VTZ) | Session-to-VTZ binding; cross-zone authorization; policy evaluation before action execution | Never allow implicit cross-VTZ access; never allow application code to bypass VTZ boundaries |
| `src/trustlock/` | TrustLock Machine Identity | Cryptographic CTX-ID validation using TrustLock public key; token expiry and rotation enforcement | Never use software-only validation when hardware-backed validation is available; never accept expired or rotated tokens |
| `src/mcp/` | MCP Policy Engine | Policy evaluation of action requests against registered policies | Never bypass policy evaluation; never treat policy evaluation failure as a pass |

### TrustFlow Event Wire Format

Every TrustFlow event MUST contain the following fields:

| Field | Type | Description |
|---|---|---|
| `event_id` | `string` (UUID) | Unique identifier for this event |
| `session_id` | `string` | Session identifier |
| `ctx_id` | `string` | CTX-ID of the actor |
| `ts` | `string` (ISO 8601) | Timestamp of event emission |
| `event_type` | `string` | One of: `allow`, `restrict`, `block`, `error` |
| `payload_hash` | `string` (SHA-256 hex) | SHA-256 hash of the action payload |

Events missing any required field MUST be rejected by the TrustFlow subsystem. Events MUST NOT be emitted with placeholder or empty values for required fields.