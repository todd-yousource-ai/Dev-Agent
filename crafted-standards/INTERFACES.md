# Interface Contracts - CraftedDevAgent

## Scope

This document defines the wire format and API contract for the CraftedDevAgent subsystem based on the provided TRD interface content and mandatory crafted component contracts.

If an implementation violates any requirement in this document, it is non-conformant.

---

## Data Structures

### ConsensusRunRequest

Request passed to the consensus engine.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Human-readable implementation task. Example source usage: `f"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string supplied to the consensus engine. External document context, if any, MUST be included in the USER prompt only, never the SYSTEM prompt. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. Values are exact and case-sensitive. |

#### Required call shape

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

#### Constraints

- `language` MUST always be present.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.
- Implementations MUST NOT omit `language`.

---

### ConsensusRunResult

Result returned from the consensus engine.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Final generated code selected by consensus. |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies execution.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | Yes | MUST be exactly `block` when VTZ policy denial occurs. |

#### Constraints

- A VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Audit/enforcement event emitted for every action outcome.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event classification for the action outcome. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Constraints

- Every TrustFlow event MUST include all fields listed above.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be treated as a WARN-level audit event.
- Failed emission MUST NOT be silently skipped.
- Every action outcome `allow`, `restrict`, or `block` MUST emit a TrustFlow event.

---

### CTXIDToken

Immutable context identity token.

#### Fields

The TRD excerpt does not define token field-level members beyond the token identifier itself as `ctx_id`. The following wire-visible token handle is therefore required:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. Missing value MUST be treated as `UNTRUSTED`. Expired values MUST be rejected. Must validate against TrustLock public key. |

#### Constraints

- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- Validation MUST be against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from ambient context when `ctx_id` is missing.

---

### AgentActionEnvelope

Minimal action-processing envelope implied by CAL/VTZ/TrustFlow requirements.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | Yes | Required for TrustFlow emission. |
| `ctx_id` | `string` | Yes | MUST be validated first before any partial processing. Missing value is treated as `UNTRUSTED`. |
| `action` | `object` | Yes | Serialized action payload subject to VTZ enforcement and payload hashing. |

#### Constraints

- Every entry point that processes an agent action MUST validate `ctx_id` first.
- On CTX-ID validation failure, processing MUST terminate immediately.
- No partial processing is permitted before CTX-ID validation succeeds.
- Every action MUST be checked against VTZ policy before execution.
- Serialized `action` payload is the input to `payload_hash` generation using SHA-256.

---

### FixStrategySelectionInput

Input shape implied by failure-type-aware fix loop strategy selection.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `string` | Yes | Used by `_choose_strategy(failure_type, attempt, records)`. |
| `attempt` | `integer` | Yes | Retry/fix attempt counter. |
| `records` | `array` | Yes | Historical records used by `_choose_strategy(...)`. |

#### Constraints

- Fix loop strategy MUST be failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup-table strategy selection is non-conformant.

---

### FixArbitrationInput

Input shape implied by fix arbitration scoring.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `claude_fix` | `string` | Yes | Candidate fix output. |
| `openai_fix` | `string` | Yes | Candidate fix output. |
| `assertion_tokens` | `array[string]` | Yes | Tokens derived from assertions and used for overlap scoring. |

#### Constraints

- Fix arbitration MUST use `_score_fix()`.
- `_score_fix()` is based on assertion token overlap.
- Length-based arbitration is forbidden.

---

## Enums and Constants

### Language

Exact allowed values for `ConsensusRunRequest.language`:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

These values are case-sensitive.

---

### ActionOutcome

TrustFlow emission is required for every action outcome:

- `allow`
- `restrict`
- `block`

---

### VTZVerdict

Defined value required by the TRD excerpt:

- `block`

---

### CTXIDState

Derived wire-relevant states from the contract text:

- `UNTRUSTED` — applied when CTX-ID is missing

---

### Reserved/Referenced System Selectors

These identifiers are referenced by contract and must be used exactly as written when selected by implementation logic:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

---

### Reserved Security Refusal Marker

- `SECURITY_REFUSAL`

When this output is seen from the LLM:
- stop
- gate
- log
- never retry to bypass

---

### Forbidden Patterns

The following behaviors are explicitly forbidden:

#### Length-based fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

#### Swift force unwrap

```swift
let value = optional!
```

#### LLM API call from Swift

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

#### Keychain read for backend

```swift
let token = KeychainKit.read("github_token")
```

Constraint:
- Only Swift reads Keychain, only to deliver via XPC.
- Python reads nothing from Keychain.

---

## Validation Rules

## 1. Before-Change Operational Contract

Before implementing changes to this subsystem:

1. Find the TRD that owns the component being modified.
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
4. Run existing tests before making changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## 2. CAL Enforcement Rules

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur first.
2. If CTX-ID validation fails, the action MUST be rejected immediately.
3. No partial processing is allowed before CTX-ID validation succeeds.
4. VTZ policy check MUST occur before execution.
5. VTZ denial MUST produce a `VTZEnforcementDecision` with:
   - `verdict = "block"`
6. Every action outcome MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST:
   - not silently continue
   - be logged
   - be surfaced

---

## 3. TrustFlow Validation Rules

For every `TrustFlowEvent`:

- `event_id` MUST be globally unique.
- `event_id` MUST come from CSPRNG.
- `event_id` MUST NOT be sequential.
- `ts` MUST be a UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is forbidden.
- Failed emission MUST be a WARN-level audit event.

---

## 4. CTX-ID Validation Rules

- CTX-ID tokens are immutable once issued.
- Rotation MUST create a new token.
- Previous token MUST be invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- Validation MUST use TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST map to `UNTRUSTED`.

---

## 5. VTZ Enforcement Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 6. Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log HTTP status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`, stop, gate, and log. Never retry to bypass.

