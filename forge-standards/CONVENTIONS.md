# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, and implementation patterns for the full Forge platform.

Forge is a multi-subsystem platform with strict specification ownership. All code must align with the controlling TRD for the subsystem being modified. Where repository guidance, subsystem guidance, and TRDs differ, the TRD is authoritative.

## Core Principles

- Follow the owning TRD before writing code.
- Do not invent interfaces, states, or error semantics not defined by spec.
- Keep boundaries explicit between subsystems.
- Prefer small, composable units over broad utility layers.
- Never weaken security, auditability, or determinism for convenience.
- Generated code must never be executed automatically.
- Tests must mirror source structure and verify documented contracts.

## Repository and Architectural Context

Forge follows a two-process architecture:

- Swift shell:
  - UI
  - authentication
  - Keychain and secret custody
  - XPC / platform-native integration
- Python backend:
  - consensus
  - pipeline orchestration
  - generation
  - GitHub operations
  - policy and trust services

Processes communicate over authenticated local IPC using line-delimited JSON. Maintain strict serialization contracts and explicit error envelopes across process boundaries.

## TRD Authority and Change Discipline

Before modifying code:

1. Identify the owning TRD.
2. Read interface, state machine, error contract, security, and testing sections.
3. For anything involving credentials, generated content, CI, policy, or external content, read the security TRD first.
4. Run relevant existing tests before changing behavior.
5. Preserve contract compatibility unless the TRD explicitly changes it.

## General Style Rules

### Naming

- Use names that reflect domain meaning, not implementation detail.
- Prefer explicit nouns for types and explicit verbs for operations.
- Avoid abbreviations unless they are established subsystem names.
- Keep subsystem prefixes in filenames and package paths, not in every symbol unless required for clarity.

### Composition

- Prefer pure functions for transformations.
- Keep side effects at edges.
- Separate:
  - parsing
  - validation
  - authorization
  - execution
  - persistence
  - audit emission

### State Handling

- Model state transitions explicitly.
- Make invalid states unrepresentable where language features allow.
- Use typed enums for finite states.
- Do not encode state with booleans when a discrete state model exists.

### Contracts

- All external boundaries must use explicit schemas.
- Validate inputs at boundaries, not deep in business logic.
- Log and audit with structured fields.
- Never silently coerce security-relevant input.

---

## File and Directory Naming (exact `src/` layout)

Use the following canonical layout for platform subsystems:

```text
src/
  cal/           # Conversation Abstraction Layer
  dtl/           # Data Trust Label
  trustflow/     # TrustFlow audit stream
  vtz/           # Virtual Trust Zone enforcement
  trustlock/     # Cryptographic machine identity
  mcp/           # MCP Policy Engine
  rewind/        # Forge Rewind replay engine

sdk/
  connector/     # Forge Connector SDK

tests/
  cal/
  dtl/
  trustflow/
  vtz/
  trustlock/
  mcp/
  rewind/
  connector/
```

### Directory Rules

- Tests must mirror `src/` structure exactly.
- Do not create top-level subsystem aliases outside this layout.
- Shared code belongs in a clearly named shared package only if:
  - used by multiple subsystems
  - domain-neutral
  - not violating trust boundaries
- Do not move code across subsystem boundaries to “simplify” imports without architectural approval.

### File Naming Rules

Use lowercase snake_case for source filenames unless the language requires otherwise.

Examples:

- `src/cal/session_router.py`
- `src/dtl/label_parser.py`
- `src/trustflow/audit_stream.py`
- `src/vtz/policy_enforcer.py`
- `src/trustlock/device_identity.py`
- `src/mcp/policy_compiler.py`
- `src/rewind/replay_coordinator.py`

Swift files should use PascalCase filenames matching the primary type when that is the established project convention:

- `ShellViewModel.swift`
- `AuthenticatedSocketClient.swift`
- `TrustZonePanel.swift`

### File Naming Patterns by Role

Use these suffixes consistently:

- `_model` for internal data models
- `_schema` for serialization schemas
- `_parser` for parsing logic
- `_validator` for validation logic
- `_service` for orchestration logic
- `_client` for outbound adapters
- `_adapter` for provider or protocol bridges
- `_store` for persistence access
- `_repository` only when implementing aggregate repository semantics
- `_controller` only for UI or API request coordination
- `_engine` for deterministic execution engines
- `_coordinator` for multi-step orchestration
- `_emitter` for event production
- `_consumer` for event handling
- `_policy` for policy definitions or evaluators
- `_auth` for authentication-specific logic
- `_crypto` for cryptographic operations

