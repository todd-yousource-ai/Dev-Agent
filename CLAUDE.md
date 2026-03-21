# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels all data at ingestion (DTL), and emits an immutable synchronous audit stream (TrustFlow) for every action outcome — all of which MUST fail closed on any violation.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — validation failure means immediate rejection with zero partial processing.
2. Check VTZ policy BEFORE execution of any action — implicit cross-VTZ access is denied; VTZ boundaries are structural, not advisory, and MUST NOT be bypassed by application code.
3. TrustFlow events MUST be emitted synchronously in the enforcement path for every action outcome (allow, restrict, block) — async buffering is forbidden; failed emission is a WARN-level audit event that MUST be surfaced.
4. Treat missing CTX-ID as UNTRUSTED — NEVER infer identity from session state, UI state, or surrounding context. CTX-ID tokens are IMMUTABLE once issued — rotation creates a new token and invalidates the old one immediately; expired CTX-ID is rejected.
5. All trust, identity, policy, and cryptographic failures MUST fail CLOSED — reject the action, log the event, surface to caller, NEVER silently continue.
6. DTL labels are assigned at data ingestion and are IMMUTABLE — derived data inherits the HIGHEST classification of any source; unlabeled data is CONFIDENTIAL until explicitly reclassified.
7. All external input (documents, PR comments, CI output, XPC messages, generated content) is UNTRUSTED — validate strictly before use; external document context goes in the USER prompt, NEVER the SYSTEM prompt.
8. Generated code is NEVER executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content; `shell=True` is banned in all subprocess calls.
9. Every file write MUST pass `path_security.validate_write_path()` before execution — no exceptions.
10. If a component returns `SECURITY_REFUSAL`, processing MUST stop — do not retry, rephrase, or route to another provider; gate, log, halt.
11. Gates wait indefinitely for operator input — auto-approve is forbidden under all circumstances.
12. Secrets, keys, tokens, and credentials MUST NEVER appear in logs, error messages, generated code, or cleartext payloads — Python receives credentials only via XPC from Swift and stores them in memory only.
13. Discard and log unknown XPC message types — NEVER raise them as uncaught exceptions.

## Architecture Overview

### Two-Process Architecture (No Exceptions)

**Swift Shell** (macOS app): Owns SwiftUI interface (Navigator + BuildStream + ContextPanel), Touch ID biometric gate, Keychain storage for all credentials, XPC channel, Python process lifecycle.
- Swift MUST NEVER: call LLM APIs, read Keychain for the backend's use, execute generated code.

**Python Backend**: Owns ConsensusEngine, BuildPipeline, GitHubTool, BuildLedger, DocumentStore, HolisticReview, TRDWorkflow, CommandRouter.
- Python MUST NEVER: read Keychain directly, access the UI, persist credentials to disk, store credentials in environment variables.

### Module Contracts

- `src/cal/` — Conversation Abstraction Layer enforcement entry points. MUST validate CTX-ID first, then VTZ, then execute, then emit TrustFlow. MUST NOT partially process requests before validation.
- `src/vtz/` — Virtual Trust Zone policy enforcement. MUST make pre-execution authorization decisions and bind each session to exactly one VTZ. MUST NOT allow implicit cross-VTZ access or application-level bypass.
- `src/trustflow/` — Synchronous audit/event emission. Every event MUST include: `event_id` (string, unique), `session_id` (string), `ctx_id` (string), `ts` (ISO-8601 UTC timestamp), `event_type` (enum: allow | restrict | block | error), `payload_hash` (SHA-256 hex). MUST emit on every outcome. MUST NOT async-buffer enforcement-path events.
- `src/dtl/` — Data Trust Label ingestion and boundary checks. MUST assign labels at ingestion and verify labels before trust-boundary crossing. MUST NOT mutate labels after assignment. Derived data MUST inherit the highest classification of any source.
- `src/trustlock/` — Cryptographic machine identity and CTX-ID verification. MUST validate CTX-ID against TrustLock public key and enforce expiry/rotation. MUST NOT use software-only validation when hardware attestation is available.
- `src/mcp/` — MCP Policy Engine. MUST supply explicit policy decisions consumed by CAL/VTZ before action execution. MUST NOT return ambiguous allow behavior; every decision is allow, restrict, or block.
- `src/rewind/` — Replay engine. MUST support full replay from append-only TrustFlow audit records alone. MUST NOT require hidden state or external data beyond the audit log.

### Enforcement Order (Every Request)

1. Validate CTX-ID (reject if missing, expired, or invalid)
2. Resolve VTZ binding (reject if no VTZ or cross-VTZ violation)
3. Evaluate MCP policy (reject if block, constrain if restrict)
4. Verify DTL labels on all input data (reject if unlabeled-as-CONFIDENTIAL crosses boundary)
5. Execute action
6. Emit synchronous TrustFlow event with outcome
7. Return result to caller

Failure at any step MUST halt the sequence — no subsequent step executes.