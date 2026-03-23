# Interface Contracts - FullPlatform

This document is the definitive wire format and API contract reference for the **FullPlatform** subsystem.

All fields, types, and constraints below are normative. Implementations are non-conformant if they omit required fields, change field names, change value spellings, or violate validation and enforcement rules.

## Data Structures

### ConsensusRunRequest

Request payload for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Freeform task description. |
| `context` | `string` | Yes | Context string passed to the engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be provided. |

#### Constraints
- `language` is mandatory on every consensus call.
- Exact invocation contract:

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

Response object from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code result. |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | Yes | Must be exactly `block` for VTZ policy denial records. |

#### Constraints
- VTZ policy denial **MUST** produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Audit/event record emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique. Generated via CSPRNG, not sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID token identifier. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | SHA-256 of the serialized action payload. |

#### Constraints
- Every TrustFlow event **MUST** include all fields listed above.
- `event_id` **MUST** be globally unique.
- `event_id` **MUST** use CSPRNG generation.
- `event_id` **MUST NOT** be sequential.
- `ts` **MUST** be UTC Unix timestamp with millisecond precision.
- `payload_hash` **MUST** be SHA-256 of the serialized action payload.

---

### SecurityRefusalOutput

Special LLM output indicating a hard security gate.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `value` | `"SECURITY_REFUSAL"` | Yes | Exact literal value. |

#### Constraints
- When `SECURITY_REFUSAL` is encountered: stop, gate, log.
- Never retry to bypass a `SECURITY_REFUSAL`.

---

## Enums and Constants

### Language

Allowed `ConsensusRunRequest.language` values:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### System Selection Constants

These values are selected based on `language`:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

#### Selection Rules
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

### Verdict

Allowed known `VTZEnforcementDecision.verdict` values in this contract:

- `"block"`

### Special Security Literal

- `"SECURITY_REFUSAL"`

---

## Validation Rules

## FullPlatform Pre-Implementation Requirements

Before modifying a component in this subsystem:

1. Find the TRD that owns the component you are modifying.
2. Read the relevant TRD sections, especially:
   - interfaces
   - error contracts
   - security
   - testing requirements
3. Check TRD-11 if the change touches:
   - credentials
   - external content
   - generated code
   - CI
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

### Consensus Engine Rules

- Every consensus invocation **MUST** pass `language`.
- `language` **MUST** be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Length-based fix arbitration is forbidden.

#### Forbidden pattern

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

---

### Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk **MUST** pass `path_security.validate_write_path()` before any write.
- All loaded document chunks **MUST** pass injection scanning before inclusion in any LLM prompt.
- Context from external documents **MUST** go in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` output appears: stop, gate, log. Never retry to bypass.

---

### Python Backend Rules

- Python version: `3.12`
- Type annotations are required on every function.
- Backend code **MUST** use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses are required for all structured data.
- Tests **MUST** use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` **MUST** pass clean.
- `mypy` **MUST** pass clean.
- Test coverage on all new modules **MUST** be `>= 85%`.
- `pyyaml` **MUST** be present in `requirements.txt`.

---

### Swift and Cross-Platform Forbidden Patterns

#### Forbidden Swift force unwrap

```swift
let value = optional!
```

#### Forbidden LLM API call from Swift

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

#### Forbidden Keychain read for backend

```swift
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
```

#### Constraint
- Only Swift reads Keychain, only to deliver via XPC.
- Python reads nothing from Keychain.

---

### CAL Enforcement Contract

Every entry point that processes an agent action:

