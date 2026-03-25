# Interface Contracts - CraftedDevAgent

Definitive wire format and API contract reference for the CraftedDevAgent subsystem.

## Data Structures

### ConsensusRunRequest

Request passed to the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Human-readable implementation task. |
| `context` | `string` | yes | Prompt context string. External document context must be included in the USER prompt, never the SYSTEM prompt. Any loaded document chunks included here must pass injection scanning first. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | yes | Must always be passed. Exact allowed values only. |

#### Required call shape

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### ConsensusRunResult

Result returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Generated code output selected by consensus. |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies execution.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | For denial, must be exactly `block`. |

---

### TrustFlowEvent

Audit event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | Must be globally unique. Must be generated using CSPRNG. Must not be sequential. |
| `session_id` | `string` | yes | Session identifier. |
| `ctx_id` | `string` | yes | CTX-ID associated with the action. Missing CTX-ID must be treated as untrusted. |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | yes | Event classification for allow, restrict, or block outcomes. |
| `payload_hash` | `string` | yes | Must be SHA-256 of the serialized action payload. |

---

### AgentAction

Logical action processed by a Crafted component entry point.

This structure is contractually required to satisfy CAL enforcement flow, but the source TRD excerpt does not define a canonical field list beyond the existence of an action payload.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Must be validated first, before any partial processing. |
| `payload` | `object` | yes | Serialized form is hashed into `TrustFlowEvent.payload_hash`. |
| `session_id` | `string` | yes | Must correspond to the emitted `TrustFlowEvent.session_id`. |

---

### SecurityRefusalSignal

Special model output condition.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `value` | `string` | yes | Must be exactly `SECURITY_REFUSAL`. On receipt: stop, gate, log. Never retry to bypass. |

---

## Enums and Constants

### Language

Exact allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Consensus System Selection Rules

These are selection constants/behaviors required by contract:

| `language` value | Selected system |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` |
| `"python"` | `GENERATION_SYSTEM` |

#### Swift addendum injection rule

`SWIFT_UI_ADDENDUM` is injected when UI keywords are detected.

### SecurityRefusal Constant

- `SECURITY_REFUSAL`

### VTZ verdict values

From provided source, the only exact required value is:

- `block`

### Forbidden patterns

These are explicitly non-conformant interface/behavior usages.

#### Forbidden fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason: length-based fix arbitration is forbidden. Use `_score_fix()`.

#### Required fix strategy selection

Fix loop strategy must be failure-type-aware via:

- `_choose_strategy(failure_type, attempt, records)`

It is not a static lookup table.

#### Required fix arbitration

Fix arbitration must use:

- `_score_fix()`

Basis: assertion token overlap, not response length.

#### Forbidden Swift/backend patterns

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
- LLM API call from Swift is forbidden.
- Keychain read for backend is forbidden.
- Only Swift reads Keychain, only to deliver via XPC.
- Python reads nothing from Keychain.

---

## Validation Rules

## Entry-point enforcement order

Every entry point that processes an agent action must satisfy all of the following:

1. Call CTX-ID validation first.
2. On CTX-ID validation failure, immediately reject.
3. Do not perform partial processing before CTX-ID validation succeeds.
4. Check every action against VTZ policy before execution.
5. If VTZ denies, produce a `VTZEnforcementDecision` with `verdict=block`.
6. Emit a `TrustFlowEvent` for every action outcome: allow, restrict, block.
7. TrustFlow emission failure must not silently continue; it must be logged and surfaced.

## TrustFlow validation

For every `TrustFlowEvent`:

- `event_id` must be globally unique.
- `event_id` must be CSPRNG-generated.
- `event_id` must not be sequential.
- `ts` must be a UTC Unix timestamp with millisecond precision.
- `payload_hash` must be SHA-256 of the serialized action payload.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.

## CTX-ID validation

- CTX-ID tokens are immutable once issued.
- No field modification is permitted after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID must be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as untrusted.
- Identity must never be inferred from surrounding context.

## VTZ enforcement

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

## Prompt and external-content handling

- Always pass `language` to consensus.
- External document context must go in the USER prompt, never the SYSTEM prompt.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- When `SECURITY_REFUSAL` is produced, stop, gate, and log.
- Never retry to bypass `SECURITY_REFUSAL`.

## Security constraints

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

## Python implementation contract

- Python version: `3.12`
- Type annotations required on every function.
- Use `async/await` throughout the backend.
- No blocking calls on the event loop.
- Dataclasses required for all structured data.
- Tests use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass.
- `mypy` must pass.
- Coverage must be `>= 85%` on all new modules.
- `pyyaml` must be present in `requirements.txt`.

## Required pre-change execution step

Before making changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```

