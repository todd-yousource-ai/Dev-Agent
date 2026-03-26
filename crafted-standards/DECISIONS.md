# DECISIONS.md

## [Treat forge-docs as the authoritative design input]
**Status:** Accepted

**Context:** CraftedAgent behavior is constrained by TRDs and PRDs stored in `forge-docs/`. The repository specification explicitly states that all TRDs and PRDs live there and must be read before building. Without a single source of truth, agent behavior drifts from approved design intent.

**Decision:** Read and treat `forge-docs/` as the authoritative source of subsystem requirements before implementing or modifying CraftedAgent behavior.

**Consequences:** Implementation must align with documents in `forge-docs/` first, not inferred behavior from code alone. Changes that contradict TRDs require document updates before implementation updates. Build logic, workflow, security, and integration decisions must be traceable to those documents.

**Rejected alternatives:**  
- Treating source code as the sole source of truth — rejected because the repository explicitly defines TRDs/PRDs as governing design inputs.  
- Using ad hoc developer notes or issue threads as equivalent authority — rejected because they are not guaranteed to be complete, reviewed, or canonical.  
- Reading only the TRD most closely related to the touched module — rejected because cross-cutting constraints span security, CI, GitHub integration, and coordination documents.

## [Read critical subsystem files before modification]
**Status:** Accepted

**Context:** Several files are designated as critical because they define core generation, orchestration, security boundaries, GitHub I/O, and CI workflow generation. Modifying behavior around these areas without understanding the designated files risks breaking global agent behavior.

**Decision:** Read the designated critical files before modifying CraftedAgent logic that touches generation flow, orchestration, GitHub operations, path validation, or CI workflow generation.

**Consequences:** Work affecting `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, or `src/ci_workflow.py` must begin with review of those files. Implementations must preserve their invariants and avoid bypassing them through parallel logic.

**Rejected alternatives:**  
- Allowing direct modifications based only on local call-site context — rejected because these files carry system-wide invariants not visible from a single caller.  
- Re-implementing security or GitHub logic in new modules — rejected because that fragments control and undermines the designated boundaries.  
- Treating critical-file guidance as advisory only — rejected because the listed files are explicitly called out as required reading before modification.

## [Centralize all GitHub I/O in github_tools]
**Status:** Accepted

**Context:** `src/github_tools.py` is identified as the module responsible for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. GitHub writes and reads are high-risk integration points and require consistent behavior.

**Decision:** Route all GitHub API interactions for CraftedAgent through `src/github_tools.py`; do not perform repository I/O through ad hoc clients or duplicated logic elsewhere.

**Consequences:** Rate limiting, SHA handling, path validation, and failure behavior remain consistent. New features that need GitHub access must extend or call the central GitHub tools layer rather than bypassing it. Testing and auditing are simplified because integration logic has a single control point.

**Rejected alternatives:**  
- Letting each feature module call the GitHub API directly — rejected because it duplicates protocol handling and creates inconsistent error behavior.  
- Splitting reads and writes across separate helper modules — rejected because correctness depends on shared path, SHA, and rate-limit semantics.  
- Using shell-based `git` or `gh` calls as a peer path to the API layer — rejected because that bypasses centralized safeguards and makes behavior environment-dependent.

## [Enforce path security through a single write boundary]
**Status:** Accepted

**Context:** `src/path_security.py` is defined as the security boundary, and every write path must pass through it. GitHub integration lessons also show that invalid roots fail or are rejected by path security guards, especially for unexpected roots and dot-prefixed directories.

**Decision:** Require every filesystem or repository write path used by CraftedAgent to be validated through `src/path_security.py` before write operations occur.

**Consequences:** No write implementation may bypass path validation, even for internal tooling or generated CI files. Security policy remains enforceable in one place. Features that create files in new directories must update the allowlist rather than introducing local exceptions.

**Rejected alternatives:**  
- Performing lightweight caller-side path checks — rejected because distributed checks are inconsistent and easy to bypass.  
- Validating only local filesystem writes but not GitHub commits — rejected because both are write surfaces with the same path traversal risk.  
- Allowing privileged modules to skip validation — rejected because security boundaries are only reliable when universal.

## [Maintain an explicit root-directory allowlist]
**Status:** Accepted

**Context:** The subsystem has learned that committing to unexpected root directories fails silently or is rejected by security guards. Standard project roots must be explicitly allowed, and `.github` requires special handling because dot-prefixed roots are commonly blocked by validators.

**Decision:** Restrict CraftedAgent write targets to an explicit allowlist of repository root directories, including `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`, unless the allowlist is deliberately expanded.

**Consequences:** Generated changes must stay within approved repository roots. Any feature requiring writes outside these roots must first update the allowlist and related validation tests. CI workflow generation into `.github` remains supported because that root is explicitly permitted.

**Rejected alternatives:**  
- Allowing arbitrary repository-relative paths — rejected because it weakens path security and causes silent failures against repo guards.  
- Inferring allowed roots from the current repository contents — rejected because presence does not imply approval.  
- Blocking dot-prefixed roots entirely — rejected because CI workflow files under `.github` are required.

## [Preserve the staged build pipeline as the execution model]
**Status:** Accepted

**Context:** The README defines a staged pipeline, including validation, a fix loop, CI generation, and operator gating. CraftedAgent is part of this broader execution model and must behave consistently with it.

**Decision:** Implement and evolve CraftedAgent behavior within the defined staged build pipeline rather than using an unstructured generate-and-commit flow.

**Consequences:** Generation, validation, fix attempts, CI preparation, and approval remain separate concerns with explicit transitions. New capabilities must fit into an existing stage or introduce a clearly bounded new stage. Observability and recovery depend on preserving stage boundaries.

**Rejected alternatives:**  
- A monolithic one-pass generation flow — rejected because it reduces fault isolation and makes retries coarse and brittle.  
- Immediate commit after generation — rejected because validation, testing, and operator gates are required before merge.  
- Allowing each agent mode to define its own pipeline semantics — rejected because shared operational guarantees depend on uniform stages.

## [Checkpoint every state transition]
**Status:** Accepted

**Context:** The pipeline specification requires that every state transition be checkpointed, including per-PR states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. Checkpointing is necessary for resumability, auditability, and controlled recovery.

**Decision:** Persist a checkpoint at every CraftedAgent stage transition and at each required per-PR lifecycle milestone.

**Consequences:** The subsystem must be resumable without replaying the full workflow from the beginning. State models and storage must represent the required milestones explicitly. Error recovery, operator inspection, and audit trails depend on these persisted checkpoints.

**Rejected alternatives:**  
- Checkpointing only on success at the end of a run — rejected because failures in intermediate stages would be opaque and expensive to recover from.  
- Logging transitions without durable checkpoints — rejected because logs do not provide authoritative resumable state.  
- Checkpointing only operator-visible gates — rejected because internal stage boundaries also matter for retries and debugging.

## [Enforce cyclomatic complexity limits per stage-critical implementation]
**Status:** Accepted

**Context:** The repository explicitly states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` notes that this limit is strictly enforced. CraftedAgent orchestration is especially prone to accumulating branching logic.

