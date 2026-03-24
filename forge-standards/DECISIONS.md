# DECISIONS.md

## [Use the documented repository layout as a hard architectural boundary]
**Status:** Accepted

**Context:** The Crafted subsystem exists within a larger monorepo whose structure is explicitly defined in the TRDs and README. The repository layout separates source-of-truth documents, implementation code, standards, tests, and the macOS application shell. This layout is part of the operating model for all agents and build stages.

**Decision:** Preserve the repository layout exactly as documented. Implement the macOS application shell under `Crafted/`, Swift tests under `CraftedTests/`, Python backend code under `src/`, Python tests under `tests/`, standards under `forge-standards/`, and requirements artifacts under `forge-docs/`. Do not relocate Crafted code into `src/` or mix Swift and Python concerns in the same top-level directory.

**Consequences:** Crafted implementation must assume clear subsystem boundaries. Shared logic between Crafted and backend must cross explicit interfaces rather than filesystem co-location. Build tooling, CI, documentation references, and agent automation may rely on these paths. Refactors that change top-level placement are out of bounds unless the governing TRDs are changed first.

**Rejected alternatives:**  
- **Flatten the repo into a single app directory:** Rejected because it breaks the documented source-of-truth structure and weakens separation between app shell, backend, and standards.  
- **Move Crafted under `src/` as another runtime module:** Rejected because `src/` is reserved for Python backend implementation, while Crafted is a Swift/SwiftUI subsystem.  
- **Create a new top-level macOS directory and deprecate `Crafted/`:** Rejected because it diverges from the prescribed repository layout and would create tooling/documentation drift.

## [Treat forge-docs and forge-standards as normative inputs before implementation]
**Status:** Accepted

**Context:** The TRDs explicitly state that all TRDs and PRDs live in `forge-docs/` and must be read before building. The standards directory contains architecture and interface constraints that govern implementation. Crafted must therefore be implemented as a downstream consumer of those artifacts, not as an independent source of truth.

**Decision:** Read and conform to requirements in `forge-docs/` and `forge-standards/` before changing Crafted code. Treat these documents as authoritative constraints on subsystem design, interfaces, and workflow behavior. Do not introduce implementation behavior in Crafted that conflicts with these artifacts.

**Consequences:** Crafted design and code changes must be traceable back to documented requirements. If implementation pressure suggests a conflicting change, the correct remedy is to update the governing document first rather than silently diverge in code. This also constrains code review: undocumented behavior is suspect even if technically feasible.

**Rejected alternatives:**  
- **Allow code to become the source of truth when documents lag:** Rejected because the repository model explicitly makes TRDs/PRDs and standards normative.  
- **Use docs as advisory only for the Crafted app shell:** Rejected because Crafted is part of the same governed system and cannot opt out of repository-wide design authority.  
- **Capture local Crafted-only decisions in code comments instead of standards/docs:** Rejected because it fragments decision authority and reduces discoverability for agents and reviewers.

## [Implement the Crafted shell as a SwiftUI state-driven root flow]
**Status:** Accepted

**Context:** TRD-1 defines a root view decision tree keyed off onboarding state, beginning with `RootView` and routing to onboarding content until onboarding is complete. This implies a state-driven composition model rather than ad hoc navigation.

**Decision:** Implement Crafted’s root shell around a single state-driven `RootView` that branches on `OnboardingState`. Route incomplete onboarding states to `OnboardingContainerView`, and represent substeps such as `.notStarted`, `.apiKeys`, `.githubAuth`, and related onboarding stages as explicit state cases rather than implicit navigation side effects.

**Consequences:** Root-level navigation logic must remain centralized and deterministic. Onboarding progression must be modeled as application state, not inferred from scattered view-local flags. Future additions to onboarding must extend the decision tree in a controlled way. This also constrains testing: root navigation should be verifiable through state transitions.

**Rejected alternatives:**  
- **Use a NavigationStack-first design with no explicit root decision tree:** Rejected because the TRD specifies root branching by onboarding state, not free-form navigation.  
- **Drive onboarding through persistent modal presentation from the main app:** Rejected because it obscures root state and weakens determinism of the shell flow.  
- **Encode onboarding completion using multiple unrelated booleans in different views:** Rejected because it increases inconsistency risk and conflicts with the explicit state-machine style implied by the TRD.

