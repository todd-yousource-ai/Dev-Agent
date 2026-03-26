# Code Conventions

This document defines repository-wide coding conventions derived from the provided TRD materials and agent guidance. The TRDs remain the source of truth for interfaces, behavior, security controls, and testing requirements. Conventions here standardize implementation style, naming, and patterns across all subsystems.

## File and Directory Naming

Use the existing two-process architecture consistently:

```text
src/
├─ swift/                  # Native macOS shell process
│  ├─ App/
│  ├─ UI/
│  ├─ Auth/
│  ├─ Security/
│  ├─ Keychain/
│  ├─ IPC/
│  ├─ Models/
│  ├─ ViewModels/
│  ├─ Services/
│  ├─ Utilities/
│  └─ Tests/
├─ python/                 # Backend process
│  ├─ api/
│  ├─ consensus/
│  ├─ pipeline/
│  ├─ providers/
│  ├─ github/
│  ├─ ipc/
│  ├─ security/
│  ├─ models/
│  ├─ services/
│  ├─ utils/
│  └─ tests/
└─ shared/                 # Cross-process schemas, fixtures, docs-generated artifacts
```

### General Rules

- Use lowercase directory names.
- Use singular conceptual names for modules unless the folder clearly contains a category of peer implementations:
  - Prefer `provider/` only if one implementation exists.
  - Prefer `providers/` if multiple adapters live there.
- Group by subsystem ownership, not by technical primitive alone.
- Keep cross-process contracts isolated from process-specific code.

### Swift File Naming

- Use `PascalCase.swift` matching the primary type in the file.
- One primary type per file.
- Suffix by role where meaningful:
  - `...View.swift`
  - `...ViewModel.swift`
  - `...Controller.swift`
  - `...Manager.swift`
  - `...Service.swift`
  - `...Client.swift`
  - `...Store.swift`
  - `...Error.swift`
- Extensions go in separate files only when they are substantial; name as:
  - `TypeName+Feature.swift`

Examples:
- `ConsensusStatusView.swift`
- `AuthenticatedSocketClient.swift`
- `KeychainCredentialStore.swift`
- `ProviderSessionError.swift`

### Python File Naming

- Use `snake_case.py`.
- Name files by responsibility, not by vague utility terms.
- Avoid generic filenames like `helpers.py`, `misc.py`, `common.py` unless bounded to a specific package.
- Prefer:
  - `consensus_engine.py`
  - `provider_adapter.py`
  - `pull_request_service.py`
  - `line_delimited_json.py`

### Test File Naming

#### Swift
- Mirror source structure under `Tests/`.
- Name test files `TypeNameTests.swift`.

#### Python
- Mirror package structure under `tests/`.
- Name test files `test_<module_name>.py`.

Examples:
- `test_consensus_engine.py`
- `test_github_graphql_client.py`

## Class and Function Naming

## General Naming Rules

- Use names that reflect domain behavior from the TRDs.
- Prefer explicit, subsystem-specific names over abstract names.
- Avoid product-branded identifiers in code conventions and new code unless externally required.
- Do not encode implementation details unnecessarily into public names.
- Name by responsibility, input/output meaning, or state transition.

## Swift Naming

### Types
- Use `PascalCase`.
- Nouns for models and services.
- Adjectival or participle forms only for states or wrappers when accurate.

Examples:
- `ConsensusEngine`
- `ProviderAdapter`
- `GitHubReviewService`
- `SocketAuthenticationManager`

### Properties and Functions
- Use `camelCase`.
- Boolean properties must read as predicates:
  - `isAuthenticated`
  - `hasStoredCredential`
  - `canSubmitReview`
- Functions should be verb-first:
  - `loadSession()`
  - `storeCredential()`
  - `sendHandshake()`
  - `convertDraftPullRequestToReady()`

### Protocols
- Name by capability or role.
- Prefer noun or `...Providing` / `...Managing` / `...Serving` patterns.

Examples:
- `CredentialStoring`
- `SocketAuthenticating`
- `ReviewSubmitting`

## Python Naming

### Classes
- Use `PascalCase`.

Examples:
- `ConsensusEngine`
- `ProviderAdapter`
- `GitHubGraphQLClient`
- `AuthenticatedUnixSocketServer`

### Functions and Methods
- Use `snake_case`.
- Verb-first for actions.
- Use precise names for stateful operations.

Examples:
- `build_consensus_result()`
- `validate_handshake_token()`
- `mark_pull_request_ready_for_review()`
- `parse_line_delimited_json()`

### Constants
- Use `UPPER_SNAKE_CASE`.
- Group subsystem-specific constants near their owning module.

Examples:
- `MAX_SOCKET_MESSAGE_BYTES`
- `DEFAULT_RETRY_BACKOFF_SECONDS`
- `GITHUB_GRAPHQL_TIMEOUT_SECONDS`

