# Interface Contracts - FullPlatform

## Data Structures

This document defines the required wire-format and API/interface contracts for the FullPlatform subsystem based on the provided TRD content.

### Consensus Engine Request

Represents a backend call into the consensus engine.

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
| `task` | `string` | Yes | Free-form task description. Example source value: `f"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string supplied to the consensus engine. |
| `language` | `string` | Yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. |

#### Response

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Final generated code output from consensus engine. |

---

### TrustFlow Event

Every TrustFlow event MUST include the following fields.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Globally unique. MUST be generated using CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID token identifier associated with the session/action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Behavioral Constraints

- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission MUST NOT be silently skipped.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### VTZEnforcementDecision

Produced when VTZ policy denies an action.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | For denial records, MUST be exactly `block`. |

#### Behavioral Constraints

- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### CTX-ID Token

Represents the trust-bound identity token used for action processing.

#### Fields

The source specifies behavioral constraints but does not enumerate internal token fields. The only explicitly required wire-visible field name is:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. Must validate against TrustLock public key. Missing value MUST be treated as `UNTRUSTED`. |

#### Behavioral Constraints

- CTX-ID validation MUST occur FIRST on every entry point that processes an agent action.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted after validation failure.
- CTX-ID tokens are IMMUTABLE once issued.
- CTX-ID rotation creates a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from context when `ctx_id` is missing.

---

### Agent Action Processing Contract

Represents the required execution sequence for any entry point processing an agent action.

#### Required Inputs

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Must be validated first. |
| `session_id` | `string` | Yes | Used in TrustFlow emission. |
| `action_payload` | `object` | Yes | Serialized payload used to compute `payload_hash`. |
| `vtz_policy` | `object` | Yes | Must be evaluated before execution. |

#### Behavioral Constraints

1. CTX-ID validation MUST occur first.
2. On CTX-ID validation failure, processing MUST stop immediately.
3. VTZ policy evaluation MUST occur before execution.
4. On VTZ denial, emit `VTZEnforcementDecision` with `verdict=block`.
5. Emit TrustFlow event for every action outcome.
6. TrustFlow emission failure MUST be logged and surfaced.

---

## Enums and Constants

### Supported Consensus Languages

Exact allowed values for `language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Language Routing Constants

These values are referenced as exact selector names:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Enforcement Verdicts

Known exact values from source:

- `block`

### Action Outcomes

Known exact values from source:

- `allow`
- `restrict`
- `block`

### Special Security / Control Tokens

Exact values referenced by contract:

- `UNTRUSTED`
- `SECURITY_REFUSAL`

### Python Runtime Contract Constants

- Python version: `3.12`

---

## Validation Rules

## 1. Consensus Engine Validation

### Request validation

- `task` MUST be present and be a string.
- `context` MUST be present and be a string.
- `language` MUST be present and equal exactly one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

### Routing behavior

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

### Response validation

- `final_code` MUST be present and be a string.

---

## 2. Fix Strategy / Arbitration Rules

These are contractually relevant implementation constraints.

- Fix loop strategy is chosen via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup-table strategy selection is non-conformant.
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration is forbidden.

### Forbidden pattern

```python
winner = max(claude_fix, openai_fix, key=len)
```

This is invalid because `_score_fix()` MUST be used instead.

---

## 3. Security Validation Rules

### Credentials and secrets

- Never hardcode credentials, API keys, tokens, or secrets as string literals.

### Subprocesses

- Never use `shell=True` in subprocess calls.

### Code execution

- Never call `eval()` or `exec()` on generated or external content.

### Logging

- Never log HTTP response bodies.
- Log status codes and error types only.

### File writes

- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

### External document handling

- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.

### Security refusal handling

- When `SECURITY_REFUSAL` output is seen from the LLM:
  - stop
  - gate
  - log
  - never retry to bypass

---

## 4. Python Backend Contract Rules

- Python code MUST target `Python 3.12`.
- Every function MUST have type annotations.
- Backend code MUST use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses MUST be used for all structured data.
- Tests MUST use `pytest`.
- Tests MUST live in `tests/` and mirror `src/` structure.
- `ruff` MUST pass clean.
- `mypy` MUST pass clean.
- Test coverage MUST be at least `85%` on all new modules.
- `pyyaml` MUST be present in `requirements.txt`.

---

## 5. Swift / Backend Boundary Rules

### Forbidden patterns

#### Force unwrap

```swift
let value = optional!
```

Forbidden.

#### LLM API call from Swift

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Forbidden.

#### Keychain read for backend

```swift
let token = KeychainKit.read("github_token")
```

Forbidden for backend usage.

### Allowed boundary rule

- Only Swift reads Keychain.
- Swift may deliver values via XPC.
- Python reads nothing from Keychain.

---

## 6. CAL / Enforcement Validation Rules

- Every entry point processing an agent action MUST call CTX-ID validation first.
- CTX-ID validation failure MUST immediately reject the request.
- Every action MUST be checked against VTZ policy before execution.
- VTZ denial MUST produce a `VTZEnforcementDecision` with `verdict=block`.
- Every action outcome MUST emit a TrustFlow event.
- TrustFlow emission failure MUST NOT silently continue.
- TrustFlow emission failure MUST be logged and surfaced.

