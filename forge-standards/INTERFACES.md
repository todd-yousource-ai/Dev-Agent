# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the **ConsensusDevAgent** subsystem based on the provided TRD excerpts and Forge component interface contracts.

Where the source material defines exact field names, values, ordering, or behavior, they are reproduced exactly.

---

### 1. Backend Startup Sequence Interface

The backend startup sequence is an externally observable contract.

#### 1.1 Startup Order

Order is mandatory:

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

#### 1.2 Stdout Readiness Line

```text
FORGE_AGENT_LISTENING:{socket_path}
```

##### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | yes | Non-empty filesystem/socket path string |

##### Constraints

- The literal prefix `FORGE_AGENT_LISTENING:` MUST appear exactly as shown.
- The value after `:` is the XPC socket path.
- This line is printed to stdout for Swift to consume.

---

### 2. XPC Ready Message

At startup step 8, the backend sends a ready message via XPC.

#### 2.1 Ready Message Object

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Non-empty |
| `capabilities` | array | yes | Zero or more capability identifiers |

#### 2.2 Capabilities Array Item

| Field | Type | Required | Constraints |
|---|---|---:|---|
| item | string | yes | Capability identifier string |

#### 2.3 Auth Error Card

On credential errors in steps 5 or 6, the backend MUST emit an `auth_error` XPC card and continue in degraded state.

##### Auth Error Card Object

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | string | yes | MUST equal `auth_error` |

No additional fields are defined by the provided source material.

---

### 3. TrustFlow Event

Every action outcome must emit a TrustFlow event.

#### 3.1 TrustFlow Event Object

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | Globally unique; generated using CSPRNG; MUST NOT be sequential |
| `session_id` | string | yes | Non-empty |
| `ctx_id` | string | yes | Non-empty valid CTX-ID token reference |
| `ts` | number | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Non-empty event type identifier |
| `payload_hash` | string | yes | SHA-256 of the serialized action payload |

#### 3.2 Constraints

- Every TrustFlow event MUST include exactly these required fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- `event_id` MUST be globally unique.
- `event_id` MUST use CSPRNG-derived uniqueness; sequential identifiers are forbidden.
- `ts` MUST be a UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be the SHA-256 hash of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and MUST NOT be silently skipped.

---

### 4. VTZ Enforcement Decision

A VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

#### 4.1 VTZEnforcementDecision Object

Only one field/value pair is explicitly defined in the source material.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | MUST equal `block` on VTZ policy denial |

No additional fields are defined by the provided source material.

---

### 5. CTX-ID Token

The CTX-ID token is a validated identity/context token used in enforcement.

#### 5.1 CTX-ID Token Representation

The exact internal field structure is not defined in the provided source material. The subsystem contract treats CTX-ID as a token value.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | Immutable once issued; must validate against TrustLock public key |

#### 5.2 Constraints

- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is allowed after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST NOT be inferred from context when CTX-ID is missing.
- Validation MUST be against TrustLock public key.
- Software-only validation is rejected.

---

### 6. Action Payload

The TrustFlow contract references a serialized action payload.

#### 6.1 Action Payload

The internal structure of the action payload is not defined in the provided source material.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| serialized action payload | bytes or string | yes | Canonical serialized form used as input to SHA-256 for `payload_hash` |

#### 6.2 Constraints

- Every entry point that processes an agent action MUST validate CTX-ID first.
- Every action MUST be checked against VTZ policy before execution.
- Action processing MUST reject immediately on CTX-ID validation failure.
- No partial processing is allowed after CTX-ID validation failure.

---

### 7. Credentials via XPC

The backend waits for credentials via XPC with a timeout.

#### 7.1 Credential Delivery Contract

| Field | Type | Required | Constraints |
|---|---|---:|---|
| GitHub token | string | conditional | Used to initialize `GitHubTool` |
| API keys | string or structured credential set | conditional | Used to initialize `ConsensusEngine` |

#### 7.2 Constraints

- Credentials are delivered via XPC.
- Wait timeout is exactly `30s`.
- Swift may read Keychain and deliver credentials via XPC.
- Python reads nothing from Keychain.
- Backend credential initialization failures at steps 5-6 are non-fatal.
- On such failures, backend MUST emit an `auth_error` XPC card and continue in degraded state.

Because the exact XPC credential message field names are not defined in the provided material, no additional wire fields are specified here.

---

### 8. DocumentStore Loading Contract

#### 8.1 Background Load Operation

| Field | Type | Required | Constraints |
|---|---|---:|---|
| DocumentStore loading state | implementation-defined | no | Loading starts in background asynchronously |

#### 8.2 Constraints

- DocumentStore loading MUST start in background.
- Loading MUST be async.
- The app MUST remain responsive while embeddings load.

---

### 9. GitHubTool Integration Surface

