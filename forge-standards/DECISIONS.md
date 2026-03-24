# DECISIONS.md

## [Use the documented monorepo layout as a hard architectural boundary]
**Status:** Accepted

**Context:** The ForgeAgent subsystem operates inside a repository with a prescribed structure. TRDs and PRDs live in `forge-docs/` and are the source of truth. Standards and architectural constraints live in `forge-standards/`. Backend implementation lives in `src/`, the macOS shell lives in `Crafted/`, Swift tests live in `CraftedTests/`, Python tests live in `tests/`, and failure classification is centralized in `FAILURE_TAXONOMY.md`. The subsystem must work predictably across build, review, and CI flows.

**Decision:** Treat the repository layout as fixed and normative. Implement ForgeAgent logic in `src/`. Read requirements from `forge-docs/` before changing behavior. Treat `forge-standards/` as controlling implementation constraints. Do not relocate, duplicate, or reinterpret these top-level responsibilities in code.

**Consequences:** Implementation must resolve inputs and outputs according to the existing directory contract. Features that need standards, requirements, or failure taxonomy must read them from their canonical locations rather than introducing parallel copies. Tooling and automation must assume this layout and fail clearly when it is violated.

**Rejected alternatives:**  
- Allowing ForgeAgent to infer repository structure dynamically from heuristics: rejected because it weakens determinism and increases the chance of reading or writing the wrong source of truth.  
- Duplicating TRD- or standards-derived data into `src/`: rejected because it creates drift against the canonical documents.  
- Treating repository layout as advisory rather than binding: rejected because orchestration, CI, and review behavior depend on stable paths.

## [Read critical files before modifying adjacent behavior]
**Status:** Accepted

**Context:** Several files are explicitly designated as critical because changes there have repository-wide impact: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. ForgeAgent changes in these areas can alter generation loops, pipeline orchestration, GitHub I/O, security boundaries, and CI generation.

**Decision:** Require any ForgeAgent change that affects generation, orchestration, GitHub interaction, path handling, or CI workflow generation to first consult the designated critical files and preserve their contracts. Treat these files as subsystem boundaries, not incidental implementation details.

**Consequences:** Refactors and feature additions must be evaluated for cross-cutting effects before changes are made. Code review should assume higher scrutiny for these files. New modules may not bypass behavior encapsulated by these critical files.

**Rejected alternatives:**  
- Allowing new functionality to reimplement similar logic outside the critical files: rejected because it fragments core behavior and breaks consistency.  
- Treating critical files as ordinary modules with no special review burden: rejected because the documented impact radius is too large.  
- Moving security- or GitHub-related logic opportunistically into feature modules: rejected because it erodes centralized control.

## [Centralize all GitHub I/O in `src/github_tools.py`]
**Status:** Accepted

**Context:** GitHub interaction is a sensitive integration surface. The documented contract states that `src/github_tools.py` owns all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. ForgeAgent depends on consistent GitHub behavior for branch, commit, PR, and repository operations.

**Decision:** Route all ForgeAgent GitHub reads and writes through `src/github_tools.py`. Do not perform direct GitHub API access from orchestration, consensus, fix-loop, or feature-specific modules.

**Consequences:** API semantics, retries, rate limiting, SHA handling, and repository safety checks remain centralized. Tests can mock a single boundary. Any new GitHub capability must be added to `src/github_tools.py` rather than embedded in callers.

**Rejected alternatives:**  
- Calling GitHub APIs directly from agent stages for convenience: rejected because it duplicates rate limiting, SHA handling, and validation logic.  
- Splitting GitHub responsibilities across multiple modules by feature area: rejected because it makes safety guarantees inconsistent.  
- Delegating path validation to callers while `github_tools.py` only performs transport: rejected because validation belongs at the I/O boundary.

## [Enforce `src/path_security.py` as the only write-path security boundary]
**Status:** Accepted

**Context:** The documented repository explicitly defines `src/path_security.py` as the security boundary and states that every write path must pass through it. ForgeAgent writes generated code, workflow files, and related artifacts; unchecked writes would create a direct repository safety risk.

**Decision:** Require every ForgeAgent filesystem write, file creation, overwrite, move, or delete operation to be validated through `src/path_security.py` before execution. Do not permit alternate path-validation implementations in stage-specific code.

**Consequences:** All write operations become auditable and consistently protected. Feature code must integrate with the security boundary instead of performing raw filesystem mutation. Any implementation shortcut that bypasses path validation is non-compliant.

