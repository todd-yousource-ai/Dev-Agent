# DECISIONS.md

## [Repository and subsystem placement]
**Status:** Accepted  
**Context:** The repository structure is explicitly defined across the TRDs and README. The Swift/SwiftUI macOS application shell lives in `Crafted/`, while Python backend implementation lives in `src/`. Documentation and architectural source of truth live in `forge-docs/` and `forge-standards/`. The Crafted subsystem must fit this structure so implementation, tests, CI, and documentation remain discoverable and enforceable.  
**Decision:** Place all Crafted subsystem production code in `Crafted/` and all Crafted-specific XCTest coverage in `CraftedTests/`. Treat `forge-docs/` and `forge-standards/` as authoritative inputs, and do not relocate app-shell responsibilities into `src/`.  
**Consequences:** This constrains implementation to a clear boundary: Swift/SwiftUI UI and app-shell concerns remain in `Crafted/`, Python orchestration and backend concerns remain in `src/`. Cross-cutting changes must update the appropriate docs rather than inventing parallel structure. Build and CI workflows can assume the documented layout.  
**Rejected alternatives:**  
- Putting macOS app code under `src/`: rejected because `src/` is reserved for Python backend implementation and would violate documented repository boundaries.  
- Splitting Crafted UI across multiple top-level folders: rejected because it weakens discoverability and conflicts with the declared repository layout.  
- Treating README structure as advisory only: rejected because the TRDs and standards are the source of truth and must constrain implementation.

## [Crafted shall be implemented as the macOS application shell]
**Status:** Accepted  
**Context:** TRD-1 defines Crafted as the macOS application shell. The subsystem’s role is not a general-purpose client or backend runtime; it is specifically the native shell responsible for the user-facing macOS experience.  
**Decision:** Implement Crafted as a native macOS application shell using Swift and SwiftUI, and keep its responsibilities focused on shell, navigation, onboarding, and platform UI concerns.  
**Consequences:** Crafted must not absorb backend orchestration logic that belongs in Python services. UI architecture, tests, and CI for Crafted must target macOS-native behavior. Platform-specific choices should optimize for macOS rather than cross-platform abstraction.  
**Rejected alternatives:**  
- Building Crafted as a cross-platform UI first: rejected because the documented requirement is specifically a macOS application shell.  
- Implementing the shell in Python or a web wrapper: rejected because this conflicts with the Swift/SwiftUI subsystem boundary implied by `Crafted/` and `CraftedTests/`.  
- Expanding Crafted into a full backend runtime: rejected because backend runtime concerns belong outside the app-shell subsystem.

## [Root navigation shall follow the documented onboarding decision tree]
**Status:** Accepted  
**Context:** TRD-1 section 3.2 defines a root-view decision tree where `RootView` branches on onboarding completion status. The onboarding path includes explicit states such as `.notStarted`, `.apiKeys`, and `.githubAuth`, with the completed path leaving onboarding and entering the main application experience.  
**Decision:** Implement root navigation from a single `RootView` that dispatches strictly by onboarding state: if onboarding is not complete, present `OnboardingContainerView` and its state-driven child views; otherwise present the post-onboarding application root.  
**Consequences:** Navigation state must be explicit and centralized. Onboarding screens cannot be presented ad hoc from arbitrary feature views. Root composition, deep linking, app launch behavior, and state restoration must preserve the same decision tree. Tests must verify each onboarding branch and the transition to the completed state.  
**Rejected alternatives:**  
- Using independent modal presentation for onboarding steps: rejected because it fragments the documented state machine and makes launch behavior ambiguous.  
- Allowing features to bypass onboarding based on local checks: rejected because root routing must be authoritative and deterministic.  
- Using multiple unrelated app entry points: rejected because the TRD defines a single root decision tree.

