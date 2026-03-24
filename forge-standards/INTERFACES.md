# Interface Contracts - ForgeAgent

This document defines the wire format and API contract for the ForgeAgent subsystem from the provided TRD excerpts. All requirements below use the exact field names, values, and constraints available in source material.

## Data Structures

### ConsensusRunRequest

Request contract for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Freeform task description. Example source usage: `"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string passed to consensus engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. Exact allowed values are listed in source. |

#### Behavioral requirements
- Caller **must always pass** `language`.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result contract returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code result. Source usage: `code = result.final_code`. |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | Must be exactly `block` when produced for VTZ policy denial. |

#### Behavioral requirements
- Every action must be checked against VTZ policy **before** execution.
- VTZ policy denial **must produce** a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Required event shape for all TrustFlow emissions.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique. Must be generated with CSPRNG, not sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action/session. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | Must be SHA-256 of the serialized action payload. |

#### Behavioral requirements
- Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.
- Emission must be **synchronous** in the enforcement path.
- Async buffering is **not permitted**.
- Failed emission is a **WARN-level audit event**, not a silent skip.
- TrustFlow emission failure must **not silently continue**; it must be logged and surfaced.

---

### AgentActionProcessingContext

Minimum processing context implied by CAL enforcement contracts.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Must be validated first before any processing. Missing `ctx_id` must be treated as `UNTRUSTED`. |
| `session_id` | `string` | Yes | Required for TrustFlow event emission. |
| `action_payload` | `object` | Yes | Serialized form is used to compute `payload_hash` as SHA-256. |

#### Behavioral requirements
- Every entry point that processes an agent action must call CTX-ID validation **first**.
- CTX-ID validation failure must result in **immediate rejection** with **no partial processing**.

---

### CTXIDToken

Logical token contract derived from CTX-ID requirements.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. |
| `vtz_binding` | `string` | Yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance. |
| `expired` | `boolean` | Yes | If `true`, token must be rejected. |
| `valid_signature` | `boolean` | Yes | Must validate against TrustLock public key. Software-only validation is rejected. |

#### Behavioral requirements
- CTX-ID tokens are **immutable once issued**.
- Rotation creates a **new token**; the old one is **invalidated immediately**.
- Expired CTX-ID must be rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- CTX-ID must be validated against **TrustLock public key**.

> Note: Only constraints explicitly present in source are normative. Internal token fields beyond `ctx_id` are not defined in the provided excerpts.

---

### FixStrategySelectionInput

Input contract implied by failure-aware fix loop strategy.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `string` | Yes | Passed to `_choose_strategy(failure_type, attempt, records)`. |
| `attempt` | `integer` | Yes | Passed to `_choose_strategy(failure_type, attempt, records)`. |
| `records` | `array` | Yes | Passed to `_choose_strategy(failure_type, attempt, records)`. |

#### Behavioral requirements
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup table strategy selection is not conformant.

---

### FixArbitrationInput

Input contract implied by fix arbitration scoring.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `assertion_tokens` | `array<string>` | Yes | Used for assertion token overlap scoring. |
| `candidate_fix` | `string` | Yes | Candidate fix content to score. |

#### Behavioral requirements
- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Length-based arbitration is forbidden.

---

## Enums and Constants

### Language

Exact allowed values for `ConsensusRunRequest.language`:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

### ActionOutcome

Exact action outcome values that require TrustFlow emission:

- `allow`
- `restrict`
- `block`

### Verdict

Exact required verdict value for VTZ policy denial:

- `block`

### CTX-ID Identity State

Exact required value for missing CTX-ID treatment:

- `UNTRUSTED`

### LLM Security Refusal Sentinel

Exact sentinel value:

- `SECURITY_REFUSAL`

#### Required behavior
- When output is `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.

### Consensus System Selectors

Exact selector names referenced by contract:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Python Runtime/Tooling Constants

Exact required values:

