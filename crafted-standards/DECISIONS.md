# DECISIONS.md

## [Adopt the documented repository structure as a hard implementation boundary]
**Status:** Accepted

**Context:** CraftedAgent operates in a repository with a prescribed top-level layout. The TRDs and README define `forge-docs/` as the source of truth for requirements and `forge-standards/` as the location for architecture and implementation constraints. The subsystem must not infer an alternate layout because path handling, documentation lookup, and generation behavior depend on these locations.

**Decision:** Treat the documented repository structure as mandatory. Implement CraftedAgent to read requirements from `forge-docs/`, honor constraints from `forge-standards/`, and assume standard project roots such as `src/`, `tests/`, `docs/`, and `scripts/` unless explicitly configured otherwise.

**Consequences:** CraftedAgent must fail clearly when required repository directories are missing or relocated. Features that read TRDs, write code, or generate standards artifacts must resolve paths against the documented roots rather than performing broad filesystem discovery. Repository portability is constrained to layouts that preserve these directories or provide explicit configuration compatible with the same semantics.

**Rejected alternatives:**  
- Auto-discover repository structure by scanning for likely folders. Rejected because it weakens determinism and can route writes or reads to unintended paths.  
- Treat documentation locations as advisory only. Rejected because TRDs are the source of truth and implementation must be constrained by them.  
- Permit arbitrary top-level layouts by default. Rejected because path security and orchestration rules assume known roots.

## [Require critical-file awareness before modifying core subsystem behavior]
**Status:** Accepted

**Context:** Several files are explicitly identified as critical because they define generation, orchestration, GitHub I/O, path security, and CI workflow behavior. Changes in these files have system-wide effects and can invalidate safety or operational guarantees.

