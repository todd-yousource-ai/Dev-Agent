# Interface Contracts - ConsensusDevAgent

This document defines the wire-format and API contract requirements for the `ConsensusDevAgent` subsystem based strictly on the provided TRD excerpts and Forge interface contracts.

## Data Structures

### TrustFlowEvent

Required for every action outcome emitted in the enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | yes | Session identifier for the agent session. |
| `ctx_id` | `string` | yes | CTX-ID token associated with the action. Missing `ctx_id` MUST be treated as `UNTRUSTED`; identity MUST NOT be inferred from context. |
| `ts` | `number` | yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | yes | TrustFlow event type. Exact allowed values are not specified in the provided TRDs. |
| `payload_hash` | `string` | yes | MUST be SHA-256 of the serialized action payload. |

#### Behavioral constraints
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be surfaced and logged as a WARN-level audit event.
- Emission failure MUST NOT silently continue.

---

### VTZEnforcementDecision

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | MUST be exactly `block` when VTZ policy denial occurs. |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### XPC Listening Announcement

Printed to stdout during backend startup.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `stdout_line` | `string` | yes | MUST be exactly formatted as `FORGE_AGENT_LISTENING:{socket_path}` |
| `socket_path` | `string` | yes | Socket path bound by the XPC server. |

#### Behavioral constraints
- Must occur after starting the XPC server and listening on the socket.
- Must occur before waiting for credentials via XPC.

---

### CredentialsViaXPC

Credentials delivered from Swift to backend via XPC.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `github_token` | `string` | no | Used to initialize `GitHubTool`. Python reads nothing from Keychain. Only Swift reads Keychain, only to deliver via XPC. |
| `api_keys` | `object` | no | Used to initialize `ConsensusEngine` with API keys. Exact subfields are not specified in the provided TRDs. |

#### Behavioral constraints
- Backend MUST wait for credentials via XPC with timeout `30s`.
- Credential errors at steps 5-6 are non-fatal.
- On credential errors, backend MUST emit `auth_error` XPC card and continue in degraded state.

---

### ReadyMessageViaXPC

Ready message sent after startup initialization.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | `string` | yes | Included in ready message via XPC. |
| `capabilities` | `array` | yes | Included in ready message via XPC. Element types/values are not specified in the provided TRDs. |

#### Behavioral constraints
- Sent after `DocumentStore` loading starts in background.
- Must be sent before entering `CommandRouter` event loop.

---

### AuthErrorXPCCard

XPC message/card emitted when credential initialization fails.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | `string` | implied | MUST be exactly `auth_error` if represented as a typed message/card. |

#### Behavioral constraints
- Emitted for credential errors in:
  - `Initialize GitHubTool with token`
  - `Initialize ConsensusEngine with API keys`
- Backend continues in degraded state after emission.

---

### AgentAction

Represents an action processed by an entry point.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | MUST be validated FIRST at every entry point that processes an agent action. |
| `session_id` | `string` | yes | Used in TrustFlow event emission. |
| `payload` | `object` | yes | Serialized form is hashed using SHA-256 to produce `payload_hash`. |
| `vtz` | `string` | implied | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance. |

#### Behavioral constraints
- CTX-ID validation MUST occur FIRST.
- CTX-ID validation failure MUST result in immediate rejection with no partial processing.
- Action MUST be checked against VTZ policy BEFORE execution.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### CTXIDToken

Immutable token used for identity and trust enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Immutable once issued. |
| `vtz` | `string` | yes | Bound to exactly one VTZ at issuance. |
| `expires_at` | `number` or `string` | implied | Exact wire type not specified; expired CTX-ID MUST be rejected. |
| `public_key_validation` | `string` or `object` | implied | MUST validate against TrustLock public key; software-only validation is rejected. |

#### Behavioral constraints
- CTX-ID tokens are IMMUTABLE once issued.
- Rotation creates a new token; old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is defined per deployment.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.

---

### PathWriteRequest

Represents any file write path sent to persistence or file-writing logic.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `path` | `string` | yes | MUST pass `path_security.validate_write_path()` before any write. |

---

### DocumentChunkForPrompting

Represents loaded document content before inclusion in an LLM prompt.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `content` | `string` | yes | MUST pass injection scanning before inclusion in any LLM prompt. |
| `prompt_role` | `string` | yes | External document context MUST go in the `USER` prompt, never the `SYSTEM` prompt. |

---

### SubprocessInvocation

Represents subprocess execution parameters.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `shell` | `boolean` | yes | MUST NOT be `true`. `shell=True` is forbidden. |

---

### LoggingRecord

