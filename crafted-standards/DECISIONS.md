# DECISIONS.md

## [Use forge-docs as the source of truth for subsystem behavior]
**Status:** Accepted  
**Context:** The repository structure defines `forge-docs/` as the location where all TRDs and PRDs live, and these documents must be read before building. The CraftedDevAgent subsystem must align implementation behavior with documented technical requirements rather than ad hoc code assumptions.  
**Decision:** Treat `forge-docs/` as the authoritative input for CraftedDevAgent design and behavior, and require implementation changes to remain consistent with the TRDs and PRDs stored there before modifying subsystem logic.  
**Consequences:** Implementation must be traceable to repository documentation. Code changes that conflict with TRDs are invalid unless the documents are updated first. The subsystem cannot rely on undocumented conventions as normative behavior.  
**Rejected alternatives:**  
- Using code as the source of truth, because it allows undocumented drift and breaks the documented development workflow.  
- Splitting authority between docs and implementation, because conflicts become ambiguous and make reviews unreliable.  
- Maintaining subsystem-local requirements outside `forge-docs/`, because it fragments the specification.

## [Preserve critical-file boundaries for core agent behavior]
**Status:** Accepted  
**Context:** The repository explicitly identifies critical files whose behavior affects generation, orchestration, GitHub I/O, security boundaries, and CI workflow generation. Unconstrained edits to these files create systemic risk across all agent operations.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as protected architectural boundaries, and require any modifications to preserve their documented responsibilities.  
**Consequences:** Changes in these files must be narrowly scoped and reviewed with subsystem-wide impact in mind. Logic must not be casually moved around in ways that blur responsibility boundaries. Security, orchestration, and external I/O remain centralized instead of duplicated elsewhere.  
**Rejected alternatives:**  
- Allowing unrestricted refactors across these files, because it increases regression risk in core generation and security paths.  
- Duplicating functionality in new modules to avoid touching critical files, because that creates inconsistent behavior and weakens control points.  
- Collapsing these responsibilities into a single module, because it would increase coupling and reduce auditability.

## [Enforce explicit repository-root allowlisting for all file operations]
**Status:** Accepted  
**Context:** GitHub integration lessons learned show that writes to unexpected root directories fail silently or are rejected by path security guards. Standard project operation requires explicit support for both common roots and `.github`, which is dot-prefixed and commonly blocked by validators.  
**Decision:** Permit CraftedDevAgent file creation and modification only under an explicit allowlist of repository root directories, including `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`, with all write paths validated through the security layer.  
**Consequences:** The subsystem cannot write to arbitrary paths even if requested by higher-level planning logic. CI workflow generation under `.github` must be explicitly supported. New root directories require deliberate allowlist updates before use. Silent path drift is prevented.  
**Rejected alternatives:**  
- Allowing writes anywhere within the repository, because it weakens path security and enables unsafe or unintended mutations.  
- Allowing inferred roots based on user intent, because inference is error-prone and can bypass security expectations.  
- Rejecting dot-prefixed roots categorically, because CI workflow files in `.github` are required for normal operation.

## [Route every write-path decision through the path security boundary]
**Status:** Accepted  
**Context:** `src/path_security.py` is designated as the security boundary, and every write path must pass through it. The subsystem performs automated code generation and repository mutation, so path validation cannot be optional or distributed inconsistently.  
**Decision:** Centralize all filesystem write authorization in `src/path_security.py` and prohibit direct write-path approval logic elsewhere in CraftedDevAgent.  
**Consequences:** Any module that writes files must depend on the shared security boundary instead of implementing its own checks. Path validation behavior stays consistent across generation, GitHub operations, and CI file creation. Security fixes can be made in one place.  
**Rejected alternatives:**  
- Letting each module validate its own paths, because duplicated validation leads to inconsistent enforcement and missed edge cases.  
- Validating only at commit time, because unsafe intermediate writes may already have occurred.  
- Trusting upstream callers to sanitize paths, because security boundaries must be enforced at the point of mutation.

## [Centralize all GitHub I/O in github_tools]
**Status:** Accepted  
**Context:** The repository marks `src/github_tools.py` as the module for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. Distributed GitHub interactions would create inconsistent correctness and API behavior.  
**Decision:** Perform all CraftedDevAgent GitHub reads and writes through `src/github_tools.py`, and do not access GitHub APIs directly from other subsystem modules.  
**Consequences:** Rate limiting, SHA handling, and repository mutation semantics remain consistent. Auditing GitHub behavior is simplified. New GitHub features must integrate through the established tool layer rather than bypassing it.  
**Rejected alternatives:**  
- Allowing direct GitHub API calls from orchestration or generation modules, because it duplicates protocol logic and increases failure modes.  
- Creating multiple specialized GitHub clients, because responsibility would fragment and enforcement of security and rate limits would weaken.  
- Treating GitHub I/O as a thin transport concern only, because the documented behavior includes substantive validation and protocol rules.

