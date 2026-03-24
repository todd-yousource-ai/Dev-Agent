# Interface Contracts - Crafted

This document defines the wire-format and API contract reference for the Crafted subsystem, derived from the provided TRD interface requirements and agent standards.

## Data Structures

### ConsensusRunRequest

Request contract for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Freeform implementation task text. |
| `context` | `string` | yes | Context string supplied to consensus engine. |
| `language` | `string` | yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. |

#### Notes
- `language` MUST always be passed.
- Example invocation shape:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
```

---

### ConsensusRunResult

Result contract returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Final generated code output. |

---

### VTZEnforcementDecision

Record emitted when VTZ policy is evaluated and denies execution.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | For denial cases, MUST be exactly `block`. |

#### Notes
- A VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Synchronous audit/enforcement event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | yes | Session identifier. |
| `ctx_id` | `string` | yes | CTX-ID associated with the action. |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | yes | Event type identifier. |
| `payload_hash` | `string` | yes | MUST be SHA-256 of the serialized action payload. |

#### Notes
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and MUST NOT be silently skipped.

---

### CTXIDToken

Logical contract for CTX-ID tokens.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Immutable once issued. |
| `vtz_binding` | `string` | yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance. |
| `expired` | `boolean` | yes | If `true`, token MUST be rejected. |

#### Behavioral Constraints
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- Old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

---

### AgentActionPayload

Serialized action payload subject to hashing and enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `payload` | `object` | yes | Serialized before SHA-256 hashing into `payload_hash`. |

#### Notes
- `payload_hash` in `TrustFlowEvent` MUST be SHA-256 of the serialized action payload.

---

### SecurityRefusalSignal

Sentinel output contract from the LLM/security gate.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `output` | `string` | yes | If value is exactly `SECURITY_REFUSAL`, processing MUST stop, gate, and log. |

---

## Enums and Constants

### Language

Allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Security Refusal Constant

- `SECURITY_REFUSAL`

### Verdict

Known required value from VTZ denial contract:

- `block`

### TrustFlow Outcome Set

Action outcomes that require TrustFlow emission:

- `allow`
- `restrict`
- `block`

### Prompt/System Selection Constants

These constants are selected by `language`:

| Language | Selected System |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` |
| `"python"` | `GENERATION_SYSTEM` |

#### Additional Constraint
- `SWIFT_UI_ADDENDUM` is injected when UI keywords are detected.

---

## Validation Rules

## 1. Entry Point Enforcement

Every entry point that processes an agent action MUST:

1. Call CTX-ID validation first.
2. Immediately reject on CTX-ID validation failure.
3. Check the action against VTZ policy before execution.
4. Emit a TrustFlow event for every outcome.
5. Surface TrustFlow emission failure; MUST NOT silently continue.

---

## 2. Consensus Engine Request Validation

### Required Fields
A valid `ConsensusRunRequest` MUST include all of:

- `task`
- `context`
- `language`

### Language Validation
`language` MUST exactly match one of:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

Any other value is invalid.

### Behavioral Rules
- Omission of `language` is invalid.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` and optionally `SWIFT_UI_ADDENDUM`.
- `language="python"` selects `GENERATION_SYSTEM`.

---

## 3. Fix Strategy and Arbitration Constraints

### Strategy Selection
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- A static lookup-table strategy is non-conformant.

### Arbitration
- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Length-based arbitration is forbidden.

#### Forbidden Example
```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

---

## 4. Security Validation Rules

### Credentials and Secrets
- Never hardcode credentials, API keys, tokens, or secrets as string literals.

### Subprocess Execution
- Never use `shell=True` in subprocess calls.

### Dynamic Execution
- Never call `eval()` or `exec()` on generated or external content.

### HTTP Logging
- Never log HTTP response bodies.
- Log status codes and error types only.

### Write Path Validation
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

### Prompt Injection Controls
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

