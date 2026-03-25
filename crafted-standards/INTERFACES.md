# Interface Contracts - CraftedDevAgent

Definitive wire-format and API contract reference for the CraftedDevAgent subsystem.

## Data Structures

All structured data MUST be represented as dataclasses in Python 3.12 code. Field names below are normative and MUST be used exactly as specified.

### TrustFlowEvent

Required for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique. MUST be generated using CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | Yes | Session identifier for the agent session. |
| `ctx_id` | `string` | Yes | CTX-ID token identifier associated with the action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Notes
- Emission MUST be synchronous in the enforcement path.
- Async buffering is NOT permitted.
- Failed emission MUST produce a WARN-level audit event and MUST NOT be silently skipped.

---

### VTZEnforcementDecision

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | MUST be `block` for VTZ policy denial records. |

#### Notes
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### ConsensusRunRequest

Input contract for consensus engine invocation.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Human-readable task string. Example uses `Implement: {spec.title}`. |
| `context` | `string` | Yes | Context string passed to consensus engine. |
| `language` | `string` | Yes | MUST be one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. Always pass language. |

#### Required invocation shape

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

---

### ConsensusRunResult

Output contract consumed from consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code result. |

---

### FixStrategySelectionInput

Input shape for failure-type-aware fix loop strategy.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `string` | Yes | Failure classification used by strategy selector. |
| `attempt` | `integer` | Yes | Current fix attempt number. |
| `records` | `array` | Yes | Prior fix/test records supplied to strategy selection. |

#### Selection rule
- Fix loop strategy MUST be selected via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup table selection is non-conformant.

---

### FixArbitrationInput

Input shape for fix arbitration scoring.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `assertion_tokens` | `array[string]` | Yes | Assertion token set used for overlap scoring. |
| `candidate_fix` | `string` | Yes | Candidate fix content to score. |

#### Arbitration rule
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration is forbidden.

---

### AgentActionPayload

Serialized action payload used to compute `payload_hash`.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `*` | `object` | Yes | Exact action payload schema is component-specific, but the serialized payload MUST be hashed with SHA-256 and included as `payload_hash` in every `TrustFlowEvent`. |

---

### CTXIDToken

Logical contract for CTX-ID token handling.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. |
| `session_id` | `string` | Yes | Agent session binding. |
| `vtz` | `string` | Yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance. |
| `expires_at` | `number` | Yes | Expiry timestamp; expired CTX-ID MUST be rejected. |
| `public_key_id` | `string` | Yes | Token MUST be validated against TrustLock public key. |

#### Notes
- Missing `ctx_id` MUST be treated as `UNTRUSTED`.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Software-only validation is rejected.

---

### AuditEvent

Used for surfaced enforcement-path failures.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `level` | `string` | Yes | MUST support `WARN` for TrustFlow emission failures. |
| `event_type` | `string` | Yes | Audit event classifier. |
| `message` | `string` | Yes | Human-readable event message. |

---

## Enums and Constants

### Language

Allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Enforcement Verdict

Allowed known value from provided contract:

- `block`

### Audit Level

Allowed known value from provided contract:

- `WARN`

### Trust Classification

Allowed known value from provided contract:

- `UNTRUSTED`

### System Selectors

These values are selected internally based on `language`:

| Condition | Selected system |
|---|---|
| `language="swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords detected |
| `language="python"` | `GENERATION_SYSTEM` |

### Required Algorithms and Formats

| Name | Required value |
|---|---|
| Payload hash algorithm | `SHA-256` |
| Timestamp basis | `UTC Unix timestamp with millisecond precision` |
| Uniqueness source for `event_id` | `CSPRNG` |

---

## Validation Rules

## Entry Point Enforcement

Every entry point that processes an agent action MUST satisfy all of the following in order:

1. MUST call CTX-ID validation FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue; it MUST be logged and surfaced.

## TrustFlow Validation

For every `TrustFlowEvent`:

- `event_id` MUST be present.
- `event_id` MUST be globally unique.
- `event_id` MUST NOT be sequential.
- `session_id` MUST be present.
- `ctx_id` MUST be present.
- `ts` MUST be a UTC Unix timestamp with millisecond precision.
- `event_type` MUST be present.
- `payload_hash` MUST be present.
- `payload_hash` MUST equal the SHA-256 hash of the serialized action payload.

## CTX-ID Validation

- CTX-ID tokens are immutable once issued.
- Any field modification after issuance is invalid.
- Rotation MUST create a new token.
- Old token MUST be invalidated immediately on rotation.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from surrounding context when `ctx_id` is missing.

## VTZ Validation

- Every agent session MUST be bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

## Consensus Engine Validation

- Calls to consensus engine MUST always include `language`.
- `language` MUST be one of `"python" | "swift" | "go" | "typescript" | "rust"`.
- `language="swift"` MUST select `SWIFT_GENERATION_SYSTEM` and MAY inject `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` MUST select `GENERATION_SYSTEM`.

## Fix Loop Validation

- Strategy selection MUST use `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration is forbidden.

