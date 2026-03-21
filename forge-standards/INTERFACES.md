# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements explicitly present in the provided TRD content for the `ConsensusDevAgent` subsystem and its required surrounding integration behavior.

Where the TRDs specify exact fields, values, ordering, or constraints, they are reproduced exactly below.

---

### 1. TrustFlowEvent

Required by: `TrustFlow Emission Contract`

Represents a synchronous audit/emission record produced for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | MUST be globally unique; CSPRNG-generated; MUST NOT be sequential |
| `session_id` | string | yes | MUST be included on every TrustFlow event |
| `ctx_id` | string | yes | MUST be included on every TrustFlow event |
| `ts` | number | yes | MUST be UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | MUST be included on every TrustFlow event |
| `payload_hash` | string | yes | MUST be SHA-256 of the serialized action payload |

#### Behavioral constraints
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

---

### 2. VTZEnforcementDecision

Required by: `CAL Enforcement Contract`

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | On VTZ policy denial, MUST equal `block` |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 3. XPC Ready Message

Required by: `Backend Startup Sequence`

Sent via XPC after initialization steps complete.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | MUST be included in ready message |
| `capabilities` | array | yes | MUST be included in ready message |

#### Behavioral constraints
- Sent at startup step 8.
- Must be sent only after:
  1. logger initialization
  2. XPC server start
  3. stdout listen message
  4. credential wait
  5. `GitHubTool` initialization attempt
  6. `ConsensusEngine` initialization attempt
  7. `DocumentStore` background loading start

---

### 4. XPC Auth Error Card

Required by: `Backend Startup Sequence`

Emitted via XPC when credential initialization fails.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `auth_error` | object or string | implied | Exact internal fields not specified in provided TRD text |

#### Behavioral constraints
- Steps 5-6 are non-fatal on credential errors.
- MUST emit `auth_error` XPC card.
- System MUST continue in degraded state.

---

### 5. Backend Listening Announcement

Required by: `Backend Startup Sequence`

Exact stdout wire line emitted for Swift discovery.

**Format**
```text
FORGE_AGENT_LISTENING:{socket_path}
```

| Component | Type | Required | Constraints |
|---|---|---:|---|
| `FORGE_AGENT_LISTENING:` | literal string prefix | yes | MUST appear exactly as shown |
| `{socket_path}` | string | yes | Socket path currently being listened on |

#### Behavioral constraints
- Printed to stdout at startup step 3.
- Swift reads this line.

---

### 6. SECURITY_REFUSAL Output Sentinel

Required by: security rules

Represents an LLM security refusal condition.

| Value | Type | Required | Constraints |
|---|---|---:|---|
| `SECURITY_REFUSAL` | string literal | yes | When present in output, processing MUST stop |

#### Behavioral constraints
- When you see `SECURITY_REFUSAL` output from the LLM: stop, gate, log.
- Never retry to bypass.
- Ignoring `SECURITY_REFUSAL` is explicitly forbidden.

---

### 7. CTX-ID Token

Required by: `CTX-ID Contract`

Opaque token used for identity/trust enforcement. Internal field schema is not specified in the provided TRD text, but validation and lifecycle constraints are mandatory.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | Missing `ctx_id` MUST be treated as `UNTRUSTED` |

#### Behavioral constraints
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification after issuance.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Never infer identity from context.

---

### 8. Session-to-VTZ Binding

Required by: `VTZ Enforcement Contract`

Represents the binding constraints for an agent session.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | string | yes | Session identity for enforcement context |
| `vtz` | string | yes | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance |

#### Behavioral constraints
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

### 9. Action Payload

Required by: `TrustFlow Emission Contract` and `CAL Enforcement Contract`

Represents the serialized payload of an agent action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `payload` | serialized object/bytes/string | yes | `payload_hash` MUST be SHA-256 of the serialized action payload |

#### Behavioral constraints
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted.
- Every action MUST be checked against VTZ policy BEFORE execution.

---

## Enums and Constants

### Enforcement Verdict

| Name | Type | Allowed Values | Constraints |
|---|---|---|---|
| `verdict` | string | `block` | Required exact value on VTZ denial |

Note: The action outcomes named by the TRD are:
- `allow`
- `restrict`
- `block`

These values are explicitly referenced as outcome categories for TrustFlow emission. Only `block` is explicitly bound to a concrete record field in the provided text.

---

### Identity / Trust Constants

