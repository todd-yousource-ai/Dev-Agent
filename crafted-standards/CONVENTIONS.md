# CONVENTIONS.md

This document defines coding conventions, naming rules, and code patterns derived from the repository TRD materials and companion build guidance. It applies to all code in this repository and is subordinate only to the TRDs themselves.

---

# Code Conventions

## Core Principles

- Treat the TRDs as the source of truth for:
  - interfaces
  - state machines
  - security controls
  - error contracts
  - testing requirements
  - subsystem ownership
- Do not invent behavior, fields, states, or error types not supported by the owning TRD.
- Preserve the two-process architecture:
  - Swift process owns UI, authentication, system integration, secrets, Keychain, and local IPC hosting/client responsibilities assigned to it
  - Python process owns intelligence, orchestration, generation, provider integration, GitHub operations, and backend pipeline responsibilities
- Never design code paths that execute generated code.
- All cross-process communication must remain structured, authenticated, and line-delimited JSON over the designated Unix socket mechanism.
- Security-sensitive changes must follow the repository security TRD before implementation.

---

## File and Directory Naming

### Exact `src/` Layout

Use a top-level split by runtime:

```text
src/
  swift/
  python/
```

If the repository already uses more specific names under `src/`, preserve the existing structure and apply the conventions below within that structure. Do not create mixed-language feature folders.

### Swift Directory Conventions

Organize Swift code by subsystem ownership, not by vague utility grouping.

Preferred structure:

```text
src/swift/
  App/
  UI/
    Views/
    Components/
    Panels/
    Cards/
    ViewModels/
  Auth/
  Security/
  Keychain/
  IPC/
  Models/
  State/
  Errors/
  Logging/
  Extensions/
  Tests/
```

Rules:

- `App/` contains application entry, lifecycle wiring, dependency assembly.
- `UI/Views/` contains screen-level SwiftUI views.
- `UI/Components/` contains reusable UI building blocks.
- `UI/Panels/` and `UI/Cards/` contain panel/card implementations when those concepts are explicit in the TRDs.
- `ViewModels/` contains presentation state coordinators only when the owning TRD permits that pattern.
- `Auth/`, `Security/`, `Keychain/`, and `IPC/` must remain separate; do not hide them under generic helpers.
- `Models/` contains immutable data contracts and UI-safe domain representations.
- `State/` contains state machines and reducers/coordinators if defined by the TRDs.
- `Errors/` contains typed error definitions and mapping helpers.
- `Extensions/` is only for narrow language extensions; do not place business logic there.

### Python Directory Conventions

Organize Python code by domain subsystem and pipeline responsibility.

Preferred structure:

```text
src/python/
  backend/
    consensus/
    pipeline/
    providers/
    github/
    ipc/
    models/
    state/
    security/
    errors/
    logging/
    services/
    tests/
```

Rules:

- `consensus/` contains consensus engine logic and supporting strategy types.
- `pipeline/` contains orchestration stages, task graph logic, and stage contracts.
- `providers/` contains external model/provider adapters.
- `github/` contains GitHub API clients, mutation/query helpers, payload mapping, and workflow-specific logic.
- `ipc/` contains line-delimited JSON protocol handling and transport adapters.
- `models/` contains transport, domain, and persistence-safe models.
- `state/` contains backend state machines and workflow state definitions.
- `security/` contains validation, policy enforcement, and boundary checks.
- `services/` contains cohesive backend capabilities that do not fit a lower-level subsystem.
- Avoid generic `utils/` directories unless the contents are truly cross-cutting and cannot belong to a named subsystem.

### File Naming Rules

#### Swift

- Types use `PascalCase`, and filenames must match the primary type.
  - `SessionManager.swift`
  - `AuthenticatedSocketClient.swift`
  - `PullRequestPanel.swift`
- SwiftUI views must end with one of:
  - `View`
  - `Panel`
  - `Card`
  - `Row`
  - `Sheet`
  - `Toolbar`
  as appropriate to the TRD-defined UI role.
