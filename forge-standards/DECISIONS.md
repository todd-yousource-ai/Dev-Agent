# DECISIONS.md

## Repository structure must preserve document-first governance
**Status:** Accepted  
**Context:** The subsystem is implemented in a repository where TRDs and PRDs in `forge-docs/` are the source of truth, and standards live in `forge-standards/`. The CraftedDevAgent must operate within this structure without relocating or redefining authority over requirements.  
**Decision:** Preserve the top-level repository layout and treat `forge-docs/` as authoritative input, `forge-standards/` as authoritative implementation constraints, `src/` as the Python backend for CraftedDevAgent, and `Crafted/` plus `CraftedTests/` as the macOS application shell and tests.  
**Consequences:** Implementation must read requirements from repository documents before making behavior changes. Code generation, orchestration, and review logic must not embed a parallel source of truth outside the documented repository structure. Automation must assume these paths are stable and must not reorganize them implicitly.  
**Rejected alternatives:**  
- Allowing the agent to infer requirements primarily from code: rejected because TRDs and PRDs are explicitly the source of truth.  
- Moving standards into `src/` for implementation convenience: rejected because it blurs governance and runtime concerns.  
- Supporting arbitrary repository layouts by default: rejected because the subsystem depends on known locations for requirements, standards, and critical files.

## Critical files must be treated as protected integration points
**Status:** Accepted  
**Context:** Several files are identified as high-impact: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes to these files can affect generation, orchestration, security, and CI behavior across all pull requests.  
**Decision:** Treat designated critical files as protected integration points and require any modification to preserve their subsystem contracts, cross-cutting responsibilities, and documented constraints.  
**Consequences:** Changes in these files must be narrowly scoped, strongly validated, and compatible with the rest of the pipeline. Refactors that redistribute their responsibilities must be avoided unless the documented contracts are updated first. New features should prefer extension around these files over uncontrolled edits within them.  
**Rejected alternatives:**  
- Treating all source files equally: rejected because these files form system-wide control and security boundaries.  
- Freely splitting critical logic across many modules: rejected because it weakens auditability and makes enforcement of pipeline and security constraints harder.  
- Locking these files completely against modification: rejected because the subsystem still needs controlled evolution.

## Build pipeline stages must remain explicit and sequential
**Status:** Accepted  
**Context:** The documented build pipeline defines named stages, including parse/lint/import validation, a failure-aware fix loop, CI execution, and an operator gate before merge. State transitions are checkpointed throughout the process.  
**Decision:** Implement CraftedDevAgent as an explicit staged pipeline with ordered transitions, including validation, fix-loop execution, CI, and final human gate, rather than as an opaque autonomous loop.  
**Consequences:** Orchestration code must model stages directly and expose state progression. The subsystem must be able to stop, resume, and audit execution at stage boundaries. Error handling must attach to a known stage instead of being buried in ad hoc control flow.  
**Rejected alternatives:**  
- A monolithic “generate until green” loop: rejected because it obscures failure modes and weakens checkpointing.  
- Parallel execution of all stages by default: rejected because several stages depend on validated outputs from earlier steps.  
- Skipping named stage representation in code while keeping it only in docs: rejected because checkpointing and auditing require first-class runtime states.

## Cyclomatic complexity per stage must not exceed 15
**Status:** Accepted  
**Context:** The build pipeline documentation explicitly constrains every stage to a maximum cyclomatic complexity of 15, and `src/build_director.py` is called out as enforcing this limit.  
**Decision:** Keep the implementation of each pipeline stage at or below cyclomatic complexity 15, and refactor orchestration logic into smaller units whenever a stage approaches the limit.  
**Consequences:** Stage handlers must remain composable and focused. Complex branching must be moved into helper strategies, classifiers, or policy objects rather than accumulated inside a single stage function. Reviews and tests must check complexity-sensitive hotspots, especially orchestration code.  
**Rejected alternatives:**  
- Enforcing complexity only at the file level: rejected because the documented constraint is per stage, not per file.  
- Allowing higher complexity in orchestration as a special case: rejected because orchestration is already identified as a critical risk area.  
- Treating the complexity limit as advisory only: rejected because the TRD language says it is strictly enforced.

