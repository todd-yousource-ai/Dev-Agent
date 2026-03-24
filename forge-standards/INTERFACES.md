# Interface Contracts - ForgeAgent

This document defines the wire format and API contract for the ForgeAgent subsystem based on the provided TRD interface standards.

## Data Structures

All structured backend data MUST use dataclasses.

### ConsensusRunRequest

Request passed to the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | Free-text task description. Example source usage: `"Implement: {spec.title}"` |
| `context` | `str` | Yes | Context string supplied to consensus engine |
| `language` | `str` | Yes | MUST be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Required call shape

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
```

#### Behavioral constraints

- `language` MUST always be passed.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Result returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Generated code output |

---

### VTZEnforcementDecision

Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `str` | Yes | MUST be exactly `"block"` when produced for VTZ denial |

#### Behavioral constraints

- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent

Event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | Yes | MUST be globally unique; generated via CSPRNG; MUST NOT be sequential |
| `session_id` | `str` | Yes | Session identifier |
| `ctx_id` | `str` | Yes | CTX-ID token or token identifier associated with the session |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `str` | Yes | Event type identifier |
| `payload_hash` | `str` | Yes | MUST be SHA-256 of the serialized action payload |

#### Behavioral constraints

- Every TrustFlow event MUST include all fields above.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and MUST NOT be silently skipped.

---

### AgentActionPayload

Serialized action payload used for hashing and enforcement processing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | Yes | MUST be validated first on every entry point that processes an agent action |
| `session_id` | `str` | Yes | Session identifier bound to the action |
| `action` | `object` | Yes | Action content; serialization output is the input to `payload_hash` SHA-256 computation |

#### Behavioral constraints

- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted before successful CTX-ID validation.
- Every action MUST be checked against VTZ policy BEFORE execution.

---

### CTXIDToken

CTX-ID token contract.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | Yes | Immutable once issued |
| `vtz_id` | `str` | Yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance |
| `issued_at` | `number` | Yes | Timestamp |
| `expires_at` | `number` | Yes | Expired CTX-ID MUST be rejected |
| `public_key_id` | `str` | Yes | Validation MUST be against TrustLock public key |

#### Behavioral constraints

- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- Old token is invalidated immediately upon rotation.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from context when CTX-ID is missing.
- Validation against software-only mechanisms is rejected; validation MUST use TrustLock public key.
- Clock skew tolerance is deployment-defined and not specified in this interface.

---

### InjectionScannedDocumentChunk

Loaded external document content eligible for prompt inclusion.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `content` | `str` | Yes | Raw chunk text |
| `injection_scanned` | `bool` | Yes | MUST be `true` before inclusion in any LLM prompt |
| `prompt_role` | `str` | Yes | External document context MUST go in the USER prompt, never the SYSTEM prompt |

#### Behavioral constraints

- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST be placed in the USER prompt only.

---

### SecurityRefusalRecord

Represents handling of `SECURITY_REFUSAL` output from an LLM.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `output` | `str` | Yes | MUST be exactly `SECURITY_REFUSAL` when this record is used |
| `stopped` | `bool` | Yes | MUST be `true` |
| `gated` | `bool` | Yes | MUST be `true` |
| `logged` | `bool` | Yes | MUST be `true` |

#### Behavioral constraints

- When `SECURITY_REFUSAL` is returned from the LLM: stop, gate, log.
- Never retry to bypass.

---

### WritePathRequest

Represents a file write operation.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `path` | `str` | Yes | MUST pass `path_security.validate_write_path()` before any write |
| `content` | `str` | Yes | File content to write |

---

## Enums and Constants

### Language

Allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Verdict

Allowed required value from provided contract:

- `"block"`

### Trust Classification

Required missing CTX-ID handling value:

- `UNTRUSTED`

### Reserved LLM Output

- `SECURITY_REFUSAL`

### Generation System Constants

These names are contract-significant:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Tooling / Runtime Constants

These are required environment/tooling constraints for ForgeAgent backend implementation:

- Python version: `3.12`
- Test runner: `pytest`
- Linter: `ruff`
- Type checker: `mypy`
- YAML dependency: `pyyaml`

---

## Validation Rules

### General Backend Rules

- Python backend code MUST use `async/await` throughout.
- No blocking calls on the event loop.
- Type annotations are required on every function.
- Structured data MUST use dataclasses.

### Entry Point Enforcement Order

For every entry point that processes an agent action:

1. Validate `ctx_id` FIRST.
2. If CTX-ID validation fails, reject immediately.
3. Do not partially process the action.
4. Check VTZ policy BEFORE execution.
5. If denied, produce `VTZEnforcementDecision` with `verdict="block"`.
6. Emit a TrustFlow event for every outcome: allow, restrict, or block.
7. If TrustFlow emission fails, log and surface the failure.

### TrustFlow Validation

A valid TrustFlow event MUST satisfy all of:

- `event_id` is globally unique.
- `event_id` is generated by CSPRNG.
- `event_id` is not sequential.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `payload_hash` is SHA-256 of the serialized action payload.
- Emission is synchronous in the enforcement path.

### CTX-ID Validation

A valid CTX-ID flow MUST satisfy all of:

- Token is present, otherwise treat as `UNTRUSTED`.
- Token is not expired.
- Token is validated against TrustLock public key.
- Token fields are not modified after issuance.
- Rotation creates a new token and invalidates the old token immediately.

### VTZ Validation

- Every agent session MUST be bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- Policy changes take effect at NEXT CTX-ID issuance, not mid-session.

### Security Validation

The following are prohibited:

- Hardcoded credentials, API keys, tokens, or secrets as string literals
- `shell=True` in subprocess calls
- `eval()` on generated or external content
- `exec()` on generated or external content
- Logging HTTP response bodies
- Force unwrap in Swift: `optional!`
- LLM API call from Swift
- Keychain reads for backend logic in Python

The following are required:

- Log HTTP status codes and error types only
- All file paths written to disk MUST pass `path_security.validate_write_path()` before write
- All loaded document chunks MUST pass injection scanning before inclusion in prompts
- External document context goes in USER prompt, never SYSTEM prompt

### Fix Loop Validation

- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration is forbidden.

Forbidden example:

```python
winner = max(claude_fix, openai_fix, key=len)
```

---

## Wire Format Examples

## Valid Payloads

### Valid consensus run request

```json
{
  "task": "Implement: Add auth middleware",
  "context": "Project context and constraints",
  "language": "python"
}
```

### Valid TrustFlow event

```json
{
  "event_id": "9f4f6b49-4e9d-4e2d-9b6d-6f7d4a4f9b11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678123,
  "event_type": "action_blocked",
  "payload_hash": "2d711642b726b04401627ca9fbac32f5da7e5f6a8d5c7e6f3b1a6e3a5f4c2d1b"
}
```

### Valid VTZ denial decision

```json
{
  "verdict": "block"
}
```

### Valid SECURITY_REFUSAL handling record

```json
{
  "output": "SECURITY_REFUSAL",
  "stopped": true,
  "gated": true,
  "logged": true
}
```

### Valid write path request

```json
{
  "path": "/safe/output/file.py",
  "content": "print('ok')"
}
```

## Invalid Payloads

### Invalid consensus run request: missing language

```json
{
  "task": "Implement: Add auth middleware",
  "context": "Project context and constraints"
}
```

Reason: `language` is required and MUST always be passed.

---

### Invalid consensus run request: unsupported language

```json
{
  "task": "Implement: Add auth middleware",
  "context": "Project context and constraints",
  "language": "java"
}
```

Reason: `language` MUST be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

---

### Invalid VTZ decision

```json
{
  "verdict": "allow"
}
```

Reason: for VTZ denial record, `verdict` MUST be exactly `"block"`.

---

### Invalid TrustFlow event: missing required field

```json
{
  "event_id": "9f4f6b49-4e9d-4e2d-9b6d-6f7d4a4f9b11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678123,
  "event_type": "action_blocked"
}
```

Reason: `payload_hash` is required.

---

### Invalid document chunk prompt role

```json
{
  "content": "external content",
  "injection_scanned": true,
  "prompt_role": "system"
}
```

Reason: external document context MUST go in the USER prompt, never the SYSTEM prompt.

---

### Invalid SECURITY_REFUSAL handling

```json
{
  "output": "SECURITY_REFUSAL",
  "stopped": false,
  "gated": false,
  "logged": false
}
```

Reason: must stop, gate, and log.

---

## Integration Points

### Consensus Engine

ForgeAgent MUST call the consensus engine with:

- `task`
- `context`
- `language`

Contracted invocation:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

### Enforcement Path

ForgeAgent entry points that process actions MUST integrate:

1. CTX-ID validation
2. VTZ policy enforcement
3. TrustFlow event emission

### TrustLock

CTX-ID validation MUST be performed against TrustLock public key.
Software-only validation is non-conformant.

### Path Security

All disk writes MUST validate path through:

```python
path_security.validate_write_path()
```

before any write occurs.

### Prompt Construction / LLM Integration

- External document chunks MUST be injection-scanned before inclusion.
- External document context MUST be placed in USER prompt.
- `SECURITY_REFUSAL` MUST terminate processing with gate-and-log behavior.

### Swift Boundary

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` and optional `SWIFT_UI_ADDENDUM`.
- Swift code MUST NOT make LLM API calls directly.
- Only Swift reads Keychain, and only to deliver via XPC.
- Python reads nothing from Keychain.

### Testing and Conformance

Required commands/process constraints from TRD:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Required standards:

- tests in `tests/`, mirroring `src/`
- `pytest` required
- `ruff` must pass clean
- `mypy` must pass clean
- coverage on new modules must be `>= 85%`
- `pyyaml` must be present in `requirements.txt`