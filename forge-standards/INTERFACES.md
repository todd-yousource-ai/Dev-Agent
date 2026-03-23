# Interface Contracts - CraftedDevAgent

## Data Structures

This document defines the wire-format and API contract for the CraftedDevAgent subsystem based on the provided TRD interface requirements.

Where the source specifies exact field names or exact literal values, they are reproduced exactly.

---

### ConsensusRunRequest

Request contract for invoking the consensus engine.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Free-form implementation task text. Example source usage: `"Implement: {spec.title}"` |
| `context` | `string` | yes | Context string supplied to consensus engine |
| `language` | `string` | yes | Must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Notes
- `language` is mandatory.
- Exact required call pattern from source:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
```

---

### ConsensusRunResult

Response contract returned by the consensus engine.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Generated code output |

#### Notes
- Source usage:

```python
code = result.final_code
```

---

### VTZEnforcementDecision

Required record produced when VTZ policy denies an action.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | Must be exactly `block` when produced for VTZ policy denial |

#### Notes
- Source requirement: “VTZ policy denial MUST produce a VTZEnforcementDecision record with `verdict=block`”.

Because no additional fields are provided in the source, no other fields are specified here.

---

### TrustFlowEvent

Required synchronous audit/enforcement event emitted for every action outcome.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | Must be globally unique; generated via CSPRNG; must not be sequential |
| `session_id` | `string` | yes | Session identifier |
| `ctx_id` | `string` | yes | CTX-ID associated with the action |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Event type identifier |
| `payload_hash` | `string` | yes | Must be SHA-256 of the serialized action payload |

#### Notes
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and must not be silently skipped.

---

### CTXIDToken

Logical token contract for CTX-ID handling.

#### Fields

The source does not define concrete serialized fields for the CTX-ID token. The following constraints therefore apply to the token as an opaque value:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Opaque CTX-ID token value; immutable once issued |

#### Behavioral constraints
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- Old token is invalidated immediately on rotation.
- Expired CTX-ID must be rejected.
- Validation must be performed against TrustLock public key.
- Missing `ctx_id` must be treated as `UNTRUSTED`.

---

### AgentActionPayload

Serialized action payload used in CAL/VTZ/TrustFlow enforcement path.

#### Fields

The source does not provide a concrete payload schema. The only enforced wire requirement is hashing behavior for the serialized action payload.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `<action payload>` | `object` | yes | Must be serializable for SHA-256 hashing into `payload_hash` |

#### Notes
- `payload_hash` in `TrustFlowEvent` must be SHA-256 of this serialized payload.
- Every entry point that processes an agent action must validate CTX-ID first, then check VTZ policy before execution.

---

## Enums and Constants

### Language

Allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

---

### Verdict

Known required value from source for `VTZEnforcementDecision.verdict`:

- `block`

No other verdict values are explicitly defined in the provided source for this record.

---

### Action Outcomes

Every action outcome that must emit a TrustFlow event:

- `allow`
- `restrict`
- `block`

These are outcome literals described by the enforcement contract.

---

### Special Security / Trust Literals

| Literal | Meaning |
|---|---|
| `UNTRUSTED` | Required treatment for missing CTX-ID |
| `SECURITY_REFUSAL` | LLM output sentinel; on receipt: stop, gate, log; never retry to bypass |

---

### Consensus System Selection Constants

Derived selection behavior:

| `language` | Selected system |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords detected |
| `"python"` | `GENERATION_SYSTEM` |

The source does not define equivalent named system constants for `"go"`, `"typescript"`, or `"rust"`.

---

## Validation Rules

## 1. Pre-Implementation Procedure

Before modifying the component:

1. Find the TRD that owns the component in `README.md`.
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
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## 2. Consensus Engine Invocation Rules

- The consensus engine call MUST include `language`.
- `language` MUST be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`
- Returned code MUST be read from `result.final_code`.
- Fix loop strategy is selected by `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration is forbidden.

### Forbidden pattern

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

---

## 3. CAL Enforcement Rules

Every entry point that processes an agent action MUST:

1. Call CTX-ID validation first.
2. Immediately reject on CTX-ID validation failure.
3. Check VTZ policy before execution.
4. Produce `VTZEnforcementDecision` with `verdict=block` on VTZ denial.
5. Emit a TrustFlow event for every action outcome.
6. Log and surface TrustFlow emission failure; must not silently continue.

---

## 4. TrustFlow Event Rules

For every `TrustFlowEvent`:

- `event_id` must be globally unique.
- `event_id` must be generated via CSPRNG.
- `event_id` must not be sequential.
- `ts` must be a UTC Unix timestamp with millisecond precision.
- `payload_hash` must be SHA-256 of the serialized action payload.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.

---

## 5. CTX-ID Validation Rules

- CTX-ID is immutable after issuance.
- Rotation creates a new token.
- Previous token is invalidated immediately.
- Expired CTX-ID must be rejected.
- Validation against TrustLock public key is mandatory.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from surrounding context when CTX-ID is missing.

---

## 6. VTZ Enforcement Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 7. Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Only log status codes and error types for HTTP failures.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` is returned by the LLM:
  - stop
  - gate
  - log
  - never retry to bypass

