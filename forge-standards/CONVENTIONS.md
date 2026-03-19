# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, and implementation patterns for the full Forge platform. It applies across native shell code, backend services, security controls, retrieval systems, SDKs, and tests.

---

## File and Directory Naming (exact `src/` layout)

### Top-level source layout

Use this layout exactly for Forge-owned source code:

```text
src/
  cal/          # Conversation Abstraction Layer components
  dtl/          # Data Trust Label components
  trustflow/    # TrustFlow audit stream components
  vtz/          # Virtual Trust Zone enforcement
  trustlock/    # Cryptographic machine identity (TPM-anchored)
  mcp/          # MCP Policy Engine
  rewind/       # Forge Rewind replay engine

sdk/
  connector/    # Forge Connector SDK

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

### General directory rules

- Directory names must be lowercase.
- Multi-word directories use `snake_case`.
- Tests must mirror source structure exactly.
- Do not create ambiguous utility directories such as:
  - `src/common`
  - `src/helpers`
  - `src/misc`
  - `src/shared`
- Shared code must live in a clearly named domain package such as:
  - `src/cal/message_schema/`
  - `src/trustflow/serialization/`
  - `src/mcp/policy_eval/`

### File naming by language

#### Python
- Use `snake_case.py`.
- Example:
  - `policy_engine.py`
  - `vector_index.py`
  - `session_state.py`

#### Swift
- Use `PascalCase.swift` for primary type files.
- One major type per file.
- Example:
  - `ShellApp.swift`
  - `AuthenticationManager.swift`
  - `BackendProcessController.swift`

#### SwiftUI
- Views use `PascalCase.swift` and end in:
  - `View`
  - `Screen`
  - `Sheet`
  - `Row`
- Example:
  - `OnboardingView.swift`
  - `SettingsScreen.swift`
  - `DocumentRow.swift`

#### Test files
- Python tests use `test_<unit>.py`.
- Swift tests use `<TypeName>Tests.swift`.
- Example:
  - `test_policy_engine.py`
  - `AuthenticationManagerTests.swift`

### Generated and derived files

- Generated files must live under a clearly named generated directory:
  - `generated/`
  - `artifacts/`
  - `snapshots/`
- Generated code must never be hand-edited.
- If generated code is committed, annotate with a header:
  - `# GENERATED FILE - DO NOT EDIT`
  - or Swift equivalent.

### Configuration and schema files

- Use `snake_case`:
  - `default_policy.yaml`
  - `embedding_config.json`
  - `user_defaults_schema.json`
- Versioned schemas should include explicit version suffixes:
  - `trust_event_v1.json`
  - `document_chunk_v2.json`

---

## Class and Function Naming

### General naming rules

- Names must reflect domain meaning, not implementation detail.
- Prefer nouns for types and verbs for actions.
- Avoid abbreviations unless they are platform-standard or Forge-standard:
  - Allowed: `XPC`, `MCP`, `TPM`, `URL`, `ID`
  - Avoid: `Mgr`, `Util`, `Proc`, `Cfg`

### Class, struct, enum, protocol names

#### Python
- Classes use `PascalCase`.
- Exceptions end with `Error`.
- Protocol-like abstract base classes end with one of:
  - `Interface`
  - `Protocol`
  - `Provider`
  - `Store`

Examples:
- `DocumentStore`
- `EmbeddingProvider`
- `PolicyEvaluationError`

#### Swift
- Types use `PascalCase`.
- Protocols describe capability and may use:
  - `Providing`
  - `Managing`
  - `Controlling`
  - `Storing`
- Enums use singular nouns.

Examples:
- `AuthenticationManager`
- `BackendProcessController`
- `KeychainSecretStore`
- `SessionManaging`

### Function and method names

#### Python
- Use `snake_case`.
- Function names must start with a verb.
- Boolean-returning functions should start with:
  - `is_`
  - `has_`
  - `can_`
  - `should_`

Examples:
- `load_document()`
- `build_embedding_index()`
- `is_policy_applicable()`

