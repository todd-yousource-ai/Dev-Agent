# Interface Contracts - ForgeAgent

This document defines the wire-format and API contract reference for the ForgeAgent subsystem.

## Data Structures

### ConsensusRunRequest

Request contract for invoking the consensus engine for implementation/generation tasks.

**Type:** object

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | string | yes | Free-form task description. |
| `context` | string | yes | Context string supplied to the consensus engine. External document context, if any, must be placed in the USER prompt, never the SYSTEM prompt. All loaded document chunks must pass injection scanning before inclusion. |
| `language` | string | yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. |

**Behavioral contract**
- Calls MUST always pass `language`.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result contract returned by the consensus engine.

**Type:** object

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | string | yes | Generated code output. |

---

### VTZEnforcementDecision

Record produced when VTZ policy is evaluated.

**Type:** object

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | For denial, MUST be exactly `block`. Action outcomes may be `allow`, `restrict`, or `block` per enforcement contract. |

**Behavioral contract**
- Every action MUST be checked against VTZ policy before execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Audit/event record emitted for every action outcome.

**Type:** object

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | Must be globally unique. Must be generated using CSPRNG. Must not be sequential. |
| `session_id` | string | yes | Session identifier for the agent session. |
| `ctx_id` | string | yes | CTX-ID associated with the session/action. |
| `ts` | integer or number | yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | string | yes | Event type identifier. |
| `payload_hash` | string | yes | Must be SHA-256 of the serialized action payload. |

**Behavioral contract**
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST NOT silently continue.
- Failed emission is a WARN-level audit event and must be logged and surfaced.

---

### CTX-ID Token

Opaque identity/binding token used by Forge enforcement.

**Type:** token/string at wire level

**Behavioral contract**
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID must be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from surrounding context when CTX-ID is missing.

---

### AgentActionPayload

Serialized action payload referenced by enforcement and audit contracts.

**Type:** object

**Fields**
- Not fully specified in the provided TRD excerpts.

**Behavioral contract**
- Every entry point that processes an agent action MUST call CTX-ID validation first.
- CTX-ID validation failure MUST result in immediate rejection with no partial processing.
- Every action payload written to disk must have all file paths validated with `path_security.validate_write_path()` before any write.
- `payload_hash` in `TrustFlowEvent` MUST be the SHA-256 hash of the serialized action payload.

---

### SecurityRefusalSignal

LLM output sentinel indicating a security refusal.

**Type:** string sentinel

| Value | Type | Required | Constraints |
|---|---|---:|---|
| `SECURITY_REFUSAL` | string | yes | Exact literal value. |

**Behavioral contract**
- When `SECURITY_REFUSAL` is returned from the LLM: stop, gate, log.
- The system must never retry to bypass this outcome.

---

## Enums and Constants

### Language

**Type:** string enum

Allowed values:
- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

---

### EnforcementVerdict

**Type:** string enum

Allowed values:
- `allow`
- `restrict`
- `block`

Constraint:
- VTZ denial MUST produce `verdict=block`.

---

### Trust State

**Type:** string constant set

Known required value:
- `UNTRUSTED`

Constraint:
- Missing CTX-ID MUST be treated as `UNTRUSTED`.

---

### Security Refusal Constant

**Type:** string constant

Exact value:
- `SECURITY_REFUSAL`

---

### System Selector Constants

These identifiers are selected internally based on `language`.

**Type:** string constant identifiers

Values:
- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

Selection rules:
- `language="swift"` => `SWIFT_GENERATION_SYSTEM` and optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` => `GENERATION_SYSTEM`

---

## Validation Rules

### Entry-Point Enforcement

1. Every entry point that processes an agent action MUST validate `ctx_id` first.
2. If CTX-ID validation fails, the request/action MUST be rejected immediately.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy before execution.

### CTX-ID Validation

1. CTX-ID is required for trusted processing.
2. Missing CTX-ID MUST be treated as `UNTRUSTED`.
3. Expired CTX-ID MUST be rejected.
4. CTX-ID MUST be validated against TrustLock public key.
5. Software-only validation is rejected.
6. CTX-ID fields MUST NOT be modified after issuance.
7. Rotation MUST create a new token and immediately invalidate the old token.

### VTZ Enforcement

1. Every agent session is bound to exactly one VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit cross-VTZ authorization is denied.
4. VTZ boundaries are structural and cannot be bypassed by application code.
5. VTZ policy changes take effect at the next CTX-ID issuance, not mid-session.
6. VTZ denial MUST yield a `VTZEnforcementDecision` with `verdict=block`.

### TrustFlow Emission

1. Every action outcome must emit a `TrustFlowEvent`.
2. Required event fields:
   - `event_id`
   - `session_id`
   - `ctx_id`
   - `ts`
   - `event_type`
   - `payload_hash`
3. `event_id` MUST be globally unique and CSPRNG-generated.
4. `ts` MUST be a UTC Unix timestamp with millisecond precision.
5. `payload_hash` MUST be SHA-256 of the serialized action payload.
6. Emission MUST be synchronous in the enforcement path.
7. Async buffering is not permitted.
8. Emission failure MUST be logged and surfaced.
9. Emission failure MUST NOT silently continue.
10. Emission failure is classified as WARN-level audit event.

### Consensus Engine Invocation

1. `language` MUST always be present.
2. `language` MUST be one of:
   - `"python"`
   - `"swift"`
   - `"go"`
   - `"typescript"`
   - `"rust"`
3. ForgeAgent implementations MUST use `result.final_code` as the generated code output field from consensus results.
4. Fix-loop strategy selection MUST use `_choose_strategy(failure_type, attempt, records)`.
5. Fix arbitration MUST use `_score_fix()`.
6. Length-based fix arbitration is forbidden.

### Security Constraints

1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Only status codes and error types may be logged for HTTP failures.
6. All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
7. All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
8. Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
9. On `SECURITY_REFUSAL`: stop, gate, log; never retry to bypass.

### Python Backend Constraints

1. Python version requirement: `Python 3.12`.
2. Type annotations are required on every function.
3. Backend code must use `async/await` throughout.
4. No blocking calls on the event loop.
5. Dataclasses are required for all structured data.
6. Tests must use `pytest`.
7. Tests live in `tests/` and mirror `src/` structure.
8. `ruff` must pass clean.
9. `mypy` must pass clean.
10. Test coverage must be `>= 85%` on all new modules.
11. `pyyaml` must be present in `requirements.txt`.

### Forbidden Patterns

The following are explicitly non-conformant:

#### Length-based fix arbitration
```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- Forbidden. Must use `_score_fix()`.