Avoid vague filenames such as:

- `utils.py`
- `helpers.py`
- `misc.py`
- `common.py`

If a file would otherwise be named one of the above, the responsibility is too broad or too poorly named.

---

## Class and Function Naming

## Class Naming

Use PascalCase for classes, structs, enums, protocols, and typed interfaces.

Examples:

- `ConversationSession`
- `TrustLabel`
- `AuditStreamEmitter`
- `VirtualTrustZone`
- `MachineIdentityProvider`
- `PolicyDecisionEngine`
- `ReplayCoordinator`

### Class Naming Patterns

- Entities: noun
  - `TrustLabel`
  - `PolicyDecision`
- Services: noun + role
  - `TrustLabelValidator`
  - `AuditStreamWriter`
- Engines: noun + `Engine`
  - `ConsensusEngine`
  - `PolicyEvaluationEngine`
- Coordinators: noun + `Coordinator`
  - `ReplayCoordinator`
- Adapters: provider/protocol + `Adapter`
  - `GitHubAdapter`
  - `SocketProtocolAdapter`
- Clients: target + `Client`
  - `ProviderClient`
  - `AuditIngestClient`
- Stores: subject + `Store`
  - `LabelStore`
  - `IdentityStore`

### Protocol / Interface Naming

- Swift protocols: noun or capability adjective ending in `Providing`, `Serving`, `Coordinating`, `Validating`, etc.
  - `IdentityProviding`
  - `PolicyEvaluating`
- Python abstract interfaces: noun + `Protocol` where typing protocols are used.
  - `AuditEmitterProtocol`

Do not use `I` prefixes such as `IClient`.

## Function and Method Naming

Use lower_snake_case in Python and lowerCamelCase in Swift.

Functions should be verb-first and intention-revealing.

Examples:

- `parse_label`
- `validate_policy`
- `emit_audit_event`
- `replay_session`
- `derive_machine_identity`
- `evaluate_access_request`

### Function Naming Rules

- `get_` only when retrieval is cheap and non-mutating.
- `load_` for I/O-backed retrieval.
- `build_` for in-memory object construction.
- `create_` for new persisted or externally visible objects.
- `derive_` for deterministic values computed from trusted inputs.
- `resolve_` for selection among candidates.
- `validate_` for contract checks returning structured validation results or raising documented validation errors.
- `enforce_` for policy decisions that may reject or stop execution.
- `emit_` for event publication.
- `record_` for persistence of facts or logs.
- `replay_` for deterministic historical execution.
- `sync_` for convergence with external systems.

Avoid ambiguous verbs:

- `handle`
- `process`
- `manage`
- `do`

Use them only when the abstraction is genuinely generic and documented.

## Boolean and Predicate Naming

Use affirmative predicates.

Python:

- `is_trusted`
- `has_valid_signature`
- `can_replay`

Swift:

- `isTrusted`
- `hasValidSignature`
- `canReplay`

Avoid negated names such as `is_not_allowed`.

## Constant Naming

- Python constants: `UPPER_SNAKE_CASE`
- Swift static constants: `lowerCamelCase` unless global constants must match platform conventions

Examples:

- `MAX_REPLAY_DEPTH`
- `defaultSocketTimeout`

## Enum Case Naming

- Python enum values: `UPPER_SNAKE_CASE` or lowercase string values if serialized
- Swift enum cases: `lowerCamelCase`

Use domain-specific names:

- `trusted`
- `quarantined`
- `rejected`
- `pendingReview`

---

## Error and Exception Patterns

Errors must be explicit, typed, and stable at subsystem boundaries.

## General Error Rules

- Do not raise generic `Exception` except at true top-level guards.
- Do not swallow exceptions.
- Preserve original causes when translating errors.
- Use structured error payloads at IPC, API, and storage boundaries.
- Security-relevant failures must be auditable.
- Validation failures must be distinguishable from system failures.
- Policy denials must be distinguishable from execution errors.

## Error Taxonomy

Use these broad categories consistently:

- `ValidationError`
  - malformed input
  - schema mismatch
  - missing required fields
- `PolicyError` / `PolicyDeniedError`
  - explicit policy rejection
- `AuthenticationError`
  - identity proof failure
- `AuthorizationError`
  - insufficient permission
- `TrustError`
  - trust chain, label, or attestation failure
- `SerializationError`
  - encode/decode failure
