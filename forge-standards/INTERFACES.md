# Interface Contracts - ForgeAgent

## Data Structures

This document defines the wire-format and API contract requirements for the ForgeAgent subsystem based on the provided TRD interface standards.

Where source material does not define a field structure, this document does not invent one.

---

### Consensus Run Request

Used when invoking the consensus engine for code generation.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | string | yes | Free-form task description. Example source usage: `"Implement: {spec.title}"` |
| `context` | string | yes | Context string passed to the consensus engine |
| `language` | string | yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Required call pattern

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

#### Response contract

The returned object from `_consensus.run(...)` must expose:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | string | yes | Generated code output |

---

### TrustFlow Event

Every TrustFlow event MUST include the following fields.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | Must be globally unique; generated via CSPRNG, not sequential |
| `session_id` | string | yes | Session identifier |
| `ctx_id` | string | yes | CTX-ID associated with the action |
| `ts` | number | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Event type identifier |
| `payload_hash` | string | yes | Must be SHA-256 of the serialized action payload |

#### Behavioral constraints

- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failure MUST NOT be silently skipped.

---

### VTZEnforcementDecision Record

A VTZ denial MUST produce a `VTZEnforcementDecision` record with the following required field contract known from source.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | For denial, value must be exactly `block` |

#### Notes

The source material requires production of a `VTZEnforcementDecision` record with `verdict=block` on VTZ policy denial. No additional fields are defined in the provided contract text.

---

### CTX-ID Token

The provided standards define lifecycle and validation constraints for CTX-ID tokens, but do not define their internal serialized field layout.

#### Type
Opaque token / implementation-defined serialized value

#### Known contract requirements

- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID must be rejected.
- Clock skew tolerance is deployment-defined.
- Validation must be performed against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from surrounding context when CTX-ID is missing.

---

### Agent Action Payload

The standards refer to “serialized action payload” for `payload_hash` calculation, but do not define a canonical schema in the provided excerpts.

#### Type
Implementation-defined object

#### Known contract requirements

- Every entry point that processes an agent action must validate CTX-ID first.
- Every action must be checked against VTZ policy before execution.
- Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.
- `payload_hash` must be SHA-256 of the serialized action payload.

---

## Enums and Constants

### Supported Consensus Languages

Exact allowed values for `language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

---

### Enforcement Verdict Values

Known exact value from provided source:

- `block`

---

### Action Outcome Values

Known exact outcome values that must emit a TrustFlow event:

- `allow`
- `restrict`
- `block`

---

### Special Security Sentinel

Known exact output token:

- `SECURITY_REFUSAL`

When this output is observed from the LLM:

- stop
- gate
- log
- never retry to bypass

---

### System Selection Constants

The source specifies these exact constant names for generation routing:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

#### Selection rules

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### Fix Strategy / Arbitration API Names

These exact function names are part of the interface/behavior contract:

- `_choose_strategy(failure_type, attempt, records)`
- `_score_fix()`

#### Forbidden pattern

Length-based arbitration is forbidden:

```python
winner = max(claude_fix, openai_fix, key=len)
```

Use `_score_fix()` instead.

---

### Security / Implementation Constants and Exact Values

#### Logging restrictions

- Never log HTTP response bodies.
- Log status codes and error types only.

#### Subprocess restriction

- Never use `shell=True` in subprocess calls.

#### Dynamic execution restriction

- Never call `eval()`.
- Never call `exec()`.

#### Path validation API

All file paths written to disk must pass:

- `path_security.validate_write_path()`

before any write.

#### Injection scanning contract

- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

---

## Validation Rules

## 1. Entry Point Enforcement Order

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur first.
2. On CTX-ID validation failure, processing MUST stop immediately.
3. No partial processing is permitted after CTX-ID validation failure.
4. VTZ policy evaluation MUST occur before execution.
5. VTZ denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every resulting outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST be logged and surfaced.
8. TrustFlow emission failure MUST NOT silently continue.

---

## 2. TrustFlow Event Validation

A TrustFlow event is valid only if all of the following hold:

- `event_id` is present.
- `session_id` is present.
- `ctx_id` is present.
- `ts` is present.
- `event_type` is present.
- `payload_hash` is present.
- `event_id` is globally unique.
- `event_id` is generated using CSPRNG.
- `event_id` is not sequential.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `payload_hash` is the SHA-256 hash of the serialized action payload.
- Emission is synchronous in the enforcement path.
- Async buffering is not used.

---

## 3. CTX-ID Validation Rules

A CTX-ID is valid only if all of the following hold:

- The token is present.
- The token is not expired.
- The token has not been invalidated by rotation.
- Validation is performed against TrustLock public key.
- Validation is not software-only.

Additional rules:

- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred when CTX-ID is missing.
- CTX-ID fields must not be modified after issuance.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 4. VTZ Enforcement Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.

---

## 5. Consensus Engine Request Validation

A consensus run request is valid only if:

- `task` is present and is a string.
- `context` is present and is a string.
- `language` is present and exactly matches one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

Behavioral validation:

- Always pass `language`.
- Result consumers must read generated code from `result.final_code`.

---

## 6. Secure Code Generation Rules

These are hard constraints for ForgeAgent implementations:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- All write paths must pass `path_security.validate_write_path()` before write.
- All loaded document chunks must pass injection scanning before inclusion in prompts.
- External document context must go in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`, stop, gate, and log; do not retry to bypass.

