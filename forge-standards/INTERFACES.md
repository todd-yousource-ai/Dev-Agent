# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements explicitly stated for the `ConsensusDevAgent` subsystem from the provided TRD excerpts and Forge component contracts.

Where the TRDs specify exact fields, values, order, or behavior, they are reproduced exactly.  
Where a subsystem interaction is mandated but payload fields are not fully defined in the excerpts, the contract is limited to what is explicitly required.

---

### 1. Startup Sequence Signals

#### 1.1 Stdout Listening Announcement

Printed by backend during startup.

- **Format**: plain text line
- **Exact value pattern**: `FORGE_AGENT_LISTENING:{socket_path}`

##### Fields

| Name | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | Yes | Inserted after the literal prefix `FORGE_AGENT_LISTENING:` |

##### Constraints

- Must be emitted at startup step 3.
- Must be printed to stdout.
- Startup order is mandatory.

---

### 2. XPC Ready Message

Sent via XPC after initialization sequence step 8.

#### 2.1 Ready Message Payload

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | Yes | Included in ready message |
| `capabilities` | array | Yes | Included in ready message |

##### Constraints

- Must be sent after:
  1. logger initialization
  2. XPC server start
  3. stdout listening announcement
  4. credential wait
  5. `GitHubTool` initialization
  6. `ConsensusEngine` initialization
  7. `DocumentStore` background loading start
- Sent at startup step 8.
- Backend then enters `CommandRouter` event loop.

---

### 3. XPC Auth Error Card

Sent via XPC when credential initialization fails.

#### 3.1 Auth Error Card

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `auth_error` | object or card discriminator | Yes | Exact card name/value indicated by TRD text: `auth_error XPC card` |

##### Constraints

- Steps 5 and 6 are non-fatal on credential errors.
- On credential errors:
  - emit `auth_error` XPC card
  - continue in degraded state

> Note: The internal fields of the `auth_error` card are not defined in the provided excerpts.

---

### 4. TrustFlow Event

Every action outcome must emit a TrustFlow event.

#### 4.1 TrustFlow Event Record

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | Yes | Must be globally unique; CSPRNG, not sequential |
| `session_id` | string | Yes | Required in every TrustFlow event |
| `ctx_id` | string | Yes | Required in every TrustFlow event |
| `ts` | number | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | Yes | Required in every TrustFlow event |
| `payload_hash` | string | Yes | Must be SHA-256 of the serialized action payload |

##### Constraints

- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission must not be silently skipped.
- Every action outcome must emit a TrustFlow event:
  - allow
  - restrict
  - block

---

### 5. VTZ Enforcement Decision

Produced when VTZ policy denies an action.

#### 5.1 VTZEnforcementDecision Record

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | Yes | Must equal `block` on VTZ policy denial |

##### Constraints

- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

> Note: No other `VTZEnforcementDecision` fields are defined in the provided excerpts.

---

### 6. CTX-ID Token

CTX-ID is a required token for action processing.

#### 6.1 CTX-ID

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | Yes | Missing CTX-ID must be treated as UNTRUSTED |

##### Constraints

- CTX-ID validation must occur first for every entry point that processes an agent action.
- CTX-ID validation failure must result in immediate rejection.
- No partial processing is allowed on CTX-ID validation failure.
- CTX-ID tokens are immutable once issued.
- No field modification is permitted after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID must be rejected.
- Clock skew tolerance is defined per deployment.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from context when CTX-ID is missing.

> Note: The token’s internal field structure is not defined in the provided excerpts.

---

### 7. Agent Action Payload

Used for enforcement and TrustFlow hashing.

#### 7.1 Serialized Action Payload

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `payload` | serialized data | Yes | `payload_hash` must be SHA-256 of the serialized action payload |

##### Constraints

- Every entry point that processes an agent action must:
  1. validate CTX-ID first
  2. check VTZ policy before execution
  3. emit TrustFlow event for outcome
- Action payload serialization must be stable enough to support SHA-256 hashing for `payload_hash`.

> Note: The action payload schema is not defined in the provided excerpts.

---

### 8. Credentials Delivery over XPC

Backend waits for credentials via XPC during startup.

#### 8.1 Credential Wait Contract

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `credentials` | object | Yes | Delivered via XPC |
| `timeout` | integer | Yes | `30` seconds |

##### Constraints

- Backend must wait for credentials via XPC.
- Timeout is exactly `30s`.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

> Note: Credential object fields are not defined in the provided excerpts.

