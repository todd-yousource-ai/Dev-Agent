# Interface Contracts - FullPlatform

## Data Structures

### Consensus Engine Invocation

#### `ConsensusRunRequest`
Request shape for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Non-empty. |
| `context` | `string` | yes | Context string supplied to the engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | yes | Must always be passed. Values exactly as shown. |

#### `ConsensusRunResult`
Result shape returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Generated code output. |

---

### TrustFlow Event

Every TrustFlow event MUST include the following fields.

#### `TrustFlowEvent`
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | Globally unique. Must be generated with CSPRNG. Must not be sequential. |
| `session_id` | `string` | yes | Session identifier. |
| `ctx_id` | `string` | yes | CTX-ID token identifier or serialized token reference used for validation context. |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | yes | Event type discriminator. |
| `payload_hash` | `string` | yes | SHA-256 of the serialized action payload. |

---

### VTZ Enforcement Decision

#### `VTZEnforcementDecision`
Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | Must be exactly `block`. |

No additional fields are defined by the provided TRD content.

---

### Structured Python Backend Data

The backend standard requires dataclasses for all structured data.

#### `StructuredData`
Abstract contract for backend structured objects.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _n/a_ | _n/a_ | _n/a_ | All structured backend data MUST be represented as Python dataclasses. Concrete fields are component-specific. |

---

## Enums and Constants

### Language Enum

Allowed `language` values for consensus execution:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

### Consensus System Selection Constants

When `language` is provided, the following selection contract applies:

| `language` value | System selected |
|---|---|
| `swift` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected |
| `python` | `GENERATION_SYSTEM` |

No exact constant mapping is defined in the provided TRD for `go`, `typescript`, or `rust` beyond the requirement that `language` must be passed with one of the allowed values.

### Security Refusal Sentinel

- `SECURITY_REFUSAL`

When this output is seen from the LLM:
- stop
- gate
- log
- never retry to bypass

### VTZ Verdict Enum

- `block`

---

## Validation Rules

### FullPlatform Entry Point Enforcement

Every entry point that processes an agent action MUST satisfy all of the following in order:

1. CTX-ID validation MUST be called first.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy before execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue; it MUST be logged and surfaced.

### TrustFlow Validation

For every `TrustFlowEvent`:

- `event_id` MUST be globally unique.
- `event_id` MUST be generated via CSPRNG.
- `event_id` MUST NOT be sequential.
- `ts` MUST be a UTC Unix timestamp.
- `ts` MUST have millisecond precision.
- `payload_hash` MUST be the SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be recorded as a WARN-level audit event.
- Failed emission MUST NOT be silently skipped.

### CTX-ID Validation Rules

- CTX-ID tokens are immutable once issued.
- No field modification is permitted after issuance.
- CTX-ID rotation creates a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from context when CTX-ID is missing.

### VTZ Enforcement Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance.
- VTZ policy changes do not take effect mid-session.

### Consensus Engine Validation Rules

For every consensus invocation:

