# Interface Contracts - CraftedApp

## Data Structures

This document defines the required wire-format and API contracts for the CraftedApp subsystem based on the provided TRD interface requirements.

---

### TrustFlowEvent

Required for every action outcome emitted in the enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | yes | Session identifier for the agent session. |
| `ctx_id` | `string` | yes | CTX-ID token identifier associated with the action. |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | yes | Event type for the emitted TrustFlow event. |
| `payload_hash` | `string` | yes | MUST be SHA-256 of the serialized action payload. |

#### Additional contract requirements
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be surfaced.
- Failed emission is a WARN-level audit event.
- Failed emission MUST NOT silently continue.

---

### VTZEnforcementDecision

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | MUST be `block` for VTZ policy denial. |

#### Additional contract requirements
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### CTX-ID Token

Represents the identity and trust context bound to an agent session.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | CTX-ID token value. Immutable once issued. |

#### Additional contract requirements
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from context if CTX-ID is missing.

---

### Agent Action

A logical action processed by a CraftedApp entry point.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | yes | Must identify the current agent session. |
| `ctx_id` | `string` | yes | MUST be validated FIRST before any partial processing. |
| `payload` | `object` | yes | Serialized action payload used to compute `payload_hash`. |

#### Additional contract requirements
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted before CTX-ID validation succeeds.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### Consensus Engine Invocation

Required invocation contract for consensus-backed implementation tasks.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Example format: `Implement: {spec.title}` |
| `context` | `string` | yes | Context string provided to the consensus engine. |
| `language` | `string` | yes | MUST be one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Result Structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Final generated code output from consensus execution. |

#### Required usage
```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

#### Behavioral requirements
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

#### Prohibited implementation behavior
- Fix loop strategy MUST use `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration is forbidden.

---

## Enums and Constants

### Action Outcome

Allowed values for action outcome emission:

- `allow`
- `restrict`
- `block`

Every action outcome with one of these values MUST emit a TrustFlow event.

---

### VTZ Enforcement Verdict

Allowed/required known value from the provided contract:

- `block`

For VTZ policy denial, `verdict` MUST be exactly `block`.

---

### CTX-ID Trust State

Known required value:

- `UNTRUSTED`

If `ctx_id` is missing, the request/session/action MUST be treated as `UNTRUSTED`.

---

### Consensus Language

Exact allowed values:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

---

### System Selector Constants

Exact referenced constant names:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

---

### Required Python Runtime/Tooling Constants

These are implementation constraints for Python-backed CraftedApp components:

- Python version: `3.12`
- Test runner: `pytest`
- Linter: `ruff`
- Type checker: `mypy`
- Required dependency: `pyyaml`

---

## Validation Rules

## 1. CAL Enforcement

1. Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is allowed before CTX-ID validation completes successfully.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

## 2. TrustFlow Event Validation

A `TrustFlowEvent` is valid only if all of the following hold:

- `event_id` is present.
- `event_id` is globally unique.
- `event_id` is generated using CSPRNG.
- `event_id` is not sequential.
- `session_id` is present.
- `ctx_id` is present.
- `ts` is present.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `event_type` is present.
- `payload_hash` is present.
- `payload_hash` equals SHA-256 of the serialized action payload.

Operational rules:

- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.

## 3. CTX-ID Validation

A CTX-ID is valid only if all of the following hold:

- It is present unless the caller is explicitly treated as `UNTRUSTED`.
- It has not expired.
- It validates against the TrustLock public key.
- Validation is not software-only.
- It has not been invalidated by rotation.

Additional rules:

- CTX-ID tokens are immutable once issued.
- No field modification after issuance is permitted.
- Rotation creates a new token and invalidates the old one immediately.
- Expired CTX-ID MUST be rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.

## 4. VTZ Enforcement Validation

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

## 5. Security Rules

The following are mandatory interface-level security constraints:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` output is returned from the LLM: stop, gate, log. Never retry to bypass.

## 6. Python Implementation Rules

For Python implementations in CraftedApp:

- Python `3.12` is required.
- Type annotations are required on every function.
- `async/await` must be used throughout the backend.
- No blocking calls on the event loop.
- Dataclasses are required for all structured data.
- Tests must use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be `>= 85%` on all new modules.
- `pyyaml` must be present in `requirements.txt`.

## 7. Forbidden Patterns

The following are explicitly non-conformant:

### Length-based fix arbitration
```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

### Swift force unwrap
```swift
let value = optional!
```

### LLM API call from Swift
```swift
let client = AnthropicClient(apiKey: keychainValue)
```

### Keychain read for backend
```swift
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
```

Additional rule:
- Only Swift reads Keychain, only to deliver via XPC.

---

## Wire Format Examples

## Valid Payloads

