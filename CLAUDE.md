# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data with immutable Data Trust Labels (DTL), and emits every outcome to an append-only TrustFlow audit stream.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST validate CTX-ID FIRST — validation failure means immediate rejection, no partial processing, no fallback.
2. Check VTZ policy BEFORE execution of every agent action — VTZ boundaries are structural, not advisory, and cannot be bypassed by application code. Never allow implicit cross-VTZ tool calls; cross-VTZ calls MUST be explicitly authorized.
3. Emit a synchronous TrustFlow event for every action outcome (allow, restrict, block) in the enforcement path — async buffering is forbidden. Failed emission is a WARN-level audit event, never a silent skip.
4. Treat missing, expired, rotated, or invalid CTX-ID as UNTRUSTED — never infer identity from ambient context. CTX-ID tokens are immutable once issued; rotation creates a new token and immediately invalidates the old one.
5. Assign DTL labels at data ingestion; labels are immutable once assigned. Derived data inherits the HIGHEST classification of any source. Unlabeled data is treated as CONFIDENTIAL. Never permit untracked label stripping or downgrade of inherited classifications.
6. All trust, identity, policy, and cryptographic failures MUST fail closed — reject the action, log the event, surface to caller, never silently continue.
7. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, audit records, prompts, or cleartext payloads — error messages include `component`, `operation`, `failure_reason`, and `ctx_id` only.
8. All external input (documents, PR comments, CI output, XPC messages, user prompts, file paths) is untrusted — validate strictly before use. Context from external documents goes in USER prompt, never SYSTEM prompt.
9. Generated code is never executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True`, no dynamic interpretation of external content.
10. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions.
11. Audit records are append-only — no modification, no deletion. Every security-relevant action generates an audit record BEFORE execution. Replay MUST be possible from the audit stream alone.
12. SECURITY_REFUSAL output is never bypassed by rephrasing or retrying with another provider — stop, gate, log.
13. Gates wait indefinitely for operator input — auto-approve is forbidden.
14. Discard and log unknown XPC message types — never raise them as uncaught exceptions.

## Architecture Overview


Enforcement order: CTX-ID validation → VTZ policy check → Action execution → TrustFlow emission → Audit record


| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point, VTZ policy gating before action execution, TrustFlow emission after every outcome | Must NOT process any action before CTX-ID validation; must NOT emit TrustFlow asynchronously |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Binds each session to exactly one VTZ, authorizes cross-VTZ calls explicitly, enforces structural boundaries | Must NOT permit advisory-only boundaries, implicit cross-VTZ tool calls, or mid-session policy mutation |
| **TrustLock** (Machine Identity) | `src/trustlock/` | Cryptographic machine identity and CTX-ID validation using TrustLock public key and TPM-anchored trust | Must NOT accept software-only validation or mutable issued tokens |
| **TrustFlow** (Audit Stream) | `src/trustflow/` | Append-only audit/event emission for every action outcome, synchronous in enforcement path | Must NOT buffer asynchronously, skip failed emissions silently, or allow modification/deletion of records |
| **DTL** (Data Trust Labels) | `src/dtl/` | Immutable label assignment at ingestion, label inheritance (highest classification), label verification before trust-boundary crossings | Must NOT permit untracked label stripping, label mutation, or classification downgrade |
| **MCP** (Policy Engine) | `src/mcp/` | Explicit, reproducible policy decisions for agent actions | Must NOT hide decision rationale or bypass VTZ enforcement |
| **Path Security** | `src/path_security/` | Write-path validation via `validate_write_path()` for all file operations | Must NOT allow any file write without prior validation |