---

## 7. Python Backend Implementation Rules

- Python version MUST be `3.12`.
- Every function MUST have type annotations.
- Backend code MUST use `async/await` throughout.
- No blocking calls on the event loop.
- All structured data MUST use dataclasses.
- Tests MUST use `pytest`.
- Tests MUST live in `tests/` and mirror `src/` structure.
- `ruff` MUST pass clean.
- `mypy` MUST pass clean.
- Test coverage on all new modules MUST be at least `85%`.
- `pyyaml` MUST be present in `requirements.txt`.

---

## 8. Consensus Engine Rules

- `language` MUST always be passed to `self._consensus.run(...)`.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` and optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.
- Fix loop strategy MUST be selected via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()`.
- Response-length selection is forbidden.

---

## Wire Format Examples

## Valid Payloads

### Valid `ConsensusRunRequest`

```json
{
  "task": "Implement: Add request validation",
  "context": "Use async Python 3.12 patterns and validate write paths before disk writes.",
  "language": "python"
}
```

### Valid `ConsensusRunResult`

```json
{
  "final_code": "from dataclasses import dataclass\n\n@dataclass\nclass Example:\n    value: str\n"
}
```

### Valid `TrustFlowEvent`

```json
{
  "event_id": "3d2af6f7-1c89-4d9a-9c37-8b8e3a4f2d10",
  "session_id": "sess_42",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa13514a978d1f5c2fcf3f1b6f8d6c7e"
}
```

### Valid `VTZEnforcementDecision`

```json
{
  "verdict": "block"
}
```

### Valid `AgentActionEnvelope`

```json
{
  "session_id": "sess_42",
  "ctx_id": "ctx_abc123",
  "action": {
    "tool": "write_file",
    "path": "/workspace/output.txt",
    "content": "hello"
  }
}
```

### Valid missing-CTX handling semantic

A missing CTX-ID is not valid for trusted processing, but its semantic classification is defined as `UNTRUSTED`.

Example envelope before rejection:

```json
{
  "session_id": "sess_42",
  "action": {
    "tool": "run_tests"
  }
}
```

Required behavior:
- classify as `UNTRUSTED`
- reject before partial processing
- do not infer identity from session or other context

---

## Invalid Payloads

