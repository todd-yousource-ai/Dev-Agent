# Interface Contracts - ConsensusDevAgent

This document defines the wire format and API contract for the `ConsensusDevAgent` subsystem, based strictly on the provided TRD/interface requirements.

## Data Structures

### TrustFlowEvent

Required for every action outcome (`allow`, `restrict`, `block`).

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | `string` | Yes | Session identifier for the agent session. |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action. Missing `ctx_id` MUST be treated as `UNTRUSTED`; event emission still requires this field, so untrusted handling must occur before processing. |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision. |
| `event_type` | `string` | Yes | Event type for TrustFlow emission. Exact allowed values are not specified in source. |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload. |

#### Notes
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

---

### VTZEnforcementDecision

Required when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | MUST be exactly `block` when produced for VTZ policy denial. |

#### Notes
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### XPCReadyMessage

Sent at backend startup step 8.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | `string` | Yes | Included in ready message via XPC. |
| `capabilities` | `array` | Yes | Included in ready message via XPC. Element type is not specified in source. |

---

### XPCAuthErrorCard

Sent on credential errors during startup steps 5-6.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | `string` | Implied | Exact structure not specified in source. Must represent an `auth_error` XPC card. |

#### Notes
- Steps 5-6 are non-fatal on credential errors.
- System MUST emit `auth_error` XPC card and continue in degraded state.

---

### StartupStdoutListeningSignal

Printed to stdout at backend startup step 3.

This is a line-oriented wire signal, not a JSON object.

| Element | Type | Required | Constraints |
|---|---|---:|---|
| Prefix | `string` | Yes | MUST be exactly `FORGE_AGENT_LISTENING:` |
| `socket_path` | `string` | Yes | Concatenated directly after the prefix. |

Serialized form:

```text
FORGE_AGENT_LISTENING:{socket_path}
```

---

### AgentAction

Represents an action entering an enforcement path.

Exact payload schema is not specified in source, but the following contractually applies:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | MUST be validated FIRST. Validation failure MUST result in immediate rejection and no partial processing. |
| `session_id` | `string` | Yes | Required because every TrustFlow event MUST include `session_id`. |
| `payload` | `object` | Yes | Serialized form is hashed into `payload_hash` using SHA-256. |
| `action` | `string` | Implied | Action subject to VTZ policy enforcement. Exact field name beyond “action” is not specified in source; included here because the contract refers to “agent action”. |

#### Notes
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- Every action MUST be checked against VTZ policy BEFORE execution.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### CTXIDToken

Represents a CTX-ID token.

Exact serialized field layout is not specified in source. The following behavioral contract applies to any implementation:

| Property | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Token identifier/value used for validation. |
| `vtz_binding` | `string` | Implied | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance. |
| `expires_at` | `number` or `string` | Implied | Expired CTX-ID MUST be rejected. Exact timestamp format is not specified in source. |
| `public_key_validation` | `boolean` or implementation-specific | Implied | CTX-ID MUST be validated against TrustLock public key. Software-only validation is rejected. |

#### Notes
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification after issuance.
- CTX-ID rotation creates a new token; the old one is invalidated immediately.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Clock skew tolerance is defined per deployment.

---

## Enums and Constants

### Startup Sequence Constants

#### Stdout Listening Prefix

```text
FORGE_AGENT_LISTENING:
```

#### Credential Wait Timeout

```text
30s
```

Used at startup step 4:

```text
Wait for credentials via XPC (timeout: 30s)
```

---

### Verdict Values

#### VTZEnforcementDecision.verdict

Allowed/required exact value from source:

```text
block
```

---

### Action Outcome Values

Every action outcome must emit a TrustFlow event for the following outcomes:

```text
allow
restrict
block
```

---

### Trust Classification Constant

#### Missing CTX-ID handling

```text
UNTRUSTED
```

---

### XPC Card Type

#### Authentication error card

```text
auth_error
```

---

### Security Refusal Sentinel

```text
SECURITY_REFUSAL
```

