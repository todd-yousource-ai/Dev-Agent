# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements explicitly stated in the provided TRD content for the `ConsensusDevAgent` subsystem and its required Forge interface contracts.

Where the TRD does not define a fielded payload shape, this document does not invent one. Only fields, values, and constraints present in source are included.

---

### 1. TrustFlow Event

Required by: **TrustFlow Emission Contract**

#### Type
Structured event record.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | MUST be globally unique; MUST be generated using CSPRNG; MUST NOT be sequential |
| `session_id` | string | yes | Required on every TrustFlow event |
| `ctx_id` | string | yes | Required on every TrustFlow event |
| `ts` | number | yes | MUST be UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Required on every TrustFlow event |
| `payload_hash` | string | yes | MUST be SHA-256 of the serialized action payload |

#### Behavioral constraints
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission:
  - MUST NOT silently continue
  - MUST be logged
  - MUST be surfaced
  - MUST be treated as a WARN-level audit event

---

### 2. VTZEnforcementDecision

Required by: **CAL Enforcement Contract**

#### Type
Structured enforcement decision record.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | For VTZ policy denial, value MUST be exactly `block` |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 3. CTX-ID Token

Required by: **CTX-ID Contract**

#### Type
Opaque token value used for identity and trust binding.

#### Representation
The TRD defines behavioral requirements but does not define internal fields. Treat as an opaque token string at interfaces unless a separate TRD defines structure.

#### Constraints
- MUST be validated first at every entry point that processes an agent action.
- Validation failure MUST result in immediate rejection.
- MUST be immutable once issued.
- Rotation creates a new token.
- Old token is invalidated immediately on rotation.
- Expired token MUST be rejected.
- Missing token MUST be treated as `UNTRUSTED`.
- MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Identity MUST NEVER be inferred from surrounding context when `ctx_id` is missing.

---

### 4. Agent Action Payload

#### Type
Serialized action payload.

#### Constraints
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- Every action MUST be checked against VTZ policy BEFORE execution.
- `payload_hash` for TrustFlow events MUST be computed as SHA-256 of the serialized action payload.

#### Notes
The TRD excerpt does not define the field schema of the action payload itself.

---

### 5. XPC Ready Message

Required by: **Backend Startup Sequence**

#### Type
Structured XPC message.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Included in ready message |
| `capabilities` | array | yes | Included in ready message; element type not further specified in provided TRD |

#### Behavioral constraints
- MUST be sent via XPC at startup step 8.
- MUST occur after:
  1. logger initialization
  2. XPC server start
  3. stdout listening line emission
  4. credential wait
  5. `GitHubTool` initialization
  6. `ConsensusEngine` initialization
  7. `DocumentStore` background loading start
- Startup order is mandatory and MUST NOT be changed.

---

### 6. XPC auth_error Card

Required by: **Backend Startup Sequence**

#### Type
Structured XPC message/card.

#### Fields
The provided TRD names the message/card type only:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | string | implied | Value is `auth_error` if represented as a tagged payload |

#### Behavioral constraints
- On credential errors in steps 5-6:
  - initialization is non-fatal
  - backend MUST emit `auth_error` XPC card
  - backend MUST continue in degraded state

#### Notes
No additional payload fields are defined in the provided TRD.

---

### 7. Backend Listening Announcement

Required by: **Backend Startup Sequence**

#### Type
Stdout line.

#### Format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Components

| Component | Type | Required | Constraints |
|---|---|---:|---|
| `FORGE_AGENT_LISTENING:` | string literal prefix | yes | MUST appear exactly as shown |
| `{socket_path}` | string | yes | Socket path for Swift to read |

#### Behavioral constraints
- MUST be printed to stdout.
- MUST occur after XPC server starts listening.
- Swift reads this value.

---

### 8. Credentials via XPC

Required by: **Backend Startup Sequence**

#### Type
XPC-delivered credentials payload.

#### Fields
The provided TRD does not define field names. Only these semantic contents are defined:

| Semantic content | Type | Required | Constraints |
|---|---|---:|---|
| GitHub token | string | conditional | Used to initialize `GitHubTool` |
| API keys | string or structured set | conditional | Used to initialize `ConsensusEngine` |

#### Constraints
- Backend waits for credentials via XPC.
- Timeout is exactly `30s`.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.
- Never hardcode credentials, API keys, tokens, or secrets as string literals.

---

### 9. Document Chunk

Required by: **Security**

#### Type
Loaded document chunk.

#### Constraints
- All loaded document chunks MUST pass injection scanning before being included in any LLM prompt.
- Context from external documents MUST go in the `USER` prompt.
- Context from external documents MUST NEVER go in the `SYSTEM` prompt.

