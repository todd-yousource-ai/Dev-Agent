# Interface Contracts - ForgeAgent

## Data Structures

### ConsensusRunRequest

Request payload passed to the consensus engine for code generation.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Human-readable implementation task. |
| `context` | `string` | Yes | Context string supplied to the model. External document context must be placed in the USER prompt, never the SYSTEM prompt. All loaded document chunks must pass injection scanning before inclusion. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be present. Exact allowed values only. |

#### Behavioral contract
- ForgeAgent **MUST** call consensus as:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code selected as final output. |

---

### VTZEnforcementDecision

Record produced when VTZ policy evaluates an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"allow" \| "restrict" \| "block"` | Yes | On VTZ policy denial, `verdict` **MUST** be `"block"`. |

#### Behavioral contract
- Every action must be checked against VTZ policy **before** execution.
- VTZ policy denial **MUST** produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Audit/event record emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique. Generated via CSPRNG, not sequential. |
| `session_id` | `string` | Yes | Required on every event. |
| `ctx_id` | `string` | Yes | Required on every event. Must correspond to the validated CTX-ID for the action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Required on every event. |
| `payload_hash` | `string` | Yes | SHA-256 of the serialized action payload. |

#### Behavioral contract
- Every action outcome (`allow`, `restrict`, `block`) **MUST** emit a TrustFlow event.
- Emission **MUST** be synchronous in the enforcement path.
- Async buffering is **not permitted**.
- Emission failure **MUST NOT** silently continue.
- Failed emission is a `WARN`-level audit event.

---

### CTX-ID Token

Opaque token validated before any action processing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Token value. Immutable once issued. Missing CTX-ID is treated as `UNTRUSTED`. |

#### Behavioral contract
- Every entry point that processes an agent action **MUST** call CTX-ID validation first.
- CTX-ID validation failure **MUST** result in immediate rejection with no partial processing.
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID **MUST** be rejected.
- CTX-ID **MUST** be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID **MUST** be treated as `UNTRUSTED`.
- Identity must never be inferred from surrounding context when `ctx_id` is absent.

---

### AgentActionPayload

Serialized action payload whose hash is included in TrustFlow events.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `<opaque action payload>` | `object` | Yes | Exact action schema is component-specific. Serialized form must be stable enough to compute SHA-256 for `payload_hash`. |

#### Behavioral contract
- `payload_hash` in `TrustFlowEvent` **MUST** equal SHA-256 of the serialized action payload.

---

### FixStrategySelection Inputs

Inputs used by failure-aware fix loop strategy.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `string` | Yes | Passed to `_choose_strategy(failure_type, attempt, records)`. |
| `attempt` | `integer` | Yes | Current retry/fix attempt. |
| `records` | `array` | Yes | Prior failure/fix records supplied to strategy selection. |

#### Behavioral contract
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup-table strategy selection is non-conformant.

---

### FixArbitration Inputs

Inputs used when choosing among candidate fixes.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `assertion_tokens` | `array<string>` | Yes | Tokenized assertions used for scoring overlap. |
| `candidate_fix` | `string` | Yes | Candidate fix response/code. |

#### Behavioral contract
- Fix arbitration **MUST** use `_score_fix()`.
- `_score_fix()` is based on assertion token overlap.
- Length-based arbitration is forbidden.

---

## Enums and Constants

### Language

Exact allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### VTZ Verdict

Exact allowed values for `VTZEnforcementDecision.verdict`:

- `"allow"`
- `"restrict"`
- `"block"`

### Trust Classification / CTX-ID Handling Constants

- `UNTRUSTED`

Used when CTX-ID is missing.

### Generation System Selectors

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Security Refusal Sentinel

- `SECURITY_REFUSAL`

When this output is seen from the LLM:
- stop
- gate
- log
- never retry to bypass

### Audit Severity

- `WARN`

Used for failed TrustFlow emission.

### Forbidden Patterns

#### Forbidden fix arbitration
```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

#### Forbidden Swift force unwrap
```swift
let value = optional!
```

#### Forbidden LLM API call from Swift
```swift
let client = AnthropicClient(apiKey: keychainValue)
```

#### Forbidden backend Keychain read
```swift
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
```

---

## Validation Rules

### 1. Entry-point enforcement order

Every entry point that processes an agent action must perform validation in this order:

1. CTX-ID validation first
2. Immediate rejection on CTX-ID validation failure
3. VTZ policy check before execution
4. Produce `VTZEnforcementDecision` on denial with `verdict=block`
5. Emit `TrustFlowEvent` for every outcome

No partial processing is permitted before CTX-ID validation succeeds.

---

### 2. CTX-ID validation rules

- `ctx_id` is required for trusted processing.
- If `ctx_id` is missing, the request must be treated as `UNTRUSTED`.
- Expired CTX-ID must be rejected.
- Rotated CTX-ID invalidates prior token immediately.
- CTX-ID fields may not be modified after issuance.
- Validation must be against TrustLock public key.
- Software-only validation is invalid.

---

### 3. VTZ enforcement rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

### 4. TrustFlow emission rules

A `TrustFlowEvent` is valid only if:

- `event_id` is present
- `session_id` is present
- `ctx_id` is present
- `ts` is present
- `event_type` is present
- `payload_hash` is present
- `event_id` is globally unique
- `ts` is UTC Unix timestamp with millisecond precision
- `payload_hash` is SHA-256 of the serialized action payload

Emission rules:
- Must be synchronous in the enforcement path
- Must not use async buffering
- Failure must not be silently skipped
- Failure must be logged/surfaced as `WARN`

---

### 5. Consensus invocation rules

Consensus requests are invalid if `language` is omitted.

Valid `language` values only:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

Selection behavior:
- `"swift"` => `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `"python"` => `GENERATION_SYSTEM`

---

### 6. Fix-loop rules

- Strategy selection must call `_choose_strategy(failure_type, attempt, records)`.
- Arbitration must call `_score_fix()`.
- Choosing winner by response length is forbidden.

Invalid example:
```python
winner = max(claude_fix, openai_fix, key=len)
```

---

### 7. Security rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies; log status codes and error types only.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- External document context goes in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log, and do not retry to bypass.

---

### 8. Python implementation rules

- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Tests use `pytest`
- Tests live in `tests/` mirroring `src/`
- `ruff` must pass
- `mypy` must pass
- Test coverage must be `>= 85%` on all new modules
- `pyyaml` must be present in `requirements.txt`

---

## Wire Format Examples

### Valid: consensus run request

```json
{
  "task": "Implement: Add session-scoped VTZ enforcement",
  "context": "User prompt context only; external chunks already injection-scanned.",
  "language": "python"
}
```

### Invalid: consensus run request missing language

```json
{
  "task": "Implement: Add session-scoped VTZ enforcement",
  "context": "User prompt context only; external chunks already injection-scanned."
}
```

Reason:
- `language` is required.

---

### Invalid: consensus run request with unsupported language

```json
{
  "task": "Implement: Add session-scoped VTZ enforcement",
  "context": "User prompt context only; external chunks already injection-scanned.",
  "language": "java"
}
```

Reason:
- `language` must be one of `"python" | "swift" | "go" | "typescript" | "rust"`.

---

### Valid: TrustFlow event

```json
{
  "event_id": "2b2d5ce4-7d5f-4f41-bb2a-2ce6c4d82411",
  "session_id": "sess_01HV7Y7K9J6P2V4M7Q8R",
  "ctx_id": "ctx_01HV7Y7M2Y3N8P1Q5R6S",
  "ts": 1712345678123,
  "event_type": "agent_action_allow",
  "payload_hash": "6f8c2e8d2c1f6a4f74f9d9c6f8f0b2f2c33f0af3e8ed7db0b6d1f39d6f0b9a10"
}
```

---

### Invalid: TrustFlow event missing required fields

```json
{
  "event_id": "2b2d5ce4-7d5f-4f41-bb2a-2ce6c4d82411",
  "session_id": "sess_01HV7Y7K9J6P2V4M7Q8R",
  "event_type": "agent_action_allow"
}
```

Reason:
- Missing `ctx_id`
- Missing `ts`
- Missing `payload_hash`

---

### Valid: VTZ enforcement decision on denial

```json
{
  "verdict": "block"
}
```

---

### Invalid: VTZ enforcement decision with unsupported verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- `verdict` must be one of `"allow" | "restrict" | "block"`.

---

### Invalid: forbidden fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- Length-based arbitration is forbidden.
- Must use `_score_fix()`.

---

### Invalid: forbidden Swift force unwrap

```swift
let value = optional!
```

Reason:
- Force unwrap is forbidden.

---

### Invalid: forbidden Swift backend credential access

```swift
let token = KeychainKit.read("github_token")
```

Reason:
- Python backend reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

---

## Integration Points

### Consensus Engine

ForgeAgent integrates with a consensus engine through:

- `await self._consensus.run(task=..., context=..., language=...)`

Required request fields:
- `task`
- `context`
- `language`

Required result field:
- `final_code`

Behavioral integration requirements:
- Always pass `language`
- Use exact language values
- Read generated code from `result.final_code`

---

### CAL Enforcement Path

ForgeAgent entry points that process agent actions must integrate with CAL enforcement such that:

- CTX-ID validation happens first
- VTZ policy evaluation happens before execution
- A `VTZEnforcementDecision` is produced on denial
- A `TrustFlowEvent` is emitted for every action outcome

This is mandatory for conformance.

---

### TrustLock

CTX-ID validation must integrate with TrustLock public key validation.

Requirements:
- Validation against TrustLock public key is mandatory
- Software-only validation is rejected

---

### Path Security

Any file write path must be validated through:

- `path_security.validate_write_path()`

This validation must occur before any write.

---

### Prompt Construction / Injection Scanning

When external documents are loaded into prompt context:

- all document chunks must pass injection scanning first
- scanned external content must go into the USER prompt
- external content must never be placed in the SYSTEM prompt

---

### Logging / Security Handling

On LLM output equal to or containing `SECURITY_REFUSAL`:

- stop
- gate
- log
- do not retry to bypass

For HTTP failures:
- log status codes and error types only
- do not log response bodies

---

### Test and Build Tooling

ForgeAgent implementations must align with:

- `pytest`
- `ruff`
- `mypy`
- `pyyaml` in `requirements.txt`

Pre-change execution requirement:

```bash
cd src && pytest ../tests/ -v --tb=short
```