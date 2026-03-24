# Interface Contracts - ForgeAgent

This document defines the wire-format and API contract reference for the ForgeAgent subsystem, derived from the provided TRD excerpts and standards. Requirements stated as MUST/REQUIRED are normative.

## Data Structures

All structured backend data MUST use dataclasses. Python implementation target is Python 3.12 with type annotations on every function.

### ConsensusRunRequest

Request passed to the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Free-form task text. Example source usage: `f"Implement: {spec.title}"`. |
| `context` | `str` | Yes | Context string supplied to consensus engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | MUST always be passed. Values exactly as listed. |

#### Semantics
- ForgeAgent MUST always call consensus with `language`.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result returned by the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Final generated code output. |

#### Semantics
- ForgeAgent reads generated code from `result.final_code`.

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `str` | Yes | MUST be `"block"` when produced for VTZ policy denial. |

#### Semantics
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Synchronous audit/event record emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | Yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | `str` | Yes | Session identifier. |
| `ctx_id` | `str` | Yes | CTX-ID associated with the action/session. |
| `ts` | `int` or `float` | Yes | MUST be UTC Unix timestamp with millisecond precision. |
| `event_type` | `str` | Yes | Event type identifier. |
| `payload_hash` | `str` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Semantics
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is NOT permitted.
- Emission failure MUST NOT silently continue.
- Failed emission is a WARN-level audit event and MUST be surfaced.

---

### AgentActionPayload

Serialized action payload used for enforcement and hashing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `payload` | serialized object/bytes/string | Yes | Exact application-defined action payload serialized prior to hashing. |

#### Semantics
- `payload_hash` in `TrustFlowEvent` MUST be the SHA-256 of the serialized action payload.

---

### CTXIDToken

Immutable trust context token.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | Yes | Token identifier. Immutable after issuance. |
| `vtz` | `str` | Yes | Every agent session is bound to exactly one VTZ at issuance. |
| `expired` | `bool` | Yes | If true, token MUST be rejected. |
| `issued_at` | UTC Unix timestamp | Implementation-defined | Implied by issuance lifecycle. |
| `rotated_from` | `str` | No | Present only for rotation lineage if modeled. |

#### Semantics
- CTX-ID tokens are IMMUTABLE once issued.
- Rotation creates a new token; old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.

> Note: Only constraints explicitly present in source are normative. Additional fields beyond `ctx_id` are implementation-defined unless required by another subsystem.

---

### AgentActionRequest

Canonical action-processing request entering ForgeAgent enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `str` | Yes | Session identifier. |
| `ctx_id` | `str` | Yes | MUST be validated first. If missing, request is `UNTRUSTED`. |
| `action` | serialized object | Yes | Action to be checked against VTZ policy before execution. |
| `vtz` | `str` | Yes | MUST match session binding established at CTX-ID issuance. |

#### Semantics
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection with no partial processing.
- Every action MUST be checked against VTZ policy BEFORE execution.

---

### SecurityRefusalSignal

LLM refusal output signaling security gate stop.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `output` | `str` | Yes | When equal to `SECURITY_REFUSAL`, processing MUST stop. |

#### Semantics
- When `SECURITY_REFUSAL` output is observed: stop, gate, log.
- Never retry to bypass.

---

### FixStrategySelectionInput

Input to failure-type-aware fix loop strategy selection.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `str` | Yes | Failure classification. |
| `attempt` | `int` | Yes | Attempt number. |
| `records` | collection | Yes | Prior fix records/history. |

#### Semantics
- Fix loop strategy MUST use `_choose_strategy(failure_type, attempt, records)`.
- Static lookup table strategy selection is non-conformant.

---

### FixArbitrationInput

Input to fix arbitration scoring.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `assertion_tokens` | collection of `str` | Yes | Tokens from assertions/failures used in overlap scoring. |
| `candidate_fix` | `str` | Yes | Candidate fix text/code. |