#### Notes
No field schema is defined in the provided TRD excerpt.

---

### 10. File Write Path

Required by: **Security**

#### Type
Filesystem path string.

#### Constraints
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

---

## Enums and Constants

### Literal status / verdict values

| Name | Type | Exact value | Notes |
|---|---|---|---|
| VTZ denial verdict | string | `block` | Required in `VTZEnforcementDecision` on policy denial |
| Missing CTX-ID trust state | string | `UNTRUSTED` | Missing CTX-ID MUST be treated as this |
| Auth error card type | string | `auth_error` | Emitted on credential errors in startup steps 5-6 |

### Action outcome values

| Name | Type | Allowed values |
|---|---|---|
| TrustFlow action outcome | string | `allow`, `restrict`, `block` |

### Prompt role constants

| Name | Type | Exact value |
|---|---|---|
| User prompt role | string | `USER` |
| System prompt role | string | `SYSTEM` |

### Algorithm constants

| Name | Type | Exact value |
|---|---|---|
| Payload hash algorithm | string | `SHA-256` |

### Time / timeout constants

| Name | Type | Exact value |
|---|---|---|
| Credential wait timeout | duration/string | `30s` |

### Startup stdout constant

| Name | Type | Exact value |
|---|---|---|
| Listening prefix | string | `FORGE_AGENT_LISTENING:` |

### Runtime / language constants

| Name | Type | Exact value |
|---|---|---|
| Python version | string | `3.12` |

### Required classes / components referenced by contract

| Name | Type | Exact value |
|---|---|---|
| GitHub integration component | identifier | `GitHubTool` |
| consensus component | identifier | `ConsensusEngine` |
| document loading component | identifier | `DocumentStore` |
| path validator | identifier | `path_security.validate_write_path()` |

---

## Validation Rules

### CAL Enforcement
1. Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is allowed after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

### TrustFlow Event Validation
1. Every TrustFlow event MUST include:
   - `event_id`
   - `session_id`
   - `ctx_id`
   - `ts`
   - `event_type`
   - `payload_hash`
2. `event_id` MUST be globally unique.
3. `event_id` MUST use CSPRNG.
4. `event_id` MUST NOT be sequential.
5. `ts` MUST be a UTC Unix timestamp with millisecond precision.
6. `payload_hash` MUST be SHA-256 of the serialized action payload.
7. Emission MUST be synchronous in the enforcement path.
8. Async buffering is not permitted.
9. Failed emission is a WARN-level audit event.

### CTX-ID Validation
1. CTX-ID tokens are immutable after issuance.
2. CTX-ID rotation MUST create a new token.
3. Old token MUST be invalidated immediately after rotation.
4. Expired CTX-ID MUST be rejected.
5. Missing CTX-ID MUST be treated as `UNTRUSTED`.
6. Identity MUST NEVER be inferred from context when CTX-ID is missing.
7. CTX-ID MUST be validated against TrustLock public key.
8. Software-only validation is rejected.

### VTZ Enforcement
1. Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit cross-VTZ authorization is denied.
4. VTZ boundaries are structural, not advisory.
5. Enforcement cannot be bypassed by application code.
6. VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

### Backend Startup Sequence Validation
Mandatory order:

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (async)
8. Send ready message via XPC (includes `agent_version`, `capabilities`)
9. Enter CommandRouter event loop

Additional startup rules:
- Order is mandatory. Do not change it.
- Steps 5-6 are non-fatal on credential errors.
- On credential errors in steps 5-6, emit `auth_error` XPC card and continue in degraded state.
- Step 7 is always async.
- App remains responsive while embeddings load.

### Security Validation
1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Log status codes and error types only.
6. All file write paths MUST pass `path_security.validate_write_path()` before write.
7. All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
8. External document context MUST go in the `USER` prompt.
9. External document context MUST NEVER go in the `SYSTEM` prompt.
10. When `SECURITY_REFUSAL` appears in LLM output:
    - stop
    - gate
    - log
    - never retry to bypass

### GitHub Integration Validation
1. All GitHub operations go through `GitHubTool`.
2. Never call the GitHub API directly from pipeline code.

### Python Implementation Validation
1. Python version MUST be `3.12`.
2. Type annotations are required on every function.
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

Only examples directly supported by the provided contract are included.

### Valid TrustFlow event
```json
{
  "event_id": "3f5f5e6a-8f88-4c73-8d7e-4d3d2b7f9b21",
  "session_id": "sess_01HXYZ",
  "ctx_id": "ctx_01HXYZ",
  "ts": 1710000000123,
  "event_type": "action_executed",
  "payload_hash": "2d711642b726b04401627ca9fbac32f5da7e5f7a6df5f3d5f6f8d7b3f1c2a9ab"
}
```

