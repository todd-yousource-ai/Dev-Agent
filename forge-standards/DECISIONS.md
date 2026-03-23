# DECISIONS.md

## [Use the documented repository layout as a hard architectural boundary]
**Status:** Accepted

**Context:** The TRDs define a repository structure with clear ownership boundaries: `forge-docs/` contains source-of-truth TRDs and PRDs, `forge-standards/` contains architectural constraints and conventions, `src/` contains the Python backend, `Crafted/` contains the Swift/SwiftUI application shell, `CraftedTests/` contains XCTest suites, and `tests/` contains the Python pytest suite. The Crafted subsystem must fit into this layout without eroding cross-subsystem boundaries.

**Decision:** Implement the Crafted subsystem only within `Crafted/` and `CraftedTests/`, and treat `forge-docs/` and `forge-standards/` as authoritative inputs rather than implementation targets.

**Consequences:** Swift and SwiftUI code, assets, view models, and app-shell logic must live under `Crafted/`. XCTest coverage for Crafted must live under `CraftedTests/`. Crafted implementation must not relocate, duplicate, or reinterpret source-of-truth TRD material into runtime code. Cross-language coupling to `src/` must occur through defined interfaces, not by collapsing directory boundaries.

**Rejected alternatives:**  
- Placing Crafted implementation alongside Python backend code in `src/` was rejected because it blurs language and subsystem ownership.  
- Moving TRD-derived behavior into `forge-docs/` or editing docs as part of runtime implementation was rejected because documentation is the source of truth, not executable substrate.  
- Creating a parallel ad hoc app directory outside `Crafted/` was rejected because it violates the prescribed repository layout.

## [Treat forge-docs TRDs as mandatory design inputs before implementation]
**Status:** Accepted

**Context:** The repository guidance explicitly states that all TRDs and PRDs live in `forge-docs/` and must be read before building. Crafted is not an isolated app shell; it is constrained by the broader multi-TRD system architecture.

**Decision:** Read and implement the Crafted subsystem in conformance with the relevant TRDs in `forge-docs/` before making code changes.

**Consequences:** Crafted features must be traceable to documented requirements. Implementation choices that conflict with TRDs are disallowed even if locally convenient. Changes to Crafted must assume the broader system constraints defined across the repository, not just SwiftUI concerns.

**Rejected alternatives:**  
- Treating README summaries as sufficient requirements was rejected because the TRDs are the source of truth.  
- Implementing Crafted based on inferred UX or standard macOS defaults without TRD review was rejected because it risks divergence from documented behavior.  
- Using code-first discovery to define app behavior was rejected because the docs prescribe the intended architecture.

## [Respect critical file boundaries and avoid bypassing backend controls]
**Status:** Accepted

**Context:** The repository identifies several critical backend files whose behavior is system-wide and security-sensitive, including `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Crafted will surface or invoke system behavior, but must not undermine backend invariants.

**Decision:** Integrate Crafted with backend capabilities only through approved interfaces and never bypass the controls enforced by critical backend files.

**Consequences:** Crafted must not implement alternate GitHub write paths, path validation logic, CI generation logic, or orchestration rules that conflict with backend controls. Any UI affordance that triggers backend actions must preserve backend ownership of validation, rate limiting, SHA protocol, path security, checkpointing, and workflow generation.

**Rejected alternatives:**  
- Reimplementing GitHub operations in Swift for convenience was rejected because it risks divergence from `src/github_tools.py` safeguards.  
- Allowing Crafted to write directly to repository paths without backend path-security enforcement was rejected because it violates the defined security boundary.  
- Duplicating orchestration logic in the UI layer was rejected because pipeline control belongs to backend critical files.

## [Preserve build-pipeline stage semantics in Crafted-facing flows]
**Status:** Accepted

**Context:** The README defines a staged build pipeline, including test and CI stages and an operator gate before merge. It also states that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`, and every gate decision is recorded.

**Decision:** Model Crafted interactions with generation, testing, commit, CI, and approval workflows according to the documented pipeline stages and checkpoint semantics.

**Consequences:** Crafted must present or consume pipeline state as staged, ordered, and checkpointed rather than as a single opaque “working” state. UI and app-shell flows must not skip or collapse mandatory transitions. Operator approval must remain a distinct gate rather than an implicit side effect of successful automation.

**Rejected alternatives:**  
- Presenting the pipeline as a single undifferentiated progress indicator was rejected because it obscures required stage semantics and checkpoints.  
- Auto-merging immediately after CI success was rejected because the documented operator gate must remain explicit.  
- Allowing UI-triggered shortcuts that skip test or CI stages was rejected because they violate the prescribed pipeline.

## [Do not introduce stage logic exceeding the complexity limit]
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15. Although this limit is called out in backend pipeline guidance, it reflects a broader maintainability constraint for orchestration logic that Crafted may expose or coordinate with.

**Decision:** Keep Crafted orchestration, state-transition handling, and stage-related control logic within the documented complexity ceiling, and factor code before exceeding it.

**Consequences:** Root coordinators, view models, and app-shell controllers in Crafted must be decomposed rather than accumulating branching logic. Complex decision trees must be represented through smaller units, typed state, and composition. This constrains implementation style toward explicit state machines and isolated handlers.

