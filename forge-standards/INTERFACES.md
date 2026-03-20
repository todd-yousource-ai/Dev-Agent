# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the required wire-level and API-facing contracts for the ConsensusDevAgent subsystem based on the provided TRD excerpts and Forge interface standards.

Where the TRD text specifies exact field names or values, they are reproduced exactly.

---

### 1. Backend Startup Sequence Interfaces

The backend startup sequence is mandatory and ordered exactly as follows:

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background (async)`
8. `Send ready message via XPC`
9. `Enter CommandRouter event loop`

#### 1.1 Stdout Listening Announcement

Printed to stdout exactly once when the XPC server is listening.

**Format**
```text
FORGE_AGENT_LISTENING:{socket_path}
```

**Fields**
- `socket_path`: string, required
  - Filesystem path to the XPC socket
  - Inserted directly after the literal `FORGE_AGENT_LISTENING:`

**Constraints**
- Prefix must be exactly `FORGE_AGENT_LISTENING:`
- Must be emitted after XPC server starts listening
- Must be emitted before waiting for credentials

---

### 2. XPC Credential Delivery Interface

The backend waits for credentials via XPC with a timeout.

**Constraints**
- Wait timeout: `30s`
- Credentials are delivered via XPC only
- Python backend must not read credentials from Keychain
- Only Swift reads Keychain, only to deliver via XPC

#### 2.1 Credential Payload

The exact XPC credential message schema is not fully specified in the provided excerpts. The following fields are explicitly implied by startup requirements:

##### CredentialsInput
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `token` | string | conditional | Used to initialize `GitHubTool` |
| `api_keys` | object | conditional | Used to initialize `ConsensusEngine` |

**Constraints**
- `token` must be supplied via XPC if GitHub functionality is to be initialized
- `api_keys` must be supplied via XPC if `ConsensusEngine` is to be initialized
- Missing or invalid credentials for steps 5 or 6 are non-fatal
- On credential errors, backend must emit `auth_error` XPC card and continue in degraded state

#### 2.2 Ready Message

Sent via XPC after initialization steps complete.

##### ReadyMessage
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Included in ready message |
| `capabilities` | array | yes | Included in ready message |

**Constraints**
- Must be sent after:
  - XPC server startup
  - credential wait
  - attempted `GitHubTool` initialization
  - attempted `ConsensusEngine` initialization
  - `DocumentStore` background loading start
- Must be sent even if running in degraded state due to auth errors

#### 2.3 Auth Error Card

##### AuthErrorCard
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | string | implied | Must identify the card as `auth_error` |

**Constraints**
- Must be emitted via XPC when step 5 or 6 encounters credential errors
- Backend continues operating in degraded state

---

### 3. TrustFlow Event Contract

Every action outcome must emit a TrustFlow event.

##### TrustFlowEvent
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | Must be globally unique; CSPRNG, not sequential |
| `session_id` | string | yes | Required on every event |
| `ctx_id` | string | yes | Required on every event |
| `ts` | number | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Required on every event |
| `payload_hash` | string | yes | Must be SHA-256 of the serialized action payload |

**Constraints**
- Emission must be synchronous in the enforcement path
- Async buffering is not permitted
- Failed emission is a WARN-level audit event
- Failed emission must not be silently skipped
- Every action outcome must emit a TrustFlow event for:
  - allow
  - restrict
  - block

---

### 4. VTZ Enforcement Decision Record

A VTZ policy denial must produce a `VTZEnforcementDecision` record.

##### VTZEnforcementDecision
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | Must be exactly `block` on VTZ policy denial |

**Constraints**
- Produced before execution when VTZ policy denies the action
- Policy check must occur before execution
- Denial must not be implicit or omitted

---

### 5. CTX-ID Token Interface

A CTX-ID token is required for trusted processing.

##### CTXIDToken
The provided excerpts define behavior and validation constraints but do not define a complete field schema.

**Behavioral contract**
- CTX-ID tokens are immutable once issued
- Rotation creates a new token
- Old token is invalidated immediately on rotation
- Expired CTX-ID must be rejected
- Missing CTX-ID must be treated as `UNTRUSTED`
- CTX-ID must be validated against TrustLock public key
- Software-only validation is rejected

**Implied wire representation**
- `ctx_id`: string, required for trusted action processing and TrustFlow events

---

### 6. Action Processing Entry Point Contract

Every entry point that processes an agent action must enforce CAL and VTZ validation.

##### AgentActionPayload
The exact action payload schema is not specified in the provided excerpts. The enforcement path requirements are:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | conditional | Must be validated first; if missing, treated as `UNTRUSTED` |
| `session_id` | string | implied | Required for TrustFlow emission |
| `payload` | object | implied | Serialized form is hashed for `payload_hash` |

**Constraints**
- CTX-ID validation must occur first
- CTX-ID validation failure must cause immediate rejection
- No partial processing is allowed after CTX-ID validation failure
- VTZ policy check must occur before execution
- Every action outcome must emit TrustFlow

---

### 7. Python Structured Data Requirement

All structured data in the backend must use dataclasses.

**Constraints**
- Python version: `3.12`
- Type annotations required on every function
- Backend uses `async/await` throughout
- No blocking calls on the event loop

This is an implementation contract affecting all structured data types listed in this document.

---

### 8. File Write Path Validation Interface

All file paths written to disk must be validated before any write.

##### WritePathValidationCall
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `path` | string | yes | Must be passed to `path_security.validate_write_path()` before write |

**Constraints**
- No disk write may occur before validation
- Validation function name must be exactly `path_security.validate_write_path()`

---

### 9. Injection Scanning Interface

All loaded document chunks must be scanned before inclusion in an LLM prompt.

##### DocumentChunk
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `chunk` | string | yes | Must pass injection scanning before prompt inclusion |

**Constraints**
- Every loaded document chunk must pass injection scanning
- External document context must go in the `USER` prompt
- External document context must never go in the `SYSTEM` prompt

---

### 10. SECURITY_REFUSAL Handling Interface

`SECURITY_REFUSAL` is a terminal gated outcome.

##### SecurityRefusalOutput
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `output` | string | yes | If it contains `SECURITY_REFUSAL`, processing must stop |

**Constraints**
- When `SECURITY_REFUSAL` appears in output:
  - stop
  - gate
  - log
- Never retry to bypass
- Retrying with another LLM call is forbidden

---

### 11. GitHub Operations Integration Interface

All GitHub operations must go through `GitHubTool`.

##### GitHubOperationRequest
The exact request schema is not specified in the provided excerpts.

**Constraints**
- All GitHub operations go through `GitHubTool`
- Never call the GitHub API directly from pipeline code

---

## Enums and Constants

### String Constants

#### Startup
- `FORGE_AGENT_LISTENING:`
- `auth_error`

#### Security
- `SECURITY_REFUSAL`

#### Trust / Enforcement
- `block`
- `UNTRUSTED`

### Time Constants
- Credential wait timeout: `30s`

### Platform / Tooling Constants
- Python version: `3.12`

### Function / Type / Component Names
These names are part of the interface contract and must appear exactly as written:
- `GitHubTool`
- `ConsensusEngine`
- `DocumentStore`
- `CommandRouter`
- `VTZEnforcementDecision`
- `TrustFlow`
- `CTX-ID`
- `TrustLock`
- `path_security.validate_write_path()`

---

## Validation Rules

### 1. Startup Ordering Rules
- Startup order is mandatory and must not change
- `FORGE_AGENT_LISTENING:{socket_path}` must be printed after socket listen begins
- Credential wait occurs before `GitHubTool` and `ConsensusEngine` initialization
- `DocumentStore` loading must start in background asynchronously
- Ready message must include:
  - `agent_version`
  - `capabilities`

### 2. Credential Handling Rules
- Credentials must arrive via XPC
- Python must not read Keychain
- Swift alone may read Keychain, and only to deliver credentials via XPC
- Auth errors in steps 5 and 6 are non-fatal
- On auth error, emit `auth_error` XPC card and continue in degraded state

### 3. TrustFlow Rules
- Required fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- `event_id` must be globally unique
- `event_id` must be generated by CSPRNG
- `event_id` must not be sequential
- `ts` must be UTC Unix timestamp with millisecond precision
- `payload_hash` must be SHA-256 of the serialized action payload
- Emission must be synchronous in the enforcement path
- Async buffering is forbidden
- Emission failure must log and surface failure
- Emission failure must not silently continue

### 4. CTX-ID Rules
- Validation must occur first for every action-processing entry point
- Validation failure causes immediate rejection
- No partial processing after validation failure
- Missing CTX-ID maps to `UNTRUSTED`
- Expired CTX-ID must be rejected
- CTX-ID is immutable once issued
- Rotation creates a new token and invalidates the old token immediately
- Validation must use TrustLock public key
- Software-only validation is rejected

### 5. VTZ Rules
- Every action must be checked against VTZ policy before execution
- VTZ denial must produce `VTZEnforcementDecision` with `verdict=block`
- Every agent session is bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit cross-VTZ access is denied
- VTZ boundaries cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session

### 6. Security Rules
- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Never use `shell=True` in subprocess calls
- Never call `eval()` or `exec()` on generated or external content
- Never log HTTP response bodies
- Log status codes and error types only
- All file paths written to disk must pass `path_security.validate_write_path()` before write
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt
- On `SECURITY_REFUSAL`: stop, gate, log, never retry

### 7. Python Backend Rules
- Python `3.12`
- Type annotations on every function
- `async/await` throughout backend
- No blocking calls on event loop
- Dataclasses for all structured data
- Tests use `pytest`
- Linting uses `ruff`
- Type checking uses `mypy`
- Test coverage must be `≥ 85%` on all new modules

---

## Wire Format Examples

## Valid Payloads

### 1. Stdout Listening Announcement
```text
FORGE_AGENT_LISTENING:/tmp/consensusdevagent.sock
```

### 2. Ready Message
```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