Why valid:
- includes all required fields
- `ts` is a Unix timestamp in milliseconds
- `payload_hash` is represented as a SHA-256 hex digest string
- no prohibited omission

---

### Invalid TrustFlow event: missing required field
```json
{
  "event_id": "3f5f5e6a-8f88-4c73-8d7e-4d3d2b7f9b21",
  "session_id": "sess_01HXYZ",
  "ctx_id": "ctx_01HXYZ",
  "ts": 1710000000123,
  "event_type": "action_executed"
}
```

Why invalid:
- missing `payload_hash`

---

### Invalid TrustFlow event: likely non-compliant timestamp precision
```json
{
  "event_id": "3f5f5e6a-8f88-4c73-8d7e-4d3d2b7f9b21",
  "session_id": "sess_01HXYZ",
  "ctx_id": "ctx_01HXYZ",
  "ts": 1710000000,
  "event_type": "action_executed",
  "payload_hash": "2d711642b726b04401627ca9fbac32f5da7e5f7a6df5f3d5f6f8d7b3f1c2a9ab"
}
```

Why invalid:
- `ts` must have millisecond precision

---

### Valid VTZEnforcementDecision on denial
```json
{
  "verdict": "block"
}
```

Why valid:
- denial requires `verdict=block`

---

### Invalid VTZEnforcementDecision on denial
```json
{
  "verdict": "deny"
}
```

Why invalid:
- contract requires exact value `block`

---

### Valid backend listening announcement
```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

Why valid:
- exact required prefix
- includes socket path

---

### Invalid backend listening announcement
```text
LISTENING:/tmp/forge-agent.sock
```

Why invalid:
- required literal prefix must be exactly `FORGE_AGENT_LISTENING:`

---

### Valid ready message
```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

Why valid:
- includes required fields `agent_version` and `capabilities`

Note:
- element values for `capabilities` are illustrative only; the TRD does not define allowed capability strings.

---

### Invalid ready message
```json
{
  "agent_version": "1.0.0"
}
```

Why invalid:
- missing required field `capabilities`

---

### Invalid security handling example
```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Why invalid:
- contract explicitly forbids retrying to bypass `SECURITY_REFUSAL`

---

### Invalid backend credential access example
```python
token = KeychainKit.read("github_token")
```

Why invalid:
- Python reads nothing from Keychain
- only Swift reads Keychain, only to deliver via XPC

---

### Invalid GitHub integration example
```python
await http_client.get("https://api.github.com/repos/...")
```

Why invalid:
- all GitHub operations must go through `GitHubTool`

---

## Integration Points

### 1. Swift ↔ Backend XPC
- Swift reads backend socket path from stdout line:
  - `FORGE_AGENT_LISTENING:{socket_path}`
- Swift delivers credentials via XPC.
- Only Swift reads Keychain.
- Python backend reads nothing from Keychain.
- Backend sends:
  - ready message including `agent_version`, `capabilities`
  - `auth_error` XPC card on credential errors

### 2. Backend Startup Dependencies
- `GitHubTool` initialized with token
- `ConsensusEngine` initialized with API keys
- `DocumentStore` starts loading in background asynchronously
- Command router begins only after required startup sequence

### 3. GitHub Operations
- All GitHub operations must route through `GitHubTool`
- Pipeline code must not directly call GitHub API

### 4. Trust / Enforcement Pipeline
For every agent action:
1. validate `ctx_id` first
2. reject immediately on CTX-ID validation failure
3. apply VTZ policy before execution
4. produce `VTZEnforcementDecision` with `verdict=block` on denial
5. emit synchronous TrustFlow event for outcome
6. log and surface TrustFlow emission failures

### 5. LLM Prompt Construction
- Loaded document chunks must be injection-scanned before inclusion
- External document context goes into `USER` prompt only
- External document context must not be placed in `SYSTEM` prompt
- On `SECURITY_REFUSAL`: stop, gate, log, never retry

### 6. File System Writes
- Any file path to be written must pass `path_security.validate_write_path()` before write

### 7. Test and Tooling Interfaces
- Tests executed with:
  ```bash
  cd src && pytest ../tests/ -v --tb=short
  ```
- Linting via `ruff`
- Type checking via `mypy`

--- 

## Notes on Undefined Structures

The provided TRD excerpt does **not** define field-level schemas for the following, so they remain unspecified in this contract:
- action payload internal fields
- credentials XPC payload field names
- `auth_error` card payload fields beyond its named type
- document chunk field names
- `capabilities` element schema
- `ConsensusEngine` request/response payloads
- `GitHubTool` request/response payloads

Implementations MUST NOT invent incompatible public wire formats for these without the owning TRD.