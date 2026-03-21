# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements explicitly stated for the ConsensusDevAgent subsystem from the provided TRD/interface sources.

Where the source defines required fields, values, ordering, or behavior, they are listed exactly. No unstated fields should be assumed conformant.

---

### 1. TrustFlowEvent

Required by: **TrustFlow Emission Contract**

A TrustFlow event emitted synchronously in the enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | MUST be globally unique; MUST be generated via CSPRNG; MUST NOT be sequential |
| `session_id` | string | yes | Required on every TrustFlow event |
| `ctx_id` | string | yes | Required on every TrustFlow event |
| `ts` | number | yes | MUST be UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Required on every TrustFlow event |
| `payload_hash` | string | yes | MUST be SHA-256 of the serialized action payload |

#### Behavioral constraints
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission MUST NOT be a silent skip.
- Every action outcome `allow`, `restrict`, or `block` MUST emit a TrustFlow event.

---

### 2. VTZEnforcementDecision

Required by: **CAL Enforcement Contract**

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | On VTZ policy denial, MUST equal `block` |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 3. AgentActionPayload

Implied by: **CAL Enforcement Contract** and **TrustFlow Emission Contract**

Serialized action payload used to compute `payload_hash`.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _serialized payload_ | bytes/string | yes | `payload_hash` MUST be SHA-256 of the serialized action payload |

#### Behavioral constraints
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted before CTX-ID validation succeeds.

> Note: The TRD excerpt does not define the internal schema of the action payload itself, only that it must be serialized and hashed.

---

### 4. XPC Listening Announcement

Required by: **Backend Startup Sequence**

A stdout wire message emitted after the XPC server starts listening.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| entire message | string | yes | MUST be printed exactly as `FORGE_AGENT_LISTENING:{socket_path}` |
| `socket_path` | string | yes | Substituted into the message after the literal prefix `FORGE_AGENT_LISTENING:` |

#### Behavioral constraints
- Startup order is mandatory.
- This message MUST occur after:
  1. Initialize logger
  2. Start XPC server, listen on socket
- This message MUST occur before:
  4. Wait for credentials via XPC (timeout: 30s)

---

### 5. XPC Credentials Delivery

Required by: **Backend Startup Sequence**

Credentials are delivered via XPC.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| credentials | object | yes | Must be received via XPC |
| timeout | number | yes | Exactly `30s` |

#### Behavioral constraints
- Backend waits for credentials via XPC.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.
- Credential wait timeout is 30 seconds.

> Note: The TRD excerpt does not define the credential object field names.

---

### 6. Auth Error XPC Card

Required by: **Backend Startup Sequence**

Non-fatal authentication error notification over XPC.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| card type / identifier | string | yes | MUST be `auth_error` |

#### Behavioral constraints
- Step 5 (`Initialize GitHubTool with token`) and Step 6 (`Initialize ConsensusEngine with API keys`) are non-fatal on credential errors.
- On such errors, the system MUST emit `auth_error` XPC card.
- The system MUST continue in degraded state.

> Note: The TRD excerpt does not define additional fields for the `auth_error` card.

---

### 7. Ready Message via XPC

Required by: **Backend Startup Sequence**

Sent after background document loading begins.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | MUST be included in ready message |
| `capabilities` | array | yes | MUST be included in ready message |

#### Behavioral constraints
- Sent at step 8 of startup.
- Must occur after:
  7. Start DocumentStore loading in background (async)
- Must occur before:
  9. Enter CommandRouter event loop

> Note: The TRD excerpt does not define the element type or allowed values of `capabilities`.

---

### 8. SECURITY_REFUSAL Output Handling

Required by: **Security**

Represents a special LLM output condition.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| output token | string | yes | Exact value: `SECURITY_REFUSAL` |

#### Behavioral constraints
- When `SECURITY_REFUSAL` appears in LLM output: stop, gate, log.
- Never retry to bypass.
- The following behavior is explicitly forbidden:
  - retrying generation when `"SECURITY_REFUSAL" in output`

---

### 9. File Write Path Validation Interface

Required by: **Security**

Validation requirement before any disk write.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| path | string | yes | All file paths written to disk must pass validation |
| validator | callable/interface | yes | Exact interface name: `path_security.validate_write_path()` |

#### Behavioral constraints
- Validation MUST occur before any write.

---

### 10. Document Chunk Injection Scan Interface

Required by: **Security**

Validation before external document content is included in prompts.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| loaded document chunk | string/object | yes | Every loaded document chunk must pass injection scanning |
| target prompt role | string | yes | External document context goes in `USER` prompt, never `SYSTEM` prompt |

#### Behavioral constraints
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

---

### 11. GitHubTool Initialization

