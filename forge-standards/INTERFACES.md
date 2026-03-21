# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements explicitly stated in the provided TRD/interface sources for the `ConsensusDevAgent` subsystem and its required integrations.

Where a field is mandated by source text, it is listed exactly. Where the source does not define a concrete payload schema, this document records only the guaranteed contract surface and constraints.

---

### 1. TrustFlow Event

Required for every action outcome in the enforcement path.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | Yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | string | Yes | Present on every TrustFlow event. |
| `ctx_id` | string | Yes | Present on every TrustFlow event. Must correspond to validated CTX-ID. |
| `ts` | number | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | string | Yes | Present on every TrustFlow event. |
| `payload_hash` | string | Yes | MUST be SHA-256 of the serialized action payload. |

#### Behavioral constraints
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission MUST NOT be silently skipped.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### 2. VTZEnforcementDecision

Produced on VTZ policy denial.

#### Type
Object

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | Yes | MUST equal `block` on VTZ policy denial. |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 3. XPC Listening Announcement

Printed by backend startup sequence for Swift consumption.

#### Type
Stdout line

#### Format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Components

| Component | Type | Required | Constraints |
|---|---|---:|---|
| `FORGE_AGENT_LISTENING:` | string literal | Yes | Literal prefix. Must appear exactly as shown. |
| `{socket_path}` | string | Yes | Socket path used by the XPC server. |

#### Behavioral constraints
- Must be emitted after XPC server start/listen.
- Must be emitted before waiting for credentials via XPC.
- Swift reads this value from stdout.

---

### 4. XPC Credentials Delivery

Backend waits for credentials from Swift via XPC.

#### Type
XPC message/payload

#### Defined fields from source
Not fully specified in the provided source.

#### Behavioral constraints
- Backend waits for credentials via XPC.
- Credential wait timeout is `30s`.
- Only Swift reads Keychain.
- Only Swift delivers backend credentials via XPC.
- Python reads nothing from Keychain.

#### Security constraints
- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Keychain access is forbidden in Python backend code.

---

### 5. XPC Ready Message

Sent after startup initialization.

#### Type
XPC message/payload

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | Yes | Included in ready message. |
| `capabilities` | array | Yes | Included in ready message. Element type not specified in provided source. |

#### Behavioral constraints
- Sent after:
  1. logger initialization
  2. XPC server start/listen
  3. listening announcement
  4. credentials wait
  5. `GitHubTool` initialization
  6. `ConsensusEngine` initialization
  7. `DocumentStore` background load start
- Startup order is mandatory and must not be changed.

---

### 6. Auth Error XPC Card

Emitted when credential-dependent initialization fails.

#### Type
XPC message/card

#### Defined fields from source
Not fully specified in the provided source.

#### Known identifier
`auth_error`

#### Behavioral constraints
- Errors in step 5 (`GitHubTool` initialization with token) and step 6 (`ConsensusEngine` initialization with API keys) are non-fatal.
- On such credential errors, backend MUST emit an `auth_error` XPC card.
- Backend MUST continue in degraded state.

---

### 7. Agent Action Input

Represents any entry point that processes an agent action.

#### Type
Object/message

#### Required fields inferred from enforcement contracts

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | Yes | CTX-ID validation MUST occur first. Missing `ctx_id` MUST be treated as `UNTRUSTED`. |
| `session_id` | string | Yes | Required indirectly because every TrustFlow event for the action must include it. |
| action payload | object | Yes | Exact field shape not specified. Used to compute `payload_hash` as SHA-256 of serialized action payload. |

#### Behavioral constraints
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted after CTX-ID validation failure.
- Every action MUST be checked against VTZ policy BEFORE execution.

---

### 8. CTX-ID Token

Identity and trust token used for request validation.

#### Type
Opaque token/string

#### Source-defined contract constraints
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is permitted after issuance.
- Rotation creates a new token.
- Old token is invalidated immediately on rotation.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from context when `ctx_id` is missing.

---

### 9. VTZ Session Binding

Binding between agent session and VTZ.

#### Type
Session-level invariant

#### Constraints
- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

### 10. SECURITY_REFUSAL Output Handling

Special LLM output contract.

#### Type
String sentinel in model output

#### Literal
```text
SECURITY_REFUSAL
```

#### Behavioral constraints
- When output contains `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.
- Retrying generation after `SECURITY_REFUSAL` is forbidden.

---

## Enums and Constants

### String Literals

| Name | Value |
|---|---|
| Security refusal sentinel | `SECURITY_REFUSAL` |
| XPC auth error card identifier | `auth_error` |
| VTZ enforcement deny verdict | `block` |
| Missing CTX-ID trust classification | `UNTRUSTED` |
| Listening stdout prefix | `FORGE_AGENT_LISTENING:` |

---

### Startup Sequence Constants

| Name | Value | Type |
|---|---|---|
| Credential wait timeout | `30s` | duration |

---

### Required Startup Order

Must occur exactly in this order:

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background (async)`
8. `Send ready message via XPC (includes agent_version, capabilities)`
9. `Enter CommandRouter event loop`

---

## Validation Rules

### General backend implementation rules
- Python version MUST be `3.12`.
- Type annotations are required on every function.
- Backend MUST use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses are required for all structured data.

---

### Security validation rules
- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log; never retry.

---

### GitHub integration rules
- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

---

### CAL enforcement rules
- Every entry point processing an agent action MUST validate `ctx_id` first.
- CTX-ID validation failure MUST immediately reject the action.
- No partial processing is permitted after CTX-ID validation failure.
- Every action MUST be checked against VTZ policy before execution.
- VTZ denial MUST create `VTZEnforcementDecision` with `verdict=block`.
- Every outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- TrustFlow emission failure MUST NOT silently continue.
- Failure must be logged and surfaced.

