# Code Conventions — Forge Platform

This document defines code conventions, naming rules, and implementation patterns for the full Forge platform. It applies across all subsystems unless a subsystem-specific rule overrides it.

Forge is a two-process platform:
- **Swift shell**: UI, auth, Keychain, local orchestration, IPC/XPC, macOS integration
- **Python backend**: consensus engine, planning, generation, GitHub operations, policy evaluation, trust subsystems

The authoritative product behavior is defined by the TRDs in `forge-docs/`. This document defines how code should be named and structured so implementations remain consistent with those TRDs.

---

## Core Principles

1. **TRDs are the source of truth.**
   - Do not invent interfaces, states, or error semantics not supported by the owning TRD.
   - Before changing a component, read the relevant TRD sections for interfaces, security, and tests.

2. **Security-first implementation.**
   - Treat all external content as untrusted.
   - Never execute generated code.
   - Never log secrets, tokens, raw credentials, or sensitive prompt material.
   - Security-sensitive changes must be consistent with TRD-11.

3. **Deterministic, inspectable behavior.**
   - Prefer explicit state machines, typed payloads, and structured logs.
   - Avoid hidden side effects.
   - Make failure modes observable and testable.

4. **Clear ownership boundaries.**
   - Swift owns UI, auth, local secrets, and OS integration.
   - Python owns intelligence, orchestration, provider interaction, and repository automation.
   - Cross-process APIs must be versioned, typed, and minimal.

5. **Tests mirror production structure.**
   - Test paths mirror `src/` paths exactly.
   - Add or update tests with every behavior change unless the TRD explicitly says otherwise.

---

## File and Directory Naming (exact `src/` layout)

Use lowercase directory names. Prefer short, stable subsystem names. Tests must mirror `src/` structure exactly.

### Required top-level subsystem layout

```text
src/
  cal/           # Conversation Abstraction Layer components
  dtl/           # Data Trust Label components
  trustflow/     # TrustFlow audit stream components
  vtz/           # Virtual Trust Zone enforcement
  trustlock/     # Cryptographic machine identity (TPM-anchored)
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
```

### General directory rules

- Directory names are **lowercase**.
- Use **singular conceptual names** for modules unless the subsystem is already pluralized by design.
- Keep nesting shallow unless the TRD defines layered boundaries.
- Group by domain and responsibility, not by arbitrary technical type.

### Python file naming

Use `snake_case.py`.

Preferred patterns:
- `models.py` — typed data models for a module
- `service.py` or `<domain>_service.py` — orchestration/service layer
- `adapter.py` or `<provider>_adapter.py` — external/provider integration
- `client.py` — outbound client
- `server.py` — inbound server
- `policy.py` — policy evaluation logic
- `validator.py` — validation rules
- `repository.py` — persistence abstraction
- `store.py` — storage implementation
- `parser.py` — parsing logic
- `serializer.py` — serialization logic
- `runner.py` — bounded execution coordinator
- `state.py` — state machine/state definitions
- `errors.py` — typed exceptions for the module
- `constants.py` — constants only when justified
- `types.py` — shared aliases/protocol-like typing only when `models.py` is not appropriate

Avoid:
- `utils.py`
- `helpers.py`
- `misc.py`
- `common.py`

If functionality seems to require one of those files, split by responsibility instead.

### Swift file naming

Use `PascalCase.swift`.

Preferred patterns:
- `AuthManager.swift`
- `SocketBridge.swift`
- `SessionCoordinator.swift`
- `ProviderStatusView.swift`
- `TrustFlowPanel.swift`
- `PolicyDecision.swift`
- `KeychainStore.swift`

Protocol files may be named:
- `SessionControlling.swift`
- `SocketTransporting.swift`

SwiftUI view files must be named after the primary view type in the file.

### Test file naming

Python tests:
- `tests/<subsystem>/test_<module>.py`
- Example: `tests/mcp/test_policy_engine.py`

