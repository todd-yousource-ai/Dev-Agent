# Interface Contracts - CraftedApp

This document defines the wire format and API contract for the CraftedApp subsystem, based strictly on the provided TRD interface requirements.

## Data Structures

### ConsensusRunRequest

Request contract for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Free-form task description. Example source usage: `f"Implement: {spec.title}"` |
| `context` | `string` | Yes | Context string passed to consensus engine |
| `language` | `string` | Yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

### ConsensusRunResult

Result contract returned by the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output |

---

### TrustFlowEvent

Required event structure for all TrustFlow emissions.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique; generated via CSPRNG; must not be sequential |
| `session_id` | `string` | Yes | Session identifier |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action/session |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | Yes | Event type identifier |
| `payload_hash` | `string` | Yes | Must be SHA-256 of the serialized action payload |

---

### VTZEnforcementDecision

Required record produced on VTZ policy denial.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | Must be exactly `block` for VTZ policy denial |

No additional fields are specified in the provided TRD content.

---

### CTXIDToken

Logical token contract for CTX-ID handling.

The provided TRD defines behavioral constraints but does not enumerate token fields. Therefore, only the following interface-level guarantees are normative:

| Property | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Must be validated first at every entry point that processes an agent action |

No other CTX-ID token fields are specified in the provided source.

---

### AgentActionPayload

Serialized action payload referenced by enforcement and TrustFlow hashing.

The provided TRD requires hashing of the serialized action payload but does not define its field schema. Therefore:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `payload` | `object` | Yes | Serialized form must be stable enough to compute `payload_hash = SHA-256(serialized action payload)` |

No concrete payload members are specified in the provided source.

## Enums and Constants

### SupportedLanguage

Exact allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Verdict

Exact known value from the provided TRD:

- `block`

### System Selection Constants

These names are part of the contract behavior for `language` routing:

| Language | Selected System |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected |
| `"python"` | `GENERATION_SYSTEM` |

No selection constants are defined in the provided source for `"go"`, `"typescript"`, or `"rust"`.

### Forbidden Patterns

These are prohibited contract-level behaviors.

#### Python
- `shell=True` in subprocess calls
- `eval()`
- `exec()`

#### Swift
- Force unwrap: `optional!`
- LLM API call from Swift
- Keychain read for backend

#### Fix Arbitration
- Length-based fix arbitration is forbidden
- `_score_fix()` must be used
- Fix loop strategy must use `_choose_strategy(failure_type, attempt, records)`

### Logging / Security Constants

| Name | Meaning |
|---|---|
| `SECURITY_REFUSAL` | If seen from the LLM, processing must stop, gate, and log; must not retry to bypass |

## Validation Rules

## Entry Point Enforcement

Every entry point that processes an agent action MUST satisfy all of the following in order:

1. Call CTX-ID validation first
2. If CTX-ID validation fails, immediately reject
3. Check the action against VTZ policy before execution
4. If VTZ policy denies, produce a `VTZEnforcementDecision` with `verdict=block`
5. Emit a TrustFlow event for every action outcome: allow, restrict, or block
6. If TrustFlow emission fails, do not silently continue; log and surface the failure

## TrustFlow Validation

For every `TrustFlowEvent`:

- `event_id` must be globally unique
- `event_id` must be generated using CSPRNG
- `event_id` must not be sequential
- `ts` must be a UTC Unix timestamp
- `ts` must include millisecond precision
- `payload_hash` must equal SHA-256 of the serialized action payload
- Emission must be synchronous in the enforcement path
- Async buffering is not permitted
- Failed emission is a WARN-level audit event
- Failed emission must not be silently skipped

## CTX-ID Validation

- CTX-ID tokens are immutable once issued
- Rotation creates a new token
- Old token is invalidated immediately upon rotation
- Expired CTX-ID must be rejected
- Clock skew tolerance is deployment-defined
- CTX-ID must be validated against TrustLock public key
- Software-only validation is rejected
- Missing CTX-ID must be treated as `UNTRUSTED`
- Identity must never be inferred from context when CTX-ID is missing

## VTZ Validation

- Every agent session is bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit cross-VTZ access is denied
- VTZ boundaries are structural and cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance
- VTZ policy changes do not take effect mid-session

## Consensus Engine Validation

For calls to the consensus engine:

- `language` must always be passed
- `language` must be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

