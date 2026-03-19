# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent systems that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) — all failing closed on any security, identity, or policy error.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — before any other processing occurs; validation failure means immediate rejection with no partial work. Missing CTX-ID is treated as UNTRUSTED — never infer identity from session state, transport context, or prior requests.
2. TrustFlow events MUST be emitted synchronously in the enforcement path for every action outcome (`allow`, `restrict`, `block`) — async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
3. VTZ policy MUST be checked BEFORE execution of any agent action — denial produces a `VTZEnforcementDecision` record with `verdict=block`; cross-VTZ tool calls require explicit policy authorization, implicit is denied. Mid-session policy mutation is forbidden.
4. DTL labels are assigned at data ingestion and are IMMUTABLE — derived data inherits the HIGHEST classification of any source; unlabeled data is treated as CONFIDENTIAL until explicitly reclassified. Labels MUST be verified before trust-boundary crossing. Downgrade, strip, or mutation of labels requires policy-controlled audited handling.
5. All trust, identity, policy, and cryptographic failures MUST fail CLOSED — reject the action, log the event, surface to caller with context; `try/except/pass` is BANNED in any enforcement code path.
6. Secrets, keys, tokens, and credentials MUST NEVER appear in logs, error messages, generated code, or cleartext payloads — no exceptions.
7. Generated code is NEVER executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content; `shell=True` is forbidden in all subprocess calls.
8. All external input (documents, PR comments, CI output, XPC messages, line-delimited JSON payloads) is UNTRUSTED — validate strictly before use; external document context goes in the USER prompt, never the SYSTEM prompt.
9. Gates wait indefinitely for operator input — no auto-approve ever; the human is in the loop at every gate. SECURITY_REFUSAL output is never bypassed by rephrasing — stop, gate, log.
10. All file writes MUST pass `path_security.validate_write_path()` before execution — no path traversal, no writes outside sanctioned directories.
11. CTX-ID tokens are IMMUTABLE once issued — rotation creates a new token and immediately invalidates the old one; expired CTX-ID is rejected; missing CTX-ID is treated as UNTRUSTED.
12. XPC unknown message types are discarded and logged — never raised as exceptions in the transport path.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → VTZ policy check → DTL label verification → Action execution → TrustFlow emission → Audit record**.

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; orchestrates the enforcement pipeline | Must NOT process any action before CTX-ID validation completes |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Binds each agent session to exactly one VTZ; decides boundary access; produces `VTZEnforcementDecision` records | Must NOT permit implicit cross-VTZ operations or mid-session policy mutation |
| **DTL** (Data Trust Labels) | `src/dtl/` | Assigns immutable labels at ingestion; verifies labels before trust-boundary crossing; enforces highest-classification inheritance on derived data | Must NOT downgrade, strip, or mutate labels without policy-controlled audited handling |
| **TrustFlow** | `src/trustflow/` | Emits synchronous audit events in the enforcement path for every action outcome | Must NOT buffer asynchronously or skip failed emission without WARN-level audit surfacing |
| **TrustLock** | `src/trustlock/` | Validates CTX-ID against TrustLock public key with hardware-backed cryptographic guarantees | Must NOT accept software-only validation or permit expired/missing CTX-ID |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Evaluates policy decisions for actions and cross-boundary operations; enforcement is authoritative | Must NOT act as advisory-only logic or defer enforcement to callers |
| **Rewind** (Forge Rewind) | `src/rewind/` | Reconstructs actions from TrustFlow audit stream for replay and forensic analysis | Must NOT modify or redact audit records during reconstruction |

## Build & Development

bash
# Build
swift build

# Test — all tests must pass before any PR merge
swift test

# Lint
swiftlint lint --strict


## Coding Standards

- Every public API in enforcement subsystems (CAL, VTZ, DTL, TrustFlow, TrustLock, MCP) MUST include CTX-ID as a required parameter.
- All enforcement decisions MUST be represented as typed enums or structs — never raw strings or untyped dictionaries.
- Error types in enforcement paths MUST be exhaustive — no catch-all `default` cases that silently swallow unknown error variants.
- All inter-subsystem communication MUST go through defined protocol interfaces — no direct struct access across module boundaries.
- XPC transport layer MUST validate message schema before dispatch — malformed messages are dropped and logged.
- No force-unwraps (`!`) in enforcement code paths — use explicit error handling.
- All cryptographic operations MUST use platform-provided frameworks (CryptoKit / Security.framework) — no vendored crypto implementations.