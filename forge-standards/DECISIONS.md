# DECISIONS.md

## Repository and document source of truth
**Status:** Accepted

**Context:** ForgeAgent operates in a repository that separates implementation, standards, and requirements artifacts. The TRDs and PRDs define the intended system behavior and must be consulted before implementation changes are made. The repository layout explicitly identifies `forge-docs/` as the home for all TRDs and PRDs and `forge-standards/` as the location for engineering constraints.

**Decision:** Treat `forge-docs/` as the authoritative source of product and technical requirements, and treat `forge-standards/` as the authoritative source of implementation constraints. Require ForgeAgent changes to align with both before modifying `src/`, `Crafted/`, `CraftedTests/`, or `tests/`.

**Consequences:** Implementation must be traceable back to documented requirements. Engineers must read relevant TRDs and standards before changing subsystem behavior. Ad hoc behavior introduced only in code is non-compliant unless later reflected in the governing documents. Repository structure is not to be repurposed casually.

**Rejected alternatives:**  
- Using code as the primary source of truth: rejected because it allows drift from approved TRDs and standards.  
- Collapsing docs, standards, and code into a single mixed hierarchy: rejected because it weakens governance and makes requirement traceability harder.  
- Treating README guidance as sufficient without consulting TRDs: rejected because README excerpts are summaries, not the full design authority.

## Critical file modification requires heightened review
**Status:** Accepted

**Context:** Several files are explicitly identified as critical because they define core generation, orchestration, GitHub I/O, path security, and CI generation behavior. Changes in these files have repository-wide impact.

**Decision:** Require heightened care and explicit review when modifying `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Preserve their boundary responsibilities and do not bypass them from adjacent code.

**Consequences:** Cross-cutting changes must be centralized in the designated critical files rather than duplicated elsewhere. Refactors that move responsibilities out of these modules require explicit design justification. Tests for these files must be expanded when behavior changes. Hidden side channels around these modules are prohibited.

**Rejected alternatives:**  
- Allowing any module to perform equivalent behavior for convenience: rejected because it would fragment policy enforcement and create inconsistent behavior.  
- Treating critical files as advisory only: rejected because these files define key security and orchestration boundaries.  
- Moving logic opportunistically during feature work: rejected because it increases coupling and obscures operational control points.

## Build pipeline stages are fixed and must remain checkpointed
**Status:** Accepted

**Context:** The build pipeline is defined as a staged process including generation, validation, fix loops, testing, CI, and operator gate decisions. The README requires every state transition to be checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`.

**Decision:** Implement ForgeAgent as a stage-based pipeline with explicit checkpointed state transitions for every major and per-PR stage. Do not skip, merge, or make implicit any required transition.

**Consequences:** Pipeline execution must be resumable and auditable. State models, persistence, and logs must encode stage transitions explicitly. Recovery logic must restart from checkpoints rather than recomputing hidden internal state. New stages require documented additions to the checkpoint model.

**Rejected alternatives:**  
- A monolithic run-to-completion workflow without persisted intermediate states: rejected because it is not resumable or auditable.  
- Best-effort in-memory stage tracking: rejected because process crashes or restarts would lose state.  
- Collapsing multiple stages into one generic “processing” state: rejected because it removes operator visibility and weakens control over failure handling.

## Cyclomatic complexity per pipeline stage is capped at 15
**Status:** Accepted

**Context:** The build pipeline documentation explicitly states that every stage has a maximum cyclomatic complexity of 15. `src/build_director.py` is called out as having this limit strictly enforced.

**Decision:** Keep each pipeline stage implementation at cyclomatic complexity 15 or below. Split logic into helper functions or smaller components rather than exceeding the limit inside a stage.

**Consequences:** Orchestration code must remain decomposed and readable. Large conditional trees inside stage handlers are not acceptable. Complexity control becomes a design constraint during feature additions. Tests should target the smaller units created by decomposition.

**Rejected alternatives:**  
- Allowing complexity exceptions for orchestrators: rejected because orchestration complexity is exactly where maintainability failures accumulate fastest.  
- Enforcing complexity only at file level: rejected because it would still permit opaque stage functions.  
- Relying on code review judgment without a numeric cap: rejected because the TRD-derived rule is explicit and measurable.

## Python validation and repair loop are mandatory before CI
**Status:** Accepted

**Context:** The documented build pipeline includes a Python validation sequence of `ast.parse → ruff → import check`, followed by a failure-aware pytest fix loop with up to 20 attempts, before CI gating.

**Decision:** Run Python code generation outputs through `ast.parse`, Ruff, and import validation in that order, then execute a failure-type-aware pytest repair loop with a maximum of 20 attempts before advancing to CI.

**Consequences:** Generated Python changes cannot proceed directly to CI or merge without local structural and lint validation. Repair behavior must classify failures and adapt strategy accordingly. The fix loop must terminate at 20 attempts rather than retrying indefinitely. Telemetry and checkpoints must record attempt count and failure class.

**Rejected alternatives:**  
- Running CI first and relying on CI feedback for syntax and lint failures: rejected because it wastes CI capacity and slows iteration.  
- Using a generic retry loop without failure classification: rejected because the documented process requires failure-type-aware handling.  
- Allowing unlimited retries until success: rejected because it risks non-termination and resource waste.

## CI workflow generation must target Linux and macOS appropriately
**Status:** Accepted

**Context:** The repository build pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is identified as the generator for this behavior.

