# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that cryptographically binds every agent action to a verified machine identity (CTX-ID), enforces policy boundaries (VTZ), labels data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) — all fail-closed, all auditable, no exceptions.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID **first** at every enforcement entry point — before any other processing; validation failure MUST result in immediate rejection with no partial execution.
2. Check VTZ policy before execution of every agent action and emit a `VTZEnforcementDecision` record with `verdict=block` on denial; cross-VTZ tool calls require explicit policy authorization or they are denied.
3. Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path — asynchronous buffering is **not permitted**; emission failures MUST NOT be silently skipped.
4. Treat missing CTX-ID as `UNTRUSTED` and MUST never infer identity from ambient context, session state, or UI state; expired CTX-ID MUST be rejected; CTX-ID tokens are immutable once issued; rotation creates a new token and the old one is invalidated immediately.
5. Fail **closed** on all trust, identity, policy, authentication, authorization, and cryptographic errors — reject the action, log the event, surface to caller — never silently continue, never degrade into permissive behavior.
6. Treat all external input as untrusted — documents, PR comments, CI output, XPC payloads, and generated code metadata — and validate strictly before use; context from external documents goes in the USER prompt, never the SYSTEM prompt.
7. Never execute generated code via `eval`, `exec`, `subprocess`, shell execution, dynamic subprocess input, or equivalent runtime interpretation — generated code is never executed by the agent.
8. Validate every file write path with `path_security.validate_write_path()` before the write occurs and reject invalid paths before any filesystem mutation.
9. Never put secrets, keys, tokens, credentials, or cleartext sensitive payloads in logs, error messages, audit records, TrustFlow payloads, or generated code.
10. Gates MUST wait indefinitely for operator input — no auto-approve, no bypass, no inferred approval from prior state, ever.
11. Discard and log unknown XPC message types; never raise them as uncaught exceptions and never process them speculatively.
12. Build memory and build rules are persistent learning systems and MUST never be cleared automatically, implicitly, or on crash recovery.
13. DTL labels are assigned at data ingestion, are immutable thereafter, and derived data inherits the **highest** classification of any source; unlabeled data is treated as `CONFIDENTIAL` and MUST NOT cross trust boundaries as low sensitivity.
14. `try/except/pass` is **banned** in all enforcement code; every exception MUST be caught with explicit handling, logging, and caller notification.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → VTZ policy check → Action execution → TrustFlow emission → Audit record**.

| Subsystem | Path | Enforces | MUST NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Entry-point validation; calls CTX-ID check first, VTZ policy second, emits TrustFlow on every outcome | MUST NOT process any action before CTX-ID validation completes |
| **TrustFlow** | `src/trustflow/` | Immutable, append-only audit stream with globally unique event IDs and synchronous emission in the enforcement path | MUST NOT buffer asynchronously; MUST NOT silently drop failed emissions |
| **CTX-ID / TrustLock** | `src/trustlock/` | Cryptographic machine identity anchored to TPM/Secure Enclave; token issuance, validation, rotation, and revocation; validates CTX-ID against the TrustLock public key | MUST NOT rely on software-only validation; MUST NOT accept expired or missing CTX-ID |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Structural policy boundaries; decides `allow`/`restrict`/`block` before execution; emits `VTZEnforcementDecision` with `verdict` field | MUST NOT allow implicit cross-VTZ actions; MUST NOT treat boundaries as advisory |
| **DTL** (Data Trust Labels) | `src/dtl/` | Immutable sensitivity labels assigned at ingestion; enforces label inheritance (highest classification wins) | MUST NOT allow unlabeled data to cross trust boundaries as low sensitivity; MUST NOT permit label downgrade after assignment |
| **MCP Policy Engine** | `src/mcp/` | Control-plane policy decisions; enforces policy as binding enforcement | MUST NOT act as advisory-only; MUST NOT permit policy bypass |

## Structured Logging Subsystem

Path: `src/logging/`

### Purpose

All log entries produced by Forge components MUST pass through the structured logging subsystem, which enforces privacy annotations, deterministic field layout, and TrustFlow integration.

### Log Entry Schema

