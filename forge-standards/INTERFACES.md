# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the required wire-format and API contract elements for the `ConsensusDevAgent` subsystem based strictly on the provided TRD/interface material.

Where the source defines exact field names, values, ordering, or constraints, they are reproduced exactly.

### 1. TrustFlow Event

Required by the **TrustFlow Emission Contract**.

#### Type
Structured record / object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | Yes | MUST be globally unique; MUST be generated using CSPRNG; MUST NOT be sequential |
| `session_id` | string | Yes | Required on every TrustFlow event |
| `ctx_id` | string | Yes | Required on every TrustFlow event |
| `ts` | number | Yes | MUST be UTC Unix timestamp with millisecond precision |
| `event_type` | string | Yes | Required on every TrustFlow event |
| `payload_hash` | string | Yes | MUST be SHA-256 of the serialized action payload |

#### Behavioral constraints
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission MUST NOT be silently skipped.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### 2. VTZEnforcementDecision

Required by the **CAL Enforcement Contract**.

#### Type
Structured record / object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | Yes | On VTZ policy denial, MUST equal `block` |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 3. XPC Listening Announcement

Required by the **Backend Startup Sequence**.

#### Type
Stdout line / plain text message

#### Format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Fields

| Component | Type | Required | Constraints |
|---|---|---:|---|
| `FORGE_AGENT_LISTENING:` | literal string prefix | Yes | MUST appear exactly as shown |
| `{socket_path}` | string | Yes | Socket path for Swift to read |

#### Constraints
- MUST be printed to stdout.
- MUST occur at startup step 3.
- Ordering is mandatory.

---

### 4. Ready Message via XPC

Required by the **Backend Startup Sequence**.

#### Type
Structured XPC message / object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | Yes | MUST be included in the ready message |
| `capabilities` | array | Yes | MUST be included in the ready message |

#### Constraints
- Sent via XPC at startup step 8.
- MUST be sent after:
  1. logger initialization
  2. XPC server start
  3. listening announcement
  4. credentials wait
  5. `GitHubTool` initialization
  6. `ConsensusEngine` initialization
  7. `DocumentStore` background loading start

---

### 5. auth_error XPC Card

Required by the **Backend Startup Sequence**.

#### Type
Structured XPC message / object

#### Fields
The provided source defines the card name only and does not define its internal fields.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _unspecified_ | — | — | Source only requires emission of an `auth_error` XPC card |

#### Constraints
- On credential errors in steps 5-6, emit `auth_error` XPC card.
- Credential errors at steps 5-6 are non-fatal.
- System MUST continue in degraded state.

---

### 6. CTX-ID Token

Required by the **CTX-ID Contract**.

#### Type
Opaque token / identifier

#### Fields
No internal token fields are defined in the provided source.

#### Constraints
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from context when CTX-ID is missing.

---

### 7. Agent Action Payload

Implied by CAL and TrustFlow contracts.

#### Type
Structured payload / serialized action payload

#### Fields
Not enumerated in the provided source.

#### Constraints
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted on CTX-ID validation failure.
- Every action MUST be checked against VTZ policy BEFORE execution.
- `payload_hash` for TrustFlow MUST be SHA-256 of the serialized action payload.

---

### 8. Session-to-VTZ Binding

Required by the **VTZ Enforcement Contract**.

#### Type
Session binding state

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | string | Yes | Session identifier used in TrustFlow events |
| `vtz` | string | Yes | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance |

#### Constraints
- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

## Enums and Constants

### Verdict values

| Name | Type | Allowed Values | Notes |
|---|---|---|---|
| `verdict` | string | `block` | Exact required value on VTZ policy denial |

### Action outcome values

| Name | Type | Allowed Values | Notes |
|---|---|---|---|
| action outcome | string | `allow`, `restrict`, `block` | Every outcome MUST emit a TrustFlow event |

### Trust state values

| Name | Type | Allowed Values | Notes |
|---|---|---|---|
| CTX-ID missing state | string | `UNTRUSTED` | Missing CTX-ID MUST be treated as `UNTRUSTED` |

