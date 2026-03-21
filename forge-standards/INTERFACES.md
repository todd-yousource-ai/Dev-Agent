# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API-contract requirements explicitly stated in the provided TRD content for the `ConsensusDevAgent` subsystem and the Forge-wide contracts it must satisfy.

Where the source material does not define a full object schema, only the exact required fields and constraints are specified here.

### 1. TrustFlowEvent

Required for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique; MUST use CSPRNG; MUST NOT be sequential |
| `session_id` | `string` | Yes | Required on every TrustFlow event |
| `ctx_id` | `string` | Yes | Required on every TrustFlow event |
| `ts` | `number` | Yes | MUST be UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | Yes | Required on every TrustFlow event |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload |

#### Semantics
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- TrustFlow emission failure MUST NOT silently continue; it must be logged and surfaced.

---

### 2. VTZEnforcementDecision

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | MUST equal `block` for VTZ policy denial |

#### Semantics
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 3. CTX-ID Token

The exact serialized fields are not defined in the supplied source, but the following contract is mandatory for any CTX-ID representation.

| Property | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Missing `ctx_id` MUST be treated as `UNTRUSTED` |
| `vtz_binding` | `string` | Yes | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance |
| `issued_at` | `number` or `string` | Deployment-defined | Used for expiry evaluation if present |
| `expires_at` | `number` or `string` | Deployment-defined | Expired CTX-ID MUST be rejected |
| `signature` / validation material | implementation-defined | Yes | MUST be validated against TrustLock public key; software-only validation is rejected |

#### Semantics
- CTX-ID validation MUST happen FIRST at every entry point that processes an agent action.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted after CTX-ID validation failure.
- CTX-ID tokens are IMMUTABLE once issued.
- CTX-ID rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from surrounding context.

---

### 4. ReadyMessage (XPC)

Sent after startup initialization completes to the ready state.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | `string` | Yes | Included in ready message via XPC |
| `capabilities` | `array` | Yes | Included in ready message via XPC |

#### Semantics
- Sent at backend startup step 8.
- Must be sent after:
  1. logger initialization
  2. XPC server start
  3. `FORGE_AGENT_LISTENING:{socket_path}` stdout emission
  4. credential wait
  5. `GitHubTool` initialization
  6. `ConsensusEngine` initialization
  7. async `DocumentStore` loading start
- `DocumentStore` loading is background async work; the agent becomes responsive before embeddings finish loading.

---

### 5. AuthErrorCard (XPC)

Emitted when startup credential initialization fails.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | `string` | Yes | SHOULD identify auth failure card type; exact value not specified in source |
| `error` | `string` | Yes | Authentication/credential error summary |
| `component` | `string` | Yes | Failing component, e.g. GitHub or Consensus engine initialization |

#### Semantics
- Steps 5 and 6 are non-fatal on credential errors.
- On credential error, emit `auth_error` XPC card.
- Continue in degraded state.

> Note: only the existence of an `auth_error` XPC card is explicitly defined in the supplied source. Additional fields above are the minimum interoperable shape recommended for implementers; if the codebase defines a stricter schema, that stricter schema governs.

---

### 6. StartupStdoutSignal

Printed to stdout for Swift discovery.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `line` | `string` | Yes | MUST match `FORGE_AGENT_LISTENING:{socket_path}` exactly |
| `socket_path` | `string` | Yes | Interpolated into the stdout line |

#### Wire Format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Semantics
- Emitted at backend startup step 3.
- Swift reads this line to discover the socket path.

---

### 7. SerializedActionPayload

Logical payload used for TrustFlow hashing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| action payload | serialized object/bytes | Yes | `payload_hash` MUST be SHA-256 of the serialized action payload |

#### Semantics
- The canonical serialization format is not specified in the source.
- Whatever serialization is used for `payload_hash` computation MUST be stable and deterministic within the deployment.

---

### 8. DocumentChunk

Exact fields not defined in the supplied source.

#### Contractual requirements
- All loaded document chunks MUST pass injection scanning before being included in any LLM prompt.
- Context from external documents MUST be placed in the `USER` prompt, never the `SYSTEM` prompt.

---

### 9. WritePathRequest

Exact fields not defined in the supplied source.

#### Contractual requirements
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

At minimum, any write-capable request structure MUST contain a path field validated before write.

---

### 10. LLMOutput

Exact schema not defined in the supplied source.

#### Contractual requirements
- If output contains `SECURITY_REFUSAL`, processing MUST stop, gate, and log.
- The system MUST NOT retry generation to bypass `SECURITY_REFUSAL`.

---

## Enums and Constants

### Required Literal Values

| Name | Type | Exact Value |
|---|---|---|
| Security refusal sentinel | `string` | `SECURITY_REFUSAL` |
| Startup stdout prefix | `string` | `FORGE_AGENT_LISTENING:` |
| XPC auth error card type | `string` | `auth_error` |
| VTZ denial verdict | `string` | `block` |
| Missing CTX-ID trust classification | `string` | `UNTRUSTED` |

