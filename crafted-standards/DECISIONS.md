# DECISIONS.md

## Repository source of truth must remain in forge-docs
**Status:** Accepted  
**Context:** The subsystem operates in a repository where TRDs and PRDs are the authoritative requirements source. Implementation behavior must be constrained by those documents before code changes are made.  
**Decision:** Read and treat `forge-docs/` as the mandatory source of truth before implementing or modifying CraftedDevAgent behavior. Do not relocate, duplicate, or reinterpret TRD/PRD authority into code comments or ad hoc documentation.  
**Consequences:** Implementation must assume requirements originate from `forge-docs/`. Any feature work, orchestration change, or behavioral adjustment is constrained by the existing document set and must remain consistent with it. Tooling may cache or index these documents, but must not replace them as the canonical source.  
**Rejected alternatives:**  
- Treating inline code documentation as the primary authority — rejected because it drifts from product and technical requirements.  
- Copying TRD content into subsystem-local docs and maintaining both — rejected because duplicate authority causes divergence.  
- Allowing implementation to proceed without reading TRDs first — rejected because it breaks requirement traceability.

## Critical subsystem files must be treated as protected design surfaces
**Status:** Accepted  
**Context:** Several files are called out as high-impact and security-sensitive. Changes to them affect generation, orchestration, GitHub I/O, path validation, and CI workflow generation across the subsystem.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as protected files requiring explicit review of their documented responsibilities before modification. Do not bypass their boundaries with duplicate logic elsewhere.  
**Consequences:** New behavior must integrate through these files’ existing responsibilities instead of reimplementing adjacent mechanisms in other modules. Refactors must preserve their contract roles: generation loop, orchestration, GitHub I/O, security boundary, and CI generation.  
**Rejected alternatives:**  
- Recreating GitHub, path validation, or CI logic in feature-specific modules — rejected because it fragments policy enforcement.  
- Treating all files as equally safe to modify — rejected because these files have system-wide blast radius.  
- Moving security checks closer to call sites only — rejected because centralized enforcement is required.

## All repository writes must pass through centralized path security
**Status:** Accepted  
**Context:** Path security is the explicit security boundary, and write operations outside approved roots can fail silently or be rejected. The subsystem needs a single enforcement point for safe writes.  
**Decision:** Route every filesystem write that targets repository content through `src/path_security.py`. Do not write directly to the repo tree without path validation against allowed roots.  
**Consequences:** File creation, updates, workflow generation, code output, and automated edits must use centralized validation. This constrains implementation to preserve a single write-policy gate and simplifies auditing of write safety.  
**Rejected alternatives:**  
- Performing path checks opportunistically at individual call sites — rejected because coverage becomes inconsistent.  
- Allowing direct writes in “trusted” internal code paths — rejected because trust assumptions erode the security boundary.  
- Validating only user-provided paths but not generated paths — rejected because generated paths can still escape intended roots.

