# Interface Contracts - ForgeAgent

## Data Structures

This document defines the wire-format and API contract requirements for the ForgeAgent subsystem, based strictly on the provided TRD interface content.

Where the TRD specifies behavior without a concrete message schema, this document records the required fields, values, and constraints exactly as stated.

---

### 1. Consensus Run Request

Used when invoking the consensus engine.

#### Shape

```python
await self._consensus.run(
    task=str,
    context=str,
    language=str,
)
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Free-form task string. Example source usage: `f"Implement: {spec.title}"` |
| `context` | `str` | Yes | Context string passed to consensus engine |
| `language` | `str` | Yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Constraints

- `language` is mandatory. The TRD states: **Always pass language**.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### 2. Consensus Run Result

Returned by the consensus engine.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Final generated code output |

#### Source usage

```python
code = result.final_code
```

---

### 3. Fix Strategy Selection Input

Used by failure-type-aware fix loop selection.

#### Function Shape

```python
_choose_strategy(failure_type, attempt, records)
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | unspecified | Yes | Must be provided; strategy is chosen from failure type |
| `attempt` | unspecified | Yes | Must be provided |
| `records` | unspecified | Yes | Must be provided |

#### Constraints

- Strategy selection is **failure-type-aware**.
- Strategy selection is **not** a static lookup table.

---

### 4. Fix Arbitration Input

Used when scoring candidate fixes.

#### Function Shape

```python
_score_fix()
```

#### Constraints

- Fix arbitration uses `_score_fix()` based on **assertion token overlap**.
- Length-based arbitration is forbidden.

#### Forbidden pattern

```python
winner = max(claude_fix, openai_fix, key=len)
```

---

### 5. TrustFlow Event

Every action outcome must emit a TrustFlow event.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | Yes | Must be globally unique; generated with CSPRNG; must not be sequential |
| `session_id` | string | Yes | Required on every TrustFlow event |
| `ctx_id` | string | Yes | Required on every TrustFlow event |
| `ts` | number | Yes | Must be UTC Unix timestamp with millisecond precision |
| `event_type` | string | Yes | Required on every TrustFlow event |
| `payload_hash` | string | Yes | Must be SHA-256 of the serialized action payload |

#### Constraints

- Emission must be **synchronous** in the enforcement path.
- Async buffering is **not permitted**.
- Failed emission is a **WARN-level audit event**, not a silent skip.
- Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.

---

### 6. VTZ Enforcement Decision Record

Produced on VTZ policy denial.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | Yes | Must be exactly `block` on VTZ policy denial |

#### Constraints

- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 7. CTX-ID Token

A CTX-ID token is required for trusted processing of agent actions.

#### Fields

No concrete field-level schema is provided in the supplied TRD excerpt.

#### Contractual properties

| Property | Requirement |
|---|---|
| Mutability | CTX-ID tokens are immutable once issued |
| Rotation | Rotation creates a new token; old token is invalidated immediately |
| Expiry | Expired CTX-ID must be rejected |
| Validation | Must be validated against TrustLock public key |
| Missing token handling | Missing CTX-ID must be treated as `UNTRUSTED` |

#### Constraints

- Software-only validation is rejected.
- Identity must never be inferred from context when CTX-ID is missing.

---

### 8. Agent Action Processing Envelope

Any entry point that processes an agent action is subject to CAL enforcement.

#### Minimum processing requirements

| Step | Requirement |
|---|---|
| 1 | CTX-ID validation must be called first |
| 2 | On CTX-ID validation failure, reject immediately |
| 3 | Check action against VTZ policy before execution |
| 4 | On VTZ denial, produce `VTZEnforcementDecision` with `verdict=block` |
| 5 | Emit TrustFlow event for every action outcome |
| 6 | If TrustFlow emission fails, log and surface the failure |

#### Notes

No concrete serialized action schema is provided in the supplied TRD excerpt. However, the serialized action payload is the input to `payload_hash`.

---

## Enums and Constants

### Language