- Protocol-first files should be named after the protocol:
  - `TokenProviding.swift`
  - `SocketAuthenticating.swift`
- Extensions use `TypeName+Concern.swift`
  - `Date+Formatting.swift`
  - `URLRequest+GitHub.swift`
- Error files use `...Error.swift` or `...Errors.swift`
  - `IPCError.swift`
  - `AuthenticationErrors.swift`

#### Python

- Files and modules use `snake_case`.
  - `consensus_engine.py`
  - `provider_adapter.py`
  - `github_client.py`
  - `pull_request_service.py`
- One primary class per file when practical.
- Adapter files must be named for the external system or role:
  - `openai_adapter.py`
  - `anthropic_adapter.py`
  - `github_graphql_client.py`
- State machine files should include `_state`, `_machine`, or `_workflow` when they define lifecycle transitions.
  - `review_state.py`
  - `pipeline_workflow.py`
- Error files should end in `_errors.py` or `_error.py`.

---

## Class and Function Naming

## Swift Naming

### Types

- Use `PascalCase` for all types.
- Prefer nouns for entities and services:
  - `SessionStore`
  - `GitHubAuthCoordinator`
  - `SocketHandshakeRequest`
- Prefer role-specific suffixes where behavior is clear:
  - `Manager` for lifecycle/resource ownership
  - `Coordinator` for flow orchestration
  - `Client` for outbound API/IPC access
  - `Store` for owned state
  - `Provider` for dependency abstraction
  - `Validator` for pure validation
  - `Mapper` for transformations
  - `ViewModel` only for UI presentation state
- Do not use vague names like:
  - `Helper`
  - `Util`
  - `Thing`
  - `DataManager`

### Protocols

- Use capability-oriented names:
  - `TokenProviding`
  - `CredentialStoring`
  - `MessageEncoding`
- Prefer `...ing` or clear noun protocols when the protocol represents a role.

### Functions and Methods

- Use `camelCase`.
- Start with a verb.
  - `loadSession()`
  - `validateHandshake(_:)`
  - `presentReviewPanel()`
  - `storeAccessToken(_:)`
- Boolean-returning APIs should read as predicates.
  - `isAuthenticated`
  - `hasRequiredScopes`
  - `canTransition(to:)`
- Throwing methods should reflect the action and rely on typed errors rather than naming conventions like `try...`.

### Properties

- Use nouns for values and adjective/boolean forms for flags.
  - `currentSession`
  - `socketPath`
  - `isDraft`
  - `isConnected`

## Python Naming

### Classes

- Use `PascalCase`.
  - `ConsensusEngine`
  - `ProviderAdapter`
  - `GitHubRestClient`
  - `DraftPullRequestService`
- Abstract/base classes should use one of:
  - `Base...`
  - `Abstract...`
  only if the inheritance role is meaningful and established.

### Functions and Methods

- Use `snake_case`.
  - `run_consensus()`
  - `create_draft_pull_request()`
  - `mark_pull_request_ready_for_review()`
  - `parse_line_delimited_message()`
- Verb-first naming for side effects.
- Predicate functions should start with:
  - `is_`
  - `has_`
  - `can_`
  - `should_`

### Constants

- Use `UPPER_SNAKE_CASE`.
  - `MAX_RETRY_ATTEMPTS`
  - `SOCKET_READ_TIMEOUT_SECONDS`
  - `GITHUB_API_VERSION`

### Internal vs Public APIs

- Prefix internal-only Python functions/methods with `_`.
- Do not use underscore prefixes in Swift as an access-control substitute; use language access modifiers.

---

## Error and Exception Patterns

## General Rules

- Every subsystem must use explicit, typed error handling aligned with the owning TRD.
- Errors must preserve:
  - stable machine-readable code
  - human-readable message
  - contextual metadata safe for logs
  - original cause where supported
- Never leak secrets, tokens, raw credentials, or sensitive payloads into:
  - errors
  - logs
  - UI strings
  - telemetry
- Cross-process errors must serialize into stable protocol-safe error envelopes.
- External API errors must be normalized before crossing subsystem boundaries.

