# Interface Contracts - ForgeAgent

## Data Structures

This document defines the wire-format and API contract requirements for the ForgeAgent subsystem based on the provided TRD excerpts and standards.

Where the TRD specifies exact field names, values, or constraints, they are reproduced exactly.

### 1. ConsensusRunRequest

Request contract for invoking the consensus engine.

#### Shape

```python
@dataclass
class ConsensusRunRequest:
    task: str
    context: str
    language: str
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Non-empty task description. Example source usage: `f"Implement: {spec.title}"`. |
| `context` | `str` | Yes | Context string supplied to the consensus engine. External document context must go in the USER prompt, never the SYSTEM prompt. |
| `language` | `str` | Yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. |

#### Behavioral requirements

- Every consensus invocation must pass `language`.
- Exact required usage pattern:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### 2. ConsensusRunResult

Result contract returned from the consensus engine.

#### Shape

```python
@dataclass
class ConsensusRunResult:
    final_code: str
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Generated code output from the consensus run. |

---

### 3. TrustFlowEvent

Required audit/event object emitted for every action outcome.

#### Shape

```python
@dataclass
class TrustFlowEvent:
    event_id: str
    session_id: str
    ctx_id: str
    ts: int | float
    event_type: str
    payload_hash: str
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | Yes | Must be globally unique. Must be generated using CSPRNG, not sequential. |
| `session_id` | `str` | Yes | Session identifier for the agent session. |
| `ctx_id` | `str` | Yes | CTX-ID associated with the action. Missing CTX-ID must be treated as `UNTRUSTED`. |
| `ts` | `int \| float` | Yes | Must be a UTC Unix timestamp with millisecond precision. |
| `event_type` | `str` | Yes | Event type describing the action outcome/event. |
| `payload_hash` | `str` | Yes | Must be SHA-256 of the serialized action payload. |

#### Behavioral requirements

- Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and must not be silently skipped.
- TrustFlow emission failure must be logged and surfaced.

---

### 4. VTZEnforcementDecision

Decision record required when VTZ policy denies an action.

#### Shape

```python
@dataclass
class VTZEnforcementDecision:
    verdict: str
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `str` | Yes | For denial, must be exactly `block`. |

#### Behavioral requirements

- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 5. CTXIDToken

Contractual representation of a CTX-ID token.

#### Shape

The TRD excerpt does not define internal token fields beyond the required externally validated identifier `ctx_id`. Therefore, the ForgeAgent wire contract only guarantees the transport/use of the CTX-ID as an immutable token identifier.

```python
@dataclass
class CTXIDToken:
    ctx_id: str
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | Yes | Immutable once issued. Must be validated before any action processing. |

#### Behavioral requirements

- CTX-ID validation must occur first for every entry point that processes an agent action.
- CTX-ID validation failure must result in immediate rejection with no partial processing.
- CTX-ID tokens are immutable once issued.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID must be rejected.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.

---

### 6. ForgeAgentActionPayload

Canonical action payload input to enforcement and TrustFlow hashing.

#### Shape

The TRD requires a serialized action payload for `payload_hash`, but does not define a fixed schema in the provided excerpt. Therefore this interface is a generic structured payload container.

```python
ActionPayload = dict[str, object]
```

#### Constraints

- Must be serializable.
- The exact serialized bytes used for `payload_hash` must be hashed with SHA-256.
- Every entry point that processes an agent action must:
  1. validate CTX-ID first,
  2. check VTZ policy before execution,
  3. emit TrustFlow event for the outcome.

---

### 7. FixStrategySelectionInput

Input contract to failure-type-aware fix loop strategy.

#### Shape

```python
@dataclass
class FixStrategySelectionInput:
    failure_type: str
    attempt: int
    records: list[dict[str, object]]
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `str` | Yes | Failure category used by `_choose_strategy(failure_type, attempt, records)`. |
| `attempt` | `int` | Yes | Current fix attempt number. |
| `records` | `list[dict[str, object]]` | Yes | Prior attempt records. |

#### Behavioral requirements

- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup-table strategy selection is non-conformant.

---

### 8. FixArbitrationInput

Input contract for fix arbitration scoring.

#### Shape

```python
@dataclass
class FixArbitrationInput:
    candidate_fix: str
    assertion_tokens: list[str]
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `candidate_fix` | `str` | Yes | Fix candidate under evaluation. |
| `assertion_tokens` | `list[str]` | Yes | Assertion token set used for overlap scoring. |

#### Behavioral requirements

- Fix arbitration must use `_score_fix()`.
- Arbitration is based on assertion token overlap.
- Response length must not be used to choose the winning fix.

---

### 9. SecurityRefusalSignal

Signal indicating the LLM returned a security refusal outcome.

#### Shape

```python
@dataclass
class SecurityRefusalSignal:
    value: str
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `value` | `str` | Yes | Must be exactly `SECURITY_REFUSAL`. |