## Error and Exception Patterns

## General Error Rules

- Errors must follow TRD-defined contracts exactly.
- Do not invent error shapes for public interfaces.
- Include enough context for diagnosis without exposing secrets, tokens, credentials, or generated sensitive content.
- Distinguish operator-correctable, transient, validation, and security failures.

## Swift Error Conventions

- Prefer typed errors with `enum`.
- Name error types with `Error` suffix.
- Cases should describe failure conditions, not remediation.

Example:
```swift
enum SocketHandshakeError: Error {
    case missingToken
    case invalidToken
    case unsupportedProtocolVersion
    case malformedMessage
}
```

- Add contextual payloads only when safe:
```swift
enum PullRequestError: Error {
    case notFound(number: Int)
    case invalidState(currentState: String)
    case apiFailure(statusCode: Int)
}
```

- Convert low-level errors into subsystem-owned error types at boundaries.
- Do not leak raw Keychain, auth, socket, or external API errors directly across subsystem interfaces unless the TRD requires it.

## Python Exception Conventions

- Use custom exceptions per subsystem.
- Suffix exception classes with `Error`.
- Maintain a clear hierarchy when a subsystem has multiple failure modes.

Example:
```python
class GitHubError(Exception):
    pass

class PullRequestStateError(GitHubError):
    pass

class GraphQLMutationError(GitHubError):
    pass
```

- Raise validation errors early at ingress boundaries.
- Wrap third-party client failures into internal exception types before crossing module boundaries.
- Preserve root cause using exception chaining:
```python
raise GraphQLMutationError("failed to mark pull request ready") from exc
```

## Error Messages

- Make messages actionable and concise.
- Include identifiers that aid tracing:
  - pull request number
  - repository owner/name
  - protocol version
  - request id
- Never include:
  - secrets
  - tokens
  - full credential material
  - raw untrusted payloads unless redacted

## Per-Subsystem Naming Rules

## Swift Shell Subsystem

Owns UI, authentication, Keychain, native app lifecycle, and XPC/process coordination.

### UI and SwiftUI

- Views: `PascalCaseView`
- Reusable cards/panels: `PascalCaseCard`, `PascalCasePanel`
- State owners: `PascalCaseViewModel`
- UI-only models: `PascalCaseDisplayModel`

Examples:
- `SessionStatusView`
- `ReviewQueuePanel`
- `ProviderHealthCard`
- `AuthenticationViewModel`

Rules:
- Views should be named by what they render, not where they appear.
- View models should be named after the view or flow they own.
- Avoid `MainView`, `DataView`, `InfoPanel` unless scoped by subsystem meaning.

### Authentication

- Prefix auth coordination types with `Auth` only when needed to disambiguate.
- Prefer explicit names:
  - `SessionAuthenticator`
  - `LoginStateStore`
  - `TokenRefreshService`

Avoid:
- `AuthHelper`
- `LoginManager` when role is broader or narrower than login

### Keychain and Secrets

- Types must make storage semantics explicit:
  - `KeychainCredentialStore`
  - `SecretAccessPolicy`
  - `CredentialMetadata`

Rules:
- Use `Store` for persistence abstraction.
- Use `Policy` for enforcement logic.
- Use `Provider` only for read-oriented dependencies.

### IPC / XPC / Unix Socket

- Name by transport and trust role:
  - `AuthenticatedSocketClient`
  - `SocketHandshakeMessage`
  - `LineDelimitedJSONEncoder`
  - `BackendProcessSupervisor`

Rules:
- Include `Authenticated` in names where authentication is security-significant.
- Include protocol format in serializer names.

## Python Backend Subsystem

Owns consensus, generation pipeline, external service operations, and repository automation.

### Consensus

- Core engine type: `ConsensusEngine`
- Strategy implementations: `...Strategy`
- Results: `...Result`
- Inputs: `...Request`, `...Context`, `...Candidate`

Examples:
- `ConsensusRequest`
- `ConsensusCandidate`
- `WeightedSelectionStrategy`
- `ConsensusResult`

Rules:
- Use `Engine` for orchestration.
- Use `Strategy` for interchangeable decision logic.
- Use `Scorer` only for components that assign scores, not final selection.

### Provider Adapters

- Adapter types: `...ProviderAdapter`
- Client wrappers: `...Client`
- Provider-specific payload mappers: `...Translator` or `...Mapper`

Examples:
- `OpenAIProviderAdapter`
- `AnthropicProviderAdapter`
- `ProviderResponseMapper`

Rules:
- All provider integrations should present a common adapter-shaped interface.
- Keep provider brand names confined to implementation classes where necessary.
- Shared abstractions should remain provider-neutral.

### Pipeline

