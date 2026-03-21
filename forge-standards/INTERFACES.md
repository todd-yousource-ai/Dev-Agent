# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements explicitly present in the provided TRD excerpts for the `ConsensusDevAgent` subsystem and its required integrations.

Where a field is required by contract but no concrete serialization container is specified in source, the requirement is listed as a contract field requirement rather than an inferred transport schema.

---

### TrustFlowEvent

Required for every TrustFlow emission in the enforcement path.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | MUST be globally unique. MUST be generated with CSPRNG. MUST NOT be sequential. |
| `session_id` | string | yes | Required in every TrustFlow event. |
| `ctx_id` | string | yes | Required in every TrustFlow event. Represents the CTX-ID associated with the action/session. |
| `ts` | number | yes | MUST be UTC Unix timestamp with millisecond precision. |
| `event_type` | string | yes | Required in every TrustFlow event. Exact allowed values are not specified in provided source. |
| `payload_hash` | string | yes | MUST be SHA-256 of the serialized action payload. Expected serialized form must be stable within implementation. |

#### Behavioral constraints
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission MUST be a WARN-level audit event.
- Failed emission MUST NOT be a silent skip.
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure.

---

### VTZEnforcementDecision

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | MUST equal `block` when produced for VTZ policy denial. |

#### Behavioral constraints
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### CTX-ID Token

Contract object representing CTX-ID identity and trust binding.

No full field schema is provided in the source excerpts. The following contract requirements apply to any CTX-ID token representation.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | Missing `ctx_id` MUST be treated as `UNTRUSTED`. |
| `vtz_binding` | string | yes | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance. |
| `expiration` | timestamp/date-time/number | yes | Expired CTX-ID MUST be rejected. Clock skew tolerance is deployment-defined. |
| `signature` | bytes/string | yes | CTX-ID MUST be validated against TrustLock public key. Software-only validation is rejected. |

#### Behavioral constraints
- CTX-ID validation MUST occur FIRST at every entry point that processes an agent action.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted after CTX-ID validation failure.
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification is allowed after issuance.
- CTX-ID rotation creates a new token.
- The old token is invalidated immediately.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from surrounding context.

---

### XPC Listening Announcement

Printed to stdout during backend startup.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| stdout line | string | yes | MUST be exactly prefixed as `FORGE_AGENT_LISTENING:{socket_path}` |

#### Format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

| Placeholder | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | yes | Path to the XPC server socket. |

#### Behavioral constraints
- Startup order is mandatory.
- The listening announcement MUST occur after XPC server starts listening on socket.
- Swift reads this stdout line.

---

### XPC Credentials Delivery

Credentials are delivered via XPC from Swift to Python backend.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| credentials payload | object | yes | Concrete fields not specified in provided source. |
| timeout | integer | yes | MUST be `30` seconds for waiting on credentials during startup. |

#### Behavioral constraints
- Backend MUST wait for credentials via XPC.
- Timeout is `30s`.
- Only Swift reads Keychain.
- Python reads nothing from Keychain.
- Swift may deliver credentials via XPC.
- Backend credential initialization errors at steps 5-6 are non-fatal.

---

### XPC Ready Message

Sent via XPC after startup initialization phase.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Included in ready message. Exact format not specified in provided source. |
| `capabilities` | array/string/object | yes | Included in ready message. Exact shape not specified in provided source. |

#### Behavioral constraints
- Ready message is sent after:
  1. logger initialization
  2. XPC server start
  3. stdout listening announcement
  4. credential wait
  5. GitHubTool initialization
  6. ConsensusEngine initialization
  7. DocumentStore background loading start
- CommandRouter event loop begins after ready message is sent.

---

### XPC Auth Error Card

Emitted on credential-related initialization failures for GitHubTool or ConsensusEngine.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| auth error card | object | yes | Exact field schema not specified in provided source. |
| card type | string | implied | Identified in source as `auth_error`. |

#### Behavioral constraints
- Steps 5-6 are non-fatal on credential errors.
- System MUST emit `auth_error` XPC card.
- System MUST continue in degraded state.

---

### Startup Component Interfaces

#### GitHubTool

| Interface | Type | Required | Constraints |
|---|---|---:|---|
| initialization token | string | yes | Initialized with token received via XPC-delivered credentials. |
| usage boundary | behavioral | yes | All GitHub operations go through `GitHubTool`. |
| direct API access | prohibited | yes | Never call the GitHub API directly from pipeline code. |

