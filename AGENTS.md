# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations where every action is identity-bound via CTX-ID, policy-gated via VTZ, data-classified via DTL, and audit-streamed via TrustFlow — with all failures failing closed and no silent degradation permitted.

Forge is a two-process architecture: a Swift shell (UI, auth, Keychain, XPC) and a Python backend (consensus, pipeline, GitHub). Enforcement order for every agent action is: **CTX-ID validation → VTZ policy check → action execution → TrustFlow emission → audit record**.

## Critical Rules — Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — before any processing, parsing, or side effects occur. A missing or expired CTX-ID MUST be treated as `UNTRUSTED` — never infer identity from session context, transport context, or user state.
2. CTX-ID tokens are IMMUTABLE once issued. Reject immediately on any validation failure.
3. Every agent action MUST be checked against VTZ policy BEFORE execution; VTZ boundaries are structural, not advisory — application code cannot bypass them.
4. Every action outcome (`allow`, `restrict`, `block`) MUST emit a synchronous TrustFlow event on the enforcement path. Each event MUST include: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, and `payload_hash`. Async buffering is forbidden.
5. DTL labels are assigned at DATA INGESTION and are immutable after assignment. Derived data inherits the HIGHEST classification of any source. Unlabeled data is `CONFIDENTIAL` until explicitly reclassified. Labels MUST be verified before any trust-boundary crossing.
6. All trust, identity, policy, authentication, authorization, and cryptographic failures MUST fail CLOSED: reject the action, log the event, surface to the caller — never silently continue.
7. Secrets, keys, tokens, and credentials MUST NEVER appear in logs, error messages, generated code, or cleartext payloads.
8. Generated code is NEVER executed by the agent — no `eval`, no `exec`, no `subprocess` of generated content.
9. All external input (documents, PR comments, CI output, XPC messages) is UNTRUSTED and MUST be validated strictly before use. Bounds-check every parser.
10. Discard and log unknown XPC message types without raising uncaught exceptions or attempting fallback handling.
11. Gates MUST wait indefinitely for explicit operator input — no auto-approve ever. `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log.
12. All file writes MUST be path-validated via `path_security.validate_write_path()` before execution. Context from external documents goes in the USER prompt — NEVER the SYSTEM prompt.
13. Build memory and build rules are persistent learning systems — they are NEVER cleared automatically. Per-PR stage checkpoints prevent re-running completed work after a crash.

## Architecture Overview

- **`src/cal/`** — Conversation Abstraction Layer. Enforcement entry points. MUST validate CTX-ID first, invoke VTZ before action execution. MUST NOT partially process rejected actions. MUST NOT process any action before CTX-ID validation completes.
- **`src/vtz/`** — Virtual Trust Zones. Structural policy boundaries per agent session. MUST decide `allow`/`restrict`/`block` before execution. Cross-VTZ calls require explicit authorization. MUST NOT permit implicit cross-boundary access. MUST NOT change policy mid-session without re-authorization.
- **`src/dtl/`** — Data Trust Labels. Assignment and verification. MUST assign labels at ingestion. MUST verify labels before trust-boundary crossing. MUST NOT mutate labels after assignment. Derived data inherits the highest classification of any source.
- **`src/trustflow/`** — Append-only audit and event emission pipeline. MUST synchronously emit outcome records on the enforcement path. MUST NOT silently skip failed emission. MUST NOT use async buffering. Every emitted event MUST contain: `event_id` (string, unique), `session_id` (string), `ctx_id` (string), `ts` (ISO-8601 UTC), `event_type` (string enum), `payload_hash` (SHA-256 hex).
- **`src/trustlock/`** — Cryptographic machine identity and CTX-ID validation anchored to TrustLock public key material. MUST enforce immutable token validation. MUST NOT accept software-only validation when hardware attestation is available.
- **`src/mcp/`** — MCP Policy Engine integration. MUST apply explicit policy decisions. MUST NOT convert policy suggestions into implicit allow.
- **`src/rewind/`** — Replay engine for audit reconstruction. MUST support full replay from the TrustFlow audit stream alone. MUST NOT depend on hidden mutable external state.
- **`sdk/connector/`** — Forge Connector SDK surface. MUST preserve the same trust and audit contracts as internal subsystems. External callers are subject to the same CTX-ID, VTZ, DTL, and TrustFlow enforcement as internal paths.

## Enforcement Invariants

- No action executes without a valid CTX-ID.
- No action executes without a VTZ policy decision.
- No action outcome goes unrecorded in TrustFlow.
- No data crosses a trust boundary without DTL label verification.
- No failure mode results in silent continuation.
- No secret appears in any observable output.
- No generated code is executed.
- No gate auto-approves.