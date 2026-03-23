# DECISIONS.md

## [Crafted lives as a dedicated Swift application shell at the repository root]
**Status:** Accepted  
**Context:** The repository structure explicitly separates Python backend implementation in `src/` from the macOS application shell in `Crafted/` and `CraftedTests/`. The Crafted subsystem must remain clearly bounded so UI concerns do not leak into backend orchestration and security-critical Python modules.  
**Decision:** Keep the Crafted subsystem as a standalone Swift/SwiftUI macOS application in `Crafted/`, with XCTest coverage in `CraftedTests/`, and do not colocate Crafted implementation inside `src/` or other backend directories.  
**Consequences:** This constrains implementation to use Swift/SwiftUI for the app shell and XCTest for native testing. Shared repository logic must cross subsystem boundaries through explicit interfaces rather than direct source intermixing. Backend changes in `src/` must not assume UI-layer ownership of orchestration, path security, or GitHub I/O.  
**Rejected alternatives:**  
- Embedding Crafted UI code inside `src/`: rejected because it would blur language and subsystem boundaries and weaken maintainability.  
- Placing macOS tests under `tests/`: rejected because Python test infrastructure is distinct from XCTest and would obscure platform-specific validation.  
- Creating a monolithic single-app structure with no dedicated Crafted boundary: rejected because the repository layout already establishes explicit subsystem separation.

## [Crafted must follow the documented root view onboarding decision tree]
**Status:** Accepted  
**Context:** TRD-1 defines a root view decision tree for the macOS application shell. The root view must deterministically select between onboarding and post-onboarding experiences based on onboarding completion state. This is foundational to user flow correctness.  
**Decision:** Implement Crafted root navigation as a state-driven decision tree rooted at `RootView`, where `OnboardingState != .complete` routes to `OnboardingContainerView`, and onboarding substates map to their corresponding screens exactly as specified by the TRD.  
**Consequences:** Root navigation cannot be ad hoc, imperative, or screen-local. New flows must preserve the top-level gating rule that onboarding completion controls entry into the main application experience. View composition and state management must support deterministic rendering from onboarding state.  
**Rejected alternatives:**  
- Using freeform navigation stacks without a root decision tree: rejected because it would allow invalid entry paths and diverge from the TRD.  
- Allowing individual onboarding screens to decide the next top-level route independently: rejected because it fragments state authority and makes flow correctness harder to verify.  
- Bypassing onboarding when partial setup exists: rejected because the TRD specifies explicit state-based routing rather than heuristic shortcuts.

## [Crafted must treat onboarding as an explicit finite state model]
**Status:** Accepted  
**Context:** The root view decision tree enumerates onboarding substates such as `.notStarted`, `.apiKeys`, and `.githubAuth`. These indicate a discrete workflow, not an implicit boolean or loosely inferred readiness check.  
**Decision:** Represent Crafted onboarding progress as an explicit finite state model with named states corresponding to the documented onboarding stages, and drive UI transitions from that model.  
**Consequences:** Implementation must not collapse onboarding into a single completion flag or infer progress from scattered persistence values alone. Persistence, restoration, and testing must be organized around state transitions. Screens must correspond to recognized states, and transition logic must be centralized and auditable.  
**Rejected alternatives:**  
- A single `isOnboarded` boolean: rejected because it cannot represent intermediate states required by the TRD.  
- Inferring current screen from which credentials happen to be present: rejected because it creates ambiguous state and brittle recovery behavior.  
- Hard-coding screen order in navigation-only logic: rejected because stateful recovery and deterministic root rendering require an explicit model.

## [Crafted must gate entry to the main experience until onboarding is complete]
**Status:** Accepted  
**Context:** The documented root decision tree makes onboarding completion the top-level condition for what the app displays. This is necessary because the app depends on required setup such as API keys and GitHub authentication before normal operation.  
**Decision:** Do not render or enable the main Crafted application experience until `OnboardingState == .complete`; all pre-completion states must remain inside onboarding containers and flows.  
**Consequences:** Main application views, actions, and integrations must assume onboarding prerequisites are already satisfied. Features requiring credentials or authentication must not independently implement first-run setup bypasses. Testing must validate that incomplete onboarding cannot access post-onboarding routes.  
**Rejected alternatives:**  
- Allowing partial app access before setup is complete: rejected because it undermines the top-level state model and introduces inconsistent prerequisite handling.  
- Prompting for missing setup opportunistically from within main views: rejected because onboarding is specified as a dedicated gated flow.  
- Treating onboarding as a dismissible modal over the main app: rejected because the TRD defines onboarding as a root-routing concern.