#### ConsensusEngine

| Interface | Type | Required | Constraints |
|---|---|---:|---|
| API keys | credential set | yes | Initialized with API keys. Exact field names not specified in provided source. |

#### DocumentStore

| Interface | Type | Required | Constraints |
|---|---|---:|---|
| background loading | async operation | yes | MUST start loading in background asynchronously. |

#### CommandRouter

| Interface | Type | Required | Constraints |
|---|---|---:|---|
| event loop | async loop | yes | Entered only after ready message is sent. |

---

### SecurityRefusal Handling Contract

Represents LLM output gating behavior.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| output | string | yes | If output contains `SECURITY_REFUSAL`, special handling is mandatory. |

#### Behavioral constraints
- When `SECURITY_REFUSAL` output is seen: stop, gate, log.
- Never retry to bypass.
- Retrying generation after `SECURITY_REFUSAL` is explicitly forbidden.

---

### Path Write Validation

Required for all file writes.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| file path | string | yes | All file paths written to disk must pass `path_security.validate_write_path()` before any write. |

---

### Injection-Scanned Document Chunk

Required for any loaded document chunk used in prompts.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| document chunk | string/object | yes | Exact chunk schema not specified in provided source. |
| injection scan result | pass/fail | yes | Chunk MUST pass injection scanning before inclusion in any LLM prompt. |

#### Behavioral constraints
- Context from external documents goes in the USER prompt.
- External document context MUST never go in the SYSTEM prompt.

---

## Enums and Constants

### Required literal values

| Name | Type | Value |
|---|---|---|
| Security refusal sentinel | string | `SECURITY_REFUSAL` |
| XPC listening stdout prefix | string | `FORGE_AGENT_LISTENING:` |
| XPC auth error card type | string | `auth_error` |
| VTZ denial verdict | string | `block` |
| Missing CTX-ID trust state | string | `UNTRUSTED` |
| TrustFlow outcome | string | `allow` |
| TrustFlow outcome | string | `restrict` |
| TrustFlow outcome | string | `block` |
| Hash algorithm | string | `SHA-256` |
| Timestamp basis | string | `UTC Unix timestamp with millisecond precision` |
| Credentials wait timeout | integer | `30` |

### Startup order constants

The following sequence is mandatory and ordered:

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

### CAL enforcement
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is permitted after validation failure.
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` with `verdict=block`.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
- TrustFlow emission failure MUST NOT silently continue.
- TrustFlow emission failure MUST be logged and surfaced.

### TrustFlow event validation
- `event_id` MUST be globally unique.
- `event_id` MUST be CSPRNG-generated.
- `event_id` MUST NOT be sequential.
- `ts` MUST be UTC Unix timestamp with millisecond precision.
- `payload_hash` MUST be SHA-256 of the serialized action payload.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.

### CTX-ID validation
- CTX-ID MUST be present or treated as `UNTRUSTED`.
- Expired CTX-ID MUST be rejected.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- CTX-ID fields MUST NOT be modified after issuance.
- Rotation MUST create a new token.
- Previous token MUST be invalidated immediately on rotation.

### VTZ validation
- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance.
- VTZ policy changes do not apply mid-session.

### Security validation
- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file write paths MUST pass `path_security.validate_write_path()` before write.
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- External document context MUST be placed in the USER prompt.
- External document context MUST never be placed in the SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log. Never retry.

### Python/backend implementation constraints
- Python version: `3.12`
- Type annotations required on every function.
- `async/await` throughout backend.
- No blocking calls on the event loop.
- Dataclasses for all structured data.
- Tests use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage must be `≥ 85%` on all new modules.

### GitHub integration validation
- All GitHub operations MUST go through `GitHubTool`.
- Pipeline code MUST NOT call the GitHub API directly.

### Credential handling validation
- Only Swift reads Keychain.
- Swift may deliver credentials via XPC.
- Python backend reads nothing from Keychain.
- Credential errors in GitHubTool/ConsensusEngine initialization are non-fatal.
- On those errors, emit `auth_error` XPC card and continue in degraded state.

---

## Wire Format Examples

Only formats explicitly defined in source are shown as concrete wire examples. For contract-only records whose full serialized schema is not present in source, examples are illustrative minimum-conformance objects.

### Valid: stdout listening announcement

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### Invalid: stdout listening announcement, wrong prefix

```text
FORGE_LISTENING:/tmp/forge-agent.sock
```

Reason:
- Must begin exactly with `FORGE_AGENT_LISTENING:`

---

### Valid: minimum TrustFlow event object

```json
{
  "event_id": "a2f6d1d2-2d5b-4f3a-8d96-1d97f3c7b5aa",
  "session_id": "sess-123",
  "ctx_id": "ctx-456",
  "ts": 1712345678123,
  "event_type": "action_outcome",
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa13514a8afa2f4d3eebbdb5e5d5d6bc"
}
```

Reason:
- Includes all required TrustFlow fields.
- `ts` is millisecond Unix time.
- `payload_hash` is SHA-256 formatted as hex string.

### Invalid: TrustFlow event missing required field

```json
{
  "event_id": "1",
  "session_id": "sess-123",
  "ts": 1712345678,
  "event_type": "action_outcome"
}
```

Reasons:
- Missing `ctx_id`
- Missing `payload_hash`
- `event_id` appears sequential/non-CSPRNG
- `ts` does not demonstrate millisecond precision

---

### Valid: VTZ enforcement denial record

```json
{
  "verdict": "block"
}
```

### Invalid: VTZ enforcement denial record

```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ denial record must use exact value `block`

