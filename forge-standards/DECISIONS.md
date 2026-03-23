# DECISIONS.md

## Repository structure is fixed and documentation-first
**Status:** Accepted

**Context:** The FullPlatform subsystem is implemented within a repository whose structure is already defined by the TRDs and README. The docs directory is the source of truth, and implementation is expected to conform to those documents before code changes are made.

**Decision:** Treat `forge-docs/` as the source of truth and preserve the established top-level repository layout: `forge-docs/`, `forge-standards/`, `src/`, `Crafted/`, `CraftedTests/`, `tests/`, and root operational documents. Read relevant TRDs and standards before modifying implementation.

**Consequences:** Implementation must not relocate core directories, invent parallel standards locations, or bypass documentation-defined constraints. Changes in FullPlatform must align with TRDs first, then code.

**Rejected alternatives:**  
- Using code as the primary source of truth: rejected because TRDs explicitly define architecture and workflow expectations.  
- Reorganizing the repository around subsystem ownership: rejected because it would break documented paths, tooling assumptions, and contributor workflow.  
- Duplicating standards inside subsystem folders: rejected because it creates drift from `forge-standards/`.

## Critical file boundaries must be respected
**Status:** Accepted

**Context:** Several files are designated as critical because they define security, orchestration, CI generation, and GitHub interaction boundaries. Unconstrained modification of these files would create system-wide risk.

**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as architectural boundary files. Route changes affecting generation, orchestration, GitHub I/O, path validation, or CI through these files deliberately and only after reading their documented role.

**Consequences:** FullPlatform changes must integrate with existing boundary modules rather than reimplementing their responsibilities elsewhere. Reviews for these files must be stricter because changes have cross-cutting effects.

**Rejected alternatives:**  
- Allowing any module to perform GitHub I/O or filesystem writes directly: rejected because it weakens security and consistency.  
- Spreading orchestration logic across many files: rejected because `src/build_director.py` is the defined orchestration boundary.  
- Treating critical files as ordinary implementation details: rejected because the TRDs explicitly call out their importance.

## All write paths must pass through the path security boundary
**Status:** Accepted

**Context:** The repository defines `src/path_security.py` as the security boundary for write paths. FullPlatform includes operations that generate, modify, or persist files, making path validation mandatory.

**Decision:** Enforce that every filesystem write in FullPlatform passes through the centralized path validation mechanism in `src/path_security.py`. Do not write directly to paths that have not been validated by the security boundary.

**Consequences:** New code must use approved path-security APIs before creating or modifying files. File-writing helpers that bypass validation are not permitted. This constrains convenience implementations but preserves the repository’s security model.

**Rejected alternatives:**  
- Inline path checks in each caller: rejected because it leads to inconsistent enforcement and review burden.  
- Trusting internal callers and skipping validation for “safe” paths: rejected because trust assumptions drift over time.  
- Using ad hoc allowlists inside unrelated modules: rejected because it fragments the security boundary.

## GitHub access must be centralized in github_tools with validation, rate limiting, and SHA protocol
**Status:** Accepted

**Context:** GitHub integration is a defined concern, and `src/github_tools.py` is identified as the sole boundary for GitHub I/O, including path validation, rate limiting, and SHA protocol handling.

**Decision:** Route all GitHub reads and writes for FullPlatform through `src/github_tools.py`. Preserve path validation, rate limiting, and SHA-based update semantics as mandatory behaviors.

**Consequences:** FullPlatform features may not call GitHub APIs directly from business logic or UI glue. All repository mutations must honor SHA protocol expectations, which constrains update flows but prevents race and consistency errors.

**Rejected alternatives:**  
- Direct GitHub API calls from feature modules: rejected because it bypasses centralized safety and protocol handling.  
- Separate GitHub clients per subsystem: rejected because it duplicates policy logic and increases inconsistency.  
- Best-effort writes without SHA coordination: rejected because it risks overwriting concurrent changes.

## Build pipeline stages are fixed and must remain explicit
**Status:** Accepted

**Context:** The README defines a staged build pipeline with explicit phases, including static checks, a bounded fix loop, CI, and an approval gate. The platform depends on these stages being stable and inspectable.

**Decision:** Implement and preserve the pipeline as explicit stages: generation and checks, fix loop, test + CI, and final gate, including the documented static analysis and test execution steps. Do not collapse these stages into a single opaque operation.

**Consequences:** FullPlatform orchestration must expose stage transitions clearly and keep per-stage behavior inspectable. This limits optimization through hidden internal shortcuts but improves debuggability, checkpointing, and operator trust.

