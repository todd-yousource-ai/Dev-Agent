# Interface Contracts - ForgeAgent

This document defines the wire-format and API contract reference for the ForgeAgent subsystem, based only on the provided TRD excerpts and standards. All field names, values, and constraints are listed exactly where specified. Where the source defines a required call shape or record contract, it is treated as normative.

## Data Structures

### ConsensusRunRequest

Request shape for invoking the consensus engine.

```python
await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Free-form task string. Example source value: `f"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string passed to consensus engine. |
| `language` | `string` | Yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. |

#### Constraints

- `language` MUST always be passed.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result shape returned by the consensus engine.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Final generated code output. |

#### Source usage

```python
code = result.final_code
```

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | For policy denial, MUST be exactly `block`. |

#### Constraints

- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Audit/enforcement event emitted for every action outcome.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique. CSPRNG-generated. MUST NOT be sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Constraints

- Every TrustFlow event MUST include all fields above.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### AgentActionPayload

Serialized action payload referenced by the TrustFlow hashing contract.

#### Fields

Not structurally defined in the provided source.

#### Constraints

- `payload_hash` in `TrustFlowEvent` MUST be the SHA-256 of the serialized action payload.
- Serialization format is not specified in the provided source; implementations MUST ensure deterministic serialization for hashing consistency.

---

### CTXIDToken

CTX-ID token contract.

#### Fields

Fields are not enumerated in the provided source.

#### Constraints

- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is permitted after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from context when CTX-ID is missing.

---

### AgentSession

Session-level binding contract.

#### Fields

Not structurally defined in the provided source.

#### Constraints

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

### LoadedDocumentChunk

External document chunk used in prompts.

#### Fields

Not structurally defined in the provided source.

#### Constraints

- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

---

### PathWriteRequest

Filesystem write operation contract.

#### Fields

Not structurally defined in the provided source.

#### Constraints

- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

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

### VTZEnforcementVerdict

Known required value from source:

- `block`

Additional values are implied by action outcomes but not defined as `VTZEnforcementDecision.verdict` values in the provided source.

---

### ActionOutcome

Every action outcome MUST emit a TrustFlow event. Source-defined outcomes:

- `allow`
- `restrict`
- `block`

---

### Missing CTX-ID Trust State

Source-defined value:

- `UNTRUSTED`

---

### Security Refusal Sentinel

Source-defined output sentinel:

- `SECURITY_REFUSAL`

#### Constraint

- When `SECURITY_REFUSAL` output is seen from the LLM: stop, gate, log. Never retry to bypass.

---

### Generation System Selectors

Source-defined constants:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

#### Selection rules

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### Fix Loop Strategy API

Source-defined strategy hook:

- `_choose_strategy(failure_type, attempt, records)`

#### Constraint

- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup table strategy is not conformant.

---

### Fix Arbitration API

Source-defined scoring hook:

- `_score_fix()`

#### Constraints

- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Response length MUST NOT be used for arbitration.

#### Forbidden pattern

```python
winner = max(claude_fix, openai_fix, key=len)
```

---

## Validation Rules

### Entry Point Enforcement

For every entry point that processes an agent action:

1. CTX-ID validation MUST be called FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a `TrustFlowEvent`.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

---

### TrustFlow Validation

For each `TrustFlowEvent`:

- `event_id` MUST be globally unique.
- `event_id` MUST be generated via CSPRNG.
- `event_id` MUST NOT be sequential.
- `session_id` MUST be present.
- `ctx_id` MUST be present.
- `ts` MUST be a UTC Unix timestamp with millisecond precision.
- `event_type` MUST be present.
- `payload_hash` MUST be present.
- `payload_hash` MUST equal SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.

---

### CTX-ID Validation

- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Expired CTX-ID MUST be rejected.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- CTX-ID is immutable after issuance.
- Rotation MUST create a new token.
- Rotation MUST invalidate the old token immediately.

---

### VTZ Validation

- Every agent session MUST be bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

### Consensus Engine Validation

- `language` MUST be present on every consensus engine call.
- `language` MUST be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