---

### Action Outcome Values

These outcome values are explicitly named in the contract for TrustFlow emission.

| Value | Meaning |
|---|---|
| `allow` | Action permitted |
| `restrict` | Action restricted |
| `block` | Action blocked |

---

### Event Severity Requirement

| Condition | Required Severity |
|---|---|
| Failed TrustFlow emission | `WARN`-level audit event |

---

### Time Format Constant

| Field | Constraint |
|---|---|
| `ts` | UTC Unix timestamp with millisecond precision |

---

### Hash Algorithm Constant

| Field | Constraint |
|---|---|
| `payload_hash` | SHA-256 |

---

## Validation Rules

## 1. Entry Point Enforcement

Every entry point that processes an agent action MUST enforce the following order:

1. CTX-ID validation FIRST
2. Immediate rejection on CTX-ID validation failure
3. VTZ policy check BEFORE execution
4. On VTZ denial, produce `VTZEnforcementDecision` with `verdict=block`
5. Emit TrustFlow event for the action outcome
6. If TrustFlow emission fails, log and surface the failure; do not silently continue

---

## 2. CTX-ID Validation

A CTX-ID is valid only if all of the following hold:

- present, or else the request is treated as `UNTRUSTED`
- not expired
- validated against TrustLock public key
- bound to exactly one VTZ established at issuance

Additional rules:

- software-only validation is rejected
- token fields are immutable once issued
- rotation issues a new token and invalidates the old token immediately
- policy changes apply at NEXT CTX-ID issuance, not mid-session

---

## 3. VTZ Enforcement

- Every session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.

---

## 4. TrustFlow Event Validation

A TrustFlow event is conformant only if:

- `event_id` is present and globally unique
- `event_id` is CSPRNG-generated
- `event_id` is not sequential
- `session_id` is present
- `ctx_id` is present
- `ts` is present and uses UTC Unix milliseconds
- `event_type` is present
- `payload_hash` is present
- `payload_hash` equals SHA-256 of the serialized action payload

Operational rules:

- emission is synchronous in the enforcement path
- async buffering is forbidden
- failed emission must be WARN-level and surfaced

---

## 5. Backend Startup Sequence Validation

Startup order is mandatory and MUST NOT be changed:

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC (timeout: `30s`)
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (async)
8. Send ready message via XPC (includes `agent_version`, `capabilities`)
9. Enter `CommandRouter` event loop

Additional rules:

- steps 5 and 6 are non-fatal on credential errors
- on such errors, emit `auth_error` XPC card
- continue in degraded state
- step 7 is always async
- the app must remain responsive while embeddings load

---

## 6. GitHub Integration Validation

- All GitHub operations MUST go through `GitHubTool`.
- Pipeline code MUST NEVER call the GitHub API directly.

---

## 7. Security Validation

The following are hard prohibitions:

- never hardcode credentials, API keys, tokens, or secrets as string literals
- never use `shell=True` in subprocess calls
- never call `eval()` or `exec()` on generated or external content
- never log HTTP response bodies
- only log status codes and error types for HTTP failures
- all write paths must be validated via `path_security.validate_write_path()` before write
- all loaded document chunks must pass injection scanning before LLM prompt inclusion
- external document context must go in the `USER` prompt, never the `SYSTEM` prompt
- when `SECURITY_REFUSAL` appears, stop, gate, and log
- never retry to bypass `SECURITY_REFUSAL`

Platform boundary rules:

- only Swift reads Keychain
- Swift may deliver credentials via XPC
- Python backend reads nothing from Keychain
- LLM API calls from Swift are forbidden

---

## 8. Python Implementation Constraints

These are implementation-level interface requirements that affect compatibility:

- Python version: `3.12`
- type annotations on every function
- backend uses `async/await` throughout
- no blocking calls on the event loop
- dataclasses for all structured data
- tests use `pytest`
- linting with `ruff`
- type checking with `mypy`
- both must pass clean
- test coverage must be `≥ 85%` on all new modules

---

## Wire Format Examples

## 1. Valid TrustFlow Event

```json
{
  "event_id": "9f4f7f5d-2e1f-4d1c-bb25-7b4d4b41dbe8",
  "session_id": "sess_01JABCXYZ",
  "ctx_id": "ctx_01JABCXYZ",
  "ts": 1735689600123,
  "event_type": "action.block",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961ff6678c61a9b1361b54a7c"
}
```

Why valid:
- contains all required fields
- `ts` is UTC Unix milliseconds
- `payload_hash` is SHA-256-shaped
- `event_id` is non-sequential in form

---

## 2. Invalid TrustFlow Event: missing required field

```json
{
  "event_id": "9f4f7f5d-2e1f-4d1c-bb25-7b4d4b41dbe8",
  "session_id": "sess_01JABCXYZ",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961ff6678c61a9b1361b54a7c"
}
```

