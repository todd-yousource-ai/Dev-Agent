# Interface Contracts - FullPlatform

## Data Structures

### Consensus Engine Invocation

#### `ConsensusRunRequest`
Request payload for consensus engine execution.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Human-readable task description. Example must follow source usage such as `Implement: {spec.title}`. |
| `context` | `string` | yes | Context string passed to the engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | yes | Must always be passed. Values exact. |

#### `ConsensusRunResult`
Result returned by consensus engine execution.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Generated code output. |

---

### VTZ Enforcement Decision

#### `VTZEnforcementDecision`
Record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | For denial cases, must be exactly `block`. |

---

### TrustFlow Event

#### `TrustFlowEvent`
Required synchronous audit/emission record for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | Must be globally unique. Must be generated via CSPRNG. Must not be sequential. |
| `session_id` | `string` | yes | Session identifier. |
| `ctx_id` | `string` | yes | CTX-ID associated with the action. |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | yes | Event type identifier. |
| `payload_hash` | `string` | yes | Must be SHA-256 of the serialized action payload. |

---

### CTX-ID Token

#### `CTXID`
Immutable trust token used for agent action processing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Token value. Immutable once issued. Must validate against TrustLock public key. |
| `session_id` | `string` | yes | Session to which the token applies. |
| `vtz_id` | `string` | yes | Every agent session is bound to exactly one VTZ at issuance. |
| `issued_at` | `number` | yes | UTC Unix timestamp. |
| `expires_at` | `number` | yes | UTC Unix timestamp. Expired CTX-ID must be rejected. |
| `invalidated` | `boolean` | yes | Old token must be invalidated immediately on rotation. |

> Note: The TRD specifies behavioral constraints for CTX-ID but does not define additional token fields beyond those required by the contract language above. Implementations must not mutate issued token fields.

---

### Agent Action Payload

#### `AgentAction`
Serialized action payload processed by enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | yes | Must correspond to TrustFlow event `session_id`. |
| `ctx_id` | `string` | yes | Must be validated first. Missing value must be treated as `UNTRUSTED`. |
| `action_type` | `string` | yes | Action identifier used for VTZ policy check. |
| `payload` | `object` | yes | Serialized action payload whose SHA-256 becomes `payload_hash`. |
| `vtz_id` | `string` | yes | Must match session-bound VTZ. Cross-VTZ calls require explicit authorization. |

---

### Security Refusal Signal

#### `SecurityRefusal`
Special LLM output condition.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `output` | `string` | yes | When value is exactly `SECURITY_REFUSAL`, processing must stop, gate, and log. No retry to bypass. |

---

## Enums and Constants

### Language Enum

Exact allowed values for `ConsensusRunRequest.language`:

- `python`
- `swift`
- `go`
- `typescript`
- `rust`

### Special String Constants

| Constant | Exact Value | Meaning |
|---|---|---|
| Security refusal marker | `SECURITY_REFUSAL` | LLM refusal output that must terminate processing. |
| VTZ denial verdict | `block` | Required `VTZEnforcementDecision.verdict` on denial. |
| Untrusted CTX state | `UNTRUSTED` | Required treatment for missing CTX-ID. |

### Engine Selection Constants

These names are part of interface behavior and must be preserved exactly:

- `SWIFT_GENERATION_SYSTEM`
- `SWIFT_UI_ADDENDUM`
- `GENERATION_SYSTEM`

### Internal Strategy/Scoring Function Names

These names are contractually referenced and must be preserved exactly where exposed by implementation behavior:

- `_choose_strategy(failure_type, attempt, records)`
- `_score_fix()`

---

## Validation Rules

### Pre-Execution Ordering Rules

1. Every entry point that processes an agent action **MUST** call CTX-ID validation first.
2. CTX-ID validation failure **MUST** result in immediate rejection.
3. No partial processing is permitted before CTX-ID validation succeeds.
4. Every action **MUST** be checked against VTZ policy before execution.
5. VTZ denial **MUST** produce a `VTZEnforcementDecision` with `verdict=block`.

