# Interface Contracts - ConsensusDevAgent

## Data Structures

This document defines the required interface contracts, wire formats, field names, values, and behavioral constraints applicable to the `ConsensusDevAgent` subsystem based on the provided TRD excerpts and Forge component interface contracts.

Where the TRDs specify exact field names or values, they are reproduced exactly.

---

### 1. XPC Startup Readiness Message

Sent via XPC after backend startup step 8.

#### Structure: `ReadyMessage`
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `agent_version` | string | Yes | Must be included in ready message |
| `capabilities` | array<string> | Yes | Must be included in ready message |

#### Notes
- Emitted only after:
  1. logger initialization
  2. XPC server startup
  3. stdout emission of `FORGE_AGENT_LISTENING:{socket_path}`
  4. credential wait via XPC
  5. `GitHubTool` initialization attempt
  6. `ConsensusEngine` initialization attempt
  7. `DocumentStore` async background loading start
- Steps 5 and 6 are non-fatal on credential errors.
- In credential-error degraded mode, backend must still continue and send readiness.

---

### 2. XPC Authentication Error Card

Sent via XPC when startup credential initialization fails in step 5 or 6.

#### Structure: `AuthErrorCard`
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `auth_error` | object | Yes | Exact card/type name is specified as `auth_error XPC card` in TRD |

#### Nested payload constraints
The TRDs provided do not define additional required nested fields for the `auth_error` card. Implementations must not invent incompatible mandatory fields without an owning TRD update.

---

### 3. TrustFlow Event

Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.

#### Structure: `TrustFlowEvent`
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | Yes | Must be globally unique; CSPRNG-generated; must not be sequential |
| `session_id` | string | Yes | Must be included on every event |
| `ctx_id` | string | Yes | Must be included on every event |
| `ts` | number | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | Yes | Must be included on every event |
| `payload_hash` | string | Yes | Must be SHA-256 of the serialized action payload |

#### Behavioral constraints
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission is a WARN-level audit event.
- Failed emission must not be a silent skip.
- TrustFlow emission failure must not silently continue; log and surface the failure.

---

### 4. VTZ Enforcement Decision Record

Produced when VTZ policy denies an action.

#### Structure: `VTZEnforcementDecision`
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | Yes | Must equal exactly `block` on VTZ policy denial |

#### Notes
- TRD excerpt defines only the required field/value above.
- Additional fields are not specified in the provided source and therefore are not part of this contract.

---

### 5. CTX-ID Token

Represents the context identity token validated before any agent action processing.

#### Structure: `CTXIDToken`
The provided TRDs define behavioral requirements but do not enumerate token fields. Therefore field-level structure is unspecified in the provided source.

#### Required behavioral properties
- Token is immutable once issued.
- Rotation creates a new token.
- Old token is invalidated immediately upon rotation.
- Expired token must be rejected.
- Validation must be performed against TrustLock public key.
- Software-only validation is rejected.
- Missing token must be treated as `UNTRUSTED`.

---

### 6. Action Payload

The action payload is the serialized payload whose SHA-256 digest becomes `payload_hash` in the `TrustFlowEvent`.

#### Structure: `ActionPayload`
Field schema is not defined in the provided TRDs.

#### Constraints
- Must be serializable.
- `payload_hash` must equal SHA-256 of the serialized action payload exactly.

---

### 7. Agent Action Processing Input

Any entry point that processes an agent action is subject to the CAL enforcement contract.

#### Structure: `AgentActionRequest`
The provided source does not enumerate fields. However, the following logical data must be present or derivable for compliant processing:
- `ctx_id`
- action payload
- session identity for `session_id`
- action type/outcome for `event_type`

Because these names are not explicitly declared as a single request object in the provided TRDs, they are compliance requirements rather than a formal payload schema.

---

### 8. Backend Listening Announcement

Printed to stdout during startup step 3.

#### Wire format
```text
FORGE_AGENT_LISTENING:{socket_path}
```

#### Structure
| Component | Type | Required | Constraints |
|---|---|---:|---|
| `FORGE_AGENT_LISTENING:` | string literal | Yes | Exact prefix |
| `{socket_path}` | string | Yes | Socket path value appended immediately after the colon |

