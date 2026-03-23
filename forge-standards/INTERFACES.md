# Interface Contracts - FullPlatform

## Data Structures

### ConsensusRunRequest
Request contract for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Human-readable implementation task description. |
| `context` | `string` | Yes | Context string passed to the consensus engine. |
| `language` | `string` | Yes | MUST be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. |

#### Notes
- Calls MUST pass `language`.
- Required call shape:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

---

### ConsensusRunResult
Return contract from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Final generated code selected by consensus flow. |

---

### VTZEnforcementDecision
Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | MUST be `"block"` when produced for VTZ policy denial. |

#### Notes
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### TrustFlowEvent
Audit/enforcement event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique. MUST be generated using CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type identifier. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Notes
- Every TrustFlow event MUST include all fields above.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and MUST NOT be silently skipped.

---

### CTXIDToken
Opaque trust token used for request validation and VTZ binding.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Token value. Immutable once issued. |
| `vtz` | `string` | Yes | Every agent session is bound to exactly one VTZ at issuance. |
| `issued_at` | `number` | Yes | Issuance time. |
| `expires_at` | `number` | Yes | Expiry time. Expired tokens MUST be rejected. |
| `public_key_id` | `string` | Yes | Identifies TrustLock public key used for validation. |

#### Notes
- CTX-ID tokens are IMMUTABLE once issued.
- Rotation creates a new token; the old one is invalidated immediately.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

---

### AgentActionEnvelope
Canonical action-processing envelope for CAL enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | Yes | Session identifier. |
| `ctx_id` | `string` | Yes | MUST be validated first. Missing value is treated as `UNTRUSTED`. |
| `action_payload` | `object` | Yes | Serialized payload to be checked by VTZ and hashed into `payload_hash`. |
| `event_type` | `string` | Yes | Outcome/event classification. |

#### Notes
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection with no partial processing.
- Every action MUST be checked against VTZ policy BEFORE execution.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### FixStrategySelectionInput
Input contract implied by failure-aware fix loop selection.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `string` | Yes | Failure classification passed to `_choose_strategy(failure_type, attempt, records)`. |
| `attempt` | `integer` | Yes | Current fix attempt number. |
| `records` | `array` | Yes | Prior records used by `_choose_strategy`. |

---

### FixArbitrationInput
Input contract implied by fix arbitration scoring.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `candidate_fix` | `string` | Yes | Candidate fix content. |
| `assertion_tokens` | `array<string>` | Yes | Assertion token set used by `_score_fix()`. |

#### Notes
- Fix arbitration MUST use `_score_fix()`.
- Length-based arbitration is forbidden.

---

## Enums and Constants

### SupportedLanguage
Exact allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### OutcomeVerdict
Observed action outcomes required by enforcement flow:

- `"allow"`
- `"restrict"`
- `"block"`

### SpecialTrustState
Special trust state for missing CTX-ID:

- `UNTRUSTED`

### SecurityRefusalOutput
Special LLM output token:

- `SECURITY_REFUSAL`

### System Selection Constants
Language-to-system selection rules:

| Language | Selected System |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords are detected |
| `"python"` | `GENERATION_SYSTEM` |

---

## Validation Rules

### General
1. All structured data in Python implementations MUST use dataclasses.
2. All functions MUST include type annotations.
3. Backend code MUST use `async/await` throughout.
4. No blocking calls on the event loop.

### Consensus Engine
1. `language` is mandatory on every consensus run call.
2. `language` MUST equal one of the exact `SupportedLanguage` values.
3. The result object MUST expose `final_code`.

### CAL Enforcement
1. CTX-ID validation MUST occur before any agent action processing.
2. CTX-ID validation failure MUST immediately reject the action.
3. No partial processing is allowed after CTX-ID validation failure.
4. VTZ policy check MUST occur before execution.
5. VTZ denial MUST create `VTZEnforcementDecision` with `verdict` equal to `"block"`.
6. Every action outcome MUST emit a `TrustFlowEvent`.
7. TrustFlow emission failure MUST be logged and surfaced.
8. TrustFlow emission MUST be synchronous in the enforcement path.

### TrustFlow
1. `event_id` MUST be globally unique.
2. `event_id` MUST be generated using CSPRNG.
3. `event_id` MUST NOT be sequential.
4. `ts` MUST be a UTC Unix timestamp with millisecond precision.
5. `payload_hash` MUST be the SHA-256 of the serialized action payload.

