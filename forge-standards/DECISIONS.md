# DECISIONS.md

## [Use the documented repository layout as a hard boundary]
**Status:** Accepted

**Context:** The TRDs and README define a fixed repository structure with `forge-docs/` as the source of truth for requirements, `forge-standards/` for architecture and conventions, `src/` for the Python backend, `Crafted/` for the Swift/SwiftUI application shell, `CraftedTests/` for XCTest suites, and `tests/` for Python tests. The Crafted subsystem must fit into this structure without creating ambiguity about ownership or execution boundaries.

**Decision:** Implement all macOS application shell code for the Crafted subsystem under `Crafted/`, place Swift tests under `CraftedTests/`, and treat `forge-docs/` and `forge-standards/` as authoritative inputs rather than implementation targets.

**Consequences:**  
- Crafted implementation work must not relocate app-shell code into `src/` or other directories.  
- SwiftUI views, app state, onboarding flow, and macOS-specific code belong in `Crafted/`.  
- XCTest coverage for Crafted belongs in `CraftedTests/`.  
- Requirements must be read from the TRDs before implementation changes are made.  
- Generated or support files must not undermine the documented layout.

**Rejected alternatives:**  
- Putting Crafted logic in `src/`: rejected because `src/` is explicitly the Python backend implementation area.  
- Creating a new parallel app directory: rejected because it fragments the documented structure and weakens discoverability.  
- Treating README guidance as advisory only: rejected because repository layout is specified as a source-of-truth constraint.

## [Treat forge-docs TRDs as implementation-governing source of truth]
**Status:** Accepted

**Context:** The repository guidance explicitly states that all TRDs and PRDs live in `forge-docs/` and must be read before building. For Crafted, TRD-1 is the governing subsystem design input for the macOS application shell.

**Decision:** Read and align Crafted implementation decisions to the applicable TRDs in `forge-docs/`, with TRD-1 taking precedence for the macOS application shell.

**Consequences:**  
- Crafted changes must be traceable to documented requirements.  
- Implementation must not introduce UI flow or structural behavior that contradicts TRD-1.  
- Missing details may be elaborated in code, but not in conflict with the TRDs.  
- Local convenience or inferred patterns cannot override documented design requirements.

**Rejected alternatives:**  
- Using existing code as the primary source of truth: rejected because the docs explicitly define requirements precedence.  
- Defining Crafted behavior solely through ad hoc implementation decisions: rejected because it causes drift from the authored subsystem design.  
- Treating all TRDs as equal for Crafted-specific behavior: rejected because subsystem-local decisions should follow the most directly applicable TRD first.

## [Implement the root navigation exactly from the onboarding decision tree]
**Status:** Accepted

**Context:** TRD-1 defines a root view decision tree in which `RootView` branches on `OnboardingState != .complete` to present `OnboardingContainerView`, with state-specific onboarding screens including `.notStarted → WelcomeView`, `.apiKeys → APIKeysView`, and `.githubAuth → GitHubAuthView`. This establishes the top-level navigation contract for Crafted.

**Decision:** Make `RootView` the single top-level switch for onboarding progression and route incomplete onboarding states through `OnboardingContainerView` according to the documented state-to-view mapping.

**Consequences:**  
- Top-level presentation logic must be state-driven rather than scattered across independent views.  
- Onboarding views must be selected by explicit onboarding state, not by implicit side effects or local view conditions.  
- Additional app content must remain inaccessible until onboarding reaches `.complete`, unless a TRD explicitly allows an exception.  
- Refactors must preserve the documented root decision tree semantics.

**Rejected alternatives:**  
- Using multiple unrelated entry points instead of a single `RootView`: rejected because it breaks the explicit decision tree.  
- Allowing child views to decide whether onboarding is complete: rejected because onboarding gating belongs at the root.  
- Presenting main app content and onboarding in parallel: rejected because the TRD defines onboarding as the controlling branch before completion.

## [Model onboarding as an explicit finite state machine]
**Status:** Accepted

**Context:** The documented root decision tree enumerates onboarding states and their mapped screens. This implies an explicit, enumerable state progression rather than free-form navigation.

**Decision:** Represent onboarding progression with a closed, explicit state model that includes at least the documented states and use that model as the sole authority for onboarding routing.

**Consequences:**  
- Onboarding logic must be testable as state transitions.  
- View presentation becomes deterministic and easier to reason about.  
- New onboarding steps require an intentional extension of the state model.  
- Persistence, restoration, and analytics can be tied to stable state values.

**Rejected alternatives:**  
- Tracking onboarding with multiple independent booleans: rejected because it allows invalid combinations and ambiguous routing.  
- Inferring onboarding stage from stored credentials alone: rejected because it couples UI flow to external side effects and obscures progression.  
- Using purely imperative navigation pushes without a state model: rejected because it is harder to validate against the TRD decision tree.