---

### 9. Credential Delivery via XPC

Credentials are delivered from Swift to Python through XPC.

#### Constraints
- Python reads nothing from Keychain.
- Only Swift reads Keychain.
- Swift may deliver credentials via XPC only.
- Backend must wait for credentials via XPC with timeout `30s`.

#### Forbidden interfaces
- Python must not read:
  ```swift
  KeychainKit.read("github_token")
  ```
- Backend/Swift must not instantiate LLM API client in Swift:
  ```swift
  AnthropicClient(apiKey: keychainValue)
  ```

---

### 10. GitHub Operations Interface

#### Component: `GitHubTool`
| Name | Type | Required | Constraints |
|---|---|---:|---|
| `GitHubTool` | component/service | Yes | All GitHub operations must go through `GitHubTool` |

#### Constraints
- Never call the GitHub API directly from pipeline code.
- `GitHubTool` is initialized in startup step 5 with token.

---

### 11. Consensus Engine Interface

#### Component: `ConsensusEngine`
| Name | Type | Required | Constraints |
|---|---|---:|---|
| `ConsensusEngine` | component/service | Yes | Initialized in startup step 6 with API keys |

#### Constraints
- Initialization credential errors are non-fatal.
- On credential error, emit `auth_error` XPC card and continue in degraded state.

---

### 12. Document Store Interface

#### Component: `DocumentStore`
| Name | Type | Required | Constraints |
|---|---|---:|---|
| `DocumentStore` | component/service | Yes | Loading starts in background asynchronously during startup step 7 |

#### Constraints
- Loading must be async.
- App remains responsive while embeddings load.
- All loaded document chunks must pass injection scanning before inclusion in any LLM prompt.

---

### 13. Path Security Validation Interface

#### Function/Contract: `path_security.validate_write_path()`
| Name | Type | Required | Constraints |
|---|---|---:|---|
| `path_security.validate_write_path()` | function | Yes | Must be called before any file path is written to disk |

#### Constraints
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

---

## Enums and Constants

### 1. TrustFlow / Enforcement Values

#### `verdict`
Allowed exact value explicitly defined by source:
- `block`

#### Action outcomes requiring TrustFlow emission
- `allow`
- `restrict`
- `block`

#### Missing CTX-ID trust state
- `UNTRUSTED`

---

### 2. Startup Constants

#### Listening stdout prefix
- `FORGE_AGENT_LISTENING:`

#### Credential wait timeout
- `30s`

#### Startup sequence order
Must occur exactly in this order:
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

### 3. Cryptographic / Identity Constants

#### `payload_hash`
- Algorithm: `SHA-256`

#### `event_id`
- Must be generated by `CSPRNG`
- Must not be sequential

#### `ts`
- UTC Unix timestamp
- Millisecond precision

---

### 4. Language / Runtime Constraints

#### Python backend requirements
- `Python 3.12`
- `async/await` throughout backend
- `dataclasses` for all structured data

#### Testing/tooling requirements
- `pytest`
- `ruff`
- `mypy`
- Test coverage `≥ 85%` on all new modules

---

### 5. Forbidden Values / Patterns

#### Forbidden retry behavior on refusal
If output contains:
- `SECURITY_REFUSAL`

Then implementation must:
- stop
- gate
- log

It must never retry to bypass.

#### Forbidden APIs / usage
- `shell=True`
- `eval()`
- `exec()`
- force unwrap in Swift:
  ```swift
  optional!
  ```

---

## Validation Rules

### 1. CAL Enforcement Contract

Every entry point that processes an agent action must satisfy all of the following:

1. CTX-ID validation must be called first.
2. If CTX-ID validation fails, processing must be immediately rejected.
3. No partial processing is allowed after CTX-ID validation failure.
4. Every action must be checked against VTZ policy before execution.
5. If VTZ policy denies, a `VTZEnforcementDecision` record must be produced with:
   - `verdict = block`
6. Every action outcome must emit a TrustFlow event.
7. If TrustFlow emission fails:
   - do not silently continue
   - log the failure
   - surface the failure