Required by: **Backend Startup Sequence** and **GitHub Operations**

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `token` | string | yes | Used to initialize `GitHubTool` |

#### Behavioral constraints
- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.
- Initialization occurs at startup step 5.
- Credential errors are non-fatal; emit `auth_error` XPC card and continue in degraded state.

---

### 12. ConsensusEngine Initialization

Required by: **Backend Startup Sequence**

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `api keys` | object/collection | yes | Used to initialize `ConsensusEngine` |

#### Behavioral constraints
- Initialization occurs at startup step 6.
- Credential errors are non-fatal; emit `auth_error` XPC card and continue in degraded state.

> Note: The TRD excerpt does not define API key field names.

---

### 13. DocumentStore Background Load Trigger

Required by: **Backend Startup Sequence**

| Field | Type | Required | Constraints |
|---|---|---:|---|
| loading mode | string | yes | MUST be background / async |

#### Behavioral constraints
- `DocumentStore` loading starts in background at startup step 7.
- Step 7 is always async.
- The app is responsive while embeddings load.

---

### 14. CommandRouter Event Loop Entry

Required by: **Backend Startup Sequence**

| Field | Type | Required | Constraints |
|---|---|---:|---|
| event loop state | string | yes | Entered at startup step 9 |

---

## Enums and Constants

### Exact string constants

| Name | Type | Exact Value |
|---|---|---|
| Security refusal token | string | `SECURITY_REFUSAL` |
| XPC listening prefix/message format | string | `FORGE_AGENT_LISTENING:{socket_path}` |
| Auth error card identifier | string | `auth_error` |
| VTZ deny verdict | string | `block` |
| Prompt role | string | `USER` |
| Prompt role | string | `SYSTEM` |

### Action outcome values

Required by **CAL Enforcement Contract**

| Enum | Allowed Values |
|---|---|
| action outcome | `allow`, `restrict`, `block` |

### Startup sequence constants

| Name | Type | Exact Value |
|---|---|---|
| credentials timeout | duration | `30s` |

### Required implementation/interface names

| Name | Kind | Exact Value |
|---|---|---|
| path validation function | interface | `path_security.validate_write_path()` |
| GitHub client wrapper | type/service | `GitHubTool` |
| consensus engine | type/service | `ConsensusEngine` |
| document store | type/service | `DocumentStore` |
| router | type/service | `CommandRouter` |

---

## Validation Rules

### CAL enforcement
1. Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted before CTX-ID validation succeeds.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every action outcome `allow`, `restrict`, or `block` MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure must be logged and surfaced.

### TrustFlow event validation
1. `event_id` is required.
2. `event_id` MUST be globally unique.
3. `event_id` MUST be generated using CSPRNG.
4. `event_id` MUST NOT be sequential.
5. `session_id` is required.
6. `ctx_id` is required.
7. `ts` is required.
8. `ts` MUST be a UTC Unix timestamp with millisecond precision.
9. `event_type` is required.
10. `payload_hash` is required.
11. `payload_hash` MUST equal the SHA-256 of the serialized action payload.
12. Emission MUST be synchronous in the enforcement path.
13. Async buffering is not permitted.

### CTX-ID validation
1. CTX-ID tokens are IMMUTABLE once issued.
2. No field modification is allowed after issuance.
3. CTX-ID rotation creates a new token.
4. The old token is invalidated immediately on rotation.
5. Expired CTX-ID MUST be rejected.
6. Clock skew tolerance is defined per deployment.
7. CTX-ID MUST be validated against TrustLock public key.
8. Software-only validation is rejected.
9. Missing CTX-ID MUST be treated as `UNTRUSTED`.
10. Identity must never be inferred from context when CTX-ID is missing.

### VTZ enforcement
1. Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit cross-VTZ access is denied.
4. VTZ boundaries are structural, not advisory.
5. Enforcement cannot be bypassed by application code.
6. VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

### Security validation
1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Log status codes and error types only.
6. All file paths written to disk must pass `path_security.validate_write_path()` before any write.
7. All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
8. Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.
9. When `SECURITY_REFUSAL` appears: stop, gate, log.
10. Never retry to bypass `SECURITY_REFUSAL`.

### Backend startup ordering
Order is mandatory and MUST be exactly:

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC (timeout: `30s`)
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (async)
8. Send ready message via XPC (includes `agent_version`, `capabilities`)
9. Enter `CommandRouter` event loop

Additional startup rules:
- Steps 5-6 are non-fatal on credential errors.
- On credential errors in steps 5-6, emit `auth_error` XPC card.
- Continue in degraded state.
- Step 7 is always async.
- The app must remain responsive while embeddings load.

