# Interface Contracts - ConsensusDevAgent

This document defines the wire format and API contract for the ConsensusDevAgent subsystem, based strictly on the provided TRD excerpts and Forge interface contracts.

## Data Structures

## BackendStartupSequence

Mandatory startup order for the backend process.

Type: ordered procedure contract

Steps:

1. `initialize_logger`
2. `start_xpc_server`
3. `print_listening_marker`
4. `wait_for_credentials`
5. `initialize_github_tool`
6. `initialize_consensus_engine`
7. `start_document_store_loading`
8. `send_ready_message`
9. `enter_command_router_event_loop`

### BackendStartupSequence.print_listening_marker

Output to stdout:

- format: `FORGE_AGENT_LISTENING:{socket_path}`
- `socket_path`
  - type: string
  - required: yes
  - constraints: must be the XPC server socket path

### BackendStartupSequence.wait_for_credentials

- type: blocking startup wait
- required: yes
- timeout_seconds: `30`

### BackendStartupSequence.initialize_github_tool

Input:

- `token`
  - type: credential/token
  - required: yes for normal operation
  - constraints:
    - must be delivered via XPC
    - must not be read from Keychain by Python
    - credential errors are non-fatal

Output:

- `GitHubTool`
  - type: initialized backend component
  - degraded mode permitted: yes

### BackendStartupSequence.initialize_consensus_engine

Input:

- `api_keys`
  - type: credentials collection
  - required: yes for normal operation
  - constraints:
    - credential errors are non-fatal

Output:

- `ConsensusEngine`
  - type: initialized backend component
  - degraded mode permitted: yes

### BackendStartupSequence.start_document_store_loading

- type: async background task
- required: yes
- constraints:
  - must be asynchronous
  - app must remain responsive while embeddings load

### BackendStartupSequence.send_ready_message

Transport: XPC

Payload fields:

- `agent_version`
  - type: string
  - required: yes
- `capabilities`
  - type: array
  - required: yes

## XPCReadyMessage

Type: object

Fields:

- `agent_version`
  - type: string
  - required: yes
- `capabilities`
  - type: array
  - required: yes
  - item type: unspecified by source

## AuthErrorCard

Type: XPC card/message

Emitted when steps 5 or 6 encounter credential errors.

Fields:

- `auth_error`
  - type: card/message indicator
  - required: yes

Constraints:

- must be emitted on credential error during:
  - `initialize_github_tool`
  - `initialize_consensus_engine`
- backend must continue in degraded state

## TrustFlowEvent

Type: object

Required fields:

- `event_id`
  - type: string
  - required: yes
  - constraints:
    - must be globally unique
    - must be generated using CSPRNG
    - must not be sequential
- `session_id`
  - type: string
  - required: yes
- `ctx_id`
  - type: string
  - required: yes
- `ts`
  - type: number
  - required: yes
  - constraints:
    - must be UTC Unix timestamp
    - must have millisecond precision
- `event_type`
  - type: string
  - required: yes
- `payload_hash`
  - type: string
  - required: yes
  - constraints:
    - must be SHA-256 of the serialized action payload

## VTZEnforcementDecision

Type: object

Required fields:

- `verdict`
  - type: string
  - required: yes
  - constraints:
    - for VTZ policy denial, value must be `block`

Additional fields:

- unspecified by source

## CTXIDToken

Type: token/object

Fields:

- field set: unspecified by source

Constraints:

- immutable once issued
- no field modification after issuance
- rotation creates a new token
- old token is invalidated immediately on rotation
- expired token must be rejected
- must be validated against TrustLock public key
- software-only validation is rejected
- missing token must be treated as `UNTRUSTED`
- identity must never be inferred from context when CTX-ID is missing

## AgentActionPayload

Type: serialized action payload

Fields:

- field set: unspecified by source

Constraints:

- every entry point that processes an agent action must validate `CTX-ID` first
- every action must be checked against VTZ policy before execution
- every action outcome must emit a TrustFlow event
- `payload_hash` must be SHA-256 of the serialized action payload

