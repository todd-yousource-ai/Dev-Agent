# Interface Contracts - CraftedDevAgent

This document defines the wire-format and API contract for the CraftedDevAgent subsystem based on the provided TRD standards and component interface contracts.

## Data Structures

### `ConsensusRunRequest`
Request passed to the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Human-readable implementation task. Example format: `"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string supplied to consensus engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. |

### `ConsensusRunResult`
Result returned by the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output. |

---

### `VTZEnforcementDecision`
Record produced when VTZ policy denies execution.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | For denial, MUST be exactly `block`. |

---

### `TrustFlowEvent`
Synchronous audit/event record emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique. Must be generated with CSPRNG, not sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

---

### `CTXIDToken`
Immutable trust/context token.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Token identifier. Immutable once issued. |
| `session_id` | `string` | Yes | Session bound to CTX-ID. |
| `vtz` | `string` | Yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance. |
| `expires_at` | `number` | Yes | Expiration time. Expired CTX-ID MUST be rejected. |
| `signature` | `string` | Yes | MUST validate against TrustLock public key. |

> Contract constraint: CTX-ID tokens are immutable once issued. Rotation creates a new token and invalidates the old one immediately.

---

### `AgentActionPayload`
Serialized action payload used in enforcement and TrustFlow hashing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | Yes | Associated session. |
| `ctx_id` | `string` | Yes | Must be validated first at entry points. |
| `action_type` | `string` | Yes | Agent action type. |
| `payload` | `object` | Yes | Action-specific content. Used to compute `payload_hash`. |

---

### `SecurityRefusalOutput`
LLM refusal output signaling security stop conditions.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `status` | `string` | Yes | When value is `SECURITY_REFUSAL`, processing MUST stop, gate, and log. Never retry to bypass. |

---

## Enums and Constants

### `language`
Allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### System Selection Constants
Derived by language selection:

| Language | Selected System |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` |
| `"python"` | `GENERATION_SYSTEM` |

Constraint:
- `SWIFT_UI_ADDENDUM` is injected when UI keywords are detected.

### `VTZEnforcementDecision.verdict`
Known required value from contract:

- `block`

### `SecurityRefusalOutput.status`
Known required value:

- `SECURITY_REFUSAL`

### Logging / Audit Severity Constants
Known required severity:

- `WARN` — failed TrustFlow emission is a WARN-level audit event.

---

## Validation Rules

## 1. Pre-Implementation Agent Requirements

Before modifying a component:

1. Find the TRD that owns the component in `README.md`.
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

## 2. Consensus Engine Contract

The consensus engine MUST always be called with `language`.

Required usage shape:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

Rules:
- `language` is mandatory.
- `result.final_code` is the code output field.
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Length-based arbitration is forbidden.

Forbidden pattern:

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

---

## 3. CAL Enforcement Contract

Every entry point that processes an agent action MUST satisfy all of the following:

1. Call CTX-ID validation first.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy before execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

---

## 4. TrustFlow Emission Contract

Every `TrustFlowEvent` MUST include:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Rules:
- `event_id` MUST be globally unique.
- `event_id` MUST use CSPRNG.
- `event_id` MUST NOT be sequential.
- `ts` MUST be a UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a `WARN`-level audit event.
- Failed emission is not a silent skip.

---

## 5. CTX-ID Contract

Rules:
- CTX-ID tokens are immutable once issued.
- No field modification is permitted after issuance.
- CTX-ID rotation creates a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from surrounding context.

---

## 6. VTZ Enforcement Contract

Rules:
- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance.
- VTZ policy changes do not take effect mid-session.

---

## 7. Security Rules

The subsystem MUST enforce all of the following:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` output is seen from the LLM: stop, gate, log, and never retry to bypass.

Forbidden Swift patterns:

```swift
// FORBIDDEN: force unwrap
let value = optional!

// FORBIDDEN: LLM API call from Swift
let client = AnthropicClient(apiKey: keychainValue)