1. **MUST** call CTX-ID validation first.
2. CTX-ID validation failure **MUST** result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action **MUST** be checked against VTZ policy before execution.
5. VTZ policy denial **MUST** produce a `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) **MUST** emit a TrustFlow event.
7. TrustFlow emission failure **MUST NOT** silently continue.
8. TrustFlow emission failure **MUST** be logged and surfaced.

---

### TrustFlow Emission Contract

- Every TrustFlow event **MUST** include:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- Emission **MUST** be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission is not a silent skip.

---

### CTX-ID Contract

- CTX-ID tokens are immutable once issued.
- No field modification is permitted after issuance.
- CTX-ID rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID **MUST** be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID **MUST** be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID **MUST** be treated as `UNTRUSTED`.
- Identity **MUST NOT** be inferred from context when CTX-ID is missing.

---

### VTZ Enforcement Contract

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## Wire Format Examples

### Valid: ConsensusRunRequest

```json
{
  "task": "Implement: Add authentication middleware",
  "context": "Relevant subsystem context here",
  "language": "python"
}
```

### Valid: ConsensusRunResult

```json
{
  "final_code": "async def handler() -> None:\n    pass\n"
}
```

### Valid: TrustFlowEvent

```json
{
  "event_id": "9d4d8a2c-4e7d-4ff4-8f97-2d7d4a0f55c2",
  "session_id": "sess_01HXYZABC",
  "ctx_id": "ctx_01HXYZDEF",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3d7e5d0b7d4d8b6c0c1e7d8a9f0b1c2d3e4f567890abcdef1234567890abcdef"
}
```

### Valid: VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Valid: SecurityRefusalOutput

```json
{
  "value": "SECURITY_REFUSAL"
}
```

### Invalid: missing `language`

```json
{
  "task": "Implement: Add authentication middleware",
  "context": "Relevant subsystem context here"
}
```

Reason:
- `language` is required.

---

### Invalid: unsupported `language`

```json
{
  "task": "Implement: Add authentication middleware",
  "context": "Relevant subsystem context here",
  "language": "java"
}
```

Reason:
- `language` must be one of `"python" | "swift" | "go" | "typescript" | "rust"`.

---

### Invalid: TrustFlowEvent missing required field

```json
{
  "event_id": "9d4d8a2c-4e7d-4ff4-8f97-2d7d4a0f55c2",
  "session_id": "sess_01HXYZABC",
  "ctx_id": "ctx_01HXYZDEF",
  "ts": 1735689600123,
  "event_type": "allow"
}
```

Reason:
- `payload_hash` is required.

---

### Invalid: non-conformant VTZ denial record

```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ policy denial record must use exact value `block`.

---

### Invalid: non-literal security refusal

```json
{
  "value": "security_refusal"
}
```

Reason:
- Exact literal must be `SECURITY_REFUSAL`.

---

## Integration Points

### Consensus Engine

Invocation contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

#### Integration constraints
- `language` must always be passed.
- Swift generation path uses `SWIFT_GENERATION_SYSTEM`.
- Optional `SWIFT_UI_ADDENDUM` is injected when UI keywords are detected.
- Python generation path uses `GENERATION_SYSTEM`.

---

### Path Security

Before any disk write:

```python
path_security.validate_write_path()
```

#### Integration constraints
- All file paths written to disk must be validated before write.

---

### Injection Scanning

#### Integration constraints
- Every loaded document chunk must pass injection scanning before inclusion in any LLM prompt.

---

### Prompt Placement

#### Integration constraints
- Context from external documents belongs in the USER prompt.
- External document context must never be placed in the SYSTEM prompt.

---

### TrustLock / CTX-ID Validation

#### Integration constraints
- CTX-ID validation occurs first in every entry point that processes an agent action.
- Validation must be against TrustLock public key.
- Software-only validation is rejected.

---

### VTZ Policy Enforcement

#### Integration constraints
- Every action is checked against VTZ policy before execution.
- Cross-VTZ calls require explicit authorization.
- Denial produces `VTZEnforcementDecision` with `verdict=block`.

---

### TrustFlow Emission

#### Integration constraints
- Every action outcome emits a TrustFlow event.
- Emission is synchronous in the enforcement path.
- Failure is WARN-level, logged, and surfaced.

---

### Test Execution

Required existing test command:

```bash
cd src && pytest ../tests/ -v --tb=short
```

#### Integration constraints
- Tests must run before making changes.
- `pytest` is the required framework.

---

### Tooling and Quality Gates

#### Integration constraints
- `ruff` must pass clean.
- `mypy` must pass clean.
- Coverage for new modules must be at least `85%`.
- `pyyaml` must exist in `requirements.txt`.