### Security Refusal Handling
- When output is `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.

---

## 5. Python Backend Rules

For Python implementations in Crafted:

- Python version MUST be 3.12.
- Every function MUST have type annotations.
- Backend code MUST use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses MUST be used for all structured data.
- Tests MUST use `pytest`.
- Tests MUST live in `tests/` and mirror `src/` structure.
- `ruff` MUST pass clean.
- `mypy` MUST pass clean.
- Test coverage MUST be at least `85%` on all new modules.
- `pyyaml` MUST be present in `requirements.txt`.

---

## 6. CTX-ID Validation Rules

- CTX-ID validation MUST happen before any partial processing.
- Missing CTX-ID => treat as `UNTRUSTED`.
- Expired CTX-ID => reject.
- Rotated CTX-ID => old token invalid immediately.
- Validation MUST use TrustLock public key.
- Software-only validation is rejected.

---

## 7. VTZ Enforcement Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 8. TrustFlow Event Validation

A valid `TrustFlowEvent` MUST include:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

### Constraints
- `event_id` MUST be globally unique.
- `event_id` MUST be CSPRNG-generated.
- `event_id` MUST NOT be sequential.
- `ts` MUST be UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be WARN-level audit event behavior.

---

## Wire Format Examples

## 1. Valid ConsensusRunRequest

```json
{
  "task": "Implement: Add validation to Crafted request parsing",
  "context": "Existing parser supports dataclass models and async execution.",
  "language": "python"
}
```

## 2. Invalid ConsensusRunRequest: Missing `language`

```json
{
  "task": "Implement: Add validation to Crafted request parsing",
  "context": "Existing parser supports dataclass models and async execution."
}
```

Reason:
- `language` is required.

---

## 3. Invalid ConsensusRunRequest: Unsupported `language`

```json
{
  "task": "Implement: Add validation to Crafted request parsing",
  "context": "Existing parser supports dataclass models and async execution.",
  "language": "java"
}
```

Reason:
- `language` MUST be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

---

## 4. Valid TrustFlowEvent

```json
{
  "event_id": "9b3c93db-2a8c-4f5a-9c7d-7e8f7e8c1b2d",
  "session_id": "sess_01JABCDEF",
  "ctx_id": "ctx_01JXYZ123",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8f8d2b2b657c0b196ea3a9c1d6e8b7f13"
}
```

---

## 5. Invalid TrustFlowEvent: Missing `payload_hash`

```json
{
  "event_id": "9b3c93db-2a8c-4f5a-9c7d-7e8f7e8c1b2d",
  "session_id": "sess_01JABCDEF",
  "ctx_id": "ctx_01JXYZ123",
  "ts": 1735689600123,
  "event_type": "allow"
}
```

Reason:
- `payload_hash` is required.

---

## 6. Invalid TrustFlowEvent: Sequential `event_id`

```json
{
  "event_id": "1001",
  "session_id": "sess_01JABCDEF",
  "ctx_id": "ctx_01JXYZ123",
  "ts": 1735689600123,
  "event_type": "restrict",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8f8d2b2b657c0b196ea3a9c1d6e8b7f13"
}
```

Reason:
- `event_id` MUST be globally unique and MUST NOT be sequential.

---

## 7. Valid Security Refusal Signal

```json
{
  "output": "SECURITY_REFUSAL"
}
```

Required handling:
- stop
- gate
- log
- never retry to bypass

---

## 8. Invalid Swift Backend Pattern

```swift
let value = optional!
```

Reason:
- Force unwrap is forbidden.

---

## 9. Invalid Swift LLM API Pattern

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Reason:
- LLM API call from Swift is forbidden.

---

## 10. Invalid Swift Backend Credential Read

```swift
let token = KeychainKit.read("github_token")
```

Reason:
- Python reads nothing from Keychain.
- Only Swift reads Keychain, and only to deliver via XPC.

---

## Integration Points

## Consensus Engine

### Invocation Contract
Crafted integrations invoking consensus MUST call:

- `_consensus.run(...)`

With fields:

- `task`
- `context`
- `language`

### Result Consumption
Consumers MUST read:

- `result.final_code`

---

## Enforcement Pipeline

Crafted components that process agent actions MUST integrate with:

1. CTX-ID validation
2. VTZ policy enforcement
3. TrustFlow emission

### Required Ordering
1. Validate CTX-ID
2. Reject immediately on failure
3. Evaluate VTZ policy
4. Execute only if permitted
5. Emit TrustFlow event synchronously for all outcomes

---

## Path Security

Before any disk write, Crafted integrations MUST call:

- `path_security.validate_write_path()`

No writes may occur before this validation passes.

---

## Prompt Construction

When integrating external documents into LLM prompts:

- All document chunks MUST pass injection scanning.
- External document context MUST go in the USER prompt.
- External document context MUST NOT go in the SYSTEM prompt.

---

## Testing and Conformance

Before modifying Crafted code, agents MUST:

1. Find the owning TRD via `README.md`
2. Read relevant TRD sections, especially interfaces, error contracts, security, testing requirements
3. Check TRD-11 if the change touches credentials, external content, generated code, or CI
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

### Required Tooling
- `pytest`
- `ruff`
- `mypy`

### Required Coverage
- `>= 85%` on all new modules

---

## Non-Conformance Conditions

A Crafted component is non-conformant if any of the following occur:

- Agent action entry point does not validate CTX-ID first
- CTX-ID validation failure allows partial processing
- VTZ policy is not checked before execution
- VTZ denial does not produce `VTZEnforcementDecision` with `verdict=block`
- TrustFlow event is not emitted for `allow`, `restrict`, or `block`
- TrustFlow emission failure is silently ignored
- `language` is omitted in consensus requests
- Unsupported `language` value is used
- Length-based fix arbitration is used instead of `_score_fix()`
- File write occurs before `path_security.validate_write_path()`
- External content is placed in SYSTEM prompt
- `SECURITY_REFUSAL` is retried instead of gated and logged