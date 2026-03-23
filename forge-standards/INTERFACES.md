# Interface Contracts - FullPlatform

## Data Structures

This document defines the wire-format and API contract requirements surfaced for the FullPlatform subsystem from the provided TRD content.

Where the TRD specifies exact field names, values, or constraints, they are reproduced exactly.

---

### ConsensusRunRequest

Request contract for invoking the consensus engine.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Free-form task description. Example uses `f"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string passed to consensus engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. Exact allowed values are listed in **Enums and Constants**. |

#### Notes
- Caller contract: `language` must always be present.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result contract returned from the consensus engine.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Final generated code output. |

---

### VTZEnforcementDecision

Record that must be produced when VTZ policy denies an action.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | Yes | On VTZ policy denial, verdict must be exactly `block`. |

#### Notes
- TRD requires: “VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.”
- No additional fields are specified in the provided source.

---

### TrustFlowEvent

Audit/event record emitted for every action outcome.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique. Must be generated using CSPRNG, not sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | Must be SHA-256 of the serialized action payload. |

#### Notes
- Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and must not be silently skipped.

---

### CTX-ID Token

Identity token contract as constrained by the TRD.

#### Fields
The provided TRD does not enumerate internal token fields. The externally visible interface requirements are:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Must be present for trusted processing. Missing CTX-ID must be treated as `UNTRUSTED`. |

#### Behavioral Constraints
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID must be rejected.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.

---

### Agent Action Processing Input

Minimal contract implied by CAL enforcement requirements.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Must be validated first before any partial processing. |
| `session_id` | `string` | Yes | Required to emit `TrustFlowEvent`. |
| `action_payload` | `object` | Yes | Serialized payload is hashed to compute `payload_hash`. |
| `event_type` | `string` | Yes | Required to emit `TrustFlowEvent`. |

#### Behavioral Constraints
- Every entry point that processes an agent action must call CTX-ID validation first.
- CTX-ID validation failure must result in immediate rejection.
- Every action must be checked against VTZ policy before execution.

---

## Enums and Constants

### SupportedLanguage

Exact allowed values:

```text
"python" | "swift" | "go" | "typescript" | "rust"
```

### Consensus System Selection Rules

| Condition | System Selected |
|---|---|
| `language="swift"` | `SWIFT_GENERATION_SYSTEM` |
| `language="swift"` and UI keywords detected | `SWIFT_GENERATION_SYSTEM` + `SWIFT_UI_ADDENDUM` |
| `language="python"` | `GENERATION_SYSTEM` |

---

### ActionOutcome

Exact outcome values named by the TRD:

```text
allow
restrict
block
```

These values are used as action outcomes that require TrustFlow emission.

---

### VTZ Verdict

Exact denial verdict required by the TRD:

```text
block
```

---

### Trust Classification

Exact value named by the TRD for missing CTX-ID:

```text
UNTRUSTED
```

---

### Security Sentinel Output

Exact sentinel value named by the TRD:

```text
SECURITY_REFUSAL
```

When this output is encountered:
- stop
- gate
- log
- never retry to bypass

---

### Logging Severity Requirement

Exact audit level named by the TRD for failed TrustFlow emission:

```text
WARN
```

---

## Validation Rules

## 1. Consensus Engine Usage

### Required Invocation Shape

The contract requires this shape:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### Validation Rules
- `language` is mandatory.
- `language` must be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`
- Consumers must read generated output from `result.final_code`.

### Prohibited Behavior
- Do not omit `language`.
- Do not use length-based fix arbitration.

Forbidden example from TRD:

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

