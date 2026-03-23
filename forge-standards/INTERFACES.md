# Interface Contracts - Crafted

This document defines the wire-format and API contract requirements for the Crafted subsystem, based on the provided TRD content.

## Data Structures

### ConsensusRunRequest

Request contract for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Free-text task description. |
| `context` | `string` | Yes | Context string supplied to the engine. |
| `language` | `string` | Yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. |

#### Required invocation form

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

### ConsensusRunResult

Result contract for consensus engine output.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Final generated code returned from consensus execution. |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | Must be exactly `block` when produced for VTZ policy denial. |

---

### TrustFlowEvent

Required event shape for all TrustFlow emissions.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique. Must be generated using CSPRNG. Must not be sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the event. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | Must be SHA-256 of the serialized action payload. |

---

### CTXIDToken

Immutable trust context token contract.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. |
| `expires_at` | `number \| string` | Unknown | Expiration is required by behavior, but concrete wire field name/type is not specified in the provided TRD text. |
| `public_key_validation` | `boolean` | Unknown | Validation must occur against TrustLock public key. Software-only validation is rejected. Concrete wire field not specified. |

> Note: The provided TRD content defines behavioral requirements for CTX-ID validation and lifecycle, but does not fully specify a concrete serialized token schema beyond `ctx_id`.

---

### AgentActionPayload

Serialized payload for an agent action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| *(implementation-defined payload fields)* | `object` | Yes | The serialized form must be hashable via SHA-256 to produce `payload_hash`. Concrete fields are not specified in the provided TRD text. |

---

### SecurityRefusalSignal

Security refusal output contract.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `value` | `string` | Yes | Must be exactly `SECURITY_REFUSAL`. When observed from the LLM, processing must stop, gate, and log. Never retry to bypass. |

---

## Enums and Constants

### SupportedLanguage

Exact allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Language System Selection

Derived behavior tied to `language`:

| `language` value | Selected system |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected |
| `"python"` | `GENERATION_SYSTEM` |

> No source-defined system selection mapping was provided for `"go"`, `"typescript"`, or `"rust"` beyond being allowed language values.

### VTZVerdict

Exact known value from provided TRD:

- `block`

### Security Constants

- `SECURITY_REFUSAL`

### TrustFlow Required Fields

Every TrustFlow event MUST include exactly these named fields:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

### Hash Algorithm

- `SHA-256`

### Timestamp Format

- `UTC Unix timestamp with millisecond precision`

---

## Validation Rules

## 1. Consensus Engine Request Validation

### Required fields
- `task` MUST be present.
- `context` MUST be present.
- `language` MUST be present.

### Language validation
- `language` MUST be exactly one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

### Invocation requirement
- All consensus engine calls MUST pass `language`.
- Omission of `language` is non-conformant.

---

## 2. Fix Strategy and Arbitration Rules

### Strategy selection
- Fix loop strategy MUST be failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- A static lookup table for fix loop strategy is non-conformant.

### Arbitration
- Fix arbitration MUST use `_score_fix()` based on assertion token overlap.
- Length-based arbitration is forbidden.

#### Forbidden example

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

---

## 3. CAL Enforcement Contract

Every entry point that processes an agent action MUST satisfy all of the following:

- MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- MUST perform no partial processing after CTX-ID validation failure.
- MUST check every action against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- TrustFlow emission failure MUST NOT silently continue.
- TrustFlow emission failure MUST be logged and surfaced.

---

## 4. TrustFlow Emission Contract

For every TrustFlow event:

- `event_id` MUST be globally unique.
- `event_id` MUST be generated using CSPRNG.
- `event_id` MUST NOT be sequential.
- `ts` MUST be a UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be the SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission MUST NOT be treated as a silent skip.

---

## 5. CTX-ID Contract

- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is permitted after issuance.
- CTX-ID rotation MUST create a new token.
- The old token MUST be invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from surrounding context when CTX-ID is missing.

---

## 6. VTZ Enforcement Contract

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance.
- VTZ policy changes do not apply mid-session.

---

## 7. Security Rules

### Credentials and secrets
- Never hardcode credentials, API keys, tokens, or secrets as string literals.

### Subprocess safety
- Never use `shell=True` in subprocess calls.

### Code execution safety
- Never call `eval()` or `exec()` on any generated or external content.

### Logging safety
- Never log HTTP response bodies.
- Log status codes and error types only.

### File write safety
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

### Prompt injection safety
- All loaded document chunks MUST pass injection scanning before being included in any LLM prompt.

### Prompt placement
- Context from external documents MUST go in the USER prompt.
- Context from external documents MUST never go in the SYSTEM prompt.

### Security refusal handling
- When `SECURITY_REFUSAL` output is observed from the LLM:
  - stop
  - gate
  - log
  - never retry to bypass

---

## 8. Python Backend Rules

- Python version MUST be 3.12.
- Every function MUST have type annotations.
- Backend code MUST use `async/await` throughout.
- Blocking calls on the event loop are not permitted.
- Dataclasses MUST be used for all structured data.
- Tests MUST use `pytest`.
- Tests MUST live in `tests/` and mirror `src/` structure.
- `ruff` MUST pass clean.
- `mypy` MUST pass clean.
- Test coverage on all new modules MUST be at least 85%.
- `pyyaml` MUST be present in `requirements.txt`.

