# DECISIONS.md

## [Use forge-docs as the mandatory source of truth before implementation]
**Status:** Accepted  
**Context:** The subsystem operates in a repository where all TRDs and PRDs live under `forge-docs/`, and those documents define required behavior and constraints. Building without consulting them risks divergence from the documented architecture and workflow.  
**Decision:** Read applicable documents in `forge-docs/` before making implementation changes, and treat them as the authoritative input for CraftedDevAgent behavior.  
**Consequences:** Implementation must be traceable back to repository documentation. Changes that conflict with TRDs or PRDs are out of bounds unless the documents are updated first. The subsystem must assume document-first development, not code-first inference.  
**Rejected alternatives:**  
- Infer behavior from existing code only — rejected because code may lag documented requirements.  
- Treat README files as sufficient authority — rejected because TRDs/PRDs are the stated source of truth.  
- Allow ad hoc implementation decisions without document review — rejected because it undermines consistency with the documented workflow.

## [Treat critical files as protected integration boundaries]
**Status:** Accepted  
**Context:** Several files are identified as critical because they enforce system-wide behavior: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes to them can affect every generated PR, orchestration flow, GitHub I/O, security enforcement, and CI generation.  
**Decision:** Treat the named critical files as protected integration boundaries; read them before modifying related behavior, and do not bypass their responsibilities from adjacent code.  
**Consequences:** CraftedDevAgent must integrate through these files’ established responsibilities rather than duplicating or circumventing them. Security, orchestration, and GitHub operations must remain centralized. Review burden is higher for changes touching these files.  
**Rejected alternatives:**  
- Reimplement equivalent logic in new modules — rejected because it fragments authority and increases drift.  
- Modify behavior indirectly without reviewing the critical file — rejected because it risks violating hidden invariants.  
- Spread path validation or GitHub I/O across multiple modules — rejected because the repository defines explicit owners for those concerns.

## [Centralize all GitHub I/O in src/github_tools.py]
**Status:** Accepted  
**Context:** GitHub interactions have repository-specific constraints including path validation, rate limiting, and SHA protocol handling. A single file is designated as the owner of all GitHub I/O.  
**Decision:** Route all GitHub reads and writes through `src/github_tools.py`; do not perform direct GitHub I/O elsewhere in the CraftedDevAgent subsystem.  
**Consequences:** This constrains implementation to a single integration boundary for repository mutations and remote API interactions. Features that need GitHub access must use or extend this module rather than creating parallel clients. Consistency in path handling, rate limiting, and commit/update semantics is preserved.  
**Rejected alternatives:**  
- Use direct API calls from feature modules — rejected because it bypasses shared controls.  
- Introduce multiple GitHub client wrappers by concern area — rejected because it duplicates SHA and rate-limit logic.  
- Permit shell-based git/GitHub operations outside the module — rejected because it weakens validation and auditability.

## [Enforce path security through src/path_security.py for every write]
**Status:** Accepted  
**Context:** Path handling is a security boundary, and repository lessons learned show that commits to unexpected root directories fail silently or are rejected by path security guards. Every write path must pass through centralized validation.  
**Decision:** Validate every write target through `src/path_security.py` before file creation, modification, or commit preparation.  
**Consequences:** No component may write directly to repository paths without security validation. New features that emit files must conform to the centralized path rules. This reduces accidental writes outside sanctioned locations and ensures compatibility with repository root allowlists.  
**Rejected alternatives:**  
- Perform local inline path checks in each module — rejected because it creates inconsistent enforcement.  
- Validate only at commit time — rejected because invalid intermediate writes still violate the security boundary.  
- Trust callers to provide safe relative paths — rejected because repository history shows path mistakes are common and costly.

