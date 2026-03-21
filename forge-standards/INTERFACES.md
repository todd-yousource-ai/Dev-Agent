# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the `ConsensusDevAgent` subsystem based strictly on the provided TRD content and Forge component interface contracts.

Where a field, payload, or structure is not explicitly defined in the source text, it is marked as **unspecified in source** and MUST NOT be invented by implementers without an owning TRD update.

---

### 1. Backend Startup stdout signal

Printed by backend during startup sequence.

#### Message
- **Type:** plain stdout line
- **Format:** string
- **Required:** yes
- **Exact value pattern:** `FORGE_AGENT_LISTENING:{socket_path}`

#### Fields
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | yes | Substituted into the stdout line after the literal prefix `FORGE_AGENT_LISTENING:` |

#### Constraints
- Must be emitted at startup step 3.
- Must occur after:
  1. Initialize logger
  2. Start XPC server, listen on socket
- Must occur before:
  4. Wait for credentials via XPC (timeout: 30s)

---

### 2. XPC credentials delivery

Credentials are delivered from Swift to backend via XPC.

#### Contract
- **Transport:** XPC
- **Producer:** Swift
- **Consumer:** Python backend
- **Required at startup:** yes
- **Wait timeout:** `30s`

#### Payload
- **Exact fields:** unspecified in source
- **Known semantic contents:** credentials, including:
  - GitHub token
  - API keys for `ConsensusEngine`

#### Constraints
- Python backend reads credentials from XPC only.
- Python backend MUST NOT read credentials from Keychain.
- Swift may read Keychain only to deliver credentials via XPC.
- Credential literals MUST NEVER be hardcoded.

---

### 3. XPC auth error card

Emitted when startup steps 5 or 6 encounter credential errors.

#### Message
- **Name:** `auth_error`
- **Transport:** XPC
- **Required on credential error:** yes

#### Payload
- **Fields:** unspecified in source

#### Constraints
- Must be emitted for credential errors during:
  - `Initialize GitHubTool with token`
  - `Initialize ConsensusEngine with API keys`
- These errors are **non-fatal**.
- Backend MUST continue in degraded state after emission.

---

### 4. XPC ready message

Sent after background document loading has started.

#### Message
- **Transport:** XPC
- **Required:** yes
- **Startup step:** 8

#### Fields
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Included in ready message |
| `capabilities` | array | yes | Included in ready message; element type unspecified in source |

#### Constraints
- Must be sent after:
  - `Start DocumentStore loading in background (async)`
- Must be sent before:
  - `Enter CommandRouter event loop`

---

### 5. TrustFlow event

Every action outcome must emit a TrustFlow event.

#### Structure
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | Must be globally unique; generated using CSPRNG; must not be sequential |
| `session_id` | string | yes | Exact format unspecified in source |
| `ctx_id` | string | yes | Must reference CTX-ID for the action |
| `ts` | number | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Exact allowed values unspecified in source |
| `payload_hash` | string | yes | Must be SHA-256 of the serialized action payload |

#### Constraints
- Emission is mandatory for every action outcome:
  - allow
  - restrict
  - block
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission:
  - must not silently continue
  - is a WARN-level audit event

---

### 6. VTZEnforcementDecision record

Produced when VTZ policy denies an action.

#### Structure
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | Must equal exactly `block` |

#### Constraints
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record.
- For denial, `verdict=block` is mandatory.
- Additional fields are unspecified in source.

---

### 7. CTX-ID token

Identity/trust token used for validation and session binding.

#### Structure
- Exact field schema: unspecified in source

#### Required semantic properties
| Property | Requirement |
|---|---|
| mutability | CTX-ID tokens are immutable once issued |
| rotation | Rotation creates a new token; old token is invalidated immediately |
| expiry | Expired CTX-ID must be rejected |
| validation | Must be validated against TrustLock public key |
| missing token handling | Missing CTX-ID must be treated as `UNTRUSTED` |
| session binding | Every agent session is bound to exactly one VTZ at CTX-ID issuance |

#### Constraints
- No field modification is allowed after issuance.
- Software-only validation is rejected.
- Clock skew tolerance is deployment-defined, not specified here.
- Identity must never be inferred from context when CTX-ID is missing.

---

### 8. Agent action payload

Payload processed by an action entry point.

#### Structure
- Exact field schema: unspecified in source

#### Constraints
- Every entry point that processes an agent action MUST:
  1. call CTX-ID validation first
  2. reject immediately on CTX-ID validation failure
  3. check action against VTZ policy before execution
- Serialized form of this payload is the input to SHA-256 for `payload_hash`.

---

### 9. Document chunk for LLM prompt inclusion

Loaded document chunks are used as external context.

#### Structure
- Exact field schema: unspecified in source

#### Constraints
- Every loaded document chunk must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents must be placed in the USER prompt, never the SYSTEM prompt.

---

### 10. SECURITY_REFUSAL output

Security refusal signal from the LLM.

