# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the `ConsensusDevAgent` subsystem, based only on the provided TRD/interface source.

Where the source defines mandatory behavior but does not define a concrete payload shape, this document marks the contract as **behavioral-only** and does not invent unspecified fields.

---

### 1. Backend Startup stdout signal

#### `FORGE_AGENT_LISTENING` line
- **Channel**: process stdout
- **Type**: plain text line
- **Format**: `FORGE_AGENT_LISTENING:{socket_path}`
- **Fields**:
  - `socket_path`
    - Type: string
    - Required: yes
    - Constraints:
      - Must appear immediately after the literal prefix `FORGE_AGENT_LISTENING:`
      - Represents the XPC socket path
- **Ordering constraint**:
  - Must be emitted at startup step 3, after:
    1. Initialize logger
    2. Start XPC server, listen on socket
  - Must be emitted before:
    4. Wait for credentials via XPC (timeout: 30s)

---

### 2. XPC credentials delivery

#### Credentials via XPC
- **Channel**: XPC
- **Direction**: Swift → backend
- **Type**: structured payload
- **Status**: concrete field schema not provided in source
- **Behavioral contract**:
  - Backend must wait for credentials via XPC
  - Timeout: `30s`
  - Swift is the only side that reads Keychain
  - Python/backend reads nothing from Keychain
  - Swift may deliver credentials via XPC only
- **Constraints**:
  - No credentials, API keys, tokens, or secrets may be hardcoded as string literals
  - Backend initialization of dependent tools must use credentials received via XPC

---

### 3. XPC ready message

#### Ready message
- **Channel**: XPC
- **Direction**: backend → Swift
- **Type**: structured payload
- **Required fields**:
  - `agent_version`
    - Type: string
    - Required: yes
  - `capabilities`
    - Type: collection
    - Required: yes
    - Element type: not specified in source
- **Emission point**:
  - Startup step 8
- **Ordering constraint**:
  - Must be sent after:
    - GitHubTool initialization
    - ConsensusEngine initialization
    - DocumentStore background loading start
  - Must be sent before:
    - Entering `CommandRouter` event loop

---

### 4. XPC auth error card

#### `auth_error` XPC card
- **Channel**: XPC
- **Direction**: backend → Swift/client
- **Type**: structured payload/card
- **Identifier/value**:
  - `auth_error`
- **Status**: concrete field schema not provided in source
- **Behavioral contract**:
  - If step 5 (`GitHubTool` initialization with token) or step 6 (`ConsensusEngine` initialization with API keys) encounters credential errors:
    - This is non-fatal
    - Backend must emit an `auth_error` XPC card
    - Backend must continue in degraded state

---

### 5. TrustFlow event

#### `TrustFlowEvent`
Every action outcome `(allow, restrict, block)` must emit a TrustFlow event.

- **Type**: structured record
- **Required fields**:
  - `event_id`
    - Type: string
    - Required: yes
    - Constraints:
      - Must be globally unique
      - Must be generated via CSPRNG
      - Must not be sequential
  - `session_id`
    - Type: string
    - Required: yes
  - `ctx_id`
    - Type: string
    - Required: yes
  - `ts`
    - Type: UTC Unix timestamp
    - Required: yes
    - Constraints:
      - Millisecond precision
  - `event_type`
    - Type: string
    - Required: yes
  - `payload_hash`
    - Type: string
    - Required: yes
    - Constraints:
      - Must be SHA-256 of the serialized action payload
- **Emission constraints**:
  - Emission must be synchronous in the enforcement path
  - Async buffering is not permitted
  - Failed emission:
    - Must be a WARN-level audit event
    - Must not be silently skipped
    - Must not silently continue

---

### 6. VTZ enforcement decision

#### `VTZEnforcementDecision`
- **Type**: structured record
- **Status**: partial schema only
- **Required fields from source**:
  - `verdict`
    - Type: string
    - Required: yes when a VTZ denial occurs
    - Required value on denial: `block`