**Decision:** Keep each stage implementation and stage-critical orchestration path at cyclomatic complexity 15 or below; refactor branching logic instead of exceeding the limit.

**Consequences:** Orchestration code must be decomposed into smaller functions or strategy objects when complexity grows. Stage handlers must remain understandable, testable, and reviewable. Complexity regressions are treated as design violations, not stylistic concerns.

**Rejected alternatives:**  
- Allowing higher complexity in orchestration because workflow code is inherently branchy — rejected because this is the exact area where maintainability most degrades.  
- Applying the limit only to new code — rejected because existing critical paths are also governed by the repository rule.  
- Waiving the limit for “temporary” exception handling paths — rejected because temporary branches tend to become permanent.

## [Retain a bounded, failure-aware test fix loop]
**Status:** Accepted

**Context:** The build pipeline includes a fix loop driven by `pytest`, capped at 20 attempts, with failure-type-aware strategy. This places an explicit upper bound on self-healing behavior and requires retries to be informed by observed failure modes.

**Decision:** Implement test remediation as a bounded loop of at most 20 attempts and vary fix strategy based on failure type rather than retrying blindly.

**Consequences:** CraftedAgent cannot enter unbounded repair cycles. Retry logic must classify failures sufficiently to choose targeted corrective actions. When the attempt limit is reached, control must escalate rather than continuing speculative edits.

**Rejected alternatives:**  
- Retrying until tests pass — rejected because it risks infinite loops, wasted resources, and repository churn.  
- A single retry only — rejected because complex but recoverable failures often need iterative correction.  
- Uniform retry behavior for all failures — rejected because syntax, import, test assertion, and environment failures require different responses.

## [Generate CI workflows in the designated workflow generator]
**Status:** Accepted

**Context:** `src/ci_workflow.py` is explicitly identified as the module that generates workflow files, and the pipeline requires `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift/macOS scenarios. Workflow generation must remain consistent with repository and platform requirements.

**Decision:** Generate CI workflow artifacts through `src/ci_workflow.py` and preserve the standard workflow outputs and platform targets required by the pipeline.

**Consequences:** Workflow file structure and naming remain centralized and predictable. Features that need CI changes must modify the generator rather than writing workflow YAML ad hoc. Support for `.github` output depends on the explicit root allowlist and path security flow.

**Rejected alternatives:**  
- Emitting workflow YAML directly from feature modules — rejected because it duplicates CI conventions and bypasses central validation.  
- Maintaining only one generic workflow for all platforms — rejected because Swift/macOS requires a distinct macOS workflow.  
- Hand-editing workflow files outside the generator path — rejected because generated CI behavior must remain deterministic and auditable.

## [Require an operator gate before merge]
**Status:** Accepted

**Context:** The pipeline defines Stage 6 as a gate where an operator approves or corrects before merge. Automated generation and repair can improve throughput, but final merge authority remains human-controlled.

**Decision:** Do not allow CraftedAgent to merge autonomously; require operator approval or correction before merge.

**Consequences:** The subsystem may prepare branches, commits, tests, and CI results, but final merge remains outside fully autonomous control. UX, state models, and notifications must support pending human review. Success criteria for automation stop at readiness for approval, not self-merging completion.

**Rejected alternatives:**  
- Fully autonomous merge after tests and CI pass — rejected because the pipeline explicitly requires an operator gate.  
- Approval only for high-risk changes — rejected because the stated process requires operator approval before merge generally, not selectively.  
- Post-merge human review — rejected because it defeats the preventative purpose of the gate.