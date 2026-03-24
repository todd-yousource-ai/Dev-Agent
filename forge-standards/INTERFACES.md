# Interface Contracts - ForgeAgent

## Data Structures

### ConsensusRunRequest

Request shape for invoking the Consensus Engine from ForgeAgent.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Freeform task description. Example source usage: `f"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string supplied to the engine. External document context, when used, MUST go in the USER prompt, never the SYSTEM prompt. All loaded document chunks MUST pass injection scanning before inclusion. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. Exact allowed values from contract. |

#### Behavioral contract
- ForgeAgent MUST always pass `language` when calling consensus:
  - `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
  - `language="python"` selects `GENERATION_SYSTEM`.
- Fix loop strategy selection MUST use `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration is forbidden.

---

### ConsensusRunResult

Result shape consumed by ForgeAgent from the Consensus Engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output used by ForgeAgent. |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | Yes | Must be exactly `block` when produced for policy denial. |

#### Behavioral contract
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Synchronous audit/event record emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique. Must be generated with CSPRNG; sequential IDs are forbidden. |
| `session_id` | `string` | Yes | Session identifier for the agent session. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. Missing CTX-ID is untrusted and must not be inferred. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event kind for the action outcome. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Behavioral contract
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST NOT silently continue.
- Failed emission is a WARN-level audit event and must be logged and surfaced.

---

### CTXIDToken

Logical token contract used by ForgeAgent entry points.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. Must validate against TrustLock public key. |
| `expired` | `boolean` | No | If true, token MUST be rejected. Clock skew tolerance is deployment-defined. |
| `vtz_id` | `string` | No | Every agent session is bound to exactly one VTZ at CTX-ID issuance. |

#### Behavioral contract
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection with no partial processing.
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token; old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Never infer identity from context.

---

### AgentActionPayload

Serialized action payload used for enforcement and TrustFlow hashing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `payload` | `object` | Yes | Arbitrary serialized action payload. `payload_hash` in `TrustFlowEvent` MUST be SHA-256 of this serialized payload. |

#### Behavioral contract
- All file paths written to disk that originate from action processing MUST pass `path_security.validate_write_path()` before any write.
- Any external/generated content carried by the payload MUST NOT be executed with `eval()` or `exec()`.
- Any subprocess invocation derived from the payload MUST NOT use `shell=True`.

---

## Enums and Constants

### Language

Exact allowed values for `ConsensusRunRequest.language`:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

---

### ActionOutcome

Required action outcomes that trigger TrustFlow emission:

- `allow`
- `restrict`
- `block`

---

### CTX-ID Trust Classification

| Value | Meaning |
|---|---|
| `UNTRUSTED` | Required treatment for missing CTX-ID. |

---

### VTZEnforcementVerdict

| Value | Meaning |
|---|---|
| `block` | Required verdict for VTZ policy denial. |

---

### Special Security Output

| Value | Meaning |
|---|---|
| `SECURITY_REFUSAL` | When seen from the LLM, ForgeAgent must stop, gate, and log. Must never retry to bypass. |

---

### Consensus System Selectors

These names are part of the contract because behavior depends on them:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

---

### Required Functions / Symbols

These symbols are mandated by the interface contract:

- `_choose_strategy(failure_type, attempt, records)`
- `_score_fix()`
- `path_security.validate_write_path()`

---

### Forbidden Patterns

These exact patterns are non-conformant:

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

#### Backend Keychain read from Swift-side backend path
```swift
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
```

---

## Validation Rules

### Entry Point Enforcement Order

For every ForgeAgent entry point that processes an agent action:

1. CTX-ID validation MUST occur first.
2. On CTX-ID validation failure, processing MUST be immediately rejected.
3. VTZ policy check MUST occur before execution.
4. On VTZ denial, a `VTZEnforcementDecision` with `verdict=block` MUST be produced.
5. Every outcome (`allow`, `restrict`, `block`) MUST synchronously emit a `TrustFlowEvent`.

No partial processing is permitted before CTX-ID validation completes successfully.

---

### Consensus Invocation Rules

- ForgeAgent MUST call consensus with:
  - `task`
  - `context`
  - `language`
- `language` is mandatory and must be one of:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`
- Result code MUST be read from `result.final_code`.