## Every state transition must be checkpointed
**Status:** Accepted  
**Context:** The pipeline documentation requires checkpointing for every state transition, including per-PR states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. This is necessary for resumability, auditability, and operator oversight.  
**Decision:** Persist a checkpoint at every state transition in the CraftedDevAgent workflow, including all per-PR lifecycle states and major pipeline stage boundaries.  
**Consequences:** The subsystem must maintain durable state records suitable for restart and inspection. Transition logic must be explicit and idempotent enough to resume from saved checkpoints. Hidden in-memory-only transitions are not permitted for meaningful workflow progress.  
**Rejected alternatives:**  
- Checkpointing only terminal states: rejected because recovery from intermediate failures would be lost.  
- Checkpointing only after successful stages: rejected because partial progress and failure context must also be auditable.  
- Using log messages instead of durable checkpoints: rejected because logs do not provide structured resumable workflow state.

## Human approval is required before merge
**Status:** Accepted  
**Context:** The build pipeline includes a final gate where the operator approves or corrects before merge. This establishes a mandatory human control point for changes proposed by the agent.  
**Decision:** Require an explicit human approval gate before merge, and do not allow CraftedDevAgent to autonomously merge changes without operator action.  
**Consequences:** The subsystem may automate branch creation, code generation, testing, commits, and CI handling, but final merge remains a supervised action. UX and backend state models must preserve a pending-review state and support operator correction paths.  
**Rejected alternatives:**  
- Fully autonomous merge on green CI: rejected because it bypasses the documented gate decision.  
- Optional approval only for risky changes: rejected because the documented process requires a gate for all merges.  
- Post-merge human review: rejected because it does not satisfy the pre-merge control requirement.

## Validation must occur before fix-loop execution
**Status:** Accepted  
**Context:** The documented pipeline places syntax parsing, Ruff linting, and import checks before the fix loop, which then runs pytest with up to 20 attempts using failure-type-aware strategies.  
**Decision:** Run structural validation (`ast.parse`, Ruff, import checks) before entering the test-driven fix loop, and only invoke iterative repair after code is syntactically and structurally valid enough to test.  
**Consequences:** The fix loop can assume a minimum baseline of parseable, importable code and focus on behavioral repair. Early-stage failures can be classified separately from test failures, improving repair strategy selection and reducing wasted attempts.  
**Rejected alternatives:**  
- Running pytest first and letting failures drive all repair: rejected because syntax and import failures are cheaper and clearer to detect upfront.  
- Interleaving lint and tests arbitrarily: rejected because it makes stage semantics unclear and weakens failure categorization.  
- Skipping import checks when syntax passes: rejected because import breakage is a distinct and common failure mode.

## The fix loop must be bounded and failure-type-aware
**Status:** Accepted  
**Context:** The pipeline specifies a pytest-based fix loop with up to 20 attempts and a strategy informed by failure type. This prevents unbounded churn and aligns repairs to the observed failure class.  
**Decision:** Limit automated test-repair iterations to 20 attempts per run and select repair behavior based on classified failure type rather than using a single generic retry strategy.  
**Consequences:** The subsystem must classify failures and track attempt counts durably. Repair logic must stop at the configured bound and surface unresolved issues for operator review or later intervention. Infinite retry loops and unclassified “try again” behavior are disallowed.  
**Rejected alternatives:**  
- Unlimited retries until tests pass: rejected because it risks runaway execution and hidden instability.  
- A fixed small retry count such as 3 or 5: rejected because the documented pipeline explicitly allows up to 20 attempts.  
- A generic retry loop without failure categorization: rejected because the design requires failure-type-aware strategies.

