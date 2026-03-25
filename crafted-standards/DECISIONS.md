# DECISIONS.md

## [Adopt TRDs and PRDs in `forge-docs/` as the source of truth]
**Status:** Accepted  
**Context:** The CraftedDevAgent subsystem operates inside a repository where all TRDs and PRDs are centralized under `forge-docs/`. The repository structure explicitly states that these documents must be read before building. Without a single authoritative source, implementation behavior can drift from product and technical requirements.  
**Decision:** Treat documents in `forge-docs/` as the authoritative requirements source and require the subsystem to align implementation behavior with them before making design or code changes.  
**Consequences:** Implementation must be constrained by documented requirements rather than inferred behavior. Changes that conflict with TRDs/PRDs are non-compliant unless the source documents are updated first. Build and orchestration logic must assume that repository-resident documentation governs agent behavior.  
**Rejected alternatives:**  
- Using code as the primary source of truth was rejected because existing code may lag intended architecture and would permit requirement drift.  
- Distributing requirements across multiple directories was rejected because it weakens discoverability and increases the chance of partial reads.  
- Treating documentation as advisory only was rejected because the subsystem must produce deterministic, reviewable behavior tied to approved specifications.

## [Preserve and treat designated critical files as controlled interfaces]
**Status:** Accepted  
**Context:** Several files are identified as critical because they define core generation, orchestration, GitHub I/O, path security, and CI workflow behavior. Modifying these files without explicit awareness risks system-wide regressions and security violations.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as controlled interfaces that require explicit review of their stated responsibilities before modification.  
**Consequences:** Implementation work touching these files must preserve their subsystem boundaries and invariants. New functionality should be added without bypassing these components’ responsibilities. Refactors that obscure or redistribute their responsibilities are constrained.  
**Rejected alternatives:**  
- Treating all source files as equally mutable was rejected because these files carry disproportionate architectural and security impact.  
- Copying logic from critical files into new modules was rejected because it would fragment responsibility and weaken enforcement points.  
- Bypassing critical files for convenience was rejected because it would undermine orchestration, security validation, and GitHub protocol correctness.

## [Enforce path writes through the path security boundary]
**Status:** Accepted  
**Context:** The repository explicitly identifies `src/path_security.py` as the security boundary and notes that every write path must pass through it. GitHub integration lessons also show that unexpected roots fail or are rejected by path guards.  
**Decision:** Route every filesystem or repository write path through the path security boundary and forbid direct writes that do not pass validation.  
**Consequences:** All file creation, modification, and commit preparation logic must integrate with centralized path validation. Implementations cannot write directly to arbitrary paths, even when paths appear internally generated or trusted. Security review can rely on a single enforcement boundary.  
**Rejected alternatives:**  
- Allowing trusted internal callers to bypass validation was rejected because trust assumptions erode over time and create inconsistent enforcement.  
- Validating paths independently in each module was rejected because duplicated logic leads to divergence and incomplete coverage.  
- Applying validation only at commit time was rejected because unsafe intermediate writes can still cause damage before commit assembly.

## [Use an explicit allowlist of repository root directories]
**Status:** Accepted  
**Context:** GitHub integration lessons learned state that commits to unexpected root directories fail silently or are rejected by security guards. Standard projects require explicit root allowlisting, including dot-prefixed roots such as `.github`.  
**Decision:** Maintain and enforce an explicit allowlist of writable repository root directories, including at minimum `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs` where applicable.  
**Consequences:** The subsystem must reject writes outside allowed roots unless the allowlist is intentionally updated. Dot-prefixed roots must be handled deliberately rather than filtered by generic validators. Repository bootstrapping and GitHub operations must remain consistent with path security rules.  
**Rejected alternatives:**  
- Permitting writes to any existing directory was rejected because existence is not equivalent to authorization.  
- Using a denylist of prohibited roots was rejected because it is brittle and fails open when new directories appear.  
- Excluding dot-prefixed directories by default was rejected because CI workflows in `.github` are a required supported case.

