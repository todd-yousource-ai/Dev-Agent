# DECISIONS.md

## [Repository documentation is the source of truth]
**Status:** Accepted

**Context:** CraftedApp operates within a repository that separates implementation from governing documentation. The TRDs and PRDs under `forge-docs/` define subsystem requirements, and `forge-standards/` contains persistent architectural constraints. The subsystem must be implemented against those artifacts rather than inferred local conventions.

**Decision:** Treat `forge-docs/` and `forge-standards/` as authoritative inputs for CraftedApp design and implementation. Read and comply with documented TRDs, PRDs, architecture standards, interfaces, conventions, and this decisions file before modifying behavior.

**Consequences:** Implementation must remain aligned with documented requirements even when code appears to permit other approaches. Changes that conflict with repository standards are invalid unless the standards are updated first. Local code comments or ad hoc patterns do not override repository documentation.

**Rejected alternatives:**  
- Using current code behavior as the primary source of truth — rejected because code may lag documented requirements and would allow architectural drift.  
- Treating TRDs as advisory only — rejected because the repository explicitly defines them as governing design inputs.  
- Embedding subsystem-specific rules only in code — rejected because cross-agent and cross-repository consistency depends on shared documentation.

## [Critical files shall be treated as architectural control points]
**Status:** Accepted

**Context:** Several files are explicitly identified as high-impact: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes in these files can affect generation, orchestration, security, GitHub I/O, and CI generation across the subsystem.

**Decision:** Treat the listed critical files as architectural control points. Do not modify them casually; any change must preserve their documented responsibilities and must be reviewed for subsystem-wide impact.

**Consequences:** Implementations touching these files must remain narrowly scoped and compatible with their established contracts. Refactors that move or duplicate their responsibilities must be justified and controlled. New functionality must integrate through these files rather than bypassing them.

**Rejected alternatives:**  
- Allowing unrestricted edits to critical files — rejected because failures in these modules propagate across all pull requests and workflows.  
- Replacing critical-file behavior through parallel modules without updating control points — rejected because it fragments the architecture and weakens enforcement.  
- Ignoring critical-file status for “small” changes — rejected because even small changes in security, orchestration, or CI generation can have broad effects.

## [All repository writes must pass through path security]
**Status:** Accepted

**Context:** Path handling is a security boundary. The repository explicitly identifies `src/path_security.py` as the enforcement point, and GitHub integration lessons learned show that invalid roots or unchecked paths cause rejected or silent failures.

**Decision:** Route every file write, commit target, and generated path for CraftedApp through the path security boundary. Do not write directly to repository paths without validation by the sanctioned path-security mechanism.

**Consequences:** All file-generation and GitHub-write logic must be composed around path validation. Convenience writes, temporary bypasses, and direct filesystem operations are disallowed if they circumvent path security. Security validation becomes a prerequisite for successful generation and commit operations.

**Rejected alternatives:**  
- Validating paths independently in each feature module — rejected because duplicated validation creates inconsistent enforcement and regression risk.  
- Trusting caller-provided paths — rejected because path origin is not a sufficient security guarantee.  
- Applying path checks only at commit time — rejected because unsafe intermediate writes can already violate repository boundaries.

## [Repository root writes are restricted to an explicit allowlist]
**Status:** Accepted

**Context:** GitHub integration lessons learned state that commits to unexpected root directories fail silently or are rejected by guards. Standard valid roots must be explicitly allowlisted, including dot-prefixed roots such as `.github`.