---

### TrustFlow validation rules
For every emitted TrustFlow event:
- `event_id` must be unique globally.
- `event_id` must be CSPRNG-generated.
- `event_id` must not be sequential.
- `ts` must be UTC Unix timestamp with millisecond precision.
- `payload_hash` must equal SHA-256 of serialized action payload.
- Emission must be synchronous.
- Async buffering is forbidden.

---

### CTX-ID validation rules
- Token immutability is mandatory.
- Rotation invalidates old token immediately.
- Expired tokens must be rejected.
- Validation must use TrustLock public key.
- Software-only validation is rejected.
- Missing token is `UNTRUSTED`.

---

### VTZ validation rules
- Exactly one VTZ per session at CTX-ID issuance.
- Cross-VTZ calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ enforcement cannot be bypassed by app code.
- Policy changes apply only at next CTX-ID issuance.

---

## Wire Format Examples

Only examples backed by provided source contracts are included.

### Valid: TrustFlow event

```json
{
  "event_id": "2b6a7e92-7d6d-4c0f-b7ec-2a4ab9f7c1d1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4c2af61a7a3c1b8d2c8e"
}
```

Why valid:
- Includes all required fields.
- `ts` is a Unix timestamp in milliseconds.
- `payload_hash` is represented as SHA-256 hex output.
- `event_id` is non-sequential in form.

---

### Invalid: TrustFlow event missing required field

```json
{
  "event_id": "1",
  "session_id": "sess_123",
  "ts": 1735689600,
  "event_type": "block"
}
```

Why invalid:
- Missing `ctx_id`.
- Missing `payload_hash`.
- `event_id` appears sequential/non-CSPRNG.
- `ts` is not millisecond precision as required.

---

### Valid: VTZ enforcement denial record

```json
{
  "verdict": "block"
}
```

Why valid:
- Denial verdict matches required literal exactly.

---

### Invalid: VTZ enforcement denial record

```json
{
  "verdict": "deny"
}
```

Why invalid:
- On VTZ policy denial, `verdict` MUST be `block`.

---

### Valid: XPC listening stdout line

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

Why valid:
- Matches required literal prefix and includes socket path.

---

### Invalid: XPC listening stdout line

```text
LISTENING:/tmp/forge-agent.sock
```

Why invalid:
- Prefix must be exactly `FORGE_AGENT_LISTENING:`.

---

### Invalid: SECURITY_REFUSAL handling pattern

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Why invalid:
- Retrying after `SECURITY_REFUSAL` is explicitly forbidden.

---

### Invalid: Python backend Keychain access

```python
token = KeychainKit.read("github_token")
```

Why invalid:
- Python reads nothing from Keychain.
- Only Swift reads Keychain and delivers via XPC.

---

## Integration Points

### 1. Swift ↔ Backend over XPC
- Swift reads Keychain.
- Swift sends credentials to backend via XPC.
- Backend prints `FORGE_AGENT_LISTENING:{socket_path}` for Swift to discover socket path.
- Backend sends a ready XPC message containing:
  - `agent_version`
  - `capabilities`
- Backend may send an `auth_error` XPC card on non-fatal credential initialization failure.

---

### 2. Backend ↔ GitHubTool
- All GitHub operations MUST go through `GitHubTool`.
- Pipeline code MUST NOT call GitHub API directly.
- `GitHubTool` is initialized with token during startup step 5.

---

### 3. Backend ↔ ConsensusEngine
- `ConsensusEngine` is initialized with API keys during startup step 6.
- Credential errors at this stage are non-fatal and require `auth_error` emission plus degraded-state continuation.

---

### 4. Backend ↔ DocumentStore
- `DocumentStore` loading begins in background during startup step 7.
- This operation is async.
- Application remains responsive while embeddings load.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.

---

### 5. Backend ↔ CommandRouter
- `CommandRouter` event loop begins only after startup steps 1-8 complete in required order.

---

### 6. Enforcement path ↔ TrustFlow
- Every processed agent action must emit a TrustFlow event for outcome.
- Emission is part of the synchronous enforcement path.
- Emission failure must be logged and surfaced.

---

### 7. Enforcement path ↔ CTX-ID / VTZ policy
- `ctx_id` validation is the first operation on every action-processing entry point.
- VTZ policy check occurs before execution.
- Denials produce `VTZEnforcementDecision` with `verdict=block`.

---

## Non-Conformance Conditions

A `ConsensusDevAgent` implementation is non-conformant if any of the following occur:

- Missing CTX-ID validation before processing agent action.
- Partial processing after CTX-ID validation failure.
- VTZ check omitted before execution.
- VTZ denial does not produce `VTZEnforcementDecision` with `verdict=block`.
- TrustFlow event omitted for any action outcome.
- TrustFlow event missing any required field:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- TrustFlow emission performed asynchronously or buffered.
- TrustFlow emission failure silently ignored.
- Missing or altered startup order.
- Ready message sent without `agent_version` and `capabilities`.
- Python backend reads Keychain directly.
- GitHub API is called directly outside `GitHubTool`.
- `SECURITY_REFUSAL` is retried instead of stopped/gated/logged.
- External document context is placed into the SYSTEM prompt.
- File writes occur without `path_security.validate_write_path()`.
- Document chunks are included in prompts without injection scanning.

---

## Notes on Unspecified Fields

The provided source does **not** define complete payload schemas for:
- credentials XPC message
- ready message `capabilities` element structure
- `auth_error` XPC card fields
- action payload field names beyond `ctx_id`/session coupling requirements

These fields must not be invented in implementations claiming TRD conformance without an owning TRD section defining them. Only the fields and literals listed in this document are contractually guaranteed by the provided sources.