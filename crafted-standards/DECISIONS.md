## [Treat `forge-docs/` as the authoritative design input]
**Status:** Accepted  
**Context:** CraftedApp implementation is constrained by TRDs and PRDs stored under `forge-docs/`. The repository structure explicitly identifies this directory as the source of truth and requires it to be read before building.  
**Decision:** Read and conform to the relevant documents in `forge-docs/` before changing CraftedApp behavior, interfaces, workflows, or repository structure. Treat `forge-docs/` as authoritative over inferred behavior from partial code inspection.  
**Consequences:** Implementation work in CraftedApp must be traceable to documented requirements. Changes that conflict with TRDs must be rejected or preceded by document updates. Ad hoc implementation based only on current code is not permitted when it diverges from documented design.  
**Rejected alternatives:**  
- **Treat source code as the only source of truth:** Rejected because the repository explicitly defines TRDs/PRDs as the governing design inputs.  
- **Use README summaries without consulting TRDs:** Rejected because summaries omit subsystem-specific constraints and edge cases.  
- **Allow undocumented behavior changes for speed:** Rejected because it breaks design traceability and increases drift from intended architecture.

## [Preserve the documented repository layout]
**Status:** Accepted  
**Context:** The repository layout is explicitly defined, including `forge-docs/` for requirements and `forge-standards/` for governing standards such as `DECISIONS.md`. CraftedApp must fit within this structure rather than inventing local conventions.  
**Decision:** Keep CraftedApp files and documentation within the documented repository layout and place design-governing artifacts in `forge-standards/` when they are cross-cutting standards. Do not relocate or duplicate authoritative documents into subsystem-specific ad hoc locations.  
**Consequences:** CraftedApp implementation must align with the existing repository contract, reducing ambiguity for agents and operators. New files must respect the established top-level structure. Documentation sprawl and shadow standards are disallowed.  
**Rejected alternatives:**  
- **Create a CraftedApp-local standards directory:** Rejected because it fragments governance and conflicts with the defined role of `forge-standards/`.  
- **Embed design decisions only in code comments:** Rejected because architecture decisions must be discoverable and durable outside implementation files.  
- **Reorganize top-level directories for subsystem convenience:** Rejected because it would break repository-wide conventions and tooling expectations.

## [Honor critical-file boundaries when modifying CraftedApp-adjacent flows]
**Status:** Accepted  
**Context:** Several files are identified as critical because they define core generation, orchestration, GitHub I/O, path security, and CI workflow generation. Changes in these files have system-wide effects beyond any single subsystem.  
**Decision:** Treat modifications to `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as architectural changes requiring explicit review against their stated responsibilities before implementing CraftedApp behavior that depends on them.  
**Consequences:** CraftedApp must prefer extension through existing interfaces over casual edits to critical infrastructure. Any required changes in these files must be narrowly scoped and justified by subsystem needs. This constrains local implementation shortcuts that would alter global behavior.  
**Rejected alternatives:**  
- **Modify critical files freely when tests pass:** Rejected because their impact extends beyond local test coverage.  
- **Duplicate logic in CraftedApp to avoid touching critical files:** Rejected because it creates divergence in security, orchestration, and GitHub behavior.  
- **Bypass critical-file review for small changes:** Rejected because small changes in these files can have broad architectural consequences.

## [Enforce the root-directory allowlist for all repository writes]
**Status:** Accepted  
**Context:** GitHub integration lessons learned specify that writes outside explicitly allowed roots fail silently or are blocked by path security. Standard valid roots include `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Dot-prefixed roots such as `.github` require explicit allowlisting.  
**Decision:** Restrict CraftedApp-created or modified files to explicitly allowed repository roots and ensure any dot-prefixed root, especially `.github`, is explicitly allowlisted before writing. Do not assume path validators will accept undeclared roots.  
**Consequences:** CraftedApp cannot emit files into arbitrary top-level locations. New root directories require explicit security and integration approval before use. CI and automation files under `.github` must be treated as a special-case allowed root, not an implicit exception.  
**Rejected alternatives:**  
- **Permit writes to any existing path in the repo:** Rejected because path security is based on allowlists, not existence checks alone.  
- **Infer safety from successful local filesystem writes:** Rejected because GitHub/path-security enforcement may still reject or silently ignore such paths.  
- **Handle `.github` like any non-dot root without explicit allowlisting:** Rejected because dot-prefixed roots are specifically called out as requiring explicit allowance.

