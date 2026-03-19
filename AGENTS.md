# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data via DTL, and emits an immutable TrustFlow audit stream — enforcing policy by default, not suggesting it.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID FIRST at every enforcement entry point — reject immediately on failure with zero partial processing; missing, expired, rotated, or unverifiable CTX-ID means `UNTRUSTED`; never infer identity from surrounding context.
2. Check VTZ policy before executing any action — deny all implicit cross-VTZ access; cross-VTZ tool calls require explicit policy authorization.
3. Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path — async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
4. Assign DTL labels at data ingestion; labels are immutable once assigned; derived data inherits the HIGHEST classification of any source; unlabeled data is treated as `CONFIDENTIAL` until explicitly reclassified; labels must never be stripped or downgraded without policy-controlled audit.
5. Fail closed on all trust, identity, policy, auth, and cryptographic errors — reject the action, log the event, surface to the caller; `try/except/pass` is BANNED in all enforcement code; never degrade into permissive behavior.
6. Secrets, keys, tokens, credentials, and cleartext sensitive payloads MUST never appear in logs, error messages, generated code, HTTP response bodies, or cleartext payloads — not in Python, not in Swift, not in test fixtures.
7. All external input (documents, PR comments, CI output, XPC messages, generated content) is UNTRUSTED — validate strictly before use; external document context goes in the USER prompt, never the SYSTEM prompt.
8. Generated code is NEVER executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content, no exceptions.
9. All file writes MUST pass `path_security.validate_write_path()` before execution — no shortcut, no bypass.
10. Gates wait indefinitely for operator input — no auto-approve, no timeout-to-approve, no auto-bypass, ever.
11. CTX-ID tokens are IMMUTABLE once issued — rotation creates a new token and immediately invalidates the old one; expired CTX-ID is rejected; missing CTX-ID means UNTRUSTED.
12. If a `SECURITY_REFUSAL` output is received, STOP — do not retry with rephrasing, do not route to another provider, do not auto-bypass; gate the action and log it.
13. Unknown XPC message types MUST be discarded and logged — never raised as exceptions, never processed speculatively.

## Architecture Overview

**Enforcement order for every agent action:** CTX-ID validation → VTZ policy check → DTL label verification → action execution → TrustFlow event emission → audit record.

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; VTZ policy before execution; TrustFlow emission after every outcome | Process any action before CTX-ID validation completes |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Structural trust boundaries; allow/restrict/block decisions before execution; explicit policy authorization for cross-VTZ tool calls | Permit implicit cross-VTZ access; allow application code to bypass zone boundaries |
| **DTL** (Data Trust Labels) | `src/dtl/` | Label assignment at ingestion; label inheritance on derivation; label verification at trust boundaries | Strip or downgrade labels without policy-controlled audit; allow unlabeled data to cross trust boundaries as anything other than CONFIDENTIAL |
| **TrustFlow** | `src/trustflow/` | Append-only audit stream; synchronous emission in the enforcement path; every event includes `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash` | Async-buffer enforcement events; silently drop failed emissions; allow mutation or deletion of emitted records |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity; CTX-ID validation against the TrustLock public key; hardware-backed identity verification | Accept software-only identity validation; skip signature verification; cache identity decisions beyond token TTL |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Explicit policy decisions for every tool invocation; allow/restrict/block evaluation before action execution | Act as advisory-only logic; permit execution without an explicit policy decision |
| **Rewind** (Forge Rewind) | `src/rewind/` | Full session replay from audit data alone; deterministic reconstruction of agent action sequences | Depend on hidden mutable external state; require live system state for replay |
| **SDK Connector** | `sdk/connector/` | Forge connector interface for external integrations; CTX-ID propagation across integration boundaries; DTL label preservation in transit | Allow unauthenticated connector sessions; strip DTL labels during data transfer |

## Shell Configuration Constants

The following constants MUST be defined and available in the shell environment for all Forge operations:

| Constant | Purpose |
|---|---|
| `FORGE_CTX_VALIDATION_MODE` | CTX-ID validation strictness (`strict` only in production; `strict` is the default) |
| `FORGE_VTZ_DEFAULT_POLICY` | Default VTZ policy when no explicit policy is found (`deny`) |
| `FORGE_DTL_DEFAULT_LABEL` | Default DTL classification for unlabeled data (`CONFIDENTIAL`) |
| `FORGE_TRUSTFLOW_EMIT_MODE` | TrustFlow emission mode (`sync` only; async is forbidden) |
| `FORGE_AUDIT_LOG_PATH` | Path to the append-only TrustFlow audit log |
| `FORGE_TRUSTLOCK_PUBKEY_PATH` | Path to the TrustLock public key for CTX-ID verification |

## Bundle Identifiers

| Bundle ID | Component | Purpose |
|---|---|---|
| `com.forge.platform.core` | Forge Core | Core enforcement engine |
| `com.forge.platform.cal` | CAL | Conversation Abstraction Layer |
| `com.forge.platform.vtz` | VTZ | Virtual Trust Zone enforcement |
| `com.forge.platform.dtl` | DTL | Data Trust Label management |
| `com.forge.platform.trustflow` | TrustFlow | Audit event emission |
| `com.forge.platform.trustlock` | TrustLock | Cryptographic identity and CTX-ID validation |
| `com.forge.platform.mcp` | MCP Policy Engine | Policy evaluation |
| `com.forge.platform.rewind` | Forge Rewind | Session replay engine |
| `com.forge.platform.connector` | SDK Connector | External integration interface |

## TrustFlow Wire Format

Every TrustFlow event MUST contain the following fields:

| Field | Type | Description |
|---|---|---|
| `event_id` | `string (UUID v4)` | Unique identifier for the event |
| `session_id` | `string (UUID v4)` | Session in which the event occurred |
| `ctx_id` | `string` | CTX-ID of the agent that triggered the action |
| `ts` | `string (ISO 8601)` | Timestamp of emission, set synchronously at enforcement time |
| `event_type` | `string enum` | One of: `allow`, `restrict`, `block`, `security_refusal`, `gate_pending`, `gate_resolved` |
| `payload_hash` | `string (SHA-256)` | Hash of the action payload; raw payload is never stored in the audit stream |
| `vtz_id` | `string` | VTZ in which the action was confined |
| `dtl_label` | `string` | DTL classification of the data involved |
| `policy_ref` | `string` | Reference to the MCP policy that produced the decision |

## Testing and Development

- All enforcement paths MUST have corresponding tests that verify fail-closed behavior.
- Tests MUST cover: CTX-ID missing, CTX-ID expired, CTX-ID rotated mid-session, VTZ boundary violation, DTL label escalation on derivation, TrustFlow emission failure, `SECURITY_REFUSAL` handling, unknown XPC message types.
- Test fixtures MUST never contain real secrets, keys, or tokens.
- Integration tests MUST verify the full enforcement order: CTX-ID → VTZ → DTL → execute → TrustFlow → audit.
- `path_security.validate_write_path()` MUST be tested with path traversal attacks, symlink attacks, and writes outside allowed directories.