# Interface Contracts - CraftedAgent

## Data Structures

All structured backend data MUST use dataclasses. All function signatures MUST be fully type-annotated.

### TrustFlowEvent

Represents the required synchronous audit event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | Yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | `str` | Yes | Session identifier for the agent session. |
| `ctx_id` | `str` | Yes | CTX-ID associated with the action. Missing CTX-ID MUST be treated as untrusted and rejected before processing. |
| `ts` | `int` \| `float` | Yes | MUST be a UTC Unix timestamp with millisecond precision. |
| `event_type` | `str` | Yes | Event type for the action outcome. |
| `payload_hash` | `str` | Yes | MUST be SHA-256 of the serialized action payload. Lower/upper hex casing is not otherwise specified; implementation must be consistent. |

#### Semantic requirements
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a `TrustFlowEvent`.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be logged and surfaced.
- Failed emission is a WARN-level audit event, not a silent skip.

---

### VTZEnforcementDecision

Represents the enforcement result for VTZ policy evaluation.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `str` | Yes | MUST support at least `block` because VTZ denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`. |
| `session_id` | `str` | No | If present, SHOULD identify the bound session. |
| `ctx_id` | `str` | No | If present, SHOULD identify the evaluated CTX-ID. |
| `reason` | `str` | No | Human/audit-readable reason for allow/restrict/block. |
| `policy_id` | `str` | No | Identifier of the policy used for the decision. |
| `action` | `str` | No | Serialized or symbolic action identifier under evaluation. |

#### Semantic requirements
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

### CTXIDToken

Represents a validated issued CTX-ID token.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | Yes | Token identifier. MUST be immutable once issued. |
| `session_id` | `str` | Yes | Session identifier bound at issuance. |
| `vtz_id` | `str` | Yes | The single VTZ bound to the session at issuance. |
| `issued_at` | `int` \| `float` | Yes | UTC Unix timestamp. |
| `expires_at` | `int` \| `float` | Yes | UTC Unix timestamp. Expired CTX-ID MUST be rejected. Clock skew tolerance is deployment-defined. |
| `public_key_id` | `str` | Yes | Identifier for the TrustLock public key used for validation. |
| `rotated_from` | `str \| None` | No | Previous CTX-ID if this token was created through rotation. |
| `invalidated` | `bool` | Yes | Whether the token has been invalidated, including after rotation. |

#### Semantic requirements
- CTX-ID validation MUST occur FIRST at every entry point that processes an agent action.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted after CTX-ID validation failure.
- CTX-ID tokens are IMMUTABLE once issued.
- CTX-ID rotation creates a new token.
- The old token is invalidated immediately.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as UNTRUSTED.
- Identity MUST NEVER be inferred from surrounding context.

---

### AgentActionPayload

Canonical action payload subject to validation, hashing, and VTZ enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `str` | Yes | Session identifier. |
| `ctx_id` | `str` | Yes | CTX-ID presented with the action. |
| `action_type` | `str` | Yes | Symbolic action type. |
| `payload` | `dict[str, object]` | Yes | Serialized action payload used to compute `payload_hash`. |
| `language` | `Literal["python", "swift", "go", "typescript", "rust"]` | No | Required when invoking the consensus engine for code generation flows. |
| `spec_title` | `str` | No | If present, used in consensus task construction as `Implement: {spec.title}`. |

#### Semantic requirements
- `payload_hash` for TrustFlow MUST be SHA-256 of the serialized `payload`.
- Any action-processing entry point MUST validate `ctx_id` first.
- The action MUST be checked against VTZ policy before execution.
- The action outcome MUST emit a TrustFlow event.

---

### ConsensusRunRequest

Request structure for Consensus Engine integration.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | SHOULD be formatted exactly as `Implement: {spec.title}` for implementation flows. |
| `context` | `str` | Yes | Prompt context string. External document context MUST go in the USER prompt, never the SYSTEM prompt. All loaded document chunks MUST pass injection scanning before inclusion. |
| `language` | `Literal["python", "swift", "go", "typescript", "rust"]` | Yes | Always required. |

#### Semantic requirements
Invocation MUST follow:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

Language selection semantics:
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result structure returned from the Consensus Engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Generated code artifact returned by consensus arbitration. |

#### Semantic requirements
- Consumers MUST read generated code from `result.final_code`.

---

### FixStrategyInput

Input model for failure-aware fix-loop strategy selection.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `str` | Yes | Failure classification passed to `_choose_strategy(failure_type, attempt, records)`. |
| `attempt` | `int` | Yes | Current fix attempt number. |
| `records` | `list[object]` | Yes | Prior failure/fix records consumed by strategy selection. |

#### Semantic requirements
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup-table-only behavior is non-conformant.

---

### FixArbitrationInput

Input model for fix arbitration scoring.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `candidate_fix` | `str` | Yes | Fix candidate under evaluation. |
| `assertion_tokens` | `list[str]` | Yes | Assertion token set used for overlap scoring. |

#### Semantic requirements
- Fix arbitration MUST use `_score_fix()`.
- Arbitration basis is assertion token overlap.
- Length-based arbitration is forbidden.

---

## Enums and Constants

### Language

Allowed values for consensus engine requests and code generation flows:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

These values MUST appear exactly as above.

---

### ActionOutcome

Required action outcomes for TrustFlow emission semantics:

- `"allow"`
- `"restrict"`
- `"block"`

Every one of these outcomes MUST emit a TrustFlow event.

---

### VTZEnforcementVerdict

Minimum required verdict value:

- `"block"`

Additional verdicts such as `"allow"` and `"restrict"` may be implemented, but `block` is mandatory because denial MUST produce `verdict=block`.

---

### Generation System Selectors

These names are part of the integration contract:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

Selection rules:
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### Forbidden Patterns

The following are explicitly forbidden contract violations.

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

#### Backend token read from Keychain

```swift
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
```

---

## Validation Rules

## Entry-point enforcement order

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur FIRST.
2. On CTX-ID validation failure, processing MUST be immediately rejected.
3. No partial processing is permitted after CTX-ID validation failure.
4. VTZ policy MUST be evaluated BEFORE execution.
5. If VTZ denies, a `VTZEnforcementDecision` MUST be created with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a synchronous `TrustFlowEvent`.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

## TrustFlow validation

- `event_id` MUST be globally unique.
- `event_id` MUST be generated by CSPRNG.
- `event_id` MUST NOT be sequential.
- `ts` MUST be UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.

## CTX-ID validation

- Token MUST be present; otherwise treat as `UNTRUSTED`.
- Token MUST validate against TrustLock public key.
- Software-only validation is rejected.
- Token MUST NOT be expired.
- Rotation MUST produce a new token.
- Previous token MUST be invalidated immediately.
- Token fields MUST NOT be modified after issuance.

## VTZ validation

- Session MUST be bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls MUST have explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect only at NEXT CTX-ID issuance.

## Consensus engine validation

- `language` MUST always be provided.
- `language` MUST be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

## Security validation

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` output is received from the LLM: stop, gate, log. Never retry to bypass.