#### Contract
- When output contains `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.

---

## Validation Rules

## 1. CAL Enforcement

These rules are mandatory for every entry point that processes an agent action.

1. CTX-ID validation MUST occur FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a `TrustFlowEvent`.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

---

## 2. TrustFlow Emission

1. `event_id` MUST be globally unique.
2. `event_id` MUST use CSPRNG.
3. `event_id` MUST NOT be sequential.
4. `ts` MUST be UTC Unix timestamp with millisecond precision.
5. `payload_hash` MUST be SHA-256 of the serialized action payload.
6. Emission MUST be synchronous in the enforcement path.
7. Async buffering is not permitted.
8. Failed emission is a WARN-level audit event.

---

## 3. CTX-ID

1. CTX-ID tokens are IMMUTABLE once issued.
2. No field modification is allowed after issuance.
3. Rotation MUST create a new token.
4. The old token MUST be invalidated immediately on rotation.
5. Expired CTX-ID MUST be rejected.
6. Missing CTX-ID MUST be treated as `UNTRUSTED`.
7. Identity MUST NEVER be inferred from context when CTX-ID is missing.
8. CTX-ID MUST be validated against TrustLock public key.
9. Software-only validation is rejected.
10. Clock skew tolerance is deployment-defined.

---

## 4. VTZ Enforcement

1. Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
2. Cross-VTZ tool calls require explicit policy authorization.
3. Implicit authorization is denied.
4. VTZ boundaries are structural, not advisory.
5. Enforcement cannot be bypassed by application code.
6. VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

## 5. Backend Startup Sequence

Order is mandatory and MUST NOT be changed.

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
- Steps 5-6 are non-fatal on credential errors.
- On credential errors in steps 5-6, emit `auth_error` XPC card.
- Continue in degraded state after credential error.
- Step 7 is always async.
- App remains responsive while embeddings load.

---

## 6. GitHub Integration

1. All GitHub operations go through `GitHubTool`.
2. Never call the GitHub API directly from pipeline code.

---

## 7. Security Rules Affecting Interface Handling

1. Never hardcode credentials, API keys, tokens, or secrets as string literals.
2. Never use `shell=True` in subprocess calls.
3. Never call `eval()` or `exec()` on generated or external content.
4. Never log HTTP response bodies.
5. Log status codes and error types only.
6. All file paths written to disk must pass `path_security.validate_write_path()` before any write.
7. All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
8. Context from external documents goes in the USER prompt, never the SYSTEM prompt.
9. On `SECURITY_REFUSAL`: stop, gate, log. Never retry.

---

## Wire Format Examples

## 1. Valid TrustFlow Event

```json
{
  "event_id": "8f8a2d2f-7a50-4d4f-9b64-0db7e2d2f6d1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action_outcome",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

Why valid:
- Includes all required fields.
- `ts` is Unix timestamp in milliseconds.
- `payload_hash` is a SHA-256 hex string representation.

---

## 2. Invalid TrustFlow Event: missing required field

```json
{
  "event_id": "8f8a2d2f-7a50-4d4f-9b64-0db7e2d2f6d1",
  "session_id": "sess_123",
  "ts": 1735689600123,
  "event_type": "action_outcome",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

Why invalid:
- Missing `ctx_id`.

---

## 3. Invalid TrustFlow Event: sequential/non-compliant event_id

```json
{
  "event_id": "42",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "action_outcome",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

Why invalid:
- `event_id` MUST be globally unique and MUST NOT be sequential.

---

## 4. Valid VTZ Enforcement Decision

```json
{
  "verdict": "block"
}
```

Why valid:
- Matches required exact value for VTZ policy denial.

---

## 5. Invalid VTZ Enforcement Decision

```json
{
  "verdict": "deny"
}
```

Why invalid:
- Source requires `verdict=block`.

---

## 6. Valid XPC Ready Message

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
- Includes required fields `agent_version` and `capabilities`.

---

## 7. Invalid XPC Ready Message

```json
{
  "agent_version": "1.0.0"
}
```

Why invalid:
- Missing required `capabilities`.

---

## 8. Valid stdout listening signal

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

Why valid:
- Exact required prefix followed by socket path.

---

## 9. Invalid stdout listening signal

```text
LISTENING:/tmp/forge-agent.sock
```

Why invalid:
- Prefix must be exactly `FORGE_AGENT_LISTENING:`.

---

## 10. Invalid processing case: missing CTX-ID

```json
{
  "session_id": "sess_123",
  "payload": {
    "op": "run"
  }
}
```

Why invalid:
- Missing `ctx_id`.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Entry point must reject or gate before partial processing.

---

## 11. Invalid security handling case

```json
{
  "llm_output": "SECURITY_REFUSAL",
  "behavior": "retry_with_another_model"
}
```

Why invalid:
- On `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.

---

## Integration Points

## GitHubTool

Purpose:
- Sole integration point for GitHub operations.

Contract:
- All GitHub operations go through `GitHubTool`.
- Pipeline code MUST NOT call GitHub API directly.

Initialization:
- Startup step 5: initialize `GitHubTool` with token.
- Credential error is non-fatal.
- Emit `auth_error` XPC card on credential error.
- Continue in degraded state.

---

## ConsensusEngine

Purpose:
- Consensus subsystem initialized during startup.

Initialization:
- Startup step 6: initialize `ConsensusEngine` with API keys.
- Credential error is non-fatal.
- Emit `auth_error` XPC card on credential error.
- Continue in degraded state.

---

## DocumentStore

Purpose:
- Background document loading.

Initialization:
- Startup step 7: start `DocumentStore` loading in background.
- This step is always async.
- App remains responsive while embeddings load.

Security constraints:
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- External document context goes in the USER prompt, never the SYSTEM prompt.

---

## XPC Server

Purpose:
- Receives credentials and sends readiness/error signaling.

Contracts:
- Start XPC server at startup step 2.
- Listen on socket.
- Wait for credentials via XPC at startup step 4 with timeout `30s`.
- Send ready message via XPC at startup step 8.
- Ready message includes `agent_version`, `capabilities`.
- Emit `auth_error` XPC card for non-fatal credential errors in steps 5-6.

---

## CommandRouter

Purpose:
- Main event loop entry after startup completes.

Contract:
- Enter `CommandRouter` event loop at startup step 9 only after prior steps execute in required order.

---

## path_security.validate_write_path()

Purpose:
- Required validation before any disk write.

Contract:
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

---

## TrustLock public key validation

Purpose:
- Required CTX-ID validation mechanism.

Contract:
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.

---

## Conformance Notes

A `ConsensusDevAgent` implementation is non-conformant if any of the following occur:

- Entry point processes an action before CTX-ID validation.
- CTX-ID validation failure allows partial processing.
- VTZ policy check occurs after execution.
- VTZ denial does not produce `VTZEnforcementDecision` with `verdict=block`.
- Any action outcome fails to emit a TrustFlow event.
- TrustFlow emission is buffered asynchronously.
- TrustFlow emission failure is silently skipped.
- Missing CTX-ID is inferred from context instead of treated as `UNTRUSTED`.
- CTX-ID is validated without TrustLock public key.
- Cross-VTZ tool call is implicitly allowed.
- Startup sequence order is changed.
- Ready message omits `agent_version` or `capabilities`.
- GitHub API is called directly outside `GitHubTool`.
- File write occurs without `path_security.validate_write_path()`.
- `SECURITY_REFUSAL` is retried to bypass.