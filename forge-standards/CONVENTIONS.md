# Code Conventions

This document defines coding conventions, naming rules, and code patterns derived from the provided TRD materials and repository guidance. The TRDs are the source of truth; this file consolidates implementation conventions implied by those materials.

## File and Directory Naming (exact `src/` layout)

### Top-level implementation layout

The codebase uses a two-process architecture:

- A native macOS shell implemented in Swift
- A backend implemented in Python

Directory structure must preserve subsystem ownership and process boundaries.

### Required source layout

```text
src/
  cal/
  dtl/
  trustflow/
  vtz/
  trustlock/
  mcp/
  rewind/
tests/
  cal/
  dtl/
  trustflow/
  vtz/
  trustlock/
  mcp/
  rewind/
sdk/
  connector/
```

### Directory naming rules

- Use lowercase directory names only.
- Use the exact subsystem names defined by standards:
  - `cal`
  - `dtl`
  - `trustflow`
  - `vtz`
  - `trustlock`
  - `mcp`
  - `rewind`
- Tests must mirror the `src/` structure exactly.
- SDK code must live under `sdk/connector/`.

### File naming rules

#### Python files

- Use `snake_case.py`.
- File names should reflect the primary type or responsibility in the file.
- Prefer singular names for modules that define a primary abstraction.
- Examples:
  - `consensus_engine.py`
  - `provider_adapter.py`
  - `pipeline_runner.py`
  - `github_client.py`
  - `socket_protocol.py`
  - `audit_stream.py`

#### Swift files

- Use `PascalCase.swift`.
- Name files after the primary type defined in the file.
- SwiftUI view files must be named after the view type.
- Examples:
  - `AuthenticatedSocketClient.swift`
  - `KeychainStore.swift`
  - `IntentPanel.swift`
  - `PullRequestCard.swift`

#### Test files

- Python tests should use `test_<module_name>.py`.
- Test directories must mirror production directories exactly.
- Examples:
  - `tests/cal/test_socket_protocol.py`
  - `tests/trustflow/test_audit_stream.py`

### File organization rules

- One primary type per file.
- Closely related helper types may exist in the same file only when they are private or tightly scoped to the primary type.
- Do not mix unrelated subsystems in a single file.
- Do not place shell-owned concerns in backend subsystem directories.
- Do not place backend-owned concerns in shell UI or auth files.

---

## Class and Function Naming

### General naming rules

- Name according to responsibility, not implementation detail.
- Prefer explicit names over abbreviated names.
- Avoid product-specific branding in identifiers.
- Use names that reflect the TRD-defined role, interface, state machine, or contract.

### Python naming

#### Classes

- Use `PascalCase`.
- Class names should be nouns or noun phrases.
- Use suffixes consistently by role:
  - `Engine` for orchestration or decision logic
  - `Adapter` for provider integrations
  - `Client` for external service communication
  - `Runner` for pipeline execution
  - `Validator` for contract or policy validation
  - `Manager` only when coordinating multiple owned resources
  - `Error` for exceptions

Examples:

- `ConsensusEngine`
- `ProviderAdapter`
- `GitHubClient`
- `PipelineRunner`
- `PolicyValidator`

#### Functions and methods

- Use `snake_case`.
- Function names must start with a verb.
- Boolean-returning functions should use predicates:
  - `is_...`
  - `has_...`
  - `can_...`
  - `should_...`

Examples:

- `build_pr_plan`
- `run_consensus`
- `open_draft_pull_request`
- `is_authenticated`
- `should_retry`

#### Constants

- Use `UPPER_SNAKE_CASE`.
- Constants must be immutable configuration values, protocol markers, or limits.

Examples:

- `MAX_RETRY_ATTEMPTS`
- `SOCKET_READ_TIMEOUT_SECONDS`
- `LINE_DELIMITED_JSON_VERSION`

### Swift naming

#### Types

- Use `PascalCase`.
- Protocols should be noun-based and capability-oriented.
- Do not prefix names unnecessarily.

Examples:

- `SocketClient`
- `KeychainStore`
- `AuthState`
- `IntentPanel`
- `PullRequestCard`

#### Properties and methods

- Use `camelCase`.
- Methods should begin with verbs.
- Boolean properties should read naturally:
  - `isAuthenticated`
  - `hasValidSession`
  - `canSubmitIntent`

#### Enums

- Use `PascalCase` for enum names.
- Use `camelCase` for cases.
- Enum case names should model domain states or outcomes directly.

Examples:

- `AuthState.signedOut`
- `PipelineStatus.running`
- `ConfidenceLevel.high`

### Acronyms and initialisms

- Treat acronyms as words for readability.
- In Swift type names, use standard casing:
  - `XpcClient`
  - `JsonMessage`
