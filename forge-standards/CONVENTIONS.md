# Code Conventions

This document defines coding conventions, naming rules, and code patterns derived from the repository guidance and the referenced technical requirements. The TRDs are the source of truth; these conventions standardize implementation style across all subsystems.

## File and Directory Naming (exact `src/` layout)

### Core architecture layout

The codebase is organized as a two-process system:

- Swift shell:
  - UI
  - authentication
  - Keychain/secrets handling
  - XPC / local process coordination
- Python backend:
  - consensus engine
  - generation pipeline
  - provider integrations
  - repository and pull request automation

Use directory names that reflect the owning subsystem and mirror the architecture boundaries.

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
```

Additional implementation directories must follow the same pattern:

- lowercase
- concise
- subsystem-scoped
- no spaces
- no hyphens unless already required by external tooling
- prefer nouns for subsystem folders

### SDK and tests

```text
sdk/
  connector/

tests/
  <subsystem>/
```

Rules:

- `tests/<subsystem>/` must mirror `src/` structure exactly.
- Test file locations must correspond to implementation ownership.
- Shared test helpers belong in a clearly named common test utility area only if used by multiple subsystem suites.

### File naming rules

#### Python

Use:

- `snake_case.py` for module files
- descriptive, subsystem-specific names
- one primary responsibility per file

Examples:

- `consensus_engine.py`
- `provider_adapter.py`
- `json_socket_client.py`
- `pr_plan_builder.py`

Avoid:

- vague names like `utils.py`, `helpers.py`, `misc.py`
- overloaded files containing unrelated classes

#### Swift

Use:

- `PascalCase.swift` for type-oriented files
- filename must match the primary type or view name
- one primary public type per file

Examples:

- `SessionCoordinator.swift`
- `AuthenticatedSocketClient.swift`
- `IntentAssessmentView.swift`

For SwiftUI:

- views end with `View`
- cards end with `Card`
- panels end with `Panel`
- coordinators end with `Coordinator`
- stores/models should reflect role precisely

#### Protocol and interface files

Name files after the protocol or interface they define:

- `ProviderAdapter.swift`
- `ConsensusEngineProtocol.swift`
- `CredentialStore.py` only if the file centers on that abstraction

### Generated and derived artifacts

Do not place generated code in source directories unless explicitly required by the owning TRD. Generated outputs, fixtures, replay data, and temporary artifacts must be isolated into clearly named non-source locations.

---

## Class and Function Naming

### General naming rules

Use names that describe domain behavior, not implementation trivia.

Prefer:

- `IntentClassifier`
- `PullRequestPlanner`
- `AuthenticatedChannel`
- `ReplaySession`

Avoid:

- `Manager` unless it truly manages lifecycle or coordination
- `Processor` unless the type performs staged transformation work
- `Thing`, `Data`, `Object`, `Util`

### Python naming

#### Classes

Use `PascalCase`.

Examples:

- `ConsensusEngine`
- `ProviderAdapter`
- `GitHubClient`
- `TrustLabelEvaluator`

#### Functions and methods

Use `snake_case`.

Examples:

- `assess_intent_confidence`
- `build_pr_sequence`
- `validate_trust_label`
- `emit_audit_event`

Boolean-returning functions should read as predicates:

- `is_authenticated`
- `has_required_scope`
- `can_open_pull_request`
- `should_retry`

Avoid ambiguous boolean names like:

- `check_auth`
- `process_valid`

#### Constants

Use `UPPER_SNAKE_CASE`.

Examples:

- `MAX_RETRY_ATTEMPTS`
- `SOCKET_READ_TIMEOUT_SECONDS`
- `DEFAULT_CONFIDENCE_THRESHOLD`

### Swift naming

#### Types

Use `PascalCase`.

Examples:

- `AuthSessionStore`
- `KeychainCredentialStore`
- `UnixSocketTransport`
- `PipelineStatusView`

#### Properties and methods

Use `camelCase`.

Examples:

- `currentSession`
- `isAuthenticated`
- `openDraftPullRequest()`
- `validateEnvelope()`

Boolean properties should use:

- `is...`
- `has...`
- `can...`
- `should...`

Examples:

- `isConnected`
- `hasValidToken`
- `canProceed`
- `shouldShowRecoveryBanner`

#### Protocols

Use role-based names. Do not prefix all protocols mechanically. Prefer semantic names such as:

- `CredentialStore`
- `SocketTransport`
- `AuditEmitter`

Use `...Providing`, `...Serving`, or `...Coordinating` only when they improve clarity:

- `TokenProviding`
- `PlanCoordinating`

### Naming by lifecycle role

Use consistent suffixes where meaningful:

- `...Client` for external service consumers
- `...Adapter` for provider normalization layers
- `...Engine` for core decision or orchestration logic
- `...Coordinator` for cross-component flow control
- `...Store` for state and persistence ownership
- `...Validator` for rule enforcement
- `...Emitter` for audit/event output
- `...Parser` for structured input parsing
- `...Builder` for deterministic object construction
- `...ViewModel` only where an MVVM boundary is explicit
- `...Error` for typed failures
- `...Result` for structured operation outcomes

---

## Error and Exception Patterns

### General principles

Errors must be:

- typed where possible
- explicit
- stable at subsystem boundaries
- safe to log
- mapped to documented interface contracts

Do not invent ad hoc error formats for cross-process, security-relevant, or externally surfaced APIs.

### Error naming

Use domain-specific error names.

Examples:

- `AuthenticationError`
- `SocketProtocolError`
- `ConsensusFailure`
- `TrustPolicyViolation`
- `ReplayIntegrityError`

Avoid generic names like:

- `GeneralError`
- `SystemError`
- `UnknownFailure` unless required as a terminal fallback case

### Python error patterns

#### Exception classes

Use `PascalCase` and suffix with `Error`.

Examples:

- `ProviderTimeoutError`
- `PlanValidationError`
- `CredentialAccessError`

Create subsystem-root exception hierarchies where useful:

```python
class ConsensusError(Exception):
    pass

