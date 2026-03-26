# Interface Contracts - CraftedAgent

This document defines the wire format and API contract for the CraftedAgent subsystem.

## Data Structures

### ConsensusRunRequest

Request passed to the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Free-form task description. Example usage: `f"Implement: {spec.title}"` |
| `context` | `string` | Yes | Context string supplied to consensus |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed |

#### Required invocation contract

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### ConsensusRunResult

Result returned by the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output |

---

### CTXIDToken

Immutable trust token used to authorize agent actions.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `token` | `string` | Yes | Must be validated against TrustLock public key |
| `issued_at` | `integer` | Yes | UTC Unix timestamp; clock skew tolerance is deployment-defined |
| `expires_at` | `integer` | Yes | Expired tokens MUST be rejected |
| `vtz_id` | `string` | Yes | Session is bound to exactly one VTZ at issuance |

#### Contract constraints

- CTX-ID tokens are **IMMUTABLE** once issued.
- Rotation creates a new token; the old one is invalidated immediately.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Software-only validation is rejected; validation MUST use TrustLock public key.

---

### VTZEnforcementDecision

Record produced when VTZ policy is evaluated.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"allow" \| "restrict" \| "block"` | Yes | VTZ policy denial MUST produce `verdict=block` |
| `session_id` | `string` | Yes | Session identifier |
| `ctx_id` | `string` | Yes | CTX-ID associated with the decision |
| `vtz_id` | `string` | Yes | Must match session binding |
| `action` | `string` | Yes | Action being evaluated |
| `reason` | `string` | No | Human/audit-readable explanation |

---

### TrustFlowEvent

Synchronous audit event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique; CSPRNG-generated, not sequential |
| `session_id` | `string` | Yes | Session identifier |
| `ctx_id` | `string` | Yes | Associated CTX-ID |
| `ts` | `integer` | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | Yes | Event classification |
| `payload_hash` | `string` | Yes | SHA-256 of the serialized action payload |

#### Emission contract

- Every action outcome (`allow`, `restrict`, `block`) MUST emit a `TrustFlowEvent`.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and MUST NOT be silently skipped.
- TrustFlow emission failure MUST be logged and surfaced.

---

### AgentActionRequest

Entry-point payload for processing an agent action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | Yes | Identifies the agent session |
| `ctx_id` | `string` | Yes | Must be validated first |
| `action` | `string` | Yes | Must be checked against VTZ policy before execution |
| `payload` | `object` | Yes | Serialized payload used to compute `payload_hash` |

#### Processing order contract

1. CTX-ID validation MUST occur first.
2. CTX-ID validation failure MUST cause immediate rejection.
3. No partial processing is permitted on CTX-ID failure.
4. VTZ policy check MUST occur before execution.
5. Outcome MUST emit a `TrustFlowEvent`.

---

### AgentSessionBinding

Session-to-VTZ binding state.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | Yes | Unique session identifier |
| `ctx_id` | `string` | Yes | Active CTX-ID |
| `vtz_id` | `string` | Yes | Exactly one VTZ per session |
| `issued_at` | `integer` | Yes | Issuance time |
| `expires_at` | `integer` | Yes | Expiration time |

#### Contract constraints

- Every agent session is bound to **EXACTLY ONE** VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

## Enums and Constants

### Language

Allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### VTZVerdict

Allowed values for `VTZEnforcementDecision.verdict`:

- `"allow"`
- `"restrict"`
- `"block"`

### CTXIDTrustState

Derived trust handling states:

- `UNTRUSTED` — used when CTX-ID is missing

### Consensus system selection rules

| `language` | Selected system |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords detected |
| `"python"` | `GENERATION_SYSTEM` |

### Fix strategy and arbitration

- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Length-based fix arbitration is forbidden.

#### Forbidden example

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

## Validation Rules

### CAL enforcement

For every entry point that processes an agent action:

- MUST call CTX-ID validation first.
- MUST reject immediately on CTX-ID validation failure.
- MUST check every action against VTZ policy before execution.
- VTZ denial MUST produce a `VTZEnforcementDecision` with `verdict="block"`.
- MUST emit a `TrustFlowEvent` for every outcome.
- MUST log and surface TrustFlow emission failure.

### CTX-ID validation

- `ctx_id` is required for trusted processing.
- Missing `ctx_id` MUST be treated as `UNTRUSTED`.
- Expired CTX-ID MUST be rejected.
- CTX-ID field values MUST NOT be modified after issuance.
- Rotation invalidates the old token immediately.
- Validation MUST be against TrustLock public key.

### TrustFlow validation

- `event_id` MUST be globally unique.
- `event_id` MUST be generated by CSPRNG.
- `event_id` MUST NOT be sequential.
- `ts` MUST be UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST equal SHA-256 of the serialized action payload.

### VTZ validation

- Session MUST be bound to exactly one VTZ.
- Cross-VTZ tool calls MUST have explicit authorization.
- VTZ enforcement cannot be bypassed by application code.
- Policy changes apply only at next CTX-ID issuance.

### Security rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` output is returned from the LLM: stop, gate, log. Never retry to bypass.