Represents logging output constraints relevant to HTTP and security refusal handling.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `status_code` | `number` | no | May be logged for HTTP responses. |
| `error_type` | `string` | no | May be logged for HTTP errors. |
| `response_body` | `string` | no | MUST NOT be logged. |
| `message` | `string` | yes | If `SECURITY_REFUSAL` is observed, processing must stop, gate, and log. |
| `level` | `string` | no | Failed TrustFlow emission is a WARN-level audit event. |

---

## Enums and Constants

### String constants

| Name | Value |
|---|---|
| XPC listening prefix | `FORGE_AGENT_LISTENING:` |
| auth error type | `auth_error` |
| CTX-ID missing trust state | `UNTRUSTED` |
| VTZ denial verdict | `block` |
| external document prompt role | `USER` |
| forbidden external document prompt role | `SYSTEM` |
| forbidden refusal token | `SECURITY_REFUSAL` |

### Startup sequence constants

| Name | Value |
|---|---|
| credentials wait timeout | `30s` |

### Required startup order

The following sequence is mandatory and must not be changed:

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC (timeout: 30s)`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background (async)`
8. `Send ready message via XPC (includes agent_version, capabilities)`
9. `Enter CommandRouter event loop`

### Enforcement outcome values

The provided contracts specify these outcome values:

| Value | Meaning |
|---|---|
| `allow` | Action permitted; must emit TrustFlow event |
| `restrict` | Action restricted; must emit TrustFlow event |
| `block` | Action denied; must emit TrustFlow event; VTZ denial must also produce `VTZEnforcementDecision` with `verdict=block` |

---

## Validation Rules

### CAL enforcement

1. Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

### TrustFlow emission

1. `event_id` MUST be globally unique.
2. `event_id` MUST use CSPRNG generation.
3. `event_id` MUST NOT be sequential.
4. `ts` MUST be UTC Unix timestamp with millisecond precision.
5. `payload_hash` MUST be SHA-256 of the serialized action payload.
6. Emission MUST be synchronous in the enforcement path.
7. Async buffering is not permitted.
8. Failed emission is a WARN-level audit event.

### CTX-ID

1. CTX-ID tokens are immutable once issued.
2. Rotation creates a new token.
3. The old token is invalidated immediately upon rotation.
4. Expired CTX-ID MUST be rejected.
5. Clock skew tolerance is deployment-defined.
6. CTX-ID MUST be validated against TrustLock public key.
7. Software-only validation is rejected.
8. Missing CTX-ID MUST be treated as `UNTRUSTED`.
9. Identity MUST never be inferred from context when CTX-ID is missing.

### VTZ enforcement

1. Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit cross-VTZ access is denied.
4. VTZ boundaries are structural, not advisory.
5. Enforcement cannot be bypassed by application code.
6. VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

### Security rules

1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Log HTTP status codes and error types only.
6. All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
7. All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
8. Context from external documents MUST go in the `USER` prompt, never the `SYSTEM` prompt.
9. When `SECURITY_REFUSAL` appears in output: stop, gate, log.
10. Never retry to bypass `SECURITY_REFUSAL`.
11. All GitHub operations go through `GitHubTool`.
12. Never call the GitHub API directly from pipeline code.

### Python/backend implementation requirements affecting interface behavior

1. Python version is `3.12`.
2. Type annotations are required on every function.
3. Backend uses `async/await` throughout.
4. No blocking calls on the event loop.
5. Dataclasses are required for all structured data.
6. Tests use `pytest`.
7. Tests live in `tests/` mirroring `src/`.
8. `ruff` and `mypy` must pass clean.
9. Test coverage must be `≥ 85%` on all new modules.

---

## Wire Format Examples

## Valid payloads

### TrustFlow event

```json
{
  "event_id": "3f8d2d4d-1b0f-4e7d-93d4-8d2c1d8b0f3a",
  "session_id": "sess_001",
  "ctx_id": "ctx_abc123",
  "ts": 1731605123456,
  "event_type": "allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961f7e2dd836118cc32cc8b4a"
}
```

### VTZ enforcement decision on denial

```json
{
  "verdict": "block"
}
```

### Ready message via XPC

```json
{
  "agent_version": "1.0.0",
  "capabilities": [
    "github",
    "consensus",
    "documents"
  ]
}
```

### Credentials via XPC

```json
{
  "github_token": "ghp_redacted",
  "api_keys": {
    "provider": "redacted"
  }
}
```

### Agent action

```json
{
  "ctx_id": "ctx_abc123",
  "session_id": "sess_001",
  "payload": {
    "command": "run_consensus"
  },
  "vtz": "vtz_alpha"
}
```