### Platform boundary rules
1. Only Swift reads Keychain.
2. Swift may read Keychain only to deliver credentials via XPC.
3. Python reads nothing from Keychain.
4. LLM API calls from Swift are forbidden.

### Python implementation constraints
1. Python version: `3.12`
2. Type annotations on every function.
3. `async/await` throughout the backend.
4. No blocking calls on the event loop.
5. Dataclasses for all structured data.
6. Tests use `pytest`.
7. Tests live in `tests/` and mirror `src/` structure.
8. `ruff` must pass clean.
9. `mypy` must pass clean.
10. Test coverage must be `≥ 85%` on all new modules.

---

## Wire Format Examples

## Valid payloads

### TrustFlow event
```json
{
  "event_id": "7f4d3a9c-9b7f-4d38-92e5-3d7db5f4d6aa",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action_executed",
  "payload_hash": "5f70bf18a08660b4f5c6e7a0c0f6b7c9e5d4a2b7c6d8e9f00112233445566778"
}
```

### VTZ enforcement denial record
```json
{
  "verdict": "block"
}
```

### Ready message via XPC
```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "document_store"]
}
```

### Stdout listening announcement
```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### Action outcome values
```json
{
  "outcome": "allow"
}
```

```json
{
  "outcome": "restrict"
}
```

```json
{
  "outcome": "block"
}
```

## Invalid payloads

### Invalid TrustFlow event: missing required field
```json
{
  "event_id": "7f4d3a9c-9b7f-4d38-92e5-3d7db5f4d6aa",
  "session_id": "sess_123",
  "ts": 1735689600123,
  "event_type": "action_executed",
  "payload_hash": "5f70bf18a08660b4f5c6e7a0c0f6b7c9e5d4a2b7c6d8e9f00112233445566778"
}
```

Reason: `ctx_id` is required.

### Invalid VTZ denial record
```json
{
  "verdict": "deny"
}
```

Reason: on VTZ policy denial, `verdict` MUST be exactly `block`.

### Invalid ready message
```json
{
  "agent_version": "1.0.0"
}
```

Reason: `capabilities` is required.

### Invalid stdout announcement
```text
FORGE_AGENT_READY:/tmp/forge-agent.sock
```

Reason: stdout message MUST be exactly `FORGE_AGENT_LISTENING:{socket_path}`.

### Invalid prompt placement
```json
{
  "role": "SYSTEM",
  "content": "External document context here"
}
```

Reason: external document context goes in `USER` prompt, never `SYSTEM` prompt.

### Invalid SECURITY_REFUSAL handling
```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Reason: retrying to bypass `SECURITY_REFUSAL` is forbidden.

### Invalid backend credential source
```python
token = KeychainKit.read("github_token")
```

Reason: Python reads nothing from Keychain.

### Invalid Swift backend LLM call
```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Reason: LLM API call from Swift is forbidden.

---

## Integration Points

### XPC
Used for:
- credential delivery to backend
- `auth_error` card emission
- ready message delivery including `agent_version` and `capabilities`

### stdout
Used for:
- listening announcement in exact format `FORGE_AGENT_LISTENING:{socket_path}`

### GitHub integration
- All GitHub operations go through `GitHubTool`
- Direct GitHub API calls from pipeline code are non-conformant

### Consensus engine integration
- Backend initializes `ConsensusEngine` with API keys
- Credential errors are non-fatal and must emit `auth_error`

### Document loading / prompt construction
- `DocumentStore` loads in background asynchronously
- Loaded document chunks must pass injection scanning before inclusion in prompts
- External document context must be placed in `USER` prompt only

### File system writes
- Every path written to disk must be validated through `path_security.validate_write_path()` before write

### Trust and enforcement path
- CTX-ID validation occurs first
- VTZ policy check occurs before execution
- Denials produce `VTZEnforcementDecision` with `verdict=block`
- All outcomes emit synchronous TrustFlow events with required fields

### Keychain / platform boundary
- Only Swift reads Keychain
- Swift delivers credentials via XPC
- Python reads nothing from Keychain

### Test and quality gates
- Run existing tests before changes:
  - `cd src && pytest ../tests/ -v --tb=short`
- New modules must satisfy:
  - `pytest`
  - `ruff`
  - `mypy`
  - coverage `≥ 85%`

---

## Notes on Undefined Fields

The following interfaces are referenced but their full field schemas are **not defined in the provided source**:
- XPC credentials payload
- `auth_error` XPC card payload beyond its identifier/type
- `ConsensusEngine` API key field names
- `capabilities` element schema/allowed values
- internal action payload schema used before serialization
- CTX-ID token internal field layout
- VTZ identity field schema
- DTL Label schema

These fields must not be invented without the owning TRD section.