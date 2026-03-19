# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographic identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data via DTL, and emits an immutable TrustFlow audit stream — rejecting any action that cannot be authenticated, authorized, and audited.

## Critical Rules - Read Before Writing Any Code

1. Validate `CTX-ID` first at every enforcement entry point and reject immediately on validation failure with zero partial processing.
2. Check `VTZ` policy before any action execution, cross-boundary operation, tool call, or data movement, and deny implicitly unless policy explicitly authorizes it.
3. Emit a synchronous `TrustFlow` event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path — async buffering is forbidden; never silently skip emission on failure.
4. Treat all unlabeled data as `CONFIDENTIAL`, enforce immutable `DTL` labels from ingestion onward, and verify labels before any trust-boundary crossing. Derived data inherits the HIGHEST classification of any source.
5. Fail closed on all authentication, cryptographic, identity, trust, and policy errors — reject the action, log the event, surface to caller — never degrade into permissive behavior or silently continue.
6. Never hardcode secrets, tokens, credentials, or cryptographic material, and never expose them in logs, errors, audit records, or generated code.
7. Treat all external input as untrusted, including documents, PR comments, CI output, XPC messages, and generated content. Validate strictly before use. Context from external documents goes in the USER prompt, never the SYSTEM prompt.
8. Never execute generated code or external content — no `eval()`, no `exec()`, no `subprocess` of generated content. `shell=True` is banned.
9. Validate every file write path with `path_security.validate_write_path()` before writing anything to disk.
10. Respect human gates absolutely: `gate_card` waits indefinitely for operator input — no auto-approve ever.
11. If output contains `SECURITY_REFUSAL`, stop, gate, and log. Never retry by rephrasing or switching providers to bypass it.
12. Discard and log unknown XPC message types — never raise them as exceptions; never infer trust from message context alone.
13. CTX-ID tokens are immutable once issued. Expired or missing CTX-ID MUST be treated as UNTRUSTED — never infer identity from context. Validation MUST use TrustLock public key.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → VTZ policy check → Action execution → TrustFlow emission → DTL label verification on output**.

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; routes actions through VTZ policy before execution | Never process an action without CTX-ID validation; never skip TrustFlow emission; never perform partial action processing before trust checks |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Structural trust boundaries binding each agent session to exactly one VTZ; cross-VTZ tool calls require explicit policy authorization | Never allow implicit cross-VTZ tool calls; never treat boundaries as advisory; application code cannot bypass enforcement |
| **TrustFlow** | `src/trustflow/` | Append-only audit stream for every security-relevant action; forensic replay capability; each event MUST contain `{ event_id, session_id, ctx_id, ts, event_type, payload_hash }` | Never emit asynchronously in the enforcement path; never buffer events; never drop events on failure |
| **DTL** (Data Trust Labels) | `src/dtl/` | Immutable classification labels assigned at data ingestion; label inheritance on derived data (highest classification wins) | Never strip labels without audit; never treat unlabeled data as public; never permit unlabeled or stripped data to cross trust boundaries without audit and policy control |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity and CTX-ID validation against TrustLock public key; hardware-anchored validation | Never accept software-only validation; never issue mutable CTX-ID tokens; never infer identity from context |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Explicit policy decisions for all enforcement gates; evaluates authorization for cross-VTZ operations, tool calls, and data movement | Never allow implicit authorization; never fall back to permissive defaults when policy evaluation fails |

## TrustFlow Event Wire Format

Every TrustFlow event MUST be a structured record with these fields:

| Field | Type | Description |
|---|---|---|
| `event_id` | `string (UUID)` | Unique identifier for this audit event |
| `session_id` | `string` | Session identifier for the agent operation |
| `ctx_id` | `string` | The validated CTX-ID of the acting agent |
| `ts` | `string (ISO 8601)` | Timestamp of the event |
| `event_type` | `enum: allow \| restrict \| block` | Outcome of the enforcement decision |
| `payload_hash` | `string (SHA-256)` | Cryptographic hash of the action payload — never the payload itself |

## Shell Logging Subsystem

All shell-level diagnostics MUST route through the structured logging subsystem before any enforcement components initialize.

- Shell log entries MUST include `{ ts, level, subsystem, ctx_id_if_available, message_hash }` — never raw message content containing secrets or payloads.
- Diagnostics bootstrap MUST complete before CAL, VTZ, TrustFlow, DTL, TrustLock, or MCP subsystems accept any input.
- Bootstrap failure MUST fail closed: if the logging subsystem cannot initialize, no enforcement subsystem starts and the platform rejects all actions.
- Log output MUST be append-only and tamper-evident; log rotation MUST NOT delete entries before they are persisted to the TrustFlow audit stream.
- `level` MUST be one of: `DIAG`, `INFO`, `WARN`, `ERROR`, `FATAL`.
- `subsystem` MUST identify the originating component (e.g., `cal`, `vtz`, `trustflow`, `dtl`, `trustlock`, `mcp`, `bootstrap`).

## Enforcement Invariants

- No action proceeds without CTX-ID validation.
- No cross-VTZ operation proceeds without explicit MCP policy authorization.
- No data crosses a trust boundary without DTL label verification.
- No enforcement outcome exists without a corresponding TrustFlow event.
- No subsystem initializes before the shell logging/diagnostics bootstrap completes.
- All failures are closed, logged, and surfaced — never silent, never permissive.