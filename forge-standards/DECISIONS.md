# DECISIONS.md

## FullPlatform repository structure is fixed and documentation-first
**Status:** Accepted  
**Context:** The subsystem operates within a repository where TRDs and PRDs are the source of truth, and implementation spans Python backend, Swift application shell, tests, and standards documents. Consistency of file placement is required so agents and developers can reliably locate architecture, runtime, and product constraints before making changes.  
**Decision:** Preserve the established top-level repository layout and treat `forge-docs/` as the authoritative source for product and technical requirements. Keep standards in `forge-standards/`, Python backend code in `src/`, macOS shell code in `Crafted/`, Swift tests in `CraftedTests/`, Python tests in `tests/`, and failure classification in `FAILURE_TAXONOMY.md`. Require implementers to read relevant TRDs and critical files before modifying subsystem behavior.  
**Consequences:** Implementation must not relocate core directories or duplicate source-of-truth documents elsewhere. Tooling, automation, and agent workflows must assume this layout. Cross-cutting changes must begin from documentation review, not code-first experimentation.  
**Rejected alternatives:**  
- Allowing teams to reorganize directories by subsystem ownership: rejected because it breaks agent assumptions and weakens discoverability of standards and requirements.  
- Treating code comments or inline docs as the primary source of truth: rejected because TRDs/PRDs are explicitly designated authoritative.  
- Merging Swift and Python implementations into a single app directory: rejected because platform boundaries and test/tooling needs are distinct.

## Critical orchestration and security files are protected change surfaces
**Status:** Accepted  
**Context:** Several files are identified as critical because they define the core generation loop, pipeline orchestration, GitHub I/O, write-path security boundary, and CI workflow generation. Uncontrolled modification of these files would create systemic risk across the FullPlatform subsystem.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as protected change surfaces. Require any implementation touching these files to preserve their designated responsibilities and evaluate impact across all dependent flows before modification. Route all write-path handling through `src/path_security.py`, all GitHub interactions through `src/github_tools.py`, and all CI workflow generation through `src/ci_workflow.py`.  
**Consequences:** Implementers may not bypass these modules with ad hoc logic elsewhere in the subsystem. Security, GitHub integration, orchestration, and CI behavior must remain centralized. Changes to protected files require broader regression validation because failures propagate platform-wide.  
**Rejected alternatives:**  
- Allowing feature teams to add direct filesystem writes in local modules: rejected because it undermines the security boundary.  
- Allowing direct GitHub API calls from arbitrary modules: rejected because rate limiting, path validation, and SHA protocol must remain centralized.  
- Splitting orchestration responsibilities across many lightweight modules without a governing director: rejected because the build pipeline already has explicit orchestration ownership.