## [Model onboarding as a finite, explicit state machine]
**Status:** Accepted

**Context:** The documented root decision tree enumerates distinct onboarding stages. A discrete sequence of stages is better represented as an explicit state machine than as inferred combinations of persisted values.

**Decision:** Represent onboarding in Crafted with a closed set of explicit states, including at minimum the documented cases such as `.notStarted`, `.apiKeys`, `.githubAuth`, and `.complete`, plus any additional TRD-defined stages. Require transitions between these states to occur through controlled application logic.

**Consequences:** State handling becomes testable, serializable, and auditable. Illegal transitions can be prevented in one place. View rendering can remain declarative and deterministic. Persistence must store and restore recognized states rather than arbitrary partial progress fragments.

**Rejected alternatives:**  
- **Infer onboarding progress from presence of API keys and auth tokens only:** Rejected because missing or stale data would blur whether the user has completed a step, is mid-step, or needs remediation.  
- **Use a loosely typed string or dictionary for onboarding progress:** Rejected because it weakens exhaustiveness, validation, and compile-time safety.  
- **Let each onboarding screen decide the next screen independently:** Rejected because it scatters transition logic and undermines the root decision tree.

## [Keep GitHub integration behind the backend boundary]
**Status:** Accepted

**Context:** The repository identifies `src/github_tools.py` as the critical file for all GitHub I/O, including path validation, rate limiting, and SHA protocol. That establishes a backend-owned integration boundary for GitHub operations. Crafted must not bypass this control plane.

**Decision:** Route GitHub operations for Crafted through the backend/runtime interfaces that are backed by `src/github_tools.py`. Do not implement direct, parallel GitHub repository mutation logic in the Crafted Swift layer when equivalent backend-governed operations exist or are required by workflow.

**Consequences:** Crafted remains a client of the system’s controlled GitHub integration rather than an alternate executor. Security, validation, rate limiting, and protocol correctness remain centralized. Swift-side code should focus on user intent capture, display, and orchestration, not repository write semantics.

**Rejected alternatives:**  
- **Use direct GitHub API calls from Swift for convenience:** Rejected because it bypasses centralized path validation, SHA handling, and rate limiting controls.  
- **Duplicate GitHub mutation logic in both Swift and Python:** Rejected because it creates protocol drift and inconsistent security behavior.  
- **Allow direct local git operations from Crafted as the primary integration path:** Rejected because the documented system centers on governed GitHub I/O and checkpointed PR lifecycle management.

## [Honor checkpointed pipeline state as the source of progress truth]
**Status:** Accepted

**Context:** The README states that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. The Crafted subsystem may surface or react to progress, but it must not invent an independent lifecycle model.

**Decision:** When Crafted displays build, generation, review, or PR progress, use the checkpointed pipeline states as the canonical lifecycle. Do not create a separate app-only progression model that cannot be mapped directly to the documented system states.

**Consequences:** UI status indicators, progress views, and action availability must align to real pipeline checkpoints. This reduces ambiguity for operators and keeps frontend and backend behavior synchronized. Any new user-visible stage must correspond to a documented or implemented checkpoint, not an informal UI abstraction.

**Rejected alternatives:**  
- **Use simplified user-friendly stages unrelated to backend checkpoints:** Rejected because it introduces ambiguity and makes debugging/operator intervention harder.  
- **Track only coarse states like idle/running/done in the app:** Rejected because it loses required fidelity for the documented multi-stage workflow.  
- **Let each screen derive its own local understanding of progress:** Rejected because it fragments lifecycle semantics and risks contradictory status displays.

## [Preserve operator gate semantics in the Crafted experience]
**Status:** Accepted

**Context:** The documented pipeline includes a gate where the operator approves or corrects before merge, and every gate decision is material to the workflow. Crafted is part of the operator-facing shell and must therefore preserve, not hide, this control point.

**Decision:** Design Crafted flows so that operator approval/correction remains an explicit gate before merge-related completion. Do not automate through this gate by default, and do not present merge completion as automatic if operator action is still required.

