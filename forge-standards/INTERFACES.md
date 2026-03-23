# Interface Contracts - Crafted

This document defines the wire-format and API contract reference for the Crafted subsystem, based only on the provided TRD interface requirements.

## Data Structures

### ConsensusRunRequest

Request passed to the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Human-readable task description. Example shape: `"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string supplied to consensus engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed. Exact allowed values only. |

#### Notes
- `language` is mandatory.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output. |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | Yes | Must be exactly `"block"` for VTZ policy denial records. |

#### Notes
- TRD requires: “VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.”
- No additional fields were specified in the provided source.

---

### TrustFlowEvent

Audit/event record emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | Must be globally unique. Must be generated with CSPRNG. Must not be sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the event. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | Must be SHA-256 of the serialized action payload. |

#### Notes
- Every TrustFlow event MUST include all fields above.
- Emission is synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and must not be silently skipped.

---

### CTXIDToken

CTX-ID token contract.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Must be validated first at every entry point that processes an agent action. |
| `expires_at` | `number \| string` | Not specified | Expired CTX-ID must be rejected. Clock skew tolerance is deployment-defined. |
| `vtz_id` | `string` | Not specified | Every agent session is bound to exactly one VTZ at CTX-ID issuance. |

#### Notes
Only the following properties are contractually defined from the source:
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- Old token is invalidated immediately.
- Validation must use TrustLock public key.
- Missing CTX-ID must be treated as `UNTRUSTED`.

Fields beyond `ctx_id` are not fully specified in the provided TRD text and must not be inferred as canonical.

---

### ActionPayload

Serialized action payload used for hashing and enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _opaque payload_ | serialized object | Yes | Serialized form must be hashable with SHA-256 to produce `payload_hash`. |

#### Notes
- Exact payload schema is not provided in the source.
- The only enforced interface requirement is that `payload_hash` equals SHA-256 of the serialized action payload.

---

## Enums and Constants

### Language

Exact allowed values for consensus engine calls:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Verdict

Exact known value from provided TRD:

- `"block"`

### CTX-ID Identity State

Exact known value from provided TRD:

- `UNTRUSTED`

### Logging / Audit Severity

Exact known value from provided TRD:

- `WARN`

### System Selectors

Exact constant names referenced by contract:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Forbidden Patterns

These are contractually forbidden and implementations are non-conformant if they appear.

#### Python
- `shell=True` in subprocess calls
- `eval()`
- `exec()`

#### Swift
- Force unwrap:
  ```swift
  let value = optional!
  ```
- LLM API call from Swift:
  ```swift
  let client = AnthropicClient(apiKey: keychainValue)
  ```
- Keychain read for backend:
  ```swift
  let token = KeychainKit.read("github_token")
  ```

#### Fix Arbitration
- Length-based fix arbitration is forbidden:
  ```python
  winner = max(claude_fix, openai_fix, key=len)
  ```

### Required Internal Strategy Functions

Exact function names referenced by contract:

- `_choose_strategy(failure_type, attempt, records)`
- `_score_fix()`

---

## Validation Rules

### 1. Entry-Point Enforcement

Every entry point that processes an agent action MUST:

1. Call CTX-ID validation first.
2. Immediately reject on CTX-ID validation failure.
3. Check action against VTZ policy before execution.
4. Emit a TrustFlow event for every outcome: allow, restrict, or block.
5. Not silently continue on TrustFlow emission failure.

### 2. Consensus Engine Request Validation

For every consensus engine invocation:

- `language` MUST be present.
- `language` MUST be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

Invalid `language` values are non-conformant.

### 3. Consensus Engine Routing Rules

- If `language == "swift"`, select `SWIFT_GENERATION_SYSTEM`.
- Optionally inject `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- If `language == "python"`, select `GENERATION_SYSTEM`.

### 4. Fix Loop / Arbitration Rules

- Fix loop strategy MUST be failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration MUST NOT be used.

### 5. TrustFlow Event Validation

A `TrustFlowEvent` is valid only if:

- `event_id` is present.
- `session_id` is present.
- `ctx_id` is present.
- `ts` is present and is a UTC Unix timestamp with millisecond precision.
- `event_type` is present.
- `payload_hash` is present and equals SHA-256 of the serialized action payload.

Additional rules:
- `event_id` must be globally unique.
- `event_id` must be CSPRNG-generated.
- `event_id` must not be sequential.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.

### 6. CTX-ID Validation Rules

- CTX-ID validation MUST happen first.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Expired CTX-ID MUST be rejected.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- Old token is invalidated immediately.

### 7. VTZ Enforcement Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

