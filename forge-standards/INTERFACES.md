# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the wire-format and API contract requirements explicitly stated for the `ConsensusDevAgent` subsystem from the provided TRD/interface sources.

Where a structure is required by contract but its full field schema is not provided in source, this document lists only fields and constraints explicitly present in source and marks the remainder as unspecified.

### 1. TrustFlowEvent

Required for every action outcome.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | `string` | yes | MUST be globally unique; CSPRNG-generated; MUST NOT be sequential |
| `session_id` | `string` | yes | Required on every TrustFlow event |
| `ctx_id` | `string` | yes | Required on every TrustFlow event; MUST represent the validated CTX-ID |
| `ts` | `number` | yes | MUST be UTC Unix timestamp with millisecond precision |
| `event_type` | `string` | yes | Required on every TrustFlow event |
| `payload_hash` | `string` | yes | MUST be SHA-256 of the serialized action payload |

#### Semantics
- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event, not a silent skip.
- Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.

---

### 2. VTZEnforcementDecision

Produced when VTZ policy denies an action.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | `string` | yes | MUST equal `block` when VTZ policy denial occurs |

#### Semantics
- Every action MUST be checked against VTZ policy BEFORE execution.
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.

---

### 3. XPCListeningAnnouncement

Printed to stdout during backend startup.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `socket_path` | `string` | yes | Inserted into the exact stdout format below |

#### Wire representation
Not JSON. Exact stdout line:

```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Semantics
- This MUST occur after XPC server startup and listen binding.
- Swift reads this exact line from stdout.

---

### 4. CredentialWaitPhase

Backend waits for credentials delivered via XPC.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `timeout_seconds` | `integer` | yes | MUST equal `30` |

#### Semantics
- Credentials are received via XPC.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

---

### 5. ReadyMessage

Sent via XPC after initialization sequence reaches ready state.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | `string` | yes | Included in ready message |
| `capabilities` | `array` | yes | Included in ready message; element type unspecified in source |

#### Semantics
- Sent after:
  1. logger initialization
  2. XPC server start
  3. stdout listening announcement
  4. credential wait
  5. `GitHubTool` initialization
  6. `ConsensusEngine` initialization
  7. `DocumentStore` loading started in background
- Backend then enters `CommandRouter` event loop.

---

### 6. AuthErrorCard

Emitted via XPC on credential-related initialization failure.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `type` | `string` | implied | MUST represent `auth_error` card type if encoded as a typed message |

#### Semantics
- Steps 5 and 6 in startup are non-fatal on credential errors.
- On such errors, emit `auth_error` XPC card and continue in degraded state.

> Note: Only the literal card name `auth_error` is specified by source. No additional fields are defined in provided material.

---

### 7. ActionPayload

Serialized payload of an agent action for hashing and enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `(serialized payload)` | `bytes` or `string` | yes | The exact serialized action payload used to compute `payload_hash` |

#### Semantics
- `payload_hash` in `TrustFlowEvent` MUST be SHA-256 of this serialized payload.
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST.
- Every action MUST be checked against VTZ policy BEFORE execution.

> Full action field schema is not provided in source.

---

### 8. CTX-ID Token

Identity/context token used for enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | `string` | yes | Required wherever a TrustFlow event is emitted and wherever action processing occurs |

#### Semantics
- CTX-ID tokens are IMMUTABLE once issued.
- No field modification after issuance.
- Rotation creates a new token; the old one is invalidated immediately.
- Expired CTX-ID MUST be rejected.
- Clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID MUST be treated as `UNTRUSTED`.
- Identity MUST never be inferred from context when CTX-ID is missing.

> Internal token fields beyond `ctx_id` are not specified in provided source.

---

### 9. Agent Session VTZ Binding

Session-to-zone binding required for enforcement.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | `string` | yes | Session identifier |
| `vtz` | `string` | yes | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance |

#### Semantics
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural, not advisory.
- Enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session.

---

### 10. ExternalDocumentChunk

Loaded document content used in prompting.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `content` | `string` | yes | All loaded document chunks must pass injection scanning before inclusion in any LLM prompt |

#### Semantics
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- All loaded document chunks must pass injection scanning before being included in any LLM prompt.

> Additional chunk metadata fields are not specified in provided source.

---

### 11. FileWriteRequest

Any path written to disk.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `path` | `string` | yes | MUST pass `path_security.validate_write_path()` before any write |

#### Semantics
- Validation MUST occur before any write operation.

---

## Enums and Constants

### Literal Strings

The following exact values are specified and MUST be used exactly as shown.

#### Security / control literals
- `SECURITY_REFUSAL`
- `UNTRUSTED`

#### Startup / XPC literals
- `FORGE_AGENT_LISTENING:{socket_path}`
- `auth_error`

#### Enforcement verdict literals
- `block`

#### Outcome literals
- `allow`
- `restrict`
- `block`

#### Logging level literal
- `WARN`

---

### Numeric Constants

| Name | Type | Value | Notes |
|---|---|---:|---|
| `credential_timeout_seconds` | `integer` | `30` | Wait for credentials via XPC timeout |
| `python_version` | `string` | `3.12` | Python requirement |
| `minimum_test_coverage_percent` | `integer` | `85` | On all new modules |

---

### Ordered Startup Sequence

Order is mandatory and MUST NOT be changed.

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

### Tooling / Component Names

These names are contractually significant:

- `GitHubTool`
- `ConsensusEngine`
- `DocumentStore`
- `CommandRouter`
- `TrustFlow`
- `TrustLock`
- `CTX-ID`
- `VTZ`
- `VTZEnforcementDecision`

---

## Validation Rules

### 1. CAL Enforcement

For every entry point that processes an agent action:

1. CTX-ID validation MUST occur FIRST.
2. CTX-ID validation failure MUST result in immediate rejection.
3. No partial processing is permitted after CTX-ID validation failure.
4. Every action MUST be checked against VTZ policy BEFORE execution.
5. VTZ policy denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event.
7. TrustFlow emission failure MUST NOT silently continue.
8. TrustFlow emission failure MUST be logged and surfaced.

---

### 2. TrustFlow Event Validation

A TrustFlow event is valid only if:

- `event_id` is present.
- `event_id` is globally unique.
- `event_id` is generated with CSPRNG.
- `event_id` is not sequential.
- `session_id` is present.
- `ctx_id` is present.
- `ts` is present.
- `ts` is a UTC Unix timestamp with millisecond precision.
- `event_type` is present.
- `payload_hash` is present.
- `payload_hash` equals SHA-256 of the serialized action payload.

Operational rules:

- Emission MUST be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.

---

### 3. CTX-ID Validation

A CTX-ID is valid only if:

- It is present, or else the request is treated as `UNTRUSTED`.
- It is not expired.
- It validates against the TrustLock public key.
- Validation is not software-only.
- It has not been invalidated by rotation.

Additional rules:

- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- The old token is invalidated immediately.
- Missing CTX-ID MUST never cause identity inference from context.

---

### 4. VTZ Enforcement Validation

- Every agent session MUST be bound to EXACTLY ONE VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ enforcement cannot be bypassed by application code.
- VTZ policy changes apply at NEXT CTX-ID issuance, not mid-session.

---

### 5. Security Validation

#### LLM refusal handling
- When output contains `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass.
- Retrying with another LLM call after `SECURITY_REFUSAL` is forbidden.

