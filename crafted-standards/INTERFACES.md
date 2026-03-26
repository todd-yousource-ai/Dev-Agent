# Interface Contracts - CraftedDevAgent

Definitive wire format and API contract reference for the CraftedDevAgent subsystem.

## Data Structures

### ConsensusRunRequest

Request payload for invoking the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `task` | `string` | yes | Freeform task description. Example source usage: `"Implement: {spec.title}"`. |
| `context` | `string` | yes | Context string supplied to consensus. External document context, if any, MUST be included in the USER prompt context and never the SYSTEM prompt. |
| `language` | `Language` | yes | MUST be exactly one of: `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`. Always pass `language`. |

### ConsensusRunResult

Result returned from the consensus engine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `final_code` | `string` | yes | Generated code selected by consensus. |
| `security_refusal` | `boolean` | no | If present and `true`, indicates `SECURITY_REFUSAL` behavior; processing MUST stop, gate, and log. Never retry to bypass. |

### CraftedSpec

Structured specification used by CraftedDevAgent when preparing consensus calls.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `title` | `string` | yes | Used to construct `task` as `"Implement: {spec.title}"`. |
| `language` | `Language` | yes | MUST be propagated to consensus unchanged. |

### FixStrategySelectionInput

Input to failure-aware fix loop strategy selection.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `failure_type` | `string` | yes | Failure category identifier. Exact allowed values are implementation-defined, but strategy selection MUST be performed by `_choose_strategy(failure_type, attempt, records)`. |
| `attempt` | `integer` | yes | Attempt number, `>= 1`. |
| `records` | `array<object>` | yes | Prior fix/attempt records. Structure implementation-defined. |

### FixArbitrationInput

Input to fix arbitration scoring.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `claude_fix` | `string` | no | Candidate fix content. |
| `openai_fix` | `string` | no | Candidate fix content. |
| `assertion_tokens` | `array<string>` | yes | Assertion token set used for overlap scoring. |

### TrustFlowEvent

Synchronous audit/enforcement event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | yes | Session identifier. |
| `ctx_id` | `string` | yes | CTX-ID associated with the action. Missing `ctx_id` MUST be treated as `UNTRUSTED`; identity MUST never be inferred from context. |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | yes | Event classification for allow, restrict, or block outcomes. |
| `payload_hash` | `string` | yes | MUST be SHA-256 of the serialized action payload. Lower/upper hex encoding is implementation-defined unless otherwise specified by owner TRD. |

### VTZEnforcementDecision

Policy decision record produced on VTZ denial.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | On VTZ policy denial, MUST be exactly `block`. |
| `session_id` | `string` | no | Session identifier if available. |
| `ctx_id` | `string` | no | CTX-ID if available. |
| `reason` | `string` | no | Human/audit-readable denial reason. |

### CTXIDToken

Logical token contract for CTX-ID validation.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Token identifier. IMMUTABLE once issued. |
| `issued_at` | `number` | yes | Issuance timestamp. |
| `expires_at` | `number` | yes | Expiration timestamp. Expired CTX-ID MUST be rejected. Clock skew tolerance is deployment-defined. |
| `vtz_id` | `string` | yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance. |
| `public_key_id` | `string` | no | Identifier for TrustLock public key used in validation. |
| `signature` | `string` | no | Validation MUST be against TrustLock public key. Software-only validation is rejected. |

### AgentActionPayload

Serialized action payload subject to validation, hashing, and enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | yes | Session identifier for enforcement and audit. |
| `ctx_id` | `string` | yes | MUST be validated first before any partial processing. |
| `action_type` | `string` | yes | Action category, implementation-defined. |
| `payload` | `object` | yes | Action-specific payload. Serialized form is the input to `payload_hash` computation. |

### WritePathValidationRequest

Validation input before any file write.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `path` | `string` | yes | Every file path written to disk MUST pass `path_security.validate_write_path()` before any write. |

### InjectionScanRequest

Validation input before including loaded document chunks in any LLM prompt.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `document_chunks` | `array<string>` | yes | All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt. |

### SubprocessInvocation

Structured subprocess call contract.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `args` | `array<string>` | yes | Command and arguments. |
| `shell` | `boolean` | no | MUST NOT be `true`. `shell=True` is forbidden. |

### TestCommand

Canonical pre-change test command.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `cwd` | `string` | yes | MUST be `src`. |
| `command` | `string` | yes | MUST be exactly `pytest ../tests/ -v --tb=short`. |

## Enums and Constants

### Language

String enum. Allowed values are exactly:

- `"python"`
- `"swift"`
- `"go"`
- `"typescript"`
- `"rust"`

### Consensus System Selection Rules

Derived constant behavior:

- `language="swift"` selects `SWIFT_GENERATION_SYSTEM`
- `language="swift"` may additionally inject `SWIFT_UI_ADDENDUM` when UI keywords are detected
- `language="python"` selects `GENERATION_SYSTEM`

### Security Refusal Sentinel

Exact sentinel value:

- `SECURITY_REFUSAL`

When observed in LLM output or result handling, processing MUST stop, gate, and log. Never retry to bypass.

### VTZ Verdict

Known required value:

- `block`

Used in `VTZEnforcementDecision.verdict` when VTZ policy denies an action.

### Trust Classification

Known required value:

- `UNTRUSTED`

Applied when `ctx_id` is missing. Identity must not be inferred from context.

### Forbidden Patterns

These are non-conformant and MUST NOT appear in implementations.

#### Forbidden fix arbitration

```python
winner = max(claude_fix, openai_fix, key=len)
```

Constraint:
- Length-based arbitration is forbidden.
- Use `_score_fix()` based on assertion token overlap.

#### Forbidden Swift force unwrap

```swift
let value = optional!
```

Constraint:
- Force unwrap is forbidden.

#### Forbidden Swift-side LLM API call

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Constraint:
- LLM API calls from Swift are forbidden.

#### Forbidden backend Keychain read

```swift
let token = KeychainKit.read("github_token")
```

Constraint:
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

### Required Tooling / Environment Constants

- Python version: `3.12`
- Test framework: `pytest`
- Linting: `ruff`
- Type checking: `mypy`
- Required package: `pyyaml`
- Coverage requirement for new modules: `>= 85%`

## Validation Rules

### Entry Point Enforcement Order

Every entry point that processes an agent action MUST enforce the following order:

1. CTX-ID validation FIRST
2. Immediate rejection on CTX-ID validation failure
3. VTZ policy check BEFORE execution
4. On VTZ denial, produce `VTZEnforcementDecision` with `verdict=block`
5. Emit a `TrustFlowEvent` for every action outcome: allow, restrict, block

Additional constraint:
- TrustFlow emission failure MUST NOT silently continue; it MUST be logged and surfaced.

### TrustFlow Event Validation

For every `TrustFlowEvent`:

- `event_id` MUST be globally unique
- `event_id` MUST use CSPRNG
- `event_id` MUST NOT be sequential
- `ts` MUST be UTC Unix timestamp with millisecond precision
- `payload_hash` MUST be SHA-256 of the serialized action payload
- Emission MUST be synchronous in the enforcement path
- Async buffering is not permitted
- Failed emission is a WARN-level audit event, not a silent skip

### CTX-ID Validation Rules

- CTX-ID tokens are immutable once issued
- Rotation creates a new token
- Old token is invalidated immediately on rotation
- Expired CTX-ID MUST be rejected
- Validation MUST be against TrustLock public key
- Software-only validation is rejected
- Missing CTX-ID MUST be treated as `UNTRUSTED`
- Identity MUST never be inferred from context when CTX-ID is missing

### VTZ Enforcement Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit authorization is denied
- VTZ boundaries are structural, not advisory
- Enforcement cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session

### Consensus Invocation Rules

