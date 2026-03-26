# DECISIONS.md

## Repository structure documents are source of truth
**Status:** Accepted

**Context:** CraftedApp is implemented inside a repository whose governing technical requirements are defined in TRDs and related standards documents. The repository structure explicitly places all TRDs and PRDs in `forge-docs/`, and repository-wide standards in `forge-standards/`. Implementation decisions for CraftedApp must remain traceable to those documents rather than local convention or inferred behavior.

**Decision:** Treat `forge-docs/` and `forge-standards/` as the authoritative specification inputs for CraftedApp. Require implementers to read relevant TRDs and standards before changing subsystem behavior.

**Consequences:**  
- CraftedApp implementation must align with documented requirements, not ad hoc assumptions.  
- Changes that conflict with TRDs or standards must be resolved by updating the governing documents first.  
- Local code comments or README guidance may clarify behavior, but must not override the source documents.  
- Development workflows must preserve these directories and keep them accessible to builders and agents.

**Rejected alternatives:**  
- Treating code as the sole source of truth was rejected because it allows drift from approved technical requirements.  
- Using README files alone as governing specification was rejected because the repository structure explicitly assigns that role to TRDs and standards documents.  
- Allowing subsystem-specific conventions to supersede repository standards was rejected because it would fragment behavior across subsystems.

## Critical files are protected change boundaries
**Status:** Accepted

**Context:** The repository identifies a set of critical files whose behavior affects generation, orchestration, GitHub I/O, path security, and CI workflow generation. Changes in these files have outsized system impact and can compromise CraftedApp correctness or security if modified casually.

**Decision:** Treat the listed critical files as protected change boundaries. Require any CraftedApp changes touching them to preserve their documented responsibilities and validate cross-cutting effects before merge.

**Consequences:**  
- Modifications to `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` must be reviewed for subsystem-wide impact.  
- CraftedApp features must integrate with these files through stable responsibilities rather than bypassing them.  
- Implementations must not reimplement path security, GitHub write behavior, orchestration, or CI generation in parallel modules.  
- Testing and review scope must expand when these files are changed.

**Rejected alternatives:**  
- Allowing unrestricted edits to critical files as ordinary implementation detail was rejected because these files define security and orchestration boundaries.  
- Duplicating critical behavior in CraftedApp-local modules was rejected because it would create inconsistent enforcement and maintenance risk.  
- Bypassing critical files for performance or convenience was rejected because it weakens repository-wide guarantees.

## All write paths must pass through path security enforcement
**Status:** Accepted

**Context:** The repository explicitly identifies `src/path_security.py` as the security boundary and notes that every write path must pass through it. GitHub integration lessons further show that unexpected root directories are rejected or fail silently unless explicitly allowed.

**Decision:** Route every CraftedApp filesystem or repository write through the shared path security layer before execution.

**Consequences:**  
- CraftedApp must not write files directly to disk or repository APIs without path validation.  
- Any new destination used by CraftedApp must be evaluated against the allowlist model.  
- Security review for CraftedApp includes verification that no alternate write path bypasses the shared validator.  
- Failures caused by invalid roots must be surfaced clearly rather than hidden behind generic write errors.

**Rejected alternatives:**  
- Performing ad hoc path checks inside CraftedApp was rejected because it duplicates and weakens the central security boundary.  
- Validating only local filesystem writes but not GitHub-backed writes was rejected because both create repository state.  
- Allowing direct writes in trusted code paths was rejected because trust assumptions erode over time and defeat uniform enforcement.

## Repository root writes are limited to explicit allowlisted directories
**Status:** Accepted

**Context:** GitHub integration lessons state that committing to unexpected root directories fails silently or is rejected by path guards. The standard project allowlist includes `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`, with dot-prefixed roots such as `.github` requiring explicit allowlisting.

**Decision:** Restrict CraftedApp-created or modified repository paths to explicitly allowlisted root directories, and require explicit approval before introducing any additional root.

**Consequences:**  
- CraftedApp features must place outputs only under approved roots.  
- Dot-prefixed roots, especially `.github`, must be explicitly handled rather than assumed valid.  
- New output categories require an allowlist update before implementation.  
- Path planning is a design concern, not a late-stage implementation detail.

**Rejected alternatives:**  
- Permitting writes to arbitrary repository roots was rejected because path security guards will reject or silently fail such operations.  
- Inferring allowed roots from existing files was rejected because presence does not equal authorization.  
- Allowing wildcard root patterns was rejected because they reduce the precision of security enforcement.

## GitHub I/O must be centralized in shared tooling
**Status:** Accepted

**Context:** The repository designates `src/github_tools.py` as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. CraftedApp depends on repository interactions that must remain consistent with these cross-cutting controls.

**Decision:** Perform all CraftedApp GitHub reads and writes through the shared GitHub tooling layer; do not call GitHub APIs directly from subsystem-specific code.

**Consequences:**  
- CraftedApp inherits path validation, SHA handling, and rate-limiting behavior from a single implementation.  
- API behavior stays consistent across subsystems and PR flows.  
- Direct client usage inside CraftedApp is prohibited unless first absorbed into shared tooling.  
- Testing can focus on shared GitHub behavior rather than duplicate implementations.