// FORBIDDEN: Keychain read for backend
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
// Only Swift reads Keychain, only to deliver via XPC
```

---

## 8. Python Backend Rules

Required backend constraints:

- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- `pytest` for all tests
- Tests live in `tests/`
- Tests mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage must be `≥ 85%` on all new modules
- `pyyaml` must be in `requirements.txt`

---

## Wire Format Examples

## 1. Valid `ConsensusRunRequest`

```json
{
  "task": "Implement: Add file validator",
  "context": "Existing module layout and test expectations",
  "language": "python"
}
```

## 2. Invalid `ConsensusRunRequest` — missing `language`

```json
{
  "task": "Implement: Add file validator",
  "context": "Existing module layout and test expectations"
}
```

Reason:
- `language` is mandatory.

---

## 3. Invalid `ConsensusRunRequest` — unsupported `language`

```json
{
  "task": "Implement: Add file validator",
  "context": "Existing module layout and test expectations",
  "language": "java"
}
```

Reason:
- `language` must be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

---

## 4. Valid `TrustFlowEvent`

```json
{
  "event_id": "5f6a9d9a-8e71-4b73-b7c8-6d6b9c0f2e11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"
}
```

## 5. Invalid `TrustFlowEvent` — sequential ID and missing hash

```json
{
  "event_id": "1002",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600,
  "event_type": "allow"
}
```

Reasons:
- `event_id` must be globally unique and CSPRNG-generated, not sequential.
- `payload_hash` is required.
- `ts` must be millisecond-precision UTC Unix timestamp.

---

## 6. Valid `VTZEnforcementDecision`

```json
{
  "verdict": "block"
}
```

## 7. Invalid `VTZEnforcementDecision`

```json
{
  "verdict": "deny"
}
```

Reason:
- Contract requires `verdict=block` for VTZ policy denial.

---

## 8. Valid `SecurityRefusalOutput`

```json
{
  "status": "SECURITY_REFUSAL"
}
```

Behavior requirement:
- Stop
- Gate
- Log
- Never retry to bypass

---

## Integration Points

## 1. Consensus Engine
CraftedDevAgent integrates with a consensus engine through:

- Method: `self._consensus.run(...)`
- Required request fields:
  - `task`
  - `context`
  - `language`
- Required response field:
  - `final_code`

---

## 2. TrustFlow
CraftedDevAgent MUST emit synchronous `TrustFlowEvent` records in the enforcement path for every action outcome:
- `allow`
- `restrict`
- `block`

Integration constraint:
- Emission failure must be logged and surfaced.
- Emission failure must not be silently ignored.

---

## 3. CTX-ID Validation / TrustLock
CraftedDevAgent MUST validate CTX-ID before any action processing.

Integration constraints:
- Validation must happen first.
- Validation must use TrustLock public key.
- Missing or expired CTX-ID causes immediate rejection.
- Software-only validation is rejected.

---

## 4. VTZ Policy Enforcement
CraftedDevAgent MUST evaluate VTZ policy before executing any action.

Integration constraints:
- Cross-VTZ tool calls require explicit policy authorization.
- Denials must produce `VTZEnforcementDecision { "verdict": "block" }`.

---

## 5. Path Security
Before any disk write, CraftedDevAgent MUST call:

```python
path_security.validate_write_path()
```

Constraint:
- Validation must happen before any write operation.

---

## 6. Prompt Construction / Injection Scanning
When using external documents:

- Every loaded document chunk must pass injection scanning before inclusion in any LLM prompt.
- External document context must be placed in the USER prompt.
- External document context must never be placed in the SYSTEM prompt.

---

## 7. Swift / XPC Boundary
Constraints inferred from forbidden patterns:

- Swift must not perform direct LLM API calls.
- Backend Python reads nothing from Keychain.
- Only Swift reads Keychain, and only to deliver via XPC.

---

## Non-Conformance Conditions

A CraftedDevAgent implementation is non-conformant if any of the following occur:

- An agent action entry point does not validate CTX-ID first.
- CTX-ID validation failure allows partial processing.
- VTZ policy is not checked before execution.
- VTZ denial does not produce `verdict=block`.
- A TrustFlow event is not emitted for an action outcome.
- TrustFlow emission failure is silently ignored.
- TrustFlow emission is async-buffered in the enforcement path.
- CTX-ID fields are modified after issuance.
- Expired or missing CTX-ID is accepted.
- CTX-ID validation does not use TrustLock public key.
- Cross-VTZ access is implicitly allowed.
- `language` is omitted from consensus calls.
- Length-based fix arbitration is used instead of `_score_fix()`.
- `SECURITY_REFUSAL` is retried.
- A disk write occurs before `path_security.validate_write_path()`.
- External content is inserted into the SYSTEM prompt.
- HTTP response bodies are logged.
- `shell=True`, `eval()`, or `exec()` is used on generated/external content.