# Interface Contracts - Crafted

## Data Structures

This subsystem inherits and MUST implement the Forge component interface contracts defined in the provided standards.

### TrustFlowEvent

Canonical audit/enforcement event emitted synchronously in the enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | MUST be globally unique; CSPRNG-generated; MUST NOT be sequential |
| `session_id` | string | yes | Session identifier |
| `ctx_id` | string | yes | Validated CTX-ID token identifier |
| `ts` | number | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Event type value; implementation-defined, but field is mandatory |
| `payload_hash` | string | yes | MUST be SHA-256 of the serialized action payload |

#### Behavioral constraints
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be treated as a WARN-level audit event.
- Failed emission MUST NOT be silently skipped.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### VTZEnforcementDecision

Record produced when VTZ policy is evaluated.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | For denial, MUST be exactly `block` |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### CTX-ID Token

Immutable trust context token used for session binding and validation.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | Token identifier; MUST be validated before any agent action is processed |

#### Behavioral constraints
- CTX-ID validation MUST be the FIRST operation on every entry point that processes an agent action.
- CTX-ID validation failure MUST result in immediate rejection with no partial processing.
- Tokens are IMMUTABLE once issued; no field modification after issuance.
- Rotation creates a new token; the old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from surrounding context when `ctx_id` is missing.

---

### Agent Action Payload

Serialized payload representing an action subject to CAL/VTZ enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _implementation-defined payload_ | object | yes | Serialized form MUST be hashable for `payload_hash` generation |

#### Behavioral constraints
- `payload_hash` MUST be computed as SHA-256 of the serialized action payload.
- The action MUST NOT be executed before CTX-ID validation and VTZ policy evaluation complete.

---

### Consensus Engine Invocation

Required invocation contract when using the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | string | yes | Free-form task description |
| `context` | string | yes | Context string |
| `language` | string | yes | MUST be one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"` |

#### Required call shape

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

#### Result contract

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | string | yes | Generated source output |

#### Behavioral constraints
- Always pass `language`.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

---

## Enums and Constants

### Language

Allowed values for consensus engine invocation:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Enforcement Verdict

Known required value from the contract:

- `block`

### Trust Outcome Values

Every action outcome MUST emit a TrustFlow event for:

- `allow`
- `restrict`
- `block`

### Special Status / Sentinel Values

- `UNTRUSTED` — required treatment for missing `CTX-ID`
- `SECURITY_REFUSAL` — if produced by the LLM, processing MUST stop, gate, and log; retry to bypass is forbidden

### Named Systems

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Python Version

- `Python 3.12`

---

## Validation Rules

### Entry Point Enforcement Order

For every entry point that processes an agent action, the following order is mandatory:

1. Call CTX-ID validation FIRST.
2. On CTX-ID validation failure, immediately reject.
3. Evaluate VTZ policy BEFORE execution.
4. If denied, produce `VTZEnforcementDecision` with `verdict=block`.
5. Emit TrustFlow event synchronously for the outcome.
6. If TrustFlow emission fails, log and surface the failure; do not silently continue.

### CTX-ID Validation

- `ctx_id` is required for trusted processing.
- Missing `ctx_id` MUST be treated as `UNTRUSTED`.
- Expired CTX-ID MUST be rejected.
- CTX-ID validation MUST use TrustLock public key.
- Software-only validation is rejected.
- CTX-ID tokens are immutable after issuance.
- Rotation invalidates the previous token immediately.

### VTZ Validation

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

### TrustFlow Validation

- `event_id` MUST be globally unique.
- `event_id` MUST be generated by CSPRNG.
- `event_id` MUST NOT be sequential.
- `ts` MUST be a UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.

### Security Validation

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies; log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log; never retry to bypass.

### Python Implementation Validation

- Python must be `3.12`.
- Type annotations are required on every function.
- Backend must use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses are required for all structured data.
- Tests must use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass.
- `mypy` must pass.
- Test coverage on new modules MUST be `>= 85%`.
- `pyyaml` MUST be present in `requirements.txt`.

### Forbidden Patterns

