# Interface Contracts - CraftedAgent

## Data Structures

### Consensus Engine Invocation

All CraftedAgent implementations that invoke the consensus engine MUST pass the following arguments exactly as shown.

#### Call Shape

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

#### Parameters

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `str` | Yes | MUST be provided. Example format shown as `f"Implement: {spec.title}"`. |
| `context` | `str` | Yes | MUST be provided as prompt context. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | MUST always be passed. |

#### Result Object

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `str` | Yes | Generated code output consumed by caller. |

---

### VTZEnforcementDecision

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `str` | Yes | On VTZ denial, MUST equal `block`. |

No additional fields are defined in the provided TRD content.

---

### TrustFlow Event

Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `str` | Yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | `str` | Yes | MUST be present on every TrustFlow event. |
| `ctx_id` | `str` | Yes | MUST be present on every TrustFlow event. |
| `ts` | `number` | Yes | MUST be a UTC Unix timestamp with millisecond precision. |
| `event_type` | `str` | Yes | MUST be present on every TrustFlow event. |
| `payload_hash` | `str` | Yes | MUST be SHA-256 of the serialized action payload. |

No additional fields are defined in the provided TRD content.

---

### CTX-ID Token

CTX-ID is a validated token used before any agent action processing.

Defined contract properties:

| Property | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `str` | Yes | Missing CTX-ID MUST be treated as `UNTRUSTED`. |
| token immutability | semantic rule | Yes | CTX-ID tokens are IMMUTABLE once issued. No field modification after issuance. |
| token rotation | semantic rule | Yes | Rotation creates a new token; the old one is invalidated immediately. |
| expiration | semantic rule | Yes | Expired CTX-ID MUST be rejected. Clock skew tolerance is deployment-defined. |
| public key validation | semantic rule | Yes | MUST be validated against TrustLock public key. Software-only validation is rejected. |

The internal serialized field layout of the CTX-ID token is not defined in the provided TRD content.

---

### Agent Session

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `str` | Yes | Used in TrustFlow event emission. |
| bound VTZ | semantic rule | Yes | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance. |

No additional session fields are defined in the provided TRD content.

---

### Action Payload

The serialized action payload is an input to TrustFlow hashing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| serialized action payload | bytes/string serialization | Yes | `payload_hash` MUST be SHA-256 of this serialized payload. |

The action payload schema itself is not defined in the provided TRD content.

---

## Enums and Constants

### Language Enum

Exact allowed values for consensus invocation:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### VTZ Verdict Enum

Defined value in provided TRD content:

- `block`

Referenced action outcomes that MUST emit TrustFlow events:

- `allow`
- `restrict`
- `block`

### Special Status Values

- `UNTRUSTED` — applied when CTX-ID is missing.
- `SECURITY_REFUSAL` — when seen from the LLM, processing MUST stop, gate, and log.

### Consensus System Selection Constants

These names are part of the contract behavior:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Fix Strategy / Arbitration API Symbols

These names are contractually referenced:

- `_choose_strategy(failure_type, attempt, records)`
- `_score_fix()`

### Forbidden Pattern Marker

The following is explicitly forbidden and non-conformant:

```python
winner = max(claude_fix, openai_fix, key=len)
```

---

## Validation Rules

## Entry Point Enforcement Order

Every entry point that processes an agent action MUST enforce the following order:

1. CTX-ID validation FIRST.
2. On CTX-ID validation failure: immediate rejection.
3. VTZ policy check BEFORE execution.
4. On VTZ policy denial: produce `VTZEnforcementDecision` with `verdict=block`.
5. Emit a TrustFlow event for every action outcome.
6. TrustFlow emission failure MUST NOT silently continue.

## TrustFlow Validation Rules

- Every TrustFlow event MUST include all of:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- `event_id` MUST be globally unique.
- `event_id` MUST use CSPRNG.
- `event_id` MUST NOT be sequential.
- `ts` MUST be UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission MUST NOT be silently skipped.
- Failed emission MUST be logged and surfaced.

## CTX-ID Validation Rules

- CTX-ID validation MUST occur before any action processing.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Expired CTX-ID MUST be rejected.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- CTX-ID tokens are immutable once issued.
- Rotation MUST create a new token.
- Rotation MUST invalidate the old token immediately.
- Identity MUST NEVER be inferred from surrounding context when CTX-ID is missing.

## VTZ Validation Rules

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Every action MUST be checked against VTZ policy before execution.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance.
- VTZ policy changes do not apply mid-session.

## Consensus Engine Rules

- `language` MUST always be passed to `self._consensus.run(...)`.
- Valid `language` values are exactly:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration MUST NOT be used.

## Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` output is seen from the LLM: stop, gate, log. Never retry to bypass.

## Python Implementation Rules

- Python version: `3.12`.
- Type annotations on every function.
- `async/await` throughout the backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- `pytest` for all tests.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be `>= 85%` on all new modules.
- `pyyaml` MUST be present in `requirements.txt`.

