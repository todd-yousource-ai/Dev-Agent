# DECISIONS.md

## [Adopt the documented repository layout as a hard contract]
**Status:** Accepted

**Context:** CraftedAgent operates inside a larger repository with a defined structure. The TRDs and README establish that `forge-docs/` contains the source-of-truth requirements, `forge-standards/` contains engineering standards and generated rules, and implementation code lives under the repository layout described in the standards. Agent behavior must be constrained by this structure to avoid writing to ambiguous or unintended locations.

**Decision:** Treat the documented repository layout as a hard contract. Read requirements from `forge-docs/`, treat `forge-standards/` as normative implementation guidance, and only generate or modify files within the project layout approved by repository and path-security rules.

**Consequences:** Implementation must not infer alternate layouts at runtime or create ad hoc top-level directories. File discovery, code generation, and commit planning must be rooted in the documented structure. Any change to repository layout requires an explicit standards update rather than silent agent adaptation.

**Rejected alternatives:**  
- **Infer repository structure dynamically from existing files:** Rejected because it makes behavior nondeterministic across repositories and can normalize accidental drift.  
- **Allow the agent to create new top-level roots as needed:** Rejected because it violates path-security expectations and increases the chance of silent or rejected commits.  
- **Treat documentation directories as advisory only:** Rejected because TRDs are explicitly the source of truth and must constrain implementation behavior.

## [Require pre-modification review of critical subsystem files]
**Status:** Accepted

**Context:** Several files are identified as critical because they form the control plane and security boundary of the agent: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes to these files have system-wide effects and can break orchestration, security, or CI generation.

**Decision:** Require explicit pre-modification review of the listed critical files before changing behavior that touches generation loops, pipeline orchestration, GitHub I/O, path validation, or CI workflow generation.

**Consequences:** Any implementation work in CraftedAgent that affects those concerns must inspect and align with the current behavior of the critical files before making edits. Refactors that bypass or duplicate logic from these files are disallowed unless the files themselves are updated consistently. This increases change discipline and reduces accidental regression at subsystem boundaries.

**Rejected alternatives:**  
- **Treat critical files as ordinary implementation details:** Rejected because their effects are cross-cutting and mistakes would impact every generated PR or weaken security boundaries.  
- **Duplicate functionality outside the critical files to avoid modifying them:** Rejected because it creates inconsistent behavior and hidden policy forks.  
- **Rely on tests alone to catch mistakes in these files:** Rejected because some failures are silent, policy-related, or only visible in downstream GitHub and CI interactions.

## [Enforce allowed root directories through path-security validation]
**Status:** Accepted

