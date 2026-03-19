# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements explicitly available from the provided TRD/interface excerpts for the `ConsensusDevAgent` subsystem and its required integrations.

Where the source defines a field name or literal value, it is reproduced exactly.

---

### 1. Startup stdout signal

The backend startup sequence requires a stdout line emitted in this exact format:

```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | yes | Non-empty filesystem socket path inserted after the literal prefix `FORGE_AGENT_LISTENING:` |

#### Constraints
- Emitted at startup step 3.
- Must occur after:
  1. Initialize logger
  2. Start XPC server, listen on socket
- Must occur before:
  4. Wait for credentials via XPC (timeout: 30s)

---

### 2. XPC credentials input

The backend startup sequence requires credentials to be received via XPC.

#### Contract
- Credentials must arrive via XPC.
- Timeout for waiting on credentials: `30s`
- Python backend must not read credentials from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

#### Prohibited behavior
- Backend reading Keychain directly is forbidden.
- LLM API calls from Swift are forbidden.

No concrete credential payload field names are provided in the source excerpt, so no additional field-level schema can be asserted here.

---

### 3. Ready message via XPC

At startup step 8, the backend sends a ready message via XPC.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Included in ready message |
| `capabilities` | array | yes | Included in ready message; element type not specified in source |

#### Constraints
- Sent after:
  - GitHubTool initialization attempt
  - ConsensusEngine initialization attempt
  - DocumentStore background loading start
- Sent before:
  - CommandRouter event loop

---

### 4. Auth error XPC card

Credential initialization errors for GitHubTool and ConsensusEngine are non-fatal.

#### Contract
- On credential errors in step 5 or 6, emit `auth_error` XPC card.
- Continue in degraded state.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | string | implied | Value must be `auth_error` if represented as a typed message |

No additional `auth_error` card fields are defined in the provided source.

---

### 5. TrustFlow event

Every action outcome must emit a TrustFlow event.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | Must be globally unique; generated with CSPRNG; not sequential |
| `session_id` | string | yes | Required |
| `ctx_id` | string | yes | Required |
| `ts` | number | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Required |
| `payload_hash` | string | yes | Must be SHA-256 of the serialized action payload |

#### Constraints
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission must not be silently skipped.
- Every action outcome `(allow, restrict, block)` must emit a TrustFlow event.

---

### 6. VTZEnforcementDecision record

A VTZ policy denial must produce a `VTZEnforcementDecision` record.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | Must be `block` for policy denial |

No additional fields are defined in the provided source excerpt.

---

### 7. CTX-ID token

CTX-ID is a required identity/control token in the enforcement path.

#### Semantics
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- Old token is invalidated immediately.
- Expired CTX-ID must be rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.

#### Fields
No internal CTX-ID token field schema is provided in the source excerpt. Only token-level validation rules are normative.

---

### 8. Action payload for enforcement

Every action-processing entry point is subject to CAL/CTX-ID/VTZ enforcement.

#### Required associated values
Any processed action must have enough data to support:

| Derived/Associated Item | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | Must be validated first |
| serialized action payload | bytes/string | yes | Used to compute SHA-256 for `payload_hash` |
| action outcome | enum-like string | yes | One of `allow`, `restrict`, `block` |

No canonical action object field schema is provided in the source excerpt.

---

## Enums and Constants

### Literal message types and values

| Name | Type | Value |
|---|---|---|
| Startup stdout prefix | string | `FORGE_AGENT_LISTENING:` |
| XPC error card type | string | `auth_error` |
| Security refusal sentinel | string | `SECURITY_REFUSAL` |
| Missing CTX-ID trust state | string | `UNTRUSTED` |
| VTZ denial verdict | string | `block` |

### Action outcomes

| Name | Type | Allowed Values |
|---|---|---|
| TrustFlow action outcome | string | `allow`, `restrict`, `block` |

### Timeouts

| Name | Type | Value |
|---|---|---|
| Credential wait timeout | duration | `30s` |

### Cryptographic requirements

| Name | Type | Value |
|---|---|---|
| `payload_hash` algorithm | string | `SHA-256` |
| `event_id` randomness source | requirement | `CSPRNG` |

### Required startup order constants

The following ordered sequence is mandatory:

```text
1. Initialize logger
2. Start XPC server, listen on socket
3. Print FORGE_AGENT_LISTENING:{socket_path} to stdout
4. Wait for credentials via XPC (timeout: 30s)
5. Initialize GitHubTool with token
6. Initialize ConsensusEngine with API keys
7. Start DocumentStore loading in background (async)
8. Send ready message via XPC (includes agent_version, capabilities)
9. Enter CommandRouter event loop
```

---

## Validation Rules

### 1. CAL enforcement contract

Every entry point that processes an agent action MUST satisfy all of the following:

1. CTX-ID validation must occur first.
2. CTX-ID validation failure must cause immediate rejection.
3. No partial processing is allowed after CTX-ID validation failure.
4. VTZ policy check must occur before execution.
5. VTZ denial must produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every outcome must emit a TrustFlow event.
7. TrustFlow emission failure must not silently continue.
8. TrustFlow emission failure must be logged and surfaced.

---

### 2. TrustFlow validation

A valid TrustFlow event must satisfy:

- `event_id` present
- `session_id` present
- `ctx_id` present
- `ts` present
- `event_type` present
- `payload_hash` present

Additional constraints:

- `event_id` must be globally unique.
- `event_id` must not be sequential.
- `event_id` must come from a CSPRNG.
- `ts` must be a UTC Unix timestamp with millisecond precision.
- `payload_hash` must equal the SHA-256 of the serialized action payload.
- Emission must be synchronous in the enforcement path.
- Async buffering is forbidden.

---

### 3. CTX-ID validation

A valid CTX-ID handling path must satisfy:

- Missing CTX-ID => treat as `UNTRUSTED`
- Expired CTX-ID => reject
- Rotated CTX-ID => old token invalid immediately
- Token fields must not be modified after issuance
- Validation must be against TrustLock public key
- Software-only validation is rejected

---

### 4. VTZ enforcement

A valid VTZ enforcement implementation must satisfy:

- Every agent session is bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit authorization is denied
- VTZ boundaries are structural and cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session

---

### 5. Security validation

#### Forbidden behaviors
- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Never retry to bypass `SECURITY_REFUSAL`.
- Never force unwrap optionals in Swift.
- Never call the GitHub API directly from pipeline code.
- Never make LLM API calls from Swift.
- Never read backend credentials from Keychain in Python.

#### Required behaviors
- Log HTTP status codes and error types only.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents must go in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log. Never retry to bypass.

---

### 6. Python/backend implementation requirements

- Python version: `3.12`
- Type annotations required on every function
- `async/await` throughout backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Tests use `pytest`
- Tests live in `tests/` and mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage must be `≥ 85%` on all new modules

---

### 7. GitHub integration validation

- All GitHub operations go through `GitHubTool`
- Never call the GitHub API directly from pipeline code

---

## Wire Format Examples

## Valid payloads

### 1. Startup stdout line

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

Why valid:
- Uses exact required prefix
- Includes a non-empty `socket_path`

---

### 2. Ready XPC message

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

Why valid:
- Includes required fields `agent_version` and `capabilities`

Note:
- Capability value set is illustrative only; the source defines the field names but not the allowed capability enum.

---

### 3. Auth error XPC card

```json
{
  "type": "auth_error"
}
```

Why valid:
- Uses the required literal `auth_error`

Note:
- Additional fields are not defined in the provided source.

---

### 4. TrustFlow event

```json
{
  "event_id": "8f5f7c4f-8e2e-4c34-bf3e-2a4c1f8b6a0d",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1710000000123,
  "event_type": "action_executed",
  "payload_hash": "6f1ed002ab5595859014ebf0951522d9d2a8b6a0c0f8b6f8e5d4c3b2a1908765"
}
```

Why valid:
- Contains all required fields
- `ts` shown as Unix milliseconds
- `payload_hash` shown as SHA-256-style hex string

Note:
- `event_type` allowed value set is not specified in the source; only presence is required.

---

### 5. VTZ enforcement denial record

```json
{
  "verdict": "block"
}
```

Why valid:
- Uses required denial verdict literal

---

## Invalid payloads

### 1. Invalid startup stdout line

```text
FORGE_AGENT_READY:/tmp/forge-agent.sock
```

Why invalid:
- Prefix must be exactly `FORGE_AGENT_LISTENING:`

---

### 2. Invalid ready XPC message

```json
{
  "agent_version": "1.0.0"
}
```

Why invalid:
- Missing required field `capabilities`

---

### 3. Invalid auth error XPC card

```json
{
  "type": "authentication_error"
}
```

Why invalid:
- Literal must be exactly `auth_error`

---

### 4. Invalid TrustFlow event: missing field

```json
{
  "event_id": "evt_1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1710000000123,
  "payload_hash": "abc"
}
```

Why invalid:
- Missing required field `event_type`

---

### 5. Invalid TrustFlow event: bad timestamp precision/source semantics

```json
{
  "event_id": "1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1710000000,
  "event_type": "action_executed",
  "payload_hash": "abc"
}
```

Why invalid:
- `event_id` must be globally unique and not sequential
- `ts` must be UTC Unix timestamp with millisecond precision

---

### 6. Invalid VTZ denial record

```json
{
  "verdict": "deny"
}
```

Why invalid:
- Policy denial must produce `VTZEnforcementDecision` with `verdict=block`

---

### 7. Invalid CTX-ID handling example

```json
{
  "ctx_id": null,
  "inferred_identity": "user_from_session"
}
```

Why invalid:
- Missing CTX-ID must be treated as `UNTRUSTED`
- Identity must never be inferred from context when CTX-ID is missing

---

## Integration Points

### 1. XPC
Used for:
- Credential delivery to backend
- Ready message delivery
- `auth_error` card delivery

Startup sequence requirements:
- XPC server must start before stdout listening signal
- Credentials are awaited via XPC with timeout `30s`

---

### 2. GitHubTool
Used for:
- All GitHub operations
- Initialization at startup step 5 using token

Constraints:
- All GitHub operations must go through `GitHubTool`
- Direct GitHub API calls from pipeline code are forbidden

---

### 3. ConsensusEngine
Used for:
- Initialization at startup step 6 using API keys

Constraints:
- Credential errors are non-fatal
- Must emit `auth_error` XPC card on credential error
- Continue in degraded state

---

### 4. DocumentStore
Used for:
- Background loading at startup step 7

Constraints:
- Loading is async
- App remains responsive while embeddings load
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt

---

### 5. CommandRouter
Used for:
- Event loop entered at startup step 9

Constraints:
- Must not start before ready message via XPC is sent

---

### 6. path_security
Required API call before any disk write:

```python
path_security.validate_write_path()
```

Constraints:
- All file paths written to disk must pass `path_security.validate_write_path()` before any write

---

### 7. TrustLock public key validation
Used for:
- CTX-ID validation

Constraints:
- CTX-ID must be validated against TrustLock public key
- Software-only validation is rejected

---

### 8. TrustFlow
Used for:
- Synchronous audit/event emission for all action outcomes

Constraints:
- Emission is mandatory for `allow`, `restrict`, and `block`
- Emission failure must be logged and surfaced
- Emission failure must not be silently ignored

---

### 9. USER vs SYSTEM prompt placement
For any external document context passed to an LLM:

- External document context must be placed in the USER prompt
- External document context must never be placed in the SYSTEM prompt

---

### 10. SECURITY_REFUSAL handling
If LLM output contains:

```text
SECURITY_REFUSAL
```

Required behavior:
- stop
- gate
- log

Forbidden behavior:
- retry to bypass
- fallback regeneration intended to circumvent refusal

---

## Notes on Unspecified Fields

The provided source excerpt does **not** define full field-level schemas for:
- credential XPC payloads
- ready message envelope/type discriminator
- auth_error card envelope beyond the literal `auth_error`
- CTX-ID token internal field structure
- action payload object schema
- ConsensusEngine API key field names
- DocumentStore chunk object schema
- CommandRouter request/response message schema

These fields must not be invented in implementations claiming conformance to this document without an owning TRD defining them.