## [Gate all primary app content on onboarding completion]
**Status:** Accepted

**Context:** The TRD root view decision tree states that `OnboardingState != .complete` routes to onboarding. This means onboarding completion is the explicit prerequisite for the normal application shell experience.

**Decision:** Prevent access to the main Crafted application experience until onboarding state is `.complete`.

**Consequences:**  
- Main workspace, operational views, and authenticated functionality must not become the default initial experience before onboarding is complete.  
- Deep links or restored state must still respect onboarding gating.  
- Error recovery and retries during onboarding must remain within the onboarding container rather than bypassing it.

**Rejected alternatives:**  
- Allowing partial access before onboarding is complete: rejected because it violates the documented root branch condition.  
- Making onboarding skippable by default: rejected because the TRD models onboarding as required progression.  
- Deferring gating to individual feature views: rejected because gating is specified at the root level.

## [Keep GitHub authentication as a distinct onboarding step]
**Status:** Accepted

**Context:** TRD-1 explicitly includes `.githubAuth → GitHubAuthView` in the onboarding state mapping. The repository also identifies GitHub integration as a distinct subsystem concern in its own TRD, reinforcing that GitHub auth is not incidental.

**Decision:** Implement GitHub authentication as a separate, explicit onboarding step and present it through `GitHubAuthView` when the onboarding state is `.githubAuth`.

**Consequences:**  
- GitHub auth cannot be silently folded into welcome, API key entry, or background setup.  
- Failure and retry behavior for GitHub auth must remain legible to the user within onboarding.  
- Auth state transitions must update onboarding progression explicitly.  
- UI contracts should preserve a dedicated place for GitHub authorization messaging and error handling.

**Rejected alternatives:**  
- Combining GitHub auth with API key entry in one screen: rejected because the TRD assigns a distinct state and view.  
- Deferring GitHub auth until after the main app loads: rejected because the decision tree places it in onboarding.  
- Performing GitHub auth invisibly in the background: rejected because onboarding requires explicit state-driven user flow.

## [Keep API key entry as a distinct onboarding step]
**Status:** Accepted

**Context:** TRD-1 explicitly maps `.apiKeys → APIKeysView`. This indicates API key collection is a first-class onboarding milestone rather than an optional settings action.

**Decision:** Implement API key collection as a dedicated onboarding step and route it through `APIKeysView` when onboarding state is `.apiKeys`.

**Consequences:**  
- Credential entry must not be hidden in a generic settings panel during initial setup.  
- Validation, save, and retry flows for API keys must be handled within onboarding.  
- The system must not mark onboarding complete until required API key conditions are satisfied.

**Rejected alternatives:**  
- Folding API key entry into a generic welcome screen: rejected because the TRD defines a separate state and view.  
- Making API keys optional during onboarding: rejected because their placement in the decision tree indicates required progression.  
- Deferring API key entry until feature use: rejected because the root flow requires it as onboarding state.

## [Preserve a dedicated onboarding container rather than ad hoc screen swapping]
**Status:** Accepted

**Context:** The root decision tree specifies `OnboardingContainerView` as the parent route for incomplete onboarding. That indicates shared onboarding orchestration, layout, and transition ownership should live in a container abstraction.

**Decision:** Centralize onboarding screen presentation, shared chrome, and flow coordination inside `OnboardingContainerView`.

**Consequences:**  
- Shared onboarding concerns such as progress indication, error banners, layout consistency, and navigation controls should be implemented once in the container or its supporting model.  
- Individual onboarding step views should remain focused on step-specific inputs and actions.  
- Flow coordination logic must not be duplicated across onboarding screens.

**Rejected alternatives:**  
- Routing directly from `RootView` to each onboarding step view with no container: rejected because it discards the explicit TRD container layer.  
- Letting each onboarding step manage transitions to the next step independently: rejected because it fragments navigation logic and weakens consistency.  
- Embedding onboarding in modal sheets over the main app: rejected because the TRD defines onboarding as the primary root branch.

## [Maintain strict separation between Crafted UI shell and Python backend orchestration]
**Status:** Accepted

**Context:** The repository layout assigns the macOS application shell to `Crafted/` and the backend implementation to `src/`. Critical backend files such as `src/consensus.py`, `src/build_director.py`, and `src/github_tools.py` are called out as high-impact files with security and orchestration responsibilities.

**Decision:** Keep Crafted focused on app-shell presentation, state, and platform-specific user interaction, and interact with backend orchestration through defined boundaries rather than re-implementing backend pipeline logic in Swift.

**Consequences:**  
- Crafted should not duplicate consensus, build pipeline, GitHub I/O, or path security logic in the app shell.  
- Backend behavior changes remain localized to backend modules.  
- The macOS client can evolve independently in presentation without taking ownership of backend orchestration rules.  
- Interfaces between Crafted and backend components must be explicit and stable.

