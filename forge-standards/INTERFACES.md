# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements applicable to the `ConsensusDevAgent` subsystem from the provided TRD and Forge interface contract excerpts.

Where the source defines exact fields, values, ordering, and constraints, they are reproduced exactly. Where a referenced interface exists but its full payload shape is not present in the supplied source, this document records only the guaranteed contract surface and marks the remainder as unspecified by the provided TRDs.

---

### 1. Backend Startup Sequence Outputs

#### 1.1 Standard Output Listening Announcement

Backend startup order is mandatory.

At startup, after the XPC server begins listening on its socket, the backend MUST print exactly:

```text
FORGE_AGENT_LISTENING:{socket_path}
```

##### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | Yes | Inserted as the runtime socket path. Must appear after the literal prefix `FORGE_AGENT_LISTENING:` with no extra wrapper fields. |

##### Format Constraints

- Output destination: `stdout`
- Emission order: must occur at step 3 of startup sequence
- Exact literal prefix: `FORGE_AGENT_LISTENING:`

---

### 2. XPC Ready Message

After startup steps complete, the backend MUST:

- send a ready message via XPC
- include `agent_version`
- include `capabilities`

#### 2.1 Ready Message

##### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | unspecified | Yes | Must be included in the ready message. Exact type/format not defined in supplied source. |
| `capabilities` | unspecified | Yes | Must be included in the ready message. Exact type/format not defined in supplied source. |

##### Constraints

- Sent at startup step 8
- Must be sent via XPC
- Must occur after:
  1. logger initialization
  2. XPC server startup
  3. listening announcement
  4. credential wait
  5. `GitHubTool` initialization attempt
  6. `ConsensusEngine` initialization attempt
  7. `DocumentStore` background loading start

---

### 3. XPC Auth Error Card

Credential initialization errors for startup steps 5 and 6 are non-fatal.

On credential error, backend MUST:

- emit `auth_error` XPC card
- continue in degraded state

#### 3.1 Auth Error Card

##### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | string | Implicit | The supplied source defines the card kind as `auth_error`. If encoded as a discriminant field, its exact value must be `auth_error`. |

##### Constraints

- Exact card identifier value: `auth_error`
- Emitted via XPC
- Triggered on credential errors during:
  - `GitHubTool` initialization
  - `ConsensusEngine` initialization
- Error is non-fatal
- Backend continues in degraded state

> Note: Full card field schema is not present in the supplied source.

---

### 4. TrustFlow Event

Every action outcome must emit a TrustFlow event.

#### 4.1 TrustFlow Event Structure

##### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | Yes | Must be globally unique. Must be CSPRNG-generated, not sequential. |
| `session_id` | string | Yes | Required in every TrustFlow event. |
| `ctx_id` | string | Yes | Required in every TrustFlow event. |
| `ts` | number | Yes | Must be UTC Unix timestamp with millisecond precision. |
| `event_type` | string | Yes | Required in every TrustFlow event. |
| `payload_hash` | string | Yes | Must be SHA-256 of the serialized action payload. |

##### Constraints

- Emission is mandatory for every action outcome:
  - allow
  - restrict
  - block
- Emission MUST be synchronous in the enforcement path
- Async buffering is not permitted
- Failed emission is a WARN-level audit event
- Failed emission MUST NOT be a silent skip
- TrustFlow emission failure must be logged and surfaced

---

### 5. VTZ Enforcement Decision Record

When VTZ policy denies an action, the system MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

#### 5.1 VTZEnforcementDecision

##### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | Yes | On VTZ denial, exact value must be `block`. |

##### Constraints

- Produced when VTZ policy denies an action
- Exact required value on denial: `block`

> Note: No additional fields for `VTZEnforcementDecision` are defined in the supplied source.

---

### 6. CTX-ID Token

The subsystem must enforce the CTX-ID contract.

#### 6.1 CTX-ID

##### Fields

No concrete token field list is provided in the supplied source.

##### Behavioral Constraints

