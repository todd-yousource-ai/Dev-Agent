# DECISIONS.md

## Treat Crafted as the macOS application shell only
**Status:** Accepted  
**Context:** The repository layout separates `Crafted/` from the Python backend in `src/`. TRD-1 defines Crafted as the macOS application shell, while orchestration, consensus, pipeline execution, GitHub I/O, path security, and CI generation are explicitly centered in backend files such as `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`.  
**Decision:** Keep all build, consensus, GitHub mutation, repository write, and pipeline orchestration logic out of `Crafted/`; implement Crafted as a presentation and application-shell layer that invokes backend capabilities through defined interfaces only.  
**Consequences:** Swift code in `Crafted/` must not duplicate backend business logic, security checks, or pipeline state machines. Any feature that requires repository mutation, CI orchestration, or path validation must delegate to backend services. This constrains Crafted to UI state, user interaction, onboarding, and shell-level coordination.  
**Rejected alternatives:**  
- Embedding build pipeline logic directly in Swift was rejected because it would duplicate critical backend behavior and bypass the documented critical-file boundaries.  
- Reimplementing GitHub and path-security logic in Crafted was rejected because `src/github_tools.py` and `src/path_security.py` are defined as the security and protocol boundaries.  
- Making Crafted a peer orchestrator to the backend was rejected because repository structure and TRDs clearly assign orchestration ownership to `src/`.

## Implement the root experience from onboarding state first
**Status:** Accepted  
**Context:** TRD-1 defines a root view decision tree driven by `OnboardingState`, where incomplete onboarding routes to `OnboardingContainerView` and its step views before the main application experience is available.  
**Decision:** Drive the top-level Crafted navigation from a single onboarding-completion state, and route users through the prescribed onboarding sequence before exposing the primary application interface.  
**Consequences:** Root navigation must be state-driven, not ad hoc. Crafted must preserve a distinct onboarding flow with explicit subviews for each onboarding phase. Features intended for the main shell must assume onboarding may be incomplete and must not bypass the root gate.  
**Rejected alternatives:**  
- Presenting onboarding as optional modals over the main app was rejected because TRD-1 defines onboarding as the root decision criterion.  
- Allowing direct entry into the main interface before required setup was rejected because it weakens the prescribed user flow and risks invalid app states.  
- Using independent navigation flags per screen instead of a single root onboarding state was rejected because it fragments the source of truth for initial routing.

## Preserve the prescribed onboarding step breakdown
**Status:** Accepted  
**Context:** The root decision tree in TRD-1 explicitly names onboarding stages including `.notStarted`, `.apiKeys`, `.githubAuth`, and subsequent onboarding phases. This implies intentional decomposition of setup into dedicated screens.  
**Decision:** Implement onboarding as discrete, typed stages with dedicated views matching the documented step breakdown, rather than collapsing setup into a single generic screen.  
**Consequences:** Crafted must maintain explicit stage models and view transitions for onboarding. Validation, persistence, and UI copy may evolve, but the structure must remain step-based and auditable. This also constrains analytics, restoration, and error handling to operate per onboarding step.  
**Rejected alternatives:**  
- A single wizard screen with dynamic sections was rejected because it obscures the explicit state model required by the root view decision tree.  
- Freeform settings-based setup was rejected because it undermines deterministic onboarding completion.  
- Skipping named intermediate states in favor of a boolean “isOnboarded” flag was rejected because it cannot represent resumable progress across required setup tasks.

## Use a single root state machine for top-level view selection
**Status:** Accepted  
**Context:** TRD-1’s root decision tree describes deterministic top-level routing from `RootView` based on `OnboardingState`. The broader system also emphasizes checkpointed state transitions throughout the pipeline, reinforcing the need for explicit state modeling.  
**Decision:** Model Crafted’s top-level navigation as a single explicit state machine with a canonical source of truth for root selection.  
**Consequences:** Root view rendering, restoration, and deep-link handling must resolve through one authoritative app state. New top-level flows must integrate into the root state machine rather than introducing parallel entry points. This limits navigation drift and inconsistent startup behavior.  
**Rejected alternatives:**  
- Decentralized per-feature routing ownership was rejected because it would conflict with the prescribed root decision tree.  
- Implicit navigation derived from scattered persisted flags was rejected because it is error-prone and difficult to reason about.  
- Multiple root coordinators selected opportunistically at launch were rejected because they make startup behavior nondeterministic.

## Keep pipeline stage semantics out of Crafted UI logic
**Status:** Accepted  
**Context:** The README defines the build pipeline stages and checkpointing requirements, including per-PR states such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. Those semantics belong to the backend orchestration layer. Crafted may surface these states, but should not own their transition logic.  
**Decision:** Treat pipeline stages and checkpoints as backend-owned domain state that Crafted only displays and triggers through approved interfaces.  
**Consequences:** Crafted UI may render progress, approvals, failures, and checkpoint history, but may not infer, mutate, or synthesize pipeline transitions locally. Swift models representing pipeline progress must mirror backend state rather than inventing app-local workflow semantics.  
**Rejected alternatives:**  
- Managing pipeline progress entirely in the UI layer was rejected because state transitions are required to be checkpointed consistently across the system.  
- Letting Crafted optimistically advance stages without backend confirmation was rejected because it would desynchronize UI state from source-of-truth execution state.  
- Encoding business rules for stage advancement in Swift was rejected because orchestration ownership is assigned to backend critical files.

