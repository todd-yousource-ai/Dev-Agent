# Code Conventions

This document defines repository-wide coding conventions derived from the technical requirements and operational notes in the provided TRD materials. These conventions are mandatory for all code, tests, interfaces, and supporting assets.

The repository is a two-process native macOS system:

- a **Swift process** for UI, authentication, Keychain access, and XPC/system-facing concerns
- a **Python process** for orchestration, consensus, generation pipeline, and source-control platform operations

All implementation must follow the owning TRD for the subsystem being modified. Where a subsystem boundary exists, naming and behavior must make that boundary explicit.

---

## General Principles

- Treat the TRDs as the source of truth for:
  - interfaces
  - error contracts
  - state machines
  - security controls
  - testing requirements
  - performance requirements
- Do not invent protocol fields, lifecycle states, or security behavior.
- Do not hardcode product identity into symbols, file names, constants, log prefixes, or comments unless required by an external protocol.
- Keep the Swift and Python responsibilities strictly separated.
- Generated code must never be executed by either process.
- Inter-process communication must remain authenticated and line-delimited JSON over the defined Unix socket boundary.
- Security-sensitive changes must align with the security TRD before implementation.

---

## File and Directory Naming (exact `src/` layout)

Use a top-level `src/` split by runtime/language boundary.

```text
src/
├── swift/
│   ├── app/
│   ├── auth/
│   ├── keychain/
│   ├── ipc/
│   ├── xpc/
│   ├── models/
│   ├── viewmodels/
│   ├── views/
│   ├── components/
│   ├── state/
│   ├── services/
│   ├── security/
│   ├── logging/
│   ├── utilities/
│   └── testsupport/
└── python/
    ├── api/
    ├── consensus/
    ├── providers/
    ├── pipeline/
    ├── github/
    ├── ipc/
    ├── models/
    ├── services/
    ├── security/
    ├── logging/
    ├── utils/
    └── testsupport/
```

If the repository already uses a different root split, preserve the existing physical layout but apply the same naming rules and subsystem separation.

### Directory Rules

- Directory names use **lowercase snake_case** in Python areas.
- Directory names use **lowercase** or **lowercase snake_case** in Swift support areas where they map to filesystem folders, but contained type names remain Swift-standard PascalCase.
- Group files by subsystem, not by vague technical category.
- Do not create folders named `misc`, `helpers`, `common`, or `stuff`.
- Shared schema/model definitions must live in `models/` within the owning process unless the TRD defines a different boundary.
- IPC message definitions must live under `ipc/` in each process.

### File Naming Rules

#### Swift files
- One primary type per file.
- File name must exactly match the primary type name.

Examples:
- `SessionManager.swift`
- `AuthenticatedSocketClient.swift`
- `KeychainCredentialStore.swift`
- `PullRequestCardView.swift`

#### Python files
- File names use **snake_case** and reflect the primary class, module, or function role.

Examples:
- `consensus_engine.py`
- `provider_adapter.py`
- `pull_request_service.py`
- `line_delimited_json_protocol.py`

#### Test files
- Swift tests:
  - `TypeNameTests.swift`
  - `SubsystemNameIntegrationTests.swift`
- Python tests:
  - `test_<module_name>.py`
  - `test_<subsystem>_integration.py`

Examples:
- `SessionManagerTests.swift`
- `AuthenticatedSocketClientIntegrationTests.swift`
- `test_consensus_engine.py`
- `test_github_merge_flow_integration.py`

---

## Class and Function Naming

### Swift Naming

Use standard Swift API Design Guidelines.

#### Types
- Use **PascalCase** for:
  - classes
  - structs
  - enums
  - protocols
  - actors
  - typealiases

Examples:
- `ConsensusRequest`
- `AuthenticationState`
- `SocketMessageEnvelope`
- `KeychainCredentialStore`

#### Functions and methods
- Use **lowerCamelCase**.
- Start with a verb when the function performs an action.
- Start with `is`, `has`, `can`, or `should` for booleans.
- Prefer argument labels that read naturally at call sites.

Examples:
- `loadSession()`
- `storeCredential(_:for:)`
- `connect(to:)`
- `sendMessage(_:)`
- `markReadyForReview(pullRequestID:)`

#### Properties
- Use **lowerCamelCase**.
- Nouns for stored values.
- Boolean properties must read as predicates.

