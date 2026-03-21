# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the `ConsensusDevAgent` subsystem using only the interface content provided.

Where source material specifies behavior but not an explicit serialized object shape, this document records the required observable contract and identifies exact required fields where mandated.

### 1. TrustFlow Event

Required by the TrustFlow Emission Contract.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---:|---:|---|
| `event_id` | string | Yes | MUST be globally unique; MUST be generated with CSPRNG; MUST NOT be sequential |
| `session_id` | string | Yes | Required on every TrustFlow event |
| `ctx_id` | string | Yes | Required on every TrustFlow event; MUST represent the CTX-ID associated with the action |
| `ts` | number | Yes | MUST be UTC Unix timestamp with millisecond precision |
| `event_type` | string | Yes | Required on every TrustFlow event |
| `payload_hash` | string | Yes | MUST be SHA-256 of the serialized action payload |

#### Behavioral constraints
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Emission failure MUST NOT silently continue.
- Failed emission is a WARN-level audit event.

---

### 2. VTZEnforcementDecision

Required by the CAL Enforcement Contract.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---:|---:|---|
| `verdict` | string | Yes | For VTZ policy denial, MUST equal `block` |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy before execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

> No additional fields are specified in the provided source.

---

### 3. CTX-ID Token

Defined by the CTX-ID Contract.

#### Type
Opaque token value

#### Wire representation
- Serialized as a token string when transported.
- Internal fields are not specified in the provided source and MUST be treated as immutable and opaque by integrators unless defined elsewhere.

#### Constraints
- CTX-ID tokens are immutable once issued.
- No field modification is permitted after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

---

### 4. Agent Ready Message

Defined by the Backend Startup Sequence.

Sent via XPC at startup step 8.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---:|---:|---|
| `agent_version` | string | Yes | Included in ready message |
| `capabilities` | array | Yes | Included in ready message; element type not specified in provided source |

---

### 5. XPC Auth Error Card

Defined by the Backend Startup Sequence.

Emitted on credential errors during startup steps 5-6.

#### Type
Object or message card

#### Fields
Not fully specified in the provided source.

#### Required behavior
- On credential errors initializing `GitHubTool` with token or `ConsensusEngine` with API keys:
  - emit `auth_error` XPC card
  - continue in degraded state

---

### 6. Listening Announcement

Defined by the Backend Startup Sequence.

Printed to stdout at startup step 3.

#### Type
String

#### Exact format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Constraints
- Must be printed to stdout.
- `{socket_path}` is the listening socket path used by the XPC server.

---

### 7. Credentials via XPC

Defined by the Backend Startup Sequence.

#### Type
XPC-delivered credential payload

#### Fields
Not fully specified in the provided source.

#### Required behavior
- Backend waits for credentials via XPC.
- Timeout is exactly `30s`.
- Swift delivers credentials via XPC.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

---

### 8. Action Payload

Used in CAL enforcement and TrustFlow hashing.

#### Type
Serialized action payload

#### Fields
Not specified in the provided source.

#### Constraints
- Every entry point that processes an agent action MUST call CTX-ID validation first.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is allowed on CTX-ID validation failure.
- Every action MUST be checked against VTZ policy before execution.
- `payload_hash` in TrustFlow MUST be SHA-256 of the serialized action payload.

---

### 9. SECURITY_REFUSAL Output

Defined by security policy.

#### Type
String sentinel

#### Exact value
```text
SECURITY_REFUSAL
```

