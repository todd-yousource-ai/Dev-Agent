# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the ConsensusDevAgent subsystem based only on the provided TRD excerpts and interface standards.

Where a field is required by contract but no enclosing message name is specified in the source, this document names the minimal required structure explicitly and marks the origin contract.

### 1. StartupStdoutListeningLine

Printed by backend startup during the mandatory startup sequence.

#### Type
String

#### Format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Constraints
- Must be printed to stdout.
- Prefix must be exactly `FORGE_AGENT_LISTENING:`
- `{socket_path}` is a non-empty socket path string.
- Emitted at startup step 3, after XPC server starts listening.
- Order is mandatory:
  1. Initialize logger
  2. Start XPC server, listen on socket
  3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
  4. Wait for credentials via XPC (timeout: `30s`)
  5. Initialize GitHubTool with token
  6. Initialize ConsensusEngine with API keys
  7. Start DocumentStore loading in background (async)
  8. Send ready message via XPC
  9. Enter CommandRouter event loop

---

### 2. XPCCredentialsWait

Implicit startup contract for credential intake over XPC.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| timeout | integer or duration literal | Yes | Must be `30s` per startup sequence |

#### Constraints
- Backend must wait for credentials via XPC.
- Credential wait occurs before initialization of `GitHubTool` and `ConsensusEngine`.
- Credential failures in steps 5-6 are non-fatal.

---

### 3. XPCReadyMessage

Ready message sent via XPC after startup initialization.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| agent_version | string | Yes | Included in ready message |
| capabilities | array | Yes | Included in ready message |

#### Constraints
- Sent at startup step 8.
- Must be sent after:
  - XPC server start
  - stdout listening line
  - credential wait
  - GitHubTool initialization attempt
  - ConsensusEngine initialization attempt
  - DocumentStore background loading start
- May be sent while DocumentStore is still loading asynchronously.

#### Notes
- Element type of `capabilities` is not specified in provided source.
- No additional fields may be inferred from source.

---

### 4. XPCAuthErrorCard

Authentication/degraded-state notification sent via XPC.

#### Type
XPC message/card

#### Fields
No explicit field-level schema is provided in source.

#### Constraints
- On credential errors in startup steps 5-6:
  - Must emit `auth_error` XPC card
  - Must continue in degraded state
- Emission applies to:
  - `GitHubTool` initialization with token
  - `ConsensusEngine` initialization with API keys

#### Required Literal
```text
auth_error
```

---

### 5. TrustFlowEvent

Required event structure for every action outcome in the enforcement path.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| event_id | string | Yes | Must be globally unique; CSPRNG; not sequential |
| session_id | string | Yes | Required by TrustFlow Emission Contract |
| ctx_id | string | Yes | Required by TrustFlow Emission Contract |
| ts | integer or decimal timestamp | Yes | UTC Unix timestamp with millisecond precision |
| event_type | string | Yes | Required by TrustFlow Emission Contract |
| payload_hash | string | Yes | Must be SHA-256 of the serialized action payload |

#### Constraints
- Every TrustFlow event must include all listed fields.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission:
  - Must not silently continue
  - Must be a WARN-level audit event
  - Must be logged and surfaced

#### Semantics
- Emitted for every action outcome:
  - allow
  - restrict
  - block

---

### 6. VTZEnforcementDecision

Required record produced on VTZ denial.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| verdict | string | Yes | Must be exactly `block` for VTZ policy denial |

#### Constraints
- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

#### Notes
- No additional fields are specified in provided source.

---

### 7. CTXIDToken

Security identity token governed by CTX-ID contract.

#### Fields
No explicit field-level schema is provided in source.

#### Constraints
- CTX-ID tokens are immutable once issued.
- No field modification is allowed after issuance.
- Rotation creates a new token.
- Old token is invalidated immediately on rotation.
- Expired CTX-ID must be rejected.
- Clock skew tolerance is defined per deployment.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from context if CTX-ID is missing.

---

### 8. AgentActionPayload

Serialized payload for an agent action, used for enforcement and hashing.

#### Fields
No explicit field-level schema is provided in source.

#### Constraints
- Every entry point that processes an agent action must call CTX-ID validation first.
- CTX-ID validation failure must result in immediate rejection.
- No partial processing is allowed after CTX-ID validation failure.
- Every action must be checked against VTZ policy before execution.
- `payload_hash` in TrustFlowEvent must be the SHA-256 of the serialized action payload.

---

### 9. SecurityRefusalOutput

LLM output sentinel indicating security refusal.

#### Type
String sentinel

#### Required Literal
```text
SECURITY_REFUSAL
```

#### Constraints
- When `SECURITY_REFUSAL` appears in output:
  - stop
  - gate
  - log
  - never retry to bypass
- Retrying generation to bypass `SECURITY_REFUSAL` is forbidden.

---

### 10. PathWriteValidationInput

Input to path security validation before any disk write.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| path | string | Yes | Must pass `path_security.validate_write_path()` before any write |