- Pipeline orchestrators: `...Pipeline` or `...PipelineRunner`
- Stages: `...Stage`
- Stage outputs: `...StageResult`
- Validation and gating: `...Validator`, `...Gate`

Examples:
- `GenerationPipeline`
- `PatchSynthesisStage`
- `SafetyValidationGate`
- `RepositoryContextStageResult`

Rules:
- Use `Stage` for ordered execution units.
- Use `Gate` for pass/fail enforcement steps.
- Use `Validator` for rule evaluation that may return detailed findings.

### GitHub Integration

Follow the documented API behavior lessons strictly.

#### Naming
- REST wrappers: `...RestClient`
- GraphQL wrappers: `...GraphQLClient`
- Workflow/service layers: `...Service`
- Domain operations must be named after actual platform behavior.

Examples:
- `GitHubRestClient`
- `GitHubGraphQLClient`
- `PullRequestService`
- `mark_pull_request_ready_for_review()`

#### Pull Request Lifecycle Rules
- Do not name a method as though REST can convert a draft pull request to ready when the implementation must use GraphQL.
- Prefer explicit names tied to the successful mechanism:
  - `mark_pull_request_ready_for_review`
  - not `update_pull_request_draft_state`

- If an operation is constrained by external platform behavior, encode that constraint in the implementation and tests, not in ambiguous naming.

### Repository and Code Generation Safety

- Types enforcing non-execution constraints should be explicit:
  - `GeneratedCodePolicy`
  - `ExecutionProhibitionError`
  - `RepositoryMutationGuard`

Rules:
- Any component handling generated content must be named to reflect review, validation, storage, or transport only.
- Do not use names implying execution, running, eval, or shelling unless the TRD explicitly permits it.

## Shared Contracts and Models

For cross-process contracts over authenticated Unix socket with line-delimited JSON:

- Message types: `...Message`
- Request payloads: `...Request`
- Response payloads: `...Response`
- Event payloads: `...Event`
- Handshake models: `...Handshake`, `...HandshakeResult`

Examples:
- `SocketHandshakeRequest`
- `SocketHandshakeResponse`
- `PipelineStatusEvent`

Rules:
- Keep wire-format names stable and versioned per TRD.
- Serializer/deserializer names must include transport format when applicable.
- Avoid embedding UI concerns into shared message names.

## Function Design Patterns

- Keep subsystem boundaries explicit.
- Validate inputs at entry points.
- Translate external or low-level errors at boundaries.
- Return typed results or structured models, not loosely shaped dictionaries or ad hoc tuples, unless required by the wire protocol.
- Prefer small composable functions with names that describe one state transition or one transformation.

Examples:
- `validate_request()`
- `build_handshake_response()`
- `persist_session_metadata()`
- `submit_review_comment()`

Avoid:
- `process_data()`
- `handle_everything()`
- `do_request()`

## State and Lifecycle Naming

Stateful flows should use consistent vocabulary:

- `initial`
- `pending`
- `authenticated`
- `ready`
- `failed`
- `completed`
- `cancelled`

Rules:
- Use the same state names in code, tests, and telemetry where the TRD defines them.
- Name transitions as verbs:
  - `authenticate`
  - `prepare`
  - `enqueue`
  - `complete`
  - `cancel`

## Logging and Diagnostic Naming

- Log categories should mirror subsystem names:
  - `auth`
  - `keychain`
  - `ipc`
  - `consensus`
  - `pipeline`
  - `github`
  - `security`
- Event names should be action-oriented:
  - `socket_handshake_started`
  - `pull_request_marked_ready`
  - `credential_store_failed`

Rules:
- Never log secrets or raw credentials.
- Redact tokens and sensitive payloads.
- Use stable identifiers for correlation.

## Test Naming Conventions

- Test names should describe behavior and expected outcome.
- Prefer:
  - `test_marks_draft_pull_request_ready_via_graphql`
  - `test_rejects_invalid_handshake_token`
  - `test_keychain_store_returns_missing_item_error`

- For Swift:
  - `testHandshakeFailsWhenTokenIsMissing()`
  - `testMarkReadyUsesGraphQLMutation()`

Rules:
- Name tests after the requirement they verify.
- Where external platform quirks exist, encode the behavior directly in the test name.

## Forbidden Naming Patterns

Do not introduce:

- `Helper`
- `Util` / `Utils` for broad unrelated logic
- `Manager` when a more specific role exists
- `Data` as a primary domain type name
- `Info` as a substitute for a concrete model
- `Common` or `Base` without a narrowly justified abstraction
- names that imply executing generated code when execution is prohibited
- names that hide security-critical behavior behind vague terminology

## Naming Decision Rule

When choosing a name, prefer this order:

1. TRD-defined term
2. External protocol or API term
3. Domain responsibility
4. Implementation role

If a shorter name is less precise than a longer one, choose the more precise name.