### Invalid `ConsensusRunRequest` with missing language

```json
{
  "task": "Implement: Add request validation",
  "context": "Use async Python 3.12 patterns."
}
```

Reason:
- `language` is required

---

### Invalid `ConsensusRunRequest` with unsupported language

```json
{
  "task": "Implement: Add request validation",
  "context": "Use async patterns.",
  "language": "java"
}
```

Reason:
- `language` must be one of:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`

---

### Invalid `VTZEnforcementDecision`

```json
{
  "verdict": "allow"
}
```

Reason:
- TRD-defined required denial record uses `verdict=block`

---

### Invalid `TrustFlowEvent` missing payload hash

```json
{
  "event_id": "evt_1",
  "session_id": "sess_42",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600123,
  "event_type": "allow"
}
```

Reason:
- `payload_hash` is required

---

### Invalid TrustFlow event with non-millisecond timestamp semantics

```json
{
  "event_id": "evt_2",
  "session_id": "sess_42",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600,
  "event_type": "allow",
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa13514a978d1f5c2fcf3f1b6f8d6c7e"
}
```

Reason:
- `ts` must be a UTC Unix timestamp with millisecond precision

---

### Invalid implementation pattern: length-based arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- length-based arbitration is forbidden
- must use `_score_fix()`

---

### Invalid implementation pattern: unsafe subprocess

```python
subprocess.run(cmd, shell=True)
```

Reason:
- `shell=True` is forbidden

---

### Invalid implementation pattern: unsafe code execution

```python
eval(untrusted_text)
exec(generated_text)
```

Reason:
- `eval()` and `exec()` on generated or external content are forbidden

---

### Invalid implementation pattern: writing without path validation

```python
with open(user_path, "w") as f:
    f.write(content)
```

Reason:
- all file paths written to disk must pass `path_security.validate_write_path()` before any write

---

## Integration Points

## Consensus Engine

### Method Contract

```python
await self._consensus.run(task=<string>, context=<string>, language=<allowed language>)
```

### Input Requirements

- `task`: required string
- `context`: required string
- `language`: required enum

### Output Requirements

- result object MUST expose `final_code: string`

### Behavioral Requirements

- Always pass `language`
- System prompt selection depends on `language`:
  - `swift` -> `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
  - `python` -> `GENERATION_SYSTEM`

---

## Strategy Selection

### Method Contract

```python
_choose_strategy(failure_type, attempt, records)
```

### Requirements

- Must be used for fix loop strategy
- Must be failure-type-aware
- Must not be replaced by static lookup-table logic

---

## Fix Arbitration

### Method Contract

```python
_score_fix()
```

### Requirements

- Must determine arbitration winner based on assertion token overlap
- Must not use response length

---

## Path Security

### Method Contract

```python
path_security.validate_write_path()
```

### Requirements

- MUST be called before any disk write
- Any attempted write without prior validation is non-conformant

---

## TrustLock Validation

### Integration Requirement

- CTX-ID validation MUST be against TrustLock public key
- Software-only validation is rejected

---

## XPC / Keychain Boundary

### Requirements

- Only Swift may read Keychain
- Swift may read Keychain only to deliver via XPC
- Python backend reads nothing from Keychain
- Swift must not make LLM API calls directly

---

## Testing Interface Obligations

Implementations touching this subsystem MUST support validation by:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Additional required toolchain checks:

- `ruff`
- `mypy`

Coverage requirement:

- `>= 85%` on all new modules

---

## Conformance Summary

A conformant CraftedDevAgent implementation MUST, at minimum:

- validate CTX-ID first
- reject immediately on CTX-ID failure
- enforce VTZ before execution
- emit synchronous TrustFlow events for all action outcomes
- use exact TrustFlow fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- pass `language` on every consensus run
- use `_choose_strategy(failure_type, attempt, records)`
- use `_score_fix()`
- validate disk write paths with `path_security.validate_write_path()`
- obey all listed security prohibitions
- satisfy Python 3.12, async, typing, dataclass, lint, type-check, and test requirements