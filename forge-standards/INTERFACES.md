# Interface Contracts - Crafted

This document defines the wire-format and API contract reference for the Crafted subsystem based on the provided TRD content.

## Data Structures

### ConsensusRunRequest

Request contract for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Free-form task description. |
| `context` | `string` | Yes | Prompt context string. |
| `language` | `string` | Yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. |

#### Required invocation shape

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
```

### ConsensusRunResult

Result returned by the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output. |

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | Must be exactly `block` when produced for VTZ policy denial. |

### TrustFlowEvent

Event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique. Must be generated using CSPRNG. Must not be sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | Must be SHA-256 of the serialized action payload. |

### CTX-ID Token

Opaque token contract with lifecycle constraints.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. Must validate against TrustLock public key. |

### SecurityRefusalSignal

LLM security gate output.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `output` | `string` | Yes | When value is exactly `SECURITY_REFUSAL`, processing must stop, gate, and log. Must not retry to bypass. |

## Enums and Constants

### SupportedLanguage

Exact allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### System Selection Rules

These are selection constants implied by the interface:

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

### Reserved Security Output

- `SECURITY_REFUSAL`

### Verdict Values

- `block`

## Validation Rules

### Consensus Engine Request Validation

1. `language` is required.
2. `language` must be passed on every call to the consensus engine.
3. `language` must be one of:
   - `"python"`
   - `"swift"`
   - `"go"`
   - `"typescript"`
   - `"rust"`

### Fix Strategy and Arbitration

These are behavioral interface constraints:

1. Fix loop strategy must be failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
2. Length-based fix arbitration is forbidden.
3. Fix arbitration must use `_score_fix()`.
4. Assertion token overlap is the scoring basis for `_score_fix()`, not response length.

### CAL Enforcement Contract

Every entry point that processes an agent action must satisfy all of the following:

1. CTX-ID validation must occur first.
2. CTX-ID validation failure must result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action must be checked against VTZ policy before execution.
5. VTZ policy denial must produce a `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.
7. TrustFlow emission failure must not silently continue.
8. TrustFlow emission failure must be logged and surfaced.

### TrustFlow Emission Contract

1. Every TrustFlow event must include all of:
   - `event_id`
   - `session_id`
   - `ctx_id`
   - `ts`
   - `event_type`
   - `payload_hash`
2. `event_id` must be globally unique.
3. `event_id` must use CSPRNG generation.
4. `event_id` must not be sequential.
5. `ts` must be a UTC Unix timestamp with millisecond precision.
6. `payload_hash` must be SHA-256 of the serialized action payload.
7. Emission must be synchronous in the enforcement path.
8. Async buffering is not permitted.
9. Failed emission is a WARN-level audit event.
10. Failed emission must not be silently skipped.

### CTX-ID Contract

1. CTX-ID tokens are immutable once issued.
2. Rotation creates a new token.
3. The old token is invalidated immediately on rotation.
4. Expired CTX-ID must be rejected.
5. Clock skew tolerance is deployment-defined.
6. CTX-ID must be validated against TrustLock public key.
7. Software-only validation is rejected.
8. Missing CTX-ID must be treated as `UNTRUSTED`.
9. Identity must never be inferred from context when CTX-ID is missing.

### VTZ Enforcement Contract

1. Every agent session is bound to exactly one VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit cross-VTZ authorization is denied.
4. VTZ boundaries are structural, not advisory.
5. Enforcement cannot be bypassed by application code.
6. VTZ policy changes take effect at the next CTX-ID issuance, not mid-session.

### Security Rules

1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Log HTTP status codes and error types only.
6. All file paths written to disk must pass `path_security.validate_write_path()` before any write.
7. All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
8. Context from external documents must go in the USER prompt, never the SYSTEM prompt.
9. On `SECURITY_REFUSAL`: stop, gate, log, and do not retry to bypass.

### Python Backend Contract

1. Python version must be `3.12`.
2. Type annotations are required on every function.
3. Backend code must use `async/await` throughout.
4. No blocking calls on the event loop.
5. Dataclasses are required for all structured data.
6. `pytest` is required for tests.
7. Tests live in `tests/` and mirror `src/` structure.
8. `ruff` must pass clean.
9. `mypy` must pass clean.
10. Test coverage must be at least `85%` on all new modules.
11. `pyyaml` must be present in `requirements.txt`.

### Forbidden Patterns

The following are non-conformant:

#### Length-based fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

#### Swift force unwrap

```swift
let value = optional!
```

#### LLM API call from Swift

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

#### Backend token read from Keychain

```swift
let token = KeychainKit.read("github_token")
```

Constraint:
- Only Swift reads Keychain.
- Swift reads Keychain only to deliver via XPC.
- Python reads nothing from Keychain.

## Wire Format Examples

### Valid: ConsensusRunRequest

```json
{
  "task": "Implement: Add validation",
  "context": "Relevant context string",
  "language": "python"
}
```

### Valid: ConsensusRunResult

```json
{
  "final_code": "from dataclasses import dataclass\n"
}
```

### Valid: TrustFlowEvent

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678.123,
  "event_type": "block",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"
}
```

### Valid: VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Invalid: ConsensusRunRequest missing language

```json
{
  "task": "Implement: Add validation",
  "context": "Relevant context string"
}
```

Reason:
- `language` is required.

### Invalid: ConsensusRunRequest with unsupported language

```json
{
  "task": "Implement: Add validation",
  "context": "Relevant context string",
  "language": "java"
}
```

Reason:
- `language` must be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid: TrustFlowEvent missing required field

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678.123,
  "event_type": "allow"
}
```

Reason:
- `payload_hash` is required.

### Invalid: VTZEnforcementDecision wrong verdict

```json
{
  "verdict": "allow"
}
```

Reason:
- VTZ policy denial must produce `verdict=block`.

### Invalid: Security refusal retry behavior

```json
{
  "output": "SECURITY_REFUSAL",
  "action": "retry"
}
```

Reason:
- On `SECURITY_REFUSAL`, the system must stop, gate, and log. It must not retry to bypass.

## Integration Points

### Consensus Engine

Interface requirement:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Integration constraints:
- `language` must always be passed.
- `result.final_code` is the generated output field.

### Prompt/System Selection

- `"swift"` routes to `SWIFT_GENERATION_SYSTEM` and may inject `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `"python"` routes to `GENERATION_SYSTEM`.

### Path Security

Before any disk write:
- `path_security.validate_write_path()` must be called and must pass.

### Injection Scanning

Before including loaded document chunks in an LLM prompt:
- Injection scanning must be performed.

### Prompt Placement

- External document context goes in the USER prompt.
- External document context must never be placed in the SYSTEM prompt.

### TrustLock Validation

CTX-ID validation integration:
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is not acceptable.

### Keychain/XPC Boundary

- Only Swift may read Keychain.
- Swift may read Keychain only to deliver via XPC.
- Python backend must not read from Keychain.

### Test Invocation

Required existing test command before changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```