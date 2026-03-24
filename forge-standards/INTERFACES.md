# Interface Contracts - Crafted

This document defines the wire-format and API contract reference for the Crafted subsystem, based only on the provided TRD excerpts. It includes all explicitly specified fields, values, and constraints.

## Data Structures

### ConsensusRunRequest

Request contract for invoking the consensus engine.

```python
@dataclass
class ConsensusRunRequest:
    task: str
    context: str
    language: str
```

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Human-readable implementation task. Example: `"Implement: {spec.title}"` |
| `context` | `str` | Yes | Context string passed to the engine |
| `language` | `str` | Yes | Must be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Semantics
- `language` MUST always be passed.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result contract returned by the consensus engine.

```python
@dataclass
class ConsensusRunResult:
    final_code: str
```

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Generated code output |

---

### VTZEnforcementDecision

Required record produced when VTZ policy denies an action.

```python
@dataclass
class VTZEnforcementDecision:
    verdict: str
```

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `str` | Yes | For denial, MUST be exactly `"block"` |

#### Semantics
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Required audit/event record emitted for every action outcome.

```python
@dataclass
class TrustFlowEvent:
    event_id: str
    session_id: str
    ctx_id: str
    ts: float | int
    event_type: str
    payload_hash: str
```

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | Yes | MUST be globally unique; generated with CSPRNG; MUST NOT be sequential |
| `session_id` | `str` | Yes | Session identifier |
| `ctx_id` | `str` | Yes | CTX-ID token identifier |
| `ts` | `float \| int` | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `str` | Yes | Event type identifier |
| `payload_hash` | `str` | Yes | MUST be SHA-256 of the serialized action payload |

#### Semantics
- Every TrustFlow event MUST include all six fields exactly:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and MUST NOT be silently skipped.

---

### CTXIDToken

Logical contract for CTX-ID tokens.

```python
@dataclass
class CTXIDToken:
    ctx_id: str
```

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | Yes | Immutable once issued |

#### Semantics
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- CTX-ID MUST be validated against TrustLock public key.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.

---

### AgentActionEnvelope

Minimum processing envelope implied by enforcement requirements.

```python
@dataclass
class AgentActionEnvelope:
    session_id: str
    ctx_id: str | None
    action_payload: dict
```

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `str` | Yes | Session identifier used in TrustFlow emission |
| `ctx_id` | `str \| None` | Yes | Required for trusted processing; if missing, MUST be treated as `UNTRUSTED` |
| `action_payload` | `dict` | Yes | Serialized payload whose SHA-256 digest becomes `payload_hash` |

#### Semantics
- Every entry point that processes an agent action MUST validate `ctx_id` first.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is allowed before CTX-ID validation succeeds.

---

## Enums and Constants

### Language

Allowed values for `ConsensusRunRequest.language`:

```text
"python"
"swift"
"go"
"typescript"
"rust"
```

### Consensus System Selection Constants

These values are selected by `language`:

```text
SWIFT_GENERATION_SYSTEM
SWIFT_UI_ADDENDUM
GENERATION_SYSTEM
```

#### Selection Rules
- `language="swift"` → `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `language="python"` → `GENERATION_SYSTEM`

---

### Enforcement Verdict

Allowed explicitly specified value:

```text
"block"
```

Used in:

- `VTZEnforcementDecision.verdict`

---

### Trust State Constant

Explicitly specified value for missing CTX-ID handling:

```text
UNTRUSTED
```

---

### Security Refusal Sentinel

Explicitly specified output token:

```text
SECURITY_REFUSAL
```

#### Handling
- When `SECURITY_REFUSAL` is returned by the LLM:
  - stop
  - gate
  - log
  - never retry to bypass

---

### Warning Level Constant

Explicitly specified audit severity:

```text
WARN
```

Used when TrustFlow emission fails.

---

## Validation Rules

## 1. Pre-implementation Process Requirements

Before any code changes:
1. Find the TRD that owns the component being modified.
2. Read relevant TRD sections, especially:
   - interfaces
   - error contracts
   - security
   - testing requirements
3. Check TRD-11 if the change touches:
   - credentials
   - external content
   - generated code
   - CI
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## 2. Consensus Engine Invocation Rules

### Required Call Shape

The invocation contract is:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### Rules
- `language` MUST be passed on every call.
- `language` MUST be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

### Fix Loop Strategy Rules
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Static lookup-table strategy selection is not the contract.

### Fix Arbitration Rules
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration is forbidden.

#### Forbidden

```python
winner = max(claude_fix, openai_fix, key=len)
```

---

## 3. CAL Enforcement Contract

Every Forge/Crafted component entry point that processes an agent action MUST satisfy all of the following:

1. CTX-ID validation MUST occur first.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing may occur before CTX-ID validation.
4. Every action MUST be checked against VTZ policy before execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` with:
   - `verdict="block"`