### TrustFlow Emission Rules

1. Every action outcome — `allow`, `restrict`, or `block` — **MUST** emit a TrustFlow event.
2. Emission **MUST** include all required fields:
   - `event_id`
   - `session_id`
   - `ctx_id`
   - `ts`
   - `event_type`
   - `payload_hash`
3. `event_id` must be globally unique and CSPRNG-generated.
4. `ts` must be a UTC Unix timestamp with millisecond precision.
5. `payload_hash` must be SHA-256 of the serialized action payload.
6. Emission in the enforcement path must be synchronous.
7. Async buffering is not permitted.
8. Failed emission must not silently continue.
9. Failed emission is a WARN-level audit event and must be surfaced.

### CTX-ID Rules

1. CTX-ID tokens are immutable once issued.
2. Rotation creates a new token.
3. The old token is invalidated immediately.
4. Expired CTX-ID must be rejected.
5. Clock skew tolerance is deployment-defined.
6. CTX-ID must be validated against TrustLock public key.
7. Software-only validation is rejected.
8. Missing CTX-ID must be treated as `UNTRUSTED`.
9. Identity must never be inferred from surrounding context when CTX-ID is missing.

### VTZ Rules

1. Every agent session is bound to exactly one VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit cross-VTZ authorization is denied.
4. VTZ boundaries are structural and cannot be bypassed by application code.
5. VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

### Consensus Engine Rules

1. `language` must always be passed to consensus engine execution.
2. Valid values are only:
   - `python`
   - `swift`
   - `go`
   - `typescript`
   - `rust`
3. `language="swift"` selects `SWIFT_GENERATION_SYSTEM` with optional `SWIFT_UI_ADDENDUM` when UI keywords are detected.
4. `language="python"` selects `GENERATION_SYSTEM`.
5. Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.
6. Fix arbitration must use `_score_fix()`.
7. Length-based fix arbitration is forbidden.

### Security Rules

1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Only log status codes and error types for HTTP failures.
6. All file paths written to disk must pass `path_security.validate_write_path()` before any write.
7. All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
8. Context from external documents must go in the USER prompt, never the SYSTEM prompt.
9. On `SECURITY_REFUSAL`, stop, gate, and log. Never retry to bypass.

### Python Backend Rules

1. Python version is `3.12`.
2. All functions must have type annotations.
3. Backend code must use `async/await` throughout.
4. No blocking calls on the event loop.
5. Dataclasses must be used for structured data.
6. Tests must use `pytest`.
7. Tests live in `tests/` and mirror `src/` structure.
8. `ruff` must pass clean.
9. `mypy` must pass clean.
10. Test coverage must be at least `85%` on all new modules.
11. `pyyaml` must be present in `requirements.txt`.

---

## Wire Format Examples

### Valid: Consensus Run Request

```json
{
  "task": "Implement: FullPlatform interface contract",
  "context": "Relevant TRD sections and enforcement requirements",
  "language": "python"
}
```

### Invalid: Consensus Run Request Missing Language

```json
{
  "task": "Implement: FullPlatform interface contract",
  "context": "Relevant TRD sections and enforcement requirements"
}
```

Reason:
- `language` is required.

### Invalid: Consensus Run Request With Unsupported Language

```json
{
  "task": "Implement: FullPlatform interface contract",
  "context": "Relevant TRD sections and enforcement requirements",
  "language": "java"
}
```

Reason:
- `language` must be one of `python`, `swift`, `go`, `typescript`, `rust`.

---

### Valid: TrustFlow Event

```json
{
  "event_id": "7f5f7b6e-4b7f-4aa8-8db7-1d4f8ce4f2ab",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.block",
  "payload_hash": "4c1f8f6d5c2df6d8d3d1d9e0f4e2b7d1e6b8c1a3f0d2e4c6b8a1d3f5c7e9a0b1"
}
```

