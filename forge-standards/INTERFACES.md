# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the required wire-level and integration contracts for the ConsensusDevAgent subsystem based on the provided TRD excerpts and Forge component interface contracts.

Where the source material specifies exact field names or values, they are reproduced exactly.

### 1. TrustFlow Event

Required by the **TrustFlow Emission Contract**.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | MUST be globally unique. MUST be generated using CSPRNG. MUST NOT be sequential. |
| `session_id` | string | yes | Required on every TrustFlow event. |
| `ctx_id` | string | yes | Required on every TrustFlow event. Represents the CTX-ID token or token identifier in use for the action. |
| `ts` | number | yes | MUST be UTC Unix timestamp with millisecond precision. |
| `event_type` | string | yes | Required on every TrustFlow event. |
| `payload_hash` | string | yes | MUST be SHA-256 of the serialized action payload. |

#### Semantics
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be treated as a WARN-level audit event.
- Failed emission MUST NOT silently continue.

---

### 2. VTZEnforcementDecision

Required by the **CAL Enforcement Contract**.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | For VTZ policy denial, MUST be exactly `block`. |

#### Semantics
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 3. CTX-ID Token

Defined by the **CTX-ID Contract** and related CAL requirements.

The exact token field structure is not provided in the source excerpts. The following constraints are mandatory for any CTX-ID representation used on the wire:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | MUST be present for trusted actions. Missing `ctx_id` MUST be treated as `UNTRUSTED`. MUST be immutable once issued. |

#### Semantics
- CTX-ID validation MUST occur FIRST for every entry point that processes an agent action.
- Validation failure MUST result in immediate rejection.
- No partial processing is permitted after validation failure.
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token; the old token is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from surrounding context.

---

### 4. XPC Ready Message

Defined by the **Backend Startup Sequence**.

Sent at step 8:

> Send ready message via XPC (includes agent_version, capabilities)

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | MUST be included in the ready message. |
| `capabilities` | array | yes | MUST be included in the ready message. Element type is not specified in source excerpts. |

---

### 5. XPC Auth Error Card

Defined by the **Backend Startup Sequence**.

When credential initialization fails at startup:

> Steps 5-6 are non-fatal on credential errors — emit `auth_error` XPC card, continue in degraded state.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | string | yes | MUST be exactly `auth_error` if represented by a typed envelope. |

#### Semantics
- Must be emitted when step 5 and/or step 6 encounters credential errors.
- Backend MUST continue in degraded state after emission.

---

### 6. Listening Announcement Line

Defined by the **Backend Startup Sequence**.

Printed to stdout at step 3:

```text
FORGE_AGENT_LISTENING:{socket_path}
```

| Element | Type | Required | Constraints |
|---|---|---:|---|
| `FORGE_AGENT_LISTENING:` | literal string prefix | yes | MUST appear exactly as shown. |
| `{socket_path}` | string | yes | Socket path value appended directly after the prefix. |

#### Wire Form
```text
FORGE_AGENT_LISTENING:/absolute/or/runtime/socket/path
```

---

### 7. Security Refusal Output Marker

Defined by the security rules.

| Field / Value | Type | Required | Constraints |
|---|---|---:|---|
| `SECURITY_REFUSAL` | string | conditional | If present in LLM output, processing MUST stop, gate, and log. MUST NOT retry to bypass. |

#### Semantics
- When `SECURITY_REFUSAL` appears in output:
  - stop
  - gate
  - log
  - never retry to bypass

---

### 8. Action Payload

The source excerpts refer to a serialized action payload for hashing, but do not define the concrete schema.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| action payload | serialized object/blob | yes | `payload_hash` MUST be SHA-256 of the serialized action payload. |

Because the payload schema is not provided, implementations MUST preserve deterministic serialization for hashing within the subsystem.

---

### 9. Capabilities Collection

Referenced by the XPC ready message.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `capabilities` | array | yes | Included in ready message. Exact element schema not provided in source excerpts. |

---

### 10. Session-to-VTZ Binding

Defined by the **VTZ Enforcement Contract**.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | string | yes | Used in TrustFlow event and session scope. |
| `vtz` | implementation-defined | yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance. Exact wire field name not provided in source excerpts. |

#### Semantics
- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

## Enums and Constants

### Literal Values

| Name | Type | Exact Value | Notes |
|---|---|---|---|
| Security refusal marker | string | `SECURITY_REFUSAL` | If seen in output, stop/gate/log; never retry. |
| Auth error card type | string | `auth_error` | XPC card emitted on non-fatal credential errors in startup steps 5-6. |
| VTZ deny verdict | string | `block` | Required in `VTZEnforcementDecision` on VTZ policy denial. |
| Action outcome | string enum | `allow`, `restrict`, `block` | Every action outcome must emit a TrustFlow event. |
| Missing trust classification | string | `UNTRUSTED` | Missing CTX-ID must be treated as `UNTRUSTED`. |
| Stdout listening prefix | string | `FORGE_AGENT_LISTENING:` | Printed before socket path. |

