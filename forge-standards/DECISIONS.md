# DECISIONS.md

## Repository documentation is the source of truth
**Status:** Accepted  
**Context:** The subsystem operates in a repository where requirements and architecture are defined in TRDs and standards documents under `forge-docs/` and `forge-standards/`. Implementation without consulting these documents risks divergence from the intended platform behavior and constraints.  
**Decision:** Read and align all CraftedDevAgent implementation work to `forge-docs/` and `forge-standards/` before modifying code; treat these documents as authoritative over inferred behavior.  
**Consequences:** Implementation must be traceable to documented requirements. Changes that conflict with TRDs, PRDs, or standards must be resolved in documentation first or explicitly escalated. Ad hoc architectural drift is disallowed.  
**Rejected alternatives:**  
- Implement from code inspection alone — rejected because code may be incomplete, outdated, or not reflect intended system behavior.  
- Treat README files as sufficient authority — rejected because README content is informative but not the full source of requirements.  
- Allow subsystem-local conventions to override repository standards — rejected because this would fragment behavior across agents and pipelines.

## Critical files require heightened change discipline
**Status:** Accepted  
**Context:** Several files are designated as critical because they define core generation, orchestration, GitHub I/O, path security, and CI workflow behavior. Changes in these files have system-wide impact.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as protected high-impact surfaces; review their documented role before modifying and minimize changes within them.  
**Consequences:** Work touching these files must preserve existing invariants and avoid incidental refactors. Security, orchestration, and GitHub integration behavior cannot be changed casually. Testing depth must increase when these files are touched.  
**Rejected alternatives:**  
- Treat all source files uniformly — rejected because impact and risk are not uniform.  
- Freely refactor critical files during feature work — rejected because broad refactors increase regression risk in the core pipeline.  
- Duplicate critical logic elsewhere to avoid touching these files — rejected because it would create drift and hidden behavior forks.

## Enforce staged pipeline execution
**Status:** Accepted  
**Context:** The build pipeline is explicitly defined as staged, including syntax and lint checks, import validation, iterative fix loops, CI execution, and operator gating. Predictability depends on preserving stage boundaries.  
**Decision:** Implement CraftedDevAgent work as a staged pipeline with explicit progression through generation, validation, fix, test, CI, and gate phases; do not collapse or bypass stages.  
**Consequences:** Logic must preserve ordered execution and stage-specific responsibilities. Debugging, recovery, and observability depend on stage boundaries remaining intact. Shortcut paths that skip validation or gating are not allowed.  
**Rejected alternatives:**  
- Use a monolithic end-to-end execution path — rejected because it reduces traceability and makes failures harder to classify and recover from.  
- Permit dynamic stage skipping based on heuristic confidence — rejected because deterministic validation is required.  
- Merge local test and CI stages into a single step — rejected because local correctness and remote environment validation serve different purposes.

## Keep cyclomatic complexity at or below 15 per stage
**Status:** Accepted  
**Context:** The repository defines a strict complexity cap of 15 for every stage, and `src/build_director.py` is specifically called out as enforcing this constraint. This is an implementation governance rule, not a suggestion.  
**Decision:** Design each pipeline stage and orchestration unit so its cyclomatic complexity does not exceed 15; split logic into subordinate functions rather than exceed the limit.  
**Consequences:** Stage logic must remain modular and reviewable. Large conditional dispatch and deeply nested recovery paths must be decomposed. Complexity-driven decomposition becomes a hard design constraint on CraftedDevAgent internals.  
**Rejected alternatives:**  
- Exceed the limit when justified by performance or convenience — rejected because the cap is explicitly strict.  
- Enforce complexity only at file level — rejected because the requirement applies per stage.  
- Hide complexity inside large helper chains without clear stage ownership — rejected because it undermines maintainability and traceability.

## Checkpoint every state transition
**Status:** Accepted  
**Context:** The pipeline requires checkpointing at every state transition, including per-PR states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. Recovery and auditability depend on durable state.  
**Decision:** Persist a checkpoint for every pipeline and per-PR state transition; do not advance state without recording it.  
**Consequences:** State management must be explicit, durable, and reconstructable. Retry and resume behavior must operate from checkpoints rather than implicit in-memory assumptions. Missing checkpoints are treated as correctness defects.  
**Rejected alternatives:**  
- Checkpoint only major milestones — rejected because the documented requirement covers every transition.  
- Use in-memory state only during a run — rejected because crashes and restarts would lose execution history.  
- Record only human-readable logs instead of structured checkpoints — rejected because logs are insufficient for deterministic resume and state auditing.