Swift tests:
- Match the type or feature under test
- Example: `TrustFlowPanelTests.swift`, `SocketBridgeTests.swift`

Property, fixture, and integration test modules may be further scoped:
- `test_policy_engine_unit.py`
- `test_policy_engine_integration.py`

### Documentation and schema naming

- Markdown docs: `UPPERCASE.md` only for repository control docs such as `README.md`, `AGENTS.md`, `CLAUDE.md`, `CONVENTIONS.md`
- Schema/spec payloads: `snake_case.json`, `snake_case.yaml`
- Example fixtures: `snake_case.fixture.json` if fixture type needs to be explicit

---

## Class and Function Naming

Naming should communicate responsibility, side effects, and abstraction level.

### General rules

- Classes, structs, enums, protocols, and Swift actors: `PascalCase`
- Python functions, methods, variables, modules: `snake_case`
- Swift functions, methods, properties, parameters: `lowerCamelCase`
- Constants:
  - Python module constants: `UPPER_SNAKE_CASE`
  - Swift static constants: `lowerCamelCase` unless bridged from external standards

### Type naming

Use nouns for data and service types:
- `ConsensusEngine`
- `PolicyDecision`
- `TrustLabel`
- `ReplaySession`
- `AuditEvent`
- `ConnectorClient`

Use adjective/noun or verb-capable suffixes for protocols/interfaces:
- Swift protocols:
  - `SessionCoordinating`
  - `TokenProviding`
  - `PolicyEvaluating`
- Python abstract interfaces / protocols:
  - `PolicyEvaluator`
  - `EventSink`
  - `ReplayStore`

### Function naming

Use verbs for functions and methods.

Good:
- `load_trds()`
- `evaluate_policy()`
- `emit_audit_event()`
- `build_pull_request_plan()`
- `open_draft_pr()`
- `verify_machine_identity()`
- `replay_session()`

Avoid vague verbs:
- `handle()`
- `process()`
- `do_work()`
- `run()` unless execution semantics are obvious from the type

### Boolean naming

Use affirmative, predicate-style names.

Python:
- `is_trusted`
- `has_required_scope`
- `can_open_pr`
- `should_redact`

Swift:
- `isTrusted`
- `hasRequiredScope`
- `canOpenPR`
- `shouldRedact`

Avoid negated names such as:
- `isNotTrusted`
- `notAllowed`

### Factory and constructor naming

Use explicit creation names when constructors alone are not clear:
- `from_payload()`
- `from_envelope()`
- `from_repository_path()`
- `makeSocketClient()`
- `makeDefaultPolicyEngine()`

### Async naming

Python:
- Do not suffix every async function with `_async`.
- Use clear verbs and rely on the async definition itself.

Swift:
- Do not add `Async` suffix unless it disambiguates from a sync overload.

### Event and message naming

Use nouns for event types:
- `AuditEvent`
- `ConsensusStarted`
- `PolicyDenied`
- `ReplayCheckpointCreated`

Use verb-past-participle or state-transition phrasing for event names/keys:
- `session_started`
- `pull_request_opened`
- `policy_denied`
- `replay_restored`

---

## Error and Exception Patterns

Errors must be typed, structured, and non-leaky. Every module should expose a clear error contract.

### General rules

- Never raise or propagate bare `Exception` in Python unless immediately wrapping unknown failures.
- Never use stringly-typed error matching as the primary control flow.
- Map external/provider/library failures into Forge-owned error types at module boundaries.
- Error messages must be safe for logs and UI.
- Include machine-readable codes where the TRD requires them.

### Python exception conventions

Define module-specific exceptions in `errors.py`.

Pattern:
```python
class ForgeError(Exception):
    """Base error for Forge backend."""
```

Subsystem-specific pattern:
```python
class PolicyError(ForgeError):
    """Base error for MCP policy failures."""

class PolicyValidationError(PolicyError):
    """Policy input failed validation."""

class PolicyDeniedError(PolicyError):
    """Policy evaluation denied the requested action."""
```

