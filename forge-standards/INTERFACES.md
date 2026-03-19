# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract for the ConsensusDevAgent subsystem, based on the provided TRD excerpts and Forge component interface contracts.

### 1. Backend Startup Sequence Contract

The backend startup sequence is an ordered protocol contract.

#### Ordered steps

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background`
8. `Send ready message via XPC`
9. `Enter CommandRouter event loop`

#### Startup constraints

- Order is mandatory.
- The exact stdout prefix at step 3 MUST be:
  - `FORGE_AGENT_LISTENING:{socket_path}`
- Credential wait timeout at step 4:
  - `30s`
- Steps 5-6 are non-fatal on credential errors.
- On credential error in steps 5-6, the backend MUST emit:
  - `auth_error` XPC card
- Step 7 MUST be async.
- Step 8 ready message MUST include:
  - `agent_version`
  - `capabilities`

---

### 2. TrustFlow Event

Every TrustFlow event MUST include the following fields.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | MUST be globally unique; MUST use CSPRNG; MUST NOT be sequential |
| `session_id` | string | yes | Required on every TrustFlow event |
| `ctx_id` | string | yes | Required on every TrustFlow event |
| `ts` | number | yes | MUST be UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Required on every TrustFlow event |
| `payload_hash` | string | yes | MUST be SHA-256 of the serialized action payload |

#### TrustFlow emission constraints

- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be treated as:
  - `WARN-level audit event`
- Failed emission MUST NOT be a silent skip.
- TrustFlow emission failure MUST NOT silently continue.
- TrustFlow emission failure MUST be logged and surfaced.

---

### 3. VTZEnforcementDecision

A VTZ policy denial MUST produce a `VTZEnforcementDecision` record.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | MUST equal `block` for VTZ policy denial |

No additional fields are defined in the provided TRD content.

---

### 4. CTX-ID Token

The provided TRD content defines behavioral constraints for `CTX-ID` tokens. The internal token field layout is not specified in the source excerpt. The wire contract therefore defines only the externally required representation.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | Missing `CTX-ID` MUST be treated as `UNTRUSTED` |

#### CTX-ID constraints

- `CTX-ID` tokens are `IMMUTABLE` once issued.
- No field modification after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired `CTX-ID` MUST be rejected.
- Clock skew tolerance is defined per deployment.
- `CTX-ID` MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing `CTX-ID` MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from context when `CTX-ID` is missing.

---

### 5. Agent Action Payload

The exact action payload schema is not provided in the source excerpt. However, all enforcement-path processing is defined against a serialized action payload.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | MUST be validated FIRST before processing |
| `session_id` | string | yes | Required to support TrustFlow event emission |
| `action` | object | yes | Serialized form is hashed for `payload_hash` |
| `vtz` | string | implied | Every agent session is bound to exactly one VTZ at CTX-ID issuance |

#### Action processing constraints

- Every entry point that processes an agent action MUST call `CTX-ID` validation FIRST.
- `CTX-ID` validation failure MUST result in immediate rejection.
- No partial processing is allowed after `CTX-ID` validation failure.
- Every action MUST be checked against VTZ policy BEFORE execution.
- Every action outcome MUST emit a TrustFlow event:
  - `allow`
  - `restrict`
  - `block`

---

### 6. XPC Ready Message

The startup sequence defines an XPC ready message with required fields.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | MUST be included in ready message |
| `capabilities` | array | yes | MUST be included in ready message |

No additional XPC ready message fields are defined in the provided source.

---

### 7. XPC Auth Error Card

The startup sequence defines an XPC card emitted on credential initialization failure.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | string | yes | MUST equal `auth_error` |

No further fields are defined in the provided source.

---

### 8. Credential Delivery via XPC

Credential handling is constrained by security and startup behavior.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `token` | string | conditional | Used to initialize `GitHubTool` |
| `api_keys` | object | conditional | Used to initialize `ConsensusEngine with API keys` |

#### Credential constraints

- Backend waits for credentials via XPC.
- Timeout is `30s`.
- Only Swift reads Keychain.
- Python reads nothing from Keychain.
- Swift may deliver credentials via XPC.
- Backend credential initialization failures are non-fatal for:
  - `GitHubTool`
  - `ConsensusEngine`

---

## Enums and Constants

### String constants

| Name | Type | Value |
|---|---|---|
| Startup stdout prefix | string | `FORGE_AGENT_LISTENING:{socket_path}` |
| XPC error card type | string | `auth_error` |
| VTZ denial verdict | string | `block` |
| Missing CTX-ID trust state | string | `UNTRUSTED` |
| TrustFlow failure log severity | string | `WARN-level audit event` |

### Required action outcomes

`Every action outcome (allow, restrict, block) MUST emit a TrustFlow event`

Allowed values:

- `allow`
- `restrict`
- `block`

### Required startup components

- `GitHubTool`
- `ConsensusEngine`
- `DocumentStore`
- `CommandRouter`

### Required tools / modules by name

- `GitHubTool`
- `ConsensusEngine`
- `DocumentStore`
- `CommandRouter`
- `path_security.validate_write_path()`

### Security refusal sentinel

| Name | Type | Value |
|---|---|---|
| Security refusal token | string | `SECURITY_REFUSAL` |

---

## Validation Rules

### 1. CAL Enforcement Contract

For every entry point that processes an agent action:

1. `CTX-ID` validation MUST occur first.
2. On `CTX-ID` validation failure:
   - immediate rejection is required
   - partial processing is forbidden
3. VTZ policy check MUST occur before execution.
4. VTZ denial MUST produce a `VTZEnforcementDecision` with:
   - `verdict=block`
5. Every outcome MUST emit a TrustFlow event.
6. TrustFlow emission failure:
   - MUST NOT silently continue
   - MUST be logged
   - MUST be surfaced

---

### 2. TrustFlow Event Validation

A TrustFlow event is valid only if all are true:

- `event_id` is present
- `session_id` is present
- `ctx_id` is present
- `ts` is present
- `event_type` is present
- `payload_hash` is present
- `event_id` is globally unique
- `event_id` is not sequential
- `ts` is a UTC Unix timestamp with millisecond precision
- `payload_hash` is SHA-256 of the serialized action payload

Invalid if any required field is missing or constraints are violated.

---

### 3. CTX-ID Validation

A `CTX-ID` is valid only if all are true:

- token is present
- token is not expired
- token validates against TrustLock public key
- token has not been invalidated by rotation

A `CTX-ID` is invalid if any are true:

- missing
- expired
- modified after issuance
- validated using software-only validation
- superseded by rotation

Special handling:

- Missing `CTX-ID` MUST be treated as `UNTRUSTED`
- Identity MUST never be inferred from context

---

### 4. VTZ Validation

- Every agent session is bound to `EXACTLY ONE VTZ` at `CTX-ID issuance`
- Cross-VTZ tool calls require explicit policy authorization
- Implicit cross-VTZ access is denied
- VTZ boundaries are structural
- Enforcement cannot be bypassed by application code
- VTZ policy changes take effect at `NEXT CTX-ID issuance`, not mid-session

---

### 5. File Write Validation

Before any file path is written to disk:

- it MUST pass `path_security.validate_write_path()`

Any write performed before this validation is non-conformant.

---

### 6. LLM and External Content Validation

- All loaded document chunks MUST pass injection scanning before being included in any LLM prompt.
- Context from external documents MUST go in the `USER` prompt.
- Context from external documents MUST NEVER go in the `SYSTEM` prompt.
- When output contains `SECURITY_REFUSAL`:
  - stop
  - gate
  - log
  - never retry to bypass

Forbidden behavior:

- retrying model generation to bypass `SECURITY_REFUSAL`
- calling `eval()` on generated or external content
- calling `exec()` on generated or external content

---

### 7. Process / Subprocess Validation

- Never use `shell=True` in subprocess calls.

---

### 8. Logging Validation

- Never log HTTP response bodies.
- Log status codes and error types only.

---

### 9. Credential Handling Validation

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Python backend MUST NOT read from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

---

### 10. GitHub Operation Validation

- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

---

### 11. Python Implementation Constraints

These are implementation constraints that affect interface conformance:

- Python version: `3.12`
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data

---

## Wire Format Examples

## Valid payloads

### 1. Valid TrustFlow event

```json
{
  "event_id": "6f0b3f3b-8b2f-4b1a-9f5b-7d6f6e6f2a11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"
}
```

Why valid:

- includes all required TrustFlow fields
- `ts` uses Unix timestamp with millisecond precision
- `payload_hash` is a SHA-256 hex string
- `event_type` uses a required action outcome value

---

### 2. Valid VTZ denial decision

```json
{
  "verdict": "block"
}
```

Why valid:

- VTZ policy denial requires a `VTZEnforcementDecision` record with `verdict=block`

---

### 3. Valid ready message

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

Why valid:

- includes required fields:
  - `agent_version`
  - `capabilities`

---

### 4. Valid auth error card

```json
{
  "type": "auth_error"
}
```

Why valid:

- credential init failures must emit an XPC card of type `auth_error`

---

## Invalid payloads

### 1. Invalid TrustFlow event: missing required field

```json
{
  "event_id": "6f0b3f3b-8b2f-4b1a-9f5b-7d6f6e6f2a11",
  "session_id": "sess_123",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"
}
```

Why invalid:

- missing `ctx_id`

---

### 2. Invalid TrustFlow event: non-millisecond timestamp

```json
{
  "event_id": "6f0b3f3b-8b2f-4b1a-9f5b-7d6f6e6f2a11",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600,
  "event_type": "allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"
}
```

Why invalid:

- `ts` is not a UTC Unix timestamp with millisecond precision

---

### 3. Invalid VTZ denial decision

```json
{
  "verdict": "deny"
}
```

Why invalid:

- VTZ policy denial MUST produce `verdict=block`

---

### 4. Invalid ready message

```json
{
  "agent_version": "1.0.0"
}
```

Why invalid:

- missing `capabilities`

---

### 5. Invalid auth error card

```json
{
  "type": "credential_error"
}
```

Why invalid:

- required type value is exactly `auth_error`

---

### 6. Invalid action processing sequence

```json
{
  "session_id": "sess_123",
  "action": {
    "tool": "github"
  }
}
```

Why invalid:

- missing `ctx_id`
- missing `ctx_id` must be treated as `UNTRUSTED`
- action processing cannot proceed without first performing `CTX-ID` validation

---

## Integration Points

### 1. XPC

Used for:

- credential delivery
- ready message delivery
- `auth_error` card delivery

Required behaviors:

- backend starts XPC server before waiting for credentials
- backend listens on socket
- backend prints `FORGE_AGENT_LISTENING:{socket_path}` to stdout for Swift to read
- Swift delivers credentials via XPC
- backend sends ready message via XPC

---

### 2. Swift Client

Swift-side integration constraints:

- Swift reads Keychain
- Swift delivers credentials via XPC
- Swift reads the stdout line:
  - `FORGE_AGENT_LISTENING:{socket_path}`

Forbidden in Swift/backend boundary:

- backend reading Keychain
- LLM API call from Swift for backend responsibilities
- force unwrap as interface behavior dependency

---

### 3. GitHubTool

All GitHub operations integrate through:

- `GitHubTool`

Constraint:

- Never call the GitHub API directly from pipeline code.

Initialization dependency:

- `Initialize GitHubTool with token`

---

### 4. ConsensusEngine

Initialized after `GitHubTool` using:

- `API keys`

Constraint:

- credential initialization errors are non-fatal
- on such errors, emit `auth_error` XPC card and continue in degraded state

---

### 5. DocumentStore

Startup integration:

- `Start DocumentStore loading in background (async)`

Constraints:

- loading is async
- app remains responsive while embeddings load
- loaded document chunks must pass injection scanning before inclusion in any LLM prompt

---

### 6. CommandRouter

Operational integration:

- backend enters `CommandRouter event loop` after ready signaling

Constraint:

- startup ordering is mandatory

---

### 7. Path Security

Any disk write integration MUST call:

- `path_security.validate_write_path()`

before any write.

---

### 8. TrustLock

`CTX-ID` validation integrates with:

- `TrustLock public key`

Constraint:

- software-only validation is rejected

---

### 9. TrustFlow Audit Path

Every action outcome integrates with TrustFlow emission.

Constraints:

- synchronous in enforcement path
- no async buffering
- failure is `WARN-level audit event`
- failure must be logged and surfaced

---

## Notes on Undefined Fields

The provided source excerpts do **not** define full field-level schemas for:

- XPC credential message payload
- complete agent action object shape
- full `VTZEnforcementDecision` structure beyond `verdict=block`
- full `CTX-ID` token internals
- complete ready message shape beyond `agent_version` and `capabilities`

Implementations MUST NOT invent incompatible field names where the TRD is silent. Only the fields and exact values listed in this document are contractually defined by the provided source.