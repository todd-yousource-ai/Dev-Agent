# Interface Contracts - Crafted

This document defines the wire-format and API contract reference for the Crafted subsystem, derived from the provided TRD interface standards.

## Data Structures

The Crafted subsystem MUST implement and honor the following interface contracts.

### TrustFlowEvent

Represents the required synchronous audit/emission record for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique. MUST be generated via CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | yes | Session identifier for the agent session. |
| `ctx_id` | `string` | yes | Immutable CTX-ID token bound to the session. |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | yes | Event type for the action outcome. |
| `payload_hash` | `string` | yes | MUST be SHA-256 of the serialized action payload. |

#### Semantic requirements
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a `TrustFlowEvent`.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Emission failure MUST NOT silently continue.
- Failed emission is a WARN-level audit event.

---

### VTZEnforcementDecision

Represents the enforcement result when an action is checked against VTZ policy.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | On VTZ policy denial, MUST be exactly `block`. |

#### Semantic requirements
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### CTX-ID Token

Represents the identity/binding token used for agent action processing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | MUST be validated first at every entry point that processes an agent action. MUST be immutable once issued. |

#### Semantic requirements
- CTX-ID validation MUST happen FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted after validation failure.
- Missing `ctx_id` MUST be treated as `UNTRUSTED`.
- Expired `ctx_id` MUST be rejected.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Identity MUST never be inferred from context when `ctx_id` is missing.

---

### AgentActionPayload

Serialized action payload used for enforcement and hashing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _serialized payload_ | `object` \| `bytes` \| `string` | yes | Exact application payload is implementation-defined, but `payload_hash` MUST be computed as SHA-256 of the serialized action payload. |

#### Semantic requirements
- Every action processed by the subsystem MUST have a serialized payload representation.
- The serialized form used for `payload_hash` MUST be stable for hashing purposes within the implementation.

---

### ConsensusRunRequest

Required invocation contract when the Crafted subsystem uses the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Example contract usage: `f"Implement: {spec.title}"` |
| `context` | `string` | yes | Context string passed to the consensus engine. |
| `language` | `string` | yes | MUST always be passed. Allowed values: `"python"` \| `"swift"` \| `"go"` \| `"typescript"` \| `"rust"` |

#### Semantic requirements
- Calls to the consensus engine MUST always pass `language`.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### ConsensusRunResult

Output contract required from consensus execution.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Generated final code output. |

---

### SecurityRefusalSignal

Represents refusal output from the LLM security gate.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `output` | `string` | yes | When value is exactly `SECURITY_REFUSAL`, processing MUST stop. |

#### Semantic requirements
- On `SECURITY_REFUSAL`: stop, gate, log.
- MUST NOT retry to bypass.

---

## Enums and Constants

### Language

Allowed values for consensus engine `language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### VTZ Verdict

Known required value from the TRD:

- `block`

### Action Outcomes

Every action outcome MUST emit a TrustFlow event for one of:

- `allow`
- `restrict`
- `block`

### Security Refusal Output

Exact value:

- `SECURITY_REFUSAL`

### Generation System Constants

Exact values referenced by contract:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Python Runtime / Tooling Constants

Exact values required by contract:

- Python version: `3.12`
- Test framework: `pytest`
- Linter: `ruff`
- Type checker: `mypy`
- YAML package requirement: `pyyaml`

---

## Validation Rules

### Entry Point Enforcement

For every entry point that processes an agent action:

1. MUST call CTX-ID validation FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. MUST NOT perform partial processing before successful CTX-ID validation.
4. MUST check the action against VTZ policy BEFORE execution.
5. MUST emit a TrustFlow event for every outcome.
6. TrustFlow emission failure MUST be logged and surfaced.
7. MUST NOT silently continue on emission failure.

---

### CTX-ID Validation

- `ctx_id` MUST be present, otherwise treat as `UNTRUSTED`.
- `ctx_id` MUST be immutable once issued.
- Rotating a CTX-ID MUST create a new token.
- The old token MUST be invalidated immediately.
- Expired tokens MUST be rejected.
- Validation MUST be against TrustLock public key.
- Software-only validation is rejected.
- Clock skew tolerance is deployment-defined and not specified in this contract.

---

### VTZ Enforcement

- Every agent session MUST be bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

### TrustFlow Emission

A valid TrustFlow emission MUST satisfy all of:

- `event_id` is globally unique.
- `event_id` is CSPRNG-generated.
- `event_id` is not sequential.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `payload_hash` is SHA-256 of the serialized action payload.
- Emission occurs synchronously in the enforcement path.
- Async buffering is not permitted.

---

### Consensus Engine Usage

A valid consensus run request MUST satisfy all of:

- `language` is present.
- `language` is one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

Additional behavioral rules:

- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Length-based fix arbitration is forbidden.

#### Forbidden example
```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

---

### Security Rules

The Crafted subsystem MUST enforce the following:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on any generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before being included in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log. Never retry to bypass.