## [Crafted implementation must respect repository critical-file boundaries]
**Status:** Accepted  
**Context:** The repository identifies security- and orchestration-critical Python files that must be read before modifying: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Crafted must not duplicate or bypass these responsibilities from the app shell.  
**Decision:** Keep Crafted focused on application-shell concerns and integrate with backend capabilities only through approved interfaces; do not reimplement consensus, build orchestration, GitHub write logic, path validation, or CI workflow generation inside Crafted.  
**Consequences:** Crafted code must not become an alternate control plane for protected backend responsibilities. UI-triggered actions that depend on backend operations must delegate to the backend rather than replicate logic in Swift. This preserves the security boundary around path validation and the operational boundary around pipeline orchestration.  
**Rejected alternatives:**  
- Reimplementing backend flows in Swift for responsiveness or convenience: rejected because it would create behavioral drift and bypass documented critical boundaries.  
- Writing GitHub operations directly from Crafted: rejected because `src/github_tools.py` is the designated boundary for GitHub I/O, including validation and protocol handling.  
- Validating filesystem write paths independently in Crafted: rejected because `src/path_security.py` is the repository security boundary and must remain authoritative.

## [Crafted must align with the staged build pipeline and gate model rather than invent a parallel workflow]
**Status:** Accepted  
**Context:** The build pipeline defines staged execution, checkpointed state transitions, CI variants, and an operator approval gate before merge. Crafted exists within the same product and repository, so its implementation and automation must fit that system.  
**Decision:** Design Crafted changes, generated artifacts, and test expectations to participate in the existing staged pipeline and gate model, including checkpointed transitions and CI execution, instead of introducing a separate app-specific release or approval workflow.  
**Consequences:** Crafted-specific automation must integrate with repository CI and state tracking conventions. Feature implementation must account for operator approval gates and not assume autonomous merge or release behavior. Any Crafted-related generated files or transitions must be representable in the repository’s checkpointing model.  
**Rejected alternatives:**  
- A standalone Crafted-only workflow outside the repository pipeline: rejected because it would fragment operational visibility and violate the unified gate model.  
- Auto-merging Crafted changes after local tests only: rejected because the repository requires CI and operator gate participation.  
- Separate state tracking for Crafted unrelated to repository checkpoints: rejected because every stage transition is required to be checkpointed.

## [Crafted complexity must be managed to remain compatible with repository implementation standards]
**Status:** Accepted  
**Context:** The repository build pipeline enforces a cyclomatic complexity limit of 15 per stage, and critical orchestration files are explicitly complexity-constrained. While this rule is defined in pipeline terms, the same maintainability expectations apply to subsystem design, especially for root routing and onboarding logic.  
**Decision:** Structure Crafted view models, routing logic, and onboarding flow into small, composable units so that no single control component becomes a high-complexity decision hub; prefer explicit decomposition over deeply nested conditional flow.  
**Consequences:** RootView and onboarding coordinators must remain declarative and segmented. Feature additions should extend state and composition rather than pile branching into a single file. Tests should target decomposed units to keep control flow understandable and maintainable.  
**Rejected alternatives:**  
- Centralizing all app-shell routing and setup logic into one large coordinator: rejected because it would become brittle and difficult to validate.  
- Encoding many feature flags and conditional branches directly in views: rejected because it would erode readability and increase risk of invalid states.  
- Relying on implicit side effects instead of explicit decomposition: rejected because it makes state transitions harder to audit and test.

## [Crafted testing must remain native and subsystem-specific]
**Status:** Accepted  
**Context:** The repository layout provides `CraftedTests/` for XCTest suites and `tests/` for Python pytest suites. Since Crafted is a Swift/SwiftUI subsystem, its tests must use platform-appropriate tooling and remain isolated from backend test concerns.  
**Decision:** Place Crafted subsystem tests in `CraftedTests/` using XCTest, and reserve `tests/` for Python backend behavior; do not shift native app-shell validation into backend-oriented test infrastructure.  
**Consequences:** UI state, onboarding flow, and macOS shell behavior must be validated through XCTest-compatible tests. Cross-subsystem behavior may require integration coverage, but ownership of Crafted behavior remains with native tests. CI expectations for Crafted must include the macOS-specific path where appropriate.  
**Rejected alternatives:**  
- Testing Crafted behavior primarily through Python integration tests: rejected because native UI and app lifecycle concerns are not well represented there.  
- Mixing Swift tests into generic repository test folders: rejected because it weakens ownership and tooling clarity.  
- Relying mainly on manual QA for onboarding and root routing: rejected because the state-driven flow is deterministic and should be testable.

## [Crafted CI must use the repository’s macOS-specific workflow path]
**Status:** Accepted  
**Context:** The README identifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. Because Crafted is the Swift/macOS subsystem, its native validation belongs on the macOS CI path.  
**Decision:** Run Crafted build and test validation through the repository’s macOS-specific CI workflow for Swift, and do not treat the generic Ubuntu workflow as sufficient proof of correctness for Crafted changes.  
**Consequences:** Changes affecting Crafted must maintain compatibility with macOS CI requirements and cannot be considered fully validated by backend-only CI. Build scripts, dependencies, and tests for Crafted must be designed to execute on the macOS workflow.  
**Rejected alternatives:**  
- Validating Crafted only in the generic Ubuntu pipeline: rejected because Swift/macOS app-shell behavior requires the macOS workflow.  
- Deferring Crafted validation to developer machines only: rejected because repository CI is the required gate.  
- Creating an unrelated bespoke CI job outside the documented workflows: rejected because the repository already defines the relevant Swift path.