---

### Security Validation

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log. Never retry to bypass.

---

### Python Backend Requirements

- Python version: `3.12`
- Type annotations required on every function.
- `async/await` throughout the backend.
- No blocking calls on the event loop.
- Dataclasses required for all structured data.
- Tests use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be `≥ 85%` on all new modules.
- `pyyaml` must be in `requirements.txt`.

---

## Wire Format Examples

## Valid payloads

### Valid `ConsensusRunRequest`

```json
{
  "task": "Implement: Add user auth",
  "context": "Build a backend endpoint with tests.",
  "language": "python"
}
```

### Valid `ConsensusRunResult`

```json
{
  "final_code": "from dataclasses import dataclass\n"
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
  "event_id": "8f5f3d7c1a8b4e5db6f7a123456789ab",
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "ts": 1735689600123,
  "event_type": "agent_action_blocked",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3b314e838e65d5c31a7cdb9b1f0c0"
}
```

### Valid action processing sequence

```json
{
  "ctx_id": "ctx_456",
  "vtz_check": {
    "authorized": false
  },
  "decision": {
    "verdict": "block"
  },
  "trustflow_event": {
    "event_id": "8f5f3d7c1a8b4e5db6f7a123456789ab",
    "session_id": "sess_123",
    "ctx_id": "ctx_456",
    "ts": 1735689600123,
    "event_type": "agent_action_blocked",
    "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3b314e838e65d5c31a7cdb9b1f0c0"
  }
}
```

## Invalid payloads

### Invalid `ConsensusRunRequest` - missing `language`

```json
{
  "task": "Implement: Add user auth",
  "context": "Build a backend endpoint with tests."
}
```

Reason:
- `language` MUST always be passed.

---

### Invalid `ConsensusRunRequest` - unsupported `language`

```json
{
  "task": "Implement: Add user auth",
  "context": "Build a backend endpoint with tests.",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

---

### Invalid `VTZEnforcementDecision` - wrong denial verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### Invalid `TrustFlowEvent` - missing required fields

```json
{
  "event_id": "8f5f3d7c1a8b4e5db6f7a123456789ab",
  "session_id": "sess_123",
  "ctx_id": "ctx_456"
}
```

Reason:
- `ts`, `event_type`, and `payload_hash` are required.

---

### Invalid TrustFlow emission mode

```json
{
  "emission_mode": "async_buffered"
}
```

Reason:
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.

---

### Invalid missing CTX-ID handling

```json
{
  "ctx_id": null,
  "identity_inferred_from_context": true
}
```

Reason:
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity must never be inferred from context.

---

## Integration Points

### Consensus Engine

Invocation contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

#### Required behavior

- Always pass `language`.
- Use exact supported language values:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

---

### Fix Loop Integration

Required strategy API:

```python
_choose_strategy(failure_type, attempt, records)
```

Required arbitration API:

```python
_score_fix()
```

#### Forbidden implementation

```python
winner = max(claude_fix, openai_fix, key=len)
```

---

### Filesystem Writes

Before any write to disk:

```python
path_security.validate_write_path()
```

#### Required behavior

- Validation MUST occur before any write.

---

### Prompt Construction

#### Required behavior

- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt.
- External document context MUST NEVER go in the SYSTEM prompt.

---

### LLM Security Refusal Handling

When the LLM returns:

- `SECURITY_REFUSAL`

#### Required behavior

- stop
- gate
- log
- never retry to bypass

---

### Enforcement Path

Required enforcement order:

1. CTX-ID validation
2. VTZ policy check
3. Decision record on denial with `verdict=block`
4. Synchronous TrustFlow emission
5. Surface any TrustFlow emission failure

---

### Backend Conformance

ForgeAgent backend implementations MUST satisfy:

- Python `3.12`
- full type annotations
- `async/await` throughout backend
- no blocking calls on event loop
- dataclasses for all structured data
- `pytest`
- `ruff`
- `mypy`
- coverage `≥ 85%` on new modules
- `pyyaml` present in `requirements.txt`