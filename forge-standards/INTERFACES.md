# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements that apply to the `ConsensusDevAgent` subsystem based on the provided TRD/interface material.

Where a field is mandated by contract text, it is listed explicitly. Where the source does not define a full object schema, only the exact required fields and constraints are specified.

---

### 1. TrustFlowEvent

Synchronous audit/enforcement event emitted for every action outcome.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | string | yes | Required on every TrustFlow event. |
| `ctx_id` | string | yes | Required on every TrustFlow event. Must reference the validated CTX-ID for the action. |
| `ts` | number \| string | yes | MUST be UTC Unix timestamp with millisecond precision. |
| `event_type` | string | yes | Required on every TrustFlow event. |
| `payload_hash` | string | yes | MUST be SHA-256 of the serialized action payload. |

#### Behavioral requirements
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- TrustFlow emission failure MUST NOT silently continue.
- Failed emission is a WARN-level audit event.

---

### 2. VTZEnforcementDecision

Decision record produced when VTZ policy denies an action.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | MUST equal `block` when produced for VTZ policy denial. |

#### Behavioral requirements
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 3. XPCReadyMessage

Ready notification sent after startup initialization reaches the ready stage.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Included in the ready message via XPC. |
| `capabilities` | array | yes | Included in the ready message via XPC. Element type is not further specified in source. |

#### Startup ordering constraints
This message MUST be sent only after:
1. logger initialization
2. XPC server start and socket listen
3. stdout line `FORGE_AGENT_LISTENING:{socket_path}`
4. waiting for credentials via XPC, timeout `30s`
5. `GitHubTool` initialization with token
6. `ConsensusEngine` initialization with API keys
7. `DocumentStore` loading started in background async

This message corresponds to startup step 8.

---

### 4. AuthErrorXPCCard

Credential/authentication degradation notification sent over XPC.

#### Type
Object

#### Fields
The source defines the message/card name but does not define payload fields.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _implementation-defined_ | unknown | unknown | Source only requires emission of an `auth_error` XPC card on credential errors. |

#### Behavioral requirements
- Steps 5 and 6 of startup are non-fatal on credential errors.
- On such errors, the backend MUST emit an `auth_error` XPC card.
- The backend MUST continue in degraded state.

---

### 5. ListeningAnnouncement

Stdout wire line consumed by Swift to discover the socket path.

#### Type
String line

#### Format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Components

| Component | Type | Required | Constraints |
|---|---|---:|---|
| `FORGE_AGENT_LISTENING:` | string literal prefix | yes | MUST match exactly. |
| `{socket_path}` | string | yes | Socket path value appended directly after the colon. |

#### Behavioral requirements
- Must be printed to stdout after XPC server starts listening on the socket.
- Swift reads this line.

---

### 6. SECURITY_REFUSAL Output

LLM security refusal sentinel.

#### Type
String sentinel in model output

#### Value
```text
SECURITY_REFUSAL
```

#### Behavioral requirements
- When `SECURITY_REFUSAL` appears in output: stop, gate, log.
- Never retry to bypass.
- Ignoring `SECURITY_REFUSAL` is forbidden.

---

### 7. CTX-ID Token

Identity/token used for trust enforcement.

#### Type
Opaque token represented by string or implementation-defined structured token.

#### Contract-defined properties

| Property | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | Must be present on every TrustFlow event. Missing CTX-ID MUST be treated as `UNTRUSTED`. |

#### Behavioral requirements
- CTX-ID validation MUST be called FIRST at every entry point that processes an agent action.
- Validation failure MUST result in immediate rejection.
- No partial processing is allowed after validation failure.
- CTX-ID tokens are IMMUTABLE once issued.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity must never be inferred from context in place of CTX-ID.

---

### 8. Agent Action Payload

Serialized action payload used as the basis for `payload_hash`.

#### Type
Serialized object/bytes/string, implementation-defined.

