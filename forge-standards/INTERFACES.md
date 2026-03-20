# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements explicitly stated in the provided TRD/interface sources for the `ConsensusDevAgent` subsystem and its required integration boundaries.

Where the source defines required fields but not a container type name, this document assigns a descriptive interface name for implementation clarity. Values and constraints are preserved exactly from source.

---

### 1. TrustFlowEvent

Required by: **TrustFlow Emission Contract**

#### Type
Structured record / object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique (`CSPRNG, not sequential`) |
| `session_id` | `string` | Yes | Required on every TrustFlow event |
| `ctx_id` | `string` | Yes | Required on every TrustFlow event |
| `ts` | `number` | Yes | MUST be `UTC Unix timestamp with millisecond precision` |
| `event_type` | `string` | Yes | Required on every TrustFlow event |
| `payload_hash` | `string` | Yes | MUST be `SHA-256 of the serialized action payload` |

#### Behavioral constraints
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a `WARN-level audit event`, not a silent skip.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

---

### 2. VTZEnforcementDecision

Required by: **CAL Enforcement Contract**

#### Type
Structured record / object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | For VTZ denial, MUST equal `block` |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

#### Notes
The source only specifies one required field/value pair explicitly:
- `verdict=block`

No additional fields are defined in the provided source and therefore are not contractually required here.

---

### 3. CTX-ID Token

Required by: **CTX-ID Contract**

#### Type
Opaque token / identity artifact

#### Representation
Implementation-defined token format, but the following contract rules are mandatory.

#### Required properties
| Property | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Used as immutable session/action trust identity |

#### Behavioral constraints
- CTX-ID tokens are `IMMUTABLE once issued — no field modification after issuance`.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against `TrustLock public key — software-only validation is rejected`.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Never infer identity from context when CTX-ID is missing.

---

### 4. AgentCapabilities

Required by: **Backend Startup Sequence**

#### Type
Structured record / object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | `string` | Yes | Included in ready message via XPC |
| `capabilities` | `array<string>` or `object` | Yes | Included in ready message via XPC; exact internal schema not defined in provided source |

#### Notes
The source mandates inclusion of:
- `agent_version`
- `capabilities`

No further field-level schema is defined in the provided source.

---

### 5. AuthError XPC Card

Required by: **Backend Startup Sequence**

#### Type
Structured XPC message / card

#### Fields
Not fully specified in the provided source.

#### Required behavior
- If step 5 or 6 encounters credential errors, the subsystem MUST emit `auth_error` XPC card.
- This is non-fatal.
- The subsystem MUST continue in degraded state.

#### Contractually required literal
| Field/Value | Requirement |
|---|---|
| message/card type = `auth_error` | MUST be emitted on credential errors during GitHubTool or ConsensusEngine initialization |

---

### 6. Listening Announcement

Required by: **Backend Startup Sequence**

#### Type
Stdout line

#### Wire format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Fields

| Segment | Type | Required | Constraints |
|---|---|---:|---|
| `FORGE_AGENT_LISTENING:` | literal string prefix | Yes | MUST appear exactly as shown |
| `{socket_path}` | `string` | Yes | Socket path on which XPC server is listening |

---

### 7. Credential Delivery via XPC

Required by: **Backend Startup Sequence**, security rules

#### Type
Structured XPC message

#### Fields
Not fully specified in provided source.

#### Behavioral constraints
- Backend waits for credentials via XPC.
- Timeout is `30s`.
- Swift reads Keychain and delivers credentials via XPC.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

#### Security constraints
- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Backend credential acquisition from Keychain is forbidden.

---

### 8. Action Payload

Required by: **CAL Enforcement Contract**, **TrustFlow Emission Contract**

#### Type
Serialized action payload

#### Fields
Not defined in provided source.

#### Contractually required handling
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection — no partial processing.
- Every action MUST be checked against VTZ policy BEFORE execution.
- `payload_hash` in corresponding TrustFlow event MUST be `SHA-256 of the serialized action payload`.

---

### 9. Loaded Document Chunk

Required by: **Security**

#### Type
Structured document fragment / chunk

#### Fields
Not defined in provided source.

#### Contractually required handling
- All loaded document chunks must pass injection scanning before being included in any LLM prompt.
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.

---

### 10. SECURITY_REFUSAL Output