## DocumentChunk

Type: object/content chunk

Fields:

- field set: unspecified by source

Constraints:

- all loaded document chunks must pass injection scanning before being included in any LLM prompt

## ExternalDocumentContext

Type: prompt content segment

Fields:

- content
  - type: external document context
  - required: yes

Constraints:

- must go in the USER prompt
- must never go in the SYSTEM prompt

## WritePathRequest

Type: object

Fields:

- `path`
  - type: string
  - required: yes

Constraints:

- every file path written to disk must pass `path_security.validate_write_path()` before any write

## SecurityRefusalOutput

Type: model output/status

Fields:

- output content
  - type: string
  - required: yes

Constraints:

- if output contains `SECURITY_REFUSAL`:
  - stop
  - gate
  - log
  - never retry to bypass

## GitHubOperation

Type: operation contract

Fields:

- operation payload
  - type: unspecified
  - required: yes

Constraints:

- all GitHub operations must go through `GitHubTool`
- pipeline code must never call the GitHub API directly

## Enums and Constants

## String Constants

- `FORGE_AGENT_LISTENING:`
- `SECURITY_REFUSAL`
- `UNTRUSTED`
- `block`

## Time Constants

- credentials wait timeout: `30s`

## Required Startup Sequence Order

Exact order:

1. `Initialize logger`
2. `Start XPC server, listen on socket`
3. `Print FORGE_AGENT_LISTENING:{socket_path} to stdout`
4. `Wait for credentials via XPC`
5. `Initialize GitHubTool with token`
6. `Initialize ConsensusEngine with API keys`
7. `Start DocumentStore loading in background (async)`
8. `Send ready message via XPC (includes agent_version, capabilities)`
9. `Enter CommandRouter event loop`

## Validation Rules

## CAL Enforcement Contract

For every entry point that processes an agent action:

1. CTX-ID validation must be called first.
2. If CTX-ID validation fails:
   - immediate rejection is required
   - no partial processing is allowed
3. VTZ policy check must occur before execution.
4. If VTZ policy denies the action:
   - a `VTZEnforcementDecision` record must be produced
   - `verdict` must equal `block`
5. Every action outcome must emit a TrustFlow event:
   - allow
   - restrict
   - block
6. If TrustFlow emission fails:
   - must not silently continue
   - must log and surface the failure

## TrustFlow Emission Contract

For every TrustFlow event:

- required fields:
  - `event_id`
  - `session_id`
  - `ctx_id`
  - `ts`
  - `event_type`
  - `payload_hash`
- `event_id` must be globally unique
- `event_id` must use CSPRNG
- `event_id` must not be sequential
- `ts` must be UTC Unix timestamp with millisecond precision
- `payload_hash` must be SHA-256 of the serialized action payload
- emission must be synchronous in the enforcement path
- async buffering is not permitted
- failed emission is a WARN-level audit event
- failed emission must not be a silent skip

## CTX-ID Contract

- CTX-ID tokens are immutable after issuance
- rotation must create a new token
- old token must be invalidated immediately
- expired CTX-ID must be rejected
- clock skew tolerance is deployment-defined
- CTX-ID must be validated against TrustLock public key
- software-only validation is rejected
- missing CTX-ID must be treated as `UNTRUSTED`
- identity must never be inferred from surrounding context

## VTZ Enforcement Contract

- every agent session must be bound to exactly one VTZ at CTX-ID issuance
- cross-VTZ tool calls require explicit policy authorization
- implicit authorization is denied
- VTZ boundaries are structural, not advisory
- enforcement cannot be bypassed by application code
- VTZ policy changes take effect at next CTX-ID issuance
- VTZ policy changes do not take effect mid-session

## Security Validation Rules

