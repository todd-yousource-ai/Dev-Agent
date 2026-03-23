# DECISIONS.md

## [Use the documented repository layout as a hard architectural boundary]
**Status:** Accepted

**Context:** The subsystem operates inside a repository with explicitly defined top-level domains: `forge-docs/` for TRDs and PRDs, `forge-standards/` for architectural constraints, `src/` for Python backend implementation, `Crafted/` for the Swift application shell, `CraftedTests/` for XCTest coverage, and `tests/` for pytest coverage. The TRDs define these directories as source-of-truth locations rather than conventions.

**Decision:** Treat the documented repository layout as mandatory. Implement CraftedDevAgent so it reads requirements from `forge-docs/`, follows constraints from `forge-standards/`, writes Python backend changes under `src/`, writes Swift application changes under `Crafted/`, writes Python tests under `tests/`, and writes Swift tests under `CraftedTests/`.

**Consequences:** Implementation must not invent alternate source locations, shadow standards in ad hoc files, or place generated code outside the approved directory structure. Any file operation logic must assume these directories are semantically significant and preserve them.

**Rejected alternatives:**  
- Allowing flexible placement of source and test files based on agent heuristics — rejected because it breaks the repository contract defined by the TRDs and weakens predictability.  
- Consolidating Python and Swift outputs into a single generated workspace — rejected because it conflicts with the documented separation of backend and application shell responsibilities.  
- Treating `forge-docs/` as optional reference material — rejected because TRDs are explicitly the source of truth.

## [Read and honor critical files before modifying subsystem behavior]
**Status:** Accepted

**Context:** Several files are designated as critical because they enforce core platform behavior and safety boundaries: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes in these files have repository-wide effects.

**Decision:** Require CraftedDevAgent to inspect and preserve the contracts of all designated critical files before making related changes. Route all modifications affecting generation, orchestration, GitHub I/O, path validation, or CI workflow through the existing mechanisms in those files rather than bypassing them.

**Consequences:** The subsystem must be conservative when editing these files, must prefer extension over replacement, and must preserve public behavior relied on elsewhere in the system. Any implementation that touches write paths, GitHub operations, orchestration, or CI generation must defer to the established boundary files.

**Rejected alternatives:**  
- Reimplementing equivalent logic in new helper modules — rejected because duplicated control logic would create drift from the repository’s enforcement points.  
- Bypassing critical files for speed in narrowly scoped changes — rejected because these files define security and orchestration boundaries, not optional abstractions.  
- Treating the critical-file list as documentation only — rejected because the TRD language indicates operational importance.

## [Enforce stage-based pipeline execution with explicit checkpoints]
**Status:** Accepted

**Context:** The build pipeline is defined as staged execution with checkpointed transitions. The README specifies that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`.

**Decision:** Implement CraftedDevAgent as a stage-based workflow engine with explicit persisted checkpoints at every transition. Record at minimum the documented per-PR states and require successful completion of the current stage before entering the next stage.

**Consequences:** The subsystem must support resumability, auditability, and deterministic recovery from interruption. It may not collapse multiple stages into one opaque execution block or advance state implicitly without writing a checkpoint.

**Rejected alternatives:**  
- Using a single in-memory execution pass without persisted checkpoints — rejected because it prevents reliable recovery and violates the documented checkpoint requirement.  
- Checkpointing only major milestones such as commit and CI — rejected because the repository requires every state transition to be checkpointed.  
- Allowing out-of-order stage advancement when dependencies appear satisfied — rejected because it undermines the explicit pipeline contract.

## [Keep cyclomatic complexity of every pipeline stage at 15 or below]
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15. `src/build_director.py` is specifically called out as a strict enforcement point.

**Decision:** Design each CraftedDevAgent pipeline stage so its cyclomatic complexity does not exceed 15. Split behavior into helper functions, policy objects, or isolated handlers whenever a stage risks exceeding the limit.

**Consequences:** The subsystem must favor compositional orchestration over monolithic control flow. Complexity budgeting becomes a design constraint for stage handlers, recovery logic, and dispatch code. Refactors are required when additional branching would push a stage above the limit.

**Rejected alternatives:**  
- Allowing complexity exceptions for orchestration-heavy stages — rejected because the requirement is stated as universal across every stage.  
- Enforcing the limit only through linting after implementation — rejected because the constraint must shape design upfront, not act only as a retrospective warning.  
- Concentrating branch logic in `build_director.py` for simplicity of file count — rejected because it directly conflicts with the strict complexity cap.

## [Implement a bounded, failure-type-aware fix loop]
**Status:** Accepted

**Context:** The build pipeline defines a fix loop using pytest with up to 20 attempts and a failure-type-aware strategy. This means retries are not unbounded and must respond differently based on the class of failure encountered.

**Decision:** Implement CraftedDevAgent’s automated repair cycle as a bounded loop capped at 20 attempts, and select remediation tactics based on identified failure type rather than retrying a generic regeneration strategy.

**Consequences:** The subsystem must classify failures, track attempt counts, and terminate with a surfaced failure when the attempt budget is exhausted. It may not loop indefinitely, hide repeated failures, or apply a one-size-fits-all retry plan.

**Rejected alternatives:**  
- Unlimited retries until tests pass — rejected because it risks non-termination and violates the documented cap.  
- A fixed retry count without failure classification — rejected because the build pipeline explicitly requires failure-type-aware strategy.  
- Immediate human escalation after the first failure — rejected because the pipeline defines an automated repair loop, not a single-shot execution model.

## [Generate and validate CI in platform-specific workflows]
**Status:** Accepted

**Context:** The repository defines CI expectations with `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. The critical file list identifies `src/ci_workflow.py` as the generator boundary for this behavior.