Rules:
- Use `...Error` suffix for all exceptions.
- Create a subsystem base exception first, then specific subclasses.
- Keep exceptions semantic, not transport-specific, unless the transport is the module concern.
- Preserve original exceptions with `raise ... from exc`.

Example:
```python
try:
    response = client.send(request)
except TimeoutError as exc:
    raise ProviderTimeoutError("provider request timed out") from exc
```

### Swift error conventions

Use `Error`-conforming enums for bounded error domains.

Example:
```swift
enum SocketBridgeError: Error {
    case invalidEnvelope
    case authenticationFailed
    case connectionClosed
}
```

Use structs for rich, payload-bearing errors only when needed by the TRD:
```swift
struct PolicyViolationError: Error {
    let code: String
    let message: String
}
```

Rules:
- Use `...Error` suffix for custom error types.
- Prefer enums over free-form error wrappers.
- Keep user-display strings separate from internal debug descriptions.
- Do not expose provider raw errors directly to UI surfaces.

### Error codes

When a module has stable error codes:
- Use a namespaced, uppercase convention
- Format: `SUBSYSTEM_REASON`
- Examples:
  - `MCP_POLICY_DENIED`
  - `VTZ_BOUNDARY_VIOLATION`
  - `TRUSTLOCK_ATTESTATION_FAILED`
  - `CAL_INVALID_MESSAGE`

If both an exception type and code are present:
- Exception type models program behavior
- Error code models telemetry/API contract

### Result handling

- Prefer explicit `Result`-style returns only where the language or subsystem benefits from them.
- Do not mix exceptions and result objects arbitrarily within the same layer.
- Boundary layers may convert exceptions into:
  - JSON error envelopes
  - API responses
  - UI-safe state models

### Logging and errors

- Log structured context, not raw payload dumps.
- Never log:
  - secrets
  - tokens
  - key material
  - full prompts if sensitive
  - full generated code when disallowed by TRD/security policy
- Include correlation identifiers where available.

---

## Per-Subsystem Naming Rules

This section defines naming patterns for all major Forge subsystems.

---

### `src/cal/` — Conversation Abstraction Layer

Purpose: normalized message, turn, session, and provider conversation abstractions.

#### Directory and file patterns

```text
src/cal/
  models.py
  session.py
  message_mapper.py
  envelope.py
  provider_adapter.py
  validator.py
  errors.py
```

#### Naming rules

Types:
- `ConversationSession`
- `ConversationTurn`
- `ConversationMessage`
- `MessageEnvelope`
- `ProviderMessageAdapter`
- `ConversationValidator`

Functions:
- `create_session()`
- `append_turn()`
- `normalize_message()`
- `serialize_envelope()`
- `parse_envelope()`
- `validate_turn_sequence()`

Enums / constants:
- `MessageRole`
- `TurnState`
- `EnvelopeVersion`

Errors:
- `ConversationError`
- `InvalidMessageError`
- `EnvelopeValidationError`
- `UnsupportedRoleError`

Rules:
- Use `message` for atomic content units.
- Use `turn` for one request/response interaction.
- Use `session` for full conversation state.
- Use `envelope` for transport-safe wrapped payloads.
- Adapter types must end in `Adapter`.

---

### `src/dtl/` — Data Trust Label

Purpose: classify, attach, propagate, and validate trust labels for data objects.

#### Directory and file patterns

```text
src/dtl/
  models.py
  labeler.py
  propagation.py
  validator.py
  policy_mapping.py
  errors.py
```

#### Naming rules

Types:
- `TrustLabel`
- `TrustLevel`
- `LabelAssignment`
- `LabelPropagationRule`
- `TrustClassification`

Functions:
- `assign_label()`
- `propagate_label()`
- `merge_labels()`
- `validate_label_transition()`
- `map_label_to_policy()`

