# DECISIONS.md

## Keep Crafted as the dedicated Swift/SwiftUI application shell
**Status:** Accepted

**Context:** Repository layout explicitly assigns `Crafted/` to the macOS application shell, while `src/` contains the Python backend implementation. The subsystem boundary must remain clear so platform UI concerns do not leak into backend orchestration and backend logic does not become embedded in the macOS client.

**Decision:** Implement Crafted strictly as the Swift/SwiftUI macOS application shell inside `Crafted/`, and keep backend orchestration, generation, GitHub I/O, path security, and pipeline logic in `src/`.

**Consequences:** Crafted must focus on presentation, local app state, operator interaction, and shell-level integration. It must not reimplement consensus, pipeline orchestration, GitHub write protocols, or security-critical path validation that already belong to Python services. Cross-subsystem communication must preserve this boundary.

**Rejected alternatives:** Embedding core pipeline logic directly in Swift was rejected because it duplicates critical backend behavior and weakens enforcement of shared security and orchestration rules. Moving the entire shell into Python was rejected because TRD-1 defines a macOS application shell and repository layout reserves `Crafted/` for that purpose. Mixing Swift and Python responsibilities ad hoc was rejected because it creates unclear ownership and increases maintenance risk.

## Enforce the RootView onboarding-first decision tree
**Status:** Accepted

**Context:** TRD-1 defines a root view decision tree in which onboarding state is evaluated first. Before onboarding is complete, the application must route users through the onboarding container and its ordered steps rather than exposing the main application surface.

**Decision:** Implement `RootView` so that it evaluates onboarding completion before any primary application content and routes incomplete users into `OnboardingContainerView` with step-specific child views for `.notStarted`, `.apiKeys`, `.githubAuth`, and subsequent onboarding states defined by TRD-1.

**Consequences:** Main application views cannot be shown until onboarding reaches `.complete`. Navigation logic must be state-driven rather than manually pushed from arbitrary screens. New entry points must respect onboarding gating and cannot bypass it.

**Rejected alternatives:** Allowing direct access to the main app with optional onboarding prompts was rejected because it violates the explicit root decision tree. Using independent modal onboarding screens on top of the main UI was rejected because it weakens the single-source-of-truth routing model. Allowing each feature to decide whether onboarding is complete was rejected because it creates inconsistent gating and fragmented state management.

## Model onboarding as explicit discrete states
**Status:** Accepted

**Context:** The root view decision tree enumerates onboarding progression as named states such as `.notStarted`, `.apiKeys`, `.githubAuth`, and `.complete`. The UI flow depends on deterministic progression and resumability.

**Decision:** Represent onboarding in Crafted as an explicit finite set of states and drive view rendering from that state machine rather than from loosely coupled booleans or inferred conditions.

**Consequences:** Onboarding progress becomes serializable, testable, and resumable. View transitions must be implemented as state transitions, and any new onboarding step requires extending the state model intentionally. Validation logic must map cleanly to advancement or rollback between defined states.

**Rejected alternatives:** Tracking onboarding with separate booleans like `hasAPIKey` and `isGitHubAuthed` was rejected because it permits invalid combinations and ambiguous routing. Inferring progress from persisted credentials alone was rejected because it obscures user intent and complicates recovery from partial setup. Using free-form string state identifiers was rejected because it is less safe and harder to test than a closed enum-like model.

## Keep stage and gate decisions checkpoint-driven in the Crafted UI
**Status:** Accepted

**Context:** The build pipeline requires every state transition to be checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. Gate decisions must be explicit, and operator approval occurs before merge. Crafted is the operator-facing shell and must present this flow faithfully.

**Decision:** Surface pipeline progress, gate status, and operator decisions in Crafted from explicit checkpointed states rather than from transient UI-only progress indicators.

**Consequences:** Crafted views must consume and display durable stage states. UI actions that approve, retry, or correct work must map to recorded pipeline transitions instead of ephemeral local events. The shell must be able to restore accurate progress after relaunch or reconnect.

**Rejected alternatives:** Showing only optimistic progress spinners without checkpoint backing was rejected because it hides authoritative state and breaks recovery. Deriving stage status from logs on demand was rejected because it is unreliable and harder to reason about. Allowing merge approval from an uncheckpointed local UI action was rejected because it violates the gate model.

