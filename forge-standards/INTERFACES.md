# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the `ConsensusDevAgent` subsystem based on the provided TRD excerpts and Forge interface contracts.

Where the source material does not define a concrete fielded payload, this document records the exact required contract language and the explicit fields that are mandated.

---

### 1. Backend Startup Sequence Messages

The backend startup sequence is mandatory and ordered.

#### 1.1 Stdout Listening Announcement

Printed to stdout exactly at startup step 3.

**Format**
```text
FORGE_AGENT_LISTENING:{socket_path}
```

**Fields**
- `socket_path`: string
  - Required
  - The XPC socket path
  - Inserted directly after the literal `FORGE_AGENT_LISTENING:`

**Constraints**
- Prefix MUST be exactly `FORGE_AGENT_LISTENING:`
- Emitted after:
  1. logger initialization
  2. XPC server start and listen
- Emitted before:
  1. waiting for credentials via XPC
  2. any tool initialization

---

#### 1.2 Credentials Wait

The backend waits for credentials via XPC.

**Fields**
- `timeout`: integer
  - Required by behavior
  - Value exactly `30` seconds

**Constraints**
- Timeout is exactly `30s`
- Credentials are delivered via XPC
- Python reads nothing from Keychain
- Only Swift reads Keychain, only to deliver via XPC

---

#### 1.3 Ready Message via XPC

At startup step 8, a ready message is sent via XPC.

**Fields**
- `agent_version`: string
  - Required
- `capabilities`: array
  - Required
  - Element type not further specified in source

**Constraints**
- Sent only after:
  - `GitHubTool` initialization attempt
  - `ConsensusEngine` initialization attempt
  - `DocumentStore` background loading start
- May be sent even in degraded state if credential initialization failed earlier
- Steps 5-6 are non-fatal on credential errors

---

#### 1.4 Auth Error XPC Card

On credential errors during startup steps 5-6, the backend emits an auth error card.

**Message identifier**
- `auth_error`

**Constraints**
- Must be emitted via XPC
- Credential errors in:
  - `GitHubTool` initialization
  - `ConsensusEngine` initialization
- Are non-fatal
- System continues in degraded state

Source does not define further required fields for the `auth_error` payload.

---

### 2. TrustFlow Event Record

Every action outcome must emit a TrustFlow event.

#### 2.1 TrustFlow Event

**Fields**
- `event_id`: string
  - Required
  - MUST be globally unique
  - MUST be generated via CSPRNG
  - MUST NOT be sequential
- `session_id`: string
  - Required
- `ctx_id`: string
  - Required
- `ts`: number
  - Required
  - UTC Unix timestamp
  - Millisecond precision
- `event_type`: string
  - Required
- `payload_hash`: string
  - Required
  - SHA-256 of the serialized action payload

**Constraints**
- Emission MUST be synchronous in the enforcement path
- Async buffering is not permitted
- Failed emission is a WARN-level audit event
- Failed emission MUST NOT be a silent skip
- Every action outcome must emit a TrustFlow event for:
  - allow
  - restrict
  - block

---

### 3. VTZ Enforcement Decision Record

On VTZ policy denial, a `VTZEnforcementDecision` record must be produced.

#### 3.1 VTZEnforcementDecision

**Fields**
- `verdict`: string
  - Required
  - Value exactly `block`

**Constraints**
- Produced when VTZ policy denies an action
- Denial check MUST occur before execution
- The source excerpt does not define additional required fields

---

### 4. CTX-ID Token Contract

The source defines behavioral constraints for `CTX-ID` tokens but not a full field schema.

#### 4.1 CTX-ID

**Type**
- token/string/object not structurally specified in source

**Constraints**
- CTX-ID tokens are immutable once issued
- No field modification after issuance
- Rotation creates a new token
- Old token is invalidated immediately
- Expired CTX-ID must be rejected
- Clock skew tolerance is deployment-defined
- CTX-ID must be validated against TrustLock public key
- Software-only validation is rejected
- Missing CTX-ID must be treated as `UNTRUSTED`
- Identity must never be inferred from context when CTX-ID is missing

---

### 5. Agent Action Processing Contract

Every entry point that processes an agent action must implement these requirements.

#### 5.1 Agent Action Request

The source does not define a canonical payload schema for an action request, but the following fields are required indirectly by enforcement and emission contracts.

**Required associated values**
- `ctx_id`: string
  - Required for trusted processing
- `session_id`: string
  - Required for TrustFlow emission
- serialized action payload
  - Required to compute `payload_hash`

**Processing order constraints**
1. CTX-ID validation MUST occur first
2. CTX-ID validation failure MUST result in immediate rejection
3. No partial processing is permitted on CTX-ID validation failure
4. VTZ policy check MUST occur before execution
5. VTZ denial MUST produce `VTZEnforcementDecision` with `verdict=block`
6. Every outcome MUST emit a TrustFlow event
7. TrustFlow emission failure MUST be logged and surfaced

---

### 6. Document and Prompt Handling Interfaces

These are mandatory processing interfaces for external document content.