## Python/backend implementation constraints

- Python version: `3.12`
- Type annotations on every function.
- `async/await` throughout backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- Tests MUST use `pytest`.
- Tests MUST live in `tests/` and mirror `src/` structure.
- `ruff` MUST pass clean.
- `mypy` MUST pass clean.
- Test coverage MUST be `>= 85%` on all new modules.
- `pyyaml` MUST be in `requirements.txt`.

---

## Wire Format Examples

## Valid payloads

### Valid `AgentActionPayload`

```json
{
  "session_id": "sess_01JABCDEF0123456789XYZ",
  "ctx_id": "ctx_01JABCDEF0123456789XYZ",
  "action_type": "generate_code",
  "payload": {
    "component": "CraftedAgent",
    "target_path": "src/crafted_agent/core.py"
  },
  "language": "python",
  "spec_title": "CraftedAgent subsystem"
}
```

### Valid `TrustFlowEvent`

```json
{
  "event_id": "evt_csprng_4f9c1c2b6a5e4d2f9a0b8c7d6e5f4a3b",
  "session_id": "sess_01JABCDEF0123456789XYZ",
  "ctx_id": "ctx_01JABCDEF0123456789XYZ",
  "ts": 1730765123123,
  "event_type": "allow",
  "payload_hash": "8d6b8a1f4d4d7a5c19f7f1f0f5d9230d0d6ab3e0f6b6b780e5d4d3d2c1b0a999"
}
```