#### Semantics
- Fix arbitration MUST use `_score_fix()` based on assertion token overlap.
- Length-based arbitration is forbidden.

## Enums and Constants

### Language

Allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

These values MUST appear exactly as above.

---

### ActionOutcome

Allowed action outcomes requiring TrustFlow emission:

- `allow`
- `restrict`
- `block`

---

### Security and Policy Constants

| Constant | Type | Exact Value / Meaning |
|---|---|---|
| `SECURITY_REFUSAL` | `str` | Security refusal output from LLM; stop, gate, log. |
| `SWIFT_GENERATION_SYSTEM` | system selector | Selected when `language="swift"`. |
| `SWIFT_UI_ADDENDUM` | system selector/addendum | Optionally injected for Swift when UI keywords are detected. |
| `GENERATION_SYSTEM` | system selector | Selected when `language="python"`. |
| `UNTRUSTED` | trust state | State assigned when CTX-ID is missing. |

> Selector constant payloads are not provided in the source excerpt; only their exact identifiers and selection rules are normative here.

## Validation Rules

### 1. Entry-Point Enforcement Order

For every entry point that processes an agent action:

1. CTX-ID validation MUST happen first.
2. If CTX-ID validation fails, processing MUST be immediately rejected.
3. No partial processing is permitted before successful CTX-ID validation.
4. VTZ policy evaluation MUST occur before action execution.
5. If VTZ policy denies, produce `VTZEnforcementDecision` with `verdict="block"`.
6. Emit a `TrustFlowEvent` for every outcome: `allow`, `restrict`, `block`.

---

### 2. TrustFlow Event Validation

A `TrustFlowEvent` is valid only if:

- `event_id` is present.
- `event_id` is globally unique.
- `event_id` is generated using CSPRNG.
- `event_id` is not sequential.
- `session_id` is present.
- `ctx_id` is present.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `event_type` is present.
- `payload_hash` is present.
- `payload_hash` equals SHA-256 of the serialized action payload.

Emission rules:

- Emission MUST be synchronous in the enforcement path.
- Async buffering is forbidden.
- Emission failure MUST NOT be silent.
- Emission failure MUST be logged and surfaced.
- Failed emission is a WARN-level audit event.

---

### 3. CTX-ID Validation

A CTX-ID is valid only if:

- It is present; otherwise the request is `UNTRUSTED`.
- It is not expired.
- It has not been invalidated by rotation.
- It is validated against TrustLock public key.
- Validation is not software-only.

Additional rules:

- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- Old token becomes invalid immediately after rotation.
- Clock skew tolerance is deployment-defined.

---

### 4. VTZ Enforcement

- Every agent session MUST be bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

### 5. Consensus Engine Invocation

ForgeAgent MUST call consensus as:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Validation requirements:

- `language` MUST always be passed.
- `language` MUST be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

Selection behavior:

- `"swift"` => `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `"python"` => `GENERATION_SYSTEM`

---

### 6. Fix Loop and Arbitration

Required behavior:

- Fix strategy selection MUST use `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()` based on assertion token overlap.

Forbidden behavior:

```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

Length-based arbitration is non-conformant.

---

### 7. Security Rules

The following are hard requirements:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- If `SECURITY_REFUSAL` is returned, stop, gate, log, and do not retry to bypass.

---

### 8. Swift-Specific Forbidden Patterns

The following are forbidden:

```swift
let value = optional!
```

- Force unwrap is forbidden.

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

- LLM API call from Swift is forbidden.

```swift
let token = KeychainKit.read("github_token")
```

- Backend token/key reads from Keychain are forbidden.
- Only Swift reads Keychain, and only to deliver via XPC.

---

### 9. Python Implementation Requirements

- Python version MUST be 3.12.
- All functions MUST have type annotations.
- Backend MUST use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses MUST be used for all structured data.
- Tests MUST use `pytest`.
- Tests MUST live in `tests/` and mirror `src/` structure.
- `ruff` MUST pass clean.
- `mypy` MUST pass clean.
- Test coverage MUST be at least 85% on all new modules.
- `pyyaml` MUST be in `requirements.txt`.

