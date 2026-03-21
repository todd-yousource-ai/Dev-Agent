# CLAUDE.md - Forge Platform

Forge is a trust enforcement platform where every AI agent action is identity-bound, policy-gated, audit-logged, and cryptographically verifiable — enforcement is structural, not advisory.

## Critical Rules — Read Before Writing Any Code

1. **CTX-ID first.** Validate CTX-ID at every enforcement entry point. Reject immediately on validation failure with zero partial processing.
2. **VTZ before execution.** Check VTZ policy before executing any agent action or cross-boundary operation. Deny implicitly unless explicit authorization exists.
3. **TrustFlow is synchronous.** Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path. Never buffer asynchronously. Never silently skip emission failures — log at WARN and surface.
4. **Missing CTX-ID means UNTRUSTED.** Treat missing, expired, invalid, or unverifiable CTX-ID as `UNTRUSTED`. Never infer identity from ambient context. CTX-ID tokens are immutable once issued; rotation creates a new token and immediately invalidates the old one.
5. **DTL labels are immutable.** Assign DTL labels at data ingestion. Derived data inherits the HIGHEST classification of any source. Unlabeled data is `CONFIDENTIAL` until explicitly reclassified. Never permit label stripping or unlabeled boundary crossing without policy control and audit.
6. **Fail closed.** All trust, identity, policy, and cryptographic errors MUST fail closed: reject the action, log the event, surface the failure to the caller with context. Never silently continue.
7. **No secrets in output.** Secrets, keys, tokens, credentials, and cleartext sensitive payloads MUST never appear in logs, error messages, audit records, generated code, or cleartext payloads.
8. **All external input is untrusted.** Validate strictly before use — documents, PR comments, CI output, user prompts, XPC messages, and file paths. External document context goes in USER prompt, never SYSTEM prompt.
9. **No execution of generated content.** Never execute generated or external content with `eval()`, `exec()`, `subprocess` of generated artifacts, `shell=True`, or shell interpolation.
10. **Validate every write path.** All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions.
11. **SECURITY_REFUSAL is final.** Stop immediately on `SECURITY_REFUSAL` output — gate, log, and halt. Never bypass by rephrasing, retrying, or switching providers. Gates wait indefinitely for operator input — no auto-approve ever.
12. **Discard unknown XPC messages.** Discard and log unknown XPC message types instead of raising uncaught exceptions or attempting best-effort handling.
13. **Audit is append-only.** Audit records are append-only with no modification or deletion. TrustFlow emission failure is a WARN-level audit event that MUST be logged and surfaced.

## Architecture Overview

Forge is a two-process architecture: a Swift shell (UI, auth, Keychain, XPC) and a Python backend (consensus, pipeline, GitHub integration). The enforcement order for every agent action is:

**CTX-ID validation → VTZ policy check → action execution → TrustFlow emission → audit record**

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; action gating against VTZ policy; enforcement order: validate CTX-ID first, check VTZ second, execute third, emit TrustFlow fourth | Process any action before CTX-ID validation and VTZ policy check complete |
| **TrustFlow** | `src/trustflow/` | Synchronous, append-only audit event emission for every action outcome; required fields: `ctx_id` (string), `vtz_id` (string), `action` (string), `outcome` (enum: `allow`, `restrict`, `block`), `timestamp` (ISO 8601), `dtl_label` (string), `signature` (base64) | Buffer events asynchronously in the enforcement path; silently drop failed emissions; modify or delete audit records |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Structural policy boundaries per agent session; one VTZ per session bound at CTX-ID issuance; cross-VTZ tool calls require explicit policy authorization | Allow implicit cross-VTZ access; permit session migration without re-authorization |
| **DTL** (Data Trust Labels) | `src/dtl/` | Label assignment at ingestion; immutable labels; derived-data classification inheritance (highest wins); boundary crossing requires policy control and audit | Permit label stripping; allow unlabeled data to cross boundaries without policy control and audit; reclassify without explicit authorization |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity; CTX-ID issuance and validation against TrustLock public key; hardware-backed credential storage | Accept software-only validation when hardware attestation is available; issue CTX-ID without verifying machine identity |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Explainable, reproducible policy control decisions; structured policy evaluation for every agent action | Degrade from enforcement into advisory behavior; produce non-reproducible or unexplainable decisions |
| **Rewind** | `src/rewind/` | Replay engine for audit reconstruction; deterministic replay of TrustFlow event streams for post-incident analysis | Modify source audit records during replay; skip events during reconstruction |
| **Path Security** | `src/path_security/` | Write-path validation via `path_security.validate_write_path()` for every file write | Allow any file write without validation; permit path traversal or symlink escape |

## Product Identity

- **Product name:** Forge (always capitalized, never "forge" in prose)
- **Platform descriptor:** trust enforcement platform
- **Core guarantee:** every agent action is identity-bound, policy-gated, audit-logged, and cryptographically verifiable
- **Naming policy:** use canonical subsystem names (CTX-ID, VTZ, TrustFlow, DTL, TrustLock, MCP, CAL, Rewind) in all documentation, code comments, commit messages, and error messages — never abbreviate or rename

## Enforcement Invariants

- No action executes without a valid CTX-ID.
- No action executes without a VTZ policy check.
- No action completes without a synchronous TrustFlow event.
- No data crosses a boundary without a DTL label check.
- No file is written without write-path validation.
- No failure is silent — every error is logged, gated, and surfaced.
- No credential appears in any output channel.
- No external input is trusted without validation.
- No generated code is executed by the agent.
- No audit record is modified or deleted.