## Surface operator gates, but do not implement approval policy in Crafted
**Status:** Accepted  
**Context:** The README specifies that Stage 6 is a gate where the operator approves or corrects before merge, and every gate decision is recorded. This creates a requirement for UI support without transferring policy ownership to the app shell.  
**Decision:** Implement Crafted to present gate status, capture operator intent, and display recorded decisions, while keeping approval rules, merge eligibility, and audit persistence outside the Swift shell.  
**Consequences:** Crafted must provide clear review and approval affordances, but final gate outcomes must come from backend validation and persisted records. UI components cannot independently decide merge readiness. Auditability must rely on backend records, not local UI memory.  
**Rejected alternatives:**  
- Performing merge-approval logic in the macOS app was rejected because gate decisions must be recorded consistently with the rest of the pipeline state.  
- Allowing the UI to bypass backend gate validation for convenience was rejected because it breaks audit and control guarantees.  
- Treating gate review as an informal client-side step was rejected because the TRD requires explicit gated transitions.

## Respect backend security boundaries for all repository-affecting actions
**Status:** Accepted  
**Context:** `src/path_security.py` is designated as the security boundary through which every write path must pass, and `src/github_tools.py` owns GitHub I/O, including path validation, rate limiting, and SHA protocol. Crafted must not create side channels around these files.  
**Decision:** Route every Crafted action that can affect repository contents, branches, pull requests, CI, or file paths through backend security and GitHub interfaces; do not perform direct repository mutation from the app shell.  
**Consequences:** Crafted cannot directly write repository files, fake commit operations, or independently call GitHub in ways that bypass backend validation. Any local editing or preview functionality must remain non-authoritative until backend validation succeeds. This constrains integrations and plugin-style extensions within Crafted.  
**Rejected alternatives:**  
- Direct GitHub API access from Swift was rejected because it would bypass rate limiting, SHA protocol handling, and centralized validation.  
- Local file mutation by the app with later reconciliation was rejected because it violates the rule that every write path passes through the security boundary.  
- Separate Swift-side path validation was rejected because duplicated security logic is brittle and inconsistent.

## Mirror backend checkpointed state instead of inventing client-only progress
**Status:** Accepted  
**Context:** The build pipeline requires every state transition to be checkpointed, including per-PR stages. Crafted will need to show progress and recover across launches, but that must align with the persisted source of truth.  
**Decision:** Persist and restore Crafted workflow displays from backend checkpointed state, and avoid client-only workflow progress models except for ephemeral presentation state.  
**Consequences:** On relaunch, Crafted must reconstruct visible workflow state from authoritative checkpoints. Spinners, temporary selections, and local drafts may exist, but substantive progress indicators must correspond to real checkpointed transitions. This improves crash recovery and reduces ambiguity during long-running operations.  
**Rejected alternatives:**  
- Storing the primary workflow state only in local app memory was rejected because it would not survive restarts or align with required checkpoints.  
- Maintaining an independent Swift persistence layer for pipeline truth was rejected because it would create two competing authorities.  
- Reconstructing status heuristically from logs or UI events was rejected because the system already mandates explicit checkpointing.

## Keep Crafted aligned with repository standards documents
**Status:** Accepted  
**Context:** The repository layout identifies `forge-standards/` as the home of `ARCHITECTURE.md`, `INTERFACES.md`, `DECISIONS.md`, `CONVENTIONS.md`, and generated build rules. These are the normative constraints for implementation across subsystems, including Crafted.  
**Decision:** Implement Crafted features only in ways that conform to the shared standards documents, and update those standards before introducing behavior that would conflict with them.  
**Consequences:** Crafted-specific implementation shortcuts cannot override repository-wide architecture or interface contracts. Design and code review for Swift changes must include standards conformance. Features requiring new cross-subsystem contracts must be documented in shared standards first.  
**Rejected alternatives:**  
- Letting Crafted establish ad hoc conventions independent of `forge-standards/` was rejected because it would fragment the repository’s source of truth.  
- Treating standards as backend-only guidance was rejected because the repository layout applies them across the project.  
- Deferring standards alignment until after implementation was rejected because it encourages divergence and rework.

## Maintain a strict separation between Crafted production code and XCTest coverage
**Status:** Accepted  
**Context:** The repository layout separates `Crafted/` and `CraftedTests/`, and the build pipeline includes dedicated test and CI stages, including a macOS workflow for Swift. This implies clear ownership of production versus verification artifacts.  
**Decision:** Keep all production Swift and SwiftUI code in `Crafted/` and all unit/UI test code in `CraftedTests/`, with changes to app behavior accompanied by corresponding XCTest coverage where feasible.  
**Consequences:** Test helpers must not leak into production targets. Swift features should be designed for testability through injectable state and interfaces rather than test-only production hooks. CI expectations for macOS test execution become a design constraint on new UI and state-management code.  
**Rejected alternatives:**  
- Mixing test fixtures into `Crafted/` was rejected because it blurs target boundaries and complicates release artifacts.  
- Relying primarily on manual verification for Crafted was rejected because the repository’s pipeline and CI model require automated validation.  
- Deferring testability concerns until after UI implementation was rejected because it leads to tightly coupled views that are difficult to validate in CI.