**Decision:** Permit CraftedApp to create or modify files only under explicitly allowlisted repository roots: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`, unless the allowlist is formally expanded.

**Consequences:** New output locations cannot be introduced informally. Features that require writing elsewhere must first add the root to the allowlist through a documented standards change. Dot-prefixed roots remain disallowed unless explicitly listed, with `.github` as the approved exception from the current rules.

**Rejected alternatives:**  
- Allowing writes anywhere under the repository if paths are syntactically valid — rejected because root-level policy enforcement is required by the security model.  
- Inferring valid roots from existing folders in the repo — rejected because presence does not imply approval for automated writes.  
- Blocking dot-prefixed directories entirely — rejected because CI workflow generation requires `.github`.

## [GitHub I/O shall be centralized]
**Status:** Accepted

**Context:** `src/github_tools.py` is designated as the location for GitHub I/O and is responsible for path validation, rate limiting, and SHA protocol handling. Distributing GitHub interactions across the subsystem would bypass those protections and create protocol inconsistencies.

**Decision:** Centralize all CraftedApp GitHub API and repository-content interactions through the sanctioned GitHub tools layer. Do not implement direct or parallel GitHub write/read flows outside that boundary.

**Consequences:** New GitHub operations must be added to or routed through the central GitHub tools module. Rate limiting, SHA handling, and path validation remain consistent across features. Testing and auditing of GitHub behavior stay focused on one integration surface.

**Rejected alternatives:**  
- Calling GitHub APIs directly from feature modules — rejected because it bypasses shared validation and protocol handling.  
- Using separate lightweight clients for different operations — rejected because it duplicates responsibility and risks inconsistent SHA or retry behavior.  
- Handling path security outside the GitHub layer only — rejected because GitHub I/O must enforce both transport and repository integrity constraints.

## [Build and orchestration stages must remain low-complexity]
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` explicitly enforces this limit. CraftedApp orchestration must therefore be decomposed to stay understandable and maintainable.

**Decision:** Keep each CraftedApp pipeline stage and orchestration unit at or below cyclomatic complexity 15. Split logic into smaller functions or components rather than concentrating branching behavior in a single stage.

**Consequences:** Implementers must decompose feature logic early and avoid monolithic stage handlers. Complexity growth is a design failure, not just a style issue. Refactoring toward smaller units is required before adding more branching to an already complex stage.

**Rejected alternatives:**  
- Permitting higher complexity for “core” orchestration modules — rejected because those modules are exactly where maintainability and correctness matter most.  
- Enforcing complexity only at the file level — rejected because stage-level readability and control-flow clarity are the actual requirement.  
- Relying on tests alone instead of complexity limits — rejected because test coverage does not eliminate comprehension and change-risk problems.

## [Pipeline execution shall follow the documented staged flow]
**Status:** Accepted

**Context:** The repository README defines a staged build pipeline including parsing, linting, import checks, iterative fix loops, CI generation, and gating. CraftedApp must behave predictably within that sequence.

**Decision:** Implement CraftedApp work as an ordered staged pipeline consistent with the documented flow: static validation before fix attempts, test and CI generation before final gate, and no stage skipping unless explicitly documented.

**Consequences:** Features cannot reorder pipeline responsibilities arbitrarily. Validation, fixing, testing, and CI generation must occur in a stable sequence so that failures are attributable to a known stage. Short-circuit behavior must be explicit and checkpoint-compatible.

**Rejected alternatives:**  
- Allowing dynamic stage ordering per task — rejected because it reduces predictability and complicates checkpoint semantics.  
- Running tests before static validation — rejected because early inexpensive validation should fail fast before costlier steps.  
- Combining all stages into a single execution block — rejected because it obscures failure modes and undermines checkpointing.

## [Fix loops shall be bounded and failure-aware]
**Status:** Accepted

**Context:** The documented build pipeline includes a fix loop with pytest retries capped at 20 attempts and guided by failure type. CraftedApp must avoid unbounded repair behavior while still supporting iterative correction.

**Decision:** Bound automated test-fix retries to 20 attempts and select remediation strategies based on failure type rather than blind repetition.

**Consequences:** CraftedApp must track retry count and classify failures sufficiently to choose an appropriate next action. Infinite or open-ended repair loops are prohibited. When the retry budget is exhausted, the subsystem must fail the stage and surface the issue for operator or higher-level handling.