#### Swift force unwrap
```swift
let value = optional!
```

Reason:
- Forbidden.

#### LLM API call from Swift
```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Reason:
- Forbidden.

#### Keychain read for backend
```swift
let token = KeychainKit.read("github_token")
```

Reason:
- Forbidden for backend. Only Swift may read Keychain, and only to deliver via XPC.

---

## Wire Format Examples

## Valid payloads

### Valid ConsensusRunRequest
```json
{
  "task": "Implement: Add file validator",
  "context": "Validate all write paths before disk operations.",
  "language": "python"
}
```

### Valid ConsensusRunResult
```json
{
  "final_code": "from dataclasses import dataclass\n..."
}
```

### Valid VTZEnforcementDecision for denial
```json
{
  "verdict": "block"
}
```

### Valid TrustFlowEvent
```json
{
  "event_id": "8f2d3a5c-4f1e-4b3d-9f3b-2df1c8f0a9ab",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600123,
  "event_type": "agent_action.block",
  "payload_hash": "4f6b8c7d9e0a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef012345"
}
```

### Valid missing-CTX handling state
```json
{
  "trust_state": "UNTRUSTED"
}
```

### Valid security refusal signal
```json
{
  "result": "SECURITY_REFUSAL"
}
```

## Invalid payloads

### Invalid ConsensusRunRequest: missing language
```json
{
  "task": "Implement: Add file validator",
  "context": "Validate all write paths before disk operations."
}
```

Reason:
- `language` is required.

### Invalid ConsensusRunRequest: unsupported language
```json
{
  "task": "Implement: Add file validator",
  "context": "Validate all write paths before disk operations.",
  "language": "java"
}
```

Reason:
- `language` must be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid VTZEnforcementDecision for denial
```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ denial must use exact value `block`.

### Invalid TrustFlowEvent: missing required field
```json
{
  "event_id": "8f2d3a5c-4f1e-4b3d-9f3b-2df1c8f0a9ab",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600123,
  "event_type": "agent_action.allow"
}
```

Reason:
- `payload_hash` is required.

### Invalid TrustFlowEvent: noncompliant event_id source
```json
{
  "event_id": "10042",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600123,
  "event_type": "agent_action.allow",
  "payload_hash": "4f6b8c7d9e0a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef012345"
}
```

Reason:
- `event_id` must be globally unique and CSPRNG-generated, not sequential.

### Invalid missing-CTX handling
```json
{
  "trust_state": "trusted"
}
```

Reason:
- Missing CTX-ID must be treated as exact value `UNTRUSTED`.

---

## Integration Points

### Consensus Engine

ForgeAgent MUST invoke the consensus engine with:

- `task`
- `context`
- `language`

Required usage contract:
```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Integration rules:
- `language` is mandatory.
- `code` must be taken from `result.final_code`.

### CTX-ID Validation Layer

ForgeAgent entry points that process agent actions MUST integrate with CTX-ID validation before any other processing.

Required ordering:
1. CTX-ID validation
2. VTZ policy check
3. Action execution
4. TrustFlow emission for outcome

### VTZ Policy Enforcement

ForgeAgent sessions MUST be bound to exactly one VTZ at CTX-ID issuance.

Integration requirements:
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- Policy changes do not alter active session behavior mid-session; they apply at next CTX-ID issuance.

### TrustFlow Audit Pipeline

ForgeAgent MUST synchronously emit a `TrustFlowEvent` in the enforcement path for every action outcome.

Required event fields:
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Failure handling:
- Do not silently skip.
- Log at WARN audit level.
- Surface the failure.

### Path Security

All disk write operations in ForgeAgent MUST validate target paths through:

- `path_security.validate_write_path()`

This validation must occur before any write.

### Prompt Construction / LLM Security

ForgeAgent integrations that assemble prompts MUST enforce:

- External document context only in USER prompt.
- Never place external document context in SYSTEM prompt.
- Injection scan all loaded document chunks before prompt inclusion.
- Stop/gate/log on `SECURITY_REFUSAL`.

### Swift / Backend Boundary

Integration constraints:
- Swift must not perform direct LLM API calls.
- Backend must not read Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

### Python Toolchain

ForgeAgent Python backend integrations must conform to:
- Python `3.12`
- `pytest`
- `ruff`
- `mypy`
- `pyyaml` in `requirements.txt`