---

### 9. Tool Initialization Inputs

#### 9.1 GitHubTool Initialization Input

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `token` | string | Yes | Used to initialize `GitHubTool` |

##### Constraints

- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

#### 9.2 ConsensusEngine Initialization Input

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `api_keys` | object or collection | Yes | Used to initialize `ConsensusEngine` |

> Note: The internal structure of `api_keys` is not defined in the provided excerpts.

---

## Enums and Constants

### 1. Startup Constants

| Name | Type | Exact Value |
|---|---|---|
| Listening stdout prefix | string | `FORGE_AGENT_LISTENING:` |
| Credential wait timeout | duration | `30s` |

---

### 2. XPC / Status Constants

| Name | Type | Exact Value |
|---|---|---|
| Auth error card name | string | `auth_error` |

---

### 3. VTZ Verdict Constants

| Name | Type | Exact Value |
|---|---|---|
| Block verdict | string | `block` |

---

### 4. Trust / Identity Constants

| Name | Type | Exact Value |
|---|---|---|
| Missing CTX-ID trust state | string | `UNTRUSTED` |

---

### 5. Logging / Audit Constants

| Name | Type | Exact Value |
|---|---|---|
| TrustFlow emission failure audit level | string | `WARN` |

---

### 6. Security Sentinel Constants

| Name | Type | Exact Value |
|---|---|---|
| LLM refusal sentinel | string | `SECURITY_REFUSAL` |

##### Constraints

- When `SECURITY_REFUSAL` appears in LLM output:
  - stop
  - gate
  - log
  - never retry to bypass

---

### 7. Algorithms / Precision Constants

| Name | Type | Exact Value |
|---|---|---|
| Payload hash algorithm | string | `SHA-256` |
| Timestamp basis | string | `UTC Unix timestamp` |
| Timestamp precision | string | `millisecond precision` |

---

### 8. Language / Runtime Constants

| Name | Type | Exact Value |
|---|---|---|
| Python version | string | `Python 3.12` |

---

## Validation Rules

## 1. Startup Ordering

The backend startup order is mandatory and must not change:

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC (timeout: 30s)`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background (async)`
8. `Send ready message via XPC (includes agent_version, capabilities)`
9. `Enter CommandRouter event loop`

### Additional startup constraints

- Steps 5-6 are non-fatal on credential errors.
- On credential errors, emit `auth_error` XPC card and continue in degraded state.
- Step 7 is always async.
- The app must remain responsive while embeddings load.

---

## 2. CAL Enforcement Validation

For every entry point that processes an agent action:

1. CTX-ID validation must be called first.
2. If CTX-ID validation fails:
   - immediate rejection is required
   - no partial processing is permitted
3. VTZ policy must be checked before execution.
4. If VTZ policy denies:
   - produce `VTZEnforcementDecision` with `verdict=block`
5. Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.
6. If TrustFlow emission fails:
   - must not silently continue
   - log and surface the failure

---

## 3. TrustFlow Validation

For every TrustFlow event:

- `event_id` must be globally unique
- uniqueness source must be CSPRNG
- sequential IDs are forbidden
- `ts` must be a UTC Unix timestamp with millisecond precision
- `payload_hash` must be SHA-256 of the serialized action payload
- emission must be synchronous in the enforcement path
- async buffering is forbidden
- failed emission must be treated as WARN-level audit event

---

## 4. CTX-ID Validation

- CTX-ID is required for trusted action processing.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from context when CTX-ID is missing.
- CTX-ID tokens are immutable after issuance.
- Rotation creates a new token and immediately invalidates the old one.
- Expired CTX-ID must be rejected.
- Validation must be against TrustLock public key.
- Software-only validation is rejected.

---

## 5. VTZ Validation

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 6. Security Validation

### 6.1 Credentials and secrets

- Never hardcode credentials, API keys, tokens, or secrets as string literals.

### 6.2 Process execution

- Never use `shell=True` in subprocess calls.

### 6.3 Code execution safety

- Never call `eval()` or `exec()` on generated or external content.

### 6.4 Logging safety

- Never log HTTP response bodies.
- Log status codes and error types only.

### 6.5 File write path validation

- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

### 6.6 Prompt injection handling

- All loaded document chunks must pass injection scanning before being included in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

### 6.7 SECURITY_REFUSAL handling

- When `SECURITY_REFUSAL` appears in output:
  - stop
  - gate
  - log
  - never retry to bypass

### 6.8 Keychain boundary

- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

---

## 7. Python Implementation Validation

- Python version must be `3.12`.
- Type annotations are required on every function.
- `async/await` throughout the backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- Tests use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be `≥ 85%` on all new modules.

---

## Wire Format Examples

## 1. Valid Payloads

### 1.1 Valid stdout listening signal

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

---

### 1.2 Valid ready message

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

This is valid because the TRD requires inclusion of:

- `agent_version`
- `capabilities`

---

### 1.3 Valid TrustFlow event

```json
{
  "event_id": "6d7c1d9e-8f77-4ac2-96b0-7a3f5d4f2d11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1742558123456,
  "event_type": "block",
  "payload_hash": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
}
```

This is valid if:

- `event_id` is globally unique and CSPRNG-derived
- `ts` is UTC Unix timestamp in milliseconds
- `payload_hash` is SHA-256 of serialized action payload

---

### 1.4 Valid VTZ denial decision

```json
{
  "verdict": "block"
}
```

---

### 1.5 Valid auth error signaling

```json
{
  "auth_error": {}
}
```

This is the minimal conformant example based only on the defined requirement that an `auth_error` XPC card be emitted.

---

## 2. Invalid Payloads

### 2.1 Invalid TrustFlow event: missing required field

```json
{
  "event_id": "evt_1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1742558123456,
  "payload_hash": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
}
```

Invalid because:

- `event_type` is required

---

### 2.2 Invalid VTZ denial decision

```json
{
  "verdict": "allow"
}
```

Invalid because:

- VTZ policy denial must produce `verdict=block`

---

### 2.3 Invalid stdout listening signal

```text
FORGE_LISTENING:/tmp/forge-agent.sock
```

Invalid because:

- exact prefix must be `FORGE_AGENT_LISTENING:`

---

### 2.4 Invalid CTX-ID handling case

```json
{
  "session_id": "sess_123",
  "action": "write_file"
}
```

Invalid for trusted processing because:

- `ctx_id` is missing
- missing CTX-ID must be treated as `UNTRUSTED`
- identity must never be inferred from context

---

### 2.5 Invalid TrustFlow event timestamp precision

```json
{
  "event_id": "6d7c1d9e-8f77-4ac2-96b0-7a3f5d4f2d11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1742558123,
  "event_type": "allow",
  "payload_hash": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
}
```

Invalid because:

- `ts` must have millisecond precision

---

## Integration Points

## 1. XPC

The subsystem integrates with XPC for:

- credential delivery
- ready message delivery
- auth error signaling

### XPC constraints

- Backend starts XPC server before credential wait.
- Swift reads Keychain and delivers credentials via XPC.
- Python must not read Keychain directly.

---

## 2. GitHubTool

All GitHub operations must go through `GitHubTool`.

### Constraints

- Never call the GitHub API directly from pipeline code.
- `GitHubTool` is initialized with `token`.

---

## 3. ConsensusEngine

`ConsensusEngine` is initialized with API keys.

### Constraints

- Initialization occurs at startup step 6.
- Credential errors are non-fatal and result in degraded state plus `auth_error` signaling.

---

## 4. DocumentStore

`DocumentStore` loading is an integration point in startup.

### Constraints

- Loading starts in background.
- Must be async.
- Application remains responsive while embeddings load.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.

---

## 5. CommandRouter

The backend enters `CommandRouter` event loop after ready signaling.

### Constraints

- This is startup step 9.
- No earlier step may be reordered past it.

---

## 6. TrustLock

CTX-ID validation integrates with TrustLock public key verification.

### Constraints

- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.

---

## 7. VTZ Policy Enforcement

All actions integrate with VTZ policy before execution.

### Constraints

- Every session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.

---

## 8. TrustFlow Audit Pipeline

All action outcomes integrate with TrustFlow emission.

### Constraints

- Required fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- Emission is synchronous in enforcement path.
- Async buffering is not permitted.
- Failures are WARN-level audit events and must be surfaced.

---

## 9. Path Security

All writes to disk integrate with path validation.

### Required call

- `path_security.validate_write_path()`

### Constraint

- Must be called before any write.

---

## 10. Testing and Quality Gates

Before code changes:

- Find the TRD that owns the component in `README.md`
- Read relevant TRD sections
- Check `TRD-11` if change touches:
  - credentials
  - external content
  - generated code
  - CI
- Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

### Ongoing requirements

- `pytest`
- `ruff`
- `mypy`
- `≥ 85%` coverage on all new modules