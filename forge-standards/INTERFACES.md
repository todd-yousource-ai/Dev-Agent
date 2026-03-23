# Interface Contracts - CraftedDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the CraftedDevAgent subsystem, derived strictly from the provided TRD content.

Where the TRD specifies exact field names, values, and constraints, they are reproduced exactly.

---

### Consensus Run Request

Used when invoking the consensus engine.

#### Structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Free-form task description. Example source usage: `"Implement: {spec.title}"` |
| `context` | `string` | yes | Context string passed to the consensus engine |
| `language` | `string` | yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Required invocation pattern

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

#### Notes

- `language` is mandatory.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### Consensus Run Result

Returned from the consensus engine invocation.

#### Structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Final generated code output |

No other result fields are defined in the supplied TRD content.

---

### VTZEnforcementDecision

Produced when VTZ policy denies an action.

#### Structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | Must be exactly `block` when produced for VTZ policy denial |

#### Required behavior

- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

No additional fields are specified in the supplied TRD content.

---

### TrustFlow Event

Every action outcome must emit a TrustFlow event.

#### Structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique; CSPRNG-generated, not sequential |
| `session_id` | `string` | yes | Session identifier |
| `ctx_id` | `string` | yes | CTX-ID associated with the action |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Event type identifier |
| `payload_hash` | `string` | yes | SHA-256 of the serialized action payload |

#### Required behavior

- Every TrustFlow event MUST include all six fields above.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

---

### CTX-ID Token

The supplied TRD defines lifecycle and validation constraints, but not a field-level schema.

#### Contracted properties

| Property | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Must be present on every entry point that processes an agent action |

#### Required behavior

- CTX-ID validation MUST occur FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- Missing `ctx_id` MUST be treated as `UNTRUSTED`.
- CTX-ID tokens are immutable once issued.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

No additional token fields are specified in the supplied TRD content.

---

### Agent Action Payload

The supplied TRD does not define a concrete action payload schema, but it defines enforcement obligations for any action payload.

#### Contracted properties

| Property | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Must be validated first |
| `action payload` | `object` | yes | Serialized form is used to compute `payload_hash` |

#### Required behavior

- Every action MUST be checked against VTZ policy BEFORE execution.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

No concrete field names beyond `ctx_id` are defined in the supplied TRD content.

---

## Enums and Constants

### Language

Allowed `language` values for consensus execution:

```text
"python"
"swift"
"go"
"typescript"
"rust"
```

---

### Verdict

Defined value from VTZ enforcement contract:

```text
block
```

---

### Action Outcomes

Defined action outcome values:

```text
allow
restrict
block
```

These are referenced as action outcomes that must emit a TrustFlow event.

---

### Trust Classification

Defined CTX-ID missing-state classification:

```text
UNTRUSTED
```

---

### Special Security Output

Defined LLM security gate output:

```text
SECURITY_REFUSAL
```

When this output is seen:
- stop
- gate
- log
- never retry to bypass

---

### System Selector Constants

Referenced selection constants:

```text
SWIFT_GENERATION_SYSTEM
SWIFT_UI_ADDENDUM
GENERATION_SYSTEM
```

These are selection targets for prompt/system behavior, not wire payload values unless explicitly modeled by an implementation.

---

### Python Version Requirement

```text
Python 3.12
```

---

## Validation Rules

## Entry Point Enforcement

Every entry point that processes an agent action MUST satisfy the following in order:

1. Call CTX-ID validation FIRST.
2. If CTX-ID validation fails, immediately reject with no partial processing.
3. Check the action against VTZ policy BEFORE execution.
4. If VTZ policy denies the action, produce a `VTZEnforcementDecision` with `verdict=block`.
5. Emit a TrustFlow event for every action outcome.
6. If TrustFlow emission fails, do not silently continue; log and surface the failure.

---

## Consensus Engine Validation

### `language`

- Required.
- Must be exactly one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

Invalid values are non-conformant.

### `task`

- Required string.

### `context`

- Required string.

### Result

- `final_code` must be present on the consensus result.

---

## TrustFlow Validation

### `event_id`

- Required.
- Must be globally unique.
- Must be CSPRNG-generated.
- Must not be sequential.

### `ts`

- Required.
- Must be a UTC Unix timestamp.
- Must have millisecond precision.

### `payload_hash`

- Required.
- Must be SHA-256 of the serialized action payload.

### Emission behavior

- Must be synchronous in enforcement path.
- Async buffering is not permitted.
- Failure must be WARN-level audit event.
- Failure must not be silently skipped.

---

## CTX-ID Validation

- `ctx_id` is required for trusted processing.
- Validation must occur first.
- Missing `ctx_id` must be treated as `UNTRUSTED`.
- Expired CTX-ID must be rejected.
- Validation must be against TrustLock public key.
- Software-only validation is rejected.
- CTX-ID is immutable after issuance.
- Rotation invalidates old token immediately.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