### Valid TrustFlowEvent
```json
{
  "event_id": "b9d7b4d8-8b8e-4b33-9e8d-5d0d5e8c1a21",
  "session_id": "sess_12345",
  "ctx_id": "ctx_abc123",
  "ts": 1712345678123,
  "event_type": "action.allow",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

### Valid VTZEnforcementDecision
```json
{
  "verdict": "block"
}
```

### Valid Agent Action
```json
{
  "session_id": "sess_12345",
  "ctx_id": "ctx_abc123",
  "payload": {
    "tool": "read_file",
    "path": "/workspace/project/README.md"
  }
}
```

### Valid Consensus Engine Invocation
```json
{
  "task": "Implement: SampleSpec",
  "context": "Relevant implementation context",
  "language": "python"
}
```

### Valid Consensus Engine Result
```json
{
  "final_code": "print('hello')"
}
```

---

## Invalid Payloads

### Invalid TrustFlowEvent: missing required field
```json
{
  "event_id": "b9d7b4d8-8b8e-4b33-9e8d-5d0d5e8c1a21",
  "session_id": "sess_12345",
  "ts": 1712345678123,
  "event_type": "action.allow",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

Reason:
- `ctx_id` is required.

### Invalid VTZEnforcementDecision: wrong verdict
```json
{
  "verdict": "allow"
}
```

Reason:
- VTZ policy denial MUST produce `verdict=block`.

### Invalid Consensus Engine Invocation: unsupported language
```json
{
  "task": "Implement: SampleSpec",
  "context": "Relevant implementation context",
  "language": "java"
}
```

Reason:
- `language` MUST be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid Agent Action: missing ctx_id
```json
{
  "session_id": "sess_12345",
  "payload": {
    "tool": "read_file"
  }
}
```

Reason:
- CTX-ID validation must occur first.
- Missing CTX-ID must be treated as `UNTRUSTED`.

### Invalid Security Behavior
```python
subprocess.run(cmd, shell=True)
```

Reason:
- `shell=True` is forbidden.

```python
eval(untrusted_content)
```

Reason:
- `eval()` on generated or external content is forbidden.

```python
log.info("response body: %s", response.text)
```

Reason:
- HTTP response bodies must never be logged.

---

## Integration Points

## 1. Agent Entry Points

Any CraftedApp entry point that processes agent actions MUST:

1. Validate `ctx_id` first.
2. Reject immediately on CTX-ID validation failure.
3. Check VTZ policy before executing the action.
4. Produce `VTZEnforcementDecision` with `verdict=block` on denial.
5. Emit a synchronous TrustFlow event for every outcome.

## 2. TrustLock

CTX-ID validation MUST integrate with:

- TrustLock public key validation

Constraint:
- Software-only validation is rejected.

## 3. VTZ Policy Engine

CraftedApp MUST integrate with a VTZ policy enforcement mechanism that supports:

- session bound to EXACTLY ONE VTZ
- explicit authorization for cross-VTZ tool calls
- denial by default for implicit cross-VTZ access
- policy application at NEXT CTX-ID issuance

## 4. TrustFlow Audit Pipeline

CraftedApp MUST integrate with a TrustFlow emission path that:

- accepts `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash`
- emits synchronously in the enforcement path
- surfaces emission failures
- records failures as WARN-level audit events

## 5. Consensus Engine

CraftedApp integrations using the consensus engine MUST call:

- `await self._consensus.run(...)`

With required parameters:

- `task`
- `context`
- `language`

And must consume:

- `result.final_code`

## 6. File Write Security

Before any disk write, CraftedApp MUST integrate with:

- `path_security.validate_write_path()`

This validation MUST occur before any write operation.

## 7. Prompt Construction / External Content Handling

For any external document content included in prompts:

- loaded document chunks MUST pass injection scanning
- external document context MUST be placed in the USER prompt
- external document context MUST NOT be placed in the SYSTEM prompt

## 8. LLM Security Refusal Handling

When the LLM returns:

- `SECURITY_REFUSAL`

CraftedApp MUST:

1. stop
2. gate
3. log
4. never retry to bypass

--- 

## Conformance Summary

A CraftedApp component is non-conformant if any of the following are violated:

- missing required TrustFlow event fields
- non-unique or sequential `event_id`
- non-millisecond or non-UTC `ts`
- incorrect `payload_hash`
- CTX-ID not validated first
- partial processing before CTX-ID validation
- expired or rotated CTX-ID accepted
- software-only CTX-ID validation
- missing TrustFlow event for any `allow` / `restrict` / `block` outcome
- asynchronous TrustFlow buffering in enforcement path
- VTZ denial without `VTZEnforcementDecision(verdict="block")`
- implicit cross-VTZ access
- bypassable VTZ enforcement
- forbidden security patterns
- unsupported consensus `language`
- use of length-based fix arbitration instead of `_score_fix()`