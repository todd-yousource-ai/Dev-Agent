# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the **ConsensusDevAgent** subsystem based strictly on the provided TRD and standards excerpts.

Where the source defines exact field names, values, ordering, or constraints, they are reproduced exactly.

### 1. Startup Sequence Signals

#### 1.1 Stdout readiness line

Printed by backend during startup.

- **Type:** plain text line
- **Format:** `FORGE_AGENT_LISTENING:{socket_path}`

##### Fields

| Name | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | yes | Inserted after the literal prefix `FORGE_AGENT_LISTENING:` |

##### Constraints

- Must be emitted at startup step 3.
- Must occur **after**:
  1. Initialize logger
  2. Start XPC server, listen on socket
- Must occur **before**:
  4. Wait for credentials via XPC (timeout: 30s)

---

### 2. XPC Credential Delivery

The backend waits for credentials via XPC.

#### 2.1 Credential wait contract

| Name | Type | Required | Constraints |
|---|---|---:|---|
| `timeout` | integer | yes | Exact value: `30` seconds |

##### Constraints

- Backend must wait for credentials via XPC.
- Timeout is exactly `30s`.
- Python backend must not read Keychain directly.
- Only Swift reads Keychain, only to deliver via XPC.

---

### 3. XPC Ready Message

Sent after initialization.

#### 3.1 Ready message payload

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Included in ready message |
| `capabilities` | array | yes | Included in ready message |

##### Constraints

- Sent at startup step 8.
- Must be sent via XPC.
- Must occur after:
  - GitHubTool initialization attempt
  - ConsensusEngine initialization attempt
  - DocumentStore background loading start
- Steps 5-6 are non-fatal on credential errors.
- On credential errors in steps 5-6, subsystem continues in degraded state.

---

### 4. XPC Auth Error Card

When credential initialization fails in steps 5-6.

#### 4.1 Auth error card

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `auth_error` | object or card type discriminator | implied | Exact card name/value referenced: `auth_error` |

##### Constraints

- On GitHubTool or ConsensusEngine credential error during startup, backend must emit `auth_error` XPC card.
- Backend must continue in degraded state.
- No additional fields are specified in the provided source.

---

### 5. TrustFlow Event

Every action outcome must emit a TrustFlow event.

#### 5.1 TrustFlow event structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | Must be globally unique; CSPRNG; not sequential |
| `session_id` | string | yes | Required on every event |
| `ctx_id` | string | yes | Required on every event |
| `ts` | number | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Required on every event |
| `payload_hash` | string | yes | Must be SHA-256 of the serialized action payload |

##### Constraints

- Every TrustFlow event must include exactly the listed required fields at minimum.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.
- TrustFlow emission failure must not silently continue; log and surface the failure.

---

### 6. VTZEnforcementDecision Record

Produced when VTZ policy denies an action.

#### 6.1 VTZEnforcementDecision

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | Exact required value on denial: `block` |

##### Constraints

- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 7. Action Payload for Enforcement Path

The exact full action payload schema is not provided in the source, but a serialized action payload is required for hashing.

#### 7.1 Serialized action payload

| Field | Type | Required | Constraints |
|---|---|---:|---|
| action payload | serialized object/blob | yes | Input to SHA-256 for `payload_hash` |

##### Constraints

- `payload_hash` must be SHA-256 of the serialized action payload.
- Every entry point that processes an agent action must validate `CTX-ID` first.
- Every action must be checked against VTZ policy before execution.

---

### 8. CTX-ID Token

The exact token wire schema is not provided. The following are mandatory behavioral constraints on any CTX-ID representation.

#### 8.1 CTX-ID semantic contract

| Property | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string/token | yes | Must be present on TrustFlow events; missing CTX-ID is treated as UNTRUSTED |

##### Constraints

- CTX-ID tokens are immutable once issued.
- No field modification after issuance.
- Rotation creates a new token.
- Old token is invalidated immediately.
- Expired CTX-ID must be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Never infer identity from context.

---

### 9. VTZ Session Binding