**Rejected alternatives:**  
- Performing lightweight path checks inline in each module: rejected because it leads to inconsistent enforcement and security drift.  
- Restricting `path_security.py` usage to external inputs only: rejected because internal stage outputs can still produce unsafe writes.  
- Relying on repository-relative paths alone as sufficient safety: rejected because normalization and traversal risks still require centralized validation.

## [Implement the build pipeline as explicit staged orchestration]
**Status:** Accepted

**Context:** The documented build pipeline is stage-based, including generation validation steps such as `ast.parse`, `ruff`, import checks, a failure-type-aware fix loop with up to 20 pytest attempts, then Test + CI and an operator gate before merge. The pipeline is not ad hoc; it is a defined operational model.

**Decision:** Implement ForgeAgent orchestration as explicit, named pipeline stages matching the documented flow. Preserve stage ordering and semantics, including generation validation, iterative fixing, CI generation/execution handoff, and operator gating before merge.

**Consequences:** Pipeline behavior is inspectable, testable, and checkpointable. Features that need additional work must integrate into an existing stage or add a clearly bounded new stage without collapsing the stage model. Implicit or hidden transitions are disallowed.

**Rejected alternatives:**  
- Implementing the pipeline as a single monolithic loop: rejected because it obscures state, complicates recovery, and violates the documented staged flow.  
- Letting individual agents choose their own stage order dynamically: rejected because it breaks reproducibility and operator expectations.  
- Skipping validation stages when generation “looks correct”: rejected because the documented pipeline requires concrete syntax, lint, and import checks.

## [Cap cyclomatic complexity at 15 for every pipeline stage]
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is called out with this limit as strictly enforced. ForgeAgent is orchestration-heavy, so this constraint exists to preserve maintainability and reviewability.

**Decision:** Design each ForgeAgent pipeline stage and its controlling functions so that cyclomatic complexity does not exceed 15. When behavior grows, split it into subordinate helpers or strategy components rather than extending a stage past the limit.

**Consequences:** Stage implementations must remain decomposed and explicit. Complex branching, especially in orchestration and fix-loop logic, must be factored into smaller units. Reviews should treat complexity growth as a design problem, not a style issue.

**Rejected alternatives:**  
- Allowing occasional exceptions for orchestration code: rejected because the strict limit is explicitly documented.  
- Enforcing complexity only at file level rather than stage/function level: rejected because the requirement applies to every stage.  
- Deferring complexity control until after implementation: rejected because the architecture must be shaped around the limit from the start.

## [Checkpoint every state transition, including per-PR lifecycle transitions]
**Status:** Accepted

**Context:** The pipeline documentation requires that every state transition be checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. ForgeAgent must survive failures, support auditability, and allow operators to understand current state.

**Decision:** Persist a checkpoint record for every ForgeAgent state transition and every per-PR lifecycle transition. Do not combine multiple transitions into an unrecorded in-memory step. Make checkpointing part of the transition contract.

**Consequences:** Recovery and resumption can occur from known states. Operators and tooling gain traceability across the PR lifecycle. Stage implementations must emit durable state changes before proceeding to the next stage.

**Rejected alternatives:**  
- Checkpointing only major milestones: rejected because the requirement covers every state transition.  
- Keeping transition state only in memory until completion: rejected because it breaks recovery and auditability.  
- Logging transitions without durable checkpoint semantics: rejected because logs alone do not provide reliable resumable state.

## [Preserve the documented per-PR lifecycle as the canonical progression model]
**Status:** Accepted

