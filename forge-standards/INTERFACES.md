# Interface Contracts - ForgeAgent

This document defines the wire formats and API contract requirements for the ForgeAgent subsystem based on the provided TRD excerpts and standards. These requirements are normative.

## Data Structures

All structured backend data MUST be represented as dataclasses in Python 3.12 with type annotations on every function.

### ConsensusRunRequest

Request passed to the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Free-form task description. Example pattern: `Implement: {spec.title}` |
| `context` | `str` | Yes | Context string supplied to consensus engine |
| `language` | `str` | Yes | MUST be one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Required invocation contract

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### ConsensusRunResult

Result returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Final generated code output |

### VTZEnforcementDecision

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `str` | Yes | MUST be `"block"` for VTZ policy denial |

### TrustFlowEvent

Every action outcome MUST emit a TrustFlow event.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | Yes | MUST be globally unique; MUST be CSPRNG-generated; MUST NOT be sequential |
| `session_id` | `str` | Yes | Session identifier |
| `ctx_id` | `str` | Yes | CTX-ID token identifier associated with the action |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `str` | Yes | Event type name |
| `payload_hash` | `str` | Yes | MUST be SHA-256 of the serialized action payload |

### AgentActionPayload

Serialized action payload used in enforcement and TrustFlow hashing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | Yes | MUST be validated first at every entry point that processes an agent action |
| `session_id` | `str` | Yes | Session identifier |
| `action` | `object` | Yes | Action-specific payload |
| `language` | `str` | No | If present, MUST be one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

### CTXIDToken

Logical CTX-ID token contract.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | Yes | Immutable once issued |
| `vtz_id` | `str` | Yes | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance |
| `issued_at` | `number` | Yes | Token issuance time |
| `expires_at` | `number` | Yes | Expired CTX-ID MUST be rejected |
| `public_key_id` | `str` | Yes | Validation MUST be against TrustLock public key |
| `session_id` | `str` | Yes | Session identifier bound to issuance |

### FixStrategyInput

Input to failure-type-aware fix loop strategy selection.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `str` | Yes | Used by `_choose_strategy(failure_type, attempt, records)` |
| `attempt` | `int` | Yes | Attempt counter |
| `records` | `list[object]` | Yes | Prior failure or fix records |

### FixArbitrationInput

Input to fix arbitration scoring.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `assertion_tokens` | `list[str]` | Yes | Tokens derived from assertions |
| `candidate_fix` | `str` | Yes | Candidate fix response to score |

### SecurityRefusalRecord

Record of LLM security refusal handling.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `output` | `str` | Yes | When value indicates `SECURITY_REFUSAL`, processing MUST stop |
| `gated` | `bool` | Yes | MUST be `true` when `SECURITY_REFUSAL` is observed |
| `logged` | `bool` | Yes | MUST be `true` when `SECURITY_REFUSAL` is observed |

## Enums and Constants

### SupportedLanguage

Exact allowed values:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### LanguageToSystemSelection

| `language` | Selected system |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords detected |
| `"python"` | `GENERATION_SYSTEM` |

No other system-selection mappings are defined in the provided source.

### Verdict

| Value | Meaning |
|---|---|
| `"block"` | VTZ policy denial |

### Special Output Tokens

| Value | Meaning |
|---|---|
| `SECURITY_REFUSAL` | LLM refusal token; processing MUST stop, gate, and log; MUST NOT retry to bypass |

### Forbidden Patterns

These are non-conformant and MUST NOT appear in implementations.

#### Forbidden fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason: length-based fix arbitration is replaced by `_score_fix()` based on assertion token overlap.

#### Forbidden Swift force unwrap

```swift
let value = optional!
```

#### Forbidden Swift LLM API call

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

#### Forbidden backend Keychain read in Swift/backend split

```swift
let token = KeychainKit.read("github_token")
```

Constraint: Only Swift reads Keychain, only to deliver via XPC. Python reads nothing from Keychain.

## Validation Rules

## Entry Point Enforcement

Every entry point that processes an agent action MUST satisfy all of the following in order:

