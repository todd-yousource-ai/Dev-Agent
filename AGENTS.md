# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographic machine identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data via DTL, and emits an immutable TrustFlow audit stream — rejecting any action that cannot be authenticated, authorized, and audited.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — validation failure causes immediate rejection with zero partial processing.
2. TrustFlow events MUST be emitted synchronously in the enforcement path for every action outcome (`allow`, `restrict`, `block`) — async buffering is forbidden; failed emission is a WARN-level audit event that MUST be surfaced, never silently skipped.
3. VTZ policy MUST be checked BEFORE execution of any agent action — cross-VTZ tool calls require explicit policy authorization; implicit cross-boundary access is denied. Denial MUST emit a `VTZEnforcementDecision` record with `verdict=block`.
4. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to caller — `try/except/pass` is BANNED in enforcement code.
5. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, or cleartext payloads — error messages include `component`, `operation`, `failure_reason`, `ctx_id` only.
6. DTL labels are assigned at data ingestion and are immutable — derived data inherits the HIGHEST classification of any source; unlabeled data is treated as `CONFIDENTIAL` until explicitly reclassified.
7. CTX-ID tokens are IMMUTABLE once issued — rotation creates a new token and immediately invalidates the old one; expired or missing CTX-ID MUST be treated as `UNTRUSTED`; validation MUST use TrustLock public key, not software-only checks. Missing CTX-ID MUST never infer identity from session state, process state, or surrounding context.
8. Generated code is NEVER executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content; `shell=True` is forbidden in all subprocess calls.
9. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions.
10. External document content goes in the USER prompt, NEVER the SYSTEM prompt — all external input (documents, PR comments, CI output, XPC messages, generated content) is untrusted and validated before use.
11. `SECURITY_REFUSAL` output is NEVER bypassed by rephrasing or retrying with another provider — stop, gate for operator input, log.
12. Audit records are APPEND-ONLY, generated BEFORE execution, and MUST NOT contain secrets — replay of the full operational history MUST be possible from the audit stream alone.
13. Unknown XPC message types MUST be discarded and logged — never raise as uncaught exceptions, never process optimistically.
14. Gates wait indefinitely for operator input — there is NEVER any auto-approve, auto-merge, or implicit operator consent.

## Architecture Overview

Enforcement order: **CTX-ID validation → VTZ policy check → DTL label verification → Action execution → TrustFlow emission → Audit record**.

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Processes agent actions; calls CTX-ID validation first on every entry point; checks VTZ policy before execution; emits TrustFlow event for every outcome. | Must NOT execute actions before trust validation; must NOT perform partial processing on validation failure. |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Binds each agent session to exactly one VTZ; enforces policy boundary for all tool calls and data access. | Must NOT allow implicit cross-VTZ tool calls; must NOT permit boundary crossing without explicit policy authorization. |
| **TrustLock** (Cryptographic Identity) | `src/trustlock/` | Issues and validates CTX-ID tokens anchored to TrustLock public key; enforces token immutability and rotation semantics. | Must NOT accept software-only validation; must NOT allow token mutation after issuance. |
| **TrustFlow** (Audit Stream) | `src/trustflow/` | Emits synchronous, append-only audit events for every enforcement decision (`allow`, `restrict`, `block`). | Must NOT buffer asynchronously; must NOT silently drop failed emissions; must NOT include secrets in events. |
| **DTL** (Data Trust Labels) | `src/dtl/` | Assigns classification labels at data ingestion; enforces label immutability and inheritance (derived data inherits highest source classification). | Must NOT permit unlabeled data to cross trust boundaries; must NOT downgrade labels. |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Evaluates policy before execution for all MCP-routed actions. | Must NOT downgrade denials into warnings; must NOT execute before policy evaluation completes. |
| **Rewind** (Replay Engine) | `src/rewind/` | Supports full operational replay from the audit stream alone. | Must NOT depend on external state missing from the audit stream. |
| **Connector SDK** | `sdk/connector/` | Interfaces to external systems while preserving trust boundaries. | Must NOT bypass CAL, VTZ, or TrustFlow enforcement; must NOT establish unvalidated external connections. |

