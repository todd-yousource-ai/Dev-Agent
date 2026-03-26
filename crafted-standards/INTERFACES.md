# Interface Contracts - CraftedAgent

## Data Structures

All structured backend data **MUST** use dataclasses.

### ConsensusRunRequest

Request shape used when invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | yes | Human-readable implementation task string. Example source usage: `f"Implement: {spec.title}"`. |
| `context` | `str` | yes | Context string supplied to the consensus engine. External document content included here must have passed injection scanning. External context belongs in the USER prompt, never the SYSTEM prompt. |
| `language` | `str` | yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. |

### ConsensusRunResult

Result returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | yes | Generated code output. Must not be executed with `eval()` or `exec()`. |

### VTZEnforcementDecision

Record emitted when VTZ policy is evaluated.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `str` | yes | For denial, value **MUST** be exactly `block`. Other verdicts may exist for outcomes such as allow or restrict, but only `block` is explicitly mandated by source requirements. |

### TrustFlowEvent

Every action outcome must emit a TrustFlow event.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | yes | Must be globally unique. Must be generated via CSPRNG. Must not be sequential. |
| `session_id` | `str` | yes | Session identifier for the agent session. |
| `ctx_id` | `str` | yes | CTX-ID associated with the session/action. Missing CTX-ID must be treated as UNTRUSTED. |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `str` | yes | Event type identifier. |
| `payload_hash` | `str` | yes | Must be SHA-256 of the serialized action payload. |

### CTX-ID Token

Immutable trust token for a session.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | yes | Token identifier. Immutable once issued. |
| `vtz` | `str` | yes | Session is bound to exactly one VTZ at issuance. |
| `expires_at` | `number` | yes | Expiry timestamp. Expired CTX-ID must be rejected. Clock skew tolerance is deployment-defined. |
| `public_key_id` | `str` | yes | Validation must be against TrustLock public key. Software-only validation is rejected. |

> Source requirements define CTX-ID behavior and validation constraints, but do not enumerate a full token payload schema. The above fields are the minimum contract implied by the requirements.

### Agent Action Payload

Serialized action payload used for enforcement and hashing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `str` | yes | Must identify the current agent session. |
| `ctx_id` | `str` | yes | Must be validated first at every action-processing entry point. |
| `action` | `str` | yes | Action identifier being evaluated against VTZ policy before execution. |
| `payload` | `object` | yes | Serialized action payload. `payload_hash` in TrustFlowEvent must be SHA-256 of this serialized payload. |

> Source requirements mandate hashing of the serialized action payload but do not define a canonical serialization format. Implementations must use a deterministic serialization format consistently.

## Enums and Constants

### Supported `language` Values

These values must appear exactly as shown:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Language-to-System Selection Rules

| `language` | System behavior |
|---|---|
| `"swift"` | Selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected |
| `"python"` | Selects `GENERATION_SYSTEM` |

No explicit system-selection behavior is specified in source for `"go"`, `"typescript"`, or `"rust"` beyond being valid `language` values for consensus execution.

### Required Verdict Value

- `block` — required value for `VTZEnforcementDecision.verdict` when VTZ policy denies an action

### Trust and Identity Constants

- `UNTRUSTED` — semantic state that must be used when CTX-ID is missing
- `SECURITY_REFUSAL` — when seen from the LLM, processing must stop, gate, and log; never retry to bypass

### Forbidden Patterns

These are contract-level prohibitions.

#### Python / backend
- `shell=True` in subprocess calls
- `eval()`
- `exec()`

#### Fix arbitration
- Length-based arbitration is forbidden:
  - `winner = max(claude_fix, openai_fix, key=len)` is **WRONG**
- Fix arbitration must use `_score_fix()`

#### Swift
- Force unwrap: `optional!`
- LLM API call from Swift
- Keychain read for backend from Swift-side backend logic

## Validation Rules

## Entry Point Enforcement Order

Every entry point that processes an agent action **MUST** perform checks in this order:

1. **CTX-ID validation first**
2. Immediate rejection on CTX-ID validation failure
3. **VTZ policy check before execution**
4. Produce `VTZEnforcementDecision` with `verdict=block` on VTZ denial
5. Emit TrustFlow event for every outcome: allow, restrict, block
6. If TrustFlow emission fails, do **not** silently continue; log and surface the failure

## CTX-ID Validation Rules

- CTX-ID tokens are **immutable once issued**
- Rotation creates a new token
- Old token is invalidated immediately on rotation
- Expired CTX-ID must be rejected
- Missing CTX-ID must be treated as `UNTRUSTED`
- Validation must be against TrustLock public key
- Software-only validation is rejected
- Identity must never be inferred from surrounding context when CTX-ID is missing

## VTZ Enforcement Rules

- Every agent session is bound to **exactly one** VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit cross-VTZ access is denied
- VTZ boundaries are structural and cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session

## TrustFlow Emission Rules

