# DECISIONS.md

## Repository structure is fixed and documentation-first
**Status:** Accepted  
**Context:** The subsystem operates inside a repository whose layout is explicitly defined by the TRDs and README. `forge-docs/` is the source of truth for product and technical requirements, `forge-standards/` contains implementation constraints, `src/` contains the Python backend, and `Crafted/` contains the macOS Swift/SwiftUI shell. The FullPlatform subsystem must fit this structure so agents and humans can reason about ownership and boundaries consistently.  
**Decision:** Preserve the documented top-level repository structure and treat `forge-docs/` as the authoritative input before implementation. Place Python FullPlatform backend code under `src/`, macOS shell code under `Crafted/`, tests under `tests/` and `CraftedTests/`, and standards documents under `forge-standards/`.  
**Consequences:** Implementation may not invent parallel source roots, move standards into code directories, or bypass TRDs as the source of truth. Any new FullPlatform assets must align with the existing directory contract. Tooling, scripts, and generated outputs must assume this layout.  
**Rejected alternatives:**  
- Using a feature-based top-level layout: rejected because it conflicts with the documented repository contract and would break agent assumptions.  
- Co-locating docs with implementation files: rejected because TRDs are explicitly centralized in `forge-docs/`.  
- Creating a separate FullPlatform repository: rejected because the subsystem is defined as part of this repository and depends on shared standards and pipelines.

## Critical files are protected change boundaries
**Status:** Accepted  
**Context:** The TRDs identify specific files whose behavior is system-critical: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. FullPlatform work that touches these files has outsized impact on generation, orchestration, GitHub I/O, security, and CI generation.  
**Decision:** Treat the documented critical files as protected architectural boundaries. Require any FullPlatform change affecting them to preserve their stated responsibilities and avoid incidental refactoring outside the targeted behavior.  
**Consequences:** FullPlatform implementation must not redistribute the responsibilities of these files casually or introduce bypass paths around them. Changes in these files should be narrow, reviewable, and justified by subsystem requirements.  
**Rejected alternatives:**  
- Freely refactoring critical files during feature work: rejected because the files are explicitly marked as high impact.  
- Duplicating logic from critical files elsewhere: rejected because it creates divergent behavior in generation, security, and CI.  
- Bypassing critical files with direct utility calls: rejected because it weakens the intended control points.

## All write paths must pass through path security validation
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. FullPlatform will necessarily create, modify, or stage files; without a single enforced boundary, path traversal and unauthorized writes become likely failure modes.  
**Decision:** Route every filesystem write performed by FullPlatform through the centralized path validation mechanism in `src/path_security.py`. Do not perform direct writes that bypass this layer.  
**Consequences:** File creation, updates, generated artifacts, patches, and CI-related outputs must use approved write APIs. Callers must be structured to validate destination paths before mutating the filesystem. Security enforcement remains centralized and auditable.  
**Rejected alternatives:**  
- Performing ad hoc path checks in each caller: rejected because distributed checks are inconsistent and harder to audit.  
- Trusting repository-relative paths without validation: rejected because relative paths do not eliminate traversal or boundary risks.  
- Validating only external inputs: rejected because internal composition bugs can also produce unsafe write targets.

## GitHub I/O must be centralized through github_tools
**Status:** Accepted  
**Context:** `src/github_tools.py` owns GitHub I/O, including path validation, rate limiting, and SHA protocol handling. FullPlatform interactions with pull requests, branches, commits, and repository contents must respect these invariants.  
**Decision:** Perform all FullPlatform GitHub reads and writes through `src/github_tools.py`; do not call the GitHub API directly from feature code. Preserve SHA-aware update semantics, built-in path controls, and rate-limiting behavior.  
**Consequences:** New GitHub features must be expressed as additions to or uses of the centralized GitHub tool layer. This constrains implementation to one integration boundary and reduces protocol drift.  
**Rejected alternatives:**  
- Calling GitHub APIs directly from orchestration or feature modules: rejected because it fragments rate limiting and SHA handling.  
- Using shell-based git/GitHub commands as the primary integration path: rejected because the designated boundary is Python I/O through `github_tools.py`.  
- Creating a second GitHub client abstraction for FullPlatform only: rejected because it would duplicate policy and increase inconsistency risk.

## Pipeline stages and state transitions must remain explicit and checkpointed
**Status:** Accepted  
**Context:** The build pipeline defines explicit stages and requires every state transition to be checkpointed, including per-PR transitions such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. FullPlatform spans backend, CI, and application shell work, so recoverability and auditability depend on durable stage tracking.  
**Decision:** Model FullPlatform execution as explicit pipeline stages with checkpointed state transitions. Persist all documented per-PR transitions and do not collapse multiple stage changes into opaque execution steps.  
**Consequences:** Long-running or multi-step work must be resumable from checkpoints. Operators and automation can inspect progress and failures at a stage boundary. Code structure must expose named transitions rather than implicit progress inside large functions.  
**Rejected alternatives:**  
- Treating the workflow as a single transaction: rejected because failures would be harder to recover and inspect.  
- Checkpointing only major milestones: rejected because the TRD requires every state transition to be checkpointed.  
- Inferring state from repository contents instead of storing transitions: rejected because inference is brittle and non-auditable.

