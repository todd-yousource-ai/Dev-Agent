# DECISIONS.md

## [Read design inputs from forge-docs before implementation]
**Status:** Accepted  
**Context:** The repository structure defines `forge-docs/` as the location where all TRDs and PRDs live and identifies them as required inputs before building. The subsystem must treat these documents as the source of truth rather than inferred behavior from code alone.  
**Decision:** Read and conform to applicable TRDs and PRDs in `forge-docs/` before changing CraftedDevAgent behavior or interfaces. Treat those documents as authoritative design inputs.  
**Consequences:** Implementation must be traceable to documented requirements. Changes that contradict TRDs or PRDs require document updates first or in lockstep. Ad hoc behavior based only on local code convenience is disallowed.  
**Rejected alternatives:**  
- Derive behavior primarily from existing implementation and only consult documents when unclear — rejected because it allows drift from stated requirements.  
- Treat README files as equal authority to TRDs/PRDs — rejected because repository structure explicitly identifies `forge-docs/` artifacts as source-of-truth design inputs.

## [Preserve security and orchestration critical files with elevated change discipline]
**Status:** Accepted  
**Context:** Several files are explicitly marked critical because they define core generation, orchestration, GitHub I/O, path validation, and CI workflow generation: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes to these files have subsystem-wide effects.  
**Decision:** Apply elevated review and change discipline to the identified critical files. Read them before modifying dependent behavior, minimize surface-area changes, and preserve their contracts unless an intentional design change is documented.  
**Consequences:** Refactors that touch critical files must be narrowly scoped and justified. Shared behavior must not be bypassed by introducing duplicate logic elsewhere. Subsystem changes should prefer extension around these files over implicit modification of their responsibilities.  
**Rejected alternatives:**  
- Freely modify critical files whenever a local feature needs it — rejected because small changes can affect every PR, every write path, or all GitHub interactions.  
- Reimplement equivalent logic in feature modules to avoid touching critical files — rejected because it creates inconsistent security, orchestration, and I/O behavior.

## [Route all repository writes through path security]
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. GitHub integration lessons also show that invalid roots are rejected or fail silently without proper allowlisting.  
**Decision:** Validate every file write, update, and commit target through the centralized path security mechanism before performing local or GitHub-backed repository mutation. Do not write directly to repository paths without this check.  
**Consequences:** All write-capable code paths must depend on the same validation rules. New tooling that creates files must integrate with path security rather than using raw filesystem or GitHub write calls. This constrains convenience scripts and one-off generators.  
**Rejected alternatives:**  
- Allow direct writes for trusted internal modules — rejected because it weakens the single security boundary and invites inconsistent validation.  
- Validate only GitHub writes and not local generated files — rejected because unsafe local paths can still become unsafe commits.

## [Enforce an explicit allowlist of repository root directories]
**Status:** Accepted  
**Context:** GitHub integration lessons specify that committing to unexpected root directories fails or is blocked by path guards. Standard projects require explicit allowlisting of valid roots, including dot-prefixed `.github`.  
**Decision:** Restrict file operations to an explicit allowlist of root directories. At minimum, support standard roots: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Require explicit approval/configuration for any additional root.  
**Consequences:** CraftedDevAgent cannot create or modify files in arbitrary top-level paths. Dot-prefixed roots must be consciously included rather than accidentally blocked. New repository layouts require an allowlist update before generation or commit succeeds.  
**Rejected alternatives:**  
- Permit any repository-relative path that does not traverse upward — rejected because it is too permissive and does not match the documented security model.  
- Block dot-prefixed roots entirely — rejected because CI workflow files in `.github` are required.  
- Infer allowed roots from the current repository tree at runtime — rejected because it can legitimize accidental or malicious directories.

## [Centralize all GitHub I/O in src/github_tools.py]
**Status:** Accepted  
**Context:** `src/github_tools.py` is designated as the module for all GitHub I/O and includes path validation, rate limiting, and SHA protocol handling. Fragmenting these concerns across the codebase would create inconsistent API behavior.  
**Decision:** Perform all GitHub reads, writes, branch operations, and commit-related API interactions through `src/github_tools.py`. Do not call GitHub APIs directly from feature modules.  
**Consequences:** GitHub-specific concerns remain consistent across the subsystem, including optimistic concurrency via SHA handling and rate-limit behavior. New GitHub capabilities must be added to the shared module rather than implemented ad hoc elsewhere.  
**Rejected alternatives:**  
- Let each module use the GitHub client directly for simplicity — rejected because path validation, rate limiting, and SHA semantics would diverge.  
- Split GitHub reads and writes across separate helper modules immediately — rejected because the documented critical-file boundary already centralizes this concern.