6. Every action outcome must emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

---

## 4. TrustFlow Emission Contract

For every TrustFlow event:

- `event_id` MUST be globally unique.
- `event_id` MUST use CSPRNG generation.
- `event_id` MUST NOT be sequential.
- `ts` MUST be a UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.

---

## 5. CTX-ID Contract

- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from surrounding context when CTX-ID is missing.

---

## 6. VTZ Enforcement Contract

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 7. Security Rules

### Secrets and Credentials
- Never hardcode credentials, API keys, tokens, or secrets as string literals.

### Subprocess
- Never use `shell=True` in subprocess calls.

### Dynamic Execution
- Never call `eval()` or `exec()` on generated or external content.

### HTTP Logging
- Never log HTTP response bodies.
- Log status codes and error types only.

### File Writes
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

### External Document Handling
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.

### LLM Security Refusal
- On `SECURITY_REFUSAL`: stop, gate, log, never retry to bypass.

---

## 8. Python Backend Rules

- Python version: `3.12`
- Type annotations are required on every function.
- Backend code must use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses are required for all structured data.
- Testing framework: `pytest`
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass.
- `mypy` must pass.
- Coverage on all new modules MUST be at least `85%`.
- `pyyaml` MUST be present in `requirements.txt`.

---

## 9. Swift/Backend Boundary Rules

### Forbidden Swift patterns

```swift
let value = optional!
```

- Force unwrap is forbidden.

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

- LLM API calls from Swift are forbidden.

```swift
let token = KeychainKit.read("github_token")
```

- Backend Python reads nothing from Keychain.
- Only Swift reads Keychain.
- Swift may read Keychain only to deliver via XPC.

---

## Wire Format Examples

## 1. Valid Consensus Run Request

```json
{
  "task": "Implement: Add file writer",
  "context": "Need async Python implementation with validation.",
  "language": "python"
}
```

Why valid:
- Includes `task`
- Includes `context`
- Includes `language`
- `language` is one of the allowed values

---

## 2. Invalid Consensus Run Request: Missing language

```json
{
  "task": "Implement: Add file writer",
  "context": "Need async Python implementation with validation."
}
```

Why invalid:
- `language` is required
- Contract states language must always be passed

---

## 3. Invalid Consensus Run Request: Unsupported language

```json
{
  "task": "Implement: Add file writer",
  "context": "Need async Python implementation with validation.",
  "language": "java"
}
```

Why invalid:
- `"java"` is not one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

---

## 4. Valid TrustFlow Event

