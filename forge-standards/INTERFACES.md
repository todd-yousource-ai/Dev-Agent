# Interface Contracts - ForgeAgent

This document defines the wire-format and API contract reference for the ForgeAgent subsystem, derived from the provided TRD excerpts and standards. All fields, types, and constraints below are normative where specified by source text.

## Data Structures

### ConsensusRunRequest

Request contract for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | Yes | Free-form task string. Example source usage: `"Implement: {spec.title}"` |
| `context` | `string` | Yes | Context string passed to the consensus engine |
| `language` | `"python" \| "swift" \| "go" \| "typescript" \| "rust"` | Yes | Must always be passed |

#### Source contract
```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

### ConsensusRunResult

Result contract returned by the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | Yes | Generated code output |

### TrustFlowEvent

Required event shape for TrustFlow emission.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique; CSPRNG-generated; not sequential |
| `session_id` | `string` | Yes | Session identifier |
| `ctx_id` | `string` | Yes | CTX-ID associated with the event |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | Yes | Event type identifier |
| `payload_hash` | `string` | Yes | SHA-256 of the serialized action payload |

### VTZEnforcementDecision

Required record produced on VTZ policy denial.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `"block"` | Yes | MUST be `"block"` on VTZ policy denial |

### CTXIDToken

Logical token contract for CTX-ID.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued |
| `expires_at` | `number \| string` | Yes | Used for expiration validation; expired CTX-ID MUST be rejected |
| `trustlock_signature` | `string` | Yes | MUST validate against TrustLock public key |
| `vtz` | `string` | Yes | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance |

> Note: Field-level CTX-ID token layout is not fully specified in the provided source. The constraints above are normative; additional token fields are implementation-specific unless defined elsewhere in source.

### AgentActionPayload

Serialized action payload used in enforcement and hashing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Validation MUST occur first at every entry point that processes an agent action |
| `session_id` | `string` | Yes | Required for TrustFlow event linkage |
| `action` | `object` | Yes | Subject to VTZ policy check before execution |

> Note: The exact internal shape of `action` is not specified in the provided excerpts.

### SecurityRefusalOutput

Special LLM output sentinel.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `value` | `"SECURITY_REFUSAL"` | Yes | When seen: stop, gate, log; never retry to bypass |

## Enums and Constants

### Language

Allowed values for `ConsensusRunRequest.language`:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### System Selection Constants

The consensus engine selects system prompts based on `language`:

| Language | Selected System |
|---|---|
| `"swift"` | `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` when UI keywords detected |
| `"python"` | `GENERATION_SYSTEM` |

No source-defined system selection constants were provided for `"go"`, `"typescript"`, or `"rust"` beyond being allowed language values.

### VTZ Verdict

Allowed value explicitly defined in source:

- `"block"`

### Special Sentinel Values

- `SECURITY_REFUSAL`

## Validation Rules

### Entry Point Enforcement

Every entry point that processes an agent action MUST satisfy all of the following:

1. Call CTX-ID validation FIRST
2. CTX-ID validation failure MUST result in immediate rejection
3. No partial processing is permitted after CTX-ID validation failure
4. Every action MUST be checked against VTZ policy BEFORE execution
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event
7. TrustFlow emission failure MUST NOT silently continue; log and surface the failure

### TrustFlow Event Validation

A valid TrustFlow event MUST satisfy all of the following:

- Includes exactly these required fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- `event_id` MUST be globally unique
- `event_id` MUST be generated using CSPRNG
- `event_id` MUST NOT be sequential
- `ts` MUST be a UTC Unix timestamp with millisecond precision
- `payload_hash` MUST be SHA-256 of the serialized action payload
- Emission MUST be synchronous in the enforcement path
- Async buffering is not permitted
- Failed emission is a WARN-level audit event, not a silent skip

### CTX-ID Validation

A valid CTX-ID flow MUST satisfy all of the following:

- CTX-ID tokens are immutable once issued
- Rotation creates a new token
- The old token is invalidated immediately on rotation
- Expired CTX-ID MUST be rejected
- Clock skew tolerance is defined per deployment
- CTX-ID MUST be validated against TrustLock public key
- Software-only validation is rejected
- Missing CTX-ID MUST be treated as `UNTRUSTED`
- Identity MUST never be inferred from context when CTX-ID is missing

### VTZ Enforcement

A valid VTZ enforcement flow MUST satisfy all of the following:

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit authorization is denied
- VTZ boundaries are structural, not advisory
- Enforcement cannot be bypassed by application code
- VTZ policy changes take effect at NEXT CTX-ID issuance
- VTZ policy changes do not take effect mid-session

### Consensus Engine Validation

- `language` MUST always be passed to `_consensus.run(...)`
- `language` MUST be one of:
  - `"python"`
  - `"swift"`
  - `"go"`
  - `"typescript"`
  - `"rust"`

### Fix Loop and Arbitration Rules

- Fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`
- Fix loop strategy is NOT a static lookup table
- Fix arbitration uses `_score_fix()` based on assertion token overlap
- Length-based arbitration is forbidden

