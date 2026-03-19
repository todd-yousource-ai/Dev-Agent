# Interface Contracts - ConsensusDevAgent

## Data Structures

This section defines the wire-visible and contract-mandated structures for the ConsensusDevAgent subsystem based on the provided TRD/interface requirements.

### TrustFlowEvent

Required for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | Yes | MUST be globally unique; CSPRNG-generated; MUST NOT be sequential |
| `session_id` | `string` | Yes | Session identifier for the agent session |
| `ctx_id` | `string` | Yes | CTX-ID associated with the action; if missing at input, action is `UNTRUSTED`, but emitted event still MUST include the effective CTX-ID state representation used by the implementation |
| `ts` | `number` | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | Yes | Event type for the enforcement/action outcome |
| `payload_hash` | `string` | Yes | MUST be SHA-256 of the serialized action payload |

#### Notes
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be treated as a WARN-level audit event and MUST NOT be silently skipped.

---

### VTZEnforcementDecision

Required when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | Yes | MUST be exactly `block` |

#### Notes
- A VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### XPCReadyMessage

Sent during backend startup sequence after background document loading has started.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | `string` | Yes | Version string for the running agent |
| `capabilities` | `array` | Yes | List of supported capabilities |

---

### XPCAuthErrorCard

Sent during backend startup sequence when credential initialization fails in degraded mode.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | `string` | Yes | SHOULD identify auth error card type; exact literal not specified in provided source |
| `error` | `string` | No | Human/machine-readable auth error summary if implemented |

#### Notes
- On credential errors in startup steps 5-6, backend MUST emit `auth_error` XPC card and continue in degraded state.
- Exact card schema beyond the `auth_error` designation is not specified in the provided source.

---

### StartupStdoutListeningLine

Line written to stdout during startup.

This is a text wire format, not a JSON object.

| Element | Type | Required | Constraints |
|---|---|---:|---|
| prefix | `string` | Yes | MUST be exactly `FORGE_AGENT_LISTENING:` |
| socket_path | `string` | Yes | Appended directly after the prefix |

Canonical format:

```text
FORGE_AGENT_LISTENING:{socket_path}
```

---

### AgentActionPayload

Serialized action payload used for hashing and enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _implementation-defined_ | _varies_ | Yes | Serialized payload MUST be stable enough to compute SHA-256 for `payload_hash` |

#### Notes
- Exact action payload schema is not specified in the provided source.
- Every entry point that processes an agent action MUST validate CTX-ID first, then check VTZ policy before execution.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### CTXIDToken

Represents CTX-ID contract state. Full token schema is not specified in the provided source, but the following contract requirements are mandatory.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _token value_ | `string` or structured token | Yes | MUST be immutable once issued |
| _expiry_ | implementation-defined | Yes | Expired CTX-ID MUST be rejected |
| _validation key binding_ | implementation-defined | Yes | MUST be validated against TrustLock public key |
| _VTZ binding_ | implementation-defined | Yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance |

#### Notes
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- CTX-ID rotation creates a new token; old token is invalidated immediately.
- Clock skew tolerance is deployment-defined.
- Software-only validation is rejected.

---

### CredentialsViaXPC

Credentials delivered from Swift to backend over XPC.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| _credentials payload_ | implementation-defined | Yes | Backend waits for credentials via XPC with timeout `30s` |

#### Notes
- Only Swift reads Keychain, only to deliver via XPC.
- Python backend reads nothing from Keychain.
- Exact credential field names are not specified in the provided source.

---

## Enums and Constants

### Action Outcome Enum

Every action outcome MUST emit a TrustFlow event with one of these outcomes implied by processing:

- `allow`
- `restrict`
- `block`

### VTZ Verdict Enum

For VTZ denial records:

- `block`

### CTX-ID Identity State

When CTX-ID is absent:

- `UNTRUSTED`

### Security Refusal Sentinel

Literal string:

- `SECURITY_REFUSAL`