## Wire Format Examples

## Valid Payloads

### Valid ConsensusRunRequest

```json
{
  "task": "Implement: Add login endpoint",
  "context": "Existing auth service uses async repository pattern.",
  "language": "python"
}
```

### Valid ConsensusRunResult

```json
{
  "final_code": "async def login(...) -> Response:\n    ..."
}
```

### Valid TrustFlowEvent

```json
{
  "event_id": "d2d7ef2d-4fe6-4d6a-a7cf-0d4e9cb4a4d1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678123,
  "event_type": "block",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961e9f9948c8a14e7b5833957"
}
```

### Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Valid AgentActionRequest

```json
{
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "vtz": "vtz_primary",
  "action": {
    "tool": "write_file",
    "path": "/workspace/output.txt"
  }
}
```

## Invalid Payloads

### Invalid ConsensusRunRequest: missing language

```json
{
  "task": "Implement: Add login endpoint",
  "context": "Existing auth service uses async repository pattern."
}
```

Reason:
- `language` is required and MUST always be passed.

---

### Invalid ConsensusRunRequest: unsupported language

```json
{
  "task": "Implement: Add login endpoint",
  "context": "Existing auth service uses async repository pattern.",
  "language": "java"
}
```

Reason:
- `language` MUST be one of `"python" | "swift" | "go" | "typescript" | "rust"`.

---

### Invalid TrustFlowEvent: sequential/non-compliant event id and missing payload hash

```json
{
  "event_id": "1001",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678,
  "event_type": "allow"
}
```

Reasons:
- `event_id` MUST be globally unique and CSPRNG-generated, not sequential.
- `ts` must have millisecond precision.
- `payload_hash` is required.

---

### Invalid VTZEnforcementDecision: wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ policy denial MUST produce `VTZEnforcementDecision` with `verdict="block"`.

---

### Invalid AgentActionRequest: missing ctx_id

```json
{
  "session_id": "sess_123",
  "vtz": "vtz_primary",
  "action": {
    "tool": "write_file"
  }
}
```

Reason:
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- No identity may be inferred from context.

## Integration Points

### 1. Consensus Engine

ForgeAgent integrates with consensus engine via:

```python
await self._consensus.run(task=..., context=..., language=...)
```

Contract:
- `language` is mandatory.
- Read output from `result.final_code`.

---

### 2. CAL Enforcement Path

All ForgeAgent action entry points MUST implement:

1. CTX-ID validation first
2. VTZ policy check before execution
3. `VTZEnforcementDecision(verdict="block")` on denial
4. Synchronous `TrustFlowEvent` emission for all outcomes

---

### 3. TrustLock / CTX-ID Validation

ForgeAgent MUST validate CTX-ID against TrustLock public key.

Contract:
- Software-only validation is rejected.
- Missing CTX-ID => `UNTRUSTED`
- Expired CTX-ID => reject
- Rotated old CTX-ID => reject

---

### 4. Path Security

Before any disk write:

```python
path_security.validate_write_path(...)
```

Contract:
- Validation MUST occur before every write.
- Unvalidated write paths are non-conformant.

---

### 5. Injection Scanning

Before any loaded document chunk is included in an LLM prompt:

- Injection scanning MUST be performed.

Contract:
- Unscanned external document chunks MUST NOT be included in prompts.
- External document context MUST be placed in the USER prompt only.

---

### 6. Logging / Audit

Contract:
- Never log HTTP response bodies.
- Log status codes and error types only.
- TrustFlow emission failure MUST be WARN-level and surfaced.
- `SECURITY_REFUSAL` MUST be logged and gated.

---

### 7. Testing and Conformance Workflow

Before code changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Conformance expectations:
- Relevant owning TRD MUST be identified first.
- Relevant TRD sections MUST be read before implementation.
- TRD-11 MUST be checked if change touches credentials, external content, generated code, or CI.