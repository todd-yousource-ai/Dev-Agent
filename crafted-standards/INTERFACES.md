# Interface Contracts - CraftedAgent

## Data Structures

All structured data in the CraftedAgent subsystem MUST use explicit typed structures. Per subsystem standards, Python implementations MUST use dataclasses for all structured data.

### CraftedAgentActionRequest

Represents an inbound agent action request entering the enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | Yes | MUST be present on every request entering enforcement. |
| `ctx_id` | `string` | Yes | MUST be validated first. Missing `ctx_id` MUST be treated as `UNTRUSTED`. |
| `action` | `object` | Yes | Serialized action payload. MUST be checked against VTZ policy before execution. Used to derive `payload_hash` as SHA-256 of the serialized action payload. |

#### Behavioral contract
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection — no partial processing.
- Every action MUST be checked against VTZ policy BEFORE execution.

---

### TrustFlowEvent

Audit/event record emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique (`CSPRNG, not sequential`). |
| `session_id` | `string` | Yes | MUST identify the agent session. |
| `ctx_id` | `string` | Yes | MUST match the CTX-ID used for the action. |
| `ts` | `number` | Yes | MUST be UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | MUST identify the event kind. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Behavioral contract
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path — async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

---

### VTZEnforcementDecision

Decision record produced when VTZ policy is evaluated.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | On VTZ policy denial, MUST be exactly `block`. |

#### Behavioral contract
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### CTXIDToken

Represents a CTX-ID token as an immutable trust identity artifact.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Token identifier; immutable once issued. |
| `vtz` | `string` | Yes | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance. |
| `expired` | `boolean` | Yes | If `true`, token MUST be rejected. |
| `signature` | `string` | Yes | MUST validate against TrustLock public key. Software-only validation is rejected. |

#### Behavioral contract
- CTX-ID tokens are IMMUTABLE once issued — no field modification after issuance.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected — clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against TrustLock public key — software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED` — never infer identity from context.

> Note: The TRD defines behavioral requirements for CTX-ID but does not define additional token fields beyond what is necessary to express the contract above.

---

### ConsensusRunRequest

Input contract for consensus engine usage when CraftedAgent invokes code generation or repair.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Example usage: `f"Implement: {spec.title}"`. |
| `context` | `string` | Yes | Context string passed to the consensus engine. |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | MUST always be passed. |

#### Behavioral contract
- Always pass `language`.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` (injected when UI keywords detected).
- `language="python"` selects `GENERATION_SYSTEM` — security-focused Python rules.

---

### ConsensusRunResult

Result contract returned by the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output. |

---

### FixStrategyInput

Input to failure-aware fix loop strategy selection.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `string` | Yes | Failure classification used by `_choose_strategy(failure_type, attempt, records)`. |
| `attempt` | `integer` | Yes | Current repair attempt count. |
| `records` | `array` | Yes | Prior failure/repair records. |

#### Behavioral contract
- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)` — not a static lookup table.

---

### FixArbitrationInput

Inputs used to score candidate fixes.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `assertion_tokens` | `array[string]` | Yes | Assertion token set used for overlap scoring. |
| `candidate_fix` | `string` | Yes | Candidate fix content. |

#### Behavioral contract
- Fix arbitration uses `_score_fix()` based on assertion token overlap — not response length.
- The following is FORBIDDEN:
  - `winner = max(claude_fix, openai_fix, key=len)`

---

## Enums and Constants

### Verdict

Allowed known value from the TRD:

| Value |
|---|
| `block` |

`VTZEnforcementDecision.verdict` MUST be exactly `block` on VTZ policy denial.

---

### Action Outcome

Every action outcome MUST be one of:

| Value |
|---|
| `allow` |
| `restrict` |
| `block` |

Each outcome MUST emit a TrustFlow event.

---

### Language

Consensus engine language values:

| Value |
|---|
| `python` |
| `swift` |
| `go` |
| `typescript` |
| `rust` |

`language` is REQUIRED in every consensus engine invocation.

---

### Trust Classification

| Value |
|---|
| `UNTRUSTED` |

Missing CTX-ID MUST be treated as `UNTRUSTED`.

---

### Generation System Selectors

| Constant | Meaning |
|---|---|
| `SWIFT_GENERATION_SYSTEM` | Selected when `language="swift"` |
| `SWIFT_UI_ADDENDUM` | Optional addendum injected when UI keywords detected |
| `GENERATION_SYSTEM` | Selected when `language="python"` |

---

### Required Algorithms / Formats

| Name | Required Value |
|---|---|
| `payload_hash` algorithm | `SHA-256` |
| `event_id` generation | `CSPRNG, not sequential` |
| `ts` format | `UTC Unix timestamp with millisecond precision` |

---

## Validation Rules

### Enforcement order
1. CTX-ID validation MUST occur FIRST.
2. If CTX-ID validation fails, processing MUST stop immediately.
3. VTZ policy evaluation MUST occur BEFORE execution.
4. On denial, produce `VTZEnforcementDecision` with `verdict=block`.
5. Emit a `TrustFlowEvent` for every action outcome.
6. TrustFlow emission MUST be synchronous in the enforcement path.

### CTX-ID rules
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is permitted after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Validation MUST be against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.

### VTZ rules
- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

### TrustFlow rules
- Every TrustFlow event MUST include:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Failed emission is a WARN-level audit event.
- Failed emission MUST NOT be silently skipped.

### Consensus engine rules
- Always pass `language`.
- Valid `language` values are exactly:
  - `python`
  - `swift`
  - `go`
  - `typescript`
  - `rust`

### Security rules
- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on any generated or external content.
- Never log HTTP response bodies. Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before being included in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- When you see `SECURITY_REFUSAL` output from the LLM: stop, gate, log. Never retry to bypass.

### Python implementation rules
- Python version MUST be `Python 3.12`.
- Type annotations required on every function.
- `async/await` throughout the backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- `pytest` for all tests.
- Tests live in `tests/`, mirror `src/` structure.
- `ruff` MUST pass clean.
- `mypy` MUST pass clean.
- Test coverage MUST be `≥ 85%` on all new modules.
- `pyyaml` MUST be in `requirements.txt`.

### Forbidden patterns
- Length-based fix arbitration is forbidden:
  - `winner = max(claude_fix, openai_fix, key=len)`
- Swift force unwrap is forbidden:
  - `let value = optional!`
- LLM API call from Swift is forbidden:
  - `let client = AnthropicClient(apiKey: keychainValue)`
- Backend token read from Keychain is forbidden:
  - `let token = KeychainKit.read("github_token")`
- Only Swift reads Keychain, only to deliver via XPC.

---

## Wire Format Examples

## Valid payloads

### Valid TrustFlowEvent

```json
{
  "event_id": "6f8d3f4b-9f9c-4e8a-a8e1-7c2f8e8d4b11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3a7bd3e2360a3d29eea436fcfb7e44c73e2d4b5d8f5f9a6b1c2d3e4f5a6b7c8d"
}
```

Why valid:
- Includes all required fields.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `payload_hash` is represented as a SHA-256 digest string.
- Suitable for synchronous emission in the enforcement path.

---

### Valid VTZEnforcementDecision on denial

```json
{
  "verdict": "block"
}
```

Why valid:
- Denial requires a `VTZEnforcementDecision` with `verdict=block`.

---

### Valid consensus run request

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant context for generation",
  "language": "python"
}
```