## [Keep pipeline orchestration in build_director with strict complexity limits]
**Status:** Accepted  
**Context:** `src/build_director.py` is the pipeline orchestration layer, and the repository states that a cyclomatic complexity limit of 15 is strictly enforced for every stage. The build pipeline is central to CraftedDevAgent execution and must remain comprehensible and maintainable.  
**Decision:** Implement and evolve pipeline orchestration in `src/build_director.py` while ensuring every stage and related control path remains at or below cyclomatic complexity 15.  
**Consequences:** Complex branching behavior must be decomposed into smaller helpers rather than accumulated in orchestration code. Pipeline changes that would exceed the complexity budget must be redesigned. The subsystem prioritizes predictable orchestration over monolithic control flow.  
**Rejected alternatives:**  
- Allowing higher complexity in orchestration for convenience, because the documented limit is strict and complexity growth would reduce maintainability.  
- Moving orchestration logic opportunistically into unrelated modules, because that obscures the pipeline architecture.  
- Replacing staged orchestration with an implicit event soup, because it weakens checkpointing and reviewability.

## [Preserve the staged build pipeline and failure-aware fix loop]
**Status:** Accepted  
**Context:** The documented build pipeline includes syntax and lint validation (`ast.parse`, `ruff`, import check), followed by a fix loop with up to 20 pytest attempts using failure-type-aware strategy, then Test + CI and operator gating. CraftedDevAgent must implement this sequence consistently.  
**Decision:** Execute code generation and validation as an explicit staged pipeline that includes syntax validation, lint/import validation, a bounded fix loop of up to 20 pytest-driven attempts, CI workflow generation, CI execution, and final gating.  
**Consequences:** The subsystem cannot skip validation stages for speed. Automated repair behavior is bounded and strategy-aware rather than unbounded retry. Pipeline state remains legible and operationally predictable.  
**Rejected alternatives:**  
- Running tests only once without a fix loop, because the documented workflow expects iterative repair.  
- Allowing unlimited retries, because it risks non-terminating behavior and resource waste.  
- Reordering validation to run expensive tests before basic syntax/lint checks, because that is less efficient and contrary to the documented pipeline.

## [Checkpoint every state transition, including per-PR lifecycle states]
**Status:** Accepted  
**Context:** The README specifies that every state transition is checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. CraftedDevAgent coordinates multi-step automated work that must survive interruption and remain auditable.  
**Decision:** Persist a checkpoint at every subsystem state transition, including all per-PR lifecycle milestones, and treat checkpointing as mandatory rather than best-effort.  
**Consequences:** Recovery, auditability, and operator visibility are built into the subsystem. Stage progression must be explicit and serializable. Implementations that perform hidden transitions without persisted state are non-compliant.  
**Rejected alternatives:**  
- Checkpointing only major milestones, because intermediate progress would be lost and debugging would be harder.  
- Using in-memory state only, because failures or restarts would destroy execution history.  
- Logging transitions without durable checkpoints, because logs are insufficient for reliable resume semantics.

## [Require operator gate before merge]
**Status:** Accepted  
**Context:** The documented pipeline includes a final gate where the operator approves or corrects before merge, and every gate decision is checkpointed. CraftedDevAgent is an automation subsystem, not a fully autonomous merger.  
**Decision:** Enforce a human operator approval or correction gate before any merge action, and persist the gate outcome as a checkpointed decision.  
**Consequences:** CraftedDevAgent cannot self-merge purely on automated success signals. Human oversight remains part of the control model. Merge automation must stop at the approval boundary unless explicit operator action is recorded.  
**Rejected alternatives:**  
- Auto-merging after tests and CI pass, because that removes the required human gate.  
- Making operator review optional based on confidence score, because the documented workflow requires a gate, not heuristic discretion.  
- Capturing approval only in transient UI state, because gate decisions must be checkpointed.

## [Generate and support platform-appropriate CI workflows, including macOS for Swift]
**Status:** Accepted  
**Context:** The pipeline documentation specifies `crafted-ci.yml` on `ubuntu-latest`, and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is identified as the generator for workflow files. CraftedDevAgent must create CI configurations that match project technology needs.  
**Decision:** Generate CI workflows through `src/ci_workflow.py`, using Ubuntu-based workflows by default and macOS workflows when Swift or equivalent macOS-specific build requirements are present.  
**Consequences:** CI generation logic must detect or be told when macOS-specific workflows are required. Workflow creation remains centralized and consistent with repository policy. `.github` support in path validation is mandatory.  
**Rejected alternatives:**  
- Emitting only Ubuntu workflows for all projects, because Swift and macOS-specific builds require macOS runners.  
- Hand-authoring workflow files outside the workflow generator, because it undermines consistency and central control.  
- Generating both workflows unconditionally, because it adds unnecessary CI cost and noise for non-macOS projects.