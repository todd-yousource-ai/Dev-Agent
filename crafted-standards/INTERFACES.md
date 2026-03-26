# Interface Contracts - CraftedApp

## Scope

This document defines the wire-format and API/data contracts for the CraftedApp subsystem, based strictly on the provided TRD interface requirements.

Where the source specifies a field or value exactly, it is reproduced exactly here.

---

## Data Structures

### TrustFlowEvent

Required for every action outcome `(allow, restrict, block)`.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique. MUST be generated via CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | Yes | Session identifier for the agent session. |
| `ctx_id` | `string` | Yes | CTX-ID token identifier bound to the session/action. |
| `ts` | `number` | Yes | MUST be UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. Exact allowed values are not specified in the provided TRDs. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. Expected serialized form must be stable within the implementation. |

#### Semantics
- Every TrustFlow event MUST include exactly the fields above at minimum.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

---

### VTZEnforcementDecision

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | MUST equal `block` when produced for VTZ policy denial. |

#### Minimum Contract
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

#### Notes
- No additional fields are specified in the provided source. Implementations MAY include internal fields, but they are not part of this contract unless documented elsewhere in the owning TRD.

---

### CTX-ID Token

Immutable trust token used for identity and VTZ binding.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Token value or identifier. MUST be immutable once issued. |

#### Semantics
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is permitted after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

#### Notes
- The internal token claims/schema are not specified in the provided source.
- Clock skew tolerance is deployment-defined and therefore not encoded here.

---

### Agent Action Payload

Opaque action payload processed by an entry point.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | Typically Yes | Required wherever a TrustFlow event must be emitted for the action. |
| `ctx_id` | `string` | Yes | MUST be validated first. Missing value is treated as `UNTRUSTED`. |
| `payload` | `object` | Yes | Serialized form is hashed using SHA-256 to produce `payload_hash`. |
| `action` | `string` | Implementation-defined | Action identifier checked against VTZ policy before execution. |

#### Semantics
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted before CTX-ID validation succeeds.
- Every action MUST be checked against VTZ policy BEFORE execution.

#### Notes
- The exact action schema is not specified in the provided TRDs.
- The `payload` object is treated as opaque for this contract; only hashing behavior is mandated.

---

### ConsensusRunRequest

Required usage contract for consensus engine invocation.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Example exact usage: `f"Implement: {spec.title}"` |
| `context` | `string` | Yes | Context string provided to consensus engine. |
| `language` | `string` | Yes | MUST be one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Semantics
Invocation contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

#### Result Contract

##### ConsensusRunResult

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Final generated code output. |

---

### Fix Arbitration Inputs

The TRD defines behavioral constraints on fix arbitration.

#### Strategy Selection Contract

A failure-aware loop strategy must use:

| Symbol | Kind | Required | Constraints |
|---|---|---:|---|
| `_choose_strategy` | function | Yes | MUST be called with `(failure_type, attempt, records)` |

#### Fix Scoring Contract

| Symbol | Kind | Required | Constraints |
|---|---|---:|---|
| `_score_fix` | function | Yes | MUST arbitrate fixes based on assertion token overlap. |
| `failure_type` | implementation-defined | Yes | Input to `_choose_strategy`. |
| `attempt` | `integer` | Yes | Input to `_choose_strategy`. |
| `records` | collection | Yes | Input to `_choose_strategy`. |

#### Forbidden Pattern
Length-based fix arbitration is non-conformant:

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

---

## Enums and Constants

### Enforcement Verdict

| Value |
|---|
| `block` |

Used in `VTZEnforcementDecision.verdict` for VTZ policy denial.

---

### Trust Level / Identity Handling Constants

| Value | Meaning |
|---|---|
| `UNTRUSTED` | Required treatment for missing CTX-ID. |

---

### Supported Consensus Language Values

Exact allowed values:

| Value |
|---|
| `"python"` |
| `"swift"` |
| `"go"` |
| `"typescript"` |
| `"rust"` |

#### Routing Semantics
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### Logging / Audit Severity

| Value | Meaning |
|---|---|
| `WARN` | Severity for failed TrustFlow emission audit event. |

---

### Cryptographic / Time Constants

| Name | Value / Constraint |
|---|---|
| `payload_hash` algorithm | `SHA-256` |
| `ts` time basis | `UTC Unix timestamp with millisecond precision` |
| `event_id` generation | `CSPRNG` |
| `event_id` forbidden pattern | `not sequential` |

---

## Validation Rules

## 1. CAL Enforcement Contract