---

## 7. TrustFlow Validation Rules

A valid TrustFlow event MUST satisfy all of:

- `event_id` present, string, globally unique, CSPRNG-generated, non-sequential
- `session_id` present, string
- `ctx_id` present, string
- `ts` present, UTC Unix timestamp with millisecond precision
- `event_type` present, string
- `payload_hash` present, SHA-256 of serialized action payload

---

## 8. CTX-ID Validation Rules

- `ctx_id` MUST be present for trusted action processing.
- Missing `ctx_id` MUST be treated as `UNTRUSTED`.
- Expired `ctx_id` MUST be rejected.
- Rotated `ctx_id` invalidates the old token immediately.
- Validation MUST use TrustLock public key.
- Software-only validation is rejected.

---

## 9. VTZ Validation Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## Wire Format Examples

## Valid Payloads

### Valid Consensus Engine Request

```json
{
  "task": "Implement: Add authentication middleware",
  "context": "Backend subsystem context",
  "language": "python"
}
```

### Valid Consensus Engine Response

```json
{
  "final_code": "from dataclasses import dataclass\n..."
}
```

### Valid TrustFlow Event

```json
{
  "event_id": "8d4a5e4a-2d3f-4c2a-9e21-2c0c4b4d9a11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600123,
  "event_type": "action.block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

### Valid VTZ Enforcement Decision

```json
{
  "verdict": "block"
}
```

### Valid Agent Action Processing Input

```json
{
  "ctx_id": "ctx_abc123",
  "session_id": "sess_123",
  "action_payload": {
    "tool": "repo.write",
    "target": "src/app.py"
  },
  "vtz_policy": {
    "zone": "default",
    "allow": false
  }
}
```

---

## Invalid Payloads

### Invalid Consensus Engine Request: unsupported language

```json
{
  "task": "Implement: Add UI",
  "context": "UI work",
  "language": "java"
}
```

Reason: `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid TrustFlow Event: missing required field

```json
{
  "event_id": "8d4a5e4a-2d3f-4c2a-9e21-2c0c4b4d9a11",
  "session_id": "sess_123",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

Reason: `ctx_id` is required.

### Invalid VTZ Enforcement Decision: wrong verdict

```json
{
  "verdict": "allow"
}
```

Reason: VTZ denial records must use `verdict="block"`.

### Invalid Agent Action: missing CTX-ID

```json
{
  "session_id": "sess_123",
  "action_payload": {
    "tool": "repo.write"
  },
  "vtz_policy": {
    "zone": "default"
  }
}
```

Reason: missing `ctx_id` must be treated as `UNTRUSTED`; trusted processing must reject or gate accordingly.

### Invalid TrustFlow Event: bad payload hash semantics

```json
{
  "event_id": "evt_1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600,
  "event_type": "action.allow",
  "payload_hash": "not-a-sha256"
}
```

Reasons:
- `event_id` must be globally unique and non-sequential
- `ts` must be UTC Unix timestamp with millisecond precision
- `payload_hash` must be SHA-256 of serialized action payload

---

## Integration Points

## 1. Consensus Engine

### Invocation contract

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### Required behavior

- Always pass `language`.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` and optional `SWIFT_UI_ADDENDUM`.
- `language="python"` selects `GENERATION_SYSTEM`.

---

## 2. Enforcement Path

All agent action entry points integrate with:

- CTX-ID validation
- VTZ policy enforcement
- TrustFlow emission

Required execution order:

1. Validate `ctx_id`
2. Evaluate VTZ policy
3. Execute or block action
4. Emit TrustFlow event synchronously
5. Surface/log any emission failure

---

## 3. TrustLock

CTX-ID validation integrates with TrustLock public key verification.

Required contract:

- Validation against TrustLock public key is mandatory.
- Software-only validation is non-conformant.

---

## 4. Path Security

Any disk write integration MUST call:

- `path_security.validate_write_path()`

before performing the write.

---

## 5. Injection Scanning

Any external document chunk integrated into prompts MUST first pass injection scanning.

Required prompt placement rule:

- External document context goes in the USER prompt
- Never in the SYSTEM prompt

---

## 6. Testing Toolchain

Required integration points:

- `pytest`
- `ruff`
- `mypy`
- `pyyaml` in `requirements.txt`

Required test command:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## 7. Non-Conformant / Forbidden Integration Patterns

### Python

```python
winner = max(claude_fix, openai_fix, key=len)
```

Forbidden. Must use `_score_fix()`.

### Swift

```swift
let value = optional!
```

Forbidden.

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Forbidden.

```swift
let token = KeychainKit.read("github_token")
```

Forbidden for backend usage.

---

## Notes on Unspecified Fields

The source TRD excerpts do not define full serialized schemas for:

- CTX-ID token internals
- VTZ policy object internals
- Action payload schema
- TrustFlow `event_type` enumeration
- `VTZEnforcementDecision` fields other than `verdict`

Implementations MUST NOT invent incompatible field contracts where the TRD excerpt does not specify them. Only the fields and constraints listed above are normative from the provided source.