**Decision:** Generate and maintain distinct CI workflows for platform-specific responsibilities: use Ubuntu-based CI for general workflows and macOS-based CI for Swift-related validation.

**Consequences:** CI generation logic must preserve platform separation. Swift and SwiftUI validation cannot be assumed to run correctly on Linux-only infrastructure. Workflow changes must consider cost, runtime availability, and platform-specific toolchains. Consolidating both into a single runner target is not permitted without revising the governing requirements.

**Rejected alternatives:**  
- A single Ubuntu-only workflow for all components: rejected because Swift validation requires macOS support.  
- A single macOS-only workflow for everything: rejected because it is unnecessarily expensive and slower for general tasks.  
- Manual CI files edited outside the generator boundary: rejected because `src/ci_workflow.py` is the designated control point.

## Operator gate is mandatory before merge
**Status:** Accepted

**Context:** The build pipeline includes a gate where the operator approves or corrects before merge. Gate decisions are part of the checkpointed process.

**Decision:** Require an explicit operator approval or correction step before merge. Do not permit fully autonomous merge completion by ForgeAgent.

**Consequences:** ForgeAgent must stop at the gate and surface enough context for human review. Merge automation must remain disabled until approval is recorded. State persistence must represent approval and correction outcomes as first-class transitions. UX and APIs must support human intervention cleanly.

**Rejected alternatives:**  
- Fully autonomous merging after CI passes: rejected because the documented process requires an operator gate.  
- Informal review outside the pipeline state model: rejected because gate decisions must be checkpointed.  
- Sampling-based approval only for risky changes: rejected because no such exception is defined.

## All GitHub I/O must go through the GitHub tools boundary
**Status:** Accepted

**Context:** `src/github_tools.py` is identified as the module for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. This module is a control point for correctness and safety when interacting with GitHub.

**Decision:** Route all GitHub API reads and writes through `src/github_tools.py`. Enforce path validation, rate limiting, and SHA-based update protocol there, and do not duplicate GitHub write logic elsewhere.

**Consequences:** Direct ad hoc GitHub API calls from other modules are prohibited. API semantics such as optimistic concurrency and throttling are centralized. Testing of GitHub interactions can focus on one boundary. Feature work requiring GitHub operations must extend the boundary rather than bypass it.

**Rejected alternatives:**  
- Letting each subsystem call GitHub directly using its preferred client: rejected because it would bypass shared safety and consistency controls.  
- Centralizing only writes but not reads: rejected because rate limiting and protocol consistency apply to both directions.  
- Deferring SHA handling to callers: rejected because concurrency correctness belongs at the I/O boundary.

## Every write path must pass through the path security boundary
**Status:** Accepted

**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. This is a hard repository safety constraint.

**Decision:** Validate every filesystem write target through `src/path_security.py` before performing the write. Do not allow direct writes that bypass this boundary for convenience, tests, or performance.

**Consequences:** File creation and modification logic must be structured to consult path security first. Utility functions that write files must depend on the security boundary rather than reimplement checks. Tests must exercise both allowed and rejected path cases. Temporary exceptions and “internal-only” bypasses are not allowed.

**Rejected alternatives:**  
- Caller-side path validation in each module: rejected because it is error-prone and inconsistent.  
- Enforcing path security only for user-provided paths: rejected because generated paths can also become unsafe.  
- Allowing bypasses in test helpers: rejected because tests should verify real security behavior, not sidestep it.

## State transitions must be durable and auditable
**Status:** Accepted

**Context:** The pipeline documentation requires every state transition to be checkpointed. This implies durability across failures and an audit trail for branch and PR progression.

**Decision:** Persist every ForgeAgent state transition durably and record sufficient metadata to reconstruct execution history for a branch or PR.

**Consequences:** In-memory-only state is insufficient for authoritative workflow status. Restart and recovery behavior must consume persisted checkpoints. Audit and debugging tools can rely on transition history. Schema design must support per-PR transitions and gate outcomes explicitly.

**Rejected alternatives:**  
- Logging transitions without durable state storage: rejected because logs alone are not reliable workflow state.  
- Persisting only final outcomes: rejected because intermediate checkpoints are explicitly required.  
- Storing opaque serialized blobs with no transition semantics: rejected because auditability and recovery require structured states.

## Swift application shell changes must preserve the documented onboarding root-view routing
**Status:** Accepted

**Context:** TRD-1 defines a root view decision tree where `RootView` routes to onboarding flows until onboarding is complete. ForgeAgent operates in a repository that includes the `Crafted/` Swift application shell, so generated or modified Swift UI code must respect that routing model.

**Decision:** Preserve the documented `RootView` decision tree so that incomplete onboarding routes to `OnboardingContainerView` and its defined onboarding subviews, and only completed onboarding proceeds beyond that flow.

**Consequences:** SwiftUI changes in the application shell must not flatten or bypass onboarding state routing. UI generation and refactoring must respect onboarding state as a top-level navigation concern. Tests in `CraftedTests/` should verify routing behavior when onboarding state changes.

**Rejected alternatives:**  
- Replacing the state-driven root router with ad hoc navigation pushes: rejected because it obscures the documented application entry flow.  
- Allowing partial onboarding completion to bypass the container structure: rejected because it breaks the specified decision tree.  
- Treating onboarding routing as an implementation detail rather than an architectural constraint: rejected because it is explicitly documented in TRD-1.