**Decision:** Generate and maintain CI through the established workflow generator, using separate workflows for Linux-oriented backend validation and macOS-oriented Swift validation. Preserve the platform split as part of the subsystem contract.

**Consequences:** CraftedDevAgent must not merge Python and Swift CI into a single generic workflow when platform-specific validation is required. Changes to CI behavior must be expressed through `src/ci_workflow.py` and must preserve the expected runner targeting.

**Rejected alternatives:**  
- A single cross-platform workflow for all validation — rejected because Swift validation requires the documented macOS workflow separation.  
- Manual editing of workflow YAML outside the generator boundary — rejected because it bypasses the critical file designated for workflow generation.  
- Running Swift checks on Ubuntu through compatibility tooling — rejected because it does not satisfy the repository’s explicit macOS CI requirement.

## [Require operator approval at the gate before merge]
**Status:** Accepted

**Context:** The pipeline includes a gate where the operator approves or corrects before merge. The documentation also states that every gate decision is checkpointed.

**Decision:** Do not permit CraftedDevAgent to merge autonomously past the final gate. Require explicit operator approval or correction, and checkpoint the gate decision before any merge action proceeds.

**Consequences:** The subsystem must expose enough state and artifacts for human review, must block merge completion pending approval, and must persist the outcome of the gate decision. Fully unattended merge execution is out of scope.

**Rejected alternatives:**  
- Auto-merging after green tests and CI — rejected because it removes the documented operator gate.  
- Treating operator review as advisory only — rejected because the gate is a mandatory stage, not an optional notification.  
- Delaying checkpointing until after merge — rejected because gate decisions themselves must be checkpointed.

## [Route every write path through the path security boundary]
**Status:** Accepted

**Context:** `src/path_security.py` is identified as the security boundary, and the critical file note states that every write path must pass through it. This is a direct safety requirement, not a style preference.

**Decision:** Require CraftedDevAgent to validate all filesystem write targets through `src/path_security.py` before creating, modifying, moving, or deleting repository files.

**Consequences:** The subsystem must not perform direct path writes that bypass the security boundary. Any feature that introduces file output, artifact generation, patch application, or temporary materialization inside the repository must integrate with the path validation layer.

**Rejected alternatives:**  
- Direct writes using standard library path handling alone — rejected because standard path APIs do not satisfy the repository’s explicit security-boundary requirement.  
- Validating only external or user-supplied paths — rejected because the requirement covers every write path.  
- Post-write auditing instead of pre-write validation — rejected because the security boundary must prevent invalid writes, not merely detect them afterward.

## [Centralize all GitHub I/O through github_tools with existing safeguards]
**Status:** Accepted

