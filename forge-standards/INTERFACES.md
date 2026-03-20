# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements that apply to the `ConsensusDevAgent` subsystem based on the provided TRD/interface material.

Where a field is required by contract text but no enclosing message schema is defined in source, the field set is specified here as a required structure for the relevant record/event.

---

### TrustFlowEvent

Required for every TrustFlow emission in the enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique; MUST be generated via CSPRNG; MUST NOT be sequential |
| `session_id` | `string` | Yes | Required on every TrustFlow event |
| `ctx_id` | `string` | Yes | Required on every TrustFlow event |
| `ts` | `number` | Yes | MUST be a UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | Yes | Required on every TrustFlow event |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload |

#### Semantics
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event and MUST NOT be silently skipped.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### VTZEnforcementDecision

Required output record when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | MUST equal `block` for VTZ policy denial |

#### Semantics
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### ReadyMessage

Sent via XPC during backend startup.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | `string` | Yes | Included in ready message via XPC |
| `capabilities` | `array<string>` | Yes | Included in ready message via XPC |

#### Semantics
- Sent at startup step 8, after background document loading begins.

---

### AuthErrorCard

Sent via XPC on credential initialization failure.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `auth_error` | `object` or `string` | Yes | TRD requires emitting an `auth_error` XPC card; inner structure not specified in provided source |

#### Semantics
- Credential errors in startup steps 5-6 are non-fatal.
- Backend MUST continue in degraded state after emitting `auth_error`.

---

### CredentialDelivery

Credentials received via XPC before backend tool initialization.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `token` | `string` | Conditional | Required to initialize `GitHubTool` |
| `api_keys` | `object` | Conditional | Required to initialize `ConsensusEngine` |

#### Semantics
- Backend waits for credentials via XPC with timeout `30s`.
- Python backend MUST NOT read credentials from Keychain.
- Only Swift reads Keychain, only to deliver credentials via XPC.

---

### ActionPayload

Serialized agent action payload used for enforcement and hashing.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | MUST be validated first at every entry point that processes an agent action |
| `session_id` | `string` | Yes | Required for TrustFlow emission |
| `action` | `object` | Yes | Subject to VTZ policy check before execution |

#### Semantics
- `payload_hash` in TrustFlow events is SHA-256 of the serialized action payload.
- Missing `ctx_id` MUST be treated as `UNTRUSTED`.
- Expired `ctx_id` MUST be rejected.
- CTX-ID validation failure MUST result in immediate rejection with no partial processing.

---

### CTX-ID Token

Opaque trust/identity token validated at action-processing entry points.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | Yes | Token is immutable once issued |

#### Semantics
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is allowed after issuance.
- Rotation creates a new token; the old token is invalidated immediately.
- Validation MUST be against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is deployment-defined and not specified here.

---

### StartupStdoutSignal

Printed to stdout during backend startup.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `message` | `string` | Yes | MUST be exactly `FORGE_AGENT_LISTENING:{socket_path}` |
| `socket_path` | `string` | Yes | Substituted into stdout signal and used by Swift |

#### Semantics
- This is emitted at mandatory startup step 3.
- Format is exact and consumed by Swift.

---

## Enums and Constants

### Enforcement Verdict

Allowed/required values from provided contracts:

| Name | Type | Values |
|---|---|---|
| `verdict` | `string` | `allow`, `restrict`, `block` |

Notes:
- `block` is mandatory for VTZ denial records.
- All action outcomes `allow`, `restrict`, and `block` require TrustFlow emission.

---

### Trust Classification / Missing Identity

| Name | Type | Values |
|---|---|---|
| CTX-ID missing treatment | `string` | `UNTRUSTED` |

---

### Security Refusal Sentinel

| Name | Type | Value |
|---|---|---|
| LLM refusal sentinel | `string` | `SECURITY_REFUSAL` |

