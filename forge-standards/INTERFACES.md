# Interface Contracts - Crafted

This document defines the wire-format and API contract reference for the Crafted subsystem, derived strictly from the provided TRD excerpts.

## Data Structures

### ConsensusRunRequest

Request contract for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Free-form task description. Example uses `f"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string passed to the engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. Exact allowed values only. |

#### Constraints
- `language` is mandatory on every consensus invocation.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` and may inject `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Response contract from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output. |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies execution.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | Yes | Must be exactly `block` on VTZ policy denial. |

#### Constraints
- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Required event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique. Generated via CSPRNG, not sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event classification. Exact values not specified in provided TRD excerpt. |
| `payload_hash` | `string` | Yes | Must be SHA-256 of the serialized action payload. |

#### Constraints
- Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and must not be silently skipped.
- TrustFlow emission failure must be logged and surfaced.

---

### CTX-ID Token

Opaque token used for identity and trust validation.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. Exact internal field structure not specified in provided TRD excerpt. |

#### Constraints
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID must be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from context when CTX-ID is missing.

---

### Agent Action Processing Entry Point

Processing contract for any entry point that handles an agent action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Must be validated first. |
| `session_id` | `string` | Yes | Required for TrustFlow emission. |
| `action_payload` | `object` | Yes | Serialized payload must be hashable via SHA-256 for `payload_hash`. |
| `vtz` | `string` | Implicit | Every agent session is bound to exactly one VTZ at CTX-ID issuance. |

#### Constraints
- CTX-ID validation must occur first.
- CTX-ID validation failure must result in immediate rejection.
- No partial processing is allowed before CTX-ID validation succeeds.
- Every action must be checked against VTZ policy before execution.

---

### SecurityRefusalOutput

Special LLM output category.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `value` | `"SECURITY_REFUSAL"` | Yes | Exact literal value. |

#### Constraints
- When `SECURITY_REFUSAL` is received: stop, gate, and log.
- Never retry to bypass.

---

## Enums and Constants

### Language

Exact allowed values for consensus engine requests:

```text
"python"
"swift"
"go"
"typescript"
"rust"
```

---

### Enforcement Verdict

Exact known value from provided TRD excerpt:

```text
"block"
```

---

### Action Outcomes

Exact action outcomes requiring TrustFlow emission:

```text
"allow"
"restrict"
"block"
```

---

### Security Output Constant

```text
"SECURITY_REFUSAL"
```

---

### Consensus Engine System Selection Constants

```text
SWIFT_GENERATION_SYSTEM
SWIFT_UI_ADDENDUM
GENERATION_SYSTEM
```

These are selection/injection constants referenced by behavior; their literal contents are not defined in the provided TRD excerpt.

---

### Backend Language Constraint

```text
Python 3.12
```

---

## Validation Rules

### Consensus Engine Usage
1. Every consensus engine call must include `language`.
2. `language` must be one of:
   - `python`
   - `swift`
   - `go`
   - `typescript`
   - `rust`
3. If `language="swift"`, system selection is `SWIFT_GENERATION_SYSTEM`.
4. If `language="swift"` and UI keywords are detected, `SWIFT_UI_ADDENDUM` may be injected.
5. If `language="python"`, system selection is `GENERATION_SYSTEM`.

### Fix Strategy and Arbitration
1. Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
2. Fix arbitration must use `_score_fix()`.
3. Length-based fix arbitration is forbidden.

Forbidden example:

```python
winner = max(claude_fix, openai_fix, key=len)
```

### CAL Enforcement Contract
1. Every entry point that processes an agent action must call CTX-ID validation first.
2. CTX-ID validation failure must cause immediate rejection.
3. No partial processing may occur before CTX-ID validation completes successfully.
4. Every action must be checked against VTZ policy before execution.
5. VTZ policy denial must produce a `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome must emit a TrustFlow event.
7. TrustFlow emission failure must not silently continue.

### TrustFlow Emission Contract
1. Every TrustFlow event must include all required fields:
   - `event_id`
   - `session_id`
   - `ctx_id`
   - `ts`
   - `event_type`
   - `payload_hash`
2. `event_id` must be globally unique and CSPRNG-generated.
3. `ts` must be a UTC Unix timestamp with millisecond precision.
4. `payload_hash` must be SHA-256 of the serialized action payload.
5. Emission must be synchronous in the enforcement path.
6. Async buffering is not permitted.
7. Failed emission must be treated as a WARN-level audit event.

### CTX-ID Validation
1. CTX-ID tokens are immutable after issuance.
2. Rotation must create a new token and immediately invalidate the old one.
3. Expired CTX-ID must be rejected.
4. Validation must be against TrustLock public key.
5. Software-only validation is rejected.
6. Missing CTX-ID must be treated as `UNTRUSTED`.
7. Identity must never be inferred from ambient context.

### VTZ Enforcement
1. Every agent session is bound to exactly one VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit cross-VTZ access is denied.
4. VTZ boundaries are structural and cannot be bypassed by application code.
5. VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

