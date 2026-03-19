# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data via DTL, and emits an immutable TrustFlow audit stream — failing closed on any violation.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST; validation failure means immediate rejection — no partial processing, no fallback.
2. Missing CTX-ID MUST be treated as `UNTRUSTED`; identity MUST NEVER be inferred from session context, request origin, or prior state.
3. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event synchronously in the enforcement path — async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
4. VTZ policy MUST be checked BEFORE execution of any agent action; denial MUST emit a `VTZEnforcementDecision` with `verdict=block`; cross-VTZ tool calls require explicit policy authorization — implicit access is denied.
5. Every agent session MUST be bound to exactly one VTZ at CTX-ID issuance.
6. DTL labels are assigned at data ingestion and are immutable; derived data inherits the HIGHEST classification of any source; unlabeled data is treated as `CONFIDENTIAL`. Post-ingestion relabeling MUST NOT occur without explicit policy-controlled reclassification.
7. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to caller — never silently continue, never degrade into insecure fallback.
8. Secrets, keys, tokens, and credentials MUST NOT appear in logs, error messages, or generated code — ever.
9. Generated code is never executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content.
10. All external input (documents, PR comments, CI output) is untrusted; document context goes in the USER prompt, never the SYSTEM prompt; all input passes injection scanning before inclusion.
11. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions.
12. Gates wait indefinitely for operator input — no auto-approve, no timeout-based approval, ever.
13. `SECURITY_REFUSAL` output is terminal — never retry with rephrasing, never route to another provider; stop, gate, log.
14. XPC unknown message types are discarded and logged — never raised as exceptions, never processed.

## Architecture Overview

Forge is a two-process architecture. Always. No exceptions.

### Swift Shell (macOS app)
- **Owns**: SwiftUI interface (Navigator + BuildStream + ContextPanel), Touch ID biometric gate, Keychain storage for all credentials, XPC channel, Python process lifecycle.
- **MUST NOT**: call LLM APIs, read Keychain for the backend's direct use, execute generated code.

### Python Backend
- **Owns**: ConsensusEngine, BuildPipeline, GitHubTool, BuildLedger, DocumentStore, HolisticReview, TRDWorkflow, CommandRouter.
- **MUST NOT**: read Keychain directly, access the UI, persist credentials to disk, store credentials in env vars.

### Credential Flow (invariant)
Touch ID → Swift reads Keychain → delivers via XPC `credentials` message → Python stores in memory only.

### Enforcement Order
Every agent action follows this sequence:
1. **CTX-ID validation** — TrustLock public-key verification; software-only validation is valid only when hardware attestation is unavailable and policy explicitly permits it.
2. **VTZ policy check** — confirm the action is authorized within the bound VTZ; emit `VTZEnforcementDecision`.
3. **DTL label verification** — verify data labels before any trust-boundary crossing.
4. **MCP policy decision** — explicit, explainable policy decision before tool execution.
5. **Action execution** — only after all preceding checks pass.
6. **TrustFlow emission** — synchronous audit event emitted for the outcome.

## Module Directory Map

| Directory | Responsibility | MUST | MUST NOT |
|---|---|---|---|
| `src/cal/` | Conversation Abstraction Layer enforcement entry points | Validate CTX-ID first; check VTZ before action execution | Partially process invalid or unauthenticated actions |
| `src/vtz/` | Virtual Trust Zone enforcement | Enforce exactly-one-VTZ session binding; require explicit cross-VTZ authorization | Allow application code to bypass VTZ boundaries |
| `src/trustflow/` | TrustFlow audit stream emission | Synchronously emit structured events for every action outcome | Async-buffer enforcement-path emissions; silently drop failures |
| `src/dtl/` | Data Trust Label handling | Assign labels at ingestion; verify labels before trust-boundary crossings | Permit mutable post-ingestion relabeling without explicit policy-controlled reclassification |
| `src/trustlock/` | Cryptographic machine identity and CTX-ID validation | Validate against TrustLock public key; reject expired or rotated tokens | Skip validation; use software-only validation when TrustLock hardware attestation is required by policy |
| `src/mcp/` | MCP Policy Engine | Make explicit, explainable policy decisions before tool execution; log every decision | Execute tools before policy evaluation; auto-approve any tool invocation |

## TrustFlow Event Wire Format

Every TrustFlow event MUST contain exactly these fields:


{
  "event_id": "<UUID v4>",
  "session_id": "<UUID v4>",
  "ctx_id": "<CTX-ID string bound to session>",
  "ts": "<ISO-8601 UTC timestamp>",
  "event_type": "<allow | restrict | block>",
  "payload_hash": "<SHA-256 hex digest of action payload>"
}


- `event_id`: UUID v4 — unique per event, generated at emission time.
- `session_id`: UUID v4 — the agent session that produced this event.
- `ctx_id`: string — the validated CTX-ID bound to the session.
- `ts`: string — ISO-8601 UTC timestamp at emission.
- `event_type`: enum string — one of `allow`, `restrict`, `block`.
- `payload_hash`: string — SHA-256 hex digest of the serialized action payload.

No additional fields are permitted without schema versioning. Missing fields MUST cause emission failure (WARN-level audit event).

## VTZEnforcementDecision Wire Format


{
  "decision_id": "<UUID v4>",
  "ctx_id": "<CTX-ID string>",
  "vtz_id": "<VTZ identifier>",
  "action": "<requested action identifier>",
  "verdict": "<allow | block>",
  "reason": "<human-readable policy rationale>",
  "ts": "<ISO-8601 UTC timestamp>"
}


## XPC Message Contract

- Known message types are processed per their handler.
- Unknown message types MUST be discarded and logged at INFO level — never raised as exceptions, never processed.
- The `credentials` message type delivers secrets from Swift Keychain to Python backend in-memory storage only.
- Credentials received via XPC MUST NOT be written to disk, environment variables, logs, or error messages.