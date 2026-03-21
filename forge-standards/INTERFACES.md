# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the required wire-visible structures and behavioral interface contracts for the `ConsensusDevAgent` subsystem based strictly on the provided TRD and standards excerpts.

Where the source defines required fields or sequencing but does not provide a concrete transport schema, this document records the contract exactly and does not invent unspecified fields.

---

### 1. Backend Startup Sequence Interface

This is a required process-level interface contract.

#### 1.1 Startup order

The backend **MUST** execute startup in exactly this order:

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC (timeout: 30s)`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background (async)`
8. `Send ready message via XPC (includes agent_version, capabilities)`
9. `Enter CommandRouter event loop`

#### 1.2 Stdout startup line

Exact required format:

```text
FORGE_AGENT_LISTENING:{socket_path}
```

##### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | Yes | Non-empty filesystem socket path |

##### Constraints

- Prefix **MUST** be exactly `FORGE_AGENT_LISTENING:`
- Output target **MUST** be `stdout`
- Emission occurs after XPC server is listening
- Swift reads this value

---

### 2. XPC Credential Wait Contract

#### 2.1 Credential wait

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `timeout` | integer | Yes | Exact value: `30` seconds |

##### Constraints

- Backend **MUST** wait for credentials via XPC
- Wait timeout **MUST** be `30s`
- Steps 5 and 6 are non-fatal on credential errors
- On credential errors, backend **MUST** emit `auth_error` XPC card and continue in degraded state

---

### 3. Ready Message via XPC

The startup sequence requires a ready message sent via XPC.

#### 3.1 Ready message payload

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | Yes | Must be included in ready message |
| `capabilities` | array | Yes | Must be included in ready message |

##### Constraints

- Message is sent at startup step 8
- Message is sent via XPC
- It occurs after `DocumentStore` background loading begins
- It occurs before entering `CommandRouter` event loop

##### Unspecified fields

No additional field names are defined in the provided source.

---

### 4. Auth Error XPC Card

The startup contract specifies an `auth_error` XPC card.

#### 4.1 Auth error card

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | string | Implicit | Exact value: `auth_error` |

##### Constraints

- Must be emitted on credential errors during:
  - `Initialize GitHubTool with token`
  - `Initialize ConsensusEngine with API keys`
- Backend continues in degraded state after emission

##### Unspecified fields

No additional card payload fields are defined in the provided source.

---

### 5. TrustFlow Event

Every action outcome must emit a TrustFlow event.

#### 5.1 TrustFlow event payload

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | Yes | Globally unique; CSPRNG-generated; not sequential |
| `session_id` | string | Yes | Required |
| `ctx_id` | string | Yes | Required |
| `ts` | number | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | Yes | Required |
| `payload_hash` | string | Yes | SHA-256 of the serialized action payload |

##### Constraints

- Every TrustFlow event **MUST** include all fields above
- `event_id` **MUST** be globally unique
- `event_id` generation **MUST** use CSPRNG
- Sequential IDs are forbidden
- `ts` **MUST** be UTC Unix timestamp with millisecond precision
- `payload_hash` **MUST** be SHA-256 of the serialized action payload
- Emission **MUST** be synchronous in the enforcement path
- Async buffering is not permitted
- Failed emission is a `WARN-level audit event`, not a silent skip

---

### 6. VTZEnforcementDecision Record

A VTZ policy denial must produce a `VTZEnforcementDecision` record.

#### 6.1 VTZEnforcementDecision payload

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | Yes | Exact value on denial: `block` |

##### Constraints

- Every action **MUST** be checked against VTZ policy before execution
- VTZ policy denial **MUST** produce a `VTZEnforcementDecision` record
- On denial, `verdict` **MUST** equal `block`

##### Unspecified fields

No other `VTZEnforcementDecision` fields are defined in the provided source.

---

### 7. CTX-ID Token

The source defines lifecycle and validation constraints for CTX-ID tokens.

#### 7.1 CTX-ID token representation

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | Yes | Required on TrustFlow event and validation path |

##### Constraints

- CTX-ID tokens are **IMMUTABLE** once issued
- No field modification is allowed after issuance
- CTX-ID rotation creates a new token
- Old token is invalidated immediately upon rotation
- Expired CTX-ID **MUST** be rejected
- Clock skew tolerance is defined per deployment
- CTX-ID **MUST** be validated against TrustLock public key
- Software-only validation is rejected
- Missing CTX-ID **MUST** be treated as `UNTRUSTED`
- Identity must never be inferred from context when CTX-ID is missing

