# DECISIONS.md

## [Use the documented repository layout as a hard architectural boundary]
**Status:** Accepted  
**Context:** The FullPlatform subsystem operates inside a repository whose structure is explicitly defined in the TRDs and README. The docs directory is the source of truth, standards live in a dedicated standards directory, Python backend code lives under `src/`, the macOS shell lives under `Crafted/`, Swift tests live under `CraftedTests/`, and Python tests live under `tests/`. The repository structure is not informational; it constrains discovery, implementation location, and review expectations.  
**Decision:** Preserve and implement against the documented repository layout exactly. Place FullPlatform backend/runtime logic in `src/`, macOS application shell logic in `Crafted/`, platform test coverage in `tests/` and `CraftedTests/`, and all design-governing artifacts in `forge-standards/` and `forge-docs/`. Do not introduce parallel top-level source trees or alternate standards/document locations.  
**Consequences:** Implementation must align with the existing layout for tooling, review, and agent coordination to work predictably. Code generation, CI, onboarding of contributors, and document lookup all assume these fixed paths. Cross-cutting platform changes must respect the separation between backend Python code and Swift application-shell code.  
**Rejected alternatives:**  
- **Create a new top-level `fullplatform/` directory:** Rejected because it fragments the documented architecture and breaks established code discovery conventions.  
- **Co-locate standards or TRDs with source code:** Rejected because `forge-docs/` and `forge-standards/` are explicitly designated as authoritative locations.  
- **Merge Python and Swift sources into a shared application tree:** Rejected because the platform already distinguishes runtime/backend concerns from the macOS shell.

## [Treat TRDs and PRDs in `forge-docs/` as the source of truth before implementation]
**Status:** Accepted  
**Context:** The repository guidance explicitly states that all TRDs and PRDs live in `forge-docs/` and must be read before building. FullPlatform spans multiple subsystem concerns, so implementation decisions must trace back to those documents rather than inferred behavior or convenience.  
**Decision:** Read and conform to the applicable TRDs and PRDs in `forge-docs/` before modifying or extending FullPlatform behavior. Treat those documents as authoritative over local assumptions, ad hoc code comments, or undocumented practices.  
**Consequences:** Implementation work must be document-driven. Changes that diverge from the TRDs require document updates and explicit design review rather than silent code drift. This also constrains future contributors to justify behavior against repository documentation.  
**Rejected alternatives:**  
- **Use current code behavior as the primary source of truth:** Rejected because code may lag design intent and the docs are explicitly authoritative.  
- **Rely on oral/team knowledge for subsystem behavior:** Rejected because it is not durable, reviewable, or enforceable across agents and contributors.  
- **Treat docs as advisory only:** Rejected because the repository instructions say they must be read before building.

## [Honor critical-file ownership and modification sensitivity]
**Status:** Accepted  
**Context:** Several files are called out as critical because they form security, orchestration, CI, and GitHub I/O boundaries. Changes to these files have repository-wide impact, including on every PR the system builds. FullPlatform must not bypass or casually duplicate their responsibilities.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as controlled architectural boundaries. Modify them only when the FullPlatform change explicitly requires it, and do not reimplement their responsibilities elsewhere to avoid those boundaries.  
**Consequences:** New FullPlatform logic must integrate through these modules instead of creating shadow orchestration, shadow GitHub access, or shadow path validation. Reviews for changes touching these files require heightened scrutiny because failures propagate across the entire platform.  
**Rejected alternatives:**  
- **Duplicate critical functionality in new FullPlatform modules:** Rejected because it creates inconsistent behavior and weakens enforcement of central safeguards.  
- **Bypass critical modules for speed or local simplification:** Rejected because these files are designated as platform-wide control points.  
- **Freely refactor critical files during unrelated feature work:** Rejected because their blast radius is too large for incidental change.

## [Route all filesystem write-path decisions through `src/path_security.py`]
**Status:** Accepted  
**Context:** The repository identifies `src/path_security.py` as the security boundary and states that every write path must pass through it. FullPlatform will necessarily create, modify, or checkpoint files, making write-path validation a mandatory control.  
**Decision:** Validate every FullPlatform filesystem write path through `src/path_security.py`. Do not write files via direct path manipulation, unchecked joins, or subsystem-local validation logic.  
**Consequences:** All file-producing features, including generated code, checkpoints, CI artifacts, and document outputs, must use the central path security mechanism. This reduces path traversal risk and makes path policy consistent across the system. Any feature that cannot work within this boundary must be redesigned.  
**Rejected alternatives:**  
- **Perform local path validation inside each module:** Rejected because duplicated validation drifts and weakens the single security boundary.  
- **Rely on repository-relative paths without validation:** Rejected because trusted-relative assumptions are insufficient for a write boundary.  
- **Allow direct writes for internal-only code paths:** Rejected because internal code paths are still part of the attack and error surface.

