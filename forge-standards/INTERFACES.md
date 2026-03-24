# Interface Contracts - ForgeAgent

## Data Structures

### ConsensusRunRequest

Request shape for invoking the consensus engine from ForgeAgent.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Free-form task text. Example source usage: `f"Implement: {spec.title}"` |
| `context` | `string` | yes | Context string supplied to consensus engine |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | yes | Must always be passed |

#### Required invocation contract

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

### ConsensusRunResult

Result shape consumed by ForgeAgent from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Generated code output |

---

### VTZEnforcementDecision

Record that MUST be produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | For denial case, value MUST be exactly `block` |

No other fields are specified in the provided TRD content.

---

### TrustFlowEvent

Every action outcome MUST emit a TrustFlow event.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique; CSPRNG-generated, not sequential |
| `session_id` | `string` | yes | Session identifier |
| `ctx_id` | `string` | yes | CTX-ID associated with the action |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Event type identifier |
| `payload_hash` | `string` | yes | MUST be SHA-256 of the serialized action payload |

---

### CTX-ID Token

Opaque token validated by ForgeAgent before processing agent actions.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _opaque token value_ | `string` or implementation-defined token blob | yes | Token is immutable once issued |

Internal fields are not specified in the provided TRD content. The following behavioral constraints are normative:

- CTX-ID tokens are IMMUTABLE once issued
- rotation creates a new token; the old one is invalidated immediately
- expired CTX-ID MUST be rejected
- clock skew tolerance is defined per deployment
- CTX-ID MUST be validated against TrustLock public key
- software-only validation is rejected
- missing CTX-ID MUST be treated as `UNTRUSTED`

---

### Agent Action Payload

Serialized payload for an action processed by ForgeAgent.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _implementation-defined_ | object | yes | Exact payload fields not specified in provided TRD content |
| serialized form | bytes/string | yes | Used to compute `payload_hash = SHA-256(serialized action payload)` |

---

### Failure Strategy Selection Inputs

Inputs to failure-type-aware fix loop strategy.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `string` | yes | Passed to `_choose_strategy(failure_type, attempt, records)` |
| `attempt` | `integer` | yes | Current attempt number |
| `records` | `array` | yes | Prior records used by strategy chooser |

Output structure is not specified in the provided TRD content.

---

### Fix Arbitration Inputs

Inputs to fix arbitration scoring.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| candidate fix | `string` | yes | Candidate response text/code |
| assertion tokens | implementation-defined | yes | Used by `_score_fix()` |
| score | implementation-defined numeric value | yes | `_score_fix()` is based on assertion token overlap |

Exact scorer I/O fields are not specified in the provided TRD content.

---

### SecurityRefusalSignal

LLM output condition requiring immediate stop/gate/log handling.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| output token | `string` | yes | Must match exactly `SECURITY_REFUSAL` |

Behavior:
- stop
- gate
- log
- never retry to bypass

---

## Enums and Constants

### Supported Languages

Exact allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Language System Selection

| `language` | Selected system |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords detected |
| `"python"` | `GENERATION_SYSTEM` |

No system-selection mappings are specified for `"go"`, `"typescript"`, or `"rust"` in the provided TRD content.

### Verdict Values

Specified value:

- `block`

### Trust Classification / CTX-ID State Constants

Specified value:

- `UNTRUSTED`

### Special Security Output

Specified value:

- `SECURITY_REFUSAL`

### Log Level Constant

Specified value:

- `WARN`

### Forbidden Patterns

These are explicitly forbidden and non-conformant.