---

### 2. TrustFlow Event Validation

A `TrustFlowEvent` is valid only if:
- `event_id` is present
- `session_id` is present
- `ctx_id` is present
- `ts` is present
- `event_type` is present
- `payload_hash` is present
- `event_id` is globally unique
- `event_id` is not sequential
- `ts` is a UTC Unix timestamp with millisecond precision
- `payload_hash` is the SHA-256 digest of the serialized action payload

Invalid if any required field is missing or constraints are violated.

---

### 3. CTX-ID Validation Rules

A `CTXIDToken` is valid only if:
- it is present, otherwise trust state is `UNTRUSTED`
- it is not expired
- it validates against TrustLock public key
- validation is not software-only

Additional required rules:
- token fields must not be modified after issuance
- rotation must create a new token
- old token must be invalidated immediately
- policy changes apply at next CTX-ID issuance, not mid-session

---

### 4. VTZ Validation Rules

Valid session-policy relationship:
- every agent session is bound to exactly one VTZ at CTX-ID issuance

Invalid conditions:
- cross-VTZ tool calls without explicit policy authorization
- implicit authorization for cross-VTZ calls
- application-code bypass of VTZ boundaries

Policy timing rule:
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session

---

### 5. Security Validation Rules

#### Credentials
- Never hardcode credentials, API keys, tokens, or secrets as string literals.

#### Subprocesses
- Never use `shell=True`.

#### Generated/external content
- Never call `eval()` or `exec()` on generated or external content.

#### Logging
- Never log HTTP response bodies.
- Log status codes and error types only.

#### Filesystem writes
- All file paths written to disk must pass `path_security.validate_write_path()` before any write.

#### Prompt construction
- All loaded document chunks must pass injection scanning before being included in any LLM prompt.
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.

#### Security refusal handling
When output contains `SECURITY_REFUSAL`:
- stop
- gate
- log
- never retry to bypass

