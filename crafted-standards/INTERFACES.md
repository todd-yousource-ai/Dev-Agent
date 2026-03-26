# Interface Contracts - CraftedAgent

## Data Structures

### ConsensusRunRequest
Request passed to the consensus engine for code generation.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Human-readable task description. Example pattern: `"Implement: {spec.title}"`. |
| `context` | `string` | yes | Context string supplied to the engine. External document context, if any, must be placed in the USER prompt, never the SYSTEM prompt. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | yes | Must always be passed. Exact allowed values only. |

### ConsensusRunResult
Result returned by the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Generated code output selected by consensus flow. |

---

### TrustFlowEvent
Mandatory audit event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | Globally unique. Must be generated with CSPRNG; must not be sequential. |
| `session_id` | `string` | yes | Session identifier for the agent session. |
| `ctx_id` | `string` | yes | CTX-ID token identifier/value associated with the session. |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | yes | Event type name for the emitted TrustFlow event. |
| `payload_hash` | `string` | yes | SHA-256 of the serialized action payload. Lower/upper hex format not otherwise specified; must represent SHA-256 exactly. |

#### Behavioral requirements
- Emission is required for every action outcome: `allow`, `restrict`, `block`.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission must be treated as a WARN-level audit event.
- Failed emission must not be silently skipped.
- TrustFlow emission failure must be logged and surfaced.

---

### VTZEnforcementDecision
Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | On VTZ policy denial, value must be exactly `block`. |

#### Behavioral requirements
- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### CTXIDToken
Logical token contract for CTX-ID.

Field-level schema is not defined in the provided TRD excerpts. The following interface constraints are mandatory:

| Property | Type | Required | Constraints |
|---|---|---:|---|
| `token` | `string` | implied | Must be validated before any agent action processing. |
| `immutable` | `boolean` | implied | CTX-ID tokens are immutable once issued; no field modification after issuance. |
| `expired` | `boolean` | implied | If expired, token must be rejected. |
| `validated_with_trustlock_public_key` | `boolean` | implied | Validation must be against TrustLock public key. Software-only validation is rejected. |

#### Behavioral requirements
- Every entry point that processes an agent action must call CTX-ID validation first.
- CTX-ID validation failure must result in immediate rejection.
- No partial processing is permitted on validation failure.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from surrounding context when CTX-ID is missing.
- Rotation creates a new token and invalidates the old token immediately.
- Clock skew tolerance is deployment-defined and not specified here.

---

### AgentActionPayload
Serialized payload of an agent action used for hashing and enforcement.

Field schema is not defined in the provided TRD excerpts.

#### Behavioral requirements
- Must be serialized deterministically enough to compute `payload_hash`.
- `payload_hash` must be the SHA-256 of the serialized action payload.
- Every action must undergo:
  1. CTX-ID validation first
  2. VTZ policy check before execution
  3. TrustFlow emission for outcome

---

### AgentSessionBinding
Session-to-VTZ binding contract.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | yes | Identifies an agent session. |
| `vtz_id` | `string` | yes | Each session must be bound to exactly one VTZ at CTX-ID issuance. |
| `ctx_id` | `string` | yes | CTX-ID associated with the binding. |

#### Behavioral requirements
- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

## Enums and Constants

### Language
Exact allowed values for `ConsensusRunRequest.language`:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

### Enforcement Verdict
Known exact value from the contract:

- `block`

### Action Outcome
Required outcomes that must emit TrustFlow events:

- `allow`
- `restrict`
- `block`

### Trust Classification
Exact required classification for missing CTX-ID:

- `UNTRUSTED`

### Security Refusal Sentinel
Exact sentinel string:

- `SECURITY_REFUSAL`

#### Required handling
- When `SECURITY_REFUSAL` is produced by the LLM: stop, gate, log.
- Never retry to bypass.

### System Selection Constants
Named generation systems selected by language:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

#### Selection rules
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

## Validation Rules

### 1. Entry-Point Enforcement Order
For every entry point that processes an agent action:

1. Validate CTX-ID first.
2. If CTX-ID validation fails, reject immediately.
3. Do not partially process the action.
4. Check action against VTZ policy before execution.
5. If denied, produce `VTZEnforcementDecision` with `verdict=block`.
6. Emit a synchronous TrustFlow event for the outcome.
7. If TrustFlow emission fails, log and surface the failure; do not silently continue.

### 2. Consensus Engine Invocation
The consensus engine contract is:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

Validation requirements:
- `language` must always be passed.
- Omission of `language` is non-conformant.
- `result.final_code` is the generated code output field to consume.

