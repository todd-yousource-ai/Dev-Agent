# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces structural policy boundaries (VTZ), labels all data at ingestion (DTL), validates machine identity via hardware-anchored cryptography (TrustLock), and emits an immutable synchronous audit stream (TrustFlow) — with every failure failing closed.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID first at every enforcement entry point — before any other processing occurs; validation failure means immediate rejection with no partial processing.
2. Validate CTX-ID against the TrustLock public key anchored to hardware trust — NEVER accept software-only identity validation.
3. Treat missing CTX-ID as `UNTRUSTED` — NEVER infer identity from session context, transport metadata, or prior state.
4. CTX-ID tokens are IMMUTABLE once issued; expired CTX-IDs MUST be rejected.
5. Check VTZ policy BEFORE executing any action or cross-boundary tool call — deny implicitly unless explicit policy authorization exists; VTZ boundaries are structural, not advisory; application code MUST NOT bypass enforcement.
6. Each agent session MUST be bound to exactly one VTZ — implicit cross-VTZ calls and mid-session policy changes are forbidden.
7. Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path — async buffering is forbidden; failed emission is a WARN-level audit event, NEVER a silent skip.
8. Assign DTL labels at data ingestion — labels are immutable; unlabeled data MUST be treated as `CONFIDENTIAL` until explicitly reclassified; derived data inherits the HIGHEST classification of any source; unlabeled or downgraded data MUST NOT cross trust boundaries without explicit policy control and audit.
9. Fail closed on ALL trust, identity, policy, and cryptographic errors: reject the action, log the event, surface the failure to the caller — NEVER silently continue.
10. NEVER log or persist secrets, keys, tokens, credentials, or cleartext sensitive payloads in logs, error messages, audit records, or generated code — error messages include component, operation, failure_reason, and ctx_id only.
11. Treat ALL external input as untrusted — including documents, PR comments, CI output, XPC messages, and generated content — validate strictly before use; context from external documents goes in the USER prompt, NEVER the SYSTEM prompt.
12. NEVER execute generated code or external content via `eval()`, `exec()`, dynamic loading, or subprocess execution of generated artifacts — no exceptions.
13. Validate every write path with `path_security.validate_write_path()` BEFORE writing any file to disk — no path bypasses.
14. Gates wait indefinitely for operator input — NEVER auto-approve, auto-merge, auto-bypass `SECURITY_REFUSAL`, or silently resolve divergence.
15. `try/except/pass` is BANNED in all enforcement code paths — every exception MUST be caught, logged with context, and surfaced.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → TrustLock cryptographic verification → VTZ policy check → Action execution → TrustFlow emission → Audit record**.

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Processes agent actions; calls CTX-ID validation first, VTZ policy second, emits TrustFlow on every outcome | Execute actions before CTX-ID validation and VTZ policy evaluation; swallow validation failures |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Binds each agent session to exactly one VTZ; enforces structural policy boundaries; denies implicitly unless explicit authorization exists | Permit implicit cross-VTZ calls; allow mid-session policy changes; treat boundaries as advisory |
| **DTL** (Data Trust Labels) | `src/dtl/` | Labels data at ingestion; enforces label immutability, inheritance, and verification at trust boundaries | Allow unlabeled data to cross trust boundaries; permit label stripping or downgrade without explicit policy control and audit |
| **TrustFlow** | `src/trustflow/` | Emits append-only synchronous audit events with complete required fields (event_id, ctx_id, timestamp, action, outcome, component, vtz_id) for every enforcement decision | Buffer asynchronously in place of synchronous emission; drop failed events silently; omit required fields |
| **TrustLock** | `src/trustlock/` | Validates CTX-ID using public-key material anchored to hardware trust; provides cryptographic machine identity | Accept software-only identity validation; cache or reuse expired cryptographic material |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Evaluates authorization and policy for cross-boundary tool calls and agent operations against VTZ-scoped rules | Permit unauthorized cross-boundary calls; bypass VTZ policy evaluation; auto-approve without operator gate |

## Naming Constants

| Canonical Name | Type | Description |
|---|---|---|
| `CTX-ID` | `string` | Cryptographically verified context identity token, immutable once issued |
| `VTZ` | `string` | Virtual Trust Zone identifier scoping an agent session's policy boundary |
| `DTL` | `enum` | Data Trust Label classification assigned at ingestion (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`) |
| `TrustFlow` | `event stream` | Append-only synchronous audit emission for all enforcement decisions |
| `TrustLock` | `crypto identity` | Hardware-anchored public-key identity used to validate CTX-ID |
| `CAL` | `subsystem` | Conversation Abstraction Layer — enforcement sequencing entry point |
| `MCP` | `subsystem` | Policy engine for authorization evaluation |
| `SECURITY_REFUSAL` | `outcome` | Explicit agent refusal on security grounds — MUST NOT be auto-bypassed |

## Cross-TRD Glossary

| Term | Definition | Authoritative TRD |
|---|---|---|
| **CTX-ID** | A cryptographically signed, immutable identity token bound to an agent session. Validated against TrustLock public-key material at every enforcement entry point. Missing CTX-ID = `UNTRUSTED`. Expired CTX-ID = rejected. | TRD: Identity & Trust |
| **VTZ (Virtual Trust Zone)** | A structural policy boundary scoping exactly one agent session. All actions MUST be authorized against VTZ policy before execution. Cross-VTZ calls require explicit MCP policy authorization. Mid-session VTZ changes are forbidden. | TRD: Policy & Boundaries |
| **DTL (Data Trust Label)** | An immutable classification label (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`) assigned at data ingestion. Derived data inherits the highest source classification. Unlabeled data defaults to `CONFIDENTIAL`. Label downgrade requires explicit policy control and audit. | TRD: Data Classification |
| **TrustFlow** | The synchronous, append-only audit event stream. Every enforcement decision emits a TrustFlow event with required fields: `event_id`, `ctx_id`, `timestamp`, `action`, `outcome`, `component`, `vtz_id`. Async buffering is forbidden. Failed emission is WARN-level, never silent. | TRD: Audit & Observability |
| **TrustLock** | The hardware-anchored cryptographic identity subsystem. Provides public-key material for CTX-ID validation. Software-only validation is forbidden. | TRD: Cryptographic Identity |
| **CAL (Conversation Abstraction Layer)** | The enforcement sequencing entry point for all agent actions. Enforces: CTX-ID validation → VTZ policy check → action execution → TrustFlow emission. | TRD: Agent Operations |
| **MCP (Policy Engine)** | Evaluates authorization for cross-boundary tool calls and agent operations against VTZ-scoped policy rules. | TRD: Policy Evaluation |
| **Fail Closed** | On any trust, identity, policy, or cryptographic error: reject the action, log the event, surface the failure. Never silently continue, degrade, or auto-approve. | All TRDs |
| **Operator Gate** | A human-approval checkpoint that waits indefinitely. No auto-approve, no auto-merge, no auto-bypass of `SECURITY_REFUSAL`, no silent divergence resolution. | TRD: Operator Controls |
| **SECURITY_REFUSAL** | An explicit refusal outcome emitted when an agent action is blocked on security grounds. MUST be surfaced to the caller and MUST NOT be auto-bypassed or silently resolved. | TRD: Agent Operations |