---

### Valid: ready message minimum shape

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus"]
}
```

Notes:
- Exact `capabilities` schema is not specified in provided source.
- This example only demonstrates required presence of `agent_version` and `capabilities`.

### Invalid: ready message missing capabilities

```json
{
  "agent_version": "1.0.0"
}
```

Reason:
- Ready message must include `agent_version, capabilities`

---

### Valid: auth error card minimum shape

```json
{
  "type": "auth_error"
}
```

Notes:
- Exact field schema for the XPC card is not specified in provided source.
- `auth_error` is the exact literal named by the contract.

### Invalid: auth error card wrong type

```json
{
  "type": "authentication_error"
}
```

Reason:
- Exact literal in source is `auth_error`

---

### Invalid: SECURITY_REFUSAL bypass pattern

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Reason:
- Explicitly forbidden
- Required behavior is stop, gate, log
- Never retry to bypass

---

### Invalid: direct GitHub API call from pipeline code

```python
await http_client.get("https://api.github.com/repos/org/repo")
```

Reason:
- All GitHub operations must go through `GitHubTool`

---

### Invalid: Keychain read in Python backend

```python
token = keychain.read("github_token")
```

Reason:
- Python reads nothing from Keychain
- Only Swift reads Keychain, only to deliver via XPC

---

## Integration Points

### Swift ↔ Python backend via XPC
- Swift reads Keychain.
- Swift delivers credentials via XPC.
- Python backend waits up to `30s` for credentials via XPC during startup.
- Python backend emits ready message via XPC with:
  - `agent_version`
  - `capabilities`
- Python backend emits `auth_error` XPC card on non-fatal credential initialization failure.

### Stdout signaling to Swift
- Backend MUST print `FORGE_AGENT_LISTENING:{socket_path}` to stdout.
- Swift consumes this signal to discover the socket path.

### GitHub integration
- All GitHub operations route through `GitHubTool`.
- No direct GitHub API calls from pipeline code are permitted.

### Consensus engine initialization
- `ConsensusEngine` initializes with API keys.
- Credential errors are non-fatal during startup and must degrade gracefully via `auth_error`.

### Document ingestion and prompting
- `DocumentStore` loading starts asynchronously in background.
- Loaded document chunks must pass injection scanning before use in prompts.
- External document context must be placed in USER prompt only.

### Trust/Policy enforcement path
- Entry point receives agent action.
- CTX-ID validation occurs first.
- VTZ policy check occurs before execution.
- On denial, produce `VTZEnforcementDecision` with `verdict=block`.
- On every outcome (`allow`, `restrict`, `block`), emit synchronous TrustFlow event.
- Emission failure must be logged and surfaced, not silently skipped.

### Filesystem writes
- Before any disk write, path must be validated with `path_security.validate_write_path()`.

### Testing/tooling integration
- Existing tests must be run before changes:

```bash
cd src && pytest ../tests/ -v --tb=short
```

- Tests use `pytest`.
- Linting uses `ruff`.
- Type checking uses `mypy`.

---