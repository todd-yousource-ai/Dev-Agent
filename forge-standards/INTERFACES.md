# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements for the `ConsensusDevAgent` subsystem from the provided TRD and interface contract excerpts.

Where the source specifies mandatory behavior without an explicit payload schema, this document records the required fields, values, ordering, and constraints exactly as stated.

---

### 1. Startup stdout signal

#### `FORGE_AGENT_LISTENING` line

Backend startup MUST print the following line to stdout at startup step 3:

```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Fields

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | string | yes | Interpolated into the exact prefix `FORGE_AGENT_LISTENING:` with no altered spelling |

#### Constraints
- Emitted at startup step `3`.
- Must occur after:
  1. `Initialize logger`
  2. `Start XPC server, listen on socket`
- Must occur before:
  4. `Wait for credentials via XPC (timeout: 30s)`

---

### 2. XPC credential wait contract

#### Credential wait timeout

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `timeout` | integer | yes | Must be `30` seconds |

#### Constraints
- Backend MUST wait for credentials via XPC.
- Timeout value is exactly `30s`.

---

### 3. XPC ready message

At startup step 8, backend MUST send a ready message via XPC.

#### Ready message

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | yes | Must be included in ready message |
| `capabilities` | array | yes | Must be included in ready message |

#### Constraints
- Ready message is sent only after:
  - `Start DocumentStore loading in background (async)`
- Ready message is sent before:
  - `Enter CommandRouter event loop`

---

### 4. XPC auth error card

If credential errors occur during startup steps 5 or 6, backend MUST emit an auth error card via XPC and continue in degraded state.

#### Auth error card

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | string | implied | Value must be `auth_error` |

#### Constraints
- Applies to:
  - `Initialize GitHubTool with token`
  - `Initialize ConsensusEngine with API keys`
- Credential errors in steps 5-6 are non-fatal.
- Backend MUST continue in degraded state.

---

### 5. TrustFlow event

Every action outcome must emit a TrustFlow event.

#### TrustFlow event payload

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | Must be globally unique; CSPRNG, not sequential |
| `session_id` | string | yes | Required |
| `ctx_id` | string | yes | Required |
| `ts` | number | yes | Must be UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Required |
| `payload_hash` | string | yes | Must be SHA-256 of the serialized action payload |

#### Constraints
- Every TrustFlow event MUST include exactly the required fields listed above.
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- TrustFlow emission failure must not silently continue; log and surface the failure.

---

### 6. VTZ enforcement decision record

A VTZ policy denial MUST produce a `VTZEnforcementDecision` record.

#### `VTZEnforcementDecision`

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | Must equal `block` for VTZ policy denial |

#### Constraints
- Produced only when VTZ policy denies an action.
- Denial check must occur before execution.

---

### 7. CTX-ID token contract

The source defines lifecycle and validation requirements for CTX-ID tokens.

#### `CTX-ID` token

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | Required for trusted processing |

#### Constraints
- CTX-ID tokens are immutable once issued.
- No field modification after issuance.
- Rotation creates a new token.
- Old token is invalidated immediately on rotation.
- Expired CTX-ID must be rejected.
- Validation must be against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must never be inferred from context when CTX-ID is missing.

---

### 8. Agent action processing contract

Every entry point that processes an agent action is subject to CAL enforcement.

#### Agent action input

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | Validation must occur first |
| `action` | object | yes | Subject to VTZ policy check before execution |

#### Constraints
- CTX-ID validation MUST occur first.
- CTX-ID validation failure MUST result in immediate rejection.
- No partial processing is allowed after validation failure.
- Every action MUST be checked against VTZ policy before execution.
- Every action outcome must emit a TrustFlow event with outcome `allow`, `restrict`, or `block`.

---

### 9. Action payload hashing input

The payload hash is defined over the serialized action payload.

#### Serialized action payload

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `serialized_action_payload` | string/bytes | yes | Input to SHA-256 for `payload_hash` |

#### Constraints
- `payload_hash` MUST equal SHA-256 of the serialized action payload.

---

### 10. Agent session VTZ binding

#### Session VTZ binding

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | string | yes | Session identifier |
| `vtz` | string | yes | Every agent session is bound to exactly one VTZ at CTX-ID issuance |

#### Constraints
- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit cross-VTZ access is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

---

### 11. Security refusal output sentinel

The source defines `SECURITY_REFUSAL` as a control sentinel.

#### Security refusal marker

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `output` | string | yes | If it contains `SECURITY_REFUSAL`, processing must stop |

#### Constraints
- When `SECURITY_REFUSAL` appears in output: stop, gate, log.
- Never retry to bypass.
- Retrying generation after detecting `SECURITY_REFUSAL` is explicitly forbidden.

---

### 12. GitHub operation integration boundary

#### `GitHubTool` usage contract

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `token` | string | yes | Used to initialize `GitHubTool` |
| `github_operation` | object | yes | Must go through `GitHubTool` |

#### Constraints
- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

---

### 13. DocumentStore startup loading contract

#### Background loading task

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `document_store_loading` | string | yes | Must be started in background |
| `async` | boolean | yes | Must be `true` |

#### Constraints
- Step 7 is always async.
- App must remain responsive while embeddings load.

---

### 14. File write path validation input

#### Write path validation

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `path` | string | yes | Must pass `path_security.validate_write_path()` before any write |

#### Constraints
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

---

### 15. Loaded document chunk prompt inclusion contract

#### Document chunk input

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `document_chunk` | string | yes | Must pass injection scanning before prompt inclusion |
| `prompt_role` | string | yes | External document context must be placed in `USER` prompt, never `SYSTEM` |

#### Constraints
- All loaded document chunks must pass injection scanning before being included in any LLM prompt.
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.

---

## Enums and Constants

### Startup sequence step numbers

| Name | Type | Value |
|---|---|---|
| `STARTUP_STEP_LOGGER` | integer | `1` |
| `STARTUP_STEP_XPC_SERVER` | integer | `2` |
| `STARTUP_STEP_PRINT_LISTENING` | integer | `3` |
| `STARTUP_STEP_WAIT_CREDENTIALS` | integer | `4` |
| `STARTUP_STEP_INIT_GITHUBTOOL` | integer | `5` |
| `STARTUP_STEP_INIT_CONSENSUSENGINE` | integer | `6` |
| `STARTUP_STEP_START_DOCUMENTSTORE` | integer | `7` |
| `STARTUP_STEP_SEND_READY` | integer | `8` |
| `STARTUP_STEP_COMMANDROUTER_LOOP` | integer | `9` |

### String constants

| Name | Type | Value |
|---|---|---|
| `LISTENING_PREFIX` | string | `FORGE_AGENT_LISTENING:` |
| `SECURITY_REFUSAL` | string | `SECURITY_REFUSAL` |
| `AUTH_ERROR_TYPE` | string | `auth_error` |
| `UNTRUSTED` | string | `UNTRUSTED` |
| `VTZ_VERDICT_BLOCK` | string | `block` |
| `PROMPT_ROLE_USER` | string | `USER` |
| `PROMPT_ROLE_SYSTEM` | string | `SYSTEM` |
| `WARN_LEVEL` | string | `WARN` |

### Outcome enum

| Value |
|---|
| `allow` |
| `restrict` |
| `block` |

### Timing constants

| Name | Type | Value |
|---|---|---|
| `CREDENTIAL_WAIT_TIMEOUT_SECONDS` | integer | `30` |

### Hash algorithm

| Name | Type | Value |
|---|---|---|
| `PAYLOAD_HASH_ALGORITHM` | string | `SHA-256` |

### Timestamp format

| Name | Type | Value |
|---|---|---|
| `TRUSTFLOW_TS_FORMAT` | string | `UTC Unix timestamp with millisecond precision` |

---

## Validation Rules

### Startup ordering
The following order is mandatory and must not be changed:

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC (timeout: 30s)`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background (async)`
8. `Send ready message via XPC (includes agent_version, capabilities)`
9. `Enter CommandRouter event loop`

### Credential initialization behavior
- Steps 5-6 are non-fatal on credential errors.
- On such errors, emit `auth_error` XPC card.
- Continue in degraded state.

### CAL enforcement
- Every entry point that processes an agent action must call CTX-ID validation first.
- CTX-ID validation failure must cause immediate rejection.
- No partial processing is permitted before rejection.
- Every action must be checked against VTZ policy before execution.
- VTZ denial must produce `VTZEnforcementDecision` with `verdict=block`.
- Every outcome must emit a TrustFlow event.
- TrustFlow emission failure must not silently continue.

### TrustFlow validation
- `event_id` must be globally unique.
- `event_id` must be generated using CSPRNG, not sequential generation.
- `ts` must be UTC Unix timestamp with millisecond precision.
- `payload_hash` must be SHA-256 of the serialized action payload.
- Emission must be synchronous in the enforcement path.
- Async buffering is not allowed.
- Failed emission is a WARN-level audit event.

### CTX-ID validation
- Missing `ctx_id` => treat as `UNTRUSTED`.
- Expired CTX-ID => reject.
- Validation must use TrustLock public key.
- Software-only validation is rejected.
- CTX-ID is immutable after issuance.
- Rotation creates a new token and invalidates the old one immediately.

### VTZ validation
- Session must be bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- If authorization is implicit or absent, deny.
- VTZ policy changes do not apply mid-session; they apply at next CTX-ID issuance.

### Security validation
- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Never use `shell=True` in subprocess calls.
- Never call `eval()` or `exec()` on generated or external content.
- Never log HTTP response bodies.
- Log status codes and error types only.
- All file write paths must pass `path_security.validate_write_path()` before write.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.
- External document context must go in `USER` prompt, never `SYSTEM`.
- If `SECURITY_REFUSAL` appears in output: stop, gate, log. Never retry to bypass.

### Python/backend implementation requirements
- Python version: `3.12`
- Type annotations required on every function.
- `async/await` throughout backend.
- No blocking calls on event loop.
- Dataclasses for all structured data.
- Tests use `pytest`.
- Linting uses `ruff`.
- Type checking uses `mypy`.
- Test coverage must be `>= 85%` on all new modules.

---

## Wire Format Examples

### Valid: startup stdout line

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### Invalid: wrong listening prefix

```text
FORGE_LISTENING:/tmp/forge-agent.sock
```

Reason:
- Prefix must be exactly `FORGE_AGENT_LISTENING:`.

---

### Valid: XPC ready message

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

### Invalid: missing required ready field

```json
{
  "agent_version": "1.0.0"
}
```

Reason:
- `capabilities` is required.

---

### Valid: auth error XPC card

```json
{
  "type": "auth_error"
}
```

### Invalid: wrong auth error type

```json
{
  "type": "authentication_error"
}
```

Reason:
- Required value is exactly `auth_error`.

---

### Valid: TrustFlow event

```json
{
  "event_id": "5d4a8d8b-9ec0-4f16-8d28-4f6f4f5df2c1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

### Invalid: sequential/noncompliant TrustFlow event

```json
{
  "event_id": "42",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600,
  "event_type": "block",
  "payload_hash": "abc"
}
```

Reasons:
- `event_id` must be globally unique and CSPRNG, not sequential.
- `ts` must be UTC Unix timestamp with millisecond precision.
- `payload_hash` must be SHA-256 of the serialized action payload.

---

### Valid: VTZ enforcement decision

```json
{
  "verdict": "block"
}
```

### Invalid: wrong VTZ denial verdict

```json
{
  "verdict": "deny"
}
```

Reason:
- VTZ policy denial must produce `VTZEnforcementDecision` with `verdict=block`.

---

### Valid: agent action processing input

```json
{
  "ctx_id": "ctx_abc",
  "action": {
    "name": "open_pull_request"
  }
}
```

### Invalid: missing CTX-ID

```json
{
  "action": {
    "name": "open_pull_request"
  }
}
```

Reason:
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Trusted processing must not infer identity from context.

---

### Valid: external document context placement

```json
{
  "document_chunk": "Repository policy excerpt...",
  "prompt_role": "USER"
}
```

### Invalid: external document context in system prompt

```json
{
  "document_chunk": "Repository policy excerpt...",
  "prompt_role": "SYSTEM"
}
```

Reason:
- External document context goes in `USER` prompt, never `SYSTEM`.

---

### Invalid: forbidden SECURITY_REFUSAL retry behavior

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Reason:
- When `SECURITY_REFUSAL` appears: stop, gate, log.
- Never retry to bypass.

---

### Invalid: forbidden direct GitHub API usage from pipeline code

```python
# direct GitHub API call from pipeline code
```

Reason:
- All GitHub operations must go through `GitHubTool`.

---

## Integration Points

### XPC
Used for:
- credential delivery
- ready message delivery
- auth error card delivery

Required interactions:
1. Backend starts XPC server and listens on socket.
2. Backend prints `FORGE_AGENT_LISTENING:{socket_path}` to stdout.
3. Backend waits for credentials via XPC for `30s`.
4. Backend sends ready message via XPC with:
   - `agent_version`
   - `capabilities`
5. On credential errors in startup steps 5-6, backend emits `auth_error` card via XPC.

### GitHubTool
- All GitHub operations must route through `GitHubTool`.
- `GitHubTool` is initialized with `token`.
- Direct GitHub API access from pipeline code is forbidden.

### ConsensusEngine
- Initialized with API keys at startup step 6.
- Credential errors are non-fatal and result in degraded state plus `auth_error` signaling.

### DocumentStore
- Loading starts at startup step 7.
- Loading must run in background asynchronously.
- Application remains responsive while embeddings load.

### CommandRouter
- Event loop begins only at startup step 9.
- Must start after ready message is sent.

### TrustFlow
- Every action outcome must emit a TrustFlow event.
- Emission is synchronous in the enforcement path.
- Failure must be logged and surfaced as WARN-level audit behavior.

### TrustLock
- CTX-ID validation must be against TrustLock public key.
- Software-only validation is rejected.

### VTZ policy engine
- Every action is checked against VTZ policy before execution.
- VTZ denial produces `VTZEnforcementDecision` with `verdict=block`.
- Cross-VTZ tool calls require explicit policy authorization.

### Path security
- Every file path written to disk must pass `path_security.validate_write_path()` before write.

### Prompt construction / LLM safety
- All loaded document chunks must pass injection scanning before inclusion in prompts.
- External content must be inserted into `USER` prompt only.
- `SECURITY_REFUSAL` must terminate the action path: stop, gate, log, no retry.