#### Credentials and secrets
- Never hardcode credentials, API keys, tokens, or secrets as string literals.
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

#### Process execution
- Never use `shell=True` in subprocess calls.

#### Code execution
- Never call `eval()` or `exec()` on generated or external content.

#### HTTP logging
- Never log HTTP response bodies.
- Log status codes and error types only.

#### File write paths
- All file paths written to disk MUST pass `path_security.validate_write_path()` before any write.

#### External content into prompts
- All loaded document chunks MUST pass injection scanning before inclusion in any LLM prompt.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

---

### 6. GitHub Integration Validation

- All GitHub operations go through `GitHubTool`.
- Never call the GitHub API directly from pipeline code.

---

### 7. Python/Implementation Constraints

- Python version MUST be `3.12`.
- Type annotations are required on every function.
- Backend code MUST use `async/await` throughout.
- No blocking calls on the event loop.
- Dataclasses are required for all structured data.
- Tests MUST use `pytest`.
- Tests live in `tests/` and mirror `src/` structure.
- `ruff` must pass clean.
- `mypy` must pass clean.
- Test coverage on all new modules MUST be at least `85%`.

---

### 8. Pre-implementation Procedure

Before making code changes:

1. Find the TRD that owns the component being modified.
2. Check the TRD Index in `README.md`.
3. Read relevant TRD sections, especially:
   - interfaces
   - error contracts
   - security
   - testing requirements
4. Check `TRD-11` if the change touches:
   - credentials
   - external content
   - generated code
   - CI
5. Run existing tests first:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

## Wire Format Examples

## Valid payloads

### 1. Valid TrustFlow event

```json
{
  "event_id": "7f1d3d4c-9d44-4c3c-a8f8-0f7d57a6d2b1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678901,
  "event_type": "action_outcome",
  "payload_hash": "3d1e5c2f9b7c6a4e8f0d1c2b3a4958675d4c3b2a1908f7e6d5c4b3a291807f6e"
}
```

Why valid:
- All required fields are present.
- `ts` is a Unix timestamp in milliseconds.
- `payload_hash` is represented as a SHA-256 hex string.
- `event_id` is non-sequential in format.

