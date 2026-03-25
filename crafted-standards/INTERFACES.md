# Interface Contracts - CraftedDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the `CraftedDevAgent` subsystem based on the provided TRD interface content.

Where the TRD defines behavioral contracts without a named transport schema, this document expresses the required structure and field constraints that implementations MUST honor.

---

### ConsensusRunRequest

Request passed to the consensus engine.

```ts
type Language = "python" | "swift" | "go" | "typescript" | "rust"

interface ConsensusRunRequest {
  task: string
  context: string
  language: Language
}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Human-readable implementation task. Example source usage: `f"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string supplied to the consensus engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | MUST always be passed. Values exactly as listed. |

#### Behavioral requirements

- `language` MUST always be present.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result returned by the consensus engine.

```ts
interface ConsensusRunResult {
  final_code: string
}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code returned by the consensus engine. |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

```ts
interface VTZEnforcementDecision {
  verdict: "block"
}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | Yes | MUST be `"block"` for VTZ policy denial records. |

#### Behavioral requirements

- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Event emitted for every action outcome.

```ts
interface TrustFlowEvent {
  event_id: string
  session_id: string
  ctx_id: string
  ts: number
  event_type: string
  payload_hash: string
}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique. MUST be generated via CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the event. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Behavioral requirements

- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is NOT permitted.
- Failed emission MUST be logged as a WARN-level audit event.
- Failed emission MUST NOT be silently skipped.

---

### CTX-ID Token

Immutable trust/context token used for action processing.

```ts
interface CtxIdToken {
  ctx_id: string
}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Token identifier. Must be validated before any agent action processing. |

#### Behavioral requirements

- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
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

### AgentActionEnvelope

Normalized action-processing envelope implied by CAL, VTZ, and TrustFlow requirements.

```ts
interface AgentActionEnvelope {
  session_id: string
  ctx_id?: string
  action_payload: string
}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | Yes | Session identifier for enforcement and TrustFlow emission. |
| `ctx_id` | `string` | No | If absent, request MUST be treated as `UNTRUSTED`. |
| `action_payload` | `string` | Yes | Serialized action payload used to compute `payload_hash` as SHA-256. |

#### Behavioral requirements

- `payload_hash` in TrustFlow MUST be computed from the serialized `action_payload`.
- Processing order is fixed:
  1. CTX-ID validation
  2. VTZ policy check
  3. Action execution decision
  4. TrustFlow emission

---

## Enums and Constants

### Language

Exact allowed values:

```ts
type Language = "python" | "swift" | "go" | "typescript" | "rust"
```

### EnforcementVerdict

Only explicitly defined value in provided TRD content:

```ts
type EnforcementVerdict = "block"
```

### ActionOutcome

TrustFlow emission is required for these outcomes:

```ts
type ActionOutcome = "allow" | "restrict" | "block"
```

### Special Classification Values

```ts
type TrustClassification = "UNTRUSTED"
type SecurityRefusalSignal = "SECURITY_REFUSAL"
```

### Consensus/Generation Constants

These identifiers are selected by language and MUST be used exactly as named:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Internal Selection Functions

These are behavioral API names referenced by contract:

- `_choose_strategy(failure_type, attempt, records)`
- `_score_fix()`

### Forbidden Implementation Pattern

Length-based arbitration is forbidden:

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

---

## Validation Rules

## 1. Entry-point enforcement

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur first.
2. On CTX-ID validation failure, processing MUST immediately reject the action.
3. No partial processing is permitted before or after rejection.
4. VTZ policy check MUST occur before execution.
5. VTZ denial MUST create `VTZEnforcementDecision { verdict: "block" }`.
6. Every resulting outcome MUST emit a `TrustFlowEvent`.

---

## 2. TrustFlow validation

A valid `TrustFlowEvent` MUST satisfy all of the following:

- `event_id` present and globally unique
- `event_id` generated by CSPRNG
- `event_id` not sequential
- `session_id` present
- `ctx_id` present
- `ts` present
- `ts` is UTC Unix timestamp with millisecond precision
- `event_type` present
- `payload_hash` present
- `payload_hash` is SHA-256 of serialized action payload

Operational constraints:

- emission is synchronous in the enforcement path
- async buffering is not permitted
- emission failure is WARN-level audit event
- emission failure must be surfaced, not silently ignored

---

## 3. CTX-ID validation

A CTX-ID is valid only if:

- it is present, unless the request is intentionally classified as `UNTRUSTED`
- it is not expired
- it validates against TrustLock public key
- it has not been invalidated by rotation

Additional constraints:

- CTX-ID is immutable once issued
- rotation creates a new token
- old token becomes invalid immediately
- missing CTX-ID MUST NOT cause inferred identity

---

## 4. VTZ validation

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 5. Consensus engine request validation

A `ConsensusRunRequest` is valid only if:

- `task` is present
- `context` is present
- `language` is present
- `language` is one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

Additional requirements:

- Implementations MUST always pass `language`.
- Swift selection behavior:
  - `language="swift"` -> `SWIFT_GENERATION_SYSTEM`
  - optional `SWIFT_UI_ADDENDUM` injected when UI keywords detected
- Python selection behavior:
  - `language="python"` -> `GENERATION_SYSTEM`

---

## 6. Security validation requirements

These are mandatory implementation constraints for all interfaces in this subsystem.

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on any generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` output is returned by the LLM:
  - stop
  - gate
  - log
  - never retry to bypass

---

## 7. Python implementation contract

For Python implementations of this subsystem:

- Python version: `3.12`
- Type annotations required on every function
- `async/await` throughout backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Testing framework: `pytest`
- Tests live in `tests/`
- Tests mirror `src/` structure
- Linting: `ruff`
- Type checking: `mypy`
- Both `ruff` and `mypy` must pass clean
- Test coverage for all new modules: `>= 85%`
- `pyyaml` MUST be in `requirements.txt`

---

## Wire Format Examples

## Valid payloads

### Valid ConsensusRunRequest

```json
{
  "task": "Implement: Add authentication middleware",
  "context": "Existing service uses async request handlers and pytest coverage.",
  "language": "python"
}
```

### Valid ConsensusRunResult

```json
{
  "final_code": "from dataclasses import dataclass\n\n@dataclass\nclass Example:\n    value: str\n"
}
```

### Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Valid TrustFlowEvent

```json
{
  "event_id": "8ab6dd9f-6af1-4af5-b2b2-9f6d1b3d2f20",
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3f5f536595a5e34d6a23a64f6cfd2"
}
```

### Valid AgentActionEnvelope

```json
{
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "action_payload": "{\"tool\":\"build\",\"target\":\"backend\"}"
}
```

### Valid untrusted envelope

```json
{
  "session_id": "sess_123",
  "action_payload": "{\"tool\":\"inspect\"}"
}
```

Interpretation:

- missing `ctx_id` => classify as `UNTRUSTED`
- do not infer identity
- enforce rejection or restricted handling per policy

---

## Invalid payloads

### Invalid ConsensusRunRequest: missing language

```json
{
  "task": "Implement: Add authentication middleware",
  "context": "Existing service uses async request handlers and pytest coverage."
}
```

Reason:
- `language` is required
- implementations must always pass language

### Invalid ConsensusRunRequest: unsupported language

```json
{
  "task": "Implement: Add authentication middleware",
  "context": "Existing service uses async request handlers and pytest coverage.",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `"python" | "swift" | "go" | "typescript" | "rust"`

### Invalid VTZEnforcementDecision: wrong verdict

```json
{
  "verdict": "allow"
}
```

Reason:
- TRD-defined denial record requires `verdict=block`

### Invalid TrustFlowEvent: missing required fields

```json
{
  "event_id": "1",
  "session_id": "sess_123",
  "event_type": "allow"
}
```

Reason:
- missing `ctx_id`
- missing `ts`
- missing `payload_hash`
- `event_id` must be globally unique and not sequential

### Invalid TrustFlowEvent: non-millisecond timestamp

```json
{
  "event_id": "8ab6dd9f-6af1-4af5-b2b2-9f6d1b3d2f20",
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "ts": 1735689600,
  "event_type": "allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3f5f536595a5e34d6a23a64f6cfd2"
}
```

Reason:
- `ts` must be UTC Unix timestamp with millisecond precision

### Invalid agent action processing: missing CTX-ID but inferred identity

```json
{
  "session_id": "sess_123",
  "action_payload": "{\"user\":\"alice\",\"tool\":\"build\"}"
}
```

Reason:
- missing `ctx_id` must be treated as `UNTRUSTED`
- identity must never be inferred from context

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

Contract requirements:

- caller MUST pass `task`
- caller MUST pass `context`
- caller MUST pass `language`
- caller reads generated output from `result.final_code`

---

## Failure strategy selection

Fix loop strategy MUST use:

```python
_choose_strategy(failure_type, attempt, records)
```

Constraints:

- strategy is failure-type-aware
- static lookup table strategy selection is non-conformant

---

## Fix arbitration

Fix arbitration MUST use:

```python
_score_fix()
```

Constraints:

- arbitration is based on assertion token overlap
- response length MUST NOT be used

Forbidden pattern:

```python
winner = max(claude_fix, openai_fix, key=len)
```

---

## Path security

Before any file write, implementations MUST call:

```python
path_security.validate_write_path()
```

Constraint:

- no disk write is permitted before validation passes

---

## Prompt construction / LLM integration

- external document chunks MUST be injection scanned before use
- external document context MUST be placed in USER prompt
- external document context MUST NOT be placed in SYSTEM prompt
- `SECURITY_REFUSAL` output MUST terminate the flow with stop/gate/log behavior

---

## Swift-specific prohibitions

These source-level interface constraints apply to any Swift-facing integration:

```swift
let value = optional!
```

Forbidden:
- force unwrap

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Forbidden:
- LLM API call from Swift

```swift
let token = KeychainKit.read("github_token")
```

Forbidden:
- backend reading from Keychain
- only Swift reads Keychain, and only to deliver via XPC

---

## Developer workflow contract

Before modifying this subsystem:

1. Find the TRD that owns the component in `README.md`.
2. Read relevant TRD sections, especially:
   - interfaces
   - error contracts
   - security
   - testing requirements
3. Check `TRD-11` if change touches:
   - credentials
   - external content
   - generated code
   - CI
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## Conformance Summary

A `CraftedDevAgent` implementation is conformant only if it satisfies all of the following:

- uses the exact `language` enum values
- always passes `language` into consensus
- reads generated code from `final_code`
- validates CTX-ID first for every action entry point
- rejects immediately on CTX-ID validation failure
- checks VTZ before execution
- emits `VTZEnforcementDecision` with `verdict="block"` on denial
- emits synchronous `TrustFlowEvent` for every outcome
- includes all required TrustFlow fields
- computes `payload_hash` as SHA-256 of serialized action payload
- treats missing CTX-ID as `UNTRUSTED`
- never infers identity from missing CTX-ID context
- uses `_choose_strategy(failure_type, attempt, records)` for fix strategy
- uses `_score_fix()` for fix arbitration
- does not use length-based arbitration
- satisfies all listed security constraints
- satisfies Python implementation and testing constraints where applicable