### Process Constants

| Name | Type | Exact Value | Notes |
|---|---|---|---|
| Credential wait timeout | duration | `30s` | Wait for credentials via XPC timeout. |
| Python version | string | `3.12` | Backend language requirement. |
| Required test coverage on new modules | percentage | `85%` | Minimum coverage requirement. |
| Hash algorithm | string | `SHA-256` | Required for `payload_hash`. |
| Timestamp basis | string | `UTC Unix timestamp with millisecond precision` | Required for `ts`. |

### Mandatory Startup Order

These steps are normative and MUST occur in this order:

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

## 1. CAL Enforcement

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur FIRST.
2. CTX-ID validation failure MUST cause immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. VTZ policy check MUST occur BEFORE execution.
5. VTZ denial MUST generate a `VTZEnforcementDecision` with:
   - `verdict = block`
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure:
   - MUST NOT silently continue
   - MUST be logged
   - MUST be surfaced

---

## 2. TrustFlow Event Validation

A TrustFlow event is valid only if all of the following are true:

- `event_id` is present
- `event_id` is globally unique
- `event_id` is CSPRNG-generated
- `event_id` is not sequential
- `session_id` is present
- `ctx_id` is present
- `ts` is present
- `ts` is a UTC Unix timestamp with millisecond precision
- `event_type` is present
- `payload_hash` is present
- `payload_hash` equals the `SHA-256` of the serialized action payload

Emission constraints:

- Emission MUST be synchronous in the enforcement path.
- Async buffering is forbidden.

---

## 3. CTX-ID Validation

A CTX-ID is valid only if:

- it is present when required for trusted processing
- it is validated against TrustLock public key
- it is not expired
- it has not been invalidated by rotation

Additional rules:

- CTX-ID tokens are immutable once issued.
- Rotation MUST create a new token.
- The old token MUST be invalidated immediately.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity inference from context is forbidden.
- Software-only validation is rejected.

---

## 4. VTZ Validation

A VTZ-bound session is valid only if:

- the session is bound to exactly one VTZ at CTX-ID issuance
- tool calls remain within that VTZ unless explicit policy authorization exists

Additional rules:

- cross-VTZ tool calls without explicit authorization MUST be denied
- implicit authorization is denied
- VTZ boundaries cannot be bypassed by application code
- policy changes apply only at next CTX-ID issuance, never mid-session

---

## 5. Startup Sequence Validation

The backend is conformant only if startup occurs in the exact required order.

Additional startup rules:

- Step 5 (`Initialize GitHubTool with token`) is non-fatal on credential errors.
- Step 6 (`Initialize ConsensusEngine with API keys`) is non-fatal on credential errors.
- On such errors, an `auth_error` XPC card MUST be emitted.
- The backend MUST continue in degraded state.
- Step 7 (`Start DocumentStore loading in background (async)`) MUST be asynchronous.
- The application MUST remain responsive while embeddings load.

---

## 6. Security Validation

The following are mandatory security constraints for the subsystem:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on any generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents MUST go in the `USER` prompt, never the `SYSTEM` prompt.
- On `SECURITY_REFUSAL` output:
  - stop
  - gate
  - log
  - never retry to bypass

---

## 7. Backend and Code-Level Requirements Affecting Interfaces

These constraints affect conformant implementation and integration behavior:

- Python must be `3.12`
- Type annotations required on every function
- `async/await` throughout backend
- No blocking calls on the event loop
- Dataclasses for all structured data
- Tests must use `pytest`
- `ruff` must pass clean
- `mypy` must pass clean
- Tests for new modules require coverage `≥ 85%`

---

## 8. GitHub Integration Rule

- All GitHub operations go through `GitHubTool`.
- Pipeline code MUST NOT call the GitHub API directly.

This is an integration contract even where no specific wire payload is defined.

---

## Wire Format Examples

Only fields and values explicitly supported by the provided source excerpts are used below.

### 1. Valid TrustFlow Event

```json
{
  "event_id": "3b1c15d6-9a5c-4d2e-9a38-4c2f8d6a7b11",
  "session_id": "sess_01",
  "ctx_id": "ctx_01",
  "ts": 1735689600123,
  "event_type": "action_executed",
  "payload_hash": "8b7d1a3187ab355dc31bc683aaa71ab5ed217940c12196a9cd5f4ca984babfa4"
}
```

Why valid:
- includes all required TrustFlow fields
- `ts` uses Unix milliseconds form
- `payload_hash` is shaped as SHA-256 hex output

---

### 2. Invalid TrustFlow Event: missing required field

```json
{
  "event_id": "3b1c15d6-9a5c-4d2e-9a38-4c2f8d6a7b11",
  "session_id": "sess_01",
  "ts": 1735689600123,
  "event_type": "action_executed",
  "payload_hash": "8b7d1a3187ab355dc31bc683aaa71ab5ed217940c12196a9cd5f4ca984babfa4"
}
```