Behavioral routing:

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM`
- `language="swift"` may also inject `SWIFT_UI_ADDENDUM` when UI keywords are detected
- `language="python"` selects `GENERATION_SYSTEM`

Fix behavior:

- Fix loop strategy must be failure-type-aware via `_choose_strategy(failure_type, attempt, records)`
- Fix arbitration must use `_score_fix()`
- Response length must not be used as arbitration criteria

## Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Never use `shell=True` in subprocess calls
- Never call `eval()` or `exec()` on generated or external content
- Never log HTTP response bodies
- Log HTTP status codes and error types only
- All file paths written to disk must pass `path_security.validate_write_path()` before any write
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt
- Context from external documents must go in the USER prompt, never the SYSTEM prompt
- On `SECURITY_REFUSAL` output from the LLM: stop, gate, log, and do not retry to bypass

## Python Requirements

- Python version: `3.12`
- All functions must have type annotations
- Backend must use `async/await` throughout
- No blocking calls on the event loop
- Dataclasses required for all structured data
- Tests must use `pytest`
- Tests live in `tests/`
- Tests mirror `src/` structure
- `ruff` must pass
- `mypy` must pass
- Test coverage must be `>= 85%` on all new modules
- `pyyaml` must be present in `requirements.txt`

## Wire Format Examples

## Valid Payloads

### Valid Consensus Engine Request

```json
{
  "task": "Implement: Add login endpoint",
  "context": "Relevant spec and constraints",
  "language": "python"
}
```

### Valid Consensus Engine Result

```json
{
  "final_code": "from dataclasses import dataclass\n..."
}
```

### Valid TrustFlow Event

```json
{
  "event_id": "b7d8c2b5-7f5d-4f50-8b0b-5f1bb7d4a9e1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678901,
  "event_type": "action.block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3edc7b3a6aeba4b2"
}
```

### Valid VTZ Enforcement Decision

```json
{
  "verdict": "block"
}
```

## Invalid Payloads

### Invalid Consensus Engine Request: Missing `language`

```json
{
  "task": "Implement: Add login endpoint",
  "context": "Relevant spec and constraints"
}
```

Reason:
- `language` is required

### Invalid Consensus Engine Request: Unsupported `language`

```json
{
  "task": "Implement: Add login endpoint",
  "context": "Relevant spec and constraints",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`

### Invalid TrustFlow Event: Missing Required Fields

```json
{
  "event_id": "123",
  "ctx_id": "ctx_abc",
  "event_type": "action.allow"
}
```

Reason:
- Missing `session_id`
- Missing `ts`
- Missing `payload_hash`

### Invalid VTZ Enforcement Decision

```json
{
  "verdict": "allow"
}
```

Reason:
- On VTZ policy denial, `verdict` must be exactly `block`

### Invalid Security Behavior Example

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- Length-based fix arbitration is forbidden
- `_score_fix()` must be used

### Invalid Swift Example

```swift
let value = optional!
```

Reason:
- Force unwrap is forbidden

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

### Inputs
- `task: string`
- `context: string`
- `language: "python" | "swift" | "go" | "typescript" | "rust"`

### Outputs
- `final_code: string`

## CTX-ID Validation

Integration requirement:
- Must be the first validation step at every entry point processing an agent action
- Must validate against TrustLock public key
- Missing or invalid CTX-ID causes immediate rejection

## VTZ Policy Enforcement

Integration requirement:
- Must execute before action execution
- Denial must produce `VTZEnforcementDecision { verdict: "block" }`

## TrustFlow Emission

Integration requirement:
- Must occur for every action outcome
- Must be synchronous in the enforcement path
- Failures must be logged and surfaced
- Failures are WARN-level audit events

## Path Security

Integration requirement:
- Every file write path must be validated with `path_security.validate_write_path()` before write

## Prompt Construction / Injection Scanning

Integration requirement:
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt
- External document context must be placed in the USER prompt only
- External document context must never be placed in the SYSTEM prompt

## Swift / Backend Credential Boundary

Integration requirement:
- Only Swift reads Keychain
- Swift may deliver values via XPC
- Python backend reads nothing from Keychain
- Swift must not make LLM API calls directly

## Undefined / Unspecified Fields

The following structures are referenced but not fully field-defined in the provided TRD material:

- CTX-ID token internal fields beyond `ctx_id`
- Agent action payload schema beyond serialized payload hashing
- Session object schema beyond `session_id`
- TrustFlow `event_type` value set
- Action outcome payload schemas for `allow`, `restrict`, `block`

These fields must not be invented without an owning TRD update. Only the explicitly defined fields and constraints in this document are normative.