Errors:
- `TrustLabelError`
- `InvalidTrustLabelError`
- `LabelPropagationError`
- `TrustLevelConflictError`

Rules:
- Use `label` for the attached metadata object.
- Use `trust_level` for scalar classification dimensions.
- Use `classification` for inference/decision logic.
- Transition validation methods must use `validate_*_transition` naming.

---

### `src/trustflow/` — TrustFlow audit stream

Purpose: append-only trust/audit events, traceability, and event inspection.

#### Directory and file patterns

```text
src/trustflow/
  models.py
  event_stream.py
  emitter.py
  sink.py
  serializer.py
  query.py
  errors.py
```

#### Naming rules

Types:
- `AuditEvent`
- `TrustEvent`
- `EventStream`
- `EventEmitter`
- `EventSink`
- `EventQuery`
- `EventCursor`

Functions:
- `emit_event()`
- `append_event()`
- `serialize_event()`
- `query_events()`
- `load_from_cursor()`

Errors:
- `TrustFlowError`
- `AuditWriteError`
- `EventSerializationError`
- `InvalidEventCursorError`

Rules:
- Use `event` for immutable audit records.
- Use `stream` for append/query abstractions.
- Use `sink` for storage/output targets.
- Event names in payloads should be `snake_case`.

---

### `src/vtz/` — Virtual Trust Zone

Purpose: enforce trust boundaries, isolation zones, and cross-zone policy checks.

#### Directory and file patterns

```text
src/vtz/
  models.py
  zone.py
  boundary.py
  enforcement.py
  policy_bridge.py
  validator.py
  errors.py
```

#### Naming rules

Types:
- `VirtualTrustZone`
- `TrustBoundary`
- `ZoneContext`
- `BoundaryRule`
- `ZoneEnforcer`
- `BoundaryValidator`

Functions:
- `enter_zone()`
- `exit_zone()`
- `validate_boundary_crossing()`
- `enforce_zone_policy()`
- `resolve_zone_context()`

Errors:
- `VirtualTrustZoneError`
- `BoundaryViolationError`
- `ZoneResolutionError`
- `ZonePolicyError`

Rules:
- Use `zone` for logical trust regions.
- Use `boundary` for crossing logic and constraints.
- Use `enforcer` for active control components.
- Security violations must use explicit `...ViolationError` names when applicable.

---

### `src/trustlock/` — Cryptographic machine identity

Purpose: TPM-anchored or hardware-backed machine identity, attestation, and key lifecycle.

#### Directory and file patterns

```text
src/trustlock/
  models.py
  identity.py
  attestation.py
  key_store.py
  verifier.py
  enrollment.py
  errors.py
```

#### Naming rules

Types:
- `MachineIdentity`
- `IdentityClaim`
- `AttestationBundle`
- `AttestationVerifier`
- `KeyStore`
- `EnrollmentRecord`

Functions:
- `generate_machine_identity()`
- `create_attestation()`
- `verify_attestation()`
- `load_key_material()`
- `rotate_identity_key()`
- `enroll_machine()`

Errors:
- `TrustLockError`
- `AttestationError`
- `AttestationVerificationError`
- `KeyMaterialUnavailableError`
- `EnrollmentError`

Rules:
- Use `attestation` for signed proof artifacts.
- Use `identity` for persistent machine identity concepts.
- Use `key_material` only for internal secure key references; never expose raw key bytes casually.
- Secret-bearing implementations must separate metadata from secure storage accessors.

---

### `src/mcp/` — MCP Policy Engine

Purpose: policy loading, compilation, evaluation, and decisioning.

#### Directory and file patterns

```text
src/mcp/
  models.py
  policy_engine.py
  evaluator.py
  compiler.py
  registry.py
  decision.py
  errors.py
```

#### Naming rules

Types:
- `PolicyEngine`
- `PolicyEvaluator`
- `PolicyCompiler`
- `PolicyRegistry`
- `PolicyDecision`
- `PolicyInput`
- `PolicyRule`