## [Centralize all GitHub I/O in `src/github_tools.py`]
**Status:** Accepted  
**Context:** The repository defines `src/github_tools.py` as the module for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. FullPlatform features that interact with GitHub must preserve these controls and avoid inconsistent API behavior.  
**Decision:** Perform all FullPlatform GitHub reads and writes through `src/github_tools.py`. Do not call GitHub APIs directly from feature modules, orchestration code, or UI glue.  
**Consequences:** Rate limiting, SHA handling, and path-related safeguards remain consistent. FullPlatform integrations must conform to the semantics and constraints of the central GitHub layer, even if that requires adapter code. This also makes audit, retries, and future API hardening feasible in one place.  
**Rejected alternatives:**  
- **Use direct GitHub API calls in the FullPlatform subsystem:** Rejected because it bypasses required repository controls.  
- **Add a second GitHub abstraction specific to FullPlatform:** Rejected because it duplicates protocol handling and invites divergence.  
- **Allow UI code to perform GitHub operations directly:** Rejected because it mixes presentation with external I/O and bypasses central safeguards.

## [Keep pipeline orchestration inside `src/build_director.py` and respect the complexity ceiling]
**Status:** Accepted  
**Context:** The build pipeline is orchestrated by `src/build_director.py`, and the repository imposes a strict maximum cyclomatic complexity of 15 for every stage. FullPlatform must integrate with the existing pipeline model rather than introducing a competing orchestrator or allowing stage logic to become monolithic.  
**Decision:** Implement FullPlatform pipeline behavior by extending or composing with `src/build_director.py`, and keep every stage at cyclomatic complexity 15 or below. Decompose logic into focused helpers rather than embedding complex branching inside stage handlers.  
**Consequences:** Pipeline changes remain testable, reviewable, and aligned with repository constraints. FullPlatform features that need orchestration must fit the stage-based architecture and may require additional helper modules rather than inlining logic. Complexity becomes a design constraint, not just a lint target.  
**Rejected alternatives:**  
- **Create a separate FullPlatform orchestrator:** Rejected because it fragments control flow and duplicates pipeline responsibilities.  
- **Ignore the complexity ceiling when functionality grows:** Rejected because the limit is explicitly strict and intended to preserve maintainability.  
- **Collapse multiple stages into one complex handler:** Rejected because it undermines checkpointing, diagnosis, and gate clarity.

## [Checkpoint every state transition, including per-PR stages]
**Status:** Accepted  
**Context:** The build pipeline documentation states that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. FullPlatform participates in this lifecycle and must preserve recoverability and auditability.  
**Decision:** Persist a checkpoint for every FullPlatform state transition, including all per-PR progression states and any subsystem-specific transitions added on top of them. Do not model progress as in-memory-only or implicit control flow.  
**Consequences:** The subsystem must expose durable state that supports resume, audit, debugging, and operator review. Features that mutate PR state must declare transition points clearly enough to checkpoint them. Error handling must assume restart from the last checkpoint rather than from process memory.  
**Rejected alternatives:**  
- **Checkpoint only major milestones:** Rejected because the documented requirement covers every state transition.  
- **Use logs as a substitute for checkpointing:** Rejected because logs are not equivalent to restartable state.  
- **Track state only in transient memory:** Rejected because it breaks recovery and observability.

## [Preserve the documented staged build pipeline and fix-loop behavior]
**Status:** Accepted  
**Context:** The README defines a specific build pipeline sequence, including analysis steps such as `ast.parse`, `ruff`, import checks, and a fix loop using `pytest` for up to 20 attempts with failure-type-aware strategy. FullPlatform must fit this operational model rather than redefining validation and correction flow.  
**Decision:** Implement FullPlatform generation and repair behavior within the documented staged pipeline, including static analysis before test execution and a bounded fix loop of at most 20 `pytest` attempts using failure-type-aware handling. Do not introduce unbounded retries or reorder the quality gates casually.  
**Consequences:** Validation remains deterministic and bounded. FullPlatform repair strategies must classify failures rather than blindly retrying. Any new stage-level behavior must preserve the existing ordering and semantics unless the governing documents are updated.  
**Rejected alternatives:**  
- **Use unlimited test-repair retries:** Rejected because bounded attempts are explicitly specified.  
- **Run tests before syntax and lint checks:** Rejected because the pipeline defines earlier static validation stages.  
- **Apply a single generic retry strategy for all failures:** Rejected because the documented loop is failure-type-aware.