## Do not bypass backend security and GitHub boundaries from Crafted
**Status:** Accepted

**Context:** Critical files establish that `src/github_tools.py` owns GitHub I/O including path validation, rate limiting, and SHA protocol, and `src/path_security.py` is the write-path security boundary through which every write path must pass. Crafted must not circumvent these controls.

**Decision:** Route all repository writes, GitHub mutations, and security-sensitive file operations initiated from Crafted through the backend boundary that enforces `github_tools.py` and `path_security.py` policies.

**Consequences:** Crafted cannot perform direct repository mutation logic as a parallel implementation. UI-initiated actions must use backend APIs or commands that preserve validation, SHA handling, rate limiting, and path restrictions. Any local file manipulation feature in Crafted must be reviewed against the same security boundary.

**Rejected alternatives:** Implementing direct GitHub API calls in Swift was rejected because it duplicates and potentially bypasses required validation and protocol handling. Writing files directly from the UI layer without path security checks was rejected because it violates the repository’s explicit security boundary. Splitting security logic between Swift and Python was rejected because it creates inconsistent enforcement.

## Preserve CI and test visibility for both Python and Swift concerns
**Status:** Accepted

**Context:** The repository includes both Python tests in `tests/` and Swift tests in `CraftedTests/`. The build pipeline defines CI on `ubuntu-latest` generally and a dedicated macOS workflow for Swift. Crafted must fit into this dual-runtime validation model.

**Decision:** Structure Crafted implementation and its tests so Swift-specific behavior is validated in `CraftedTests/` and remains compatible with the dedicated macOS CI workflow, while backend-dependent behavior remains covered in Python CI where appropriate.

**Consequences:** Swift UI and shell logic must be testable in XCTest. Features that span shell and backend boundaries must be partitioned so each side is validated in its native test harness. Crafted changes must not assume Ubuntu-only validation is sufficient.

**Rejected alternatives:** Relying solely on manual testing for Crafted was rejected because the repository already defines automated test suites and platform-specific CI. Moving Swift shell tests into Python was rejected because native UI behavior requires XCTest-level validation. Treating macOS CI as optional was rejected because the build pipeline explicitly reserves a Swift-specific workflow.

## Keep operator approval as a first-class UI responsibility before merge
**Status:** Accepted

**Context:** The build pipeline includes a gate where the operator approves or corrects before merge. Crafted is the application shell through which this review and approval responsibility is expected to be exercised.

**Decision:** Implement Crafted to require explicit operator approval or correction at the gate stage before any merge-completion action is exposed.

**Consequences:** The UI must distinguish generated success from merge authorization. Review surfaces must support inspect-before-approve workflows, and merge-triggering controls must remain disabled or absent until gate conditions are satisfied. Automated completion paths must stop short of merge without operator action.

**Rejected alternatives:** Auto-merging after CI passes was rejected because it skips the required operator gate. Treating approval as an optional post-merge annotation was rejected because it reverses the mandated control point. Hiding the gate in backend automation rather than surfacing it in the shell was rejected because Crafted must support operator oversight.

## Favor simple stage-oriented view composition over complex orchestration inside Crafted
**Status:** Accepted

**Context:** The broader system constrains stage complexity, with every stage capped at cyclomatic complexity 15. Although this rule is specified for pipeline stages, the same design pressure applies to Crafted so the shell remains understandable and does not absorb orchestration complexity intended for backend components.

**Decision:** Organize Crafted into small, stage-oriented views and view models that reflect distinct application states, and avoid embedding multi-stage orchestration logic directly in root or coordinator views.

**Consequences:** Root-level SwiftUI code must remain declarative and routing-focused. Complex branching, retry strategies, and failure taxonomy handling belong in backend services, with Crafted presenting their results. Feature additions should prefer composition of focused screens over a monolithic coordinator.

**Rejected alternatives:** Building a single all-knowing app coordinator with end-to-end pipeline branching was rejected because it centralizes too much complexity in the UI shell. Encoding failure-recovery strategy directly in SwiftUI views was rejected because the backend already owns pipeline behavior. Using deeply nested conditional rendering without state abstraction was rejected because it becomes difficult to test and maintain.