## Required documentation lookup flow

Before writing code:

1. Find the TRD that owns the component in `README.md`.
2. Read relevant TRD sections, especially:
   - interfaces
   - error contracts
   - security
   - testing requirements
3. Check `TRD-11` if the change touches:
   - credentials
   - external content
   - generated code
   - CI

---

## Wire Format Examples

## Valid payloads

### Valid ConsensusRunRequest

```json
{
  "task": "Implement: Add CTX-ID validation to entry point",
  "context": "User prompt context only. Scanned external document chunks may appear here after injection scanning.",
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
  "event_id": "8f4d6f0d-9a7d-4e60-9b9c-9e2d1b8f6c31",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "4d967a4bd7320f3c1f5d38b1f1e4a6a7c9d3d98e5f0a1b2c3d4e5f60718293ab"
}
```

### Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Valid SECURITY_REFUSAL signal

```json
{
  "value": "SECURITY_REFUSAL"
}
```

## Invalid payloads

### Invalid ConsensusRunRequest: missing language

```json
{
  "task": "Implement feature",
  "context": "some context"
}
```

Reason: `language` must always be passed.

### Invalid ConsensusRunRequest: unsupported language

```json
{
  "task": "Implement feature",
  "context": "some context",
  "language": "java"
}
```

Reason: allowed values are only `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid TrustFlowEvent: sequential event_id and non-millisecond timestamp

```json
{
  "event_id": "1001",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600,
  "event_type": "allow",
  "payload_hash": "abc123"
}
```

Reasons:

- `event_id` must be globally unique and non-sequential.
- `ts` must be Unix time in milliseconds.
- `payload_hash` must be SHA-256 of the serialized action payload.

### Invalid VTZEnforcementDecision: wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason: denial record must use exact value `block`.

### Invalid behavior: forbidden fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason: must use `_score_fix()`.

### Invalid behavior: forbidden Swift force unwrap

```swift
let value = optional!
```

Reason: force unwrap is forbidden.

---

## Integration Points

## Consensus Engine

CraftedDevAgent must invoke the consensus engine with:

- `task`
- `context`
- `language`

Required result consumption:

- `result.final_code`

Selection behavior:

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` and optional `SWIFT_UI_ADDENDUM`
- `language="python"` selects `GENERATION_SYSTEM`

## TrustFlow

Every action outcome must emit a synchronous `TrustFlowEvent` in the enforcement path.

Required event fields:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Emission failure handling:

- WARN-level audit event
- must be logged
- must be surfaced
- must not be silently skipped

## CTX-ID / TrustLock

CTX-ID validation is a mandatory first gate on every action-processing entry point.

Validation requirements:

- validate against TrustLock public key
- reject expired tokens
- reject missing tokens as untrusted
- reject modified tokens
- old token invalid immediately upon rotation

## VTZ Policy Engine

Every action must be checked against VTZ policy before execution.

If denied:

- produce `VTZEnforcementDecision`
- set `verdict` to `block`
- emit TrustFlow event for the blocked outcome

Cross-VTZ calls:

- require explicit policy authorization
- otherwise denied

## Path Security

Before any file write, all write paths must be validated using:

- `path_security.validate_write_path()`

## Testing and Tooling

Required test command:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Required tooling contracts:

- `pytest`
- `ruff`
- `mypy`

Required repository structure:

- source under `src/`
- tests under `tests/`, mirroring `src/`

## Security-sensitive change review

If changes touch any of the following, `TRD-11` must be checked:

- credentials
- external content
- generated code
- CI