## [Keep build-stage and orchestration complexity at or below 15]
**Status:** Accepted  
**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` explicitly enforces this limit. This is a hard maintainability and operability constraint.  
**Decision:** Design each build stage and orchestration function so its cyclomatic complexity does not exceed 15. When logic grows, decompose into smaller units rather than increasing branch density in a single stage.  
**Consequences:** Pipeline features must be added through composition, helper extraction, or additional stages rather than larger monolithic control flow. `src/build_director.py` and adjacent orchestration code cannot accumulate exception-heavy branching without refactoring.  
**Rejected alternatives:**  
- Allow higher complexity in orchestration because pipelines naturally branch — rejected because the documented limit is explicit and intended to preserve maintainability.  
- Enforce complexity only on new code — rejected because pipeline stability depends on the whole stage remaining within the limit.

## [Model execution as checkpointed stage transitions]
**Status:** Accepted  
**Context:** The build pipeline requires checkpointing of every state transition, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This ensures resumability, auditability, and operator visibility.  
**Decision:** Represent CraftedDevAgent workflow progress as explicit stage transitions and checkpoint each transition durably. Do not rely on implicit in-memory progress or inferred state from side effects alone.  
**Consequences:** Long-running or interrupted work can be resumed from a known state. Observability and audit trails become part of the design. New stages or transitions require corresponding checkpoint semantics.  
**Rejected alternatives:**  
- Track only final success/failure — rejected because it loses resumability and stage-level auditability.  
- Infer state from repository artifacts and CI status on demand — rejected because inference is brittle and incomplete for in-progress work.

## [Use a bounded, failure-type-aware fix loop for test remediation]
**Status:** Accepted  
**Context:** The build pipeline defines a fix loop that runs `pytest` up to 20 attempts and uses failure-type-aware strategy. This reflects a controlled remediation model rather than open-ended retries.  
**Decision:** Implement test remediation as a bounded loop with a hard cap of 20 attempts and vary remediation strategy based on detected failure type. Do not permit unbounded retry behavior.  
**Consequences:** The subsystem must classify failures sufficiently to choose appropriate fixes, and it must terminate predictably when progress stalls. Retry budgeting becomes part of pipeline control and operator expectations.  
**Rejected alternatives:**  
- Retry until tests pass — rejected because it can loop indefinitely and obscures non-converging failures.  
- Use a small fixed retry count with no failure classification — rejected because it underuses the documented strategy and reduces recovery effectiveness.

## [Generate and maintain standard CI workflows through the CI workflow module]
**Status:** Accepted  
**Context:** `src/ci_workflow.py` is the critical file responsible for generating CI workflows. The documented pipeline requires `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift-related workflows.  
**Decision:** Generate CI workflow files through `src/ci_workflow.py` and standardize on `crafted-ci.yml` for general CI and `crafted-ci-macos.yml` when macOS/Swift execution is required. Do not handcraft workflow files in feature code.  
**Consequences:** CI behavior remains consistent and centrally governed. Workflow naming and runner selection become stable contracts. Projects needing CI changes must extend the generator rather than committing bespoke workflow definitions from scattered modules.  
**Rejected alternatives:**  
- Let each feature emit or edit workflow YAML directly — rejected because it fragments CI policy and bypasses the critical module boundary.  
- Use a single universal workflow for all stacks — rejected because Swift/macOS requirements are explicitly distinct.

## [Require an operator gate before merge]
**Status:** Accepted  
**Context:** The pipeline includes a gate where the operator approves or corrects before merge, and every gate decision is checkpointed. This indicates that CraftedDevAgent is assistive and controlled, not fully autonomous at merge time.  
**Decision:** Require explicit operator approval or correction before merge. Record the gate decision as part of the checkpointed workflow state.  
**Consequences:** CraftedDevAgent may prepare branches, code, tests, commits, and CI runs, but it cannot treat successful automation as sufficient authorization to merge. Human oversight is a mandatory control point.  
**Rejected alternatives:**  
- Auto-merge after CI passes — rejected because it bypasses the documented gate and removes required human control.  
- Treat comments or passive inactivity as approval — rejected because gate decisions must be explicit and checkpointed.

## [Maintain canonical repository layout boundaries]
**Status:** Accepted  
**Context:** The repository layout identifies `forge-docs/` for source-of-truth documents and `forge-standards/` for governance artifacts including `DECISIONS.md`. Respecting these boundaries is necessary for consistent subsystem behavior and tooling expectations.  
**Decision:** Preserve the canonical repository layout: keep design/source-of-truth documents in `forge-docs/` and standards/governance artifacts in `forge-standards/`. Do not relocate or duplicate these responsibilities into implementation directories.  
**Consequences:** Tooling and contributors can rely on stable document locations. Generated or implementation-specific artifacts should not be mixed with governing documents. CraftedDevAgent features that read standards or requirements must target these canonical locations.  
**Rejected alternatives:**  
- Move active design documents into `src/` for convenience — rejected because it blurs implementation and governance boundaries.  
- Duplicate standards and TRDs near consuming code — rejected because it creates divergence and stale copies.