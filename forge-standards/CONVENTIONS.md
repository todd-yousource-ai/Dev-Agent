# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, and code patterns for the full Forge platform. It applies across all subsystems unless a subsystem-specific rule overrides it.

The Forge platform includes:

- Swift shell/UI process
- Python backend services
- Security, trust, audit, and policy subsystems
- SDK components
- Test suites
- Supporting tooling

The authoritative product and architecture requirements live in the TRDs under `forge-docs/`. This document defines implementation conventions, not product behavior. If a convention conflicts with a TRD, follow the TRD.

---

## Core Principles

1. **TRDs are source of truth.**
   - Read the owning TRD before changing any component.
   - Do not infer behavior when interfaces, state machines, or security controls are defined in a TRD.

2. **Security-sensitive code is explicit.**
   - Never hide security decisions in helpers with vague names.
   - Validation, authorization, sanitization, signing, identity binding, and trust decisions must be obvious in code.

3. **Generated code is never executed automatically.**
   - Treat generated artifacts as untrusted until validated through the required platform flow.

4. **Names must reveal ownership and trust boundaries.**
   - A reader should be able to identify whether code belongs to CAL, DTL, TrustFlow, VTZ, TrustLock, MCP, Rewind, SDK, Swift shell, or Python backend from filenames, symbols, and module layout.

5. **Tests mirror implementation layout.**
   - Test paths and names must map directly to the code they validate.

6. **Prefer boring code.**
   - Use predictable naming, small units, explicit types, narrow interfaces, and stable error contracts.

---

## File and Directory Naming (exact `src/` layout)

### Top-level source layout

The following directories are reserved and must be used exactly as named:

```text
src/cal/           - Conversation Abstraction Layer components
src/dtl/           - Data Trust Label components
src/trustflow/     - TrustFlow audit stream components
src/vtz/           - Virtual Trust Zone enforcement
src/trustlock/     - Cryptographic machine identity (TPM-anchored)
src/mcp/           - MCP Policy Engine
src/rewind/        - Forge Rewind replay engine
sdk/connector/     - Forge Connector SDK
tests/<subsystem>/ - Tests mirror src/ structure exactly
```

### Required layout rules

- Do not create alternate abbreviations or aliases for subsystem directories.
  - Correct: `src/trustflow/`
  - Incorrect: `src/tf/`, `src/trust_flow/`, `src/auditstream/`

- Use lowercase directory names only.

- Use singular subsystem roots exactly as listed above.

- Tests must mirror the implementation path structure.
  - Example:
    - Source: `src/dtl/label_evaluator.py`
    - Test: `tests/dtl/test_label_evaluator.py`

- Shared internal helpers must live under the owning subsystem, not a generic dumping ground.
  - Correct: `src/vtz/_path_guard.py`
  - Avoid: `src/common/helpers.py`

- If cross-subsystem shared code is necessary, place it in an explicitly named shared package with a domain-specific name and documented ownership. Do not introduce vague directories such as:
  - `utils/`
  - `helpers/`
  - `misc/`
  - `stuff/`

### File naming rules

#### Python

- Use `snake_case.py` for all Python filenames.
- Module filenames must describe domain behavior, not implementation trivia.
  - Correct:
    - `policy_evaluator.py`
    - `audit_event_writer.py`
    - `replay_session_store.py`
  - Incorrect:
    - `utils.py`
    - `manager.py`
    - `helpers.py`
    - `misc_logic.py`

- Prefix internal-only modules with a single underscore only when the module is not part of the subsystem’s public surface.
  - Example: `_socket_framing.py`

#### Swift

- Use `PascalCase.swift` for type-centric files.
- File name must match the primary type defined in the file.
  - `ConsensusSessionView.swift`
  - `TrustFlowEventStore.swift`

- For extensions, use:
  - `TypeName+Concern.swift`
  - Examples:
    - `URLRequest+AuthHeaders.swift`
    - `DataTrustLabel+Formatting.swift`

- For protocol conformances, use:
  - `TypeName+ProtocolName.swift`
  - Example:
    - `PolicyDecision+Codable.swift`

- For SwiftUI view fragments, use names ending in `View`, `Panel`, `Card`, `Row`, or `Section` as appropriate.

### Directory layering inside subsystems

Within each subsystem, use explicit domain folders where needed:

```text
src/<subsystem>/
  models/
  services/
  adapters/
  policies/
  storage/
  transport/
  validators/
  serializers/
```

Only create a subdirectory when it groups multiple related files. Do not create deep nesting for one or two files.

Recommended maximum depth under a subsystem root: 3 levels unless a TRD-defined structure requires more.

---

## Class and Function Naming

### General rules

- Names must be domain-specific and intention-revealing.
- Prefer nouns for types, verbs for actions, adjectives only for predicates or value semantics.
- Avoid vague suffixes:
  - `Manager`
  - `Helper`
  - `Processor`
  - `Thing`
  - `Object`

Use a more precise name:
- `AuditEventWriter`
- `TrustZonePolicyEvaluator`
- `ReplaySessionLoader`
- `MachineIdentityAttestor`

### Python naming

- Classes: `PascalCase`
- Functions and methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Variables: `snake_case`
- Private/internal attributes: leading single underscore
- Internal module constants: leading underscore if not exported

Examples:

```python
class PolicyDecisionRecord:
    pass

def evaluate_policy_bundle(bundle, request_context):
    pass

MAX_REPLAY_EVENTS = 10_000
```

### Swift naming

- Types, protocols, enums: `PascalCase`
- Functions, methods, properties, enum cases: `camelCase`
- Static constants: `camelCase`
- Acronyms should be readable, not fully shouted:
  - Prefer `JsonLineEncoder` over `JSONLINEEncoder`
  - Prefer `XpcSession` over `XPCSESSION`

### Naming by role

#### Types

Use these suffixes consistently where applicable:

- `Request` — input command/query payload
- `Response` — output payload
- `Result` — operation result object, only when not conflicting with language/library `Result`
- `Record` — persisted or logged data model
- `Event` — immutable domain event
- `Entry` — append-only stream item
- `Snapshot` — point-in-time state capture
- `State` — state machine state
- `Error` — error type
- `Validator` — validation component
- `Evaluator` — rule/policy/decision logic
- `Resolver` — lookup plus selection logic
- `Writer` — append/persist behavior
- `Reader` — load/query behavior
- `Store` — durable storage abstraction
- `Repository` — aggregate-oriented storage access
- `Adapter` — boundary implementation for external system/protocol
- `Client` — outbound API/network caller
- `Session` — stateful interaction scope
- `Coordinator` — orchestration across multiple components
- `Factory` — construction abstraction when needed
- `Builder` — staged object assembly
- `Formatter` — presentation formatting only
- `Serializer` / `Deserializer` — wire/storage transformation only

#### Functions

Use verb-led names:

- `load_trust_labels`
- `evaluate_request`
- `append_audit_event`
- `derive_machine_identity`
- `attest_platform_state`
- `replay_session`
- `validate_connector_manifest`

Boolean functions and properties must read as predicates:

- `is_trusted`
- `has_required_scope`
- `can_replay`
- `should_rotate_key`

Avoid ambiguous verbs:
- `handle`
- `process`
- `do`
- `run`
- `manage`

Unless the surrounding type makes the operation exact and unambiguous.

---

## Error and Exception Patterns

### General requirements

- Errors must be typed, structured, and stable.
- Every subsystem must expose a small set of explicit domain errors.
- Error messages must be actionable but must not leak secrets, credentials, raw tokens, private keys, or sensitive payload contents.

### Python

- Define subsystem-specific exception hierarchies.
- All custom exceptions must inherit from a subsystem root exception.

Example:

```python
class DtlError(Exception):
    """Base exception for DTL subsystem."""


class LabelValidationError(DtlError):
    """Raised when a trust label is structurally or semantically invalid."""


class LabelAuthorizationError(DtlError):
    """Raised when access to a trust-labeled resource is not permitted."""
```

Rules:

- Raise specific exceptions, not generic `Exception`.
- Catch at trust boundaries, transport boundaries, and top-level orchestration boundaries.
- Do not swallow exceptions silently.
- If translating an exception, preserve the cause.
  - `raise LabelValidationError("invalid label checksum") from exc`

### Swift

- Define `Error`-conforming enums for domain failures.
- Use precise cases with associated values where useful and safe.

Example:

```swift
enum TrustFlowError: Error {
    case invalidEventSequence(streamId: String)
    case unauthorizedAppend
    case storageUnavailable
}
```

Rules:

- Do not use stringly-typed error dispatch.
- Avoid `NSError` unless bridging with Apple APIs requires it.
- Expose user-facing errors separately from internal diagnostics where appropriate.

### Error naming conventions

Use these suffixes consistently:

- `ValidationError`
- `AuthorizationError`
- `AuthenticationError`
- `TimeoutError`
- `ConflictError`
- `NotFoundError`
- `SerializationError`
- `TransportError`
- `PolicyError`
- `AttestationError`
- `ReplayError`

### Logging and errors

- Log structured context, not raw sensitive payloads.
- Include identifiers, correlation IDs, subsystem names, and operation names where permitted.
- Never log:
  - access tokens
  - refresh tokens
  - private keys
  - full certificate contents unless explicitly allowed
  - raw user secrets
  - unredacted generated code if policy forbids it
  - protected trust labels unless the TRD explicitly permits it

### Error translation pattern

Translate low-level errors into subsystem errors at subsystem boundaries.

Example:

```python
try:
    row = storage.load(label_id)
except sqlite3.DatabaseError as exc:
    raise LabelStoreError("failed to load trust label record") from exc
```

---

## Per-Subsystem Naming Rules

---

### `src/cal/` — Conversation Abstraction Layer

Purpose: conversation/session abstraction, message normalization, model/provider interaction boundaries, and conversation-safe orchestration surfaces.

#### File naming

Use names such as:

- `conversation_session.py`
- `message_normalizer.py`
- `provider_request.py`
- `provider_response.py`
- `conversation_context_store.py`

Avoid:

- `chat.py`
- `llm_utils.py`
- `wrapper.py`

#### Type naming

Preferred type names:

- `ConversationSession`
- `ConversationMessage`
- `NormalizedMessage`
- `ProviderRequest`
- `ProviderResponse`
- `ConversationContext`
- `ConversationTurnRecord`
- `ModelSelectionPolicy`

#### Function naming

- `normalize_message_batch`
- `build_provider_request`
- `parse_provider_response`
- `append_conversation_turn`
- `truncate_context_window`

#### Error naming

- `CalError`
- `ConversationStateError`
- `ProviderProtocolError`
- `MessageNormalizationError`
- `ContextWindowOverflowError`

---

### `src/dtl/` — Data Trust Label

Purpose: trust labels, classification metadata, label derivation, validation, enforcement hooks, and label-aware access logic.

#### File naming

Use names such as:

- `trust_label.py`
- `label_schema.py`
- `label_evaluator.py`
- `label_validator.py`
- `label_binding.py`
- `label_resolution.py`

Avoid:

- `labels.py`
- `data_utils.py`
- `security_helper.py`

#### Type naming

Preferred type names:

- `DataTrustLabel`
- `TrustLabelSchema`
- `LabelBinding`
- `LabelConstraint`
- `LabelEvaluator`
- `LabelValidator`
- `LabelResolutionResult`

#### Function naming

- `validate_trust_label`
- `bind_label_to_artifact`
- `resolve_effective_label`
- `evaluate_label_constraints`
- `redact_label_fields`

#### Error naming

- `DtlError`
- `LabelValidationError`
- `LabelBindingError`
- `LabelResolutionError`
- `LabelConstraintError`

---

### `src/trustflow/` — TrustFlow audit stream

Purpose: append-only audit streams, event integrity, trust lineage, audit serialization, and verifiable event sequencing.

#### File naming

Use names such as:

- `audit_event.py`
- `audit_entry.py`
- `audit_stream_writer.py`
- `audit_stream_reader.py`
- `event_sequencer.py`
- `lineage_verifier.py`

Avoid:

- `audit_utils.py`
- `stream_manager.py`
- `events.py`

#### Type naming

Preferred type names:

- `AuditEvent`
- `AuditEntry`
- `AuditStreamWriter`
- `AuditStreamReader`
- `EventSequence`
- `LineageVerifier`
- `TrustLineageRecord`

#### Function naming

- `append_audit_event`
- `read_audit_range`
- `verify_event_lineage`
- `seal_audit_batch`
- `compute_event_digest`

#### Error naming

- `TrustFlowError`
- `AuditAppendError`
- `EventSequenceError`
- `LineageVerificationError`
- `AuditSerializationError`

---

### `src/vtz/` — Virtual Trust Zone

Purpose: isolation boundaries, execution constraints, path/resource restrictions, trust zone enforcement, and zone state verification.

#### File naming

