# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels all data by classification (DTL), and emits an immutable audit stream (TrustFlow) — with all failures failing closed.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST validate CTX-ID FIRST — before any other processing; validation failure means immediate rejection with no partial processing.
2. TrustFlow events MUST be emitted synchronously in the enforcement path for every action outcome (allow, restrict, block) — async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
3. VTZ policy MUST be checked BEFORE execution of any agent action; cross-VTZ tool calls require explicit policy authorization — implicit access is denied.
4. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to caller — never silently continue.
5. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, or cleartext payloads.
6. All external input (documents, PR comments, CI output) is untrusted and MUST be validated strictly before use; context from external documents goes in the USER prompt, never the SYSTEM prompt.
7. Generated code is never executed by the agent — no `eval`, no `exec`, no subprocess of generated content.
8. Gates wait indefinitely for operator input — no auto-approve ever.
9. All file writes MUST be path-validated via `path_security.validate_write_path()` before execution.
10. DTL labels are assigned at data ingestion and are immutable; derived data inherits the HIGHEST classification of any source; unlabeled data MUST be treated as CONFIDENTIAL.
11. CTX-ID tokens are IMMUTABLE once issued; expired or missing CTX-ID MUST be rejected — never infer identity from context; validation MUST use TrustLock public key.
12. Build memory and build rules are never cleared automatically — they are persistent learning systems; per-PR stage checkpoints prevent re-running completed work after a crash.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → VTZ policy check → DTL label verification → action execution → TrustFlow emission → audit record**.

| Subsystem | Path | Enforces | Must NOT |
|-----------|------|----------|----------|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Processes agent actions; calls CTX-ID validation first on every entry point | Never execute an action without CTX-ID validation and VTZ policy check |
| **DTL** (Data Trust Labels) | `src/dtl/` | Assigns immutable classification labels at ingestion; enforces label inheritance | Never strip or downgrade a label without audited policy authorization |
| **TrustFlow** | `src/trustflow/` | Emits append-only audit events for every action outcome synchronously | Never buffer asynchronously; never skip emission silently |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Structural policy boundaries per agent session; one VTZ per CTX-ID | Never allow implicit cross-VTZ access; never apply policy changes mid-session |
| **TrustLock** | `src/trustlock/` | TPM-anchored cryptographic machine identity; CTX-ID issuance and validation | Never validate CTX-ID in software-only mode; never modify tokens post-issuance |
| **MCP Policy Engine** | `src/mcp/` | Policy evaluation and decision rendering | Never suggest policy — enforce it |
| **Forge Rewind** | `src/rewind/` | Replay engine for forensic reconstruction from audit stream | Never depend on external state — replay from audit stream alone |
| **Connector SDK** | `sdk/connector/` | Integration SDK for external tool connections | Never bypass VTZ enforcement at the SDK boundary |
| **Consensus Engine** | `src/consensus.py` | Dual-LLM code generation with Claude arbitration; `_score_fix()` for fix arbitration | Never use length-based fix arbitration (`max(fix, key=len)` is BANNED) |
| **Build Director** | `src/build_director.py` | Pipeline orchestration, confidence gating, PR-type routing | Never auto-approve a gate; never skip the lint or fix-loop stages |
| **GitHub Tools** | `src/github_tools.py` | `GitHubTool`, `WebhookReceiver` for repo operations | Never expose tokens in webhook payloads or logs |
| **Build Ledger** | `src/build_ledger.py` | Persistent build state and checkpoint tracking | Never clear state automatically |

**macOS Shell** (TRD-1): Swift 5.9+ / SwiftUI native container. Owns installation, biometric auth, Keychain secrets, XPC channel to Python backend, session lifecycle. Min macOS 13.0 (Ventura).

**XPC Channel**: Line-delimited JSON, nonce-authenticated, max 16 MB per message. Unknown message types are discarded and logged — never raised as exceptions.

## Interface Contracts - Mandatory Implementation Rules

### CTX-ID Contract
- Tokens are **IMMUTABLE** once issued — no field modification after issuance.
- Rotation creates a new token; old token is invalidated **immediately**.
- Expired CTX-ID MUST be rejected; clock skew tolerance is defined per deployment.
- Validation MUST use TrustLock public key — software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.

### CAL Enforcement Contract
- Every entry point processing an agent action MUST call CTX-ID validation **FIRST**.
- CTX-ID validation failure → immediate rejection, no partial processing.
- Every action MUST be checked against VTZ policy **BEFORE** execution.
- VTZ denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
- Every action outcome MUST emit a TrustFlow event.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