#### Swift
- Use lowerCamelCase.
- Prefer clear argument labels.
- Boolean-returning methods should read naturally:
  - `isAuthenticated`
  - `hasValidSession`
  - `canAccessSecureStore()`

Examples:
- `launchBackend(with:)`
- `storeSecret(_:forAccount:)`
- `restartProcessIfNeeded()`

### Variables and properties

- Use descriptive names.
- Prefer `document_id` over `id` when ambiguity exists.
- Prefer `policy_result` over `result`.
- Loop variables may be short only when scope is tiny:
  - `i`, `j` only for indices
  - `doc` acceptable for document in tight scope
- Boolean names must express state:
  - `is_first_launch`
  - `has_biometric_access`
  - `should_restart_backend`

### Constants

#### Python
- Module-level constants use `UPPER_SNAKE_CASE`.
- Example:
  - `MAX_CHUNK_SIZE`
  - `DEFAULT_EMBEDDING_MODEL`

#### Swift
- Static constants use lowerCamelCase.
- Type names carry namespace responsibility.
- Example:
  - `ShellDefaults.firstLaunchKey`
  - `LoggingSubsystem.authentication`

### Acronyms

- Python: treat acronyms as normal words in `snake_case`.
  - `xpc_channel.py`
  - `tpm_identity_store.py`
- Swift: preserve Apple-style acronym casing when established.
  - `XPCChannel`
  - `TPMIdentity`
  - `URLSessionBridge`

---

## Error and Exception Patterns

### General rules

- Errors must be typed, actionable, and domain-specific.
- Never raise or throw generic errors for expected failure cases.
- Every error must support:
  - machine classification
  - human-readable message
  - structured context
  - safe logging without secret leakage

### Naming

#### Python
- Exception classes end with `Error`.
- Domain-prefixed when needed:
  - `DocumentParseError`
  - `EmbeddingModelUnavailableError`
  - `PolicyEvaluationError`
  - `PromptInjectionDetectedError`

#### Swift
- Error enums or structs end with `Error` when concrete.
- Use domain grouping:
  - `AuthenticationError`
  - `BackendLaunchError`
  - `XPCTransportError`
  - `SettingsMigrationError`

### Error structure

#### Python pattern

```python
class PolicyEvaluationError(Exception):
    def __init__(self, message: str, policy_id: str | None = None) -> None:
        super().__init__(message)
        self.policy_id = policy_id
```

Preferred pattern:
- include typed fields
- preserve original cause
- include redaction-safe metadata only

#### Swift pattern

```swift
enum AuthenticationError: Error {
    case biometricUnavailable
    case keychainAccessDenied
    case invalidSessionState
}
```

Preferred for richer context:

```swift
struct BackendLaunchError: Error {
    let reason: Reason
    let executablePath: String
    let exitStatus: Int32?
}
```

### Wrapping and propagation

- Wrap infrastructure failures at subsystem boundaries.
- Do not leak vendor/library-specific exceptions across domain layers.
- Preserve root cause internally.
- Translate low-level errors into subsystem errors at public boundaries.

### Logging and secrets

- Never include:
  - API keys
  - access tokens
  - raw prompts containing secrets
  - biometric artifacts
  - keychain values
- Security-sensitive failures must log identifiers and classifications, not secret material.

### Expected vs unexpected failures

Expected failures:
- validation failure
- auth denied
- unsupported format
- policy rejection
- missing embedding model

Unexpected failures:
- invariant violation
- impossible state transition
- corrupted internal index
- malformed signed envelope after internal generation

Expected failures must use explicit typed errors.
Unexpected failures may assert, crash, or fault depending on runtime criticality and subsystem.

---

## Per-Subsystem Naming Rules

---

### `src/cal/` — Conversation Abstraction Layer

#### Purpose
Owns conversation orchestration, message normalization, turn state, context assembly, and model-facing conversation structures.

#### Directory patterns

```text
src/cal/
  conversation/
  messages/
  context/
  sessions/
  adapters/
  safety/
```

#### Naming rules

