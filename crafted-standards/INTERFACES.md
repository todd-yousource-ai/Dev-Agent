# Interface Contracts - CraftedAgent

## Data Structures

All structured backend data MUST use Python dataclasses. All function signatures MUST be fully type-annotated.

### TrustFlowEvent

Required for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | Yes | MUST be globally unique. MUST be generated via CSPRNG. MUST NOT be sequential. |
| `session_id` | `str` | Yes | Session identifier for the agent session. |
| `ctx_id` | `str` | Yes | CTX-ID associated with the action. Missing CTX-ID MUST be treated as untrusted and rejected before processing. |
| `ts` | `int` \| `float` | Yes | MUST be a UTC Unix timestamp with millisecond precision. |
| `event_type` | `str` | Yes | Event type for TrustFlow emission. |
| `payload_hash` | `str` | Yes | MUST be SHA-256 of the serialized action payload. Lower/upper hex encoding is not otherwise specified by source; implementation MUST be consistent. |

#### Behavioral requirements
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is NOT permitted.
- Emission failure MUST NOT silently continue.
- Failed emission is a WARN-level audit event and MUST be surfaced.

---

### VTZEnforcementDecision

Produced when VTZ policy is evaluated.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `str` | Yes | MUST support at least `block` because VTZ denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`. |
| `session_id` | `str` | No | Recommended correlation field; source requires session binding semantics but does not explicitly define record schema. |
| `ctx_id` | `str` | No | Recommended correlation field. |
| `reason` | `str` | No | Human/audit-readable denial reason. |
| `policy_id` | `str` | No | Policy identifier if available. |

#### Behavioral requirements
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### CTXIDToken

Immutable token used to establish trusted identity and VTZ binding.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | Yes | Token identifier. |
| `vtz_id` | `str` | Yes | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance. |
| `issued_at` | `int` \| `float` | Yes | UTC Unix timestamp. |
| `expires_at` | `int` \| `float` | Yes | UTC Unix timestamp. Expired CTX-ID MUST be rejected. |
| `trustlock_signature` | `bytes` \| `str` | Yes | MUST validate against TrustLock public key. Software-only validation is rejected. |
| `subject` | `str` | No | Optional principal/subject identifier if present in issuing system. |

#### Behavioral requirements
- CTX-ID tokens are IMMUTABLE once issued.
- Rotation creates a new token; the old one is invalidated immediately.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from surrounding context when CTX-ID is missing.
- Validation against TrustLock public key is mandatory.

---

### AgentAction

Action presented to CraftedAgent enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `str` | Yes | Session receiving the action. |
| `ctx_id` | `str` | Yes | MUST be validated FIRST at every entry point that processes an agent action. |
| `action_type` | `str` | Yes | Action discriminator. |
| `payload` | `dict[str, object]` | Yes | Serialized form is input to `payload_hash` calculation. |
| `target_vtz` | `str` | No | If present and different from bound VTZ, requires explicit policy authorization. |

#### Behavioral requirements
- Entry-point processing order is mandatory:
  1. CTX-ID validation FIRST
  2. Immediate rejection on CTX-ID validation failure
  3. VTZ policy check BEFORE execution
  4. Action execution only if permitted
  5. TrustFlow emission for outcome

---

### ConsensusRunRequest

Required usage contract for consensus engine calls.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Example source usage: `f"Implement: {spec.title}"` |
| `context` | `str` | Yes | Context string passed to consensus engine. |
| `language` | `str` | Yes | MUST be one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Required invocation shape
```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

---

### ConsensusRunResult

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Generated code returned by consensus engine. |

---

### FixStrategyInputs

Used by failure-aware fix loop selection.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `str` | Yes | Input to `_choose_strategy(failure_type, attempt, records)` |
| `attempt` | `int` | Yes | Current retry/fix attempt count. |
| `records` | `list[object]` | Yes | Prior fix/test records used by strategy selector. |

#### Behavioral requirements
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup table strategy selection is non-conformant.

---

### FixArbitrationInputs

Used by fix arbitration scorer.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `candidate_fix` | `str` | Yes | Candidate fix content. |
| `assertion_tokens` | `list[str]` | Yes | Tokens from test/assertion failures used for scoring. |

#### Behavioral requirements
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration is forbidden.

Forbidden pattern:
```python
winner = max(claude_fix, openai_fix, key=len)
```