**Rejected alternatives:**  
- A single monolithic “build and verify” step: rejected because it obscures failure location and weakens recovery.  
- Dynamically skipping stages based on heuristics: rejected because the documented pipeline is normative and gateable.  
- Subsystem-specific custom stage ordering: rejected because it would fragment operational behavior.

## Cyclomatic complexity per pipeline stage must not exceed 15
**Status:** Accepted

**Context:** The repository README explicitly states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is called out as having this limit strictly enforced.

**Decision:** Keep each FullPlatform pipeline stage at cyclomatic complexity 15 or below. When behavior grows, split logic into smaller helpers or additional well-defined units rather than increasing branching inside a stage.

**Consequences:** Implementation must favor compositional design over large conditional blocks. This constrains how orchestration and recovery logic are expressed, but preserves maintainability and enforceability.

**Rejected alternatives:**  
- Allowing higher complexity in “central” orchestration code: rejected because the limit is explicitly strict.  
- Measuring complexity only at module level: rejected because the requirement applies per stage.  
- Temporarily exceeding the limit during feature growth: rejected because architectural constraints are not optional debt.

## Every state transition must be checkpointed
**Status:** Accepted

**Context:** The pipeline documentation requires that every state transition be checkpointed, including per-PR transitions such as `branch_opened → code_generated → tests_passed → committed → ci_passed`.

**Decision:** Persist a checkpoint at every FullPlatform state transition, including all documented per-PR stages and any equivalent subsystem transitions. Do not treat intermediate states as ephemeral.

**Consequences:** Recovery, auditability, and resumability become mandatory design properties. New features must define their state transitions explicitly and attach checkpoint behavior to them, which adds implementation overhead but prevents silent progress loss.

**Rejected alternatives:**  
- Checkpointing only major milestones: rejected because the requirement covers every state transition.  
- In-memory-only transition tracking: rejected because it prevents crash recovery and auditability.  
- Logging transitions without durable checkpoints: rejected because logs alone are insufficient for resumable workflow state.

## Gate decisions must be explicit and operator-mediated before merge
**Status:** Accepted

**Context:** The build pipeline includes a final gate where an operator approves or corrects before merge, and gate decisions are described as first-class workflow events.

**Decision:** Require an explicit operator gate before merge and record the gate decision as part of workflow state. Do not auto-merge FullPlatform changes solely on the basis of passing automation.

**Consequences:** FullPlatform remains human-supervised at merge time. This reduces end-to-end automation speed but preserves governance, correction opportunities, and accountability for system-generated changes.

**Rejected alternatives:**  
- Automatic merge on green CI: rejected because the documented gate requires operator approval or correction.  
- Optional human review only for high-risk changes: rejected because the gate is part of the standard pipeline, not a conditional exception.  
- Informal approval outside the workflow state machine: rejected because decisions must be recorded and checkpointed.

## CI workflow generation must target documented environments
**Status:** Accepted

**Context:** The README defines CI execution targets: `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is the boundary module generating this behavior.

**Decision:** Generate and maintain CI workflows that match the documented environment split: Ubuntu for the crafted CI workflow and macOS for Swift-specific workflow execution. Manage this through `src/ci_workflow.py`.

**Consequences:** FullPlatform cannot arbitrarily change runner selection or collapse platform-specific workflows. This preserves compatibility with Python/backend and Swift/macOS responsibilities across the stack.

**Rejected alternatives:**  
- Running all CI on a single OS: rejected because Swift/macOS concerns require a dedicated macOS path.  
- Hand-maintaining workflow YAML outside the generator boundary: rejected because `src/ci_workflow.py` is the designated control point.  
- Using only macOS runners for everything: rejected because it increases cost and diverges from the documented split.

## The macOS shell must preserve the documented RootView onboarding decision tree
**Status:** Accepted

**Context:** TRD-1 defines a specific RootView decision tree for the Crafted macOS shell, with onboarding state driving initial view selection before the main application experience.

**Decision:** Preserve the RootView branching model in the FullPlatform macOS shell: if onboarding is not complete, render the onboarding container and its state-specific screens; only proceed to the post-onboarding application flow once onboarding is complete.

**Consequences:** FullPlatform UI work must integrate with the existing onboarding state machine rather than bypassing it with direct entry into application features. This constrains navigation architecture but maintains predictable startup behavior.

**Rejected alternatives:**  
- Directly opening the main application shell regardless of onboarding state: rejected because it violates the documented decision tree.  
- Replacing state-driven onboarding with loosely coupled modal prompts: rejected because it weakens determinism and flow control.  
- Embedding onboarding inside unrelated feature views: rejected because the root decision tree defines onboarding as the primary entry branch.