| Constant | Type | Exact Value | Meaning |
|---|---|---|---|
| Untrusted identity state | string | `UNTRUSTED` | Applied when CTX-ID is missing |

---

### Security Sentinel

| Constant | Type | Exact Value | Meaning |
|---|---|---|---|
| LLM refusal sentinel | string | `SECURITY_REFUSAL` | Indicates refusal; processing must stop |

---

### Startup Output Constant

| Constant | Type | Exact Value | Meaning |
|---|---|---|---|
| stdout listen prefix | string | `FORGE_AGENT_LISTENING:` | Prefix for startup socket announcement |

---

### Timing Constant

| Constant | Type | Exact Value | Meaning |
|---|---|---|---|
| credential wait timeout | duration | `30s` | Maximum wait for credentials via XPC during startup step 4 |

---

### Logging Severity Constant

| Constant | Type | Exact Value | Meaning |
|---|---|---|---|
| TrustFlow emission failure severity | string | `WARN` | Required audit severity for failed emission |

---

## Validation Rules

## 1. Startup Sequence Validation

Order is mandatory and MUST NOT change.

Exact sequence:

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

### Additional startup rules
- Steps 5-6 are non-fatal on credential errors.
- On such errors, emit `auth_error` XPC card.
- Continue in degraded state.
- Step 7 is always async.
- App must remain responsive while embeddings load.

---

## 2. CAL Enforcement Validation

For every entry point that processes an agent action:

1. CTX-ID validation MUST happen FIRST.
2. If CTX-ID validation fails:
   - immediate rejection is required
   - no partial processing is permitted
3. VTZ policy check MUST happen BEFORE execution.
4. If VTZ denies:
   - produce `VTZEnforcementDecision`
   - set `verdict=block`
5. Every action outcome must emit a TrustFlow event.
6. If TrustFlow emission fails:
   - MUST NOT silently continue
   - MUST log
   - MUST surface the failure

---

## 3. TrustFlow Event Validation

A TrustFlow event is valid only if all required fields are present:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Additional constraints:

- `event_id` must be globally unique
- `event_id` must be CSPRNG-based
- `event_id` must not be sequential
- `ts` must be UTC Unix timestamp with millisecond precision
- `payload_hash` must be SHA-256 of the serialized action payload
- emission must be synchronous in the enforcement path
- async buffering is invalid

---

## 4. CTX-ID Validation

- Missing `ctx_id` is not nullable/implicit; it MUST be treated as `UNTRUSTED`
- Expired CTX-ID MUST be rejected
- CTX-ID must be validated against TrustLock public key
- Software-only validation is rejected
- CTX-ID field mutation after issuance is invalid
- Rotation must create a new token and invalidate the old token immediately

---

## 5. VTZ Validation

- Every agent session must be bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls without explicit policy authorization are invalid
- Implicit authorization is denied
- Mid-session VTZ policy change does not alter current session; changes apply at next CTX-ID issuance

---

## 6. Security Validation

### Prohibited behavior
- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Never use `shell=True` in subprocess calls
- Never call `eval()` or `exec()` on any generated or external content
- Never log HTTP response bodies
- Never call the GitHub API directly from pipeline code
- Never retry when `SECURITY_REFUSAL` is returned
- Never force unwrap optionals in Swift
- Never read backend credentials from Keychain in Python

### Required behavior
- All GitHub operations go through `GitHubTool`
- All file paths written to disk must pass `path_security.validate_write_path()` before any write
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt
- Context from external documents goes in the USER prompt, never the SYSTEM prompt
- Only Swift reads Keychain, only to deliver via XPC

---

## 7. Python Implementation Contract

- Python version: `3.12`
- Type annotations required on every function
- `async/await` throughout backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Testing with `pytest`
- Linting with `ruff`
- Type checking with `mypy`
- Test coverage must be `≥ 85%` on all new modules

These are implementation constraints, but they govern all structured-data implementations of this subsystem.

---

## Wire Format Examples

## 1. Valid TrustFlow Event

```json
{
  "event_id": "7e5cfd7f-0b15-4b5c-a7a6-54d4bdb6f1ab",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1731012345678,
  "event_type": "action_blocked",
  "payload_hash": "5f70bf18a086007016e948b04aed3b82103a36be-a-placeholder-example"
}
```

Valid because:
- all required fields are present
- `ts` is a Unix timestamp with millisecond precision
- includes required TrustFlow fields

---

## 2. Invalid TrustFlow Event: missing required field

