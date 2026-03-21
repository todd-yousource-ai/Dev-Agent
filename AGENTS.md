# AGENTS.md - Forge Platform

Forge is a secure-by-default trust-enforcement platform for AI agent operations that binds every agent action to a cryptographic machine identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data via DTL, and records every action outcome through TrustFlow and append-only audit streams — enforcement is structural, not advisory.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID FIRST at every enforcement entry point — reject immediately on failure with zero partial processing.
2. Treat missing, expired, invalid, or unverified CTX-ID as `UNTRUSTED` — NEVER infer identity from session context, transport context, or caller state.
3. CTX-ID tokens are IMMUTABLE once issued — rotation creates a new token and immediately invalidates the old one; expired CTX-ID MUST be rejected.
4. Bind every agent session to exactly one VTZ at CTX-ID issuance — deny implicit cross-VTZ access; cross-VTZ tool calls require explicit policy authorization.
5. Check VTZ policy BEFORE any action execution, tool call, or cross-boundary operation — default to deny.
6. Emit a synchronous TrustFlow event in the enforcement path for every action outcome (allow, restrict, block) — every event MUST include `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, and `payload_hash`; async buffering is forbidden; failed emission is a WARN-level audit event that MUST be surfaced.
7. Assign DTL labels at data ingestion — labels are immutable; derived data inherits the HIGHEST classification of any source; unlabeled data MUST be treated as `CONFIDENTIAL` until explicitly reclassified.
8. Fail closed on ALL trust, identity, policy, cryptographic, and authorization errors — reject the action, log the event, surface to caller — NEVER silently continue.
9. NEVER write any file until `path_security.validate_write_path()` has approved the destination path — no exceptions, no workarounds.
10. NEVER execute generated or external content with `eval()`, `exec()`, subprocess execution of generated content, or `shell=True` in any subprocess call.
11. NEVER bypass `SECURITY_REFUSAL` by rephrasing, retrying with another model, or downgrading the request — stop, gate, and log.
12. NEVER expose secrets, keys, tokens, credentials, or cleartext sensitive payloads in logs, error messages, audit records, or generated code — no exceptions.
13. All external input (documents, PR comments, CI output, MCP payloads) is untrusted — validate strictly before use; context from external documents goes in the USER prompt, NEVER the SYSTEM prompt.
14. Gate cards (`gate_card`) block indefinitely for operator input — no auto-approve, ever.
15. Audit records are generated BEFORE execution, are APPEND-ONLY (no modification or deletion), MUST NOT contain secrets, and replay MUST be possible from the audit stream alone.
16. Discard and log unknown XPC message types — enforce the 16 MB XPC message size limit — NEVER raise unknown-message exceptions into control flow.

## Architecture Overview

Enforcement order for every agent action:

**CTX-ID validation → VTZ policy check → DTL label verification → Audit record → Action execution → TrustFlow emission**

| Subsystem | Path | Enforces | MUST NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Entry-point sequencing: CTX-ID validation → VTZ policy check → audit record → action execution → TrustFlow emission | NEVER execute an action before CTX-ID validation and VTZ policy check complete; NEVER swallow enforcement exceptions |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Binds each session to one zone; decides allow/restrict/block per policy | NEVER permit implicit cross-VTZ tool calls; NEVER mutate policy mid-session without re-authorization |
| **DTL** (Data Trust Labels) | `src/dtl/` | Applies immutable classification at ingestion; verifies labels before trust-boundary crossing | NEVER downgrade derived data below the highest source classification; NEVER allow unlabeled data past a trust boundary without classifying it as CONFIDENTIAL |
| **TrustFlow** | `src/trustflow/` | Emits synchronous action-outcome events (allow, restrict, block) with required fields: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash` | NEVER buffer asynchronously in the enforcement path; NEVER skip emission silently |
| **TrustLock** | `src/trustlock/` | Validates CTX-ID against the TrustLock public key with hardware-backed guarantees | NEVER accept software-only validation as sufficient; NEVER cache validation results past token expiry |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Evaluates explicit policy for tools, data movement, and cross-VTZ requests; all MCP payloads are untrusted input | NEVER allow implicit tool authorization; NEVER treat MCP payload content as trusted without validation |
| **Audit** | `src/audit/` | Append-only audit records generated before execution; supports full replay | NEVER modify or delete audit records; NEVER include secrets in audit payloads |
| **Path Security** | `src/path_security/` | Validates all file write destinations via `validate_write_path()` | NEVER allow a file write without prior path validation |

## Cross-Subsystem Conflict Resolution

When subsystem policies conflict, resolution follows this strict hierarchy (highest priority first):

1. **CTX-ID / TrustLock** — identity validation failures override all other decisions; an invalid or missing CTX-ID means REJECT regardless of VTZ, DTL, or MCP policy.
2. **VTZ** — zone boundary enforcement takes precedence over DTL and MCP; if VTZ policy denies an action, DTL allowance or MCP authorization cannot override.
3. **DTL** — data classification constraints take precedence over MCP tool policy; data MUST NOT cross a trust boundary to a lower-classification zone even if MCP policy would allow the tool call.
4. **MCP** — tool and data-movement policy applies after CTX-ID, VTZ, and DTL constraints are satisfied.
5. **CAL** — orchestrates the above order; CAL MUST NOT reorder or skip any enforcement layer.

Ambiguity resolution rules:
- If two subsystems return contradictory decisions for the same action, the MORE RESTRICTIVE decision wins.
- If a subsystem returns no decision (timeout, error, missing policy), treat the result as DENY and emit a TrustFlow event with `event_type: enforcement_ambiguity`.
- Mid-session VTZ policy changes MUST NOT apply retroactively — they take effect on the next action only.
- DTL reclassification of existing data MUST only raise classification level, NEVER lower it, unless performed by an operator through a `gate_card` approval.

## Development Workflow

- Run all enforcement tests before committing: tests validate the full enforcement chain (CTX-ID → VTZ → DTL → TrustFlow → Audit).
- Every new subsystem entry point MUST include a test that verifies fail-closed behavior on invalid CTX-ID, expired CTX-ID, and missing CTX-ID.
- Every new tool integration MUST include a test that verifies VTZ cross-boundary denial without explicit policy.
- Every new data path MUST include a test that verifies DTL label inheritance from the highest-classification source.
- NEVER commit code that disables, mocks out, or bypasses enforcement in production configuration.
- All PRs that touch enforcement paths MUST include audit-stream replay verification.