**Context:** The repository documentation defines specific per-PR states: `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. ForgeAgent needs a canonical progression model so orchestration, UI, and operator actions refer to the same lifecycle.

**Decision:** Use the documented per-PR state sequence as the canonical ForgeAgent lifecycle model. Map all orchestration and status reporting onto these named states, and extend only when a new state is necessary and explicitly bounded.

**Consequences:** PR status is comparable across runs and components. UI and backend integrations can depend on a stable lifecycle vocabulary. Any new state must be inserted carefully to avoid ambiguity or overlapping semantics.

**Rejected alternatives:**  
- Representing lifecycle progress as free-form status text: rejected because it is not machine-safe or auditable.  
- Using only coarse statuses like “running” and “done”: rejected because they lose operational detail required by checkpoints and gates.  
- Letting each stage invent its own status names: rejected because it fragments reporting and recovery logic.

## [Use a failure-type-aware pytest fix loop with a hard limit of 20 attempts]
**Status:** Accepted

**Context:** The documented Stage 4e fix loop is failure-type-aware and runs pytest for up to 20 attempts. ForgeAgent must improve generated code iteratively while avoiding endless retries and must use error classification rather than blind repetition.

**Decision:** Implement the fix loop as bounded iterative repair driven by failure type, with a hard maximum of 20 pytest attempts. Stop when tests pass, the attempt limit is reached, or a non-recoverable failure condition is identified.

**Consequences:** The subsystem has deterministic retry bounds and can tailor repair strategies to failure classes. Fix-loop logic must classify failures and choose strategies accordingly rather than re-running the same generic prompt or patch blindly.

**Rejected alternatives:**  
- Retrying indefinitely until success: rejected because it risks runaway execution and contradicts the documented limit.  
- Using a fixed number of retries with no failure classification: rejected because the documented strategy is failure-type-aware.  
- Performing only one repair attempt after initial failure: rejected because the pipeline explicitly includes an iterative fix loop.

## [Generate CI workflows for both Ubuntu and macOS according to target technology]
**Status:** Accepted

**Context:** The build pipeline documentation specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. ForgeAgent spans Python backend and Swift/macOS application concerns, so CI generation must reflect the correct runtime environment.

**Decision:** Generate and maintain CI workflows that target Ubuntu for general crafted CI and macOS for Swift-related validation. Route workflow generation through the repository’s CI workflow boundary rather than embedding ad hoc YAML in feature code.

**Consequences:** Platform-appropriate CI remains explicit and reproducible. Python and Swift validation are not conflated into a single unsuitable environment. Changes to CI generation belong in the centralized workflow generator.

**Rejected alternatives:**  
- Running all CI only on Ubuntu: rejected because Swift/macOS validation requires macOS.  
- Running all CI only on macOS: rejected because it is unnecessary for non-Swift paths and increases cost and queue time.  
- Allowing features to emit bespoke workflow files independently: rejected because CI definition must stay centralized and governed.

## [Require an explicit operator gate before merge]
**Status:** Accepted

**Context:** The documented pipeline ends with a gate where the operator approves or corrects before merge. ForgeAgent is an autonomous subsystem, but the process explicitly retains human control at the final merge boundary.

**Decision:** Do not permit ForgeAgent to merge autonomously past the final gate. Require explicit operator approval or operator-provided correction before merge completion.

**Consequences:** Human oversight is preserved for repository changes. Automation may prepare branches, commits, tests, and CI outcomes, but final integration remains supervised. Merge workflows must expose enough context for the operator to make a decision.

**Rejected alternatives:**  
- Fully automatic merge after CI passes: rejected because it violates the documented operator gate.  
- Manual gating only for high-risk changes: rejected because the documented process applies the gate generally.  
- Treating silence or timeout as implicit approval: rejected because the gate requires an explicit decision.

## [Record every gate decision for auditability]
**Status:** Accepted

**Context:** The documentation states that every gate decision is recorded. Since the operator gate controls whether generated work proceeds to merge, ForgeAgent must preserve a durable record of approval, rejection, or correction.

**Decision:** Persist every ForgeAgent gate decision with enough metadata to reconstruct what was decided and at which pipeline point. Do not treat gate outcomes as ephemeral UI events or transient logs.

**Consequences:** Audit trails, postmortems, and compliance review become possible. Operator actions become part of the system of record. Gate-handling code must write durable decision records as part of normal flow.

**Rejected alternatives:**  
- Recording only approvals and ignoring rejections/corrections: rejected because all gate decisions matter operationally.  
- Keeping gate decisions only in application logs: rejected because logs are insufficient as the authoritative decision record.  
- Storing only the final merge result: rejected because it loses decision history and operator intervention context.

## [Keep ForgeAgent aligned with the macOS shell’s documented root-view flow]
**Status:** Accepted

**Context:** The repository includes a documented root view decision tree for the macOS application shell, with onboarding states determining which container or view is shown. ForgeAgent status and controls presented in the app must fit into this state-driven UI architecture rather than bypassing it.

**Decision:** Expose ForgeAgent-facing application behavior in a way that respects the documented state-driven root view decision tree. Do not introduce alternate top-level navigation or bypass onboarding-dependent routing for agent functionality.

**Consequences:** The backend and app shell remain consistent with the documented user flow. Agent-related UI must integrate into existing onboarding and authenticated states rather than creating parallel entry points. Backend status models should support the app’s state-driven presentation.

**Rejected alternatives:**  
- Adding a separate top-level ForgeAgent root outside the documented root view tree: rejected because it conflicts with the prescribed application shell flow.  
- Making agent screens always accessible regardless of onboarding state: rejected because onboarding state explicitly drives root presentation.  
- Letting backend implementation dictate new UI routing patterns ad hoc: rejected because UI architecture is already specified.