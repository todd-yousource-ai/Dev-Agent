# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the `ConsensusDevAgent` subsystem based only on the provided TRD/interface content.

Where the source material does not define a concrete JSON schema, transport envelope, or exact field set, this document preserves the exact contractual requirements and marks unspecified items as implementation-defined.

---

### 1. XPC Startup Handshake: Listening Announcement

Printed by backend to `stdout` during startup.

#### Wire format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | yes | Must be the socket path the XPC server is listening on |

#### Constraints
- Emitted at startup step 3.
- Must occur after:
  1. Initialize logger
  2. Start XPC server, listen on socket
- Must occur before:
  4. Wait for credentials via XPC (timeout: 30s)

---

### 2. XPC Credentials Delivery

Credentials are delivered from Swift to Python via XPC.

#### Contract
- Swift may read Keychain.
- Python reads nothing from Keychain.
- Backend credentials must arrive via XPC.
- Waiting for credentials via XPC has a timeout of `30s`.

#### Data structure: `CredentialsViaXPC`
Exact field names are not defined in the provided source. The following required semantic fields are defined by the startup sequence.

| Semantic field | Type | Required | Constraints |
|---|---|---:|---|
| GitHub token | string | conditional | Required to initialize `GitHubTool`; credential errors are non-fatal |
| Consensus engine API keys | object or map of string to string | conditional | Required to initialize `ConsensusEngine`; credential errors are non-fatal |

#### Constraints
- Credential absence or invalidity in steps 5-6 is non-fatal.
- On credential error, backend must emit an `auth_error` XPC card and continue in degraded state.
- No credential may be hardcoded as a string literal.

---

### 3. XPC Ready Message

Sent after startup initialization completes.

#### Contract
- Sent at startup step 8 via XPC.
- Includes `agent_version`, `capabilities`.

#### Data structure: `ReadyMessage`

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Version identifier of the running agent |
| `capabilities` | array | yes | Capability list exposed to client |

#### Constraints
- Must be sent after:
  - `GitHubTool` initialization attempt
  - `ConsensusEngine` initialization attempt
  - `DocumentStore` background loading start
- `DocumentStore` loading is async; readiness does not imply document loading completion.

---

### 4. XPC Auth Error Card

Emitted when credentials for `GitHubTool` or `ConsensusEngine` fail initialization.

#### Data structure: `AuthErrorCard`

Only the card name is specified by source.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | string | implementation-defined | Should identify the card as `auth_error` if represented as a typed envelope |

#### Constraints
- Must be emitted on credential errors in startup steps 5-6.
- Emission is required even though startup continues in degraded state.

---

### 5. TrustFlow Event

Every action outcome must emit a TrustFlow event.

#### Data structure: `TrustFlowEvent`

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | Must be globally unique; CSPRNG-generated; not sequential |
| `session_id` | string | yes | Session identifier |
| `ctx_id` | string | yes | CTX-ID associated with the action |
| `ts` | number or integer | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Event classification |
| `payload_hash` | string | yes | Must be SHA-256 of the serialized action payload |

#### Constraints
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission must not be silently skipped.
- Every action outcome must emit a TrustFlow event for:
  - allow
  - restrict
  - block

---

### 6. VTZ Enforcement Decision

Produced when VTZ policy denies an action.

#### Data structure: `VTZEnforcementDecision`

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | Must equal `block` when VTZ policy denies |

#### Constraints
- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 7. CTX-ID Token

Represents the trust-bound session context token.

#### Data structure: `CTX-ID`
Exact internal field names are not defined in the provided source.

| Semantic field | Type | Required | Constraints |
|---|---|---:|---|
| token value | string or structured token | yes | Immutable once issued |
| issuance binding to VTZ | string | yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance |
| expiration | timestamp | implementation-defined | Expired CTX-ID must be rejected |
| signature / verification material | implementation-defined | yes | Must validate against TrustLock public key |

#### Constraints
- Immutable once issued.
- Rotation creates a new token.
- Old token is invalidated immediately on rotation.
- Expired token must be rejected.
- Clock skew tolerance is deployment-defined.
- Validation must be against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from surrounding context when CTX-ID is missing.

---

### 8. Action Payload

Payload processed by an agent action in the CAL/VTZ/TrustFlow path.

#### Data structure: `ActionPayload`
Exact field names are not defined in the provided source.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| serialized action payload | bytes or string | yes | Used as input to SHA-256 for `payload_hash` |

