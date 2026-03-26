# Interface Contracts - CraftedDevAgent

Definitive wire format and API contract reference for the CraftedDevAgent subsystem.

## Data Structures

All structured backend data MUST use dataclasses. Python target is 3.12 with type annotations on every function.

### ConsensusRunRequest

Request passed to the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Human-readable implementation task. Example source usage: `f"Implement: {spec.title}"`. |
| `context` | `str` | Yes | Context string supplied to the model. External document context MUST appear only in the USER prompt, never the SYSTEM prompt. All loaded document chunks MUST pass injection scanning before inclusion. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Language MUST always be passed. Exact allowed values are fixed to the listed literals. |

#### Behavioral requirements
- Invocation shape MUST be:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result returned by the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Generated code output selected by consensus/fix arbitration. |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `str` | Yes | MUST be exactly `block` for VTZ policy denial records. |

#### Behavioral requirements
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Synchronous enforcement-path audit event.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | Yes | MUST be globally unique. MUST be generated using CSPRNG. MUST NOT be sequential. |
| `session_id` | `str` | Yes | Session identifier for the agent session. |
| `ctx_id` | `str` | Yes | CTX-ID associated with the action/event. Missing CTX-ID MUST be treated as untrusted at enforcement time. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `str` | Yes | Event type identifier. |
| `payload_hash` | `str` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Behavioral requirements
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is NOT permitted.
- TrustFlow emission failure MUST NOT silently continue.
- Failed emission is a WARN-level audit event and MUST be logged and surfaced.

---

### CTX-ID Token

Opaque token representing issued context identity.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | Yes | Immutable once issued. Validation is mandatory before any agent action processing. |

#### Behavioral requirements
- CTX-ID validation MUST occur FIRST at every entry point that processes an agent action.
- CTX-ID validation failure MUST result in immediate rejection with no partial processing.
- CTX-ID tokens are immutable once issued.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from surrounding context when CTX-ID is missing.

---

### Agent Action Payload

Serialized payload whose digest is used for TrustFlow emission.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `payload` | `object` | Yes | Serialized form MUST be stable enough to compute `payload_hash = SHA-256(serialized action payload)`. |

#### Behavioral requirements
- The serialized action payload is the exact input to the `payload_hash` computation.

---

### Fix Strategy Selection Input

Internal arbitration input for failure-aware retry strategy.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `str` | Yes | Passed to `_choose_strategy(failure_type, attempt, records)`. |
| `attempt` | `int` | Yes | Retry attempt number. |
| `records` | `list[object]` | Yes | Historical attempt/failure records passed into strategy selection. |

#### Behavioral requirements
- Fix loop strategy MUST be failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup table strategy selection is non-conformant.

---

### Fix Arbitration Input

Internal arbitration input for selecting a fix candidate.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `assertion_tokens` | `list[str]` | Yes | Tokens derived from assertions/failure signals. |
| `candidate_fix` | `str` | Yes | Candidate fix content to score. |

#### Behavioral requirements
- Fix arbitration MUST use `_score_fix()` based on assertion token overlap.
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

### CTX-ID Trust State

| Value | Meaning |
|---|---|
| `UNTRUSTED` | Used when CTX-ID is missing. Missing CTX-ID MUST be treated as untrusted. |

### VTZ Verdict

| Value | Meaning |
|---|---|
| `block` | Required verdict value for a VTZ policy denial record. |

### Action Outcomes Requiring TrustFlow Emission

Exact outcome values:

- `allow`
- `restrict`
- `block`

### Generation System Selectors

| Value | Usage |
|---|---|
| `SWIFT_GENERATION_SYSTEM` | Selected when `language="swift"` |
| `SWIFT_UI_ADDENDUM` | Optional addendum injected for Swift when UI keywords are detected |
| `GENERATION_SYSTEM` | Selected when `language="python"` |

### Security Refusal Sentinel

| Value | Meaning |
|---|---|
| `SECURITY_REFUSAL` | When observed in LLM output, processing MUST stop, gate, and log. Retry to bypass is forbidden. |

---

## Validation Rules

## Entry Point Enforcement Order

Every entry point that processes an agent action MUST enforce the following order:

1. CTX-ID validation FIRST.
2. Immediate rejection on CTX-ID validation failure.
3. VTZ policy check BEFORE execution.
4. On denial, produce `VTZEnforcementDecision` with `verdict=block`.
5. Emit TrustFlow event for every outcome (`allow`, `restrict`, `block`).
6. If TrustFlow emission fails, do NOT silently continue; log and surface failure.

## Consensus Engine Rules

- `language` is mandatory on every consensus run.
- Allowed language values are exactly:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`
- `result.final_code` is the code retrieval field.
- `language="swift"` MUST select `SWIFT_GENERATION_SYSTEM` and MAY include `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` MUST select `GENERATION_SYSTEM`.

## Fix Loop and Arbitration Rules

- `_choose_strategy(failure_type, attempt, records)` MUST be used.
- Length-based fix arbitration is forbidden.
- `_score_fix()` MUST be used for arbitration.
- Arbitration basis is assertion token overlap, not response length.

### Explicitly forbidden example

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

## Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Only log HTTP status codes and error types.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`, processing MUST stop, gate, and log. Never retry to bypass.

## Swift/Backend Boundary Rules

Forbidden patterns:

```swift
// FORBIDDEN: force unwrap
let value = optional!

// FORBIDDEN: LLM API call from Swift
let client = AnthropicClient(apiKey: keychainValue)

// FORBIDDEN: Keychain read for backend
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
// Only Swift reads Keychain, only to deliver via XPC
```

Derived constraints:
- Swift MUST NOT perform backend LLM API calls directly.
- Python backend MUST NOT read from Keychain.
- Only Swift may read Keychain, and only to deliver via XPC.
- Force unwrap is forbidden in Swift code.

## Python Backend Rules

- Python version MUST be 3.12.
- Backend MUST use `async/await` throughout.
- Blocking calls on the event loop are forbidden.
- Dataclasses MUST be used for all structured data.
- Tests MUST use `pytest`.
- Tests MUST live in `tests/` and mirror `src/` structure.
- `ruff` MUST pass clean.
- `mypy` MUST pass clean.
- Test coverage MUST be at least 85% on all new modules.
- `pyyaml` MUST be present in `requirements.txt`.

## CAL / VTZ / CTX-ID / TrustFlow Rules

### CAL Enforcement
- Every entry point that processes an agent action MUST call CTX-ID validation first.
- CTX-ID validation failure MUST result in immediate rejection with no partial processing.
- Every action MUST be checked against VTZ policy before execution.
- VTZ policy denial MUST produce `VTZEnforcementDecision` with `verdict=block`.
- Every action outcome MUST emit a TrustFlow event.
- TrustFlow emission failure MUST NOT silently continue.

### TrustFlow Emission
- Every TrustFlow event MUST include:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- `event_id` MUST be globally unique, generated via CSPRNG, not sequential.
- `ts` MUST be a UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.

### CTX-ID
- Tokens are immutable once issued.
- Rotation creates a new token and immediately invalidates the old token.
- Expired tokens MUST be rejected.
- Validation MUST be against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.

### VTZ
- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

## Testing and Pre-Work Contract

Before modifying the subsystem:

1. Find the owning TRD in `README.md`.
2. Read relevant TRD sections, especially:
   - interfaces
   - error contracts
   - security
   - testing requirements
3. Check `TRD-11` if change touches:
   - credentials
   - external content
   - generated code
   - CI
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## Wire Format Examples

## Valid Payloads

### Valid consensus engine request

```json
{
  "task": "Implement: Add session validation",
  "context": "User supplied implementation context",
  "language": "python"
}
```

### Valid consensus engine result

```json
{
  "final_code": "from dataclasses import dataclass\n..."
}
```

### Valid TrustFlow event

```json
{
  "event_id": "9f5d2b3e-6d0b-4f9d-9d53-6cdd7f5ab8d1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1712345678901,
  "event_type": "block",
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa135014..."
}
```

### Valid VTZ denial decision

```json
{
  "verdict": "block"
}
```

### Valid CTX-ID-bearing action envelope

```json
{
  "ctx_id": "ctx_abc123",
  "payload": {
    "action": "generate_code",
    "target": "module_x"
  }
}
```

## Invalid Payloads

### Invalid consensus request: missing language

```json
{
  "task": "Implement: Add session validation",
  "context": "User supplied implementation context"
}
```

Reason:
- `language` is required.

### Invalid consensus request: unsupported language

```json
{
  "task": "Implement: Add session validation",
  "context": "User supplied implementation context",
  "language": "java"
}
```

Reason:
- `language` MUST be exactly one of `python`, `swift`, `go`, `typescript`, `rust`.

### Invalid TrustFlow event: missing required fields

```json
{
  "event_id": "123",
  "event_type": "allow"
}
```

Reason:
- Missing `session_id`, `ctx_id`, `ts`, and `payload_hash`.

### Invalid VTZ denial decision

```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ denial record verdict MUST be exactly `block`.

### Invalid action processing: missing CTX-ID

```json
{
  "payload": {
    "action": "generate_code"
  }
}
```

Reason:
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Processing must not infer identity from context.

### Invalid implementation pattern: length-based arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- Length-based fix arbitration is forbidden; use `_score_fix()`.

---

## Integration Points

## Consensus Engine

Required call contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Integration constraints:
- `language` MUST always be passed.
- `spec.language` MUST resolve to one of:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`

## Prompt Construction

- External document context MUST be placed in the USER prompt only.
- External document chunks MUST pass injection scanning before inclusion.
- Generated or external content MUST NEVER be executed via `eval()` or `exec()`.

## File System Writes

Before any write to disk:

```python
path_security.validate_write_path(...)
```

Constraint:
- All file paths written to disk MUST pass `path_security.validate_write_path()` before write.

## TrustLock / CTX-ID Validation

Integration constraints:
- CTX-ID validation MUST occur before any action processing.
- Validation MUST use TrustLock public key.
- Software-only validation is rejected.

## TrustFlow Audit Pipeline

Integration constraints:
- Emit synchronously in enforcement path.
- Include all required fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- Failure MUST be logged at WARN level and surfaced.

## VTZ Policy Engine

Integration constraints:
- Every session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- VTZ policy changes apply only at next CTX-ID issuance.

## Swift ↔ Backend XPC Boundary

Integration constraints:
- Only Swift reads Keychain.
- Swift may deliver secrets via XPC.
- Python backend reads nothing from Keychain.
- Swift must not instantiate backend LLM clients directly.

## Tooling and Test Integration

Required command before work:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Required quality gates:
- `pytest`
- `ruff`
- `mypy`
- coverage ≥ 85% on all new modules