Why valid:
- Includes required `language`.
- Uses an allowed language enum value.

---

### Valid crafted action request

```json
{
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "action": {
    "tool": "write_file",
    "path": "/workspace/output.py"
  }
}
```

Why valid:
- Contains required `session_id`, `ctx_id`, and `action`.
- `action` can be serialized for SHA-256 `payload_hash` generation.
- Request is eligible for CTX-ID validation first, then VTZ evaluation.

---

## Invalid payloads

### Invalid TrustFlowEvent: missing required field

```json
{
  "event_id": "6f8d3f4b-9f9c-4e8a-a8e1-7c2f8e8d4b11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "payload_hash": "3a7bd3e2360a3d29eea436fcfb7e44c73e2d4b5d8f5f9a6b1c2d3e4f5a6b7c8d"
}
```

Why invalid:
- Missing required `event_type`.

---

### Invalid VTZEnforcementDecision: wrong verdict

```json
{
  "verdict": "deny"
}
```

Why invalid:
- On VTZ policy denial, `verdict` MUST be exactly `block`.

---

### Invalid consensus run request: language omitted

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant context for generation"
}
```

Why invalid:
- `language` is mandatory.

---

### Invalid consensus run request: unsupported language

```json
{
  "task": "Implement: ExampleSpec",
  "context": "Relevant context for generation",
  "language": "java"
}
```

Why invalid:
- Allowed values are exactly `python`, `swift`, `go`, `typescript`, `rust`.

---

### Invalid action request: missing CTX-ID

```json
{
  "session_id": "sess_123",
  "action": {
    "tool": "write_file"
  }
}
```

Why invalid:
- Missing `ctx_id` MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from surrounding context.

---

## Integration Points

### Consensus engine integration

CraftedAgent MUST invoke the consensus engine with this contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

#### Integration requirements
- `language` MUST always be passed.
- `result.final_code` is the generated code output.
- `language="swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM`.
- `language="python"` selects `GENERATION_SYSTEM`.

---

### TrustFlow integration

Every action outcome in CraftedAgent MUST synchronously emit a `TrustFlowEvent` including:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Emission failure handling:
- MUST log and surface the failure.
- MUST be treated as a WARN-level audit event.
- MUST NOT silently continue.

---

### CTX-ID / TrustLock integration

CraftedAgent MUST validate CTX-ID:
- before any partial processing,
- against TrustLock public key,
- with expiry enforcement,
- with immediate invalidation on rotation.

Software-only validation is non-conformant.

---

### VTZ policy integration

CraftedAgent MUST:
- bind each session to EXACTLY ONE VTZ at CTX-ID issuance,
- evaluate every action against VTZ policy before execution,
- deny implicit cross-VTZ tool calls,
- enforce policy structurally, not advisory.

On denial, CraftedAgent MUST produce:

```json
{
  "verdict": "block"
}
```

---

### Path security integration

Before any disk write, CraftedAgent MUST call:

```python
path_security.validate_write_path()
```

All file paths written to disk must pass this validation before any write.

---

### Prompt construction integration

When external documents are used:
- all loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt,
- context from external documents MUST go in the USER prompt,
- context from external documents MUST NEVER go in the SYSTEM prompt.

If the LLM returns `SECURITY_REFUSAL`:
- stop,
- gate,
- log,
- never retry to bypass.