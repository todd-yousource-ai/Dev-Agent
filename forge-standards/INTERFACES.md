# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements applicable to the `ConsensusDevAgent` subsystem from the provided TRD excerpts and enforced Forge interface contracts.

Where the source material specifies exact field names, values, ordering, or behavior, they are reproduced exactly.

### 1. TrustFlow Event

Required by the **TrustFlow Emission Contract**.

#### Type
Structured record.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | MUST be globally unique. MUST be generated via CSPRNG. MUST NOT be sequential. |
| `session_id` | string | yes | Required on every TrustFlow event. |
| `ctx_id` | string | yes | Required on every TrustFlow event. |
| `ts` | integer or number | yes | MUST be UTC Unix timestamp with millisecond precision. |
| `event_type` | string | yes | Required on every TrustFlow event. |
| `payload_hash` | string | yes | MUST be SHA-256 of the serialized action payload. |

#### Behavioral constraints
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

---

### 2. VTZEnforcementDecision

Required by the **CAL Enforcement Contract**.

#### Type
Structured record.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | On VTZ policy denial, MUST equal `block`. |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 3. CTX-ID Token

Required by the **CTX-ID Contract**.

#### Type
Opaque token represented on the wire as a string unless a deployment-specific container is defined elsewhere.

#### Fields
No internal field schema is defined in the provided source excerpts.

#### Behavioral constraints
- CTX-ID tokens are IMMUTABLE once issued — no field modification after issuance.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection — no partial processing.

---

### 4. XPC Listening Announcement

Required by the **Backend Startup Sequence**.

#### Type
Single stdout line.

#### Format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | yes | Substituted directly after the literal prefix `FORGE_AGENT_LISTENING:`. |

#### Behavioral constraints
- Must occur after XPC server starts listening on socket.
- Must occur before waiting for credentials via XPC.

---

### 5. Ready Message via XPC

Required by the **Backend Startup Sequence**.

#### Type
Structured XPC message/card.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Must be included in ready message. |
| `capabilities` | array | yes | Must be included in ready message. Element type not further specified in provided excerpts. |

#### Behavioral constraints
- Sent after `DocumentStore` loading begins in background.
- Sent before entering `CommandRouter` event loop.

---

### 6. Auth Error XPC Card

Required by the **Backend Startup Sequence**.

#### Type
Structured XPC message/card.

#### Fields
The provided excerpts define only the card type name and not its full payload schema.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | string | implied | Should identify this as `auth_error` because source states “emit auth_error XPC card”. |

#### Behavioral constraints
- Steps 5–6 are non-fatal on credential errors.
- On credential errors in GitHubTool or ConsensusEngine initialization, emit `auth_error` XPC card and continue in degraded state.

---

### 7. Serialized Action Payload

Required by the **TrustFlow Emission Contract**.

#### Type
Serialized payload blob used as hash input.

#### Fields
Not defined in the provided excerpts.

#### Behavioral constraints
- `payload_hash` MUST be SHA-256 of the serialized action payload.

---

### 8. File Write Path Input

Required by the **Security** section.

#### Type
Filesystem path string.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| path value | string | yes | All file paths written to disk must pass `path_security.validate_write_path()` before any write. |

---

### 9. Loaded Document Chunk

Required by the **Security** section.

#### Type
Structured or unstructured document chunk.

#### Fields
Schema not defined in the provided excerpts.

#### Behavioral constraints
- All loaded document chunks must pass injection scanning before being included in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

---

### 10. SECURITY_REFUSAL Output

Required by the **Security** section and explicit forbidden pattern.

#### Type
String sentinel in model output.

#### Exact value
```text
SECURITY_REFUSAL
```