```json
{
  "event_id": "7e5cfd7f-0b15-4b5c-a7a6-54d4bdb6f1ab",
  "session_id": "sess_123",
  "ts": 1731012345678,
  "event_type": "action_blocked",
  "payload_hash": "abc123"
}
```

Invalid because:
- missing `ctx_id`

---

## 3. Invalid TrustFlow Event: sequential identifier

```json
{
  "event_id": "1002",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1731012345678,
  "event_type": "action_allowed",
  "payload_hash": "abc123"
}
```

Invalid because:
- `event_id` MUST be globally unique
- `event_id` MUST be CSPRNG-generated
- sequential values are forbidden

---

## 4. Valid VTZ Denial Decision

```json
{
  "verdict": "block"
}
```

Valid because:
- VTZ denial must produce `VTZEnforcementDecision` with exact value `block`

---

## 5. Invalid VTZ Denial Decision

```json
{
  "verdict": "deny"
}
```

Invalid because:
- exact required value is `block`

---

## 6. Valid Ready Message

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

Valid because:
- includes both required fields: `agent_version`, `capabilities`

---

## 7. Invalid Ready Message

```json
{
  "agent_version": "1.0.0"
}
```

Invalid because:
- missing `capabilities`

---

## 8. Valid Startup Listen Output

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

Valid because:
- exact required prefix is present
- includes socket path

---

## 9. Invalid Startup Listen Output

```text
LISTENING:/tmp/forge-agent.sock
```

Invalid because:
- missing exact literal prefix `FORGE_AGENT_LISTENING:`

---

## 10. Invalid SECURITY_REFUSAL Handling

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Invalid because:
- retrying to bypass `SECURITY_REFUSAL` is explicitly forbidden

---

## Integration Points

## 1. XPC

The subsystem integrates with XPC for:

### Credential intake
- backend waits for credentials via XPC
- timeout is `30s`

### Ready signaling
- backend sends ready message via XPC with:
  - `agent_version`
  - `capabilities`

### Error signaling
- backend emits `auth_error` XPC card on credential initialization failure

### Keychain boundary
- Only Swift reads Keychain
- Swift delivers credentials via XPC
- Python backend reads nothing from Keychain

---

## 2. GitHubTool

All GitHub operations integrate exclusively through `GitHubTool`.

### Contract
- All GitHub operations go through `GitHubTool`
- Never call the GitHub API directly from pipeline code
- Backend startup step 5: initialize `GitHubTool` with token

---

## 3. ConsensusEngine

Backend startup step 6:

- Initialize `ConsensusEngine` with API keys

If credential errors occur:
- initialization is non-fatal
- emit `auth_error`
- continue in degraded state

---

## 4. DocumentStore

Backend startup step 7:

- start `DocumentStore` loading in background
- operation is async
- app remains responsive while embeddings load

Security integration:
- all loaded document chunks must pass injection scanning before inclusion in any LLM prompt
- external document context must go in the USER prompt, never the SYSTEM prompt

---

## 5. CommandRouter

Backend startup step 9:

- enter `CommandRouter` event loop

All agent action entry points handled through this path remain subject to:
- CTX-ID validation first
- VTZ check before execution
- TrustFlow emission for every outcome

---

## 6. Path Security

Before any file write:

- path must pass `path_security.validate_write_path()`

This is a mandatory pre-write integration contract.

---

## 7. TrustLock Public Key Validation

CTX-ID validation integrates with TrustLock public-key verification.

### Contract
- CTX-ID MUST be validated against TrustLock public key
- software-only validation is rejected

---

## 8. Testing Toolchain

Required project integration points:

- `pytest` in `tests/`
- `ruff`
- `mypy`

Pre-change test command from TRD:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## 9. Language and Structure Requirements

All structured backend data for this subsystem must conform to:

- Python `3.12`
- dataclasses for all structured data
- type annotations on every function
- async/await throughout backend
- no blocking calls on the event loop

---

## Notes on Unspecified Fields

The provided TRD excerpts do **not** define full field schemas for:
- credentials payloads received via XPC
- `auth_error` card internal structure
- `ConsensusEngine` API-key object structure
- `GitHubTool` token wrapper structure
- `CommandRouter` command payload schema
- CTX-ID internal token fields beyond `ctx_id` presence and lifecycle constraints
- VTZ identifier field names beyond the concept of a bound VTZ
- DTL Label schema

These fields must not be invented at implementation time without the owning TRD section. Only the exact fields and constraints listed above are normative from the provided source.