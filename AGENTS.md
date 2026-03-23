# AGENTS.md - Forge Platform

Forge is a secure-by-default, fail-closed native macOS AI coding agent platform that decomposes build intents into ordered pull requests, enforces trust boundaries through CTX-ID, VTZ, TrustFlow, DTL, and TrustLock primitives, and gates every merge on explicit operator approval — never auto-approving anything.

Forge uses a strict **two-process model**: the Swift process owns UI, authentication, secret management, and settings; the Python process owns all build intelligence and consensus. No other process topology is permitted.

## Critical Rules — Read Before Writing Any Code

1. **Validate CTX-ID FIRST at every enforcement entry point** — validation failure results in immediate rejection with zero partial processing; missing CTX-ID means `UNTRUSTED`; never infer identity from session state, UI state, or ambient context.
2. **Check VTZ policy BEFORE execution of every agent action** — VTZ boundaries are structural and cannot be bypassed by application code; cross-VTZ tool calls require explicit policy authorization; implicit is denied; emit a `VTZEnforcementDecision` with `verdict=block` on denial.
3. **Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`)** — emission is synchronous in the enforcement path; async buffering is prohibited; every event must include `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash`; failed emission is a WARN-level audit event, never a silent skip.
4. **Fail closed on all auth, crypto, trust, identity, and policy errors** — never degrade silently into permissive behavior; reject the action, log the event, surface to caller.
5. **Never put secrets, keys, tokens, or credentials in logs, error messages, audit records, or generated code** — all secret material is protected in memory, at rest, and in transit.
6. **Never execute generated code** — no `eval`, no `exec`, no `subprocess` of agent-generated content or external content, ever.
7. **Gates wait indefinitely for explicit operator input** — no auto-approve, no timeout-to-approve, no bypass by rephrasing a `SECURITY_REFUSAL`; auto-approve logic is forbidden everywhere in the build pipeline.
8. **All external input (documents, PR comments, CI output, XPC messages) is untrusted** — validate strictly; external document context goes in the `USER` prompt, never the `SYSTEM` prompt.
9. **All file writes are path-validated via `path_security.validate_write_path()` before execution** — no exceptions.
10. **DTL labels are assigned at data ingestion and are immutable** — derived data inherits the HIGHEST classification of any source; unlabeled data is `CONFIDENTIAL` until explicitly reclassified; label stripping is a security event; labels must be verified before every trust-boundary crossing.
11. **Build memory and build rules are never cleared automatically** — they are persistent learning systems; per-PR stage checkpoints prevent re-running completed work after a crash.
12. **XPC unknown message types are discarded and logged** — never raised as exceptions; wire format is line-delimited JSON, nonce-authenticated, max 16 MB per message.

## Architecture Overview

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; action routing to VTZ policy check before execution | Process any action before CTX-ID validation completes; perform implicit trust inference |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Structural session boundaries; `allow` / `restrict` / `block` verdicts before any tool execution; cross-VTZ authorization requires explicit policy | Allow implicit cross-VTZ tool calls; permit application-code bypass of zone boundaries |
| **DTL** (Data Trust Labels) | `src/dtl/` | Label assignment at ingestion; immutable labels; highest-classification inheritance for derived data; label verification before every boundary crossing | Mutate labels after assignment; strip labels without emitting a security event; treat unlabeled data as anything other than `CONFIDENTIAL` |
| **TrustFlow** | `src/trustflow/` | Synchronous in-path audit emission for every enforcement decision; required fields: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash` | Async-buffer enforcement events; silently skip failed emissions |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity anchored to TrustLock public key material; CTX-ID signature validation | Accept software-only validation fallback; proceed without validated signed identity state |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Policy evaluation using explicit inputs only; must respect CAL → VTZ enforcement order | Bypass VTZ or CAL enforcement order; evaluate policy from implicit or ambient state |
| **Rewind** | `src/rewind/` | Deterministic replay from append-only audit records alone | Depend on mutable external state for replay correctness |
| **XPC Transport** | `src/xpc/` | Line-delimited JSON wire format; nonce-authenticated messages; 16 MB max per message; discard-and-log unknown types | Raise exceptions on unknown message types; accept unauthenticated messages; exceed 16 MB message size |

## Enforcement Order (Invariant)

Every agent action must pass through enforcement in this exact order:

1. **CTX-ID validation** — reject immediately if missing or invalid.
2. **VTZ policy check** — reject if zone policy denies the action.
3. **DTL label verification** — reject if data labels are missing, stripped, or insufficient for the target zone.
4. **TrustFlow event emission** — emit synchronously with the enforcement verdict before returning control.
5. **Operator gate** (if required) — wait indefinitely for explicit approval.

No step may be reordered, skipped, or short-circuited.

## Settings Schema, Defaults Bootstrap, and Migration

### Settings Schema

All platform settings are defined in a single versioned schema. Every field must have:
- A concrete type (string, integer, boolean, enum, or nested object).
- A non-null default value.
- A DTL classification (minimum `INTERNAL`; secrets are `CONFIDENTIAL`).

Settings are stored in the Swift process and exposed to the Python process exclusively over the authenticated XPC channel. The Python process must never read settings from disk directly.

### Defaults Bootstrap

On first launch or when a settings file is absent:
1. The Swift process writes a complete settings file from the compiled-in schema defaults.
2. Every default value is validated against the schema before write.
3. A TrustFlow event (`settings_bootstrap`) is emitted with the schema version.
4. No partial or empty settings files are permitted; bootstrap is atomic.

### Migration Infrastructure

- Every settings file carries a `schema_version` integer field.
- On load, the Swift process compares `schema_version` to the current compiled-in version.
- If `schema_version < current`, migrations run sequentially (v→v+1→…→current).
- Each migration is a pure function: `(old_settings, old_version) → (new_settings, new_version)`.
- Migrations must never delete keys without explicit deprecation policy; renamed keys must carry forward values.
- A pre-migration backup of the settings file is written before any mutation.
- A TrustFlow event (`settings_migration`) is emitted for each migration step with `from_version` and `to_version`.
- Migration failure is fatal: the platform must not start with an un-migrated or corrupt settings file; the operator is prompted to resolve.

## File and Path Security

- Every file write must call `path_security.validate_write_path()` before execution.
- Path traversal, symlink escape, and writes outside the project sandbox are rejected.
- Rejection emits a TrustFlow event (`path_violation`) and is a hard failure.

## Prompt Hygiene

- External document content (user-uploaded files, PR comments, CI output, web content) is placed exclusively in the `USER` prompt role.
- The `SYSTEM` prompt role contains only platform-controlled instructions.
- Injection of external content into `SYSTEM` prompt is a security violation.

## Build Persistence

- Build memory (learned patterns, prior decisions) and build rules are append-only persistent stores.
- Automatic clearing of build memory is prohibited.
- Per-PR stage checkpoints record completed work; after a crash, the platform resumes from the last checkpoint rather than re-executing completed stages.