### 3. TrustFlow Event
```json
{
  "event_id": "7f6bb7df-2b7d-4c9e-9f23-5a1d4f9a6a21",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

### 4. VTZ Enforcement Decision
```json
{
  "verdict": "block"
}
```

### 5. Auth Error Card
```json
{
  "type": "auth_error"
}
```

### 6. Agent Action Payload
```json
{
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "payload": {
    "action": "open_pr"
  }
}
```

---

## Invalid Payloads

### 1. Invalid Stdout Announcement
Wrong prefix:
```text
LISTENING:/tmp/consensusdevagent.sock
```

### 2. Invalid TrustFlow Event
Missing required fields:
```json
{
  "event_id": "123",
  "event_type": "allow"
}
```

Reason:
- Missing `session_id`
- Missing `ctx_id`
- Missing `ts`
- Missing `payload_hash`

### 3. Invalid VTZ Enforcement Decision
Wrong verdict:
```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ denial must produce `verdict=block`

### 4. Invalid Ready Message
Missing capabilities:
```json
{
  "agent_version": "1.0.0"
}
```

Reason:
- `capabilities` is required

### 5. Invalid Action Processing Request
Missing CTX-ID for trusted processing:
```json
{
  "session_id": "sess_123",
  "payload": {
    "action": "open_pr"
  }
}
```

