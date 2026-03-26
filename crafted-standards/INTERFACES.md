# Interface Contracts - CraftedAgent

## Data Structures

This section defines the required wire-format and behavioral contract for the CraftedAgent subsystem based on the provided TRD content.

### ConsensusRunRequest

Request passed to the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Human-readable implementation task. Example source usage: `"Implement: {spec.title}"` |
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

### TrustFlowEvent

Every action outcome must emit a TrustFlow event.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | Must be globally unique; generated via CSPRNG; must not be sequential |
| `session_id` | `string` | yes | Session identifier |
| `ctx_id` | `string` | yes | CTX-ID associated with the session/action |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Event type identifier |
| `payload_hash` | `string` | yes | Must be SHA-256 of the serialized action payload |

#### Behavioral requirements

- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission must not be silently skipped.
- TrustFlow emission failure must be logged and surfaced.

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | For denial, value MUST be exactly `block` |

#### Behavioral requirements

- Every action must be checked against VTZ policy before execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### CTX-ID Token

Opaque identity/security token used for agent action processing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Immutable once issued |

#### Behavioral requirements

- CTX-ID validation MUST occur first for every entry point that processes an agent action.
- Validation failure MUST result in immediate rejection.
- No partial processing is permitted after validation failure.
- Tokens are immutable once issued.
- Rotation creates a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID must be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from surrounding context when CTX-ID is missing.

---

### ActionPayload

Serialized action payload used to compute `payload_hash`.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _implementation-defined_ | serialized object | yes | Serialized form must be stable enough to compute SHA-256 for `payload_hash` |

#### Behavioral requirements

- `payload_hash` MUST equal SHA-256 of the serialized action payload.

---

### FailureStrategySelection

Internal fix-loop strategy selection contract.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `string` | yes | Used as input to strategy selection |
| `attempt` | `integer` | yes | Current retry/fix attempt |
| `records` | `array` | yes | Historical records used by strategy selection |

#### Required selection function

```python
_choose_strategy(failure_type, attempt, records)
```

#### Constraints

- Fix loop strategy is failure-type-aware.
- Static lookup-table strategy selection is non-conformant.

---

### FixArbitrationInput

Internal contract for choosing between fix candidates.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `assertion tokens` | tokenized text | yes | Used for overlap scoring |
| `candidate fix` | `string` | yes | Candidate response/fix body |

#### Required scoring function

```python
_score_fix()
```

#### Constraints

- Fix arbitration MUST use `_score_fix()`.
- Assertion token overlap is the scoring basis.
- Response length must not be used as the arbitration criterion.

---

## Enums and Constants

### SupportedLanguage

Exact allowed values for `ConsensusRunRequest.language`:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

### Language-System Mapping

| `language` value | Selected system |
|---|---|
| `swift` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected |
| `python` | `GENERATION_SYSTEM` |

No mappings were provided for `go`, `typescript`, or `rust` beyond their validity as `language` values.

### Special Security Output

| Constant | Type | Meaning |
|---|---|---|
| `SECURITY_REFUSAL` | `string` | LLM security refusal output; processing must stop |

#### Required handling

When `SECURITY_REFUSAL` is observed:

- stop
- gate
- log
- never retry to bypass

### Trust Verdict Values

| Value | Meaning |
|---|---|
| `block` | VTZ denial verdict |

### Trust State Values

| Value | Meaning |
|---|---|
| `UNTRUSTED` | Required treatment for missing CTX-ID |

---

## Validation Rules

## CraftedAgent entry-point enforcement

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur first.
2. If CTX-ID validation fails, processing MUST be immediately rejected.
3. No partial processing is allowed after CTX-ID validation failure.
4. VTZ policy MUST be checked before execution.
5. If VTZ denies the action, a `VTZEnforcementDecision` with `verdict=block` MUST be produced.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. If TrustFlow emission fails, the failure MUST be logged and surfaced.
8. TrustFlow emission failure MUST NOT silently continue.

## TrustFlow validation

A TrustFlow event is valid only if all required fields are present:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Additional rules:

- `event_id` must be globally unique.
- `event_id` must come from CSPRNG generation.
- `event_id` must not be sequential.
- `ts` must be a UTC Unix timestamp with millisecond precision.
- `payload_hash` must be a SHA-256 digest of the serialized action payload.
- Emission must be synchronous in the enforcement path.
- Async buffering is invalid.

## CTX-ID validation

A CTX-ID is valid only if:

- it is present, unless the caller is explicitly treated as `UNTRUSTED`
- it is not expired
- it validates against the TrustLock public key
- it has not been invalidated by rotation

Additional rules:

- Missing CTX-ID must never be inferred from context.
- Software-only validation is invalid.
- Rotation must invalidate the previous token immediately.
- VTZ policy changes apply only at next CTX-ID issuance.

