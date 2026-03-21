# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements explicitly available from the provided TRD material for the `ConsensusDevAgent` subsystem.

Where the TRDs define behavior but do not define a concrete payload shape, this document records the requirement as a contract-level obligation and does not invent unspecified fields.

---

### TrustFlowEvent

Required by the TrustFlow Emission Contract.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | MUST be globally unique; CSPRNG-generated; MUST NOT be sequential |
| `session_id` | string | yes | Required on every TrustFlow event |
| `ctx_id` | string | yes | Required on every TrustFlow event; MUST correspond to validated CTX-ID |
| `ts` | number | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Required on every TrustFlow event |
| `payload_hash` | string | yes | MUST be SHA-256 of the serialized action payload |

#### Additional contract rules
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

---

### VTZEnforcementDecision

Required by the CAL Enforcement Contract.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | For VTZ policy denial, MUST be exactly `block` |

#### Additional contract rules
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### XPC Ready Message

Sent during backend startup sequence at step 8.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Included in ready message via XPC |
| `capabilities` | array | yes | Included in ready message via XPC; element type not further specified in provided TRDs |

#### Additional contract rules
- Sent only after:
  1. logger initialization
  2. XPC server start
  3. stdout emission of listening line
  4. credential wait
  5. `GitHubTool` initialization attempt
  6. `ConsensusEngine` initialization attempt
  7. `DocumentStore` loading started in background
- Backend must then enter `CommandRouter` event loop.

---

### XPC Auth Error Card

Emitted during backend startup sequence on credential errors for steps 5-6.

No field-level payload schema is defined in the provided TRDs.

#### Additional contract rules
- Must be emitted via XPC on credential errors during:
  - `GitHubTool` initialization with token
  - `ConsensusEngine` initialization with API keys
- These errors are non-fatal.
- Backend MUST continue in degraded state.

---

### Backend Listening Line

Printed to stdout during backend startup sequence at step 3.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | yes | Inserted exactly after `FORGE_AGENT_LISTENING:` |

#### Wire representation
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Additional contract rules
- Must be printed to stdout.
- Swift reads this value.

---

### CTX-ID Token

A concrete field schema is not defined in the provided TRDs, but the following interface constraints are mandatory.

| Property | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes when present in action/event payloads | Missing `ctx_id` MUST be treated as UNTRUSTED |

#### Additional contract rules
- CTX-ID validation MUST occur FIRST at every entry point that processes an agent action.
- CTX-ID validation failure MUST result in immediate rejection with no partial processing.
- CTX-ID tokens are IMMUTABLE once issued.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity must never be inferred from context when CTX-ID is missing.

---

### Agent Action Payload

A concrete wire schema is not defined in the provided TRDs. The following enforcement-dependent requirements apply to any payload treated as an agent action.

| Property | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | effectively required for trusted processing | Must be validated first |
| serialized payload | bytes/string | yes for hashing | Used to compute `payload_hash` as SHA-256 |

#### Additional contract rules
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- Every action MUST be checked against VTZ policy BEFORE execution.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

## Enums and Constants

### Enforcement outcomes

These values are explicitly defined by contract text.

| Name | Value |
|---|---|
| TrustFlow action outcome | `allow` |
| TrustFlow action outcome | `restrict` |
| TrustFlow action outcome | `block` |

### VTZ enforcement verdict

| Name | Value |
|---|---|
| VTZ denial verdict | `block` |

### CTX-ID trust state

| Name | Value |
|---|---|
| Missing CTX-ID treatment | `UNTRUSTED` |

### Startup stdout prefix

| Name | Value |
|---|---|
| Listening line prefix | `FORGE_AGENT_LISTENING:` |

### Security refusal sentinel

| Name | Value |
|---|---|
| LLM refusal marker | `SECURITY_REFUSAL` |

### Logging/audit constants

| Name | Value |
|---|---|
| TrustFlow emission failure log level | `WARN` |

### Language/runtime/tooling requirements

| Name | Value |
|---|---|
| Python version | `3.12` |
| Test runner | `pytest` |
| Linter | `ruff` |
| Type checker | `mypy` |
| Minimum coverage for new modules | `85%` |

### Startup timeout

| Name | Value |
|---|---|
| Credential wait timeout | `30s` |

---

## Validation Rules

## 1. Startup sequence ordering

Order is mandatory and MUST NOT change:

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (async)
8. Send ready message via XPC (includes `agent_version`, `capabilities`)
9. Enter `CommandRouter` event loop

Additional rules:
- Steps 5-6 are non-fatal on credential errors.
- On such errors, emit `auth_error` XPC card and continue in degraded state.
- Step 7 is always async.

---

## 2. CAL enforcement

At every entry point that processes an agent action:

1. CTX-ID validation MUST occur FIRST.
2. On CTX-ID validation failure, processing MUST be immediately rejected.
3. No partial processing is allowed after CTX-ID validation failure.
4. VTZ policy MUST be checked BEFORE execution.
5. VTZ denial MUST produce a `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.

---

## 3. TrustFlow validation

For every TrustFlow event:

- `event_id` MUST be present.
- `event_id` MUST be globally unique.
- `event_id` MUST be CSPRNG-generated.
- `event_id` MUST NOT be sequential.
- `session_id` MUST be present.
- `ctx_id` MUST be present.
- `ts` MUST be a UTC Unix timestamp with millisecond precision.
- `event_type` MUST be present.
- `payload_hash` MUST be present.
- `payload_hash` MUST be the SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.

---

## 4. CTX-ID validation

- CTX-ID tokens are immutable after issuance.
- Rotation MUST create a new token.
- The old token is invalidated immediately upon rotation.
- Expired CTX-ID MUST be rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

---

## 5. VTZ validation

- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

## 6. Security validation

These are hard interface-adjacent constraints for all request/response handling and implementation behavior:

- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on any generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before being included in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- When output contains `SECURITY_REFUSAL`: stop, gate, log. Never retry to bypass.

Forbidden patterns:
- Retrying generation to bypass `SECURITY_REFUSAL`
- Swift force unwrap: `optional!`
- LLM API call from Swift
- Python backend reading from Keychain directly

---

## 7. GitHub integration validation

- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

---

## Wire Format Examples

## Valid payloads

### TrustFlowEvent
```json
{
  "event_id": "3f4b3ad5-3c36-4d6c-a7ef-0e2d0b8d9f13",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action.allow",
  "payload_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd38c7a0b7c6f5f6f2d"
}
```

### VTZEnforcementDecision
```json
{
  "verdict": "block"
}
```

### XPC ready message
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

### Backend listening line
```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

---

## Invalid payloads

### Invalid TrustFlowEvent: missing required field
```json
{
  "event_id": "3f4b3ad5-3c36-4d6c-a7ef-0e2d0b8d9f13",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "payload_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd38c7a0b7c6f5f6f2d"
}
```

Reason: `event_type` is required.

### Invalid TrustFlowEvent: nonconformant timestamp precision/type
```json
{
  "event_id": "3f4b3ad5-3c36-4d6c-a7ef-0e2d0b8d9f13",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": "1735689600",
  "event_type": "action.block",
  "payload_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd38c7a0b7c6f5f6f2d"
}
```

Reason: `ts` must be a UTC Unix timestamp with millisecond precision.

### Invalid VTZEnforcementDecision: wrong denial verdict
```json
{
  "verdict": "deny"
}
```

Reason: for VTZ policy denial, verdict MUST be exactly `block`.

### Invalid backend listening line
```text
LISTENING:/tmp/forge-agent.sock
```

Reason: stdout line must begin exactly with `FORGE_AGENT_LISTENING:`.

### Invalid action processing request context
```json
{
  "session_id": "sess_123",
  "action": "run"
}
```

Reason: missing `ctx_id` must be treated as `UNTRUSTED`; trusted processing must not be inferred from context.

---

## Integration Points

## XPC

Defined interactions from the TRDs:

1. Backend starts XPC server and listens on socket.
2. Backend prints `FORGE_AGENT_LISTENING:{socket_path}` to stdout.
3. Swift reads the socket path.
4. Backend waits for credentials via XPC for `30s`.
5. Backend sends:
   - ready message via XPC containing `agent_version`, `capabilities`
   - `auth_error` XPC card on credential failures for steps 5-6

Constraints:
- Only Swift reads Keychain.
- Swift may deliver credentials via XPC.
- Python reads nothing from Keychain.

---

## GitHubTool

Integration contract:
- All GitHub operations MUST go through `GitHubTool`.
- Pipeline code MUST NOT call GitHub API directly.
- `GitHubTool` is initialized with token during startup step 5.

---

## ConsensusEngine

Integration contract:
- Initialized with API keys during startup step 6.
- Credential errors are non-fatal and must result in `auth_error` XPC card plus degraded-state continuation.

---

## DocumentStore

Integration contract:
- Loading starts in background during startup step 7.
- Loading is async.
- Application remains responsive while embeddings load.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.

---

## CommandRouter

Integration contract:
- Entered at startup step 9.
- Must only begin after ready message is sent at step 8.

---

## Logging and audit

Integration contract:
- TrustFlow events are mandatory for every action outcome.
- Failed TrustFlow emission is a WARN-level audit event.
- HTTP response bodies must never be logged.
- On `SECURITY_REFUSAL`: stop, gate, log; never retry.

---

## File system security

Integration contract:
- Every file path written to disk MUST pass:
  - `path_security.validate_write_path()`

---

## Testing and conformance requirements

- Run existing tests before changes:
  - `cd src && pytest ../tests/ -v --tb=short`
- Tests live in `tests/` and mirror `src/` structure.
- All functions require type annotations.
- Dataclasses are required for all structured data.
- `ruff` and `mypy` must pass clean.
- Test coverage on new modules must be at least `85%`.

---

## Non-specified areas

The provided TRD excerpts do **not** define concrete field schemas for:
- `auth_error` XPC card payload
- CTX-ID token internals
- action request payload body beyond required enforcement properties
- `capabilities` element schema
- `event_type` allowed value set
- degraded-state status payload shape

These fields and payloads MUST NOT be invented without the owning TRD.