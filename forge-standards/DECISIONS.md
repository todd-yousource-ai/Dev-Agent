# DECISIONS.md

## [Use the documented repository layout as a hard subsystem boundary]
**Status:** Accepted

**Context:** The Crafted subsystem exists within a repository whose structure is explicitly defined in the TRDs and README. `forge-docs/` is the source of truth for requirements, `forge-standards/` contains governing standards and decisions, `src/` contains the Python backend, and `Crafted/` contains the Swift/SwiftUI macOS application shell with `CraftedTests/` for XCTest coverage. The subsystem must fit this structure so implementation remains discoverable, reviewable, and aligned with the rest of the platform.

**Decision:** Implement the Crafted subsystem exclusively under `Crafted/` for production Swift/SwiftUI code and `CraftedTests/` for XCTest coverage. Treat `forge-docs/` as read-only requirements input and `forge-standards/` as governing constraints. Do not place Crafted application logic in `src/`, and do not relocate or duplicate TRD-derived requirements into ad hoc locations.

**Consequences:** Crafted implementation must be organized as a macOS app shell, not as backend Python code. Tests for Crafted behavior must live in `CraftedTests/`. Any cross-subsystem integration must respect the repository’s existing division between Swift UI shell and Python backend/runtime. Build and review workflows can assume stable locations for source, tests, and governing documentation.

**Rejected alternatives:**  
- Storing Crafted implementation in `src/` to colocate all logic was rejected because `src/` is explicitly reserved for Python backend implementation.  
- Creating a parallel undocumented app directory was rejected because it would violate the declared repository layout and reduce discoverability.  
- Copying TRD requirements into local subsystem docs was rejected because `forge-docs/` is the source of truth and duplication would create drift.

## [Make TRDs and standards authoritative before implementation changes]
**Status:** Accepted

**Context:** The repository guidance explicitly states that all TRDs and PRDs live in `forge-docs/` and must be read before building. It also identifies critical files and standards documents that must be understood before modification. Crafted design and implementation must therefore be constrained by those documents rather than by local convention or inferred behavior.

**Decision:** Read and follow applicable TRDs in `forge-docs/` and standards in `forge-standards/` before implementing or modifying the Crafted subsystem. Treat those documents as authoritative over informal code patterns or convenience-driven local changes.

**Consequences:** Crafted changes must be traceable back to documented requirements. Design deviations require an explicit new decision rather than silent implementation drift. Review of Crafted changes should verify alignment with TRDs, standards, and repository-wide constraints.

**Rejected alternatives:**  
- Letting implementation details emerge solely from current code structure was rejected because the repository explicitly defines documentation-first development.  
- Treating standards as advisory rather than binding was rejected because the repository identifies them as governing files.  
- Using undocumented subsystem-specific conventions as primary guidance was rejected because they would conflict with the source-of-truth model.

## [Implement Crafted as a SwiftUI macOS application shell]
**Status:** Accepted

**Context:** The repository layout states that `Crafted/` is the Swift/SwiftUI application shell, and TRD-1 defines the macOS Application Shell. This establishes that Crafted is not a generic client and not a web frontend; it is specifically the native macOS shell for the system.

**Decision:** Build Crafted as a native macOS application using Swift and SwiftUI. Keep UI composition, app lifecycle handling, and shell navigation inside the SwiftUI app layer appropriate for a macOS application shell.

**Consequences:** Crafted implementation must use native macOS app patterns and SwiftUI view composition. UI state, navigation, and shell responsibilities belong in the app shell rather than in backend Python services. Any feature requiring backend execution must integrate across the subsystem boundary rather than be reimplemented in the shell using the wrong technology stack.

**Rejected alternatives:**  
- Building Crafted as a web-based frontend was rejected because the TRD defines a macOS application shell.  
- Using Python UI frameworks was rejected because the repository allocates Crafted to Swift/SwiftUI.  
- Treating Crafted as a cross-platform abstraction first was rejected because the documented scope is the macOS shell.

## [Use the RootView decision tree as the top-level navigation contract]
**Status:** Accepted

