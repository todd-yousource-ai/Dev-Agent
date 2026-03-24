# Interface Contracts - ForgeAgent

## Data Structures

This document defines the wire-format and API contract requirements for the ForgeAgent subsystem based on the provided TRD interface standards.

Where source material does not define an explicit object shape, this document records the exact required fields, values, and behavioral constraints only.

---

### ConsensusRunRequest

Request shape for invoking the consensus engine from ForgeAgent.

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
| `task` | `string` | Yes | Freeform task description. Example source usage: `f"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string supplied to the consensus engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. Values must match exactly. |

#### Behavioral requirements

- ForgeAgent MUST always pass `language` when invoking the consensus engine.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.
- Fix loop strategy selection MUST use `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()`.
- Length-based fix arbitration is forbidden.

---

### ConsensusRunResult

Result shape returned by the consensus engine as consumed by ForgeAgent.

```ts
interface ConsensusRunResult {
  final_code: string
}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output returned by consensus execution. |

---

### VTZEnforcementDecision

Record that MUST be produced on VTZ policy denial.

```ts
interface VTZEnforcementDecision {
  verdict: "block"
}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | Yes | On VTZ policy denial, value MUST be exactly `"block"`. |

#### Behavioral requirements

- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Required event shape for TrustFlow emission in the enforcement path.

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
| `event_id` | `string` | Yes | MUST be globally unique. MUST be generated using CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action/event. |
| `ts` | `number` | Yes | MUST be a UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Behavioral requirements

- Every TrustFlow event MUST include all fields listed above.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission MUST NOT silently continue; failure must be logged and surfaced.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### CTX-ID Token

The source defines validation and lifecycle constraints for CTX-ID but does not define additional token fields beyond identifier usage.

```ts
interface CtxIdReference {
  ctx_id: string
}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. Missing CTX-ID MUST be treated as `UNTRUSTED`. |

#### Behavioral requirements

- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted after CTX-ID validation failure.
- CTX-ID tokens are immutable once issued.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from surrounding context when CTX-ID is missing.

---

### AgentActionPayload

The source requires serialized action payload hashing but does not define a canonical payload schema.

```ts
type AgentActionPayload = unknown
```

#### Constraints

- A serialized form of the action payload MUST exist.
- `payload_hash` in `TrustFlowEvent` MUST equal the SHA-256 of the serialized action payload.
- Every entry point processing an agent action is subject to CTX-ID and VTZ enforcement before execution.

---

## Enums and Constants

### Language

Exact allowed values for consensus engine invocation:

```ts
type Language = "python" | "swift" | "go" | "typescript" | "rust"
```

### VTZ Verdict

Exact required denial verdict value:

```ts
type VTZVerdict = "block"
```

### Action Outcome

TrustFlow emission is required for all of the following outcomes:

```ts
type ActionOutcome = "allow" | "restrict" | "block"
```

### CTX-ID Missing State

Exact required treatment for absent CTX-ID:

```ts
type TrustState = "UNTRUSTED"
```

### Generator System Selection Constants

These identifiers are selected by language and must match exactly as named in source text:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Internal Strategy Functions

These function identifiers are part of the required implementation contract and must match exactly:

- `_choose_strategy(failure_type, attempt, records)`
- `_score_fix()`

### Forbidden Pattern

The following arbitration pattern is explicitly forbidden:

```python
winner = max(claude_fix, openai_fix, key=len)
```

---

## Validation Rules

## 1. Entry-point enforcement

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur first.
2. If CTX-ID validation fails, the request/action MUST be rejected immediately.
3. No partial processing is permitted before or after a CTX-ID validation failure.
4. VTZ policy MUST be evaluated before execution.
5. If VTZ denies the action, a `VTZEnforcementDecision` with `verdict: "block"` MUST be produced.
6. Every outcome (`allow`, `restrict`, `block`) MUST emit a `TrustFlowEvent`.
7. TrustFlow emission failure MUST be logged and surfaced.
8. TrustFlow emission failure MUST NOT silently continue.

---

## 2. TrustFlow event validation

A valid `TrustFlowEvent` MUST satisfy all of the following:

- `event_id` present
- `session_id` present
- `ctx_id` present
- `ts` present
- `event_type` present
- `payload_hash` present
- `event_id` globally unique
- `event_id` generated via CSPRNG
- `event_id` not sequential
- `ts` encoded as UTC Unix timestamp with millisecond precision
- `payload_hash` equals SHA-256 of the serialized action payload
- emission occurs synchronously in the enforcement path
- async buffering is not used

---

## 3. CTX-ID validation rules

A CTX-ID is valid only if all applicable checks pass:

- token is present unless explicitly treated as missing/`UNTRUSTED`
- token is not expired
- token has not been invalidated by rotation
- token validation is performed against TrustLock public key
- validation is not software-only

Additional rules:

- CTX-ID fields MUST NOT be modified after issuance
- rotation MUST create a new token
- rotation MUST immediately invalidate the old token
- expired CTX-ID MUST be rejected

---

## 4. VTZ enforcement rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 5. Consensus invocation rules

A valid consensus engine call from ForgeAgent MUST satisfy:

- `task` is present and is a string
- `context` is present and is a string
- `language` is present
- `language` is one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

Additional rules:

- `language` MUST always be passed.
- For Swift generation, system selection uses `SWIFT_GENERATION_SYSTEM` and optionally `SWIFT_UI_ADDENDUM`.
- For Python generation, system selection uses `GENERATION_SYSTEM`.

---

## 6. Security and content-handling rules

These requirements apply to ForgeAgent implementations:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL` output from the LLM: stop, gate, log. Never retry to bypass.

---

## 7. Python implementation rules

When ForgeAgent is implemented in Python:

- Python version MUST be 3.12.
- Every function MUST have type annotations.
- Backend code MUST use `async/await` throughout.
- Blocking calls on the event loop are not permitted.
- Structured data MUST use dataclasses.
- Tests MUST use `pytest`.
- Tests MUST live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage on all new modules MUST be at least 85%.
- `pyyaml` MUST be present in `requirements.txt`.

---

## 8. Swift-specific prohibitions

The following are forbidden:

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

Additional constraint:

- Only Swift reads Keychain, only to deliver via XPC.
- Python reads nothing from Keychain.
- LLM API calls from Swift are forbidden.

---

## Wire Format Examples

## Valid payloads

### Valid ConsensusRunRequest

```json
{
  "task": "Implement: Add session enforcement",
  "context": "Relevant code paths and constraints",
  "language": "python"
}
```

### Valid ConsensusRunResult

```json
{
  "final_code": "from dataclasses import dataclass\n"
}
```

### Valid TrustFlowEvent

```json
{
  "event_id": "5d6a3d5e-93e1-4d34-bf4d-0d8b4ad7d7c2",
  "session_id": "sess_01HZXA7K8V4G9M2P1Q",
  "ctx_id": "ctx_01HZXA7M0X8M4T2B7R",
  "ts": 1717171717123,
  "event_type": "block",
  "payload_hash": "7f5c3b8d1f0e4c2a6b9d8e7f1234567890abcdef1234567890abcdef12345678"
}
```

### Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Valid CTX-ID reference

```json
{
  "ctx_id": "ctx_01HZXA7M0X8M4T2B7R"
}
```

---

## Invalid payloads

### Invalid ConsensusRunRequest: missing language

```json
{
  "task": "Implement: Add session enforcement",
  "context": "Relevant code paths and constraints"
}
```

Reason:
- `language` is required.
- ForgeAgent must always pass `language`.

### Invalid ConsensusRunRequest: unsupported language

```json
{
  "task": "Implement: Add session enforcement",
  "context": "Relevant code paths and constraints",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid TrustFlowEvent: missing required fields

```json
{
  "event_id": "123",
  "session_id": "sess_1"
}
```

Reason:
- Missing `ctx_id`
- Missing `ts`
- Missing `event_type`
- Missing `payload_hash`

### Invalid VTZEnforcementDecision: wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- On VTZ denial, `verdict` must be exactly `"block"`.

### Invalid CTX-ID usage: absent token treated as trusted

```json
{}
```

Reason:
- Missing CTX-ID must be treated as `UNTRUSTED`, never as authenticated or inferred identity.

### Invalid fix arbitration pattern

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- Length-based fix arbitration is forbidden.
- `_score_fix()` must be used.

---

## Integration Points

## Consensus Engine

ForgeAgent integrates with the consensus engine using:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### Contract

- Invocation is asynchronous.
- `language` is mandatory.
- Returned object must expose `final_code`.

---

## CAL enforcement path

ForgeAgent entry points that process agent actions MUST integrate:

1. CTX-ID validation
2. VTZ policy enforcement
3. TrustFlow emission

### Required ordering

1. Validate CTX-ID first
2. Reject immediately on failure
3. Evaluate VTZ policy before execution
4. Produce `VTZEnforcementDecision` with `verdict="block"` on denial
5. Emit `TrustFlowEvent` synchronously for every outcome

---

## TrustLock integration

CTX-ID validation MUST integrate with:

- TrustLock public key validation

### Constraints

- Software-only validation is rejected.
- Missing CTX-ID must map to `UNTRUSTED`.

---

## Path security integration

Before any disk write:

- `path_security.validate_write_path()` MUST be called.

---

## Prompt-construction integration

When using external documents:

- loaded document chunks MUST pass injection scanning before prompt inclusion
- external document context MUST be placed in the USER prompt
- external document context MUST NOT be placed in the SYSTEM prompt

---

## Logging and audit integration

### Required logging behavior

- TrustFlow emission failure: WARN-level audit event
- HTTP logging: status codes and error types only
- HTTP response bodies: never log
- `SECURITY_REFUSAL`: stop, gate, log; never retry to bypass

---

## Test and quality integration

Before changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```

### Ongoing requirements

- `pytest` test suite
- `ruff` clean
- `mypy` clean
- coverage ≥ 85% on new modules

---

## Non-conformance

A ForgeAgent component is non-conformant if it violates any required contract in this document, including but not limited to:

- missing `language` in consensus invocation
- missing CTX-ID-first validation
- partial processing after CTX-ID validation failure
- VTZ denial without `VTZEnforcementDecision { "verdict": "block" }`
- missing TrustFlow event fields
- async-buffered TrustFlow emission
- silent TrustFlow emission failure
- use of length-based fix arbitration
- failure to validate disk write paths
- inclusion of unscanned document chunks in prompts
- logging HTTP response bodies
- retrying after `SECURITY_REFUSAL`