#### Behavioral constraints
- When output contains `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.
- Retrying another model call after receiving `SECURITY_REFUSAL` is explicitly forbidden.

---

### 11. Credentials via XPC

Required by the **Backend Startup Sequence**.

#### Type
Structured XPC credential delivery message.

#### Fields
Exact field names are not defined in the provided excerpts.

#### Behavioral constraints
- Backend waits for credentials via XPC with timeout: `30s`.
- Only Swift reads Keychain, only to deliver via XPC.
- Python reads nothing from Keychain.

---

### 12. GitHubTool Initialization Input

Required by the **Backend Startup Sequence** and **GitHub Operations**.

#### Type
Structured initialization input.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| token | string | yes for authenticated mode | Used to initialize `GitHubTool` in startup step 5. |

#### Behavioral constraints
- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.
- Credential errors are non-fatal during startup; emit `auth_error` XPC card and continue in degraded state.

---

### 13. ConsensusEngine Initialization Input

Required by the **Backend Startup Sequence**.

#### Type
Structured initialization input.

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| API keys | string or collection of strings | yes for authenticated mode | Source states “Initialize ConsensusEngine with API keys”; exact field names not specified. |

#### Behavioral constraints
- Credential errors are non-fatal during startup; emit `auth_error` XPC card and continue in degraded state.

---

## Enums and Constants

### Required literal values

| Name | Type | Exact Value |
|---|---|---|
| Security refusal sentinel | string | `SECURITY_REFUSAL` |
| Listening prefix | string | `FORGE_AGENT_LISTENING:` |
| Auth error card type | string | `auth_error` |
| VTZ denial verdict | string | `block` |
| Missing identity trust state | string | `UNTRUSTED` |
| Action outcome | string enum | `allow` |
| Action outcome | string enum | `restrict` |
| Action outcome | string enum | `block` |

### Startup timing constant

| Name | Type | Exact Value |
|---|---|---|
| Credential wait timeout | duration/string in spec | `30s` |

### Logging / audit constant

| Name | Type | Exact Value |
|---|---|---|
| TrustFlow failed emission level | string | `WARN` |

### Required named components

These names are contract-significant integration targets or startup components:

- `GitHubTool`
- `ConsensusEngine`
- `DocumentStore`
- `CommandRouter`
- `TrustLock`
- `path_security.validate_write_path()`

---

## Validation Rules

## 1. Entry-point enforcement

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur FIRST.
2. If CTX-ID validation fails, processing MUST be immediately rejected.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. If VTZ policy denies the action, a `VTZEnforcementDecision` MUST be created with:
   - `verdict = block`
6. Every action outcome MUST emit a TrustFlow event.
7. TrustFlow event emission failure:
   - MUST NOT silently continue
   - MUST be logged
   - MUST be surfaced

## 2. TrustFlow event validation

A valid TrustFlow event MUST satisfy all of the following:

- Contains all required fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- `event_id`:
  - globally unique
  - generated via CSPRNG
  - not sequential
- `ts`:
  - UTC Unix timestamp
  - millisecond precision
- `payload_hash`:
  - SHA-256 of serialized action payload

## 3. CTX-ID validation

A valid CTX-ID handling path MUST satisfy all of the following:

- Token is treated as immutable after issuance.
- Rotation issues a new token.
- Old token is invalidated immediately on rotation.
- Expired token is rejected.
- Validation is performed against TrustLock public key.
- Software-only validation is rejected.
- Missing token is treated as `UNTRUSTED`.

## 4. VTZ validation

A valid VTZ enforcement path MUST satisfy all of the following:

- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

## 5. Startup sequence validation

Order is mandatory and MUST be exactly:

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC (timeout: `30s`)
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (async)
8. Send ready message via XPC (includes `agent_version`, `capabilities`)
9. Enter `CommandRouter` event loop

Additional startup constraints:

- Steps 5–6 are non-fatal on credential errors.
- On those credential errors, emit `auth_error` XPC card.
- Continue in degraded state.
- Step 7 is always async.
- App remains responsive while embeddings load.

## 6. Security validation

The following are mandatory:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- When `SECURITY_REFUSAL` appears in output: stop, gate, log. Never retry to bypass.

## 7. Language/runtime implementation constraints

### Python backend
- Python `3.12`
- Type annotations on every function
- `async/await` throughout backend
- No blocking calls on event loop
- Dataclasses for all structured data

### Testing/tooling
- `pytest` for tests
- Tests live in `tests/`
- Tests mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage `≥ 85%` on all new modules

## 8. Forbidden implementations

The following behaviors are explicitly non-conformant:

- Ignoring `SECURITY_REFUSAL` and retrying generation
- Swift force unwrap:
  ```swift
  let value = optional!
  ```
- LLM API call from Swift
- Backend Python reading from Keychain directly

Exact forbidden examples from source:

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)  # WRONG — do not retry
```

```swift
let value = optional!
let client = AnthropicClient(apiKey: keychainValue)
let token = KeychainKit.read("github_token")
```

---

## Wire Format Examples

## 1. Valid TrustFlow event

```json
{
  "event_id": "6f4d7b73-9d3e-4ec8-8d48-1d4a0d79cb8b",
  "session_id": "sess_01JXYZ8YQ1M3J7B4P2K9",
  "ctx_id": "ctx_01JXYZ8YY2A4D6E8F0G1",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "5f70bf18a086007016e948b04aed3b82103a36beA41755bD6f2f0f8c2d1b7f54"
}
```

Notes:
- Example demonstrates required fields only.
- `payload_hash` is shown as a SHA-256-style hex string example; producer MUST use SHA-256 of serialized action payload.

## 2. Invalid TrustFlow event: missing required field

