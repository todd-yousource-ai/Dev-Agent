# Interface Contracts - CraftedApp

## Scope

This document defines the wire-format and API contract requirements for the CraftedApp subsystem based on the provided TRD content.

Where the source text specifies normative behavior, the values and field names below are reproduced exactly.

---

## Data Structures

### ConsensusRunRequest

Request contract for invoking the consensus engine.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Free-form task description. Example source usage: `"Implement: {spec.title}"` |
| `context` | `string` | yes | Context string passed to the engine |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | yes | Must always be passed |

#### Required call shape

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

#### Output fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Final generated code result |

---

### VTZEnforcementDecision

Record emitted when VTZ policy denies an action.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | For denial, MUST equal `block` |

#### Notes

- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Every action outcome must emit a TrustFlow event.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique; CSPRNG, not sequential |
| `session_id` | `string` | yes | Session identifier |
| `ctx_id` | `string` | yes | CTX-ID associated with the action |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Event classification |
| `payload_hash` | `string` | yes | MUST be SHA-256 of the serialized action payload |

#### Behavioral constraints

- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### CTX-ID Token

Logical token contract for CTX-ID handling.

#### Fields

The TRD excerpt does not define a concrete serialized field schema for CTX-ID tokens. The following constraints are normative:

| Property | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Missing `CTX-ID` MUST be treated as `UNTRUSTED` |
| `immutable` | `boolean` | implied | CTX-ID tokens are IMMUTABLE once issued |
| `expired` | `boolean` | implied | Expired CTX-ID MUST be rejected |
| `validated_against_trustlock_public_key` | `boolean` | implied | MUST be true for acceptance; software-only validation is rejected |

#### Lifecycle constraints

- CTX-ID rotation creates a new token.
- The old token is invalidated immediately.
- No field modification is permitted after issuance.
- Clock skew tolerance is defined per deployment.

---

### AgentActionProcessingEntryPoint

Normative processing contract for any entry point that processes an agent action.

#### Required ordered checks

| Order | Step | Required |
|---:|---|---:|
| 1 | CTX-ID validation | yes |
| 2 | Immediate rejection on CTX-ID validation failure | yes |
| 3 | VTZ policy check before execution | yes |
| 4 | Produce `VTZEnforcementDecision` on VTZ denial | yes |
| 5 | Emit `TrustFlowEvent` for every action outcome | yes |
| 6 | Log and surface TrustFlow emission failure | yes |

---

## Enums and Constants

### Language

Allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Verdict

Known required value from the TRD:

- `block`

### Action Outcome

Action outcomes that MUST emit TrustFlow events:

- `allow`
- `restrict`
- `block`

### Trust Classification

Known required classification:

- `UNTRUSTED`

### Logging / audit severity

Known required severity:

- `WARN`

### Security refusal sentinel

Known output token:

- `SECURITY_REFUSAL`

### Generator system selection constants

Known exact values:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Python runtime contract constants

Known exact values:

- Python version: `3.12`
- Test framework: `pytest`
- Linter: `ruff`
- Type checker: `mypy`
- YAML package requirement: `pyyaml`
- Coverage floor: `85%`

---

## Validation Rules

## 1. Consensus Engine Usage

### Required

- Always pass `language`.
- `language` MUST be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

### Selection behavior

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

### Fix strategy behavior

- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Length-based fix arbitration is forbidden.

### Forbidden example

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

---

## 2. Security Rules

### Forbidden

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on any generated or external content.
- Never log HTTP response bodies.
- Never retry to bypass `SECURITY_REFUSAL`.

### Required

- Log status codes and error types only for HTTP failures.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` is seen: stop, gate, log.

---

## 3. Python Backend Rules

- Python must be `3.12`.
- Type annotations on every function.
- `async/await` throughout the backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` and `mypy` must pass clean.
- Test coverage must be at least `85%` on all new modules.
- `pyyaml` must be in `requirements.txt`.

---

## 4. CAL Enforcement Contract

### Required

- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted after CTX-ID validation failure.
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- TrustFlow emission failure MUST NOT silently continue.
- TrustFlow emission failure MUST be logged and surfaced.

---

## 5. TrustFlow Emission Contract

### Required fields

A TrustFlow event MUST include:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

### Field constraints

- `event_id` MUST be globally unique.
- `event_id` MUST use CSPRNG.
- `event_id` MUST NOT be sequential.
- `ts` MUST be a UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.

### Emission constraints

- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission must not be silently skipped.

---

## 6. CTX-ID Contract

- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is allowed after issuance.
- CTX-ID rotation creates a new token.
- The old one is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity must never be inferred from context when CTX-ID is missing.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

---

## 7. VTZ Enforcement Contract

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance.
- VTZ policy changes do not take effect mid-session.

---

## Wire Format Examples

## Valid Payloads

### Valid consensus engine request

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context",
  "language": "python"
}
```

### Valid TrustFlow event

```json
{
  "event_id": "6f7f7d8c-3d1c-4d55-8b89-5d52d7d8f0a1",
  "session_id": "session-123",
  "ctx_id": "ctx-abc",
  "ts": 1712345678123,
  "event_type": "allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

### Valid VTZ enforcement denial record

```json
{
  "verdict": "block"
}
```

---

## Invalid Payloads

### Invalid consensus request: missing language

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context"
}
```

Reason:
- `language` is required.

### Invalid consensus request: unsupported language

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context",
  "language": "java"
}
```

Reason:
- `language` must be one of `"python" | "swift" | "go" | "typescript" | "rust"`.

### Invalid TrustFlow event: missing required field

```json
{
  "event_id": "6f7f7d8c-3d1c-4d55-8b89-5d52d7d8f0a1",
  "session_id": "session-123",
  "ctx_id": "ctx-abc",
  "ts": 1712345678123,
  "event_type": "allow"
}
```

Reason:
- `payload_hash` is required.

### Invalid VTZ decision: wrong verdict

```json
{
  "verdict": "allow"
}
```

Reason:
- On VTZ policy denial, `verdict` MUST equal `block`.

### Invalid Swift behavior

```swift
let value = optional!
```

Reason:
- Force unwrap is forbidden.

### Invalid backend credential access in Swift

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Reason:
- LLM API call from Swift is forbidden.

### Invalid backend token read

```swift
let token = KeychainKit.read("github_token")
```

Reason:
- Keychain read for backend is forbidden.
- Only Swift reads Keychain, only to deliver via XPC.

---

## Integration Points

## Pre-implementation workflow

Before code changes:

1. Find the TRD that owns the component being modified.
2. Read the relevant TRD sections:
   - interfaces
   - error contracts
   - security
   - testing requirements
3. Check `TRD-11` if the change touches:
   - credentials
   - external content
   - generated code
   - CI
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## Consensus engine integration

Required invocation shape:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

---

## File write integration

Before any disk write:

- `path_security.validate_write_path()` MUST be called successfully.

---

## Prompt construction integration

- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST be placed in the USER prompt.
- Context from external documents MUST NOT be placed in the SYSTEM prompt.

---

## Enforcement-path integration

For every agent action:

1. Validate CTX-ID first.
2. Reject immediately on failure.
3. Check VTZ policy before execution.
4. If denied, produce `VTZEnforcementDecision` with `verdict=block`.
5. Emit synchronous TrustFlow event with:
   - `event_id`
   - `session_id`
   - `ctx_id`
   - `ts`
   - `event_type`
   - `payload_hash`
6. If TrustFlow emission fails:
   - log it
   - surface it
   - do not silently continue

---

## Non-conformance

A Crafted component that does not implement these contracts is non-conformant.