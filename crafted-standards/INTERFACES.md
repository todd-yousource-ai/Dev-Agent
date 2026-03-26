# Interface Contracts - CraftedApp

## Scope

This document defines the wire-format and API contract requirements for the CraftedApp subsystem based on the provided TRD interface standards.

## Data Structures

### TrustFlowEvent

Required for every action outcome in the enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | Yes | Session identifier for the agent session. |
| `ctx_id` | `string` | Yes | CTX-ID token identifier associated with the session/action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type for the emitted TrustFlow record. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Additional contract requirements
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission MUST NOT be silently skipped.
- TrustFlow emission failure MUST be logged and surfaced.

---

### VTZEnforcementDecision

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | MUST be `block` when VTZ policy denial occurs. |

#### Additional contract requirements
- A VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### CTX-ID Token

Represents the issued trust context identifier.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. Missing CTX-ID MUST be treated as UNTRUSTED. |
| `session_id` | `string` | Yes | Each agent session is bound to exactly one VTZ at CTX-ID issuance. |
| `vtz` | `string` | Yes | EXACTLY ONE VTZ is bound at CTX-ID issuance. |
| `expires_at` | `number` | Yes | Expired CTX-ID MUST be rejected. Clock skew tolerance is deployment-defined. |
| `public_key_id` | `string` | Yes | Validation MUST be against TrustLock public key. |
| `issued_at` | `number` | No | UTC Unix timestamp, if present. |
| `rotated_from` | `string` | No | Present only for rotated tokens. Rotation creates a new token and invalidates the old token immediately. |

#### Additional contract requirements
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is allowed after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NOT be inferred from surrounding context.
- Software-only validation is rejected.
- Validation MUST use TrustLock public key.

---

### AgentActionPayload

Serialized action payload whose hash is included in `TrustFlowEvent.payload_hash`.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | Yes | Must match active session. |
| `ctx_id` | `string` | Yes | MUST be validated first at entry points processing agent actions. |
| `action` | `string` | Yes | Agent action identifier. |
| `vtz` | `string` | Yes | Must correspond to session-bound VTZ. |
| `payload` | `object` | Yes | Serialized before SHA-256 hashing. |

#### Additional contract requirements
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is allowed before validation succeeds.
- Every action MUST be checked against VTZ policy BEFORE execution.

---

### ConsensusRunRequest

Required when using the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Example format: `"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string passed to consensus. |
| `language` | `string` | Yes | MUST be one of `"python" \| "swift" \| "go" \| "typescript" \| "rust"`. |

#### Additional contract requirements
- `language` MUST always be passed.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Returned by the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Final generated code output. |

---

## Enums and Constants

### Verdict

Allowed values for VTZ enforcement decisions.

| Value |
|---|
| `block` |

---

### CTX-ID Trust State

Named trust state required by contract.

| Value | Meaning |
|---|---|
| `UNTRUSTED` | Used when CTX-ID is missing. Identity must not be inferred. |

---

### Supported Consensus Languages

Exact allowed values:

| Value |
|---|
| `"python"` |
| `"swift"` |
| `"go"` |
| `"typescript"` |
| `"rust"` |

---

### Consensus System Selection Constants

Exact values referenced by contract:

| Constant | Applies when |
|---|---|
| `SWIFT_GENERATION_SYSTEM` | `language="swift"` |
| `SWIFT_UI_ADDENDUM` | Optional injection when UI keywords are detected with `language="swift"` |
| `GENERATION_SYSTEM` | `language="python"` |

---

### Forbidden Implementations

These are non-conformant behaviors.

#### Forbidden fix arbitration
```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

#### Required replacement behavior
- Fix arbitration uses `_score_fix()`
- Fix loop strategy uses `_choose_strategy(failure_type, attempt, records)`

