# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements explicitly present in the provided TRD content for the `ConsensusDevAgent` subsystem and its directly referenced integration surfaces.

Where the TRDs specify exact field names, values, ordering, or constraints, they are listed here verbatim. No unspecified fields may be assumed conformant.

---

### 1. Backend Startup Sequence Interface

This is a process-level interface contract between the backend, Swift client, XPC transport, and subsystem initializers.

#### 1.1 Startup Event Sequence

Order is mandatory.

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background
8. Send ready message via XPC
9. Enter `CommandRouter` event loop

#### 1.2 Stdout Listening Announcement

**Format**
- Type: string
- Required: yes
- Exact prefix: `FORGE_AGENT_LISTENING:`
- Suffix: `{socket_path}`

**Constraints**
- Must be printed to stdout.
- `{socket_path}` is the XPC socket path Swift reads.
- Emission occurs after XPC server starts listening.
- Emission occurs before waiting for credentials.

**Wire shape**
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### 1.3 Credential Wait

**Operation**
- Wait for credentials via XPC

**Constraints**
- Timeout: `30s`

#### 1.4 GitHubTool Initialization Input

**Input structure**
- `token`
  - Type: string
  - Required: yes for normal operation
  - Source constraint: delivered via XPC
  - Security constraint: Python reads nothing from Keychain

**Degraded-state behavior**
- Credential errors at this step are non-fatal.
- Must emit `auth_error` XPC card.
- Process must continue in degraded state.

#### 1.5 ConsensusEngine Initialization Input

**Input structure**
- `api keys`
  - Type: collection of credential values
  - Required: yes for normal operation
  - Security constraints:
    - Never hardcode credentials, API keys, tokens, or secrets as string literals.
    - Delivered through approved credential path only.

**Degraded-state behavior**
- Credential errors at this step are non-fatal.
- Must emit `auth_error` XPC card.
- Process must continue in degraded state.

#### 1.6 DocumentStore Load Operation

**Operation**
- Start `DocumentStore` loading in background

**Constraints**
- Must be async.
- App must remain responsive while embeddings load.

#### 1.7 XPC Ready Message

The startup sequence requires a ready message sent via XPC.

**Required fields**
- `agent_version`
  - Type: string
  - Required: yes
- `capabilities`
  - Type: array
  - Required: yes

**Constraints**
- Sent only after:
  - XPC server is listening
  - credential wait has completed or degraded-state handling is established
  - `GitHubTool` initialization attempted
  - `ConsensusEngine` initialization attempted
  - `DocumentStore` background loading started

#### 1.8 XPC Auth Error Card

Referenced explicitly as `auth_error`.

**Fields**
- Exact wire shape not specified in the provided TRD excerpts.
- Minimum required discriminant/value:
  - `auth_error`
    - Type: string enum value or card type identifier
    - Required: yes when credential initialization fails

**Constraints**
- Must be emitted on credential errors for steps 5 and 6.
- Must not terminate startup.
- Backend continues in degraded state.

---

### 2. CAL Enforcement Contract Structures

Every entry point that processes an agent action must conform to this contract.

#### 2.1 Agent Action Payload

The action payload is referenced for hashing and enforcement, but no explicit field schema is provided in the supplied TRD excerpts.

**Known contract properties**
- Must undergo CTX-ID validation first.
- Must be checked against VTZ policy before execution.
- Serialized form is hashed using SHA-256 for TrustFlow emission.

#### 2.2 VTZEnforcementDecision

This record is required on VTZ denial.

**Fields**
- `verdict`
  - Type: string
  - Required: yes
  - Required exact value on denial: `block`

**Constraints**
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record.
- On denial, `verdict=block` exactly.

No additional fields are specified in the provided excerpts.

#### 2.3 Action Outcome

Possible enforcement outcomes explicitly referenced:
- `allow`
- `restrict`
- `block`

**Constraints**
- Every action outcome must emit a TrustFlow event.

---

### 3. TrustFlow Event Structure

Every TrustFlow event must include the following fields.

#### 3.1 TrustFlowEvent

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | Must be globally unique; CSPRNG-generated; not sequential |
| `session_id` | string | yes | Required |
| `ctx_id` | string | yes | Required |
| `ts` | number | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Required |
| `payload_hash` | string | yes | SHA-256 of the serialized action payload |

**Constraints**
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission must not be a silent skip.
- CAL contract additionally requires failures to be logged and surfaced.

#### 3.2 `event_id`

- Type: string
- Required: yes
- Constraints:
  - globally unique
  - generated with CSPRNG
  - not sequential