### 8. Security Validation Rules

Implementations MUST NOT:

- Hardcode credentials, API keys, tokens, or secrets as string literals.
- Use `shell=True` in subprocess calls.
- Call `eval()` or `exec()` on generated or external content.
- Log HTTP response bodies.

Implementations MUST:

- Log status codes and error types only for HTTP failures.
- Validate every file path written to disk with `path_security.validate_write_path()` before any write.
- Scan all loaded document chunks for injection before including them in any LLM prompt.
- Place context from external documents in the USER prompt, never the SYSTEM prompt.
- Stop, gate, and log on `SECURITY_REFUSAL`. Never retry to bypass.

### 9. Python Implementation Rules

- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout backend
- No blocking calls on event loop
- Dataclasses for all structured data
- Tests use `pytest`
- `ruff` must pass
- `mypy` must pass
- Coverage on new modules must be `>= 85%`
- `pyyaml` must be present in `requirements.txt`

---

## Wire Format Examples

## Valid Payloads

### Valid ConsensusRunRequest

```json
{
  "task": "Implement: Add audit event emission",
  "context": "Relevant component context here",
  "language": "python"
}
```

### Valid ConsensusRunRequest for Swift

```json
{
  "task": "Implement: Build Swift UI flow",
  "context": "UI component context here",
  "language": "swift"
}
```

### Valid ConsensusRunResult

```json
{
  "final_code": "print('hello')"
}
```

### Valid TrustFlowEvent

```json
{
  "event_id": "8f4d6b8e-9b2e-4d7b-a5b2-2f53e6d2c1a1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678.123,
  "event_type": "action.block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3edc1004b6fdef58"
}
```

### Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Valid Missing-CTX Handling Outcome

```json
{
  "ctx_id_state": "UNTRUSTED"
}
```

## Invalid Payloads

### Invalid ConsensusRunRequest: missing language

```json
{
  "task": "Implement: Feature X",
  "context": "Some context"
}
```

Reason:
- `language` is required.

### Invalid ConsensusRunRequest: unsupported language

```json
{
  "task": "Implement: Feature X",
  "context": "Some context",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `"python" | "swift" | "go" | "typescript" | "rust"`.

### Invalid TrustFlowEvent: missing required fields

```json
{
  "event_id": "123",
  "session_id": "sess_123"
}
```

Reason:
- Missing `ctx_id`, `ts`, `event_type`, and `payload_hash`.

### Invalid VTZEnforcementDecision: wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- Provided contract specifies `verdict=block` for VTZ policy denial.

### Invalid Security Behavior: external context in system prompt

```json
{
  "system_prompt": "External document content here"
}
```

Reason:
- Context from external documents must go in the USER prompt, never the SYSTEM prompt.

### Invalid Security Behavior: write without path validation

```json
{
  "path": "/tmp/output.txt",
  "validated": false
}
```

Reason:
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

---

## Integration Points

### Consensus Engine

Required call shape:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

#### Contract
- `language` must always be passed.
- Returned object must expose `final_code`.

---

### Enforcement Path

The enforcement path integrates:

1. CTX-ID validation
2. VTZ policy evaluation
3. `VTZEnforcementDecision` creation on denial
4. Synchronous TrustFlow emission

#### Ordering Contract
1. Validate CTX-ID first.
2. Reject immediately on failure.
3. Evaluate VTZ policy before execution.
4. Emit TrustFlow event for every outcome.

---

### TrustLock

CTX-ID validation must integrate with:

- TrustLock public key validation

#### Contract
- Software-only validation is rejected.

---

### Path Security

Before any disk write, integration must call:

- `path_security.validate_write_path()`

#### Contract
- Validation must occur before write.
- Skipping validation is non-conformant.

---

### Injection Scanning

Before including loaded document chunks in an LLM prompt:

- Perform injection scanning

#### Contract
- Every loaded document chunk must pass injection scanning.
- External document context must go in USER prompt only.

---

### Logging / Audit

#### Contract
- Do not log HTTP response bodies.
- Log status codes and error types only.
- TrustFlow emission failure must be logged and surfaced.
- Failed emission is a WARN-level audit event.

---

### Testing / Tooling

Required integration expectations:

- Test runner:
  ```bash
  cd src && pytest ../tests/ -v --tb=short
  ```
- Tests live in `tests/` and mirror `src/`
- `ruff` clean
- `mypy` clean
- Coverage `>= 85%` on new modules

---

## Source-Boundary Notes

This document includes only fields and constraints explicitly present in the provided TRD content. Where the source names a record but does not define a complete schema, only the explicitly stated fields and rules are treated as canonical.