---

### Swift-specific Forbidden Patterns

These are explicitly non-conformant:

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
- Force unwrap is forbidden.
- LLM API call from Swift is forbidden.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

---

### Python-specific Requirements

- Python version MUST be `3.12`.
- All functions MUST have type annotations.
- Backend code MUST use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses MUST be used for all structured data.
- Tests MUST use `pytest`.
- Tests MUST live in `tests/` and mirror `src/` structure.
- `ruff` MUST pass clean.
- `mypy` MUST pass clean.
- Test coverage MUST be `≥ 85%` on all new modules.
- `pyyaml` MUST be in `requirements.txt`.

---

## Wire Format Examples

## Valid payloads

### Valid TrustFlowEvent

```json
{
  "event_id": "5a9c0d8f-6c6d-4c2d-9d89-6d9ce5ef2d11",
  "session_id": "sess_01HV7Z3A8Q8P2K9M4J6N",
  "ctx_id": "ctx_01HV7Z5TW3R4A1Y9P8LK",
  "ts": 1716412345123,
  "event_type": "block",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961cbe6a2c93f6ae9b9d1b444"
}
```

Why valid:
- Contains all required fields.
- `ts` is millisecond Unix time.
- `payload_hash` is a SHA-256 hex string representation.
- `event_type` is an action outcome value.

---

### Valid VTZEnforcementDecision on denial

```json
{
  "verdict": "block"
}
```

Why valid:
- On denial, `verdict` MUST be exactly `block`.

---

### Valid ConsensusRunRequest

```json
{
  "task": "Implement: Crafted subsystem contract",
  "context": "Relevant TRD context here",
  "language": "python"
}
```

Why valid:
- Includes required `language`.
- `language` is one of the allowed values.

---

### Valid SecurityRefusalSignal

```json
{
  "output": "SECURITY_REFUSAL"
}
```

Why valid:
- Exact refusal sentinel value is preserved.

---

## Invalid payloads

### Invalid TrustFlowEvent: missing required field

```json
{
  "event_id": "5a9c0d8f-6c6d-4c2d-9d89-6d9ce5ef2d11",
  "session_id": "sess_01HV7Z3A8Q8P2K9M4J6N",
  "ts": 1716412345123,
  "event_type": "allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961cbe6a2c93f6ae9b9d1b444"
}
```

Why invalid:
- Missing `ctx_id`.

---

### Invalid VTZEnforcementDecision: wrong denial verdict

```json
{
  "verdict": "deny"
}
```

Why invalid:
- TRD requires denial record with `verdict=block`.

---

### Invalid ConsensusRunRequest: missing language

```json
{
  "task": "Implement: Crafted subsystem contract",
  "context": "Relevant TRD context here"
}
```

Why invalid:
- `language` is mandatory.

---

### Invalid ConsensusRunRequest: unsupported language

```json
{
  "task": "Implement: Crafted subsystem contract",
  "context": "Relevant TRD context here",
  "language": "java"
}
```

Why invalid:
- `language` MUST be one of `"python" | "swift" | "go" | "typescript" | "rust"`.

---

### Invalid SecurityRefusal handling

```json
{
  "output": "SECURITY_REFUSAL",
  "action": "retry"
}
```

Why invalid:
- On `SECURITY_REFUSAL`, retrying to bypass is forbidden.

---

## Integration Points

### Agent Action Entry Points

Any Crafted subsystem entry point that processes an agent action MUST integrate the following sequence:

1. Validate `ctx_id` FIRST.
2. Reject immediately on CTX-ID validation failure.
3. Evaluate VTZ policy BEFORE execution.
4. On VTZ denial, produce `VTZEnforcementDecision` with:
   - `verdict: "block"`
5. Emit `TrustFlowEvent` synchronously for the outcome.
6. Log and surface TrustFlow emission failure.

---

### Consensus Engine

Required invocation pattern:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Integration requirements:
- `language` MUST always be supplied.
- `result.final_code` is the expected output field.
- Swift generation path selects `SWIFT_GENERATION_SYSTEM` and optional `SWIFT_UI_ADDENDUM`.
- Python generation path selects `GENERATION_SYSTEM`.

---

### File Write Security

Before any disk write:
- The destination path MUST pass `path_security.validate_write_path()`.

---

### LLM Prompt Construction

When including external document content:
- Every loaded document chunk MUST pass injection scanning first.
- External document context MUST go in the USER prompt.
- External document context MUST NEVER go in the SYSTEM prompt.

---

### Testing and Conformance

Before implementation changes:
- Find the TRD that owns the component in `README.md`.
- Read relevant TRD sections, especially interfaces, error contracts, security, testing requirements.
- Check TRD-11 if the change touches credentials, external content, generated code, or CI.
- Run existing tests with:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Conformance requirements:
- `pytest`, `ruff`, and `mypy` must pass.
- Coverage on new modules must be at least `85%`.