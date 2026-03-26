# Interface Contracts - CraftedDevAgent

## Data Structures

### Consensus Engine Invocation

Structured contract for invoking the consensus engine from CraftedDevAgent.

#### `ConsensusRunRequest`
Type: conceptual call contract

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Free-form task string. Example source usage: `f"Implement: {spec.title}"`. |
| `context` | `str` | Yes | Prompt/context string supplied to the consensus engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. Exact allowed values only. |

#### `ConsensusRunResult`
Type: object

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Generated code result consumed by CraftedDevAgent. |

Source contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

---

### Fix Loop Strategy Selection

Structured contract inferred from required strategy selection behavior.

#### `_choose_strategy(...)`
Type: internal function contract

| Parameter | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | implementation-defined | Yes | Strategy selection is failure-type-aware. |
| `attempt` | implementation-defined | Yes | Current retry/fix attempt number. |
| `records` | implementation-defined | Yes | Prior records/history used for strategy selection. |

Constraints:
- Must be used instead of any static lookup table.
- Strategy selection is dynamic and failure-type-aware.

---

### Fix Arbitration Scoring

Structured contract inferred from required fix arbitration behavior.

#### `_score_fix(...)`
Type: internal function contract

| Parameter | Type | Required | Constraints |
|---|---|---:|---|
| `...` | implementation-defined | Yes | Must score candidate fixes based on assertion token overlap. |

Constraints:
- Must be used for fix arbitration.
- Response length must not be used as the arbitration criterion.

Forbidden example:

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

---

### VTZ Enforcement Decision Record

#### `VTZEnforcementDecision`
Type: record

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | enum-like string | Yes | Must support value `block` for VTZ policy denial. |

Constraints:
- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlow Event

#### `TrustFlowEvent`
Type: record

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | Yes | Must be globally unique. Must be generated via CSPRNG. Must not be sequential. |
| `session_id` | `str` | Yes | Session identifier. |
| `ctx_id` | `str` | Yes | CTX-ID associated with the event. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `str` | Yes | Event type identifier. |
| `payload_hash` | `str` | Yes | Must be SHA-256 of the serialized action payload. |

Constraints:
- Every action outcome `(allow, restrict, block)` must emit a TrustFlow event.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission must not be silently skipped.
- TrustFlow emission failure must be logged and surfaced.

---

### CTX-ID Token

#### `CTXIDToken`
Type: token / record

Fields: not enumerated in source material.

Constraints:
- CTX-ID tokens are immutable once issued.
- No field modification is permitted after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately on rotation.
- Expired CTX-ID must be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from surrounding context when CTX-ID is missing.

---

### Agent Action Processing Entry Point

#### `AgentActionRequest`
Type: conceptual request

Fields: action payload is implementation-defined.

Required processing order:
1. CTX-ID validation first.
2. Immediate rejection on CTX-ID validation failure.
3. VTZ policy check before execution.
4. Emit TrustFlow event for every outcome.

Constraints:
- No partial processing is allowed before CTX-ID validation succeeds.

---

## Enums and Constants

### Language Enum

Exact allowed values for consensus invocation:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Language-Specific System Selection

| `language` value | Selected system |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected |
| `"python"` | `GENERATION_SYSTEM` |

Notes:
- `SWIFT_UI_ADDENDUM` is injected only when UI keywords are detected.
- `GENERATION_SYSTEM` is the security-focused Python ruleset.

### VTZ Verdict Values

Known required value:
- `block`

### Action Outcomes Requiring TrustFlow Emission

Required values:
- `allow`
- `restrict`
- `block`

### Trust State Constant

Required handling value:
- `UNTRUSTED`

### Special LLM Output

Required sentinel:
- `SECURITY_REFUSAL`

Behavior:
- Stop.
- Gate.
- Log.
- Never retry to bypass.

### Python Runtime / Tooling Constants

- Python version: `3.12`
- Test runner: `pytest`
- Linter: `ruff`
- Type checker: `mypy`
- YAML dependency requirement: `pyyaml`
- Coverage requirement: `>= 85%` on all new modules

---

## Validation Rules

### Pre-Implementation Process Contract

Before modifying code:
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
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

### Consensus Invocation Rules

