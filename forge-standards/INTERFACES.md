# Interface Contracts - Crafted

## Data Structures

This document defines the Crafted subsystem wire-format and API contract references derived from the provided standards and TRD excerpts.

Where a field is mandated by contract text, it is listed as **required**.

---

### TrustFlowEvent

Required for every TrustFlow emission.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique; generated via CSPRNG; MUST NOT be sequential |
| `session_id` | `string` | yes | Present on every TrustFlow event |
| `ctx_id` | `string` | yes | Present on every TrustFlow event; MUST reference a validated CTX-ID |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Present on every TrustFlow event |
| `payload_hash` | `string` | yes | MUST be SHA-256 of the serialized action payload |

#### Notes
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be treated as a WARN-level audit event and MUST NOT be silently skipped.

---

### VTZEnforcementDecision

Produced when VTZ policy is evaluated.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | On denial, MUST be exactly `block` |

#### Notes
- A VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### ConsensusRunRequest

Request shape required when invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Example usage: `f"Implement: {spec.title}"` |
| `context` | `string` | yes | Context string passed to the consensus engine |
| `language` | `string` | yes | MUST be one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Notes
- Always pass `language`.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result shape consumed from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Final generated code output |

---

### CTXIDToken

Contract-level representation for CTX-ID handling.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Token identifier; immutable once issued |
| `vtz_id` | `string` | yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance |
| `issued_at` | `number` | yes | Timestamp at issuance |
| `expires_at` | `number` | yes | Expired CTX-ID MUST be rejected |
| `public_key_id` | `string` | yes | Validation MUST be against TrustLock public key |

#### Notes
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token; the old token is invalidated immediately.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NOT be inferred from surrounding context.

---

### AgentActionPayload

Logical action payload referenced by enforcement and hashing rules.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | yes | Session being processed |
| `ctx_id` | `string` | yes | MUST be validated first |
| `action` | `string` | yes | Action requested by the agent |
| `payload` | `object` | yes | Serialized payload used to compute `payload_hash` |

#### Notes
- Every entry point that processes an agent action MUST validate CTX-ID first.
- CTX-ID validation failure MUST result in immediate rejection with no partial processing.
- Every action MUST be checked against VTZ policy before execution.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

## Enums and Constants

### `language`

Allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

---

### Trust outcomes

Action outcomes that MUST emit a TrustFlow event:

- `allow`
- `restrict`
- `block`

---

### VTZ enforcement verdict

Required denial verdict value:

- `block`

---

### Identity / trust state constants

Required missing-identity state:

- `UNTRUSTED`

---

### System selector constants

Exact selector values referenced by contract text:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

---

## Validation Rules

## 1. CAL Enforcement Contract

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur first.
2. CTX-ID validation failure MUST cause immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. VTZ policy MUST be checked before execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue; it MUST be logged and surfaced.

---

## 2. TrustFlow Emission Contract

For every TrustFlow event:

1. `event_id` is required.
2. `session_id` is required.
3. `ctx_id` is required.
4. `ts` is required.
5. `event_type` is required.
6. `payload_hash` is required.
7. `event_id` MUST be globally unique and CSPRNG-generated.
8. `event_id` MUST NOT be sequential.
9. `ts` MUST be a UTC Unix timestamp with millisecond precision.
10. `payload_hash` MUST be the SHA-256 of the serialized action payload.
11. Emission MUST be synchronous in the enforcement path.
12. Async buffering is not permitted.
13. Failed emission is a WARN-level audit event.

---

## 3. CTX-ID Contract

1. CTX-ID tokens are immutable once issued.
2. Rotation MUST create a new token.
3. The old token MUST be invalidated immediately on rotation.
4. Expired CTX-ID MUST be rejected.
5. Validation MUST be against TrustLock public key.
6. Software-only validation is rejected.
7. Missing CTX-ID MUST be treated as `UNTRUSTED`.
8. Identity MUST NOT be inferred from context.

---

## 4. VTZ Enforcement Contract

1. Every agent session is bound to exactly one VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit cross-VTZ access is denied.
4. VTZ boundaries are structural, not advisory.
5. Enforcement cannot be bypassed by application code.
6. VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 5. Security Rules

These are mandatory interface-adjacent constraints for any implementation using these contracts:

1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Only log status codes and error types for HTTP failures.
6. All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
7. All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
8. Context from external documents goes in the USER prompt, never the SYSTEM prompt.
9. When `SECURITY_REFUSAL` output is seen from the LLM: stop, gate, log, and never retry to bypass.

---

## 6. Python Backend Requirements