### Invalid: TrustFlow Event Missing Payload Hash

```json
{
  "event_id": "7f5f7b6e-4b7f-4aa8-8db7-1d4f8ce4f2ab",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.block"
}
```

Reason:
- `payload_hash` is required.

### Invalid: TrustFlow Event With Non-Millisecond Timestamp Semantics

```json
{
  "event_id": "7f5f7b6e-4b7f-4aa8-8db7-1d4f8ce4f2ab",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600,
  "event_type": "action.block",
  "payload_hash": "4c1f8f6d5c2df6d8d3d1d9e0f4e2b7d1e6b8c1a3f0d2e4c6b8a1d3f5c7e9a0b1"
}
```

Reason:
- `ts` must be UTC Unix timestamp with millisecond precision.

---

### Valid: VTZ Enforcement Decision

```json
{
  "verdict": "block"
}
```

### Invalid: VTZ Enforcement Decision

```json
{
  "verdict": "deny"
}
```

Reason:
- Denial verdict must be exactly `block`.

---

### Valid: Agent Action

```json
{
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "action_type": "tool.invoke",
  "payload": {
    "tool": "search",
    "query": "full platform requirements"
  },
  "vtz_id": "vtz_primary"
}
```

### Invalid: Agent Action Missing CTX-ID

```json
{
  "session_id": "sess_123",
  "action_type": "tool.invoke",
  "payload": {
    "tool": "search",
    "query": "full platform requirements"
  },
  "vtz_id": "vtz_primary"
}
```

Reason:
- Missing `ctx_id` must be treated as `UNTRUSTED`.
- Processing must not infer identity from context.

---

### Valid: Security Refusal Signal

```json
{
  "output": "SECURITY_REFUSAL"
}
```

### Invalid: Security Refusal Retry Behavior

```json
{
  "output": "SECURITY_REFUSAL",
  "retry": true
}
```

Reason:
- `SECURITY_REFUSAL` must stop, gate, and log.
- Retry to bypass is forbidden.

---

## Integration Points

### Agent Action Processing Entry Points

Any entry point that processes an agent action must implement this ordered pipeline:

1. Validate `ctx_id` first.
2. Reject immediately on CTX-ID validation failure.
3. Evaluate VTZ policy before execution.
4. On denial, emit `VTZEnforcementDecision` with `verdict=block`.
5. Emit `TrustFlowEvent` synchronously for every outcome.
6. Surface TrustFlow emission failure; do not silently continue.

### Consensus Engine Integration

Required invocation form:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Contract notes:
- `language` is mandatory.
- `result.final_code` is the required result field.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` plus optional `SWIFT_UI_ADDENDUM`.
- `language="python"` selects `GENERATION_SYSTEM`.

### File Write Security Integration

Before any disk write, the target path must be validated with:

```python
path_security.validate_write_path()
```

Minimum contract:
- Validation must occur before write.
- Unvalidated writes are non-conformant.

### Prompt Construction Integration

For external document content:
- loaded chunks must pass injection scanning before inclusion in any LLM prompt
- external context must be placed in the USER prompt
- external context must never be placed in the SYSTEM prompt

### Backend Implementation Integration

Python backend components must conform to:
- Python `3.12`
- `async/await` only on backend execution paths
- dataclasses for structured data
- `pytest` test layout under `tests/`
- `ruff` and `mypy` clean
- `pyyaml` present in `requirements.txt`

### Forbidden Integration Patterns

The following are explicitly non-conformant:

```python
winner = max(claude_fix, openai_fix, key=len)
```

Reason:
- length-based fix arbitration is forbidden; use `_score_fix()`.

```swift
let value = optional!
```

Reason:
- force unwrap is forbidden.

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Reason:
- LLM API call from Swift is forbidden.

```swift
let token = KeychainKit.read("github_token")
```

Reason:
- backend credentials must not be read from Keychain by Python; only Swift reads Keychain, only to deliver via XPC.