class ArbitrationError(ConsensusError):
    pass
```

#### Raising exceptions

- Raise the most specific exception available.
- Preserve causal chains.
- Include structured context when useful.
- Do not leak secrets, tokens, prompts, or untrusted raw content in exception messages.

Prefer:

```python
raise ProviderTimeoutError("provider response exceeded timeout")
```

When wrapping:

```python
raise PlanValidationError("invalid PR dependency graph") from exc
```

#### Error return objects

Where a TRD defines line-delimited JSON or structured inter-process responses, use explicit error envelopes rather than free-form strings.

Error payloads should include only documented fields, for example:

- machine-readable code
- human-readable message
- retryability if defined
- correlation or trace identifier if defined

### Swift error patterns

#### Error types

Use enums for finite error domains:

```swift
enum AuthenticationError: Error {
    case missingCredential
    case invalidSession
    case accessDenied
}
```

Use structs only when an error requires attached structured context and that pattern is already established in the subsystem.

#### Propagation

- Throw typed errors from subsystem APIs.
- Map lower-level errors to boundary-safe domain errors.
- Never surface raw storage, transport, or provider internals directly to UI or socket boundaries unless the TRD explicitly permits it.

#### User-facing error handling

UI text must be:

- actionable
- concise
- non-sensitive

Internal logs may contain technical detail, but never secrets or unsafe raw generated content.

### Logging and audit alignment

Errors that cross trust, credential, policy, replay, or audit boundaries must be recorded through the approved audit path for that subsystem.

Do not:

- log bearer tokens
- log private keys
- log full secrets from Keychain or equivalent storage
- log unredacted generated code if policy forbids it
- log untrusted payloads without labeling or sanitization requirements defined by the owning subsystem

---

## Per-Subsystem Naming Rules

## `src/cal/` — Conversation Abstraction Layer

Purpose: abstraction over conversational/model interactions and related message flow.

Naming rules:

- files use `snake_case.py`
- core abstractions use names like:
  - `ConversationSession`
  - `MessageEnvelope`
  - `ProviderAdapter`
  - `ConsensusEngine`
- adapter implementations should be provider-neutral in shared layers and provider-specific in leaf modules
- line-delimited JSON transport helpers should include `json`, `socket`, or `transport` in the name where relevant
- message schema types should use nouns:
  - `PromptFrame`
  - `ResponseChunk`
  - `ConsensusDecision`

Avoid embedding provider names into shared interfaces.

Preferred suffixes:

- `...Adapter`
- `...Engine`
- `...Envelope`
- `...Session`
- `...Transport`

## `src/dtl/` — Data Trust Label components

Purpose: labeling, classification, and trust-state handling for data.

Naming rules:

- names must communicate trust semantics clearly
- label types use nouns such as:
  - `TrustLabel`
  - `DataClassification`
  - `LabelPolicy`
  - `LabelEvaluator`
- functions that assess trust should use predicate or decision names:
  - `is_trusted`
  - `requires_review`
  - `assign_trust_label`
  - `validate_label_transition`
- files should distinguish:
  - schema/model definitions
  - policy evaluation
  - transition validation

Preferred suffixes:

- `...Label`
- `...Policy`
- `...Evaluator`
- `...Classifier`
- `...TransitionValidator`

## `src/trustflow/` — TrustFlow audit stream components

Purpose: append-only audit/event stream and trust-relevant telemetry.

Naming rules:

- event types must be explicit and immutable in meaning
- use names like:
  - `AuditEvent`
  - `TrustEvent`
  - `EventEnvelope`
  - `AuditEmitter`
  - `EventStreamWriter`
- sequence/order concepts should be named consistently:
  - `sequence_id`
  - `event_index`
  - `stream_position`
- replayable event data should distinguish envelope from payload:
  - `AuditEventEnvelope`
  - `AuditEventPayload`

Preferred suffixes:

- `...Event`
- `...Envelope`
- `...Emitter`
- `...Writer`
- `...Reader`

## `src/vtz/` — Virtual Trust Zone enforcement

Purpose: policy enforcement and isolation boundaries.

Naming rules:

- names must imply enforcement, boundary checking, or scoped execution control
- use terms like:
  - `TrustZone`
  - `ZonePolicy`
  - `BoundaryGuard`
  - `ExecutionConstraint`
  - `PolicyEnforcer`
- gate functions should be imperative or predicate-based:
  - `enforce_zone_policy`
  - `validate_boundary_crossing`
  - `is_execution_permitted`

Avoid vague names like `security_check`; be specific about zone or policy intent.

Preferred suffixes:

- `...Guard`
- `...Policy`
- `...Enforcer`
- `...Constraint`
- `...Boundary`

## `src/trustlock/` — Cryptographic machine identity

Purpose: machine identity, hardware-rooted attestation, and cryptographic binding.

Naming rules:

- cryptographic and identity terms must be precise
- use names like:
  - `MachineIdentity`
  - `AttestationRecord`
  - `IdentityBinding`
  - `KeyMaterialHandle`
  - `AttestationVerifier`
- storage handles and references should indicate indirection, not raw secret ownership
- methods involving keys should describe operation, not implementation detail:
  - `create_attestation`
  - `verify_identity_binding`
  - `load_key_handle`

Do not name variables or fields as if they contain raw secret material unless they actually do and the owning TRD permits that representation.

Preferred suffixes:

- `...Identity`
- `...Attestation`
- `...Binding`
- `...Verifier`
- `...Handle`

## `src/mcp/` — MCP Policy Engine

Purpose: policy evaluation, rule application, and decision outputs.

Naming rules:

- policy constructs should be named deterministically
- use names like:
  - `PolicyRule`
  - `PolicyDecision`
  - `RuleEvaluator`
  - `DecisionContext`
  - `PolicyEngine`
- functions should reflect evaluation semantics:
  - `evaluate_policy`
  - `resolve_rule_set`
  - `build_decision_context`
- result objects should separate input context from final decision

Preferred suffixes:

- `...Rule`
- `...Decision`
- `...Evaluator`
- `...Context`
- `...Engine`

## `src/rewind/` — replay engine

Purpose: deterministic replay, reconstruction, and trace verification.

Naming rules:

- replay terms must differentiate live execution from reconstruction
- use names like:
  - `ReplaySession`
  - `ReplayCursor`
  - `TraceSnapshot`
  - `ReplayVerifier`
  - `TimelineReconstructor`
- position and ordering names should be stable and unambiguous:
  - `cursor`
  - `offset`
  - `frame_index`
  - `timeline_position`
- methods should express replay semantics:
  - `replay_next_frame`
  - `reconstruct_timeline`
  - `verify_replay_integrity`

Preferred suffixes:

- `...Replay`
- `...Session`
- `...Cursor`
- `...Verifier`
- `...Snapshot`

## `sdk/connector/` — Connector SDK

Purpose: external integration SDK for connectors into the platform.

Naming rules:

- public SDK APIs must favor clarity and stability over brevity
- types should be externally understandable:
  - `ConnectorClient`
  - `ConnectorSession`
  - `ConnectorRequest`
  - `ConnectorResponse`
  - `ConnectorConfiguration`
- avoid internal shorthand in public API names
- versioned interfaces should use explicit version suffixes only when required by compatibility policy

Preferred suffixes:

- `...Client`
- `...Session`
- `...Request`
- `...Response`
- `...Configuration`

## Swift shell conventions

Applies to UI, auth, secrets, local IPC, and shell-side orchestration.

### UI naming

For SwiftUI and presentation components:

- screens/views: `...View`
- reusable tiles/cards: `...Card`
- side or modal panels: `...Panel`
- flow owners: `...Coordinator`
- observable state holders: `...Store` or `...ViewModel` according to existing subsystem style

Examples:

- `IntentAssessmentView`
- `PipelineStatusCard`
- `ReviewGatePanel`

### Authentication and secrets

Names must reflect ownership and sensitivity:

- `AuthSession`
- `CredentialStore`
- `KeychainCredentialStore`
- `SessionTokenRef`

Prefer `Ref`, `Handle`, or `Store` for indirect secret access rather than implying in-memory raw secret ownership.

### IPC and transport

For Unix socket and line-delimited JSON communication:

- `SocketTransport`
- `AuthenticatedSocketClient`
- `JsonLineEncoder`
- `JsonLineDecoder`
- `EnvelopeValidator`

Use `Envelope` for framed cross-process messages and `Message` for semantic content carried inside envelopes where that distinction exists.

## Python backend conventions

Applies to consensus, pipeline, planning, generation, provider access, repository automation, and CI coordination.

### Planning and decomposition

Use clear stage-oriented names:

- `IntentAssessor`
- `PrdPlanBuilder`
- `PullRequestPlanner`
- `DependencyGraphValidator`

Functions should describe deterministic steps:

- `assess_intent_confidence`
- `decompose_prd`
- `order_pull_requests`
- `validate_plan_dependencies`

### Consensus and provider orchestration

Use role-true names:

- `ConsensusEngine`
- `ArbitrationDecision`
- `ParallelGenerationCoordinator`
- `ProviderAdapter`

Provider-specific modules should be leaf implementations under provider-scoped files, while shared interfaces remain provider-neutral.

### Repository and pull request automation

Use repository domain terminology consistently:

- `RepositoryWorkspace`
- `BranchStrategy`
- `PullRequestDraft`
- `CiGateResult`
- `LintGateResult`

Methods should be action-oriented:

- `create_feature_branch`
- `open_draft_pull_request`
- `run_ci_gate`
- `apply_fix_iteration`

## Testing conventions

### Layout

Tests must mirror implementation structure exactly under `tests/`.

Examples:

```text
src/mcp/policy_engine.py
tests/mcp/test_policy_engine.py