## [Use crafted CI workflows as the canonical CI targets]
**Status:** Accepted  
**Context:** The build pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. FullPlatform spans Python backend and Swift shell concerns, so CI target selection must remain aligned with platform responsibilities.  
**Decision:** Use the documented crafted CI workflows as the canonical CI execution paths: `crafted-ci.yml` for the general pipeline on Ubuntu and `crafted-ci-macos.yml` for Swift/macOS-specific validation. Do not introduce substitute workflows for equivalent responsibilities without updating the governing docs.  
**Consequences:** Python/backend changes must remain compatible with the Ubuntu pipeline, while Swift/macOS shell changes must validate on the macOS workflow. FullPlatform implementation must be conscious of where each concern is exercised in CI.  
**Rejected alternatives:**  
- **Run all CI only on one operating system:** Rejected because Swift/macOS concerns require dedicated macOS validation.  
- **Create ad hoc feature-specific workflows as primary gates:** Rejected because it fragments the canonical CI model.  
- **Skip macOS workflow for shell-adjacent changes with backend impact only:** Rejected when Swift-facing behavior is affected, because the documented split exists to catch those issues.

## [Require operator approval at the gate before merge]
**Status:** Accepted  
**Context:** The pipeline includes a Gate stage where the operator approves or corrects before merge. FullPlatform may automate generation, testing, and CI progression, but the final merge path includes a human decision point.  
**Decision:** Preserve the operator gate as a mandatory pre-merge control. Do not allow FullPlatform to auto-merge solely on successful generation, tests, and CI.  
**Consequences:** Automation must stop at the gate and surface enough context for operator approval or correction. Design must account for human-in-the-loop workflow, including actionable status and checkpoint visibility.  
**Rejected alternatives:**  
- **Enable fully automatic merge after CI passes:** Rejected because the documented gate requires operator approval or correction.  
- **Make the operator gate optional for low-risk changes:** Rejected because no such exception is defined.  
- **Collapse operator review into CI status alone:** Rejected because approval is a distinct decision, not just a test result.

## [Record gate decisions explicitly]
**Status:** Accepted  
**Context:** The build pipeline documentation states that every gate decision is recorded. Because FullPlatform includes checkpointed progression and a human gate, gate outcomes must be durable and inspectable.  
**Decision:** Persist every FullPlatform gate decision explicitly, including approvals, corrections, and any associated transition metadata. Do not treat gate outcomes as implicit in merge state or log text alone.  
**Consequences:** Auditing, debugging, and process compliance become possible without reconstructing state from external systems. UI and backend flows must surface and store gate results as first-class entities.  
**Rejected alternatives:**  
- **Infer gate decisions from merge/no-merge outcomes:** Rejected because that loses decision intent and correction context.  
- **Store gate outcomes only in logs:** Rejected because logs are not reliable structured decision records.  
- **Record only approvals and omit corrections:** Rejected because the docs require recording every gate decision.

## [Maintain a strict separation between Python backend/runtime and Swift application-shell responsibilities]
**Status:** Accepted  
**Context:** The repository layout and TRD set distinguish Python backend implementation under `src/` from the macOS Swift/SwiftUI application shell under `Crafted/`. The FullPlatform subsystem necessarily spans both, but the architectural boundary remains important for testability, runtime independence, and platform clarity.  
**Decision:** Keep orchestration, backend runtime, GitHub integration, security controls, and pipeline logic in Python under `src/`, and keep macOS shell presentation, root view routing, and native UI behavior in Swift under `Crafted/`. Communicate across the boundary through explicit interfaces rather than embedding backend logic in the shell or UI logic in the backend.  
**Consequences:** The subsystem remains portable and understandable. Swift code can focus on native application behavior, while Python code owns automation and platform services. Cross-language changes require interface design rather than opportunistic coupling.  
**Rejected alternatives:**  
- **Move backend orchestration into the Swift app:** Rejected because it conflicts with the documented source layout and backend ownership.  
- **Generate or control UI behavior directly from Python implementation details:** Rejected because it collapses presentation and runtime concerns.  
- **Treat Swift shell code as just another backend client without architectural distinction:** Rejected because the application shell has explicit platform-specific responsibilities.

## [Implement the macOS root experience according to the documented onboarding decision tree]
**Status:** Accepted  
**Context:** TRD-1 defines a root view decision tree in which `RootView` routes to `OnboardingContainerView` until onboarding is complete, with explicit onboarding substates including `.notStarted`, `.apiKeys`, and `.githubAuth`. FullPlatform must not invent a competing root-routing model for the macOS shell.  
**Decision:** Implement macOS FullPlatform root navigation so that `RootView` follows the documented onboarding-state decision tree, routing users through onboarding until completion before exposing the main experience.  
**Consequences:** Root routing becomes state-driven and predictable. Features that require platform readiness, such as API key setup or GitHub authentication, must integrate with onboarding state rather than bypassing it. Future UI additions must respect this root decision structure.  
**Rejected alternatives:**  
- **Present the main application immediately and prompt for setup later:** Rejected because the documented root flow requires onboarding-first gating.  
- **Use a different root router independent of onboarding state:** Rejected because it would conflict with the specified decision tree.  
- **Allow partial access before GitHub/auth setup is complete:** Rejected where it contradicts the onboarding completion gate implied by the root flow.