**Rejected alternatives:**  
- Retrying until tests pass — rejected because it risks runaway execution and hides systemic faults.  
- Using a very small fixed retry count regardless of failure type — rejected because some issues need iterative correction while still requiring a safe bound.  
- Repeating the same generic fix strategy each time — rejected because the pipeline explicitly expects failure-type-aware behavior.

## [State transitions must be checkpointed]
**Status:** Accepted

**Context:** The build pipeline requires checkpointing of every state transition, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. CraftedApp needs durable execution visibility and recoverability.

**Decision:** Checkpoint every meaningful CraftedApp state transition, including the documented per-PR lifecycle states, before advancing to the next stage.

**Consequences:** The subsystem must persist enough structured state to resume, audit, and diagnose execution. Implicit in-memory progression is insufficient. New states introduced by implementation must also be checkpointed if they affect control flow or recovery.

**Rejected alternatives:**  
- Checkpointing only major milestones such as final success or failure — rejected because intermediate recovery and auditability are required.  
- Logging transitions without structured checkpoints — rejected because logs alone are not reliable execution state.  
- Checkpointing only after side effects complete — rejected because transition intent and partial progress must be visible for recovery.

## [Operator gate is mandatory before merge]
**Status:** Accepted

**Context:** The pipeline defines a gate in which the operator approves or corrects before merge. CraftedApp is therefore not authorized to self-merge solely on automated success.

**Decision:** Require explicit operator approval or correction at the gate stage before any merge action. Do not treat passing tests and CI as sufficient merge authority.

**Consequences:** CraftedApp must surface results for human review and preserve a pause point before merge. Full automation ends at gate readiness unless repository policy is formally changed. Any merge-related automation must verify the gate decision exists.

**Rejected alternatives:**  
- Auto-merging after tests and CI pass — rejected because the documented process reserves final authority for the operator.  
- Making the operator gate optional for low-risk changes — rejected because no such exception is documented.  
- Replacing human approval with heuristic confidence scoring — rejected because confidence is not equivalent to required approval.

## [CI workflow generation must include platform-specific outputs]
**Status:** Accepted

**Context:** The build pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is the critical generator for these workflows, so CraftedApp must preserve this platform distinction.

**Decision:** Generate and maintain CI workflows consistent with the documented platform split: a standard Ubuntu workflow and a macOS workflow for Swift-related execution.

**Consequences:** CraftedApp CI generation cannot collapse all jobs into a single generic workflow when Swift or macOS-specific needs exist. Workflow changes must preserve the repository’s expected filenames and platform intent unless standards are updated. CI generation logic must remain within the sanctioned workflow generator path.

**Rejected alternatives:**  
- Using only a single Ubuntu workflow for all cases — rejected because Swift/macOS requirements are explicitly documented separately.  
- Generating ad hoc workflow names per feature — rejected because stable workflow naming is part of the expected pipeline contract.  
- Moving workflow generation outside the CI workflow module — rejected because that would bypass the designated control point.

## [Gate decisions and stage outcomes must be auditable]
**Status:** Accepted

**Context:** The pipeline documentation states that every gate decision is logged, and checkpointing is required for state transitions. CraftedApp must support later reconstruction of why a PR advanced, stopped, or was corrected.

**Decision:** Record auditable artifacts for stage outcomes and gate decisions in a structured, reviewable form tied to the relevant execution or PR.

**Consequences:** CraftedApp must not rely on ephemeral console output as the sole record of execution. Audit trails must be sufficient to explain approvals, corrections, failures, and progression through the pipeline. This constrains implementation toward durable metadata and consistent event recording.

**Rejected alternatives:**  
- Keeping only transient runtime logs — rejected because they are not a reliable or structured audit record.  
- Recording only failures — rejected because approvals and successful transitions must also be reconstructable.  
- Leaving audit behavior to individual feature implementations — rejected because audit consistency is a subsystem-level requirement.