- `TransportError`
  - IPC/network framing or delivery failure
- `PersistenceError`
  - storage read/write failure
- `ConcurrencyError`
  - lock, race, or ordering contract violation
- `ReplayError`
  - non-replayable or invalid replay state
- `ExternalServiceError`
  - upstream provider failure
- `InternalInvariantError`
  - impossible state indicating bug

Use subsystem-specific variants where appropriate:

- `DTLValidationError`
- `TrustFlowAppendError`
- `VTZPolicyDeniedError`
- `TrustLockAttestationError`
- `MCPCompilationError`
- `RewindConsistencyError`

## Error Naming

Exception classes must end with `Error`.

Examples:

- `LabelParseError`
- `AuditEmissionError`
- `IdentityDerivationError`
- `PolicyCompilationError`

Do not use:

- `LabelException`
- `BadThingHappened`
- `Failure`

## Error Translation

At subsystem boundaries:

- translate low-level library errors into Forge domain errors
- preserve the original cause
- attach stable context fields
- avoid leaking secrets, token material, raw credentials, or untrusted content in messages

Python example pattern:

```python
try:
    record = schema.loads(payload)
except SomeLibraryError as exc:
    raise SerializationError("failed to decode audit payload") from exc
```

Swift example pattern:

```swift
do {
    return try decoder.decode(EventEnvelope.self, from: data)
} catch {
    throw TransportError.decodeFailed(underlying: error)
}
```

## Error Payload Structure

Structured error payloads crossing process boundaries should include:

- `code`
- `message`
- `subsystem`
- `operation`
- `retryable`
- `details` - sanitized, structured only
- `correlation_id`

Never send stack traces across public or cross-process contracts unless explicitly defined for debug-only channels.

---

## Per-Subsystem Naming Rules

## `src/cal/` — Conversation Abstraction Layer

Purpose: conversation/session abstraction, prompt envelope shaping, turn state, provider-facing conversation coordination.

### Naming Rules

Use `conversation`, `session`, `turn`, `prompt`, `context`, and `envelope` consistently.

Preferred type names:

- `ConversationSession`
- `TurnState`
- `PromptEnvelope`
- `ContextWindow`
- `SessionCoordinator`
- `ConversationAdapter`

Preferred file names:

- `session_coordinator.py`
- `turn_state_model.py`
- `prompt_envelope_schema.py`
- `context_window_validator.py`

Avoid mixing UI terms with CAL internals. Do not name CAL objects as `chat_*`.

### CAL Function Patterns

- `build_prompt_envelope`
- `append_turn`
- `trim_context_window`
- `serialize_session_state`
- `restore_session_state`

## `src/dtl/` — Data Trust Label

Purpose: label creation, parsing, validation, propagation, and trust metadata enforcement.

### Naming Rules

Always use `label` for the core artifact, not `tag`, `marker`, or `stamp`.

Preferred type names:

- `TrustLabel`
- `LabelDescriptor`
- `LabelValidator`
- `LabelPropagationPolicy`
- `TrustClassification`

Preferred file names:

- `label_parser.py`
- `label_validator.py`
- `label_propagation_policy.py`
- `trust_classification_model.py`

### DTL Function Patterns

- `parse_label`
- `validate_label`
- `propagate_label`
- `classify_content_trust`
- `merge_label_constraints`

## `src/trustflow/` — TrustFlow Audit Stream

Purpose: append-only audit events, provenance tracking, trace correlation, audit export.

### Naming Rules

Use `audit`, `event`, `stream`, `append`, `provenance`, and `correlation` consistently.

Preferred type names:

- `AuditEvent`
- `AuditEnvelope`
- `AuditStreamWriter`
- `ProvenanceRecord`
- `CorrelationContext`

Preferred file names:

- `audit_event_schema.py`
- `audit_stream_writer.py`
- `provenance_record_model.py`
- `correlation_context.py`

### TrustFlow Function Patterns

- `append_audit_event`
- `emit_provenance_record`
- `load_audit_stream`
- `correlate_event_chain`
- `export_audit_segment`

Never imply mutability of historical audit records. Avoid verbs like `update_audit_event`.

## `src/vtz/` — Virtual Trust Zone

Purpose: enforcement boundaries, isolation policies, execution gating, trust-zone decisions.

### Naming Rules

Use `zone`, `boundary`, `enforcement`, `isolation`, `gate`, and `attestation` consistently.

Preferred type names:

- `VirtualTrustZone`
- `ZoneBoundary`
- `EnforcementGate`
- `IsolationPolicy`
- `ZoneAttestation`

Preferred file names:

- `zone_boundary.py`
- `enforcement_gate.py`
- `isolation_policy.py`
- `zone_attestation_validator.py`

### VTZ Function Patterns

- `enforce_zone_boundary`
- `evaluate_isolation_policy`
- `attest_zone_state`
- `gate_sensitive_operation`
- `reject_boundary_violation`

Use denial-specific naming when behavior is security-enforcing.

## `src/trustlock/` — Cryptographic Machine Identity

Purpose: TPM-/hardware-anchored machine identity, attestation, key custody, device binding.

### Naming Rules

Use `identity`, `attestation`, `device`, `binding`, `key`, and `custody` consistently.

Preferred type names:

- `MachineIdentity`
- `DeviceBinding`
- `AttestationBundle`
- `KeyCustodyService`
- `IdentityProvider`

Preferred file names:

- `machine_identity.py`
- `device_binding_store.py`
- `attestation_bundle_schema.py`
- `key_custody_service.py`

### TrustLock Function Patterns

- `derive_machine_identity`
- `verify_attestation_bundle`
- `bind_device_identity`
- `rotate_custody_key`
- `load_identity_material`

Never name sensitive key operations with generic verbs like `handle_key`.

## `src/mcp/` — MCP Policy Engine

Purpose: policy definition, compilation, evaluation, decision explanation, enforcement integration.

### Naming Rules

Use `policy`, `rule`, `decision`, `effect`, `evaluation`, and `compiler` consistently.

Preferred type names:

- `PolicyRule`
- `PolicyDecision`
- `PolicyCompiler`
- `PolicyEvaluationEngine`
- `DecisionExplanation`

Preferred file names:

- `policy_rule_model.py`
- `policy_compiler.py`
- `policy_evaluation_engine.py`
- `decision_explanation.py`

### MCP Function Patterns

- `compile_policy`
- `evaluate_policy`
- `resolve_policy_effect`
- `explain_decision`
- `enforce_policy_decision`

Distinguish clearly between:
- compilation
- evaluation
- enforcement
- explanation

Do not collapse these into one generic `process_policy`.

## `src/rewind/` — Forge Rewind Replay Engine

Purpose: deterministic replay, timeline reconstruction, historical state re-evaluation, diffing.

### Naming Rules

Use `replay`, `timeline`, `checkpoint`, `frame`, `reconstruction`, and `consistency` consistently.

Preferred type names:

- `ReplayCoordinator`
- `ReplayFrame`
- `TimelineCheckpoint`
- `StateReconstruction`
- `ConsistencyVerifier`

Preferred file names:

- `replay_coordinator.py`
- `replay_frame_model.py`
- `timeline_checkpoint_store.py`
- `consistency_verifier.py`

### Rewind Function Patterns

- `replay_timeline`
- `load_checkpoint`
- `reconstruct_state`
- `verify_replay_consistency`
- `diff_replayed_output`

Use `replay` only for deterministic historical reproduction, not generic retries.

## `sdk/connector/` — Forge Connector SDK

Purpose: external integration surface for connectors, adapters, and partner/system interoperability.

### Naming Rules

Use `connector`, `integration`, `capability`, `manifest`, `binding`, and `transport` consistently.

Preferred type names:

- `ConnectorManifest`
- `ConnectorCapability`
- `ConnectorBinding`
- `IntegrationClient`
- `ConnectorTransport`

Preferred file names:

- `connector_manifest_schema.py`
- `connector_binding.py`
- `integration_client.py`
- `connector_transport.py`

### Connector Function Patterns

- `load_connector_manifest`
- `validate_connector_capability`
- `bind_connector`
- `negotiate_transport`
- `invoke_connector_operation`

Do not leak internal subsystem terms into SDK contracts unless explicitly part of the public spec.

---

## Cross-Language Conventions

## Python

- Follow PEP 8 with project-specific domain naming above.
- Use type hints on all public functions, methods, and module-level constants where applicable.
- Prefer `dataclass` or explicit typed models for structured data.
- Use `Enum` for finite states and decision types.
- Module-level globals are discouraged except immutable constants.
- Side-effectful code must not run at import time.

### Python Imports

- Standard library
- third-party
- local package imports

Use absolute imports from the repository root package when available. Avoid circular imports by extracting contracts to schema/model modules.

## Swift

