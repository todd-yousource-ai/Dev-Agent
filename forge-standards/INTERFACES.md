# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements stated in the provided TRD excerpts for the `ConsensusDevAgent` subsystem and its immediate integration surfaces.

Where the source specifies exact field names, those names are normative and must be used exactly as written.

---

### 1. TrustFlowEvent

Required by: `TrustFlow Emission Contract`

#### Type
Structured record

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | Yes | MUST be globally unique. MUST be generated using CSPRNG. MUST NOT be sequential. |
| `session_id` | string | Yes | Session identifier. |
| `ctx_id` | string | Yes | CTX-ID token identifier associated with the event. |
| `ts` | number | Yes | MUST be UTC Unix timestamp with millisecond precision. |
| `event_type` | string | Yes | Event type name. |
| `payload_hash` | string | Yes | MUST be SHA-256 of the serialized action payload. |

#### Behavioral constraints
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Emission failure MUST NOT silently continue; the failure must be logged and surfaced.

---

### 2. VTZEnforcementDecision

Required by: `CAL Enforcement Contract`

#### Type
Structured record

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | Yes | On VTZ policy denial, MUST equal `block`. |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 3. XPC Listening Announcement

Required by: `Backend Startup Sequence`

#### Type
Stdout line

#### Format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Fields

| Segment | Type | Required | Constraints |
|---|---|---:|---|
| `FORGE_AGENT_LISTENING:` | literal string | Yes | MUST appear exactly as written. |
| `{socket_path}` | string | Yes | Socket path that Swift reads from stdout. |

#### Behavioral constraints
- MUST be printed after XPC server start and listen.
- MUST occur before waiting for credentials via XPC.

---

### 4. Credentials via XPC

Required by: `Backend Startup Sequence`

#### Type
XPC-delivered credential message

#### Fields
The provided TRD excerpt does **not** define field names for the credential payload.

#### Behavioral constraints
- Backend waits for credentials via XPC.
- Timeout is `30s`.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.
- Credentials are used to initialize:
  - `GitHubTool` with token
  - `ConsensusEngine` with API keys

#### Error behavior
- Credential errors at startup steps 5–6 are non-fatal.
- Backend MUST emit `auth_error` XPC card and continue in degraded state.

---

### 5. Ready Message via XPC

Required by: `Backend Startup Sequence`

#### Type
XPC message

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | Yes | Included in ready message. |
| `capabilities` | array | Yes | Included in ready message. Element type not specified in provided TRD excerpt. |

#### Behavioral constraints
- Sent after background `DocumentStore` loading starts.
- Sent before entering `CommandRouter` event loop.

---

### 6. auth_error XPC Card

Required by: `Backend Startup Sequence`

#### Type
XPC message/card

#### Fields
The provided TRD excerpt defines the message/card name only.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `auth_error` | string or message discriminator | Yes | MUST be emitted on credential initialization failure for startup steps 5–6. Exact envelope structure not defined in provided TRD excerpt. |

#### Behavioral constraints
- MUST be emitted when `GitHubTool` token initialization or `ConsensusEngine` API key initialization fails due to credential error.
- Startup continues in degraded state.

---

### 7. SECURITY_REFUSAL Output

Required by: security excerpts

#### Type
LLM output sentinel string

#### Value
```text
SECURITY_REFUSAL
```

#### Behavioral constraints
- When output contains `SECURITY_REFUSAL`: stop, gate, log.
- MUST NOT retry to bypass.
- The following behavior is explicitly forbidden:
  ```python
  if "SECURITY_REFUSAL" in output:
      output = await self._generate_openai(prompt)  # WRONG — do not retry
  ```

---

### 8. Action Payload

Required by: `TrustFlow Emission Contract`

#### Type
Serialized action payload

#### Fields
Not defined in the provided TRD excerpt.

#### Behavioral constraints
- `payload_hash` in `TrustFlowEvent` MUST be SHA-256 of the serialized action payload.

---

### 9. CTX-ID Token

