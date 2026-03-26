# Interface Contracts - CraftedDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the CraftedDevAgent subsystem based on the provided TRD interface content.

Where the TRD specifies mandatory behavior but does not define a concrete transport object, this document expresses the minimum required contract as normative structured data.

---

### ConsensusRunRequest

Request contract for invoking the consensus engine.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Free-text task description. Example from TRD: `"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string supplied to the consensus engine. External document context, when present, MUST be placed in the USER prompt, never the SYSTEM prompt. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. Values must appear exactly as listed. |

#### Behavioral constraints

- `language` MUST always be supplied.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.
- Fix loop strategy MUST be failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()` based on assertion token overlap.
- Length-based fix arbitration is forbidden.

---

### ConsensusRunResult

Result contract returned by the consensus engine.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output selected by the consensus engine. |

---

### VTZEnforcementDecision

Required record produced when VTZ policy denies an action.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | Yes | Must be exactly `block` when produced due to VTZ policy denial. |

#### Behavioral constraints

- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Required event emitted for every action outcome.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique. Must be generated with CSPRNG. Must not be sequential. |
| `session_id` | `string` | Yes | Session identifier for the agent session. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. Missing CTX-ID must be treated as untrusted at validation time. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event classification for the action outcome. |
| `payload_hash` | `string` | Yes | Must be SHA-256 of the serialized action payload. |

#### Behavioral constraints

- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be a WARN-level audit event.
- Failed emission MUST NOT silently continue.

---

### CTXIDToken

Logical contract for CTX-ID validation and lifecycle.

#### Fields

The provided TRD excerpt does not enumerate CTX-ID token fields. The following constraints are therefore normative only for the visible field usage and lifecycle semantics.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable identifier once issued. Required for trusted processing. |

#### Behavioral constraints

- CTX-ID validation MUST be the FIRST step for every entry point that processes an agent action.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted after CTX-ID validation failure.
- CTX-ID tokens are immutable once issued.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity must never be inferred from context when `ctx_id` is missing.

---

### AgentActionEntryPoint

Normative processing contract for any entry point that processes an agent action.

#### Required processing sequence

1. CTX-ID validation FIRST
2. Immediate rejection on CTX-ID validation failure
3. VTZ policy check BEFORE execution
4. Produce `VTZEnforcementDecision` with `verdict=block` on VTZ denial
5. Emit `TrustFlowEvent` for every outcome
6. Surface TrustFlow emission failures as WARN-level audit events

This is a sequencing contract, not a standalone wire object.

---

## Enums and Constants

### SupportedLanguage

Exact allowed values for consensus engine language selection:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### VTZVerdict

Known required value from the TRD:

- `"block"`

### ActionOutcome

Required action outcome categories for TrustFlow emission:

- `"allow"`
- `"restrict"`
- `"block"`

### Special Security Sentinel

- `SECURITY_REFUSAL`

#### Constraint

When `SECURITY_REFUSAL` output is seen from the LLM:
- stop
- gate
- log
- never retry to bypass

### System Selection Constants

Named constants referenced by contract:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

These names must appear exactly as above when used in implementation logic.

### Python Platform Requirements

- Python version: `3.12`
- Required package: `pyyaml`

These are environment and dependency contract requirements, not payload fields.

---

## Validation Rules

## 1. Consensus Engine Invocation