#### Constraints
- Every entry point that processes an agent action must validate CTX-ID first.
- CTX-ID validation failure must result in immediate rejection.
- No partial processing is allowed on CTX-ID validation failure.
- VTZ policy check must occur before execution.

---

### 9. Document Chunk for LLM Prompting

Represents externally loaded content used in LLM prompt construction.

#### Data structure: `DocumentChunk`
Exact field names are not defined in the provided source.

| Semantic field | Type | Required | Constraints |
|---|---|---:|---|
| chunk content | string | yes | Must pass injection scanning before inclusion in any LLM prompt |
| source metadata | implementation-defined | optional | Not specified |

#### Constraints
- All loaded document chunks must pass injection scanning before being included in any LLM prompt.
- Context from external documents must go in the `USER` prompt, never the `SYSTEM` prompt.

---

### 10. File Write Path

Represents any file path written to disk.

#### Data structure: `WritePath`

| Field | Type | Required | Constraints |
|---|---|---:|---|
| path | string | yes | Must pass `path_security.validate_write_path()` before any write |

#### Constraints
- Validation must occur before any write.
- Unvalidated write paths are non-conformant.

---

## Enums and Constants

### String Constants

| Name | Value |
|---|---|
| Listening prefix | `FORGE_AGENT_LISTENING:` |
| XPC error card type/name | `auth_error` |
| Security refusal marker | `SECURITY_REFUSAL` |
| Missing CTX-ID trust classification | `UNTRUSTED` |
| VTZ denial verdict | `block` |

---

### Startup Order Constants

Mandatory backend startup sequence:

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

#### Timing constant

| Name | Value |
|---|---|
| Credentials wait timeout | `30s` |

---

### Enforcement Outcome Values

The source defines the following action outcomes:

| Value |
|---|
| `allow` |
| `restrict` |
| `block` |

These are required as semantic outcomes for TrustFlow emission. Only `block` is explicitly required as the `VTZEnforcementDecision.verdict` value on denial.

---

## Validation Rules

### 1. General Implementation Rules
- Python version must be `Python 3.12`.
- Type annotations are required on every function.
- Backend must use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses are required for all structured data.
- Tests must use `pytest`.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be `≥ 85%` on all new modules.

---

### 2. Security Rules
- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Only log status codes and error types.
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.
- When output contains `SECURITY_REFUSAL`: stop, gate, log. Never retry to bypass.

#### Explicitly forbidden patterns
- Retrying an LLM call to bypass `SECURITY_REFUSAL`
- Swift force unwrap: `optional!`
- LLM API call from Swift
- Python backend reading Keychain directly

---

### 3. Startup Validation Rules
- Startup order is mandatory and must not be changed.
- `FORGE_AGENT_LISTENING:{socket_path}` must be printed before waiting for credentials.
- Waiting for credentials must time out at `30s`.
- Initialization failures for `GitHubTool` and `ConsensusEngine` due to credentials are non-fatal.
- On such failures, emit `auth_error` and continue in degraded state.
- `DocumentStore` loading must be background async.
- Application must remain responsive while embeddings load.

---

### 4. GitHub Integration Rules
- All GitHub operations must go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

---

### 5. CAL Enforcement Rules
For every entry point that processes an agent action:

1. CTX-ID validation must happen first.
2. If CTX-ID validation fails:
   - reject immediately
   - do not partially process
3. VTZ policy must be checked before execution.
4. If VTZ denies:
   - produce `VTZEnforcementDecision` with `verdict=block`
5. Every action outcome must emit a TrustFlow event.
6. If TrustFlow emission fails:
   - do not silently continue
   - log and surface the failure

---

### 6. TrustFlow Validation Rules
A `TrustFlowEvent` is valid only if:
- `event_id` is globally unique
- `event_id` is generated by CSPRNG
- `event_id` is not sequential
- `ts` is a UTC Unix timestamp with millisecond precision
- `payload_hash` equals the SHA-256 of the serialized action payload
- emission is synchronous in the enforcement path

---

### 7. CTX-ID Validation Rules
A CTX-ID is valid only if:
- it has not been modified after issuance
- it has not expired
- it validates against TrustLock public key
- it is present when trusted execution is required

Additional rules:
- rotation issues a new token
- old token becomes invalid immediately
- missing CTX-ID => `UNTRUSTED`
- never infer identity from context if CTX-ID is missing

---

### 8. VTZ Validation Rules
- Every agent session must be bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## Wire Format Examples

## Valid Payloads