src/rewind/replay_session.py
tests/rewind/test_replay_session.py
```

### Test naming

Use:

- `test_<behavior>.py` for Python test modules
- `test_<expected_behavior>` for test functions

Examples:

- `test_evaluate_policy_denies_untrusted_input`
- `test_replay_next_frame_advances_cursor`
- `test_open_draft_pull_request_retries_on_transient_failure`

### Test class naming

If test classes are used, name them after the subject under test:

- `TestConsensusEngine`
- `TestPolicyDecision`
- `TestReplayVerifier`

### Behavior focus

Tests should reflect documented contracts:

- interface behavior
- error contracts
- security controls
- deterministic replay requirements
- policy decisions
- transport framing and validation

Avoid naming tests after implementation details unless verifying a required internal invariant.

## Cross-boundary schema conventions

For messages crossing process or subsystem boundaries:

- use explicit envelope names
- version schemas only when required by compatibility rules
- keep field names stable and machine-readable
- prefer singular nouns for single values and plural nouns for collections

Examples:

- `message_id`
- `request_id`
- `correlation_id`
- `event_type`
- `stream_position`

Boolean fields should read as predicates:

- `is_retryable`
- `has_more`
- `is_authenticated`

Timestamp fields should include unit or format semantics where necessary:

- `created_at`
- `expires_at`
- `timeout_seconds`

## Forbidden naming patterns

Do not use:

- hardcoded product names in identifiers, filenames, or types unless required by existing immutable external interfaces
- `misc`, `stuff`, `temp`, `new`, `old`
- meaningless abbreviations not already established by subsystem naming
- overloaded `utils` modules as a dumping ground
- secret-implying names for handles or references
- provider-specific names in shared abstractions

## Consistency rule

When modifying an existing subsystem:

1. Follow the owning TRD first.
2. Match the subsystem’s existing naming style.
3. Preserve boundary contracts and error vocabulary.
4. Prefer extending established patterns over introducing new ones.
5. Keep names explicit, deterministic, and safe for security-reviewed code.