**Rejected alternatives:**  
- Centralizing all app-shell decision-making in one large coordinator was rejected because it invites complexity growth beyond the documented threshold.  
- Encoding workflow branching directly in large SwiftUI views was rejected because it reduces testability and maintainability.  
- Ignoring the limit for UI-side orchestration because it is “not backend code” was rejected because the constraint exists to control system complexity across stage logic.

## [Implement the root application shell from the documented onboarding decision tree]
**Status:** Accepted

**Context:** TRD-1 defines the Crafted macOS application shell root view decision tree. It specifies that `RootView` routes to `OnboardingContainerView` when `OnboardingState != .complete`, with subflows including `.notStarted → WelcomeView`, `.apiKeys → APIKeysView`, `.githubAuth → GitHubAuthView`, and additional onboarding states implied by the TRD. This is an explicit architectural decision, not a suggestion.

**Decision:** Build Crafted’s root navigation as a state-driven decision tree centered on `RootView`, with onboarding gating all post-onboarding application content until `OnboardingState == .complete`.

**Consequences:** The app shell must not allow users to bypass onboarding-dependent prerequisites. Root-level presentation must be driven by onboarding state rather than ad hoc navigation flags. Onboarding views must remain distinct states in a container flow, and post-onboarding content must only appear after completion.

**Rejected alternatives:**  
- Using a tab-first application shell that exposes all features before onboarding completion was rejected because it conflicts with the TRD decision tree.  
- Allowing deep links directly into authenticated or operational views before onboarding completion was rejected because onboarding is a hard gate.  
- Implementing onboarding as a modal layered over the main app was rejected because the TRD defines onboarding as the root routing branch.

## [Represent onboarding as explicit states, not implicit flags]
**Status:** Accepted

**Context:** The documented root view decision tree enumerates onboarding progression through named states such as `.notStarted`, `.apiKeys`, and `.githubAuth`, culminating in `.complete`. This implies a discrete state model rather than loosely related booleans.

**Decision:** Encode onboarding progression as an explicit finite state model and route views from that state.

**Consequences:** Crafted must avoid scattered boolean flags like “hasSeenWelcome,” “hasAPIKeys,” and “isGitHubAuthed” as the primary navigation source of truth. View transitions, persistence, restoration, and testing should target a single onboarding state representation. This supports predictable resumption and consistent root routing.

**Rejected alternatives:**  
- Managing onboarding with multiple independent booleans was rejected because it permits invalid combinations and complicates restoration.  
- Driving onboarding only from view-local state was rejected because root navigation needs a shared, durable source of truth.  
- Using stringly typed route identifiers for onboarding phases was rejected because the TRD implies named, structured states.

## [Keep operator approval as a first-class gate in Crafted UX]
**Status:** Accepted

**Context:** The build pipeline defines a gate stage where the operator approves or corrects before merge, and every gate decision is recorded. Crafted, as the application shell, is a likely place where this gate is surfaced.

**Decision:** Expose operator approval and correction as explicit user actions in Crafted, and do not hide or automate away the gate.

**Consequences:** Crafted UX must provide a clear decision point before merge-related completion. The app must support both approval and correction paths. Any status display or action model that implies “CI passed means done” is non-compliant. Auditability expectations require the decision to remain distinct and attributable.

**Rejected alternatives:**  
- Treating operator review as optional metadata after merge was rejected because the gate is required before merge.  
- Auto-approving successful runs was rejected because it removes the documented human gate.  
- Hiding correction workflows behind developer-only tooling was rejected because the operator must be able to correct before merge.

## [Separate Swift XCTest coverage from Python pytest coverage]
**Status:** Accepted

**Context:** The repository layout separates `CraftedTests/` for XCTest suites from `tests/` for Python pytest suites. Crafted is a Swift subsystem and must align with the prescribed test layout.

**Decision:** Place Crafted automated tests in `CraftedTests/` using XCTest, and do not mix Swift app-shell tests into the Python `tests/` hierarchy.

**Consequences:** View model, navigation, state-machine, and app-shell behavior for Crafted must be testable in XCTest. Cross-subsystem end-to-end validation may involve broader infrastructure, but Swift unit and integration tests belong in `CraftedTests/`. This preserves language-appropriate tooling and repository clarity.

**Rejected alternatives:**  
- Putting Swift behavior validation into Python-driven tests only was rejected because it weakens direct coverage of Swift logic.  
- Creating a custom nonstandard test directory for Crafted was rejected because it violates the repository layout.  
- Relying solely on manual UI verification for Crafted was rejected because the repository prescribes automated test structure.

## [Use CI workflows as defined by repository conventions]
**Status:** Accepted

**Context:** The README specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. The repository also identifies `src/ci_workflow.py` as the generator for workflow logic, making CI definition a controlled subsystem concern.

**Decision:** Align Crafted CI expectations with the documented workflow split and do not introduce ad hoc CI paths that conflict with generated workflow conventions.

**Consequences:** Swift-specific validation for Crafted must remain compatible with the macOS workflow path, while shared or non-Swift concerns align with the existing CI structure. Crafted implementation must not depend on undocumented CI behavior. Workflow changes affecting Crafted should respect generator ownership in `src/ci_workflow.py`.

**Rejected alternatives:**  
- Running all Crafted validation only on Ubuntu was rejected because Swift requires the documented macOS workflow.  
- Hand-maintaining separate bespoke Crafted workflows outside the established generation path was rejected because CI workflow ownership is centralized.  
- Assuming local build success is sufficient without CI alignment was rejected because pipeline stage 5 explicitly requires test plus CI.