#### Requirements
- `payload_hash` in TrustFlow events MUST be the SHA-256 of the serialized action payload.
- Every action that processes an agent action is subject to:
  1. CTX-ID validation first
  2. VTZ policy check before execution
  3. TrustFlow event emission for outcome

---

### 9. GitHubTool Initialization Input

Credential input used to initialize `GitHubTool`.

#### Type
Object or parameter set, implementation-defined.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `token` | string | yes | Used to initialize `GitHubTool` in startup step 5. |

#### Behavioral requirements
- All GitHub operations go through `GitHubTool`.
- Pipeline code MUST NEVER call the GitHub API directly.
- Credential errors during initialization are non-fatal and must emit `auth_error` XPC card.

---

### 10. ConsensusEngine Initialization Input

Credential input used to initialize `ConsensusEngine`.

#### Type
Object or parameter set, implementation-defined.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `api_keys` | array \| object | yes | Used to initialize `ConsensusEngine` in startup step 6. Exact shape not defined in source. |

#### Behavioral requirements
- Credential/API key errors during initialization are non-fatal and must emit `auth_error` XPC card.
- Backend continues in degraded state.

---

### 11. Document Chunk Prompt Input

Loaded external document content eligible for inclusion in an LLM prompt.

#### Type
Object or text chunk, implementation-defined.

#### Required processing constraints
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt.
- Context from external documents MUST NEVER go in the SYSTEM prompt.

---

### 12. File Write Path

Filesystem path for any write operation.

#### Type
String path

#### Required processing constraints
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

---

### 13. Credentials via XPC

Credentials delivered from Swift to backend over XPC.

#### Type
Object or message, implementation-defined.

#### Behavioral requirements
- Backend waits for credentials via XPC.
- Timeout is `30s`.
- Only Swift reads Keychain.
- Swift may deliver credentials via XPC.
- Python reads nothing from Keychain.

---

## Enums and Constants

### Action Outcome
String enum values required for TrustFlow emission:

| Value |
|---|
| `allow` |
| `restrict` |
| `block` |

---

### VTZ Enforcement Verdict

| Value |
|---|
| `block` |

---

### CTX-ID Missing Identity State

| Value |
|---|
| `UNTRUSTED` |

---

### Security Refusal Sentinel

| Value |
|---|
| `SECURITY_REFUSAL` |

---

### Stdout Startup Prefix

| Value |
|---|
| `FORGE_AGENT_LISTENING:` |

---

### XPC Card Type

| Value |
|---|
| `auth_error` |

---

### Required Startup Timeout

| Constant | Value |
|---|---|
| credential wait timeout | `30s` |

---

### Runtime/Implementation Constants

| Constant | Value |
|---|---|
| Python version | `3.12` |

---

## Validation Rules

### A. Entry Point Enforcement
Every entry point that processes an agent action MUST:

1. Call CTX-ID validation FIRST.
2. Immediately reject on CTX-ID validation failure.
3. Perform VTZ policy check BEFORE execution.
4. Produce `VTZEnforcementDecision` with `verdict=block` on VTZ denial.
5. Emit a TrustFlow event for every outcome.
6. Not silently continue if TrustFlow emission fails.

---

### B. TrustFlow Event Validation

A `TrustFlowEvent` is valid only if all of the following hold:

- `event_id` is present.
- `event_id` is globally unique.
- `event_id` is generated by CSPRNG.
- `event_id` is not sequential.
- `session_id` is present.
- `ctx_id` is present.
- `ts` is present.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `event_type` is present.
- `payload_hash` is present.
- `payload_hash` equals the SHA-256 of the serialized action payload.

Invalid if any required field is missing or any generation/format constraint is violated.

---

### C. CTX-ID Validation Rules

A CTX-ID is invalid if any of the following are true:

- missing
- expired
- fails validation against TrustLock public key
- modified after issuance
- superseded by rotation/invalidation