Required usage form:
```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

---

### Fix Loop Rules

- Strategy selection MUST be failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()` based on assertion token overlap.
- Response-length-based selection is forbidden.

---

### TrustFlow Validation

A `TrustFlowEvent` is valid only if all of the following are true:

- `event_id` present and globally unique
- `event_id` generated via CSPRNG
- `session_id` present
- `ctx_id` present
- `ts` present as UTC Unix timestamp with millisecond precision
- `event_type` present
- `payload_hash` present and equals SHA-256 of the serialized action payload

Emission constraints:

- Must be synchronous in the enforcement path
- Async buffering not permitted
- Emission failure must be logged and surfaced
- Emission failure cannot be silently skipped

---

### CTX-ID Validation

A CTX-ID is valid only if all of the following are true:

- Token is present
- Token is not expired
- Token validates against TrustLock public key
- Token has not been invalidated by rotation

Additional rules:

- Tokens are immutable once issued
- Rotation invalidates the old token immediately
- Missing token => treat as `UNTRUSTED`
- Identity must never be inferred from surrounding context

---

### VTZ Validation

- Every agent session MUST be bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

### Security Validation

#### Credentials and secrets
- Never hardcode credentials, API keys, tokens, or secrets as string literals.

#### Subprocess
- Never use `shell=True` in subprocess calls.

#### Code execution
- Never call `eval()` or `exec()` on generated or external content.

#### HTTP logging
- Never log HTTP response bodies.
- Log status codes and error types only.

#### File writes
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

#### Prompt construction
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.

#### Security refusal handling
- On `SECURITY_REFUSAL`, ForgeAgent MUST stop, gate, and log.
- ForgeAgent MUST NOT retry to bypass the refusal.

---

### Python Implementation Requirements

These are binding implementation constraints for Python-side ForgeAgent components:

- Python `3.12`
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- `pytest` for tests
- Tests live in `tests/` and mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage `>= 85%` on all new modules
- `pyyaml` must be present in `requirements.txt`

---

## Wire Format Examples

### Valid: ConsensusRunRequest

```json
{
  "task": "Implement: Add TrustFlow emission to ForgeAgent action pipeline",
  "context": "User prompt context only. External document chunks were injection-scanned before inclusion.",
  "language": "python"
}
```

### Invalid: ConsensusRunRequest missing `language`

```json
{
  "task": "Implement: Add TrustFlow emission to ForgeAgent action pipeline",
  "context": "Missing language is non-conformant."
}
```

Reason:
- `language` is required.

---

### Invalid: ConsensusRunRequest with unsupported `language`

```json
{
  "task": "Implement: Add TrustFlow emission to ForgeAgent action pipeline",
  "context": "Unsupported language value.",
  "language": "java"
}
```

Reason:
- `language` must be one of `python`, `swift`, `go`, `typescript`, `rust`.

---

### Valid: TrustFlowEvent

```json
{
  "event_id": "a4d7d1d2-7c49-4d36-a7d7-2e3d3f6d8a11",
  "session_id": "sess_01HV7RZX8M7K4A9C2Q",
  "ctx_id": "ctx_01HV7S3D6YJ6M4N8TQ",
  "ts": 1712345678123,
  "event_type": "block",
  "payload_hash": "7f5c8e9d4a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef01234567"
}
```

Notes:
- `ts` is a UTC Unix timestamp in milliseconds.
- `payload_hash` is SHA-256 of the serialized action payload.

---

### Invalid: TrustFlowEvent with sequential ID semantics and second precision timestamp

```json
{
  "event_id": "42",
  "session_id": "sess_01HV7RZX8M7K4A9C2Q",
  "ctx_id": "ctx_01HV7S3D6YJ6M4N8TQ",
  "ts": 1712345678,
  "event_type": "allow",
  "payload_hash": "abc123"
}
```