## Enforcement Contracts

### CTX-ID Validation
- Every public entry point calls `trustlock.validate_ctx_id(token)` before any other logic.
- Returns validated identity or raises `CTXIDValidationError`.
- Expired, malformed, or missing tokens → action rejected, `TrustFlow` event emitted with `verdict=block`, `failure_reason` logged.

### VTZ Policy Check
- After CTX-ID validation, `vtz.check_policy(ctx_id, action, target_resource)` is called.
- Cross-VTZ requests require explicit policy rule; absence of rule → deny.
- Denial emits `VTZEnforcementDecision` with fields: `ctx_id`, `vtz_id`, `action`, `target_resource`, `verdict` (`allow` | `block`), `policy_rule_id`, `timestamp`.

### DTL Label Propagation
- `dtl.assign_label(data, classification)` called at ingestion.
- `dtl.derive_label(sources)` returns the highest classification among all sources.
- Unlabeled data defaults to `CONFIDENTIAL`.
- Labels are immutable after assignment; reclassification requires explicit operator action and audit record.

### TrustFlow Event Emission
- `trustflow.emit(event)` called synchronously after every enforcement decision.
- Event fields: `event_id`, `ctx_id`, `vtz_id`, `action`, `verdict` (`allow` | `restrict` | `block`), `dtl_label`, `timestamp`, `component`, `operation`, `failure_reason` (if applicable).
- Emission failure → WARN-level audit event surfaced to caller; action outcome is NOT affected but failure is never silently dropped.

### Audit Record Format
- Append-only; generated BEFORE action execution.
- Fields: `record_id`, `event_id`, `ctx_id`, `vtz_id`, `action`, `verdict`, `dtl_label`, `timestamp`, `component`, `operation`, `failure_reason`.
- MUST NOT contain secrets, keys, tokens, or credentials.
- The full operational history MUST be replayable from audit records alone via `src/rewind/`.

## Cross-Subsystem Conflict Resolution Hierarchy

When multiple subsystems produce conflicting enforcement decisions, the following precedence applies (highest priority first):

1. **CTX-ID validation failure** — overrides all other decisions; action is rejected immediately.
2. **VTZ policy denial** — overrides DTL and MCP decisions; action is blocked.
3. **DTL classification violation** — overrides MCP and CAL permissive decisions; data access is denied.
4. **MCP policy denial** — overrides CAL-level permissions.
5. **CAL enforcement** — lowest priority; applies only when all higher-priority subsystems allow.

In all conflict cases: the MORE RESTRICTIVE decision wins. No subsystem may override a denial from a higher-priority subsystem. Every conflict resolution emits a TrustFlow event documenting all participating decisions.

## Ambiguity Resolutions

- **Ambiguity: What happens when TrustFlow emission fails during a block verdict?** Resolution: The block verdict stands (fail closed). The emission failure is logged as a WARN-level audit event via a secondary logging path. The action remains rejected.
- **Ambiguity: Can DTL labels be reclassified downward?** Resolution: Only via explicit operator gate action with full audit trail. Automated downgrade is forbidden.
- **Ambiguity: What if a VTZ policy rule and an MCP policy rule conflict?** Resolution: VTZ policy takes precedence per the conflict resolution hierarchy. MCP may further restrict within a VTZ but may never relax a VTZ denial.
- **Ambiguity: How are unknown or malformed XPC messages handled?** Resolution: Discard and log. Never raise as uncaught exceptions. Never process optimistically.
- **Ambiguity: What if an operator gate times out?** Resolution: Gates never time out. They wait indefinitely. There is no auto-approve path.
- **Ambiguity: What if derived data has sources with different DTL labels?** Resolution: Derived data inherits the HIGHEST (most restrictive) classification of any source.
- **Ambiguity: Is async TrustFlow emission ever acceptable for performance?** Resolution: No. Emission is always synchronous in the enforcement path. Performance is never a justification for async buffering of audit events.