Examples:
- `sessionToken`
- `socketPath`
- `isAuthenticated`
- `hasValidCredential`

#### Protocols
- Name protocols by capability or role.
- Prefer nouns or `-ing` only when the protocol models a continuous behavior.

Examples:
- `CredentialStore`
- `SocketAuthenticating`
- `PullRequestManaging`

Do not use:
- `CredentialStoreProtocol`
- `ManagerProtocol`

#### Enums
- Enum type names use PascalCase.
- Enum cases use lowerCamelCase.
- State enums must be explicit and finite.

Examples:
- `AuthenticationState.idle`
- `AuthenticationState.authenticating`
- `AuthenticationState.authenticated`
- `AuthenticationState.failed`

### Python Naming

Follow PEP 8, with repository-specific rules below.

#### Classes
- Use **PascalCase**.

Examples:
- `ConsensusEngine`
- `ProviderAdapter`
- `PullRequestService`
- `AuthenticatedSocketServer`

#### Functions and methods
- Use **snake_case**.
- Use verbs for actions.
- Use `is_`, `has_`, `can_`, `should_` prefixes for booleans where useful.

Examples:
- `build_consensus()`
- `validate_message()`
- `store_credential_reference()`
- `is_draft_pull_request()`

#### Variables
- Use **snake_case**.
- Avoid abbreviations except well-known protocol terms.

Preferred:
- `pull_request_number`
- `repository_owner`
- `line_delimited_payload`

Avoid:
- `pr_num`
- `repo_own`
- `ld_payload`

#### Constants
- Use **UPPER_SNAKE_CASE**.

Examples:
- `MAX_MESSAGE_BYTES`
- `DEFAULT_SOCKET_TIMEOUT_SECONDS`
- `GITHUB_GRAPHQL_ENDPOINT`

#### Modules
- Use **snake_case** and make the name describe the domain behavior.

Examples:
- `draft_pull_request_lifecycle.py`
- `mergeability_validator.py`

---

## Error and Exception Patterns

Errors must follow subsystem contracts defined by the owning TRD. Name errors so that the source, scope, and handling expectation are obvious.

### Cross-Language Error Principles

- Errors must be typed and categorized.
- Never swallow an error that changes security, state machine correctness, or external side effects.
- Preserve the original cause when wrapping errors.
- Messages must be actionable and safe:
  - no secrets
  - no tokens
  - no raw credentials
  - no sensitive payload dumps
- User-facing messages and diagnostic messages must be separated where the architecture supports it.
- IPC and network errors must include enough structured context for retry and telemetry decisions.

### Swift Error Conventions

- Prefer `enum` types conforming to `Error` for domain errors.
- Name error enums as `<Subsystem>Error`.

Examples:
- `AuthenticationError`
- `KeychainError`
- `IPCError`
- `PullRequestError`

- Use specific cases, not catch-all strings.

Example:
```swift
enum IPCError: Error {
    case unauthenticatedPeer
    case invalidMessageFormat
    case messageTooLarge
    case connectionClosed
}
```

- If an error wraps an underlying system/framework error, include the associated value.

Example:
```swift
enum KeychainError: Error {
    case itemNotFound
    case accessDenied
    case unexpectedStatus(OSStatus)
}
```

- Functions that can fail must either:
  - `throw` typed errors, or
  - return a TRD-defined result type

Do not:
- return `nil` for meaningful failures unless the absence is explicitly non-error by contract
- use generic `NSError` in domain code unless bridging from an Apple API boundary

### Python Exception Conventions

- Define custom exception classes per subsystem.
- Name exceptions as `<Subsystem>Error` or more specific derivatives.

Examples:
- `ConsensusError`
- `ProviderError`
- `PipelineError`
- `GitHubApiError`
- `PullRequestLifecycleError`

- Build inheritance trees only where handling semantics require it.

Example:
```python
class GitHubError(Exception):
    pass

class GitHubApiError(GitHubError):
    pass

class DraftPullRequestStateError(GitHubError):
    pass
```

- Raise exceptions with concise, structured messages.
- Attach machine-usable context as attributes when needed for retry or reporting logic.

Example:
```python
class GitHubApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
```

### IPC Error Handling

- Treat all inbound messages as untrusted until validated.
- Validation failures must map to explicit protocol or authentication errors.
- Do not continue processing after:
  - authentication failure
  - schema validation failure
  - framing corruption
  - message size violation