#### Required behavior
- When output contains `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.
- Retrying generation after `SECURITY_REFUSAL` is explicitly forbidden.

---

### 10. File Write Path Validation Interface

Defined by security policy.

#### Type
Function/interface requirement

#### Required call
```text
path_security.validate_write_path()
```

#### Required behavior
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

---

### 11. GitHubTool Integration

Defined by GitHub Operations and startup sequence.

#### Type
Service dependency

#### Initialization input

| Field | Type | Required | Constraints |
|---|---:|---:|---|
| `token` | string | Yes | Used to initialize `GitHubTool`; on credential error, emit `auth_error` XPC card and continue in degraded state |

#### Required behavior
- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

---

### 12. ConsensusEngine Integration

Defined by startup sequence.

#### Type
Service dependency

#### Initialization input

| Field | Type | Required | Constraints |
|---|---:|---:|---|
| `api_keys` | object or collection | Yes | Used to initialize `ConsensusEngine`; exact structure not specified in provided source |

#### Required behavior
- On credential errors, emit `auth_error` XPC card and continue in degraded state.

---

### 13. DocumentStore Loading Trigger

Defined by startup sequence.

#### Type
Startup action

#### Required behavior
- `DocumentStore` loading starts in background.
- This load is async.
- App remains responsive while embeddings load.

---

## Enums and Constants

### Literal values

| Name | Type | Exact Value |
|---|---:|---|
| Security refusal sentinel | string | `SECURITY_REFUSAL` |
| Listening prefix | string | `FORGE_AGENT_LISTENING:` |
| XPC error card type | string | `auth_error` |
| VTZ denial verdict | string | `block` |
| Missing CTX-ID trust state | string | `UNTRUSTED` |
| TrustFlow action outcome | string | `allow` |
| TrustFlow action outcome | string | `restrict` |
| TrustFlow action outcome | string | `block` |

### Timeouts and precision

| Name | Type | Exact Value |
|---|---:|---|
| Credential wait timeout | duration | `30s` |
| TrustFlow timestamp precision | string | `millisecond precision` |

### Algorithms

| Name | Type | Exact Value |
|---|---:|---|
| Payload hash algorithm | string | `SHA-256` |

### Runtime / language requirements

| Name | Type | Exact Value |
|---|---:|---|
| Python version | string | `Python 3.12` |

### Mandatory startup order constants

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

## Validation Rules

## A. CAL Enforcement

1. Every entry point that processes an agent action MUST call CTX-ID validation first.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy before execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

## B. TrustFlow Event Validation

1. `event_id` MUST be present.
2. `event_id` MUST be globally unique.
3. `event_id` MUST use CSPRNG.
4. `event_id` MUST NOT be sequential.
5. `session_id` MUST be present.
6. `ctx_id` MUST be present.
7. `ts` MUST be present.
8. `ts` MUST be a UTC Unix timestamp.
9. `ts` MUST have millisecond precision.
10. `event_type` MUST be present.
11. `payload_hash` MUST be present.
12. `payload_hash` MUST be SHA-256 of the serialized action payload.
13. Emission MUST be synchronous in the enforcement path.
14. Async buffering is not permitted.

## C. CTX-ID Validation

1. Missing CTX-ID MUST be treated as `UNTRUSTED`.
2. Expired CTX-ID MUST be rejected.
3. CTX-ID MUST be validated against TrustLock public key.
4. Software-only validation is rejected.
5. CTX-ID tokens are immutable once issued.
6. Rotation creates a new token.
7. Old token is invalidated immediately upon rotation.

## D. VTZ Enforcement

1. Every agent session is bound to exactly one VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit authorization is denied.
4. VTZ boundaries are structural, not advisory.
5. Enforcement cannot be bypassed by application code.
6. VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

## E. Security Rules

1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Log status codes and error types only.
6. All file paths written to disk must pass `path_security.validate_write_path()` before any write.
7. All loaded document chunks must pass injection scanning before being included in any LLM prompt.
8. Context from external documents goes in the USER prompt, never the SYSTEM prompt.
9. When `SECURITY_REFUSAL` output is seen: stop, gate, log.
10. Never retry to bypass `SECURITY_REFUSAL`.

## F. Backend / Language Rules

1. Python functions must have type annotations.
2. Backend must use `async/await` throughout.
3. No blocking calls on the event loop.
4. Dataclasses must be used for all structured data.
5. Tests must use `pytest`.
6. Tests live in `tests/` and mirror `src/` structure.
7. `ruff` must pass clean.
8. `mypy` must pass clean.
9. Test coverage must be `≥ 85%` on all new modules.

## G. Keychain / Credential Handling

1. Python reads nothing from Keychain.
2. Only Swift reads Keychain.
3. Swift may read Keychain only to deliver credentials via XPC.
4. Backend waits for credentials via XPC for `30s`.

## H. GitHub Integration

1. All GitHub operations go through `GitHubTool`.
2. Never call the GitHub API directly from pipeline code.

---

## Wire Format Examples

## 1. Valid TrustFlow event

```json
{
  "event_id": "a8b2b87a-3a9f-4d7c-9f5d-7cb2f22c6a21",
  "session_id": "sess_01HZX9K8YQ7V0J2A3B4C",
  "ctx_id": "ctx_01HZX9N3T1V6X8Y0Z2AB",
  "ts": 1731012345123,
  "event_type": "allow",
  "payload_hash": "4d967a4c7e3c5f1d0d2b4b3a7f8c9e6a1b2d3f4c5a6b7c8d9e0f112233445566"
}
```

Why valid:
- Includes all required TrustFlow fields.
- `ts` is numeric Unix time in milliseconds.
- `payload_hash` is SHA-256-shaped hex content.
- `event_type` uses a required action outcome value.

---

## 2. Invalid TrustFlow event: missing required field

```json
{
  "event_id": "evt_123",
  "session_id": "sess_123",
  "ts": 1731012345123,
  "event_type": "block",
  "payload_hash": "4d967a4c7e3c5f1d0d2b4b3a7f8c9e6a1b2d3f4c5a6b7c8d9e0f112233445566"
}
```

Why invalid:
- Missing `ctx_id`.

---

## 3. Invalid TrustFlow event: bad timestamp precision/type

```json
{
  "event_id": "evt_123",
  "session_id": "sess_123",
  "ctx_id": "ctx_123",
  "ts": "2025-01-01T00:00:00Z",
  "event_type": "allow",
  "payload_hash": "4d967a4c7e3c5f1d0d2b4b3a7f8c9e6a1b2d3f4c5a6b7c8d9e0f112233445566"
}
```

Why invalid:
- `ts` must be a UTC Unix timestamp with millisecond precision, not a string datetime.

---

## 4. Valid VTZEnforcementDecision for denial

```json
{
  "verdict": "block"
}
```

Why valid:
- Matches the only explicitly required field/value in the provided source.

---

## 5. Invalid VTZEnforcementDecision for denial

```json
{
  "verdict": "allow"
}
```

Why invalid:
- For VTZ policy denial, `verdict` MUST be `block`.

---

## 6. Valid stdout listening announcement

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

Why valid:
- Matches exact required prefix and format.

---

## 7. Invalid stdout listening announcement

```text
LISTENING:/tmp/forge-agent.sock
```

Why invalid:
- Must begin exactly with `FORGE_AGENT_LISTENING:`.

---

## 8. Valid ready message

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

Why valid:
- Includes required `agent_version` and `capabilities`.

---

## 9. Invalid ready message

```json
{
  "agent_version": "1.0.0"
}
```

Why invalid:
- Missing required `capabilities`.

---

## 10. SECURITY_REFUSAL handling example

Observed output:
```text
SECURITY_REFUSAL
```

Required handling:
- stop
- gate
- log

Forbidden handling:
- retrying generation to bypass refusal

---

## Integration Points

## 1. XPC

Used for:
- credential delivery to backend
- ready message transmission
- `auth_error` card emission

Contract requirements:
- XPC server must start before printing listening message.
- Backend must listen on socket before stdout announcement.
- Credentials are delivered via XPC.
- Ready message is sent via XPC and includes `agent_version`, `capabilities`.
- Credential initialization failures for `GitHubTool` and `ConsensusEngine` emit `auth_error` via XPC and continue in degraded state.

## 2. Stdout

Used for:
- socket discovery by Swift

Contract:
- Must print exactly:
  ```text
  FORGE_AGENT_LISTENING:{socket_path}
  ```

## 3. Swift Client

Contract:
- Swift reads the stdout listening line.
- Swift reads Keychain.
- Swift delivers credentials via XPC.
- Swift must not make LLM API calls for backend credentials flow.
- Swift force unwraps are forbidden in implementation guidance.

## 4. Python Backend

Contract:
- Python 3.12.
- `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- Python reads nothing from Keychain.