### Valid `VTZEnforcementDecision`

```json
{
  "verdict": "block",
  "session_id": "sess_01JABCDEF0123456789XYZ",
  "ctx_id": "ctx_01JABCDEF0123456789XYZ",
  "reason": "cross_vtz_tool_call_without_explicit_policy_authorization",
  "policy_id": "pol_vtz_2025_01",
  "action": "tool.call"
}
```

### Valid `ConsensusRunRequest`

```json
{
  "task": "Implement: CraftedAgent subsystem",
  "context": "User-provided implementation context after injection scanning.",
  "language": "python"
}
```

### Valid `ConsensusRunResult`

```json
{
  "final_code": "from dataclasses import dataclass\n"
}
```

## Invalid payloads

### Invalid `AgentActionPayload` — missing `ctx_id`

Reason: missing CTX-ID MUST be treated as UNTRUSTED.

```json
{
  "session_id": "sess_01JABCDEF0123456789XYZ",
  "action_type": "generate_code",
  "payload": {
    "component": "CraftedAgent"
  },
  "language": "python"
}
```

### Invalid `ConsensusRunRequest` — missing `language`

Reason: always pass language.

```json
{
  "task": "Implement: CraftedAgent subsystem",
  "context": "Context without language."
}
```

### Invalid `ConsensusRunRequest` — unsupported `language`

```json
{
  "task": "Implement: CraftedAgent subsystem",
  "context": "Context",
  "language": "java"
}
```

### Invalid `TrustFlowEvent` — sequential `event_id`

Reason: `event_id` MUST be globally unique and not sequential.

```json
{
  "event_id": "1",
  "session_id": "sess_01JABCDEF0123456789XYZ",
  "ctx_id": "ctx_01JABCDEF0123456789XYZ",
  "ts": 1730765123123,
  "event_type": "block",
  "payload_hash": "8d6b8a1f4d4d7a5c19f7f1f0f5d9230d0d6ab3e0f6b6b780e5d4d3d2c1b0a999"
}
```

### Invalid fix arbitration implementation

Reason: length-based arbitration is forbidden.

```python
winner = max(claude_fix, openai_fix, key=len)
```

### Invalid Swift backend integration

Reason: LLM API calls from Swift are forbidden.

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

---

## Integration Points

## Consensus Engine

Required call shape:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

### Contract requirements
- `language` MUST always be passed.
- `result.final_code` is the output field to consume.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` and optionally `SWIFT_UI_ADDENDUM`.
- `language="python"` selects `GENERATION_SYSTEM`.

## Enforcement pipeline

The CraftedAgent subsystem MUST integrate:
- CTX-ID validation
- VTZ policy enforcement
- TrustFlow synchronous emission

Minimum enforcement sequence:
1. Validate `ctx_id`
2. Reject immediately on failure
3. Evaluate VTZ policy
4. Produce `VTZEnforcementDecision` with `verdict=block` on denial
5. Emit `TrustFlowEvent` for `allow`, `restrict`, or `block`

## Path security

Before writing any file path to disk, the subsystem MUST call:

```python
path_security.validate_write_path()
```

Contract rule:
- Validation MUST happen before any write.

## Prompt construction

- External document context MUST be included only in the USER prompt.
- External document context MUST NOT be included in the SYSTEM prompt.
- All loaded document chunks MUST pass injection scanning before inclusion.

## Security refusal handling

If the LLM returns `SECURITY_REFUSAL`:
- stop
- gate
- log
- never retry to bypass

## Testing and quality gates

Before and during modifications, the subsystem contract requires:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Additional required gates:
- `pytest`
- `ruff`
- `mypy`
- coverage `>= 85%` on all new modules

## Platform boundary rules

- Only Swift reads Keychain, and only to deliver via XPC.
- Python backend reads nothing from Keychain.
- Swift MUST NOT make direct LLM API calls.
- Swift MUST NOT use force unwraps.