#### Value
- **Type:** string token / substring
- **Exact value:** `SECURITY_REFUSAL`

#### Constraints
- If `SECURITY_REFUSAL` appears in output:
  - stop
  - gate
  - log
- Must never retry to bypass.
- Retrying generation after `SECURITY_REFUSAL` is forbidden.

---

## Enums and Constants

### Exact string constants

| Name | Type | Exact Value |
|---|---|---|
| Security refusal token | string | `SECURITY_REFUSAL` |
| Startup stdout prefix | string | `FORGE_AGENT_LISTENING:` |
| Auth error message name | string | `auth_error` |
| VTZ denial verdict | string | `block` |
| Missing CTX-ID trust state | string | `UNTRUSTED` |

---

### Startup sequence constants

| Name | Type | Exact Value |
|---|---|---|
| Credentials wait timeout | duration/string | `30s` |

---

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

---

### Outcome set for action processing

| Name | Type | Allowed Values |
|---|---|---|
| Action outcome | enum/string | `allow`, `restrict`, `block` |

These values are sourced from: “Every action outcome (allow, restrict, block) MUST emit a TrustFlow event”.

---

## Validation Rules

### 1. CAL enforcement validation

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur first.
2. If CTX-ID validation fails:
   - immediate rejection is required
   - no partial processing is allowed
3. VTZ policy evaluation MUST occur before execution.
4. If VTZ policy denies the action:
   - produce `VTZEnforcementDecision`
   - set `verdict` to `block`
5. Every outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
6. TrustFlow emission failure:
   - MUST NOT silently continue
   - MUST be logged
   - MUST be surfaced

---

### 2. TrustFlow event validation

A TrustFlow event is valid only if:

- `event_id` is present
- `session_id` is present
- `ctx_id` is present
- `ts` is present
- `event_type` is present
- `payload_hash` is present

Additional validation:

- `event_id` MUST be globally unique
- `event_id` MUST be generated via CSPRNG
- `event_id` MUST NOT be sequential
- `ts` MUST be UTC Unix timestamp with millisecond precision
- `payload_hash` MUST equal SHA-256 of the serialized action payload

Operational validation:

- emission MUST be synchronous in enforcement path
- async buffering MUST NOT be used

---

### 3. CTX-ID validation

A CTX-ID is valid only if all are true:

- present, unless the request is to be treated as `UNTRUSTED`
- not expired
- validated against TrustLock public key
- not modified after issuance
- not invalidated by rotation

Additional rules:

- rotation MUST create a new token
- old token MUST be invalidated immediately
- software-only validation is rejected
- missing CTX-ID MUST NOT be replaced by inferred identity

---

### 4. VTZ validation

- every agent session MUST be bound to exactly one VTZ at CTX-ID issuance
- cross-VTZ tool calls require explicit policy authorization
- implicit authorization is denied
- VTZ boundaries are structural and cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session

---

### 5. Startup behavior validation

#### Required behavior
- Steps 1 through 9 must occur in the specified order.
- Step 7 must be asynchronous.
- Application must remain responsive while embeddings load.

#### Credential error handling
- Step 5 credential errors are non-fatal.
- Step 6 credential errors are non-fatal.
- On such errors, emit `auth_error` XPC card and continue in degraded state.

---

### 6. Security validation

#### Credentials
- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

#### Process execution
- Never use `shell=True` in subprocess calls.

#### Code execution
- Never call `eval()` or `exec()` on generated or external content.

#### Logging
- Never log HTTP response bodies.
- Log status codes and error types only.

#### File writes
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

#### Prompt construction
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

