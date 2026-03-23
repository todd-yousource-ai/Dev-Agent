# Interface Contracts - FullPlatform

This document defines the wire-format and API contract reference for the **FullPlatform** subsystem based on the provided TRD interface content.

## Data Structures

### ConsensusRunRequest

Request payload for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Free-form task description. |
| `context` | `string` | yes | Context string provided to the consensus engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | yes | Must always be passed. |

#### Notes
- Invocation contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Response object returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Final generated code output. |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | yes | Must be exactly `block` for policy denial records. |

#### Notes
- A VTZ policy denial **MUST** produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Audit event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | Must be globally unique. Must be generated via CSPRNG. Must not be sequential. |
| `session_id` | `string` | yes | Session identifier. |
| `ctx_id` | `string` | yes | CTX-ID associated with the action. |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | yes | Event type identifier. |
| `payload_hash` | `string` | yes | Must be SHA-256 of the serialized action payload. |

#### Notes
- Every action outcome (`allow`, `restrict`, `block`) **MUST** emit a TrustFlow event.
- Emission **MUST** be synchronous in the enforcement path.
- Async buffering is **not permitted**.
- Failed emission is a WARN-level audit event and must not be silently skipped.
- TrustFlow emission failure must be logged and surfaced.

---

### CTX-ID Token

Logical token used for trust and session validation.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Immutable once issued. |
| `session_id` | `string` | yes | Bound session identifier. |
| `vtz` | `string` | yes | Every agent session is bound to exactly one VTZ at issuance time. |

#### Behavioral constraints
- CTX-ID tokens are **IMMUTABLE** once issued.
- Rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID must be rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Identity must never be inferred from context when CTX-ID is missing.

---

### AgentActionPayload

Serialized action payload referenced by TrustFlow hashing and CAL/VTZ enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | yes | Must correspond to the current session. |
| `ctx_id` | `string` | yes | Must be validated first before any processing. |
| `action` | `string` | yes | Action identifier being processed. |
| `payload` | `object` | yes | Serialized action payload used to compute `payload_hash`. |

#### Notes
- `payload_hash` in `TrustFlowEvent` must be the SHA-256 of the serialized `AgentActionPayload.payload`.

---

### SecurityRefusalSignal

Special LLM output condition.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | `"SECURITY_REFUSAL"` | yes | Exact literal value. |

#### Required handling
- On `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.

---

## Enums and Constants

### Language

Allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### VTZ Verdict

Allowed value defined by the provided interface contract:

- `"block"`

### Action Outcome

TrustFlow emission is required for every action outcome:

- `"allow"`
- `"restrict"`
- `"block"`

### Special Security Output

- `"SECURITY_REFUSAL"`

### Trust Constants / Requirements

#### `payload_hash`
- Algorithm: `SHA-256`

#### `event_id`
- Must be globally unique
- Must use CSPRNG
- Must not be sequential

#### `ts`
- UTC Unix timestamp
- Millisecond precision

### Generation System Selection Constants

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Forbidden Patterns

These are prohibited interface/implementation behaviors and therefore part of the effective subsystem contract.

#### Forbidden fix arbitration
```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

#### Required fix arbitration
- Use `_score_fix()`
- Fix loop strategy is selected via `_choose_strategy(failure_type, attempt, records)`

#### Forbidden Swift force unwrap
```swift
let value = optional!
```

#### Forbidden LLM API call from Swift
```swift
let client = AnthropicClient(apiKey: keychainValue)
```

#### Forbidden backend Keychain read
```swift
let token = KeychainKit.read("github_token")
```

#### Keychain boundary
- Only Swift reads Keychain
- Only to deliver via XPC
- Python reads nothing from Keychain

---

## Validation Rules

### 1. Entry Point Enforcement

Every entry point that processes an agent action **MUST**:

1. Call CTX-ID validation first.
2. Immediately reject on CTX-ID validation failure.
3. Check the action against VTZ policy before execution.
4. Emit a TrustFlow event for every outcome.
5. Log and surface TrustFlow emission failure.

### 2. CTX-ID Validation

- CTX-ID validation must happen before any partial processing.
- CTX-ID tokens are immutable after issuance.
- Rotation invalidates the previous token immediately.
- Expired tokens must be rejected.
- Missing tokens must be treated as `UNTRUSTED`.
- Validation must use TrustLock public key.
- Software-only validation is rejected.

### 3. VTZ Enforcement

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

### 4. TrustFlow Emission

Each emitted `TrustFlowEvent` must satisfy:

- `event_id` present and globally unique
- `session_id` present
- `ctx_id` present
- `ts` present as UTC Unix timestamp with millisecond precision
- `event_type` present
- `payload_hash` present as SHA-256 of serialized action payload

Emission constraints:

- Synchronous in enforcement path
- No async buffering
- Failure is WARN-level audit event
- Failure must not be silent

### 5. Consensus Engine Invocation

- `language` must always be provided.
- Valid values are only:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

### 6. Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before being included in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`, stop, gate, log, and do not retry.

### 7. Python Backend Contract

- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Tests use `pytest`
- Tests live in `tests/` and mirror `src/` structure
- `ruff` must pass
- `mypy` must pass
- Test coverage must be `>= 85%` on all new modules
- `pyyaml` must be in `requirements.txt`

### 8. Pre-Implementation Agent Workflow

Before writing code:

1. Find the owning TRD in `README.md`.
2. Read relevant TRD sections, especially:
   - interfaces
   - error contracts
   - security
   - testing requirements
3. Check `TRD-11` if the change touches:
   - credentials
   - external content
   - generated code
   - CI
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## Wire Format Examples

## Valid Payloads

### Valid `ConsensusRunRequest`

```json
{
  "task": "Implement: FullPlatform subsystem",
  "context": "Subsystem requirements and interfaces",
  "language": "python"
}
```

### Valid `ConsensusRunResult`

```json
{
  "final_code": "from dataclasses import dataclass\n..."
}
```

### Valid `TrustFlowEvent`

```json
{
  "event_id": "9d6c2c7d-9e5a-4b37-a4a9-2f7d2c3a5e11",
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961e3a001a8c4d8d1bbf4c8a3"
}
```

### Valid `VTZEnforcementDecision`

```json
{
  "verdict": "block"
}
```

### Valid `SecurityRefusalSignal`

```json
{
  "type": "SECURITY_REFUSAL"
}
```

## Invalid Payloads

### Invalid `ConsensusRunRequest` - missing language

```json
{
  "task": "Implement: FullPlatform subsystem",
  "context": "Subsystem requirements and interfaces"
}
```

Reason:
- `language` is required.

### Invalid `ConsensusRunRequest` - unsupported language

```json
{
  "task": "Implement: FullPlatform subsystem",
  "context": "Subsystem requirements and interfaces",
  "language": "java"
}
```

Reason:
- `language` must be one of `"python" | "swift" | "go" | "typescript" | "rust"`.

### Invalid `TrustFlowEvent` - missing required fields

```json
{
  "event_id": "123",
  "session_id": "sess_123"
}
```

Reason:
- Missing `ctx_id`, `ts`, `event_type`, and `payload_hash`.

### Invalid `VTZEnforcementDecision` - wrong verdict

```json
{
  "verdict": "allow"
}
```

Reason:
- For the defined denial record, `verdict` must be exactly `"block"`.

### Invalid `SecurityRefusalSignal` - wrong literal

```json
{
  "type": "security_refusal"
}
```

Reason:
- `type` must be exactly `"SECURITY_REFUSAL"`.

---

## Integration Points

## Consensus Engine

### Invocation
```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### Selection behavior
- `language="swift"` → `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `language="python"` → `GENERATION_SYSTEM`

### Fix behavior
- Strategy selection uses `_choose_strategy(failure_type, attempt, records)`
- Fix arbitration uses `_score_fix()`
- Length-based arbitration is forbidden

---

## CAL Enforcement Path

Integrated requirements for any agent-action entry point:

1. Validate `ctx_id`
2. Reject immediately on validation failure
3. Enforce VTZ policy
4. If denied, produce `VTZEnforcementDecision` with `verdict="block"`
5. Emit synchronous `TrustFlowEvent`
6. Log and surface emission failure

---

## TrustLock

CTX-ID validation integration requirements:

- Validate against TrustLock public key
- Do not use software-only validation
- Missing CTX-ID is `UNTRUSTED`

---

## Path Security

Before any disk write:

```python
path_security.validate_write_path()
```

All file paths written to disk must pass this validation before write.

---

## Injection Scanning

All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.

Additional prompt-placement rule:

- External document context goes in the USER prompt
- Never in the SYSTEM prompt

---

## Keychain / XPC Boundary

- Swift may read Keychain
- Swift may deliver via XPC
- Python must not read Keychain

---

## Test and Quality Tooling

Required integration/tooling contracts:

- `pytest`
- `ruff`
- `mypy`
- `pyyaml`

Test command:

```bash
cd src && pytest ../tests/ -v --tb=short
```