Additional rules:

- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Software-only validation is rejected.
- Clock skew tolerance is deployment-defined, not specified here.

---

### D. VTZ Rules

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

### E. Startup Sequence Validation

The startup sequence is valid only in this exact order:

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC (timeout: `30s`)
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (async)
8. Send ready message via XPC (includes `agent_version`, `capabilities`)
9. Enter `CommandRouter` event loop

Reordering is non-conformant.

---

### F. Security Validation Rules

The following are mandatory:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- Every file write path must pass `path_security.validate_write_path()` before write.
- Every loaded document chunk must pass injection scanning before inclusion in any LLM prompt.
- External document context must go in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log; never retry.

---

### G. Language and Implementation Rules

- Python backend code MUST use Python `3.12`.
- Type annotations are required on every function.
- `async/await` throughout backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- Tests use `pytest`.
- Tests live in `tests/` and mirror `src/`.
- `ruff` and `mypy` must pass clean.
- Test coverage must be `≥ 85%` on all new modules.

---

### H. Keychain/XPC Boundary Rules

- Swift may read Keychain.
- Python/backend reads nothing from Keychain.
- Credentials are delivered via XPC.
- LLM API calls from Swift are forbidden.

---

### I. GitHub Integration Rules

- All GitHub operations MUST go through `GitHubTool`.
- Pipeline code MUST NEVER call the GitHub API directly.

---

## Wire Format Examples

## Valid payloads

### 1. Valid TrustFlowEvent
```json
{
  "event_id": "0d8f5b6b-1b6e-4f8d-9db7-3ec9df0f6b85",
  "session_id": "sess_01JABCDEF",
  "ctx_id": "ctx_01JCTXVALID",
  "ts": 1735689600123,
  "event_type": "action_execution",
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa135014a5b7a4a29f0fcb8f7e5d4e5a"
}
```

Why valid:
- Contains all required TrustFlow fields.
- `ts` is represented as Unix timestamp with millisecond precision.
- `payload_hash` is a SHA-256 hex string.

---

### 2. Valid VTZEnforcementDecision
```json
{
  "verdict": "block"
}
```

Why valid:
- Uses the exact required denial verdict.

---

### 3. Valid XPCReadyMessage
```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "document_store"]
}
```

Why valid:
- Includes both required fields.
- Sent only at startup step 8.

---

### 4. Valid stdout listening announcement
```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

Why valid:
- Matches exact required prefix and includes a socket path.

---

### 5. Valid security refusal output
```text
SECURITY_REFUSAL
```

Why valid:
- Exact sentinel value required by security handling logic.

---

## Invalid payloads

### 1. Invalid TrustFlowEvent: missing `payload_hash`
```json
{
  "event_id": "0d8f5b6b-1b6e-4f8d-9db7-3ec9df0f6b85",
  "session_id": "sess_01JABCDEF",
  "ctx_id": "ctx_01JCTXVALID",
  "ts": 1735689600123,
  "event_type": "action_execution"
}
```

Why invalid:
- `payload_hash` is mandatory.

---

### 2. Invalid TrustFlowEvent: missing `ctx_id`
```json
{
  "event_id": "0d8f5b6b-1b6e-4f8d-9db7-3ec9df0f6b85",
  "session_id": "sess_01JABCDEF",
  "ts": 1735689600123,
  "event_type": "action_execution",
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa135014a5b7a4a29f0fcb8f7e5d4e5a"
}
```

Why invalid:
- Every TrustFlow event MUST include `ctx_id`.
- Missing CTX-ID is treated as `UNTRUSTED` and is not a valid normal TrustFlow payload for a validated action.

---

### 3. Invalid VTZEnforcementDecision
```json
{
  "verdict": "deny"
}
```

Why invalid:
- Contract requires `verdict=block` for VTZ policy denial.

---

### 4. Invalid listening announcement
```text
LISTENING:/tmp/forge-agent.sock
```

Why invalid:
- Prefix must be exactly `FORGE_AGENT_LISTENING:`.

---

### 5. Invalid startup ready message
```json
{
  "capabilities": ["github"]
}
```

Why invalid:
- `agent_version` is required.

---

### 6. Invalid security handling pattern
```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Why invalid:
- Forbidden retry behavior.
- Required behavior is stop, gate, log.