## Swift-Specific Forbidden Rules

The following patterns are forbidden:

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

Constraint notes:

- Only Swift reads Keychain.
- Swift reads Keychain only to deliver via XPC.
- Python reads nothing from Keychain.
- LLM API calls from Swift are forbidden.

---

## Wire Format Examples

## Valid Payloads

### Valid TrustFlow Event

```json
{
  "event_id": "6f1b3c9e-7d42-4ad4-a7ce-9d9ef3c1b2a1",
  "session_id": "sess_01HZX8YQ7K8M2P4R9T6N3V1C5B",
  "ctx_id": "ctx_01HZX8Z2W4D9S6F3J7K1M5P8Q",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "3f0d5c7c6a5b4e2d1f9a8b7c6d5e4f30112233445566778899aabbccddeeff00"
}
```

### Valid VTZ Denial Record

```json
{
  "verdict": "block"
}
```

### Valid Consensus Invocation Shape

```python
result = await self._consensus.run(
    task="Implement: ExampleSpec",
    context="relevant context",
    language="python",
)
code = result.final_code
```

---

## Invalid Payloads

### Invalid TrustFlow Event: Missing Required Field

```json
{
  "event_id": "6f1b3c9e-7d42-4ad4-a7ce-9d9ef3c1b2a1",
  "session_id": "sess_01HZX8YQ7K8M2P4R9T6N3V1C5B",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "3f0d5c7c6a5b4e2d1f9a8b7c6d5e4f30112233445566778899aabbccddeeff00"
}
```

Reason: `ctx_id` is required.

### Invalid TrustFlow Event: Non-millisecond Timestamp

```json
{
  "event_id": "6f1b3c9e-7d42-4ad4-a7ce-9d9ef3c1b2a1",
  "session_id": "sess_01HZX8YQ7K8M2P4R9T6N3V1C5B",
  "ctx_id": "ctx_01HZX8Z2W4D9S6F3J7K1M5P8Q",
  "ts": 1735689600,
  "event_type": "allow",
  "payload_hash": "3f0d5c7c6a5b4e2d1f9a8b7c6d5e4f30112233445566778899aabbccddeeff00"
}
```

Reason: `ts` MUST be a UTC Unix timestamp with millisecond precision.

### Invalid VTZ Denial Record

```json
{
  "verdict": "allow"
}
```

Reason: on VTZ policy denial, `verdict` MUST equal `block`.

### Invalid Consensus Invocation: Missing Language

```python
result = await self._consensus.run(
    task="Implement: ExampleSpec",
    context="relevant context",
)
```

Reason: `language` MUST always be passed.

### Invalid Consensus Invocation: Unsupported Language

```python
result = await self._consensus.run(
    task="Implement: ExampleSpec",
    context="relevant context",
    language="java",
)
```

Reason: allowed values are exactly `"python" | "swift" | "go" | "typescript" | "rust"`.

### Invalid Fix Arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason: length-based arbitration is forbidden; use `_score_fix()`.

### Invalid Swift Pattern: Force Unwrap

```swift
let value = optional!
```

Reason: force unwrap is forbidden.

### Invalid Swift Pattern: Backend LLM API Call

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Reason: LLM API call from Swift is forbidden.

### Invalid Swift Pattern: Backend Keychain Read

```swift
let token = KeychainKit.read("github_token")
```

Reason: Python reads nothing from Keychain; Swift reads Keychain only to deliver via XPC.

---

## Integration Points

## Consensus Engine

CraftedAgent integrates with a consensus engine through:

- `await self._consensus.run(task, context, language)`
- Output field: `result.final_code`

Behavioral routing:

- `language="swift"` -> `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`
- `language="python"` -> `GENERATION_SYSTEM`

## CAL Enforcement

Every agent action entry point integrates with CAL enforcement through:

1. CTX-ID validation
2. VTZ policy evaluation
3. `VTZEnforcementDecision` creation on denial
4. TrustFlow emission for all outcomes

## TrustFlow

Synchronous emission in enforcement path. No async buffering permitted.

Required event fields:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

## TrustLock

CTX-ID validation MUST be against TrustLock public key. Software-only validation is rejected.

## Path Security

Before any disk write, integrate:

- `path_security.validate_write_path()`

## Injection Scanning

Before including loaded document chunks in any LLM prompt, integrate injection scanning.

## Prompt Placement

External document context integration rule:

- external document context -> USER prompt
- never -> SYSTEM prompt

## Security Gating

On LLM output value `SECURITY_REFUSAL`:

- stop
- gate
- log
- do not retry to bypass

## Test and Quality Tooling

Required integration points:

- `pytest`
- `ruff`
- `mypy`
- `pyyaml` in `requirements.txt`

## Pre-Implementation Procedure

Before modifying CraftedAgent-related code:

1. Find the owning TRD in `README.md`.
2. Read relevant TRD sections, especially interfaces, error contracts, security, testing requirements.
3. Check TRD-11 if the change touches credentials, external content, generated code, or CI.
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```