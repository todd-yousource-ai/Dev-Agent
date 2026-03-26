# Interface Contracts - CraftedAgent

## Data Structures

This section defines the wire-format and API contract requirements for the CraftedAgent subsystem based on the provided standards.

### TrustFlowEvent

Required for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique; generated via CSPRNG; MUST NOT be sequential |
| `session_id` | `string` | yes | Session identifier |
| `ctx_id` | `string` | yes | Validated CTX-ID token identifier |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Event type name |
| `payload_hash` | `string` | yes | SHA-256 of the serialized action payload |

#### Constraints
- Every TrustFlow event MUST include exactly the fields: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash`.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

---

### VTZEnforcementDecision

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | MUST equal `block` |

#### Constraints
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### ConsensusRunRequest

Invocation contract for consensus engine calls.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Example: `Implement: {spec.title}` |
| `context` | `string` | yes | Context string passed to consensus engine |
| `language` | `string` | yes | MUST be one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Required call shape

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

---

### ConsensusRunResult

Result returned from consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Generated code output |

---

### CTX-ID Token

Logical token contract for identity and trust binding.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Immutable once issued; validated first at every entry point processing an agent action |

#### Constraints
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification after issuance.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

---

### Agent Action Payload

Structured payload processed by an agent entry point.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | yes | Must identify the agent session |
| `ctx_id` | `string` | yes | Must be validated first |
| `action` | `object` | yes | Serialized action payload used to compute `payload_hash` |

#### Constraints
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection — no partial processing.
- Every action MUST be checked against VTZ policy BEFORE execution.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

## Enums and Constants

### Language

Allowed `ConsensusRunRequest.language` values:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### VTZ Enforcement Verdict

Known required verdict values:

- `block`

### Trust State Constants

Known required trust classification values:

- `UNTRUSTED`

### Backend generation system selection

These values are selected by `language`:

| Language | Selected system |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords detected |
| `"python"` | `GENERATION_SYSTEM` |

### Forbidden implementation patterns

These are contractually forbidden and MUST NOT appear in implementations.

#### Forbidden fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

#### Required fix strategy behavior
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Response length MUST NOT be used for fix arbitration.

#### Forbidden Swift patterns

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

#### Required credential boundary
- Only Swift reads Keychain.
- Only to deliver via XPC.
- Python reads nothing from Keychain.

---

## Validation Rules

## Entry point enforcement

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur first.
2. On CTX-ID validation failure, processing MUST stop immediately.
3. VTZ policy check MUST occur before execution.
4. If VTZ denies the action, a `VTZEnforcementDecision` with `verdict=block` MUST be produced.
5. Every outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
6. TrustFlow emission failure MUST NOT silently continue.

## TrustFlow validation

A valid TrustFlow event MUST satisfy all of the following:

- `event_id` is present.
- `event_id` is globally unique.
- `event_id` is CSPRNG-generated.
- `event_id` is not sequential.
- `session_id` is present.
- `ctx_id` is present.
- `ts` is present.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `event_type` is present.
- `payload_hash` is present.
- `payload_hash` is the SHA-256 of the serialized action payload.

## CTX-ID validation

- Missing `ctx_id` => treat as `UNTRUSTED`.
- Expired `ctx_id` => reject.
- Rotated old `ctx_id` => invalid immediately.
- Validation MUST be against TrustLock public key.
- Software-only validation is rejected.
- Identity MUST NOT be inferred from surrounding context when `ctx_id` is missing.

## VTZ validation

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

## Security validation

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on any generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` output is returned from the LLM: stop, gate, log. Never retry to bypass.

## Python implementation contract

- Python version: `3.12`
- Type annotations on every function.
- `async/await` throughout the backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- Tests use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be `≥ 85%` on all new modules.
- `pyyaml` must be in `requirements.txt`.

---

## Wire Format Examples

## Valid payloads

### Valid TrustFlow event

```json
{
  "event_id": "9d5d5f9a-1c0e-4a8d-9a72-2fd6c4a7f4d1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "3f79bb7b435b05321651daefd374cd21b4c6e7f0d5f5d8d7d3c6e9f1b2a4c8e1"
}
```

### Valid VTZ denial decision

```json
{
  "verdict": "block"
}
```

### Valid consensus request

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context",
  "language": "python"
}
```

### Valid consensus result

```json
{
  "final_code": "print('hello')\n"
}
```

### Valid agent action payload

```json
{
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "action": {
    "type": "tool_call",
    "name": "build_component",
    "arguments": {
      "target": "CraftedAgent"
    }
  }
}
```

## Invalid payloads

### Invalid TrustFlow event: missing required field

```json
{
  "event_id": "9d5d5f9a-1c0e-4a8d-9a72-2fd6c4a7f4d1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "allow"
}
```

Invalid because `payload_hash` is required.

### Invalid consensus request: unsupported language

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context",
  "language": "java"
}
```

Invalid because `language` MUST be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid VTZ decision: wrong verdict

```json
{
  "verdict": "allow"
}
```

Invalid because VTZ denial MUST produce `verdict=block`.

### Invalid agent action payload: missing ctx_id

```json
{
  "session_id": "sess_123",
  "action": {
    "type": "tool_call"
  }
}
```

Invalid because `ctx_id` is required on the payload, and missing CTX-ID must be treated as `UNTRUSTED` and rejected per enforcement flow.

---

## Integration Points

## Consensus Engine

CraftedAgent integrations with the consensus engine MUST use:

- `await self._consensus.run(...)`
- Required arguments:
  - `task`
  - `context`
  - `language`

Required usage:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Selection behavior:
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords detected.
- `language="python"` selects `GENERATION_SYSTEM`.

## TrustLock

CTX-ID validation MUST be performed against TrustLock public key.

## VTZ policy engine

Every action MUST be checked against VTZ policy before execution.

## TrustFlow audit pipeline

Every action outcome MUST synchronously emit a TrustFlow event containing:
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

## Path security

Before any file write, integrations MUST call:

```python
path_security.validate_write_path()
```

## Prompt assembly / document ingestion

- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST be placed in the USER prompt, never the SYSTEM prompt.

## LLM security gate

If the LLM outputs `SECURITY_REFUSAL`:
- stop
- gate
- log
- never retry to bypass

## Testing / developer workflow integration

Before implementation changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```