- Use names that distinguish transport failures from payload failures.

Preferred:
- `SocketConnectionError`
- `MessageFramingError`
- `MessageValidationError`
- `PeerAuthenticationError`

### External API Error Handling

For source-control platform interactions:

- Separate:
  - transport failure
  - authentication/authorization failure
  - rate limit failure
  - validation failure
  - unsupported API behavior
  - workflow state conflict
- Encode API-specific lifecycle constraints explicitly in names.

Examples:
- `DraftPullRequestConversionError`
- `MergeabilityPollingTimeoutError`
- `BranchUpdateConflictError`

- Where known API behavior differs between REST and GraphQL, name the method and exception to reflect the actual supported mechanism.

Preferred:
- `mark_ready_for_review_via_graphql()`
- `GraphQLMutationError`

Avoid:
- `update_pull_request()` when the implementation actually depends on a specific mutation lifecycle

---

## Per-Subsystem Naming Rules

## Swift Shell Subsystems

### App and Process Boundary

Use names that make process ownership explicit.

Preferred:
- `ShellApplication`
- `BackendProcessLauncher`
- `BackendConnectionMonitor`

Avoid ambiguous names:
- `AppCore`
- `MainManager`

If a type exists only in the Swift process, do not name it as if it were shared runtime infrastructure.

### Authentication

Authentication code must clearly distinguish:
- operator sign-in/session state
- backend peer authentication
- stored credential state

Preferred names:
- `UserSession`
- `AuthenticationState`
- `SessionTokenProvider`
- `PeerAuthenticator`

Avoid:
- `AuthThing`
- `TokenManager` if it handles multiple unrelated credential forms

### Keychain and Secrets

Anything that stores, reads, rotates, or deletes secrets must be explicit.

Preferred:
- `KeychainCredentialStore`
- `SecretReference`
- `CredentialAccessPolicy`
- `StoredCredentialRecord`

Rules:
- Files under `keychain/` or `security/` must include `Keychain`, `Credential`, `Secret`, `Security`, or the precise security domain in the type name.
- Never use `DataStore` or `Cache` for secret persistence types.

### IPC / Unix Socket / XPC

Distinguish transport, framing, authentication, and message schema.

Preferred:
- `AuthenticatedSocketClient`
- `SocketMessageFramer`
- `LineDelimitedJSONEncoder`
- `IPCMessageEnvelope`
- `BackendXPCBridge`

Avoid:
- `SocketHelper`
- `MessageUtils`

When a type implements the line-delimited JSON protocol, include at least one of:
- `LineDelimited`
- `JSONProtocol`
- `MessageFramer`
- `Envelope`

### UI, Views, and ViewModels

Use suffixes consistently.

#### Views
- SwiftUI view types must end in `View`.

Examples:
- `AuthenticationPanelView`
- `PullRequestCardView`
- `BuildStatusView`

#### View models
- View model types must end in `ViewModel`.

Examples:
- `AuthenticationPanelViewModel`
- `RepositoryStateViewModel`

#### Reusable UI components
- Components may end in `View`, `Button`, `Panel`, `Card`, or `Row` according to UI role.

Examples:
- `RepositoryCardView`
- `PrimaryActionButton`
- `StatusRow`

Do not use:
- `ThingView`
- `DataCard` unless the domain noun is explicit

### State and Models

- State-holder types must end in `State` when modeling mutable app or workflow state.
- Immutable message or schema types should use domain nouns such as `Request`, `Response`, `Envelope`, `Descriptor`, `Record`, or `Snapshot`.

Examples:
- `ApplicationState`
- `PipelineState`
- `RepositorySnapshot`
- `AuthRequest`
- `AuthResponse`

---

## Python Backend Subsystems

### Consensus and Provider Orchestration

Consensus-related types must use the exact domain vocabulary.

Preferred:
- `ConsensusEngine`
- `ConsensusRequest`
- `ConsensusResult`
- `ProviderAdapter`
- `ProviderResponseAggregator`

Avoid:
- `ModelManager`
- `AIService`
- `Brain`

Methods should describe orchestration stages clearly.

Examples:
- `build_consensus()`
- `collect_provider_responses()`
- `score_candidate_outputs()`
- `select_consensus_result()`

### Pipeline and Generation

Pipeline naming must reflect ordered stages and non-execution constraints.

