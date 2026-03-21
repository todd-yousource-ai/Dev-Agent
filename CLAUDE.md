# CLAUDE.md - Forge Platform

Forge is a security-first autonomous development platform that enforces explicit trust, identity, policy, labeling, audit, and human-gated execution across every agent action. Every agent action is bound to a cryptographically verified identity (CTX-ID), checked against policy boundaries (VTZ), labeled at ingestion (DTL), and emits an immutable audit stream (TrustFlow).

## Critical Rules - Read Before Writing Any Code

1. Validate `CTX-ID` first at every enforcement entry point and reject immediately on failure with no partial processing.
2. Check `VTZ` policy before executing any action and deny cross-`VTZ` operations unless explicitly authorized.
3. Emit a synchronous `TrustFlow` event for every action outcome (`allow`, `restrict`, `block`) and never silently skip emission failures.
4. Treat missing, expired, rotated, malformed, or unverifiable `CTX-ID` as `UNTRUSTED` and fail closed.
5. Assign `DTL` labels at ingestion, keep them immutable, and treat unlabeled data as `CONFIDENTIAL` until explicitly reclassified. Label inheritance MUST use highest classification wins.
6. Never infer trust, identity, authorization, or classification implicitly from runtime context, prior state, or caller assumptions.
7. Fail closed on all trust, identity, policy, and cryptographic errors; reject the action, log the event, and surface the failure to the caller.
8. Validate all external input as untrusted, including documents, PR comments, CI output, XPC messages, and generated content.
9. Never execute generated code or external content via `eval()`, `exec()`, dynamic import, `shell=True`, or subprocess execution of generated artifacts.
10. Validate every file write with `path_security.validate_write_path()` before writing to disk.
11. Never hardcode secrets, tokens, credentials, or cryptographic material. Secrets MUST never appear in logs, error messages, audit records, or generated code.
12. Gates wait indefinitely for operator input; never auto-approve, never bypass `SECURITY_REFUSAL`, and never retry around it by rephrasing, retrying with another provider, or suppressing.
13. Discard and log unknown XPC message types instead of raising uncaught exceptions or attempting fallback processing.
14. Audit records are append-only, generated BEFORE execution, and MUST NOT contain secrets, keys, tokens, or cleartext sensitive data.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → VTZ policy check → Action execution → TrustFlow emission → Audit record**.

- `src/cal/` — **CAL** (Conversation Abstraction Layer): enforcement entry points. Enforces `CTX-ID` validation first, then `VTZ` policy, then execution, then `TrustFlow` emission. MUST NOT partially process actions before identity and policy checks.
- `src/vtz/` — **VTZ** (Virtual Trust Zones): structural policy boundaries per session. Binds each agent session to exactly one `VTZ`. MUST NOT allow implicit cross-zone tool calls or bypass by application code.
- `src/trustflow/` — **TrustFlow**: append-only synchronous audit/event stream. Records every action outcome synchronously in the enforcement path. MUST NOT buffer asynchronously or omit required fields.
- `src/dtl/` — **DTL** (Data Trust Labels): immutable classification labels assigned at ingestion. Verifies labels before trust-boundary crossing. Label inheritance uses highest classification wins. MUST NOT mutate labels after assignment or allow silent stripping without audit.
- `src/trustlock/` — **TrustLock**: cryptographic machine identity anchored to hardware `TrustLock` public-key validation. Validates `CTX-ID` cryptographically. MUST NOT accept software-only validation.
- `src/mcp/` — **MCP Policy Engine**: evaluates authorization and policy decisions before action execution. MUST NOT act as advisory-only logic — decisions are binding.
- `src/rewind/` — **Forge Rewind**: deterministic replay engine. Replays from append-only TrustFlow audit stream. MUST NOT mutate state during replay.

## Branding Constants

Python branding constants are defined in `forge/branding.py`. All user-facing strings, product names, and platform identifiers MUST reference constants from this module. Never hardcode branding strings inline.

## File & Module Conventions

- All new modules MUST follow the existing directory layout under `src/`.
- Every module that performs enforcement MUST follow the enforcement order: CTX-ID → VTZ → Execute → TrustFlow → Audit.
- Test files MUST validate that enforcement failures result in closed-state rejection, not silent continuation.
- Configuration files MUST NOT contain secrets — use environment variables or secret-manager references only.