Every entry point that processes an agent action:

1. MUST call CTX-ID validation FIRST.
2. MUST immediately reject on CTX-ID validation failure.
3. MUST perform no partial processing before CTX-ID validation succeeds.
4. MUST check every action against VTZ policy BEFORE execution.
5. MUST produce a `VTZEnforcementDecision` record with `verdict=block` on VTZ denial.
6. MUST emit a TrustFlow event for every action outcome:
   - `allow`
   - `restrict`
   - `block`
7. MUST NOT silently continue if TrustFlow emission fails.
8. MUST log and surface TrustFlow emission failure.

---

## 2. TrustFlow Event Validation

A TrustFlow event is valid only if:

- `event_id` is present.
- `session_id` is present.
- `ctx_id` is present.
- `ts` is present.
- `event_type` is present.
- `payload_hash` is present.
- `event_id` is globally unique.
- `event_id` is generated by CSPRNG.
- `event_id` is not sequential.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `payload_hash` equals the SHA-256 of the serialized action payload.

### Emission Rules
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.

---

## 3. CTX-ID Validation

A CTX-ID is valid only if:

- It is present, unless the request is intentionally treated as `UNTRUSTED`.
- It is not expired.
- It validates against TrustLock public key.
- Validation is not software-only.

### Additional CTX-ID Rules
- Tokens are immutable once issued.
- Rotation MUST create a new token.
- Old token MUST be invalidated immediately upon rotation.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from surrounding context when CTX-ID is missing.

---

## 4. VTZ Enforcement Validation

VTZ enforcement is conformant only if:

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Every action is evaluated against VTZ policy before execution.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

## 5. Consensus Engine Validation

Consensus engine requests are valid only if:

- `language` is provided.
- `language` is exactly one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

### Required Call Shape

```python
await self._consensus.run(
    task=...,
    context=...,
    language=...,
)
```

### Invalid Usage
- Omitting `language`
- Using any language value outside the exact allowed set

---

## 6. Security-Related Interface Rules

These are interface-affecting behavioral requirements from the TRDs.

### Secrets and Credentials
- Never hardcode credentials, API keys, tokens, or secrets as string literals.

### Subprocess
- Never use `shell=True` in subprocess calls.

### Code / Content Execution
- Never call `eval()` or `exec()` on generated or external content.

### HTTP Logging
- Never log HTTP response bodies.
- Log status codes and error types only.

### File Writes
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

### Prompt Construction
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

### Security Refusal Handling
- When `SECURITY_REFUSAL` output is received from the LLM:
  - stop
  - gate
  - log
  - never retry to bypass

---

## 7. Swift / Backend Boundary Constraints

The following patterns are explicitly forbidden:

### Forbidden Swift Force Unwrap

```swift
let value = optional!
```

### Forbidden LLM API Call from Swift

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

### Forbidden Keychain Read for Backend

```swift
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
```

### Boundary Rule
- Only Swift reads Keychain, only to deliver via XPC.
- Python reads nothing from Keychain.

---

## 8. Python Module Contract

For Python implementations in this subsystem:

- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Testing framework: `pytest`
- Tests location: `tests/`
- Test structure mirrors `src/`
- Linting: `ruff`
- Type checking: `mypy`
- Both must pass clean
- Test coverage must be `≥ 85%` on all new modules
- `pyyaml` must be in `requirements.txt`

---

## Wire Format Examples

## TrustFlowEvent

### Valid

```json
{
  "event_id": "9b8df0df-8c7a-4f6d-9f8d-3d8d9c3f2b11",
  "session_id": "sess_01HZXA7V2K8M",
  "ctx_id": "ctx_01HZXA7W5R9N",
  "ts": 1717000123456,
  "event_type": "action.block",
  "payload_hash": "8c11d1d551df06a3ab0a31c6f5d2c8baf7fca6e7929c2d9a1d5f9d7d6a7a6f10"
}
```

Why valid:
- All required fields present
- `ts` is a Unix timestamp in milliseconds
- `payload_hash` is a SHA-256 hex string
- `event_id` is non-sequential in form

### Invalid: missing required field

```json
{
  "event_id": "9b8df0df-8c7a-4f6d-9f8d-3d8d9c3f2b11",
  "session_id": "sess_01HZXA7V2K8M",
  "ts": 1717000123456,
  "event_type": "action.block",
  "payload_hash": "8c11d1d551df06a3ab0a31c6f5d2c8baf7fca6e7929c2d9a1d5f9d7d6a7a6f10"
}
```

