# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the required interface and wire-level contracts for the **ConsensusDevAgent** subsystem based on the provided TRD excerpts and Forge component standards.

Where the source defines exact field names, values, ordering, or constraints, they are reproduced exactly.

### 1. Backend Startup Sequence Contract

The backend startup flow is an ordered protocol. The order is mandatory and must not be changed.

#### Startup Steps

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC (timeout: 30s)`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background (async)`
8. `Send ready message via XPC (includes agent_version, capabilities)`
9. `Enter CommandRouter event loop`

#### Startup Event: Listening Announcement

Printed to stdout exactly as:

```text
FORGE_AGENT_LISTENING:{socket_path}
```

##### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | yes | Concrete filesystem/socket path substituted into the literal prefix `FORGE_AGENT_LISTENING:` |

##### Notes

- The literal prefix must be exactly `FORGE_AGENT_LISTENING:`.
- Swift reads this value from stdout.
- This is a wire-visible startup signal.

---

### 2. Ready Message via XPC

At startup step 8, a ready message is sent via XPC.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Must be included in ready message |
| `capabilities` | array | yes | Must be included in ready message |

#### Notes

- Additional fields are not defined in the provided source and therefore are unspecified here.
- The ready message must only be sent after step 7 begins.

---

### 3. Auth Error XPC Card

Credential initialization failures for steps 5 and 6 are non-fatal.

#### Fields

The source defines the message/card name only:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `auth_error` | object/message | yes | Must be emitted via XPC on credential error |

#### Notes

- Steps 5 and 6 continue in degraded state after emitting `auth_error`.
- Exact payload shape beyond the `auth_error` message/card identity is not defined in the provided source.

---

### 4. TrustFlow Event

Every action outcome must emit a TrustFlow event.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | Must be globally unique; generated via CSPRNG, not sequential |
| `session_id` | string | yes | Required on every TrustFlow event |
| `ctx_id` | string | yes | Required on every TrustFlow event |
| `ts` | number | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Required on every TrustFlow event |
| `payload_hash` | string | yes | Must be SHA-256 of the serialized action payload |

#### Notes

- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and must not be silently skipped.

---

### 5. VTZEnforcementDecision Record

VTZ policy denial must produce a `VTZEnforcementDecision` record.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | Must equal `block` for VTZ policy denial |

#### Notes

- The source only defines `verdict=block` explicitly.
- Other fields for `VTZEnforcementDecision` are not defined in the provided material.

---

### 6. CTX-ID Token

The CTX-ID token is an identity/security token used in every action processing entry point.

#### Represented Data

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | Required for validation and TrustFlow events |

#### Lifecycle Constraints

- CTX-ID tokens are **IMMUTABLE** once issued.
- CTX-ID rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID must be rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from context when CTX-ID is missing.
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.

#### Session Binding Constraints

- Every agent session is bound to **EXACTLY ONE VTZ** at CTX-ID issuance.
- VTZ policy changes take effect at **NEXT CTX-ID issuance**, not mid-session.

---

### 7. Action Payload

The source defines a serialized action payload indirectly through hashing requirements.

#### Fields

The explicit field set for the action payload is not provided. However, the following constraint is mandatory:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| serialized action payload | bytes/string serialization | yes | `payload_hash` must be SHA-256 of this serialized form |

#### Notes

- Any implementation must produce a deterministic serialized payload for hashing consistency.
- Exact serialization format is not defined in the provided source.

---

### 8. Credentials via XPC

Backend startup waits for credentials via XPC.

#### Fields

The source defines only the credential categories consumed later:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `token` | string | conditionally | Used to initialize `GitHubTool` |
| `api keys` | collection of strings or key-value mapping | conditionally | Used to initialize `ConsensusEngine` |

#### Notes

- Wait timeout is exactly `30s`.
- Python reads nothing from Keychain directly.
- Only Swift reads Keychain, only to deliver via XPC.

---

### 9. GitHubTool Initialization Input

All GitHub operations go through `GitHubTool`.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `token` | string | yes | Passed to `GitHubTool` during startup step 5 |

#### Notes

- Pipeline code must never call the GitHub API directly.
- `GitHubTool` is the sole integration path for GitHub operations.

---

### 10. ConsensusEngine Initialization Input

`ConsensusEngine` is initialized with API keys.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `api keys` | collection of strings or key-value mapping | yes | Passed to `ConsensusEngine` during startup step 6 |

#### Notes

- Initialization errors are non-fatal and must produce `auth_error`.

---

### 11. DocumentStore Loading Trigger

DocumentStore loading starts asynchronously in the background.

#### Fields

No payload fields are explicitly defined.

#### Constraints

- Loading must begin at startup step 7.
- It must be async.
- The app must remain responsive while embeddings load.

---

## Enums and Constants

### Literal Strings