## Stage implementations must not exceed cyclomatic complexity 15
**Status:** Accepted  
**Context:** The build pipeline explicitly states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` enforces this discipline. FullPlatform orchestration can easily accumulate conditional logic across backend, CI, and macOS shell concerns.  
**Decision:** Keep each FullPlatform pipeline stage at cyclomatic complexity 15 or below. Split orchestration into smaller helpers or sub-stages rather than allowing stage handlers to grow beyond the limit.  
**Consequences:** Implementation must favor decomposition, explicit delegation, and narrow stage responsibilities. Large conditional controllers are not permitted. Reviews should reject stage growth that violates the complexity ceiling.  
**Rejected alternatives:**  
- Allowing higher complexity in “central” orchestration code: rejected because the complexity cap applies to every stage.  
- Enforcing the limit only informally: rejected because this boundary exists to constrain architecture, not just style.  
- Moving complex logic into nested closures or dynamic dispatch to hide complexity: rejected because it preserves cognitive complexity while evading the rule.

## The fix loop must remain bounded and failure-type-aware
**Status:** Accepted  
**Context:** The documented pipeline includes a fix loop that runs `pytest` with up to 20 attempts and uses failure-type-aware strategy. FullPlatform work may involve iterative repair across Python, CI, and generated code, but unbounded repair loops create cost, latency, and non-termination risks.  
**Decision:** Implement FullPlatform repair behavior as a bounded fix loop with a hard cap of 20 attempts and strategy selection informed by failure type. Do not use unbounded retries or uniform retry behavior.  
**Consequences:** Retry logic must classify failures and stop after the configured limit. Observability should make each attempt and strategy choice visible. Some failures will remain unresolved and must surface to operators instead of looping indefinitely.  
**Rejected alternatives:**  
- Retrying until success: rejected because it can stall indefinitely and hide real defects.  
- Using a single generic retry strategy: rejected because the TRD requires failure-type-aware handling.  
- Failing immediately after one test run: rejected because the pipeline explicitly includes iterative repair.

## CI generation must target the documented runner split
**Status:** Accepted  
**Context:** The README specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. FullPlatform spans Python backend and macOS shell concerns, so CI must preserve this platform separation instead of collapsing everything onto one runner class.  
**Decision:** Generate and maintain CI workflows that follow the documented split: Ubuntu-based workflow for general/backend validation and macOS-based workflow for Swift-related validation.  
**Consequences:** Python and repository-wide checks should not force unnecessary macOS execution, and Swift validation must not be incorrectly hosted on Ubuntu. CI changes must preserve runner intent and workflow naming compatibility.  
**Rejected alternatives:**  
- Running all CI on macOS: rejected because it increases cost and diverges from the documented Ubuntu workflow for general checks.  
- Running all CI on Ubuntu: rejected because Swift/macOS validation requires the macOS workflow.  
- Generating ad hoc workflow names per feature: rejected because the repository already defines stable workflow identities.

## Operator gate remains mandatory before merge
**Status:** Accepted  
**Context:** The pipeline includes a gate stage where an operator approves or corrects before merge, and every gate decision is checkpointed. FullPlatform is cross-cutting and can affect code generation, CI, and application behavior, so human oversight is a required control point.  
**Decision:** Require an explicit operator approval or correction gate before any FullPlatform change is merged, and checkpoint that gate decision as part of the workflow state.  
**Consequences:** Full automation may not bypass the pre-merge operator gate. Merge-ready status must remain distinct from approved-for-merge status. Workflow state must record whether the operator approved or requested correction.  
**Rejected alternatives:**  
- Auto-merging after tests and CI pass: rejected because the process explicitly requires operator approval.  
- Logging operator input without checkpointing it: rejected because gate decisions are required to be checkpointed.  
- Restricting operator review only to high-risk changes: rejected because the gate is defined as part of the standard pipeline.

## The macOS shell root view must follow the onboarding-first decision tree
**Status:** Accepted  
**Context:** TRD-1 defines the RootView decision tree: if onboarding is not complete, the application shows `OnboardingContainerView` and its state-specific child views; only after onboarding completion should the normal application flow continue. FullPlatform includes the app shell integration surface and must not undermine this entry contract.  
**Decision:** Implement the macOS shell root navigation according to the documented onboarding-first RootView decision tree. Route incomplete onboarding states to `OnboardingContainerView` and its state-specific views before exposing post-onboarding application surfaces.  
**Consequences:** FullPlatform features integrated into the app shell must respect onboarding state and may not assume immediate access to the main application UI. Root navigation logic must remain state-driven and consistent with the documented onboarding phases.  
**Rejected alternatives:**  
- Presenting the main application UI and overlaying onboarding later: rejected because it violates the root decision tree.  
- Skipping intermediate onboarding states when partial configuration exists: rejected because the TRD defines explicit state-based routing.  
- Allowing features to mount their own root screens independently: rejected because RootView is the central navigation authority.