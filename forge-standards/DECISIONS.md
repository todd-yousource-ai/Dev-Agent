# DECISIONS.md

## Repository layout is a hard contract
**Status:** Accepted  
**Context:** The FullPlatform subsystem spans documentation, backend runtime, CI generation, and the macOS application shell. The TRDs define a fixed repository structure and identify source-of-truth locations for standards, implementation, and product documents. Drift in layout would break agent assumptions, file discovery, and automation.  
**Decision:** Preserve the repository layout exactly as defined: `forge-docs/` for TRDs and PRDs, `forge-standards/` for architecture and conventions, `src/` for Python backend code, `Crafted/` for the Swift/SwiftUI shell, `CraftedTests/` for XCTest, `tests/` for pytest, and root-level operational documents such as `FAILURE_TAXONOMY.md`. Treat `forge-docs/` as required pre-implementation input and `forge-standards/` as implementation constraints.  
**Consequences:** Implementations must not relocate subsystem boundaries, duplicate standards into code directories, or invent alternate source-of-truth paths. Build tooling, agent workflows, and documentation readers must resolve files from these fixed locations. New FullPlatform features must fit within this structure rather than redefining it.  
**Rejected alternatives:**  
- Allowing teams to reorganize directories by feature area: rejected because agent workflows and TRD references assume stable paths.  
- Co-locating docs with implementation folders: rejected because the standards/docs split is explicit and supports governance.  
- Treating repository structure as advisory: rejected because path-sensitive tooling and security checks depend on consistency.

## Critical files require constrained modification
**Status:** Accepted  
**Context:** Several files are explicitly identified as high-impact control points: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes to these files affect generation, orchestration, GitHub I/O, security boundaries, and CI synthesis across the FullPlatform subsystem.  
**Decision:** Treat the listed critical files as controlled interfaces. Modify them only when the change is necessary for subsystem behavior, keep responsibilities aligned with their documented purpose, and do not bypass them with parallel implementations. In particular, all GitHub I/O must remain centralized in `src/github_tools.py`, all write-path validation must continue through `src/path_security.py`, and pipeline orchestration must continue through `src/build_director.py`.  
**Consequences:** New code must integrate with, not route around, these files. Security, GitHub access, and orchestration logic must not be duplicated elsewhere. Reviews for these files must assume subsystem-wide blast radius. Refactors must preserve their role as chokepoints.  
**Rejected alternatives:**  
- Splitting equivalent logic into multiple helper modules without a single chokepoint: rejected because it weakens auditability and enforcement.  
- Directly performing GitHub operations from feature modules: rejected because it bypasses path validation, rate limiting, and SHA protocol controls.  
- Writing files without `src/path_security.py`: rejected because it violates the defined security boundary.

## Pipeline stages and transitions must remain explicit and checkpointed
**Status:** Accepted  
**Context:** The build pipeline is defined as a staged process with explicit transitions and checkpoints, including per-PR states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. The system depends on resumability, traceability, and operator visibility across long-running automation.  
**Decision:** Implement and preserve the pipeline as explicit stages with durable checkpointed state transitions. Record every transition, including per-PR stage progression, and require downstream actions to read prior checkpoint state rather than infer progress implicitly.  
**Consequences:** Stateless or ad hoc orchestration is disallowed. Recovery, retry, and audit flows must use persisted checkpoints. New stages or transition names must be added deliberately and integrated into the state model rather than hidden in logs or temporary memory.  
**Rejected alternatives:**  
- Using only in-memory orchestration state: rejected because it breaks resumability and observability.  
- Checkpointing only major milestones: rejected because the TRD requires every state transition to be checkpointed.  
- Inferring state from Git history or CI status alone: rejected because those sources are incomplete for internal generation stages.

## Cyclomatic complexity per stage is capped at 15
**Status:** Accepted  
**Context:** The build pipeline explicitly requires every stage to maintain a maximum cyclomatic complexity of 15. This is a design constraint intended to keep orchestration understandable, testable, and reviewable.  
**Decision:** Enforce a hard maximum cyclomatic complexity of 15 for every pipeline stage implementation, especially within orchestration code such as `src/build_director.py`. Decompose behavior into helper functions or smaller stage units rather than exceeding the cap.  
**Consequences:** Stage implementations must be factored for clarity, and feature additions that would push a stage past the limit must be split structurally. Review and tooling must treat complexity growth as a design failure, not a cleanup task for later.  
**Rejected alternatives:**  
- Allowing exceptions for “core orchestration” files: rejected because `src/build_director.py` is explicitly called out as constrained.  
- Measuring complexity only at module level: rejected because the requirement applies per stage.  
- Deferring complexity cleanup until after feature delivery: rejected because the limit is preventive, not aspirational.

## Static validation and fix loop are mandatory pipeline behaviors
**Status:** Accepted  
**Context:** The pipeline definition includes static validation steps (`ast.parse`, `ruff`, import check) followed by a fix loop using `pytest` with up to 20 attempts and failure-type-aware strategy. These are not optional optimizations; they are part of the expected generation lifecycle.  
**Decision:** Run static validation before test-driven repair, and implement the fix loop with a maximum of 20 pytest-based attempts using failure-type-aware remediation. Do not skip static checks, collapse them into a single opaque command, or run unbounded retries.  
**Consequences:** Generated changes must pass syntax, lint, and import validation before entering iterative repair. Retry logic must be bounded and classified by failure type. The subsystem must expose failure when the retry budget is exhausted rather than looping indefinitely.  
**Rejected alternatives:**  
- Running tests before static validation: rejected because cheaper deterministic failures should be caught first.  
- Using unlimited repair retries: rejected because it hides non-converging failures and wastes resources.  
- Treating all test failures identically: rejected because the pipeline specifies failure-type-aware strategy.

