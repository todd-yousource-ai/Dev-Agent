# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform where every agent action is identity-bound, policy-gated, audit-logged, and cryptographically verifiable — and the Consensus Dev Agent is its native macOS AI coding agent that decomposes build intents into ordered PRs through parallel LLM generation, 3-pass review, CI execution, and operator-gated merging.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — validation failure means immediate rejection with zero partial processing. Treat missing CTX-ID as `UNTRUSTED` and never infer identity from ambient context, session state, or caller location.
2. Every action MUST be checked against VTZ policy BEFORE execution — implicit cross-VTZ access is denied, always. Enforce exactly one VTZ binding per agent session at CTX-ID issuance. Emit a `VTZEnforcementDecision` record with `verdict=block` on denial.
3. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event synchronously in the enforcement path — async buffering is forbidden; never silently skip emission failures.
4. All trust, identity, policy, cryptographic, and authorization failures MUST fail closed: reject, log, surface — never silently continue.
5. Never hardcode secrets, tokens, credentials, or cryptographic material; never log them; never include them in error messages, audit records, test fixtures, or generated code.
6. All external input (documents, PR comments, CI output, XPC messages, user prompts, generated content) is untrusted — validate strictly before parsing or use; external document context goes in the USER prompt, never the SYSTEM prompt.
7. Generated code is never executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True`, no equivalent code-loading path.
8. DTL labels are assigned at data ingestion and are immutable — derived data inherits the HIGHEST classification of any source; unlabeled data is `CONFIDENTIAL` until explicitly reclassified.
9. Gates wait indefinitely for operator input — no auto-approve, ever.
10. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions.
11. If a component emits `SECURITY_REFUSAL`, do not retry, do not rephrase, do not switch providers to bypass — stop, gate, log.
12. XPC unknown message types are discarded and logged — never raised as exceptions; XPC wire format is line-delimited JSON, nonce-authenticated, max 16 MB per message.

## Architecture Overview

Forge is a two-process system: a Swift shell (UI, auth, Keychain, XPC) and a Python backend (consensus, pipeline, GitHub). Enforcement order for every agent action: **CTX-ID validation → VTZ policy check → action execution → TrustFlow emission → audit record**.

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; action abstraction; must validate CTX-ID first, check VTZ second, execute third, emit TrustFlow fourth | Never process an action without CTX-ID validation first; never perform partial processing before identity validation |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Structural policy boundaries per session; cross-VTZ denial; exactly one VTZ binding per agent session | Never allow application code to bypass zone boundaries; never allow implicit cross-VTZ access |
| **TrustFlow** | `src/trustflow/` | Synchronous audit event emission for every action outcome; append-only audit stream | Never buffer asynchronously; never silently skip failed emissions; never drop events |
| **DTL** (Data Trust Labels) | `src/dtl/` | Immutable classification at ingestion; label verification before boundary crossing; derived-data inherits highest source classification | Never permit mutable or stripped labels without policy-controlled audit; never allow unlabeled data to cross trust boundaries without `CONFIDENTIAL` default |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity; CTX-ID validation against TrustLock public key; hardware-anchored validation | Never accept software-only validation when hardware anchoring is available; never skip CTX-ID cryptographic verification |
| **Path Security** | `src/path_security/` | Write-path validation for all file operations via `validate_write_path()` | Never allow a file write without prior path validation |
| **XPC Bridge** | `src/xpc/` | Line-delimited JSON wire format; nonce authentication; 16 MB max message size; unknown message type discard-and-log | Never raise exceptions on unknown XPC message types; never exceed wire format limits; never skip nonce authentication |
| **Consensus Pipeline** | `src/consensus/` | Parallel LLM generation; 3-pass review; CI execution gating; operator-gated merging | Never auto-approve a gate; never merge without operator confirmation; never execute generated code |

## Enforcement Contract

Every subsystem entry point MUST enforce this exact order:

1. **CTX-ID Validation** — Verify identity is present, cryptographically valid against TrustLock, and not `UNTRUSTED`. Reject immediately on failure.
2. **VTZ Policy Check** — Confirm the action is permitted within the caller's bound VTZ. Emit `VTZEnforcementDecision` with `verdict=block` on denial.
3. **Action Execution** — Perform the requested operation only after steps 1 and 2 succeed.
4. **TrustFlow Emission** — Synchronously emit the audit event recording the action outcome (`allow`, `restrict`, or `block`) before returning control to the caller.
5. **Audit Record** — Persist the complete enforcement chain for post-hoc verification.

No step may be reordered, skipped, or deferred.