##### Unspecified fields

No token-internal field names are defined in the provided source.

---

### 8. Action Payload Hash Input

The `payload_hash` field is defined as SHA-256 of the serialized action payload.

#### 8.1 Serialized action payload

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `serialized_action_payload` | bytes or string | Yes | Exact serialized input to SHA-256 |

##### Constraints

- `payload_hash` is computed over the serialized action payload
- Serialization format is not specified in the provided source
- Implementations must ensure deterministic serialization for correct hashing

---

### 9. Command Processing Entry Point Contract

Every entry point that processes an agent action must enforce the CAL contract.

#### 9.1 Agent action processing sequence

| Step | Requirement |
|---|---|
| 1 | Call CTX-ID validation first |
| 2 | On CTX-ID validation failure, reject immediately |
| 3 | Check every action against VTZ policy before execution |
| 4 | On VTZ denial, produce `VTZEnforcementDecision` with `verdict=block` |
| 5 | Emit TrustFlow event for every action outcome: allow, restrict, block |
| 6 | If TrustFlow emission fails, do not silently continue; log and surface failure |

##### Constraints

- No partial processing is allowed before CTX-ID validation
- VTZ policy check must occur before execution
- All outcomes (`allow`, `restrict`, `block`) require TrustFlow emission

---

### 10. GitHubTool Integration

#### 10.1 GitHub operations interface

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `token` | string | Yes for authenticated initialization | Used to initialize `GitHubTool` |

##### Constraints

- All GitHub operations go through `GitHubTool`
- Pipeline code must never call the GitHub API directly
- `GitHubTool` initialization occurs at startup step 5
- Credential error at this step is non-fatal
- On credential error, emit `auth_error` XPC card and continue in degraded state

---

### 11. ConsensusEngine Integration

#### 11.1 ConsensusEngine initialization

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `api_keys` | object or collection | Yes for authenticated initialization | Used to initialize `ConsensusEngine` |

##### Constraints

- `ConsensusEngine` initialization occurs at startup step 6
- Credential error at this step is non-fatal
- On credential error, emit `auth_error` XPC card and continue in degraded state

##### Unspecified fields

The source does not define API key field names.

---

### 12. DocumentStore Loading Interface

#### 12.1 Background loading contract

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `async` | boolean | Yes | Exact behavior: background loading is async |

##### Constraints

- `DocumentStore` loading starts at startup step 7
- It is always async
- The app remains responsive while embeddings load

---

### 13. External Document Chunk Handling

#### 13.1 Loaded document chunk processing

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `document_chunk` | string or bytes | Yes | Must pass injection scanning before inclusion in any LLM prompt |

##### Constraints

- All loaded document chunks must pass injection scanning before being included in any LLM prompt
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt

---

### 14. File Write Path Validation Interface

#### 14.1 Write path validation

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `path` | string | Yes | Must pass `path_security.validate_write_path()` before any write |

##### Constraints

- All file paths written to disk must pass `path_security.validate_write_path()` before any write

---

### 15. SECURITY_REFUSAL Handling Interface

#### 15.1 LLM output handling

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `output` | string | Yes | If it contains `SECURITY_REFUSAL`, do not retry |

##### Constraints