#### 3.3 `session_id`

- Type: string
- Required: yes

#### 3.4 `ctx_id`

- Type: string
- Required: yes

#### 3.5 `ts`

- Type: number
- Required: yes
- Constraints:
  - UTC Unix timestamp
  - millisecond precision

#### 3.6 `event_type`

- Type: string
- Required: yes

#### 3.7 `payload_hash`

- Type: string
- Required: yes
- Constraints:
  - SHA-256 of the serialized action payload

---

### 4. CTX-ID Token Contract

The CTX-ID schema is not fully defined in the provided excerpts, but the following interface requirements are mandatory.

#### 4.1 CTX-ID Token

**Fields**
- `ctx_id`
  - Type: token/string identifier
  - Required: yes for trusted requests
  - Behavior when missing: treated as `UNTRUSTED`

**Constraints**
- Tokens are immutable once issued.
- No field modification after issuance.
- Rotation creates a new token.
- Old token is invalidated immediately on rotation.
- Expired CTX-ID must be rejected.
- Validation must be against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must never result in inferred identity from context.

#### 4.2 Missing CTX-ID Classification

- Exact value: `UNTRUSTED`
- Type: string classification/state
- Applied when `ctx_id` is missing

---

### 5. VTZ Session Binding Contract

The VTZ schema is not fully defined in the provided excerpts. The required interface semantics are:

#### 5.1 Session-to-VTZ Binding

**Fields**
- `vtz`
  - Type: identifier
  - Required: yes at CTX-ID issuance/session binding time

**Constraints**
- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

### 6. Security-Gated LLM Output Handling

#### 6.1 SECURITY_REFUSAL Handling

**Input**
- LLM output content containing the exact token:
  - `SECURITY_REFUSAL`

**Required behavior**
- stop
- gate
- log

**Prohibited behavior**
- Never retry to bypass.
- Specifically forbidden:
  ```python
  if "SECURITY_REFUSAL" in output:
      output = await self._generate_openai(prompt)
  ```

**Interface significance**
- Any response-processing interface that accepts model output must support detection of the exact string `SECURITY_REFUSAL`.

---

### 7. Document Loading and Prompt-Construction Interfaces

#### 7.1 Loaded Document Chunk

**Fields**
- Exact chunk schema not defined in the provided excerpts.

**Required processing constraints**
- Every loaded document chunk must pass injection scanning before inclusion in any LLM prompt.

#### 7.2 Prompt Context Placement

**Constraint**
- Context from external documents goes in the `USER` prompt.
- Never place external document context in the `SYSTEM` prompt.

---

### 8. Path Validation Interface

#### 8.1 Write Path Validation

Before any file write to disk:

**Required function**
- `path_security.validate_write_path()`

**Contract**
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

**Input**
- file path
  - Type: path/string

**Output**
- pass/fail validation result
  - Exact return schema not specified in provided excerpts

---

### 9. GitHub Operations Integration Interface

#### 9.1 GitHubTool

All GitHub operations go through `GitHubTool`.

**Constraints**
- Never call the GitHub API directly from pipeline code.
- `GitHubTool` is initialized with `token`.

**Initialization input**
- `token`
  - Type: string
  - Required: yes for authenticated operation

---

### 10. Backend Language/Structure Conformance Requirements

These are implementation-level interface constraints that affect shape and compatibility of subsystem APIs.

#### 10.1 Structured Data Carrier

**Required form**
- Dataclasses for all structured data

#### 10.2 Async Contract

**Constraints**
- `async/await` throughout the backend
- No blocking calls on the event loop

#### 10.3 Function Signatures

**Constraints**
- Type annotations on every function

---

## Enums and Constants

### 1. Exact String Constants

| Constant | Type | Meaning |
|---|---|---|
| `FORGE_AGENT_LISTENING:` | string prefix | Stdout startup announcement prefix |
| `auth_error` | string | XPC card/type emitted on credential error |
| `SECURITY_REFUSAL` | string | LLM refusal marker that must stop/gate/log handling |
| `UNTRUSTED` | string | Classification when CTX-ID is missing |
| `block` | string | Required `VTZEnforcementDecision.verdict` value on VTZ denial |
| `USER` | string | Prompt role for external document context |
| `SYSTEM` | string | Prompt role external document context must not use |

### 2. Enumerated Outcome Values

#### 2.1 Enforcement Outcome
Allowed explicit values from the TRD text:
- `allow`
- `restrict`
- `block`

#### 2.2 VTZEnforcementDecision.verdict
Explicitly required on denial:
- `block`