### 3. Fix Strategy and Arbitration
Behavioral contract:

- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Length-based arbitration is forbidden.

Forbidden pattern:

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

### 4. Security Rules
These are hard requirements for CraftedAgent implementations:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log; never retry to bypass.

### 5. Python Backend Contract
When implementing CraftedAgent backend code in Python:

- Python version: `3.12`
- Type annotations are required on every function.
- Use `async/await` throughout the backend.
- No blocking calls on the event loop.
- Use dataclasses for all structured data.
- Tests must use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be `>= 85%` on all new modules.
- `pyyaml` must be present in `requirements.txt`.

### 6. Swift-Specific Forbidden Patterns
Forbidden exactly as specified:

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

Additional rule:
- Only Swift reads Keychain, only to deliver via XPC.
- Backend Python reads nothing from Keychain.

## Wire Format Examples

### Valid: ConsensusRunRequest

```json
{
  "task": "Implement: Add login endpoint",
  "context": "Use async backend patterns and validate write paths before disk writes.",
  "language": "python"
}
```

### Valid: ConsensusRunResult

```json
{
  "final_code": "from dataclasses import dataclass\n\n@dataclass\nclass Example:\n    value: str\n"
}
```

### Valid: TrustFlowEvent

```json
{
  "event_id": "3f8c8a71-6dc0-4f44-a5cc-9c0b6e6f5d6f",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678901,
  "event_type": "agent_action.block",
  "payload_hash": "4d967a5a6f1d2b3c4e5f67890123456789abcdef0123456789abcdef01234567"
}
```

### Valid: VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Valid: AgentSessionBinding

```json
{
  "session_id": "sess_123",
  "vtz_id": "vtz_primary",
  "ctx_id": "ctx_abc"
}
```

### Invalid: Missing language in consensus request

```json
{
  "task": "Implement: Add login endpoint",
  "context": "Use async backend patterns."
}
```

Reason:
- `language` is required and must always be passed.

### Invalid: Unsupported language

```json
{
  "task": "Implement: Add login endpoint",
  "context": "Use async backend patterns.",
  "language": "java"
}
```

Reason:
- `language` must be one of: `python`, `swift`, `go`, `typescript`, `rust`.

### Invalid: TrustFlowEvent missing required field

```json
{
  "event_id": "evt_1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678901,
  "event_type": "agent_action.allow"
}
```

Reason:
- `payload_hash` is required.

### Invalid: VTZ denial record with wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- On VTZ policy denial, `verdict` must be exactly `block`.

### Invalid: Sequential TrustFlow event identifier

```json
{
  "event_id": "10042",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678901,
  "event_type": "agent_action.restrict",
  "payload_hash": "4d967a5a6f1d2b3c4e5f67890123456789abcdef0123456789abcdef01234567"
}
```

Reason:
- `event_id` must be globally unique and generated with CSPRNG, not sequential.

## Integration Points

### Consensus Engine
CraftedAgent must integrate with the consensus engine using:

- Method: `self._consensus.run(...)`
- Required inputs:
  - `task: string`
  - `context: string`
  - `language: "python" | "swift" | "go" | "typescript" | "rust"`
- Required output:
  - `final_code: string`

Language routing rules:
- `swift` -> `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `python` -> `GENERATION_SYSTEM`

### CTX-ID Validation
All agent-action entry points integrate with CTX-ID validation.

Required properties:
- Validation must run first.
- Validation must use TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID yields `UNTRUSTED`.
- Expired CTX-ID must be rejected.
- Rotation invalidates the previous token immediately.

### VTZ Policy Enforcement
All agent actions integrate with VTZ policy enforcement.

Required properties:
- Action must be checked before execution.
- Session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- VTZ boundaries cannot be bypassed by application code.
- Policy changes apply only at next CTX-ID issuance.

### TrustFlow Audit Emission
All enforcement outcomes integrate with TrustFlow emission.

Required properties:
- Emit on `allow`, `restrict`, and `block`.
- Include exactly:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- Emission must be synchronous in the enforcement path.
- Failures are WARN-level audit events and must be surfaced.

### Path Security
Before any disk write:

- Call `path_security.validate_write_path()`.

### Prompt Assembly / External Content
When external documents are used:

- Scan all loaded document chunks for injection before inclusion in any LLM prompt.
- Put external document context in the USER prompt only.
- Never place external document context in the SYSTEM prompt.

### LLM Refusal Handling
When model output equals or contains `SECURITY_REFUSAL`:

- Stop.
- Gate.
- Log.
- Do not retry to bypass.