**Rejected alternatives:**  
- Calling GitHub APIs directly from CraftedApp was rejected because it bypasses shared security and protocol handling.  
- Creating a separate CraftedApp GitHub client was rejected because it duplicates logic and risks divergence in SHA and rate-limit behavior.  
- Using shell-based Git commands as the primary integration layer was rejected because the repository standardizes GitHub I/O in shared tooling.

## Build pipeline stages are mandatory and ordered
**Status:** Accepted

**Context:** The build pipeline defines a staged flow ending with testing, CI, and an operator gate. The documented stages include static validation steps and a fix loop, and the pipeline structure is part of the repository’s operating model.

**Decision:** Implement CraftedApp changes to participate in the defined build pipeline stages in the documented order, without skipping validation, test, CI, or gate stages.

**Consequences:**  
- CraftedApp work products must pass parse, lint, import, test, and CI stages before merge.  
- Pipeline integrations must preserve the expected sequencing of generation, validation, fix loop, CI, and approval.  
- Subsystem features may add checks, but must not remove or reorder required gates.  
- Failures must be handled at the appropriate pipeline stage rather than deferred to later stages.

**Rejected alternatives:**  
- Allowing CraftedApp to use a shortened pipeline for faster iteration was rejected because it weakens repository-wide quality controls.  
- Reordering validation after tests was rejected because early static checks are intended to fail fast.  
- Making operator approval optional was rejected because the pipeline explicitly includes a gate before merge.

## Cyclomatic complexity per stage is capped at 15
**Status:** Accepted

**Context:** The repository README states that every stage has a maximum cyclomatic complexity of 15, and specifically calls out `src/build_director.py` as a location where the complexity 15 limit is strictly enforced. CraftedApp orchestration must conform to this constraint.

**Decision:** Keep each CraftedApp pipeline stage and orchestration unit at cyclomatic complexity 15 or lower, refactoring into smaller units when needed.

**Consequences:**  
- CraftedApp implementation must prefer composition over large control-heavy functions.  
- Stage logic that grows beyond the limit must be split before merge.  
- Complexity control becomes a design-time requirement, not just a linting afterthought.  
- Reviews must evaluate orchestration changes for structural simplicity as well as correctness.

**Rejected alternatives:**  
- Allowing higher complexity in “central” orchestration code was rejected because that is where maintainability risk is highest.  
- Enforcing complexity only at file level was rejected because the documented requirement is stage-oriented.  
- Waiving the cap for generated or temporary logic was rejected because such logic still becomes maintenance burden.

## State transitions must be checkpointed
**Status:** Accepted

**Context:** The build pipeline documentation requires every state transition to be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. CraftedApp participates in this lifecycle and must preserve recoverability and auditability.

**Decision:** Checkpoint every CraftedApp state transition in the pipeline, including the documented per-PR milestone states.

**Consequences:**  
- CraftedApp must emit or persist transition records at each required state boundary.  
- Recovery, resume, and audit behavior must use checkpointed state rather than inferred progress.  
- Partial execution must be observable and restartable from known states.  
- Hidden in-memory progress without durable checkpoints is not sufficient.

**Rejected alternatives:**  
- Checkpointing only final success or failure was rejected because intermediate recoverability is explicitly required.  
- Inferring state from branch contents or logs was rejected because it is ambiguous and brittle.  
- Using best-effort transient checkpoints was rejected because the requirement is for actual state transition checkpointing.

## CI workflow generation must include platform-specific workflows
**Status:** Accepted

**Context:** The documented pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. The repository also identifies `src/ci_workflow.py` as the generator for workflow output, making CI definition a controlled shared capability.

**Decision:** Generate and maintain CraftedApp CI workflows through the shared CI workflow generator, including Ubuntu and macOS workflows when platform requirements apply.

**Consequences:**  
- CraftedApp must not handcraft divergent CI workflow files outside the shared generation path.  
- Swift or macOS-relevant functionality must be covered by the macOS workflow.  
- Linux-compatible validation remains covered by the Ubuntu workflow.  
- CI changes must be implemented in generator logic rather than edited independently in emitted files.

**Rejected alternatives:**  
- Maintaining handcrafted workflow YAML directly in `.github` was rejected because CI generation is centralized in `src/ci_workflow.py`.  
- Using only Ubuntu CI for all CraftedApp behavior was rejected because Swift and macOS-specific validation require dedicated workflow coverage.  
- Generating workflows in subsystem-local code was rejected because it duplicates a shared responsibility.

## Operator approval is required before merge
**Status:** Accepted

**Context:** The pipeline defines a final gate where the operator approves or corrects before merge, and the README states that every gate decision is checkpointed. CraftedApp must not bypass human review at the final integration step.

**Decision:** Require explicit operator approval before merging CraftedApp changes, and checkpoint that gate decision.

**Consequences:**  
- Fully automated merge of CraftedApp output is disallowed by default.  
- CraftedApp workflows must surface enough context for operator review and correction.  
- Approval and correction outcomes must be recorded as part of the checkpointed process.  
- Deployment confidence depends on preserving a human-controlled final gate.

**Rejected alternatives:**  
- Auto-merging after CI success was rejected because the documented process requires an operator gate.  
- Treating review comments as implicit approval was rejected because the gate requires an explicit decision.  
- Skipping gate checkpointing was rejected because all gate decisions must be recorded.