Consensus calls MUST follow this contract:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,
)
code = result.final_code
```

Validation constraints:

- `language` is mandatory
- `language` MUST be one of the `Language` enum values
- `task` SHOULD be derived from spec title as shown above for implementation tasks
- Returned code MUST be read from `result.final_code`

### Fix Loop Rules

- Fix loop strategy MUST be failure-type-aware via `_choose_strategy(failure_type, attempt, records)`
- Static lookup-table strategy selection is non-conformant
- Fix arbitration MUST use `_score_fix()`
- `_score_fix()` MUST score based on assertion token overlap
- Response length MUST NOT be used as the arbitration criterion

### Security Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Never use `shell=True` in subprocess calls
- Never call `eval()` or `exec()` on generated or external content
- Never log HTTP response bodies
- Only log HTTP status codes and error types
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt
- On `SECURITY_REFUSAL`: stop, gate, log; never retry to bypass

### Python Backend Rules

- Python `3.12`
- Type annotations on every function
- `async/await` throughout backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Tests live in `tests/`
- Tests mirror `src/` structure
- `ruff` and `mypy` MUST pass clean
- Test coverage on all new modules MUST be at least `85%`
- `pyyaml` MUST be present in `requirements.txt`

### Keychain / Platform Boundary Rules

- Swift may read Keychain only to deliver via XPC
- Python backend reads nothing from Keychain
- Swift must not make direct LLM API calls

### Pre-change Workflow Rule

Before writing code:

1. Find the TRD that owns the component in `README.md`
2. Read relevant TRD sections, especially interfaces, error contracts, security, testing requirements
3. Check TRD-11 if the change touches credentials, external content, generated code, or CI
4. Run existing tests using the canonical command

## Wire Format Examples

### Valid: ConsensusRunRequest

```json
{
  "task": "Implement: Add retry-safe file writer",
  "context": "User prompt context only. External document excerpts have been injection scanned.",
  "language": "python"
}
```

### Invalid: ConsensusRunRequest missing language

```json
{
  "task": "Implement: Add retry-safe file writer",
  "context": "Context without language"
}
```

Reason:
- `language` is required

### Invalid: ConsensusRunRequest bad language

```json
{
  "task": "Implement: Add retry-safe file writer",
  "context": "Context",
  "language": "java"
}
```

Reason:
- `language` must be exactly one of `"python"`, `"swift"`, `"go"`, `"typescript"`, `"rust"`

### Valid: TrustFlowEvent

```json
{
  "event_id": "8df0cc0d-309c-4e8e-b910-f6d9c4f48712",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "3d1e5c4f7a8b9c00112233445566778899aabbccddeeff001122334455667788"
}
```

### Invalid: TrustFlowEvent with sequential event_id and second-precision timestamp

```json
{
  "event_id": "42",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600,
  "event_type": "allow",
  "payload_hash": "not-a-sha256"
}
```

Reasons:
- `event_id` must be globally unique and CSPRNG-generated, not sequential
- `ts` must have millisecond precision
- `payload_hash` must be SHA-256 of serialized action payload

### Valid: VTZEnforcementDecision on denial

```json
{
  "verdict": "block",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "reason": "Cross-VTZ tool call denied by policy"
}
```

### Invalid: VTZEnforcementDecision wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- On VTZ policy denial, `verdict` must be exactly `block`

### Valid: AgentActionPayload

```json
{
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "action_type": "tool_call",
  "payload": {
    "tool": "write_file",
    "path": "/workspace/output.txt"
  }
}
```

### Invalid: AgentActionPayload without ctx_id

```json
{
  "session_id": "sess_123",
  "action_type": "tool_call",
  "payload": {
    "tool": "write_file"
  }
}
```

Reason:
- `ctx_id` is required for trusted processing
- Missing CTX-ID must be treated as `UNTRUSTED`

### Valid: SubprocessInvocation

```json
{
  "args": ["pytest", "../tests/", "-v", "--tb=short"],
  "shell": false
}
```

### Invalid: SubprocessInvocation using shell=True

```json
{
  "args": ["pytest ../tests/ -v --tb=short"],
  "shell": true
}
```

Reason:
- `shell=True` is forbidden

### Valid: WritePathValidationRequest

```json
{
  "path": "/workspace/output.txt"
}
```

Constraint:
- Must be validated by `path_security.validate_write_path()` before write

### Valid: InjectionScanRequest

```json
{
  "document_chunks": [
    "Chunk 1",
    "Chunk 2"
  ]
}
```

Constraint:
- All chunks must pass injection scanning before prompt inclusion

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

Selection rules:

- `"swift"` -> `SWIFT_GENERATION_SYSTEM`
- `"swift"` + UI keywords -> optional `SWIFT_UI_ADDENDUM`
- `"python"` -> `GENERATION_SYSTEM`

### Enforcement Pipeline

Required integration sequence for any agent action:

1. Receive `AgentActionPayload`
2. Validate `ctx_id` first using TrustLock public key backed CTX-ID validation
3. Reject immediately on CTX-ID failure
4. Evaluate VTZ policy before execution
5. If denied, create `VTZEnforcementDecision` with `verdict=block`
6. Emit `TrustFlowEvent` synchronously
7. If TrustFlow emission fails, log and surface at WARN level

### File System Writes

Before any disk write:

1. Construct `WritePathValidationRequest`
2. Call `path_security.validate_write_path()`
3. Only write on successful validation

### Prompt Construction

Before including external document content in prompts:

1. Construct `InjectionScanRequest`
2. Scan all `document_chunks`
3. Include approved content only in USER prompt context
4. Never place external document content in SYSTEM prompt

### Testing / CI

Canonical pre-change test execution:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Required ecosystem constraints:

- `pytest`
- `ruff`
- `mypy`
- `pyyaml` in `requirements.txt`
- Coverage `>= 85%` for new modules