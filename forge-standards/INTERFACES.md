# Interface Contracts - ForgeAgent

## Data Structures

This document defines the wire-format and API contract for the ForgeAgent subsystem based on the provided TRD standards.

### ConsensusRunRequest

Request shape for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Free-form task description. Example source usage: `"Implement: {spec.title}"` |
| `context` | `string` | yes | Context string passed to consensus engine |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | yes | Must always be provided |

#### Notes
- `language` is mandatory.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result shape returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Generated code output |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | yes | Must be exactly `block` for VTZ denial record |

#### Notes
- A VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Audit/event record emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | Must be globally unique; generated via CSPRNG; must not be sequential |
| `session_id` | `string` | yes | Session identifier |
| `ctx_id` | `string` | yes | CTX-ID associated with the action |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Event classification |
| `payload_hash` | `string` | yes | SHA-256 of the serialized action payload |

#### Notes
- Every TrustFlow event MUST include all six fields exactly:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`

---

### CTX-ID Token

Logical token contract for identity and trust context.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Immutable once issued |

#### Behavioral Constraints
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

---

### AgentActionPayload

Serialized action payload referenced by TrustFlow hashing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| *(opaque payload)* | `object` | yes | Serialized form is hashed using SHA-256 to produce `payload_hash` |

#### Notes
- The TRD does not define fixed payload fields for the action payload in the provided material.
- The serialized action payload is required to compute `payload_hash`.

---

### FixStrategySelectionInput

Logical input to failure-aware fix strategy selection.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `string` | yes | Passed to `_choose_strategy(failure_type, attempt, records)` |
| `attempt` | `integer` | yes | Current attempt count |
| `records` | `array` | yes | Historical records used by strategy selector |

#### Notes
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup-table strategy selection is non-conformant.

---

### FixArbitrationInput

Logical input to fix arbitration scoring.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `assertion_tokens` | `array<string>` | yes | Used for token overlap scoring |
| `candidate_fix` | `string` | yes | Candidate fix content |

#### Notes
- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Length-based arbitration is forbidden.

---

## Enums and Constants

### Language

Allowed values for `ConsensusRunRequest.language`:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

---

### VTZ Verdict

Known required value from the provided TRD:

- `block`

---

### Trust Classification

Known required value from the provided TRD:

- `UNTRUSTED`

Used when CTX-ID is missing.

---

### Named Functions / Entry Contract Symbols

These names are contract-significant and must appear exactly as written where implemented:

- `_choose_strategy(failure_type, attempt, records)`
- `_score_fix()`
- `path_security.validate_write_path()`

---

### Named System Selectors

These identifiers are contract-significant:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

---

### Security Refusal Sentinel

Exact sentinel value:

- `SECURITY_REFUSAL`

Behavior:
- stop
- gate
- log
- never retry to bypass

---

### Forbidden Patterns

The following are explicitly forbidden:

#### Length-based fix arbitration
```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
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
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
```

---

## Validation Rules

## Entry Point Enforcement

Every entry point that processes an agent action MUST:

1. call CTX-ID validation first
2. reject immediately on CTX-ID validation failure
3. check the action against VTZ policy before execution
4. emit a TrustFlow event for every outcome: allow, restrict, block

Additional constraints:
- No partial processing is permitted before CTX-ID validation succeeds.
- TrustFlow emission failure MUST NOT silently continue.
- TrustFlow emission failure MUST be logged and surfaced.

---

## TrustFlow Event Validation

A valid `TrustFlowEvent` MUST satisfy all of the following:

- `event_id` present
- `session_id` present
- `ctx_id` present
- `ts` present
- `event_type` present
- `payload_hash` present
- `event_id` is globally unique
- `event_id` is generated by CSPRNG
- `event_id` is not sequential
- `ts` is a UTC Unix timestamp with millisecond precision
- `payload_hash` equals SHA-256 of the serialized action payload
- emission is synchronous in the enforcement path
- async buffering is not permitted

Failure handling:
- Failed emission is a WARN-level audit event
- Failed emission is not a silent skip

---

## CTX-ID Validation

A valid CTX-ID flow MUST satisfy all of the following:

- token is immutable after issuance
- rotation creates a new token
- old token is invalidated immediately on rotation
- expired token is rejected
- validation is against TrustLock public key
- software-only validation is rejected
- missing token is treated as `UNTRUSTED`
- identity must never be inferred from context when CTX-ID is missing

---

## VTZ Validation

A valid VTZ enforcement flow MUST satisfy all of the following:

- every agent session is bound to exactly one VTZ at CTX-ID issuance
- cross-VTZ tool calls require explicit policy authorization
- implicit cross-VTZ access is denied
- VTZ boundaries are structural, not advisory
- enforcement cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance
- policy changes do not take effect mid-session

---

## Consensus Engine Validation

A valid consensus engine call MUST satisfy all of the following:

- `language` is always passed
- `language` is one of:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`

Behavioral selection:
- `swift` selects `SWIFT_GENERATION_SYSTEM`
- `swift` may inject `SWIFT_UI_ADDENDUM` when UI keywords are detected
- `python` selects `GENERATION_SYSTEM`