Use names such as:

- `trust_zone.py`
- `zone_policy.py`
- `zone_enforcer.py`
- `path_guard.py`
- `resource_boundary.py`
- `zone_state.py`

Avoid:

- `sandbox.py` unless the TRD explicitly uses that term
- `guardrails.py`
- `zone_utils.py`

#### Type naming

Preferred type names:

- `VirtualTrustZone`
- `TrustZonePolicy`
- `TrustZoneEnforcer`
- `PathGuard`
- `ResourceBoundary`
- `ZoneStateSnapshot`

#### Function naming

- `enforce_zone_policy`
- `validate_zone_path_access`
- `capture_zone_state`
- `deny_cross_zone_access`
- `is_path_within_zone`

#### Error naming

- `VtzError`
- `ZonePolicyError`
- `ZoneBoundaryError`
- `ZoneStateError`
- `PathAccessError`

---

### `src/trustlock/` — Cryptographic machine identity

Purpose: TPM-anchored or hardware-rooted machine identity, attestation, key lifecycle, binding, and identity verification.

#### File naming

Use names such as:

- `machine_identity.py`
- `identity_attestor.py`
- `attestation_bundle.py`
- `key_derivation.py`
- `key_rotation.py`
- `platform_measurement.py`

Avoid:

- `crypto.py`
- `tpm_utils.py`
- `identity_manager.py`

#### Type naming

Preferred type names:

- `MachineIdentity`
- `MachineIdentityAttestor`
- `AttestationBundle`
- `PlatformMeasurement`
- `KeyDerivationPolicy`
- `KeyRotationRecord`

#### Function naming

- `derive_machine_identity`
- `attest_platform_state`
- `verify_attestation_bundle`
- `rotate_identity_key`
- `load_platform_measurements`

#### Error naming

- `TrustLockError`
- `AttestationError`
- `MachineIdentityError`
- `KeyRotationError`
- `MeasurementVerificationError`

---

### `src/mcp/` — MCP Policy Engine

Purpose: policy definition, compilation, evaluation, decisioning, enforcement integration, and explainable policy results.

#### File naming

Use names such as:

- `policy_bundle.py`
- `policy_rule.py`
- `policy_evaluator.py`
- `policy_decision.py`
- `policy_compiler.py`
- `decision_explainer.py`

Avoid:

- `engine.py`
- `policy_utils.py`
- `rules.py`

#### Type naming

Preferred type names:

- `PolicyBundle`
- `PolicyRule`
- `PolicyEvaluator`
- `PolicyDecision`
- `PolicyDecisionTrace`
- `PolicyCompilationResult`
- `DecisionExplainer`

#### Function naming

- `compile_policy_bundle`
- `evaluate_policy_request`
- `explain_policy_decision`
- `resolve_policy_inputs`
- `enforce_policy_decision`

#### Error naming

- `McpError`
- `PolicyCompilationError`
- `PolicyEvaluationError`
- `PolicyConflictError`
- `DecisionTraceError`

---

### `src/rewind/` — Forge Rewind replay engine

Purpose: replay, deterministic reconstruction, timeline inspection, artifact restoration, and session/event rehydration.

#### File naming

Use names such as:

- `replay_session.py`
- `timeline_cursor.py`
- `event_rehydrator.py`
- `artifact_restorer.py`
- `replay_snapshot.py`
- `determinism_verifier.py`

Avoid:

- `replay_utils.py`
- `rewind_manager.py`
- `timeline.py` if multiple timeline concepts exist

#### Type naming

Preferred type names:

- `ReplaySession`
- `ReplaySnapshot`
- `TimelineCursor`
- `EventRehydrator`
- `ArtifactRestorer`
- `DeterminismVerifier`

#### Function naming

- `replay_session`
- `restore_artifact_state`
- `rehydrate_event_sequence`
- `verify_replay_determinism`
- `seek_timeline_offset`

#### Error naming

- `RewindError`
- `ReplayError`
- `RehydrationError`
- `ArtifactRestoreError`
- `DeterminismError`

---

### `sdk/connector/` — Forge Connector SDK

Purpose: external connector interfaces, integration contracts, manifest/schema validation, outbound bridge APIs, and connector lifecycle support.

#### File naming

Use names such as:

- `connector_client.py`
- `connector_manifest.py`
- `manifest_validator.py`
- `connector_session.py`
- `capability_descriptor.py`
- `bridge_transport.py`