1. MUST call CTX-ID validation FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` with `verdict="block"`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. Failed TrustFlow emission MUST be logged and surfaced.
9. Emission in the enforcement path MUST be synchronous; async buffering is not permitted.

## TrustFlow Validation

For every `TrustFlowEvent`:

- `event_id` MUST be globally unique.
- `event_id` MUST be generated with CSPRNG.
- `event_id` MUST NOT be sequential.
- `ts` MUST be a UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST equal SHA-256 of the serialized action payload.
- Missing any required field makes the event non-conformant.
- Failed emission is a WARN-level audit event, not a silent skip.

## CTX-ID Validation

- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined and not specified here.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from context when CTX-ID is missing.

## VTZ Enforcement Validation

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

## Consensus Engine Validation

- `language` MUST always be passed to `_consensus.run(...)`.
- Allowed values are exactly: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.
- For `"swift"`, system selection is `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- For `"python"`, system selection is `GENERATION_SYSTEM`.
- Fix loop strategy MUST use `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration MUST NOT be used.

## Security Validation

### Credentials and secrets

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

### Process execution

- Never use `shell=True` in subprocess calls.

### Code execution

- Never call `eval()` or `exec()` on generated or external content.

### Logging

- Never log HTTP response bodies.
- Log status codes and error types only.

### File writes

- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

### Prompt injection handling

- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

### Security refusal handling

- When output is `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.

## Python Implementation Requirements

- Python version MUST be 3.12.
- All functions MUST have type annotations.
- Backend MUST use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses MUST be used for all structured data.
- Tests MUST use `pytest`.
- Tests MUST live in `tests/` and mirror `src/` structure.
- `ruff` MUST pass clean.
- `mypy` MUST pass clean.
- Test coverage MUST be at least 85% on all new modules.
- `pyyaml` MUST be present in `requirements.txt`.

## Wire Format Examples

## Valid Payloads

### Valid consensus request

```json
{
  "task": "Implement: Add health check endpoint",
  "context": "Existing service exposes /status and uses async handlers.",
  "language": "python"
}
```

### Valid TrustFlow event

```json
{
  "event_id": "8f6b6b8b-7e7a-4f27-9c1f-2d4e7b8a9c10",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3f7850c2e9c5e7a0d8e2c4c5a9b1d3f0e6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1"
}
```

### Valid enforcement decision

```json
{
  "verdict": "block"
}
```

### Valid security refusal record

```json
{
  "output": "SECURITY_REFUSAL",
  "gated": true,
  "logged": true
}
```

## Invalid Payloads

### Invalid consensus request: missing `language`

```json
{
  "task": "Implement: Add health check endpoint",
  "context": "Existing service exposes /status and uses async handlers."
}
```

Reason: `language` is required and MUST always be passed.

### Invalid consensus request: unsupported language

```json
{
  "task": "Implement: Add health check endpoint",
  "context": "Existing service exposes /status and uses async handlers.",
  "language": "java"
}
```

Reason: `language` MUST be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid TrustFlow event: missing `payload_hash`

```json
{
  "event_id": "8f6b6b8b-7e7a-4f27-9c1f-2d4e7b8a9c10",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "allow"
}
```

Reason: every TrustFlow event MUST include `payload_hash`.

### Invalid enforcement flow: missing `ctx_id`

```json
{
  "session_id": "sess_123",
  "action": {
    "type": "generate_code"
  }
}
```

Reason: missing CTX-ID MUST be treated as `UNTRUSTED`; identity must not be inferred from context.

### Invalid security handling

```json
{
  "output": "SECURITY_REFUSAL",
  "gated": false,
  "logged": false
}
```

Reason: on `SECURITY_REFUSAL`, processing MUST stop, gate, and log.

## Integration Points

## Consensus Engine

ForgeAgent integrates with a consensus engine via:

- Method: `_consensus.run(...)`
- Required arguments:
  - `task: str`
  - `context: str`
  - `language: "python" | "swift" | "go" | "typescript" | "rust"`
- Result field consumed:
  - `final_code: str`

## Enforcement Path

Every agent action entry point integrates with:

1. CTX-ID validation
2. VTZ policy enforcement
3. TrustFlow synchronous emission

Required sequencing:

1. Validate `ctx_id`
2. Reject immediately on validation failure
3. Evaluate VTZ policy before execution
4. Emit TrustFlow event synchronously for every outcome
5. Surface TrustFlow emission failures

## TrustLock

CTX-ID validation MUST be against TrustLock public key.

- Software-only validation is non-conformant.
- Missing CTX-ID is `UNTRUSTED`.

## Path Security

Before any file write, ForgeAgent MUST call:

- `path_security.validate_write_path()`

This validation MUST occur before the write operation.

## Prompt Construction and Document Loading

When external documents are used:

- Every loaded document chunk MUST pass injection scanning before inclusion in any LLM prompt.
- External document context MUST be placed in the USER prompt.
- External document context MUST NEVER be placed in the SYSTEM prompt.

## Testing and Pre-Change Workflow

Before modifying ForgeAgent code:

1. Find the owning TRD via the TRD Index in `README.md`.
2. Read the relevant TRD sections, especially interfaces, error contracts, security, and testing requirements.
3. Check TRD-11 if the change touches credentials, external content, generated code, or CI.
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```