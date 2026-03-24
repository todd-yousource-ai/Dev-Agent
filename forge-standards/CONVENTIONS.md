# Code Conventions

This document defines coding conventions, naming rules, and code patterns derived from the provided technical repository documents. These conventions apply across the full two-process architecture, all source subsystems, and mirrored test structure.

## File and Directory Naming (exact `src/` layout)

### Top-level source layout

Use a source layout that reflects ownership boundaries and subsystem responsibilities.

```text
src/
  shell/          # Swift process: UI, auth, Keychain, XPC, native orchestration
  backend/        # Python process: consensus, planning, generation, VCS operations
  cal/            # Conversation Abstraction Layer components
  dtl/            # Data Trust Label components
  trustflow/      # Audit stream components
  vtz/            # Virtual Trust Zone enforcement
  trustlock/      # Cryptographic machine identity components
  mcp/            # Policy engine components
  rewind/         # Replay engine components
sdk/
  connector/      # Connector SDK
tests/
  shell/
  backend/
  cal/
  dtl/
  trustflow/
  vtz/
  trustlock/
  mcp/
  rewind/
```

Tests must mirror `src/` structure exactly.

### Directory naming rules

- Use lowercase directory names.
- Use singular subsystem names exactly as defined by the repository structure.
- Do not invent alternate aliases for subsystem directories.
- Group code by responsibility first, then by feature.
- Keep security-sensitive code in clearly bounded directories owned by the appropriate process or subsystem.

### File naming rules

#### Swift files
- Use `PascalCase.swift` matching the primary type in the file.
- One primary top-level type per file.
- Supporting extensions may remain in the same file only if tightly related.
- View files must be named after the view type, for example:
  - `SessionPanel.swift`
  - `ReviewCard.swift`
  - `AuthenticationCoordinator.swift`

#### Python files
- Use `snake_case.py`.
- Filename should describe the primary module responsibility.
- Prefer nouns for domain modules and verb phrases only for task runners or command modules.
- Examples:
  - `consensus_engine.py`
  - `provider_adapter.py`
  - `plan_builder.py`
  - `github_client.py`
  - `socket_protocol.py`

#### Test files
- Swift tests: match the tested type or feature, suffixed by `Tests.swift`.
- Python tests: `test_<module_name>.py`.
- Test paths must mirror production paths exactly.
- Examples:
  - `tests/backend/test_consensus_engine.py`
  - `tests/dtl/test_label_parser.py`

### Generated and interface-bound files

- Files implementing protocol, schema, or transport contracts must be named after the contract they implement.
- JSON line protocol handlers should use names indicating transport role:
  - `socket_server.py`
  - `socket_client.py`
  - `message_codec.py`

## Class and Function Naming

### General naming rules

- Name by responsibility, not implementation detail.
- Use stable domain terminology from the TRDs.
- Avoid abbreviations unless they are the subsystem’s canonical short name.
- Do not encode version numbers, provider names, or temporary rollout markers in identifiers.
- Prefer explicit names over generic names like `Manager`, `Helper`, or `Util` unless the type truly coordinates a broad responsibility.

### Swift naming

#### Types
- Use `PascalCase` for:
  - classes
  - structs
  - enums
  - protocols
  - actors
- Protocols should be capability-oriented and noun-based:
  - `CredentialStore`
  - `AuthenticationProvider`
  - `PipelineCoordinator`

#### Methods and properties
- Use `camelCase`.
- Method names should read as actions or queries.
- Boolean properties should be prefixed with `is`, `has`, `can`, or `should`.
- Prefer argument labels that read naturally at call sites.

Examples:
- `startSession()`
- `validateIntent(_:)`
- `openDraftPullRequest(for:)`
- `isAuthenticated`
- `hasPendingReview`

#### Enum cases
- Use `camelCase`.
- Name cases semantically, not numerically.

### Python naming

#### Classes
- Use `PascalCase`.
- Name core domain components as nouns:
  - `ConsensusEngine`
  - `ProviderAdapter`
  - `PolicyEvaluator`
  - `ReplaySession`

#### Functions and methods
- Use `snake_case`.
- Use verbs for commands and noun phrases only for pure constructors/factories where appropriate.
- Examples:
  - `build_plan()`
  - `run_fix_loop()`
  - `parse_label()`
  - `emit_audit_event()`

#### Constants
- Use `UPPER_SNAKE_CASE`.
- Constants must represent true invariants or configuration defaults, not mutable runtime state.

### Naming for transport and protocol code

- Transport message types must be named by domain intent, not wire mechanics.
- Use names like:
  - `AuthRequest`
  - `PlanAccepted`
  - `PipelineStatusEvent`
  - `ErrorResponse`
- Codec and serializer names must indicate direction or role:
  - `encode_message`
  - `decode_line`
  - `serialize_event`

## Error and Exception Patterns

### General principles

- Follow the owning TRD’s error contract exactly.
- Errors must be typed and structured.
- Never use ambiguous, catch-all error names where a bounded domain error exists.
- Error messages must be actionable, concise, and safe for logs.
- Never place secrets, tokens, raw credentials, or sensitive generated content in error text.

