# AGENTS.md - Forge Platform

Forge is a security-first enforcement platform and operator-gated AI development system that validates identity with CTX-ID, enforces policy with VTZ and DTL, emits synchronous TrustFlow audit events, and fails closed on every trust, policy, crypto, and boundary decision.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID first at every enforcement entry point and reject immediately on failure with no partial processing.
2. Check VTZ policy before executing any agent action or cross-boundary operation and deny implicitly unless explicit authorization exists.
3. Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path — async buffering is forbidden and emission failures MUST NOT be silently skipped.
4. Treat missing, expired, rotated, or invalid CTX-ID as `UNTRUSTED` and never infer identity from session context, transport context, or prior state. CTX-ID tokens are immutable once issued.
5. Assign DTL labels at data ingestion, keep them immutable, inherit the HIGHEST source classification for derived data, and treat unlabeled data as `CONFIDENTIAL` until explicitly reclassified.
6. Fail closed on all auth, crypto, identity, policy, and trust errors — reject the action, log the event, and surface the failure to the caller. Never silently continue.
7. Validate every write path with `path_security.validate_write_path()` before any file write and never write outside approved roots — no exceptions.
8. Treat all external input as untrusted, including documents, PR comments, CI output, XPC messages, agent prompts, and generated code — validate or scan it before use. Context from external documents goes in USER prompt, never SYSTEM prompt.
9. Never execute generated or external content with `eval()`, `exec()`, `subprocess` of generated content, `shell=True`, dynamic import, or any equivalent code-loading path.
10. Never bypass `SECURITY_REFUSAL` — if output contains `SECURITY_REFUSAL`, stop the workflow immediately. Do not retry, rephrase, route to another provider, or auto-continue. Gate for operator action and log the refusal.
11. Discard and log unknown XPC message types instead of raising transport-breaking exceptions.
12. Wait indefinitely for operator input at every gate — never auto-approve, auto-merge, or auto-continue through a blocked approval step. The human is in the loop at every gate.
13. Never hardcode secrets, tokens, credentials, or cryptographic material; never log keys, tokens, secrets, or cleartext payloads; never include them in error messages.

## Architecture Overview

Enforcement order: **CTX-ID validation → VTZ policy check → Action execution → TrustFlow emission → DTL label verification on data egress**.

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; action routing through VTZ policy; binds actions to VTZ | Process any action before CTX-ID validation completes; execute actions before policy evaluation |
| **TrustLock** | `src/trustlock/` | TPM-anchored machine identity and CTX-ID validation against TrustLock public key | Accept software-only identity validation; bypass TPM anchor |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Structural policy boundaries per agent session; cross-zone authorization; decides authorization before execution | Allow implicit cross-VTZ tool calls; apply policy changes mid-session |
| **DTL** (Data Trust Labels) | `src/dtl/` | Classification labels at ingestion; label inheritance for derived data; label verification before boundary crossing | Permit unlabeled outbound data without `CONFIDENTIAL` handling; allow label mutation after assignment; allow derived data at a lower classification than any source |
| **TrustFlow** | `src/trustflow/` | Immutable, synchronous, append-only audit event emission for every action outcome | Buffer events asynchronously; silently skip or drop failed emissions |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Explicit policy decisions for every enforcement query | Act as advisory-only logic; return permissive defaults on policy lookup failure |

## Naming Lint Rule

All code, comments, documentation, and configuration MUST use the canonical Forge subsystem names exactly as specified:

| Canonical Name | Prohibited Variants |
|---|---|
| `CTX-ID` | `ctx_id`, `ctxid`, `CtxId`, `context-id`, `context_id`, `contextId` |
| `VTZ` | `vtz`, `Vtz`, `virtual-trust-zone`, `trustZone`, `trust_zone` |
| `TrustFlow` | `trustflow`, `trust_flow`, `trust-flow`, `TRUSTFLOW`, `audit_stream`, `auditStream` |
| `DTL` | `dtl`, `Dtl`, `data-trust-label`, `dataLabel`, `data_label` |
| `TrustLock` | `trustlock`, `trust_lock`, `trust-lock`, `TRUSTLOCK` |
| `CAL` | `cal`, `Cal`, `conversation-abstraction-layer`, `conversationLayer` |
| `MCP` | `mcp`, `Mcp`, `policy-engine`, `policyEngine` |

A CI lint scanner MUST reject any commit containing a prohibited variant in source files, configuration, documentation, or comments. The scanner covers `*.py`, `*.ts`, `*.js`, `*.md`, `*.yaml`, `*.yml`, `*.toml`, `*.json`, and `*.cfg` files. No exceptions, no suppression comments.

## Development Workflow

- Every PR MUST pass CTX-ID validation, VTZ policy check, DTL label check, and TrustFlow emission verification in CI before merge.
- Every PR MUST pass the naming lint scanner with zero prohibited-variant findings.
- Generated code is never executed by the agent — code generation output is written to files for human review only.
- All tests MUST assert fail-closed behavior: missing CTX-ID → reject; expired CTX-ID → reject; missing VTZ policy → deny; TrustFlow emission failure → block action; unlabeled data → CONFIDENTIAL.
- Test coverage MUST include negative cases for every enforcement boundary.