Reason:
- Missing `ctx_id` must be treated as `UNTRUSTED`
- Trusted processing must not be inferred from context

### 6. Invalid SECURITY_REFUSAL Handling
Forbidden retry behavior:
```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Reason:
- Must stop, gate, and log
- Never retry to bypass

---

## Integration Points

### 1. Swift ↔ Backend XPC
- Swift reads Keychain
- Swift delivers credentials via XPC
- Backend waits up to `30s`
- Backend sends ready message with:
  - `agent_version`
  - `capabilities`
- Backend emits `auth_error` card on credential initialization failures

### 2. Backend ↔ GitHubTool
- `GitHubTool` is initialized with `token`
- All GitHub operations must go through `GitHubTool`
- Direct GitHub API calls from pipeline code are forbidden

### 3. Backend ↔ ConsensusEngine
- `ConsensusEngine` is initialized with `api_keys`

### 4. Backend ↔ DocumentStore
- `DocumentStore` loading starts in background asynchronously
- App must remain responsive while embeddings load

### 5. Backend ↔ CommandRouter
- After ready signaling, backend enters `CommandRouter` event loop

### 6. Enforcement Path ↔ TrustFlow
- Every action outcome emits a synchronous TrustFlow event
- Failures are WARN-level audit events
- Failures must be logged and surfaced

### 7. Enforcement Path ↔ VTZ
- VTZ policy check occurs before execution
- Denials produce `VTZEnforcementDecision` with `verdict=block`

### 8. Enforcement Path ↔ CTX-ID Validation
- CTX-ID validation is always first
- Failure causes immediate rejection
- Missing token yields `UNTRUSTED`

### 9. Filesystem Writes ↔ Path Security
- Every write path must pass `path_security.validate_write_path()` before any write

### 10. Document Prompting ↔ Injection Scanning
- Every loaded document chunk must pass injection scanning
- External document context belongs in `USER` prompt only

---