**Context:** Lessons learned from GitHub integration establish that commits to unexpected root directories fail silently or are rejected by path-security guards. Standard projects require explicit allowlisting of `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Dot-prefixed roots such as `.github` must be explicitly allowed.

**Decision:** Enforce an explicit allowlist of permitted repository root directories for all write operations, and require every write path to pass through path-security validation before file creation, update, or commit staging.

**Consequences:** CraftedAgent may only write under approved roots. CI workflow generation under `.github` must be explicitly supported rather than treated as a special-case bypass. New root directories cannot be used until they are added to the allowlist and recognized by path-security logic. This constrains file generation, patch application, and GitHub commit payload construction.

**Rejected alternatives:**  
- **Validate only for path traversal and not root-directory membership:** Rejected because writes can still target unexpected but syntactically safe locations.  
- **Allow all existing repository roots automatically:** Rejected because repositories may contain experimental or legacy directories that should not be mutated by the agent.  
- **Bypass path validation for `.github` files:** Rejected because dot-prefixed directories are specifically called out as needing explicit allowlisting, not exemption.

## [Centralize all GitHub I/O in the GitHub tools boundary]
**Status:** Accepted

**Context:** `src/github_tools.py` is identified as the single location for GitHub I/O and is responsible for path validation, rate limiting, and SHA protocol handling. Direct API usage outside this boundary would fragment correctness and security logic.

**Decision:** Route all GitHub reads, writes, branch operations, and commit-related interactions through the GitHub tools boundary. Do not perform direct GitHub API calls from other CraftedAgent components.

**Consequences:** Components that need repository state or need to write changes must depend on the shared GitHub tools interface. Path validation, rate limiting, and SHA handling remain uniform. This constrains implementation architecture by prohibiting convenience wrappers that skip the central boundary.

**Rejected alternatives:**  
- **Allow direct GitHub API calls in specialized components for convenience:** Rejected because it duplicates protocol logic and risks inconsistent SHA or rate-limit behavior.  
- **Split GitHub responsibilities across multiple modules by feature:** Rejected because path validation and commit semantics are cross-cutting and must remain consistent.  
- **Perform local filesystem writes first and reconcile with GitHub later using ad hoc sync logic:** Rejected because it obscures the source of truth for write authorization and complicates commit correctness.

## [Preserve the core generation loop in the consensus subsystem as the primary execution path]
**Status:** Accepted

**Context:** `src/consensus.py` is identified as the core generation loop, and changes there affect every PR the agent builds. CraftedAgent must maintain predictable generation behavior across all tasks.

**Decision:** Preserve the consensus subsystem as the primary execution path for code generation and PR construction. Changes to generation behavior must be integrated through the core loop rather than introduced as parallel orchestration paths.

**Consequences:** Feature work that alters planning, generation, or revision behavior must compose with the consensus loop instead of bypassing it. This constrains implementation patterns by disallowing hidden generation paths that would produce inconsistent PR outcomes. System-wide generation semantics stay centralized and auditable.

**Rejected alternatives:**  
- **Create specialized generation loops per task type:** Rejected because behavior would diverge across PR categories and become harder to reason about.  
- **Let downstream stages mutate generated output without returning through consensus:** Rejected because it weakens the central control point for quality and consistency.  
- **Move generation logic into build orchestration:** Rejected because consensus and pipeline orchestration are separate concerns with different risk profiles.

## [Keep pipeline orchestration in the build director and maintain a maximum cyclomatic complexity of 15 per stage]
**Status:** Accepted

**Context:** `src/build_director.py` owns pipeline orchestration, and the build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15. This is a direct implementation constraint intended to control operational complexity and maintainability.

**Decision:** Keep pipeline orchestration centralized in the build director, and enforce a maximum cyclomatic complexity of 15 for every pipeline stage implementation.

**Consequences:** New stage logic must be decomposed into helpers rather than expanding decision depth inside a single stage. Orchestration remains centralized, but stage implementations must stay structurally simple. Reviews and static analysis must reject stage implementations that exceed the complexity limit.

**Rejected alternatives:**  
- **Allow complexity to grow in orchestration code when features demand it:** Rejected because the complexity cap is explicitly mandated and protects maintainability.  
- **Distribute stage transitions across unrelated modules:** Rejected because orchestration becomes fragmented and harder to checkpoint and reason about.  
- **Use one large state machine method for all stages:** Rejected because it would almost certainly violate the complexity budget and obscure stage boundaries.

## [Checkpoint every state transition, including per-PR stage transitions]
**Status:** Accepted

**Context:** The build pipeline requires that every state transition be checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This ensures recoverability, auditability, and operator visibility.

**Decision:** Persist a checkpoint at every state transition in the CraftedAgent workflow, including all per-PR stage transitions and gate outcomes.

**Consequences:** Workflow execution must be modeled as explicit state progression rather than implicit control flow. Recovery and resume behavior must consume checkpointed state instead of reconstructing progress heuristically. This constrains storage, orchestration, and failure-handling design by requiring durable transition records.

**Rejected alternatives:**  
- **Checkpoint only major milestones:** Rejected because required per-PR transitions would be lost, reducing recoverability and audit precision.  
- **Infer state from GitHub branch or CI status after failure:** Rejected because inference is incomplete and can miss internal stage outcomes.  
- **Keep state only in memory during a run:** Rejected because crashes or restarts would lose execution history and violate checkpoint requirements.

## [Implement a bounded, failure-type-aware fix loop for test remediation]
**Status:** Accepted

**Context:** The build pipeline specifies a fix loop in which `pytest` may be retried up to 20 attempts using a failure-type-aware strategy. This is a concrete operational rule for iterative repair.

**Decision:** Implement test remediation as a bounded fix loop with a maximum of 20 attempts, and select remediation actions based on classified failure type rather than generic blind retries.

**Consequences:** CraftedAgent must track attempt count, classify failures, and stop retrying once the maximum is reached. The fix loop cannot be open-ended or purely repetition-based. This constrains retry orchestration, logging, and termination behavior, and it encourages structured failure analysis.

**Rejected alternatives:**  
- **Retry indefinitely until tests pass:** Rejected because it is operationally unsafe and contradicts the documented cap.  
- **Use a fixed small retry count without failure classification:** Rejected because the pipeline explicitly requires failure-type-aware strategy and allows more headroom for remediation.  
- **Perform only a single repair attempt before escalation:** Rejected because it underuses the designed iterative repair capability of the subsystem.

## [Generate and maintain required CI workflows for Linux and macOS targets]
**Status:** Accepted

**Context:** The build pipeline defines CI expectations: `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is the generator for these workflows. CI output is therefore a product of the subsystem, not a manual side effect.

**Decision:** Generate and maintain the required CI workflow files through the CI workflow generator, including Linux CI on `ubuntu-latest` and macOS CI for Swift-targeted projects.

**Consequences:** CI workflow definitions must be treated as generated artifacts owned by the subsystem. Workflow creation and updates must occur through the generator instead of hand-authored divergence. `.github` must remain in the allowed roots and under path-security enforcement. Platform coverage is constrained by the documented workflow set unless requirements are updated.

**Rejected alternatives:**  
- **Rely on existing repository CI workflows without generating standardized ones:** Rejected because the pipeline explicitly defines required workflow artifacts.  
- **Generate only one cross-platform workflow:** Rejected because the requirements call out distinct Linux and macOS workflows, including a Swift-specific macOS path.  
- **Allow manual edits to generated workflow logic as the primary maintenance path:** Rejected because it creates drift from generator behavior and undermines reproducibility.

## [Require an operator gate before merge]
**Status:** Accepted

**Context:** The build pipeline defines Stage 6 as a gate where the operator approves or corrects before merge. Gate decisions are also checkpointed. CraftedAgent therefore does not have unconditional authority to merge generated changes.

**Decision:** Require explicit operator approval or correction before merge, and record the gate decision as part of the checkpointed workflow state.

**Consequences:** CraftedAgent may prepare branches, commits, and CI results, but merge completion remains gated by a human decision point. Automation must pause at the gate and surface sufficient context for approval or correction. This constrains end-to-end autonomy and requires state persistence around pending approval.

**Rejected alternatives:**  
- **Auto-merge once tests and CI pass:** Rejected because it violates the documented operator gate.  
- **Use operator review only for exceptional failures:** Rejected because the gate is a standard stage, not an exception path.  
- **Treat gate decisions as transient UI events without persistence:** Rejected because every gate decision must be checkpointed.