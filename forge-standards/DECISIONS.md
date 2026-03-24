# DECISIONS.md

## Repository and documents are source-of-truth constrained
**Status:** Accepted  
**Context:** ForgeAgent operates inside a repository with an explicitly defined structure. TRDs and PRDs under `forge-docs/` are the authoritative design inputs, while implementation standards live under `forge-standards/`. The subsystem must not invent structure or bypass documented constraints.  
**Decision:** Treat `forge-docs/` as the canonical source of product and technical requirements, and treat `forge-standards/` as the canonical source of implementation constraints. Implement ForgeAgent so it reads and conforms to these locations before changing code. Preserve the documented repository layout: Python backend in `src/`, macOS shell in `Crafted/`, Swift tests in `CraftedTests/`, Python tests in `tests/`, and standards documents in `forge-standards/`.  
**Consequences:** Implementation must assume these directories are stable interfaces. New subsystem behavior must integrate into the existing layout rather than creating parallel conventions. Tooling, prompts, validation, and file generation must be path-aware and repository-layout-aware.  
**Rejected alternatives:**  
- Allowing the agent to infer its own repository structure from discovery at runtime — rejected because the TRDs define a fixed layout and divergence would create non-deterministic behavior.  
- Treating generated code or local conventions as equal to TRDs — rejected because requirements documents are explicitly the source of truth.  
- Relocating ForgeAgent-specific state into ad hoc folders — rejected because it would bypass the documented repository organization.

## Critical implementation files are protected interfaces
**Status:** Accepted  
**Context:** Several files are explicitly designated as critical because they govern generation flow, orchestration, GitHub I/O, path security, and CI workflow generation. Modifications in these files have cross-cutting system impact.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as protected subsystem interfaces. Require ForgeAgent changes that touch these files to preserve their documented invariants and to avoid incidental refactors unrelated to the requested behavior.  
**Consequences:** Changes in these files must be minimal, targeted, and justified by subsystem requirements. Tests and validation for these areas must be stricter than for ordinary files. Design work for ForgeAgent must consider these modules first-class boundaries, not implementation details.  
**Rejected alternatives:**  
- Treating all files as equally modifiable — rejected because the TRDs identify these files as especially sensitive.  
- Rewriting critical modules wholesale to simplify implementation — rejected because broad rewrites would increase regression risk across the build pipeline and security boundary.  
- Hiding critical behavior behind new wrappers while leaving existing modules inconsistent — rejected because it would duplicate logic and weaken the documented control points.

## Build pipeline stages are mandatory and ordered
**Status:** Accepted  
**Context:** The README defines a staged build pipeline with explicit sequencing, including parse/lint/import validation, a bounded fix loop, CI execution, and an operator gate before merge. ForgeAgent must participate in this pipeline rather than improvising an alternate flow.  
**Decision:** Implement ForgeAgent to operate within the existing ordered pipeline stages and preserve their semantics: generation and validation must flow through the documented stages; syntax and lint checks must occur before test/fix iteration; CI must run before merge; and operator gate approval must remain required before merge completion.  
**Consequences:** ForgeAgent cannot skip, reorder, or collapse stages for convenience. Error handling and retries must map to stage boundaries. Any state machine or orchestration code must expose stage-aware progress and failure reporting.  
**Rejected alternatives:**  
- Running tests before parse/lint/import checks — rejected because cheaper structural validation must fail fast first.  
- Merging automatically after local tests pass — rejected because CI and operator gate are explicit required stages.  
- Allowing ad hoc agent-selected stage ordering — rejected because deterministic orchestration is part of the system design.

## Cyclomatic complexity per pipeline stage is capped at 15
**Status:** Accepted  
**Context:** The build pipeline documentation explicitly states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is called out as enforcing this strictly. This is both an implementation and maintainability constraint.  
**Decision:** Keep the implementation of each ForgeAgent pipeline stage at cyclomatic complexity 15 or below. Decompose logic into helper functions, strategies, or data-driven dispatch instead of concentrating branching inside a single stage implementation.  
**Consequences:** Stage implementations must remain small and composable. New failure handling, retries, or branching behavior must be extracted rather than added inline if doing so would breach the limit. Code review for ForgeAgent must treat this as a hard constraint, not a style preference.  
**Rejected alternatives:**  
- Applying the complexity cap only to newly added code — rejected because the requirement applies to every stage.  
- Allowing temporary exceptions for orchestration-heavy modules — rejected because `src/build_director.py` is explicitly named as strictly enforcing the cap.  
- Measuring complexity only at file level — rejected because the requirement is per stage, not per file.