Reasons:
- `event_id` must be globally unique and CSPRNG-generated, not sequential.
- `ts` must have millisecond precision.
- `payload_hash` must be SHA-256 of the serialized action payload.

---

### Valid: VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

---

### Invalid: VTZEnforcementDecision wrong verdict for denial record

```json
{
  "verdict": "deny"
}
```

Reason:
- Policy denial record must use exact value `block`.

---

### Valid: AgentActionPayload and corresponding TrustFlow hash relationship

```json
{
  "payload": {
    "action": "write_file",
    "path": "/workspace/output/module.py",
    "contents": "print('hello')"
  }
}
```

Constraints:
- Before any write, `/workspace/output/module.py` must pass `path_security.validate_write_path()`.
- If a `TrustFlowEvent` is emitted for this payload, `payload_hash` must equal SHA-256 of the serialized `payload`.

---

### Invalid: Missing CTX-ID treated as inferred identity

```json
{
  "session_id": "sess_01HV7RZX8M7K4A9C2Q",
  "user_hint": "probably same caller as previous request"
}
```

Reason:
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from context.

---

### Invalid: Forbidden subprocess configuration

```python
subprocess.run(command, shell=True)
```

Reason:
- `shell=True` is forbidden.

---

### Invalid: Forbidden code execution

```python
eval(external_content)
```

Reason:
- `eval()` and `exec()` on generated or external content are forbidden.

---

### Invalid: Forbidden HTTP body logging

```python
logger.error("request failed: %s", response.text)
```

Reason:
- HTTP response bodies must never be logged.

---

## Integration Points

### 1. Consensus Engine

ForgeAgent integrates with the Consensus Engine through an async call returning an object with `final_code`.

Required call contract:
```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Integration requirements:
- Always pass `language`
- Language values are exactly:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`

Behavior selection:
- `swift` => `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `python` => `GENERATION_SYSTEM`

---

### 2. CAL Enforcement Path

ForgeAgent entry points must integrate with CAL enforcement as follows:

- CTX-ID validation first
- Immediate reject on validation failure
- VTZ policy check before action execution
- Produce `VTZEnforcementDecision(verdict="block")` on denial
- Emit `TrustFlowEvent` for every outcome

This is a hard conformance contract.

---

### 3. TrustFlow

ForgeAgent must synchronously emit `TrustFlowEvent` records in the enforcement path.

Required event fields:
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Emission failure handling:
- WARN-level audit event
- Must be logged
- Must be surfaced
- Must not silently continue

---

### 4. TrustLock / CTX-ID Validation

ForgeAgent must validate CTX-ID tokens against TrustLock public key material.

Integration requirements:
- Software-only validation is rejected
- Missing CTX-ID => `UNTRUSTED`
- Rotation invalidates previous token immediately

---

### 5. VTZ Policy Engine

ForgeAgent must enforce VTZ boundaries structurally.

Integration requirements:
- One VTZ per session at CTX-ID issuance
- Cross-VTZ tool calls require explicit authorization
- Implicit cross-VTZ access denied
- Policy changes apply at next CTX-ID issuance

---

### 6. Path Security

All disk write operations initiated by ForgeAgent must call:

- `path_security.validate_write_path()`

This validation must occur before any write.

---

### 7. Prompt Construction / Document Loading

If ForgeAgent loads external documents for prompt context:

- Every loaded chunk must pass injection scanning
- External document context must be placed in the USER prompt
- External document context must never be placed in the SYSTEM prompt

---

### 8. Security Refusal Handling

When LLM output equals or contains `SECURITY_REFUSAL`:

- stop
- gate
- log
- do not retry to bypass

---

### 9. Python Runtime / Tooling

ForgeAgent Python implementation integrates with the following required toolchain/runtime constraints:

- Python `3.12`
- `pytest`
- `ruff`
- `mypy`
- `pyyaml`

Required test command before changes:
```bash
cd src && pytest ../tests/ -v --tb=short
```