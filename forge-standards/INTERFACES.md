# Interface Contracts - Crafted

This document defines the wire-format and API contract reference for the Crafted subsystem, derived from the provided TRD excerpts and Forge component interface contracts.

## Data Structures

### ConsensusRunRequest

Request passed to the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Free-form task description. Example source usage: `f"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string supplied to the consensus engine. External document context must go in the USER prompt, never the SYSTEM prompt. All loaded document chunks must pass injection scanning before inclusion. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. Exact allowed values are: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. |

#### Semantics
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output. |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | Must be exactly `block` when produced for a VTZ policy denial. |

#### Semantics
- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Audit/event record emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique. Must be generated using CSPRNG; sequential identifiers are forbidden. |
| `session_id` | `string` | Yes | Session identifier for the agent session. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. Missing CTX-ID must be treated as untrusted. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event classification for the action outcome. |
| `payload_hash` | `string` | Yes | Must be SHA-256 of the serialized action payload. |

#### Semantics
- Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and must not be silently skipped.

---

### CTXIDToken

Logical token contract for CTX-ID validation and binding.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. |
| `vtz` | `string` | Yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance. |
| `expires_at` | `number \| string` | Yes | Expired CTX-ID must be rejected. Clock skew tolerance is deployment-defined. |
| `public_key_binding` | `string` | Yes | Must validate against TrustLock public key. Software-only validation is rejected. |

#### Semantics
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token; the old one is invalidated immediately.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from surrounding context when `ctx_id` is absent.

---

### FixArbitrationInput

Logical input to fix arbitration.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `string` | Yes | Used by `_choose_strategy(failure_type, attempt, records)`. |
| `attempt` | `integer` | Yes | Retry/fix attempt number. |
| `records` | `array` | Yes | Strategy-selection context records. |

#### Semantics
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- A static lookup table is non-conformant.

---

### FixCandidateScoringInput

Logical input to fix scoring.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `assertion_tokens` | `array<string>` | Yes | Tokens derived from assertions for overlap scoring. |
| `candidate_response` | `string` | Yes | Fix candidate content to score. |

#### Semantics
- Fix arbitration must use `_score_fix()` based on assertion token overlap.
- Length-based selection is forbidden.

---

### PathWriteRequest

Logical contract for file writes in Crafted-related backend flows.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `path` | `string` | Yes | Must pass `path_security.validate_write_path()` before any write. |
| `content` | `string \| bytes` | Yes | Content to write after path validation succeeds. |

---

### SecurityRefusalEvent

Represents a gated stop condition from the LLM.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `output_type` | `string` | Yes | Must be exactly `SECURITY_REFUSAL`. |
| `logged` | `boolean` | Yes | Must be `true` once the refusal is gated and logged. |
| `retried` | `boolean` | Yes | Must be `false`. Never retry to bypass. |

---

## Enums and Constants

### Language

Exact allowed values:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

---

### Trust Decision Outcomes

Action outcomes that must emit a TrustFlow event:

- `allow`
- `restrict`
- `block`

---

### Special Output Types

- `SECURITY_REFUSAL`

---

### Required System Selectors

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

---

### Required Functions / Hooks

These names are contract-significant and must be used exactly as referenced by implementations:

- `_choose_strategy(failure_type, attempt, records)`
- `_score_fix()`
- `path_security.validate_write_path()`

---

### Logging / Severity Requirements

- Failed TrustFlow emission: `WARN-level audit event`

---

### Forbidden Patterns

These are explicitly non-conformant interface/behavior patterns.

#### Length-based fix arbitration
```python
winner = max(claude_fix, openai_fix, key=len)
```

#### Swift force unwrap
```swift
let value = optional!
```

#### LLM API call from Swift
```swift
let client = AnthropicClient(apiKey: keychainValue)
```

#### Keychain read for backend
```swift
let token = KeychainKit.read("github_token")
```

#### Forbidden backend behavior
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.

---

## Validation Rules

## 1. Entry Point Enforcement

Every entry point that processes an agent action must satisfy all of the following, in order:

1. Call CTX-ID validation first.
2. On CTX-ID validation failure, reject immediately.
3. Perform no partial processing before CTX-ID validation passes.
4. Check the action against VTZ policy before execution.
5. If VTZ denies, produce `VTZEnforcementDecision` with `verdict=block`.
6. Emit a TrustFlow event for every action outcome.
7. If TrustFlow emission fails, do not silently continue; log and surface the failure.

---

## 2. Consensus Engine Request Validation

A `ConsensusRunRequest` is valid only if:

- `task` is present and is a string.
- `context` is present and is a string.
- `language` is present and equals one of:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`

Additional rules:

- Language must always be passed.
- External document chunks in `context` must pass injection scanning before inclusion.
- External document context must be included in the USER prompt, never the SYSTEM prompt.

---

## 3. Fix Strategy Validation

Valid fix-loop behavior requires:

- Strategy selection via `_choose_strategy(failure_type, attempt, records)`.
- No static lookup-table strategy replacement.
- Arbitration via `_score_fix()`.
- No length-based arbitration.

---

## 4. TrustFlow Event Validation

A `TrustFlowEvent` is valid only if:

- `event_id` is present, unique, and non-sequential.
- `session_id` is present.
- `ctx_id` is present for trusted flows.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `event_type` is present.
- `payload_hash` is present and equals SHA-256 of the serialized action payload.

Operational rules:

- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Emission failure must produce a WARN-level audit event.

---

## 5. CTX-ID Validation

A `CTXIDToken` is valid only if:

- It validates against the TrustLock public key.
- It is not expired.
- It has not been invalidated by rotation.
- It has not been modified after issuance.

