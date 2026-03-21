# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels all data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) for every decision — failing closed on any violation.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID first at every enforcement entry point — validation failure means immediate rejection with no partial processing.
2. Never infer identity from session context, transport context, or prior state — missing or expired CTX-ID MUST be treated as `UNTRUSTED`.
3. Check VTZ policy BEFORE executing any agent action — implicit cross-VTZ access is always denied.
4. Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path — async buffering is not permitted; never silently skip emission failures.
5. All trust, identity, policy, and cryptographic failures MUST fail CLOSED — reject the action, log the event, surface to the caller with context, never silently continue.
6. Never hardcode secrets, tokens, credentials, API keys, or cryptographic material — secrets MUST NOT appear in logs, error messages, generated code, HTTP response bodies, or audit records.
7. All external input (documents, PR comments, CI output, XPC messages, generated code) is UNTRUSTED — validate strictly before use; context from external documents goes in the USER prompt, never the SYSTEM prompt.
8. Generated code is never executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True`, no dynamic equivalent.
9. DTL labels are assigned at DATA INGESTION and are IMMUTABLE — unlabeled data MUST be treated as `CONFIDENTIAL`; derived data inherits the HIGHEST classification of any source; labels MUST be verified before any trust-boundary crossing.
10. CTX-ID tokens are IMMUTABLE once issued — validation MUST use TrustLock public key anchored in hardware-backed trust, not software-only checks.
11. Audit records are APPEND-ONLY, generated BEFORE execution, and MUST NOT contain secrets, keys, tokens, or cleartext sensitive data.
12. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions.
13. If a `SECURITY_REFUSAL` output is received, STOP — never retry with rephrasing, never bypass via another provider, never continue the same operation; gate, log, and surface to operator.
14. Discard and log unknown XPC message types — never raise them as uncaught exceptions and never process them speculatively.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → VTZ policy check → DTL label verification → Action execution → TrustFlow emission → Audit record**.

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Processes agent actions; calls CTX-ID validation first, VTZ policy second, emits TrustFlow on every outcome | Never process an action without CTX-ID validation; never skip TrustFlow emission |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Decides authorization before execution; enforces zone boundaries for all cross-boundary operations | Never allow implicit cross-VTZ access; never defer authorization to post-execution |
| **TrustFlow** | `src/trustflow/` | Emits synchronous, append-only audit events with fields: `event_id` (UUID), `session_id` (string), `ctx_id` (string), `ts` (ISO-8601), `event_type` (enum: `allow`, `restrict`, `block`), `payload_hash` (SHA-256 hex) | Never buffer asynchronously in the enforcement path; never omit required fields; never include cleartext secrets in payload |
| **DTL** (Data Trust Labels) | `src/dtl/` | Assigns immutable classification labels at data ingestion; enforces label inheritance on derived data; verifies labels at every trust-boundary crossing | Never allow unlabeled data to cross a trust boundary without `CONFIDENTIAL` default; never strip or mutate labels without audit |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity and CTX-ID validation against TrustLock public key; anchors validation in hardware-backed trust | Never accept software-only validation when hardware-backed trust is available; never cache or reuse expired CTX-ID tokens |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Evaluates explicit policy decisions at enforcement boundaries | Never substitute hints, heuristics, or advisory-only outputs for enforcement decisions |
| **Rewind** (Forge Rewind) | `src/rewind/` | Supports deterministic replay of audit streams for forensic analysis and compliance verification | Never mutate original audit records during replay; never skip TrustFlow events during reconstruction |

## Enforcement Contract Summary

- **Identity**: Every request MUST carry a valid CTX-ID. Validation uses TrustLock public key. Missing or expired CTX-ID → reject as `UNTRUSTED`.
- **Authorization**: Every action MUST pass VTZ policy check. No implicit grants. Deny by default.
- **Labeling**: Every data object MUST carry a DTL label from ingestion forward. Unlabeled → `CONFIDENTIAL`. Labels are immutable. Derived data inherits the highest classification.
- **Audit**: Every enforcement decision MUST emit a TrustFlow event synchronously. Events are append-only. Events MUST NOT contain secrets or cleartext sensitive data.
- **Failure mode**: All failures are CLOSED. No silent fallthrough. No partial processing. Surface error to caller.

## Build & Development Notes

- Run tests: follow per-subsystem README instructions in each `src/` subdirectory.
- All code contributions MUST pass `path_security.validate_write_path()` checks.
- All code contributions MUST NOT introduce `eval()`, `exec()`, `shell=True`, or dynamic execution of generated content.
- All logging MUST be reviewed to ensure no secrets, tokens, or credentials are emitted.