Required by: **Security**, **FORBIDDEN: ignoring SECURITY_REFUSAL**

#### Type
Literal model output marker / string token

#### Literal value
```text
SECURITY_REFUSAL
```

#### Required behavior
- When output contains `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.
- Retrying another LLM generation after `SECURITY_REFUSAL` is forbidden.

---

## Enums and Constants

### Verdict Values

| Name | Type | Allowed Values | Notes |
|---|---|---|---|
| `verdict` | `string` | `block` | Only explicitly defined value in provided source |

### Action Outcome Values

| Name | Type | Allowed Values | Notes |
|---|---|---|---|
| action outcome | `string` | `allow`, `restrict`, `block` | Every outcome MUST emit a TrustFlow event |

### Special Message/Card Types

| Name | Type | Exact Value |
|---|---|---|
| auth error XPC card type | `string` | `auth_error` |

### Special Output Tokens

| Name | Type | Exact Value |
|---|---|---|
| security refusal marker | `string` | `SECURITY_REFUSAL` |
| startup stdout prefix | `string` | `FORGE_AGENT_LISTENING:` |

### Timing Constants

| Name | Type | Exact Value |
|---|---|---|
| credential wait timeout | duration | `30s` |

### Runtime / Tooling Constants

| Name | Type | Exact Value |
|---|---|---|
| Python version | `string` | `3.12` |
| required test runner | `string` | `pytest` |
| required linter | `string` | `ruff` |
| required type checker | `string` | `mypy` |
| minimum new-module coverage | `number` | `85%` |

---

## Validation Rules

## 1. Entry Point Enforcement

Every entry point that processes an agent action MUST:

1. Call CTX-ID validation FIRST.
2. Immediately reject on CTX-ID validation failure.
3. Perform VTZ policy check BEFORE execution.
4. Emit a TrustFlow event for every action outcome.
5. Not silently continue if TrustFlow emission fails; log and surface the failure.

---

## 2. CTX-ID Validation

A CTX-ID is valid only if all of the following are true:

- Present; otherwise treat as `UNTRUSTED`
- Not expired
- Validated against `TrustLock public key`
- Unmodified since issuance

Additional rules:

- Software-only validation is rejected.
- Rotation creates a new token and invalidates the old token immediately.
- Identity MUST NOT be inferred from surrounding context if CTX-ID is missing.

---

## 3. VTZ Enforcement

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

## 4. TrustFlow Event Validation

A TrustFlow event is conformant only if:

- `event_id` exists and is globally unique
- `event_id` is generated by CSPRNG and is not sequential
- `session_id` exists
- `ctx_id` exists
- `ts` exists and is a UTC Unix timestamp with millisecond precision
- `event_type` exists
- `payload_hash` exists
- `payload_hash` equals SHA-256 of the serialized action payload

Operational rule:
- Emission MUST be synchronous in the enforcement path.

Failure handling:
- Failed emission is a WARN-level audit event, not a silent skip.

---

## 5. Startup Sequence Validation

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
- On such errors emit `auth_error` XPC card.
- Continue in degraded state.
- Step 7 is always async.

---

## 6. GitHub Integration Validation

- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

---

## 7. Security Validation

The following are mandatory:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on any generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.
- When `SECURITY_REFUSAL` appears: stop, gate, log. Never retry to bypass.

---

## 8. Python Implementation Constraints

- Python `3.12`
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Tests in `tests/`, mirroring `src/`
- `pytest` required
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage `≥ 85%` on all new modules

---

## Wire Format Examples

## 1. Valid TrustFlow Event

```json
{
  "event_id": "9d7d1f9d-55fd-4d9f-b4ad-1b0e9c3f7d61",
  "session_id": "sess_01JXYZABC",
  "ctx_id": "ctx_01JXYZDEF",
  "ts": 1731975123456,
  "event_type": "action_executed",
  "payload_hash": "4d9f2c7b2d3d9d0b4f1f7a6a8f8d2b0f2b7d4e2c1a9e6f3b8c7d5e1f0a2b3c4d"
}
```

Why valid:
- Contains all required fields
- `ts` is millisecond Unix timestamp
- `payload_hash` is a SHA-256-style hex string
- `event_id` is non-sequential in format

---

## 2. Invalid TrustFlow Event: missing required field

```json
{
  "event_id": "9d7d1f9d-55fd-4d9f-b4ad-1b0e9c3f7d61",
  "session_id": "sess_01JXYZABC",
  "ts": 1731975123456,
  "event_type": "action_executed",
  "payload_hash": "4d9f2c7b2d3d9d0b4f1f7a6a8f8d2b0f2b7d4e2c1a9e6f3b8c7d5e1f0a2b3c4d"
}
```

Why invalid:
- Missing `ctx_id`

---

## 3. Invalid VTZ Enforcement Decision

```json
{
  "verdict": "allow"
}
```

Why invalid:
- For VTZ policy denial, the contract requires `verdict=block`

---

## 4. Valid Startup Listening Announcement

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

Why valid:
- Matches exact required stdout prefix and includes socket path

---

## 5. Invalid Startup Listening Announcement

```text
LISTENING:/tmp/forge-agent.sock
```

Why invalid:
- Prefix must be exactly `FORGE_AGENT_LISTENING:`

---

## 6. Valid Ready Message via XPC

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

Why valid:
- Includes required `agent_version` and `capabilities`

Note:
- The provided source does not constrain the exact internal schema of `capabilities`, only that it is included.

---

## 7. Valid Auth Error Card via XPC

```json
{
  "type": "auth_error"
}
```

Why valid:
- Includes the required literal `auth_error`

Note:
- Additional fields are not specified in the provided source.

---

## 8. Invalid Security Handling Example

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Why invalid:
- When `SECURITY_REFUSAL` appears, the required behavior is stop, gate, log
- Never retry to bypass

---

## Integration Points

## 1. Swift ↔ Backend XPC

### Required interactions
- Swift reads backend socket path from stdout line:
  - `FORGE_AGENT_LISTENING:{socket_path}`
- Swift delivers credentials via XPC
- Backend waits up to `30s` for credentials
- Backend sends ready message via XPC including:
  - `agent_version`
  - `capabilities`
- Backend may emit `auth_error` XPC card and continue in degraded state

### Security boundary
- Only Swift reads Keychain
- Python reads nothing from Keychain
- Swift reads Keychain only to deliver credentials via XPC

---

## 2. Backend ↔ GitHub

### Required component
- `GitHubTool`

### Contract
- All GitHub operations must go through `GitHubTool`
- Direct GitHub API calls from pipeline code are forbidden

---

## 3. Backend ↔ Consensus Engine

### Required component
- `ConsensusEngine`

### Startup role
- Initialized at startup step 6 with API keys
- Credential errors are non-fatal and should emit `auth_error`

---

## 4. Backend ↔ DocumentStore

### Required component
- `DocumentStore`

### Contract
- Loading starts in background asynchronously at startup step 7
- App remains responsive while embeddings load
- All loaded document chunks must pass injection scanning before prompt inclusion

---

## 5. Backend ↔ CommandRouter

### Required component
- `CommandRouter`

### Contract
- Entered only after step 8 of startup sequence
- Startup order is mandatory

---

## 6. Enforcement Path Integrations

### Required sequence for any agent action
1. CTX-ID validation
2. Immediate rejection on validation failure
3. VTZ policy evaluation
4. Produce `VTZEnforcementDecision` with `verdict=block` on denial
5. Emit synchronous TrustFlow event for outcome
6. Execute only if enforcement permits

---

## Non-Conformance Conditions

A `ConsensusDevAgent` implementation is non-conformant if any of the following occur:

- Missing CTX-ID validation before processing action
- Partial processing after CTX-ID validation failure
- VTZ check occurs after execution
- VTZ denial does not produce `VTZEnforcementDecision` with `verdict=block`
- Any action outcome does not emit TrustFlow event
- TrustFlow emission failure is silently ignored
- TrustFlow event omits any required field
- `event_id` is sequential or not CSPRNG-generated
- `payload_hash` is not SHA-256 of serialized action payload
- Startup order differs from mandated sequence
- Ready XPC message omits `agent_version` or `capabilities`
- Backend reads Keychain directly
- Pipeline code calls GitHub API directly instead of `GitHubTool`
- `SECURITY_REFUSAL` is retried
- External document context is placed in `SYSTEM` prompt
- File writes occur without `path_security.validate_write_path()`
- HTTP response bodies are logged
- `shell=True`, `eval()`, or `exec()` is used on generated or external content