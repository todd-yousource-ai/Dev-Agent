# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), constrains it within a Virtual Trust Zone (VTZ), labels all data via DTL, and emits an immutable TrustFlow audit stream — failing closed on any violation.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — before any processing, before any side effect.
2. CTX-ID validation failure MUST result in immediate rejection with no partial processing — fail closed, log, surface.
3. Missing, invalid, expired, or unverifiable CTX-ID MUST be treated as `UNTRUSTED` — never infer identity from ambient context.
4. Every agent action MUST be checked against VTZ policy BEFORE execution; implicit cross-VTZ calls are denied.
5. Every action outcome (`allow`, `restrict`, `block`) MUST emit a synchronous TrustFlow event — async buffering is forbidden in the enforcement path.
6. TrustFlow emission failure is a WARN-level audit event that MUST be surfaced — never silently skipped.
7. All trust, identity, policy, cryptographic, and authorization failures MUST fail closed: reject the action, log the event, surface to caller.
8. Secrets, keys, tokens, credentials, and cleartext sensitive payloads MUST never appear in logs, error messages, or generated code.
9. All external input (documents, PR comments, CI output, XPC messages, user prompts) is untrusted — validate strictly before use.
10. Generated code is never executed by the agent — no `eval()`, no `exec()`, no subprocess of generated content.
11. Unlabeled data MUST be treated as `CONFIDENTIAL` until explicitly reclassified; DTL labels are immutable after assignment and MUST never be stripped or downgraded without explicit policy-controlled auditing.
12. `SECURITY_REFUSAL` output is never bypassed by rephrasing or retrying with another provider — stop, gate, log.
13. Gates wait indefinitely for operator input — no auto-approve, ever.
14. Validate every file write path with `path_security.validate_write_path()` before writing to disk.
15. Discard and log unknown XPC message types — never raise them as uncaught exceptions.

## Architecture Overview

### Subsystem Map (enforcement order)

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity anchored to TPM; issues and validates CTX-ID tokens against TrustLock public key | Never perform software-only CTX-ID validation; never store private keys outside hardware-backed storage |
| **CTX-ID** | (issued by TrustLock, validated everywhere) | Immutable identity binding per session; validated against TrustLock public key | Never modify fields after issuance; never infer identity from context when CTX-ID is missing |
| **VTZ** | `src/vtz/` | Structural trust zone boundaries; binds each agent session to exactly one VTZ at CTX-ID issuance time | Never allow application code to bypass zone enforcement; never apply policy changes mid-session; never allow implicit cross-VTZ tool calls |
| **CAL** | `src/cal/` | Conversation Abstraction Layer — orchestrates CTX-ID validation → VTZ policy check → action execution → TrustFlow emission | Never process an action without completing this full sequence; never skip any step; never perform partial execution before enforcement completes |
| **DTL** | `src/dtl/` | Data Trust Labels — assigns classification at ingestion, enforces label inheritance (highest wins), verifies before cross-boundary transfer | Never strip labels; never allow unlabeled data to cross trust boundaries without treating it as `CONFIDENTIAL`; never downgrade without policy-controlled audit |
| **TrustFlow** | `src/trustflow/` | Synchronous audit/event emission on the enforcement path | Never buffer asynchronously; never drop events silently |
| **MCP** | `src/mcp/` | MCP Policy Engine — makes explainable, binding policy decisions before execution | Never act as advisory-only logic; every decision MUST be enforced |
| **Rewind** | `src/rewind/` | Replay engine — supports deterministic replay from append-only audit data | Never depend on mutable external state for reconstruction |
| **Forge Connector SDK** | `sdk/connector/` | External integrations — preserves the same enforcement semantics as core services | Never weaken CTX-ID, VTZ, DTL, or TrustFlow guarantees at the integration boundary |

### TrustFlow Event Wire Format

Every TrustFlow event MUST include:

| Field | Type | Description |
|---|---|---|
| `event_id` | `string (UUID v4)` | Unique identifier for this event |
| `session_id` | `string (UUID v4)` | Session that produced the event |
| `ctx_id` | `string` | CTX-ID of the acting agent |
| `ts` | `string (ISO 8601, UTC)` | Timestamp of event emission |
| `event_type` | `string enum` | One of: `action.allow`, `action.restrict`, `action.block`, `enforcement.failure`, `audit.warn` |
| `vtz_id` | `string` | VTZ in which the action occurred |
| `dtl_label` | `string` | DTL classification of affected data |
| `payload_hash` | `string (SHA-256)` | Integrity hash of the event payload |
| `outcome` | `string enum` | `allow`, `restrict`, `block` |

### Enforcement Sequence (CAL pipeline)

Every action MUST pass through this sequence in order:


1. CTX-ID Validation   → reject if invalid, expired, or missing
2. VTZ Policy Check     → reject if action violates zone boundary or policy
3. DTL Label Verify     → reject if data label forbids the operation
4. Action Execution     → execute only after steps 1-3 succeed
5. TrustFlow Emission   → emit synchronous audit event with outcome


No step may be reordered. No step may be skipped. Failure at any step MUST fail closed and emit a TrustFlow event recording the failure.

### CTX-ID Lifecycle

- **Issuance**: TrustLock issues a CTX-ID token bound to the agent session and exactly one VTZ. The token is signed with TrustLock's hardware-backed private key.
- **Validation**: Every subsystem validates CTX-ID against TrustLock's public key before processing.
- **Immutability**: CTX-ID fields MUST NOT be modified after issuance.
- **Expiry**: Expired CTX-ID tokens MUST be rejected — never silently renewed.

### DTL Label Rules

- Labels are assigned at data ingestion and are immutable after assignment.
- Unlabeled data is classified as `CONFIDENTIAL`.
- When data from multiple sources is combined, the highest classification wins (label inheritance).
- Cross-boundary data transfer MUST verify DTL labels; transfer is denied if the destination VTZ policy does not permit the label.

### VTZ Binding Rules

- Each agent session is bound to exactly one VTZ at CTX-ID issuance.
- VTZ binding MUST NOT change mid-session.
- Cross-VTZ communication MUST be explicit, policy-checked, and audited via TrustFlow.
- Implicit cross-VTZ calls are always denied.

## File and Path Safety

- Every file write MUST be validated with `path_security.validate_write_path()` before execution.
- Path traversal attempts MUST be rejected and logged.

## XPC Message Handling

- Unknown XPC message types MUST be discarded and logged.
- Unknown XPC message types MUST NOT raise uncaught exceptions.

## Security Refusal Protocol

- When any provider returns `SECURITY_REFUSAL`, the agent MUST stop, gate for operator review, and log the refusal.
- `SECURITY_REFUSAL` MUST NOT be bypassed by rephrasing the request or retrying with another provider.