- Primary types:
  - `ConversationSession`
  - `ConversationTurn`
  - `MessageEnvelope`
  - `ContextAssembler`
  - `ModelAdapter`
- Message representations must use `Message` or `Envelope`.
- Turn-scoped state must use `Turn`.
- Cross-turn state must use `Session`.

#### Function patterns

- Builders:
  - `build_context_window`
  - `assemble_prompt_context`
- Validators:
  - `validate_message_envelope`
  - `validate_turn_transition`
- Transformers:
  - `normalize_message_content`
  - `convert_provider_response`

#### Anti-patterns

- Do not use vague names like `AgentState`, `Manager`, or `Handler` unless domain-qualified.
- Do not name prompt-building code as `utils`.

---

### `src/dtl/` — Data Trust Label

#### Purpose
Owns data provenance labels, trust metadata, sensitivity classification, and propagation rules.

#### Directory patterns

```text
src/dtl/
  labels/
  classifiers/
  propagation/
  schemas/
  enforcement/
```

#### Naming rules

- Types must include one of:
  - `TrustLabel`
  - `SensitivityLevel`
  - `ProvenanceRecord`
  - `ClassificationResult`
  - `PropagationRule`
- Classification outputs should end in `Result`.
- Schema objects should end in `Schema`.

Examples:
- `DataTrustLabel`
- `DocumentProvenanceRecord`
- `TrustLabelSchema`
- `LabelPropagationRule`

#### Function patterns

- `classify_document_sensitivity`
- `apply_label_propagation`
- `derive_provenance_record`
- `validate_trust_label_schema`

#### Required semantics

- Labels are nouns.
- Propagation logic uses verbs: `apply`, `derive`, `merge`, `downgrade`, `escalate`.

---

### `src/trustflow/` — TrustFlow audit stream

#### Purpose
Owns append-only audit events, event serialization, integrity linkage, and replay-safe audit records.

#### Directory patterns

```text
src/trustflow/
  events/
  stream/
  serialization/
  integrity/
  export/
```

#### Naming rules

- Event types end with `Event`.
- Stream records end with `Record`.
- Integrity artifacts end with:
  - `Digest`
  - `Chain`
  - `Checkpoint`
  - `Signature`

Examples:
- `PolicyEvaluatedEvent`
- `DocumentRetrievedEvent`
- `AuditStreamRecord`
- `EventDigestChain`

#### Function patterns

- `append_audit_event`
- `serialize_event_record`
- `verify_digest_chain`
- `export_trustflow_stream`

#### Rules

- Avoid generic names like `log_event`.
- Audit objects must distinguish:
  - event payload
  - stream record
  - exported artifact

---

### `src/vtz/` — Virtual Trust Zone enforcement

#### Purpose
Owns isolation boundaries, execution policy enforcement, compartment capabilities, and sensitive operation gating.

#### Directory patterns

```text
src/vtz/
  boundaries/
  enforcement/
  capabilities/
  runtime/
  policies/
```

#### Naming rules

- Isolation types include:
  - `TrustZone`
  - `ExecutionBoundary`
  - `CapabilityToken`
  - `ZonePolicy`
  - `EnforcementDecision`
- Decisions end with `Decision`.
- Capability-bearing objects end with `Capability` or `Token`.

Examples:
- `VirtualTrustZone`
- `FilesystemAccessCapability`
- `BoundaryEnforcementDecision`

#### Function patterns

- `evaluate_zone_policy`
- `enforce_execution_boundary`
- `grant_capability_token`
- `revoke_runtime_capability`

#### Rules

- Boundary checks must use verbs like `enforce`, `deny`, `allow`, `verify`.
- Do not hide security-critical actions behind vague names like `process_request`.

---

### `src/trustlock/` — Cryptographic machine identity

#### Purpose
Owns TPM-anchored identity, attestation, device binding, hardware-backed signing, and machine trust material.

#### Directory patterns

```text
src/trustlock/
  identity/
  attestation/
  signing/
  binding/
  storage/
```

#### Naming rules