- `language` MUST always be passed.
- `language` MUST be one of:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`

### Fix Arbitration Rules

- Failure handling uses `_choose_strategy(failure_type, attempt, records)`.
- Static lookup-table loop strategy is non-conformant.
- Fix arbitration uses `_score_fix()`.
- Length-based arbitration is forbidden.

#### Forbidden pattern
```python
winner = max(claude_fix, openai_fix, key=len)
```

### Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log, and do not retry to bypass.

### Backend Implementation Rules

- Python version: `3.12`
- Type annotations are required on every function.
- Backend must use `async/await` throughout.
- No blocking calls on the event loop.
- Structured backend data must use dataclasses.
- Tests must use `pytest`.
- Tests must live in `tests/` and mirror `src/` structure.
- `ruff` must pass.
- `mypy` must pass.
- Test coverage must be `>= 85%` on all new modules.
- `pyyaml` must be present in `requirements.txt`.

### Forbidden Swift / Platform Patterns

#### Forbidden Swift force unwrap
```swift
let value = optional!
```

#### Forbidden LLM API call from Swift
```swift
let client = AnthropicClient(apiKey: keychainValue)
```

#### Forbidden backend Keychain read
```swift
let token = KeychainKit.read("github_token")
```

Constraint:
- Only Swift reads Keychain.
- Swift reads Keychain only to deliver via XPC.
- Python backend reads nothing from Keychain.

---

## Wire Format Examples

## Valid Payloads

### Valid `ConsensusRunRequest`
```json
{
  "task": "Implement: Add TrustFlow emission",
  "context": "Relevant TRD context here",
  "language": "python"
}
```

### Valid `ConsensusRunResult`
```json
{
  "final_code": "async def emit_event() -> None:\n    pass\n"
}
```

### Valid `TrustFlowEvent`
```json
{
  "event_id": "b7e3d5d8-7d7e-4b1a-a4c0-1c2d9f8e6a11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce"
}
```

### Valid `VTZEnforcementDecision`
```json
{
  "verdict": "block"
}
```

## Invalid Payloads

### Invalid `ConsensusRunRequest` — missing `language`
```json
{
  "task": "Implement: Add TrustFlow emission",
  "context": "Relevant TRD context here"
}
```

Reason:
- `language` is required and must always be passed.

### Invalid `ConsensusRunRequest` — unsupported `language`
```json
{
  "task": "Implement: Add TrustFlow emission",
  "context": "Relevant TRD context here",
  "language": "java"
}
```

Reason:
- `language` must be one of `python`, `swift`, `go`, `typescript`, `rust`.

### Invalid `TrustFlowEvent` — missing required field
```json
{
  "event_id": "b7e3d5d8-7d7e-4b1a-a4c0-1c2d9f8e6a11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.allow"
}
```

Reason:
- `payload_hash` is required.

### Invalid `TrustFlowEvent` — non-millisecond timestamp semantics
```json
{
  "event_id": "b7e3d5d8-7d7e-4b1a-a4c0-1c2d9f8e6a11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600,
  "event_type": "action.allow",
  "payload_hash": "4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce"
}
```

Reason:
- `ts` must be UTC Unix timestamp with millisecond precision.

### Invalid `VTZEnforcementDecision` — wrong verdict
```json
{
  "verdict": "allow"
}
```

Reason:
- On VTZ policy denial, `verdict` must be exactly `block`.

---

## Integration Points

### Agent Action Processing Pipeline

A conformant FullPlatform processing path integrates these steps in order:

1. Receive agent action.
2. Validate CTX-ID first.
3. Reject immediately on CTX-ID validation failure.
4. Evaluate VTZ policy before execution.
5. If denied, emit `VTZEnforcementDecision` with `verdict=block`.
6. Emit `TrustFlowEvent` synchronously for every outcome.
7. Surface TrustFlow emission failure; do not silently continue.

### Consensus Engine Integration

Required invocation shape:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Integration requirements:

- `language=spec.language` is mandatory.
- `spec.language` must resolve to one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

### Security Integration Points

- Before any disk write: call `path_security.validate_write_path()`.
- Before any external document chunk enters an LLM prompt: perform injection scanning.
- External document context must be placed in the USER prompt only.
- If LLM returns `SECURITY_REFUSAL`, stop processing and gate the flow.

### Testing and Quality Gates

Before changes are made, the existing test command is:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Required quality gates for FullPlatform-conformant backend changes:

- `pytest`
- `ruff`
- `mypy`
- coverage `>= 85%` on new modules

### Non-Conformance Conditions

A component is non-conformant if it violates any Forge component contract listed above, including but not limited to:

- missing CTX-ID-first validation
- missing VTZ pre-execution policy check
- failure to emit TrustFlow events for all outcomes
- silent continuation after TrustFlow emission failure
- omitted `language` in consensus invocation
- length-based fix arbitration
- software-only CTX-ID validation
- backend Keychain reads
- unsafe file writes without `path_security.validate_write_path()`