## [Allow writes only to explicitly allowlisted repository root directories]
**Status:** Accepted  
**Context:** The repository maintains an allowlist of valid root directories, and writes to unexpected roots are rejected or fail silently. Standard projects must explicitly allow `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Dot-prefixed roots like `.github` require explicit inclusion.  
**Decision:** Restrict CraftedDevAgent-generated file operations to explicitly allowlisted repository roots, including explicit support for `.github` when CI files are generated.  
**Consequences:** File generation is constrained to known-safe top-level locations. Any new root must be intentionally added before use. CI workflow generation is permitted only because `.github` is explicitly recognized. This improves predictability and guards against repository pollution or security issues.  
**Rejected alternatives:**  
- Allow any relative path within the repo — rejected because unexpected roots are known failure cases.  
- Block dot-prefixed roots categorically — rejected because CI workflows must be written under `.github`.  
- Maintain an implicit allowlist based on observed usage — rejected because explicit policy is required by the path guards.

## [Preserve build pipeline stage structure as the governing execution model]
**Status:** Accepted  
**Context:** The build pipeline is defined as an ordered staged process, including generation, validation, fix loop, test/CI, and gate phases. The subsystem must fit into this execution model to remain compatible with the rest of the system.  
**Decision:** Implement CraftedDevAgent behavior as stage-aligned pipeline execution that conforms to the documented build pipeline ordering and gates.  
**Consequences:** The subsystem cannot collapse or reorder core stages arbitrarily. Validation and correction must occur in their defined places, and gate behavior must remain explicit before merge. Features that affect execution flow must preserve compatibility with the pipeline model.  
**Rejected alternatives:**  
- Use a free-form agent loop without explicit stages — rejected because it obscures progress and weakens control points.  
- Merge validation and testing into a single opaque step — rejected because the documented pipeline distinguishes them.  
- Skip gating when automated checks pass — rejected because operator approval is part of the documented process.

## [Limit each pipeline stage to cyclomatic complexity 15]
**Status:** Accepted  
**Context:** The repository explicitly requires every stage to have a maximum cyclomatic complexity of 15, and `src/build_director.py` is called out as having this limit strictly enforced.  
**Decision:** Keep each CraftedDevAgent pipeline stage implementation at or below cyclomatic complexity 15, refactoring into helper units when necessary.  
**Consequences:** Stage logic must remain composable and readable. Large decision trees must be decomposed rather than expanded inline. This constrains implementation style and prevents orchestration code from accumulating hidden branching complexity.  
**Rejected alternatives:**  
- Permit higher complexity for “orchestration-only” code — rejected because the limit is explicit and strict.  
- Enforce only module-level average complexity — rejected because the requirement applies per stage.  
- Defer complexity control to later cleanup — rejected because the rule is a design-time constraint, not a best-effort guideline.

## [Checkpoint every state transition in the agent workflow]
**Status:** Accepted  
**Context:** The documented process requires every state transition to be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. This supports recoverability, auditability, and controlled progression.  
**Decision:** Persist a checkpoint for every meaningful state transition in CraftedDevAgent workflow execution, including all documented per-PR milestones.  
**Consequences:** The subsystem must expose stateful progress rather than only final outcomes. Recovery, retries, and operator inspection depend on these checkpoints. New workflow states must be added deliberately with corresponding checkpoint semantics.  
**Rejected alternatives:**  
- Checkpoint only start and finish of a run — rejected because intermediate recovery and traceability are required.  
- Log transitions without durable checkpoints — rejected because logs alone are insufficient for resumability.  
- Checkpoint only failure states — rejected because successful milestones are also required by the documented process.

## [Model gate decisions explicitly before merge]
**Status:** Accepted  
**Context:** The build pipeline includes a gate where the operator approves or corrects before merge, and every gate decision is intended to be recorded. This means merge readiness is not solely determined by automated checks.  
**Decision:** Require an explicit gate decision before merge-related completion, and record that decision as part of workflow state.  
**Consequences:** CraftedDevAgent must stop short of implicit merge completion after CI success. Operator approval or correction becomes a first-class workflow event. Automation may prepare merge artifacts, but it must not erase the human gate.  
**Rejected alternatives:**  
- Auto-merge immediately after tests and CI pass — rejected because it bypasses the documented operator gate.  
- Treat lack of objection as approval — rejected because the process requires explicit gate decisions.  
- Store gate outcomes only in transient UI state — rejected because gate decisions must remain part of checkpointed workflow history.

## [Use a bounded, failure-aware fix loop for test remediation]
**Status:** Accepted  
**Context:** The documented pipeline specifies a fix loop using `pytest` with up to 20 attempts and a failure-type-aware strategy. This defines both the retry bound and the expectation that retries are guided by failure classification rather than blind repetition.  
**Decision:** Implement test remediation as a bounded fix loop of no more than 20 attempts, with strategy selection based on failure type.  
**Consequences:** CraftedDevAgent must classify failures and adapt remediation behavior accordingly. Infinite or open-ended retry behavior is prohibited. Retry accounting becomes part of workflow state and must be observable.  
**Rejected alternatives:**  
- Retry until success with no hard cap — rejected because it risks non-terminating runs.  
- Use a fixed retry count without failure-type analysis — rejected because the documented strategy is failure-aware.  
- Perform a single remediation pass only — rejected because the pipeline explicitly allows iterative repair.

## [Generate CI workflows through src/ci_workflow.py and target documented runners]
**Status:** Accepted  
**Context:** CI workflow generation is owned by `src/ci_workflow.py`, and the documented pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. Workflow files are written under `.github`, which must be allowlisted explicitly.  
**Decision:** Generate CI workflow definitions through `src/ci_workflow.py` only, and target the documented workflow files and runners unless requirements are updated.  
**Consequences:** CraftedDevAgent cannot emit ad hoc CI files from other modules. CI behavior must remain consistent with the documented Linux and macOS runner split, especially for Swift-related needs. Changes to runner strategy require explicit design updates.  
**Rejected alternatives:**  
- Generate YAML inline from feature code — rejected because workflow ownership is centralized.  
- Use a single runner for all stacks — rejected because the repository explicitly distinguishes Ubuntu and macOS workflows.  
- Write CI files outside `.github` — rejected because GitHub Actions expects `.github`, and path policy already accounts for this root.