#### LLM refusal handling
- On `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.

---

### 7. Language and implementation conformance

#### Python backend
- Python version: `3.12`
- Type annotations required on every function
- `async/await` throughout backend
- No blocking calls on event loop
- Dataclasses for all structured data

#### Testing
- Test framework: `pytest`
- Tests location: `tests/`
- Tests mirror: `src/` structure
- Linting: `ruff`
- Type checking: `mypy`
- Coverage requirement: `≥ 85%` on all new modules

---

### 8. GitHub integration validation

- All GitHub operations must go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

---

## Wire Format Examples

Only fields explicitly defined in source are shown as normative.

### 1. Valid stdout startup signal

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

Why valid:
- Uses exact required prefix `FORGE_AGENT_LISTENING:`
- Includes a `socket_path` value

---

### 2. Invalid stdout startup signal

```text
FORGE_AGENT_READY:/tmp/forge-agent.sock
```

Why invalid:
- Prefix is not exactly `FORGE_AGENT_LISTENING:`

---

### 3. Valid TrustFlow event

```json
{
  "event_id": "9d7f0a4d-0a79-4f1a-9d52-6a4f19c0df31",
  "session_id": "sess-123",
  "ctx_id": "ctx-abc",
  "ts": 1735689600123,
  "event_type": "action.blocked",
  "payload_hash": "3b7e7d0c58eb2f4f6bfa6b5b4f9f1d9d8e1e2c1f4b6a7d8e9f00112233445566"
}
```

Why valid:
- Contains all required fields
- `ts` is a Unix timestamp in milliseconds
- `payload_hash` is represented as SHA-256 hex string form
- `event_id` is non-sequential in shape

Note:
- `session_id`, `ctx_id`, and `event_type` exact formats are unspecified in source; example is illustrative only.

---

### 4. Invalid TrustFlow event: missing required field

```json
{
  "event_id": "9d7f0a4d-0a79-4f1a-9d52-6a4f19c0df31",
  "session_id": "sess-123",
  "ctx_id": "ctx-abc",
  "ts": 1735689600123,
  "payload_hash": "3b7e7d0c58eb2f4f6bfa6b5b4f9f1d9d8e1e2c1f4b6a7d8e9f00112233445566"
}
```

Why invalid:
- Missing required field `event_type`

---

### 5. Invalid TrustFlow event: bad timestamp precision

```json
{
  "event_id": "9d7f0a4d-0a79-4f1a-9d52-6a4f19c0df31",
  "session_id": "sess-123",
  "ctx_id": "ctx-abc",
  "ts": 1735689600,
  "event_type": "action.allowed",
  "payload_hash": "3b7e7d0c58eb2f4f6bfa6b5b4f9f1d9d8e1e2c1f4b6a7d8e9f00112233445566"
}
```

Why invalid:
- `ts` must be UTC Unix timestamp with millisecond precision

---

### 6. Valid VTZEnforcementDecision record

```json
{
  "verdict": "block"
}
```

Why valid:
- Denial verdict matches exact required value `block`

---

### 7. Invalid VTZEnforcementDecision record

```json
{
  "verdict": "deny"
}
```

Why invalid:
- Verdict must equal exactly `block`

---

### 8. Valid XPC ready message

```json
{
  "agent_version": "1.0.0",
  "capabilities": []
}
```

Why valid:
- Includes required fields `agent_version` and `capabilities`

Note:
- Capability element schema is unspecified in source.

---

### 9. Invalid XPC ready message

```json
{
  "agent_version": "1.0.0"
}
```

Why invalid:
- Missing required field `capabilities`

---

### 10. Invalid refusal handling pattern

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Why invalid:
- Retries after `SECURITY_REFUSAL`
- Explicitly forbidden by contract

---

## Integration Points

### 1. Swift ↔ Python backend over XPC

#### Direction
- Swift → Python: credentials
- Python → Swift: `auth_error` card, ready message

#### Constraints
- Swift is the only side that may read Keychain
- Python backend must receive backend credentials via XPC
- Startup waits for credentials for `30s`

---

### 2. Stdout integration with Swift launcher

#### Message
- `FORGE_AGENT_LISTENING:{socket_path}`

#### Purpose
- Swift reads this line to discover socket path

#### Constraints
- Must be printed exactly during startup step 3

---

### 3. GitHub integration

#### Component
- `GitHubTool`

#### Contract
- All GitHub operations go through `GitHubTool`
- Direct GitHub API calls from pipeline code are forbidden

---

### 4. Consensus engine initialization

#### Component
- `ConsensusEngine`

#### Inputs
- API keys delivered via XPC credentials flow

#### Error behavior
- Credential errors are non-fatal
- Must emit `auth_error`
- Must continue in degraded state

---

### 5. Document store and prompt pipeline

#### Component
- `DocumentStore`

#### Startup behavior
- Starts loading in background asynchronously

#### Prompt safety contract
- Loaded chunks must pass injection scanning
- External document context must be included only in USER prompt

---

### 6. Command routing

#### Component
- `CommandRouter`

#### Startup relationship
- Event loop begins only after ready message is sent

---

### 7. Trust and policy infrastructure

#### Components / concepts
- CTX-ID
- VTZ policy
- TrustFlow
- TrustLock public key

#### Processing order
1. Validate CTX-ID
2. Enforce VTZ policy
3. Execute or deny action
4. Emit TrustFlow event synchronously

---

### 8. File path security integration

#### Function
- `path_security.validate_write_path()`

#### Contract
- Every file path written to disk must pass this validation before any write

---

### 9. Testing/tooling integration

#### Required commands and tools
- Test command:
  ```bash
  cd src && pytest ../tests/ -v --tb=short
  ```
- Test framework: `pytest`
- Lint: `ruff`
- Type check: `mypy`

---

## Notes on Unspecified Interfaces

The following schemas are referenced but not fully defined in the provided source and therefore remain non-normative until an owning TRD defines them:

- XPC credentials payload field names and types
- XPC `auth_error` payload schema
- `capabilities` item schema in ready message
- Full CTX-ID token field layout
- Full agent action payload field layout
- Full `VTZEnforcementDecision` schema beyond `verdict`
- Allowed `event_type` values for TrustFlow events
- Document chunk field layout
- Socket path format constraints beyond string substitution in stdout line

Implementers MUST NOT invent compatibility-critical wire fields for these without an owning TRD update.