**Rejected alternatives:**  
- Re-implementing pipeline orchestration in Swift for UI convenience: rejected because it duplicates critical backend logic and increases divergence risk.  
- Allowing the UI layer to write directly around backend security boundaries: rejected because critical files define the security and GitHub I/O boundary in `src/`.  
- Mixing backend and app-shell code within one subsystem directory: rejected because it conflicts with the documented repository layout and responsibility split.

## [Respect backend security and GitHub boundaries from the Crafted subsystem]
**Status:** Accepted

**Context:** The repository identifies `src/github_tools.py` as the sole GitHub I/O layer, `src/path_security.py` as the write-path security boundary, and notes SHA protocol, path validation, and rate limiting as critical concerns. Even if Crafted initiates actions, it must not bypass these guarantees.

**Decision:** Route any Crafted-initiated GitHub or file-write operations through the backend’s established security and GitHub integration boundaries.

**Consequences:**  
- Crafted must not directly implement independent file-write paths that bypass path validation.  
- Crafted must not create alternate GitHub mutation paths that ignore rate limiting, SHA handling, or validation rules.  
- UI affordances for repository operations must be designed around backend-mediated execution and error reporting.

**Rejected alternatives:**  
- Performing direct GitHub API mutations from the app shell: rejected because it bypasses the documented GitHub I/O boundary.  
- Writing files directly from Crafted into managed repository areas: rejected because it weakens the documented path security boundary.  
- Creating a second security implementation in Swift: rejected because duplicate enforcement is harder to verify and maintain consistently.

## [Do not violate pipeline checkpointing and gate semantics from the UI]
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage is checkpointed, per-PR states are tracked (`branch_opened → code_generated → tests_passed → committed → ci_passed`), and operator approval gates decisions before merge. Crafted may expose these workflows, but must not flatten or bypass them.

**Decision:** Reflect pipeline state as checkpointed, ordered stages in Crafted UI and do not provide UI actions that skip mandatory gates or reorder required state transitions.

**Consequences:**  
- Crafted status displays should align with actual pipeline checkpoints rather than free-form labels.  
- Merge or approval-related UI actions must respect operator-gated semantics.  
- The app shell must not imply success or completion before backend checkpoints confirm it.  
- Resumption and restoration behavior should map onto persisted checkpoint states where available.

**Rejected alternatives:**  
- Presenting an oversimplified single “done/running” state model: rejected because it hides required checkpoint and gate semantics.  
- Letting users trigger merge-equivalent actions before operator approval: rejected because the documented gate requires approval before merge.  
- Allowing UI-driven stage skipping for convenience: rejected because ordered checkpointed transitions are a core pipeline requirement.

## [Reflect CI platform distinction in Crafted workflow presentation]
**Status:** Accepted

**Context:** The README specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. This creates an explicit distinction between general CI and Swift/macOS-specific validation relevant to the Crafted subsystem.

**Decision:** Model and present Crafted-related CI status with awareness that Swift/macOS validation is distinct from generic CI execution.

**Consequences:**  
- Crafted UI and status interpretation must not collapse all CI into a single undifferentiated result when platform-specific status matters.  
- Swift/macOS failures should be attributable as such in user-facing workflow state where CI is shown.  
- Crafted implementation should remain compatible with the dedicated macOS CI path.

**Rejected alternatives:**  
- Treating all CI as one generic workflow: rejected because the documented pipeline distinguishes Swift/macOS CI explicitly.  
- Assuming ubuntu-only validation is sufficient for Crafted changes: rejected because Swift code requires dedicated macOS CI.  
- Hiding platform-specific CI from users entirely: rejected because it obscures the validation path for the Crafted subsystem.

## [Preserve test ownership by language and subsystem]
**Status:** Accepted

**Context:** The repository layout explicitly separates `CraftedTests/` for XCTest suites and `tests/` for Python pytest coverage. This division aligns with subsystem and runtime boundaries.

**Decision:** Place Crafted subsystem automated tests in `CraftedTests/` using XCTest, and do not move Swift validation into the Python test suite.

**Consequences:**  
- SwiftUI view logic, onboarding state behavior, and app-shell regressions should be covered by XCTest in `CraftedTests/`.  
- Python tests remain responsible for backend behavior.  
- Cross-boundary behavior should be tested at the appropriate layer instead of collapsing all tests into one framework.

**Rejected alternatives:**  
- Using only end-to-end Python tests for Crafted behavior: rejected because Swift app-shell behavior belongs in Swift-native tests.  
- Placing Swift tests under `tests/`: rejected because it conflicts with the documented layout and language boundary.  
- Relying only on manual UI verification: rejected because the subsystem requires durable automated coverage.