#### Constraints
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

---

### 11. InjectionScannedDocumentChunk

Loaded document chunk eligible for inclusion in LLM prompt context.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| chunk | string or structured document chunk | Yes | Must pass injection scanning before inclusion in any LLM prompt |

#### Constraints
- All loaded document chunks must pass injection scanning before being included in any LLM prompt.
- Context from external documents must go in the USER prompt, never the SYSTEM prompt.

---

### 12. GitHubToolInitialization

Initialization input for GitHub operations subsystem.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| token | string | Yes | Used to initialize `GitHubTool` |

#### Constraints
- All GitHub operations go through `GitHubTool`.
- Pipeline code must never call the GitHub API directly.
- Initialization occurs at startup step 5.
- Credential error is non-fatal:
  - emit `auth_error` XPC card
  - continue in degraded state

---

### 13. ConsensusEngineInitialization

Initialization input for consensus subsystem.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| api_keys | array or map of string credentials | Yes | Used to initialize `ConsensusEngine` |

#### Constraints
- Initialization occurs at startup step 6.
- Credential error is non-fatal:
  - emit `auth_error` XPC card
  - continue in degraded state

#### Notes
- Exact shape of `api_keys` is not specified in provided source.

---

### 14. DocumentStoreBackgroundLoadState

Background loading state for document store.

#### Fields
No explicit field-level schema is provided in source.

#### Constraints
- DocumentStore loading starts at startup step 7.
- Loading must be asynchronous.
- App remains responsive while embeddings load.

---

## Enums and Constants

### String Literals

| Name | Value |
|---|---|
| SECURITY_REFUSAL | `SECURITY_REFUSAL` |
| XPC auth error card type | `auth_error` |
| Startup listening prefix | `FORGE_AGENT_LISTENING:` |
| VTZ denial verdict | `block` |
| Missing CTX-ID trust state | `UNTRUSTED` |

### Startup Constants

| Name | Value |
|---|---|
| credentials timeout | `30s` |

### Action Outcome Enum

Required action outcomes that must emit a TrustFlow event:

```text
allow
restrict
block
```

### Logging / Emission Semantics

| Name | Value |
|---|---|
| Failed TrustFlow emission audit level | `WARN-level audit event` |

### Language / Implementation Constants

| Name | Value |
|---|---|
| Python version | `3.12` |

---

## Validation Rules

## 1. CAL Enforcement

For every entry point that processes an agent action:

1. CTX-ID validation must occur first.
2. If CTX-ID validation fails:
   - immediate rejection is required
   - no partial processing is allowed
3. VTZ policy must be checked before execution.
4. If VTZ policy denies:
   - produce `VTZEnforcementDecision`
   - `verdict` must equal `block`
5. Every action outcome must emit a TrustFlow event.
6. If TrustFlow emission fails:
   - do not silently continue
   - log and surface the failure

## 2. TrustFlow Event Validation

A valid `TrustFlowEvent` must satisfy all of:

- `event_id` present
- `session_id` present
- `ctx_id` present
- `ts` present
- `event_type` present
- `payload_hash` present
- `event_id` generated via CSPRNG
- `event_id` not sequential
- `ts` is UTC Unix timestamp with millisecond precision
- `payload_hash` is SHA-256 of serialized action payload
- emission is synchronous in enforcement path
- async buffering is forbidden

## 3. CTX-ID Validation

A valid CTX-ID flow must satisfy all of:

- token is immutable after issuance
- rotation creates a new token
- old token invalidated immediately
- expired token rejected
- validation uses TrustLock public key
- software-only validation rejected
- missing token treated as `UNTRUSTED`
- identity never inferred from surrounding context

## 4. VTZ Validation

A valid VTZ enforcement flow must satisfy all of:

- every agent session bound to exactly one VTZ at CTX-ID issuance
- cross-VTZ tool calls require explicit policy authorization
- implicit authorization is denied
- VTZ boundaries are structural and cannot be bypassed by application code
- policy changes take effect at next CTX-ID issuance
- policy changes do not apply mid-session

## 5. Startup Sequence Validation

The following order is mandatory and must not change:

```text
1. Initialize logger
2. Start XPC server, listen on socket
3. Print FORGE_AGENT_LISTENING:{socket_path} to stdout
4. Wait for credentials via XPC (timeout: 30s)
5. Initialize GitHubTool with token
6. Initialize ConsensusEngine with API keys
7. Start DocumentStore loading in background (async)
8. Send ready message via XPC (includes agent_version, capabilities)
9. Enter CommandRouter event loop
```

Additional rules:
- Steps 5-6 are non-fatal on credential errors.
- On those errors, emit `auth_error` XPC card and continue degraded.
- Step 7 must be async.

## 6. Security Validation

The subsystem must enforce all of:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- External document context must go in USER prompt, never SYSTEM prompt.
- If `SECURITY_REFUSAL` appears:
  - stop
  - gate
  - log
  - never retry to bypass

## 7. Python Backend Validation

Implementation requirements:

- Python `3.12`
- Type annotations on every function
- `async/await` throughout backend
- No blocking calls on event loop
- Dataclasses for all structured data
- Tests use `pytest`
- Tests live in `tests/`, mirroring `src/`
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage must be `≥ 85%` on all new modules

---

## Wire Format Examples

## 1. Valid Startup stdout line

```text
FORGE_AGENT_LISTENING:/tmp/consensusdevagent.sock
```

## 2. Invalid Startup stdout line

Wrong prefix:
```text
AGENT_LISTENING:/tmp/consensusdevagent.sock
```

Missing socket path:
```text
FORGE_AGENT_LISTENING:
```

---

## 3. Valid XPC ready message

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

### Why valid
- Includes `agent_version`
- Includes `capabilities`

## 4. Invalid XPC ready message

Missing `capabilities`:
```json
{
  "agent_version": "1.0.0"
}
```

Missing `agent_version`:
```json
{
  "capabilities": ["github"]
}
```

---

## 5. Valid TrustFlow event

```json
{
  "event_id": "4f2d7b57-6cf8-4b77-a6c1-6ff0f7d6d4f1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action_allow",
  "payload_hash": "8c5e5d56f6b5e0a7f9a3a2e6dbf2c0d3f7f6a8d0f1e2c3b4a5d6e7f8a9b0c1d2"
}
```

### Why valid
- All required fields present
- `ts` shown as Unix timestamp in milliseconds
- `payload_hash` shown as SHA-256 hex string shape
- `event_id` is non-sequential in form

## 6. Invalid TrustFlow event

Missing required field:
```json
{
  "event_id": "1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600,
  "payload_hash": "abc"
}
```

Invalid because:
- `event_type` missing
- `event_id` appears sequential/non-CSPRNG
- `ts` not millisecond precision as shown
- `payload_hash` not valid SHA-256 shape

---

## 7. Valid VTZ enforcement decision

```json
{
  "verdict": "block"
}
```

## 8. Invalid VTZ enforcement decision

```json
{
  "verdict": "allow"
}
```

Invalid because VTZ policy denial must produce `verdict=block`.

---

## 9. Valid security refusal handling trigger

```json
{
  "output": "SECURITY_REFUSAL"
}
```

### Required behavior
- stop
- gate
- log
- do not retry

## 10. Invalid security refusal handling

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Invalid because retrying to bypass `SECURITY_REFUSAL` is forbidden.

---

## 11. Valid disk write path validation flow

```json
{
  "path": "/safe/output/file.txt"
}
```

Valid only if `path_security.validate_write_path()` passes before write.

## 12. Invalid disk write path validation flow

```json
{
  "path": "/safe/output/file.txt"
}
```

Invalid if written without first passing `path_security.validate_write_path()`.

---

## Integration Points

## 1. XPC

Used for:
- credential delivery
- ready message delivery
- `auth_error` card delivery

Required sequence integration:
- XPC server starts before stdout listening line
- credentials are received via XPC
- ready message is sent via XPC
- auth failures emit XPC `auth_error` card

## 2. GitHubTool

Contract:
- All GitHub operations go through `GitHubTool`
- Pipeline code must never call GitHub API directly
- Initialized with `token`
- Startup step 5

## 3. ConsensusEngine

Contract:
- Initialized with `api_keys`
- Startup step 6
- Credential failure is non-fatal and degrades gracefully via XPC `auth_error`

## 4. DocumentStore

Contract:
- Loading begins in background at startup step 7
- Must be async
- App remains responsive while embeddings load

## 5. CommandRouter

Contract:
- Event loop starts only at startup step 9
- Must not begin before ready message is sent

## 6. TrustFlow

Contract:
- Every action outcome emits a synchronous TrustFlow event
- Required fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`

## 7. CTX-ID / TrustLock

Contract:
- CTX-ID validated first on every agent action entry point
- Validation must use TrustLock public key
- Missing CTX-ID is `UNTRUSTED`
- Expired CTX-ID rejected

## 8. VTZ Policy Enforcement

Contract:
- Checked before execution for every action
- Denial produces `VTZEnforcementDecision` with `verdict=block`
- Cross-VTZ calls require explicit authorization

## 9. Path Security

Contract:
- Every file path written to disk must pass:
  - `path_security.validate_write_path()`

## 10. Prompt Construction / Document Ingestion

Contract:
- Every loaded document chunk must pass injection scanning before LLM prompt inclusion
- External document context goes in USER prompt
- External document context must never go in SYSTEM prompt

## 11. Logging / Audit

Contract:
- Never log HTTP response bodies
- Log status codes and error types only
- Failed TrustFlow emission is a WARN-level audit event
- Security refusal events must be logged

## 12. Swift / Backend Boundary

Contract from forbidden examples:
- Swift must not make LLM API calls for backend responsibilities
- Python backend must not read from Keychain
- Only Swift reads Keychain, only to deliver via XPC
- Backend credentials arrive via XPC, not direct Keychain reads