#### Behavioral requirements

- When `SECURITY_REFUSAL` output is observed: stop, gate, log.
- Never retry to bypass.

---

## Enums and Constants

### Language

Allowed `language` values for consensus engine invocation:

```text
"python"
"swift"
"go"
"typescript"
"rust"
```

### Security refusal constant

```text
SECURITY_REFUSAL
```

### VTZ decision verdict

```text
block
```

### Action outcomes requiring TrustFlow emission

```text
allow
restrict
block
```

### Prompt/system selection constants

```text
SWIFT_GENERATION_SYSTEM
SWIFT_UI_ADDENDUM
GENERATION_SYSTEM
```

These names must be used exactly as specified by the TRD behavior.

---

## Validation Rules

## 1. CAL Enforcement Contract

Every ForgeAgent component entry point that processes an agent action must satisfy all of the following:

1. CTX-ID validation must be called first.
2. If CTX-ID validation fails, reject immediately.
3. No partial processing is permitted after CTX-ID validation failure.
4. VTZ policy check must occur before execution.
5. VTZ denial must produce a `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome must emit a TrustFlow event.
7. TrustFlow emission failure must not silently continue.

## 2. TrustFlow Emission Validation

A valid `TrustFlowEvent` must include all of:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Additional constraints:

- `event_id` must be globally unique.
- `event_id` must be generated by CSPRNG.
- `event_id` must not be sequential.
- `ts` must be UTC Unix timestamp with millisecond precision.
- `payload_hash` must be SHA-256 of the serialized action payload.
- Emission must be synchronous.
- Async buffering is forbidden.
- Failed emission must produce WARN-level audit behavior.

## 3. CTX-ID Validation

- CTX-ID is immutable after issuance.
- Rotation creates a new token and immediately invalidates the old token.
- Expired CTX-ID must be rejected.
- Validation must be against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID is treated as `UNTRUSTED`.
- Identity must never be inferred from context when CTX-ID is missing.

## 4. VTZ Enforcement Validation

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

## 5. Consensus Engine Invocation Validation

A valid invocation must:

- call `await self._consensus.run(...)`
- include `task`
- include `context`
- include `language`

Valid example pattern:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Invalid patterns:

- missing `language`
- unsupported `language`
- using response-length-based fix arbitration
- using static fix strategy lookup in place of `_choose_strategy(failure_type, attempt, records)`

## 6. Security Validation

The following are forbidden:

- hardcoded credentials, API keys, tokens, or secrets as string literals
- `shell=True` in subprocess calls
- `eval()` on generated or external content
- `exec()` on generated or external content
- logging HTTP response bodies
- writing any file path before `path_security.validate_write_path()` passes
- including loaded document chunks in prompts before injection scanning
- putting external document context in the SYSTEM prompt
- retrying to bypass `SECURITY_REFUSAL`
- Swift force unwrap:
  ```swift
  let value = optional!
  ```
- LLM API call from Swift:
  ```swift
  let client = AnthropicClient(apiKey: keychainValue)
  ```
- backend Keychain read:
  ```swift
  let token = KeychainKit.read("github_token")
  ```

Allowed/required security behavior:

- log HTTP status codes and error types only
- external document context belongs in the USER prompt
- only Swift reads Keychain, only to deliver via XPC

## 7. Python Backend Conformance

For ForgeAgent Python backend components:

- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout the backend
- no blocking calls on the event loop
- dataclasses for all structured data
- tests use `pytest`
- tests live in `tests/` and mirror `src/` structure
- `ruff` must pass
- `mypy` must pass
- test coverage must be `≥ 85%` on all new modules
- `pyyaml` must be present in `requirements.txt`

---

## Wire Format Examples

## 1. Valid ConsensusRunRequest

```json
{
  "task": "Implement: Add VTZ enforcement to agent action execution",
  "context": "User-provided specification and validated external context.",
  "language": "python"
}
```

## 2. Invalid ConsensusRunRequest - missing language

```json
{
  "task": "Implement: Add VTZ enforcement to agent action execution",
  "context": "User-provided specification and validated external context."
}
```

Reason:
- `language` is required.

## 3. Invalid ConsensusRunRequest - unsupported language

```json
{
  "task": "Implement: Add VTZ enforcement to agent action execution",
  "context": "User-provided specification and validated external context.",
  "language": "java"
}
```

Reason:
- `language` must be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

## 4. Valid TrustFlowEvent

```json
{
  "event_id": "9b6a6dc2-8f6f-4e27-a8c0-5f14b8d7e1b4",
  "session_id": "sess_01HVK9M6WQ4T",
  "ctx_id": "ctx_01HVK9M9X8AA",
  "ts": 1712345678123,
  "event_type": "allow",
  "payload_hash": "4d7e2f5b1d4c6c9f6a07d2f0e3b0a52f4f41d6c54d6dc0d4d6a930f6f9d8ce21"
}
```

## 5. Invalid TrustFlowEvent - missing payload_hash

```json
{
  "event_id": "9b6a6dc2-8f6f-4e27-a8c0-5f14b8d7e1b4",
  "session_id": "sess_01HVK9M6WQ4T",
  "ctx_id": "ctx_01HVK9M9X8AA",
  "ts": 1712345678123,
  "event_type": "block"
}
```

Reason:
- `payload_hash` is required.

## 6. Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

## 7. Invalid VTZEnforcementDecision

```json
{
  "verdict": "deny"
}
```

Reason:
- On VTZ denial, `verdict` must be exactly `block`.

## 8. Valid action processing sequence

```json
{
  "ctx_id": "ctx_01HVK9M9X8AA",
  "session_id": "sess_01HVK9M6WQ4T",
  "action_payload": {
    "tool": "write_file",
    "path": "/workspace/output.py"
  }
}
```

Required processing order:

1. validate `ctx_id`
2. reject immediately if invalid
3. evaluate VTZ policy
4. if denied, create:
   ```json
   { "verdict": "block" }
   ```
5. emit synchronous TrustFlow event with required fields

## 9. Invalid action processing sequence

```json
{
  "ctx_id": "ctx_01HVK9M9X8AA",
  "session_id": "sess_01HVK9M6WQ4T",
  "action_payload": {
    "tool": "write_file",
    "path": "/workspace/output.py"
  },
  "processed_before_ctx_validation": true
}
```

Reason:
- CTX-ID validation must happen first.
- Partial processing before validation is forbidden.

## 10. Invalid fix arbitration example

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- Length-based fix arbitration is forbidden.
- Must use `_score_fix()`.

## 11. Invalid Swift examples

### Force unwrap

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

All are non-conformant.

---

## Integration Points

## 1. Consensus Engine

ForgeAgent integrates with the consensus engine through:

```python
await self._consensus.run(
    task=...,
    context=...,
    language=...,
)
```

Output consumed from:

```python
result.final_code
```

Integration requirements:

- `language` must always be passed.
- Prompt-system selection must follow language-specific behavior exactly.

## 2. CAL / CTX-ID / VTZ Enforcement Path

Every ForgeAgent action-processing entry point integrates with:

- CTX-ID validation
- VTZ policy enforcement
- TrustFlow event emission

Required order:

1. CTX-ID validation
2. VTZ policy check
3. action execution or block
4. synchronous TrustFlow emission

## 3. TrustFlow Audit System

ForgeAgent must emit a `TrustFlowEvent` on every action outcome.

Required event fields:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

## 4. Path Security

All file writes must integrate with:

```python
path_security.validate_write_path()
```

Requirement:

- validation must occur before any write to disk.

## 5. Injection Scanning

All loaded document chunks must integrate with injection scanning before inclusion in any LLM prompt.

Requirement:

- unscanned loaded document chunks must not be included in prompts.

## 6. Prompt Construction

Prompt construction must enforce:

- external document context goes in the USER prompt
- external document context never goes in the SYSTEM prompt

## 7. Security Gating

When LLM output is:

```text
SECURITY_REFUSAL
```

ForgeAgent integration behavior must be:

1. stop
2. gate
3. log

Retrying to bypass is forbidden.

## 8. Python Tooling and Test Integration

ForgeAgent backend modules must integrate with:

- `pytest`
- `ruff`
- `mypy`

And satisfy:

- tests under `tests/`
- mirrored `src/` structure
- coverage `≥ 85%` for all new modules

## 9. Pre-implementation workflow

Before modifying ForgeAgent:

1. Find the owning TRD via `README.md`
2. Read relevant TRD sections:
   - interfaces
   - error contracts
   - security
   - testing requirements
3. Check TRD-11 if change touches:
   - credentials
   - external content
   - generated code
   - CI
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```