Contract:
- When output contains `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.

---

### Startup Timing Constant

| Name | Type | Value |
|---|---|---|
| Credential wait timeout | duration/string | `30s` |

---

### Required Stdout Prefix

| Name | Type | Value |
|---|---|---|
| Listening signal | `string` | `FORGE_AGENT_LISTENING:{socket_path}` |

---

### Logging Constraints

| Name | Type | Value |
|---|---|---|
| HTTP response body logging | policy | forbidden |
| TrustFlow emission failure log level | `string` | `WARN` |

---

### Language / Runtime Constraints

These are implementation-interface requirements affecting conformance:

| Name | Value |
|---|---|
| Python version | `3.12` |
| structured data model | `dataclasses` |
| concurrency model | `async/await` throughout backend |
| tests | `pytest` |
| linter | `ruff` |
| type checker | `mypy` |
| new module coverage minimum | `85%` |

---

## Validation Rules

### 1. Entry Point Enforcement
Every entry point that processes an agent action MUST:

1. Call CTX-ID validation FIRST.
2. Reject immediately on CTX-ID validation failure.
3. Perform VTZ policy check BEFORE execution.
4. Emit a TrustFlow event for every action outcome.

### 2. CTX-ID Rules
- `ctx_id` is required for trusted processing.
- Missing `ctx_id` => treat as `UNTRUSTED`.
- Expired `ctx_id` => reject.
- Validation MUST use TrustLock public key.
- Software-only validation is rejected.
- Token is immutable after issuance.
- Rotation creates a new token and invalidates the old token immediately.

### 3. VTZ Rules
- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

### 4. TrustFlow Rules
For every emitted TrustFlow event:
- `event_id` MUST be globally unique.
- `event_id` MUST use CSPRNG generation.
- `event_id` MUST NOT be sequential.
- `ts` MUST be UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST equal SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Emission failure MUST NOT silently continue.
- Emission failure MUST be logged/surfaced as WARN-level audit event.

### 5. Startup Sequence Rules
Order is mandatory:

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
- On those errors, emit `auth_error` XPC card and continue in degraded state.
- Step 7 is always async.

### 6. Security Rules
- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies; log status codes and error types only.
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log; never retry to bypass.
- All GitHub operations MUST go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

### 7. Keychain / Credential Boundary
- Python reads nothing from Keychain.
- Only Swift reads Keychain.
- Swift may read Keychain only to deliver credentials via XPC.

### 8. Backend Implementation Constraints
- Python `3.12`
- Type annotations on every function.
- `async/await` throughout backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.

---

## Wire Format Examples

## Valid payloads

### TrustFlowEvent
```json
{
  "event_id": "9c2a05d2-3e45-4fd8-bf2e-9e9a3d0e6d77",
  "session_id": "sess_01JABCDEF",
  "ctx_id": "ctx_01JCTX123",
  "ts": 1712345678123,
  "event_type": "action_allow",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

### VTZEnforcementDecision
```json
{
  "verdict": "block"
}
```

### ReadyMessage
```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "document_store"]
}
```

### Startup stdout signal
```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### ActionPayload
```json
{
  "ctx_id": "ctx_01JCTX123",
  "session_id": "sess_01JABCDEF",
  "action": {
    "type": "run_consensus"
  }
}
```

---

## Invalid payloads

### Invalid TrustFlowEvent: sequential/non-unique style identifier
```json
{
  "event_id": "1001",
  "session_id": "sess_01JABCDEF",
  "ctx_id": "ctx_01JCTX123",
  "ts": 1712345678,
  "event_type": "action_allow",
  "payload_hash": "abc"
}
```

Reasons:
- `event_id` appears sequential/non-CSPRNG.
- `ts` is not millisecond precision.
- `payload_hash` is not a valid SHA-256 hex digest.

### Invalid VTZ denial record
```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ policy denial MUST produce `verdict=block`.

### Invalid action payload: missing CTX-ID
```json
{
  "session_id": "sess_01JABCDEF",
  "action": {
    "type": "run_consensus"
  }
}
```

Reason:
- Missing `ctx_id` MUST be treated as `UNTRUSTED`.

### Invalid stdout startup signal
```text
LISTENING:/tmp/forge-agent.sock
```

Reason:
- Must be exactly `FORGE_AGENT_LISTENING:{socket_path}`.

### Invalid security behavior
```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Reason:
- Forbidden. On `SECURITY_REFUSAL`: stop, gate, log. Never retry.

---

## Integration Points

### XPC
The subsystem integrates with Swift over XPC for:
- credential delivery
- ready notification
- auth error signaling

Known XPC payload requirements from provided source:
- credentials are awaited before tool initialization
- ready message includes `agent_version`, `capabilities`
- `auth_error` card is emitted on credential initialization failure

### Stdout
Swift consumes the startup listening signal from stdout:

```text
FORGE_AGENT_LISTENING:{socket_path}
```

### GitHub
- All GitHub operations MUST go through `GitHubTool`.
- Direct GitHub API calls from pipeline code are forbidden.

### Consensus Engine
- Initialized after `GitHubTool`.
- Receives API keys from XPC-delivered credentials.

### DocumentStore
- Loading starts in background asynchronously during startup step 7.
- App must remain responsive while embeddings load.

### CommandRouter
- Event loop begins only after the mandatory startup sequence reaches step 9.

### Filesystem
- Any file write path MUST be validated with `path_security.validate_write_path()` before write.

### LLM Prompt Construction
- All loaded document chunks MUST pass injection scanning before inclusion in prompts.
- External document context MUST be placed in the USER prompt, never the SYSTEM prompt.

### Audit / Enforcement Path
- CTX-ID validation and VTZ enforcement are mandatory before action execution.
- TrustFlow emission is mandatory for every action outcome.
- Emission is synchronous and part of the enforcement path.