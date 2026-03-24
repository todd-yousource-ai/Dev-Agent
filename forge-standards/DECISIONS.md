# DECISIONS.md

## [Crafted lives as a separate Swift application shell at the repository root]
**Status:** Accepted

**Context:** The repository structure explicitly reserves `Crafted/` for the Swift/SwiftUI application shell and `CraftedTests/` for its XCTest suites, while Python backend implementation remains in `src/`. The overall system separates product documentation in `forge-docs/`, standards in `forge-standards/`, backend logic in `src/`, and the macOS UI shell in `Crafted/`.

**Decision:** Implement the Crafted subsystem as a standalone Swift/SwiftUI macOS application in the top-level `Crafted/` directory, with tests in `CraftedTests/`, and do not place Crafted UI code inside `src/` or any backend-oriented package.

**Consequences:** This constrains implementation to a clear platform boundary: Swift and SwiftUI for Crafted, Python for backend logic. Build, test, and CI paths must treat Crafted as a first-class macOS app target. Shared logic between backend and UI must cross an explicit interface boundary rather than being co-located informally. Repository changes must preserve the documented layout.

**Rejected alternatives:**  
- Embedding the macOS shell inside `src/` as Python-driven UI code was rejected because it violates the documented repository layout and weakens the language/runtime boundary.  
- Placing Crafted under a generic `app/` or `ui/` directory was rejected because the repository layout already establishes `Crafted/` as the canonical location.  
- Mixing Swift tests into the Python `tests/` directory was rejected because XCTest and pytest have distinct tooling, conventions, and CI requirements.

## [Crafted root navigation must follow onboarding-first gating]
**Status:** Accepted

**Context:** TRD-1 defines a root view decision tree in which `RootView` routes to onboarding until `OnboardingState == .complete`, with staged onboarding states including `.notStarted`, `.apiKeys`, `.githubAuth`, and additional onboarding steps before the main application experience becomes available.

**Decision:** Implement `RootView` as a state-driven gate that routes to `OnboardingContainerView` for every onboarding state except `.complete`, and only present the main post-onboarding application once onboarding is complete.

**Consequences:** Crafted cannot expose the primary application workspace before onboarding completion. Navigation logic must be centralized around explicit onboarding state, not scattered across independent screens. Deep links, app restoration, and startup flows must respect onboarding gating. Tests must cover each onboarding branch and the complete-state transition.

**Rejected alternatives:**  
- Allowing users to bypass onboarding and enter the main app with partial setup was rejected because it contradicts the documented root view decision tree.  
- Using ad hoc conditional presentation in multiple views instead of a single root routing decision was rejected because it increases inconsistency and makes state restoration harder to reason about.  
- Deferring onboarding checks to individual feature screens was rejected because it permits invalid partial navigation states.

## [Onboarding is modeled as explicit discrete states]
**Status:** Accepted

**Context:** The documented root decision tree names onboarding stages explicitly, including `.notStarted`, `.apiKeys`, `.githubAuth`, and subsequent steps. This indicates that onboarding is not a generic boolean but a structured progression.

**Decision:** Represent Crafted onboarding as an explicit finite state model with named states matching the documented flow, rather than as a single completion flag or loosely coupled per-screen booleans.

**Consequences:** View rendering, persistence, restoration, and test cases must be keyed to explicit onboarding states. State transitions must be intentional and auditable. Adding or changing onboarding steps requires extending the state model rather than introducing hidden conditional flags. Persistence must preserve enough information to resume onboarding accurately.

**Rejected alternatives:**  
- A single `hasCompletedOnboarding` boolean was rejected because it cannot represent partial progress or determine which screen to show next.  
- Independent booleans such as `hasAPIKeys` and `hasGitHubAuth` were rejected because they permit contradictory combinations and make routing logic brittle.  
- Inferring onboarding progress from missing stored values alone was rejected because it couples navigation to storage internals and obscures legal transitions.

## [Crafted must support GitHub authentication as a first-class onboarding step]
**Status:** Accepted

**Context:** The onboarding decision tree explicitly includes a `.githubAuth` step. The broader repository also identifies GitHub integration as a core system concern, with all GitHub I/O centralized in backend tooling.

**Decision:** Implement GitHub authentication as an explicit, user-visible onboarding stage in Crafted and do not treat GitHub connection as an optional background enhancement during initial setup.

**Consequences:** The UI must provide a dedicated GitHub authentication flow, validation states, and failure handling during onboarding. Main application features that depend on repository access must assume GitHub auth has been established by the time onboarding is complete. Interface contracts between Crafted and backend GitHub capabilities must be explicit and testable.

