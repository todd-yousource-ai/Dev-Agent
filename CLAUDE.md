# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) — all enforced locally on macOS through a two-process architecture (Swift shell + Python backend) connected by XPC.

## Critical Rules - Read Before Writing Any Code

1. **Fail closed on every auth, crypto, identity, and policy error** — never degrade silently, never fall back to permissive behavior.
2. **Validate CTX-ID FIRST at every enforcement entry point** — CTX-ID validation failure MUST result in immediate rejection with zero partial processing. Treat missing CTX-ID as `UNTRUSTED` and never infer identity from session context, transport context, or prior state.
3. **Emit a TrustFlow event for every action outcome (allow, restrict, block)** — emission is synchronous in the enforcement path; async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
4. **Check VTZ policy BEFORE execution of any agent action** — VTZ boundaries are structural, not advisory; implicit cross-VTZ calls are denied; enforcement cannot be bypassed by application code.
5. **Never put secrets, keys, tokens, or credentials in logs, error messages, or generated code** — Python receives credentials via XPC `credentials` message and holds them in memory only, never in env vars or on disk.
6. **Never execute generated code** — no `eval()`, no `exec()`, no `subprocess` of LLM-generated content, ever.
7. **All external input (documents, PR comments, CI output) is untrusted** — validate strictly; external document context goes in the USER prompt, never the SYSTEM prompt.
8. **All file writes MUST pass `path_security.validate_write_path()` before execution** — no exceptions.
9. **Gates wait indefinitely for operator input** — no auto-approve, no timeout-based approval, ever.
10. **DTL labels are assigned at data ingestion and are immutable** — derived data inherits the HIGHEST classification of any source; unlabeled data is treated as CONFIDENTIAL.
11. **Audit records are append-only, generated BEFORE execution, and MUST NOT contain secrets** — replay must be possible from the audit stream alone.
12. **If a `SECURITY_REFUSAL` output is returned, stop — do not retry, rephrase, or bypass** — gate the event, log it, surface it to the operator.
13. **Discard and log unknown XPC message types** — never raise them as unhandled exceptions and never continue processing as if valid.

## Architecture Overview

**Two-process architecture. Always. No exceptions.**

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **Swift Shell** | macOS app (SwiftUI) | UI, Touch ID biometric gate, Keychain storage, XPC channel, Python process lifecycle | Call LLM APIs, read Keychain for the backend, execute generated code |
| **Python Backend** | `src/` | ConsensusEngine, BuildPipeline, GitHub, Ledger, DocumentStore, HolisticReview, TRDWorkflow, CommandRouter | Read Keychain directly, access UI, persist credentials to disk |

### Subsystem Contracts

- **`src/cal/`** — Conversation Abstraction Layer enforcement entry points. MUST validate CTX-ID first. MUST NOT partially process an action before identity validation. CTX-ID validation decorates every action entry point.
- **`src/vtz/`** — Virtual Trust Zone policy enforcement. MUST decide authorization before execution. MUST NOT allow implicit cross-VTZ tool calls. VTZ boundaries are structural; enforcement cannot be bypassed by application code.
- **`src/dtl/`** — Data Trust Label assignment and verification. MUST assign labels at ingestion. MUST NOT permit unlabeled data to cross a trust boundary. Derived data inherits the HIGHEST classification of any source.
- **`src/trustflow/`** — TrustFlow event emission. MUST synchronously emit events with required fields (`ctx_id`, `action`, `outcome`, `timestamp`, `vtz_scope`, `dtl_label`) in the enforcement path. MUST NOT buffer asynchronously. Failed emission is a WARN-level audit event.
- **`src/trustlock/`** — Cryptographic machine identity and CTX-ID validation against TrustLock public key. MUST enforce hardware-anchored validation. MUST NOT allow software-only validation fallback.
- **`src/mcp/`** — MCP Policy Engine. MUST provide explicit policy decisions consumed by enforcement code. MUST NOT act as advisory-only logic. Policy decisions are `ALLOW`, `RESTRICT`, or `BLOCK` — never implicit.
- **`src/rewind/`** — Forge Rewind replay engine. MUST support full replay from append-only audit state. MUST NOT depend on mutable external state for reconstruction.
- **`sdk/connector/`** — Forge Connector SDK. MUST preserve all Forge enforcement contracts (CTX-ID, VTZ, DTL, TrustFlow) at integration boundaries. MUST NOT weaken or omit enforcement at the boundary.

## XPC Message Contract

- Swift Shell sends `credentials` message type to Python Backend — Python holds in memory only.
- Unknown XPC message types are discarded and logged; never raised as unhandled exceptions.
- XPC is the ONLY channel between the two processes. No shared files, no sockets, no environment variables.

## TrustFlow Event Required Fields

Every TrustFlow event MUST include:
- `ctx_id` — the validated CTX-ID of the acting agent
- `action` — the action name being performed
- `outcome` — one of `allow`, `restrict`, `block`
- `timestamp` — ISO 8601 UTC timestamp
- `vtz_scope` — the VTZ boundary in which the action was evaluated
- `dtl_label` — the DTL classification of the data involved
- `audit_hash` — append-only chain hash linking to the previous audit record

## Versioning

Forge follows strict semantic versioning:
- **MAJOR** — breaking changes to enforcement contracts (CTX-ID, VTZ, DTL, TrustFlow wire formats, XPC message types)
- **MINOR** — new enforcement capabilities, new subsystems, new TrustFlow event types that do not break existing contracts
- **PATCH** — bug fixes, documentation updates, non-contract-affecting changes

The canonical version is stored in `VERSION` at the repository root. All build artifacts, audit records, and TrustFlow events MUST reference this version. The `VERSION` file contains a single line in the format `MAJOR.MINOR.PATCH` with no prefix and no trailing newline.