### TrustFlow Emission Contract
- Required fields: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash`.
- `event_id`: globally unique, generated via CSPRNG (not sequential).
- `ts`: UTC Unix timestamp, **millisecond** precision.
- `payload_hash`: SHA-256 of the serialized action payload.
- Emission MUST be **synchronous** in the enforcement path.
- Failed emission → WARN-level audit event.

### VTZ Enforcement Contract
- One VTZ per agent session, bound at CTX-ID issuance.
- Cross-VTZ tool calls require **explicit** policy authorization.
- VTZ boundaries are **structural** — application code cannot bypass enforcement.
- Policy changes take effect at **next** CTX-ID issuance, not mid-session.

### DTL Label Contract
- Labels assigned at **data ingestion**, immutable thereafter.
- Derived data inherits the **HIGHEST** classification of any source.
- Unlabeled data MUST be treated as `CONFIDENTIAL`.
- Label verification MUST occur before data crosses any trust boundary.
- Label stripping is a security event — MUST be audited and policy-controlled.

### Audit Contract
- Audit record generated **BEFORE** execution of every security-relevant action.
- Records are **APPEND-ONLY** — no modification, no deletion.
- Audit failures are non-fatal to agent operation but MUST be surfaced immediately.
- Records MUST NOT contain secrets, keys, tokens, or cleartext sensitive data.
- Full replay MUST be possible from audit stream alone.

### Consensus Engine Contract
- Always pass `language` parameter: `"python"` | `"swift"` | `"go"` | `"typescript"` | `"rust"`.
- `language="swift"` → `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`.
- `language="python"` → `GENERATION_SYSTEM`.
- Fix arbitration uses `_score_fix()` based on assertion token overlap — **never** response length.
- Fix loop strategy selected by `_choose_strategy(failure_type, attempt, records)`.

### XPC Protocol Contract
- Wire format: line-delimited JSON, nonce-authenticated, max 16 MB per message.
- `ready`: `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`: `{ card_type, stage, content, progress }` — streamed to `BuildStreamView`.
- `gate_card`: `{ gate_type, options[], description }` — blocks until operator responds.
- `credentials`: `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`: `{ doc_id, doc_name, status, chunk_count, embedded_count }`
- Unknown message types → discard and log. Never raise as exception.

## Wire Formats and Schemas

### XPC Messages (line-delimited JSON, nonce-authenticated)

```json
// ready
{ "agent_version": "string", "min_swift_version": "string", "capabilities": ["string"], "doc_store_status": "object" }

// build_card
{ "card_type": "string", "stage": "string", "content": "string", "progress": 0.0 }

// gate_card
{ "gate_type": "string", "options": ["string"], "description": "string" }

// credentials — NEVER log or persist outside Keychain
{ "anthropic_api_key": "string", "openai_api_key": "string", "github_token": "string", "engineer_id": "string" }

// doc_status
{ "doc_id": "string", "doc_name": "string", "status": "string", "chunk_count": 0, "embedded_count": 0 }
```

### TrustFlow Event

```json
{
  "event_id": "CSPRNG-generated UUID",
  "session_id": "string",
  "ctx_id": "string",
  "ts": 1719500000000,
  "event_type": "string",
  "payload_hash": "SHA-256 hex string"
}
```

### VTZEnforcementDecision

```json
{
  "verdict": "allow | restrict | block",
  "ctx_id": "string",
  "vtz_id": "string",
  "policy_ref": "string",
  "reason": "string",
  "ts": 1719500000000
}
```

## Error Handling Rules

**Universal rule**: All trust, identity, policy, and cryptographic failures MUST fail **closed** — reject the action, log the event, surface to caller.

| Failure Type | Required Response |
|---|---|
| CTX-ID validation failure | Immediate rejection. No partial processing. Log with `component`, `operation`, `failure_reason`. |
| CTX-ID expired | Reject. Do not auto-renew mid-session. |
| CTX-ID missing | Treat as `UNTRUSTED`. Reject. |
| VTZ policy denial | Produce `VTZEnforcementDecision` with `verdict=block`. Emit TrustFlow event. |
| Cross-VTZ implicit access | Deny. Log attempted boundary crossing. |
| TrustFlow emission failure | WARN-level audit event. Do NOT silently continue. |
| Cryptographic failure | Fail closed. Never degrade into insecure behavior. |
| Audit write failure | Non-fatal to agent operation. Surface immediately. |
| XPC unknown message type | Discard and log. Never raise as exception. |
| `SECURITY_REFUSAL` from LLM | Stop, gate, log. Never bypass by rephrasing. |
| Path validation failure | Reject file write. Log attempted path. |
| External input validation failure | Reject. Log source and failure reason. |

### Banned Patterns

```python
# BANNED — swallowed exception in enforcement code
try:
    enforce_policy(action)