Preferred:
- `PipelineStage`
- `GenerationPipeline`
- `PatchAssemblyStage`
- `ValidationStage`
- `ArtifactBundle`

Rules:
- Names involving generated outputs should use `artifact`, `patch`, `bundle`, `result`, or `output`.
- Do not use `runner`, `executor`, or `sandbox` unless the TRD explicitly defines such a component.
- Avoid names suggesting generated code is executed.

### Source-Control Platform Integration

This subsystem has special naming requirements because API behavior is lifecycle-sensitive.

#### Services and clients
Preferred:
- `GitHubRestClient`
- `GitHubGraphQLClient`
- `PullRequestService`
- `DraftPullRequestService`
- `MergeabilityPoller`

If the implementation depends on API modality, include `Rest` or `GraphQL` in the type/function name.

#### Pull request lifecycle methods
Use names that match actual platform behavior.

Preferred:
- `create_draft_pull_request()`
- `mark_ready_for_review()`
- `poll_mergeability_state()`
- `merge_pull_request()`
- `update_pull_request_branch()`

If converting draft to ready for review, prefer names that indicate the supported GraphQL path where relevant:
- `mark_ready_for_review_via_graphql()`

Do not name a method as though REST supports a state transition if that transition actually requires GraphQL.

#### GraphQL operations
- Name wrappers after the mutation/query intent, not generic transport verbs.

Examples:
- `mark_pull_request_ready_for_review_mutation()`
- `pull_request_mergeability_query()`

#### API result objects
- Use names like:
  - `PullRequestDescriptor`
  - `MergeabilityState`
  - `RepositoryRef`
  - `WorkflowRunSummary`

Avoid generic names like:
- `Data`
- `Info`
- `ResponseObject`

### IPC and Protocol Handling in Python

Use names that distinguish:
- transport server/client
- message framing
- schema validation
- peer authentication

Preferred:
- `AuthenticatedSocketServer`
- `LineDelimitedJsonProtocol`
- `MessageEnvelopeParser`
- `PeerAuthenticationValidator`

Note: if using JSON in a class name in Python, `Json` is acceptable in type names; module names remain `json`.

### Security

Security code must be unmistakable by file and symbol name.

Preferred:
- `content_safety_validator.py`
- `credential_redactor.py`
- `external_input_classifier.py`
- `secret_exposure_guard.py`

Avoid:
- `filters.py`
- `checks.py`

All code that validates external or generated content should use names containing one of:
- `validator`
- `guard`
- `policy`
- `classifier`
- `sanitizer`

### Logging and Telemetry

Logging modules must indicate whether they format, redact, emit, or correlate events.

Preferred:
- `structured_logger.py`
- `log_redactor.py`
- `event_emitter.py`
- `trace_context.py`

Avoid:
- `logger_utils.py`

---

## Interface and Message Naming

### JSON / IPC Fields

Use stable, explicit field names.

Preferred field naming:
- JSON fields: `snake_case`
- enum values: lowercase snake_case unless the protocol requires another form

Examples:
```json
{
  "message_type": "auth_request",
  "request_id": "req_123",
  "session_token": "...",
  "payload": {}
}
```

Avoid:
- mixed casing in the same schema
- single-letter keys except where external protocols require them

### Requests and Responses

Use symmetrical names.

Preferred:
- `AuthRequest` / `AuthResponse`
- `ConsensusRequest` / `ConsensusResponse`
- `PullRequestCreateRequest` / `PullRequestCreateResponse`

For event-style messages, use:
- `...Event`
- `...Notification`
- `...Snapshot`

Choose one based on semantics and use it consistently.

---

## State Machine Naming

Where the TRD defines a state machine:

- The enum/type name must end in `State`.
- Transition functions must use verbs like:
  - `begin...`
  - `complete...`
  - `fail...`
  - `transitionTo...`
- Boolean guards must read as state predicates.

Examples:
- `PipelineState`
- `beginAuthentication()`
- `completeMerge()`
- `failValidation(with:)`
- `canRetry`

Do not model TRD-defined states with freeform strings when an enum or constrained type is possible.

---

## Asynchronous Code Naming

### Swift
- Async functions should still use verb-first names without `async` suffix unless needed for overload disambiguation.
- Completion handlers, where used, should be named `completion`.
- Methods that update UI-bound state should indicate that effect when not obvious.