Required by: `CTX-ID Contract`

#### Type
Token / structured identifier

#### Fields
Field-level schema is not defined in the provided TRD excerpt.

#### Behavioral constraints
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification after issuance.
- Rotation creates a new token.
- Old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from context when CTX-ID is missing.

---

### 10. Session-to-VTZ Binding

Required by: `VTZ Enforcement Contract`

#### Type
Session binding invariant

#### Fields
No explicit wire fields defined in the provided TRD excerpt.

#### Constraints
- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

## Enums and Constants

### Literal Strings

| Name | Type | Value |
|---|---|---|
| Listening stdout prefix | string | `FORGE_AGENT_LISTENING:` |
| Security refusal sentinel | string | `SECURITY_REFUSAL` |
| Auth error card/message name | string | `auth_error` |
| VTZ deny verdict | string | `block` |
| Missing CTX-ID trust state | string | `UNTRUSTED` |

### Timing Constants

| Name | Type | Value |
|---|---|---|
| Credential wait timeout | duration string | `30s` |

### Hash / Time Constants

| Name | Type | Value |
|---|---|---|
| Payload hash algorithm | string | `SHA-256` |
| Timestamp basis | string | `UTC Unix timestamp with millisecond precision` |

### Startup Sequence Order

Order is mandatory and MUST NOT be changed:

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background (async)`
8. `Send ready message via XPC (includes agent_version, capabilities)`
9. `Enter CommandRouter event loop`

---

## Validation Rules

### Entry Point Enforcement
Every entry point that processes an agent action MUST:

1. Call CTX-ID validation FIRST.
2. Immediately reject on CTX-ID validation failure.
3. Check action against VTZ policy BEFORE execution.
4. Emit a TrustFlow event for every outcome:
   - allow
   - restrict
   - block

### TrustFlow Validation
A `TrustFlowEvent` is valid only if:

- `event_id` is globally unique
- `event_id` is CSPRNG-generated
- `event_id` is not sequential
- `session_id` is present
- `ctx_id` is present
- `ts` is UTC Unix timestamp with millisecond precision
- `event_type` is present
- `payload_hash` is present
- `payload_hash` is SHA-256 of the serialized action payload

### CTX-ID Validation
A CTX-ID is valid only if:

- it is present, or the request is explicitly treated as `UNTRUSTED`
- it is not expired
- it validates against the TrustLock public key
- it has not been invalidated by rotation

A CTX-ID is invalid if:

- missing and treated as trusted
- expired
- modified after issuance
- validated by software-only means
- retained after rotation to a new token

### VTZ Validation
A VTZ-enforced action is valid only if:

- session is bound to exactly one VTZ
- action is authorized under that VTZ policy before execution
- any cross-VTZ tool call has explicit policy authorization

If denied:
- a `VTZEnforcementDecision` MUST be produced
- `verdict` MUST equal `block`

### Security Validation
The subsystem MUST enforce all of the following:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log. Never retry to bypass.

### Language and Implementation Constraints
- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Tests use `pytest`
- Tests live in `tests/` and mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage must be `≥ 85%` on all new modules

### GitHub Integration Constraint
- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

---

## Wire Format Examples

Only fields explicitly defined in the provided source are included as normative examples.

### Valid: TrustFlowEvent
```json
{
  "event_id": "8f7d5d4e-8aa3-4fc5-bdd2-0e6c4c3e91d1",
  "session_id": "sess_01HZX8M9YQ7T",
  "ctx_id": "ctx_01HZX8N4P2AB",
  "ts": 1735689600123,
  "event_type": "action_blocked",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3a1c2b8b7b1d6f5f0e9a4a6d2c1b3"
}
```

### Invalid: TrustFlowEvent missing required field
```json
{
  "event_id": "8f7d5d4e-8aa3-4fc5-bdd2-0e6c4c3e91d1",
  "session_id": "sess_01HZX8M9YQ7T",
  "ts": 1735689600123,
  "event_type": "action_blocked",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3a1c2b8b7b1d6f5f0e9a4a6d2c1b3"
}
```

Reason:
- `ctx_id` is required.

### Invalid: VTZEnforcementDecision wrong verdict
```json
{
  "verdict": "deny"
}
```

Reason:
- On VTZ policy denial, `verdict` MUST equal `block`.

### Valid: VTZEnforcementDecision on denial
```json
{
  "verdict": "block"
}
```

### Valid: XPC ready message
```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