## All state transitions must be checkpointed
**Status:** Accepted  
**Context:** The pipeline documentation requires checkpointing for every state transition, including per-PR states such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This is necessary for recovery, auditability, and deterministic orchestration.  
**Decision:** Persist a checkpoint at every ForgeAgent state transition, including intermediate per-PR stage changes and gate outcomes. Model workflow state explicitly enough that transitions are serializable, resumable, and inspectable.  
**Consequences:** ForgeAgent must not rely solely on in-memory progress. Crash recovery, restart behavior, and operator visibility must be designed around persisted transition records. State mutation paths must be explicit and testable.  
**Rejected alternatives:**  
- Checkpointing only major milestones such as start and finish — rejected because the requirement applies to every transition.  
- Relying on Git history as implicit workflow state — rejected because not all workflow transitions correspond to commits.  
- Using best-effort logging instead of structured checkpoints — rejected because logs do not provide reliable resumable state.

## Gate decisions must be recorded before merge
**Status:** Accepted  
**Context:** The pipeline includes an operator approval/correction gate before merge, and the documentation states that every gate decision must be recorded. This makes human intervention part of the formal workflow.  
**Decision:** Require explicit recording of operator gate decisions, including approval or correction, before any merge-completing action occurs. Treat gate records as workflow artifacts, not optional logs.  
**Consequences:** ForgeAgent cannot finalize merge actions without a persisted gate decision. UIs, APIs, and orchestration flows must surface pending gate status clearly. Audit trails must include who approved or corrected and at what point in the pipeline.  
**Rejected alternatives:**  
- Treating operator approval as an ephemeral UI action — rejected because gate decisions must be recorded.  
- Auto-approving on behalf of the operator when all automated checks pass — rejected because the gate is a distinct required stage.  
- Recording only negative gate outcomes — rejected because all gate decisions are part of the workflow history.

## The fix loop is bounded and failure-type-aware
**Status:** Accepted  
**Context:** The build pipeline specifies a fix loop with `pytest` and a hard limit of up to 20 attempts, using failure-type-aware strategy. ForgeAgent must improve code iteratively without entering unbounded retry behavior.  
**Decision:** Implement the ForgeAgent fix loop with a strict maximum of 20 attempts and require remediation strategy selection to be informed by detected failure type. Do not use open-ended retries or identical retry behavior for all failures.  
**Consequences:** Retry orchestration must track attempt count and classify failures. The subsystem must stop and surface unresolved issues when the limit is reached. Prompting, patch generation, and recovery behavior must differ based on failure taxonomy or equivalent classification.  
**Rejected alternatives:**  
- Infinite retries until tests pass — rejected because the pipeline explicitly bounds attempts.  
- A fixed number of retries without regard to failure type — rejected because the loop must be failure-type-aware.  
- Manual-only remediation after the first failed test run — rejected because iterative automated fixing is a required stage behavior.

## GitHub interactions must flow through the dedicated tools module
**Status:** Accepted  
**Context:** `src/github_tools.py` is identified as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. This centralization is critical for correctness and security.  
**Decision:** Route all ForgeAgent GitHub reads and writes through `src/github_tools.py` or APIs layered directly on top of it that preserve its controls. Do not perform direct GitHub I/O elsewhere in the subsystem.  
**Consequences:** Rate limiting, SHA correctness, and repository write safety remain centralized. ForgeAgent features that need repository or PR operations must integrate with the existing GitHub abstraction instead of bypassing it. Testing can mock one boundary consistently.  
**Rejected alternatives:**  
- Calling GitHub APIs directly from orchestration or agent logic — rejected because it would bypass validation and protocol handling.  
- Splitting GitHub write paths across multiple modules for convenience — rejected because it weakens centralized safety controls.  
- Using shell git commands as a substitute for GitHub API workflows — rejected because the documented critical module governs GitHub I/O semantics.