### XPC listening announcement

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### Document chunk routed to USER prompt

```json
{
  "content": "External document excerpt",
  "prompt_role": "USER"
}
```

### File write request with validated path

```json
{
  "path": "/safe/output/file.txt"
}
```

---

## Invalid payloads

### Invalid TrustFlow event: sequential/non-unique `event_id`

```json
{
  "event_id": "123",
  "session_id": "sess_001",
  "ctx_id": "ctx_abc123",
  "ts": 1731605123456,
  "event_type": "allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961f7e2dd836118cc32cc8b4a"
}
```

Reason:
- `event_id` must be globally unique and CSPRNG-generated, not sequential.

### Invalid TrustFlow event: missing `ctx_id`

```json
{
  "event_id": "3f8d2d4d-1b0f-4e7d-93d4-8d2c1d8b0f3a",
  "session_id": "sess_001",
  "ts": 1731605123456,
  "event_type": "allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961f7e2dd836118cc32cc8b4a"
}
```

Reason:
- `ctx_id` is required on TrustFlow events.
- Missing CTX-ID must be treated as `UNTRUSTED` for action processing; identity must not be inferred.

### Invalid VTZ denial record

```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ policy denial must produce `VTZEnforcementDecision` with `verdict=block`.

### Invalid document prompt placement

```json
{
  "content": "External document excerpt",
  "prompt_role": "SYSTEM"
}
```

Reason:
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.

### Invalid subprocess invocation

```json
{
  "shell": true
}
```

Reason:
- `shell=True` is forbidden.

### Invalid logging record containing HTTP response body

```json
{
  "status_code": 403,
  "error_type": "Forbidden",
  "response_body": "{\"message\":\"secret details\"}"
}
```

Reason:
- Never log HTTP response bodies.

### Invalid security refusal handling

```json
{
  "message": "SECURITY_REFUSAL",
  "retry": true
}
```

Reason:
- When `SECURITY_REFUSAL` is seen: stop, gate, log.
- Never retry to bypass.

### Invalid startup ordering example

```text
1. Initialize logger
2. Initialize GitHubTool with token
3. Start XPC server, listen on socket
```

Reason:
- Startup order is mandatory and must not be changed.

### Invalid GitHub integration behavior

```json
{
  "github_api_call_origin": "pipeline_code"
}
```

Reason:
- All GitHub operations must go through `GitHubTool`.
- Direct GitHub API calls from pipeline code are forbidden.

---

## Integration Points

### XPC

#### Backend startup integration
- Backend MUST start XPC server and listen on a socket.
- Backend MUST print `FORGE_AGENT_LISTENING:{socket_path}` to stdout.
- Swift reads this stdout line.
- Backend MUST wait for credentials via XPC for `30s`.
- Swift is the only component that reads Keychain.
- Python backend reads nothing from Keychain.
- Swift delivers credentials via XPC.

#### Credential handling
- `github_token` is used to initialize `GitHubTool`.
- `api_keys` are used to initialize `ConsensusEngine`.
- Failures in these steps are non-fatal.
- On failure, backend emits `auth_error` XPC card and continues in degraded state.

#### Ready signaling
- After starting async `DocumentStore` loading, backend sends a ready message via XPC.
- Ready message includes:
  - `agent_version`
  - `capabilities`

### Command routing
- After ready signaling, backend enters `CommandRouter` event loop.

### GitHub integration
- All GitHub operations go through `GitHubTool`.
- Pipeline code MUST NOT call the GitHub API directly.

### Consensus engine integration
- `ConsensusEngine` is initialized with API keys received via XPC.
- Initialization occurs after `GitHubTool` initialization in the mandatory startup order.

### Document store integration
- `DocumentStore` loading starts in background asynchronously.
- App remains responsive while embeddings load.
- Any loaded document chunk must pass injection scanning before inclusion in an LLM prompt.

### Security and trust enforcement integration
- Every action-processing entry point integrates:
  1. CTX-ID validation
  2. VTZ policy enforcement
  3. Synchronous TrustFlow emission
- Missing or invalid CTX-ID results in rejection or `UNTRUSTED` handling per contract.
- Cross-VTZ calls require explicit policy authorization.

### File system integration
- Any path written to disk must be validated with `path_security.validate_write_path()` before writing.

### Logging/audit integration
- HTTP logs may include status code and error type only.
- HTTP response bodies must never be logged.
- TrustFlow emission failure must be logged as WARN-level audit event.
- `SECURITY_REFUSAL` must stop processing, gate, and log.