Why invalid:
- missing `ctx_id`

---

## 3. Invalid TrustFlow Event: bad timestamp precision

```json
{
  "event_id": "9f4f7f5d-2e1f-4d1c-bb25-7b4d4b41dbe8",
  "session_id": "sess_01JABCXYZ",
  "ctx_id": "ctx_01JABCXYZ",
  "ts": 1735689600,
  "event_type": "action.allow",
  "payload_hash": "8f434346648f6b96df89dda901c5176b10a6d83961ff6678c61a9b1361b54a7c"
}
```

Why invalid:
- `ts` is not expressed with millisecond precision

---

## 4. Valid VTZ Enforcement Decision

```json
{
  "verdict": "block"
}
```

---

## 5. Invalid VTZ Enforcement Decision

```json
{
  "verdict": "allow"
}
```

Why invalid:
- for VTZ policy denial, `verdict` MUST equal `block`

---

## 6. Valid Ready Message

```json
{
  "agent_version": "1.0.0",
  "capabilities": [
    "github",
    "consensus",
    "document_store"
  ]
}
```

Why valid:
- contains required `agent_version`
- contains required `capabilities`

---

## 7. Startup stdout signal

```text
FORGE_AGENT_LISTENING:/tmp/consensusdevagent.sock
```

Why valid:
- exact required prefix
- includes socket path after colon

---

## 8. Invalid startup stdout signal

```text
LISTENING:/tmp/consensusdevagent.sock
```

Why invalid:
- does not match `FORGE_AGENT_LISTENING:{socket_path}`

---

## 9. SECURITY_REFUSAL handling example

### Valid behavior
```json
{
  "llm_output": "SECURITY_REFUSAL",
  "action": "stop_gate_log"
}
```

### Invalid behavior
```json
{
  "llm_output": "SECURITY_REFUSAL",
  "action": "retry_generation"
}
```

Why invalid:
- retrying to bypass `SECURITY_REFUSAL` is forbidden

---

## Integration Points

## 1. Swift ↔ Backend XPC

### Inputs to backend
- credentials via XPC
- delivered after backend starts listening
- credential wait timeout: `30s`

### Outputs from backend
- ready message via XPC including:
  - `agent_version`
  - `capabilities`
- `auth_error` XPC card on credential initialization failure
- stdout discovery line:
  - `FORGE_AGENT_LISTENING:{socket_path}`

### Boundary constraints
- Swift reads Keychain
- Swift may deliver secrets via XPC
- Python backend reads nothing from Keychain
- Swift must not make LLM API calls

---

## 2. Backend ↔ GitHub

- All GitHub operations route through `GitHubTool`
- No direct GitHub API calls from pipeline code
- `GitHubTool` is initialized at startup step 5 with token

---

## 3. Backend ↔ Consensus Engine

- `ConsensusEngine` is initialized at startup step 6 with API keys
- Credential errors are non-fatal at initialization
- On failure, emit `auth_error` XPC card and continue in degraded state

---

## 4. Backend ↔ DocumentStore

- `DocumentStore` loading starts at startup step 7
- loading is background async work
- app remains responsive while embeddings load
- all document chunks must pass injection scanning before inclusion in prompts

---

## 5. Backend ↔ CommandRouter

- `CommandRouter` event loop is entered at startup step 9
- only after ready-message emission

---

## 6. Enforcement Path Dependencies

Every action-processing integration path must include:

1. CTX-ID validation
2. VTZ policy enforcement
3. `VTZEnforcementDecision` on denial
4. synchronous TrustFlow emission
5. surfaced WARN audit on emission failure

---

## 7. Filesystem Writes

Any integration point that writes to disk must validate all target paths through:

```python
path_security.validate_write_path()
```

before any write occurs.

---

## 8. Prompt Construction

Any integration point that includes external document content in prompts must enforce:

- document chunks are injection-scanned first
- external document context is placed only in the `USER` prompt
- external document context is never placed in the `SYSTEM` prompt

---

## Non-Conformance Conditions

A `ConsensusDevAgent` implementation is non-conformant if any of the following occur:

- agent action entry point does not validate CTX-ID first
- CTX-ID validation failure does not immediately reject
- VTZ check occurs after execution begins
- VTZ denial does not emit `VTZEnforcementDecision` with `verdict=block`
- action outcome does not emit a TrustFlow event
- TrustFlow event omits any of:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- TrustFlow emission is buffered asynchronously
- TrustFlow emission failure is silently ignored
- startup order differs from the mandatory sequence
- stdout signal is not exactly `FORGE_AGENT_LISTENING:{socket_path}`
- GitHub API is called directly outside `GitHubTool`
- Python backend reads Keychain
- external document context is placed in the `SYSTEM` prompt
- a document chunk bypasses injection scanning
- a file write occurs before `path_security.validate_write_path()`
- `SECURITY_REFUSAL` causes retry instead of stop/gate/log