## [Onboarding shall be modeled as explicit state, not inferred UI flow]
**Status:** Accepted  
**Context:** The root-view decision tree enumerates named onboarding states. This implies onboarding is a domain state machine rather than a loose sequence of screens. Explicit state is necessary to resume progress, enforce prerequisites, and route correctly on launch.  
**Decision:** Model onboarding as a discrete state enum with at least the documented stages, and use that state as the sole source of truth for onboarding progress and routing.  
**Consequences:** Screen visibility, button actions, persistence, and launch restoration must update and read the same onboarding state model. Implementation must not infer progress from view history, partial credentials, or presentation stack alone. This also enables deterministic tests for each state transition.  
**Rejected alternatives:**  
- Inferring onboarding completion from whether fields are non-empty: rejected because it is brittle and does not encode ordered workflow.  
- Using navigation stack depth as onboarding progress: rejected because navigation structure is not durable application state.  
- Tracking onboarding with scattered booleans: rejected because enumerated state is clearer, safer, and aligned with the documented decision tree.

## [GitHub authentication shall be a first-class onboarding step]
**Status:** Accepted  
**Context:** The documented onboarding flow explicitly includes a `.githubAuth` state. GitHub integration is a core repository capability, and the app shell must expose authentication as part of the initial setup experience rather than burying it in later settings.  
**Decision:** Include GitHub authentication as a required, explicit onboarding step in the `OnboardingContainerView` flow, represented by its own state and view.  
**Consequences:** Users cannot be considered fully onboarded until the GitHub authentication step is completed or explicitly handled according to the app’s state rules. Root routing and onboarding persistence must account for GitHub authentication status. Crafted UI must present auth-specific error and retry paths within onboarding, not as an undefined later dependency.  
**Rejected alternatives:**  
- Deferring GitHub authentication until the first GitHub action: rejected because the TRD defines it as part of onboarding.  
- Treating GitHub auth as an optional settings page only: rejected because it breaks the prescribed decision tree.  
- Merging GitHub auth into a generic welcome screen without state distinction: rejected because it removes the explicit routing contract.

## [API key collection shall be a first-class onboarding step]
**Status:** Accepted  
**Context:** The onboarding decision tree explicitly includes an `.apiKeys` state. This indicates required credentials must be gathered in a structured onboarding sequence before the main application experience is available.  
**Decision:** Implement API key entry as a dedicated onboarding state and view, separate from welcome and GitHub authentication.  
**Consequences:** Credential entry must have explicit validation, persistence, and state transition behavior. The app cannot silently assume keys are available or defer collection without reflecting that in onboarding state. This keeps prerequisites visible and testable.  
**Rejected alternatives:**  
- Combining API key entry into a generic settings screen: rejected because the TRD defines it as onboarding.  
- Collecting API keys lazily when a feature fails: rejected because it creates nondeterministic startup behavior and violates the prescribed flow.  
- Folding API key entry into a monolithic single-screen wizard without state distinction: rejected because distinct onboarding states are required.

## [Crafted test coverage shall live in CraftedTests using XCTest]
**Status:** Accepted  
**Context:** The repository layout explicitly assigns `CraftedTests/` to XCTest suites. The subsystem requires a test boundary aligned with the Swift application shell rather than the Python pytest suite in `tests/`.  
**Decision:** Write Crafted subsystem tests in `CraftedTests/` using XCTest, and reserve `tests/` for Python backend coverage.  
**Consequences:** Swift UI state, onboarding routing, view models, and app-shell behavior must be covered by XCTest-based tests. CI and developers can rely on language-appropriate test boundaries. Cross-language regressions require coordinated tests rather than blurring the test directories.  
**Rejected alternatives:**  
- Putting Swift tests under `tests/`: rejected because `tests/` is the Python pytest suite by repository contract.  
- Using no dedicated Crafted test target: rejected because app-shell behavior must remain verifiable and isolated.  
- Relying only on end-to-end tests from the backend: rejected because native UI logic needs subsystem-local verification.