Result access:
- generated code is read from `result.final_code`

---

## Fix Loop Validation

A valid fix loop implementation MUST satisfy all of the following:

- strategy selection uses `_choose_strategy(failure_type, attempt, records)`
- arbitration uses `_score_fix()`
- `_score_fix()` is based on assertion token overlap
- response length must not be used as the arbitration criterion

Invalid implementation pattern:
- `max(..., key=len)` for fix selection is forbidden

---

## Security Validation

The ForgeAgent subsystem MUST satisfy all of the following security rules:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before being included in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log, never retry to bypass.

---

## Language/Runtime Validation

### Python
- Python version: `3.12`
- Type annotations required on every function
- `async/await` throughout backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Tests use `pytest`
- Tests live in `tests/`
- Tests mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage on all new modules must be `>= 85%`
- `pyyaml` must be in `requirements.txt`

### Swift
- No force unwrap
- No LLM API call directly from Swift
- Swift may read Keychain only to deliver via XPC

### Backend / Python Keychain Rule
- Python reads nothing from Keychain

---

## Wire Format Examples

## Valid Payloads

### Valid ConsensusRunRequest
```json
{
  "task": "Implement: Add TrustFlow event emission",
  "context": "Agent action requires VTZ check and CTX-ID validation.",
  "language": "python"
}
```

### Valid ConsensusRunResult
```json
{
  "final_code": "from dataclasses import dataclass\n\n@dataclass\nclass Example:\n    value: str\n"
}
```

### Valid TrustFlowEvent
```json
{
  "event_id": "c1d7a9c4-6c2c-4b83-9e85-3d1d3d7f7c5a",
  "session_id": "sess_01HZX8K2A6M7Q9N3T4V5W6X7Y",
  "ctx_id": "ctx_01HZX8M1B2C3D4E5F6G7H8J9K",
  "ts": 1717171717123,
  "event_type": "agent_action_blocked",
  "payload_hash": "0f4c1a7b9a54e3b2d1c6f8e7a9b0c3d4e5f67890123456789abcdef012345678"
}
```

### Valid VTZEnforcementDecision
```json
{
  "verdict": "block"
}
```

### Valid Missing CTX-ID Handling State
```json
{
  "ctx_id": null,
  "trust_state": "UNTRUSTED"
}
```

## Invalid Payloads

### Invalid ConsensusRunRequest: missing language
```json
{
  "task": "Implement: Add TrustFlow event emission",
  "context": "Agent action requires VTZ check and CTX-ID validation."
}
```

Reason:
- `language` is required.

---

### Invalid ConsensusRunRequest: unsupported language
```json
{
  "task": "Implement: Add TrustFlow event emission",
  "context": "Agent action requires VTZ check and CTX-ID validation.",
  "language": "java"
}
```

Reason:
- `language` must be one of `python`, `swift`, `go`, `typescript`, `rust`.

---

### Invalid TrustFlowEvent: missing required fields
```json
{
  "event_id": "123",
  "session_id": "sess_1"
}
```

Reason:
- Missing `ctx_id`
- Missing `ts`
- Missing `event_type`
- Missing `payload_hash`

---

### Invalid VTZEnforcementDecision
```json
{
  "verdict": "allow"
}
```

Reason:
- VTZ denial record must use `verdict = "block"`.

---

### Invalid Security Behavior: external context in SYSTEM prompt
```json
{
  "system_prompt": "External document content here"
}
```

Reason:
- Context from external documents must go in the USER prompt, never the SYSTEM prompt.

---

### Invalid File Write Flow
```json
{
  "path": "/tmp/output.txt",
  "validated": false
}
```

Reason:
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

---

## Integration Points

## Consensus Engine

Required invocation shape:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

Integration requirements:
- always pass `language`
- read output from `result.final_code`

---

## CAL / CTX-ID / VTZ Enforcement Path

Execution ordering requirements:

1. CTX-ID validation
2. immediate rejection on failure
3. VTZ policy check
4. execute or deny
5. emit TrustFlow event synchronously

Required outputs:
- VTZ denial produces `VTZEnforcementDecision` with `verdict=block`
- all outcomes emit a `TrustFlowEvent`

---

## TrustFlow

TrustFlow is a mandatory synchronous audit integration in the enforcement path.

Required event fields:
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Failure contract:
- emission failure is WARN-level
- emission failure must be logged
- emission failure must be surfaced
- emission failure must not be silently skipped

---

## Path Security

Before any disk write:
- call `path_security.validate_write_path()`

No write may occur before validation passes.

---

## Prompt Construction

When including external document content:
- scan loaded document chunks for injection
- include external context only in USER prompt
- never place external document context in SYSTEM prompt

---

## Security Gate

On `SECURITY_REFUSAL` output from the LLM:
- stop
- gate
- log
- do not retry to bypass

---

## Testing and Conformance

Before modification:
```bash
cd src && pytest ../tests/ -v --tb=short
```

Conformance expectations:
- `pytest`
- `ruff`
- `mypy`
- coverage `>= 85%` on new modules
- Python structured data uses dataclasses
- backend code uses `async/await` throughout