except Exception:
    pass  # NEVER

# BANNED — length-based fix arbitration
winner = max(claude_fix, openai_fix, key=len)  # Use _score_fix()

# BANNED — executing generated code
eval(generated_code)       # NEVER
exec(generated_code)       # NEVER
subprocess.run(generated)  # NEVER

# BANNED — auto-approve
if timeout_reached:
    approve()  # Gates wait INDEFINITELY

# BANNED — implicit identity
if session_looks_valid:
    ctx_id = infer_from_context()  # NEVER — validate explicitly
```

**All errors MUST include**: `component`, `operation`, `failure_reason`, `ctx_id` (if available).
**All errors MUST NOT include**: keys, tokens, secrets, or cleartext payloads.

## Testing Requirements

- Enforcement path test coverage MUST be **≥ 90%**.
- Every enforcement path MUST have at least one **negative test** (rejection behavior).
- Every cryptographic operation MUST have a test with invalid/expired material.
- Every TrustFlow emission MUST be tested for both success and failure paths.
- Tests MUST NOT mock the enforcement decision — they may mock the external call but the enforcement logic MUST run.
- All parsing, policy, trust, and cryptographic logic MUST be tested against malformed inputs.
- Add a regression test for every material bug.
- Benchmark tests MUST exist for network, crypto, policy, and telemetry hot paths.
- Fuzzing MUST be used where inputs are complex, attacker-controlled, or parser-driven.
- Run existing tests before making changes: `cd src && pytest ../tests/ -v --tb=short`

## File Naming and Code Conventions

### Directory Structure
```
src/cal/           — Conversation Abstraction Layer components
src/dtl/           — Data Trust Label components
src/trustflow/     — TrustFlow audit stream components
src/vtz/           — Virtual Trust Zone enforcement
src/trustlock/     — Cryptographic machine identity (TPM-anchored)
src/mcp/           — MCP Policy Engine
src/rewind/        — Forge Rewind replay engine
sdk/connector/     — Forge Connector SDK
tests/<subsystem>/ — Tests mirror src/ structure exactly
```

### Python Backend (key files)
```
src/consensus.py       — ConsensusEngine, GENERATION_SYSTEM, SWIFT_GENERATION_SYSTEM + UI_ADDENDUM
src/build_director.py  — BuildPipeline orchestration, confidence gate, pr_type routing
src/github_tools.py    — GitHubTool, WebhookReceiver
src/build_ledger.py    — Persistent build state and checkpoints
```

### Swift Frontend (TRD-1)
- Swift 5.9+, SwiftUI, min macOS 13.0 (Ventura)
- `BuildStreamView` consumes `build_card` messages
- Keychain for all secret storage — never UserDefaults for credentials
- Biometric gate for authentication
- `os_log` with privacy annotations for all logging

### Naming Conventions
- Test files mirror source: `src/vtz/enforcer.py` → `tests/vtz/test_enforcer.py`
- Enforcement functions: prefix with `enforce_` or `validate_`
- Decision types: suffix with `Decision` (e.g., `VTZEnforcementDecision`)
- Event types: suffix with `Event` (e.g., `TrustFlowEvent`)
- All IDs generated via CSPRNG — never sequential

## Security Checklist - Before Every Commit

- [ ] CTX-ID validated at every enforcement entry point
- [ ] TrustFlow event emitted for every action outcome
- [ ] VTZ policy checked before cross-boundary operations
- [ ] DTL labels verified before data crosses trust boundaries
- [ ] No silent failure paths in trust/crypto/policy code
- [ ] No secrets, keys, or tokens in logs or error messages
- [ ] All external input validated before use
- [ ] No `eval`, `exec`, or subprocess of generated content
- [ ] All file writes path-validated via `path_security.validate_write_path()`
- [ ] External document context placed in USER prompt, never SYSTEM prompt
- [ ] FIPS-approved algorithms used for all cryptographic operations
- [ ] Test coverage includes at least one negative path per security boundary
- [ ] Audit records generated before execution, contain no secrets
- [ ] Gates block indefinitely — no auto-approve logic
- [ ] Error messages include component/operation/failure_reason but never secrets
- [ ] XPC messages validated; unknown types discarded and logged
- [ ] `_score_fix()` used for fix arbit