### Security refusal sentinel

| Name | Type | Exact Value | Notes |
|---|---|---|---|
| security refusal output marker | string | `SECURITY_REFUSAL` | When seen in LLM output: stop, gate, log; never retry to bypass |

### Startup output constant

| Name | Type | Exact Value | Notes |
|---|---|---|---|
| listening prefix | string | `FORGE_AGENT_LISTENING:` | Must be printed to stdout with socket path appended |

### Startup timeout constant

| Name | Type | Exact Value | Notes |
|---|---|---|---|
| credentials wait timeout | duration | `30s` | Wait for credentials via XPC |

### Logging level constant

| Name | Type | Exact Value | Notes |
|---|---|---|---|
| failed TrustFlow emission level | string | `WARN` | Must be a WARN-level audit event |

### Runtime / language constants

| Name | Type | Exact Value | Notes |
|---|---|---|---|
| Python version | string | `Python 3.12` | Backend requirement |
| test framework | string | `pytest` | Required |
| linter | string | `ruff` | Required |
| type checker | string | `mypy` | Required |
| minimum test coverage | percentage | `85%` | On all new modules |

---

## Validation Rules

## 1. Startup sequencing

Order is mandatory and MUST NOT be changed.

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

Additional rules:
- Steps 5-6 are non-fatal on credential errors.
- On credential errors in steps 5-6, emit `auth_error` XPC card.
- Continue in degraded state.
- Step 7 is always async.
- App must remain responsive while embeddings load.

---

## 2. CAL enforcement

For every entry point that processes an agent action:
1. CTX-ID validation MUST occur FIRST.
2. CTX-ID validation failure MUST cause immediate rejection.
3. No partial processing is allowed after CTX-ID validation failure.
4. VTZ policy check MUST occur BEFORE execution.
5. VTZ denial MUST produce `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

---

## 3. TrustFlow validation

A TrustFlow event is valid only if:
- `event_id` is present
- `session_id` is present
- `ctx_id` is present
- `ts` is present
- `event_type` is present
- `payload_hash` is present

Additional validation:
- `event_id` MUST be globally unique.
- `event_id` MUST use CSPRNG generation.
- `event_id` MUST NOT be sequential.
- `ts` MUST be UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is invalid.

---

## 4. CTX-ID validation

A CTX-ID is valid only if:
- it is present, unless the request is explicitly handled as `UNTRUSTED`
- it is not expired
- it validates against TrustLock public key

Invalid conditions:
- missing CTX-ID when trusted processing is expected
- expired CTX-ID
- software-only validation
- inferred identity from surrounding context instead of CTX-ID

Additional lifecycle rules:
- CTX-ID is immutable once issued.
- Rotation MUST create a new token.
- Previous token MUST be invalidated immediately.

---

## 5. VTZ validation

A session is valid only if:
- it is bound to exactly one VTZ at CTX-ID issuance

Invalid conditions:
- multiple VTZ bindings for one session
- implicit cross-VTZ authorization
- bypass of VTZ enforcement in application code

Policy timing rule:
- VTZ policy changes apply at NEXT CTX-ID issuance, not mid-session.

---

## 6. Security validation

### Forbidden behavior
The following are non-conformant:

#### Ignoring `SECURITY_REFUSAL`
If `SECURITY_REFUSAL` appears in output:
- stop
- gate
- log
- never retry to bypass

#### Hardcoded secrets
- Never hardcode credentials, API keys, tokens, or secrets as string literals.

#### Subprocess execution
- Never use `shell=True` in subprocess calls.

#### Dynamic execution
- Never call `eval()` or `exec()` on generated or external content.

#### HTTP logging
- Never log HTTP response bodies.
- Log status codes and error types only.

#### File writes
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

#### Document prompt injection scanning
- All loaded document chunks MUST pass injection scanning before being included in any LLM prompt.

#### Prompt placement
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

#### GitHub API access
- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

#### Backend credential access
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

---

## 7. Implementation constraints

- Python 3.12
- Type annotations on every function
- `async/await` throughout the backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Tests live in `tests/` and mirror `src/` structure
- `ruff` must pass clean
- `mypy` must pass clean
- Test coverage must be at least `85%` on all new modules

---

## Wire Format Examples

## 1. Valid TrustFlow event

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1710000000123,
  "event_type": "action_executed",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3a070f2f872d603d260a7b23ac48c"
}
```