Every log entry MUST be a structured record with the following fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `event_id` | `string` (UUID v4) | MUST | Globally unique identifier for this log entry |
| `timestamp` | `string` (ISO 8601, UTC) | MUST | Time of emission; MUST be UTC |
| `level` | `enum` (`TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`) | MUST | Severity level |
| `subsystem` | `string` | MUST | Originating subsystem identifier (e.g., `cal`, `vtz`, `trustflow`, `trustlock`, `dtl`, `mcp`) |
| `ctx_id` | `string` | MUST when available; `"UNTRUSTED"` when missing | The CTX-ID of the agent or caller associated with this event |
| `vtz_zone` | `string` | MUST when in VTZ scope | The VTZ zone identifier for the current execution context |
| `message` | `string` | MUST | Human-readable description of the event |
| `privacy` | `enum` (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`) | MUST | Privacy annotation for this log entry; determines downstream handling |
| `fields` | `map<string, AnnotatedValue>` | MAY | Additional structured key-value pairs; every value MUST carry a privacy annotation |
| `trustflow_event_id` | `string` (UUID v4) | MUST when log corresponds to a TrustFlow event | Correlation ID linking to the TrustFlow audit record |
| `dtl_label` | `string` | MUST | DTL classification of this log entry; defaults to `CONFIDENTIAL` if unset; derived from highest classification of any source data referenced |

### AnnotatedValue Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `value` | `any` | MUST | The payload value |
| `privacy` | `enum` (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`) | MUST | Privacy classification of this specific value |
| `redact_for` | `list<string>` | MAY | List of output contexts where this value MUST be redacted (e.g., `["external_audit", "debug_console"]`) |

### Privacy Annotation Rules

1. Every log field MUST carry an explicit privacy annotation; unannotated fields MUST be rejected at emission time — the logger MUST NOT emit a record with unannotated fields.
2. Privacy annotations are immutable once assigned; downstream processors MUST NOT downgrade a privacy annotation.
3. When a log entry references data from multiple sources, the entry-level `privacy` field MUST be set to the **highest** classification of any referenced source, consistent with DTL inheritance rules.
4. Fields annotated `RESTRICTED` MUST be redacted from all outputs except the encrypted audit archive; fields annotated `CONFIDENTIAL` MUST be redacted from external-facing outputs.
5. Secrets, keys, tokens, credentials, and cleartext sensitive payloads MUST never appear in any log field regardless of annotation — the logger MUST reject entries containing detected secret patterns before emission.
6. The structured logger MUST expose a `redact(entry, output_context) -> RedactedEntry` function that strips or masks fields based on their `privacy` and `redact_for` annotations for the given output context.

### Emission Rules

1. Log entries associated with enforcement decisions (`allow`, `restrict`, `block`) MUST include a valid `trustflow_event_id` linking to the synchronous TrustFlow event.
2. Log emission failures MUST fail closed: if the logger cannot write the entry, the originating operation MUST be halted and an error surfaced to the caller — logs MUST NOT be silently dropped.
3. Log entries MUST be emitted synchronously in enforcement paths; asynchronous emission is permitted only for `TRACE` and `DEBUG` levels outside enforcement paths.
4. All log sinks (file, network, console) MUST apply the `redact()` function for their output context before writing; no sink may write an unredacted `RESTRICTED` or `CONFIDENTIAL` field to an unauthorized destination.

### Integration Contracts

- **CAL → Logger**: CAL MUST call the structured logger for every enforcement entry-point event, passing the active `ctx_id` and `vtz_zone`.
- **TrustFlow → Logger**: TrustFlow events MUST include a `trustflow_event_id` that the logger cross-references; the logger MUST reject enforcement-path log entries that lack a corresponding `trustflow_event_id`.
- **DTL → Logger**: The logger MUST query DTL for the classification of any referenced data and set `dtl_label` accordingly; if DTL classification is unavailable, `dtl_label` defaults to `CONFIDENTIAL`.
- **TrustLock → Logger**: The logger MUST validate that `ctx_id` is a currently valid CTX-ID before including it in the log entry; if validation fails, `ctx_id` MUST be set to `"UNTRUSTED"` and the entry `privacy` MUST be elevated to `RESTRICTED`.

### Banned Patterns

- `print()`, `NSLog()`, `os_log()` without structured wrapper — all log output MUST go through the structured logging subsystem.
- `try/except/pass` in any logging code path — every exception MUST be caught with explicit handling.
- String interpolation of secrets or tokens into log messages — the logger MUST reject entries matching secret patterns.
- Logging raw request/response bodies without privacy annotation — every field MUST be annotated.