Required behavior:
- Fix loop strategy uses `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration uses `_score_fix()`.

---

## 2. CAL Enforcement Contract

For every entry point that processes an agent action:

1. CTX-ID validation must occur first.
2. If CTX-ID validation fails, reject immediately.
3. No partial processing is allowed before validation.
4. VTZ policy check must occur before execution.
5. If VTZ denies the action:
   - produce `VTZEnforcementDecision`
   - set `verdict=block`
6. Every action outcome must emit a `TrustFlowEvent`.
7. If TrustFlow emission fails:
   - do not silently continue
   - log and surface the failure

---

## 3. TrustFlow Event Validation

### Required Fields
A valid `TrustFlowEvent` must include exactly these required interface fields:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

### Field Constraints
- `event_id` must be globally unique.
- `event_id` must be CSPRNG-generated.
- `event_id` must not be sequential.
- `ts` must be a UTC Unix timestamp with millisecond precision.
- `payload_hash` must be SHA-256 of the serialized action payload.

### Emission Constraints
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission must be treated as a WARN-level audit event.

---

## 4. CTX-ID Validation Rules

- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID must be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from surrounding context when `ctx_id` is missing.

---

## 5. VTZ Enforcement Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 6. Security Rules

### Hard Prohibitions
- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on any generated or external content.
- Never log HTTP response bodies.
- Never retry to bypass `SECURITY_REFUSAL`.

### Required Controls
- Log status codes and error types only for HTTP failures.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

---

## 7. Python Backend Rules

- Python version: `3.12`
- Type annotations required on every function.
- `async/await` throughout the backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- Tests use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass.
- `mypy` must pass.
- Test coverage must be `>= 85%` on all new modules.
- `pyyaml` must be present in `requirements.txt`.

---

## Wire Format Examples

## 1. Valid Consensus Run Request

```json
{
  "task": "Implement: Add TrustFlow emitter",
  "context": "Need backend implementation for audit emission",
  "language": "python"
}
```

Why valid:
- Includes `task`
- Includes `context`
- Includes `language`
- `language` is one of the exact allowed values

---

## 2. Invalid Consensus Run Request: Missing language

```json
{
  "task": "Implement: Add TrustFlow emitter",
  "context": "Need backend implementation for audit emission"
}
```

Why invalid:
- `language` is mandatory

---

## 3. Invalid Consensus Run Request: Unsupported language

```json
{
  "task": "Implement: Add TrustFlow emitter",
  "context": "Need backend implementation for audit emission",
  "language": "java"
}
```

Why invalid:
- `language` must be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

---

## 4. Valid Consensus Run Result

```json
{
  "final_code": "print('hello')"
}
```

Why valid:
- Contains required `final_code` field

---

## 5. Valid TrustFlow Event

```json
{
  "event_id": "8f5d5bc6d7f54c5f9df6f2b5b8d9b7a1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "3a7bd3e2360a3d80b3c3f0b8a1f1d87a6d9a3f54b7e5c2d1f0a9e8b7c6d5a4f3"
}
```

Why valid:
- Includes all required TrustFlow fields
- `ts` is millisecond Unix timestamp
- `payload_hash` is represented as SHA-256 hex

---

## 6. Invalid TrustFlow Event: Missing required field

```json
{
  "event_id": "8f5d5bc6d7f54c5f9df6f2b5b8d9b7a1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "payload_hash": "3a7bd3e2360a3d80b3c3f0b8a1f1d87a6d9a3f54b7e5c2d1f0a9e8b7c6d5a4f3"
}
```

Why invalid:
- Missing `event_type`

---

## 7. Valid VTZ Enforcement Decision

```json
{
  "verdict": "block"
}
```

Why valid:
- On VTZ denial, `verdict` must be exactly `block`

---

## 8. Invalid VTZ Enforcement Decision

```json
{
  "verdict": "deny"
}
```

Why invalid:
- TRD requires exact value `block`

---

## 9. Invalid Agent Action Input: Missing CTX-ID

```json
{
  "session_id": "sess_123",
  "action_payload": {
    "tool": "read_file"
  },
  "event_type": "action.allow"
}
```

Why invalid:
- Missing `ctx_id`
- Missing CTX-ID must be treated as `UNTRUSTED`
- Identity must not be inferred from context

---

## Integration Points

## Consensus Engine

### Input Contract
- Method shape:
  - `await self._consensus.run(task=..., context=..., language=...)`
- Required arguments:
  - `task`
  - `context`
  - `language`

### Output Contract
- Read generated code from:
  - `result.final_code`

### Strategy Integration
- Failure handling strategy must use:
  - `_choose_strategy(failure_type, attempt, records)`
- Fix arbitration must use:
  - `_score_fix()`

### Forbidden
- Length-based winner selection is non-conformant.

---

## TrustFlow

### Producer Requirements
Any enforcement-path component producing action decisions must synchronously emit a `TrustFlowEvent`.

### Required Event Fields
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

### Failure Behavior
- Failure must be logged
- Failure must be surfaced
- Failure must not be silently ignored
- Audit severity is `WARN`

---

## CTX-ID / TrustLock

### Validation Integration
- CTX-ID must be validated before action processing.
- Validation must use TrustLock public key.
- Software-only validation is rejected.

### Rotation Integration
- Token rotation issues a new CTX-ID.
- Old token is invalid immediately.
- Policy changes apply on next CTX-ID issuance.

---

## VTZ Policy Engine

### Enforcement Integration
- Action must be checked against VTZ policy before execution.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.

### Denial Output
- Must produce `VTZEnforcementDecision` with:
  - `verdict: "block"`

---

## File Path Security

Before any disk write, integration must call:

```text
path_security.validate_write_path()
```

This validation is mandatory for all file paths written to disk.

---

## Prompt Construction / Injection Scanning

### External Document Handling
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- External document context must be placed in the USER prompt.
- External document context must never be placed in the SYSTEM prompt.

---

## HTTP Logging

### Error Logging Contract
- Log HTTP status codes and error types only.
- Do not log HTTP response bodies.

---

## Swift / Backend Boundary

The provided TRD includes explicit forbidden integration patterns:

### Forbidden Swift Patterns

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

### Required Boundary Rule
- Only Swift reads Keychain, only to deliver via XPC.
- Python backend reads nothing from Keychain.

---

## Test and Compliance Integration

Before code changes, agents must run:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Additional compliance requirements:
- `pytest` test suite
- `ruff`
- `mypy`
- coverage `>= 85%` on new modules

---

## Non-Conformance

A FullPlatform component is non-conformant if it violates any of the Forge Component Interface Contracts listed above, including:
- missing CTX-ID-first validation
- missing VTZ pre-execution check
- missing `VTZEnforcementDecision` with `verdict=block` on denial
- missing required TrustFlow fields
- non-synchronous TrustFlow emission in enforcement path
- software-only CTX-ID validation
- inferred identity when CTX-ID is missing