**Context:** TRD-1 section 3.2 defines a RootView decision tree. It specifies that when `OnboardingState != .complete`, the app must show `OnboardingContainerView`, with specific onboarding branches including `.notStarted → WelcomeView`, `.apiKeys → APIKeysView`, and `.githubAuth → GitHubAuthView`. This is an explicit product and architectural flow, not an implementation suggestion.

**Decision:** Implement `RootView` as the single top-level routing decision point and enforce the documented onboarding-first navigation tree. When onboarding is incomplete, render `OnboardingContainerView` and route to the state-specific child view defined by the TRD. Do not bypass this flow with alternate startup routing.

**Consequences:** App launch behavior is constrained by onboarding state. Initial navigation logic must be centralized and deterministic. Additional views or application areas may only become active after the root decision tree has allowed them. State modeling must support at least the documented onboarding phases and their corresponding views.

**Rejected alternatives:**  
- Presenting the main application UI first and overlaying onboarding later was rejected because the TRD defines onboarding as the primary branch when state is incomplete.  
- Allowing each feature area to independently check onboarding and redirect was rejected because it would fragment the root decision logic.  
- Using ad hoc string-based route switching was rejected because the TRD already defines an explicit state-driven tree.

## [Model onboarding as explicit application state, not implicit UI conditions]
**Status:** Accepted

**Context:** The documented RootView decision tree is driven by `OnboardingState`, with named values such as `.notStarted`, `.apiKeys`, `.githubAuth`, and `.complete`. This requires onboarding to be represented as an explicit domain state rather than inferred from scattered booleans or view-local conditions.

**Decision:** Define onboarding progression as a strongly typed application state with explicit cases that correspond to the documented flow. Use that state to drive view selection and progression through onboarding.

**Consequences:** Crafted must maintain a coherent source of truth for onboarding status. Views should not independently infer onboarding completion from unrelated persistence or partial credentials. Testing can validate state transitions directly. Future onboarding steps must be added as explicit state cases rather than hidden conditional logic.

**Rejected alternatives:**  
- Using multiple independent booleans like `hasSeenWelcome`, `hasAPIKey`, and `hasGitHubAuth` was rejected because it creates invalid intermediate combinations and weakens routing determinism.  
- Inferring onboarding from persistence existence checks alone was rejected because it hides the state machine and complicates testing.  
- Encoding onboarding stage as loosely typed strings or integers was rejected because the TRD expresses a finite, meaningful state set.

## [Keep stage and state transitions checkpointable and auditable where Crafted participates]
**Status:** Accepted