Why invalid:
- missing `ctx_id`

---

### 3. Invalid VTZ Enforcement Decision

```json
{
  "verdict": "deny"
}
```

Why invalid:
- for VTZ policy denial, `verdict` MUST be exactly `block`

---

### 4. Valid VTZ Enforcement Decision for Denial

```json
{
  "verdict": "block"
}
```

---

### 5. Valid XPC Ready Message

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
- includes required `agent_version`
- includes required `capabilities`

Note:
- exact capability element schema is not specified in the source excerpts

---

### 6. Valid XPC Auth Error Card

```json
{
  "type": "auth_error"
}
```

---

### 7. Stdout Listening Announcement

```text
FORGE_AGENT_LISTENING:/tmp/forge-consensusdevagent.sock
```

Why valid:
- exact required prefix
- socket path follows immediately after `:`

---

### 8. Invalid Listening Announcement

```text
LISTENING:/tmp/forge-consensusdevagent.sock
```

Why invalid:
- prefix must be exactly `FORGE_AGENT_LISTENING:`

---

### 9. Missing CTX-ID Case

```json
{
  "session_id": "sess_01",
  "action": "run_task"
}
```

Interpretation:
- if `ctx_id` is missing, request MUST be treated as `UNTRUSTED`
- identity MUST NOT be inferred from surrounding context

---

### 10. SECURITY_REFUSAL Handling Case

```json
{
  "llm_output": "SECURITY_REFUSAL"
}
```

Required behavior:
- stop
- gate
- log
- do not retry to bypass

---

## Integration Points

## 1. XPC

ConsensusDevAgent integrates with the Swift side over XPC.

Required integration behaviors:

- XPC server MUST start before credentials are awaited.
- Backend MUST print:
  - `FORGE_AGENT_LISTENING:{socket_path}`
- Backend MUST wait for credentials via XPC with timeout `30s`.
- Backend MUST send a ready message via XPC containing:
  - `agent_version`
  - `capabilities`
- On credential errors during:
  - `Initialize GitHubTool with token`
  - `Initialize ConsensusEngine with API keys`
  
  the backend MUST emit an `auth_error` XPC card and continue in degraded state.

Additional constraints from source:
- Only Swift reads Keychain.
- Only Swift delivers credentials via XPC.
- Python reads nothing from Keychain.

---

## 2. GitHubTool

All GitHub operations integrate through `GitHubTool`.

Required behaviors:

- Initialize `GitHubTool` with token during startup step 5.
- All GitHub operations MUST go through `GitHubTool`.
- Pipeline code MUST NOT call the GitHub API directly.

---

## 3. ConsensusEngine

Startup integration:

- Initialize `ConsensusEngine` with API keys during startup step 6.
- Credential errors at this step are non-fatal.
- On credential error, emit `auth_error` XPC card and continue in degraded state.

---

## 4. DocumentStore

Startup integration:

- `DocumentStore` loading MUST start in background at step 7.
- Loading MUST be async.
- App responsiveness MUST be preserved while embeddings load.

Security integration:

- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- External document context MUST be placed in the `USER` prompt, never the `SYSTEM` prompt.

---

## 5. CommandRouter

Startup integration:

- `CommandRouter` event loop begins only at step 9.
- Startup order before entering the event loop is mandatory.

---

## 6. TrustLock

CTX-ID validation integration:

- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

This is a hard integration dependency for trusted action processing.

---

## 7. Path Security

Disk write integration:

- Every file path written to disk MUST pass `path_security.validate_write_path()` before any write.

No exceptions are defined in the provided excerpts.

---

## 8. Logging / Audit

Required logging-related integration behaviors:

- Logger initialization is startup step 1.
- Failed TrustFlow emission MUST be logged and surfaced.
- Failed TrustFlow emission is a WARN-level audit event.
- HTTP response bodies MUST NOT be logged.
- Only status codes and error types may be logged for HTTP failures.
- `SECURITY_REFUSAL` output MUST be logged as part of stop/gate/log handling.

---

## 9. Testing / Conformance Gates

Integration requirements for development and CI:

- Run existing tests before changes:
  - `cd src && pytest ../tests/ -v --tb=short`
- Tests live in `tests/` and mirror `src/` structure.
- `pytest` required
- `ruff` required
- `mypy` required
- coverage for new modules must be at least `85%`

---

## Non-Specified Fields and Schemas

The provided source excerpts do **not** define full wire schemas for the following. Implementations MUST NOT invent incompatible contracts without updating the owning TRD.

- full agent action request schema
- full CTX-ID token field layout beyond `ctx_id`
- full `VTZEnforcementDecision` schema beyond `verdict`
- TrustFlow `event_type` enumeration
- XPC credential message schema
- XPC ready message capability element schema
- degraded-state status payload schema
- `auth_error` card schema beyond the literal type requirement
- session VTZ field name and serialized structure
- serialized action payload format used before SHA-256 hashing

Where these are needed, the current contract is behavioral and constraint-based rather than fully structural.