- When `SECURITY_REFUSAL` appears in LLM output: stop, gate, log
- Never retry to bypass
- The following behavior is explicitly forbidden:

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)  # WRONG — do not retry
```

---

## Enums and Constants

### 1. Fixed string constants

| Name | Type | Exact Value |
|---|---|---|
| Startup stdout prefix | string | `FORGE_AGENT_LISTENING:` |
| Auth error card type | string | `auth_error` |
| VTZ denial verdict | string | `block` |
| Missing CTX-ID trust state | string | `UNTRUSTED` |
| Refusal sentinel | string | `SECURITY_REFUSAL` |

### 2. Action outcomes

These values are named explicitly in the source as outcomes requiring TrustFlow emission.

| Enum | Values |
|---|---|
| ActionOutcome | `allow`, `restrict`, `block` |

### 3. Prompt roles

| Enum | Values | Constraints |
|---|---|---|
| PromptRole | `USER`, `SYSTEM` | External document context goes in `USER`, never `SYSTEM` |

### 4. Log severity

| Enum | Values | Constraints |
|---|---|---|
| LogLevel | `WARN-level audit event` | Used when TrustFlow emission fails |

### 5. Time constants

| Name | Type | Exact Value |
|---|---|---|
| Credential wait timeout | duration | `30s` |

---

## Validation Rules

### 1. CAL enforcement

- Every entry point that processes an agent action **MUST** call CTX-ID validation **FIRST**
- CTX-ID validation failure **MUST** result in immediate rejection
- No partial processing is allowed before validation
- Every action **MUST** be checked against VTZ policy **BEFORE** execution
- VTZ policy denial **MUST** produce a `VTZEnforcementDecision` record with `verdict=block`
- Every action outcome (`allow`, `restrict`, `block`) **MUST** emit a TrustFlow event
- TrustFlow emission failure **MUST NOT** silently continue
- Failure must be logged and surfaced

### 2. TrustFlow event validation

- `event_id` required
- `session_id` required
- `ctx_id` required
- `ts` required
- `event_type` required
- `payload_hash` required
- `event_id` must be globally unique
- `event_id` must be CSPRNG-generated
- `event_id` must not be sequential
- `ts` must be UTC Unix timestamp with millisecond precision
- `payload_hash` must equal SHA-256 of serialized action payload
- Emission must be synchronous in enforcement path
- Async buffering is forbidden

### 3. CTX-ID validation

- CTX-ID tokens are immutable once issued
- Rotation creates a new token and invalidates the old one immediately
- Expired CTX-ID must be rejected
- Validation must be against TrustLock public key
- Software-only validation is rejected
- Missing CTX-ID must be treated as `UNTRUSTED`
- Identity must never be inferred from context without CTX-ID

### 4. VTZ enforcement

- Every agent session is bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit authorization is denied
- VTZ boundaries are structural, not advisory
- Enforcement cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session

### 5. Startup validation

- Startup order is mandatory and must not change
- Socket must be listening before stdout line is printed
- Ready message must include `agent_version` and `capabilities`
- `DocumentStore` loading must be async
- App must remain responsive while embeddings load

### 6. Security validation

- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Never use `shell=True` in subprocess calls
- Never call `eval()` or `exec()` on generated or external content
- Never log HTTP response bodies
- Log status codes and error types only
- All file write paths must pass `path_security.validate_write_path()`
- All loaded document chunks must pass injection scanning before inclusion in LLM prompts
- External document context must be placed in `USER` prompt, never `SYSTEM`
- On `SECURITY_REFUSAL`: stop, gate, log; never retry

### 7. Python implementation contract

- Python version must be `3.12`
- Type annotations required on every function
- Backend must use `async/await` throughout
- No blocking calls on the event loop
- Dataclasses required for all structured data
- Tests use `pytest`
- Tests live in `tests/` and mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage must be `≥ 85%` on all new modules

---

## Wire Format Examples

Only fields explicitly defined in source are included below.

### 1. Valid startup stdout line

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### 2. Invalid startup stdout line

Wrong prefix:

```text
LISTENING:/tmp/forge-agent.sock
```

Wrong because required exact prefix is `FORGE_AGENT_LISTENING:`.

---

### 3. Valid ready message payload

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus"]
}
```

Why valid:
- Includes `agent_version`
- Includes `capabilities`

### 4. Invalid ready message payload

Missing required field:

```json
{
  "agent_version": "1.0.0"
}
```

Why invalid:
- Missing `capabilities`

---

### 5. Valid auth error XPC card

```json
{
  "type": "auth_error"
}
```

### 6. Invalid auth error XPC card

```json
{
  "type": "authentication_error"
}
```

Why invalid:
- Exact type defined is `auth_error`

---

### 7. Valid TrustFlow event

```json
{
  "event_id": "4f5f1b9a-90d0-4d6b-8b8f-2dc1e9ec8e11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961b2a29f31c6b9a4c9b7e6e2"
}
```

Why valid:
- Includes all required fields
- `ts` shown as Unix timestamp in milliseconds
- `payload_hash` shown as SHA-256 hex string

### 8. Invalid TrustFlow event: missing field