## Swift Error Patterns

- Use `enum` types conforming to `Error` for bounded error domains.
- Group errors by subsystem:
  - `AuthenticationError`
  - `IPCError`
  - `KeychainError`
  - `GitHubAuthError`
- Include narrow cases with associated values only when the values are safe and useful.
- Provide mapping layers from platform/system errors into app-defined errors.
- Prefer:

```swift
enum IPCError: Error {
    case socketUnavailable
    case handshakeFailed(reason: String)
    case invalidMessage
    case unauthorizedPeer
}
```

- Avoid passing raw `NSError` across domain boundaries without mapping.
- Surface UI-facing error text through a presentation layer; do not bind raw internal errors directly to UI.

## Python Exception Patterns

- Use typed exception classes per subsystem.
- Create a shared base exception per subsystem when useful.

Example:

```python
class GitHubError(Exception):
    """Base GitHub integration error."""


class PullRequestTransitionError(GitHubError):
    """Raised when a PR lifecycle transition fails."""
```

- Use exception names ending in `Error`.
- Catch external library exceptions at boundaries and convert them into internal typed exceptions.
- Do not swallow exceptions silently.
- Include retriable vs non-retriable distinction where required by the TRD or integration behavior.
- For protocol and API layers, preserve:
  - operation
  - endpoint or message type
  - status/result classification
  while redacting sensitive data.

## Error Codes and Contracts

- If a TRD defines explicit error codes, use them exactly.
- If machine-readable codes are required, define them centrally and keep them stable.
- Error messages intended for operators must be:
  - concise
  - actionable
  - non-sensitive
- Validation failures should identify the invalid field or invariant, not dump entire payloads.

---

## Per-Subsystem Naming Rules

## Swift Shell

### UI

- Screen-level SwiftUI types: `...View`
- Reusable visual units: `...Card`, `...Panel`, `...Row`
- Modal surfaces: `...Sheet`
- Tool-specific controls: `...Toolbar`
- UI state owners: `...ViewModel` only when they hold presentation state rather than domain orchestration.
- Bindings and state variables should reflect displayed meaning:
  - `selectedRepository`
  - `isShowingAuthSheet`
  - `reviewSummaryText`

Do not name UI files by generic container terms like `Main`, `Screen1`, or `MiscView`.

### Authentication

- Coordinator/flow types:
  - `...AuthCoordinator`
  - `...SignInCoordinator`
- Token/session abstractions:
  - `...TokenStore`
  - `...SessionStore`
  - `...CredentialProvider`
- Browser/web auth callback handlers should indicate callback responsibility:
  - `OAuthCallbackHandler`
  - `AuthRedirectProcessor`

### Keychain and Secrets

- Keychain wrappers:
  - `...KeychainStore`
  - `...SecretStore`
- Secret access protocols:
  - `SecretReading`
  - `SecretWriting`
  - `CredentialStoring`
- Do not use names that imply secrets are plain values or cacheable blobs.
- Secret-bearing types must have names that clarify secure ownership.

### IPC

- Transport/client/server roles:
  - `SocketClient`
  - `SocketServer`
  - `IPCMessageEncoder`
  - `IPCHandshakeValidator`
- Message envelope types:
  - `...Request`
  - `...Response`
  - `...Event`
  - `...Envelope`
- Functions dealing with line-delimited JSON should name framing explicitly:
  - `encode_line_delimited_message` in Python
  - `encodeLineDelimitedMessage()` in Swift if implemented there

### Security

- Validation and policy names should be direct:
  - `ContentValidator`
  - `ExecutionPolicyEnforcer`
  - `CredentialRedactor`
  - `TrustedPeerVerifier`
- Use `Policy`, `Validator`, `Verifier`, `Redactor`, `Sanitizer`, `Enforcer` suffixes for security roles.
- Avoid ambiguous names like `Guard` unless the type models a specific TRD-defined concept.

## Python Backend

### Consensus