- Every consensus engine call MUST pass `language`.
- `language` MUST be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`
- Omission of `language` is non-conformant.
- `final_code` is the required output field consumed from the result.

### Forbidden logic

The following is explicitly forbidden:

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

Implementations MUST use `_score_fix()` for arbitration, not response length.

---

## 2. Security Validation

### Credentials and secrets

- Never hardcode credentials, API keys, tokens, or secrets as string literals.

### Subprocess usage

- Never use `shell=True` in subprocess calls.

### Dynamic execution

- Never call `eval()` or `exec()` on generated or external content.

### Logging

- Never log HTTP response bodies.
- Log status codes and error types only.

### File writes

- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

### Prompt injection safety

- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.

### Security refusal handling

- On `SECURITY_REFUSAL`, processing MUST stop, gate, and log.
- The system MUST NOT retry to bypass.

---

## 3. CAL Enforcement Validation

- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is allowed before successful validation.
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ denial MUST produce `VTZEnforcementDecision` with `verdict=block`.
- Every action outcome MUST emit a `TrustFlowEvent`.
- TrustFlow emission failure MUST NOT silently continue.

---

## 4. TrustFlow Event Validation

### `event_id`

- Required
- String
- Must be globally unique
- Must be generated using CSPRNG
- Must not be sequential

### `session_id`

- Required
- String

### `ctx_id`

- Required on emitted event
- String

### `ts`

- Required
- UTC Unix timestamp
- Millisecond precision required

### `event_type`

- Required
- String

### `payload_hash`

- Required
- String
- Must be SHA-256 of the serialized action payload

### Emission mode

- Emission in enforcement path MUST be synchronous
- Async buffering is forbidden

### Failure mode

- Failed emission MUST be logged/surfaced as WARN-level audit event
- Silent skip is forbidden

---

## 5. CTX-ID Validation

- CTX-ID is immutable after issuance.
- Rotation MUST create a new token.
- Old token MUST be invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Validation MUST use TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.

---

## 6. VTZ Enforcement

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 7. Swift-Specific Forbidden Operations

The following are explicitly forbidden:

```swift
let value = optional!
```

- Force unwrap is forbidden.

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

- LLM API calls from Swift are forbidden.

```swift
let token = KeychainKit.read("github_token")
```

- Backend token reads from Keychain are forbidden.
- Only Swift reads Keychain, and only to deliver via XPC.

---

## 8. Python Backend Requirements

- Python `3.12`
- Type annotations on every function
- `async/await` throughout backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- `pytest` for tests
- Tests live in `tests/` and mirror `src/` structure
- `ruff` for linting
- `mypy` for type checking
- Both `ruff` and `mypy` must pass clean
- Test coverage must be `>= 85%` on all new modules
- `pyyaml` must be present in `requirements.txt`

---

## Wire Format Examples

## Valid Payloads

### Valid `ConsensusRunRequest`

```json
{
  "task": "Implement: Add repository sync",
  "context": "Use the existing backend service layer. External document context is user-supplied.",
  "language": "python"
}
```

### Valid `ConsensusRunResult`

```json
{
  "final_code": "from dataclasses import dataclass\n\n@dataclass\nclass Example:\n    value: str\n"
}
```

### Valid `VTZEnforcementDecision`

```json
{
  "verdict": "block"
}
```

### Valid `TrustFlowEvent`

```json
{
  "event_id": "8d5ed57d-7204-4b2a-bf4a-df5f6da9c7d1",
  "session_id": "sess_01JABCXYZ123",
  "ctx_id": "ctx_01JABCXYZ123",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "7b3d5aeca9c1b1d0a26c9f1f9b9d4b2cf9d9d8f0a1b2c3d4e5f60718293a4b5c"
}
```

## Invalid Payloads

### Invalid `ConsensusRunRequest` without `language`

```json
{
  "task": "Implement: Add repository sync",
  "context": "Missing language"
}
```

Reason:
- `language` is required.

### Invalid `ConsensusRunRequest` with unsupported language

```json
{
  "task": "Implement: Add repository sync",
  "context": "Use backend",
  "language": "java"
}
```

Reason:
- `language` must be one of `"python" | "swift" | "go" | "typescript" | "rust"`.

### Invalid `VTZEnforcementDecision`

```json
{
  "verdict": "allow"
}
```

Reason:
- For VTZ denial, verdict must be exactly `"block"`.

### Invalid `TrustFlowEvent` missing `payload_hash`

```json
{
  "event_id": "8d5ed57d-7204-4b2a-bf4a-df5f6da9c7d1",
  "session_id": "sess_01JABCXYZ123",
  "ctx_id": "ctx_01JABCXYZ123",
  "ts": 1735689600123,
  "event_type": "allow"
}
```

Reason:
- `payload_hash` is required.

### Invalid `TrustFlowEvent` with second-precision timestamp

```json
{
  "event_id": "8d5ed57d-7204-4b2a-bf4a-df5f6da9c7d1",
  "session_id": "sess_01JABCXYZ123",
  "ctx_id": "ctx_01JABCXYZ123",
  "ts": 1735689600,
  "event_type": "allow",
  "payload_hash": "7b3d5aeca9c1b1d0a26c9f1f9b9d4b2cf9d9d8f0a1b2c3d4e5f60718293a4b5c"
}
```

Reason:
- `ts` must be UTC Unix timestamp with millisecond precision.

---

## Integration Points

## Consensus Engine

Required usage pattern:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

### Integration contract

- `self._consensus.run(...)` must accept:
  - `task: string`
  - `context: string`
  - `language: "python" | "swift" | "go" | "typescript" | "rust"`
- The returned object must expose:
  - `final_code: string`

---

## Path Security

Before any disk write:

- Call `path_security.validate_write_path()`

### Contract

| Symbol | Kind | Required | Constraint |
|---|---|---:|---|
| `path_security.validate_write_path()` | function | Yes | Must be called before any write to disk. |

---

## TrustLock Validation

CTX-ID validation must use:

- TrustLock public key

### Contract

Software-only validation is non-conformant.

---

## XPC / Keychain Boundary

- Only Swift reads Keychain
- Swift may read Keychain only to deliver via XPC
- Python backend reads nothing from Keychain

This is a cross-component boundary contract.

---

## Test Execution Contract

Before making changes, run:

```bash
cd src && pytest ../tests/ -v --tb=short
```

This is a required process contract for agents modifying the subsystem.

---

## Conformance Notes

A CraftedDevAgent component is non-conformant if it violates any of the following:

- Missing required `language` in consensus engine invocation
- Length-based fix arbitration
- Missing CTX-ID validation first
- Partial processing after CTX-ID validation failure
- Missing VTZ policy check before execution
- Missing `VTZEnforcementDecision` with `verdict=block` on VTZ denial
- Missing `TrustFlowEvent` on any action outcome
- Async-buffered TrustFlow emission in enforcement path
- Silent TrustFlow emission failure
- File write without `path_security.validate_write_path()`
- Inclusion of unscanned document chunks in LLM prompts
- External document context in SYSTEM prompt
- Retry after `SECURITY_REFUSAL`
- Any forbidden Swift operation listed above
- Any forbidden security operation listed above