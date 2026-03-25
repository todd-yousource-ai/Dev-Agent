# Interface Contracts - CraftedDevAgent

Definitive wire format and API contract reference for the CraftedDevAgent subsystem.

## Data Structures

All structured data MUST be implemented as dataclasses in Python 3.12.

### ConsensusRunRequest

Request passed to the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Human-readable task description. |
| `context` | `str` | Yes | Context string supplied to the consensus engine. External document context MUST be placed in the USER prompt, never the SYSTEM prompt. All loaded document chunks MUST pass injection scanning before inclusion. |
| `language` | `str` | Yes | MUST be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. |

#### Required call shape

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
| `final_code` | `str` | Yes | Final generated code output. |

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `str` | Yes | MUST be exactly `"block"` for VTZ policy denial records required by the enforcement contract. |

### TrustFlowEvent

Synchronous audit/enforcement event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | Yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | `str` | Yes | Session identifier. |
| `ctx_id` | `str` | Yes | CTX-ID associated with the action. Missing `ctx_id` MUST be treated as UNTRUSTED. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `str` | Yes | Event type identifier. |
| `payload_hash` | `str` | Yes | MUST be SHA-256 of the serialized action payload. |

### SECURITY_REFUSAL Handling Record

Logical handling contract for LLM refusal output.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `output` | `str` | Yes | If value is `SECURITY_REFUSAL`, processing MUST stop, gate, and log. MUST NOT retry to bypass. |

## Enums and Constants

### SupportedLanguage

Exact allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Language System Selection Rules

These are required behavioral mappings.

| `language` value | Selected system/addendum |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected |
| `"python"` | `GENERATION_SYSTEM` |

No source-defined generation system mapping is provided here for `"go"`, `"typescript"`, or `"rust"` beyond their validity as accepted `language` values.

### Verdict Values

| Value | Meaning |
|---|---|
| `"block"` | VTZ policy denial outcome in `VTZEnforcementDecision` |

### Security Sentinel Value

| Value | Meaning |
|---|---|
| `SECURITY_REFUSAL` | LLM security refusal output; MUST stop, gate, and log; MUST NOT retry to bypass |

## Validation Rules

## Entry Point Enforcement

Every entry point that processes an agent action MUST satisfy all of the following in order:

1. MUST call CTX-ID validation FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. MUST NOT perform partial processing before CTX-ID validation succeeds.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict="block"`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a `TrustFlowEvent`.
7. TrustFlow emission failure MUST NOT silently continue; it MUST be logged and surfaced.

## TrustFlow Event Validation

A `TrustFlowEvent` is valid only if all of the following are true:

- `event_id` is present.
- `event_id` is globally unique.
- `event_id` is generated with CSPRNG.
- `event_id` is not sequential.
- `session_id` is present.
- `ctx_id` is present for trusted processing.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `event_type` is present.
- `payload_hash` is present.
- `payload_hash` equals the SHA-256 of the serialized action payload.

Emission requirements:

- Emission MUST be synchronous in the enforcement path.
- Async buffering is NOT permitted.
- Failed emission is a WARN-level audit event.
- Failed emission is NOT permitted to be a silent skip.

## CTX-ID Validation Rules

- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is permitted after issuance.
- CTX-ID rotation creates a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NOT be inferred from context when CTX-ID is missing.

## VTZ Enforcement Rules

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

## Consensus Engine Validation

- Every consensus engine invocation MUST pass `language`.
- `language` MUST be one of the exact supported values.
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()`.
- Length-based fix arbitration is FORBIDDEN.

### Forbidden fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

## Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on any generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` output is observed: stop, gate, log. Never retry to bypass.

## Python Implementation Requirements

- Python version MUST be 3.12.
- Type annotations are required on every function.
- Backend code MUST use `async/await` throughout.
- No blocking calls on the event loop.
- Structured data MUST use dataclasses.
- Tests MUST use `pytest`.
- Tests MUST live in `tests/` and mirror `src/` structure.
- `ruff` linting MUST pass clean.
- `mypy` type checking MUST pass clean.
- Test coverage on all new modules MUST be `>= 85%`.
- `pyyaml` MUST be present in `requirements.txt`.