Contract:
- When output contains `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.

### Startup Sequence Constants

| Name | Value |
|---|---|
| credentials wait timeout | `30s` |
| listening line prefix | `FORGE_AGENT_LISTENING:` |

### Required Backend Startup Order

Order is mandatory:

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC (timeout: 30s)`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background (async)`
8. `Send ready message via XPC (includes agent_version, capabilities)`
9. `Enter CommandRouter event loop`

### Required Tooling/Implementation Constants

| Name | Value |
|---|---|
| Python version | `3.12` |
| test framework | `pytest` |
| linter | `ruff` |
| type checker | `mypy` |
| minimum coverage on new modules | `85%` |

---

## Validation Rules

### CAL Enforcement Contract

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue; it MUST be logged and surfaced.

### TrustFlow Event Validation

A TrustFlow event is valid only if:

- `event_id` is present and globally unique
- `event_id` is CSPRNG-generated, not sequential
- `session_id` is present
- `ctx_id` is present
- `ts` is present and is a UTC Unix timestamp with millisecond precision
- `event_type` is present
- `payload_hash` is present
- `payload_hash` equals SHA-256 of the serialized action payload

### CTX-ID Validation

A CTX-ID is valid only if:

- It has not been modified after issuance
- It has not expired
- It validates against the TrustLock public key
- It is the currently valid token if rotation has occurred
- It is bound to the session VTZ established at issuance

Additional rules:

- Missing CTX-ID MUST be treated as `UNTRUSTED`
- Expired CTX-ID MUST be rejected
- Old CTX-ID MUST be invalidated immediately on rotation
- Cross-VTZ tool calls are denied unless explicit policy authorization exists

### VTZ Enforcement Validation

- Every agent session MUST be bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit cross-VTZ authorization is denied
- VTZ boundaries cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session

### Startup Validation

- Startup order MUST match the required sequence exactly
- Step 5 (`Initialize GitHubTool with token`) is non-fatal on credential errors
- Step 6 (`Initialize ConsensusEngine with API keys`) is non-fatal on credential errors
- On step 5 or 6 credential error, backend MUST emit `auth_error` XPC card and continue in degraded state
- Step 7 MUST be asynchronous
- Application MUST remain responsive while embeddings load

### Security Validation

- Never hardcode credentials, API keys, tokens, or secrets as string literals
- Never use `shell=True` in subprocess calls
- Never call `eval()` or `exec()` on generated or external content
- Never log HTTP response bodies
- Log status codes and error types only
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt
- Context from external documents MUST go in the USER prompt, never the SYSTEM prompt
- On `SECURITY_REFUSAL`: stop, gate, log; never retry

### GitHub Integration Validation

- All GitHub operations MUST go through `GitHubTool`
- Never call the GitHub API directly from pipeline code

### Python Backend Validation

- Python version MUST be `3.12`
- All functions MUST have type annotations
- Backend MUST use `async/await` throughout
- No blocking calls on the event loop
- All structured data MUST use dataclasses
- Tests MUST use `pytest`
- Tests MUST live in `tests/` and mirror `src/` structure
- `ruff` and `mypy` MUST pass clean
- Test coverage for all new modules MUST be at least `85%`

---

## Wire Format Examples

## Valid payloads

### TrustFlow event

```json
{
  "event_id": "8c2f4c56-7f65-4fd1-a72b-7a3d5d9a7d6e",
  "session_id": "sess-42",
  "ctx_id": "ctx-abc123",
  "ts": 1735689600123,
  "event_type": "action_allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

### VTZ enforcement denial record

```json
{
  "verdict": "block"
}
```

### Ready message over XPC

```json
{
  "agent_version": "1.0.0",
  "capabilities": [
    "github",
    "consensus",
    "documents"
  ]
}
```

### Startup stdout line

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### Auth error indication over XPC

```json
{
  "type": "auth_error",
  "error": "missing GitHub token"
}
```

## Invalid payloads

### Invalid TrustFlow event: sequential/non-unique `event_id`

```json
{
  "event_id": "1",
  "session_id": "sess-42",
  "ctx_id": "ctx-abc123",
  "ts": 1735689600123,
  "event_type": "action_allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8cfa3e704025d4fda3ed0c5ca05468728"
}
```

Reason:
- `event_id` must be globally unique and CSPRNG-generated, not sequential.

### Invalid VTZ denial record: wrong verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- `verdict` must be exactly `block`.

### Invalid startup line: wrong prefix

```text
AGENT_LISTENING:/tmp/forge-agent.sock
```

Reason:
- Prefix must be exactly `FORGE_AGENT_LISTENING:`.

### Invalid handling of security refusal

```json
{
  "llm_output": "SECURITY_REFUSAL",
  "action": "retry_with_different_provider"
}
```

Reason:
- On `SECURITY_REFUSAL`, implementation must stop, gate, and log. Never retry to bypass.

### Invalid backend credential sourcing

```json
{
  "token_source": "Keychain"
}
```

Reason:
- Python backend reads nothing from Keychain.
- Only Swift reads Keychain and delivers credentials via XPC.

---

## Integration Points

### XPC

ConsensusDevAgent integrates with Swift via XPC for:

- credential delivery
- ready notification
- auth error signaling

Required behaviors:

- XPC server starts before credentials are awaited
- credentials are awaited for `30s`
- ready message includes `agent_version` and `capabilities`
- auth failures at GitHubTool or ConsensusEngine initialization emit `auth_error` and continue degraded

### Stdout contract with Swift

Swift reads backend readiness socket path from stdout.

Exact line format:

```text
FORGE_AGENT_LISTENING:{socket_path}
```

### GitHubTool

All GitHub operations integrate exclusively through:

- `GitHubTool`

Direct GitHub API calls from pipeline code are non-conformant.

### ConsensusEngine

ConsensusDevAgent initializes:

- `ConsensusEngine` with API keys

Credential errors are non-fatal at initialization and must produce degraded-mode behavior plus `auth_error` signaling.

### DocumentStore

ConsensusDevAgent starts:

- `DocumentStore` loading in background `(async)`

Contract requirements:

- load starts after `ConsensusEngine` initialization
- load is asynchronous
- app remains responsive while embeddings load
- loaded document chunks must pass injection scanning before inclusion in any LLM prompt

### CommandRouter

After startup completes, backend enters:

- `CommandRouter` event loop

All agent-action entry points in this loop must satisfy:

- CTX-ID validation first
- VTZ policy enforcement before execution
- TrustFlow emission for every outcome

### Path security

All disk write integrations must call:

- `path_security.validate_write_path()`

before any write.

### TrustLock

CTX-ID validation must integrate with:

- TrustLock public key

Software-only validation is rejected.

### Testing and quality gates

Before code changes and for subsystem conformance:

- run existing tests with:
  ```bash
  cd src && pytest ../tests/ -v --tb=short
  ```
- `pytest`, `ruff`, and `mypy` must pass
- new modules require `>= 85%` test coverage