### 1. Listening announcement
```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

---

### 2. Ready message
```json
{
  "agent_version": "1.2.3",
  "capabilities": ["github", "consensus", "document_store"]
}
```

Note: capability values are implementation-defined; only the presence of `agent_version` and `capabilities` is contractually specified.

---

### 3. TrustFlow event
```json
{
  "event_id": "3f7d8c72-7f26-4d82-bb0e-2a1ce0f5b8c1",
  "session_id": "sess_01HVABCXYZ",
  "ctx_id": "ctx_01HVABCXYZ",
  "ts": 1712345678123,
  "event_type": "action_blocked",
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa13514a8afa1920fdfd6b8a7c0f2f99"
}
```

---

### 4. VTZ enforcement decision
```json
{
  "verdict": "block"
}
```

---

### 5. External document chunk placement rule
Valid prompt placement:
```json
{
  "system": "You are the backend agent.",
  "user": "External document context: <chunk content after injection scan>"
}
```

---

## Invalid Payloads

### 1. Missing required TrustFlow fields
```json
{
  "event_id": "123",
  "event_type": "action_allowed"
}
```

Invalid because:
- missing `session_id`
- missing `ctx_id`
- missing `ts`
- missing `payload_hash`

---

### 2. Invalid VTZ denial record
```json
{
  "verdict": "deny"
}
```

Invalid because:
- denial verdict must be exactly `block`

---

### 3. Invalid external context placement
```json
{
  "system": "External document content copied here"
}
```

Invalid because:
- external document context must go in the `USER` prompt, never the `SYSTEM` prompt

---

### 4. Invalid startup order behavior
```text
1. Initialize logger
2. Wait for credentials via XPC
3. Start XPC server
```

Invalid because:
- startup order is mandatory
- XPC server must start before waiting for credentials
- listening announcement must be printed before waiting for credentials

---

### 5. Invalid security refusal handling
```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Invalid because:
- `SECURITY_REFUSAL` must cause stop, gate, and log
- retry to bypass is forbidden

---

### 6. Invalid backend credential access
```python
token = KeychainKit.read("github_token")
```

Invalid because:
- Python reads nothing from Keychain
- only Swift reads Keychain, only to deliver via XPC

---

### 7. Invalid subprocess usage
```python
subprocess.run(cmd, shell=True)
```

Invalid because:
- `shell=True` is forbidden

---

## Integration Points

### Swift ↔ Python Backend
- Transport: XPC
- Swift responsibilities:
  - read Keychain if needed
  - deliver credentials via XPC
- Python responsibilities:
  - never read Keychain directly
  - wait up to `30s` for credentials
  - emit `auth_error` on credential initialization failure
  - send ready message including `agent_version`, `capabilities`

---

### Backend Startup Components
- `logger`
- XPC server
- `GitHubTool`
- `ConsensusEngine`
- `DocumentStore`
- `CommandRouter`

#### Integration ordering
1. `logger`
2. XPC server
3. stdout listening announcement
4. credentials via XPC
5. `GitHubTool`
6. `ConsensusEngine`
7. `DocumentStore` background loading
8. XPC ready message
9. `CommandRouter`

---

### GitHub Integration
- All GitHub operations must flow through `GitHubTool`.
- Pipeline code must not call GitHub API directly.

---

### Trust / Enforcement Integration
- Every action entry point integrates:
  1. CTX-ID validation
  2. VTZ policy evaluation
  3. `VTZEnforcementDecision` creation on deny
  4. synchronous TrustFlow emission

---

### File System Integration
- Before any disk write:
  - call `path_security.validate_write_path()`

---

### LLM Prompt Construction Integration
- Before including external content:
  - run injection scanning on every loaded document chunk
- When constructing prompts:
  - external document context goes in `USER`
  - never in `SYSTEM`
- On `SECURITY_REFUSAL`:
  - stop
  - gate
  - log
  - never retry to bypass

---

### Testing and Quality Integration
Before code changes:
```bash
cd src && pytest ../tests/ -v --tb=short
```

Required quality gates:
- `pytest`
- `ruff`
- `mypy`
- coverage `≥ 85%` on new modules

---

## Notes on Unspecified Fields

The provided source does **not** define exact wire field names for:
- credential XPC payloads
- auth error card envelope fields beyond `auth_error`
- CTX-ID token internal schema
- action payload object schema
- document chunk metadata schema
- capability item schema

Implementations must not invent incompatible public contracts without the owning TRD. Only the exact requirements listed above are considered normative from the supplied source.