---

### 2. Valid VTZ enforcement denial record

```json
{
  "verdict": "block"
}
```

Why valid:
- Uses the exact required verdict literal for VTZ denial.

---

### 3. Valid ready message

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

Why valid:
- Includes both required fields: `agent_version` and `capabilities`.

> Capability element values are illustrative; source specifies presence of the field but not allowed enum values.

---

### 4. Valid stdout listening announcement

```text
FORGE_AGENT_LISTENING:/tmp/forge.sock
```

Why valid:
- Matches exact required stdout format.

---

### 5. Valid file write request shape

```json
{
  "path": "/safe/output/file.txt"
}
```

Why valid:
- Contains required `path` field.
- Must still pass `path_security.validate_write_path()` before any write.

---

## Invalid payloads

### 1. Invalid TrustFlow event: missing `payload_hash`

```json
{
  "event_id": "7f1d3d4c-9d44-4c3c-a8f8-0f7d57a6d2b1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1712345678901,
  "event_type": "action_outcome"
}
```

Why invalid:
- `payload_hash` is required on every TrustFlow event.

---

### 2. Invalid VTZ denial record: wrong verdict

```json
{
  "verdict": "deny"
}
```

Why invalid:
- Source requires `verdict=block`.

---

### 3. Invalid listening announcement: wrong prefix

```text
AGENT_LISTENING:/tmp/forge.sock
```

Why invalid:
- Required exact stdout format is `FORGE_AGENT_LISTENING:{socket_path}`.

---

### 4. Invalid action processing sequence

```json
{
  "session_id": "sess_123",
  "action": "run_tool"
}
```

Why invalid:
- No CTX-ID is present.
- Missing CTX-ID must be treated as `UNTRUSTED`.
- Identity must not be inferred from context.
- Action cannot bypass CTX-ID-first validation.

---

### 5. Invalid security handling pattern

```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

Why invalid:
- When `SECURITY_REFUSAL` appears: stop, gate, log.
- Never retry to bypass.

---

### 6. Invalid backend credential sourcing

```python
token = KeychainKit.read("github_token")
```

Why invalid:
- Python reads nothing from Keychain.
- Only Swift reads Keychain, only to deliver via XPC.

---

### 7. Invalid subprocess usage

```python
subprocess.run(cmd, shell=True)
```

Why invalid:
- `shell=True` is forbidden.

---

### 8. Invalid prompt placement for external context

```json
{
  "system_prompt": "External document content here"
}
```

Why invalid:
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

---

## Integration Points

### 1. XPC

ConsensusDevAgent integrates with Swift over XPC.

Required interactions:
- Start XPC server and listen on socket.
- Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout.
- Wait up to `30` seconds for credentials via XPC.
- Receive credentials from Swift.
- Emit `auth_error` XPC card on credential-related initialization failure.
- Send ready message via XPC including:
  - `agent_version`
  - `capabilities`

Constraints:
- Python must not read Keychain directly.
- Swift is the only component that reads Keychain.
- Swift delivers credentials via XPC.

---

### 2. GitHubTool

All GitHub operations integrate through `GitHubTool`.

Constraints:
- Initialize `GitHubTool` with token during startup step 5.
- Never call GitHub API directly from pipeline code.

---

### 3. ConsensusEngine

Startup integration:
- Initialize `ConsensusEngine` with API keys during startup step 6.

Failure handling:
- Credential errors are non-fatal.
- Emit `auth_error` XPC card and continue in degraded state.

---

### 4. DocumentStore

Startup integration:
- Start `DocumentStore` loading in background asynchronously during startup step 7.

Constraints:
- App must remain responsive while embeddings load.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.

---

### 5. CommandRouter

Runtime integration:
- Enter `CommandRouter` event loop after ready message is sent.

---

### 6. TrustFlow

Enforcement integration:
- Every action outcome must emit a TrustFlow event.
- Emission occurs synchronously in the enforcement path.
- Emission failure must be logged and surfaced.
- Failed emission is a WARN-level audit event.

---

### 7. TrustLock

CTX-ID validation integration:
- CTX-ID must be validated against TrustLock public key.
- Software-only validation is rejected.

---

### 8. Path security

Filesystem integration:
- Every disk write path must be validated using `path_security.validate_write_path()` before write.

---

### 9. Test and quality tooling

Required ecosystem integrations:
- `pytest`
- `ruff`
- `mypy`

Command specified in source:

```bash
cd src && pytest ../tests/ -v --tb=short
```

---

### 10. Prompt construction / LLM boundary

Constraints at integration boundary:
- External document context must be placed in USER prompt only.
- Never place external document context in SYSTEM prompt.
- On `SECURITY_REFUSAL`: stop, gate, log.
- Never retry to bypass refusal.