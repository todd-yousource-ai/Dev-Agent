# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements that apply to the `ConsensusDevAgent` subsystem based on the provided TRD excerpts and Forge interface contracts.

Where the source defines exact field names or values, they are reproduced exactly.

---

### 1. TrustFlow Event

Required by the **TrustFlow Emission Contract**.

#### Type
Structured record / object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | Yes | MUST be globally unique; MUST be generated using CSPRNG; MUST NOT be sequential |
| `session_id` | string | Yes | Session identifier |
| `ctx_id` | string | Yes | CTX-ID token identifier; MUST refer to a validated CTX-ID |
| `ts` | number | Yes | MUST be UTC Unix timestamp with millisecond precision |
| `event_type` | string | Yes | Event type discriminator |
| `payload_hash` | string | Yes | MUST be SHA-256 of the serialized action payload |

#### Behavioral constraints
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be treated as a WARN-level audit event.
- Failed emission MUST NOT be silently skipped.
- TrustFlow emission failure MUST NOT silently continue; it must be logged and surfaced.

---

### 2. VTZEnforcementDecision

Required by the **CAL Enforcement Contract**.

#### Type
Structured record / object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | Yes | For VTZ policy denial, MUST be exactly `block` |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

> Note: No additional fields are defined in the provided source excerpt.

---

### 3. XPC Ready Message

Required by the **Backend Startup Sequence**.

#### Type
Structured message / object sent via XPC

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | Yes | Included in ready message |
| `capabilities` | array | Yes | Included in ready message |

#### Behavioral constraints
- Must be sent at startup step 8.
- Must be sent after:
  1. logger initialization
  2. XPC server start
  3. stdout listen announcement
  4. credential wait
  5. `GitHubTool` initialization
  6. `ConsensusEngine` initialization
  7. background `DocumentStore` loading start

---

### 4. XPC Auth Error Card

Required by the **Backend Startup Sequence**.

#### Type
Structured message / object sent via XPC

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `auth_error` | object or string | Yes | Emitted on credential errors during startup steps 5-6 |

#### Behavioral constraints
- Credential errors in steps 5-6 are non-fatal.
- On such errors, subsystem MUST emit `auth_error` XPC card.
- Subsystem MUST continue in degraded state.

> Note: Internal shape of the `auth_error` payload is not defined in the provided source.

---

### 5. Backend Listening Announcement

Required by the **Backend Startup Sequence**.

#### Type
Stdout line

#### Exact wire format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Fields

| Segment | Type | Required | Constraints |
|---|---|---:|---|
| `FORGE_AGENT_LISTENING:` | string literal | Yes | MUST appear exactly as shown |
| `{socket_path}` | string | Yes | XPC socket path |

#### Behavioral constraints
- Must be printed to stdout at startup step 3.
- Swift reads this value.
- Order is mandatory.

---

### 6. SECURITY_REFUSAL Output Marker

#### Type
String sentinel value

#### Exact value
```text
SECURITY_REFUSAL
```

#### Behavioral constraints
- When output contains `SECURITY_REFUSAL`: stop, gate, log.
- MUST NOT retry to bypass.
- Retrying a different LLM generation path after `SECURITY_REFUSAL` is forbidden.

---

### 7. Action Payload

Implicitly required by TrustFlow hashing and CAL enforcement.

#### Type
Structured payload / serialized action object

#### Required processing constraints
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted on CTX-ID validation failure.
- Every action MUST be checked against VTZ policy BEFORE execution.
- The serialized action payload MUST be hashed using SHA-256 and recorded as `payload_hash` in the emitted TrustFlow event.

> Note: The field-level schema of the action payload is not defined in the provided source excerpts.

---

### 8. CTX-ID Token

Defined by the **CTX-ID Contract**.

#### Type
Token / opaque string or structured token identifier

#### Fields
No internal wire fields are defined in the provided source.

#### Behavioral constraints
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is allowed after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately on rotation.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from context when CTX-ID is missing.

---

### 9. VTZ Binding

Defined by the **VTZ Enforcement Contract**.

#### Type
Session-to-zone binding invariant

#### Fields
No wire fields defined in the provided source.

#### Behavioral constraints
- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

### 10. Document Chunk Included in LLM Prompt

#### Type
Loaded document chunk / prompt context unit

#### Fields
No wire fields defined in the provided source.

#### Required processing constraints
- All loaded document chunks MUST pass injection scanning before being included in any LLM prompt.
- Context from external documents MUST go in the USER prompt.
- Context from external documents MUST NEVER go in the SYSTEM prompt.

---

### 11. File Write Path Input

#### Type
Filesystem path string

#### Fields
No object fields defined.

#### Required processing constraints
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

---

### 12. Credentials Payload Delivered via XPC

#### Type
Structured credentials message via XPC

#### Fields
Not defined in the provided source.

#### Behavioral constraints
- Backend waits for credentials via XPC with timeout `30s`.
- Only Swift reads Keychain.
- Python backend reads nothing from Keychain.
- Swift may deliver credentials via XPC.
- Backend startup continues in degraded state on credential errors for steps 5-6.

