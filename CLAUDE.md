# CLAUDE.md - Forge Platform

Forge is a secure-by-default trust-enforcement platform for AI agent operations. It binds every agent action to a cryptographically verified identity (CTX-ID), enforces structural policy boundaries (VTZ), assigns and preserves immutable data classification labels (DTL), produces a synchronous immutable audit stream (TrustFlow), and fails closed on all trust, identity, policy, and cryptographic violations.

## Critical Rules — Read Before Writing Any Code

1. **CTX-ID first.** Every enforcement entry point MUST call CTX-ID validation FIRST — before any processing, parsing, or side effects occur.
2. **Reject invalid identity immediately.** CTX-ID validation failure MUST result in immediate rejection. Never partially process an action with an invalid, expired, or missing CTX-ID.
3. **Never infer identity.** Treat a missing CTX-ID as `UNTRUSTED`. Never infer identity from session context, transport headers, or prior requests.
4. **VTZ before execution.** VTZ policy MUST be checked BEFORE execution of any agent action. Enforcement is structural, not advisory; application code MUST NOT bypass it. Never allow implicit cross-VTZ tool calls.
5. **Synchronous TrustFlow on every outcome.** Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event synchronously in the enforcement path. Async buffering in the enforcement path is forbidden. The `payload_hash` field MUST NOT be omitted.
6. **TrustFlow emission failure is auditable.** TrustFlow emission failure MUST be logged as a WARN-level audit event and surfaced to the caller — never silently skipped.
7. **Fail closed — always.** All trust, identity, policy, auth, crypto, and enforcement failures MUST fail closed: reject the action, log the event, surface to the caller. Never degrade into permissive behavior. Never silently continue.
8. **Never swallow enforcement exceptions.** `try/except/pass`, silent `continue`, and best-effort bypasses are banned in all enforcement code paths.
9. **No secrets in output.** Secrets, keys, tokens, credentials, and cleartext sensitive payloads MUST never appear in logs, error messages, audit records, generated code, or TrustFlow event payloads.
10. **DTL labels are immutable and inherited.** DTL labels are assigned at data ingestion and are immutable. Derived data inherits the HIGHEST classification of any source. Unlabeled data MUST be treated as `CONFIDENTIAL`. DTL labels MUST be verified before any data crosses a trust boundary. Unlabeled outbound data is forbidden.
11. **Validate all write paths.** All file writes MUST pass `path_security.validate_write_path()` before execution.
12. **Never execute generated or external content.** No `eval()`, no `exec()`, no subprocess execution of generated code, no `shell=True`.
13. **Gates wait indefinitely.** Gates MUST wait indefinitely for operator input. No auto-approve, no auto-merge, no auto-resolve of security decisions — ever.
14. **SECURITY_REFUSAL is terminal.** A `SECURITY_REFUSAL` output MUST NOT be bypassed by rephrasing. Stop, gate, log.
15. **XPC unknown types are discarded.** Unknown XPC message types MUST be discarded and logged. Never raise transport-breaking exceptions for unknown types.
16. **External input is untrusted.** All external input (documents, PR comments, CI output, XPC messages) is untrusted and MUST be validated strictly before use. Context from external documents goes in the USER prompt, never the SYSTEM prompt.

## Architecture Overview

Enforcement order for every agent action:

**CTX-ID validation → VTZ policy check → Action execution → TrustFlow emission → Audit record**

| Subsystem | Path | Enforces | MUST NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Processes agent actions; calls CTX-ID validation first, VTZ policy second, emits TrustFlow on every outcome | Execute any action before CTX-ID validation, VTZ policy check, and TrustFlow emission requirements are satisfied |
| **TrustFlow** | `src/trustflow/` | Immutable, append-only synchronous audit event stream for every action outcome; every event includes `payload_hash` | Buffer asynchronously in the enforcement path; drop events silently; omit `payload_hash` |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Structural policy boundaries per agent session; exactly one VTZ per session, bound at CTX-ID issuance | Permit implicit cross-VTZ operations; allow mid-session policy mutation without re-validation |
| **DTL** (Data Trust Labels) | `src/dtl/` | Assigns immutable classification labels at ingestion; enforces highest-classification inheritance on derived data | Permit unlabeled outbound data; strip labels without audit and policy control |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity; validates CTX-ID against the TrustLock public key with hardware-anchored enforcement | Fall back to software-only validation when hardware anchoring is available |
| **MCP Policy Engine** | `src/mcp/` | Evaluates authorization and tool policy decisions; returns enforcement-grade allow/deny results | Return advisory-only results when enforcement is required |
| **Rewind** | `src/rewind/` | Audit replay and forensic rollback of TrustFlow event streams | Mutate or delete historical audit records |

## Error Taxonomy — Shared Structured Error Types

All enforcement subsystems MUST use the shared error taxonomy defined below. Every error MUST include `error_code`, `category`, `subsystem`, `message`, and `ctx_id` (or `"UNTRUSTED"` if CTX-ID is absent). Errors MUST NOT contain secrets, keys, tokens, or cleartext sensitive payloads.

### Error Categories