### CTX-ID
1. CTX-ID tokens MUST be immutable after issuance.
2. CTX-ID rotation MUST issue a new token and immediately invalidate the old token.
3. Expired CTX-ID tokens MUST be rejected.
4. Validation MUST use TrustLock public key.
5. Software-only validation is rejected.
6. Missing CTX-ID MUST be treated as `UNTRUSTED`.
7. Clock skew tolerance is deployment-defined and not specified here.

### VTZ
1. Every agent session MUST be bound to exactly one VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit cross-VTZ access is denied.
4. VTZ boundaries are structural and cannot be bypassed by application code.
5. VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

### Security
1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Log HTTP status codes and error types only.
6. All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
7. All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
8. Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
9. If `SECURITY_REFUSAL` is returned, processing MUST stop, gate, and log. It MUST NOT retry to bypass.

### Forbidden Implementations
The following are non-conformant:

#### Length-based fix arbitration
```python
winner = max(claude_fix, openai_fix, key=len)
```

#### Swift force unwrap
```swift
let value = optional!
```

#### LLM API call from Swift
```swift
let client = AnthropicClient(apiKey: keychainValue)
```

#### Keychain read for backend
```swift
let token = KeychainKit.read("github_token")
```

### Backend/Swift boundary
1. Only Swift reads Keychain.
2. Swift reads Keychain only to deliver via XPC.
3. Python backend reads nothing from Keychain.

---

## Wire Format Examples

### Valid: ConsensusRunRequest
```json
{
  "task": "Implement: Add retry handling",
  "context": "Relevant spec and failure history",
  "language": "python"
}
```

### Invalid: ConsensusRunRequest with missing language
```json
{
  "task": "Implement: Add retry handling",
  "context": "Relevant spec and failure history"
}
```

Reason:
- `language` is required.

### Invalid: ConsensusRunRequest with unsupported language
```json
{
  "task": "Implement: Add retry handling",
  "context": "Relevant spec and failure history",
  "language": "java"
}
```

Reason:
- `language` MUST be one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`.

---

### Valid: TrustFlowEvent
```json
{
  "event_id": "3f7a4f42-7f5f-4b76-90aa-2f9b8dd8a0e1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961cdd3d6556c10d2f0f9c2b2"
}
```

### Invalid: TrustFlowEvent with sequential event_id and second-precision ts
```json
{
  "event_id": "10042",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600,
  "event_type": "allow",
  "payload_hash": "not-a-sha256"
}
```

Reasons:
- `event_id` MUST be globally unique and not sequential.
- `ts` MUST have millisecond precision.
- `payload_hash` MUST be SHA-256 of serialized action payload.

---

### Valid: VTZEnforcementDecision
```json
{
  "verdict": "block"
}
```

### Invalid: VTZEnforcementDecision
```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ denial record MUST use `verdict` exactly equal to `"block"`.

---

### Valid: AgentActionEnvelope
```json
{
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "action_payload": {
    "tool": "write_file",
    "path": "/workspace/output.txt"
  },
  "event_type": "restrict"
}
```

### Invalid: AgentActionEnvelope with missing ctx_id
```json
{
  "session_id": "sess_123",
  "action_payload": {
    "tool": "write_file",
    "path": "/workspace/output.txt"
  },
  "event_type": "allow"
}
```

Reasons:
- `ctx_id` must be validated first.
- Missing CTX-ID is treated as `UNTRUSTED` and must not proceed as trusted processing.

---

## Integration Points

### Consensus Engine
- Invocation method: `await self._consensus.run(...)`
- Required parameters:
  - `task`
  - `context`
  - `language`
- Returned field consumed by callers:
  - `final_code`

### System Prompt Selection
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
- `language="python"` selects `GENERATION_SYSTEM`.

### Fix Loop
- Strategy selection entry point: `_choose_strategy(failure_type, attempt, records)`
- Arbitration entry point: `_score_fix()`
- Length-based arbitration is forbidden and non-conformant.

### Path Security
- Any disk write integration MUST call:
  - `path_security.validate_write_path()`

### Prompt Assembly / Injection Scanning
- Loaded document chunks MUST pass injection scanning before inclusion in prompts.
- External document context MUST be placed in the USER prompt, never the SYSTEM prompt.

### Trust / Enforcement Pipeline
- Entry points handling agent actions MUST:
  1. Validate CTX-ID first
  2. Enforce VTZ policy before execution
  3. Emit TrustFlow event synchronously for every outcome
  4. Surface emission failures

### Backend Startup / Test Requirements
- Existing tests MUST be run with:

```bash
cd src && pytest ../tests/ -v --tb=short
```

### Python Module Requirements
- Python version: `3.12`
- Testing framework: `pytest`
- Linting: `ruff`
- Type checking: `mypy`
- Required dependency: `pyyaml`
- Coverage requirement for new modules: `>= 85%`