**Context:** The build pipeline documentation states that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`, and that every gate decision is recorded. Although Crafted is the macOS shell rather than the backend orchestrator, any UI that initiates, displays, or depends on these transitions must preserve this auditable state model rather than inventing a parallel, lossy representation.

**Decision:** Represent backend workflow progress in Crafted using explicit named states that align with the documented checkpoint model. When Crafted displays or reacts to pipeline progress, it must use the canonical stage names and preserve ordering semantics rather than flattening them into vague statuses.

**Consequences:** Crafted UI and state models must be compatible with checkpointed backend progress. Progress displays, operator gates, and approval surfaces cannot treat the workflow as a simple percentage or binary success/failure. Integration code must expect auditable, discrete transitions and recorded gate outcomes.

**Rejected alternatives:**  
- Reducing workflow state to generic labels like “working”, “done”, and “failed” was rejected because it discards required checkpoint granularity.  
- Letting the UI maintain its own independent progress model was rejected because it would diverge from the canonical stage sequence.  
- Treating gate decisions as ephemeral UI events rather than recorded state was rejected because the documentation requires auditable gate decisions.

## [Respect the CI split between general backend validation and macOS-specific validation]
**Status:** Accepted

**Context:** The README specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. This means repository CI already distinguishes between general pipeline validation and macOS/Swift-specific execution. Crafted must be implemented with that split in mind.

**Decision:** Assume that Crafted Swift/SwiftUI validation belongs in the macOS-specific CI workflow and keep subsystem build/test expectations compatible with `crafted-ci-macos.yml`. Do not couple the Crafted subsystem to Linux-only assumptions or backend-only CI paths.

**Consequences:** Crafted code and tests must be buildable and testable in the macOS CI context. Swift-specific validation should not be hidden behind backend tests in `tests/`. Changes that affect Crafted must consider the macOS workflow as the authoritative CI path for the subsystem.

**Rejected alternatives:**  
- Relying solely on `ubuntu-latest` CI for Crafted validation was rejected because Swift/macOS shell testing is explicitly separated into `crafted-ci-macos.yml`.  
- Embedding Crafted verification entirely inside Python test suites was rejected because it would not validate the native shell correctly.  
- Treating local-only Xcode builds as sufficient was rejected because CI workflows are part of the documented pipeline contract.

## [Preserve complexity discipline in Crafted orchestration code]
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15. While this requirement is called out in the pipeline context, it expresses a repository-wide design discipline against overly complex orchestration logic. Crafted, as an application shell with routing and state transitions, is especially susceptible to bloated view models and coordinator logic.

**Decision:** Keep Crafted orchestration units—particularly root routing, onboarding flow coordination, and integration state handlers—at or below a cyclomatic complexity of 15. Refactor branching logic into smaller typed units before exceeding that threshold.

**Consequences:** Large monolithic `RootView`, coordinator, or view model logic is disallowed. State transitions must be decomposed into testable units. The subsystem should prefer explicit state modeling and small composable decision functions over nested conditional chains.

**Rejected alternatives:**  
- Allowing higher complexity in UI code because “views are different” was rejected because the documented discipline exists to prevent fragile orchestration everywhere.  
- Centralizing all navigation and integration logic into one large coordinator was rejected because it would likely violate the complexity cap and reduce testability.  
- Deferring complexity control until after feature completion was rejected because retrospective simplification is unreliable and expensive.

## [Do not duplicate backend security-critical behavior inside Crafted]
**Status:** Accepted

**Context:** The repository identifies backend critical files such as `src/path_security.py`, `src/github_tools.py`, `src/consensus.py`, and `src/build_director.py`, each with explicit security and orchestration responsibilities. Crafted is a shell, not the authority for path validation, GitHub write safety, rate limiting, SHA protocol handling, or core generation orchestration.

**Decision:** Keep security-critical repository operations, GitHub I/O, path validation, and generation orchestration in the backend/runtime boundary. Crafted may initiate or display those operations, but it must not reimplement their authoritative logic in Swift.

**Consequences:** Crafted integration layers must call or consume backend/runtime capabilities rather than reproducing them. The shell should treat security-sensitive decisions as backend-owned. This reduces divergence and ensures that the documented critical files remain the single enforcement points for their respective concerns.

**Rejected alternatives:**  
- Reimplementing path validation in Swift for convenience was rejected because `src/path_security.py` is the documented security boundary.  
- Performing direct GitHub mutation logic from Crafted was rejected because `src/github_tools.py` is the documented authority for GitHub I/O and safety protocols.  
- Moving orchestration logic into the UI shell was rejected because `src/consensus.py` and `src/build_director.py` are the core generation and pipeline authorities.

## [Keep Crafted tests in XCTest and align them to explicit state and routing behavior]
**Status:** Accepted

**Context:** The repository layout reserves `CraftedTests/` for XCTest suites. The Crafted subsystem’s most important documented constraints are state-driven: root routing, onboarding progression, and macOS shell behavior. Those constraints are best validated where the subsystem lives, using native test tooling.

**Decision:** Write Crafted subsystem tests in `CraftedTests/` using XCTest, focusing on root routing, onboarding state transitions, and shell-level behavior derived from the documented decision tree and state model.

**Consequences:** Validation of Crafted behavior remains close to implementation and native runtime expectations. Tests should assert explicit state-to-view or state-to-navigation outcomes rather than relying on indirect backend tests. Subsystem changes are expected to include XCTest updates when routing or state semantics change.

**Rejected alternatives:**  
- Testing Crafted behavior primarily through Python integration tests was rejected because the subsystem is a native SwiftUI shell.  
- Relying only on manual UI verification was rejected because the routing model is explicit and testable.  
- Concentrating tests only on snapshots without state transition assertions was rejected because the documented constraints are behavioral, not just visual.