- Emission is synchronous in the enforcement path
- Async buffering is not permitted
- Every TrustFlow event must include all required fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- `payload_hash` must be SHA-256 of the serialized action payload
- Failed emission is a WARN-level audit event
- Failed emission must not be silently skipped

## Consensus Engine Invocation Rules

Call shape:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Validation requirements:

- `language` is mandatory
- `language` must be one of the supported values exactly
- `context` must be a string
- `task` must be a string
- Fix loop strategy is chosen by `_choose_strategy(failure_type, attempt, records)`
- Fix arbitration must use `_score_fix()`
- Length-based fix arbitration is non-conformant

## Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Never use `shell=True` in subprocess calls
- Never call `eval()` or `exec()` on generated or external content
- Never log HTTP response bodies
- Log status codes and error types only
- Every file path written to disk must pass `path_security.validate_write_path()` before any write
- Every loaded document chunk must pass injection scanning before inclusion in any LLM prompt
- External document context must go in the USER prompt, never the SYSTEM prompt
- On `SECURITY_REFUSAL`: stop, gate, log; never retry to bypass

## Python Backend Rules

- Python version: **3.12**
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Tests must use `pytest`
- Tests live in `tests/` and mirror `src/` structure
- `ruff` must pass
- `mypy` must pass
- Test coverage on new modules must be `>= 85%`
- `pyyaml` must be present in `requirements.txt`

## Wire Format Examples

## Valid Payloads

### Valid consensus run request

```json
{
  "task": "Implement: Add VTZ enforcement",
  "context": "Agent action details and validated external context",
  "language": "python"
}
```

### Valid consensus run result

```json
{
  "final_code": "from dataclasses import dataclass\n\n@dataclass\nclass Example:\n    value: str\n"
}
```

### Valid TrustFlow event

```json
{
  "event_id": "6d4e7ab8-4d97-4d3c-9f5f-7ad66f4a5d91",
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "ts": 1735689600123,
  "event_type": "vtz.allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961e7a2bd2c4c3df4b5b547ab"
}
```

### Valid VTZ block decision

```json
{
  "verdict": "block"
}
```

### Valid action payload

```json
{
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "action": "tool.invoke",
  "payload": {
    "tool": "search",
    "arguments": {
      "query": "status"
    }
  }
}
```

## Invalid Payloads

### Invalid consensus run request: missing `language`

```json
{
  "task": "Implement: Add VTZ enforcement",
  "context": "Agent action details"
}
```

Reason: `language` is required.

### Invalid consensus run request: unsupported `language`

```json
{
  "task": "Implement: Add VTZ enforcement",
  "context": "Agent action details",
  "language": "java"
}
```

Reason: `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid TrustFlow event: missing required field

```json
{
  "event_id": "6d4e7ab8-4d97-4d3c-9f5f-7ad66f4a5d91",
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "ts": 1735689600123,
  "event_type": "vtz.allow"
}
```

Reason: `payload_hash` is required.

### Invalid VTZ denial decision

```json
{
  "verdict": "deny"
}
```

Reason: on VTZ policy denial, `verdict` must be exactly `block`.

### Invalid action processing request: missing CTX-ID

```json
{
  "session_id": "sess_123",
  "action": "tool.invoke",
  "payload": {
    "tool": "search"
  }
}
```

Reason: missing CTX-ID must be treated as `UNTRUSTED`; the action cannot proceed as a trusted action.

## Integration Points

## Consensus Engine

CraftedAgent must invoke the consensus engine with:

- `task`
- `context`
- `language`

and consume:

- `result.final_code`

Required invocation behavior:

- Always pass `language`
- Use `await`
- Use the returned `final_code`

## TrustLock / CTX-ID Validation

CraftedAgent must integrate with CTX-ID validation such that:

- validation happens first at every action-processing entry point
- validation uses TrustLock public key
- software-only validation is rejected

## VTZ Policy Engine

CraftedAgent must integrate with VTZ policy evaluation such that:

- every action is checked before execution
- cross-VTZ tool calls require explicit authorization
- denial produces `VTZEnforcementDecision` with `verdict=block`

## TrustFlow Audit Pipeline

CraftedAgent must synchronously emit TrustFlow events containing:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Emission failures:

- must be logged
- must be surfaced
- must not be silently skipped

## Path Security

Before any disk write, CraftedAgent must call:

- `path_security.validate_write_path()`

## Injection Scanning

Before any loaded document chunk is included in an LLM prompt:

- injection scanning must be performed

## Prompt Construction

- External document context goes in the USER prompt
- External document context must never go in the SYSTEM prompt

## Testing and Quality Gates

Before changes to CraftedAgent:

- find the owning TRD via `README.md`
- read relevant TRD sections
- check TRD-11 if credentials, external content, generated code, or CI are involved
- run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Ongoing conformance requirements:

- `pytest`
- `ruff`
- `mypy`
- coverage `>= 85%` on new modules