Note:
- Only `agent_version` and `capabilities` are defined by the provided TRD excerpt.
- Capability string vocabulary is not specified in the provided source.

### Invalid: XPC ready message missing required field
```json
{
  "agent_version": "1.0.0"
}
```

Reason:
- `capabilities` is required.

### Valid: stdout listening announcement
```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### Invalid: stdout listening announcement
```text
forge_agent_listening:/tmp/forge-agent.sock
```

Reason:
- Prefix must be exactly `FORGE_AGENT_LISTENING:`.

### Invalid: SECURITY_REFUSAL bypass behavior
```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Reason:
- Retry to bypass is explicitly forbidden.

---

## Integration Points

### 1. Swift ↔ Backend XPC
#### Backend obligations
- Start XPC server and listen on socket.
- Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout.
- Wait for credentials via XPC for up to `30s`.
- Send ready message via XPC containing:
  - `agent_version`
  - `capabilities`

#### Swift obligations
- Read socket path from stdout listening line.
- Deliver credentials via XPC.
- Swift is the only layer that reads Keychain.
- Swift reads Keychain only to deliver credentials via XPC.

#### Prohibitions
- Python must not read Keychain.
- Swift must not make LLM API calls for backend execution.
- Force unwraps are forbidden in Swift:
  ```swift
  let value = optional!
  ```

### 2. Backend ↔ GitHubTool
- All GitHub operations MUST go through `GitHubTool`.
- Pipeline code MUST NOT call GitHub API directly.
- `GitHubTool` is initialized with token during startup step 5.
- Credential initialization failure is non-fatal and emits `auth_error`.

### 3. Backend ↔ ConsensusEngine
- `ConsensusEngine` is initialized with API keys during startup step 6.
- Credential initialization failure is non-fatal and emits `auth_error`.

### 4. Backend ↔ DocumentStore
- `DocumentStore` loading starts in background asynchronously at startup step 7.
- Application remains responsive while embeddings load.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.

### 5. Backend ↔ CommandRouter
- `CommandRouter` event loop starts only after ready message is sent.

### 6. Backend ↔ CAL / CTX-ID / VTZ / TrustFlow
For every agent action processing entry point:

1. Validate `ctx_id` first.
2. Reject immediately on validation failure.
3. Check VTZ policy before execution.
4. Produce `VTZEnforcementDecision` with `verdict=block` on denial.
5. Emit `TrustFlowEvent` synchronously for every allow/restrict/block outcome.
6. If TrustFlow emission fails, log and surface failure.

### 7. Backend ↔ Filesystem
- Every file path written to disk MUST be validated with:
  - `path_security.validate_write_path()`

### 8. Backend ↔ LLM Prompt Construction
- External document context MUST go into the USER prompt.
- External document context MUST NOT go into the SYSTEM prompt.
- `SECURITY_REFUSAL` output MUST stop processing, gate, and log.
- Never retry to bypass `SECURITY_REFUSAL`.

---

## Non-Specified Interfaces

The following interfaces are referenced but not field-defined in the provided TRD excerpts, so no additional wire fields can be specified normatively from source:

- credential XPC payload schema
- `auth_error` XPC card envelope schema
- CTX-ID token internal field schema
- action payload serialization schema
- VTZ policy request/response schema
- `GitHubTool` method signatures
- `ConsensusEngine` method signatures
- `CommandRouter` command envelope schema
- `DocumentStore` load message schema
- DTL Label schema

Only the names, literals, and constraints explicitly present above are normative from the provided source.