- **Behavioral contract**:
  - Every action must be checked against VTZ policy before execution
  - VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`

No additional fields are defined in the provided source.

---

### 7. Agent action payload

#### Action payload
- **Type**: structured payload
- **Status**: concrete schema not provided in source
- **Behavioral contract**:
  - Every entry point that processes an agent action must:
    1. Call CTX-ID validation first
    2. Immediately reject on CTX-ID validation failure
    3. Check the action against VTZ policy before execution
  - Every action outcome must emit a TrustFlow event
- **Hashing constraint**:
  - The serialized action payload is the input to `payload_hash` SHA-256 computation

---

### 8. CTX-ID token

#### `CTX-ID`
- **Type**: token / structured identity artifact
- **Status**: concrete field schema not provided in source
- **Behavioral contract**:
  - CTX-ID tokens are immutable once issued
  - No field modification is allowed after issuance
  - Rotation creates a new token
  - The old token is invalidated immediately
  - Expired CTX-ID must be rejected
  - Clock skew tolerance is deployment-defined
  - Validation must be against TrustLock public key
  - Software-only validation is rejected
  - Missing CTX-ID must be treated as `UNTRUSTED`
  - Identity must never be inferred from context when CTX-ID is missing

---

### 9. Session-to-VTZ binding

#### Session VTZ binding
- **Type**: session property / authorization binding
- **Status**: behavioral-only
- **Contract**:
  - Every agent session is bound to exactly one VTZ at CTX-ID issuance
  - Cross-VTZ tool calls require explicit policy authorization
  - Implicit authorization is denied
  - VTZ boundaries are structural and cannot be bypassed by application code
  - VTZ policy changes take effect at next CTX-ID issuance, not mid-session

---

### 10. SECURITY_REFUSAL handling

#### `SECURITY_REFUSAL`
- **Type**: output sentinel/string value
- **Exact value**: `SECURITY_REFUSAL`
- **Behavioral contract**:
  - When `SECURITY_REFUSAL` appears in LLM output:
    - stop
    - gate
    - log
  - Never retry to bypass
- **Forbidden behavior**:
  - Retrying a different LLM call after seeing `SECURITY_REFUSAL`

---

## Enums and Constants

### Literal values

#### Startup stdout prefix
- `FORGE_AGENT_LISTENING:`

#### XPC error card type/value
- `auth_error`

#### Security sentinel
- `SECURITY_REFUSAL`

#### VTZ denial verdict
- `block`

#### Missing CTX-ID trust state
- `UNTRUSTED`

### Action outcomes
The source defines the following action outcomes:
- `allow`
- `restrict`
- `block`

These values are required conceptually for action outcomes; the exact field carrying them is not specified in the provided source.

### Time constant
- Credentials wait timeout: `30s`

### Algorithms / generation requirements
- `payload_hash` algorithm: `SHA-256`
- `event_id` uniqueness source: `CSPRNG`

### Logging severity requirement
- TrustFlow emission failure severity: `WARN-level audit event`

---

## Validation Rules

### 1. Startup sequence validation
The backend startup order is mandatory and must be validated as follows:

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (async)
8. Send ready message via XPC
9. Enter `CommandRouter` event loop

Violations of this order are non-conformant.

Additional rules:
- Step 7 must always be async
- App must remain responsive while embeddings load

### 2. CTX-ID enforcement
For every entry point that processes an agent action:
- CTX-ID validation must occur first
- If CTX-ID validation fails:
  - immediate rejection is required
  - no partial processing is allowed
- Missing CTX-ID:
  - must be treated as `UNTRUSTED`
  - identity inference from context is forbidden
- Expired CTX-ID:
  - must be rejected
- Validation mechanism:
  - must validate against TrustLock public key
  - software-only validation is rejected

### 3. VTZ enforcement
For every action:
- VTZ policy check must occur before execution
- If VTZ denies:
  - a `VTZEnforcementDecision` must be produced
  - `verdict` must equal `block`
- Cross-VTZ tool calls:
  - require explicit policy authorization
  - implicit authorization is denied

### 4. TrustFlow emission
For every action outcome:
- A TrustFlow event must be emitted for:
  - `allow`
  - `restrict`
  - `block`
- Required fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- `event_id`:
  - must be globally unique
  - must be CSPRNG-generated
  - must not be sequential
- `ts`:
  - must be UTC Unix timestamp
  - must have millisecond precision
- `payload_hash`:
  - must be SHA-256 of serialized action payload
- Emission:
  - must be synchronous in enforcement path
  - async buffering is forbidden
- Failure:
  - must not be silent
  - must be logged/surfaced
  - must be WARN-level audit event

### 5. Credential handling
- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Python/backend must not read Keychain
- Only Swift reads Keychain
- Swift may deliver secrets to backend via XPC
- Credential initialization failures in steps 5 and 6:
  - are non-fatal
  - must emit `auth_error`
  - backend continues in degraded state

### 6. GitHub integration
- All GitHub operations must go through `GitHubTool`
- Pipeline code must never call the GitHub API directly

### 7. Secure coding constraints affecting interfaces
- Never use `shell=True` in subprocess calls
- Never call `eval()` or `exec()` on generated or external content
- Never log HTTP response bodies
  - Only log status codes and error types
- All file paths written to disk must pass `path_security.validate_write_path()` before any write
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt
- Context from external documents must go in the USER prompt, never the SYSTEM prompt

### 8. Language/runtime conformance
- Python version: `3.12`
- Type annotations required on every function
- Backend must use `async/await` throughout
- No blocking calls on the event loop
- Dataclasses required for all structured data

---

## Wire Format Examples

Only examples whose fields are explicitly defined in the source are shown as normative examples. Examples using unspecified message schemas are intentionally omitted.

### 1. Valid stdout startup signal

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

Why valid:
- Uses exact required prefix
- Includes `socket_path`

### 2. Invalid stdout startup signal

```text
LISTENING:/tmp/forge-agent.sock
```

Why invalid:
- Missing exact required prefix `FORGE_AGENT_LISTENING:`

---

### 3. Valid TrustFlow event

```json
{
  "event_id": "7f2d2c8f-1f56-4c2f-9b7d-8fd8af6c7c91",
  "session_id": "sess_42",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

Why valid:
- Includes all required TrustFlow fields
- `ts` shown as Unix timestamp in milliseconds
- `payload_hash` shown as SHA-256 hex string

### 4. Invalid TrustFlow event: missing required field

```json
{
  "event_id": "7f2d2c8f-1f56-4c2f-9b7d-8fd8af6c7c91",
  "session_id": "sess_42",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

Why invalid:
- Missing required `ctx_id`

### 5. Invalid TrustFlow event: wrong timestamp precision

```json
{
  "event_id": "7f2d2c8f-1f56-4c2f-9b7d-8fd8af6c7c91",
  "session_id": "sess_42",
  "ctx_id": "ctx_abc123",
  "ts": 1735689600,
  "event_type": "restrict",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

Why invalid:
- `ts` must have millisecond precision, not second precision

---

### 6. Valid VTZ enforcement decision

```json
{
  "verdict": "block"
}
```

Why valid:
- On VTZ denial, required `verdict=block`

### 7. Invalid VTZ enforcement decision

```json
{
  "verdict": "allow"
}
```

Why invalid:
- For a VTZ policy denial, the verdict must be exactly `block`

---

### 8. Invalid security handling example

```json
{
  "llm_output": "SECURITY_REFUSAL",
  "behavior": "retry_with_different_model"
}
```

Why invalid:
- When `SECURITY_REFUSAL` is observed, the system must stop, gate, and log
- Retrying to bypass is forbidden

---

## Integration Points

### 1. Swift ↔ backend XPC
- Swift reads Keychain
- Swift sends credentials via XPC
- Backend waits up to `30s` for credentials
- Backend sends:
  - ready message including `agent_version`, `capabilities`
  - `auth_error` XPC card on credential-related initialization failure

### 2. Backend stdout ↔ Swift bootstrap
- Backend prints `FORGE_AGENT_LISTENING:{socket_path}` to stdout
- Swift reads this line to discover socket path

### 3. Backend ↔ GitHub
- All GitHub operations must go through `GitHubTool`
- Direct GitHub API calls from pipeline code are forbidden

### 4. Backend ↔ Consensus engine
- `ConsensusEngine` is initialized with API keys
- Credential failures are non-fatal and must degrade gracefully with `auth_error`

### 5. Backend ↔ DocumentStore
- `DocumentStore` loading starts in background asynchronously
- Loaded document chunks must pass injection scanning before being included in any LLM prompt

### 6. Backend ↔ path security
- Any file path written to disk must be validated with:
  - `path_security.validate_write_path()`

### 7. Backend ↔ TrustFlow
- TrustFlow event emission is mandatory for every action outcome
- Emission is part of the enforcement path and must be synchronous

### 8. Backend ↔ CAL / CTX-ID / VTZ enforcement
- Every action-processing entry point must integrate:
  1. CTX-ID validation
  2. VTZ policy check
  3. TrustFlow emission
- Failure at any of these steps must not be silently ignored

---

## Non-Specified Interfaces

The provided source does **not** define complete field-level schemas for the following payloads, so no additional fields are contractually specified here:

- Credentials XPC payload
- Ready message `capabilities` element schema
- `auth_error` XPC card body
- Agent action payload schema
- CTX-ID token field schema
- Full `VTZEnforcementDecision` schema beyond `verdict`
- `event_type` enumeration for TrustFlow beyond requiring the field itself

Implementations must not invent compatibility assumptions and should treat these as undefined until the owning TRD provides the concrete schema.