Allowed values for `Consensus Run Request.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Enforcement Verdict

Allowed/required values explicitly present in the TRD:

- `block`

### Action Outcomes

Explicitly referenced action outcomes:

- `allow`
- `restrict`
- `block`

### Trust Classification

Explicitly referenced classification:

- `UNTRUSTED`

### Log/Audit Severity

Explicitly referenced severity:

- `WARN`

### Security Refusal Sentinel

Explicit sentinel output from the LLM:

- `SECURITY_REFUSAL`

### System Selectors

Explicitly referenced generation system constants:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

---

## Validation Rules

## 1. Consensus Engine Rules

1. Every consensus invocation must include `language`.
2. `language` must be exactly one of:
   - `"python"`
   - `"swift"`
   - `"go"`
   - `"typescript"`
   - `"rust"`
3. For Swift generation:
   - use `SWIFT_GENERATION_SYSTEM`
   - optionally inject `SWIFT_UI_ADDENDUM` when UI keywords are detected
4. For Python generation:
   - use `GENERATION_SYSTEM`

---

## 2. Fix Loop Rules

1. Strategy selection must use `_choose_strategy(failure_type, attempt, records)`.
2. Strategy selection must be failure-type-aware.
3. Static lookup table strategy selection is non-conformant.
4. Fix arbitration must use `_score_fix()`.
5. Length-based arbitration is forbidden.

Invalid example:

```python
winner = max(claude_fix, openai_fix, key=len)
```

---

## 3. CAL Enforcement Rules

1. Every entry point that processes an agent action must call CTX-ID validation first.
2. CTX-ID validation failure must result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action must be checked against VTZ policy before execution.
5. VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every action outcome must emit a TrustFlow event.
7. TrustFlow emission failure must not silently continue.
8. TrustFlow emission failure must be logged and surfaced.

---

## 4. TrustFlow Validation Rules

A valid TrustFlow event must include all required fields:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Additional constraints:

1. `event_id` must be globally unique.
2. `event_id` must be generated using CSPRNG.
3. `event_id` must not be sequential.
4. `ts` must be a UTC Unix timestamp with millisecond precision.
5. `payload_hash` must be the SHA-256 of the serialized action payload.
6. Emission must be synchronous in the enforcement path.
7. Async buffering is not permitted.
8. Failed emission must produce a WARN-level audit event.

---

## 5. CTX-ID Validation Rules

1. CTX-ID tokens are immutable once issued.
2. CTX-ID rotation creates a new token.
3. The old token is invalidated immediately on rotation.
4. Expired CTX-ID must be rejected.
5. Clock skew tolerance is deployment-defined.
6. CTX-ID must be validated against TrustLock public key.
7. Software-only validation is rejected.
8. Missing CTX-ID must be treated as `UNTRUSTED`.
9. Identity must never be inferred from context when CTX-ID is missing.

---

## 6. VTZ Enforcement Rules

1. Every agent session is bound to exactly one VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit cross-VTZ access is denied.
4. VTZ boundaries are structural, not advisory.
5. Enforcement cannot be bypassed by application code.
6. VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 7. Security Rules

The following are hard requirements:

1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Log status codes and error types only.
6. All file paths written to disk must pass `path_security.validate_write_path()` before any write.
7. All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
8. Context from external documents goes in the USER prompt, never the SYSTEM prompt.
9. When `SECURITY_REFUSAL` output is seen from the LLM:
   - stop
   - gate
   - log
   - never retry to bypass

---

## 8. Python Backend Rules

1. Python version is `3.12`.
2. Every function must have type annotations.
3. Use `async/await` throughout the backend.
4. No blocking calls on the event loop.
5. Use dataclasses for all structured data.
6. Use `pytest` for all tests.
7. Tests live in `tests/`.
8. Tests must mirror `src/` structure.
9. `ruff` must pass clean.
10. `mypy` must pass clean.
11. Test coverage must be `>= 85%` on all new modules.
12. `pyyaml` must be in `requirements.txt`.

---

## 9. Forbidden Code Patterns

### Swift

Forbidden:

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

Constraint:

- Only Swift reads Keychain, only to deliver via XPC.
- Python reads nothing from Keychain.
- LLM API calls from Swift are forbidden.

---

## Wire Format Examples

## 1. Valid Consensus Run Request

```json
{
  "task": "Implement: Add session validation",
  "context": "Existing subsystem context and constraints",
  "language": "python"
}
```

Why valid:
- includes `task`
- includes `context`
- includes `language`
- `language` is one of the allowed values

---

## 2. Invalid Consensus Run Request: missing language

```json
{
  "task": "Implement: Add session validation",
  "context": "Existing subsystem context and constraints"
}
```

Why invalid:
- `language` is required

---

## 3. Invalid Consensus Run Request: unsupported language

```json
{
  "task": "Implement: Add session validation",
  "context": "Existing subsystem context and constraints",
  "language": "java"
}
```

Why invalid:
- `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`

---

## 4. Valid Consensus Run Result

```json
{
  "final_code": "from dataclasses import dataclass\n..."
}
```

Why valid:
- includes required `final_code`

---

## 5. Valid TrustFlow Event

```json
{
  "event_id": "8e6eb31f-8ee1-4f91-9d2c-2fd2d7d7b8c4",
  "session_id": "sess_01HZXA1YQK9M",
  "ctx_id": "ctx_01HZXA20V2M1",
  "ts": 1712345678123,
  "event_type": "action.block",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

Why valid:
- all required fields present
- `ts` is millisecond Unix time
- `payload_hash` is a SHA-256 hex digest
- `event_id` is non-sequential in representation

---

## 6. Invalid TrustFlow Event: missing required field

```json
{
  "event_id": "8e6eb31f-8ee1-4f91-9d2c-2fd2d7d7b8c4",
  "session_id": "sess_01HZXA1YQK9M",
  "ts": 1712345678123,
  "event_type": "action.block",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

Why invalid:
- missing `ctx_id`

---

## 7. Invalid TrustFlow Event: bad timestamp precision

```json
{
  "event_id": "8e6eb31f-8ee1-4f91-9d2c-2fd2d7d7b8c4",
  "session_id": "sess_01HZXA1YQK9M",
  "ctx_id": "ctx_01HZXA20V2M1",
  "ts": 1712345678,
  "event_type": "action.block",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

Why invalid:
- `ts` must use millisecond precision

---

## 8. Valid VTZ Enforcement Decision Record

```json
{
  "verdict": "block"
}
```

Why valid:
- VTZ denial requires `verdict=block`

---

## 9. Invalid VTZ Enforcement Decision Record

```json
{
  "verdict": "allow"
}
```

Why invalid:
- on VTZ policy denial, `verdict` must be exactly `block`

---

## 10. Invalid Fix Arbitration Example

```python
winner = max(claude_fix, openai_fix, key=len)
```

Why invalid:
- length-based arbitration is explicitly forbidden

---

## Integration Points

## 1. Consensus Engine

ForgeAgent integrates with a consensus engine via:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### Contract requirements

- invocation must be `await`-based
- `language` must be passed explicitly
- result must expose `final_code`

---

## 2. TrustFlow

ForgeAgent must emit TrustFlow events in the enforcement path.

### Required event fields

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

### Required behavior

- synchronous emission only
- no async buffering
- WARN-level audit on failed emission
- failure must be surfaced, not silently skipped

---

## 3. CTX-ID Validation

ForgeAgent entry points that process agent actions must validate CTX-ID first.

### Required behavior

- validate before any partial processing
- reject immediately on failure
- treat missing CTX-ID as `UNTRUSTED`
- validate against TrustLock public key

---

## 4. VTZ Policy Enforcement

ForgeAgent must enforce VTZ policy before action execution.

### Required behavior

- one session maps to exactly one VTZ at CTX-ID issuance
- cross-VTZ tool calls require explicit authorization
- denials produce `VTZEnforcementDecision` with `verdict=block`

---

## 5. Path Security

Before any disk write:

```python
path_security.validate_write_path()
```

### Required behavior

- every file path written to disk must be validated before write

---

## 6. Injection Scanning

Before external document chunks are included in prompts:

- all loaded document chunks must pass injection scanning

### Prompt placement rule

- external document context goes in the USER prompt
- never in the SYSTEM prompt

---

## 7. LLM Security Refusal Handling

When LLM output equals or contains `SECURITY_REFUSAL`:

- stop
- gate
- log
- never retry to bypass

---

## 8. Swift/XPC Boundary

### Required behavior

- Swift may read Keychain only to deliver via XPC
- Python reads nothing from Keychain
- Swift must not perform LLM API calls directly

---

## 9. Testing and Conformance Workflow

Before implementation work:

```bash
cd src && pytest ../tests/ -v --tb=short
```

### Required conformance checks

- relevant TRD sections must be read before modifying the component
- check TRD-11 if credentials, external content, generated code, or CI are touched
- run existing tests before making changes

---

## Non-Specified Areas

The supplied TRD content does **not** provide concrete field schemas for the following, so no additional fields may be inferred from this document:

- serialized agent action payload structure
- full `VTZEnforcementDecision` schema beyond `verdict=block`
- CTX-ID token internal field layout
- session object schema
- XPC message schema
- injection scan result schema
- TrustLock public key distribution format

Only the explicitly stated interfaces and constraints above are normative in this document.