## [Route every write through path security validation]
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. CraftedApp must not create alternate write mechanisms that bypass this control.  
**Decision:** Validate every CraftedApp file write, update, move, or generated artifact path through the shared path security boundary before execution. Do not implement direct write paths that circumvent `src/path_security.py`.  
**Consequences:** CraftedApp file operations are constrained by centralized validation rules. Convenience writes, temporary shortcuts, and subsystem-specific path exceptions are prohibited unless added through the shared security layer. This improves consistency and reduces security regressions.  
**Rejected alternatives:**  
- **Perform local path checks inside CraftedApp only:** Rejected because it duplicates and weakens the shared security boundary.  
- **Bypass validation for generated files considered “safe”:** Rejected because generated output can still target unsafe or disallowed locations.  
- **Validate only on commit rather than on write intent:** Rejected because earlier validation prevents unsafe operations sooner and matches the documented boundary.

## [Centralize GitHub I/O through shared GitHub tooling]
**Status:** Accepted  
**Context:** `src/github_tools.py` owns GitHub I/O, including path validation, rate limiting, and SHA protocol handling. CraftedApp must not implement competing repository-write behavior.  
**Decision:** Perform all CraftedApp GitHub reads and writes through the shared GitHub tooling and honor its path validation, rate limiting, and SHA-handling semantics. Do not introduce direct API calls that bypass this layer.  
**Consequences:** CraftedApp behavior will remain consistent with repository-wide GitHub safety and concurrency rules. Implementation options that need lower-level API access must first extend the shared tooling rather than bypass it.  
**Rejected alternatives:**  
- **Call the GitHub API directly from CraftedApp for speed:** Rejected because it bypasses validated path handling and repository-wide safeguards.  
- **Use separate GitHub helpers inside the subsystem:** Rejected because it duplicates protocol logic and risks inconsistent SHA/rate-limit handling.  
- **Write locally and let another process sync remotely:** Rejected because it obscures responsibility for validation and repository state management.

## [Maintain stage boundaries in the build pipeline]
**Status:** Accepted  
**Context:** The build pipeline is explicitly staged, including parse/lint/import checks, a bounded fix loop, CI generation, testing, and gated merge progression. CraftedApp must integrate with this staged model rather than collapsing it.  
**Decision:** Implement CraftedApp workflow behavior as explicit progression through the documented pipeline stages and do not skip validation, fix-loop, CI, or gate stages when producing repository changes.  
**Consequences:** CraftedApp changes must remain observable and controllable at each stage. This constrains attempts to merge generation, validation, and commit logic into opaque monolithic execution. It also ensures CI artifacts and operator gates remain part of the flow.  
**Rejected alternatives:**  
- **Run a single end-to-end generation step without intermediate checkpoints:** Rejected because the pipeline requires stage visibility and recovery points.  
- **Skip fix loops and rely only on CI:** Rejected because local correction before CI is an explicit part of the process.  
- **Allow direct merge after local tests:** Rejected because the documented process includes CI and operator gating before merge.

## [Bound automated test-fix retries to 20 attempts]
**Status:** Accepted  
**Context:** The pipeline defines a fix loop with pytest retries capped at 20 attempts and guided by failure type. CraftedApp must not introduce unbounded self-healing loops.  
**Decision:** Limit CraftedApp automated test-fix iteration to no more than 20 attempts per run and require failure-type-aware handling within that bound. Stop and surface the issue when the bound is reached.  
**Consequences:** CraftedApp avoids runaway repair cycles and preserves predictable runtime. Implementations must include explicit loop control and escalation behavior instead of indefinite retries.  
**Rejected alternatives:**  
- **Retry until tests pass:** Rejected because it creates unbounded execution and hides persistent defects.  
- **Use a smaller arbitrary retry count without regard to documented limit:** Rejected because the pipeline explicitly defines the allowed cap.  
- **Disable automated fix retries entirely:** Rejected because the documented workflow includes a repair loop as a first-class stage.

