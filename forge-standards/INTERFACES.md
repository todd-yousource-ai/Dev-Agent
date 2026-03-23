# Interface Contracts - FullPlatform

## Data Structures

This document defines the wire-format and API contract requirements for the FullPlatform subsystem based on the provided TRD interface content.

### ConsensusRunRequest

Request passed to the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Human-readable task description. Example from contract: `"Implement: {spec.title}"` |
| `context` | `string` | yes | Context string supplied to the consensus engine |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | yes | Must always be passed |

#### Required invocation form

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### ConsensusRunResult

Result returned by the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Generated code output |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | Must be exactly `block` for VTZ policy denial records |

---

### TrustFlowEvent

Audit/event record emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | Must be globally unique; generated via CSPRNG, not sequential |
| `session_id` | `string` | yes | Session identifier |
| `ctx_id` | `string` | yes | CTX-ID associated with the action |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Event type identifier |
| `payload_hash` | `string` | yes | Must be SHA-256 of the serialized action payload |

---

### CTXIDToken

Logical token requirements for CTX-ID.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Immutable once issued |
| `bound_vtz` | `string` | yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance |
| `expired` | `boolean` | yes | Expired CTX-ID must be rejected |
| `valid_signature` | `boolean` | yes | Must validate against TrustLock public key |
| `issued_at` | `number` | implied | UTC Unix timestamp semantics are implied by issuance/expiry handling |
| `expires_at` | `number` | implied | Subject to deployment-defined clock skew tolerance |

Note: The TRD content specifies behavioral constraints for CTX-ID, but does not define a canonical serialized token schema beyond `ctx_id` semantics. Implementations must not mutate fields after issuance.

---

### AgentActionPayload

Serialized payload whose hash is used in TrustFlow emission.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `payload` | `object` | yes | Must be serialized deterministically for `payload_hash` computation |

No additional action payload field schema is defined in the provided TRD excerpt.

---

### SecurityRefusalSignal

Special output from the LLM pipeline.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `value` | `string` | yes | Must be exactly `SECURITY_REFUSAL` |

Behavioral contract:
- When `SECURITY_REFUSAL` is seen: stop, gate, log.
- Never retry to bypass.

---

## Enums and Constants

### SupportedLanguage

Exact allowed values for consensus engine `language`:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

### LanguageSystemSelection

Derived behavior based on `language`:

| `language` | System selection |
|---|---|
| `swift` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords detected |
| `python` | `GENERATION_SYSTEM` |

No source-defined mappings were provided for `go`, `typescript`, or `rust` beyond being valid `language` values.

### VTZVerdict

Known required value from contract:

- `block`

### SecurityRefusalConstant

- `SECURITY_REFUSAL`

### Logging / Audit Severity

Known exact severity value from contract:

- `WARN`

---

## Validation Rules

## Entry Point Enforcement

Every entry point that processes an agent action MUST satisfy all of the following in order:

1. Call CTX-ID validation FIRST.
2. On CTX-ID validation failure, immediately reject.
3. Do not perform partial processing after CTX-ID validation failure.
4. Check every action against VTZ policy BEFORE execution.
5. On VTZ policy denial, produce a `VTZEnforcementDecision` with `verdict=block`.
6. Emit a TrustFlow event for every action outcome:
   - `allow`
   - `restrict`
   - `block`
7. TrustFlow emission failure MUST NOT silently continue.
8. Failed emission must be logged and surfaced.

## TrustFlow Event Validation

A `TrustFlowEvent` is valid only if:

- `event_id` is globally unique
- `event_id` is generated using CSPRNG
- `event_id` is not sequential
- `ts` is a UTC Unix timestamp
- `ts` has millisecond precision
- `payload_hash` equals the SHA-256 of the serialized action payload
- emission is synchronous in the enforcement path
- async buffering is not permitted

Failure behavior:
- Failed emission is a `WARN`-level audit event
- failed emission must not be silently skipped

## CTX-ID Validation

A CTX-ID is valid only if all of the following hold:

- token is present; missing CTX-ID must be treated as `UNTRUSTED`
- token is immutable once issued
- if rotation occurs, a new token is created and the old one is invalidated immediately
- expired token is rejected
- validation is performed against TrustLock public key
- software-only validation is rejected
- identity must never be inferred from surrounding context when CTX-ID is missing

## VTZ Enforcement Validation