**Rejected alternatives:**  
- Deferring GitHub authentication until a later feature interaction was rejected because the onboarding flow explicitly requires a `.githubAuth` stage.  
- Making GitHub auth optional during onboarding was rejected because it undermines repository-centric workflows and complicates downstream assumptions.  
- Hiding GitHub auth entirely inside backend processes was rejected because authentication requires user-facing consent and status feedback.

## [Crafted must collect API keys during onboarding rather than at point of use]
**Status:** Accepted

**Context:** The onboarding decision tree explicitly includes an `.apiKeys` stage before onboarding completion. This indicates that required credentials are part of initial setup, not an incidental per-feature prompt.

**Decision:** Implement API key entry and validation as an onboarding step and require completion of that step before the user reaches the main application shell.

**Consequences:** Credential capture UX, validation messaging, and secure persistence behavior must be available early in app lifecycle. Features in the main app may assume required API credentials exist or that onboarding blocks access until they do. State transitions from `.apiKeys` must not occur on incomplete or invalid credential entry.

**Rejected alternatives:**  
- Prompting for API keys only when a feature first needs them was rejected because it conflicts with the explicit onboarding flow and produces fragmented setup experiences.  
- Allowing onboarding completion with missing API keys was rejected because it weakens readiness guarantees for the main application.  
- Storing placeholder or unvalidated keys to advance onboarding was rejected because it creates false completion states.

## [Crafted testing must use XCTest in a dedicated test target]
**Status:** Accepted

**Context:** The repository layout defines `CraftedTests/` as the location for XCTest suites, distinct from Python `tests/`. The build pipeline also distinguishes Swift-related CI by requiring `crafted-ci-macos.yml` for Swift.

**Decision:** Write Crafted subsystem tests as XCTest cases in `CraftedTests/` and integrate them with the macOS-specific CI workflow, not the Python pytest suite.

**Consequences:** Swift UI and application logic must be structured to be testable through XCTest-friendly seams. CI changes for Crafted must be validated in the macOS workflow. Test ownership and failures remain platform-appropriate and easier to diagnose. Cross-language integration tests, if needed, must be explicitly designed rather than improvised inside pytest.

**Rejected alternatives:**  
- Testing Crafted behavior through Python-based end-to-end scripts only was rejected because it does not align with the repository’s test layout and weakens native macOS verification.  
- Co-locating Swift tests with application sources inside `Crafted/` was rejected because the repository already defines a separate `CraftedTests/` target.  
- Relying primarily on manual QA for Crafted UI behavior was rejected because the documented layout and CI strategy require automated test coverage.

## [Crafted changes must run on the macOS-specific CI workflow]
**Status:** Accepted

**Context:** The build pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. Since Crafted is the Swift application shell, its validation must occur in the macOS workflow.

**Decision:** Validate all Crafted subsystem build and test changes through `crafted-ci-macos.yml`, and do not rely on the Linux-oriented pipeline as the authoritative CI signal for Swift/macOS behavior.

**Consequences:** Every implementation choice in Crafted must remain compatible with macOS CI execution. Build scripts, dependencies, signing assumptions, and test setup must be automatable on a macOS runner. Merge readiness for Crafted changes depends on passing the macOS workflow. Backend-only CI success is insufficient evidence for Crafted correctness.

**Rejected alternatives:**  
- Running Crafted validation only in the default Ubuntu CI was rejected because Swift/macOS application behavior requires a macOS environment.  
- Skipping CI for UI-only changes was rejected because the documented pipeline establishes explicit CI stages and platform-specific workflows.  
- Using ad hoc local verification as the primary gate was rejected because it is not reproducible and conflicts with the required CI structure.

## [Crafted implementation must preserve stage and state observability expected by the build system]
**Status:** Accepted

**Context:** The build pipeline checkpoints every state transition and treats stage progression as a first-class concept. Although this requirement is defined for the wider system, Crafted is a visible subsystem in the same repository and must not introduce opaque navigation or mutation that undermines traceability.

**Decision:** Model Crafted user flow and significant setup transitions with explicit state changes that can be observed, tested, and persisted, rather than with hidden side effects or transient-only navigation logic.

**Consequences:** Navigation and onboarding code must favor explicit state machines, bindings, and durable transition points. Tests must assert transitions, not just final screenshots. Persistence and restoration logic must map cleanly onto those states. Future integration with logging, analytics, or orchestration will be easier because state changes are well defined.

**Rejected alternatives:**  
- Driving the app entirely through local ephemeral view state was rejected because it makes transitions hard to restore, audit, and test.  
- Encoding progress indirectly through arbitrary combinations of storage keys and view appearance hooks was rejected because it obscures lifecycle semantics.  
- Using implicit navigation side effects as the primary flow mechanism was rejected because it produces brittle behavior under relaunch and state restoration.