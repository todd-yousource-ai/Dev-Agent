# Interface Contracts - ConsensusDevAgent

This document defines the wire-format and API contract requirements for the `ConsensusDevAgent` subsystem, derived from the provided TRD content and Forge interface contracts.

## Data Structures

Only structures explicitly defined or implied by the source material are included here.

### TrustFlowEvent

Represents the required audit event emitted for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique. MUST be generated using CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | Yes | Session identifier. No format specified in source. |
| `ctx_id` | `string` | Yes | CTX-ID token identifier associated with the action. Missing `ctx_id` MUST be treated as untrusted and rejected by enforcement logic. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type value. No closed enum provided in source. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Notes
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be treated as a WARN-level audit event and MUST NOT be silently skipped.

---

### VTZEnforcementDecision

Represents the required record produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | MUST be exactly `block` when VTZ policy denial occurs. |

#### Notes
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### ReadyMessage

Represents the XPC ready message sent after startup initialization.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | `string` | Yes | Included in the ready message via XPC. |
| `capabilities` | `array` | Yes | Included in the ready message via XPC. Element type not specified in source. |

---

### AuthErrorCard

Represents the XPC auth error message/card emitted on credential initialization failure.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `auth_error` | `object` | Yes | Exact inner schema not specified in source. Presence is implied by “emit auth_error XPC card”. |

#### Notes
- Startup steps 5 and 6 are non-fatal on credential errors.
- On credential errors, the backend MUST emit an `auth_error` XPC card and continue in degraded state.

---

### ListeningAnnouncement

Represents the stdout startup announcement consumed by Swift.

This is a line-oriented string, not a JSON object.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | `string` | Yes | Emitted as part of the exact stdout format below. |

#### Wire Representation
```text
FORGE_AGENT_LISTENING:{socket_path}
```

- Prefix MUST be exactly `FORGE_AGENT_LISTENING:`
- `{socket_path}` is the listening socket path
- This line is read by Swift

---

### AgentActionPayload

Represents the serialized payload of an agent action for hashing and enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `payload` | `object` | Yes | Exact schema not specified in source. Serialized form is hashed using SHA-256 to produce `payload_hash`. |

#### Notes
- Every entry point that processes an agent action MUST validate `CTX-ID` first.
- Validation failure MUST result in immediate rejection with no partial processing.
- Every action MUST be checked against VTZ policy before execution.

---

### CredentialsViaXPC

Represents credentials delivered from Swift to the backend over XPC.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `token` | `string` | Conditional | Used to initialize `GitHubTool` with token. |
| `api_keys` | `object` | Conditional | Used to initialize `ConsensusEngine` with API keys. Exact schema not specified in source. |

#### Notes
- Backend waits for credentials via XPC with timeout `30s`.
- Python backend MUST NOT read from Keychain.
- Only Swift reads Keychain, only to deliver credentials via XPC.
- Credential literals MUST NEVER be hardcoded.

---

### CTXIDToken

Represents a CTX-ID token under the enforcement contract.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Immutable once issued. |
| `vtz_binding` | `string` | Yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance. |
| `expired` | `boolean` | Yes | Expired CTX-ID MUST be rejected. |
| `invalidated` | `boolean` | Yes | Rotation creates a new token; old token is invalidated immediately. |

#### Notes
- Exact wire schema is not provided in source; fields above express mandatory contract state, not a normative serialized shape.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.

## Enums and Constants

### Required Literal Values

| Name | Type | Value |
|---|---|---|
| Listening prefix | `string` | `FORGE_AGENT_LISTENING:` |
| Security refusal sentinel | `string` | `SECURITY_REFUSAL` |
| VTZ deny verdict | `string` | `block` |
| Missing CTX-ID trust state | `string` | `UNTRUSTED` |

### Startup Sequence Constants

| Name | Type | Value |
|---|---|---|
| Credentials wait timeout | duration/string | `30s` |

### Logging / Severity Constants

| Name | Type | Value |
|---|---|---|
| TrustFlow emission failure severity | `string` | `WARN` |

### Runtime / Language Constraints

| Name | Type | Value |
|---|---|---|
| Python version | `string` | `3.12` |

## Validation Rules

## 1. Entry Point Enforcement

For every entry point that processes an agent action:

1. `CTX-ID` validation MUST occur FIRST.
2. If `CTX-ID` validation fails, processing MUST be immediately rejected.
3. No partial processing is permitted before successful `CTX-ID` validation.
4. VTZ policy evaluation MUST occur BEFORE execution.
5. If VTZ policy denies the action, a `VTZEnforcementDecision` record MUST be produced with:
   - `verdict = block`
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a `TrustFlowEvent`.

## 2. TrustFlow Event Validation

A valid `TrustFlowEvent` MUST satisfy all of the following:

- `event_id` present
- `session_id` present
- `ctx_id` present
- `ts` present
- `event_type` present
- `payload_hash` present
- `event_id` is globally unique
- `event_id` is CSPRNG-derived
- `event_id` is not sequential
- `ts` is a UTC Unix timestamp with millisecond precision
- `payload_hash` equals SHA-256 of the serialized action payload