- CTX-ID tokens are immutable once issued
- No field modification is permitted after issuance
- Rotation creates a new token
- The old token is invalidated immediately upon rotation
- Expired CTX-ID must be rejected
- Clock skew tolerance is deployment-defined
- CTX-ID must be validated against TrustLock public key
- Software-only validation is rejected
- Missing CTX-ID must be treated as `UNTRUSTED`
- Identity must never be inferred from context when CTX-ID is missing

---

### 7. Agent Action Processing Entry Point Contract

Every entry point that processes an agent action must obey the CAL enforcement contract.

#### 7.1 Action Processing Requirements

##### Inputs

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | Yes | CTX-ID validation MUST occur first. Missing CTX-ID is treated as `UNTRUSTED`. |
| `action` | unspecified | Yes | Must be checked against VTZ policy before execution. Used to compute `payload_hash` via serialized action payload. |

##### Processing Constraints

- CTX-ID validation MUST happen first
- CTX-ID validation failure MUST result in immediate rejection
- No partial processing is permitted after CTX-ID validation failure
- Every action MUST be checked against VTZ policy before execution
- Every action outcome MUST emit a TrustFlow event

---

### 8. Action Payload Hash Input

The TrustFlow event requires `payload_hash`.

#### 8.1 Serialized Action Payload

| Item | Type | Required | Constraints |
|---|---|---:|---|
| serialized action payload | bytes or string serialization | Yes | `payload_hash` MUST be SHA-256 of this serialized payload. Serialization format is not defined in supplied source. |

---

## Enums and Constants

### 1. String Constants

| Constant | Exact Value | Usage |
|---|---|---|
| Listening announcement prefix | `FORGE_AGENT_LISTENING:` | Stdout startup announcement |
| XPC auth error card identifier | `auth_error` | Credential initialization failure notification |
| VTZ denial verdict | `block` | `VTZEnforcementDecision.verdict` on denial |
| Missing trust state | `UNTRUSTED` | Missing CTX-ID handling |
| Security refusal sentinel | `SECURITY_REFUSAL` | LLM refusal handling gate |

---

### 2. Startup Sequence Constants

| Constant | Value | Constraints |
|---|---:|---|
| Credential wait timeout | `30s` | Exact timeout for waiting for credentials via XPC |

---

### 3. Required Startup Order

The following sequence is mandatory and must not be changed:

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC (timeout: `30s`)
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (async)
8. Send ready message via XPC (includes `agent_version`, `capabilities`)
9. Enter `CommandRouter` event loop

---

### 4. Outcome Values

The source defines the following action outcomes for TrustFlow emission requirements:

| Value |
|---|
| `allow` |
| `restrict` |
| `block` |

---

## Validation Rules

## 1. CAL Enforcement Validation

Every entry point that processes an agent action MUST satisfy all of the following:

1. CTX-ID validation MUST be called first
2. CTX-ID validation failure MUST cause immediate rejection
3. No partial processing is allowed after CTX-ID validation failure
4. VTZ policy check MUST occur before execution
5. VTZ denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event
7. TrustFlow emission failure MUST NOT silently continue
8. TrustFlow emission failure MUST be logged and surfaced

---

## 2. TrustFlow Event Validation

A TrustFlow event is valid only if all required fields are present and satisfy these constraints:

- `event_id`
  - must be present
  - must be globally unique
  - must be CSPRNG-generated
  - must not be sequential

- `session_id`
  - must be present

- `ctx_id`
  - must be present

- `ts`
  - must be present
  - must be UTC Unix timestamp
  - must have millisecond precision

- `event_type`
  - must be present

- `payload_hash`
  - must be present
  - must be SHA-256 of the serialized action payload

- emission behavior
  - must be synchronous in enforcement path
  - async buffering is prohibited

- failure behavior
  - failed emission must be a WARN-level audit event
  - failed emission must not be silently skipped

---

## 3. CTX-ID Validation

A CTX-ID is valid only if all applicable contract requirements are met:

- token has not been modified after issuance
- token has not expired
- token has not been invalidated by rotation
- validation is performed against TrustLock public key
- validation is not software-only

If CTX-ID is:

- missing: treat as `UNTRUSTED`
- expired: reject
- invalid: reject

Clock skew tolerance is deployment-defined and not specified here.

---

## 4. VTZ Validation

- Every agent session must be bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit cross-VTZ access is denied
- VTZ boundaries are structural and cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session

---

## 5. Security Validation Rules

These are hard requirements applicable to this subsystem.

### 5.1 Credential and Secret Handling

- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Only Swift reads Keychain, only to deliver via XPC
- Python reads nothing from Keychain

### 5.2 LLM Refusal Handling

If output contains `SECURITY_REFUSAL`:

- stop
- gate
- log
- never retry to bypass

Forbidden behavior:

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)  # WRONG — do not retry
```

### 5.3 Subprocess and Code Execution

- Never use `shell=True` in subprocess calls
- Never call `eval()` on generated or external content
- Never call `exec()` on generated or external content

### 5.4 Logging

- Never log HTTP response bodies
- Log status codes and error types only

### 5.5 File Writes

- All file paths written to disk must pass `path_security.validate_write_path()` before any write

### 5.6 Document Injection Scanning

- All loaded document chunks must pass injection scanning before being included in any LLM prompt
- Context from external documents goes in the USER prompt, never the SYSTEM prompt

---

## 6. Python Implementation Contract

Applicable implementation constraints for structured data and APIs:

- Python version: `3.12`
- Type annotations required on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- `pytest` for tests
- Tests live in `tests/` and mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage must be `≥ 85%` on all new modules

---

## 7. GitHub Operations Validation

- All GitHub operations go through `GitHubTool`
- Never call the GitHub API directly from pipeline code

---

## Wire Format Examples

## 1. Valid Payloads

### 1.1 Valid Listening Announcement

```text
FORGE_AGENT_LISTENING:/tmp/consensusdevagent.sock
```

Why valid:

- Uses exact required prefix
- Includes socket path directly after `:`
- Intended for stdout emission at startup step 3

---

### 1.2 Valid TrustFlow Event

```json
{
  "event_id": "9c7f0d2b-8f7e-4d90-a9d1-57c8d1c0f3ab",
  "session_id": "sess_42",
  "ctx_id": "ctx_abc123",
  "ts": 1731692400123,
  "event_type": "action_executed",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8f4937b7d8b93c2098e6f4b8c13b3ce2a"
}
```

Why valid:

- Includes all required TrustFlow fields
- `ts` is a Unix timestamp with millisecond precision
- `payload_hash` is represented as a SHA-256 hex digest string
- `event_id` is non-sequential in form

> Note: `event_type` allowed value set is not specified in the supplied source; only presence is required.

---

### 1.3 Valid VTZ Denial Decision

```json
{
  "verdict": "block"
}
```

Why valid:

- VTZ denial requires a `VTZEnforcementDecision` record
- Required denial verdict is exactly `block`

---

### 1.4 Valid XPC Ready Message

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

Why valid:

- Includes `agent_version`
- Includes `capabilities`

> Note: exact types and value constraints for these fields are not defined in the supplied source; this is an illustrative valid-minimum example only.

---

### 1.5 Valid Auth Error Card

```json
{
  "type": "auth_error"
}
```

Why valid:

- Uses exact required card identifier value `auth_error`

> Note: full auth error card schema is not defined in the supplied source.

---

## 2. Invalid Payloads

### 2.1 Invalid Listening Announcement

```text
FORGE_AGENT_LISTENER:/tmp/consensusdevagent.sock
```

Why invalid:

- Prefix is not exactly `FORGE_AGENT_LISTENING:`

---

### 2.2 Invalid TrustFlow Event: Missing Required Field

```json
{
  "event_id": "9c7f0d2b-8f7e-4d90-a9d1-57c8d1c0f3ab",
  "session_id": "sess_42",
  "ctx_id": "ctx_abc123",
  "ts": 1731692400123,
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8f4937b7d8b93c2098e6f4b8c13b3ce2a"
}
```

Why invalid:

- Missing required field `event_type`

---

### 2.3 Invalid TrustFlow Event: Non-millisecond Timestamp

```json
{
  "event_id": "9c7f0d2b-8f7e-4d90-a9d1-57c8d1c0f3ab",
  "session_id": "sess_42",
  "ctx_id": "ctx_abc123",
  "ts": 1731692400,
  "event_type": "action_executed",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8f4937b7d8b93c2098e6f4b8c13b3ce2a"
}
```

Why invalid:

- `ts` is not millisecond precision

---

### 2.4 Invalid VTZ Denial Decision

```json
{
  "verdict": "deny"
}
```

Why invalid:

- On VTZ denial, verdict must be exactly `block`

---

### 2.5 Invalid Ready Message

```json
{
  "agent_version": "1.0.0"
}
```

Why invalid:

- Missing required field `capabilities`

---

### 2.6 Invalid Auth Error Handling Behavior

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Why invalid:

- `SECURITY_REFUSAL` must stop/gate/log
- Retry to bypass is explicitly forbidden

---

## Integration Points

## 1. XPC

The subsystem integrates with XPC for:

- receiving credentials
- sending ready message
- sending `auth_error` card

### XPC Requirements

- XPC server must start before listening announcement
- credentials must be awaited via XPC with timeout `30s`
- ready message must include:
  - `agent_version`
  - `capabilities`

---

## 2. Swift Host

Swift depends on stdout parsing of the listening announcement.

### Contract

- Backend must print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
- Swift reads this value
- This output must occur after XPC socket is listening

---

## 3. GitHubTool

### Contract

- Initialize `GitHubTool` with token at startup step 5
- All GitHub operations must go through `GitHubTool`
- Direct GitHub API calls from pipeline code are forbidden

---

## 4. ConsensusEngine

### Contract

- Initialize `ConsensusEngine` with API keys at startup step 6
- Credential errors are non-fatal
- On credential error, emit `auth_error` XPC card and continue in degraded state

---

## 5. DocumentStore

### Contract

- Start loading in background at startup step 7
- Loading is async
- App must remain responsive while embeddings load
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt

---

## 6. CommandRouter

### Contract

- Enter `CommandRouter` event loop at startup step 9
- Must occur after ready message is sent

---

## 7. TrustLock

### Contract

- CTX-ID must be validated against TrustLock public key
- Software-only validation is rejected

---

## 8. VTZ Policy Enforcement

### Contract

- Every action must be checked against VTZ policy before execution
- Cross-VTZ tool calls require explicit policy authorization
- Implicit cross-VTZ calls are denied

---

## 9. TrustFlow Audit Path

### Contract

- Every action outcome emits a TrustFlow event
- Emission is synchronous in enforcement path
- Failure is WARN-level audit event
- Failure must not be silently skipped

---

## 10. Path Security

### Contract

- Any file path written to disk must be validated by:
  - `path_security.validate_write_path()`

Validation must occur before any write.

---

## 11. External Document Prompting

### Contract

- External document chunks must be injection-scanned before use
- External document context goes in the USER prompt
- External document context must never go in the SYSTEM prompt

---

## 12. Keychain Boundary

### Contract

- Only Swift reads Keychain
- Swift may deliver credentials via XPC
- Python backend reads nothing from Keychain

---

## Non-Specified Interfaces

The supplied source references, but does not fully define, the wire schemas for the following. Implementations must not invent incompatible fields without consulting the owning TRD:

- full XPC credential message schema
- full XPC ready message schema beyond `agent_version` and `capabilities`
- full `auth_error` XPC card schema beyond the exact identifier `auth_error`
- full CTX-ID token field structure
- full `VTZEnforcementDecision` schema beyond `verdict=block` on denial
- allowed `event_type` enumeration for TrustFlow events
- serialized action payload canonicalization format for SHA-256 computation