Functions:
- `load_policy()`
- `compile_policy()`
- `evaluate_policy()`
- `register_policy()`
- `explain_decision()`

Errors:
- `PolicyError`
- `PolicyCompilationError`
- `PolicyEvaluationError`
- `PolicyDeniedError`
- `PolicyRegistryError`

Rules:
- Use `decision` for evaluation outputs.
- Use `rule` for individual policy clauses.
- Use `registry` for indexed policy lookup.
- Denials should be modeled distinctly from malformed inputs.

---

### `src/rewind/` — Forge Rewind replay engine

Purpose: replay, checkpoint, restore, and deterministic reconstruction of prior execution.

#### Directory and file patterns

```text
src/rewind/
  models.py
  replay_engine.py
  checkpoint.py
  recorder.py
  restorer.py
  timeline.py
  errors.py
```

#### Naming rules

Types:
- `ReplayEngine`
- `ReplaySession`
- `ReplayCheckpoint`
- `ExecutionTimeline`
- `StateRecorder`
- `StateRestorer`

Functions:
- `start_replay()`
- `replay_session()`
- `create_checkpoint()`
- `restore_checkpoint()`
- `record_transition()`
- `rebuild_timeline()`

Errors:
- `RewindError`
- `ReplayError`
- `CheckpointNotFoundError`
- `TimelineCorruptionError`
- `RestoreError`

Rules:
- Use `replay` for deterministic re-execution.
- Use `checkpoint` for persisted restore points.
- Use `timeline` for ordered event/state history.
- Corruption-related failures must be named explicitly.

---

### `sdk/connector/` — Forge Connector SDK

Purpose: external integration SDK for Forge-compatible connectors.

#### Directory and file patterns

```text
sdk/connector/
  client.py
  server.py
  models.py
  auth.py
  transport.py
  registry.py
  errors.py
```

#### Naming rules

Types:
- `ConnectorClient`
- `ConnectorServer`
- `ConnectorRequest`
- `ConnectorResponse`
- `ConnectorTransport`
- `ConnectorRegistry`
- `ConnectorCredentials`

Functions:
- `send_request()`
- `handle_request()`
- `register_connector()`
- `authenticate_connector()`
- `serialize_response()`

Errors:
- `ConnectorError`
- `ConnectorAuthenticationError`
- `ConnectorTransportError`
- `UnsupportedConnectorOperationError`

Rules:
- Public SDK names must be stable and explicit.
- Avoid leaking internal subsystem names into external SDK APIs unless required by the TRD.
- Backward compatibility matters more in `sdk/` than in internal modules.

---

## Cross-Process Interface Conventions

Forge includes Swift and Python processes communicating over authenticated local IPC.

### Message schema naming

Use explicit envelope names:
- `RequestEnvelope`
- `ResponseEnvelope`
- `EventEnvelope`

JSON fields use `snake_case`.

Preferred field names:
- `message_id`
- `correlation_id`
- `session_id`
- `request_type`
- `event_type`
- `payload`
- `error`
- `timestamp`
- `schema_version`

### IPC method naming

Use action-oriented request types:
- `start_session`
- `evaluate_policy`
- `open_pull_request`
- `emit_audit_event`
- `replay_execution`

Avoid generic types like:
- `command`
- `action1`

### Serialization rules

- Cross-process payloads must be versioned.
- Enums crossing process boundaries must serialize to stable string values.
- Missing or invalid required fields must fail closed.

---

## State Machine Conventions

Where the TRD defines states, model them explicitly.

### Naming

State enums:
- `SessionState`
- `ReplayState`
- `PolicyEvaluationState`

Transition functions:
- `transition_to_*`
- `advance_*`
- `validate_*_transition`

Examples:
- `transition_to_review()`
- `advance_replay_state()`
- `validate_session_transition()`

### Rules