## [Centralize all GitHub I/O in `src/github_tools.py`]
**Status:** Accepted  
**Context:** `src/github_tools.py` is designated as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. GitHub interactions are error-prone and tightly coupled to repository safety and commit correctness.  
**Decision:** Perform all GitHub reads, writes, commit assembly, and related protocol operations through `src/github_tools.py` and do not introduce parallel GitHub access paths.  
**Consequences:** API behavior, retries, rate limiting, path checks, and SHA handling remain consistent across the subsystem. New features requiring GitHub access must extend the centralized tooling instead of embedding ad hoc client calls. Operational debugging and auditing are simplified.  
**Rejected alternatives:**  
- Letting each module call GitHub APIs directly was rejected because it would duplicate protocol logic and increase inconsistency.  
- Splitting GitHub write and read logic across separate utilities was rejected because SHA and validation concerns cross both directions and benefit from co-location.  
- Wrapping GitHub calls only at higher orchestration layers was rejected because lower-level direct access would still remain possible and unsafe.

## [Keep `src/consensus.py` as the core generation loop authority]
**Status:** Accepted  
**Context:** The critical file list identifies `src/consensus.py` as the core generation loop, and changes there affect every PR the agent builds. The CraftedDevAgent subsystem depends on consistent generation behavior across all downstream stages.  
**Decision:** Preserve `src/consensus.py` as the authoritative implementation point for the core generation loop and require generation-flow changes to be made there rather than dispersed across orchestration or integration modules.  
**Consequences:** Core generation semantics remain centralized and easier to reason about. Behavior that affects all PRs cannot be hidden in feature-specific modules. Testing strategy can focus on one authoritative loop for cross-cutting generation changes.  
**Rejected alternatives:**  
- Embedding generation branching logic in pipeline stages was rejected because it couples generation semantics to orchestration details.  
- Allowing per-integration custom generation loops was rejected because it would create inconsistent PR outputs.  
- Replacing the central loop with multiple specialized loops was rejected because the system requires a predictable shared path for all generated changes.

## [Keep pipeline orchestration in `src/build_director.py` with a strict complexity ceiling]
**Status:** Accepted  
**Context:** `src/build_director.py` is identified as the orchestration point, and the repository documentation states that every stage has a maximum cyclomatic complexity of 15. This implies orchestration must remain decomposed and auditable.  
**Decision:** Implement pipeline orchestration in `src/build_director.py` while enforcing a strict cyclomatic complexity limit of 15 for each stage and for logic added there.  
**Consequences:** New stage behavior must be factored into helpers or smaller units rather than accumulated into deeply branching orchestration code. The subsystem is constrained toward explicit, testable stage boundaries. Complexity becomes a design limit, not just a lint target.  
**Rejected alternatives:**  
- Allowing orchestration complexity to grow when functionality expands was rejected because it degrades maintainability and weakens failure reasoning.  
- Moving orchestration into many disconnected modules was rejected because a single director is needed for stage visibility and checkpoint control.  
- Enforcing complexity only at file level was rejected because stage-level readability and auditability are the actual operational concern.

## [Model the build pipeline as explicit staged execution]
**Status:** Accepted  
**Context:** The README describes a staged build pipeline, including parse/lint/import checks, a pytest-based fix loop, CI workflow execution, and a gated merge process. The subsystem must behave in a structured, repeatable way rather than as a monolithic task runner.  
**Decision:** Implement CraftedDevAgent execution as explicit sequential stages with named transitions, rather than as an unstructured end-to-end procedure.  
**Consequences:** Each stage can be checkpointed, observed, retried, and reviewed independently. Failures can be localized to a stage. Adding capabilities must respect stage boundaries and transition semantics.  
**Rejected alternatives:**  
- Using a single monolithic run method was rejected because it obscures progress, complicates retry behavior, and weakens auditability.  
- Relying on implicit stage inference from logs was rejected because state must be machine-readable and persistent.  
- Allowing arbitrary stage ordering per task was rejected because the documented pipeline expects predictable progression.