```json
{
  "event_id": "4f5f1b9a-90d0-4d6b-8b8f-2dc1e9ec8e11",
  "session_id": "sess_123",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961b2a29f31c6b9a4c9b7e6e2"
}
```

Why invalid:
- Missing required `ctx_id`

### 9. Invalid TrustFlow event: weak event_id pattern

```json
{
  "event_id": "42",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961b2a29f31c6b9a4c9b7e6e2"
}
```

Why invalid:
- `event_id` must be globally unique and CSPRNG-generated, not sequential

---

### 10. Valid VTZEnforcementDecision denial record

```json
{
  "verdict": "block"
}
```

### 11. Invalid VTZEnforcementDecision denial record

```json
{
  "verdict": "deny"
}
```

Why invalid:
- Required exact denial verdict is `block`

---

### 12. Invalid SECURITY_REFUSAL handling example

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Why invalid:
- Retry is forbidden when `SECURITY_REFUSAL` appears

---

## Integration Points

### 1. Swift ↔ Backend

#### Interface
- Backend prints `FORGE_AGENT_LISTENING:{socket_path}` to stdout
- Swift reads this line
- Credentials are delivered via XPC
- Backend sends ready message via XPC
- Backend may send `auth_error` XPC card

#### Constraints
- Only Swift reads Keychain
- Only Swift delivers backend credentials via XPC
- Python reads nothing from Keychain

Explicitly forbidden pattern:

```swift
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
```

---

### 2. Backend ↔ GitHubTool

#### Interface
- Backend initializes `GitHubTool` with token
- All GitHub operations go through `GitHubTool`

#### Constraints
- Never call the GitHub API directly from pipeline code
- Initialization failure due to credentials is non-fatal
- Must emit `auth_error` XPC card and continue in degraded state

---

### 3. Backend ↔ ConsensusEngine

#### Interface
- Backend initializes `ConsensusEngine` with API keys

#### Constraints
- Initialization failure due to credentials is non-fatal
- Must emit `auth_error` XPC card and continue in degraded state

---

### 4. Backend ↔ DocumentStore

#### Interface
- Backend starts `DocumentStore` loading in background

#### Constraints
- Loading is async
- App remains responsive while embeddings load

---

### 5. Agent Action Entry Points ↔ CAL / CTX-ID / VTZ / TrustFlow

#### Interface
Every entry point that processes an agent action integrates with:
- CTX-ID validation
- VTZ policy enforcement
- TrustFlow event emission

#### Required order
1. CTX-ID validation
2. VTZ policy check
3. Execution if allowed
4. TrustFlow emission for outcome

---

### 6. Backend ↔ Path Security

#### Interface
- All file writes must call `path_security.validate_write_path()` before write

---

### 7. Backend ↔ LLM Prompt Construction

#### Interface
- Loaded document chunks are scanned for injection before inclusion
- External document context is inserted into `USER` prompt only

#### Constraints
- Never place external document context in `SYSTEM` prompt
- On `SECURITY_REFUSAL`, stop, gate, log; never retry

---

### 8. Testing and Quality Tooling

#### Interface requirements
- Run existing tests before making changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```

#### Additional conformance requirements
- `pytest`
- `ruff`
- `mypy`
- coverage `≥ 85%` on new modules

---

## Non-Conformant / Forbidden Patterns

These are explicitly forbidden by contract.

### 1. Ignoring SECURITY_REFUSAL

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)  # WRONG — do not retry
```

### 2. Swift force unwrap

```swift
let value = optional!
```

### 3. LLM API call from Swift

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

### 4. Backend credential read from Keychain

```swift
let token = KeychainKit.read("github_token")
```

### 5. shell=True usage

Forbidden in subprocess calls.

### 6. eval/exec on generated or external content

Forbidden.

### 7. Logging HTTP response bodies

Forbidden. Log status codes and error types only.

---

## Summary of Required Explicit Fields

### TrustFlow event
- `event_id: string`
- `session_id: string`
- `ctx_id: string`
- `ts: number`
- `event_type: string`
- `payload_hash: string`

### Ready message
- `agent_version: string`
- `capabilities: array`

### Auth error card
- `type: string` with exact value `auth_error`

### VTZEnforcementDecision
- `verdict: string` with exact value `block` on denial

### Startup stdout line
- `FORGE_AGENT_LISTENING:{socket_path}` where `socket_path` is a non-empty string