- In Python, use standard `snake_case`:
  - `xpc_client.py`
  - `json_message.py`

### Naming by ownership

Use names that make process ownership obvious.

#### Shell-owned names

For UI, auth, secrets, local IPC, and native integration:

- `AuthSession`
- `KeychainCredentialStore`
- `UnixSocketBridge`
- `XpcService`
- `IntentViewModel`

#### Backend-owned names

For consensus, generation, planning, repair, CI, and remote operations:

- `ConsensusEngine`
- `GenerationPipeline`
- `FixLoopRunner`
- `CiGate`
- `PullRequestPlanner`

---

## Error and Exception Patterns

### General error model

All errors must follow TRD-defined contracts. Do not invent undocumented error semantics.

Use errors to communicate:

- contract violations
- authentication failures
- authorization failures
- protocol violations
- validation failures
- external dependency failures
- retryable operational failures
- terminal pipeline failures

### Python exception rules

#### Exception naming

- Custom exceptions must end with `Error`.
- Name exceptions by failure domain, not generic outcome.

Examples:

- `AuthenticationError`
- `AuthorizationError`
- `ProtocolError`
- `ValidationError`
- `ConsensusError`
- `PipelineError`
- `ProviderError`
- `GitHubError`
- `SecurityPolicyError`

#### Exception hierarchy

- Define subsystem-local base exceptions where appropriate.
- Catch broad exceptions only at process boundaries, adapters, or top-level orchestration points.
- Raise specific exceptions internally.

Example pattern:

```python
class PipelineError(Exception):
    pass


class ValidationError(PipelineError):
    pass


class RetryLimitExceededError(PipelineError):
    pass
```

#### Error messages

- Error messages must be explicit and actionable.
- Include the failed operation and violated condition.
- Do not include secrets, tokens, raw credentials, or sensitive payloads.
- Do not log generated code content unless the TRD explicitly permits it.

Preferred pattern:

```python
raise ValidationError("pull request plan is missing required typed steps")
```

Avoid:

```python
raise Exception("bad input")
```

### Swift error rules

- Use typed `Error` conforming types.
- Prefer enums for finite domain errors.
- Use associated values only when they add structured context.
- Preserve user-safe and log-safe separation.

Example pattern:

```swift
enum AuthError: Error {
    case missingCredential
    case invalidSession
    case socketHandshakeFailed
}
```

### Boundary handling

Handle and translate errors at subsystem boundaries.

#### Required boundary translations

- Native shell ↔ backend socket boundary:
  - transport errors
  - authentication errors
  - protocol framing errors
  - JSON decode/encode errors
- Backend ↔ provider boundary:
  - provider API errors
  - malformed provider responses
  - timeout and retry exhaustion
- Backend ↔ remote repository boundary:
  - authentication failures
  - rate limiting
  - branch or PR creation failures

### Retry behavior

- Only retry explicitly retryable failures.
- Retry logic must be centralized in adapters, clients, or runners responsible for external communication.
- Never retry:
  - schema violations
  - authentication failures unless token refresh is part of the TRD-defined flow
  - local validation failures
  - policy denials

### Logging and errors

- Log structured context, not secrets.
- Use stable field names for operation, subsystem, outcome, and correlation identifiers.
- Errors exposed to UI must be sanitized.
- Internal logs may include technical detail but must still exclude protected material.

---

## Per-Subsystem Naming Rules

## `cal` naming rules

Conversation Abstraction Layer components must use names that reflect message transport, framing, session semantics, and abstraction boundaries.

### Preferred names

- `ConversationSession`
- `MessageEnvelope`
- `SocketProtocol`
- `TransportClient`
- `TransportServer`
- `SessionState`
- `RequestContext`

### File patterns

- `conversation_session.py`
- `message_envelope.py`
- `socket_protocol.py`

### Function patterns

- `send_message`
- `receive_message`
- `encode_envelope`
- `decode_envelope`
- `open_session`
- `close_session`

### Avoid

- vague names like `handler.py`, `utils.py`, `misc.py`
- names tied to a specific provider when the layer is abstraction-focused

---

## `dtl` naming rules

Data Trust Label components must use names that communicate labeling, provenance, trust level, and policy-aware data classification.

### Preferred names

- `TrustLabel`
- `DataClassification`
- `ProvenanceRecord`
- `LabelValidator`
- `TrustLevel`
- `ContentOrigin`

### File patterns

- `trust_label.py`
- `provenance_record.py`
- `label_validator.py`

### Function patterns

- `assign_label`
- `validate_label`
- `derive_trust_level`
- `record_provenance`

### Avoid