## Every write path must pass through the path security boundary
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. ForgeAgent will generate and modify files, so this boundary is mandatory.  
**Decision:** Validate every ForgeAgent filesystem write path through `src/path_security.py` before performing the write. Do not introduce alternate write mechanisms, unchecked path joins, or direct file mutations that bypass this module.  
**Consequences:** All file creation and modification code must be structured so path validation is unavoidable. Security review can focus on one enforcement point. Attempts to write outside approved repository boundaries must fail before I/O occurs.  
**Rejected alternatives:**  
- Validating only external-input-derived paths — rejected because the requirement applies to every write path.  
- Performing ad hoc path normalization within each module — rejected because security enforcement must remain centralized.  
- Trusting LLM-generated file paths if they appear in-repo — rejected because generated paths must still cross the security boundary.

## CI workflow generation remains centralized in the CI workflow module
**Status:** Accepted  
**Context:** `src/ci_workflow.py` is identified as the module that generates workflow files, and the build pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. ForgeAgent must not fragment CI definition behavior.  
**Decision:** Generate or modify CI workflows only through `src/ci_workflow.py`, preserving the documented split between Linux-oriented and macOS Swift workflows. Keep ForgeAgent CI changes compatible with the existing workflow naming and platform responsibilities unless the standards documents explicitly change.  
**Consequences:** CI behavior remains discoverable and centralized. ForgeAgent cannot create shadow workflows with overlapping responsibilities. Platform-specific logic must remain aligned with documented workflow separation.  
**Rejected alternatives:**  
- Emitting workflow YAML directly from agent logic — rejected because CI generation is already centralized in a critical module.  
- Combining all CI into a single workflow for simplicity — rejected because the repository explicitly distinguishes Ubuntu and macOS workflows.  
- Creating ForgeAgent-only private workflows outside the documented naming scheme — rejected because it would fragment pipeline behavior.

## ForgeAgent must respect the existing multi-language repository split
**Status:** Accepted  
**Context:** The repository contains a Python backend and a Swift/SwiftUI macOS application shell with distinct test suites and CI concerns. ForgeAgent must operate across this split without collapsing language-specific conventions.  
**Decision:** Keep ForgeAgent backend implementation in Python under `src/`, and treat Swift/SwiftUI code under `Crafted/` and `CraftedTests/` as separate platform-specific surfaces with their own CI and test handling. Do not blur backend and app-shell responsibilities.  
**Consequences:** Python orchestration, security, and GitHub integration stay in the backend. Swift changes must be handled with awareness of macOS-specific CI and test contexts. Shared abstractions must be repository-level contracts rather than mixed-language runtime coupling.  
**Rejected alternatives:**  
- Moving orchestration logic into the Swift app shell — rejected because backend implementation is defined under `src/`.  
- Treating Swift and Python test flows as interchangeable — rejected because the repository and CI are explicitly split by language/platform.  
- Building ForgeAgent as a language-agnostic freeform script layer outside `src/` — rejected because it would violate the documented layout.

## UI flow assumptions must not contradict the documented Root View decision tree
**Status:** Accepted  
**Context:** TRD-1 defines a root view decision tree driven by onboarding state, routing users through onboarding views until completion. ForgeAgent may surface status or controls to the app shell, so it must not assume arbitrary root navigation.  
**Decision:** Any ForgeAgent-driven UI integration with the macOS shell must respect the documented RootView onboarding-state-driven routing and must not bypass onboarding-dependent entry conditions.  
**Consequences:** Features that expose ForgeAgent functionality in the app must account for onboarding completion and proper placement in the existing navigation model. Backend assumptions about UI availability must tolerate onboarding not being complete.  
**Rejected alternatives:**  
- Launching ForgeAgent views directly at app start regardless of onboarding state — rejected because it contradicts the documented root decision tree.  
- Embedding agent flows as an independent root coordinator — rejected because the shell already defines root routing.  
- Assuming GitHub or API-key-dependent features are always available — rejected because onboarding explicitly stages those prerequisites.