- Python version: `3.12`
- Test runner: `pytest`
- Linter: `ruff`
- Type checker: `mypy`
- YAML dependency: `pyyaml`
- Coverage threshold: `85%`

---

## Validation Rules

### 1. Entry Point Enforcement

For every entry point that processes an agent action:

1. Validate `ctx_id` first.
2. If CTX-ID validation fails, reject immediately.
3. Do not perform partial processing before successful validation.
4. Check VTZ policy before execution.
5. On denial, produce `VTZEnforcementDecision` with `verdict=block`.
6. Emit a TrustFlow event for every outcome: `allow`, `restrict`, or `block`.

### 2. TrustFlow Event Validation

A TrustFlow event is valid only if:

- `event_id` is present.
- `event_id` is globally unique.
- `event_id` is generated using CSPRNG.
- `event_id` is not sequential.
- `session_id` is present.
- `ctx_id` is present.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `event_type` is present.
- `payload_hash` is present.
- `payload_hash` equals SHA-256 of the serialized action payload.

Operational constraints:

- Emission must be synchronous in the enforcement path.
- Async buffering is not allowed.
- Failed emission must not be silently skipped.
- Failed emission must be logged and surfaced as a WARN-level audit event.

### 3. CTX-ID Validation

A CTX-ID is valid only if:

- It is present; otherwise treat as `UNTRUSTED`.
- It is not expired.
- It validates against TrustLock public key.
- Validation is not software-only.
- It has not been invalidated by rotation.

Additional lifecycle rules:

- Tokens are immutable once issued.
- Rotation creates a new token.
- Old token becomes invalid immediately.
- Clock skew tolerance is deployment-defined.

### 4. VTZ Enforcement

A VTZ binding is valid only if:

- Each agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls have explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

### 5. Consensus Request Validation

A consensus request is valid only if:

- `task` is present.
- `context` is present.
- `language` is present.
- `language` is exactly one of:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`

Selection behavior:

- `swift` => `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `python` => `GENERATION_SYSTEM`

### 6. Fix Loop Validation

Valid fix loop behavior requires:

- Use `_choose_strategy(failure_type, attempt, records)`.
- Do not use a static lookup table.
- Use `_score_fix()` for arbitration.
- Do not choose winner by response length.

Forbidden example from source:

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

### 7. Security Validation

The subsystem must enforce all of the following:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log; never retry to bypass.

### 8. Python Backend Validation

For Python implementations:

- Must use Python `3.12`.
- Must use type annotations on every function.
- Must use `async/await` throughout the backend.
- No blocking calls on the event loop.
- Must use dataclasses for all structured data.
- Tests must use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be at least `85%` on all new modules.
- `pyyaml` must be present in `requirements.txt`.

### 9. Forbidden Swift/Backend Patterns

Forbidden exact patterns from source:

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

Constraint details:

- Force unwrap is forbidden.
- LLM API call from Swift is forbidden.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

---

## Wire Format Examples

## Valid payloads

### Valid ConsensusRunRequest

```json
{
  "task": "Implement: Add session-bound VTZ enforcement",
  "context": "Agent action must validate ctx_id first and emit TrustFlow events.",
  "language": "python"
}
```

### Valid ConsensusRunResult

```json
{
  "final_code": "from dataclasses import dataclass\n\n@dataclass\nclass Example:\n    value: str\n"
}
```

### Valid TrustFlowEvent

```json
{
  "event_id": "0d4e7d5e-8b6c-4d43-a7ad-2a6d6f9ef001",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1710000000123,
  "event_type": "agent_action.block",
  "payload_hash": "3b7c3b9f6a8d4b0d5e8f1c2a7b9e4d6c1f0a2b3c4d5e6f708192a3b4c5d6e7f8"
}
```

### Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Valid AgentActionProcessingContext

```json
{
  "ctx_id": "ctx_abc",
  "session_id": "sess_123",
  "action_payload": {
    "tool": "write_file",
    "path": "/workspace/output.txt"
  }
}
```

