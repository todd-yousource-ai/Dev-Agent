# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) — all enforced locally on macOS via a two-process Swift/Python architecture with XPC communication.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID first at every enforcement entry point and reject immediately on validation failure with no partial processing.
2. Check VTZ policy before executing any action and record `VTZEnforcementDecision` with `verdict=block` on denial.
3. Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) and never silently skip emission failures.
4. Treat missing CTX-ID as `UNTRUSTED` and never infer identity from ambient context, session state, or prior requests.
5. Treat all external input as untrusted, including documents, PR comments, CI output, XPC messages, and generated code. Context from external documents goes in the USER prompt, never the SYSTEM prompt.
6. Fail closed on all auth, crypto, identity, trust, and policy errors — reject the action, log the event, surface the failure to the caller with context, never silently continue.
7. Never execute generated code by `eval`, `exec`, dynamic import, shell execution, or subprocess invocation of generated content — under any circumstance.
8. Validate every file write with `path_security.validate_write_path()` before execution and reject invalid paths — no exceptions.
9. Keep secrets, keys, tokens, credentials, and cleartext sensitive payloads out of logs, errors, audit records, generated code, and error messages — not in any code path, not in any environment.
10. Preserve DTL immutability: assign labels at ingestion, inherit the highest classification in derived data, and treat unlabeled data as `CONFIDENTIAL` until explicitly reclassified.
11. Discard and log unknown XPC message types — never raise them as uncaught exceptions, never process them.
12. Never auto-approve gates: operator gates (`gate_card`) block indefinitely until an explicit human response is received — no timeout-based approval.
13. VTZ boundaries are structural and enforced — cross-VTZ tool calls require explicit policy authorization; implicit access is denied. VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.
14. Build memory and build rules are NEVER cleared automatically — they are persistent learning systems.
15. `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log.

## Architecture Overview

Forge runs as a two-process model: a **Swift process** (UI, authentication, Keychain, XPC server) and a **Python process** (build intelligence, consensus, enforcement logic). The enforcement order for every agent action is:

**CTX-ID validation → VTZ policy check → action execution → TrustFlow emission → audit record**

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; action routing through VTZ policy | Never process an action without CTX-ID validation first; never execute actions before identity and policy checks complete |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Boundary access decisions before execution; explicit policy authorization for cross-VTZ calls | Never allow implicit cross-VTZ calls; never permit boundary crossing without policy check |
| **DTL** (Data Trust Labels) | `src/dtl/` | Immutable label assignment at ingestion; highest-classification inheritance for derived data; label verification before boundary crossing | Never downgrade or strip labels without policy-controlled audit; never allow unlabeled data to cross boundaries without CONFIDENTIAL classification |
| **TrustFlow** | `src/trustflow/` | Immutable, append-only audit stream; synchronous emission in the enforcement path | Never buffer asynchronously in the enforcement path; never silently drop emission failures |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity and CTX-ID validation against TrustLock public key | Never accept software-only validation; never infer identity from ambient context |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Deterministic and explainable policy evaluation | Never make unenforced advisory-only decisions; never produce non-deterministic policy results |
| **Rewind** (Forge Rewind) | `src/rewind/` | Replay from append-only audit records | Never depend on hidden mutable external state for replay |

## TrustFlow Event Wire Format

Every TrustFlow event MUST include the following fields:

| Field | Type | Description |
|---|---|---|
| `event_id` | `string (UUID)` | Unique identifier for this event |
| `session_id` | `string (UUID)` | Session in which the event occurred |
| `ctx_id` | `string` | CTX-ID of the agent whose action produced this event |
| `ts` | `string (ISO 8601)` | Timestamp of event emission |
| `event_type` | `string` | One of: `action_allow`, `action_restrict`, `action_block`, `vtz_enforcement`, `dtl_violation`, `identity_failure`, `policy_error` |
| `payload_hash` | `string (SHA-256)` | Hash of the event payload for integrity verification |

TrustFlow events are append-only and immutable. No event is ever deleted, modified, or reordered after emission.

## VTZ Enforcement Decision Record

When VTZ policy denies an action, the enforcement layer MUST record a `VTZEnforcementDecision` with:
- `verdict`: one of `allow`, `restrict`, `block`
- `ctx_id`: the requesting agent's CTX-ID
- `source_vtz`: the agent's current VTZ
- `target_vtz`: the VTZ the action would cross into
- `policy_rule`: the specific policy rule that produced the verdict
- `ts`: timestamp of the decision

## Structured Logging Subsystem with Privacy Annotations

All log entries MUST be structured (JSON format) and MUST include privacy annotations on every field.

### Privacy Annotation Levels

| Annotation | Meaning | Retention | May appear in external reports |
|---|---|---|---|
| `@public` | No privacy restriction | Unlimited | Yes |
| `@internal` | Internal operational data | Per retention policy | No |
| `@confidential` | DTL-CONFIDENTIAL or higher | Per DTL policy | Never |
| `@secret` | Keys, tokens, credentials | NEVER logged | Never |

### Structured Log Entry Fields

Every log entry MUST include:

| Field | Privacy | Type | Description |
|---|---|---|---|
| `log_id` | `@public` | `string (UUID)` | Unique log entry identifier |
| `ts` | `@public` | `string (ISO 8601)` | Timestamp of log emission |
| `level` | `@public` | `string` | One of: `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL` |
| `subsystem` | `@public` | `string` | Originating subsystem (`cal`, `vtz`, `dtl`, `trustflow`, `trustlock`, `mcp`, `rewind`) |
| `ctx_id` | `@internal` | `string` | CTX-ID of the agent in context (or `NONE` if pre-validation) |
| `vtz_id` | `@internal` | `string` | Current VTZ identifier |
| `message` | `@internal` | `string` | Human-readable log message — MUST NOT contain secrets, keys, tokens, or credentials |
| `event_ref` | `@internal` | `string (UUID) or null` | Reference to associated TrustFlow `event_id` if applicable |
| `dtl_label` | `@internal` | `string` | DTL classification of the data context — derived data inherits highest source classification |
| `error_code` | `@public` | `string or null` | Structured error code if this is an error entry |
| `privacy_annotations` | `@public` | `object` | Map of field name → privacy annotation for every field in this entry |

### Logging Rules

1. Every log entry MUST include a `privacy_annotations` map declaring the privacy level of every field present in that entry.
2. Fields annotated `@secret` MUST never be written to any log sink — the logging subsystem MUST strip or reject them before serialization.
3. Fields annotated `@confidential` MUST only be written to log sinks that enforce DTL-CONFIDENTIAL access controls.
4. Log entries associated with a TrustFlow event MUST include the `event_ref` field pointing to the TrustFlow `event_id`.
5. Log entries MUST inherit the highest DTL classification of any data they reference — the `dtl_label` field reflects this.
6. The logging subsystem MUST fail closed: if a log entry cannot be written (sink unavailable, serialization error), the originating action MUST be blocked and a TrustFlow event emitted recording the logging failure.
7. Log sinks MUST be append-only within a session — no log entry is ever deleted or modified after emission.
8. The structured logging subsystem MUST validate that no `@secret`-annotated data appears in `message`, `error_code`, or any other string field before emission — this validation is enforced at serialization time, not as an advisory.
9. Cross-VTZ log aggregation MUST enforce VTZ boundary policy — logs from one VTZ are not readable by another VTZ without explicit policy authorization.
10. All log entries from the XPC boundary MUST include the originating process identifier (Swift or Python) as an additional `@internal` field named `xpc_origin`.