#### 9.1 GitHub Operation Routing

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `GitHubTool` | component reference | yes | All GitHub operations MUST go through this component |

#### 9.2 Constraints

- All GitHub operations go through `GitHubTool`.
- Pipeline code MUST NOT call the GitHub API directly.

---

### 10. Security Refusal Output Contract

#### 10.1 SECURITY_REFUSAL Detection

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `SECURITY_REFUSAL` | string | conditional | If present in LLM output, triggers refusal handling |

#### 10.2 Constraints

- When `SECURITY_REFUSAL` appears in LLM output: stop, gate, log.
- Never retry to bypass.
- Retrying generation after `SECURITY_REFUSAL` is explicitly forbidden.

---

## Enums and Constants

### 1. String Constants

| Name | Type | Value |
|---|---|---|
| Readiness stdout prefix | string | `FORGE_AGENT_LISTENING:` |
| Auth error card type | string | `auth_error` |
| SECURITY_REFUSAL token | string | `SECURITY_REFUSAL` |
| Missing CTX-ID trust state | string | `UNTRUSTED` |
| VTZ denial verdict | string | `block` |

---

### 2. Timing Constants

| Name | Type | Value |
|---|---|---|
| Credential wait timeout | duration/string literal in TRD | `30s` |

---

### 3. Runtime / Language Constants

| Name | Type | Value |
|---|---|---|
| Python version | string | `Python 3.12` |

---

## Validation Rules

### 1. CAL Enforcement Contract

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

### 2. TrustFlow Validation

A TrustFlow event is valid only if:

- `event_id` is present
- `session_id` is present
- `ctx_id` is present
- `ts` is present
- `event_type` is present
- `payload_hash` is present
- `event_id` is globally unique
- `event_id` is not sequential
- `ts` is UTC Unix timestamp with millisecond precision
- `payload_hash` equals SHA-256 of the serialized action payload

### 3. CTX-ID Validation

A CTX-ID is valid only if:

- It is present unless explicitly treated as `UNTRUSTED`
- It is not expired
- It validates against TrustLock public key
- It has not been invalidated by rotation

Additional rules:

- Missing CTX-ID MUST be treated as `UNTRUSTED`
- Identity MUST NOT be inferred from context
- Software-only validation is rejected

### 4. VTZ Validation

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

### 5. Startup Validation

Backend startup is valid only if the exact order is preserved:

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC (timeout: `30s`)
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (async)
8. Send ready message via XPC (includes `agent_version`, `capabilities`)
9. Enter `CommandRouter` event loop

### 6. Security Validation

The subsystem MUST enforce all of the following:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on any generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log. Never retry to bypass.

### 7. Python Implementation Validation

- Python version MUST be `Python 3.12`
- Type annotations are required on every function
- Backend code MUST use `async/await` throughout
- No blocking calls on the event loop
- Dataclasses are required for all structured data
- Tests MUST use `pytest`
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage must be `≥ 85%` on all new modules

---

## Wire Format Examples

Only fields explicitly defined in the provided source material are used below.

### 1. Valid TrustFlow Event

```json
{
  "event_id": "9d72c513-bf65-4dc5-a3eb-9f5f6a3cb6b1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1731975123456,
  "event_type": "action_allow",
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa1350144a978f5f8f5d4f0f7f7a0b65"
}
```

Why valid:
- Contains all required fields
- `ts` is a Unix timestamp in milliseconds
- `payload_hash` is a SHA-256 hex string
- `event_id` is non-sequential in form

---

### 2. Invalid TrustFlow Event: Missing Required Field

```json
{
  "event_id": "9d72c513-bf65-4dc5-a3eb-9f5f6a3cb6b1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1731975123456,
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa1350144a978f5f8f5d4f0f7f7a0b65"
}
```

Why invalid:
- Missing `event_type`

---

### 3. Invalid TrustFlow Event: Bad Timestamp Precision

```json
{
  "event_id": "9d72c513-bf65-4dc5-a3eb-9f5f6a3cb6b1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc123",
  "ts": 1731975123,
  "event_type": "action_block",
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa1350144a978f5f8f5d4f0f7f7a0b65"
}
```

Why invalid:
- `ts` is not millisecond precision

---

### 4. Valid VTZEnforcementDecision for Denial

```json
{
  "verdict": "block"
}
```

Why valid:
- VTZ policy denial requires `verdict=block`

---

### 5. Invalid VTZEnforcementDecision for Denial

```json
{
  "verdict": "allow"
}
```

Why invalid:
- On VTZ policy denial, `verdict` MUST equal `block`

---

### 6. Valid Ready Message

```json
{
  "agent_version": "1.0.0",
  "capabilities": [
    "github",
    "consensus"
  ]
}
```

