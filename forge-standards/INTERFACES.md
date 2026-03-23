# Interface Contracts - CraftedDevAgent

This document defines the wire-format and API contract requirements for the CraftedDevAgent subsystem, derived from the provided TRD content. These contracts are normative.

## Data Structures

Only structures explicitly defined or implied by the TRD content are included.

### ConsensusRunRequest

Request contract for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Human-readable task description. Example source usage: `"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string passed to consensus engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. Exact allowed values are fixed. |

#### Notes
- The caller **MUST** always pass `language`.
- Language selection behavior:
  - `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
  - `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResponse

Response contract from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output. |

#### Source usage
```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

---

### VTZEnforcementDecision

Required record produced on VTZ denial.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | On VTZ policy denial, value **MUST** be exactly `block`. |

#### Notes
- A VTZ policy denial **MUST** produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Required event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique. Must be generated with CSPRNG. Must not be sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event classification. Exact values not specified in source. |
| `payload_hash` | `string` | Yes | Must be SHA-256 of the serialized action payload. |

#### Notes
- Every action outcome (`allow`, `restrict`, `block`) **MUST** emit a TrustFlow event.
- Emission **MUST** be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission **MUST NOT** be silently skipped.
- Failed emission is a WARN-level audit event.

---

### CTX_ID Token

Logical token contract for CTX-ID.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. Must validate against TrustLock public key. |

#### Behavioral constraints
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token; old token is invalidated immediately.
- Expired CTX-ID must be rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from surrounding context when CTX-ID is missing.
- Software-only validation is rejected; validation must be against TrustLock public key.

---

### AgentActionPayload

Serialized action payload referenced by enforcement and hashing requirements.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _opaque payload_ | serialized object | Yes | Exact schema not specified in source. Serialized form is the input to SHA-256 for `payload_hash`. |

#### Notes
- `payload_hash` in `TrustFlowEvent` **MUST** be computed from the serialized action payload.

---

### SecurityRefusalOutput

Special LLM output contract.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `value` | `string` | Yes | Exact value: `SECURITY_REFUSAL`. |

#### Required behavior
- When `SECURITY_REFUSAL` output is observed: stop, gate, log.
- Never retry to bypass.

## Enums and Constants

### Language

Exact allowed values for consensus engine invocation:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

---

### VTZ Verdict

Known required value from source:

- `block`

---

### Action Outcomes

Every action outcome must emit a TrustFlow event. Known values from source:

- `allow`
- `restrict`
- `block`

---

### Special Security Output

- `SECURITY_REFUSAL`

---

### System Selection Constants

Exact identifiers referenced by source:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

## Validation Rules

## 1. Consensus Engine Invocation

### Required request validation
- `language` **MUST** be present on every call to consensus engine.
- `language` **MUST** equal one of:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`

### Behavioral rules
- `language="swift"`:
  - selects `SWIFT_GENERATION_SYSTEM`
  - may inject `SWIFT_UI_ADDENDUM` when UI keywords are detected
- `language="python"`:
  - selects `GENERATION_SYSTEM`

### Forbidden implementation
Length-based fix arbitration is forbidden.

#### Invalid
```python
winner = max(claude_fix, openai_fix, key=len)
```

#### Required
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration uses `_score_fix()` based on assertion token overlap.

---

## 2. CAL Enforcement Contract

Every entry point that processes an agent action:

1. **MUST** call CTX-ID validation first.
2. CTX-ID validation failure **MUST** result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action **MUST** be checked against VTZ policy before execution.
5. VTZ policy denial **MUST** produce a `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) **MUST** emit a TrustFlow event.
7. TrustFlow emission failure **MUST NOT** silently continue.
8. TrustFlow emission failure **MUST** be logged and surfaced.

---

## 3. TrustFlow Event Validation

A valid `TrustFlowEvent` must satisfy all of the following:

- `event_id` is present
- `event_id` is globally unique
- `event_id` is generated with CSPRNG
- `event_id` is not sequential
- `session_id` is present
- `ctx_id` is present
- `ts` is present
- `ts` is UTC Unix timestamp with millisecond precision
- `event_type` is present
- `payload_hash` is present
- `payload_hash` is SHA-256 of the serialized action payload

Emission constraints:

- Emission must be synchronous in the enforcement path
- Async buffering is not permitted
- Failed emission is a WARN-level audit event
- Silent skip is forbidden

---

## 4. CTX-ID Validation

A valid CTX-ID flow must satisfy all of the following:

- CTX-ID is validated before any processing of agent action
- CTX-ID is immutable once issued
- Rotation issues a new token and invalidates old token immediately
- Expired CTX-ID is rejected
- Validation uses TrustLock public key
- Software-only validation is rejected
- Missing CTX-ID is treated as `UNTRUSTED`
- Identity is never inferred from context if CTX-ID is missing

---

## 5. VTZ Enforcement

- Every agent session is bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit authorization is denied
- VTZ boundaries are structural and cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session

---

## 6. Security Rules

### Credentials and secrets
- Never hardcode credentials, API keys, tokens, or secrets as string literals.

### Process execution
- Never use `shell=True` in subprocess calls.

### Dynamic code execution
- Never call `eval()` or `exec()` on generated or external content.

### Logging
- Never log HTTP response bodies.
- Log status codes and error types only.

### File writes
- All file paths written to disk **MUST** pass `path_security.validate_write_path()` before any write.

### Prompt injection protection
- All loaded document chunks **MUST** pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

### Security refusal handling
- On `SECURITY_REFUSAL`: stop, gate, log. Never retry to bypass.

### Forbidden Swift patterns
```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

#### Constraint notes
- Only Swift reads Keychain, only to deliver via XPC.
- Python reads nothing from Keychain.
- LLM API calls from Swift are forbidden.

---

## 7. Python Backend Requirements

These are implementation contract requirements for Python-facing CraftedDevAgent components:

- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout backend
- No blocking calls on event loop
- Dataclasses for all structured data
- Tests use `pytest`
- Tests live in `tests/` and mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage must be `≥ 85%` on all new modules
- `pyyaml` must be in `requirements.txt`

## Wire Format Examples

## Valid Payloads

### Valid ConsensusRunRequest
```json
{
  "task": "Implement: Add file writer",
  "context": "Use async Python backend and validate output paths before write.",
  "language": "python"
}
```

### Valid ConsensusRunResponse
```json
{
  "final_code": "from dataclasses import dataclass\n..."
}
```

### Valid TrustFlowEvent
```json
{
  "event_id": "f8f0e6d0-5d1f-4a2c-9d9e-2b7df5c4f9a1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3b7c3b6a8d4e2f1c0a9b8e7d6c5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7"
}
```

### Valid VTZEnforcementDecision
```json
{
  "verdict": "block"
}
```

### Valid SecurityRefusalOutput
```json
{
  "value": "SECURITY_REFUSAL"
}
```

## Invalid Payloads

### Invalid ConsensusRunRequest: missing language
```json
{
  "task": "Implement: Add file writer",
  "context": "Use async backend."
}
```

Reason:
- `language` is required.

---

### Invalid ConsensusRunRequest: unsupported language
```json
{
  "task": "Implement: Add file writer",
  "context": "Use async backend.",
  "language": "java"
}
```

Reason:
- `language` must be one of `python | swift | go | typescript | rust`.

---

### Invalid TrustFlowEvent: missing payload_hash
```json
{
  "event_id": "f8f0e6d0-5d1f-4a2c-9d9e-2b7df5c4f9a1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "allow"
}
```

Reason:
- `payload_hash` is required.

---

### Invalid VTZEnforcementDecision: wrong verdict on denial
```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ policy denial must produce `verdict=block`.

---

### Invalid Swift usage
```swift
let value = optional!
```

Reason:
- Force unwrap is forbidden.

---

### Invalid Python fix arbitration
```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- Length-based fix arbitration is forbidden; use `_score_fix()`.

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

Integration requirements:
- Always pass `language`
- Consume `result.final_code`

---

## Path Security
Before any file write:
- Call `path_security.validate_write_path()`

Integration rule:
- Validation must occur before write, not after.

---

## Prompt Assembly / LLM Input
Before including loaded document chunks in any prompt:
- Perform injection scanning

Prompt placement rule:
- External document context goes in USER prompt
- Never place external document context in SYSTEM prompt

---

## CTX-ID / TrustLock
For every action entry point:
- Validate CTX-ID first
- Validate against TrustLock public key
- Reject immediately on failure

---

## VTZ Policy Engine
Before action execution:
- Evaluate action against VTZ policy
- On denial, create `VTZEnforcementDecision` with `verdict=block`

---

## TrustFlow Audit Pipeline
For every action outcome:
- Emit synchronous `TrustFlowEvent`
- Include:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`

Failure behavior:
- WARN-level audit event
- Must be logged and surfaced
- Must not silently continue

---

## Test Invocation Contract
Before making changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```

This command is part of the required agent workflow contract.