Avoid:

- `sdk_utils.py`
- `client_helpers.py`
- `integration_manager.py`

#### Type naming

Preferred type names:

- `ConnectorClient`
- `ConnectorManifest`
- `ManifestValidator`
- `ConnectorSession`
- `CapabilityDescriptor`
- `BridgeTransport`
- `ConnectorRegistrationRequest`

#### Function naming

- `validate_connector_manifest`
- `register_connector`
- `open_connector_session`
- `negotiate_connector_capabilities`
- `send_bridge_request`

#### Error naming

- `ConnectorError`
- `ManifestValidationError`
- `ConnectorRegistrationError`
- `CapabilityNegotiationError`
- `BridgeTransportError`

---

## Swift Shell Conventions

These apply to the native macOS process.

### File naming

Use `PascalCase.swift` and match file to primary type.

Examples:

- `AppSessionController.swift`
- `AuthenticationViewModel.swift`
- `KeychainSecretStore.swift`
- `BackendSocketClient.swift`

### Type naming

Preferred suffixes by role:

- `View` — SwiftUI view
- `ViewModel` — presentation state holder
- `Controller` — app/session flow coordinator when needed
- `Store` — local persistence abstraction
- `Client` — outbound connection/API interface
- `Bridge` — process boundary bridge
- `Coordinator` — orchestration logic
- `Presenter` — only if architecture explicitly uses presenters

Avoid:

- `Manager`
- `Helper`
- `Util`

### SwiftUI naming

- Screen-level views: `...Screen` or `...View`
- Reusable visual component: `...Card`, `...Row`, `...Panel`, `...Section`
- Modal surfaces: `...Sheet`, `...Dialog`
- State enums: `...ViewState`

Examples:

- `PullRequestQueueView`
- `ConsensusStatusCard`
- `TrustLabelSection`
- `AuthDialog`

### State and actions

- View model state properties should read clearly:
  - `isLoading`
  - `hasAuthenticatedSession`
  - `selectedRepositoryURL`
  - `currentBuildState`

- Action methods should be verb-led:
  - `loadRepository()`
  - `refreshPullRequests()`
  - `submitIntent()`

---

## Python Backend Conventions

These apply to backend orchestration, consensus, pipeline, policy, GitHub, and subsystem services.

### Module design

- One module should have one clear responsibility.
- Keep top-level side effects out of modules.
- Avoid implicit global mutable state.

### Dependency naming

Injected dependencies should be named by role:

- `policy_evaluator`
- `audit_stream_writer`
- `machine_identity_attestor`

Not:

- `service`
- `manager`
- `dependency`

### Data model naming

- Use `dataclass` or equivalent for structured in-memory records where appropriate.
- Serialized wire types should be named distinctly from internal domain models when semantics differ.
  - `PolicyDecision` vs `PolicyDecisionPayload`

### Async naming

- Async functions should still use normal verb-led names.
- Do not prefix with `async_` unless needed to disambiguate from a sync counterpart.

---

## Interfaces and Boundary Patterns

### Boundary components must be explicit

Use `Adapter`, `Client`, `Bridge`, or `Transport` for components crossing:

- process boundaries
- network boundaries
- storage boundaries
- trust boundaries

Examples:

- `GitHubClient`
- `UnixSocketTransport`
- `PolicyEngineAdapter`
- `TrustFlowBridge`

### Serialization types

Distinguish domain models from wire models:

- `AuditEvent` — domain event
- `AuditEventPayload` — serialized transport form
- `PolicyDecision` — domain result
- `PolicyDecisionResponse` — API/wire output

### Validation pattern

Validation components should be explicit and separate from mutation when practical.

Preferred:

- `LabelValidator.validate(...)`
- `ManifestValidator.validate(...)`

Avoid hidden validation in unrelated constructors unless the type is explicitly a validated value object.

---

## Tests

## Test path rules

- Tests mirror source structure exactly.
- Python tests use `test_<module>.py`
- Swift test files use `<TypeName>Tests.swift`

Examples:

```text
src/mcp/policy_evaluator.py
tests/mcp/test_policy_evaluator.py

src/trustflow/audit_stream_writer.py
tests/trustflow/test_audit_stream_writer.py
```

### Test naming

#### Python

- Test functions:
  - `test_evaluate_policy_request_denies_missing_scope`
  - `test_append_audit_event_rejects_invalid_sequence`