## VTZ validation

- Every agent session must be bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes do not take effect mid-session.

## Consensus engine validation

- `language` must always be passed.
- `language` must be one of:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`

## Security validation

### Forbidden behaviors

The following are non-conformant:

- Hardcoded credentials, API keys, tokens, or secrets as string literals
- `shell=True` in subprocess calls
- `eval()` on generated or external content
- `exec()` on generated or external content
- Logging HTTP response bodies
- Writing any file path before passing it through `path_security.validate_write_path()`
- Including loaded document chunks in an LLM prompt without injection scanning
- Putting context from external documents in the SYSTEM prompt
- Retrying to bypass `SECURITY_REFUSAL`
- Length-based fix arbitration
- Swift force unwraps
- LLM API calls from Swift
- Python backend reading Keychain values

### Required security controls

- Log HTTP status codes and error types only.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents must go in the USER prompt, never the SYSTEM prompt.

## Python implementation contract

- Python version: `3.12`
- Type annotations required on every function
- Backend must use `async/await` throughout
- No blocking calls on the event loop
- Dataclasses required for all structured data
- Testing framework: `pytest`
- Tests must live in `tests/` and mirror `src/` structure
- `ruff` must pass
- `mypy` must pass
- Test coverage must be `>= 85%` on all new modules
- `pyyaml` must be present in `requirements.txt`

---

## Wire Format Examples

## Valid payloads

### Valid consensus run request

```json
{
  "task": "Implement: Add session enforcement",
  "context": "Relevant spec and constraints...",
  "language": "python"
}
```

### Valid TrustFlow event

```json
{
  "event_id": "7f0b0c74-8f4e-4b4e-9e91-0a4fc0f7d91a",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8a07a9e6eff5b7c2a4d6a4b1fdc0f6d9a"
}
```

### Valid VTZ enforcement decision

```json
{
  "verdict": "block"
}
```

## Invalid payloads

### Invalid consensus run request: missing language

```json
{
  "task": "Implement: Add session enforcement",
  "context": "Relevant spec and constraints..."
}
```

Reason: `language` MUST always be passed.

### Invalid consensus run request: unsupported language

```json
{
  "task": "Implement: Add session enforcement",
  "context": "Relevant spec and constraints...",
  "language": "java"
}
```

Reason: `language` must be one of `python`, `swift`, `go`, `typescript`, `rust`.

### Invalid TrustFlow event: missing required field

```json
{
  "event_id": "7f0b0c74-8f4e-4b4e-9e91-0a4fc0f7d91a",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600123,
  "event_type": "block"
}
```

Reason: missing `payload_hash`.

### Invalid VTZ enforcement decision

```json
{
  "verdict": "deny"
}
```

Reason: denial verdict MUST be exactly `block`.

### Invalid fix arbitration implementation

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason: length-based arbitration is forbidden; use `_score_fix()`.

### Invalid Swift code

```swift
let value = optional!
```

Reason: force unwrap is forbidden.

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Reason: LLM API call from Swift is forbidden.

```swift
let token = KeychainKit.read("github_token")
```

Reason: backend credentials must not be read from Keychain by Python; Swift may only read Keychain to deliver via XPC.

---

## Integration Points

## Consensus Engine

CraftedAgent must call the consensus engine with:

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

### Language-specific integration

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` and optionally `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

## CAL / CTX-ID / VTZ / TrustFlow enforcement path

Every agent action processing entry point integrates with:

1. CTX-ID validation
2. VTZ policy enforcement
3. TrustFlow synchronous emission

Required ordering:

1. validate CTX-ID
2. reject immediately on failure
3. check VTZ policy
4. execute only if allowed
5. emit TrustFlow event for every outcome

## Path security

Before any disk write:

```python
path_security.validate_write_path()
```

This validation must occur before the write operation.

## Prompt construction security

When using external documents:

- perform injection scanning on all loaded document chunks before including them in any LLM prompt
- place external document context in the USER prompt
- never place external document context in the SYSTEM prompt

## Test and quality gate integration

Before changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Required project quality/tooling integration:

- `pytest`
- `ruff`
- `mypy`
- coverage threshold `>= 85%` for new modules

## Non-conformance summary

A CraftedAgent component is non-conformant if any of the following are violated:

- missing CTX-ID-first validation
- partial processing after CTX-ID failure
- missing VTZ check before execution
- missing `VTZEnforcementDecision` with `verdict=block` on denial
- missing TrustFlow event emission for any action outcome
- silent TrustFlow emission failure
- async-buffered TrustFlow emission
- missing `language` in consensus calls
- length-based fix arbitration
- retrying after `SECURITY_REFUSAL`
- any listed security forbidden behavior