## [Crafted changes shall use the macOS-specific CI workflow]
**Status:** Accepted  
**Context:** The build pipeline documentation distinguishes `crafted-ci.yml` for `ubuntu-latest` from `crafted-ci-macos.yml` for Swift. Since Crafted is the Swift/SwiftUI macOS shell, its validation must run through the macOS-specific workflow rather than the generic Linux pipeline.  
**Decision:** Validate all Crafted subsystem changes through `crafted-ci-macos.yml` and keep Swift build and test responsibilities out of the Ubuntu-targeted CI workflow.  
**Consequences:** Implementation may rely on macOS and Swift toolchains available in the macOS runner. Pull requests affecting Crafted must trigger or pass the macOS workflow before merge. CI ownership remains clear between backend and app-shell concerns.  
**Rejected alternatives:**  
- Running Crafted validation only on `ubuntu-latest`: rejected because Swift/macOS shell validation requires the macOS workflow.  
- Merging Crafted checks into the generic backend pipeline: rejected because it obscures platform-specific failures and contradicts the documented CI split.  
- Skipping CI for UI-only changes: rejected because app-shell behavior is production code and must be validated.

## [Crafted shall respect stage-gated, checkpointed pipeline integration]
**Status:** Accepted  
**Context:** The README defines a staged build pipeline with checkpointed state transitions and explicit gate decisions before merge. Although Crafted is a Swift subsystem, it still participates in the same repository-wide governance model for generation, testing, CI, and approval.  
**Decision:** Integrate Crafted work with the repository’s staged pipeline, including checkpointed transitions and final operator gate before merge. Do not introduce a separate uncheckpointed path for app-shell changes.  
**Consequences:** Crafted implementation and automation must expose enough state for branch, generation, test, commit, and CI progression to be observable and recoverable. App-shell changes are subject to the same gate discipline as backend changes. Tooling around Crafted must not bypass repository controls.  
**Rejected alternatives:**  
- Allowing direct merge for UI changes without checkpoints: rejected because all state transitions are required to be checkpointed.  
- Creating a separate, lighter pipeline for Crafted: rejected because the repository-wide build and gate model applies across subsystems.  
- Treating Swift changes as manual-only exceptions: rejected because CI and gated progression are explicit repository requirements.

## [Complexity limits apply to Crafted-supporting orchestration and generated workflow code]
**Status:** Accepted  
**Context:** The build pipeline states that every stage has a maximum cyclomatic complexity of 15. While this rule is called out in pipeline documentation and critical backend files, it constrains any orchestration or generated integration code that supports Crafted within the repository.  
**Decision:** Keep Crafted-related orchestration, workflow generation, and integration code within the repository’s maximum cyclomatic complexity of 15 per stage-aligned unit, and refactor rather than embedding large conditional flows.  
**Consequences:** Implementers must prefer small, composable state handlers over monolithic launch or onboarding coordinators. Reviewers should reject complexity growth that undermines the repository standard. This especially constrains root routing and onboarding flow management code.  
**Rejected alternatives:**  
- Allowing higher complexity for UI flow code because it is “just presentation”: rejected because navigation logic is still control flow and subject to maintainability constraints.  
- Ignoring complexity limits outside the Python backend: rejected because the build-pipeline rule is repository-wide in effect.  
- Centralizing all onboarding logic in one large coordinator: rejected because it is likely to violate the complexity constraint and reduce testability.

## [Critical backend security and GitHub boundaries shall not be reimplemented inside Crafted]
**Status:** Accepted  
**Context:** The repository marks `src/github_tools.py` and `src/path_security.py` as critical files for GitHub I/O and security boundaries. Crafted interfaces with onboarding and user-facing setup, but those critical controls remain authoritative in the backend layer.  
**Decision:** Do not reimplement repository path validation, SHA protocol handling, rate limiting, or write-path security rules inside Crafted. Delegate those concerns to the established backend boundaries and keep Crafted focused on UI and state presentation.  
**Consequences:** Crafted may collect user intent and credentials, but enforcement of repository write safety and GitHub protocol correctness remains centralized. This avoids divergence between UI assumptions and backend guarantees. Any UI flow that depends on these capabilities must call through the authoritative integration path.  
**Rejected alternatives:**  
- Implementing separate GitHub request and security logic in Swift for convenience: rejected because it duplicates critical controls and risks inconsistent behavior.  
- Performing direct repository writes from Crafted without backend boundary checks: rejected because all write paths must pass through the established security boundary.  
- Mirroring backend validation logic in the UI as the source of truth: rejected because UI validation may assist UX but cannot replace authoritative enforcement.