```json
{
  "event_id": "2c0b8b69-9a7c-4a77-a3d6-4e8d5e8a51f1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678.123,
  "event_type": "action_allowed",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

Why valid:
- Contains all required TrustFlow fields
- `ts` is a Unix timestamp with millisecond precision
- `payload_hash` is a SHA-256 hex digest

---

## 5. Invalid TrustFlow Event: Missing payload_hash

```json
{
  "event_id": "2c0b8b69-9a7c-4a77-a3d6-4e8d5e8a51f1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678.123,
  "event_type": "action_allowed"
}
```

Why invalid:
- `payload_hash` is mandatory

---

## 6. Invalid TrustFlow Event: Sequential event_id

```json
{
  "event_id": "10001",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678.123,
  "event_type": "action_allowed",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

Why invalid:
- `event_id` MUST be globally unique
- `event_id` MUST be generated by CSPRNG
- Sequential IDs are forbidden

---

## 7. Valid VTZ Denial Record

```json
{
  "verdict": "block"
}
```

Why valid:
- Denial contract explicitly requires `verdict=block`

---

## 8. Invalid VTZ Denial Record

```json
{
  "verdict": "deny"
}
```

Why invalid:
- Provided contract specifies denial as `verdict="block"`

---

## 9. Invalid Action Envelope: Missing CTX-ID treated as UNTRUSTED

```json
{
  "session_id": "sess_123",
  "ctx_id": null,
  "action_payload": {
    "tool": "write_file",
    "path": "/tmp/output.txt"
  }
}
```

Why invalid for trusted processing:
- Missing `ctx_id` MUST be treated as `UNTRUSTED`
- Identity cannot be inferred
- Trusted processing cannot proceed without CTX-ID validation

---

## 10. Invalid Security Handling Example

```json
{
  "llm_output": "SECURITY_REFUSAL",
  "action": "retry_with_modified_prompt"
}
```

Why invalid:
- On `SECURITY_REFUSAL`, the system must stop, gate, and log
- Retrying to bypass is forbidden

---

## Integration Points

## Consensus Engine

### Input
- `task: str`
- `context: str`
- `language: "python" | "swift" | "go" | "typescript" | "rust"`

### Output
- `final_code: str`

### Required Access Pattern

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

---

## TrustFlow

### Producer Requirements
Any component that processes agent actions must synchronously emit a `TrustFlowEvent` for every action outcome:
- allow
- restrict
- block

### Event Fields
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

---

## CTX-ID Validation

### Enforcement Point
Must be the first operation at every entry point that processes an agent action.

### Failure Behavior
- Immediate rejection
- No partial processing

### Validation Requirements
- Validate against TrustLock public key
- Software-only validation is not acceptable

---

## VTZ Policy Engine

### Invocation Timing
- Must run after successful CTX-ID validation
- Must run before action execution

### Denial Output
- Produce `VTZEnforcementDecision`
- Set `verdict` to exactly `"block"`

---

## Path Security

### Write Path Validation
Before any disk write, the target path MUST pass:

```python
path_security.validate_write_path()
```

---

## Prompt Construction

### External Content Rules
- Loaded document chunks must pass injection scanning before prompt inclusion
- External document context must be placed in the USER prompt
- External document context must never be placed in the SYSTEM prompt

---

## Test and Quality Tooling

### Required Commands / Tools
- `pytest`
- `ruff`
- `mypy`

### Required Test Invocation

```bash
cd src && pytest ../tests/ -v --tb=short
```

### Required Coverage
- `>= 85%` on all new modules

---

## Non-Conformance Conditions

A Crafted component is non-conformant if any of the following are violated:

- Missing `language` in consensus engine invocation
- Unsupported `language` value
- Length-based fix arbitration
- CTX-ID not validated first
- Partial processing before CTX-ID validation
- VTZ check omitted before execution
- VTZ denial without `verdict="block"`
- Missing TrustFlow emission
- Silent TrustFlow emission failure
- Non-synchronous TrustFlow emission in enforcement path
- Missing required TrustFlow fields
- Sequential or non-CSPRNG `event_id`
- Non-SHA-256 `payload_hash`
- Missing or unvalidated write-path checks
- Logging HTTP response bodies
- `shell=True` subprocess usage
- Use of `eval()` or `exec()` on generated/external content
- Retry after `SECURITY_REFUSAL`
- Force unwrap in Swift
- LLM API calls from Swift
- Backend Keychain reads
- Missing type annotations
- Non-async backend behavior
- Structured data not represented with dataclasses
- Failing `ruff` or `mypy`
- Coverage below `85%`
- Missing `pyyaml` in `requirements.txt`