Why valid:
- all required fields present
- `ts` shown as Unix timestamp in milliseconds
- `payload_hash` shown as SHA-256 hex string
- field names match contract exactly

---

## 2. Invalid TrustFlow event: missing required fields

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "sess_123",
  "ts": 1710000000123
}
```

Why invalid:
- missing `ctx_id`
- missing `event_type`
- missing `payload_hash`

---

## 3. Valid VTZEnforcementDecision on denial

```json
{
  "verdict": "block"
}
```

Why valid:
- denial record includes exact required value `block`

---

## 4. Invalid VTZEnforcementDecision on denial

```json
{
  "verdict": "deny"
}
```

Why invalid:
- source requires `verdict=block`

---

## 5. Valid startup stdout announcement

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

Why valid:
- exact required prefix
- includes socket path

---

## 6. Invalid startup stdout announcement

```text
LISTENING:/tmp/forge-agent.sock
```

Why invalid:
- required literal prefix must be exactly `FORGE_AGENT_LISTENING:`

---

## 7. Valid ready XPC message

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["consensus", "github"]
}
```

Why valid:
- includes required `agent_version`
- includes required `capabilities`

Note:
- exact capability values are not defined in the provided source; example values are illustrative only.

---

## 8. Invalid ready XPC message

```json
{
  "agent_version": "1.0.0"
}
```

Why invalid:
- missing required `capabilities`

---

## 9. Invalid security handling example

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Why invalid:
- retries to bypass `SECURITY_REFUSAL`
- contract requires stop, gate, log
- never retry to bypass

---

## 10. Invalid Swift/backend credential handling examples

```swift
let value = optional!
```

Why invalid:
- force unwrap is explicitly forbidden

```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Why invalid:
- LLM API call from Swift is explicitly forbidden

```swift
let token = KeychainKit.read("github_token")
```

Why invalid:
- Python reads nothing from Keychain
- only Swift reads Keychain, only to deliver via XPC

---

## Integration Points

## 1. XPC
ConsensusDevAgent interacts with Swift/app infrastructure through XPC for:
- credential delivery
- ready message delivery
- `auth_error` card emission

Defined wire elements:
- stdout announcement: `FORGE_AGENT_LISTENING:{socket_path}`
- credential wait timeout: `30s`
- ready message fields: `agent_version`, `capabilities`
- error card name: `auth_error`

---

## 2. GitHubTool
All GitHub operations MUST go through:

| Component | Requirement |
|---|---|
| `GitHubTool` | Required integration point for all GitHub operations |

Constraint:
- Never call the GitHub API directly from pipeline code.

---

## 3. ConsensusEngine
Startup integration:
- Initialize `ConsensusEngine` with API keys at startup step 6.
- Credential errors are non-fatal at this step.
- Emit `auth_error` XPC card and continue in degraded state on credential error.

---

## 4. DocumentStore
Startup integration:
- Start `DocumentStore` loading in background at startup step 7.
- Loading is async.
- App must remain responsive while embeddings load.

Security integration:
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- External document context must go in the USER prompt, never the SYSTEM prompt.

---

## 5. CommandRouter
Runtime integration:
- Enter `CommandRouter` event loop at startup step 9.

Preconditions:
- all prior startup steps completed in mandatory order
- ready message already sent

---

## 6. TrustLock
CTX-ID validation integration:
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

---

## 7. path_security
File system integration:
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

---

## 8. Tooling and test interfaces
Required development/test interfaces:

| Interface | Requirement |
|---|---|
| `pytest` | Test runner |
| `ruff` | Linting |
| `mypy` | Type checking |

Execution command from TRD:
```bash
cd src && pytest ../tests/ -v --tb=short
```