---

## 9. Swift-Specific Prohibitions

### Forbidden force unwrap

```swift
let value = optional!
```

### Forbidden LLM API call from Swift

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

### Forbidden backend token read from Keychain

```swift
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
```

Constraint:
- Only Swift reads Keychain, only to deliver via XPC.
- Python reads nothing from Keychain.

---

## Wire Format Examples

## Valid Payloads

### Valid `ConsensusRunRequest`

```json
{
  "task": "Implement: Add trustflow emission",
  "context": "Entry point validates CTX-ID before VTZ policy enforcement.",
  "language": "python"
}
```

### Valid `ConsensusRunRequest` for Swift

```json
{
  "task": "Implement: Build settings screen",
  "context": "UI keywords detected; use Swift generation path.",
  "language": "swift"
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
  "event_id": "9d7c6f64-7d3c-4f7f-8e1b-4d6d2d9b9a91",
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "ts": 1712345678123,
  "event_type": "agent_action_blocked",
  "payload_hash": "0f4c3b2a1d5e6f7890abcdeffedcba09876543211234567890abcdef12345678"
}
```

### Valid security refusal signal

```json
{
  "value": "SECURITY_REFUSAL"
}
```

---

## Invalid Payloads

### Invalid `ConsensusRunRequest` missing `language`

```json
{
  "task": "Implement: Add tests",
  "context": "Need backend coverage"
}
```

Reason:
- `language` is required.

### Invalid `ConsensusRunRequest` with unsupported `language`

```json
{
  "task": "Implement: Add tests",
  "context": "Need backend coverage",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid `VTZEnforcementDecision`

```json
{
  "verdict": "allow"
}
```

Reason:
- The provided contract defines `verdict=block` as the required value for VTZ policy denial records.

### Invalid `TrustFlowEvent` missing required field

```json
{
  "event_id": "9d7c6f64-7d3c-4f7f-8e1b-4d6d2d9b9a91",
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "ts": 1712345678123,
  "event_type": "agent_action_blocked"
}
```

Reason:
- `payload_hash` is required.

### Invalid `TrustFlowEvent` with sequential ID semantics

```json
{
  "event_id": "10042",
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "ts": 1712345678123,
  "event_type": "agent_action_blocked",
  "payload_hash": "0f4c3b2a1d5e6f7890abcdeffedcba09876543211234567890abcdef12345678"
}
```

Reason:
- `event_id` must be globally unique, CSPRNG-generated, and not sequential.

### Invalid security refusal handling payload

```json
{
  "value": "SECURITY_REFUSAL",
  "retry": true
}
```

Reason:
- When `SECURITY_REFUSAL` occurs, processing must stop, gate, and log. Never retry to bypass.

---

## Integration Points

## Consensus Engine

### Call contract
- Invoke via `await self._consensus.run(...)`.
- Required named parameters:
  - `task`
  - `context`
  - `language`

### Output contract
- Read generated code from `result.final_code`.

### Language-dependent system routing
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` and optionally `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

## Enforcement Pipeline

Required processing order for every entry point that processes an agent action:

1. CTX-ID validation
2. Immediate rejection on CTX-ID validation failure
3. VTZ policy check
4. Produce `VTZEnforcementDecision` with `verdict=block` on denial
5. Emit TrustFlow event synchronously
6. Log and surface TrustFlow emission failure

---

## TrustLock

### Validation dependency
- CTX-ID validation MUST be performed against TrustLock public key.
- Software-only validation is rejected.

---

## Path Security

### Pre-write hook
- Every file path written to disk MUST be validated through:
  - `path_security.validate_write_path()`

---

## LLM Prompt Construction

### External document handling
- All loaded document chunks must pass injection scanning before inclusion in prompts.
- External document context MUST be placed in the USER prompt.
- External document context MUST NOT be placed in the SYSTEM prompt.

---

## Keychain and XPC Boundary

### Allowed behavior
- Only Swift reads Keychain.
- Swift may read Keychain only to deliver via XPC.

### Forbidden behavior
- Python backend reads nothing from Keychain.
- Swift must not make direct LLM API calls with Keychain-derived credentials.

---

## Test and Tooling Integration

### Required command before modifications

```bash
cd src && pytest ../tests/ -v --tb=short
```

### Required tooling contracts
- `pytest`
- `ruff`
- `mypy`
- `pyyaml` in `requirements.txt`

---

## Notes on Unspecified Fields

The provided TRD content includes several behavioral contracts without complete serialized schemas. The following are therefore normative as behavioral requirements, but not fully specified as wire objects in the source provided:

- Full CTX-ID token field schema
- Full agent action payload schema
- Enumerated `event_type` values
- Serialized schema for `allow` and `restrict` outcomes
- Concrete trust/audit error payload schemas

Where source text did not define field names, values, or types, this document does not invent them beyond the minimum necessary to reflect the stated contract.