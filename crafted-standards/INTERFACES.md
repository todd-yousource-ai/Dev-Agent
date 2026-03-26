# Interface Contracts - CraftedApp

## Data Structures

This section defines the required wire-level and API-visible structures for the CraftedApp subsystem based on the provided TRD excerpts.

### ConsensusRunRequest

Request contract for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Free-text task description. Example source value: `"Implement: {spec.title}"` |
| `context` | `string` | yes | Context string passed to consensus engine |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | yes | Must always be passed |

#### Source usage
```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
```

---

### ConsensusRunResult

Result contract returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Final generated code output |

#### Source usage
```python
code = result.final_code
```

---

### TrustFlowEvent

Required event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique; CSPRNG-generated; MUST NOT be sequential |
| `session_id` | `string` | yes | Session identifier |
| `ctx_id` | `string` | yes | CTX-ID associated with the action |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Event type identifier |
| `payload_hash` | `string` | yes | MUST be SHA-256 of the serialized action payload |

---

### VTZEnforcementDecision

Record required when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | yes | MUST be exactly `block` for VTZ policy denial |

No additional fields are defined in the provided TRD excerpts.

---

### CTX-ID Token

Opaque token contract with validation and lifecycle requirements.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Immutable once issued; validated against TrustLock public key; missing value MUST be treated as `UNTRUSTED` |

No internal token fields are defined in the provided TRD excerpts. Only external contract requirements are normative.

---

### Agent Action Payload

Serialized action payload referenced by enforcement and hashing rules.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `payload` | `object` | yes | Serialized form MUST be hashable via SHA-256 for `payload_hash` generation |

No schema for the internal payload object is defined in the provided TRD excerpts.

---

## Enums and Constants

### Language

Exact allowed values for consensus engine invocation:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

### Verdict

Defined value from VTZ enforcement contract:

- `block`

### Trust Status / Identity Handling Constants

Defined semantic value:

- `UNTRUSTED`

### System Selector Constants

Exact source constants referenced by language selection behavior:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Security Refusal Sentinel

Exact output string referenced by security handling:

- `SECURITY_REFUSAL`

### Logging Severity Constant

Exact severity referenced for failed TrustFlow emission:

- `WARN`

---

## Validation Rules

## Crafted Component Interface Contracts

Every Crafted component MUST implement these contracts or the component is non-conformant.

### CAL Enforcement Contract

- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection — no partial processing.
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

### TrustFlow Emission Contract

- Every TrustFlow event MUST include:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- `event_id` MUST be globally unique (CSPRNG, not sequential).
- `ts` MUST be UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path — async buffering is not permitted.
- Failed emission is a `WARN`-level audit event, not a silent skip.

### CTX-ID Contract

- CTX-ID tokens are IMMUTABLE once issued — no field modification after issuance.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected — clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against TrustLock public key — software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED` — never infer identity from context.

### VTZ Enforcement Contract

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization — implicit is denied.
- VTZ boundaries are structural, not advisory — enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

### Consensus Engine Usage Rules

- Always pass `language`.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.
- Fix loop strategy is selected via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration uses `_score_fix()` based on assertion token overlap.
- Length-based fix arbitration is forbidden.

### Forbidden Patterns

These are non-conformant and MUST NOT appear in implementations:

#### Python / backend / security
- Hardcoded credentials, API keys, tokens, or secrets as string literals
- `shell=True` in subprocess calls
- `eval()`
- `exec()`
- Logging HTTP response bodies
- Writing any file path before `path_security.validate_write_path()`
- Including loaded document chunks in any LLM prompt before injection scanning
- Putting external document context in the SYSTEM prompt
- Retrying to bypass `SECURITY_REFUSAL`

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

### Python Backend Requirements

- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- `pytest` for all tests
- Tests live in `tests/` and mirror `src/` structure
- `ruff` for linting
- `mypy` for type checking
- Coverage requirement: `>= 85%` on all new modules
- `pyyaml` must be present in `requirements.txt`

---

## Wire Format Examples

## Valid Payloads

### Valid `ConsensusRunRequest`
```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context",
  "language": "python"
}
```

### Valid `ConsensusRunRequest` for Swift
```json
{
  "task": "Implement: ExampleSwiftUIFeature",
  "context": "UI-related context",
  "language": "swift"
}
```

### Valid `TrustFlowEvent`
```json
{
  "event_id": "3f8c0b7b-4c47-4f7d-bf39-2efcb3e2a6a1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678123,
  "event_type": "block",
  "payload_hash": "5f70bf18a086007016e948b04aed3b82103a36be-a-placeholder-example"
}
```

Note: `payload_hash` value format above is illustrative only; actual value MUST be a SHA-256 of the serialized action payload.

### Valid `VTZEnforcementDecision`
```json
{
  "verdict": "block"
}
```

---

## Invalid Payloads

### Invalid `ConsensusRunRequest` - missing `language`
```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context"
}
```

Reason: `language` is mandatory.

### Invalid `ConsensusRunRequest` - unsupported `language`
```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant implementation context",
  "language": "java"
}
```

Reason: `language` MUST be one of:
`python`, `swift`, `go`, `typescript`, `rust`.

### Invalid `TrustFlowEvent` - missing required fields
```json
{
  "event_id": "evt_1",
  "ctx_id": "ctx_abc",
  "event_type": "allow"
}
```

Reason: Missing `session_id`, `ts`, and `payload_hash`.

### Invalid `VTZEnforcementDecision` - wrong verdict
```json
{
  "verdict": "allow"
}
```

Reason: For VTZ policy denial, `verdict` MUST be exactly `block`.

### Invalid CTX-ID handling
```json
{
  "ctx_id": null
}
```

Reason: Missing CTX-ID MUST be treated as `UNTRUSTED` and rejected where validation is required.

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

Behavioral integration rules:

- `language` is mandatory.
- `swift` selects `SWIFT_GENERATION_SYSTEM` and optionally `SWIFT_UI_ADDENDUM`.
- `python` selects `GENERATION_SYSTEM`.

### Enforcement Pipeline

Required processing order for every agent action entry point:

1. CTX-ID validation
2. Immediate rejection on CTX-ID validation failure
3. VTZ policy check
4. Action execution only if permitted
5. TrustFlow event emission for every outcome
6. Log and surface TrustFlow emission failure

### TrustLock

CTX-ID validation integration:

- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

### Path Security

Any disk write integration:

- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

### Prompt Construction / LLM Safety

- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log; never retry to bypass.

### Testing and Tooling

Required project integrations:

- Test command:
```bash
cd src && pytest ../tests/ -v --tb=short
```

- Linting: `ruff`
- Type checking: `mypy`
- Testing: `pytest`

## Undefined by Provided TRD Excerpts

The following are referenced conceptually but not structurally defined in the provided source excerpts, so no additional fields may be inferred for them in a conformant implementation:

- Internal CTX-ID token fields
- Full agent action payload schema
- TrustFlow `event_type` enum values
- Full `VTZEnforcementDecision` schema beyond `verdict=block`
- TrustLock public key transport format
- Session identifier format
- Error object schema and status code mappings