1. Python version MUST be 3.12.
2. All functions MUST have type annotations.
3. Backend code MUST use `async/await` throughout.
4. No blocking calls on the event loop.
5. Dataclasses MUST be used for all structured data.
6. Tests MUST use `pytest`.
7. Tests MUST live in `tests/` and mirror `src/` structure.
8. `ruff` MUST pass clean.
9. `mypy` MUST pass clean.
10. Test coverage MUST be at least 85% on all new modules.
11. `pyyaml` MUST be present in `requirements.txt`.

---

## 7. Forbidden Patterns

These values and patterns are explicitly non-conformant.

### Invalid fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- Length-based fix arbitration is forbidden.
- Use `_score_fix()`.

### Invalid Swift force unwrap

```swift
let value = optional!
```

Reason:
- Force unwrap is forbidden.

### Invalid Swift-side backend LLM API call

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Reason:
- LLM API calls from Swift are forbidden.

### Invalid backend Keychain read

```swift
let token = KeychainKit.read("github_token")
```

Reason:
- Python reads nothing from Keychain.
- Only Swift reads Keychain, and only to deliver via XPC.

---

## Wire Format Examples

## Valid payload: TrustFlowEvent

```json
{
  "event_id": "b6e4aa0d-8a40-4f0b-a4a6-2d4ac7dcb8f1",
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "ts": 1712345678.123,
  "event_type": "block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa1b8f2e542d1d7a7f58b0e4a6a6d3c"
}
```

## Invalid payload: TrustFlowEvent missing required field

```json
{
  "event_id": "b6e4aa0d-8a40-4f0b-a4a6-2d4ac7dcb8f1",
  "session_id": "sess_123",
  "ts": 1712345678.123,
  "event_type": "block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa1b8f2e542d1d7a7f58b0e4a6a6d3c"
}
```

Invalid because:
- `ctx_id` is required.

---

## Valid payload: ConsensusRunRequest

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context",
  "language": "python"
}
```

## Invalid payload: ConsensusRunRequest invalid enum

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context",
  "language": "java"
}
```

Invalid because:
- `language` MUST be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

---

## Valid payload: VTZEnforcementDecision on denial

```json
{
  "verdict": "block"
}
```

## Invalid payload: VTZEnforcementDecision wrong denial verdict

```json
{
  "verdict": "deny"
}
```

Invalid because:
- On VTZ policy denial, `verdict` MUST be exactly `block`.

---

## Valid payload: AgentActionPayload

```json
{
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "action": "tool.invoke",
  "payload": {
    "tool": "example_tool",
    "arguments": {
      "id": "42"
    }
  }
}
```

## Invalid payload: AgentActionPayload without CTX-ID

```json
{
  "session_id": "sess_123",
  "action": "tool.invoke",
  "payload": {
    "tool": "example_tool"
  }
}
```

Invalid because:
- `ctx_id` is required.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.

---

## Integration Points

### Consensus Engine

Required invocation contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Integration requirements:
- `language` MUST always be passed.
- `spec.language` MUST resolve to one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

Behavioral selectors:
- `"swift"` -> `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `"python"` -> `GENERATION_SYSTEM`

Fix-loop requirements:
- Loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`
- Fix arbitration uses `_score_fix()`
- Length-based arbitration is forbidden

---

### TrustFlow

All enforcement-path integrations MUST synchronously emit `TrustFlowEvent`.

Minimum emitted fields:
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Failure handling:
- Emission failure MUST be logged
- Emission failure MUST be surfaced
- Emission failure MUST NOT be silently ignored

---

### CTX-ID Validation

Every action-processing entry point MUST:
1. Receive or resolve `ctx_id`
2. Validate CTX-ID before any other processing
3. Reject immediately on validation failure
4. Validate against TrustLock public key
5. Reject expired tokens
6. Treat missing CTX-ID as `UNTRUSTED`

---

### VTZ Policy Enforcement

Before action execution:
1. Check action against VTZ policy
2. Deny implicit cross-VTZ access
3. Require explicit authorization for cross-VTZ tool calls
4. Produce `VTZEnforcementDecision` with `verdict=block` on denial
5. Emit TrustFlow event for `allow`, `restrict`, or `block`

---

### File Write Security

Before any disk write:
1. Validate target path with `path_security.validate_write_path()`

---

### Prompt Construction Security

Before including external document content in prompts:
1. Injection-scan all loaded document chunks
2. Place external document context in USER prompt only
3. Never place external document context in SYSTEM prompt

---

### LLM Security Gate

On LLM output exactly matching or containing `SECURITY_REFUSAL`:
1. Stop
2. Gate
3. Log
4. Do not retry to bypass

---

### Testing and Conformance

Before modifying code:
1. Find the owning TRD in `README.md`
2. Read relevant TRD sections
3. Check TRD-11 if touching credentials, external content, generated code, or CI
4. Run:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Conformance requirements:
- `pytest` test suite
- `ruff` clean
- `mypy` clean
- Coverage ≥ 85% on new modules