- generic names like `tag`, `meta`, or `info` where trust semantics are intended

---

## `trustflow` naming rules

TrustFlow audit stream components must use names that communicate append-only auditing, event chronology, and verifiable flow records.

### Preferred names

- `AuditStream`
- `AuditEvent`
- `EventRecord`
- `FlowTrace`
- `AuditSink`
- `AuditEmitter`

### File patterns

- `audit_stream.py`
- `audit_event.py`
- `flow_trace.py`

### Function patterns

- `append_event`
- `emit_audit_record`
- `flush_stream`
- `load_event_range`
- `verify_event_chain`

### Avoid

- names implying mutable history rewriting unless explicitly part of replay behavior in `rewind`

---

## `vtz` naming rules

Virtual Trust Zone enforcement components must use names that communicate isolation, enforcement, boundaries, and execution restrictions.

### Preferred names

- `TrustZone`
- `ZonePolicy`
- `ExecutionBoundary`
- `IsolationGuard`
- `EnforcementDecision`
- `BoundaryValidator`

### File patterns

- `trust_zone.py`
- `zone_policy.py`
- `isolation_guard.py`

### Function patterns

- `enforce_boundary`
- `validate_isolation`
- `deny_execution`
- `check_zone_policy`

### Avoid

- ambiguous security names like `secure_mode` when a specific policy or boundary concept exists

---

## `trustlock` naming rules

Cryptographic machine identity components must use names that communicate machine identity, attestation, anchoring, and key material custody.

### Preferred names

- `MachineIdentity`
- `IdentityAttestation`
- `KeyAnchor`
- `AttestationValidator`
- `IdentityToken`
- `KeyCustodyRecord`

### File patterns

- `machine_identity.py`
- `identity_attestation.py`
- `attestation_validator.py`

### Function patterns

- `create_attestation`
- `validate_attestation`
- `load_machine_identity`
- `rotate_identity_token`

### Avoid

- names exposing implementation secrets
- generic `key_manager` if the actual concern is identity anchoring or attestation

---

## `mcp` naming rules

MCP Policy Engine components must use names that communicate policy evaluation, decisioning, rule enforcement, and policy scope.

### Preferred names

- `PolicyEngine`
- `PolicyRule`
- `PolicyDecision`
- `PolicyScope`
- `RuleSet`
- `DecisionContext`

### File patterns

- `policy_engine.py`
- `policy_rule.py`
- `decision_context.py`

### Function patterns

- `evaluate_policy`
- `apply_rule_set`
- `build_decision_context`
- `deny_by_policy`

### Avoid

- naming policies as generic configuration when they are executable decision logic

---

## `rewind` naming rules

Replay engine components must use names that communicate replay, event reconstruction, deterministic restoration, and historical inspection.

### Preferred names

- `ReplayEngine`
- `ReplaySession`
- `EventSnapshot`
- `ReconstructionPlan`
- `PlaybackCursor`
- `StateRestorer`

### File patterns

- `replay_engine.py`
- `replay_session.py`
- `event_snapshot.py`

### Function patterns

- `replay_events`
- `restore_state`
- `advance_cursor`
- `build_reconstruction_plan`

### Avoid

- names implying mutation of canonical history
- `undo` unless the TRD explicitly defines user-facing undo semantics

---

## SDK connector naming rules

Connector SDK code must use names that communicate integration boundaries and external consumer APIs.

### Preferred names

- `ConnectorClient`
- `ConnectorSession`
- `ConnectorConfig`
- `ConnectorRequest`
- `ConnectorResponse`
- `ConnectorError`

### File patterns

- `connector_client.py`
- `connector_session.py`
- `connector_config.py`

### Function patterns

- `connect`
- `disconnect`
- `send_request`
- `parse_response`

---

## Architecture-driven naming conventions

### Shell process conventions

Swift shell code owns:

- UI
- authentication
- secret storage
- Keychain access
- XPC
- authenticated Unix socket communication

Names in this layer must reflect native ownership and user-facing state.

Preferred patterns:

- `AuthCoordinator`
- `SessionController`
- `KeychainStore`
- `SocketBridge`
- `IntentPanel`
- `ReviewQueueView`

### Backend process conventions

Python backend code owns:

- consensus
- planning
- generation
- self-correction
- lint gate
- iterative fix loop
- CI execution
- remote repository operations

Preferred patterns:

- `ConsensusEngine`
- `ArbitrationResult`
- `PrdPlanner`
- `PullRequestPlan`
- `GenerationPass`
- `LintGate`
- `FixLoopRunner`
- `CiRunner`
- `DraftPullRequestPublisher`

---

## Interface and protocol conventions

### JSON protocol naming

The processes communicate over an authenticated Unix socket using line-delimited JSON.