## VTZ Validation

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.

---

## Security Validation

### Credentials and secrets

- Never hardcode credentials, API keys, tokens, or secrets as string literals.

### Subprocess execution

- Never use `shell=True` in subprocess calls.

### Code execution

- Never call `eval()` or `exec()` on generated or external content.

### Logging

- Never log HTTP response bodies.
- Log status codes and error types only.

### File writes

- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

### External document handling

- All loaded document chunks must pass injection scanning before being included in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

### SECURITY_REFUSAL handling

When `SECURITY_REFUSAL` is returned:
- stop
- gate
- log
- never retry to bypass

---

## Implementation Conformance Rules

### Python backend rules

- Python 3.12
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- `pytest` for tests
- Tests live in `tests/` and mirror `src/`
- `ruff` must pass
- `mypy` must pass
- Test coverage must be `>= 85%` on all new modules
- `pyyaml` must be in `requirements.txt`

---

## Forbidden Patterns

The following are explicitly forbidden by contract.

### Length-based fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason: must use `_score_fix()`, not response length.

### Swift force unwrap

```swift
let value = optional!
```

### LLM API call from Swift

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

### Backend Keychain read

```swift
let token = KeychainKit.read("github_token")
```

Constraint:
- Only Swift reads Keychain
- Only to deliver via XPC
- Python reads nothing from Keychain

---

## Wire Format Examples

## Valid Payloads

### Valid consensus run request

```json
{
  "task": "Implement: Add login handler",
  "context": "Relevant repository context and spec details",
  "language": "python"
}
```

### Valid consensus run request for Swift

```json
{
  "task": "Implement: Add settings screen",
  "context": "UI feature implementation context",
  "language": "swift"
}
```

### Valid consensus run result

```json
{
  "final_code": "def handler() -> None:\n    pass\n"
}
```

### Valid TrustFlow event

```json
{
  "event_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678.123,
  "event_type": "action.allow",
  "payload_hash": "3f79bb7b435b05321651daefd374cd21b4c6e5f2d3f5f6c7e8a9b0c1d2e3f4a5"
}
```

### Valid VTZ enforcement decision

```json
{
  "verdict": "block"
}
```

---

## Invalid Payloads

### Invalid consensus run request: missing language

```json
{
  "task": "Implement: Add login handler",
  "context": "Relevant repository context and spec details"
}
```

Reason:
- `language` is required.

### Invalid consensus run request: unsupported language

```json
{
  "task": "Implement: Add login handler",
  "context": "Relevant repository context and spec details",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid TrustFlow event: missing required fields

```json
{
  "event_id": "123",
  "ctx_id": "ctx_abc",
  "event_type": "action.block"
}
```

Reason:
- Missing `session_id`
- Missing `ts`
- Missing `payload_hash`

### Invalid VTZ decision: wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- The specified contract value is exactly `block` for VTZ policy denial.

### Invalid processing request: missing ctx_id

```json
{
  "action": {
    "type": "tool_call"
  }
}
```

Reason:
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Trusted processing cannot proceed without CTX-ID validation.

---

## Integration Points

## Consensus Engine

Invocation contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Selection behavior:
- `"swift"` -> `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `"python"` -> `GENERATION_SYSTEM`

Fix-loop behavior:
- Strategy selection uses `_choose_strategy(failure_type, attempt, records)`
- Fix arbitration uses `_score_fix()`

### Non-conformant behavior

- Static lookup table for fix loop strategy is non-conformant.
- Length-based fix arbitration is non-conformant.

---

## CAL Enforcement Path

Every action-processing entry point must integrate:

1. CTX-ID validation
2. VTZ policy check
3. VTZ denial decision creation when applicable
4. TrustFlow synchronous emission

Failure to implement any of the above is non-conformant.

---

## TrustLock

CTX-ID validation must integrate with TrustLock public key validation.

Constraint:
- Software-only validation is rejected.

---

## Path Security

Before any disk write, integration must call:

```text
path_security.validate_write_path()
```

This validation must occur before the write operation.

---

## Prompt Construction

When using external documents:

- Injection scanning is required before inclusion in any LLM prompt.
- External document context must be placed in the USER prompt.
- External document context must never be placed in the SYSTEM prompt.

---

## Testing and Quality Gates

Before code changes:
- Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Required toolchain gates:
- `pytest`
- `ruff`
- `mypy`

Required thresholds:
- Coverage `>= 85%` on all new modules

---

## Undefined Areas

The supplied TRD content does **not** define the following concrete wire schemas:

- Full CTX-ID token field structure
- Full agent action payload field structure
- Full VTZ policy object schema
- Full TrustFlow `event_type` enum set
- Error response payload schema
- DTL label schema

Implementations MUST NOT invent conflicting field contracts in these areas without the owning TRD.