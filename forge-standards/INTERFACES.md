# Interface Contracts - CraftedDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the CraftedDevAgent subsystem, derived from the provided TRD excerpts.

Where the TRD defines exact field names or exact literal values, they are reproduced verbatim.

---

### Consensus Run Request

Invocation contract for consensus execution.

#### Shape

```python
await self._consensus.run(
    task=str,
    context=str,
    language=str,
)
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Free-form task description. Example source usage: `f"Implement: {spec.title}"` |
| `context` | `str` | Yes | Context string passed to the consensus engine |
| `language` | `str` | Yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Return Shape

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Generated code output |

#### Required Usage

Language must always be passed:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

---

### Failure Strategy Selection

Internal strategy-selection interface for fix loops.

#### Shape

```python
_choose_strategy(failure_type, attempt, records)
```

#### Fields

| Parameter | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | unspecified | Yes | Failure category input |
| `attempt` | unspecified | Yes | Current attempt number |
| `records` | unspecified | Yes | Prior fix-loop records |

#### Contract

- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup-table strategy selection is non-conformant.

---

### Fix Arbitration

Internal arbitration interface for choosing a fix candidate.

#### Shape

```python
_score_fix()
```

#### Contract

- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Length-based arbitration is forbidden.

#### Forbidden Pattern

```python
winner = max(claude_fix, openai_fix, key=len)
```

---

### TrustFlow Event

Every action outcome must emit a TrustFlow event.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique; generated via CSPRNG, not sequential |
| `session_id` | `string` | Yes | Session identifier |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | Yes | Event type identifier |
| `payload_hash` | `string` | Yes | Must be SHA-256 of the serialized action payload |

#### Contract

- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission must not be silently skipped.
- Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.

---

### VTZEnforcementDecision Record

Produced when VTZ policy denies an action.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | Must be exactly `block` for VTZ policy denial |

#### Contract

- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### CTX-ID Token

Identity/enforcement token used in agent actions.

#### Fields

Field-level structure is not defined in the provided TRD excerpt. The following token-level constraints are mandatory.

#### Contract

- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- The old token is invalidated immediately on rotation.
- Expired CTX-ID must be rejected.
- Clock-skew tolerance is defined per deployment.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from surrounding context when CTX-ID is missing.

---

### Agent Action Processing Entry Point

Applies to every entry point that processes an agent action.

#### Required Inputs

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Must be validated first |
| `session_id` | `string` | Yes | Required for TrustFlow emission |
| `action payload` | serialized object | Yes | Used to compute `payload_hash` |

#### Contract

- CTX-ID validation must occur first.
- CTX-ID validation failure must result in immediate rejection.
- No partial processing is permitted before CTX-ID validation succeeds.
- VTZ policy evaluation must occur before execution.

---

## Enums and Constants

### Supported Consensus Languages

Exact allowed values:

```text
"python" | "swift" | "go" | "typescript" | "rust"
```

### Language System Selection

| `language` value | Selected system |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected |
| `"python"` | `GENERATION_SYSTEM` |

No source-defined mappings were provided for `"go"`, `"typescript"`, or `"rust"` beyond their validity as `language` values.

---

### Trust Outcomes

Exact action outcome values referenced by contract:

```text
allow
restrict
block
```

---

### Special Security Value

```text
SECURITY_REFUSAL
```

Contract:
- When `SECURITY_REFUSAL` output is returned from the LLM: stop, gate, log.
- Never retry to bypass.

---

### Missing Identity Classification

```text
UNTRUSTED
```

Contract:
- Missing CTX-ID must be treated as `UNTRUSTED`.

---

### Logging Severity

```text
WARN
```

Contract:
- TrustFlow emission failure is a WARN-level audit event.

---

### Required Python Version

```text
Python 3.12
```

---

## Validation Rules

## 1. Consensus Engine Validation

### Required

- `language` must always be supplied.
- `language` must be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

### Invalid

- Omitting `language`
- Passing any other string value
- Using length-based fix arbitration instead of `_score_fix()`

---

## 2. Security Validation

### Hard Prohibitions

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Never bypass `SECURITY_REFUSAL`.

### Required

- Log HTTP status codes and error types only.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before being included in any LLM prompt.
- Context from external documents must go in the USER prompt, never the SYSTEM prompt.

---

## 3. Python Backend Validation

- Python code must target `Python 3.12`.
- Every function must have type annotations.
- Backend code must use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses are required for all structured data.
- Tests must use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be `>= 85%` on all new modules.
- `pyyaml` must be present in `requirements.txt`.

---

## 4. CAL Enforcement Validation

For every entry point that processes an agent action:

1. Validate `ctx_id` first.
2. If validation fails, reject immediately.
3. Do not partially process before successful validation.
4. Check VTZ policy before execution.
5. On VTZ deny, emit `VTZEnforcementDecision` with `verdict=block`.
6. Emit a TrustFlow event for every action outcome.
7. If TrustFlow emission fails, log and surface the failure.

Any deviation is non-conformant.

---

## 5. TrustFlow Validation

For every emitted TrustFlow event:

- `event_id` must be globally unique.
- `event_id` must come from CSPRNG.
- `event_id` must not be sequential.
- `ts` must be a UTC Unix timestamp with millisecond precision.
- `payload_hash` must equal the SHA-256 of the serialized action payload.
- Emission must be synchronous in the enforcement path.
- Async buffering is invalid.

---

## 6. CTX-ID Validation

- CTX-ID is immutable once issued.
- Rotation must create a new token.
- Rotation must immediately invalidate the old token.
- Expired tokens must be rejected.
- Validation must be against TrustLock public key.
- Software-only validation is rejected.
- Missing token must classify requester as `UNTRUSTED`.

---

## 7. VTZ Validation

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## Wire Format Examples

## Valid Payloads

### Valid Consensus Run Request

```json
{
  "task": "Implement: Add parser",
  "context": "Relevant implementation context",
  "language": "python"
}
```

### Valid TrustFlow Event

```json
{
  "event_id": "8f23a96f-61f3-4f87-a2f4-6a9b7d4d7a12",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
}
```

### Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

---

## Invalid Payloads

### Invalid Consensus Run Request: missing language

```json
{
  "task": "Implement: Add parser",
  "context": "Relevant implementation context"
}
```

Reason:
- `language` is required.

### Invalid Consensus Run Request: unsupported language

```json
{
  "task": "Implement: Add parser",
  "context": "Relevant implementation context",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid TrustFlow Event: missing required fields

```json
{
  "event_id": "123",
  "session_id": "sess_123"
}
```

Reason:
- Missing `ctx_id`, `ts`, `event_type`, and `payload_hash`.

### Invalid VTZEnforcementDecision

```json
{
  "verdict": "allow"
}
```

Reason:
- On VTZ denial, `verdict` must be exactly `block`.

### Invalid Security Handling

```json
{
  "llm_output": "SECURITY_REFUSAL",
  "action": "retry"
}
```

Reason:
- `SECURITY_REFUSAL` must cause stop, gate, and log. Retry is forbidden.

---

## Integration Points

## Consensus Engine

Required integration:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Rules:
- `language` must always be passed.
- `"swift"` selects `SWIFT_GENERATION_SYSTEM` and optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `"python"` selects `GENERATION_SYSTEM`.

---

## Fix Loop Integration

Required:
- Use `_choose_strategy(failure_type, attempt, records)` for strategy selection.
- Use `_score_fix()` for arbitration.

Forbidden:
- Any static lookup-table replacement for `_choose_strategy(...)`
- Any length-based arbitration such as:

```python
winner = max(claude_fix, openai_fix, key=len)
```

---

## File Write Integration

Before any disk write:

```python
path_security.validate_write_path()
```

Required:
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

---

## Prompt Construction Integration

Required:
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- External document context must be placed in the USER prompt.
- External document context must never be placed in the SYSTEM prompt.

---

## Trust and Enforcement Integration

Every agent action processing entry point must integrate:

1. CTX-ID validation
2. VTZ policy enforcement
3. TrustFlow emission

Execution order is mandatory:

1. Validate CTX-ID first
2. Reject immediately on failure
3. Evaluate VTZ policy
4. Execute only if allowed
5. Emit TrustFlow event for outcome
6. Surface TrustFlow emission failure

---

## Swift / Backend Boundary Constraints

Forbidden patterns:

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

Constraints:
- Force unwrap is forbidden.
- LLM API calls from Swift are forbidden.
- Backend credentials must not be read from Keychain by Python.
- Only Swift reads Keychain, and only to deliver via XPC.

---

## Test and Conformance Invocation

Before making changes, required command:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Conformance expectations:
- `pytest`, `ruff`, and `mypy` must pass.
- Coverage on new modules must be at least `85%`.