#### Fix arbitration
```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

- Length-based fix arbitration is forbidden.
- Fix arbitration MUST use `_score_fix()`.
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.

#### Swift/backend forbidden patterns
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
- LLM API calls from Swift are forbidden.
- Backend credential reads from Keychain are forbidden.
- Only Swift reads Keychain, and only to deliver via XPC.

---

## Wire Format Examples

## Valid payloads

### Valid TrustFlowEvent

```json
{
  "event_id": "9f6c1c7f-5d5e-4d61-bf7a-8d5a8e5b6f21",
  "session_id": "sess_01JABCDEF123456789",
  "ctx_id": "ctx_01JABCDEFGH987654321",
  "ts": 1735689600123,
  "event_type": "action.block",
  "payload_hash": "5f70bf18a086007016e948b04aed3b82103a36beA41755BfEbbE2a2fE5aE4f3".lower()
}
```

Note: `payload_hash` is semantically required to be a SHA-256 hex digest of the serialized action payload.

### Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Valid consensus invocation

```json
{
  "task": "Implement: Crafted subsystem contract",
  "context": "Relevant TRD sections and enforcement requirements",
  "language": "python"
}
```

### Valid minimal trusted action envelope

```json
{
  "session_id": "sess_01JABCDEF123456789",
  "ctx_id": "ctx_01JABCDEFGH987654321",
  "payload": {
    "action": "run"
  }
}
```

## Invalid payloads

### Invalid TrustFlowEvent: sequential event_id

```json
{
  "event_id": "1001",
  "session_id": "sess_01JABCDEF123456789",
  "ctx_id": "ctx_01JABCDEFGH987654321",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "abc123"
}
```

Invalid because:
- `event_id` is sequential
- `payload_hash` is not a valid SHA-256 digest

### Invalid action processing: missing ctx_id treated as trusted

```json
{
  "session_id": "sess_01JABCDEF123456789",
  "payload": {
    "action": "run"
  }
}
```

Invalid because:
- missing `ctx_id` MUST be treated as `UNTRUSTED`
- trusted processing MUST NOT proceed by inferring identity from context

### Invalid consensus invocation: missing language

```json
{
  "task": "Implement: Crafted subsystem contract",
  "context": "Relevant TRD sections"
}
```

Invalid because:
- `language` is mandatory

### Invalid consensus invocation: unsupported language

```json
{
  "task": "Implement: Crafted subsystem contract",
  "context": "Relevant TRD sections",
  "language": "java"
}
```

Invalid because:
- `language` MUST be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`

### Invalid security handling

```json
{
  "llm_output": "SECURITY_REFUSAL",
  "action": "retry"
}
```

Invalid because:
- on `SECURITY_REFUSAL`, the system MUST stop, gate, and log
- retry to bypass is forbidden

---

## Integration Points

### CAL Enforcement

Every Crafted entry point that processes an agent action MUST integrate:

1. CTX-ID validation
2. VTZ policy enforcement
3. TrustFlow synchronous emission

Required outcomes:
- CTX-ID validation failure: immediate rejection
- VTZ denial: emit `VTZEnforcementDecision` with `verdict=block`
- Any action outcome: emit TrustFlow event
- TrustFlow emission failure: WARN-level audit event and surfaced failure

### TrustLock

CTX-ID validation MUST integrate with:
- TrustLock public key validation

Software-only validation is explicitly non-conformant.

### Consensus Engine

When Crafted invokes the consensus engine, it MUST call:

```python
await self._consensus.run(task=..., context=..., language=...)
```

Required integration behavior:
- always pass `language`
- use `result.final_code`
- do not use length-based fix arbitration
- use `_score_fix()`
- fix loop strategy uses `_choose_strategy(failure_type, attempt, records)`

### Path Security

Before any file write, Crafted MUST call:

- `path_security.validate_write_path()`

### Injection Scanning

Before any loaded document chunk is included in an LLM prompt, Crafted MUST ensure:
- injection scanning has passed

### Prompt Placement

For external document context:
- USER prompt only
- never SYSTEM prompt

### Testing and Tooling

Crafted implementations MUST integrate with:
- `pytest`
- `ruff`
- `mypy`

Required command before changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```

### Swift/XPC Boundary

If Swift participates:
- Swift may read Keychain only to deliver credentials via XPC
- Swift must not directly call LLM APIs
- Backend Python must not read from Keychain

### Conformance Summary

A Crafted component is non-conformant if any of the following are violated:

- missing CTX-ID-first validation
- partial processing after CTX-ID validation failure
- VTZ check occurs after execution
- missing `VTZEnforcementDecision` on denial
- missing TrustFlow event for any outcome
- silent TrustFlow emission failure
- non-unique or sequential `event_id`
- non-millisecond Unix `ts`
- non-SHA-256 `payload_hash`
- missing `language` in consensus invocation
- forbidden `_score_fix()` replacement by response length
- any forbidden security pattern
- any bypass of TrustLock, VTZ, or prompt-placement rules