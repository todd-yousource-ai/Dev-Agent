# Interface Contracts - CraftedApp

This document defines the wire formats and API/data contracts for the CraftedApp subsystem based on the provided TRD content. These contracts are mandatory.

## Data Structures

### TrustFlowEvent

Required for every action outcome in the enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique; generated via CSPRNG; MUST NOT be sequential |
| `session_id` | `string` | yes | Session identifier; exact format not specified in provided TRD |
| `ctx_id` | `string` | yes | CTX-ID token identifier; MUST refer to the validated CTX-ID for the action |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Event type discriminator; exact allowed values not specified in provided TRD |
| `payload_hash` | `string` | yes | MUST be SHA-256 of the serialized action payload |

#### Structural requirements
- Every TrustFlow event MUST include exactly at least:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- Emission MUST be synchronous in the enforcement path.
- Async buffering is NOT permitted.
- Failed emission is a WARN-level audit event and MUST NOT be silently skipped.

---

### VTZEnforcementDecision

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | MUST equal `block` for VTZ policy denial |

#### Structural requirements
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record.
- On denial, `verdict=block` is mandatory.

---

### CTX-ID Token

Represents the trust/context identity token used by entry points and sessions.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Token identifier; immutable once issued |

#### Behavioral constraints
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is permitted after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

> Note: The internal token field set beyond `ctx_id` is not specified in the provided TRD excerpt.

---

### Agent Action Payload

Represents the serialized payload of the action being enforced.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `payload` | `object` | yes | Serialized action payload used to compute `payload_hash` |

#### Behavioral constraints
- Every entry point that processes an agent action MUST validate CTX-ID first.
- Every action MUST be checked against VTZ policy before execution.
- `payload_hash` in `TrustFlowEvent` MUST be the SHA-256 of the serialized action payload.

> Note: The schema of the action payload itself is not specified in the provided TRD excerpt.

---

### ConsensusRunRequest

Invocation contract for the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Example usage: `f"Implement: {spec.title}"` |
| `context` | `string` | yes | Context string passed to the engine |
| `language` | `string` | yes | MUST be one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Required call shape
```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

---

### ConsensusRunResult

Return contract for consensus engine execution.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Final generated code output |

> Additional fields are not specified in the provided TRD excerpt.

---

## Enums and Constants

### Language

Allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Verdict

Allowed values specified by provided TRD content:

- `block`

### Trust State

Allowed value explicitly specified by provided TRD content for missing CTX-ID handling:

- `UNTRUSTED`

### Fixed identifiers and system selectors

These values are referenced exactly as specified:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Internal strategy functions

These identifiers are part of the contract guidance and MUST be used as named:

- `_choose_strategy(failure_type, attempt, records)`
- `_score_fix()`

---

## Validation Rules

## Crafted Component Enforcement Rules

### CAL Enforcement Contract

Every Crafted component MUST satisfy all of the following:

1. Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

### TrustFlow Emission Contract

1. Every TrustFlow event MUST include:
   - `event_id`
   - `session_id`
   - `ctx_id`
   - `ts`
   - `event_type`
   - `payload_hash`
2. `event_id` MUST be globally unique.
3. `event_id` generation MUST use CSPRNG.
4. `event_id` MUST NOT be sequential.
5. `ts` MUST be a UTC Unix timestamp with millisecond precision.
6. `payload_hash` MUST be SHA-256 of the serialized action payload.
7. Emission MUST be synchronous in the enforcement path.
8. Async buffering is NOT permitted.
9. Failed emission is a WARN-level audit event.
10. Failed emission MUST NOT be silently skipped.

### CTX-ID Contract

1. CTX-ID tokens are IMMUTABLE once issued.
2. No field modification is allowed after issuance.
3. CTX-ID rotation MUST create a new token.
4. The old token is invalidated immediately.
5. Expired CTX-ID MUST be rejected.
6. Clock skew tolerance is deployment-defined.
7. CTX-ID MUST be validated against TrustLock public key.
8. Software-only validation is rejected.
9. Missing CTX-ID MUST be treated as `UNTRUSTED`.
10. Identity MUST NEVER be inferred from context when CTX-ID is missing.

### VTZ Enforcement Contract

1. Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit cross-VTZ authorization is denied.
4. VTZ boundaries are structural, not advisory.
5. Enforcement cannot be bypassed by application code.
6. VTZ policy changes take effect at NEXT CTX-ID issuance.
7. VTZ policy changes do NOT take effect mid-session.

## Consensus Engine Rules

1. Consensus engine calls MUST pass `language`.
2. `language` MUST be one of:
   - `"python"`
   - `"swift"`
   - `"go"`
   - `"typescript"`
   - `"rust"`
3. For `language="swift"`, system selection is:
   - `SWIFT_GENERATION_SYSTEM`
   - optional `SWIFT_UI_ADDENDUM` when UI keywords are detected
4. For `language="python"`, system selection is:
   - `GENERATION_SYSTEM`
5. Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
6. Fix arbitration MUST use `_score_fix()`.
7. Length-based fix arbitration is forbidden.

## Security Rules

1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Only log HTTP status codes and error types.
6. All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
7. All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
8. Context from external documents goes in the USER prompt, never the SYSTEM prompt.
9. When `SECURITY_REFUSAL` output is returned from the LLM:
   - stop
   - gate
   - log
   - never retry to bypass

## Python Backend Rules

1. Python version MUST be `3.12`.
2. Every function MUST have type annotations.
3. Backend code MUST use `async/await` throughout.
4. No blocking calls on the event loop.
5. Dataclasses MUST be used for all structured data.
6. Tests MUST use `pytest`.
7. Tests MUST live in `tests/`.
8. Tests MUST mirror `src/` structure.
9. `ruff` MUST pass clean.
10. `mypy` MUST pass clean.
11. Test coverage MUST be `>= 85%` on all new modules.
12. `pyyaml` MUST be present in `requirements.txt`.

## Forbidden Implementations

### Forbidden Python/logic pattern
```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason: length-based fix arbitration is replaced by `_score_fix()`.