- CraftedDevAgent must always pass `language` to `self._consensus.run(...)`.
- `language` must be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`
- Caller reads generated code from `result.final_code`.

---

### Fix Loop Rules

- Fix loop strategy must use `_choose_strategy(failure_type, attempt, records)`.
- Static lookup table strategy selection is non-conformant.
- Fix arbitration must use `_score_fix()`.
- Length-based arbitration is forbidden.

---

### Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Only log HTTP status codes and error types.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents must go in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL` output:
  - stop
  - gate
  - log
  - never retry to bypass

---

### Python Backend Rules

- Python `3.12`.
- Type annotations on every function.
- `async/await` throughout the backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- Tests must use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be at least `85%` on all new modules.
- `pyyaml` must be present in `requirements.txt`.

---

### CAL Enforcement Rules

- Every entry point processing an agent action must call CTX-ID validation first.
- CTX-ID validation failure must cause immediate rejection.
- No partial processing is allowed after validation failure.
- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce `VTZEnforcementDecision` with `verdict=block`.
- Every action outcome must emit a TrustFlow event.
- TrustFlow emission failure must not silently continue.
- TrustFlow emission failure must be logged and surfaced.

---

### TrustFlow Validation Rules

For every `TrustFlowEvent`:
- `event_id` must be globally unique.
- `event_id` generation must use CSPRNG.
- `event_id` must not be sequential.
- `ts` must be a UTC Unix timestamp with millisecond precision.
- `payload_hash` must equal SHA-256 of the serialized action payload.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is WARN-level audit behavior.

---

### CTX-ID Validation Rules

- Tokens are immutable after issuance.
- Rotation creates a new token and immediately invalidates the old token.
- Expired tokens must be rejected.
- Clock skew tolerance is deployment-defined.
- Validation must be against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity inference without CTX-ID is forbidden.

---

### VTZ Enforcement Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

### Swift-Specific Forbidden Patterns

Forbidden exactly as specified:

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

## Wire Format Examples

## Valid Payloads

### Consensus Run Request

```json
{
  "task": "Implement: Add login endpoint",
  "context": "Relevant TRD excerpts and implementation context",
  "language": "python"
}
```

### Consensus Run Result

```json
{
  "final_code": "async def login(...) -> dict:\n    ..."
}
```

### TrustFlow Event

```json
{
  "event_id": "c2c9d6b7-6d1e-4c69-9f35-7bc89f7a2d10",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

### VTZ Enforcement Decision

```json
{
  "verdict": "block"
}
```

## Invalid Payloads

### Invalid Consensus Run Request: missing `language`

```json
{
  "task": "Implement: Add login endpoint",
  "context": "Relevant TRD excerpts and implementation context"
}
```

Reason:
- `language` is required and must always be passed.

### Invalid Consensus Run Request: unsupported `language`

```json
{
  "task": "Implement: Add login endpoint",
  "context": "Relevant TRD excerpts and implementation context",
  "language": "java"
}
```

Reason:
- Allowed values are exactly `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

### Invalid TrustFlow Event: missing required field

```json
{
  "event_id": "c2c9d6b7-6d1e-4c69-9f35-7bc89f7a2d10",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.block"
}
```

Reason:
- `payload_hash` is required.

### Invalid TrustFlow Event: nonconformant `event_id`

```json
{
  "event_id": "1001",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

Reason:
- `event_id` must be globally unique and not sequential.

### Invalid VTZ Enforcement Decision

```json
{
  "verdict": "allow"
}
```

Reason:
- For VTZ policy denial, the record must be produced with `verdict=block`.

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
- Always pass `language`.
- `"swift"` selects `SWIFT_GENERATION_SYSTEM` and optionally `SWIFT_UI_ADDENDUM`.
- `"python"` selects `GENERATION_SYSTEM`.

---

### Path Security

Function:
- `path_security.validate_write_path()`

Integration requirement:
- Must be called before any file path is written to disk.

---

### Injection Scanning

Integration requirement:
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.

---

### Prompt Placement Contract

Integration requirement:
- External document context belongs in the USER prompt.
- External document context must never be placed in the SYSTEM prompt.

---

### TrustLock

Integration requirement:
- CTX-ID validation must be performed against the TrustLock public key.
- Software-only validation is rejected.

---

### XPC / Keychain Boundary

Integration requirement:
- Only Swift reads Keychain.
- Swift may read Keychain only to deliver via XPC.
- Python reads nothing from Keychain.

---

### Test and Quality Toolchain

Commands / tools:
- `pytest`
- `ruff`
- `mypy`

Required baseline test command:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Required repository layout:
- tests in `tests/`
- tests mirror `src/`

Required dependency:
- `pyyaml` in `requirements.txt`