- Identity types include:
  - `MachineIdentity`
  - `AttestationQuote`
  - `DeviceBinding`
  - `HardwareSigner`
  - `TrustAnchor`
- TPM-backed resources should include `TPM` where applicable.
- Signed objects end with `Signature` or `SignedEnvelope`.

Examples:
- `TPMMachineIdentity`
- `DeviceBindingRecord`
- `AttestationSignature`
- `SignedTrustEnvelope`

#### Function patterns

- `generate_attestation_quote`
- `bind_identity_to_device`
- `sign_with_hardware_key`
- `verify_trust_anchor`

#### Rules

- Cryptographic naming must distinguish:
  - key material
  - identity claims
  - attestation evidence
  - signatures
- Never name cryptographic wrappers as `token` unless they are bearer-like artifacts.

---

### `src/mcp/` — MCP Policy Engine

#### Purpose
Owns policy representation, evaluation, effect resolution, constraint application, and policy decision reporting.

#### Directory patterns

```text
src/mcp/
  policies/
  evaluation/
  effects/
  constraints/
  reporting/
```

#### Naming rules

- Policy types end with:
  - `Policy`
  - `Rule`
  - `Constraint`
  - `Decision`
  - `EvaluationResult`
- Decision enums should use explicit effect names:
  - `allow`
  - `deny`
  - `requireReview`
  - `escalate`

Examples:
- `RepositoryWritePolicy`
- `PromptSanitizationRule`
- `CapabilityConstraint`
- `PolicyDecision`

#### Function patterns

- `evaluate_policy`
- `resolve_policy_effects`
- `apply_constraint_set`
- `build_decision_report`

#### Rules

- Evaluation functions return decision objects, not booleans, for non-trivial policy logic.
- Policy source representations must be separated from executable evaluation objects.

---

### `src/rewind/` — Forge Rewind replay engine

#### Purpose
Owns deterministic replay, state reconstruction, event timeline traversal, and forensic or debug re-execution.

#### Directory patterns

```text
src/rewind/
  replay/
  timelines/
  snapshots/
  reconstruction/
  diff/
```

#### Naming rules

- Replay types include:
  - `ReplaySession`
  - `TimelineCursor`
  - `StateSnapshot`
  - `EventReconstructor`
  - `ReplayDiff`
- Determinism-related types should include:
  - `Deterministic`
  - `Canonical`
  - `Replayable`

Examples:
- `DeterministicReplaySession`
- `CanonicalStateSnapshot`
- `ReplayDiffReport`

#### Function patterns

- `replay_event_stream`
- `reconstruct_state_at_offset`
- `compare_replay_output`
- `load_canonical_snapshot`

#### Rules

- Distinguish snapshot state from replay state.
- Diff objects must end with `Diff` or `DiffReport`.
- Timeline navigation names should imply ordering semantics.

---

### `sdk/connector/` — Forge Connector SDK

#### Purpose
Owns public integration APIs, client authentication surfaces, transport abstractions, and partner-facing SDK ergonomics.

#### Directory patterns

```text
sdk/connector/
  client/
  auth/
  transport/
  models/
  errors/
```

#### Naming rules

- Public entry points end with:
  - `Client`
  - `Connector`
  - `Session`
- Transport abstractions end with:
  - `Transport`
  - `Request`
  - `Response`
- Public-facing models must be stable and explicit.

Examples:
- `ForgeConnectorClient`
- `ConnectorSession`
- `HTTPTransport`
- `ConnectorRequest`

#### Function patterns

- `create_connector_session`
- `authenticate_client`
- `send_connector_request`
- `parse_connector_response`

#### Rules

- SDK naming prioritizes external clarity over internal brevity.
- Avoid leaking internal subsystem names into public SDK APIs unless intentional and documented.

---

## macOS Application Shell Conventions

Applies to the native Swift/SwiftUI shell from TRD-1.

### Module boundaries

Use feature-based Swift modules or groups aligned to shell responsibilities:

```text
Shell/
  App/
  Authentication/
  Keychain/
  Backend/
  XPC/
  Settings/
  Onboarding/
  Logging/
  Updates/
```