## 5. GitHubTool

Contract:
- Initialized with token after XPC credential receipt.
- All GitHub operations must route through `GitHubTool`.
- Direct GitHub API calls from pipeline code are forbidden.

## 6. ConsensusEngine

Contract:
- Initialized with API keys after XPC credential receipt.
- Credential errors are non-fatal and produce `auth_error` XPC card.

## 7. DocumentStore

Contract:
- Loading starts asynchronously in background after `ConsensusEngine` initialization.
- External document chunks must pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

## 8. TrustLock

Contract:
- CTX-ID validation must be against TrustLock public key.
- Software-only validation is rejected.

## 9. Path Security

Contract:
- Every disk write path must be validated through:
  ```text
  path_security.validate_write_path()
  ```

## 10. CommandRouter

Contract:
- Entered only after the mandatory startup sequence reaches step 9.
- No earlier entry is conformant.

## 11. Testing and Quality Gates

Required invocation before changes:
```bash
cd src && pytest ../tests/ -v --tb=short
```

Quality gates:
- `pytest`
- `ruff`
- `mypy`
- coverage `≥ 85%` on all new modules

---

## Conformance Notes

A `ConsensusDevAgent` implementation is non-conformant if any of the following occur:
- missing CTX-ID validation before processing an action
- partial processing after CTX-ID validation failure
- VTZ enforcement skipped before execution
- denial without `VTZEnforcementDecision` with `verdict=block`
- missing TrustFlow emission for any action outcome
- async-buffered TrustFlow emission
- silent TrustFlow emission failure
- direct GitHub API access outside `GitHubTool`
- retry after `SECURITY_REFUSAL`
- Python backend reading Keychain
- disk write without `path_security.validate_write_path()`
- startup order changed from the mandated sequence