```json
{
  "event_id": "6f4d7b73-9d3e-4ec8-8d48-1d4a0d79cb8b",
  "session_id": "sess_01JXYZ8YQ1M3J7B4P2K9",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "5f70bf18a086007016e948b04aed3b82103a36bea41755bd6f2f0f8c2d1b7f54"
}
```

Reason:
- Missing `ctx_id`

## 3. Invalid TrustFlow event: sequential/non-compliant event id

```json
{
  "event_id": "10042",
  "session_id": "sess_01JXYZ8YQ1M3J7B4P2K9",
  "ctx_id": "ctx_01JXYZ8YY2A4D6E8F0G1",
  "ts": 1735689600123,
  "event_type": "action.block",
  "payload_hash": "5f70bf18a086007016e948b04aed3b82103a36bea41755bd6f2f0f8c2d1b7f54"
}
```

Reason:
- `event_id` MUST be globally unique and not sequential

## 4. Valid VTZ enforcement decision on denial

```json
{
  "verdict": "block"
}
```

## 5. Invalid VTZ enforcement decision on denial

```json
{
  "verdict": "deny"
}
```

Reason:
- On VTZ policy denial, exact required value is `block`

## 6. Valid listening announcement

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

## 7. Invalid listening announcement

```text
LISTENING:/tmp/forge-agent.sock
```

Reason:
- Must use exact prefix `FORGE_AGENT_LISTENING:`

## 8. Valid ready XPC message

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

Notes:
- Exact capability values are deployment-defined unless specified elsewhere.
- Only `agent_version` and `capabilities` are mandated by provided source excerpts.

## 9. Invalid ready XPC message

```json
{
  "version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

Reason:
- Missing exact required field name `agent_version`

## 10. Valid auth error XPC card

```json
{
  "type": "auth_error"
}
```

## 11. Invalid handling of SECURITY_REFUSAL

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Reason:
- Must stop, gate, and log
- Must never retry to bypass

## 12. Valid handling of SECURITY_REFUSAL

```python
if "SECURITY_REFUSAL" in output:
    logger.warning("SECURITY_REFUSAL")
    return {"type": "security_gate"}
```

Notes:
- Exact gated return payload is implementation-defined in provided excerpts.
- Required behavior is stop, gate, log, and no retry.

---

## Integration Points

## 1. XPC boundary

### Inputs from Swift to backend
- Credentials via XPC
- Delivery source must be Swift
- Only Swift reads Keychain
- Only Swift may deliver Keychain-derived credentials via XPC

### Outputs from backend to Swift
- Listening announcement via stdout:
  - `FORGE_AGENT_LISTENING:{socket_path}`
- Ready message via XPC:
  - includes `agent_version`
  - includes `capabilities`
- `auth_error` XPC card on non-fatal credential initialization errors

## 2. GitHub integration

- All GitHub operations go through `GitHubTool`
- Never call GitHub API directly from pipeline code
- `GitHubTool` is initialized in startup step 5 with token

## 3. Consensus engine integration

- `ConsensusEngine` is initialized in startup step 6 with API keys
- Credential errors are non-fatal during startup
- On credential failure, backend continues in degraded state and emits `auth_error`

## 4. Document loading integration

- `DocumentStore` loading starts in background asynchronously
- This must not block readiness of the app
- All loaded document chunks must pass injection scanning before inclusion in LLM prompts

## 5. Command routing integration

- `CommandRouter` event loop is entered only after:
  - logger initialization
  - XPC server start
  - listening announcement
  - credential wait
  - `GitHubTool` initialization
  - `ConsensusEngine` initialization
  - `DocumentStore` background load start
  - ready message send

## 6. Trust and enforcement integration

- CTX-ID validation must be first enforcement operation on any action-processing entry point
- CTX-ID validation must be against TrustLock public key
- VTZ check must precede execution
- Denial must produce `VTZEnforcementDecision` with `verdict=block`
- Every outcome must emit TrustFlow synchronously

## 7. Filesystem integration

- Before any disk write, path must be validated with:
  - `path_security.validate_write_path()`

## 8. Prompt construction integration

- External document context goes in USER prompt only
- Never place external document context in SYSTEM prompt

## 9. Development and test integration

Before implementation changes:
1. Find the TRD that owns the component being modified
2. Read relevant TRD sections
3. Check TRD-11 if change touches credentials, external content, generated code, or CI
4. Run existing tests:

```bash
cd src && pytest ../tests/ -v --tb=short
```

Required implementation standards:
- Python 3.12
- Full type annotations
- async/await backend
- dataclasses for structured data
- pytest
- ruff
- mypy
- coverage ≥ 85% on new modules