## Preserve the per-PR state machine
**Status:** Accepted  
**Context:** The repository defines a specific per-PR lifecycle: `branch_opened → code_generated → tests_passed → committed → ci_passed`. This sequence governs delivery semantics and external integration behavior.  
**Decision:** Model PR work using the documented ordered state machine and prohibit out-of-order transitions.  
**Consequences:** The subsystem must validate legal transitions and reject invalid jumps, such as committing before tests pass or marking CI passed before commit creation. Reporting and recovery logic must align to this lifecycle.  
**Rejected alternatives:**  
- Use a looser event-based model with inferred status — rejected because deterministic stage tracking is required.  
- Allow state skipping for trivial changes — rejected because all PRs must follow the same observable lifecycle.  
- Infer state from GitHub alone — rejected because internal generation and test states occur before or outside remote visibility.

## Treat operator approval as a mandatory merge gate
**Status:** Accepted  
**Context:** The build pipeline includes an explicit gate where the operator approves or corrects before merge, and every gate decision is recorded. Human oversight is therefore a required control point.  
**Decision:** Require explicit operator approval or correction before merge; do not permit autonomous merge by CraftedDevAgent.  
**Consequences:** The subsystem must stop at the gate pending human input and must record the gate outcome. Full automation ends before merge completion. UX and orchestration must support a paused, reviewable state.  
**Rejected alternatives:**  
- Auto-merge after passing tests and CI — rejected because it removes the mandated human gate.  
- Make operator review optional for low-risk changes — rejected because no such exception is defined.  
- Treat silence or timeout as approval — rejected because approval must be explicit and auditable.

## Record every gate decision
**Status:** Accepted  
**Context:** The pipeline documentation requires every gate decision to be recorded. This supports auditability, accountability, and postmortem analysis.  
**Decision:** Persist gate decisions as explicit structured records, including approval and correction outcomes.  
**Consequences:** The subsystem must provide durable audit records for review actions. Merge eligibility, rollback analysis, and compliance reporting depend on these records being complete and queryable.  
**Rejected alternatives:**  
- Store gate decisions only in ephemeral UI state — rejected because decisions must survive restarts and be auditable.  
- Rely on GitHub review comments as the only record — rejected because the gate is an internal pipeline concept, not solely a GitHub artifact.  
- Record approvals but not corrections — rejected because both outcomes affect execution history and recovery.

## Route all write paths through the path security boundary
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. This is a core enforcement point for filesystem safety.  
**Decision:** Validate every filesystem write through `src/path_security.py`; do not perform direct writes that bypass this boundary.  
**Consequences:** All file creation, update, and generated-output paths must be funneled through centralized validation. New code that writes files must integrate with existing path security mechanisms rather than introducing independent checks.  
**Rejected alternatives:**  
- Validate only user-supplied paths — rejected because generated and derived paths are also part of the write attack surface.  
- Perform ad hoc validation in each module — rejected because distributed validation leads to inconsistent enforcement.  
- Trust repository-relative paths without validation — rejected because relative paths can still be unsafe or manipulated.

## Centralize all GitHub I/O in github_tools
**Status:** Accepted  
**Context:** `src/github_tools.py` owns GitHub I/O, including path validation, rate limiting, and SHA protocol handling. Fragmenting GitHub access would bypass repository safeguards.  
**Decision:** Perform all GitHub reads and writes through `src/github_tools.py`; do not introduce direct GitHub API calls elsewhere in the subsystem.  
**Consequences:** Rate limiting, SHA correctness, and path safety remain consistently enforced. Any new GitHub interaction must be added to the centralized tooling layer rather than implemented inline.  
**Rejected alternatives:**  
- Call the GitHub API directly from feature modules — rejected because it would bypass shared safeguards and duplicate protocol logic.  
- Split read and write responsibilities across multiple modules — rejected because the repository already defines a single integration boundary.  
- Use shell-based GitHub CLI calls opportunistically — rejected because they are harder to validate, test, and rate-limit consistently.