---

## Enums and Constants

### String Literals

| Name | Exact Value | Notes |
|---|---|---|
| Security refusal marker | `SECURITY_REFUSAL` | Must trigger stop/gate/log behavior |
| Listening prefix | `FORGE_AGENT_LISTENING:` | Stdout protocol prefix |
| VTZ denial verdict | `block` | Required in `VTZEnforcementDecision` on denial |
| Missing CTX-ID trust state | `UNTRUSTED` | Must be used when CTX-ID is missing |

---

### Action Outcome Values

Required by TrustFlow emission requirements.

| Value |
|---|
| `allow` |
| `restrict` |
| `block` |

These are the action outcomes for which TrustFlow events MUST be emitted.

---

### Time and Timeout Constants

| Name | Value | Notes |
|---|---|---|
| Credential wait timeout | `30s` | Startup step 4 |
| Timestamp precision | `millisecond` | `ts` precision requirement |
| Timestamp base | `UTC Unix timestamp` | `ts` requirement |

---

### Hash / Crypto Constants

| Name | Exact Value | Notes |
|---|---|---|
| Payload hash algorithm | `SHA-256` | For `payload_hash` |
| event_id randomness source | `CSPRNG` | Must not be sequential |
| CTX-ID validation key material | `TrustLock public key` | Required validation basis |

---

### Mandatory Startup Order

Order is exact and mandatory:

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC (timeout: 30s)`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background (async)`
8. `Send ready message via XPC (includes agent_version, capabilities)`
9. `Enter CommandRouter event loop`

---

### Technology / Implementation Constraints

These are contract-level requirements affecting interface conformance.

| Item | Required Value |
|---|---|
| Python version | `Python 3.12` |
| Function typing | `Type annotations on every function` |
| Backend async model | `async/await throughout the backend` |
| Structured data model | `Dataclasses for all structured data` |
| Test framework | `pytest` |
| Linting | `ruff` |
| Type checking | `mypy` |
| New module coverage | `≥ 85%` |

---

## Validation Rules

### CAL Enforcement Validation

1. Every entry point that processes an agent action MUST validate CTX-ID first.
2. If CTX-ID validation fails:
   - reject immediately
   - do not partially process
3. Every action MUST be checked against VTZ policy before execution.
4. If VTZ denies:
   - create `VTZEnforcementDecision`
   - set `verdict` to exactly `block`
5. Every action outcome MUST emit a TrustFlow event.
6. If TrustFlow emission fails:
   - log the failure
   - surface the failure
   - do not silently continue

---

### TrustFlow Event Validation

A TrustFlow event is valid only if:
- `event_id` is present
- `session_id` is present
- `ctx_id` is present
- `ts` is present
- `event_type` is present
- `payload_hash` is present
- `event_id` is globally unique
- `event_id` is CSPRNG-based
- `event_id` is not sequential
- `ts` is a UTC Unix timestamp
- `ts` has millisecond precision
- `payload_hash` is SHA-256 of the serialized action payload

---

### CTX-ID Validation

A CTX-ID is valid for processing only if:
- it is present, otherwise trust state is `UNTRUSTED`
- it is not expired
- it validates against the TrustLock public key
- it has not been invalidated by rotation

A CTX-ID is invalid if:
- missing
- expired
- modified after issuance
- validated only by software without TrustLock public key validation
- replaced by inferred identity from context

---

### VTZ Validation

A VTZ relationship is valid only if:
- the session is bound to exactly one VTZ at CTX-ID issuance
- any cross-VTZ tool call has explicit policy authorization

Invalid conditions:
- implicit cross-VTZ authorization
- mid-session VTZ policy change affecting an already-issued CTX-ID
- any application-code bypass of VTZ boundary enforcement

---

### Startup Sequence Validation

Startup is conformant only if the sequence order is exactly preserved.

Invalid conditions include:
- printing `FORGE_AGENT_LISTENING:{socket_path}` before XPC server starts
- sending ready message before background `DocumentStore` loading starts
- entering `CommandRouter` event loop before sending ready message
- failing to wait for credentials via XPC before initializing credentialed components

---

### Security Validation

#### Forbidden behaviors
- Hardcoded credentials, API keys, tokens, or secrets as string literals
- `shell=True` in subprocess calls
- `eval()` on generated or external content
- `exec()` on generated or external content
- Logging HTTP response bodies
- Calling GitHub API directly from pipeline code
- LLM retry to bypass `SECURITY_REFUSAL`
- Swift force unwrap:
  ```swift
  let value = optional!
  ```
- LLM API call from Swift:
  ```swift
  let client = AnthropicClient(apiKey: keychainValue)
  ```
- Backend Keychain read from Python:
  ```swift
  let token = KeychainKit.read("github_token")
  ```

#### Required behaviors
- All GitHub operations go through `GitHubTool`
- All file write paths must pass `path_security.validate_write_path()`
- All loaded document chunks must pass injection scanning
- External document context must be placed in USER prompt, never SYSTEM prompt
- On `SECURITY_REFUSAL`: stop, gate, log; never retry