## GitHub interactions must be centralized in `src/github_tools.py`
**Status:** Accepted  
**Context:** `src/github_tools.py` is identified as the integration point for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. This file is a control boundary for external repository mutation and API interaction.  
**Decision:** Route all GitHub API and repository I/O through `src/github_tools.py`, and do not implement ad hoc GitHub access paths elsewhere in the subsystem.  
**Consequences:** Branch operations, file updates, PR interactions, SHA-sensitive writes, and rate-limited API usage must share one consistent implementation surface. Security and correctness fixes in GitHub handling can then be applied centrally.  
**Rejected alternatives:**  
- Allowing each feature module to call GitHub APIs directly: rejected because it duplicates protocol logic and weakens enforcement of rate limiting and SHA handling.  
- Splitting write and read logic across unrelated modules: rejected because path validation and mutation safety depend on a coherent boundary.  
- Wrapping third-party GitHub clients directly inside business logic: rejected because it bypasses repository-specific safeguards.

## All write paths must pass through `src/path_security.py`
**Status:** Accepted  
**Context:** `src/path_security.py` is designated as the security boundary, and every write path is required to pass through it. This controls filesystem safety and prevents unauthorized path traversal or writes outside approved targets.  
**Decision:** Enforce `src/path_security.py` as the mandatory gateway for all filesystem write path validation, with no exceptions for convenience, tests, or internal tooling.  
**Consequences:** Any code that writes files must validate destination paths through the shared security layer first. New write-capable utilities must depend on this module rather than reimplementing path checks. This may add friction to small features, but it preserves the security boundary.  
**Rejected alternatives:**  
- Performing local path validation inside each writer: rejected because duplicated checks drift and are harder to audit.  
- Allowing direct writes in trusted internal modules: rejected because “trusted” exceptions erode the boundary over time.  
- Restricting path security only to GitHub-originated writes: rejected because local and generated writes can be equally dangerous.

## CI workflow generation must remain a dedicated responsibility
**Status:** Accepted  
**Context:** `src/ci_workflow.py` is identified as the generator for CI workflows, including Linux CI and a macOS-specific workflow for Swift. The repository contains both Python backend and Swift application code, requiring distinct CI treatment.  
**Decision:** Keep CI workflow generation centralized in `src/ci_workflow.py`, and generate separate workflows appropriate to the technology stack, including `ubuntu-latest` for backend validation and a macOS workflow for Swift-related work.  
**Consequences:** The subsystem must preserve platform-aware CI generation and avoid scattering workflow templates across unrelated modules. Changes to CI policy should be made in one place and applied consistently. Python-only assumptions must not erase macOS-specific workflow needs.  
**Rejected alternatives:**  
- Maintaining a single universal workflow for all stacks: rejected because Swift/macOS requirements differ from Python backend execution.  
- Hardcoding CI YAML in multiple features: rejected because it fragments ownership and increases drift.  
- Treating CI workflow generation as an external manual step: rejected because CI is an explicit stage in the documented automated pipeline.

## The macOS shell must respect the documented onboarding-first root view tree
**Status:** Accepted  
**Context:** The application shell documentation defines a root view decision tree where incomplete onboarding routes users into `OnboardingContainerView` and its state-specific screens before normal operation. CraftedDevAgent must integrate with, not override, this app-shell flow.  
**Decision:** Preserve the documented root view decision tree in the SwiftUI shell, and gate normal agent-facing functionality behind completion of onboarding states.  
**Consequences:** Backend and UI integration must support onboarding state as a first-class prerequisite. Features requiring API keys, GitHub authentication, or related setup must not assume immediate availability before onboarding is complete. Root navigation must remain state-driven rather than shortcut-driven.  
**Rejected alternatives:**  
- Letting the app drop directly into the main agent interface on launch: rejected because it bypasses required setup flow.  
- Handling onboarding as modal overlays on top of the main app: rejected because the documented architecture defines onboarding as a root-level branch.  
- Moving onboarding requirements entirely to backend validation: rejected because the shell’s navigation contract is explicitly documented.