### 3. Timing Constants

| Name | Value | Type | Applies To |
|---|---:|---|---|
| credential wait timeout | `30s` | duration string | XPC credential wait during startup |

### 4. Hashing and Timestamp Constants

| Name | Value |
|---|---|
| payload hash algorithm | `SHA-256` |
| timestamp basis | `UTC Unix timestamp` |
| timestamp precision | `millisecond` |

---

## Validation Rules

### 1. Startup Validation

1. Backend must print `FORGE_AGENT_LISTENING:{socket_path}` to stdout after XPC server starts listening.
2. Credentials must be awaited via XPC with timeout `30s`.
3. `GitHubTool` initialization must occur before `ConsensusEngine` initialization.
4. `DocumentStore` loading must start after `ConsensusEngine` initialization attempt.
5. Ready XPC message must include:
   - `agent_version`
   - `capabilities`
6. On credential errors during `GitHubTool` or `ConsensusEngine` initialization:
   - emit `auth_error`
   - continue in degraded state

### 2. CAL Enforcement Validation

1. Every entry point processing an agent action must validate CTX-ID first.
2. CTX-ID validation failure must cause immediate rejection.
3. No partial processing is permitted after CTX-ID failure.
4. Every action must be checked against VTZ policy before execution.
5. VTZ denial must produce `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.
7. TrustFlow emission failure must be logged and surfaced.
8. TrustFlow emission failure must not silently continue.

### 3. TrustFlow Event Validation

A TrustFlow event is invalid unless all of the following are true:

- `event_id` exists
- `session_id` exists
- `ctx_id` exists
- `ts` exists
- `event_type` exists
- `payload_hash` exists
- `event_id` is globally unique
- `event_id` is CSPRNG-generated
- `event_id` is not sequential
- `ts` is a UTC Unix timestamp with millisecond precision
- `payload_hash` is SHA-256 of the serialized action payload

Additional transport rule:
- emission must be synchronous in enforcement path
- async buffering is invalid

### 4. CTX-ID Validation

A CTX-ID is valid only if all of the following hold:

- present, unless request is intentionally treated as `UNTRUSTED`
- not expired
- validated against TrustLock public key
- not modified after issuance

Additional rules:
- software-only validation is rejected
- rotated CTX-ID must produce a new token
- old token becomes invalid immediately
- missing CTX-ID must be treated as `UNTRUSTED`

### 5. VTZ Validation

1. Each agent session must be bound to exactly one VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls are invalid unless explicit policy authorization exists.
3. Implicit cross-VTZ authorization is denied.
4. VTZ policy changes do not alter current session behavior mid-session; they apply at next CTX-ID issuance.

### 6. Security Validation

1. If output contains `SECURITY_REFUSAL`, processing must stop, gate, and log.
2. Retrying an LLM call to bypass `SECURITY_REFUSAL` is invalid.
3. No credentials, API keys, tokens, or secrets may appear as string literals.
4. `shell=True` in subprocess calls is forbidden.
5. `eval()` and `exec()` on generated or external content are forbidden.
6. HTTP response bodies must not be logged.
7. Only status codes and error types may be logged for HTTP errors.
8. Every file path must pass `path_security.validate_write_path()` before write.
9. Every loaded document chunk must pass injection scanning before prompt inclusion.
10. External document context must be placed in `USER`, never `SYSTEM`.

### 7. Keychain/Credential Boundary Validation

1. Swift may read Keychain.
2. Python reads nothing from Keychain.
3. Backend credentials are delivered via XPC.
4. Direct backend Keychain reads are non-conformant.

---

## Wire Format Examples

## 1. Valid Payloads

### 1.1 Stdout Listening Announcement
```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### 1.2 XPC Ready Message
```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

### 1.3 TrustFlow Event
```json
{
  "event_id": "7f6c8c2f-4a4f-4b9d-8c7a-5a2cb5d1a2e1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action_allow",
  "payload_hash": "3d6f0a6c458f7e7d5b1c2a9f9b6c3e4d2a1b0f8e7d6c5b4a3928171615141312"
}
```

### 1.4 VTZ Denial Decision
```json
{
  "verdict": "block"
}
```

### 1.5 Missing CTX-ID Classification
```json
{
  "ctx_id": "UNTRUSTED"
}
```

### 1.6 Auth Error Card
```json
{
  "type": "auth_error"
}
```

## 2. Invalid Payloads

### 2.1 Invalid TrustFlow Event: Missing Required Field
```json
{
  "event_id": "7f6c8c2f-4a4f-4b9d-8c7a-5a2cb5d1a2e1",
  "session_id": "sess_123",
  "ts": 1735689600123,
  "event_type": "action_allow",
  "payload_hash": "3d6f0a6c458f7e7d5b1c2a9f9b6c3e4d2a1b0f8e7d6c5b4a3928171615141312"
}
```

Reason:
- missing `ctx_id`

### 2.2 Invalid TrustFlow Event: Sequential/Non-CSPRNG Event ID
```json
{
  "event_id": "1001",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action_allow",
  "payload_hash": "3d6f0a6c458f7e7d5b1c2a9f9b6c3e4d2a1b0f8e7d6c5b4a3928171615141312"
}
```

Reason:
- `event_id` must be globally unique, CSPRNG-generated, and not sequential

### 2.3 Invalid VTZ Denial Decision
```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ denial must produce `verdict=block`