## Prohibited Patterns

### Swift

```swift
let value = optional!
```

Reason: force unwrap is FORBIDDEN.

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Reason: LLM API call from Swift is FORBIDDEN.

```swift
let token = KeychainKit.read("github_token")
```

Reason: Keychain read for backend is FORBIDDEN. Only Swift reads Keychain, only to deliver via XPC.

## Wire Format Examples

## Valid Payloads

### Valid `ConsensusRunRequest`

```json
{
  "task": "Implement: Add CTX-ID validation to action entry point",
  "context": "Validate ctx_id before any processing. Emit TrustFlow event on allow/restrict/block.",
  "language": "python"
}
```

### Valid `ConsensusRunResult`

```json
{
  "final_code": "async def handle_action(...):\n    ...\n"
}
```

### Valid `VTZEnforcementDecision`

```json
{
  "verdict": "block"
}
```

### Valid `TrustFlowEvent`

```json
{
  "event_id": "7f5d4d8b-6f8e-4f4d-9f0d-8f4bb0d5b6c1",
  "session_id": "sess_01JABCDEF1234567890",
  "ctx_id": "ctx_01JABCDEF1234567890",
  "ts": 1735689600123,
  "event_type": "action.block",
  "payload_hash": "3a7bd3e2360a3d29eea436fcfb7e44c73f6f0afc6a5e9f1b2d5b6c7d8e9f0123"
}
```

## Invalid Payloads

### Invalid `ConsensusRunRequest` — missing language

```json
{
  "task": "Implement: Add CTX-ID validation to action entry point",
  "context": "Validate ctx_id before any processing."
}
```

Reason: `language` is required.

### Invalid `ConsensusRunRequest` — unsupported language

```json
{
  "task": "Implement: Add CTX-ID validation to action entry point",
  "context": "Validate ctx_id before any processing.",
  "language": "java"
}
```

Reason: `language` MUST be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid `VTZEnforcementDecision` — wrong verdict

```json
{
  "verdict": "allow"
}
```

Reason: VTZ policy denial record required by contract MUST use `verdict="block"`.

### Invalid `TrustFlowEvent` — missing required fields

```json
{
  "event_id": "123",
  "session_id": "sess_01",
  "ts": 1735689600
}
```

Reasons:

- `ctx_id` missing
- `event_type` missing
- `payload_hash` missing
- `event_id` not proven globally unique/CSPRNG/non-sequential
- `ts` not expressed with millisecond precision

### Invalid security handling

```json
{
  "output": "SECURITY_REFUSAL",
  "retry": true
}
```

Reason: `SECURITY_REFUSAL` MUST stop, gate, and log. Retry to bypass is forbidden.

## Integration Points

## Consensus Engine

Required invocation contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Behavioral integration requirements:

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.
- Fix loop strategy integrates via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration integrates via `_score_fix()`.

## Path Security

Before any disk write, all file paths MUST be validated with:

```python
path_security.validate_write_path()
```

Constraint:

- Validation MUST occur before the write operation.

## Prompt Construction

- External document context MUST be placed in the USER prompt.
- External document context MUST NOT be placed in the SYSTEM prompt.
- Every loaded document chunk MUST pass injection scanning before inclusion.

## TrustLock / CTX-ID Validation

Integration requirements:

- CTX-ID validation MUST occur first in every action-processing entry point.
- Validation MUST be against TrustLock public key.
- Software-only validation is rejected.

## TrustFlow Emission

Integration requirements:

- Emission occurs for every action outcome.
- Emission is synchronous in the enforcement path.
- Emission failure MUST be logged and surfaced.
- Emission failure is a WARN-level audit event.

## Test Invocation

Existing tests MUST be run before making changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```