**Consequences:** Crafted UI must expose pending approval states and operator actions clearly. Any automation affordance must stop short of bypassing the required gate unless the governing documents are changed. This constrains completion UX, notifications, and status labeling.

**Rejected alternatives:**  
- **Auto-approve successful pipeline runs in the app:** Rejected because it removes the documented operator gate.  
- **Hide gate details behind a generic “completed” label:** Rejected because it misrepresents actual workflow state.  
- **Treat operator correction as an exceptional side path rather than a first-class gate outcome:** Rejected because the workflow explicitly allows approval or correction before merge.

## [Design Crafted to coexist with dual CI targets rather than collapsing them]
**Status:** Accepted

**Context:** The build pipeline defines `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. This establishes a dual-CI model where platform-specific concerns are separated rather than unified under one runner.

**Decision:** Implement Crafted so that Swift/macOS validation remains compatible with the dedicated macOS CI workflow, while broader system checks remain compatible with the ubuntu-based workflow. Do not assume a single CI environment can validate all subsystem behavior.

**Consequences:** Crafted-specific build/test expectations must stay explicit and platform-aware. Changes to app shell code should anticipate macOS runner validation. Cross-subsystem changes should not couple Swift checks to Linux-only assumptions. Documentation and developer workflows must reflect that passing one CI lane does not replace the other where both apply.

**Rejected alternatives:**  
- **Collapse all validation into a single ubuntu workflow:** Rejected because Swift/macOS application shell behavior requires a macOS-specific lane.  
- **Run only macOS CI for all subsystem checks:** Rejected because the documented pipeline already separates broader and Swift-specific concerns.  
- **Treat Crafted as exempt from repository-wide CI orchestration:** Rejected because it is an integrated subsystem and must participate in the defined workflows.

## [Keep subsystem orchestration simple enough to satisfy complexity limits]
**Status:** Accepted

**Context:** The README states that every stage has a maximum cyclomatic complexity of 15, and critical orchestration files enforce this discipline. While this limit is documented for pipeline stages, the same architectural pressure applies to subsystem orchestration code that interacts with those stages.

**Decision:** Structure Crafted coordinators, view models, reducers, and root flow logic so that no single orchestration unit grows into a high-complexity decision hub. Split logic by stage, feature, or state boundary before complexity becomes concentrated.

**Consequences:** Crafted implementation should favor composable, narrowly scoped units over monolithic app controllers. Root flow, onboarding transitions, pipeline-state rendering, and operator actions should be decomposed into testable pieces. This improves maintainability and keeps the subsystem aligned with repository-wide complexity discipline.

**Rejected alternatives:**  
- **Centralize all app state and navigation in one large coordinator:** Rejected because it tends to accumulate branching complexity quickly and becomes hard to reason about.  
- **Allow complexity to grow in frontend code because the formal cap is documented for backend stages:** Rejected because the same maintainability rationale applies, and Crafted participates in those stage-driven workflows.  
- **Rely on stylistic review only instead of structural decomposition:** Rejected because complexity problems are easier to prevent via architecture than through subjective review comments.

## [Do not bypass documented security boundaries for file or repository writes]
**Status:** Accepted

**Context:** The repository marks `src/path_security.py` as the security boundary and states that every write path must pass through it. Crafted may initiate actions that cause writes, but must not create alternate write channels that escape the governed path-validation model.

**Decision:** Ensure any Crafted-initiated file or repository write operation is executed through backend paths that enforce the documented security boundary. Do not add direct Swift-side filesystem or repository mutation paths that circumvent centralized path validation when operating on governed project content.

**Consequences:** Crafted remains a requester of privileged mutations, not an ungoverned executor. Security-sensitive write validation stays centralized. Features that appear simple in the UI may require backend endpoints or commands rather than direct local implementation. This may increase integration work but preserves the documented trust boundary.

**Rejected alternatives:**  
- **Write directly to project files from the app shell for speed:** Rejected because it bypasses the mandated path security boundary.  
- **Maintain a separate Swift validation layer equivalent to `path_security.py`:** Rejected because duplicated security logic drifts and weakens assurance.  
- **Permit temporary bypasses for local-only operations:** Rejected because the requirement is framed as an every-write-path rule, not a production-only guideline.