### Swift error conventions

- Define bounded error enums per subsystem or feature.
- Use `PascalCase` enum names ending in `Error`.
- Enum cases use `camelCase`.
- Conform to `Error`; add localized presentation only when the UI requires it.
- Separate internal diagnostic context from user-facing text.

Example pattern:
- `AuthenticationError`
- `SocketProtocolError`
- `KeychainAccessError`

Preferred case naming:
- `.invalidCredentials`
- `.connectionClosed`
- `.malformedMessage`
- `.authorizationDenied`

### Python exception conventions

- Define custom exceptions for domain failures.
- Use `PascalCase` names ending in `Error`.
- Inherit from a subsystem-specific base error where practical.

Example hierarchy:
- `BackendError`
  - `ConsensusError`
  - `ProviderError`
  - `PipelineError`
  - `GitOperationError`

### Error propagation rules

- Validate at boundaries.
- Translate low-level errors into domain errors before crossing process or subsystem boundaries.
- Preserve causal context internally.
- Expose only contract-safe error payloads over socket or UI boundaries.
- Transport-facing errors must map to line-delimited JSON error responses consistently.

### Logging and observability rules for errors

- Log structured context, not free-form dumps.
- Include identifiers such as:
  - request id
  - session id
  - plan id
  - pull request unit id
- Exclude:
  - credentials
  - raw secret material
  - unsafe external content
  - generated code unless explicitly permitted by the owning security requirements

## Per-Subsystem Naming Rules

## `shell/` naming rules

This process owns UI, authentication, secret handling, native coordination, and local interprocess communication.

### Type naming
- Coordinators: `<Domain>Coordinator`
- Stores: `<Domain>Store`
- Native service wrappers: `<Domain>Service`
- Keychain adapters: `<Domain>KeychainStore`
- XPC-facing types: `<Domain>XPCClient`, `<Domain>XPCServer`

### UI naming
- SwiftUI views use visible role names:
  - `<Domain>View`
  - `<Domain>Panel`
  - `<Domain>Card`
  - `<Domain>Sheet`
- View models, if present, use `<Domain>ViewModel`.

Examples:
- `IntentPanel`
- `PlanReviewCard`
- `SessionView`
- `AuthenticationViewModel`

### Auth and secret naming
- Types dealing with credentials must be explicit:
  - `CredentialStore`
  - `AuthenticationSession`
  - `TokenRefreshCoordinator`
- Never use vague names like `SecretsHelper`.

## `backend/` naming rules

This process owns planning, consensus, generation, correction loops, lint gating, CI orchestration, and repository operations.

### Core engine naming
- Engines use `<Domain>Engine`.
- Adapters use `<Provider>Adapter` only when the provider distinction is part of the contract; otherwise use role-based names such as `ModelAdapter`.
- Orchestrators use `<Domain>Orchestrator`.
- Iterative loops use `<Domain>Loop`.

Examples:
- `ConsensusEngine`
- `PipelineOrchestrator`
- `FixLoop`
- `LintGate`
- `CiEvaluator`

### Planning and decomposition naming
- Intent-level logic:
  - `IntentAssessor`
  - `PlanBuilder`
  - `ScopeEvaluator`
- PRD and pull request decomposition:
  - `PrdPlanner`
  - `PullRequestSequenceBuilder`
  - `WorkUnitClassifier`

### Version control and review naming
- Use explicit repository operation names:
  - `RepositoryClient`
  - `BranchPlanner`
  - `PullRequestPublisher`
  - `DraftReviewFormatter`

## `cal/` naming rules

Conversation Abstraction Layer code must use abstraction-oriented naming.

- Interfaces: `<Domain>Channel`, `<Domain>Session`, `<Domain>Message`
- Adapters: `<Provider>ConversationAdapter` only where provider-specific behavior is required
- Normalizers: `<Domain>Normalizer`
- State trackers: `<Domain>SessionState`

Examples:
- `ConversationSession`
- `MessageNormalizer`
- `ChannelPolicy`

Use `message`, `turn`, `session`, and `channel` consistently; do not mix with unrelated terminology such as `chat` unless the contract explicitly does.

## `dtl/` naming rules

Data Trust Label components must name labels and trust state explicitly.

- Core types:
  - `TrustLabel`
  - `LabelParser`
  - `LabelPolicy`
  - `LabelValidator`
  - `LabelDecision`
- Metadata carriers:
  - `LabeledDocument`
  - `LabeledArtifact`
  - `TrustAnnotatedContent`

Boolean fields should clearly state trust meaning:
- `isTrusted`
- `isRestricted`
- `hasExternalOrigin`

Avoid generic names like `Tag` or `Marker` when the domain concept is a trust label.

## `trustflow/` naming rules

Audit stream code must emphasize event lineage, traceability, and append-only behavior.

- Event types: `<Domain>Event`
- Sinks and emitters:
  - `AuditEmitter`
  - `EventSink`
  - `AuditStreamWriter`