### 2.4 Invalid External Context Placement
```json
{
  "role": "SYSTEM",
  "content": "External document excerpt"
}
```

Reason:
- external document context must go in `USER`, never `SYSTEM`

### 2.5 Invalid SECURITY_REFUSAL Handling
```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Reason:
- retry to bypass `SECURITY_REFUSAL` is forbidden

### 2.6 Invalid Backend Keychain Access
```python
token = KeychainKit.read("github_token")
```

Reason:
- Python reads nothing from Keychain

### 2.7 Invalid Swift Force Unwrap
```swift
let value = optional!
```

Reason:
- force unwrap is forbidden by subsystem rules

### 2.8 Invalid Swift-side Direct LLM API Call
```swift
let client = AnthropicClient(apiKey: keychainValue)
```

Reason:
- LLM API call from Swift is forbidden

---

## Integration Points

### 1. Swift Client ↔ Backend

#### 1.1 Stdout Discovery
- Swift reads stdout line:
  - `FORGE_AGENT_LISTENING:{socket_path}`

#### 1.2 XPC Credential Delivery
- Swift delivers credentials via XPC.
- Backend waits up to `30s`.
- Python must not read Keychain directly.
- Only Swift reads Keychain, only to deliver via XPC.

#### 1.3 XPC Startup Messaging
Backend sends:
- ready message with:
  - `agent_version`
  - `capabilities`
- `auth_error` card on credential initialization failures

### 2. Backend ↔ GitHubTool

- All GitHub operations go through `GitHubTool`.
- Pipeline code must not call GitHub API directly.
- Initialization input:
  - `token: string`

### 3. Backend ↔ ConsensusEngine

- `ConsensusEngine` initializes with API keys.
- Credential failure is non-fatal:
  - emit `auth_error`
  - continue degraded

### 4. Backend ↔ DocumentStore

- `DocumentStore` loading starts in background asynchronously.
- System must remain responsive while embeddings load.

### 5. Enforcement Path ↔ TrustFlow

Every action-processing entry point must:
1. validate CTX-ID
2. enforce VTZ policy
3. emit TrustFlow event synchronously

Required TrustFlow fields:
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

### 6. Enforcement Path ↔ CTX-ID Validation

- CTX-ID validation happens first.
- Expired, invalid, or missing identity must be handled per CTX-ID contract.
- Missing CTX-ID maps to `UNTRUSTED`.

### 7. Enforcement Path ↔ VTZ Policy

- Every action is checked before execution.
- Denial produces `VTZEnforcementDecision` with `verdict=block`.

### 8. File System Writes ↔ Path Security

Before any disk write:
- validate with `path_security.validate_write_path()`

### 9. Document Ingestion ↔ Prompt Builder

Before any document chunk is included in prompt context:
- injection scanning required

Prompt role contract:
- external context in `USER`
- never in `SYSTEM`

### 10. LLM Output Handling ↔ Security Gate

If output contains:
- `SECURITY_REFUSAL`

Then system must:
- stop
- gate
- log

Must not:
- retry to bypass refusal

---

## Conformance Notes

A `ConsensusDevAgent` implementation is non-conformant if any of the following occur:

- missing TrustFlow event fields
- non-synchronous TrustFlow emission in enforcement path
- CTX-ID checked after any action processing begins
- VTZ denial without `VTZEnforcementDecision.verdict = "block"`
- direct GitHub API calls outside `GitHubTool`
- backend Keychain reads
- external context placed in `SYSTEM`
- file writes without `path_security.validate_write_path()`
- retry after `SECURITY_REFUSAL`
- startup sequence order changed
- ready message missing `agent_version` or `capabilities`