## Repository root allowlisting must be explicit, including dot-prefixed roots
**Status:** Accepted  
**Context:** The agent’s path guards reject or silently fail for unexpected roots unless they are explicitly allowlisted. Standard projects require support for normal code roots and CI workflow roots, including `.github`.  
**Decision:** Enforce an explicit allowlist of valid repository root directories and include dot-prefixed roots such as `.github` as first-class allowed roots when required. At minimum, support the documented standard roots: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`.  
**Consequences:** New write targets must be added intentionally rather than emerging implicitly. Workflow generation and other dot-directory writes remain valid only when explicitly approved. Implementations must not assume leading-dot paths are invalid by default if they are part of the sanctioned layout.  
**Rejected alternatives:**  
- Allowing writes to any existing directory in the repo — rejected because presence does not imply authorization.  
- Blocking all dot-prefixed roots categorically — rejected because CI workflows live in `.github`.  
- Using regex-based permissive matching for “common” roots — rejected because it is harder to reason about and audit than explicit allowlists.

## GitHub repository I/O must remain centralized in github_tools
**Status:** Accepted  
**Context:** GitHub interactions include path validation, rate limiting, and SHA protocol handling. These concerns must be applied consistently to avoid corruption, race conditions, or API misuse.  
**Decision:** Centralize all GitHub read and write operations in `src/github_tools.py`. Do not call GitHub APIs directly from orchestration, generation, or feature modules when repository content is being read or modified.  
**Consequences:** API semantics such as SHA preconditions, retry behavior, and rate-limit handling remain uniform. Feature code must depend on the centralized module instead of embedding custom GitHub request logic.  
**Rejected alternatives:**  
- Letting each module use the GitHub API client directly — rejected because it duplicates protocol handling and weakens controls.  
- Splitting reads and writes across separate ad hoc helpers — rejected because consistency of path and SHA handling is more important than convenience.  
- Bypassing `github_tools` for performance-sensitive paths — rejected because correctness and safety take priority.

## Build pipeline stages must preserve bounded complexity
**Status:** Accepted  
**Context:** The build pipeline defines staged execution and explicitly requires every stage to have maximum cyclomatic complexity of 15. `src/build_director.py` is identified as a critical orchestration file where this limit is strictly enforced.  
**Decision:** Implement and maintain pipeline orchestration such that every stage function or equivalent execution unit stays at cyclomatic complexity 15 or below. Split logic into smaller composable units rather than accumulating branching in stage handlers.  
**Consequences:** Orchestration code must remain modular and auditable. Adding new checks or transitions requires decomposition instead of inflating existing stage complexity. Review must treat complexity regressions as design violations, not style issues.  
**Rejected alternatives:**  
- Allowing orchestration stages to exceed complexity limits when “justified” — rejected because the limit is an architectural control, not a suggestion.  
- Measuring complexity only at file level — rejected because the requirement applies to stages.  
- Deferring decomposition until later refactors — rejected because complexity debt accumulates in the highest-risk control path.

## Pipeline execution must remain stage-oriented with explicit checkpoints
**Status:** Accepted  
**Context:** The documented build pipeline is organized into stages, and every state transition is checkpointed, including per-PR transitions such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. Reliable recovery and auditability depend on explicit state tracking.  
**Decision:** Model CraftedDevAgent execution as discrete stages with checkpointed state transitions. Persist or emit each transition explicitly rather than inferring progress from side effects.  
**Consequences:** Restart, recovery, operator inspection, and debugging must rely on durable stage/state records. Implementations cannot collapse multiple transitions into opaque “done” markers. New stages or sub-states must integrate with the checkpoint model.  
**Rejected alternatives:**  
- Inferring state from repository contents or branch names alone — rejected because side effects are ambiguous and hard to recover from.  
- Tracking only start and finish of the whole pipeline — rejected because per-stage and per-PR visibility is required.  
- Using transient in-memory state only — rejected because crashes would destroy execution history.

## Test remediation must use bounded, failure-aware retry loops
**Status:** Accepted  
**Context:** The pipeline specifies a fix loop with `pytest` up to 20 attempts and a failure-type-aware strategy. This constrains both retry count and the logic used to respond to failures.  
**Decision:** Limit automated test-fix retries to 20 attempts and make retry behavior sensitive to failure type. Do not implement unbounded or uniform retry loops.  
**Consequences:** Automated remediation remains predictable in cost and behavior. Error handling must classify failures sufficiently to choose an appropriate strategy instead of applying the same patching approach repeatedly.  
**Rejected alternatives:**  
- Retrying until success — rejected because it can loop indefinitely and hide systemic failures.  
- Using a single generic remediation strategy for all failures — rejected because different failure classes require different responses.  
- Reducing retries to a trivial fixed small number with no classification — rejected because it underutilizes the documented repair loop.

## CI workflow generation must target documented environments
**Status:** Accepted  
**Context:** CI is part of the pipeline and includes `crafted-ci.yml` on `ubuntu-latest` plus `crafted-ci-macos.yml` for Swift. Workflow generation is handled by a critical file and depends on `.github` being an allowed root.  
**Decision:** Generate CI workflows that match the documented environment targets: `crafted-ci.yml` for `ubuntu-latest` and `crafted-ci-macos.yml` for Swift/macOS scenarios. Place them under `.github` only through approved path security and workflow generation paths.  
**Consequences:** CI support remains consistent with platform requirements and repository layout constraints. Implementations must not silently rename, relocate, or merge these workflows into incompatible formats without an explicit architectural change.  
**Rejected alternatives:**  
- Generating a single universal workflow for all languages and platforms — rejected because the documented pipeline distinguishes Ubuntu and macOS/Swift needs.  
- Writing workflows directly without path-security approval — rejected because `.github` is a controlled root.  
- Using nonstandard runner targets by default — rejected because the documented environments are part of the expected contract.

## Operator approval must remain a gate before merge
**Status:** Accepted  
**Context:** The build pipeline includes a gate where the operator approves or corrects before merge, and every gate decision must be checkpointed. Human oversight is therefore an architectural requirement, not an optional UI feature.  
**Decision:** Require an explicit operator gate before merge and checkpoint the decision. Do not implement automatic merge-on-green as the default path for CraftedDevAgent.  
**Consequences:** The subsystem must expose merge readiness to an operator and preserve the approval or correction outcome as part of execution state. Fully autonomous merge behavior is constrained unless separately authorized by a future decision.  
**Rejected alternatives:**  
- Auto-merging immediately after CI passes — rejected because the documented process requires operator approval.  
- Treating operator review as advisory logging only — rejected because the gate is a control point.  
- Recording approvals outside the checkpointed state model — rejected because gate decisions must be durable and auditable.