#### 6.1 Loaded Document Chunk

Concrete field schema is not defined in the source, but the contract requires:

**Constraints**
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt
- Context from external documents goes in the `USER` prompt
- Context from external documents must never go in the `SYSTEM` prompt

---

### 7. File Write Path Validation Interface

Any file path written to disk must pass security validation.

#### 7.1 Write Path Validation Input

**Fields**
- `path`: string
  - Required

**Validator**
- `path_security.validate_write_path()`

**Constraints**
- Validation must occur before any write
- All file paths written to disk must pass this validation

---

### 8. GitHub Operations Integration

#### 8.1 GitHubTool Usage Contract

**Component**
- `GitHubTool`

**Constraints**
- All GitHub operations go through `GitHubTool`
- Never call the GitHub API directly from pipeline code

No wire payload schema is provided in the source excerpt.

---

### 9. Consensus Engine Initialization

#### 9.1 ConsensusEngine Initialization Input

**Fields**
- `API keys`: credentials object/value
  - Required for full operation
  - Exact field names not specified in source

**Constraints**
- Initialized at startup step 6
- Credential errors are non-fatal
- On credential error, emit `auth_error` XPC card and continue in degraded state

---

### 10. Command Router Event Loop

#### 10.1 CommandRouter

**Component**
- `CommandRouter`

**Constraints**
- Entered at startup step 9
- Only after all prior startup steps complete in the specified order

No message schema is defined in the source excerpt.

---

## Enums and Constants

### 1. Startup Sequence Constants

#### 1.1 Listening Prefix
```text
FORGE_AGENT_LISTENING:
```

#### 1.2 Credential Wait Timeout
```text
30s
```

#### 1.3 Auth Error Identifier
```text
auth_error
```

---

### 2. VTZ Enforcement Constants

#### 2.1 VTZ Verdict
```text
block
```

---

### 3. Trust State Constant

#### 3.1 Missing CTX-ID Classification
```text
UNTRUSTED
```

---

### 4. Logging / Audit Severity Constant

#### 4.1 TrustFlow Emission Failure Severity
```text
WARN
```

---

### 5. Cryptographic / Time Constants

#### 5.1 Payload Hash Algorithm
```text
SHA-256
```

#### 5.2 Timestamp Format
```text
UTC Unix timestamp with millisecond precision
```

#### 5.3 event_id Generation Requirement
```text
CSPRNG
```

---

### 6. Prompt Role Constants

#### 6.1 Allowed Role for External Document Context
```text
USER
```

#### 6.2 Forbidden Role for External Document Context
```text
SYSTEM
```

---

## Validation Rules

## 1. Startup Ordering

The backend startup order is mandatory and must not change:

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (async)
8. Send ready message via XPC (includes `agent_version`, `capabilities`)
9. Enter `CommandRouter` event loop

### Rules
- Steps 5-6 are non-fatal on credential errors
- On credential errors in steps 5-6, emit `auth_error` XPC card
- Continue in degraded state
- Step 7 is always async
- App remains responsive while embeddings load

---

## 2. CAL Enforcement

### Rules
- Every entry point that processes an agent action MUST call CTX-ID validation first
- CTX-ID validation failure MUST cause immediate rejection
- No partial processing is permitted after CTX-ID failure
- Every action MUST be checked against VTZ policy before execution
- VTZ denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event
- TrustFlow emission failure MUST NOT silently continue
- Failure must be logged and surfaced

---

## 3. TrustFlow Event Validation

### Required fields
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

### Field constraints
- `event_id` must be globally unique
- `event_id` must use CSPRNG generation
- `event_id` must not be sequential
- `ts` must be a UTC Unix timestamp with millisecond precision
- `payload_hash` must be SHA-256 of the serialized action payload

### Emission constraints
- Emission must be synchronous in the enforcement path
- Async buffering is not permitted
- Failed emission is a WARN-level audit event
- Failed emission is not a silent skip

---

## 4. CTX-ID Validation

### Rules
- CTX-ID tokens are immutable once issued
- No field modification is permitted after issuance
- Rotation creates a new token
- Old token is invalidated immediately
- Expired CTX-ID must be rejected
- Validation must be against TrustLock public key
- Software-only validation is rejected
- Missing CTX-ID must be treated as `UNTRUSTED`
- Identity must never be inferred from context

---

## 5. VTZ Enforcement

### Rules
- Every agent session is bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit cross-VTZ access is denied
- VTZ boundaries are structural, not advisory
- Enforcement cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance
- VTZ policy does not change mid-session

---

## 6. Security Validation

### Rules
- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Never use `shell=True` in subprocess calls
- Never call `eval()` or `exec()` on generated or external content
- Never log HTTP response bodies
- Log status codes and error types only
- All file paths written to disk must pass `path_security.validate_write_path()` before any write
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt
- When `SECURITY_REFUSAL` output is returned from the LLM:
  - stop
  - gate
  - log
  - never retry to bypass

### Forbidden behaviors
- Ignoring `SECURITY_REFUSAL`
- Force unwrap in Swift:
  ```swift
  let value = optional!
  ```
