# DECISIONS.md

## Repository structure documentation is authoritative
**Status:** Accepted

**Context:** CraftedDevAgent operates inside a repository with explicit documentation boundaries. The TRDs and PRDs in `forge-docs/` are the source of truth for system behavior, and repository-wide engineering constraints live in `forge-standards/`. The subsystem must not infer structure from convenience or current implementation alone.

**Decision:** Treat `forge-docs/` as the authoritative source for requirements and `forge-standards/` as the authoritative source for implementation constraints before changing CraftedDevAgent behavior.

**Consequences:** Implementation must be aligned to documented TRDs before code changes are made. Features that conflict with documented repository standards must be rejected or escalated. Code must assume the documented repository layout is stable and meaningful, not incidental.

**Rejected alternatives:**  
- Derive behavior only from existing code: rejected because the repository explicitly declares TRDs and standards as source of truth.  
- Allow ad hoc local conventions within the subsystem: rejected because this would drift from repository-wide constraints and weaken cross-agent consistency.  
- Treat documentation as advisory rather than binding: rejected because the workflow depends on deterministic, reviewable requirements.

## Critical files are change-controlled boundaries
**Status:** Accepted

**Context:** Several files are identified as critical because they define core generation, orchestration, GitHub I/O, path security, and CI workflow generation. Changes in these locations can impact every pull request produced by the subsystem.

**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as controlled boundaries requiring explicit review of downstream effects before modification.

**Consequences:** Implementations must avoid incidental edits to these files. Any change touching them must account for system-wide impact, especially generation flow, orchestration complexity, GitHub write semantics, security validation, and CI generation. New logic should be added outside these files when possible unless the behavior truly belongs at the boundary.

**Rejected alternatives:**  
- Freely modify critical files as ordinary implementation detail: rejected because these files are explicitly called out as high-impact.  
- Duplicate critical logic elsewhere to avoid touching them: rejected because duplication would fragment ownership and create inconsistent behavior.  
- Hide changes behind undocumented feature flags: rejected because it weakens auditability and reviewability.

## All write paths must pass through path security
**Status:** Accepted

**Context:** Path validation is the security boundary for repository writes. The repository explicitly identifies `src/path_security.py` as the enforcement point, and GitHub integration lessons show unexpected roots are rejected or fail silently without strict validation.

**Decision:** Route every filesystem write and GitHub-targeted file path through the centralized path security validator before execution.

**Consequences:** No component may write directly to repository paths without validation. New file creation, updates, generated artifacts, and workflow files must all use the same validation boundary. Security policy remains centralized and auditable, and silent failures from unsupported roots are reduced.

**Rejected alternatives:**  
- Validate paths independently in each module: rejected because distributed validation leads to policy drift and inconsistent enforcement.  
- Rely on GitHub API errors to catch invalid paths: rejected because some failures are silent or delayed and do not enforce repository security invariants.  
- Permit trusted internal callers to bypass validation: rejected because trust shortcuts erode the security boundary.

## Repository write targets are restricted to an explicit root allowlist
**Status:** Accepted