---

### 7. Invalid backend credential source
```python
token = KeychainKit.read("github_token")
```

Why invalid:
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

---

### 8. Invalid Swift LLM API call
```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Why invalid:
- LLM API call from Swift is forbidden.

---

## Integration Points

### 1. Swift ↔ Backend XPC
Purpose:
- Deliver credentials from Swift to backend.
- Receive ready message and auth degradation messages.

Known wire elements:
- Credentials delivered via XPC, timeout `30s`.
- Ready message includes:
  - `agent_version`
  - `capabilities`
- Auth failure/degraded-state message:
  - `auth_error` XPC card

Constraints:
- Swift reads Keychain.
- Python/backend does not read Keychain.

---

### 2. Stdout ↔ Swift bootstrap discovery
Purpose:
- Advertise backend socket path for Swift.

Wire format:
```text
FORGE_AGENT_LISTENING:{socket_path}
```

Consumer:
- Swift

Ordering:
- Must occur after XPC server starts listening.

---

### 3. Backend ↔ GitHubTool
Purpose:
- All GitHub operations.

Constraints:
- Initialize `GitHubTool` with token.
- All GitHub operations MUST go through `GitHubTool`.
- No direct GitHub API access from pipeline code.

---

### 4. Backend ↔ ConsensusEngine
Purpose:
- Consensus functionality initialized with API keys.

Constraints:
- Initialization occurs at startup step 6.
- Credential errors are non-fatal and trigger `auth_error` XPC card.

---

### 5. Backend ↔ DocumentStore
Purpose:
- Background document loading.

Constraints:
- Loading starts in background async.
- App remains responsive while embeddings load.
- All loaded document chunks must pass injection scanning before prompt inclusion.

---

### 6. Backend ↔ TrustFlow
Purpose:
- Synchronous enforcement-path event emission.

Required event fields:
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Constraints:
- Emission is synchronous.
- Async buffering is not permitted.
- Failure is WARN-level audit event and must be surfaced.

---

### 7. Backend ↔ CTX-ID / TrustLock Validation
Purpose:
- Validate CTX-ID before action processing.

Constraints:
- Validation occurs first.
- Validation must use TrustLock public key.
- Software-only validation is rejected.

---

### 8. Backend ↔ VTZ Policy Enforcement
Purpose:
- Policy enforcement before action execution.

Constraints:
- Exactly one VTZ per agent session at CTX-ID issuance.
- Cross-VTZ requires explicit authorization.
- Denials produce `VTZEnforcementDecision` with `verdict=block`.

---

### 9. Backend ↔ Filesystem
Purpose:
- Any disk write.

Constraints:
- All write paths must pass `path_security.validate_write_path()` before write.

---

### 10. Backend ↔ LLM Prompt Construction
Purpose:
- Include external document context safely.

Constraints:
- Document chunks must pass injection scanning first.
- External document context goes in USER prompt only.
- Never place external document context in SYSTEM prompt.
- On `SECURITY_REFUSAL`, stop, gate, log; never retry.

---

## Notes on Unspecified Shapes

The provided source material does **not** define complete field-level payload schemas for:
- credentials via XPC
- `auth_error` XPC card payload
- `ConsensusEngine` API key object shape
- document chunk object fields
- command router message formats
- GitHubTool operation request/response bodies

These interfaces are therefore implementation-defined beyond the exact mandatory names and constraints listed above. Only the explicitly specified fields and values in this document are normative from the provided source.