- Correlation types:
  - `TraceContext`
  - `EventEnvelope`
  - `AuditCursor`

Examples:
- `PipelineEvent`
- `SecurityDecisionEvent`
- `AuditStreamWriter`

Event names should be immutable and descriptive. Do not use vague event names like `UpdatedEvent`.

## `vtz/` naming rules

Virtual Trust Zone enforcement must use boundary and enforcement language.

- Enforcement types:
  - `ZonePolicy`
  - `ZoneEnforcer`
  - `BoundaryGuard`
  - `ExecutionConstraint`
  - `ContentIsolationRule`
- Evaluation outputs:
  - `ZoneDecision`
  - `BoundaryViolation`
  - `IsolationResult`

Names must make clear whether a type:
- defines policy
- evaluates policy
- enforces policy
- reports violations

## `trustlock/` naming rules

Cryptographic machine identity components must use identity, attestation, and key material terminology precisely.

- Identity types:
  - `MachineIdentity`
  - `AttestationRecord`
  - `KeyHandle`
  - `IdentityProof`
- Services:
  - `IdentityProvider`
  - `AttestationVerifier`
  - `KeyProvisioningService`

Do not use names that imply raw key exposure. Prefer `KeyHandle` over `PrivateKey` unless the type truly contains raw key material and the TRD explicitly permits that representation.

## `mcp/` naming rules

Policy engine code must use rule-evaluation terminology.

- Core types:
  - `PolicyEngine`
  - `PolicyRule`
  - `PolicyInput`
  - `PolicyDecision`
  - `DecisionReason`
- Composition:
  - `RuleSet`
  - `PolicyBundle`
  - `EvaluationContext`

Functions should distinguish:
- loading policy
- evaluating policy
- explaining policy decisions
- enforcing policy outcomes

Examples:
- `load_policy_bundle()`
- `evaluate_policy()`
- `explain_decision()`

## `rewind/` naming rules

Replay engine code must use deterministic replay terminology.

- Core types:
  - `ReplayEngine`
  - `ReplaySession`
  - `ReplayFrame`
  - `ReplayCursor`
  - `ReplaySnapshot`
- Validation and comparison:
  - `ReplayVerifier`
  - `FrameComparator`
  - `DeterminismCheck`

Prefer `replay`, `frame`, `snapshot`, and `cursor` over generic words like `history` or `recording` unless the owning contract distinguishes them.

## `sdk/connector/` naming rules

Connector SDK code must use integration-facing terminology.

- Public API types:
  - `ConnectorClient`
  - `ConnectorSession`
  - `ConnectorRequest`
  - `ConnectorResponse`
- Configuration:
  - `ConnectorConfig`
  - `RetryPolicy`
  - `TransportConfig`

SDK public names must be stable, explicit, and free of internal implementation details.

## Code patterns

### Boundary-first design

- Validate all external inputs at the process and subsystem boundaries.
- Parse transport data into typed domain models early.
- Reject malformed, unauthorized, or unsafe content before deeper processing.
- Keep policy, validation, transport, and business logic separated.

### Single-responsibility modules

- Each file should own one primary concept.
- Each class should have one clear responsibility.
- Prefer composition over deep inheritance.
- Extract policy evaluation, transport handling, persistence, and orchestration into separate types.

### Contract-driven implementation

- Interfaces, state transitions, message formats, and error behaviors must follow the owning TRD exactly.
- Do not add undocumented fields to wire contracts.
- Do not collapse distinct state machine states into generic status strings.

### Two-process communication pattern

- Interprocess communication must use authenticated Unix socket transport with line-delimited JSON.
- Message handlers should follow this flow:
  1. receive line
  2. decode
  3. validate schema
  4. authorize
  5. execute domain logic
  6. encode typed response or typed error

### Safe execution pattern

- Neither process may execute generated code.
- Code that handles generated artifacts must use names indicating non-execution behavior:
  - `GeneratedArtifactStore`
  - `PatchApplier`
  - `CandidateValidator`

Avoid names like `Runner` or `Executor` for generated output handling unless the TRD explicitly defines a safe, non-code-execution use.

### Testing pattern

- Tests must mirror subsystem structure exactly.
- Name tests by observable behavior.
- Prefer contract and state-machine assertions over implementation-detail assertions.
- Include tests for:
  - success path
  - boundary validation
  - error contract behavior
  - security restrictions
  - replayability or determinism where relevant

### Naming anti-patterns to avoid

Do not use:
- `misc`
- `helpers`
- `stuff`
- `data` for typed domain objects
- `manager` for narrow responsibilities
- `util` when a specific domain name exists
- provider-specific names in generic abstraction layers
- transport-specific names in domain models

## Final rules

- The TRDs are the authority for interfaces, behavior, security controls, and testing requirements.
- Use the subsystem’s canonical terminology consistently.
- Keep names explicit, typed, and boundary-aware.
- Preserve process ownership boundaries in both code structure and naming.
- Keep test structure isomorphic to source structure.