- Every agent session must be bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit cross-VTZ access is denied
- VTZ boundaries are structural, not advisory
- Enforcement cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session

## Consensus Engine Validation

- `language` must always be passed
- `language` must be one of:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`

Fix-loop behavior constraints:

- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`
- It is not a static lookup table
- Fix arbitration uses `_score_fix()`
- Fix arbitration must not use response length

Forbidden example:

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

## Security Validation

### Credentials and secrets

- Never hardcode credentials, API keys, tokens, or secrets as string literals

### Subprocess

- Never use `shell=True` in subprocess calls

### Dynamic execution

- Never call `eval()` or `exec()` on generated or external content

### Logging

- Never log HTTP response bodies
- Log status codes and error types only

### File writes

- All file paths written to disk must pass `path_security.validate_write_path()` before any write

### Document injection scanning

- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt
- Context from external documents goes in the USER prompt, never the SYSTEM prompt

### SECURITY_REFUSAL handling

- On `SECURITY_REFUSAL`: stop, gate, log
- Never retry to bypass

## Python Backend Requirements

These are interface-adjacent implementation requirements enforced by contract:

- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Tests use `pytest`
- Tests live in `tests/` and mirror `src/` structure
- `ruff` must pass
- `mypy` must pass
- Test coverage must be `≥ 85%` on all new modules
- `pyyaml` must be in `requirements.txt`

## Forbidden Patterns

### Swift

```swift
let value = optional!
```

Forbidden because force unwrap is disallowed.

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Forbidden because LLM API calls from Swift are disallowed.

```swift
let token = KeychainKit.read("github_token")
```

Forbidden for backend credential access. Only Swift reads Keychain, and only to deliver via XPC.

---

## Wire Format Examples

## Valid Payloads

### Valid `ConsensusRunRequest`

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context",
  "language": "python"
}
```

### Valid `TrustFlowEvent`

```json
{
  "event_id": "3f7d5b8c-2f41-4f6d-9d1d-7f2f8b8d4a11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961fca8ba17bca8db811b9c2c"
}
```

### Valid `VTZEnforcementDecision`

```json
{
  "verdict": "block"
}
```

### Valid `SECURITY_REFUSAL` signal

```json
{
  "value": "SECURITY_REFUSAL"
}
```

## Invalid Payloads

### Invalid `ConsensusRunRequest` — missing `language`

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context"
}
```

Reason:
- `language` is required and must always be passed

### Invalid `ConsensusRunRequest` — unsupported `language`

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context",
  "language": "java"
}
```

Reason:
- `language` must be one of `python`, `swift`, `go`, `typescript`, `rust`

### Invalid `TrustFlowEvent` — missing required fields

```json
{
  "event_id": "123",
  "session_id": "sess_123"
}
```

Reason:
- Missing `ctx_id`, `ts`, `event_type`, and `payload_hash`

### Invalid `VTZEnforcementDecision` — wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- For VTZ policy denial, verdict must be exactly `block`

### Invalid CTX-ID handling example

```json
{
  "ctx_id": null
}
```

Reason:
- Missing CTX-ID must be treated as `UNTRUSTED`
- Identity must never be inferred from context

---

## Integration Points

## Consensus Engine

Interface usage contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

Integration rules:

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `language="python"` selects `GENERATION_SYSTEM`
- fix-loop strategy uses `_choose_strategy(failure_type, attempt, records)`
- fix arbitration uses `_score_fix()`

## CTX-ID Validation Layer

The CTX-ID validation layer must be invoked before any processing of agent actions.

Required behaviors:

- validate against TrustLock public key
- reject expired tokens
- reject missing tokens as untrusted
- invalidate old token immediately on rotation

## VTZ Policy Engine

The VTZ policy engine must evaluate every action before execution.

Required outputs:

- on denial, create `VTZEnforcementDecision` with `verdict=block`

## TrustFlow Emission Pipeline

TrustFlow emission is part of the enforcement path.

Required characteristics:

- synchronous emission only
- no async buffering
- emit on every action outcome
- on failure, emit/log a `WARN`-level audit event and surface failure

## Path Security

Before any disk write:

- call `path_security.validate_write_path()`

## Prompt Construction / Document Loading

Before including loaded document chunks in prompts:

- perform injection scanning
- place external document context in the USER prompt
- never place external document context in the SYSTEM prompt

## Testing Invocation

Required existing test invocation before changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```