## [Enforce cyclomatic complexity limit of 15 per stage component]
**Status:** Accepted  
**Context:** The repository documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` specifically has this limit strictly enforced. CraftedApp must conform to this implementation discipline.  
**Decision:** Keep each CraftedApp pipeline stage function or equivalent orchestration component at cyclomatic complexity 15 or below. Refactor branching logic into smaller units rather than exceeding the limit.  
**Consequences:** CraftedApp orchestration code must remain modular and reviewable. This constrains large controller methods and encourages decomposition of decision-heavy logic. Complexity reduction becomes a design requirement, not a post hoc cleanup task.  
**Rejected alternatives:**  
- **Allow higher complexity in “temporary” orchestration code:** Rejected because orchestrators are long-lived and central to correctness.  
- **Enforce complexity only at file level:** Rejected because the documented constraint applies per stage, not just per module aggregate.  
- **Ignore complexity if tests cover branches:** Rejected because test coverage does not address maintainability and reviewability requirements.

## [Checkpoint every state transition]
**Status:** Accepted  
**Context:** The build pipeline requires every state transition to be checkpointed, including per-PR states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. CraftedApp must preserve this recoverability and traceability model.  
**Decision:** Persist a checkpoint at every CraftedApp state transition and include the documented per-PR milestones where applicable. Do not collapse multiple transitions into a single untracked state update.  
**Consequences:** CraftedApp execution must be resumable, auditable, and observable across failures or operator intervention. This constrains ephemeral in-memory-only workflow state and requires durable transition recording.  
**Rejected alternatives:**  
- **Checkpoint only major milestones such as commit and CI:** Rejected because the documented process requires every state transition to be tracked.  
- **Use logs instead of explicit checkpoints:** Rejected because logs are insufficient for deterministic recovery and state resumption.  
- **Store state only in memory during a run:** Rejected because crashes or restarts would lose required workflow history.

## [Require an operator gate before merge]
**Status:** Accepted  
**Context:** The documented pipeline includes a gate where the operator approves or corrects before merge. CraftedApp must not fully automate past this control point.  
**Decision:** Require explicit operator approval or correction before merging CraftedApp-produced changes. Do not implement unattended merge behavior that bypasses the gate.  
**Consequences:** CraftedApp remains human-governed at the final integration boundary. This constrains full autonomy and requires clear presentation of pending merge decisions to an operator.  
**Rejected alternatives:**  
- **Auto-merge when tests and CI pass:** Rejected because the process explicitly reserves final authority to the operator.  
- **Gate only on high-risk changes:** Rejected because the documented gate is a standard stage, not a conditional exception path.  
- **Treat silent timeout as approval:** Rejected because approval must be explicit, not inferred.

## [Generate and use CI workflows appropriate to platform]
**Status:** Accepted  
**Context:** The build pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is the critical generator for these workflows. CraftedApp must honor the documented CI split.  
**Decision:** Generate or update CI workflows through the shared CI workflow generator and use Linux CI for general workloads and macOS CI when the subsystem includes Swift-specific requirements. Do not handcraft divergent workflow files outside the defined pattern.  
**Consequences:** CraftedApp CI remains consistent with platform requirements and repository conventions. Workflow changes must pass through the shared generator path, constraining bespoke YAML drift.  
**Rejected alternatives:**  
- **Use a single Ubuntu workflow for all languages:** Rejected because Swift/macOS support is explicitly called out as requiring macOS CI.  
- **Hand-edit workflow YAML directly in each feature branch:** Rejected because `src/ci_workflow.py` is the designated generation point and direct edits increase drift.  
- **Run only local tests without CI workflow generation:** Rejected because CI is a mandatory pipeline stage.