| Category | Prefix | Fail Behavior | Description |
|---|---|---|---|
| `IDENTITY` | `E_ID_` | Fail closed; reject | CTX-ID validation, expiry, format, or absence errors |
| `POLICY` | `E_VTZ_` | Fail closed; reject | VTZ boundary violations, cross-VTZ attempts, policy load failures |
| `CLASSIFICATION` | `E_DTL_` | Fail closed; reject | DTL label missing, invalid, inheritance conflict, or boundary crossing without label |
| `AUDIT` | `E_TF_` | Fail closed; WARN log + surface to caller | TrustFlow emission failure, missing required fields, stream unavailability |
| `CRYPTO` | `E_CRYPTO_` | Fail closed; reject | Signature verification failure, key unavailability, TrustLock hardware anchor missing |
| `AUTH` | `E_AUTH_` | Fail closed; reject | MCP authorization denial, tool policy rejection, scope violation |
| `TRANSPORT` | `E_XPC_` | Discard + log; no exception raised | Unknown XPC message types, malformed transport frames |
| `PATH` | `E_PATH_` | Fail closed; reject | Write-path validation failure from `path_security.validate_write_path()` |
| `EXECUTION` | `E_EXEC_` | Fail closed; reject | Attempted execution of generated/external content; `eval`/`exec`/subprocess violation |

### Structured Error Type

All enforcement errors MUST conform to this structure:

python
@dataclass(frozen=True)
class ForgeError:
    error_code: str        # e.g., "E_ID_EXPIRED", "E_VTZ_CROSS_BOUNDARY"
    category: str          # One of: IDENTITY, POLICY, CLASSIFICATION, AUDIT, CRYPTO, AUTH, TRANSPORT, PATH, EXECUTION
    subsystem: str         # One of: cal, vtz, dtl, trustlock, trustflow, mcp, rewind, path_security
    message: str           # Human-readable; MUST NOT contain secrets or cleartext payloads
    ctx_id: str            # The CTX-ID under validation, or "UNTRUSTED" if absent/invalid
    timestamp: str         # ISO 8601 UTC
    action: str            # The action that was attempted (e.g., "tool_invoke", "file_write", "data_export")
    resolution: str        # One of: "rejected", "discarded", "gated", "logged_warn"


### Canonical Error Codes

| Error Code | Category | Subsystem | Meaning |
|---|---|---|---|
| `E_ID_MISSING` | IDENTITY | trustlock | No CTX-ID provided; treated as UNTRUSTED |
| `E_ID_INVALID` | IDENTITY | trustlock | CTX-ID failed cryptographic validation |
| `E_ID_EXPIRED` | IDENTITY | trustlock | CTX-ID has expired |
| `E_ID_FORMAT` | IDENTITY | trustlock | CTX-ID is malformed |
| `E_VTZ_NO_POLICY` | POLICY | vtz | No VTZ policy bound for session |
| `E_VTZ_CROSS_BOUNDARY` | POLICY | vtz | Implicit cross-VTZ operation attempted |
| `E_VTZ_POLICY_DENIED` | POLICY | vtz | Action denied by VTZ policy |
| `E_VTZ_MUTATION` | POLICY | vtz | Mid-session policy mutation attempted without re-validation |
| `E_DTL_UNLABELED` | CLASSIFICATION | dtl | Data has no DTL label; treated as CONFIDENTIAL |
| `E_DTL_BOUNDARY` | CLASSIFICATION | dtl | Labeled data attempted to cross trust boundary without verification |
| `E_DTL_STRIP` | CLASSIFICATION | dtl | Label removal attempted without audit/policy control |
| `E_DTL_INHERITANCE` | CLASSIFICATION | dtl | Derived data did not inherit highest source classification |
| `E_TF_EMIT_FAIL` | AUDIT | trustflow | TrustFlow event emission failed |
| `E_TF_MISSING_HASH` | AUDIT | trustflow | TrustFlow event missing required `payload_hash` |
| `E_TF_STREAM_UNAVAIL` | AUDIT | trustflow | TrustFlow audit stream is unavailable |
| `E_CRYPTO_SIG_FAIL` | CRYPTO | trustlock | Signature verification failed |
| `E_CRYPTO_KEY_UNAVAIL` | CRYPTO | trustlock | Required cryptographic key is unavailable |
| `E_CRYPTO_HW_MISSING` | CRYPTO | trustlock | Hardware anchor unavailable; software fallback denied |
| `E_AUTH_DENIED` | AUTH | mcp | MCP policy engine denied authorization |
| `E_AUTH_SCOPE` | AUTH | mcp | Tool call outside authorized scope |
| `E_XPC_UNKNOWN_TYPE` | TRANSPORT | cal | Unknown XPC message type received; discarded |
| `E_XPC_MALFORMED` | TRANSPORT | cal | Malformed XPC transport frame; discarded |
| `E_PATH_INVALID` | PATH | path_security | Write path failed `validate_write_path()` |
| `E_PATH_TRAVERSAL` | PATH | path_security | Path traversal attempt detected |
| `E_EXEC_GENERATED` | EXECUTION | cal | Attempted execution of generated content |
| `E_EXEC_EXTERNAL` | EXECUTION | cal | Attempted execution of external/untrusted content |

### Error Handling Rules

1. Every `ForgeError` with `resolution: "rejected"` MUST also emit a TrustFlow event with the error details (excluding secrets).
2. Every `ForgeError` with `resolution: "logged_warn"` (AUDIT category) MUST be logged at WARN level and surfaced to the caller.
3. Every `ForgeError` with `resolution: "discarded"` (TRANSPORT category) MUST be logged but MUST NOT raise an exception.
4. Every `ForgeError` with `resolution: "gated"` MUST block until operator input; no timeout, no auto-resolve.
5. `ForgeError` instances are immutable (`frozen=True`). Never mutate an error after creation.
6. Never catch a `ForgeError` with a bare `except` or `except Exception: pass`. All enforcement errors MUST propagate or be explicitly handled per category rules above.