## [Checkpoint every state transition, including per-PR progression]
**Status:** Accepted  
**Context:** The repository README states that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This supports recovery, observability, and gating.  
**Decision:** Persist a checkpoint for every state transition in the subsystem, including all per-PR lifecycle milestones and gate decisions.  
**Consequences:** The subsystem must maintain durable transition records rather than only ephemeral runtime state. Recovery logic must resume from checkpoints instead of recomputing uncertain state. Implementations are constrained to explicit transition naming and persistence.  
**Rejected alternatives:**  
- Checkpointing only major milestones was rejected because intermediate states are required for safe resume and audit trails.  
- Keeping transitions only in logs was rejected because logs are not structured state stores and are poor recovery mechanisms.  
- Reconstructing state from Git history after failure was rejected because not all transitions map cleanly to commits or remote events.

## [Limit the automated pytest fix loop to 20 attempts]
**Status:** Accepted  
**Context:** The documented build pipeline specifies a fix loop that runs pytest with up to 20 attempts and uses failure-type-aware strategy. Unbounded repair loops risk wasted compute, non-termination, and unclear operator expectations.  
**Decision:** Cap the automated pytest-driven fix loop at 20 attempts and require the loop to terminate when the cap is reached.  
**Consequences:** The subsystem must surface unresolved failures instead of retrying indefinitely. Strategy logic must operate within a bounded remediation budget. Monitoring and operator review can assume a known maximum retry count.  
**Rejected alternatives:**  
- Allowing unlimited retries was rejected because it risks non-terminating runs and cost blowouts.  
- Using a very small fixed retry count was rejected because iterative repair requires enough attempts to converge on common failures.  
- Making the cap entirely operator-defined at runtime was rejected because the documented standard requires predictable default behavior.

## [Generate CI workflows in a dedicated workflow module and support both Ubuntu and macOS cases]
**Status:** Accepted  
**Context:** `src/ci_workflow.py` is designated as the workflow generator. The repository README specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift/macOS cases. CI generation must therefore be deliberate and support platform-specific outputs.  
**Decision:** Generate CI workflow files exclusively through `src/ci_workflow.py`, including support for standard Ubuntu workflows and separate macOS workflows when the project requires Swift or macOS execution.  
**Consequences:** Workflow structure remains centralized and consistent. Implementations cannot handcraft workflow YAML in unrelated modules. Platform-specific CI behavior must be represented as an explicit supported variant rather than improvised output.  
**Rejected alternatives:**  
- Emitting workflow YAML directly from orchestration code was rejected because it mixes pipeline control with artifact generation.  
- Supporting only Ubuntu workflows was rejected because documented macOS/Swift scenarios require dedicated handling.  
- Using a single polymorphic workflow file for all cases was rejected because the repository standard explicitly distinguishes Ubuntu and macOS workflow artifacts.

## [Require an operator gate before merge]
**Status:** Accepted  
**Context:** The build pipeline defines a final gate where the operator approves or corrects before merge. This is a control point ensuring that automated generation and testing do not bypass human oversight.  
**Decision:** Require an explicit operator approval or correction step before merge completion and do not allow the subsystem to auto-merge solely on prior stage success.  
**Consequences:** Merge completion is constrained by human review. Automation can prepare branches, commits, and CI results, but final promotion remains gated. The subsystem must preserve enough state and artifacts to support operator review.  
**Rejected alternatives:**  
- Fully automatic merge after green CI was rejected because the documented process includes a mandatory human gate.  
- Optional operator review only for failures was rejected because the gate is a standard stage, not an exception path.  
- Delaying human review until after merge was rejected because it defeats the purpose of a pre-merge control point.