### Swift type naming

- App root:
  - `ForgeShellApp`
  - `AppCoordinator`
- Authentication:
  - `AuthenticationManager`
  - `BiometricGate`
  - `SessionController`
- Secret storage:
  - `KeychainSecretStore`
- Backend control:
  - `BackendProcessController`
  - `BackendLaunchConfiguration`
- XPC:
  - `XPCConnectionManager`
  - `AuthenticatedXPCChannel`
- Settings:
  - `SettingsStore`
  - `SettingsMigration`
- Logging:
  - `ShellLogger`
  - `LoggingSubsystem`

### SwiftUI view conventions

- Root navigable views end with `View` or `Screen`.
- Modal presentations end with `Sheet`.
- Row/list items end with `Row`.
- View models end with `ViewModel`.

Examples:
- `RootView`
- `OnboardingView`
- `SettingsScreen`
- `AuthenticationSheet`
- `BackendStatusViewModel`

### State ownership

- `@State` only for local ephemeral view state.
- `@StateObject` for view-owned observable models.
- `@ObservedObject` for externally owned models passed into views.
- `@EnvironmentObject` only for app-wide shared state with clear ownership.
- Business logic must not live directly in SwiftUI views.

### Concurrency

- UI-affecting types should be `@MainActor` where appropriate.
- Async methods must be verb-led:
  - `authenticateUser()`
  - `launchBackend()`
  - `refreshSession()`
- Callback-based APIs should be wrapped behind async interfaces where feasible.
- Do not mix unstructured concurrency into stateful flows without explicit cancellation semantics.

### XPC patterns

- Interface names:
  - `BackendXPCProtocol`
  - `ShellXPCProtocol`
- Message DTOs:
  - `XPCRequestEnvelope`
  - `XPCResponseEnvelope`
- Authenticated channel types must include `Authenticated` or `Secure`.

### Logging

- Use `os_log`/`Logger` categories by subsystem:
  - `authentication`
  - `backend`
  - `xpc`
  - `settings`
  - `updates`
- Log categories must match owning module names.
- Sensitive fields require privacy annotations.

### Settings and defaults

- UserDefaults keys must be namespaced:
  - `forge.onboarding.completed`
  - `forge.backend.auto_restart`
- Key constants should be defined centrally:
  - `ShellDefaults.onboardingCompletedKey`

---

## Document Store and Retrieval Conventions

Applies to TRD-10.

### Directory patterns

```text
src/cal/context/
src/dtl/schemas/
src/trustflow/events/
src/...           # retrieval-specific code should live in its owning subsystem
```

If implemented as a dedicated service package, use:

```text
src/document_store/
  parsing/
  chunking/
  embeddings/
  indexing/
  retrieval/
  metadata/
```

### Naming rules

- Parsing:
  - `DocumentParser`
  - `ParseResult`
  - `DocumentMetadata`
- Chunking:
  - `SemanticChunker`
  - `FixedSizeChunker`
  - `ChunkBoundary`
  - `ChunkingStrategy`
- Embeddings:
  - `EmbeddingModel`
  - `EmbeddingProvider`
  - `EmbeddingVector`
- Retrieval:
  - `RetrievalQuery`
  - `RetrievalResult`
  - `ContextCandidate`

### Function patterns

- `parse_input_document`
- `extract_document_metadata`
- `chunk_document_semantically`
- `generate_embedding_vector`
- `retrieve_relevant_context`

### Rules

- Chunk objects must distinguish source span from rendered content.
- Embedding model wrappers must not expose vendor-specific response structures beyond integration boundaries.
- Retrieval ranking outputs should include explicit score naming:
  - `similarity_score`
  - `rank_position`

---

## Security Threat Model Conventions

Applies to TRD-11.

### Security-sensitive naming

- Detection types:
  - `PromptInjectionDetector`
  - `ThreatClassifier`
  - `SafetyInterlock`
- Threat outputs:
  - `ThreatAssessment`
  - `RiskScore`
  - `MitigationDecision`