| Name | Value |
|---|---|
| Listening stdout prefix | `FORGE_AGENT_LISTENING:` |
| Security refusal marker | `SECURITY_REFUSAL` |
| Missing CTX-ID trust state | `UNTRUSTED` |
| VTZ denial verdict | `block` |
| Audit log level for TrustFlow emission failure | `WARN` |

### Timing Constants

| Name | Value |
|---|---|
| Credential wait timeout | `30s` |

### Structural Constants

| Name | Value |
|---|---|
| Python version | `Python 3.12` |
| New module coverage minimum | `85%` |

### Required TrustFlow Fields

Exactly these field names are required on every TrustFlow event:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

### Startup Ordering Constant

The startup order is mandatory and must not be changed.

---

## Validation Rules

## 1. Entry Point Enforcement

Every entry point that processes an agent action MUST:

1. call CTX-ID validation first
2. reject immediately on CTX-ID validation failure
3. check the action against VTZ policy before execution
4. emit a TrustFlow event for every outcome: allow, restrict, block

### Rejection Rules

| Condition | Required Behavior |
|---|---|
| CTX-ID validation failure | immediate rejection; no partial processing |
| Missing CTX-ID | treat as `UNTRUSTED`; never infer identity from context |
| Expired CTX-ID | reject |
| VTZ policy denial | produce `VTZEnforcementDecision` with `verdict=block` |
| TrustFlow emission failure | do not silently continue; log and surface the failure |

---

## 2. TrustFlow Validation

A TrustFlow event is valid only if all required fields are present and constraints are met.

### Field-Level Rules

| Field | Validation |
|---|---|
| `event_id` | must be globally unique; must not be sequential; must be generated using CSPRNG |
| `session_id` | required |
| `ctx_id` | required |
| `ts` | must be UTC Unix timestamp with millisecond precision |
| `event_type` | required |
| `payload_hash` | must equal SHA-256 of serialized action payload |

### Emission Rules

- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failure is a WARN-level audit event.

---

## 3. CTX-ID Validation

A CTX-ID is valid only if all of the following hold:

- present
- not expired
- not invalidated by rotation
- validated against TrustLock public key
- not modified after issuance

### Invalid Cases

| Condition | Valid? | Required Behavior |
|---|---:|---|
| Missing `ctx_id` | no | treat as `UNTRUSTED` |
| Expired CTX-ID | no | reject |
| Modified token after issuance | no | reject |
| Software-only validation | no | reject |
| Old token after rotation | no | reject immediately |

---

## 4. VTZ Validation

### Rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes apply only at next CTX-ID issuance.

### Denial Output

On VTZ denial, a valid implementation must produce:

```text
VTZEnforcementDecision(verdict=block)
```

At minimum, the `verdict` field must equal `block`.

---

## 5. Security Validation Rules

### Forbidden Behaviors

The following are explicitly forbidden:

- ignoring `SECURITY_REFUSAL`
- retrying an LLM call to bypass `SECURITY_REFUSAL`
- force unwrap in Swift: `optional!`
- LLM API call from Swift
- Keychain read for backend in Python
- hardcoded credentials, API keys, tokens, or secrets as string literals
- `shell=True` in subprocess calls
- `eval()` on generated or external content
- `exec()` on generated or external content
- logging HTTP response bodies

### Required Security Behaviors

| Requirement | Constraint |
|---|---|
| File path validation | All file paths written to disk must pass `path_security.validate_write_path()` before any write |
| Injection scanning | All loaded document chunks must pass injection scanning before inclusion in any LLM prompt |
| Prompt placement | Context from external documents goes in the USER prompt, never the SYSTEM prompt |
| SECURITY_REFUSAL handling | stop, gate, log; never retry to bypass |

---

## 6. Language and Testing Conformance

### Python Backend Rules

- `Python 3.12`
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data

### Test and Static Analysis Rules

- `pytest` for all tests
- Tests live in `tests/`
- Tests mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage must be `≥ 85%` on all new modules

### Pre-change Test Command

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## Wire Format Examples

## 1. Valid Listening Announcement

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### Why valid

- Uses exact prefix `FORGE_AGENT_LISTENING:`
- Includes a socket path value

---

## 2. Invalid Listening Announcement

```text
FORGE_AGENT_READY:/tmp/forge-agent.sock
```

### Why invalid

- Prefix must be exactly `FORGE_AGENT_LISTENING:`

---

## 3. Valid TrustFlow Event

```json
{
  "event_id": "c2b9b6e6-5f13-4a7f-a9d2-9f4bb8ed0b5e",
  "session_id": "sess_01HZX8K4R3K2A9",
  "ctx_id": "ctx_01HZX8K4R3K2A9",
  "ts": 1712345678123,
  "event_type": "allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3a00f2f1cf5a2461f2a10f6b3c0d4"
}
```

### Why valid