Additional rules:

- Software-only validation is rejected.
- Rotation must create a new token and invalidate the old token immediately.
- Missing CTX-ID means `UNTRUSTED`.
- Identity must never be inferred when CTX-ID is missing.

---

## 6. VTZ Validation

VTZ enforcement is valid only if:

- Each agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structurally enforced and cannot be bypassed by application code.
- VTZ policy changes take effect at the next CTX-ID issuance, not mid-session.

---

## 7. File Write Validation

Before any disk write:

- The target path must pass `path_security.validate_write_path()`.
- No write may occur before validation succeeds.

---

## 8. Security Validation

The following are mandatory:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies; log status codes and error types only.
- When `SECURITY_REFUSAL` is returned by the LLM: stop, gate, log, and do not retry.

---

## 9. Python Backend Contract

For Python implementations in Crafted:

- Python version: `3.12`
- Type annotations on every function.
- `async/await` throughout the backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- Tests must use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage on all new modules must be `>= 85%`.
- `pyyaml` must be in `requirements.txt`.

---

## Wire Format Examples

## Valid Payloads

### Valid `ConsensusRunRequest`
```json
{
  "task": "Implement: Add crafted validation",
  "context": "User-supplied context that has passed injection scanning.",
  "language": "python"
}
```

### Valid `ConsensusRunResult`
```json
{
  "final_code": "from dataclasses import dataclass\n"
}
```

### Valid `TrustFlowEvent`
```json
{
  "event_id": "3f9c4c56-2fd8-4a5e-a3c4-6f4c1fbd1a21",
  "session_id": "sess_01HZX8K7YQ",
  "ctx_id": "ctx_01HZX8K80A",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961ff75c4b698d872f0e7a0b2"
}
```

### Valid `VTZEnforcementDecision`
```json
{
  "verdict": "block"
}
```

### Valid `SecurityRefusalEvent`
```json
{
  "output_type": "SECURITY_REFUSAL",
  "logged": true,
  "retried": false
}
```

---

## Invalid Payloads

### Invalid `ConsensusRunRequest` - missing language
```json
{
  "task": "Implement: Add crafted validation",
  "context": "Context"
}
```

Reason:
- `language` is required and must always be passed.

---

### Invalid `ConsensusRunRequest` - unsupported language
```json
{
  "task": "Implement: Add crafted validation",
  "context": "Context",
  "language": "java"
}
```

Reason:
- `language` must be one of: `python`, `swift`, `go`, `typescript`, `rust`.

---

### Invalid `VTZEnforcementDecision`
```json
{
  "verdict": "deny"
}
```

Reason:
- For VTZ policy denial, `verdict` must be exactly `block`.

---

### Invalid `TrustFlowEvent` - missing required fields
```json
{
  "event_id": "123",
  "event_type": "allow"
}
```

Reason:
- Missing `session_id`, `ctx_id`, `ts`, and `payload_hash`.
- `event_id` must be globally unique and non-sequential.

---

### Invalid `SecurityRefusalEvent`
```json
{
  "output_type": "SECURITY_REFUSAL",
  "logged": true,
  "retried": true
}
```

Reason:
- `SECURITY_REFUSAL` must not be retried.

---

### Invalid file write request
```json
{
  "path": "../../etc/passwd",
  "content": "data"
}
```

Reason:
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

---

## Integration Points

## Consensus Engine

Required invocation pattern:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Integration requirements:

- `language` must always be supplied.
- `spec.language` must resolve to one of the allowed `Language` values.
- Consumers must read generated code from `result.final_code`.

---

## Prompt Construction

- External document context must be placed in the USER prompt.
- External document context must never be placed in the SYSTEM prompt.
- All loaded document chunks must pass injection scanning before inclusion.

---

## Enforcement Pipeline

A conformant Crafted processing pipeline integrates these checks in this order:

1. CTX-ID validation
2. Immediate rejection on CTX-ID failure
3. VTZ policy check
4. VTZ denial record creation with `verdict=block`
5. TrustFlow event emission for outcome
6. Surface emission failures as logged WARN-level audit events

---

## TrustLock

CTX-ID validation must integrate with:

- TrustLock public key validation

Software-only validation is explicitly non-conformant.

---

## Filesystem Security

Any integration that writes files must call:

- `path_security.validate_write_path()`

before performing the write.

---

## Swift / Backend Boundary

Boundary contract:

- Only Swift reads Keychain.
- Swift may deliver secrets via XPC.
- Python backend reads nothing from Keychain.
- Swift code must not make LLM API calls directly.

---

## Tooling and Test Integration

Before implementation work:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Ongoing conformance requirements:

- `pytest`
- `ruff`
- `mypy`
- coverage `>= 85%` on new modules
- `pyyaml` present in `requirements.txt`

---

## Non-Conformance Summary

An implementation is non-conformant if any of the following occur:

- Omits `language` in consensus engine calls
- Uses unsupported `language` values
- Uses length-based fix arbitration
- Uses static fix strategy lookup instead of `_choose_strategy(failure_type, attempt, records)`
- Processes an action before CTX-ID validation
- Fails to reject immediately on CTX-ID validation failure
- Executes an action before VTZ policy evaluation
- Fails to emit a TrustFlow event for `allow`, `restrict`, or `block`
- Silently ignores TrustFlow emission failure
- Performs software-only CTX-ID validation
- Allows implicit cross-VTZ calls
- Writes a file before `path_security.validate_write_path()` succeeds
- Retries after `SECURITY_REFUSAL`
- Logs HTTP response bodies
- Uses `shell=True`
- Uses `eval()` or `exec()`
- Reads Keychain from Python
- Makes LLM API calls from Swift