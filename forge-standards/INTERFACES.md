# Interface Contracts - ForgeAgent

## Data Structures

This document defines the wire-format and API contract requirements for the ForgeAgent subsystem based on the provided TRD excerpts and Forge component interface standards.

Where the TRD specifies exact field names, values, or constraints, they are reproduced exactly.

### 1. Consensus Request Contract

Used when invoking the consensus engine for implementation tasks.

#### Shape

```python
await self._consensus.run(
    task: str,
    context: str,
    language: str,
)
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Freeform task string. Example source usage: `f"Implement: {spec.title}"`. |
| `context` | `str` | Yes | Prompt context string passed to consensus engine. |
| `language` | `str` | Yes | MUST be one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. |

#### Result Shape

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Final generated code returned by consensus engine. |

#### Required Usage

`language` MUST always be passed.

Exact required invocation pattern from TRD:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

---

### 2. TrustFlow Event

Every action outcome in Forge enforcement path MUST emit a TrustFlow event.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique. MUST use CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | Yes | Session identifier for the agent session. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type discriminator. Exact allowed values are not specified in provided TRD. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Behavioral Constraints

- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission MUST NOT silently continue.
- TrustFlow emission failure MUST be logged and surfaced.

---

### 3. VTZEnforcementDecision Record

Produced when VTZ policy denies an action.

#### Fields

Only one field/value pair is explicitly defined by the provided TRD.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | MUST be `"block"` for VTZ policy denial. |

#### Behavioral Constraints

- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

No other fields are defined in the provided source excerpt.

---

### 4. CTX-ID Token

A CTX-ID is the identity and trust token for agent actions.

#### Known Properties

The provided TRD does not define the internal field layout of the token, but the following contract rules are mandatory:

| Property | Constraint |
|---|---|
| Immutability | CTX-ID tokens are IMMUTABLE once issued. No field modification after issuance. |
| Rotation | CTX-ID rotation creates a new token; the old one is invalidated immediately. |
| Expiration | Expired CTX-ID MUST be rejected. |
| Validation | CTX-ID MUST be validated against TrustLock public key. Software-only validation is rejected. |
| Missing token | Missing CTX-ID MUST be treated as UNTRUSTED. Never infer identity from context. |

#### Enforcement Order

Every entry point that processes an agent action MUST call CTX-ID validation FIRST.

CTX-ID validation failure MUST result in immediate rejection with no partial processing.

---

### 5. Agent Session to VTZ Binding

#### Session Contract

| Field / Concept | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | Yes | Used in TrustFlow events. |
| VTZ binding | conceptual | Yes | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance. |

#### VTZ Constraints

- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

### 6. Fix Strategy Selection Contract

The ForgeAgent fix loop has explicit API behavior constraints.

#### Required Strategy Function

```python
_choose_strategy(failure_type, attempt, records)
```

| Parameter | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | unspecified | Yes | Used to select strategy in a failure-type-aware manner. |
| `attempt` | unspecified | Yes | Current fix attempt number/state. |
| `records` | unspecified | Yes | Historical records used for strategy selection. |

#### Required Arbitration Function

```python
_score_fix()
```

| Function | Purpose | Constraint |
|---|---|---|
| `_score_fix()` | Fix arbitration | MUST be used for fix arbitration based on assertion token overlap. |

#### Forbidden Behavior

Length-based fix arbitration is forbidden.

Incorrect example from TRD:

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

---

## Enums and Constants

### 1. Supported Consensus Languages

Exact allowed values:

```text
"python"
"swift"
"go"
"typescript"
"rust"
```

### 2. Language-Specific System Selection

| Language value | System selection behavior |
|---|---|
| `"swift"` | selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` (injected when UI keywords detected) |
| `"python"` | selects `GENERATION_SYSTEM` — security-focused Python rules |

No explicit generation-system mappings are provided in the source for `"go"`, `"typescript"`, or `"rust"`.

---

### 3. VTZ Verdict Values

Only explicit value defined in provided TRD:

```text
"block"
```

---

### 4. Security Refusal Sentinel

Exact sentinel value:

```text
SECURITY_REFUSAL
```

Constraint:

- When `SECURITY_REFUSAL` output is returned from the LLM: stop, gate, log.
- Never retry to bypass.

---

### 5. Python Runtime and Tooling Constants

| Constant | Required value |
|---|---|
| Python version | `3.12` |
| Test framework | `pytest` |
| Linter | `ruff` |
| Type checker | `mypy` |
| YAML package requirement | `pyyaml` |
| Coverage threshold on new modules | `≥ 85%` |