- LLM API call from Swift
- Backend token reads from Keychain in Python

---

## 7. Language / Implementation Requirements

### Python
- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data

### Tests
- `pytest`
- Tests live in `tests/`
- Tests mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage must be `≥ 85%` on all new modules

### Existing test command
```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## Wire Format Examples

## 1. Valid Stdout Listening Announcement

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### Invalid
Wrong prefix:
```text
FORGE_LISTENING:/tmp/forge-agent.sock
```

Wrong format:
```text
FORGE_AGENT_LISTENING
```

---

## 2. Valid Ready Message via XPC

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "document_store"]
}
```

### Constraints demonstrated
- Includes `agent_version`
- Includes `capabilities`

### Invalid
Missing `agent_version`:
```json
{
  "capabilities": ["github"]
}
```

Missing `capabilities`:
```json
{
  "agent_version": "1.0.0"
}
```

---

## 3. Valid TrustFlow Event

```json
{
  "event_id": "a8d7a4e3-6f8f-4ac0-a3fd-7f1ca2d0d93e",
  "session_id": "sess-123",
  "ctx_id": "ctx-abc",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3edc1e7346b2c7b9"
}
```

### Invalid
Missing required field:
```json
{
  "event_id": "a8d7a4e3-6f8f-4ac0-a3fd-7f1ca2d0d93e",
  "session_id": "sess-123",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3edc1e7346b2c7b9"
}
```

Sequential `event_id` not allowed:
```json
{
  "event_id": "1001",
  "session_id": "sess-123",
  "ctx_id": "ctx-abc",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3edc1e7346b2c7b9"
}
```

Non-millisecond timestamp:
```json
{
  "event_id": "a8d7a4e3-6f8f-4ac0-a3fd-7f1ca2d0d93e",
  "session_id": "sess-123",
  "ctx_id": "ctx-abc",
  "ts": 1735689600,
  "event_type": "allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3edc1e7346b2c7b9"
}
```

---

## 4. Valid VTZ Enforcement Decision

```json
{
  "verdict": "block"
}
```

### Invalid
Wrong verdict:
```json
{
  "verdict": "allow"
}
```

Missing verdict:
```json
{}
```

---

## 5. Valid External Document Prompt Placement

### Valid
```json
{
  "role": "USER",
  "content": "External document context here"
}
```

### Invalid
```json
{
  "role": "SYSTEM",
  "content": "External document context here"
}
```

---

## 6. Valid File Write Validation Flow

### Valid sequence
```text
path_security.validate_write_path(path) -> success
write(path)
```

### Invalid sequence
```text
write(path)
path_security.validate_write_path(path)
```

---

## 7. Valid SECURITY_REFUSAL Handling

### Valid behavior
```text
LLM output contains SECURITY_REFUSAL
-> stop
-> gate
-> log
-> do not retry
```

### Invalid behavior
```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

---

## Integration Points

## 1. XPC

Used for:
- credential delivery
- ready message delivery
- auth error card delivery

Required interactions:
- Start XPC server before stdout listening announcement
- Wait up to `30s` for credentials via XPC
- Send ready message via XPC with:
  - `agent_version`
  - `capabilities`
- Send `auth_error` via XPC on non-fatal credential initialization failures

---

## 2. Swift Host Application

Contracts:
- Swift reads stdout line:
  - `FORGE_AGENT_LISTENING:{socket_path}`
- Swift reads Keychain
- Swift may deliver credentials via XPC
- Swift must not make LLM API calls on behalf of backend logic
- Swift must not force unwrap optionals in conformant code

---

## 3. GitHubTool

Contracts:
- Startup step 5 initializes `GitHubTool` with token
- All GitHub operations must go through `GitHubTool`
- Pipeline code must never call GitHub API directly

---

## 4. ConsensusEngine

Contracts:
- Startup step 6 initializes `ConsensusEngine` with API keys
- Credential errors are non-fatal
- On credential error:
  - emit `auth_error`
  - continue in degraded state

---

## 5. DocumentStore

Contracts:
- Startup step 7 starts `DocumentStore` loading
- Loading is background and async
- App remains responsive while embeddings load

Security coupling:
- All loaded document chunks must pass injection scanning before inclusion in prompts

---

## 6. CommandRouter

Contracts:
- Enter event loop only at startup step 9
- Must occur after ready message via XPC
- Must operate under CAL, CTX-ID, VTZ, and TrustFlow enforcement requirements

---

## 7. TrustLock

Contracts:
- CTX-ID validation must be against TrustLock public key
- Software-only validation is rejected

---

## 8. path_security

Contracts:
- Use `path_security.validate_write_path()` before any disk write

---

## 9. Test / Build Tooling

Required tools:
- `pytest`
- `ruff`
- `mypy`

Required command before changes:
```bash
cd src && pytest ../tests/ -v --tb=short
```

Required quality gates:
- `ruff` passes clean
- `mypy` passes clean
- coverage `≥ 85%` on all new modules