- Do not encode critical state as ad hoc booleans when a finite state enum is appropriate.
- Validate illegal transitions centrally.
- Side effects should occur in orchestration layers, not inside passive state models.

---

## Model and DTO Conventions

### Data model naming

Use:
- `...Model` only when necessary to disambiguate framework-specific usage.
- Plain domain nouns are preferred:
  - `PolicyDecision` over `PolicyDecisionModel`
  - `AuditEvent` over `AuditEventData`

### Input/output models

Use explicit suffixes when crossing boundaries:
- `PolicyEvaluationRequest`
- `PolicyEvaluationResponse`
- `AuditEventPayload`
- `ConnectorRegistrationInput`

### Persistence models

If persistence shape differs from domain shape, suffix with:
- `Record`
- `Row`
- `Document`

Examples:
- `AuditEventRecord`
- `CheckpointDocument`

---

## Logging and Telemetry Naming

### Logger naming

Use module-scoped loggers.

Python:
```python
logger = logging.getLogger(__name__)
```

Swift:
- Prefer subsystem/category naming aligned with bundle and module.

### Field naming

Structured log fields use `snake_case` even in Swift-emitted JSON logs.

Examples:
- `session_id`
- `policy_id`
- `zone_id`
- `trust_level`
- `error_code`

### Event naming

Telemetry/audit events should be:
- short
- stable
- past-tense or transition-oriented

Examples:
- `policy_evaluated`
- `attestation_verified`
- `checkpoint_restored`
- `boundary_violation_detected`

---

## Testing Conventions

### Structure

Tests mirror `src/` exactly.

Examples:
```text
src/mcp/policy_engine.py
tests/mcp/test_policy_engine.py

src/trustflow/emitter.py
tests/trustflow/test_emitter.py
```

### Naming

Test function names:
- `test_<behavior>_<condition>_<expected_result>`

Examples:
- `test_evaluate_policy_when_input_is_denied_returns_denial_decision`
- `test_restore_checkpoint_when_checkpoint_missing_raises_error`

Swift test naming:
- `test<Behavior><Condition><ExpectedResult>()`

Examples:
- `testSocketBridgeWhenEnvelopeInvalidThrowsError()`
- `testTrustFlowPanelWhenNoEventsShowsEmptyState()`

### Rules

- One behavioral concern per test.
- Use fixtures/builders for complex trust and policy objects.
- Security-sensitive regression tests must be explicit and named clearly.
- Add tests for error contracts and redaction behavior.

---

## Anti-Patterns

Do not introduce the following:

- `utils.py`, `helpers.py`, `common.py`, `misc.py`
- God objects such as `Manager` or `Service` that own unrelated responsibilities
- Bare dictionaries where typed models are expected
- Stringly-typed state or policy decisions
- Cross-subsystem imports that bypass defined boundaries
- Catch-all exception swallowing
- Logging raw external payloads without redaction review
- Naming that exposes implementation accidents rather than domain intent

Bad examples:
- `src/mcp/utils.py`
- `def process(data): ...`
- `class DataManager: ...` for unrelated policy + storage + network behavior
- `status = "ok"` when an enum/typed decision exists

---

## Naming Decision Checklist

Before finalizing a new file or type, verify:

- Does the name match the owning TRD terminology?
- Is the responsibility clear from the name alone?
- Does the name describe domain meaning, not implementation trivia?
- Does it fit existing subsystem patterns?
- Is the failure mode typed and named clearly?
- Will the mirrored test file/path be obvious?

If any answer is no, rename before merging.

---

## Summary

Forge code must be:
- TRD-aligned
- security-conscious
- strongly named
- boundary-respecting
- test-mirrored
- explicit in states, errors, and payloads

When choosing names:
- prefer domain nouns for types
- prefer precise verbs for functions
- prefer typed errors over generic failures
- mirror `src/` in `tests/`
- keep subsystem terminology consistent across Swift, Python, schemas, and logs