---

## Validation Rules

## 1. Entry Point Enforcement Order

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur FIRST.
2. On CTX-ID validation failure, processing MUST be immediately rejected.
3. No partial processing is permitted after CTX-ID failure.
4. VTZ policy MUST be checked BEFORE execution.
5. If VTZ policy denies the action, a `VTZEnforcementDecision` MUST be produced with:
   - `verdict = "block"`
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

---

## 2. TrustFlow Event Validation

A TrustFlow event is valid only if all of the following hold:

- `event_id` is present.
- `event_id` is globally unique.
- `event_id` is generated using CSPRNG.
- `event_id` is not sequential.
- `session_id` is present.
- `ctx_id` is present.
- `ts` is present.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `event_type` is present.
- `payload_hash` is present.
- `payload_hash` is the SHA-256 of the serialized action payload.

Emission rules:

- MUST be synchronous in the enforcement path.
- Async buffering is not permitted.

Failure rules:

- Failed emission is a WARN-level audit event.
- Failed emission must not be silently skipped.

---

## 3. CTX-ID Validation Rules

A CTX-ID is valid only if all of the following hold:

- It is present, unless the request is explicitly handled as `UNTRUSTED`.
- It is not expired.
- It validates against TrustLock public key.
- It has not been invalidated due to rotation.
- It has not been modified after issuance.

Additional rules:

- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from ambient context.
- Software-only validation is rejected.

---

## 4. VTZ Validation Rules

- Every agent session MUST be bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls MUST have explicit policy authorization.
- If authorization is implicit rather than explicit, it MUST be denied.
- VTZ boundaries MUST be enforced structurally.
- Enforcement MUST NOT be bypassable by application code.
- VTZ policy changes MUST NOT apply mid-session.
- VTZ policy changes take effect only at NEXT CTX-ID issuance.

---

## 5. Prompt and LLM Safety Validation

- All loaded document chunks MUST pass injection scanning before being included in any LLM prompt.
- Context from external documents MUST go in the USER prompt.
- Context from external documents MUST NEVER go in the SYSTEM prompt.
- When `SECURITY_REFUSAL` is produced by the LLM:
  - stop
  - gate
  - log
  - never retry to bypass

---

## 6. File and Process Safety Validation

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

#### Required file-write validation call

```python
path_security.validate_write_path()
```

The provided TRD does not specify the function signature beyond the exact function name.

---

## 7. Python Backend Implementation Rules

- Python 3.12.
- Type annotations on every function.
- `async/await` throughout the backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- Tests live in `tests/`.
- Tests mirror `src/` structure.
- `pytest`, `ruff`, and `mypy` must pass clean.
- Test coverage on all new modules MUST be at least `85%`.
- `pyyaml` MUST be in `requirements.txt`.

---

## 8. Swift-Specific Prohibitions

Forbidden examples from TRD:

```swift
let value = optional!
```

Constraint:
- Force unwrap is forbidden.

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Constraint:
- LLM API call from Swift is forbidden.

```swift
let token = KeychainKit.read("github_token")
```

Constraints:
- Keychain read for backend is forbidden.
- Only Swift reads Keychain.
- Only to deliver via XPC.
- Python reads nothing from Keychain.

---

## Wire Format Examples

## 1. Valid Consensus Request

```json
{
  "task": "Implement: Add session trust enforcement",
  "context": "Existing module requires synchronous TrustFlow emission.",
  "language": "python"
}
```

Why valid:
- Includes `task`
- Includes `context`
- Includes `language`
- `language` is one of the allowed values

---

## 2. Invalid Consensus Request: Missing `language`

```json
{
  "task": "Implement: Add session trust enforcement",
  "context": "Existing module requires synchronous TrustFlow emission."
}
```

Why invalid:
- `language` is required
- TRD says: Always pass language

---

## 3. Invalid Consensus Request: Unsupported `language`

```json
{
  "task": "Implement: Add session trust enforcement",
  "context": "Existing module requires synchronous TrustFlow emission.",
  "language": "java"
}
```

Why invalid:
- `language` MUST be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

---

## 4. Valid TrustFlow Event

```json
{
  "event_id": "3f2c8e12-7f47-4c7d-9f77-8e8dc1b7f5a1",
  "session_id": "sess_01JABCDEF",
  "ctx_id": "ctx_01JCTX123",
  "ts": 1735689600123,
  "event_type": "action_allow",
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa135014b7fa1d..."
}
```