**Context:** The subsystem must commit only to expected repository roots. The documented allowlist for a standard project includes `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Dot-prefixed roots such as `.github` require explicit inclusion.

**Decision:** Enforce an explicit root-directory allowlist for all repository writes, including dot-prefixed roots only when specifically listed.

**Consequences:** CraftedDevAgent must reject writes outside approved roots. Support for new top-level directories requires an explicit policy update rather than opportunistic creation. CI workflow generation must account for `.github` being allowed by exception, not by generic path rules.

**Rejected alternatives:**  
- Allow writes anywhere within the repository if the path is normalized: rejected because normalized paths alone do not prevent policy violations.  
- Infer allowed roots from existing repository contents: rejected because presence does not imply permission.  
- Ban dot-prefixed roots categorically: rejected because workflow files in `.github` are a required use case.

## GitHub I/O is centralized in github_tools
**Status:** Accepted

**Context:** GitHub interactions carry specialized requirements including path validation, rate limiting, and SHA protocol handling. The repository designates `src/github_tools.py` as the single high-impact integration point for this behavior.

**Decision:** Centralize all GitHub API reads and writes for CraftedDevAgent through `src/github_tools.py`.

**Consequences:** Callers must not invoke GitHub operations directly from unrelated modules. Rate limiting, SHA handling, and path checks remain consistent across the subsystem. Future GitHub behavior changes can be implemented in one place and audited centrally.

**Rejected alternatives:**  
- Allow each feature module to call the GitHub API directly: rejected because it duplicates protocol logic and increases inconsistency risk.  
- Split GitHub logic across per-feature helpers: rejected because repository policy identifies a single integration boundary.  
- Treat read operations as exempt from centralization: rejected because protocol, observability, and throttling concerns apply to reads as well.

## Pipeline stages must preserve bounded complexity
**Status:** Accepted

**Context:** The build pipeline requires that every stage have maximum cyclomatic complexity of 15. `src/build_director.py` is specifically identified as the orchestration boundary where this rule is strictly enforced.

**Decision:** Keep each pipeline stage and orchestration transition at cyclomatic complexity 15 or lower, refactoring into smaller units before exceeding the limit.

**Consequences:** New logic must be decomposed rather than appended into monolithic orchestration flows. Stage-specific behavior should be extracted into focused helpers or strategy objects when complexity grows. Complexity budget becomes a design constraint, not just a lint target.

**Rejected alternatives:**  
- Permit exceptions for orchestration code because it is inherently complex: rejected because the repository explicitly states the limit is strictly enforced.  
- Raise the complexity threshold for urgent features: rejected because this would undermine maintainability and checkpoint clarity.  
- Ignore complexity until static analysis fails: rejected because the constraint is architectural and should guide design upfront.

## Generation and fix loops must remain staged and deterministic
**Status:** Accepted

**Context:** The documented pipeline includes discrete stages such as parsing, linting, import checking, and a fix loop with up to 20 pytest attempts using failure-type-aware strategy. The subsystem depends on predictable transitions rather than open-ended autonomous iteration.

**Decision:** Implement generation, validation, and repair as explicit pipeline stages with bounded, deterministic retry behavior rather than unconstrained agent loops.

**Consequences:** Retry counts and progression are reviewable and testable. Failure handling must map to known strategies instead of improvising indefinitely. The subsystem remains operable under checkpointing and operator review because its state transitions are explicit.

**Rejected alternatives:**  
- Use an open-ended self-healing loop until success: rejected because it can become non-terminating and obscures stage accountability.  
- Collapse validation and repair into a single adaptive phase: rejected because this weakens observability and makes checkpoints less meaningful.  
- Apply a uniform retry strategy regardless of failure type: rejected because the documented pipeline calls for failure-type-aware repair.

## State transitions must be checkpointed
**Status:** Accepted

**Context:** The build pipeline requires checkpointing of every state transition, including per-PR states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. This supports recovery, auditing, and controlled progression.

**Decision:** Persist a checkpoint at every meaningful pipeline and per-PR state transition before advancing to the next state.

**Consequences:** The subsystem must expose explicit state boundaries and durable transition records. Recovery logic should resume from checkpoints rather than recomputing ambiguous state. Hidden in-memory transitions are disallowed for workflow-critical progress.

**Rejected alternatives:**  
- Checkpoint only major milestones such as commit and CI pass: rejected because the repository requires every state transition to be checkpointed.  
- Reconstruct state from Git history after failure: rejected because not all orchestration state is derivable from repository contents.  
- Keep state only in memory for speed: rejected because it breaks crash recovery and auditability.

## Gate decisions require explicit operator approval before merge
**Status:** Accepted

**Context:** The documented pipeline includes a gate stage where the operator approves or corrects before merge. The subsystem therefore supports automation up to, but not through, final governance.

**Decision:** Require an explicit operator gate decision before merge and do not allow CraftedDevAgent to self-authorize final integration.

**Consequences:** The subsystem may prepare branches, commits, tests, and CI artifacts, but final merge authority remains external. Automation must surface enough context for human approval or correction. Any implementation that bypasses operator review violates the workflow.

**Rejected alternatives:**  
- Auto-merge when tests and CI pass: rejected because the process explicitly reserves a human gate.  
- Require approval only for high-risk changes: rejected because the documented gate is part of the standard workflow, not an exception path.  
- Let the agent decide merge readiness autonomously: rejected because it collapses governance and execution into one actor.

## CI workflow generation must support standard and macOS-specific pipelines
**Status:** Accepted

**Context:** The repository specifies CI generation for `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. The workflow generator is identified as a critical file, making CI output part of the subsystem’s controlled surface.

**Decision:** Generate CI workflows that distinguish standard Linux-based validation from macOS-specific Swift validation, using separate workflow artifacts as defined by repository convention.

**Consequences:** The subsystem must not collapse all CI concerns into a single generic workflow when platform-specific behavior is required. Changes to workflow generation must preserve compatibility with both standard and Swift/macOS execution paths. `.github` writes must remain explicitly allowed and validated.

**Rejected alternatives:**  
- Use a single universal workflow for all languages and platforms: rejected because the repository defines separate standard and macOS workflows.  
- Run all CI on macOS for consistency: rejected because it is costlier and unnecessary for standard projects.  
- Omit workflow generation from the subsystem and expect manual setup: rejected because CI generation is an identified critical responsibility.