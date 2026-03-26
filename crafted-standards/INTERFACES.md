# Interface Contracts - CraftedDevAgent

## Data Structures

This document defines the required interface and wire-format contracts for the CraftedDevAgent subsystem based on the provided TRD content.

Where the TRD specifies behavioral contracts without a concrete serialized schema, those contracts are documented as normative requirements. Only fields explicitly named in source are defined as wire fields.

---

### Consensus Run Request

Used when invoking the consensus engine.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---:|:---:|---|
| `task` | `string` | Yes | Free-form task description. Example source value: `"Implement: {spec.title}"` |
| `context` | `string` | Yes | Context string provided to the consensus engine |
| `language` | `string` | Yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Behavioral contract
- `language` MUST always be passed.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.
- Fix loop strategy MUST use `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration is forbidden.

---

### Consensus Run Result

Returned by the consensus engine.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---:|:---:|---|
| `final_code` | `string` | Yes | Final generated code output |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---:|:---:|---|
| `verdict` | `string` | Yes | For denial, MUST be exactly `block` |

#### Behavioral contract
- Every action MUST be checked against VTZ policy before execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlow Event

Audit/enforcement event emitted for every action outcome.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---:|:---:|---|
| `event_id` | `string` | Yes | MUST be globally unique; generated via CSPRNG; MUST NOT be sequential |
| `session_id` | `string` | Yes | Session identifier |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | Yes | Event type identifier |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload |

#### Behavioral contract
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be treated as a WARN-level audit event.
- Failed emission MUST NOT silently continue; the failure must be logged and surfaced.

---

### CTX-ID Token

The TRD defines validation and lifecycle requirements but does not provide a concrete token field schema.

#### Type
Opaque token / implementation-defined serialized value

#### Required contract
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Every entry point that processes an agent action MUST call CTX-ID validation first.
- CTX-ID validation failure MUST result in immediate rejection with no partial processing.

---

### Agent Action Payload

The TRD references an “action payload” for hashing, but does not define its schema.

#### Type
Implementation-defined object

#### Required contract
- The serialized action payload is the input to SHA-256 for `payload_hash`.
- Every processed agent action is subject to:
  1. CTX-ID validation first
  2. VTZ policy evaluation before execution
  3. TrustFlow emission for the outcome

---

## Enums and Constants

### `language`

Allowed values:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### VTZ enforcement verdict

Known required value from TRD:

- `block`

### Action outcomes for TrustFlow emission

Every action outcome MUST emit a TrustFlow event for:

- `allow`
- `restrict`
- `block`

### Special security sentinel

Known literal value:

- `SECURITY_REFUSAL`

#### Contract
- When `SECURITY_REFUSAL` output is seen from the LLM: stop, gate, log.
- Never retry to bypass.

### Named systems and functions

These are contract-significant identifiers referenced by the TRD:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`
- `_choose_strategy(failure_type, attempt, records)`
- `_score_fix()`
- `path_security.validate_write_path()`

These names must be used exactly as specified where applicable.

---

## Validation Rules

## 1. Entry-point enforcement order

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur first.
2. If CTX-ID validation fails, processing MUST stop immediately.
3. VTZ policy check MUST occur before execution.
4. If VTZ denies the action, a `VTZEnforcementDecision` with `verdict=block` MUST be produced.
5. A TrustFlow event MUST be emitted for every outcome.
6. TrustFlow emission failure MUST be logged and surfaced, not silently ignored.

## 2. TrustFlow validation

A TrustFlow event is valid only if:

- `event_id` is present
- `session_id` is present
- `ctx_id` is present
- `ts` is present
- `event_type` is present
- `payload_hash` is present
- `event_id` is globally unique
- `event_id` is CSPRNG-generated
- `event_id` is not sequential
- `ts` is a UTC Unix timestamp with millisecond precision
- `payload_hash` is the SHA-256 hash of the serialized action payload

## 3. CTX-ID validation

A CTX-ID is acceptable only if:

- it is present, unless the request is intentionally treated as `UNTRUSTED`
- it is not expired
- it validates against the TrustLock public key
- it has not been invalidated by rotation

Additional constraints:

- Missing CTX-ID MUST NOT be inferred from surrounding context.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Software-only validation is rejected.

## 4. VTZ enforcement

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

## 5. Consensus engine validation

A consensus invocation is valid only if:

- `task` is present
- `context` is present
- `language` is present
- `language` is one of the allowed literals

Additional constraints:

- Do not omit `language`.
- Do not use length-based fix arbitration.
- Use `_score_fix()` for fix arbitration.
- Use `_choose_strategy(failure_type, attempt, records)` for failure-type-aware fix strategy.