### Swift-specific forbidden patterns

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

Rules:
- Force unwrap is forbidden.
- LLM API calls from Swift are forbidden.
- Backend credential reads from Keychain are forbidden.
- Only Swift reads Keychain, and only to deliver via XPC.

---

## 8. Python Backend Rules

- Python version: `3.12`
- Type annotations are required on every function.
- Backend must use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses are required for all structured data.
- Tests must use `pytest`.
- Tests must live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Coverage must be at least `85%` on all new modules.
- `pyyaml` must be present in `requirements.txt`.

---

## Wire Format Examples

## 1. Valid ConsensusRunRequest

```json
{
  "task": "Implement: Add retry handling",
  "context": "Failure occurs when VTZ denial is returned from enforcement path.",
  "language": "python"
}
```

---

## 2. Invalid ConsensusRunRequest: missing language

```json
{
  "task": "Implement: Add retry handling",
  "context": "Failure occurs when VTZ denial is returned from enforcement path."
}
```

Reason:
- `language` is required.

---

## 3. Invalid ConsensusRunRequest: unsupported language

```json
{
  "task": "Implement: Add retry handling",
  "context": "Failure occurs when VTZ denial is returned from enforcement path.",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

---

## 4. Valid ConsensusRunResult

```json
{
  "final_code": "async def run() -> None:\n    pass\n"
}
```

---

## 5. Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

---

## 6. Invalid VTZEnforcementDecision

```json
{
  "verdict": "deny"
}
```

Reason:
- Source requires `verdict=block` for VTZ policy denial.

---

## 7. Valid TrustFlowEvent

```json
{
  "event_id": "b7f0d2b1-8f7a-4c1f-a6fd-9f2ec7d4b9af",
  "session_id": "sess_42",
  "ctx_id": "ctx_abc123",
  "ts": 1712345678.123,
  "event_type": "block",
  "payload_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd38b..."
}
```

Notes:
- Example `payload_hash` is illustrative SHA-256-format hex.
- `ts` is shown as Unix timestamp with millisecond precision.

---

## 8. Invalid TrustFlowEvent: missing required field

```json
{
  "event_id": "b7f0d2b1-8f7a-4c1f-a6fd-9f2ec7d4b9af",
  "session_id": "sess_42",
  "ts": 1712345678.123,
  "event_type": "allow",
  "payload_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd38b..."
}
```

Reason:
- `ctx_id` is required.

---

## 9. Invalid action processing flow

```json
{
  "session_id": "sess_42",
  "action": {
    "tool": "cross_vtz_call"
  }
}
```

Reasons:
- No `ctx_id` present.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must not be inferred.
- VTZ check must occur before execution.

---

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

Integration requirements:
- Must pass `language`.
- Must consume `result.final_code`.
- `"swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`.
- `"python"` selects `GENERATION_SYSTEM`.

---

## Fix Loop / Repair Arbitration

Required internal integration points:
- `_choose_strategy(failure_type, attempt, records)`
- `_score_fix()`

Forbidden integration pattern:
- Length-based arbitration using `key=len`

---

## Trust / Enforcement Stack

Required ordered integration sequence for every agent action entry point:

1. CTX-ID validation
2. VTZ policy enforcement
3. Action execution decision
4. `VTZEnforcementDecision` emission when denied with `verdict=block`
5. Synchronous `TrustFlowEvent` emission

---

## Path Security

Before any disk write:

- Call `path_security.validate_write_path()`

This validation must occur before the write operation.

---

## Prompt Construction / External Document Handling

- Loaded document chunks must pass injection scanning before inclusion in prompts.
- External document context must be placed in the USER prompt.
- External document context must never be placed in the SYSTEM prompt.

---

## Testing / Quality Tooling

Required integration commands and tools:
- `pytest`
- `ruff`
- `mypy`

Required pre-change test command:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Required dependency:
- `pyyaml` in `requirements.txt`

---

## Conformance Summary

A CraftedDevAgent implementation is non-conformant if any of the following are violated:

- Missing required `language` in consensus calls
- Use of length-based fix arbitration
- Agent action entry point that does not validate CTX-ID first
- VTZ denial without `VTZEnforcementDecision` with `verdict=block`
- Missing or asynchronous TrustFlow emission
- Missing required TrustFlow fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- CTX-ID treated as mutable
- Missing CTX-ID not treated as `UNTRUSTED`
- Cross-VTZ call allowed without explicit authorization
- Disk write without `path_security.validate_write_path()`
- Inclusion of unscanned document chunks in prompts
- External document context placed in SYSTEM prompt
- Retrying past `SECURITY_REFUSAL`
- Python backend violating async/type/dataclass/testing/tooling requirements