---

## Enums and Constants

### `language`

Exact allowed values:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### TrustFlow action outcomes

Exact values required by source contract:

- `allow`
- `restrict`
- `block`

### VTZ enforcement verdicts

Exact value explicitly required by source:

- `block`

Implementations MAY define additional verdict values, but `block` MUST exist and MUST be emitted on VTZ denial.

### Trust state for missing CTX-ID

Exact required value:

- `UNTRUSTED`

### Security sentinel output

Exact value:

- `SECURITY_REFUSAL`

When observed from the LLM:
- stop
- gate
- log
- never retry to bypass

### System selection constants

Exact constant names referenced by contract:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Tooling and platform constants

- Python version: `3.12`
- Test framework: `pytest`
- Linter: `ruff`
- Type checker: `mypy`
- YAML dependency requirement: `pyyaml`

---

## Validation Rules

## CAL Enforcement Validation

Every entry point that processes an agent action MUST satisfy all of the following:

1. CTX-ID validation MUST occur FIRST.
2. CTX-ID validation failure MUST cause immediate rejection.
3. No partial processing is permitted before successful CTX-ID validation.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ denial MUST create a `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.

## TrustFlow Event Validation

A valid `TrustFlowEvent` MUST satisfy:

- `event_id` present and globally unique
- `event_id` generated by CSPRNG
- `event_id` not sequential
- `session_id` present
- `ctx_id` present
- `ts` present and UTC Unix timestamp with millisecond precision
- `event_type` present
- `payload_hash` present
- `payload_hash == sha256(serialized_action_payload)`

Emission rules:
- synchronous only in enforcement path
- no async buffering
- failed emission logged as WARN-level audit event
- failure surfaced to caller/operator path; no silent skip

## CTX-ID Validation

A valid CTX-ID MUST satisfy:

- token present
- token unmodified since issuance
- token not expired
- token validated against TrustLock public key
- token bound to exactly one VTZ at issuance

Rejection conditions:
- missing token
- expired token
- invalid signature/public key validation failure
- rotated/invalidated old token
- malformed token

Special handling:
- missing CTX-ID => `UNTRUSTED`
- do not infer identity from context

## VTZ Validation

- Each session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls are denied unless explicitly authorized by policy.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

## Consensus Engine Validation

Every consensus call MUST pass `language`.

Valid `language` values only:
- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

Selection behavior:
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

## Security Validation

The following are forbidden:

- hardcoded credentials, API keys, tokens, or secrets as string literals
- `shell=True` in subprocess calls
- `eval()` on generated or external content
- `exec()` on generated or external content
- logging HTTP response bodies
- writing any file path before `path_security.validate_write_path()`
- including loaded document chunks in an LLM prompt before injection scanning
- placing context from external documents in the SYSTEM prompt
- retrying to bypass `SECURITY_REFUSAL`
- force unwrap in Swift:
  ```swift
  let value = optional!
  ```
- LLM API call from Swift:
  ```swift
  let client = AnthropicClient(apiKey: keychainValue)
  ```
- backend token read from Keychain:
  ```swift
  let token = KeychainKit.read("github_token")
  ```

Required handling:
- all file paths written to disk MUST pass `path_security.validate_write_path()` before any write
- all loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt
- external document context MUST go in the USER prompt, never the SYSTEM prompt
- when `SECURITY_REFUSAL` occurs: stop, gate, log

## Python Backend Validation

- Python `3.12`
- type annotations on every function
- `async/await` throughout backend
- no blocking calls on event loop
- dataclasses for all structured data
- tests in `tests/`, mirroring `src/`
- `pytest` required
- `ruff` must pass clean
- `mypy` must pass clean
- test coverage `>= 85%` on all new modules
- `pyyaml` must be in `requirements.txt`

---

## Wire Format Examples

## Valid payloads

### Valid `TrustFlowEvent`
```json
{
  "event_id": "2d4e9c62-70a0-4d7e-bb4d-0f0a1e8d5c9b",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action_blocked",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

### Valid `VTZEnforcementDecision`
```json
{
  "verdict": "block",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "reason": "cross-VTZ tool call denied",
  "policy_id": "vtz_policy_default"
}
```

### Valid `AgentAction`
```json
{
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "action_type": "tool_call",
  "payload": {
    "tool": "file_write",
    "path": "/workspace/out.txt"
  },
  "target_vtz": "vtz_primary"
}
```

### Valid `ConsensusRunRequest`
```json
{
  "task": "Implement: ExampleSpec",
  "context": "Generate a safe implementation.",
  "language": "python"
}
```

### Valid `ConsensusRunResult`
```json
{
  "final_code": "def example() -> None:\n    pass\n"
}
```

### Valid `CTXIDToken`
```json
{
  "ctx_id": "ctx_abc",
  "vtz_id": "vtz_primary",
  "issued_at": 1735689600,
  "expires_at": 1735693200,
  "trustlock_signature": "BASE64_OR_HEX_SIGNATURE",
  "subject": "user_123"
}
```

## Invalid payloads

### Invalid `TrustFlowEvent` missing required field
```json
{
  "event_id": "123",
  "session_id": "sess_123",
  "ts": 1735689600123,
  "event_type": "action_allowed",
  "payload_hash": "abc"
}
```

Reason:
- missing `ctx_id`

### Invalid `ConsensusRunRequest` missing `language`
```json
{
  "task": "Implement: ExampleSpec",
  "context": "Generate a safe implementation."
}
```

Reason:
- `language` is mandatory

### Invalid `ConsensusRunRequest` with unsupported language
```json
{
  "task": "Implement: ExampleSpec",
  "context": "Generate a safe implementation.",
  "language": "java"
}
```

Reason:
- `language` MUST be one of `"python" | "swift" | "go" | "typescript" | "rust"`

### Invalid `VTZEnforcementDecision` for denial
```json
{
  "verdict": "allow"
}
```

Reason:
- VTZ policy denial MUST produce `verdict=block`

### Invalid CTX-ID usage
```json
{
  "session_id": "sess_123",
  "action_type": "tool_call",
  "payload": {
    "tool": "network_request"
  }
}
```

Reason:
- missing `ctx_id`
- missing CTX-ID MUST be treated as `UNTRUSTED`
- request MUST be rejected before partial processing

### Invalid security pattern: external content in system prompt
```json
{
  "system": "Summarize the following external document: ...",
  "user": "Proceed"
}
```

Reason:
- external document context MUST go in USER prompt, never SYSTEM prompt

---

## Integration Points

## CraftedAgent entry points

Any entry point that processes an agent action MUST integrate, in order, with:

1. CTX-ID validator
2. VTZ policy enforcement
3. TrustFlow emitter
4. Action executor

Required order:
- validate CTX-ID first
- reject immediately on failure
- evaluate VTZ before execution
- emit TrustFlow for final outcome

## TrustLock integration

Used for CTX-ID verification.

Requirements:
- validate CTX-ID against TrustLock public key
- software-only validation is rejected
- expired or rotated tokens must fail validation

## VTZ policy engine integration

Used before any action execution.

Requirements:
- session bound to exactly one VTZ from CTX-ID issuance
- explicit authorization required for cross-VTZ tool calls
- implicit cross-VTZ access denied
- policy updates apply only at next CTX-ID issuance

## TrustFlow integration

Used for synchronous audit/event emission.

Requirements:
- emit for every outcome: `allow`, `restrict`, `block`
- include exact fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- synchronous in enforcement path only
- no async buffering
- warn and surface on failure

## Consensus engine integration

Required invocation:
```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Language routing:
- `"swift"` => `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `"python"` => `GENERATION_SYSTEM`

Fix-loop integration:
- choose repair strategy with `_choose_strategy(failure_type, attempt, records)`
- arbitrate fixes with `_score_fix()`
- do NOT use response length as selection criteria

## Filesystem integration

Before writing any file:
- call `path_security.validate_write_path()`

## Prompt construction integration

Before including external document chunks in prompts:
- perform injection scanning

Prompt placement:
- external document context in USER prompt only
- never in SYSTEM prompt

## Testing and compliance integration

Before modifying code:
1. find the owning TRD in `README.md`
2. read relevant TRD sections
3. check TRD-11 if touching credentials, external content, generated code, or CI
4. run:
   ```bash
   cd src && pytest ../tests/ -v --tb=short
   ```

Ongoing compliance:
- tests in `tests/` mirroring `src/`
- `pytest`, `ruff`, `mypy` all required
- new module coverage must be at least `85%`