Examples:
- `loadRepositoryState() async`
- `refreshPullRequests() async`
- `updateAuthenticationState()`

### Python
- Coroutine functions use `async def` and standard snake_case names.
- Do not suffix every coroutine with `_async`; only use it when needed to distinguish from a synchronous variant.

Preferred:
- `poll_mergeability_state()`
- `stream_protocol_messages()`

Avoid:
- `poll_mergeability_state_async()`

---

## Test Naming Conventions

### Test function names

#### Swift
- Use descriptive test names that encode scenario and expectation.

Examples:
- `testConnectRejectsUnauthenticatedPeer()`
- `testStoreCredentialReturnsItemNotFoundWhenMissing()`
- `testMarkReadyForReviewUsesGraphQLMutation()`

#### Python
- Use `test_<scenario>_<expected_behavior>()`.

Examples:
- `test_create_draft_pull_request_sets_draft_flag()`
- `test_mark_ready_for_review_uses_graphql_mutation()`
- `test_invalid_message_fails_schema_validation()`

### Test class names

#### Swift
- `<TypeName>Tests`
- `<SubsystemName>IntegrationTests`

#### Python
- `Test<TypeName>`
- `Test<SubsystemName>Integration`

### Fixture naming

- Use `fixture_` prefix for reusable Python fixtures where not managed by framework decorators alone.
- Use `Mock`, `Stub`, `Fake`, or `Spy` suffixes according to test-double behavior.

Examples:
- `ProviderAdapterStub`
- `KeychainStoreFake`
- `SocketClientSpy`

Do not use `TestData1`, `DummyThing`, or `Obj`.

---

## Naming Rules for External API Behavior Learned in Production

The source-control platform integration must encode known platform behavior in both naming and implementation.

### Draft pull request lifecycle

- Opening pull requests as draft must be reflected explicitly:
  - `create_draft_pull_request()`
  - `DraftPullRequestService`
- Conversion from draft to ready for review must not be represented as a generic PATCH update when the actual supported path is GraphQL.
- Use names that preserve this distinction:
  - `mark_ready_for_review_via_graphql()`
  - `MarkReadyForReviewMutation`
  - `DraftPullRequestConversionError`

### Silent no-op behavior

When an API is known to accept a request but ignore a field without error:
- method names must not imply guaranteed state mutation unless verification follows
- postcondition checks must be explicit in code structure

Preferred helper names:
- `verify_pull_request_ready_state()`
- `assert_postcondition()`
- `refresh_pull_request_state()`

Avoid:
- `set_pull_request_draft_status()` if the backing API path does not reliably enforce the change

---

## Forbidden Naming Patterns

Do not introduce any of the following unless required by an external dependency:

- `Helper`, `Utils`, `Common`, `Misc`
- `Manager` without a specific domain prefix
- `Thing`, `Stuff`, `Data`, `Info`
- `Handler` when the behavior is actually validation, transport, or state orchestration
- `Service` for every class by default; use it only when the type truly models a service boundary
- abbreviations such as:
  - `cfg`
  - `msg`
  - `authn` / `authz` in public APIs
  - `pr` in public type names unless the surrounding module is already strictly pull-request scoped

Allowed exceptions:
- established protocol or platform abbreviations in localized contexts, such as:
  - `IPC`
  - `XPC`
  - `JSON`
  - `URL`
  - `ID`

---

## Documentation and Comment Conventions

- Comments must explain **why**, not restate **what** obvious code does.
- Security-sensitive code must document the relevant invariant or trust boundary.
- External API workarounds must include a short comment describing the observed behavior and the chosen compliant path.
- Reference the owning TRD section in comments or docstrings when behavior is non-obvious or contract-sensitive.
- Do not include marketing names or branding language in code comments or internal documentation.

Examples of good comment intent:
- why a GraphQL mutation is required for a lifecycle transition
- why generated content is validated but never executed
- why a message is rejected before deserialization into a richer type

---

## Summary

Every symbol name should make these things obvious:

- which process owns it
- which subsystem it belongs to
- whether it is transport, model, state, UI, security, or API logic
- whether it is draft/ready lifecycle specific
- whether it handles secrets or untrusted external input
- whether it validates, stores, transforms, polls, or mutates

If a name could fit in three subsystems, it is too vague. If a name hides a security boundary or API constraint, it is incorrect.