### Valid CTX-ID state example

```json
{
  "ctx_id": "ctx_abc",
  "vtz_binding": "vtz_primary",
  "expired": false,
  "valid_signature": true
}
```

## Invalid payloads

### Invalid ConsensusRunRequest: missing language

```json
{
  "task": "Implement: Add session-bound VTZ enforcement",
  "context": "Agent action must validate ctx_id first and emit TrustFlow events."
}
```

Reason:
- `language` is required.

### Invalid ConsensusRunRequest: unsupported language

```json
{
  "task": "Implement feature",
  "context": "Context",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `python`, `swift`, `go`, `typescript`, `rust`.

### Invalid TrustFlowEvent: missing required fields

```json
{
  "event_id": "evt_1",
  "session_id": "sess_123",
  "event_type": "agent_action.allow"
}
```

Reason:
- Missing `ctx_id`
- Missing `ts`
- Missing `payload_hash`

### Invalid VTZEnforcementDecision: wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- For VTZ policy denial, `verdict` must be exactly `block`.

### Invalid AgentActionProcessingContext: missing ctx_id

```json
{
  "session_id": "sess_123",
  "action_payload": {
    "tool": "write_file"
  }
}
```

Reason:
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Processing must not infer identity from context.

### Invalid fix arbitration behavior

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- Length-based fix arbitration is forbidden.
- Must use `_score_fix()`.

### Invalid subprocess behavior

```python
subprocess.run(cmd, shell=True)
```

Reason:
- `shell=True` is forbidden.

### Invalid dynamic execution behavior

```python
exec(generated_code)
```

Reason:
- `eval()` / `exec()` on generated or external content is forbidden.

---

## Integration Points

### 1. Consensus Engine

Required invocation shape:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Contract requirements:

- `language` must always be passed.
- `result.final_code` is the output field consumed by ForgeAgent.

### 2. CAL Enforcement Path

ForgeAgent entry points that process agent actions must integrate:

1. CTX-ID validation
2. VTZ policy evaluation
3. `VTZEnforcementDecision` generation on denial
4. TrustFlow event emission for all outcomes

### 3. TrustFlow

ForgeAgent must emit synchronous TrustFlow events containing exactly these required fields:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

### 4. Path Security

Before any disk write, ForgeAgent must call:

- `path_security.validate_write_path()`

This validation must occur before the write.

### 5. Prompt Construction

When constructing prompts:

- Loaded document chunks must pass injection scanning before inclusion.
- Context from external documents must go in the USER prompt.
- Context from external documents must never go in the SYSTEM prompt.

### 6. Security Refusal Handling

If the LLM returns:

- `SECURITY_REFUSAL`

ForgeAgent must:

1. stop
2. gate
3. log

And must not retry to bypass.

### 7. Backend/Test Tooling

ForgeAgent Python integration must conform to:

- `pytest`
- `ruff`
- `mypy`
- `pyyaml`

Required existing test command from source:

```bash
cd src && pytest ../tests/ -v --tb=short
```

### 8. Keychain/XPC Boundary

Integration boundary constraints:

- Only Swift reads Keychain.
- Swift may read Keychain only to deliver via XPC.
- Python reads nothing from Keychain.
- Swift must not make LLM API calls directly.

---

## Non-Conformant Patterns

The following are explicitly non-conformant:

```python
winner = max(claude_fix, openai_fix, key=len)
```

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

```python
subprocess.run(cmd, shell=True)
```

```python
eval(untrusted_input)
```

```python
exec(generated_code)
```

---

## Notes on Undefined Fields

The provided TRD excerpts define required contracts and some wire fields, but do not define a complete serialized schema for:
- full CTX-ID token contents
- full VTZ policy object structure
- full action payload schema
- TrustFlow `event_type` value taxonomy
- `VTZEnforcementDecision` fields beyond `verdict`

No additional fields should be inferred as normative beyond what is specified above.