- Primary engine: `ConsensusEngine`
- Strategy/adaptation roles:
  - `ConsensusStrategy`
  - `VoteAggregator`
  - `ResponseRanker`
  - `ProviderAdapter`
- Provider-specific consensus helpers should include provider or decision role in the name.

### Pipeline

- Stage-oriented classes/files:
  - `...Stage`
  - `...Pipeline`
  - `...Workflow`
  - `...Orchestrator`
- Stage methods should clearly describe transitions:
  - `prepare_inputs()`
  - `run_generation_stage()`
  - `validate_outputs()`
  - `publish_results()`
- State transitions should use domain language from the TRD, not ad hoc synonyms.

### Provider Integration

- Adapters must end in `Adapter`.
  - `OpenAIAdapter`
  - `AnthropicAdapter`
- Shared provider contracts:
  - `ProviderAdapter`
  - `ProviderRequest`
  - `ProviderResponse`
  - `ProviderCapability`
- Retry and rate-limit helpers should be named for the concern:
  - `RateLimitPolicy`
  - `RetryScheduler`

### GitHub Integration

Use naming that reflects actual GitHub object semantics and known API behavior.

#### Clients

- REST client types/files:
  - `GitHubRestClient`
  - `github_rest_client.py`
- GraphQL client types/files:
  - `GitHubGraphQLClient`
  - `github_graphql_client.py`
- Composite façade/service:
  - `GitHubService`
  - `PullRequestService`
  - `RepositorySyncService`

#### Pull Requests

- PR lifecycle methods must distinguish draft and ready-for-review transitions explicitly:
  - `create_draft_pull_request()`
  - `mark_pull_request_ready_for_review()`
  - `merge_pull_request()`
  - `update_pull_request_metadata()`
- Do not use ambiguous names like `publish_pr()` if the underlying action is specifically draft conversion.
- Where behavior differs between REST and GraphQL, reflect that in helper naming:
  - `mark_ready_for_review_via_graphql()`
  - `update_pull_request_via_rest()`

#### GitHub IDs and References

- Use precise field names:
  - `pull_request_number` for repository-visible PR number
  - `pull_request_id` for GraphQL/global node identifier if applicable
  - `repository_owner`
  - `repository_name`
  - `head_ref_name`
  - `base_ref_name`
- Do not overload `id` when a stronger name is available.

### Models and Contracts

- Transport models should indicate protocol/domain role:
  - `HandshakeRequest`
  - `HandshakeResponse`
  - `PipelineStatusEvent`
  - `PullRequestDescriptor`
- Request/response objects must match TRD field names exactly at system boundaries.
- Internal model names may be more expressive, but boundary mappers must preserve wire compatibility.

### State Machines

- State enums/classes must end in `State` where they model states.
- Transition handlers should use:
  - `transition_to(...)`
  - `can_transition_to(...)`
  - `validate_transition(...)`
- Workflow coordinators may use `...StateMachine` or `...Workflow`.
- State names should be adjectives or nouns representing actual lifecycle states from the TRD:
  - `pending`
  - `running`
  - `failed`
  - `completed`
  - `awaiting_review`
- Do not invent synonymous state labels for the same transition graph.

### Logging and Telemetry

- Logger names should be subsystem-scoped:
  - `auth_logger`
  - `ipc_logger`
  - `github_logger`
- Event names should be stable and machine-readable.
- Log helper names should state redaction or sanitization where applicable:
  - `redact_headers()`
  - `sanitize_error_context()`

---

## Code Patterns

## Boundary Mapping Pattern

At every external boundary, map foreign formats into internal models before business logic.

Examples of boundaries:

- Swift UI ↔ domain state
- Swift shell ↔ Python backend IPC
- Python backend ↔ provider APIs
- Python backend ↔ GitHub REST/GraphQL APIs
- system APIs ↔ application domain

Pattern:

1. Parse/receive boundary payload
2. Validate required fields
3. Map into internal typed model
4. Perform domain logic
5. Map result into boundary contract
6. Redact sensitive context before logging/errors

## Adapter Pattern

Use adapters for all third-party and cross-process integrations.