- Sanitization types:
  - `PromptSanitizer`
  - `ContentIsolationPolicy`
  - `UntrustedContentEnvelope`

### Function patterns

- `classify_threat_input`
- `detect_prompt_injection`
- `sanitize_untrusted_content`
- `apply_safety_interlock`
- `record_security_decision`

### Rules

- Untrusted content types must include `Untrusted`, `External`, or `Sanitized` in names where ambiguity exists.
- Code paths that cross trust boundaries must use explicit method names:
  - `import_external_document`
  - `sanitize_external_context`
  - `execute_in_isolated_zone`
- Do not name threat handling logic as generic validation when it is actually security enforcement.

---

## Cross-Cutting Implementation Patterns

### Layering

Use clear boundaries:

1. transport/interface layer
2. application/service layer
3. domain layer
4. infrastructure layer

Naming should reflect layer role:
- `*Controller`, `*Endpoint`, `*Protocol` for interface boundaries
- `*Service` for application orchestration
- `*Policy`, `*Session`, `*Record`, `*Decision` for domain
- `*Store`, `*Client`, `*Provider`, `*Repository` for infrastructure

### DTOs and domain models

- Transport DTOs must be explicitly named:
  - `CreateSessionRequest`
  - `PolicyDecisionResponse`
- Domain models must avoid transport suffixes.
- Never reuse persistence models as API responses without an explicit translation layer.

### Serialization

- Serialized payload versions must be explicit.
- Use suffixes:
  - `V1`
  - `v1` in filenames
- Stable wire models must not silently change field meaning.

### Time and identifiers

- Use explicit names:
  - `created_at`
  - `updated_at`
  - `event_id`
  - `session_id`
  - `machine_id`
- Never use bare `timestamp` or `data` where semantics matter.

### Boolean and enum design

- Prefer enums over multiple correlated booleans.
- Example:
  - use `PolicyDecision.allow | deny | requireReview`
  - not `is_allowed`, `needs_review`, `is_denied`

### Comments and docs

- Code should explain intent through naming first.
- Comments should explain:
  - invariants
  - security assumptions
  - concurrency expectations
  - non-obvious tradeoffs
- Do not write comments that restate the code literally.

---

## Test Naming and Structure

### Directory mirroring

Tests must mirror source structure exactly.

Examples:

```text
src/mcp/evaluation/policy_engine.py
tests/mcp/evaluation/test_policy_engine.py
```

```text
src/trustflow/events/event_record.py
tests/trustflow/events/test_event_record.py
```

### Naming rules

- Test functions use `test_<behavior>`.
- Prefer behavior-driven names:
  - `test_evaluate_policy_denies_untrusted_write`
  - `test_chunk_document_semantically_preserves_overlap`
- Swift tests:
  - `func testAuthenticationFailsWhenBiometricAccessIsDenied()`

### Structure

- One behavioral concern per test.
- Arrange/Act/Assert structure required.
- Security tests must include both allow and deny cases.
- Replay/determinism tests must include stable fixture assertions.

---

## Prohibited Naming Patterns

Do not introduce these names unless heavily qualified and justified:

- `utils`
- `helpers`
- `misc`
- `manager` as a standalone catch-all
- `handler` without domain qualifier
- `data`
- `info`
- `service` when the type is actually a store, client, or policy
- `processor` when action semantics are known and more specific names exist

Bad:
- `utils.py`
- `DataManager`
- `process()`
- `handle()`

Good:
- `policy_eval_report.py`
- `DocumentParser`
- `evaluate_policy()`
- `append_audit_event()`

---

## Naming Checklist

Before merging, verify:

- File path matches subsystem ownership.
- File name follows language convention.
- Type name is domain-specific and noun-based.
- Function name is verb-led and semantically precise.
- Error type is typed and ends with `Error`.
- Test path mirrors source path exactly.
- Security-sensitive code uses trust-boundary-explicit naming.
- No vague utility or helper names were introduced.
- Public SDK names are externally understandable.
- Logs and errors avoid secret disclosure.

---