**Decision:** Require any implementation that changes agent behavior in `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, or `src/ci_workflow.py` to treat those files as protected design surfaces. Read and preserve their existing contracts before modifying them, and constrain changes to their documented responsibilities.

**Consequences:** CraftedAgent implementation must not introduce side effects into these files casually or bypass their logic elsewhere in the codebase. New functionality that overlaps their concerns must integrate through these files’ established responsibilities rather than duplicating parallel mechanisms. Review burden is increased for changes touching these files, but consistency and safety are improved.

**Rejected alternatives:**  
- Allow any component to reimplement GitHub, path validation, orchestration, or CI generation logic independently. Rejected because duplicated control paths create drift and bypass critical safeguards.  
- Treat the critical-files list as informational only. Rejected because these files define subsystem boundaries and failure in them affects every generated PR.  
- Centralize all logic into a new module and deprecate these files implicitly. Rejected because it breaks documented expectations and obscures responsibility boundaries.

## [Enforce explicit allowed root directories for all repository writes]
**Status:** Accepted

**Context:** GitHub integration lessons learned show that writes to unexpected roots either fail silently or are blocked by path security. Dot-prefixed roots such as `.github` require explicit allowlisting. CraftedAgent must operate safely and predictably when creating or modifying files.

**Decision:** Allow CraftedAgent to write only within an explicit root allowlist. At minimum, support the standard project roots `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs` when those roots are enabled for the target repository. Reject writes outside allowed roots before any GitHub or filesystem operation.

**Consequences:** Every write path must be validated against an allowlist rooted at approved top-level directories. New repository areas cannot be used until explicitly added. CI workflow generation under `.github` remains possible because that root is explicitly allowed. This reduces flexibility for unconventional layouts but prevents unsafe or silently ignored writes.

**Rejected alternatives:**  
- Permit writes anywhere under the repository root after normalization. Rejected because it is too permissive and weakens the security boundary.  
- Special-case `.github` without general allowlist support. Rejected because other nonstandard roots also need explicit governance.  
- Validate only at commit time. Rejected because earlier rejection is safer and avoids wasted generation work.

## [Route every write path through the path security boundary]
**Status:** Accepted

**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. CraftedAgent performs code generation, file updates, and workflow creation; each of these actions can become a security issue if path validation is bypassed.

**Decision:** Require all filesystem and GitHub write operations in CraftedAgent to pass through the path security layer before execution. Prohibit direct writes, direct path concatenation, or alternate validation paths that bypass `src/path_security.py`.

**Consequences:** Implementation must centralize path resolution and validation. Utility functions that write files must depend on the security boundary instead of using raw paths. This may add integration overhead, but it ensures one enforceable place for path traversal prevention, root allowlisting, and normalization rules.

**Rejected alternatives:**  
- Let each module perform its own path validation. Rejected because duplicated validation logic diverges and creates bypasses.  
- Validate only local filesystem writes and trust GitHub API paths separately. Rejected because GitHub paths are equally security-sensitive.  
- Rely on code review to catch unsafe path usage. Rejected because the boundary must be enforced in code, not process alone.

## [Centralize all GitHub I/O in the GitHub tools module]
**Status:** Accepted

**Context:** `src/github_tools.py` is the designated location for GitHub I/O and already encompasses path validation, rate limiting, and SHA protocol handling. CraftedAgent will open branches, create commits, and interact with repository contents; these actions must be consistent and safe.

**Decision:** Implement all GitHub API reads and writes for CraftedAgent through `src/github_tools.py`. Do not call GitHub APIs directly from generation, orchestration, or review logic.

**Consequences:** Rate limiting, SHA handling, and path constraints remain consistent across the subsystem. Changes to GitHub semantics can be localized. This constrains module design by requiring dependency injection or adapters around `github_tools` rather than direct API client usage in feature code.

**Rejected alternatives:**  
- Allow direct GitHub API calls in feature modules for convenience. Rejected because it duplicates protocol handling and weakens consistency.  
- Introduce a second GitHub client layer specific to CraftedAgent. Rejected because it splits responsibility and risks conflicting behavior.  
- Use shell-based git operations for all repository changes. Rejected because the documented subsystem relies on GitHub I/O guarantees such as SHA protocol handling and controlled validation.

## [Preserve the staged build pipeline as the execution model]
**Status:** Accepted

**Context:** The README defines a staged build pipeline including static validation, a bounded fix loop, CI generation, test/CI execution, and an operator gate before merge. CraftedAgent is part of this workflow and must fit into its sequencing rather than inventing a different execution model.

**Decision:** Implement CraftedAgent behavior as an explicit stage-driven pipeline. Preserve the documented order of validation, fix loop, CI generation, test/CI execution, and gating, and do not skip required stages during normal operation.

**Consequences:** The subsystem must expose stage boundaries and pass artifacts cleanly between them. Fast paths that bypass validation or gating are disallowed unless separately and explicitly designed. This improves auditability and recovery but limits ad hoc orchestration optimizations.

**Rejected alternatives:**  
- Use a single monolithic “generate and commit” routine. Rejected because it obscures failures and bypasses stage-specific controls.  
- Dynamically reorder stages based on heuristic confidence. Rejected because the documented pipeline is normative and checkpointed.  
- Make CI generation optional by default. Rejected because CI is part of the required pipeline output.

## [Cap cyclomatic complexity at 15 for every pipeline stage implementation]
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is specifically called out as strictly enforcing this limit. CraftedAgent’s orchestration logic must remain maintainable and reviewable.

**Decision:** Keep the implementation of each CraftedAgent pipeline stage at cyclomatic complexity 15 or below. Split logic into helper functions or subordinate components rather than exceeding the stage-level complexity cap.

**Consequences:** Stage handlers must be narrowly scoped and decomposed. Complex retry logic, branching strategies, and error classification must be factored into helpers rather than accumulated in orchestration methods. This constrains implementation style and may increase the number of smaller functions, but it preserves readability and aligns with the documented limit.

**Rejected alternatives:**  
- Exceed the limit where complexity is operationally necessary. Rejected because the cap is an explicit architectural rule.  
- Apply the cap only to new code, not existing stage implementations. Rejected because the constraint applies to every stage.  
- Measure complexity only at the module level. Rejected because the requirement is stage-specific, not aggregate.

## [Bound the automated fix loop to 20 attempts with failure-type-aware handling]
**Status:** Accepted

**Context:** The documented pipeline includes a fix loop that runs `pytest` for up to 20 attempts and uses failure-type-aware strategy. CraftedAgent must improve code iteratively without entering unbounded retry behavior.

**Decision:** Limit the automated fix loop to a maximum of 20 attempts per run and require retry behavior to branch on classified failure types rather than repeating the same action blindly.

**Consequences:** CraftedAgent must track attempt count and stop with a clear terminal state once the limit is reached. Error analysis becomes a required capability for retry logic. The subsystem may stop before resolving all issues, but it avoids infinite or wasteful loops and produces more interpretable failure modes.

**Rejected alternatives:**  
- Retry until tests pass. Rejected because it risks nontermination and resource exhaustion.  
- Use a smaller fixed retry count without failure classification. Rejected because the documented behavior requires both bounded retries and strategy awareness.  
- Let each fixer choose its own retry limit. Rejected because a uniform cap is part of the pipeline contract.

## [Checkpoint every state transition, including per-PR milestones]
**Status:** Accepted

**Context:** The README requires every state transition to be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. CraftedAgent needs resumability, auditability, and visibility into partial progress.

**Decision:** Persist a checkpoint for every stage transition and for each documented per-PR milestone. Treat checkpoint creation as part of the success criteria for advancing state.

**Consequences:** State management becomes a first-class concern in CraftedAgent. Recovery and resume flows must read from checkpoints rather than infer state indirectly. This adds persistence and serialization requirements, but it enables restart safety, operator inspection, and deterministic pipeline behavior.

**Rejected alternatives:**  
- Checkpoint only major stages. Rejected because the requirement explicitly includes per-PR milestones.  
- Derive state from GitHub artifacts on demand. Rejected because derived state can be incomplete or ambiguous.  
- Keep checkpoints only in memory. Rejected because restart recovery requires durable persistence.

## [Require an operator gate before merge]
**Status:** Accepted

**Context:** The documented pipeline includes a final gate in which the operator approves or corrects before merge, and every gate decision is checkpointed. CraftedAgent may automate preparation, but merge authority remains supervised.

**Decision:** Do not allow CraftedAgent to merge autonomously as part of the standard pipeline. Require an explicit operator approval or correction step before any merge action and checkpoint the decision.

**Consequences:** Full end-to-end unattended merge is out of scope for the standard CraftedAgent flow. The subsystem must present sufficient artifacts for human review and must block progression from CI-passed state to merge until a gate decision is recorded. This reduces throughput but preserves accountability and safety.

**Rejected alternatives:**  
- Auto-merge when tests and CI pass. Rejected because the documented process requires operator gating.  
- Make operator approval optional for low-risk changes. Rejected because no such exception is documented.  
- Record gate decisions informally outside the pipeline state model. Rejected because gate decisions must be checkpointed.

## [Generate CI workflows through the dedicated CI workflow module]
**Status:** Accepted

**Context:** `src/ci_workflow.py` is the designated generator for CI workflows, and the pipeline specifies `crafted-ci.yml` on `ubuntu-latest` plus `crafted-ci-macos.yml` for Swift. CraftedAgent must produce CI configuration consistently with the repository’s standards and allowed roots.

**Decision:** Generate and update CI workflow files only through `src/ci_workflow.py`, targeting `.github` as an explicitly allowlisted root. Support the documented workflow variants, including Ubuntu-based CI and macOS CI for Swift projects.

**Consequences:** Workflow structure, naming, and platform targeting remain centralized and consistent. CraftedAgent cannot emit ad hoc workflow YAML from unrelated modules. This constrains flexibility for custom CI generation but ensures compatibility with path security and the documented build pipeline.

**Rejected alternatives:**  
- Let feature generators write workflow YAML directly into `.github/workflows`. Rejected because it bypasses the dedicated workflow module and increases inconsistency.  
- Generate only a single Linux workflow for all projects. Rejected because Swift requires the documented macOS workflow.  
- Skip workflow generation when CI files already exist. Rejected because updates and conformance still need centralized handling.