Forbidden example:

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

## Security Validation

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on any generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` output is returned from the LLM: stop, gate, log. Never retry to bypass.

## Python Backend Requirements

- Python version MUST be `3.12`.
- Type annotations are required on every function.
- Backend MUST use `async/await` throughout.
- Blocking calls on the event loop are not permitted.
- Dataclasses are required for all structured data.
- Tests MUST use `pytest`.
- Tests MUST live in `tests/` and mirror `src/` structure.
- `ruff` MUST pass clean.
- `mypy` MUST pass clean.
- Test coverage MUST be `≥ 85%` on all new modules.
- `pyyaml` MUST be present in `requirements.txt`.

## Pre-Implementation Process Contract

Before modifying code:

1. Find the TRD that owns the component in `README.md`.
2. Read relevant TRD sections, especially interfaces, error contracts, security, testing requirements.
3. Check TRD-11 if the change touches credentials, external content, generated code, or CI.
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## Wire Format Examples

## Valid Payloads

### Valid `TrustFlowEvent`

```json
{
  "event_id": "8f8b6b0f-93a0-4ac8-98b2-4b5ce7b9e7a1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

### Valid `VTZEnforcementDecision`

```json
{
  "verdict": "block"
}
```

### Valid `ConsensusRunRequest`

```json
{
  "task": "Implement: Add validation",
  "context": "Relevant component context",
  "language": "python"
}
```

### Valid `ConsensusRunResult`

```json
{
  "final_code": "def example() -> None:\n    pass\n"
}
```

### Valid CTX-ID token shape

```json
{
  "ctx_id": "ctx_abc",
  "session_id": "sess_123",
  "vtz": "vtz_primary",
  "expires_at": 1735689900123,
  "public_key_id": "trustlock-key-1"
}
```

## Invalid Payloads

### Invalid `TrustFlowEvent` - missing required field

```json
{
  "event_id": "8f8b6b0f-93a0-4ac8-98b2-4b5ce7b9e7a1",
  "session_id": "sess_123",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

Invalid because `ctx_id` is required.

### Invalid `ConsensusRunRequest` - unsupported language

```json
{
  "task": "Implement: Add validation",
  "context": "Relevant component context",
  "language": "java"
}
```

Invalid because `language` MUST be one of `"python" | "swift" | "go" | "typescript" | "rust"`.

### Invalid fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Invalid because length-based arbitration is forbidden; use `_score_fix()`.

### Invalid Swift patterns

```swift
let value = optional!
```

Invalid because force unwrap is forbidden.

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Invalid because LLM API call from Swift is forbidden.

```swift
let token = KeychainKit.read("github_token")
```

Invalid because Python reads nothing from Keychain; only Swift reads Keychain, only to deliver via XPC.

### Invalid subprocess usage

```python
subprocess.run(cmd, shell=True)
```

Invalid because `shell=True` is forbidden.

### Invalid code execution

```python
eval(generated_content)
exec(external_content)
```

Invalid because `eval()` and `exec()` on generated or external content are forbidden.

---

## Integration Points

## Consensus Engine

CraftedDevAgent MUST invoke the consensus engine with:

- `task`
- `context`
- `language`

Output consumed:

- `result.final_code`

Language-dependent selector behavior:

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` and optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

## CAL Enforcement Layer

CraftedDevAgent entry points that process agent actions MUST integrate with CAL enforcement and satisfy:

- CTX-ID validation first
- VTZ policy check before execution
- `VTZEnforcementDecision` on denial
- Synchronous TrustFlow emission for all outcomes

## TrustFlow

CraftedDevAgent MUST emit a `TrustFlowEvent` containing:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Emission failure handling:

- MUST log
- MUST surface failure
- MUST NOT silently continue
- MUST be WARN-level audit event

## Path Security

Before any file write, CraftedDevAgent MUST call:

- `path_security.validate_write_path()`

## Prompt Construction / Document Loading

- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- External document context MUST be placed in the USER prompt.
- External document context MUST NOT be placed in the SYSTEM prompt.

## Security Refusal Handling

When the LLM returns `SECURITY_REFUSAL`:

- stop
- gate
- log
- never retry to bypass

## Testing Toolchain

Required toolchain integrations:

- `pytest`
- `ruff`
- `mypy`

Required test command before making changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```