The full VTZ binding object schema is not provided; enforcement requirements are defined below.

#### 9.1 VTZ session binding contract

| Property | Type | Required | Constraints |
|---|---|---:|---|
| VTZ binding | session property | yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance |

##### Constraints

- Every agent session is bound to **EXACTLY ONE VTZ** at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

### 10. Document Loading / Prompt Inclusion Contract

#### 10.1 Loaded document chunk

| Field | Type | Required | Constraints |
|---|---|---:|---|
| document chunk | object/text chunk | yes | Must pass injection scanning before inclusion in any LLM prompt |

##### Constraints

- All loaded document chunks must pass injection scanning before being included in any LLM prompt.
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.

---

### 11. Filesystem Write Path Contract

#### 11.1 Write path validation

| Field | Type | Required | Constraints |
|---|---|---:|---|
| file path | string/path | yes | Must pass `path_security.validate_write_path()` before any write |

##### Constraints

- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

---

### 12. Logging/Error Content Contract

#### 12.1 HTTP error logging

| Field | Type | Required | Constraints |
|---|---|---:|---|
| HTTP status code | integer | yes | May be logged |
| error type | string | yes | May be logged |
| HTTP response body | string/object | no | Must never be logged |

##### Constraints

- Never log HTTP response bodies.
- Log status codes and error types only.

---

### 13. SECURITY_REFUSAL Handling

#### 13.1 LLM refusal output

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `SECURITY_REFUSAL` | string sentinel | yes when present | Exact sentinel string: `SECURITY_REFUSAL` |

##### Constraints

- When `SECURITY_REFUSAL` output is seen from the LLM: stop, gate, log.
- Never retry to bypass.
- The following behavior is explicitly forbidden:

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)  # WRONG — do not retry
```

---

### 14. GitHubTool Integration

#### 14.1 GitHub operations contract

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `GitHubTool` | backend component | yes | All GitHub operations go through this component |

##### Constraints

- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.
- Backend startup step 5: Initialize `GitHubTool` with token.

---

### 15. ConsensusEngine Integration

#### 15.1 Consensus engine initialization

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ConsensusEngine` | backend component | yes | Initialized with API keys |

##### Constraints

- Backend startup step 6: Initialize `ConsensusEngine` with API keys.
- Credential errors are non-fatal during startup.
- On credential error, emit `auth_error` XPC card and continue in degraded state.

---

### 16. DocumentStore Integration

#### 16.1 DocumentStore loading

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `DocumentStore` | backend component | yes | Loading starts in background (async) |

##### Constraints

- Startup step 7: Start `DocumentStore` loading in background (async).
- App must remain responsive while embeddings load.

---

### 17. CommandRouter Integration

#### 17.1 Event loop entry

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `CommandRouter` | backend component | yes | Enter event loop after ready message |

##### Constraints

- Startup step 9: Enter `CommandRouter` event loop.

---

## Enums and Constants

### 1. Literal Strings

| Name | Type | Exact Value |
|---|---|---|
| Listening line prefix | string | `FORGE_AGENT_LISTENING:` |
| Security refusal sentinel | string | `SECURITY_REFUSAL` |
| Auth error card name | string | `auth_error` |
| Trust decision verdict | string | `block` |
| Missing CTX-ID trust state | string | `UNTRUSTED` |
| Prompt role | string | `USER` |
| Forbidden prompt role for external documents | string | `SYSTEM` |

### 2. Action Outcome Values

The source explicitly names the following action outcomes:

| Value |
|---|
| `allow` |
| `restrict` |
| `block` |

### 3. Required Startup Order

Exact mandatory sequence:

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC (timeout: 30s)`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background (async)`
8. `Send ready message via XPC (includes agent_version, capabilities)`
9. `Enter CommandRouter event loop`

### 4. Runtime/Implementation Constants

| Name | Value |
|---|---|
| Python version | `3.12` |
| Credential wait timeout | `30s` |
| Timestamp precision | `millisecond` |
| Hash algorithm | `SHA-256` |
| TrustFlow uniqueness source | `CSPRNG` |
| Minimum new-module test coverage | `85%` |