## Preserve the core generation loop in consensus
**Status:** Accepted  
**Context:** `src/consensus.py` is identified as the core generation loop affecting every PR the agent builds. Behavior changes here propagate globally.  
**Decision:** Keep generation-loop logic centralized in `src/consensus.py` and modify it only when the change is required across all PR generation flows.  
**Consequences:** Feature-specific generation behavior should prefer extension points or parameterization over branching the core loop. Changes to consensus behavior require broad validation because they affect all outputs.  
**Rejected alternatives:**  
- Reimplement generation loops in task-specific modules — rejected because it creates divergent PR generation behavior.  
- Patch behavior downstream after generation instead of preserving a coherent loop — rejected because it hides errors and weakens system predictability.  
- Move orchestration into multiple agent-specific flows — rejected because the repository identifies a single core generation loop.

## Use failure-type-aware fix loops with a maximum of 20 pytest attempts
**Status:** Accepted  
**Context:** The build pipeline specifies a fix loop that runs pytest with failure-type-aware strategy and a maximum of 20 attempts. This creates a bounded iterative repair process.  
**Decision:** Implement test-fix iteration as failure-classified retries capped at 20 pytest attempts; stop once the cap is reached or tests pass.  
**Consequences:** Retry behavior must be finite and informed by failure taxonomy rather than blind repetition. The subsystem must surface exhaustion clearly when the attempt limit is hit. Infinite or open-ended repair loops are prohibited.  
**Rejected alternatives:**  
- Retry until success with no cap — rejected because it risks non-terminating execution.  
- Use a fixed retry strategy regardless of failure type — rejected because the pipeline requires failure-aware handling.  
- Allow fewer or more attempts based on local heuristics — rejected because the documented cap is explicit.

## Distinguish local test validation from CI validation
**Status:** Accepted  
**Context:** The pipeline defines Stage 5 CI workflows separately, including `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. Local test passes are not equivalent to CI passes.  
**Decision:** Treat local test success and CI success as distinct required validations; do not substitute one for the other.  
**Consequences:** State transitions, reporting, and gating must separately represent local tests and remote CI outcomes. Swift-related work must account for macOS CI, while broader checks run on Ubuntu as defined.  
**Rejected alternatives:**  
- Consider local pytest success sufficient for merge readiness — rejected because CI is explicitly required.  
- Run only one CI workflow for all changes — rejected because the repository defines platform-specific workflows.  
- Collapse CI results into the generic test state — rejected because `tests_passed` and `ci_passed` are separate lifecycle states.

## Respect the documented repository layout
**Status:** Accepted  
**Context:** The repository layout assigns specific responsibilities to `forge-docs/`, `forge-standards/`, `src/`, `Crafted/`, `CraftedTests/`, `tests/`, and `FAILURE_TAXONOMY.md`. CraftedDevAgent must work within this structure.  
**Decision:** Place implementation, tests, app shell code, and standards updates only in their documented repository locations; do not create parallel structures that duplicate existing responsibilities.  
**Consequences:** Python backend changes belong in `src/` with pytest coverage in `tests/`. Swift/SwiftUI shell changes belong in `Crafted/` with XCTest coverage in `CraftedTests/`. Failure handling logic must reference the shared taxonomy rather than inventing independent categories.  
**Rejected alternatives:**  
- Create subsystem-specific top-level directories for convenience — rejected because it fragments repository organization.  
- Store generated standards or design notes alongside implementation code — rejected because `forge-standards/` and `forge-docs/` already define canonical locations.  
- Embed failure categories directly in code without reference to `FAILURE_TAXONOMY.md` — rejected because it would drift from the shared taxonomy.

## Follow the RootView onboarding decision tree for macOS shell integration
**Status:** Accepted  
**Context:** The macOS application shell defines a RootView decision tree keyed on onboarding state, including onboarding-specific screens before the main application flow. CraftedDevAgent integration in the shell must not violate this navigation contract.  
**Decision:** Integrate any CraftedDevAgent macOS shell entry points under the documented RootView onboarding flow and do not bypass onboarding completion checks.  
**Consequences:** Agent-related UI cannot appear as the default root experience for users who have not completed onboarding. Navigation, state restoration, and shell integration must respect onboarding state as the primary routing condition.  
**Rejected alternatives:**  
- Launch directly into agent functionality regardless of onboarding state — rejected because it contradicts the documented RootView routing.  
- Add a parallel root coordinator outside RootView — rejected because it would fork application navigation semantics.  
- Defer onboarding enforcement to individual screens — rejected because the decision tree establishes root-level control.