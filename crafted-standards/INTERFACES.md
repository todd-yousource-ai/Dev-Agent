# Interface Contracts - CraftedApp

## Data Structures

This document defines the required wire-level and implementation-facing contracts for the CraftedApp subsystem based on the provided TRD content.

All structured backend data **MUST** be represented as dataclasses in Python 3.12 with type annotations on every function.

### ConsensusRunRequest

Request contract for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Human-readable implementation task string. |
| `context` | `str` | Yes | Context string supplied to the consensus engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. Values must match exactly. |

#### Required invocation form

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### ConsensusRunResult

Result contract returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Final generated code artifact. |

### TrustFlowEvent

Every action outcome event emitted in the enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | Yes | Must be globally unique. Must be generated via CSPRNG, not sequential. |
| `session_id` | `str` | Yes | Session identifier for the agent session. |
| `ctx_id` | `str` | Yes | CTX-ID associated with the action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `str` | Yes | Event type for the action outcome. |
| `payload_hash` | `str` | Yes | Must be SHA-256 of the serialized action payload. |

### VTZEnforcementDecision

Record emitted when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `str` | Yes | Must be exactly `block` for VTZ policy denial. |

### CTXIDToken

Logical contract for CTX-ID tokens.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | Yes | Immutable once issued. |
| `vtz` | `str` | Yes | Every agent session is bound to exactly one VTZ at issuance. |
| `issued_at` | `number` | Yes | Token issuance timestamp. |
| `expires_at` | `number` | Yes | Expired CTX-ID must be rejected. |
| `public_key_binding` | `str` | Yes | Must validate against TrustLock public key. Software-only validation is rejected. |
| `status` | `str` | Yes | Old token must be invalidated immediately on rotation. |

> Note: The TRD content defines behavioral requirements for CTX-ID but does not provide a full serialized token schema. The above fields are the minimum contract implied by the requirements and must be preserved as immutable once issued.

### AgentActionPayload

Serialized action payload used for enforcement and hashing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `str` | Yes | Must correspond to the agent session. |
| `ctx_id` | `str` | Yes | Must be validated first. |
| `action` | `str` | Yes | Action being requested by the agent. |
| `payload` | `object` | Yes | Serialized before SHA-256 computation for `payload_hash`. |

## Enums and Constants

### SupportedLanguage

Exact allowed values for `ConsensusRunRequest.language`:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

### Language System Selection

| `language` value | Selected system |
|---|---|
| `swift` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords detected |
| `python` | `GENERATION_SYSTEM` |

No other system-selection mappings are defined in the provided TRD content.

### VTZ Verdict Values

| Value | Meaning |
|---|---|
| `block` | VTZ policy denied the action |

### Security Refusal Sentinel

| Value | Meaning |
|---|---|
| `SECURITY_REFUSAL` | When output by the LLM: stop, gate, log. Never retry to bypass. |

### Forbidden Patterns

These values and usages are non-conformant and must not appear in implementation logic:

#### Python / general

- `shell=True`
- `eval()`
- `exec()`

#### Fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Must not be used. Fix arbitration must use `_score_fix()`.

#### Swift

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

## Validation Rules

## Entry Point Enforcement Order

Every entry point that processes an agent action **MUST** apply validation in this order:

1. **CTX-ID validation FIRST**
2. Immediate rejection on CTX-ID validation failure
3. **VTZ policy check BEFORE execution**
4. If denied, produce `VTZEnforcementDecision` with `verdict=block`
5. Emit a `TrustFlowEvent` for every action outcome: allow, restrict, block
6. If TrustFlow emission fails, do not silently continue; log and surface the failure

## TrustFlow Validation

A `TrustFlowEvent` is valid only if all of the following are true:

- `event_id` is present
- `session_id` is present
- `ctx_id` is present
- `ts` is present
- `event_type` is present
- `payload_hash` is present
- `event_id` is globally unique
- `event_id` is generated with CSPRNG, not sequential generation
- `ts` is a UTC Unix timestamp with millisecond precision
- `payload_hash` equals the SHA-256 of the serialized action payload
- emission is synchronous in the enforcement path
- async buffering is not permitted
- failed emission is a WARN-level audit event, not a silent skip

## CTX-ID Validation

A CTX-ID is valid only if all of the following are true:

- token is present; missing CTX-ID must be treated as `UNTRUSTED`
- token has not expired
- token validates against the TrustLock public key
- token has not been invalidated by rotation
- token fields have not been modified after issuance

Additional rules:

- CTX-ID tokens are immutable once issued
- CTX-ID rotation creates a new token
- old token is invalidated immediately
- expired CTX-ID must be rejected
- clock skew tolerance is deployment-defined
- never infer identity from context when CTX-ID is missing

## VTZ Enforcement Validation

A VTZ-bound session is valid only if:

- every agent session is bound to exactly one VTZ at CTX-ID issuance
- cross-VTZ tool calls have explicit policy authorization
- implicit authorization is denied
- VTZ boundaries are structural and cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session

## Consensus Engine Validation

Consensus invocation is conformant only if:

- `language` is always passed
- `language` is one of:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`

Loop/fix behavior rules:

- fix loop strategy must use `_choose_strategy(failure_type, attempt, records)`
- strategy selection is failure-type-aware
- fix arbitration must use `_score_fix()`
- response length must not be used for arbitration

## Security Validation

The subsystem is non-conformant if any of the following occur:

- credentials, API keys, tokens, or secrets are hardcoded as string literals
- subprocess calls use `shell=True`
- generated or external content is passed to `eval()` or `exec()`
- HTTP response bodies are logged
- file paths are written without `path_security.validate_write_path()` before write
- loaded document chunks are included in any LLM prompt without injection scanning
- context from external documents is placed in the SYSTEM prompt instead of the USER prompt
- `SECURITY_REFUSAL` is retried to bypass the refusal

Required behavior:

- log status codes and error types only for HTTP failures
- all disk write paths must pass `path_security.validate_write_path()`
- all loaded document chunks must pass injection scanning before inclusion in any LLM prompt
- external document context goes in the USER prompt, never the SYSTEM prompt
- on `SECURITY_REFUSAL`: stop, gate, log

## Python Backend Conformance Rules

All CraftedApp Python backend components must satisfy:

- Python `3.12`
- type annotations on every function
- `async/await` throughout the backend
- no blocking calls on the event loop
- dataclasses for all structured data
- tests use `pytest`
- tests live in `tests/` and mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- test coverage must be `≥ 85%` on all new modules
- `pyyaml` must be in `requirements.txt`

## Wire Format Examples

## Valid Payloads

### Valid ConsensusRunRequest

```json
{
  "task": "Implement: Add login flow",
  "context": "Relevant implementation context",
  "language": "python"
}
```

### Valid TrustFlowEvent

```json
{
  "event_id": "7f3e7db3-7aa7-4a86-a7f2-7d4e59d5d9c0",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678.123,
  "event_type": "allow",
  "payload_hash": "4d967a4aa3c61e37b5b5b2f1b3d7c8c8d9e2c8f4d92f9a1c2e5d0a6b7c8d9e0f"
}
```

### Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Valid AgentActionPayload

```json
{
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "action": "tool.invoke",
  "payload": {
    "tool": "repo.read",
    "resource": "src/app.py"
  }
}
```

## Invalid Payloads

### Invalid ConsensusRunRequest: missing language

```json
{
  "task": "Implement: Add login flow",
  "context": "Relevant implementation context"
}
```

Reason: `language` is required and must always be passed.

### Invalid ConsensusRunRequest: unsupported language

```json
{
  "task": "Implement: Add login flow",
  "context": "Relevant implementation context",
  "language": "java"
}
```

Reason: `language` must be exactly one of `python`, `swift`, `go`, `typescript`, `rust`.

### Invalid TrustFlowEvent: missing payload_hash

```json
{
  "event_id": "7f3e7db3-7aa7-4a86-a7f2-7d4e59d5d9c0",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678.123,
  "event_type": "allow"
}
```

Reason: every TrustFlow event must include `payload_hash`.

### Invalid VTZEnforcementDecision: wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason: VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

### Invalid CTX-ID usage: missing token

```json
{
  "session_id": "sess_123",
  "action": "tool.invoke",
  "payload": {
    "tool": "repo.read"
  }
}
```

Reason: missing CTX-ID must be treated as `UNTRUSTED`; identity must never be inferred from context.

## Integration Points

## Consensus Engine

Call contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Integration requirements:

- `language` must always be supplied
- `spec.language` must be one of the supported values
- `result.final_code` is the output artifact
- `swift` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM`
- `python` selects `GENERATION_SYSTEM`

## Enforcement Path

All agent action entry points integrate the following sequence:

1. CTX-ID validator
2. VTZ policy evaluator
3. VTZ decision recorder
4. TrustFlow emitter

The enforcement path must be synchronous for event emission. Async buffering is not permitted for TrustFlow emission.

## TrustLock

CTX-ID validation must integrate with TrustLock public key validation.

Required behavior:

- software-only validation is rejected
- TrustLock public key validation is mandatory

## Path Security

Before any file write, integration must call:

- `path_security.validate_write_path()`

No file write is conformant without this validation.

## Prompt Construction / LLM Safety

When integrating external document content:

- perform injection scanning on all loaded document chunks before prompt inclusion
- place external document context in the USER prompt
- never place external document context in the SYSTEM prompt

On LLM output `SECURITY_REFUSAL`:

- stop
- gate
- log
- never retry to bypass

## Testing and Tooling

Required integration checks:

- run existing tests before making changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```

- tests must use `pytest`
- lint must pass with `ruff`
- type checking must pass with `mypy`

## Non-Conformance Summary

A CraftedApp component is non-conformant if it fails any required contract in this document, including but not limited to:

- missing or invalid `language` in consensus calls
- CTX-ID not validated first
- VTZ policy not enforced before execution
- missing TrustFlow emission
- TrustFlow emitted without required fields
- asynchronous buffering in the enforcement path
- missing TrustLock public key validation
- unsafe file writes without `path_security.validate_write_path()`
- use of forbidden fix arbitration by response length
- use of forbidden security patterns or unsafe Swift/backend credential access patterns