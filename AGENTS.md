# AGENTS.md - Forge Platform

Forge is a security-first trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces structural policy boundaries (VTZ), labels all data at ingestion (DTL), emits an immutable audit stream (TrustFlow) for every decision, and defaults to deny on any failure — never degrading silently on trust, identity, policy, or cryptographic failures.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — before any processing, parsing, or side effects occur. CTX-ID validation failure MUST immediately reject the request with no partial processing, no fallback, no silent degradation.
2. Treat missing CTX-ID as `UNTRUSTED` — NEVER infer identity from session context, transport context, or prior state.
3. Check VTZ policy before executing any agent action or cross-boundary operation — deny implicitly unless explicit policy authorization exists. VTZ boundaries are structural and non-bypassable.
4. Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path — async buffering is prohibited. NEVER silently skip emission failures.
5. Assign DTL labels at data ingestion — labels are immutable. Derived data inherits the HIGHEST classification of any source. Unlabeled data is `CONFIDENTIAL` until explicitly reclassified. Verify labels before any trust-boundary crossing.
6. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to caller — NEVER silently continue, NEVER fall back to insecure behavior.
7. Secrets, keys, tokens, credentials, and cleartext sensitive payloads MUST NEVER appear in logs, error messages, audit records, or generated code.
8. All external input (documents, PR comments, CI output, user prompts, XPC messages, generated artifacts) is untrusted — validate strictly before use. External document context goes in USER prompt, NEVER SYSTEM prompt.
9. Generated code is NEVER executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True`, no shell interpolation.
10. `SECURITY_REFUSAL` output is terminal — NEVER retry with rephrasing, NEVER bypass. Stop, gate, and log.
11. Gate cards block indefinitely for operator input — no auto-approve, no auto-merge, no timeout-based approval, ever.
12. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions, no bypass for "temporary" files.
13. Discard and log unknown XPC message types — NEVER raise them as uncaught exceptions in the message-handling path.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID → VTZ → CAL → DTL → Action → TrustFlow → Audit**.

- `src/cal/` — **Conversation Abstraction Layer (CAL)** enforces entry-point processing order: `CTX-ID validation → VTZ policy check → execution → TrustFlow emission`. It MUST NOT execute any action before CTX-ID validation and VTZ policy check complete.
- `src/vtz/` — **Virtual Trust Zone (VTZ)** binds each session to exactly one VTZ and blocks unauthorized cross-VTZ calls. It MUST NOT allow implicit cross-VTZ access or mid-session policy mutation without explicit re-authorization.
- `src/trustlock/` — **TrustLock** validates CTX-ID against the TrustLock public key with hardware-backed or approved validation paths. It MUST NOT accept software-only validation where TrustLock hardware-backed validation is required.
- `src/trustflow/` — **TrustFlow** emits synchronous, immutable audit events with required fields (`ctx_id`, `vtz_id`, `action`, `outcome`, `timestamp`, `dtl_label`) for every outcome. It MUST NOT buffer asynchronously in the enforcement path or drop failed emissions silently.
- `src/dtl/` — **Data Trust Labeling (DTL)** assigns immutable labels at ingestion and enforces highest-source inheritance on derived data. It MUST NOT permit unlabeled boundary crossing or untracked label stripping. Label removal MUST emit an audit event.
- `src/mcp/` — **MCP Policy** enforces Model Context Protocol boundaries. It MUST validate all MCP tool invocations against VTZ policy before dispatch.

## Naming and Terminology Lint Rules

All code, comments, documentation, and audit output MUST use canonical Forge terminology:

| Canonical Name | Prohibited Variants |
|---|---|
| `CTX-ID` | `ctx_id` (in prose), `context-id`, `contextId`, `context_identifier`, `session-id` (when referring to cryptographic identity) |
| `VTZ` | `trust-zone`, `trustzone`, `TZ`, `zone`, `sandbox` (when referring to Virtual Trust Zone) |
| `TrustFlow` | `trust_flow`, `trust-flow`, `audit-stream`, `event-log` (when referring to the TrustFlow subsystem) |
| `DTL` | `data-label`, `datalabel`, `trust-label`, `classification` (when referring to the DTL subsystem) |
| `TrustLock` | `trust_lock`, `trust-lock`, `identity-lock` |
| `CAL` | `conversation-layer`, `abstraction-layer`, `cal` (lowercase in subsystem references) |
| `SECURITY_REFUSAL` | `security_refusal` (lowercase), `sec-refusal`, `refusal`, `denial` (when referring to terminal refusal output) |

### Prohibited-Variants Scanner

- CI MUST run a naming lint pass on every PR that scans all `.rs`, `.swift`, `.py`, `.md`, `.toml`, and `.yaml` files for prohibited variants.
- Any prohibited variant found in code identifiers (variable names, struct fields, function names), string literals used in audit/log output, comments, or documentation MUST fail the lint check.
- Exception: `ctx_id` as a Rust/Python field name or variable name is permitted in code (snake_case convention); the prohibition applies to prose, documentation, comments, and user-facing strings where `CTX-ID` is the correct form.
- The scanner configuration lives at `tools/naming_lint.toml` and MUST be updated whenever a new canonical term is added.
- Lint failures block merge — no override without Security Lead approval logged in TrustFlow.

## Development Workflow

- Run all tests before committing: tests validate enforcement order, CTX-ID rejection paths, VTZ boundary isolation, DTL label inheritance, and TrustFlow emission completeness.
- Every PR MUST include tests for any new enforcement path covering: CTX-ID valid, CTX-ID missing, CTX-ID invalid, VTZ authorized, VTZ denied, DTL labeled, DTL unlabeled, TrustFlow event emitted.
- NEVER commit code that introduces a new enforcement entry point without CTX-ID validation as the first operation.
- NEVER commit code that crosses a VTZ boundary without an explicit policy check.
- NEVER commit code that ingests data without assigning a DTL label.
- NEVER commit code that produces an action outcome without a synchronous TrustFlow event.
- The naming lint scanner MUST pass before merge on every PR.