- Contains all required fields
- `ts` is a Unix timestamp in milliseconds
- `payload_hash` is shaped as a SHA-256 hex digest
- `event_id` is non-sequential in form

---

## 4. Invalid TrustFlow Event: Missing Field

```json
{
  "event_id": "123",
  "session_id": "sess_01HZX8K4R3K2A9",
  "ts": 1712345678123,
  "event_type": "allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3a00f2f1cf5a2461f2a10f6b3c0d4"
}
```

### Why invalid

- Missing required field `ctx_id`

---

## 5. Invalid TrustFlow Event: Bad Timestamp Precision

```json
{
  "event_id": "c2b9b6e6-5f13-4a7f-a9d2-9f4bb8ed0b5e",
  "session_id": "sess_01HZX8K4R3K2A9",
  "ctx_id": "ctx_01HZX8K4R3K2A9",
  "ts": 1712345678,
  "event_type": "allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3a00f2f1cf5a2461f2a10f6b3c0d4"
}
```

### Why invalid

- `ts` must have millisecond precision

---

## 6. Valid VTZ Denial Record

```json
{
  "verdict": "block"
}
```

### Why valid

- VTZ policy denial requires `verdict=block`

---

## 7. Invalid VTZ Denial Record

```json
{
  "verdict": "deny"
}
```

### Why invalid

- Required value is exactly `block`

---

## 8. Valid Ready Message via XPC

```json
{
  "agent_version": "1.0.0",
  "capabilities": [
    "github",
    "consensus"
  ]
}
```

### Why valid

- Includes required fields `agent_version` and `capabilities`

---

## 9. Invalid Ready Message via XPC

```json
{
  "agent_version": "1.0.0"
}
```

### Why invalid

- Missing required field `capabilities`

---

## 10. Invalid SECURITY_REFUSAL Handling

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

### Why invalid

- Explicitly forbidden: must not retry to bypass `SECURITY_REFUSAL`

---

## 11. Invalid Swift Backend Credential Access

```swift
let token = KeychainKit.read("github_token")
```

### Why invalid

- Python backend reads nothing from Keychain
- Only Swift reads Keychain, only to deliver via XPC

---

## Integration Points

## 1. Swift ↔ Backend

### Mechanisms

- Swift reads stdout for:
  - `FORGE_AGENT_LISTENING:{socket_path}`
- Swift sends credentials via XPC
- Backend sends:
  - ready message via XPC
  - `auth_error` XPC card on credential failures

### Constraints

- Only Swift reads Keychain
- Swift may deliver credentials via XPC
- Backend must not read Keychain directly

---

## 2. Backend ↔ GitHub

### Integration Component

- `GitHubTool`

### Contract

- All GitHub operations go through `GitHubTool`
- Pipeline code must never call the GitHub API directly

### Initialization Input

- `token`

---

## 3. Backend ↔ Consensus Engine

### Integration Component

- `ConsensusEngine`

### Initialization Input

- `API keys`

### Error Contract

- Credential/API key errors are non-fatal
- Must emit `auth_error`
- System continues in degraded state

---

## 4. Backend ↔ DocumentStore

### Integration Component

- `DocumentStore`

### Contract

- Loading starts in background at startup step 7
- Must be async
- App remains responsive while embeddings load
- Loaded document chunks must pass injection scanning before inclusion in any LLM prompt

---

## 5. Enforcement Path ↔ CAL / VTZ / TrustFlow

### Required Execution Order

1. CTX-ID validation
2. immediate reject on validation failure
3. VTZ policy check
4. execution decision
5. synchronous TrustFlow emission

### Output Records

- `VTZEnforcementDecision` with `verdict=block` on VTZ denial
- TrustFlow event on every outcome: allow, restrict, block

---

## 6. File System Writes

### Security Integration

Before any write to disk:

- path must pass `path_security.validate_write_path()`

This validation is mandatory for all file paths written to disk.

---

## 7. LLM Prompt Construction

### Security Integration

- All loaded document chunks must pass injection scanning before inclusion
- External document context must be placed in the `USER` prompt
- External document context must never be placed in the `SYSTEM` prompt
- On `SECURITY_REFUSAL`: stop, gate, log; never retry

---

## 8. Development Workflow Integration

Before code changes:

1. Find the TRD that owns the component in `README.md`
2. Read the relevant TRD sections
3. Check TRD-11 if touching credentials, external content, generated code, or CI
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## Unspecified Fields and Open Areas

The provided source does **not** define the full payload schemas for the following items:

- XPC credential message exact field names beyond `token` / `API keys`
- `auth_error` payload structure
- full `VTZEnforcementDecision` schema beyond `verdict`
- full action payload schema and serialization format
- full ready-message schema beyond `agent_version` and `capabilities`

Implementations must not invent incompatible field names where additional TRD-owned schemas exist elsewhere. Only the fields and constraints explicitly defined above are normative from the provided source.