## 6. Security validation

### Credentials and secrets
- Never hardcode credentials, API keys, tokens, or secrets as string literals.

### Subprocesses
- Never use `shell=True` in subprocess calls.

### Code execution
- Never call `eval()` or `exec()` on generated or external content.

### Logging
- Never log HTTP response bodies.
- Log status codes and error types only.

### File writes
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

### Prompt injection handling
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

### LLM refusal handling
- On `SECURITY_REFUSAL`: stop, gate, log; do not retry to bypass.

## 7. Python backend constraints

Applicable when `language="python"` and/or backend Python code is involved:

- Python version: `3.12`
- Type annotations required on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Tests use `pytest`
- Tests live in `tests/` and mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage on all new modules must be `>= 85%`
- `pyyaml` must be in `requirements.txt`

## 8. Swift-specific prohibitions

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

Contract:
- Only Swift reads Keychain, and only to deliver via XPC.
- Backend Python reads nothing from Keychain.
- LLM API calls from Swift are forbidden.
- Force unwrap is forbidden.

---

## Wire Format Examples

## Valid payloads

### Valid Consensus Run Request

```json
{
  "task": "Implement: Add parser support",
  "context": "Existing parser lives in src/parser.py",
  "language": "python"
}
```

### Valid Consensus Run Result

```json
{
  "final_code": "from dataclasses import dataclass\n"
}
```

### Valid TrustFlow Event

```json
{
  "event_id": "6f7f6f8e-2d6d-4d1d-8af0-4f8b2a6b7c90",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678123,
  "event_type": "action.block",
  "payload_hash": "3b7e6d1b5f2c4f8b3a0e1d6a7c9f2b1e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0"
}
```

### Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

---

## Invalid payloads

### Invalid Consensus Run Request: missing `language`

```json
{
  "task": "Implement: Add parser support",
  "context": "Existing parser lives in src/parser.py"
}
```

Reason:
- `language` is required.

### Invalid Consensus Run Request: unsupported `language`

```json
{
  "task": "Implement: Add parser support",
  "context": "Existing parser lives in src/parser.py",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid TrustFlow Event: missing required field

```json
{
  "event_id": "abc",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678123,
  "payload_hash": "deadbeef"
}
```

Reason:
- `event_type` is required.

### Invalid VTZEnforcementDecision: wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- On VTZ denial, `verdict` must be exactly `block`.

### Invalid processing flow

```json
{
  "ctx_id": null,
  "action": "execute_without_validation"
}
```

Reason:
- Missing CTX-ID must be treated as `UNTRUSTED`.
- CTX-ID validation must happen first.
- Identity must never be inferred from context.

---

## Integration Points

## Consensus Engine

Required invocation shape:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### Contracts
- `language=spec.language` MUST be passed.
- `result.final_code` is the consumed output field.

## CAL enforcement path

Every entry point handling an agent action must integrate:

1. CTX-ID validation
2. VTZ policy check
3. VTZ denial record generation when applicable
4. TrustFlow event emission

## TrustFlow

The subsystem must emit a synchronous TrustFlow event in the enforcement path for every action outcome.

Required event fields:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

## Path security

Before any disk write:

- Call `path_security.validate_write_path()` on the target path.

## Prompt construction / LLM safety

- Scan loaded document chunks for injection before using them in prompts.
- Put external document context in the USER prompt only.
- Never place external document context in the SYSTEM prompt.
- On `SECURITY_REFUSAL`, stop, gate, and log.

## Testing and compliance

Before changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Required compliance targets:

- `pytest`
- `ruff`
- `mypy`
- coverage `>= 85%` on new modules

## Component ownership workflow

Before modifying a component:

1. Find the owning TRD via `README.md`
2. Read relevant TRD sections, especially:
   - interfaces
   - error contracts
   - security
   - testing requirements
3. Check TRD-11 if the change touches:
   - credentials
   - external content
   - generated code
   - CI

---

## Non-conformance conditions

A CraftedDevAgent component is non-conformant if it violates any required contract above, including but not limited to:

- omitting CTX-ID-first validation
- allowing partial processing after CTX-ID validation failure
- skipping VTZ enforcement before execution
- failing to produce `VTZEnforcementDecision` with `verdict=block` on denial
- omitting TrustFlow emission for any outcome
- silently skipping failed TrustFlow emission
- omitting `language` in consensus calls
- using length-based fix arbitration instead of `_score_fix()`
- failing to validate write paths with `path_security.validate_write_path()`
- retrying after `SECURITY_REFUSAL`
- using forbidden Swift/backend credential patterns