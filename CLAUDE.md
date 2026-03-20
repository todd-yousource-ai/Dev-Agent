# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels all data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) — with every failure mode closing to deny.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — validation failure means immediate rejection with zero partial processing.
2. Treat missing CTX-ID as `UNTRUSTED` — NEVER infer identity from session context, transport state, or caller location.
3. Bind every agent session to exactly one VTZ at CTX-ID issuance — deny implicit cross-VTZ tool calls.
4. Every agent action MUST be checked against VTZ policy BEFORE execution — on denial, emit a `VTZEnforcementDecision` with `verdict=block` and reject immediately.
5. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event synchronously in the enforcement path — async buffering is forbidden; NEVER silently skip emission failures.
6. TrustFlow events MUST include: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash`.
7. All trust, identity, policy, cryptographic, and authentication failures MUST fail closed: reject the action, log the event, surface to the caller — NEVER silently continue.
8. Secrets, keys, tokens, and credentials MUST NOT appear in logs, error messages, generated code, audit records, or XPC messages beyond the designated `credentials` envelope.
9. Generated code is NEVER executed by the agent — no `eval()`, no `exec()`, no shell expansion, no `subprocess` of generated or external content.
10. All external input (documents, PR comments, CI output, XPC messages, line-delimited JSON payloads) is untrusted — validate strictly before use.
11. All file writes MUST pass `path_security.validate_write_path()` before execution.
12. DTL labels are assigned at data ingestion and are immutable — derived data inherits the HIGHEST classification of any source; unlabeled data is `CONFIDENTIAL` until explicitly reclassified. Labels MUST be verified before boundary crossing. Labels MUST NOT be stripped or downgraded without policy-controlled audit.
13. Gates wait indefinitely for operator input — no auto-approve, ever.
14. XPC unknown message types MUST be discarded and logged — NEVER raised as exceptions, NEVER processed.
15. `SECURITY_REFUSAL` is terminal for the current operation: stop, gate, and log — NEVER bypass by retrying or rephrasing.

## Architecture Overview

Forge is a two-process architecture with no exceptions:

| Subsystem | Location | Enforces | MUST NOT |
|---|---|---|---|
| **Swift Shell** | macOS app | UI (Navigator + BuildStream + ContextPanel), Touch ID biometric gate, Keychain storage, XPC channel, Python process lifecycle | Call LLM APIs, read Keychain for the backend, execute generated code |
| **Python Backend** | `src/` | ConsensusEngine, BuildPipeline, GitHubTool, BuildLedger, DocumentStore, HolisticReview, TRDWorkflow, CommandRouter | Read Keychain directly, access UI, persist credentials to disk |

### Subsystem Contracts

- **`src/cal/`** — Conversation Abstraction Layer. MUST validate CTX-ID first at every enforcement entry point, consult VTZ before action execution, and emit a TrustFlow event for every outcome. MUST NOT partially process rejected actions or proceed before CTX-ID validation completes.

- **`src/vtz/`** — Virtual Trust Zone boundary enforcement. Structural, not advisory. MUST decide boundary access before execution and emit `VTZEnforcementDecision` with `verdict` field (`allow`, `restrict`, `block`). MUST NOT allow implicit cross-VTZ calls, permit application code to bypass enforcement, or apply policy changes mid-session.

- **`src/dtl/`** — Data Trust Label ingestion and propagation. MUST assign immutable labels at ingestion, enforce highest-label inheritance on derived data, and verify labels before boundary crossing. MUST NOT strip or downgrade labels without policy-controlled audit.

- **`src/trustflow/`** — Immutable, append-only audit stream. Every event MUST synchronously include: `event_id` (UUID), `session_id` (string), `ctx_id` (string), `ts` (ISO-8601 UTC), `event_type` (enum), `payload_hash` (SHA-256 hex). MUST NOT buffer asynchronously in the enforcement path. MUST NOT contain secrets, keys, tokens, or cleartext sensitive data.

- **`src/trustlock/`** — Cryptographic machine identity and CTX-ID validation using TrustLock public key. MUST enforce hardware-anchored (Secure Enclave / TPM) validation. MUST NOT accept software-only validation as sufficient.

- **`src/mcp/`** — MCP Policy Engine. MUST provide explicit policy decisions for every agent action request. MUST NOT return ambiguous or partial decisions; every query receives a definitive `allow` or `deny`.

## Agent Bridge Protocol Envelope Schema

All inter-process messages between Swift Shell and Python Backend use the Agent Bridge Protocol (ABP) envelope. Every message MUST conform to this schema:


{
  "abp_version": "1.0",
  "message_id": "<UUID v4>",
  "ctx_id": "<CTX-ID string — MUST be present and validated>",
  "session_id": "<session identifier>",
  "ts": "<ISO-8601 UTC timestamp>",
  "vtz_id": "<bound VTZ identifier>",
  "message_type": "<registered type string>",
  "payload": { },
  "payload_hash": "<SHA-256 hex of canonical JSON payload>",
  "dtl_label": "<PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED>",
  "credentials": { }
}


### Envelope Validation Rules

1. `abp_version` MUST be a supported version string; unknown versions MUST be rejected.
2. `message_id` MUST be a valid UUID v4; duplicates within a session MUST be rejected.
3. `ctx_id` MUST be validated against TrustLock before any further processing; missing or invalid CTX-ID MUST reject the envelope.
4. `vtz_id` MUST match the VTZ bound to the `ctx_id` at session creation; mismatches MUST reject the envelope.
5. `message_type` MUST be a registered type; unknown types MUST be discarded and logged per Rule 14.
6. `payload_hash` MUST match the SHA-256 of the canonicalized `payload`; mismatches MUST reject the envelope.
7. `dtl_label` MUST be present; missing labels default to `CONFIDENTIAL`. Labels MUST NOT be downgraded from the source data classification.
8. `credentials` is the ONLY field permitted to carry secrets; it MUST be stripped before logging or TrustFlow emission.
9. The entire envelope MUST be validated before dispatching to any handler — no partial processing.
10. All validation failures MUST emit a TrustFlow event with `event_type=ENVELOPE_REJECTED` and fail closed.