## FullPlatform build execution shall follow the staged pipeline with checkpointed state transitions
**Status:** Accepted  
**Context:** The platform’s build pipeline is defined as a sequence of stages ending in test, CI, and an operator gate. The README also specifies that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. Reliable recovery, auditability, and deterministic progression depend on honoring this flow.  
**Decision:** Implement FullPlatform execution as an explicit staged pipeline with checkpointed transitions at every stage and sub-stage. Persist and recognize per-PR states including `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. Do not skip checkpoint creation or collapse multiple stage transitions into a single opaque step.  
**Consequences:** The subsystem must be resumable and auditable at stage boundaries. Recovery logic, operator visibility, and diagnostics must rely on persisted stage transitions. Pipeline code must expose state progression clearly enough for checkpointing and inspection.  
**Rejected alternatives:**  
- Running the pipeline as one monolithic job with only start/end status: rejected because it prevents recovery and obscures failures.  
- Checkpointing only external milestones such as commits and CI completion: rejected because internal build progression must also be recoverable.  
- Using inferred state from Git history alone: rejected because not all pipeline stages map cleanly to commits.

## Cyclomatic complexity per pipeline stage shall not exceed 15
**Status:** Accepted  
**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is explicitly noted as having a strictly enforced complexity limit. This constraint exists to keep orchestration understandable, testable, and safe to modify.  
**Decision:** Keep every FullPlatform pipeline stage at cyclomatic complexity 15 or below. Refactor branching logic into smaller helpers or stage-specific units rather than increasing complexity within a stage implementation. Enforce this limit as a design constraint, especially in orchestration code.  
**Consequences:** New features must fit within decomposed control flow rather than accumulating conditionals in central orchestrators. Reviewers should reject changes that increase stage complexity past the limit, even if behavior is functionally correct. This encourages smaller, testable stage components.  
**Rejected alternatives:**  
- Allowing exceptions for “core” orchestration paths: rejected because those are the highest-risk areas and most need the constraint.  
- Raising the limit to accommodate feature growth: rejected because it trades short-term convenience for long-term fragility.  
- Measuring complexity only at module level instead of per stage: rejected because the documented requirement is stage-specific.

## FullPlatform shall use failure-aware validation and bounded fix loops
**Status:** Accepted  
**Context:** The documented pipeline includes syntax and lint validation (`ast.parse → ruff → import check`) followed by a fix loop using `pytest` for up to 20 attempts with failure-type-aware strategy. This structure constrains how the platform identifies and remedies generated-code defects.  
**Decision:** Apply validation in the defined order: parse, lint, then import checks before entering test-driven repair. Limit automated fix attempts to 20 and select remediation behavior based on failure type rather than blind retries. Do not implement unbounded repair loops or reorder early validation steps.  
**Consequences:** The subsystem must classify failures sufficiently to support targeted repair behavior. Fast-fail validation must catch basic structural issues before expensive test execution. Repair workflows must terminate predictably instead of looping indefinitely.  
**Rejected alternatives:**  
- Running tests before syntax/lint/import validation: rejected because it wastes time on failures detectable earlier.  
- Using unlimited retries until success: rejected because it risks runaway execution and non-deterministic behavior.  
- Applying the same repair strategy to all failures: rejected because the documented approach is failure-type-aware.

## CI generation shall target both Linux and macOS according to workload
**Status:** Accepted  
**Context:** The build pipeline defines CI execution on `ubuntu-latest` through `crafted-ci.yml`, with `crafted-ci-macos.yml` used for Swift-related workflows. The FullPlatform subsystem spans Python backend and macOS Swift shell, so CI targeting must reflect platform-specific execution needs.  
**Decision:** Generate and maintain separate CI workflows for Linux and macOS responsibilities. Use `crafted-ci.yml` on `ubuntu-latest` for general backend and cross-platform validation, and use `crafted-ci-macos.yml` for Swift/macOS-specific validation. Do not collapse all CI onto a single runner class.  
**Consequences:** CI logic must remain platform-aware. Swift validation must assume macOS execution, while general backend checks should prefer Linux where appropriate. Workflow generation and gating must account for multiple CI results.  
**Rejected alternatives:**  
- Running all jobs only on Linux: rejected because Swift/macOS shell validation requires macOS support.  
- Running everything only on macOS: rejected because it increases cost and conflates platform-specific and general-purpose validation.  
- Generating CI workflows ad hoc per feature: rejected because the repository already defines named workflow artifacts and responsibilities.

## Operator approval is a mandatory gate before merge
**Status:** Accepted  
**Context:** The build pipeline includes a final gate where an operator approves or corrects before merge, and every gate decision is checkpointed. This establishes that autonomous progression is intentionally bounded by human review at merge time.  
**Decision:** Require explicit operator approval or operator correction before merge. Persist gate outcomes as checkpointed decisions and do not permit FullPlatform to auto-merge solely on the basis of generated code, passing tests, or passing CI.  
**Consequences:** The subsystem must expose enough information for operator review and must support paused execution awaiting a human decision. Merge automation must remain subordinate to the operator gate. Audit records must include the gate decision.  
**Rejected alternatives:**  
- Fully automatic merge after CI passes: rejected because the documented process requires operator approval.  
- Optional operator review only for high-risk changes: rejected because the gate is defined as a universal pipeline stage.  
- Recording gate outcomes only in logs: rejected because gate decisions must be checkpointed state.

## Root application routing in FullPlatform macOS shell shall follow onboarding-first branching
**Status:** Accepted  
**Context:** The macOS application shell defines a root view decision tree where `RootView` routes to `OnboardingContainerView` whenever onboarding is not complete, with subroutes for specific onboarding states such as welcome, API keys, and GitHub auth. The FullPlatform subsystem must respect this routing contract when integrating shell behavior.  
**Decision:** Implement root application routing so that incomplete onboarding always takes precedence over the main application experience. Route from `RootView` to `OnboardingContainerView` whenever onboarding state is not complete, and preserve explicit substate-driven onboarding views rather than replacing them with a single generic setup screen.  
**Consequences:** Application-shell changes must remain compatible with the onboarding state machine. Main platform functionality cannot assume availability before onboarding completion. UI integration work must preserve state-specific onboarding routes.  
**Rejected alternatives:**  
- Sending users directly to the main app and surfacing setup tasks later: rejected because the decision tree makes onboarding completion a root-level prerequisite.  
- Replacing multiple onboarding views with one combined form: rejected because the shell defines explicit state-based routing.  
- Letting backend readiness determine root routing independently of onboarding state: rejected because the root decision tree is driven by onboarding completion.