Why valid:
- Includes required `agent_version`
- Includes required `capabilities`

Note:
- Capability value set is not enumerated by the provided source material; strings shown are illustrative.

---

### 7. Invalid Ready Message

```json
{
  "agent_version": "1.0.0"
}
```

Why invalid:
- Missing `capabilities`

---

### 8. Valid Auth Error Card

```json
{
  "type": "auth_error"
}
```

Why valid:
- Matches defined XPC card type

---

### 9. Stdout Readiness Example

```text
FORGE_AGENT_LISTENING:/tmp/forge-consensus-agent.sock
```

Why valid:
- Exact required prefix
- Includes a socket path

---

### 10. Invalid Stdout Readiness Example

```text
LISTENING:/tmp/forge-consensus-agent.sock
```

Why invalid:
- Prefix is not exactly `FORGE_AGENT_LISTENING:`

---

## Integration Points

### 1. Swift ↔ Backend XPC

#### Required interactions

- Swift reads stdout line:
  - `FORGE_AGENT_LISTENING:{socket_path}`
- Swift provides credentials via XPC
- Backend sends ready message via XPC with:
  - `agent_version`
  - `capabilities`
- Backend may send `auth_error` XPC card on credential initialization failure

#### Constraints

- Only Swift reads Keychain
- Only Swift delivers backend credentials via XPC
- Python reads nothing from Keychain

---

### 2. Backend ↔ GitHubTool

- Backend initializes `GitHubTool` with token
- All GitHub operations MUST go through `GitHubTool`
- Direct GitHub API calls from pipeline code are forbidden

---

### 3. Backend ↔ ConsensusEngine

- Backend initializes `ConsensusEngine` with API keys
- Credential failure is non-fatal
- On failure, emit `auth_error` and continue in degraded state

---

### 4. Backend ↔ DocumentStore

- Backend starts DocumentStore loading in background
- Operation is async
- Application remains responsive while embeddings load

---

### 5. Enforcement Path ↔ TrustFlow

For every action:

1. Validate CTX-ID first
2. Enforce VTZ policy before execution
3. Emit TrustFlow event for outcome
4. If TrustFlow emission fails:
   - do not silently continue
   - log and surface failure
   - failure is a WARN-level audit event

---

### 6. Enforcement Path ↔ TrustLock

- CTX-ID validation MUST be against TrustLock public key
- Software-only validation is rejected

---

### 7. File System Write Path Validation

Before any file write:

- Path MUST pass `path_security.validate_write_path()`

This function name is part of the required contract and must appear exactly as shown.

---

### 8. LLM Prompt Construction

- All loaded document chunks MUST pass injection scanning before inclusion in prompts
- Context from external documents goes in the USER prompt
- Context from external documents MUST NOT go in the SYSTEM prompt
- If output contains `SECURITY_REFUSAL`, processing MUST stop and gate; no retry is permitted

---

### 9. Test and Quality Gate Integration

Before implementation work:

```text
cd src && pytest ../tests/ -v --tb=short
```

Required quality gates:

- `pytest`
- `ruff`
- `mypy`

Coverage requirement:

- `≥ 85%` on all new modules

---

## Non-Conformance Conditions

A ConsensusDevAgent implementation is non-conformant if any of the following occur:

- Does not validate CTX-ID first
- Performs partial processing after CTX-ID validation failure
- Executes an action before VTZ policy check
- Fails to emit TrustFlow for action outcome
- Silently skips TrustFlow emission failure
- Uses non-unique or sequential `event_id`
- Uses non-millisecond `ts`
- Computes `payload_hash` from anything other than serialized action payload
- Treats missing CTX-ID as anything other than `UNTRUSTED`
- Infers identity from context without CTX-ID
- Uses software-only CTX-ID validation
- Bypasses `GitHubTool` for GitHub operations
- Changes startup order
- Omits stdout line `FORGE_AGENT_LISTENING:{socket_path}`
- Blocks startup on step 5 or 6 credential errors instead of degrading with `auth_error`
- Loads DocumentStore synchronously instead of async background load
- Retries after `SECURITY_REFUSAL`
- Writes file paths without `path_security.validate_write_path()`
- Logs HTTP response bodies
- Uses `shell=True`
- Uses `eval()` or `exec()` on generated or external content
- Reads backend credentials from Keychain in Python

--- 

## Undefined / Not Specified by Provided Source

The following interfaces are referenced but not structurally defined in the provided materials, so no additional fields may be assumed from this contract:

- Full XPC credential message schema
- Full `VTZEnforcementDecision` schema beyond `verdict`
- Full CTX-ID token internal field schema
- Full action payload schema
- Full CommandRouter message schema
- Enumerated `capabilities` values
- Detailed `auth_error` payload beyond card type
- Detailed `ConsensusEngine` API key field names