#### Forbidden example
```python
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

### Security Rules

The ForgeAgent subsystem MUST enforce the following:

- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Never use `shell=True` in subprocess calls
- Never call `eval()` or `exec()` on any generated or external content
- Never log HTTP response bodies
- Log status codes and error types only
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write
- All loaded document chunks MUST pass injection scanning before being included in any LLM prompt
- Context from external documents goes in the USER prompt, never the SYSTEM prompt
- When `SECURITY_REFUSAL` output is seen from the LLM: stop, gate, log; never retry to bypass

### Python Backend Rules

For Python implementations in ForgeAgent:

- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- `pytest` for all tests
- Tests live in `tests/`
- Tests mirror `src/` structure
- `ruff` for linting
- `mypy` for type checking
- Both must pass clean
- Test coverage must be `>= 85%` on all new modules
- `pyyaml` must be in `requirements.txt`

### Swift-Specific Forbidden Patterns

The following are forbidden exactly as specified:

```swift
// FORBIDDEN: force unwrap
let value = optional!

// FORBIDDEN: LLM API call from Swift
let client = AnthropicClient(apiKey: keychainValue)

// FORBIDDEN: Keychain read for backend
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
// Only Swift reads Keychain, only to deliver via XPC
```

## Wire Format Examples

### Valid: ConsensusRunRequest

```json
{
  "task": "Implement: Add session-scoped VTZ enforcement",
  "context": "Use existing enforcement path. Validate CTX-ID first.",
  "language": "python"
}
```

### Valid: ConsensusRunResult

```json
{
  "final_code": "from dataclasses import dataclass\n..."
}
```

### Valid: TrustFlowEvent

```json
{
  "event_id": "9d7d1b4d-1b1d-4c9f-9d6b-6f5c4b6f7a10",
  "session_id": "sess_01HV8M9R4J2Y",
  "ctx_id": "ctx_01HV8MA2PK8N",
  "ts": 1712512345123,
  "event_type": "agent_action_allow",
  "payload_hash": "5d41402abc4b2a76b9719d911017c5926a8b7e5d6c8f1a2b3c4d5e6f7a8b9c0d"
}
```

### Valid: VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

### Valid: AgentActionPayload

```json
{
  "ctx_id": "ctx_01HV8MA2PK8N",
  "session_id": "sess_01HV8M9R4J2Y",
  "action": {
    "type": "tool_call",
    "tool": "repo.write_file"
  }
}
```

### Invalid: ConsensusRunRequest missing language

```json
{
  "task": "Implement: Add CTX-ID validation",
  "context": "Validate before processing."
}
```

Reason:
- `language` is required
- Language must always be passed

### Invalid: ConsensusRunRequest with unsupported language

```json
{
  "task": "Implement: Add CTX-ID validation",
  "context": "Validate before processing.",
  "language": "java"
}
```

Reason:
- `language` must be one of `"python" | "swift" | "go" | "typescript" | "rust"`

### Invalid: TrustFlowEvent missing payload_hash

```json
{
  "event_id": "9d7d1b4d-1b1d-4c9f-9d6b-6f5c4b6f7a10",
  "session_id": "sess_01HV8M9R4J2Y",
  "ctx_id": "ctx_01HV8MA2PK8N",
  "ts": 1712512345123,
  "event_type": "agent_action_block"
}
```

Reason:
- Every TrustFlow event MUST include `payload_hash`

### Invalid: VTZEnforcementDecision wrong verdict

```json
{
  "verdict": "allow"
}
```

Reason:
- On VTZ policy denial, record MUST have `verdict=block`

### Invalid: Agent action processing without CTX-ID

```json
{
  "session_id": "sess_01HV8M9R4J2Y",
  "action": {
    "type": "tool_call"
  }
}
```

Reason:
- Missing CTX-ID must be treated as `UNTRUSTED`
- CTX-ID validation must occur first
- Processing must be rejected immediately

## Integration Points

### Consensus Engine

ForgeAgent integrates with the consensus engine via:

```python
await self._consensus.run(
    task=...,
    context=...,
    language=...,
)
```

#### Required behavior
- Always pass `language`
- Read output from `result.final_code`

### Prompt Construction

- External document context MUST be placed in the USER prompt
- External document context MUST NOT be placed in the SYSTEM prompt
- Loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt

### Path Security

Before any disk write:

```python
path_security.validate_write_path()
```

Required behavior:
- All file paths written to disk must pass `path_security.validate_write_path()` before any write

### TrustFlow Emission

TrustFlow emission is part of the enforcement path and must be synchronous.

Required event fields:
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Failure handling:
- Failed emission is a WARN-level audit event
- Failure must be logged
- Failure must be surfaced
- Silent continuation is forbidden

### TrustLock Validation

CTX-ID validation must integrate with TrustLock public-key validation.

Required behavior:
- Validate against TrustLock public key
- Software-only validation is rejected

### VTZ Policy Engine

Every action must be checked against VTZ policy before execution.

Required behavior:
- Cross-VTZ tool calls require explicit policy authorization
- Implicit authorization is denied
- Policy denial must emit `VTZEnforcementDecision { "verdict": "block" }`

### Testing and Conformance

Before modifying ForgeAgent-related code:

1. Find the TRD that owns the component in `README.md`
2. Read the relevant TRD sections, especially:
   - interfaces
   - error contracts
   - security
   - testing requirements
3. Check `TRD-11` if the change touches:
   - credentials
   - external content
   - generated code
   - CI
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```