---

## Validation Rules

## 1. CAL Enforcement Contract

Every entry point that processes an agent action must enforce all of the following:

1. `CTX-ID` validation must occur first.
2. If `CTX-ID` validation fails, reject immediately.
3. No partial processing is permitted after validation failure.
4. Every action must be checked against VTZ policy before execution.
5. VTZ denial must produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.
7. TrustFlow emission failure must not silently continue; it must be logged and surfaced.

## 2. TrustFlow Validation

For every TrustFlow event:

- `event_id`:
  - required
  - globally unique
  - generated via CSPRNG
  - not sequential
- `session_id`:
  - required
- `ctx_id`:
  - required
- `ts`:
  - required
  - UTC Unix timestamp
  - millisecond precision
- `event_type`:
  - required
- `payload_hash`:
  - required
  - must equal SHA-256 of serialized action payload

Emission rules:

- must be synchronous in enforcement path
- async buffering is not permitted
- failure is WARN-level audit event
- failure is never a silent skip

## 3. CTX-ID Validation

- Missing `CTX-ID` => treat as `UNTRUSTED`
- Expired `CTX-ID` => reject
- Validation must be against TrustLock public key
- Software-only validation is rejected
- CTX-ID is immutable once issued
- Rotation creates a new token and invalidates old token immediately
- Identity must never be inferred from surrounding context when CTX-ID is missing

## 4. VTZ Validation

- Each agent session has exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit authorization is denied
- VTZ boundary enforcement cannot be bypassed by application code
- Policy changes apply only at next CTX-ID issuance

## 5. Security Validation

- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Never use `shell=True` in subprocess calls
- Never call `eval()` or `exec()` on generated or external content
- Never log HTTP response bodies
- All write paths must pass `path_security.validate_write_path()` before write
- All loaded document chunks must pass injection scanning before inclusion in LLM prompt
- External document context must go in `USER` prompt, never `SYSTEM`
- On `SECURITY_REFUSAL`: stop, gate, log; never retry

## 6. Backend/Language Constraints

- Python `3.12`
- Type annotations on every function
- `async/await` throughout backend
- No blocking calls on event loop
- Dataclasses for all structured data
- Tests use `pytest`
- Tests live in `tests/` and mirror `src/`
- `ruff` must pass
- `mypy` must pass
- Coverage on new modules must be at least `85%`

## 7. Keychain/Credential Boundary

- Python reads nothing from Keychain
- Only Swift reads Keychain
- Swift may deliver credentials only via XPC

Forbidden examples from source:

```swift
// FORBIDDEN: Keychain read for backend
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
// Only Swift reads Keychain, only to deliver via XPC
```

```swift
// FORBIDDEN: LLM API call from Swift
let client = AnthropicClient(apiKey: keychainValue)
```

## 8. GitHub Integration Validation

- All GitHub operations must go through `GitHubTool`
- Never call GitHub API directly from pipeline code

---

## Wire Format Examples

## 1. Valid Examples

### 1.1 Valid stdout listening line

```text
FORGE_AGENT_LISTENING:/tmp/consensusdevagent.sock
```

### 1.2 Valid ready message

Exact transport framing is unspecified; minimum payload contract:

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

### 1.3 Valid TrustFlow event

```json
{
  "event_id": "7f6f5c5d-96df-4a6f-a7bb-0a1f1f88c4d4",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action_outcome",
  "payload_hash": "4e3b4c1a7d4f0b3c2e1a6d9b8c7f5e4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8"
}
```

### 1.4 Valid VTZEnforcementDecision on denial

```json
{
  "verdict": "block"
}
```

### 1.5 Valid external document prompt placement

```json
{
  "role": "USER",
  "content": "External document context after injection scanning"
}
```

---

## 2. Invalid Examples

### 2.1 Invalid TrustFlow event: missing required fields

```json
{
  "event_id": "123",
  "event_type": "action_outcome"
}
```

Invalid because:

- missing `session_id`
- missing `ctx_id`
- missing `ts`
- missing `payload_hash`

### 2.2 Invalid TrustFlow event: sequential/non-CSPRNG event_id

```json
{
  "event_id": "42",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action_outcome",
  "payload_hash": "4e3b4c1a7d4f0b3c2e1a6d9b8c7f5e4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8"
}
```

Invalid because `event_id` must be globally unique and generated by CSPRNG, not sequential.

### 2.3 Invalid VTZ denial decision

```json
{
  "verdict": "deny"
}
```

Invalid because the required denial verdict is exactly:

```json
{
  "verdict": "block"
}
```

### 2.4 Invalid prompt placement for external document context

```json
{
  "role": "SYSTEM",
  "content": "External document context"
}
```

Invalid because external document context must go in `USER`, never `SYSTEM`.

### 2.5 Invalid security-refusal retry behavior

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Invalid because `SECURITY_REFUSAL` must cause stop, gate, and log; never retry.

### 2.6 Invalid backend Keychain access

```swift
let token = KeychainKit.read("github_token")
```

Invalid because Python backend reads nothing from Keychain; only Swift reads Keychain to deliver via XPC.

### 2.7 Invalid direct GitHub API usage from pipeline code

```python
# direct GitHub API call from pipeline code
```

Invalid because all GitHub operations must go through `GitHubTool`.

### 2.8 Invalid write without path validation

```python
with open(user_path, "w") as f:
    f.write(data)
```

Invalid because all file paths written to disk must pass `path_security.validate_write_path()` before any write.

---

## Integration Points

## 1. Backend Startup Dependencies

### Required startup order

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC (`timeout: 30s`)
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (`async`)
8. Send ready message via XPC (`includes agent_version, capabilities`)
9. Enter `CommandRouter` event loop

### Non-fatal startup behavior

- Steps 5-6 are non-fatal on credential errors
- Emit `auth_error` XPC card
- Continue in degraded state

### Responsiveness contract

- Step 7 is always async
- App remains responsive while embeddings load

---

## 2. XPC Boundary

### Swift side

- Reads Keychain
- Delivers credentials via XPC
- Reads stdout listening line: `FORGE_AGENT_LISTENING:{socket_path}`

### Python side

- Waits for credentials via XPC
- Does not read Keychain
- Initializes backend components after receiving credentials or timeout/error path

---

## 3. Enforcement Path

For every agent action entry point:

1. Validate `CTX-ID` first
2. Reject immediately on validation failure
3. Check VTZ policy before execution
4. On VTZ denial, produce `VTZEnforcementDecision` with `verdict=block`
5. Emit TrustFlow event for outcome
6. If TrustFlow emission fails, log and surface failure

---

## 4. External Service Integration

### GitHub

- Integration point: `GitHubTool`
- No direct GitHub API calls from pipeline code

### LLM/Consensus

- Integration point: `ConsensusEngine`
- `SECURITY_REFUSAL` is terminal/gating behavior, not retryable

### Documents

- Integration point: `DocumentStore`
- Loaded chunks require injection scanning before LLM prompt inclusion

---

## 5. Testing and Conformance Hooks

Before modifying subsystem code:

1. Find the TRD that owns the component you are modifying
2. Read relevant TRD sections
3. Check TRD-11 if change touches credentials, external content, generated code, or CI
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Conformance requirements:

- `pytest`
- `ruff`
- `mypy`
- coverage `>= 85%` on all new modules

---

## 6. Unspecified Fields

The provided source does **not** define complete wire schemas for the following items:

- credential XPC payload fields
- `auth_error` card payload fields beyond the exact card name
- `CTX-ID` token internal field layout
- full action payload object schema
- full `VTZEnforcementDecision` fields beyond `verdict`
- XPC framing/envelope structure
- `capabilities` element type beyond being included in ready message
- `agent_version` version format constraints

Implementations must not invent incompatible field names where upstream TRDs define them elsewhere. Only the fields and constraints listed in this document are contractually defined from the supplied material.