#### Forbidden fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

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
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
```

---

## Validation Rules

## Entry Point Enforcement

Every entry point that processes an agent action MUST satisfy all of the following, in order:

1. call CTX-ID validation FIRST
2. on CTX-ID validation failure, reject immediately
3. perform no partial processing before rejection
4. check every action against VTZ policy BEFORE execution
5. on VTZ denial, produce a `VTZEnforcementDecision` record with `verdict=block`
6. emit a TrustFlow event for every action outcome: allow, restrict, block
7. if TrustFlow emission fails, do not silently continue; log and surface failure

## TrustFlow Validation

Every TrustFlow event MUST satisfy:

- includes `event_id`
- includes `session_id`
- includes `ctx_id`
- includes `ts`
- includes `event_type`
- includes `payload_hash`
- `event_id` is globally unique
- `event_id` is generated by CSPRNG
- `event_id` is not sequential
- `ts` is UTC Unix timestamp with millisecond precision
- `payload_hash` is SHA-256 of the serialized action payload
- emission is synchronous in the enforcement path
- async buffering is not permitted
- failed emission is a `WARN`-level audit event
- failed emission is not a silent skip

## CTX-ID Validation

- CTX-ID validation MUST occur before any agent action processing
- CTX-ID tokens MUST NOT be modified after issuance
- rotation MUST create a new token
- old token MUST be invalidated immediately upon rotation
- expired CTX-ID MUST be rejected
- missing CTX-ID MUST be treated as `UNTRUSTED`
- identity MUST NEVER be inferred from surrounding context when CTX-ID is missing
- CTX-ID MUST be validated against TrustLock public key
- software-only validation is rejected

## VTZ Enforcement

- every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance
- cross-VTZ tool calls require explicit policy authorization
- implicit authorization is denied
- VTZ boundaries are structural, not advisory
- enforcement cannot be bypassed by application code
- VTZ policy changes take effect at NEXT CTX-ID issuance
- VTZ policy changes do not take effect mid-session

## Consensus Engine Invocation

- ForgeAgent MUST always pass `language`
- valid values are exactly:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

## Fix Loop / Arbitration

- fix loop strategy MUST be failure-type-aware via `_choose_strategy(failure_type, attempt, records)`
- static lookup table strategy is non-conformant
- fix arbitration MUST use `_score_fix()`
- `_score_fix()` is based on assertion token overlap
- length-based arbitration is forbidden

## Security Rules

- never hardcode credentials, API keys, tokens, or secrets as string literals
- never use `shell=True` in subprocess calls
- never call `eval()` or `exec()` on generated or external content
- never log HTTP response bodies
- may log status codes and error types only
- all file paths written to disk MUST pass `path_security.validate_write_path()` before any write
- all loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt
- context from external documents goes in the USER prompt, never the SYSTEM prompt
- when output is `SECURITY_REFUSAL`: stop, gate, log, and never retry to bypass

## Python Backend Requirements

- Python version: `3.12`
- type annotations on every function
- `async/await` throughout backend
- no blocking calls on the event loop
- dataclasses for all structured data
- tests use `pytest`
- tests live in `tests/`
- tests mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- test coverage on all new modules must be `>= 85%`
- `pyyaml` must be in `requirements.txt`

## Wire Format Examples

## Valid Payloads

### Valid consensus request

```json
{
  "task": "Implement: Add authentication middleware",
  "context": "Use existing session manager and emit TrustFlow events for all outcomes.",
  "language": "python"
}
```

### Valid TrustFlow event

```json
{
  "event_id": "8d8c9a4f2f7c4f7db0f8c7e4e8c3b0a1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "5f70bf18a08660bcaadf8f2e9e19b4d7c4b6d3f7d8a0b1c2d3e4f5a6b7c8d9e0"
}
```

### Valid VTZ denial record

```json
{
  "verdict": "block"
}
```

### Valid security refusal signal

```json
{
  "output": "SECURITY_REFUSAL"
}
```

## Invalid Payloads

### Invalid consensus request: missing `language`

```json
{
  "task": "Implement: Add authentication middleware",
  "context": "Use existing session manager."
}
```

Reason:
- `language` is mandatory

### Invalid consensus request: unsupported `language`

```json
{
  "task": "Implement: Add authentication middleware",
  "context": "Use existing session manager.",
  "language": "java"
}
```

Reason:
- `language` must be one of `"python" | "swift" | "go" | "typescript" | "rust"`

### Invalid TrustFlow event: missing required field

```json
{
  "event_id": "8d8c9a4f2f7c4f7db0f8c7e4e8c3b0a1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.allow"
}
```

Reason:
- `payload_hash` is required

### Invalid VTZ denial record: wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- denial record must use `verdict = "block"`

### Invalid implementation pattern: length-based fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- must use `_score_fix()`, not response length

### Invalid implementation pattern: unsafe subprocess

```python
subprocess.run(cmd, shell=True)
```

Reason:
- `shell=True` is forbidden

### Invalid implementation pattern: unsafe code execution

```python
eval(untrusted_content)
```

Reason:
- `eval()` and `exec()` on generated or external content are forbidden

### Invalid implementation pattern: external context in SYSTEM prompt

```json
{
  "system": "External document content here",
  "user": "Please summarize"
}
```

Reason:
- external document context must go in USER prompt, never SYSTEM prompt

---

## Integration Points

## Consensus Engine

ForgeAgent integrates with consensus engine using:

- method: `await self._consensus.run(...)`
- required inputs:
  - `task`
  - `context`
  - `language`
- required consumed output:
  - `result.final_code`

Selection behavior:
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected
- `language="python"` selects `GENERATION_SYSTEM`

## Path Security

Before any disk write, ForgeAgent MUST call:

- `path_security.validate_write_path()`

This validation MUST occur before the write operation.

## Prompt Construction / Injection Scanning

- all loaded document chunks must pass injection scanning before inclusion in any LLM prompt
- external document context must be placed in the USER prompt
- external document context must never be placed in the SYSTEM prompt

## TrustLock / CTX-ID Validation

ForgeAgent MUST validate CTX-ID against:

- TrustLock public key

Software-only validation is rejected.

## VTZ Policy Engine

ForgeAgent MUST check every action against VTZ policy before execution.

On denial:
- produce `VTZEnforcementDecision` with `verdict=block`

## TrustFlow Audit Pipeline

ForgeAgent MUST synchronously emit a TrustFlow event in the enforcement path for every action outcome:

- allow
- restrict
- block

If emission fails:
- log at `WARN`
- surface the failure
- do not silently continue

## Testing / Conformance Entry Step

Before modifying code, required execution step:

```bash
cd src && pytest ../tests/ -v --tb=short
```

This is a required agent workflow contract from the provided standards.