---

## Wire Format Examples

### 1. Valid TrustFlow Event

```json
{
  "event_id": "8d4f1d72-9a4f-4d5d-91b7-6d9ff4d7e2aa",
  "session_id": "sess_01HZZZZZZZZZZZZZZZZZZZZ",
  "ctx_id": "ctx_01HYYYYYYYYYYYYYYYYYYYY",
  "ts": 1731605123123,
  "event_type": "action_execution",
  "payload_hash": "3b7e6d1c6d9d8b2efc4b9a2d14f6de7b1d9c3b8d7f5e2a1c6f4b9d8e7a6c5b4"
}
```

Why valid:
- includes all required fields
- `ts` is millisecond Unix time
- `payload_hash` is formatted as a SHA-256 hex string
- `event_id` is non-sequential in representation

---

### 2. Invalid TrustFlow Event: missing required field

```json
{
  "event_id": "1",
  "session_id": "sess_123",
  "ts": 1731605123,
  "event_type": "action_execution",
  "payload_hash": "abc"
}
```

Why invalid:
- missing `ctx_id`
- `event_id` appears sequential / non-CSPRNG
- `ts` is not clearly millisecond precision
- `payload_hash` is not a valid SHA-256 value

---

### 3. Valid VTZEnforcementDecision

```json
{
  "verdict": "block"
}
```

Why valid:
- VTZ denial requires exact `verdict=block`

---

### 4. Invalid VTZEnforcementDecision

```json
{
  "verdict": "deny"
}
```

Why invalid:
- source requires exact value `block` for VTZ denial

---

### 5. Valid stdout listening announcement

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

Why valid:
- exact required prefix
- includes socket path

---

### 6. Invalid stdout listening announcement

```text
LISTENING:/tmp/forge-agent.sock
```

Why invalid:
- prefix must be exactly `FORGE_AGENT_LISTENING:`

---

### 7. Valid ready message via XPC

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

Why valid:
- includes both required fields defined by source

---

### 8. Invalid ready message via XPC

```json
{
  "version": "1.0.0"
}
```

Why invalid:
- missing required `agent_version`
- missing required `capabilities`
- `version` is not the contract field name

---

### 9. SECURITY_REFUSAL handling example

#### Valid behavior
Input/output marker:
```text
SECURITY_REFUSAL
```

Required system action:
- stop
- gate
- log
- do not retry

#### Invalid behavior
```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Why invalid:
- explicitly forbidden bypass retry

---

## Integration Points

### 1. XPC Boundary
ConsensusDevAgent integrates with Swift over XPC.

#### Required interactions
- Swift reads stdout line:
  - `FORGE_AGENT_LISTENING:{socket_path}`
- Backend waits for credentials via XPC
- Backend sends:
  - ready message including `agent_version`, `capabilities`
  - `auth_error` XPC card on non-fatal credential errors

#### Constraints
- Swift is the only side that reads Keychain
- Python backend reads nothing from Keychain
- Swift may deliver credentials via XPC

---

### 2. GitHub Integration

#### Required component
- `GitHubTool`

#### Constraint
- All GitHub operations go through `GitHubTool`
- Never call the GitHub API directly from pipeline code

---

### 3. Consensus Engine Integration

#### Required component
- `ConsensusEngine`

#### Startup dependency
- Initialized at startup step 6 with API keys

---

### 4. Document Store Integration

#### Required component
- `DocumentStore`

#### Startup dependency
- Loading begins at startup step 7
- Loading is in background
- Loading is async
- App must remain responsive while embeddings load

#### Prompting constraints
- Loaded chunks must pass injection scanning
- External document context goes into USER prompt only

---

### 5. Command Routing Integration

#### Required component
- `CommandRouter`

#### Startup dependency
- Event loop begins only at startup step 9
- Must occur after ready message emission

---

### 6. Trust / Policy Enforcement Integration

ConsensusDevAgent must conform to Forge enforcement contracts.

#### Required sequence for any agent action
1. Validate `ctx_id`
2. Reject immediately if invalid
3. Evaluate VTZ policy
4. If denied, emit `VTZEnforcementDecision` with `verdict=block`
5. Emit TrustFlow event for outcome
6. Execute only if allowed by policy

---

### 7. Filesystem Integration

#### Constraint
- Any path written to disk must be validated with:
  - `path_security.validate_write_path()`

---

### 8. Testing and Conformance Integration

Before code changes:
```bash
cd src && pytest ../tests/ -v --tb=short
```

Required quality gates:
- `pytest`
- `ruff`
- `mypy`
- coverage `≥ 85%` on all new modules

---

## Notes on Undefined Fields

The following interfaces are referenced but not fully field-specified in the provided source excerpts:
- action payload schema
- internal CTX-ID token fields
- `auth_error` payload schema
- credentials payload schema over XPC
- `capabilities` element schema
- `event_type` enum values

For these, only the explicitly provided field names, literals, and constraints in source are normative here.