This means the following behavior is non-conformant:
```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

---

### 6. Startup Sequence Validation

The backend startup sequence is valid only if it follows the exact mandatory order:

1. Initialize logger
2. Start XPC server, listen on socket
3. Print `FORGE_AGENT_LISTENING:{socket_path}` to stdout
4. Wait for credentials via XPC (`30s`)
5. Initialize `GitHubTool` with token
6. Initialize `ConsensusEngine` with API keys
7. Start `DocumentStore` loading in background (`async`)
8. Send ready message via XPC (`agent_version`, `capabilities`)
9. Enter `CommandRouter` event loop

Additional validation:
- steps 5 and 6 credential failures are non-fatal
- such failures must emit `auth_error` XPC card
- system must continue in degraded state
- step 7 must always be async

---

### 7. GitHub Integration Validation

Valid GitHub operation:
- performed through `GitHubTool`

Invalid GitHub operation:
- direct GitHub API call from pipeline code

---

### 8. Keychain / Credential Boundary Validation

Valid:
- Swift reads Keychain
- Swift delivers credentials via XPC
- Python receives credentials via XPC

Invalid:
- Python reads Keychain
- backend code accesses Keychain directly
- Swift creates backend LLM API client with credential material

---

## Wire Format Examples

## Valid payloads

### 1. Ready message
```json
{
  "agent_version": "1.0.0",
  "capabilities": ["github", "consensus", "documents"]
}
```

### 2. TrustFlow event
```json
{
  "event_id": "4f1e8f2d-7f3b-4f6d-a9e9-1b63d8d3f5d1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "allow",
  "payload_hash": "3a6eb0790f39ac87c94f3856b2dd2c5d110e6811602261a9a923d3bb23adc8b7"
}
```

### 3. VTZ enforcement decision
```json
{
  "verdict": "block"
}
```

### 4. Listening announcement
```text
FORGE_AGENT_LISTENING:/tmp/consensusdevagent.sock
```

### 5. Auth error card
```json
{
  "auth_error": {}
}
```

---

## Invalid payloads

### 1. TrustFlow event missing required field
Invalid because `payload_hash` is required.
```json
{
  "event_id": "4f1e8f2d-7f3b-4f6d-a9e9-1b63d8d3f5d1",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1735689600123,
  "event_type": "allow"
}
```

### 2. VTZ enforcement decision with wrong verdict
Invalid because denial must produce `verdict=block`.
```json
{
  "verdict": "deny"
}
```

### 3. Listening announcement with wrong prefix
Invalid because prefix must be exactly `FORGE_AGENT_LISTENING:`.
```text
AGENT_LISTENING:/tmp/consensusdevagent.sock
```

### 4. Missing CTX-ID treated as trusted
Invalid because missing CTX-ID must be treated as `UNTRUSTED`.
```json
{
  "session_id": "sess_123",
  "event_type": "allow"
}
```

### 5. Security refusal retry flow
Invalid because `SECURITY_REFUSAL` must not trigger retry.
```python
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)
```

### 6. Direct GitHub API use from pipeline code
Invalid because all GitHub operations must go through `GitHubTool`.

```python
# invalid conceptual example
response = await github_api.post("/repos/owner/repo/issues", json=payload)
```

### 7. Python Keychain access
Invalid because Python reads nothing from Keychain.
```python
token = KeychainKit.read("github_token")
```

---

## Integration Points

### 1. XPC
Used for:
- credential delivery from Swift to backend
- ready message transmission
- `auth_error` card transmission

Required sequencing:
- XPC server starts before credentials are awaited
- ready message sent after service initialization attempts and document loading start

---

### 2. Stdout integration with Swift
Used for socket discovery.

Exact wire format:
```text
FORGE_AGENT_LISTENING:{socket_path}
```

Swift reads this line to obtain the socket path.

---

### 3. GitHubTool
All GitHub operations must route through:
- `GitHubTool`

No direct GitHub API access is permitted from pipeline code.

---

### 4. ConsensusEngine
Initialized with API keys during startup.
May operate in degraded state if credential initialization fails.

---

### 5. DocumentStore
Background async loading begins during startup.
Loaded chunks must be injection-scanned before prompt inclusion.

---

### 6. TrustFlow
Every action outcome emits a synchronous TrustFlow event in the enforcement path.

Required fields:
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

---

### 7. CTX-ID / TrustLock
Every action-processing entry point must validate CTX-ID first.
Validation must be against TrustLock public key.
Software-only validation is rejected.

---

### 8. VTZ Policy
Every action must be checked against VTZ policy before execution.
Cross-VTZ tool calls require explicit policy authorization.

---

### 9. Filesystem Security
Before any file write:
- call `path_security.validate_write_path()`

---

### 10. Prompt Construction Security
Before including external document content in an LLM prompt:
- perform injection scanning
- place document context in the `USER` prompt only
- never place external document context in the `SYSTEM` prompt

---

### 11. Testing and Conformance Tooling
Required backend conformance:
- Python `3.12`
- type annotations on every function
- `async/await` throughout backend
- `dataclasses` for all structured data
- tests in `tests/` mirroring `src/`
- `pytest`
- `ruff`
- `mypy`
- coverage `≥ 85%` on all new modules

---

## Non-Conformance Summary

A `ConsensusDevAgent` implementation is non-conformant if any of the following occurs:

- startup order differs from the mandated sequence
- ready message omits `agent_version` or `capabilities`
- GitHub operations bypass `GitHubTool`
- CTX-ID validation is not first
- CTX-ID failure permits partial processing
- VTZ denial does not emit `VTZEnforcementDecision` with `verdict=block`
- action outcome does not emit TrustFlow event
- TrustFlow emission is async-buffered
- TrustFlow failure is silently ignored
- missing CTX-ID is treated as trusted instead of `UNTRUSTED`
- CTX-ID validation is software-only
- cross-VTZ action is implicitly allowed
- `SECURITY_REFUSAL` is retried
- file writes occur without `path_security.validate_write_path()`
- external chunks are not injection-scanned
- external document context is placed into the `SYSTEM` prompt
- Python reads Keychain
- backend uses hardcoded secrets
- subprocesses use `shell=True`
- generated or external content is passed to `eval()` or `exec()`
- HTTP response bodies are logged