- Follow Swift API Design Guidelines.
- Types use `PascalCase`; members use `lowerCamelCase`.
- Prefer value types for immutable state.
- Use `enum` for finite state and typed errors.
- Mark access control explicitly for nontrivial modules.
- Avoid force unwraps except in tightly controlled test-only code.
- Bridge IPC payloads with explicit `Codable` schemas.

---

## Serialization and Schema Conventions

- Every cross-process message must have a named schema/model.
- Do not pass raw dictionaries where a typed schema is appropriate.
- Version serialized contracts explicitly when they may evolve.
- Use stable field names; do not rename serialized keys casually.
- Separate wire schemas from domain models when semantics differ.

Preferred naming:

- `*_schema.py`
- `EventEnvelope`
- `PolicyDecisionPayload`
- `ReplayFrameRecord`

---

## Logging, Audit, and Observability

- Use structured logging only.
- Include subsystem and operation names in every meaningful log.
- Include correlation IDs for multi-step flows.
- Do not log:
  - secrets
  - raw tokens
  - private keys
  - unredacted credentials
  - untrusted generated code bodies unless explicitly permitted by TRD
- Security decisions and policy denials must emit audit events where required by spec.

Preferred field names:

- `subsystem`
- `operation`
- `correlation_id`
- `session_id`
- `policy_id`
- `decision`
- `trust_level`
- `retryable`

---

## Testing Conventions

## Test Layout

Tests must mirror source structure exactly.

Examples:

```text
src/dtl/label_validator.py
tests/dtl/test_label_validator.py

src/mcp/policy_compiler.py
tests/mcp/test_policy_compiler.py
```

## Test Naming

Use descriptive names that capture behavior and condition.

Python:

- `test_validate_label_rejects_missing_origin`
- `test_evaluate_policy_returns_deny_for_untrusted_input`

Swift:

- `testSocketClientRejectsInvalidHandshake()`
- `testTrustZonePanelRendersDeniedState()`

## Test Rules

- Test documented contracts, not incidental implementation.
- Include positive, negative, and boundary cases.
- Add regression tests for every bug fix.
- Security-sensitive code must include failure-mode tests.
- Replay and audit systems require determinism tests.
- Policy engines require explanation and denial-path tests.

---

## Code Patterns to Prefer

## Validation Then Execution

```python
def evaluate_policy(request: PolicyRequest) -> PolicyDecision:
    validate_policy_request(request)
    return policy_engine.evaluate(request)
```

## Boundary Translation

```python
def load_attestation_bundle(raw_payload: bytes) -> AttestationBundle:
    try:
        return attestation_bundle_schema.loads(raw_payload)
    except DecodeError as exc:
        raise SerializationError("invalid attestation bundle payload") from exc
```

## Explicit Decision Objects

```python
@dataclass(frozen=True)
class PolicyDecision:
    effect: PolicyEffect
    reason: str
    rule_id: str
```

## Append-Only Audit Pattern

```python
def append_audit_event(event: AuditEvent) -> None:
    validated = validate_audit_event(event)
    stream_writer.append(validated)
```

---

## Patterns to Avoid

- generic utility dumping grounds
- hidden side effects in model constructors
- broad catch-and-log without rethrow or translation
- silent policy fallback
- implicit trust elevation
- mutable shared state across subsystem boundaries
- schema-less cross-process payloads
- using replay terminology for retry behavior
- using audit terminology for mutable operational logs

---

## Naming Anti-Patterns

Avoid these classes of names:

- vague:
  - `Manager`
  - `Handler`
  - `Processor`
  - `Thing`
- misleading:
  - `TrustedLabel` when trust is only asserted, not verified
  - `SecureClient` without a documented security property
- overloaded:
  - `Context` without qualification
  - `State` without scope
  - `Data` as a primary type name

Prefer:

- `SessionCoordinator`
- `AuditStreamWriter`
- `PolicyEvaluationEngine`
- `LabelValidationResult`

---

## Pull Request and Change Hygiene

- Keep changes scoped to one logical concern.
- Name files and symbols according to subsystem ownership.
- If introducing a new abstraction, document why an existing pattern was insufficient.
- Update tests in the mirrored subsystem path.
- If a serialized contract changes, update schema, compatibility handling, and tests together.
- If a security control changes, verify compliance against the security TRD before merging.

---

## Final Rule

If a name, pattern, or abstraction makes it harder to determine:

- which subsystem owns it
- what contract it implements
- what trust boundary it crosses
- what error it can produce

then it is not acceptable for Forge.