Why invalid:
- Missing `ctx_id`

### Invalid: wrong timestamp precision

```json
{
  "event_id": "9b8df0df-8c7a-4f6d-9f8d-3d8d9c3f2b11",
  "session_id": "sess_01HZXA7V2K8M",
  "ctx_id": "ctx_01HZXA7W5R9N",
  "ts": 1717000123,
  "event_type": "action.block",
  "payload_hash": "8c11d1d551df06a3ab0a31c6f5d2c8baf7fca6e7929c2d9a1d5f9d7d6a7a6f10"
}
```

Why invalid:
- `ts` is not millisecond precision

---

## VTZEnforcementDecision

### Valid

```json
{
  "verdict": "block"
}
```

### Invalid

```json
{
  "verdict": "allow"
}
```

Why invalid:
- Provided contract only specifies `verdict=block` for VTZ policy denial records

---

## ConsensusRunRequest

### Valid

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context",
  "language": "python"
}
```

### Valid

```json
{
  "task": "Implement: iOS Settings Screen",
  "context": "SwiftUI app context",
  "language": "swift"
}
```

### Invalid: missing language

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context"
}
```

Why invalid:
- `language` is required

### Invalid: unsupported language

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context",
  "language": "java"
}
```

Why invalid:
- `language` must be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`

---

## Agent Action Payload

### Valid

```json
{
  "session_id": "sess_01HZXA7V2K8M",
  "ctx_id": "ctx_01HZXA7W5R9N",
  "action": "tool.execute",
  "payload": {
    "tool": "search",
    "query": "example"
  }
}
```

Why valid:
- Contains `ctx_id`
- Contains serializable `payload`
- Can be checked against VTZ policy before execution

### Invalid: missing CTX-ID

```json
{
  "session_id": "sess_01HZXA7V2K8M",
  "action": "tool.execute",
  "payload": {
    "tool": "search",
    "query": "example"
  }
}
```

Why invalid / handling:
- Missing `ctx_id`
- Must be treated as `UNTRUSTED`
- Must not infer identity from context
- Must not proceed as if validated

---

## Integration Points

## 1. Enforcement Path

Processing order for any agent action entry point:

1. Receive action payload
2. Validate `ctx_id` FIRST
3. Reject immediately on CTX-ID validation failure
4. Evaluate VTZ policy BEFORE execution
5. If denied, produce `VTZEnforcementDecision` with `verdict=block`
6. Emit TrustFlow event synchronously
7. If TrustFlow emission fails, log and surface failure at WARN audit level

---

## 2. TrustLock

CTX-ID validation integrates with:

- `TrustLock public key`

Constraint:
- Software-only validation is rejected

---

## 3. VTZ Policy Layer

Action authorization integrates with VTZ policy enforcement.

Constraints:
- Session bound to EXACTLY ONE VTZ at CTX-ID issuance
- Cross-VTZ calls require explicit policy authorization
- Implicit authorization is denied
- Policy changes apply at NEXT CTX-ID issuance

---

## 4. Consensus Engine

Required invocation interface:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Routing behavior:
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `language="python"` selects `GENERATION_SYSTEM`

---

## 5. Path Security

Before any disk write, integrate with:

```python
path_security.validate_write_path()
```

Constraint:
- All file paths written to disk must pass validation before any write

---

## 6. LLM Prompt Construction

External content integration rules:

- Loaded document chunks must pass injection scanning before inclusion in prompts
- External document context goes in the USER prompt
- External document context never goes in the SYSTEM prompt
- `SECURITY_REFUSAL` output must stop processing and trigger gate + log behavior

---

## 7. Swift/XPC Boundary

Credential transport boundary:

- Only Swift reads Keychain
- Swift may deliver via XPC
- Python backend reads nothing from Keychain

---

## Non-Conformance Summary

A CraftedApp component is non-conformant if any of the following occurs:

- Missing CTX-ID-first validation
- Partial processing before CTX-ID validation
- Missing VTZ pre-execution check
- VTZ denial without `VTZEnforcementDecision` and `verdict=block`
- Missing TrustFlow emission for `allow`, `restrict`, or `block`
- Async-buffered TrustFlow emission in enforcement path
- Silent TrustFlow emission failure
- Mutable CTX-ID after issuance
- Missing explicit `language` in consensus calls
- Use of unsupported language value
- Length-based fix arbitration instead of `_score_fix`
- Software-only CTX-ID validation
- Cross-VTZ access without explicit authorization
- Any bypass of VTZ boundaries by application code