For protocol objects:

- message types must be nouns or imperative event labels
- payload fields must be `snake_case` in Python-owned protocol definitions
- version fields must be explicit
- identifiers must be stable and machine-readable

Preferred names:

- `message_type`
- `request_id`
- `correlation_id`
- `session_id`
- `protocol_version`
- `payload`
- `error_code`
- `error_message`

### Protocol type naming

- `RequestEnvelope`
- `ResponseEnvelope`
- `ErrorEnvelope`
- `HandshakeRequest`
- `HandshakeResponse`

### Serialization conventions

- Use explicit serializer/deserializer names.
- Avoid implicit magic conversion in boundary code.

Examples:

- `to_json_dict`
- `from_json_dict`
- `encode_line`
- `decode_line`

---

## State and status naming

Use nouns for stored state and adjectives or participles for statuses only when they represent transient processing phases.

### Preferred examples

- `auth_state`
- `pipeline_status`
- `review_state`
- `session_state`
- `trust_level`

### Status value examples

- `pending`
- `running`
- `completed`
- `failed`
- `denied`
- `authenticated`
- `unauthenticated`

Avoid mixing state-machine terms and UI copy in the same enum or constant set.

---

## Code pattern conventions

### Separation of concerns

- UI code must not contain backend generation logic.
- Secret handling must remain in the native shell-owned layer.
- Backend code must not assume direct access to shell-managed secrets.
- Provider-specific logic must remain behind adapters.
- Consensus and arbitration logic must remain separate from transport and UI.

### Adapter pattern

Use adapters for all provider and external service integrations.

Naming pattern:

- `<Provider>Adapter`
- `<Service>Client`

Examples:

- `ModelProviderAdapter`
- `RepositoryClient`

### Engine pattern

Use `Engine` for deterministic orchestration or multi-step decision logic driven by TRD-defined workflows.

Examples:

- `ConsensusEngine`
- `ReplayEngine`
- `PolicyEngine`

### Runner pattern

Use `Runner` for executable pipelines, loops, or staged processing flows.

Examples:

- `PipelineRunner`
- `FixLoopRunner`
- `CiRunner`

### Validator pattern

Use `Validator` for schema, policy, state, or contract checks that do not own side effects beyond reporting validity.

Examples:

- `LabelValidator`
- `BoundaryValidator`
- `AttestationValidator`

### Record / Envelope / Context pattern

Use these suffixes consistently:

- `Record` for persisted or auditable facts
- `Envelope` for transport wrappers
- `Context` for evaluation or request-scoped inputs

Examples:

- `AuditRecord`
- `MessageEnvelope`
- `DecisionContext`

---

## Test naming conventions

### Test structure

- Tests must mirror `src/` exactly by subsystem.
- Keep test modules named after the production module under test.

### Test function naming

Use descriptive names with `test_` prefix.

Preferred patterns:

- `test_<unit>_<expected_behavior>`
- `test_<unit>_<condition>_<outcome>`

Examples:

- `test_consensus_engine_returns_arbitrated_result`
- `test_socket_protocol_rejects_invalid_handshake`
- `test_policy_engine_denies_untrusted_content`

### Test class naming

If grouping tests in classes, use:

- `Test<ClassName>`
- `Test<Subsystem><Behavior>`

Examples:

- `TestConsensusEngine`
- `TestAuditStreamAppend`

### Security-sensitive tests

Where security rules apply, test names must clearly describe the denied or constrained behavior.

Examples:

- `test_keychain_store_never_logs_secret_values`
- `test_protocol_rejects_unauthenticated_socket_client`
- `test_pipeline_does_not_execute_generated_code`

---

## Forbidden naming patterns

Do not use:

- `utils`
- `helpers`
- `common`
- `misc`
- `thing`
- `data` as a primary domain type name without qualification
- `manager` when a narrower role exists
- `handle` / `process` / `do` without a specific object
- hardcoded product branding in reusable subsystem code

Replace vague names with role-specific names drawn from the subsystem vocabulary.

---

## Documentation and code comment conventions

- Comments must explain why, not restate what.
- Public types and functions should use names clear enough to reduce comment volume.
- Security-sensitive code should document invariants and forbidden behavior.
- Any behavior mandated by a TRD should be referenced in implementation documentation by TRD identifier if local documentation is needed, but naming should remain domain-based and generic.

---

## Final rules

- Follow the owning TRD before following convenience.
- Preserve process ownership boundaries in names and file placement.
- Prefer explicit, typed, contract-driven code over implicit behavior.
- Name by domain role, failure mode, and state-machine meaning.
- Keep subsystem vocabulary consistent across source, tests, protocol objects, and logs.