- External provider integrations must be behind `...Adapter`.
- GitHub protocol differences should be isolated in dedicated clients or adapters.
- System service interactions in Swift should use narrow wrappers rather than direct framework calls throughout the codebase.

## State Machine Pattern

When a TRD defines lifecycle transitions:

- represent states explicitly
- validate transitions centrally
- keep side effects outside bare state types when practical
- make invalid transitions fail with typed errors

## Service vs Manager vs Coordinator

Use these suffixes consistently:

- `Service`: domain capability exposed as an operation set
- `Manager`: owns lifecycle, resources, or caches
- `Coordinator`: orchestrates multi-step flow across components
- `Client`: speaks to an external or remote interface
- `Store`: owns durable or in-memory state
- `Adapter`: translates to/from external systems
- `Validator`: pure invariant checking
- `Mapper`: pure data transformation

Do not use these interchangeably.

## Extension Pattern

### Swift

- Extensions must be small and concern-specific.
- Name files `Type+Concern.swift`.
- Do not hide core business logic inside extensions to unrelated types.

### Python

- Prefer module-level helper functions over pseudo-extension patterns.
- Keep helpers in the subsystem module where they are used.

---

## Data Contract Conventions

- Boundary schemas must remain stable and explicit.
- JSON field naming must match the owning protocol/TRD exactly.
- If the wire contract uses snake_case, preserve snake_case on the wire even if Swift internals use camelCase.
- Add explicit mapping rather than relying on implicit serializer magic where contract stability matters.
- Optional fields must only be used when the TRD permits omission.
- Versioned contracts should include clearly named version fields only when the TRD requires them.

---

## Testing-Oriented Conventions

- Test names should describe behavior, not implementation.
- Mirror subsystem names in test layout.
- Name tests by scenario and expected result.

Examples:

- Swift:
  - `IPCHandshakeValidatorTests.swift`
  - `PullRequestPanelTests.swift`
- Python:
  - `test_mark_pull_request_ready_for_review_uses_graphql.py`
  - `test_invalid_handshake_returns_protocol_error.py`

Behavior naming patterns:

- `test_<condition>_<expected_result>()`
- `test_<operation>_<scenario>_<result>()`

Focus tests on:

- TRD-defined interfaces
- state transitions
- error contracts
- redaction behavior
- protocol compatibility
- GitHub lifecycle edge cases discovered in integration lessons

---

## Prohibited Naming and Structure Patterns

Do not use:

- `misc`, `helpers`, `stuff`, `common` as catch-all dumping grounds
- ambiguous method names like `handle()`, `process()`, `do_work()` without context
- generic type names like `Manager`, `Service`, or `Client` without a domain prefix
- duplicate concepts with different names across Swift and Python
- undocumented abbreviations in public APIs
- direct exposure of third-party payloads beyond integration boundaries

Avoid:

- mixing UI logic into security/auth code
- mixing provider-specific logic into generic consensus interfaces
- mixing REST and GraphQL behavior in a single ambiguously named GitHub method
- passing raw dictionaries/maps deep into domain code when typed models are available

---

## Cross-Language Consistency Rules

When Swift and Python represent the same concept:

- use the same domain term in both languages
- vary only for language idiom
  - Swift: `PullRequestDescriptor`
  - Python: `PullRequestDescriptor`
  - Swift property: `pullRequestNumber`
  - Python field: `pull_request_number`
- keep state names, error codes, and protocol message types semantically identical
- do not rename a concept across the process boundary for convenience

---

## Documentation Conventions in Code

- Public interfaces should include concise documentation where the TRD contract is non-obvious.
- Document invariants, redaction requirements, and lifecycle assumptions.
- Do not document behavior contrary to the TRDs.
- For GitHub-specific operations, document protocol choice when behavior is non-obvious, especially where draft PR transitions require GraphQL rather than REST.

---

## Final Rule

If a convention here conflicts with an owning TRD, the TRD wins. If a change introduces a new subsystem pattern, naming family, or error contract, update this document only after the TRD support for that pattern is confirmed.