### Security Rules
1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Log status codes and error types only for HTTP failures.
6. All file paths written to disk must pass `path_security.validate_write_path()` before any write.
7. All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
8. Context from external documents must go in the USER prompt, never the SYSTEM prompt.
9. On `SECURITY_REFUSAL`: stop, gate, log; never retry to bypass.

### Python Contract
1. Python version must be `3.12`.
2. Type annotations are required on every function.
3. Backend must use `async/await` throughout.
4. No blocking calls on the event loop.
5. Dataclasses are required for all structured data.
6. Tests must use `pytest`.
7. Tests must live in `tests/` and mirror `src/` structure.
8. `ruff` must pass clean.
9. `mypy` must pass clean.
10. Test coverage must be at least `85%` on all new modules.
11. `pyyaml` must be present in `requirements.txt`.

### Swift-Specific Forbidden Operations
1. Force unwrap is forbidden.

Forbidden example:

```swift
let value = optional!
```

2. LLM API calls from Swift are forbidden.

Forbidden example:

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

3. Backend token reads from Keychain are forbidden.

Forbidden example:

```swift
let token = KeychainKit.read("github_token")
```

4. Only Swift reads Keychain, and only to deliver via XPC.

---

## Wire Format Examples

### Valid: ConsensusRunRequest

```json
{
  "task": "Implement: Crafted subsystem contract",
  "context": "Use dataclasses and async backend patterns",
  "language": "python"
}
```

### Valid: ConsensusRunResult

```json
{
  "final_code": "from dataclasses import dataclass\n..."
}
```

### Valid: TrustFlowEvent

```json
{
  "event_id": "8d3d8b0f7b2d4b67b46e6f8f7d2d8c61",
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "ts": 1712345678.123,
  "event_type": "block",
  "payload_hash": "4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce"
}
```

### Valid: VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Invalid: ConsensusRunRequest Missing Language

```json
{
  "task": "Implement: Crafted subsystem contract",
  "context": "Use dataclasses and async backend patterns"
}
```

Reason:
- `language` is required.

### Invalid: ConsensusRunRequest With Unsupported Language

```json
{
  "task": "Implement: Crafted subsystem contract",
  "context": "Use dataclasses and async backend patterns",
  "language": "java"
}
```

Reason:
- `language` must be one of `python`, `swift`, `go`, `typescript`, `rust`.

### Invalid: TrustFlowEvent Missing Required Field

```json
{
  "event_id": "8d3d8b0f7b2d4b67b46e6f8f7d2d8c61",
  "session_id": "sess_123",
  "ctx_id": "ctx_456",
  "ts": 1712345678.123,
  "payload_hash": "4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce"
}
```

Reason:
- `event_type` is required.

### Invalid: VTZEnforcementDecision Wrong Verdict

```json
{
  "verdict": "allow"
}
```

Reason:
- On VTZ policy denial, `verdict` must be exactly `block`.

### Invalid: Missing CTX-ID

```json
{
  "session_id": "sess_123",
  "action_payload": {
    "tool": "write_file"
  }
}
```

Reason:
- Missing `ctx_id` must be treated as `UNTRUSTED`.
- Identity must never be inferred from context.
- Entry point must reject before partial processing.

### Invalid: Forbidden Fix Arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- Length-based arbitration is forbidden.
- `_score_fix()` must be used.

### Invalid: Forbidden Swift Force Unwrap

```swift
let value = optional!
```

Reason:
- Force unwrap is forbidden.

### Invalid: Forbidden Swift LLM API Call

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Reason:
- LLM API calls from Swift are forbidden.

### Invalid: Forbidden Keychain Read for Backend

```swift
let token = KeychainKit.read("github_token")
```

Reason:
- Backend must not read Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

---

## Integration Points

### Consensus Engine
Invocation contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Integration requirements:
- `language` must always be passed.
- Consumer must read generated code from `result.final_code`.

### CTX-ID Validation
Integration requirements:
- Must execute first in every agent action processing entry point.
- Failure must reject the request immediately.
- Validation must use TrustLock public key.
- Software-only validation is non-conformant.

### VTZ Policy Enforcement
Integration requirements:
- Must execute before any action.
- Session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ calls require explicit authorization.
- Denial must produce `VTZEnforcementDecision(verdict="block")`.

### TrustFlow
Integration requirements:
- Emit for every action outcome: `allow`, `restrict`, `block`.
- Must include all required fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- Emission must be synchronous in the enforcement path.
- Failures must be logged and surfaced as WARN-level audit events.

### Path Security
Integration requirements:
- Every file path written to disk must pass:

```python
path_security.validate_write_path()
```

before any write occurs.

### Prompt Construction / Injection Scanning
Integration requirements:
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- External document context must be placed in the USER prompt only.
- External document context must never be placed in the SYSTEM prompt.

### Security Refusal Handling
Integration requirements:
- Detect exact output `SECURITY_REFUSAL`.
- On detection: stop, gate, log.
- No retry-to-bypass behavior is permitted.

### Testing and Tooling
Integration requirements:
- Run existing tests before making changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```

- Test framework: `pytest`
- Lint: `ruff`
- Type check: `mypy`
- Coverage requirement: `>= 85%` on new modules

### Dependency Contract
Integration requirement:
- `pyyaml` must be present in `requirements.txt`.