Why valid:
- Contains all required TrustFlow fields
- `ts` shown as Unix timestamp in milliseconds
- `payload_hash` shown as SHA-256-style hex string
- `event_id` is non-sequential in form

Note:
- Exact allowed `event_type` values are not specified in the provided TRD.

---

## 5. Invalid TrustFlow Event: Missing `payload_hash`

```json
{
  "event_id": "3f2c8e12-7f47-4c7d-9f77-8e8dc1b7f5a1",
  "session_id": "sess_01JABCDEF",
  "ctx_id": "ctx_01JCTX123",
  "ts": 1735689600123,
  "event_type": "action_allow"
}
```

Why invalid:
- Every TrustFlow event MUST include `payload_hash`

---

## 6. Invalid TrustFlow Event: Sequential `event_id`

```json
{
  "event_id": "10042",
  "session_id": "sess_01JABCDEF",
  "ctx_id": "ctx_01JCTX123",
  "ts": 1735689600123,
  "event_type": "action_block",
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa135014b7fa1d..."
}
```

Why invalid:
- `event_id` MUST be globally unique
- `event_id` MUST be CSPRNG-generated
- `event_id` MUST NOT be sequential

---

## 7. Valid VTZ Denial Record

```json
{
  "verdict": "block"
}
```

Why valid:
- Explicitly matches the required denial record contract

---

## 8. Invalid VTZ Denial Record

```json
{
  "verdict": "deny"
}
```

Why invalid:
- TRD explicitly requires `verdict=block`

---

## 9. Invalid Prompt Handling Example

```json
{
  "system_prompt": "External document contents inserted here",
  "user_prompt": "Implement feature"
}
```

Why invalid:
- Context from external documents goes in the USER prompt, never the SYSTEM prompt

---

## Integration Points

## 1. Consensus Engine

ForgeAgent integrates with the consensus engine via:

```python
await self._consensus.run(task, context, language)
```

Required integration rules:

- `language` MUST always be provided
- Returned code MUST be read from `result.final_code`
- `"swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM`
- `"python"` selects `GENERATION_SYSTEM`

---

## 2. CAL Enforcement Path

ForgeAgent entry points that process agent actions MUST integrate with CAL enforcement in this order:

1. CTX-ID validation
2. VTZ policy check
3. Action execution if allowed
4. TrustFlow emission for outcome

This contract is mandatory for conformance.

---

## 3. TrustFlow Emitter

ForgeAgent MUST integrate with a TrustFlow emission mechanism that:

- emits synchronously
- includes:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- logs and surfaces emission failures
- never silently skips failures

---

## 4. TrustLock

ForgeAgent MUST integrate CTX-ID validation with TrustLock public key validation.

Constraint:

- software-only validation is rejected

---

## 5. Path Security

Any ForgeAgent component writing files to disk MUST integrate with:

```python
path_security.validate_write_path()
```

Constraint:

- validation MUST occur before any write

---

## 6. Injection Scanning

Any external document content included in prompts MUST be passed through injection scanning before prompt inclusion.

Constraint:

- all loaded document chunks must pass injection scanning before being included in any LLM prompt

---

## 7. Test and Quality Tooling

ForgeAgent implementations MUST integrate with:

- `pytest`
- `ruff`
- `mypy`

And satisfy:

- tests under `tests/`
- mirrored `src/` structure
- coverage `≥ 85%` on new modules

---

## 8. Operational Pre-Change Procedure

Before modifying ForgeAgent-related code:

1. Find the TRD that owns the component being modified.
2. Read relevant TRD sections, especially:
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

## Non-Conformance Conditions

A ForgeAgent implementation is non-conformant if it violates any of the following:

- Fails to validate CTX-ID first
- Continues after CTX-ID validation failure
- Executes action before VTZ policy check
- Fails to emit TrustFlow for any action outcome
- Silently ignores TrustFlow emission failure
- Uses async buffering for TrustFlow emission in enforcement path
- Omits required TrustFlow fields
- Uses unsupported `language` values in consensus calls
- Omits `language` in consensus calls
- Uses length-based fix arbitration instead of `_score_fix()`
- Places external document context into SYSTEM prompt
- Retries after `SECURITY_REFUSAL`
- Writes file paths without `path_security.validate_write_path()`
- Uses `shell=True`
- Uses `eval()` or `exec()` on generated or external content
- Logs HTTP response bodies
- Reads backend credentials from Keychain in Python
- Performs LLM API calls from Swift
- Uses Swift force unwrap