# Interface Contracts - CraftedDevAgent

This document defines the wire-format and API contract requirements for the CraftedDevAgent subsystem, derived from the provided TRD standards.

## Data Structures

The provided TRD excerpts define required invocation patterns, enforcement records, and event payload fields. Only fields explicitly present in source are included below.

### ConsensusRunRequest

Request contract for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Free-form task description. Example source usage: `f"Implement: {spec.title}"` |
| `context` | `string` | yes | Context string passed to consensus engine |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | yes | Must always be passed |

#### Notes
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

### ConsensusRunResult

Result contract returned by the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Final generated code output |

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | Must be exactly `block` when produced for VTZ policy denial |

### TrustFlowEvent

Required event shape for all TrustFlow emissions.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | Must be globally unique; generated via CSPRNG; must not be sequential |
| `session_id` | `string` | yes | Session identifier |
| `ctx_id` | `string` | yes | CTX-ID associated with the action |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Event type identifier |
| `payload_hash` | `string` | yes | Must be SHA-256 of the serialized action payload |

## Enums and Constants

### SupportedLanguage

Exact allowed values for `ConsensusRunRequest.language`:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

### Required Verdict Value

For `VTZEnforcementDecision.verdict` on VTZ policy denial:

- `block`

### Security Refusal Sentinel

Literal output value referenced by contract:

- `SECURITY_REFUSAL`

### Named System Selectors

These names are part of the interface selection contract:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

## Validation Rules

## Entry Point Enforcement

Every entry point that processes an agent action MUST satisfy all of the following:

1. Call CTX-ID validation first.
2. On CTX-ID validation failure, reject immediately.
3. Do not partially process on CTX-ID validation failure.
4. Check every action against VTZ policy before execution.
5. If VTZ policy denies, produce a `VTZEnforcementDecision` with `verdict=block`.
6. Emit a TrustFlow event for every action outcome: allow, restrict, or block.
7. If TrustFlow emission fails, do not silently continue; log and surface the failure.

## TrustFlow Emission Rules

For every `TrustFlowEvent`:

- `event_id` must be globally unique.
- `event_id` must use CSPRNG generation.
- `event_id` must not be sequential.
- `ts` must be a UTC Unix timestamp with millisecond precision.
- `payload_hash` must be SHA-256 of the serialized action payload.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission must not be silently skipped.

## CTX-ID Rules

- CTX-ID tokens are immutable once issued.
- No field modification is permitted after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately on rotation.
- Expired CTX-ID must be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from context when CTX-ID is missing.

## VTZ Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance.
- VTZ policy changes do not take effect mid-session.

## Consensus Engine Invocation Rules

- `language` must always be passed to consensus engine calls.
- Fix loop strategy must use `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration must use `_score_fix()`.
- Length-based fix arbitration is forbidden.

## Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents must go in the USER prompt, never the SYSTEM prompt.
- When output is `SECURITY_REFUSAL`: stop, gate, log, and never retry to bypass.

## Python Backend Rules

- Python version: `3.12`
- Type annotations required on every function.
- `async/await` throughout backend.
- No blocking calls on the event loop.
- Dataclasses required for all structured data.
- Tests use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be `≥ 85%` on all new modules.
- `pyyaml` must be present in `requirements.txt`.

## Forbidden Patterns

The following are explicitly non-conformant.

### Forbidden fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

### Forbidden Swift force unwrap

```swift
let value = optional!
```

### Forbidden LLM API call from Swift

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

### Forbidden backend Keychain read in Swift contract context

```swift
let token = KeychainKit.read("github_token")
```

Constraint:
- Only Swift reads Keychain, only to deliver via XPC.
- Python reads nothing from Keychain.

## Wire Format Examples

## Valid Payloads

### Valid ConsensusRunRequest

```json
{
  "task": "Implement: Add retry handling",
  "context": "Existing backend uses async consensus execution.",
  "language": "python"
}
```

### Valid ConsensusRunResult

```json
{
  "final_code": "async def run() -> None:\n    pass\n"
}
```

### Valid TrustFlowEvent

```json
{
  "event_id": "3b7a8e2f-6e1d-4d2e-a8d3-3d4e7f92c1ab",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action_allow",
  "payload_hash": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
}
```

### Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

## Invalid Payloads

### Invalid ConsensusRunRequest: missing language

```json
{
  "task": "Implement: Add retry handling",
  "context": "Existing backend uses async consensus execution."
}
```

Reason:
- `language` is required and must always be passed.

### Invalid ConsensusRunRequest: unsupported language

```json
{
  "task": "Implement: Add retry handling",
  "context": "Existing backend uses async consensus execution.",
  "language": "java"
}
```

Reason:
- `language` must be one of: `python`, `swift`, `go`, `typescript`, `rust`.

### Invalid TrustFlowEvent: missing required field

```json
{
  "event_id": "3b7a8e2f-6e1d-4d2e-a8d3-3d4e7f92c1ab",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action_allow"
}
```

Reason:
- `payload_hash` is required.

### Invalid VTZEnforcementDecision: wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- On VTZ policy denial, `verdict` must be exactly `block`.

## Integration Points

## Consensus Engine

Invocation contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

Integration requirements:
- `language` must be supplied on every call.
- Consumers must read generated code from `result.final_code`.

## Enforcement Path

All agent-action entry points must integrate with:

1. CTX-ID validation
2. VTZ policy enforcement
3. TrustFlow emission

Required ordering:
1. Validate `ctx_id` first
2. Enforce VTZ policy before execution
3. Emit `TrustFlowEvent` synchronously for every outcome

## Path Security

Before any disk write:
- Call `path_security.validate_write_path()`

## Prompt Construction

When loading external document content:
- Perform injection scanning on all loaded document chunks before inclusion in any LLM prompt
- Place external document context in the USER prompt only
- Never place external document context in the SYSTEM prompt

## Security Gating

On receiving `SECURITY_REFUSAL` from the LLM:
- stop
- gate
- log
- do not retry to bypass

## Test Execution Contract

Before making changes, run:

```bash
cd src && pytest ../tests/ -v --tb=short
```