#### Forbidden Swift behaviors
```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

#### Required Swift/backend credential boundary
- Only Swift reads Keychain.
- Swift reads Keychain only to deliver via XPC.
- Python reads nothing from Keychain.

---

## Validation Rules

## Entry Point Enforcement

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur FIRST.
2. If CTX-ID validation fails, the request MUST be rejected immediately.
3. No partial processing is permitted before CTX-ID validation succeeds.
4. VTZ policy MUST be checked BEFORE execution.
5. If VTZ denies the action:
   - a `VTZEnforcementDecision` MUST be produced
   - `verdict` MUST equal `block`
6. Every action outcome MUST emit a `TrustFlowEvent`.
7. If TrustFlow emission fails:
   - the failure MUST NOT silently continue
   - the failure MUST be logged
   - the failure MUST be surfaced
   - the audit event level is WARN

---

## TrustFlowEvent Validation

A `TrustFlowEvent` is valid only if all of the following hold:

- `event_id` is present
- `event_id` is globally unique
- `event_id` is generated using CSPRNG
- `event_id` is not sequential
- `session_id` is present
- `ctx_id` is present
- `ts` is present
- `ts` is a UTC Unix timestamp with millisecond precision
- `event_type` is present
- `payload_hash` is present
- `payload_hash` equals the SHA-256 of the serialized action payload

Emission constraints:

- MUST be synchronous in the enforcement path
- MUST NOT use async buffering

---

## CTX-ID Validation

A CTX-ID is valid only if all of the following hold:

- token is present; otherwise trust state is `UNTRUSTED`
- token has not expired
- token validates against TrustLock public key
- validation is not software-only
- token fields have not been modified after issuance

Rotation rules:

- rotation MUST create a new token
- old token MUST be invalidated immediately

Session binding rules:

- every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance
- cross-VTZ tool calls require explicit policy authorization
- implicit authorization is denied
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session

---

## Security and Runtime Constraints

### Python requirements
- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data

### Testing requirements
- Test framework: `pytest`
- Tests live in `tests/`
- Tests mirror `src/` structure
- Coverage for all new modules: `>= 85%`

### Static analysis requirements
- Linting: `ruff`
- Type checking: `mypy`
- Both MUST pass clean

### Dependency requirement
- `pyyaml` MUST be in `requirements.txt`

### Security requirements
- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Never use `shell=True` in subprocess calls
- Never call `eval()` or `exec()` on generated or external content
- Never log HTTP response bodies
- Log HTTP status codes and error types only
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt
- Context from external documents goes in the USER prompt, never the SYSTEM prompt
- On `SECURITY_REFUSAL` output from the LLM: stop, gate, log; never retry to bypass

---

## Wire Format Examples

## Valid Payloads

### Valid AgentActionPayload
```json
{
  "session_id": "sess_01HZX8M9R5A7",
  "ctx_id": "ctx_01HZX8MB3N2K",
  "action": "tool.invoke",
  "vtz": "vtz_primary",
  "payload": {
    "tool": "search",
    "query": "status"
  }
}
```

### Valid TrustFlowEvent
```json
{
  "event_id": "evt_8f3b1c5a9d7e4f2a",
  "session_id": "sess_01HZX8M9R5A7",
  "ctx_id": "ctx_01HZX8MB3N2K",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "3f0c0b5b3d4e2a1f6c7d8e9a0b1c2d3e4f5061728394a5b6c7d8e9f0a1b2c3d4"
}
```

### Valid VTZEnforcementDecision
```json
{
  "verdict": "block"
}
```

### Valid ConsensusRunRequest
```json
{
  "task": "Implement: ExampleSpec",
  "context": "component requirements and constraints",
  "language": "python"
}
```

### Valid ConsensusRunResult
```json
{
  "final_code": "print('ok')"
}
```

---

## Invalid Payloads

### Invalid TrustFlowEvent: sequential event_id
```json
{
  "event_id": "1001",
  "session_id": "sess_01HZX8M9R5A7",
  "ctx_id": "ctx_01HZX8MB3N2K",
  "ts": 1735689600,
  "event_type": "action.allow",
  "payload_hash": "abc"
}
```

Reasons:
- `event_id` is sequential
- `ts` is not millisecond precision
- `payload_hash` is not a valid SHA-256 value

### Invalid VTZEnforcementDecision: wrong verdict
```json
{
  "verdict": "allow"
}
```

Reason:
- VTZ denial contract requires `verdict=block`

### Invalid ConsensusRunRequest: missing language
```json
{
  "task": "Implement: ExampleSpec",
  "context": "component requirements and constraints"
}
```

Reason:
- `language` MUST always be passed

### Invalid CTX-ID usage: missing ctx_id
```json
{
  "session_id": "sess_01HZX8M9R5A7",
  "action": "tool.invoke",
  "vtz": "vtz_primary",
  "payload": {}
}
```

Reasons:
- missing CTX-ID MUST be treated as `UNTRUSTED`
- entry point MUST reject before partial processing

---

## Integration Points

## Consensus Engine

Required usage:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

Contract notes:
- `language` is mandatory
- `result.final_code` is the output field
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` and optionally `SWIFT_UI_ADDENDUM`
- `language="python"` selects `GENERATION_SYSTEM`

---

## TrustLock / CTX-ID Validation

Integration requirements:
- CTX-ID MUST be validated against TrustLock public key
- Software-only validation is rejected

---

## TrustFlow Audit Path

Integration requirements:
- every action outcome emits a `TrustFlowEvent`
- emission is synchronous in enforcement path
- failure is WARN-level and surfaced

---

## Path Security

Before any disk write:
- call `path_security.validate_write_path()`

---

## LLM Prompt Construction

Integration requirements:
- external document chunks MUST pass injection scanning before use
- external document context goes into USER prompt only
- never place external document context into SYSTEM prompt
- on `SECURITY_REFUSAL`, stop, gate, log; do not retry

---

## Non-Conformance

A Crafted component is non-conformant if it violates any of the contracts in this document, including but not limited to:

- missing CTX-ID-first validation
- partial processing before CTX-ID validation
- missing VTZ pre-execution check
- VTZ denial without `VTZEnforcementDecision(verdict="block")`
- missing TrustFlow emission
- silent TrustFlow emission failure
- async-buffered TrustFlow emission
- non-unique or sequential `event_id`
- non-SHA-256 `payload_hash`
- mutable CTX-ID fields after issuance
- software-only CTX-ID validation
- omitted `language` in consensus engine calls
- use of forbidden length-based fix arbitration
- Swift force unwraps in conformant implementation
- backend Keychain reads
- violation of the listed security constraints