Operational rules:

- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Emission failure MUST NOT silently continue.
- Emission failure MUST be logged and surfaced.
- Emission failure is a `WARN`-level audit event.

## 3. CTX-ID Validation Rules

- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- The old token is invalidated immediately on rotation.
- Expired CTX-ID MUST be rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NEVER be inferred from surrounding context when `ctx_id` is missing.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

## 4. VTZ Enforcement Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

## 5. Startup Sequence Contract

Order is mandatory and MUST NOT change:

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC (timeout: `30s`)
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (async)
8. Send ready message via XPC (includes `agent_version`, `capabilities`)
9. Enter `CommandRouter` event loop

Additional constraints:

- Steps 5-6 are non-fatal on credential errors.
- On credential errors, emit `auth_error` XPC card.
- Continue in degraded state after credential errors.
- Step 7 is always async.
- The app remains responsive while embeddings load.

## 6. Security Validation Rules

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- When output contains `SECURITY_REFUSAL`: stop, gate, log. Never retry to bypass.

### Forbidden Behaviors

The following are explicitly non-conformant:

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)  # WRONG — do not retry
```

```swift
let value = optional!
```

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

```swift
let token = KeychainKit.read("github_token")
```

## 7. GitHub Integration Rules

- All GitHub operations MUST go through `GitHubTool`.
- Pipeline code MUST NEVER call the GitHub API directly.

## 8. Python Implementation Constraints

- Python version MUST be `3.12`.
- Type annotations are required on every function.
- Backend code MUST use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses are required for all structured data.

## Wire Format Examples

## Valid Payloads

### TrustFlowEvent
```json
{
  "event_id": "7f4c6d6f-5a1e-4d3d-9c6d-3c6e7d88e2c1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678123,
  "event_type": "allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961fca13f5969b7e08f840aff"
}
```

### VTZEnforcementDecision
```json
{
  "verdict": "block"
}
```

### ReadyMessage
```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

### ListeningAnnouncement
```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### Auth error XPC card
```json
{
  "auth_error": {
    "type": "credential_initialization_failed"
  }
}
```

## Invalid Payloads

### TrustFlowEvent missing required fields
```json
{
  "event_id": "123",
  "session_id": "sess_123"
}
```

Invalid because:
- missing `ctx_id`
- missing `ts`
- missing `event_type`
- missing `payload_hash`

### VTZEnforcementDecision with wrong verdict
```json
{
  "verdict": "deny"
}
```

Invalid because:
- denial record MUST use exact value `block`

### Listening announcement with wrong prefix
```text
AGENT_LISTENING:/tmp/forge-agent.sock
```

Invalid because:
- prefix MUST be exactly `FORGE_AGENT_LISTENING:`

### TrustFlowEvent with non-millisecond timestamp shape
```json
{
  "event_id": "7f4c6d6f-5a1e-4d3d-9c6d-3c6e7d88e2c1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678,
  "event_type": "allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961fca13f5969b7e08f840aff"
}
```

Invalid because:
- `ts` MUST be UTC Unix timestamp with millisecond precision

### Missing CTX-ID on agent action
```json
{
  "payload": {
    "action": "commit"
  }
}
```

Invalid because:
- missing `ctx_id` MUST be treated as `UNTRUSTED`
- action must be rejected before partial processing

## Integration Points

## XPC

### Inputs from Swift to backend
- Credentials are delivered via XPC.
- Backend waits up to `30s` for credentials.
- Swift is the only side that reads Keychain.
- Backend consumes credentials via XPC only.

### Outputs from backend to Swift
- Listening announcement via stdout:
  - `FORGE_AGENT_LISTENING:{socket_path}`
- Ready message via XPC:
  - includes `agent_version`
  - includes `capabilities`
- Auth error card via XPC:
  - `auth_error`

## CommandRouter

- Backend enters `CommandRouter` event loop after startup sequence completes.
- All agent actions entering through command routing are subject to:
  - CTX-ID validation first
  - VTZ policy enforcement before execution
  - synchronous TrustFlow event emission for every outcome

## GitHubTool

- `GitHubTool` is the sole integration point for GitHub operations.
- Direct GitHub API access from pipeline code is forbidden.

## ConsensusEngine

- Initialized with API keys after credentials are received.
- Credential initialization failure is non-fatal and must emit `auth_error`.

## DocumentStore

- Loading starts in background asynchronously.
- App must remain responsive while embeddings load.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.

## Filesystem

- Any file path written to disk must be validated with:
  - `path_security.validate_write_path()`

## LLM Prompt Construction

- External document context must be placed in the USER prompt.
- External document context must never be placed in the SYSTEM prompt.
- If LLM output contains `SECURITY_REFUSAL`, processing must stop, gate, and log.
- Retrying to bypass `SECURITY_REFUSAL` is forbidden.

## Non-Normative Gaps

The source material does not define the complete serialized schemas for the following, so they remain contractually required but structurally unspecified beyond named fields explicitly present in source:

- `auth_error` XPC card inner payload
- credentials `api_keys` object shape
- `capabilities` element schema
- `event_type` enum values
- full CTX-ID token serialized representation
- full agent action payload schema