### Forbidden Swift force unwrap
```swift
let value = optional!
```

### Forbidden LLM API call from Swift
```swift
let client = AnthropicClient(apiKey: keychainValue)
```

### Forbidden backend token read from Keychain in Swift/backend path
```swift
let token = KeychainKit.read("github_token")
```

Constraint:
- Only Swift reads Keychain.
- Only to deliver via XPC.
- Python reads nothing from Keychain.

---

## Wire Format Examples

## Valid Payloads

### Valid TrustFlowEvent
```json
{
  "event_id": "7e5d8b4f-3f6e-4f8f-a2c8-7a4c90e8d4d1",
  "session_id": "sess_01JABCXYZ",
  "ctx_id": "ctx_01JDEFUVW",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8f1863b42db2fc314a0d6d4f3f9d8b7e2"
}
```

### Valid VTZEnforcementDecision
```json
{
  "verdict": "block"
}
```

### Valid ConsensusRunRequest
```json
{
  "task": "Implement: Add TrustFlow emission",
  "context": "Enforce CTX-ID validation before VTZ policy checks.",
  "language": "python"
}
```

### Valid ConsensusRunResult
```json
{
  "final_code": "from dataclasses import dataclass\n..."
}
```

## Invalid Payloads

### Invalid TrustFlowEvent: missing required field
```json
{
  "event_id": "7e5d8b4f-3f6e-4f8f-a2c8-7a4c90e8d4d1",
  "session_id": "sess_01JABCXYZ",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8f1863b42db2fc314a0d6d4f3f9d8b7e2"
}
```

Invalid because `ctx_id` is required.

### Invalid TrustFlowEvent: non-compliant identifier generation semantics
```json
{
  "event_id": "1001",
  "session_id": "sess_01JABCXYZ",
  "ctx_id": "ctx_01JDEFUVW",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8f1863b42db2fc314a0d6d4f3f9d8b7e2"
}
```

Invalid because `event_id` MUST be globally unique and MUST NOT be sequential.

### Invalid VTZEnforcementDecision
```json
{
  "verdict": "allow"
}
```

Invalid because provided TRD content requires `verdict=block` for VTZ policy denial.

### Invalid ConsensusRunRequest: missing language
```json
{
  "task": "Implement: Add TrustFlow emission",
  "context": "Enforce CTX-ID validation before VTZ policy checks."
}
```

Invalid because `language` is mandatory.

### Invalid ConsensusRunRequest: unsupported language
```json
{
  "task": "Implement: Add TrustFlow emission",
  "context": "Enforce CTX-ID validation before VTZ policy checks.",
  "language": "java"
}
```

Invalid because `language` MUST be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

---

## Integration Points

### Agent Action Entry Points

All entry points that process an agent action MUST implement this order:

1. CTX-ID validation FIRST
2. Immediate rejection on validation failure
3. VTZ policy check BEFORE execution
4. Produce `VTZEnforcementDecision` with `verdict=block` on denial
5. Emit TrustFlow event for every action outcome
6. Treat TrustFlow emission failure as logged and surfaced WARN-level audit failure

### TrustLock Validation

CTX-ID validation integrates with TrustLock:

- CTX-ID MUST be validated against TrustLock public key
- Software-only validation is rejected

### VTZ Policy Engine

Required integration semantics:

- session is bound to EXACTLY ONE VTZ at CTX-ID issuance
- cross-VTZ tool calls require explicit policy authorization
- implicit authorization is denied
- policy changes apply at NEXT CTX-ID issuance only

### Consensus Engine

Required invocation and result handling:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Language routing behavior:

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM`
- `language="swift"` may also inject `SWIFT_UI_ADDENDUM` when UI keywords are detected
- `language="python"` selects `GENERATION_SYSTEM`

Fix handling behavior:

- strategy selection via `_choose_strategy(failure_type, attempt, records)`
- fix arbitration via `_score_fix()`
- do NOT use length-based arbitration

### File Path Security

Before any disk write:

- path MUST pass `path_security.validate_write_path()`

### Prompt Construction and External Content

- loaded document chunks MUST pass injection scanning before inclusion in LLM prompt
- context from external documents MUST be placed in USER prompt
- external document context MUST NOT be placed in SYSTEM prompt

### LLM Security Refusal Handling

If LLM output is exactly or contains `SECURITY_REFUSAL`:

- stop
- gate
- log
- do not retry to bypass

### Swift / Python Boundary

- Swift MUST NOT call LLM APIs directly
- Swift MAY read Keychain only to deliver via XPC
- Python backend reads nothing from Keychain

### Testing and Tooling

- Run existing tests before changes:
  - `cd src && pytest ../tests/ -v --tb=short`
- Test framework: `pytest`
- Linting: `ruff`
- Type checking: `mypy`
- Coverage requirement: `>= 85%` on all new modules