## CI generation must target both Linux and macOS execution contexts
**Status:** Accepted  
**Context:** The repository uses distinct generated workflows: `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift/macOS concerns. The FullPlatform subsystem spans Python backend and Swift shell components, so CI must reflect both environments.  
**Decision:** Generate and maintain separate CI workflows for Linux and macOS responsibilities. Use Ubuntu for general backend validation and a dedicated macOS workflow for Swift or platform-specific validation. Do not collapse all checks into a single runner type.  
**Consequences:** CI logic must remain environment-aware. Swift and macOS application shell changes must be validated in macOS CI, while backend checks continue to run in Ubuntu where appropriate. Workflow generation in `src/ci_workflow.py` must preserve this split.  
**Rejected alternatives:**  
- Running everything on Ubuntu only: rejected because Swift/macOS validation requires macOS-specific execution.  
- Running everything on macOS only: rejected because it is costlier and unnecessary for all backend checks.  
- Maintaining one monolithic workflow file with conditional branching: rejected because the defined output names and responsibilities are already split.

## Operator gate is required before merge
**Status:** Accepted  
**Context:** The pipeline includes a gate where the operator approves or corrects before merge. The FullPlatform subsystem combines autonomous generation with human oversight, and gate decisions are part of the controlled flow.  
**Decision:** Require an explicit operator approval or correction step before merge. Treat the gate as a first-class state in the pipeline and record the decision rather than assuming CI success is sufficient for merge authority.  
**Consequences:** Fully automatic merge-on-green is not permitted for this subsystem. Tooling must support pause, review, correction, and resume behavior. Audit trails must include gate outcomes as part of the checkpointed state model.  
**Rejected alternatives:**  
- Auto-merging after CI passes: rejected because the pipeline explicitly requires operator approval or correction.  
- Informal manual review outside the pipeline state model: rejected because gate decisions must be trackable.  
- Optional gating only for risky changes: rejected because the stage is defined as part of the standard flow.

## Path security is the mandatory write boundary
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. For the FullPlatform subsystem, generated code, workflow files, and document updates create broad write surfaces that must be constrained.  
**Decision:** Route every filesystem write through the path security boundary in `src/path_security.py`. Forbid direct writes that bypass validation, normalization, or repository-boundary checks.  
**Consequences:** Any feature that emits files must integrate with the existing path security API. Utility shortcuts such as direct `open(..., "w")` in feature modules are not acceptable unless wrapped by the security boundary. Security review can assume a single enforcement point for write-path controls.  
**Rejected alternatives:**  
- Allowing trusted modules to bypass path security: rejected because trust-based exceptions erode the boundary.  
- Validating only external user-supplied paths: rejected because internal generation can also produce unsafe paths.  
- Relying on code review instead of technical enforcement: rejected because the file is defined as the enforcement boundary.

## GitHub interactions must be centralized and protocol-aware
**Status:** Accepted  
**Context:** `src/github_tools.py` owns all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. The FullPlatform subsystem depends on deterministic repository interaction and must avoid inconsistent GitHub semantics across modules.  
**Decision:** Centralize all GitHub reads and writes in `src/github_tools.py` and preserve enforcement of path validation, rate limiting, and SHA-aware update protocols. Do not implement direct GitHub API calls elsewhere in the subsystem.  
**Consequences:** Feature modules must call shared GitHub utilities rather than embedding API clients. Retry behavior, content updates, and concurrency semantics remain consistent across the platform. Security and correctness fixes in GitHub handling can be made once at the chokepoint.  
**Rejected alternatives:**  
- Per-feature GitHub clients: rejected because they duplicate protocol handling and invite inconsistency.  
- Using git CLI for some operations and API calls for others without central mediation: rejected because it fragments behavior and auditability.  
- Ignoring SHA protocol on updates: rejected because it risks overwrites and race conditions.

## The macOS shell must preserve the root view decision tree
**Status:** Accepted  
**Context:** TRD-1 defines a root view decision tree in which onboarding state controls whether the user sees onboarding flows or the main application hierarchy. This is a foundational navigation contract for the FullPlatform user-facing shell.  
**Decision:** Preserve onboarding-driven root navigation as the top-level routing rule in the SwiftUI shell. `RootView` must branch first on onboarding completion state and present the onboarding container when onboarding is incomplete. New top-level UI states must extend this decision model rather than bypass it.  
**Consequences:** Features cannot attach themselves as alternate root flows that skip onboarding prerequisites. Authentication, API key collection, GitHub authorization, and related setup states must remain upstream of the main application experience. UI refactors must keep root-state logic explicit.  
**Rejected alternatives:**  
- Allowing feature modules to present independently at app launch: rejected because it undermines onboarding completeness guarantees.  
- Replacing state-driven root routing with ad hoc modal presentation: rejected because it weakens determinism and testability.  
- Treating onboarding as optional decoration: rejected because TRD-1 defines it as the initial decision boundary.