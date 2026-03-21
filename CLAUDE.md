# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform where every agent action is identity-verified, policy-checked, audited, and replayable — and the Consensus Dev Agent is a native macOS two-process AI coding agent (Swift shell + Python backend) that decomposes build intents into ordered PRs through parallel LLM generation, 3-pass review, CI execution, and mandatory operator gates.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST validate CTX-ID FIRST — validation failure means immediate rejection with zero partial processing. Missing CTX-ID is treated as `UNTRUSTED`; never infer identity from session state, transport context, or prior requests.
2. Every action outcome (allow, restrict, block) MUST emit a synchronous TrustFlow event in the enforcement path with `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, and `payload_hash` — async buffering is forbidden, failed emission is a WARN-level audit event, never a silent skip.
3. VTZ policy MUST be checked BEFORE execution of any agent action — cross-VTZ tool calls require explicit policy authorization, implicit access is denied.
4. DTL labels are assigned at data ingestion and are immutable — derived data inherits the HIGHEST classification of any source, unlabeled data is CONFIDENTIAL until explicitly reclassified. Unlabeled or stripped data MUST NOT cross trust boundaries silently.
5. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to caller — `try/except/pass` is BANNED in enforcement code. Never degrade silently into permissive behavior.
6. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, audit records, or generated code — Python backend never reads Keychain directly; only Swift reads Keychain and delivers via XPC.
7. Generated code is never executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True` in subprocess calls.
8. All external input (documents, PR comments, CI output) is untrusted — context from external documents goes in the USER prompt, never the SYSTEM prompt; all loaded document chunks must pass injection scanning.
9. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions, no writes to disk before path validation succeeds.
10. Gates wait indefinitely for operator input — no auto-approve ever; `SECURITY_REFUSAL` output is never bypassed by rephrasing, retrying with another provider, or any other mechanism — stop, gate, log.
11. XPC unknown message types are discarded and logged — never raised as exceptions, never speculatively handled; wire format is line-delimited JSON, nonce-authenticated, max 16MB per message.
12. Audit records are append-only, generated BEFORE execution, must never contain secrets, and must support full replay from the audit stream alone without external state.

## Architecture Overview

**Enforcement order for every agent action:** CTX-ID validation → VTZ policy check → Action execution → TrustFlow event emission → Audit record.

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; action processing pipeline; enforcement order: validate CTX-ID first, check VTZ policy second, execute action third, emit TrustFlow fourth | Process any action before CTX-ID validation passes |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Structural policy boundaries per agent session; binds each session to exactly one VTZ; cross-zone authorization requires explicit policy | Allow implicit cross-VTZ tool calls; bypass by application code |
| **DTL** (Data Trust Labels) | `src/dtl/` | Immutable classification labels assigned at ingestion; highest-classification inheritance for derived data; boundary enforcement | Permit unlabeled or stripped data to cross trust boundaries silently; allow label mutation after assignment |
| **TrustFlow** | `src/trustflow/` | Append-only action audit stream; synchronous event emission in enforcement path with `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash` | Buffer asynchronously; skip failed emission silently; contain secrets in records |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity and CTX-ID validation anchored to TrustLock public key; hardware-backed identity where available | Accept software-only validation as equivalent; allow mutable token fields after issuance |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Explicit policy evaluation before action execution; enforcement-grade decisions | Return advisory-only results where enforcement is required; allow action without policy match |
| **Path Security** | `src/path_security/` | Write-path validation for all file operations via `validate_write_path()` | Allow any file write without prior path validation |
| **XPC Bridge** | Swift ↔ Python | Line-delimited JSON, nonce-authenticated, max 16MB per message; Swift owns Keychain access | Pass secrets to Python side; raise exceptions on unknown message types; exceed 16MB per message |

## Consensus Dev Agent — Two-Process Architecture

- **Swift Shell (macOS):** Owns Keychain access, XPC transport, operator gate UI, and system integration. Delivers secrets to Python backend exclusively via authenticated XPC.
- **Python Backend:** Decomposes build intents into ordered PRs through parallel LLM generation, 3-pass review, CI execution. Never reads Keychain directly. Never executes generated code.
- **Operator Gates:** Every PR merge, security-sensitive action, and `SECURITY_REFUSAL` triggers a gate. Gates wait indefinitely — no auto-approve, no timeout bypass.
- **Audit Replay:** The full agent session is replayable from the TrustFlow audit stream alone, with no external state required.