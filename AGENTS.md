# AGENTS.md - Forge Platform

Forge is a security-first enforcement platform and native macOS AI coding agent that validates CTX-ID, enforces VTZ policy, preserves DTL labels, emits TrustFlow audit events, and fails closed on every trust, identity, policy, and cryptographic boundary. It uses a strict two-process model: a Swift/SwiftUI shell (UI, auth, secrets, XPC) and a Python backend (build intelligence, consensus, enforcement).

## Critical Rules — Read Before Writing Any Code

1. **CTX-ID first.** Validate CTX-ID at every enforcement entry point. Validation failure means immediate rejection with no partial processing. Missing, expired, invalid, or unverified CTX-ID is treated as `UNTRUSTED`. Never infer identity from ambient context.
2. **VTZ before execution.** Check VTZ policy BEFORE executing any agent action or cross-boundary operation. Cross-VTZ tool calls require explicit policy authorization; implicit access is denied. Mid-session policy mutation is forbidden.
3. **Synchronous TrustFlow emission.** Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path. Asynchronous buffering is forbidden. Emission failures must never be silently skipped.
4. **Fail closed — always.** All trust, identity, policy, audit, and cryptographic errors fail closed: reject the action, log the event, surface to the caller. Never silently continue. Never degrade into permissive behavior.
5. **No secrets in output.** Secrets, keys, tokens, credentials, and cleartext sensitive payloads must never appear in logs, error messages, generated code, audit records, or cleartext payloads.
6. **No execution of generated code.** Generated code is NEVER executed by the agent. No `eval`, no `exec`, no dynamic import, no `subprocess` of generated content.
7. **All external input is untrusted.** Documents, PR comments, CI output, XPC messages, and tool output must be validated strictly before use. External document context goes in the USER prompt, never the SYSTEM prompt.
8. **DTL labels are immutable.** DTL labels are assigned at data ingestion and are immutable. Derived data inherits the HIGHEST classification of any source. Unlabeled data is treated as `CONFIDENTIAL`. Labels must not be stripped without audit.
9. **Gates wait indefinitely.** Gates wait indefinitely for operator input. `SECURITY_REFUSAL` is terminal for that path. No code may auto-approve, bypass a gate by rephrasing, or time out a gate.
10. **Path-validated writes.** All file writes must be path-validated via `path_security.validate_write_path()` before execution. Reject path traversal or out-of-root writes.
11. **CTX-ID tokens are immutable.** Rotation creates a new token and immediately invalidates the old one. Missing CTX-ID means `UNTRUSTED`.
12. **Build memory is persistent.** Build memory and build rules are NEVER cleared automatically. They are persistent learning systems. Per-PR stage checkpoints prevent re-running completed work after a crash.
13. **Unknown XPC messages.** Unknown XPC message types must be discarded and logged. Never raise them as exceptions. Never process them optimistically.

## Architecture Overview

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; routes agent actions through policy | Execute actions before CTX-ID validation completes |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Structural session boundaries; cross-zone policy authorization; `allow`/`restrict`/`block` decisions before execution | Allow implicit cross-VTZ access or mid-session policy changes |
| **TrustFlow** | `src/trustflow/` | Append-only synchronous audit event emission for every action outcome | Buffer events asynchronously or silently skip failed emissions |
| **DTL** (Data Trust Labels) | `src/dtl/` | Immutable classification labels at ingestion; label inheritance; boundary verification | Strip labels without audit; allow unlabeled data to pass as unclassified or cross trust boundaries |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity and CTX-ID validation using TrustLock public key and TPM-anchored trust | Rely on software-only validation; accept tokens without cryptographic verification |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Deterministic policy evaluation for all enforcement decisions | Mutate enforcement state implicitly; return non-deterministic results |
| **Rewind** (Forge Rewind) | `src/rewind/` | Full session replay from the TrustFlow audit stream alone | Depend on state outside the audit stream for replay fidelity |

## Settings Schema, Defaults Bootstrap, and Migration Infrastructure

### Settings Schema

All platform settings are defined in a strict schema. Every setting must declare:
- **key**: dot-namespaced string (e.g., `vtz.cross_zone_policy`, `trustflow.emission_mode`).
- **type**: one of `string`, `integer`, `boolean`, `enum`, `path`, `duration`.
- **default**: the bootstrap default value — must be the most restrictive secure value.
- **mutable_at_runtime**: `boolean` — whether the setting can change after process start. Settings that affect trust boundaries must be `false`.
- **migration_version**: integer — the schema version at which this setting was introduced or last structurally changed.

Unrecognized settings keys must be rejected at load time. Missing required settings must cause a fatal startup error — never fall back to implicit defaults.

### Defaults Bootstrap

1. On first launch or when the settings store is absent, the platform must write the full schema with all default values to the canonical settings path.
2. Defaults must be the most restrictive secure posture: `trustflow.emission_mode` = `synchronous`, `vtz.implicit_cross_zone` = `deny`, `dtl.unlabeled_classification` = `CONFIDENTIAL`, `gate.auto_approve` = `false`.
3. Bootstrap must complete before any enforcement subsystem initializes. If bootstrap fails, the platform must refuse to start.
4. The bootstrap event must be recorded as a TrustFlow event with action `settings.bootstrap` and outcome `allow`.

### Migration Infrastructure

1. Every settings schema change increments a monotonic `schema_version` integer.
2. Migrations are forward-only. Rollback is achieved by restoring from backup, never by running reverse migrations.
3. Each migration must be an idempotent, atomic function: `migrate_vN_to_vN+1(settings) -> settings`. If migration fails, the platform must refuse to start with the corrupted settings.
4. Before migration, the platform must snapshot the current settings store. The snapshot path must be logged.
5. After migration, the platform must validate the resulting settings against the target schema version. Validation failure is fatal.
6. Every migration execution must emit a TrustFlow event: action `settings.migrate`, fields `from_version`, `to_version`, outcome `allow` or `block`.
7. Settings files must never be silently upgraded — the operator must see a log entry for every migration step.