---

## 7. Python Backend Conformance Rules

For Python implementations in ForgeAgent:

- Python version: `3.12`
- Type annotations are required on every function.
- Backend code must use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses must be used for all structured data.
- Tests must use `pytest`.
- Tests must live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be `>= 85%` on all new modules.
- `pyyaml` must be in `requirements.txt`.

---

## Wire Format Examples

## Valid Payloads

### Valid consensus run request

```json
{
  "task": "Implement: Add agent execution guard",
  "context": "Security-sensitive backend path",
  "language": "python"
}
```

### Valid TrustFlow event

```json
{
  "event_id": "6f4c3a2d-4b4f-4d5e-91aa-c2d0d91d8c0e",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1712345678123,
  "event_type": "agent_action_blocked",
  "payload_hash": "7b1c4a1d5e6f7890abc123def4567890abc123def4567890abc123def4567890"
}
```

### Valid VTZ enforcement decision

```json
{
  "verdict": "block"
}
```

---

## Invalid Payloads

### Invalid consensus run request: missing language

```json
{
  "task": "Implement: Add agent execution guard",
  "context": "Security-sensitive backend path"
}
```

Reason:
- `language` is required.

---

### Invalid consensus run request: unsupported language

```json
{
  "task": "Implement: Add agent execution guard",
  "context": "Security-sensitive backend path",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

---

### Invalid TrustFlow event: missing required fields

```json
{
  "event_id": "123",
  "event_type": "agent_action_allowed"
}
```

Reason:
- Missing `session_id`
- Missing `ctx_id`
- Missing `ts`
- Missing `payload_hash`

---

### Invalid VTZ enforcement decision: wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- Source contract requires `verdict=block` for VTZ policy denial.

---

### Invalid processing flow: partial execution before CTX-ID validation

```json
{
  "ctx_id": null,
  "action_executed": true
}
```

Reason:
- CTX-ID validation must occur first.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- No partial processing is allowed after CTX-ID validation failure.

---

## Integration Points

## Consensus Engine

ForgeAgent integrates with a consensus engine through:

- `await self._consensus.run(task=..., context=..., language=...)`

Required integration behavior:

- `language` must always be passed.
- Generated code must be read from `result.final_code`.
- Swift routing uses `SWIFT_GENERATION_SYSTEM` and optional `SWIFT_UI_ADDENDUM`.
- Python routing uses `GENERATION_SYSTEM`.

---

## CAL Enforcement Path

Every agent-action entry point must integrate with CAL enforcement in this order:

1. CTX-ID validation
2. VTZ policy evaluation
3. Action execution decision
4. TrustFlow synchronous emission

Required side effects:

- VTZ denial produces `VTZEnforcementDecision` with `verdict=block`
- Every outcome emits a TrustFlow event
- Emission failure is logged and surfaced

---

## TrustLock

CTX-ID validation must integrate with:

- TrustLock public key validation

Prohibited integration behavior:

- Software-only validation
- Inferring identity without CTX-ID

---

## Filesystem Writes

Before any file write, ForgeAgent must call:

- `path_security.validate_write_path()`

No write may occur before this validation succeeds.

---

## Prompt Construction / External Content Handling

When external documents are included in LLM context:

- Every loaded document chunk must pass injection scanning.
- External document context must be placed in the USER prompt.
- External document context must never be placed in the SYSTEM prompt.

---

## Test and Quality Tooling

ForgeAgent Python implementations must integrate with:

- `pytest`
- `ruff`
- `mypy`

Test execution command from source guidance:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## Non-Conformance Conditions

A ForgeAgent implementation is non-conformant if any of the following occur:

- Agent action entry point does not validate CTX-ID first
- CTX-ID validation failure allows partial processing
- VTZ policy is not checked before execution
- VTZ denial does not produce `VTZEnforcementDecision` with `verdict=block`
- TrustFlow event is not emitted for every outcome
- TrustFlow emission failure is silently ignored
- TrustFlow event omits any required field
- `event_id` is sequential or not globally unique
- `payload_hash` is not SHA-256 of serialized action payload
- Consensus engine call omits `language`
- Consensus engine consumer does not use `result.final_code`
- Length-based fix arbitration is used instead of `_score_fix()`
- File writes occur without `path_security.validate_write_path()`
- External content is included without injection scanning
- External content is placed in the SYSTEM prompt
- `SECURITY_REFUSAL` is retried to bypass
- Python backend violates async/dataclass/type-annotation/testing requirements