**Context:** `src/github_tools.py` is designated as the single boundary for GitHub I/O, including path validation, rate limiting, and SHA protocol handling. These controls are essential for correct and safe repository interaction.

**Decision:** Perform all GitHub API reads and writes for CraftedDevAgent through `src/github_tools.py`, preserving its rate limiting, path validation, and SHA-based update semantics.

**Consequences:** The subsystem must not call GitHub APIs directly from new modules for convenience. It must respect optimistic concurrency and repository consistency rules already encoded in the GitHub tools layer.

**Rejected alternatives:**  
- Direct REST or GraphQL calls from feature modules — rejected because they bypass the repository’s designated I/O control point.  
- Wrapping `github_tools` with a parallel custom client for some operations — rejected because it fragments safeguards and creates protocol drift.  
- Ignoring SHA semantics for generated file updates — rejected because the critical file explicitly governs SHA protocol behavior.

## [Preserve consensus engine integration as the core generation loop]
**Status:** Accepted

**Context:** `src/consensus.py` is identified as the core generation loop and changes there affect every PR the agent builds. This implies the subsystem’s generation behavior must remain compatible with that core loop.

**Decision:** Build CraftedDevAgent generation features as extensions to, or consumers of, the existing consensus engine rather than replacing it with an isolated generation path.

**Consequences:** New generation capabilities must integrate with the established consensus flow, preserving system-wide behavior consistency across PRs. The subsystem may not introduce a separate “fast path” generator that bypasses consensus for normal operation.

**Rejected alternatives:**  
- Creating a standalone generation pipeline just for CraftedDevAgent — rejected because it would fork core PR-building behavior.  
- Replacing `src/consensus.py` with subsystem-specific orchestration logic — rejected because that file is a repository-wide core dependency.  
- Using consensus only for large changes while bypassing it for small edits — rejected because it creates inconsistent behavior across PRs.

## [Use TRDs and standards documents as authoritative inputs before implementation]
**Status:** Accepted

**Context:** The repository documentation states that all TRDs and PRDs live in `forge-docs/` and should be read before building. `forge-standards/` contains `ARCHITECTURE.md`, `INTERFACES.md`, `DECISIONS.md`, `CONVENTIONS.md`, and `build_rules.md`, which together define implementation constraints.

**Decision:** Require CraftedDevAgent to consult `forge-docs/` and `forge-standards/` as authoritative inputs before planning or applying subsystem changes. When conflicts arise, prefer explicit TRD and standards constraints over inferred implementation convenience.

**Consequences:** The subsystem must be document-driven, must not rely solely on local code patterns as authority, and must preserve alignment with architecture and interface definitions. Planning logic should assume documents are normative unless superseded through formal change.

**Rejected alternatives:**  
- Inferring requirements from existing code without reading TRDs — rejected because the repository explicitly directs builders to read the documents first.  
- Treating standards documents as non-binding guidance — rejected because they are part of the repository’s formal control surface.  
- Prioritizing generated build rules over TRDs in case of conflict — rejected because build rules are derived artifacts, while TRDs are the source of truth.

## [Respect the application shell’s root view state machine when backend changes affect onboarding]
**Status:** Accepted

**Context:** TRD-1 defines a root view decision tree where `RootView` branches on onboarding state, including `OnboardingContainerView` and specific onboarding steps. Backend and agent-driven changes can impact assumptions about setup progression and gating.

**Decision:** Preserve compatibility with the documented onboarding state machine whenever CraftedDevAgent changes APIs, persistence, setup flows, or generated behavior that affects the macOS application shell. Do not introduce backend assumptions that skip, reorder, or collapse the documented onboarding states.

**Consequences:** Subsystem changes that touch authentication, environment setup, or initial configuration must be validated against the app shell’s onboarding flow. Backend contracts must support the existing state transitions instead of forcing UI divergence.

**Rejected alternatives:**  
- Simplifying onboarding by inferring completion from partial backend state — rejected because it would bypass the documented root view decision tree.  
- Letting backend implementation details dictate UI state progression — rejected because the UI flow is explicitly documented in TRD-1.  
- Collapsing onboarding steps to reduce integration complexity — rejected because it changes product behavior outside this subsystem’s authority.