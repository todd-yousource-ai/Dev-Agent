# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data via DTL, and emits an immutable TrustFlow audit stream — rejecting any action that fails validation at any layer.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — before any processing, parsing, or side effects occur; validation failure means immediate rejection with no partial work.
2. TrustFlow events MUST be emitted synchronously in the enforcement path for every action outcome (`allow`, `restrict`, `block`) — async buffering is forbidden, and emission failure MUST be logged at WARN level, never silently skipped.
3. VTZ policy MUST be checked BEFORE execution of any agent action — cross-VTZ tool calls require explicit policy authorization; implicit access is denied.
4. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to the caller — `try/except/pass` is BANNED in enforcement code.
5. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, or error payloads — Python stores credentials in memory only, never in env vars or on disk.
6. All external input (documents, PR comments, CI output, XPC messages) is untrusted — validate strictly before use; context from external documents goes in the USER prompt, never the SYSTEM prompt.
7. Generated code is never executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True`.
8. Gates wait indefinitely for operator input — no auto-approve, no auto-merge ever; the human is in the loop at every gate.
9. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions.
10. DTL labels are assigned at data ingestion and are immutable; derived data inherits the HIGHEST classification of any source; unlabeled data MUST be treated as CONFIDENTIAL.
11. CTX-ID tokens are IMMUTABLE once issued — rotation creates a new token and immediately invalidates the old one; expired CTX-IDs MUST be rejected; missing CTX-ID MUST be treated as UNTRUSTED — never infer identity from session context, UI state, or call site.
12. If a `SECURITY_REFUSAL` output is received, stop — do not retry with rephrasing, do not fall back to another provider; gate and log.
13. Discard and log unknown XPC message types — never raise them as uncaught exceptions in the transport path.

## Architecture Overview

### Two-Process Architecture (No Exceptions)

**Swift Shell** (macOS app): Owns SwiftUI interface, Touch ID biometric gate, Keychain storage, XPC channel, Python process lifecycle. Swift MUST NEVER call LLM APIs, read Keychain for the backend, or execute generated code.

**Python Backend**: Owns ConsensusEngine, BuildPipeline, GitHubTool, BuildLedger, DocumentStore, HolisticReview, TRDWorkflow, CommandRouter. Python MUST NEVER read Keychain directly, access the UI, or persist credentials to disk.

**Credential Flow**: Touch ID → Swift reads Keychain → delivers via XPC credential message → Python holds in memory only → credential is never written to disk, env vars, or logs.

### Directory Contracts

- `src/cal/` — Conversation Abstraction Layer enforcement entry points. MUST validate CTX-ID first, then VTZ, then emit TrustFlow. MUST NOT partially process actions before validation completes.
- `src/vtz/` — Virtual Trust Zone policy enforcement. MUST bind each session to exactly one VTZ and deny implicit cross-VTZ calls. MUST NOT allow application code to bypass VTZ boundaries.
- `src/dtl/` — Data Trust Label handling. MUST assign labels at ingestion and verify labels before any boundary crossing. MUST NOT permit silent relabeling or label stripping.
- `src/trustflow/` — TrustFlow audit stream. MUST synchronously emit events on every outcome. MUST NOT async-buffer enforcement-path emissions.
- `src/trustlock/` — Cryptographic machine identity and CTX-ID validation rooted in TrustLock public key material. MUST reject software-only validation. MUST NOT accept unverifiable CTX-ID tokens.
- `src/mcp/` — MCP Policy Engine. MUST make explicit policy decisions before tool use or cross-boundary actions. MUST NOT act as advisory-only logic.
- `src/rewind/` — Replay and reconstruction engine. MUST support replay from append-only audit records alone. MUST NOT require hidden external state to reconstruct a session.

### TrustFlow Event Wire Format

Every TrustFlow event MUST contain the following fields:

| Field | Type | Description |
|---|---|---|
| `event_id` | `string (UUID v4)` | Unique identifier for this event |
| `session_id` | `string (UUID v4)` | Session that produced the event |
| `ctx_id` | `string` | CTX-ID of the acting identity |
| `ts` | `string (ISO 8601)` | Timestamp of event emission |
| `event_type` | `enum: allow, restrict, block` | Outcome of the enforcement decision |
| `payload_hash` | `string (SHA-256 hex)` | Hash of the action payload |
| `vtz_id` | `string` | VTZ in which the action was evaluated |
| `dtl_label` | `string` | Highest DTL classification of data involved |

All fields are REQUIRED. Events with missing fields MUST be rejected by the audit stream.

### Shared Contract Base Classes

All enforcement subsystems MUST extend from shared base classes in `src/contracts/`:

- `EnforcementBase` — abstract base requiring `validate_ctx_id()`, `check_vtz_policy()`, `emit_trustflow_event()` in that order.
- `TrustFlowEmitter` — shared emitter ensuring synchronous emission with the required wire format fields.
- `DTLHandler` — shared label assignment and propagation logic enforcing immutability and highest-classification inheritance.

### Registry

All subsystems MUST register with the central `EnforcementRegistry` at startup. The registry:
- Tracks all active enforcement modules and their VTZ bindings.
- Rejects duplicate registrations for the same VTZ.
- Provides introspection for audit and replay.
- MUST fail closed if any required subsystem fails to register.

### Schema Export

The `src/contracts/schema_export.py` tool MUST:
- Export JSON Schema definitions for all TrustFlow event types, DTL label enums, VTZ policy structures, and CTX-ID token formats.
- Be runnable as `python -m src.contracts.schema_export` to produce a single `forge_schemas.json` artifact.
- Validate that all exported schemas match the canonical wire format — schema drift MUST cause CI failure.