#### Swift

- Test methods:
  - `testEvaluatePolicyRequestDeniesMissingScope()`
  - `testAppendAuditEventRejectsInvalidSequence()`

### Test class naming

- Python:
  - `class TestPolicyEvaluator:`
- Swift:
  - `final class PolicyEvaluatorTests: XCTestCase`

### Test fixtures

Name fixtures by domain role:

- `policy_bundle`
- `audit_entry`
- `connector_manifest`
- `zone_snapshot`

Avoid generic names:

- `data`
- `obj`
- `sample`
- `thing`

Unless the scope is trivial and obvious.

---

## Constants, Enums, and Configuration

### Constants

- Constants must be named by domain meaning, not literal value usage.
- Group related constants in a dedicated module/type when they form a cohesive set.

Examples:

- `MAX_AUDIT_BATCH_SIZE`
- `DEFAULT_REPLAY_WINDOW`
- `attestationNonceLength`

### Enums

Enum cases should be domain terms, not UI text.

Examples:

- `allow`, `deny`, `defer`
- `pending`, `verified`, `rejected`

Avoid:

- `green`, `red`
- `good`, `bad`

### Configuration keys

- Use explicit, namespaced keys.
- Prefer subsystem prefixes.

Examples:

- `trustflow.stream_flush_interval`
- `mcp.policy_cache_ttl_seconds`
- `rewind.max_replay_events`

---

## Documentation and Comments

### Docstrings and comments

- Document why, not what, unless the code is implementing a subtle contract.
- Public APIs and security-sensitive functions must have documentation.
- Comments must use the subsystem’s domain vocabulary consistently.

### TODOs

Every TODO must include:
- reason
- owner or tracking reference
- completion condition

Format:

```text
TODO(TRD-11 / owner): enforce attestation freshness window once verifier API lands.
```

Avoid bare TODOs.

---

## Forbidden Naming Patterns

Do not introduce files, classes, or functions named:

- `utils`
- `helpers`
- `common` without a specific domain qualifier
- `manager`
- `processor`
- `wrapper`
- `misc`
- `temp`
- `final`
- `new_*`
- `old_*`

Do not use single-letter names except:
- well-known loop indices in tiny scopes
- mathematical notation where standard and obvious

---

## Recommended Code Patterns

### Pattern: explicit evaluator

```python
decision = policy_evaluator.evaluate_policy_request(request_context)
if decision.is_denied:
    raise PolicyEvaluationError("policy denied request")
```

### Pattern: explicit error translation

```python
try:
    attestation_bundle = identity_attestor.attest_platform_state(nonce)
except OSError as exc:
    raise AttestationError("platform attestation failed") from exc
```

### Pattern: explicit boundary naming

```python
class TrustFlowClient:
    def append_audit_event(self, event: AuditEvent) -> AuditEntry:
        ...
```

### Pattern: validated state transition

```swift
func transition(to nextState: ReplayState) throws {
    guard currentState.canTransition(to: nextState) else {
        throw RewindError.invalidStateTransition(currentState, nextState)
    }
    currentState = nextState
}
```

---

## Cross-Subsystem Consistency Rules

- If the same concept appears in multiple subsystems, prefer the same base noun.
  - `PolicyDecision` everywhere, not `PolicyResult` in one place and `RuleOutcome` in another.
  - `AuditEvent` everywhere, not `TrustEvent` elsewhere unless semantics differ.

- Use subsystem prefixes in root exception names only, not in every type.
  - Good: `DtlError`, `TrustFlowError`
  - Good: `LabelValidator` inside `dtl`
  - Avoid: `DtlLabelValidator` unless needed to disambiguate outside the package

- Boundary DTOs may include subsystem prefixes if crossing a shared namespace.

---

## Change Discipline

Before adding a new file, type, or naming pattern:

1. Check whether the concept already exists under another name.
2. Reuse established suffixes and role names.
3. Confirm the naming matches the owning subsystem vocabulary in the relevant TRD.
4. Add or update mirrored tests.
5. Keep trust and security semantics explicit in names.

---

## Summary

Forge code must be:

- TRD-aligned
- subsystem-explicit
- security-clear
- test-mirrored
- type-precise
- boring in the best way

When naming something, optimize for:
- trust clarity
- ownership clarity
- boundary clarity
- future maintenance