### Python implementation rules

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
- `pyyaml` must be present in `requirements.txt`

### Swift/backend boundary rules

Forbidden patterns:

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

Constraints:

- No force unwrap.
- No LLM API call from Swift.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, and only to deliver via XPC.

## Wire Format Examples

### Valid: agent action request

```json
{
  "session_id": "sess_01HZX8K9M9T1Q7V6A2B3C4D5E6",
  "ctx_id": "ctx_01HZX8M3N4P5Q6R7S8T9U0V1W2",
  "action": "tool.invoke",
  "payload": {
    "tool": "filesystem.write",
    "path": "/workspace/output.txt",
    "content": "hello"
  }
}
```

### Invalid: missing CTX-ID

Reason: missing CTX-ID MUST be treated as `UNTRUSTED`; trusted action processing must not continue.

```json
{
  "session_id": "sess_01HZX8K9M9T1Q7V6A2B3C4D5E6",
  "action": "tool.invoke",
  "payload": {
    "tool": "filesystem.write"
  }
}
```

### Valid: VTZ enforcement decision

```json
{
  "verdict": "block",
  "session_id": "sess_01HZX8K9M9T1Q7V6A2B3C4D5E6",
  "ctx_id": "ctx_01HZX8M3N4P5Q6R7S8T9U0V1W2",
  "vtz_id": "vtz_prod_backend",
  "action": "tool.invoke",
  "reason": "cross-VTZ tool call without explicit policy authorization"
}
```

### Valid: TrustFlow event

```json
{
  "event_id": "evt_4f7d9c4e8c9b4f1e9c2d7a6b5e1f3a2c",
  "session_id": "sess_01HZX8K9M9T1Q7V6A2B3C4D5E6",
  "ctx_id": "ctx_01HZX8M3N4P5Q6R7S8T9U0V1W2",
  "ts": 1735689600123,
  "event_type": "vtz.block",
  "payload_hash": "8c5e5d4f7a0c2f2b6f6b8d2a1a4e3f9c7b2d1e0f6a5c4b3d2e1f0a9b8c7d6e5"
}
```

### Invalid: TrustFlow event with sequential ID and second-precision timestamp

Reason:
- `event_id` must be CSPRNG-generated, not sequential
- `ts` must have millisecond precision

```json
{
  "event_id": "event_000001",
  "session_id": "sess_01HZX8K9M9T1Q7V6A2B3C4D5E6",
  "ctx_id": "ctx_01HZX8M3N4P5Q6R7S8T9U0V1W2",
  "ts": 1735689600,
  "event_type": "vtz.allow",
  "payload_hash": "abcd"
}
```

### Valid: consensus run request

```json
{
  "task": "Implement: Add audit logging",
  "context": "Existing module requires synchronous TrustFlow emission.",
  "language": "python"
}
```

### Invalid: consensus run request without language

Reason: language must always be passed.

```json
{
  "task": "Implement: Add audit logging",
  "context": "Existing module requires synchronous TrustFlow emission."
}
```

## Integration Points

### Consensus engine

CraftedAgent MUST call consensus with:

- `task`
- `context`
- `language`

Result consumption:

- Read generated code from `result.final_code`

### Enforcement path

The enforcement path integrates:

1. CTX-ID validation
2. VTZ policy evaluation
3. `VTZEnforcementDecision` creation on denial
4. synchronous `TrustFlowEvent` emission
5. execution only if permitted by policy

### Path security

Before any file write:

- Call `path_security.validate_write_path()`

### Prompt construction

When external content is used:

- Scan all loaded document chunks for injection before prompt inclusion
- Place external document context in the USER prompt
- Never place external document context in the SYSTEM prompt

### LLM refusal handling

If LLM output equals or contains `SECURITY_REFUSAL`:

- stop
- gate
- log
- do not retry to bypass

### Test and conformance prerequisites

Before modifying CraftedAgent:

1. Find the owning TRD via `README.md`
2. Read relevant TRD sections
3. Check TRD-11 if credentials, external content, generated code, or CI are involved
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```