- never hardcode credentials, API keys, tokens, or secrets as string literals
- never use `shell=True` in subprocess calls
- never call `eval()` or `exec()` on generated or external content
- never log HTTP response bodies
- log status codes and error types only
- all file paths written to disk must pass `path_security.validate_write_path()` before write
- all loaded document chunks must pass injection scanning before inclusion in any LLM prompt
- context from external documents must go in the USER prompt, never the SYSTEM prompt
- when `SECURITY_REFUSAL` appears in LLM output:
  - stop
  - gate
  - log
  - never retry to bypass

## Language and Implementation Constraints

### Python

- version: `Python 3.12`
- every function must have type annotations
- backend must use `async/await` throughout
- no blocking calls on the event loop
- all structured data must use dataclasses

### Testing

- framework: `pytest`
- tests location: `tests/`
- tests must mirror `src/` structure
- linting: `ruff`
- type checking: `mypy`
- both must pass clean
- test coverage on all new modules must be `>= 85%`

## Wire Format Examples

## Valid Payloads

### Stdout listening marker

```text
FORGE_AGENT_LISTENING:/tmp/forge-agent.sock
```

### XPC ready message

```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "document_store"]
}
```

### TrustFlow event

```json
{
  "event_id": "8f4d7f4c-7f1e-4c7e-9b58-7d6f2d8d3e91",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "block",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8f8bea5a8b1c5c3e6c8c4d7d8e9f0a1b2"
}
```

### VTZ enforcement denial record

```json
{
  "verdict": "block"
}
```

## Invalid Payloads

### Invalid TrustFlow event: missing required field

```json
{
  "event_id": "123",
  "session_id": "sess_123",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8f8bea5a8b1c5c3e6c8c4d7d8e9f0a1b2"
}
```

Invalid because:

- missing `ctx_id`

### Invalid TrustFlow event: non-conformant event_id generation

```json
{
  "event_id": "1001",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "3f0a377ba0a4a460ecb616f6507ce0d8f8bea5a8b1c5c3e6c8c4d7d8e9f0a1b2"
}
```

Invalid because:

- `event_id` must be globally unique
- `event_id` must be CSPRNG-generated
- sequential identifiers are not permitted

### Invalid VTZ denial record

```json
{
  "verdict": "deny"
}
```

Invalid because:

- VTZ policy denial must produce `verdict=block`

### Invalid startup output

```text
LISTENING:/tmp/forge-agent.sock
```

Invalid because:

- required prefix is exactly `FORGE_AGENT_LISTENING:`

## Integration Points

## XPC

Used for:

- credential delivery to backend
- ready message delivery
- auth error card delivery

Required behaviors:

- backend must start XPC server before waiting for credentials
- backend must wait for credentials via XPC with timeout `30s`
- backend must send ready message via XPC including:
  - `agent_version`
  - `capabilities`

## Swift Integration

Constraints:

- Swift reads stdout marker `FORGE_AGENT_LISTENING:{socket_path}`
- only Swift reads Keychain
- Swift may deliver credentials via XPC
- backend Python must not read Keychain

Forbidden patterns:

- force unwrap: `optional!`
- LLM API call from Swift
- backend credential retrieval from Keychain in Python

## GitHubTool

Constraints:

- all GitHub operations must go through `GitHubTool`
- pipeline code must never call GitHub API directly
- `GitHubTool` is initialized at startup step 5 using token received via XPC

## ConsensusEngine

Constraints:

- initialized at startup step 6
- initialization uses API keys
- credential errors are non-fatal
- degraded operation is allowed

## DocumentStore

Constraints:

- loading starts at startup step 7
- must load in background asynchronously
- application must remain responsive during loading
- loaded document chunks must pass injection scanning before inclusion in prompts

## CommandRouter

Constraints:

- entered only after startup step 8 completes
- event loop begins at startup step 9

## Path Security

Validation function:

- `path_security.validate_write_path()`

Requirement:

- must be called before any disk write path is used

## LLM Prompt Construction

Constraints:

- external document context must be placed in USER prompt only
- external document context must never be placed in SYSTEM prompt
- if model output contains `SECURITY_REFUSAL`, processing must stop and must not retry to bypass