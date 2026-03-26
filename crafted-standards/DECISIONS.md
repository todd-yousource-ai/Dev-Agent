# DECISIONS.md

## [Constrain CraftedApp to the standard repository roots]
**Status:** Accepted  
**Context:** CraftedApp operates inside a repository with enforced path security and GitHub commit validation. Prior incidents showed that writing outside approved root directories either fails silently or is blocked by security guards. Dot-prefixed roots such as `.github` are not implicitly valid and must be explicitly permitted.  
**Decision:** Restrict all CraftedApp file generation, modification, and commits to an explicit allowlist of repository roots: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Require every write path to pass through the path security boundary before any filesystem or GitHub operation.  
**Consequences:** CraftedApp cannot create ad hoc top-level directories without first updating the allowlist and associated security validation. CI workflow generation under `.github` is permitted only because it is explicitly allowlisted. All implementation paths must route through centralized path validation rather than constructing write locations inline.  
**Rejected alternatives:**  
- Allow writes anywhere under the repository root because it is simpler. Rejected because it weakens the security boundary and conflicts with existing path guards.  
- Infer allowed roots dynamically from current repository contents. Rejected because it makes security policy implicit and inconsistent across repositories.  
- Exclude `.github` from the allowlist. Rejected because CraftedApp must support CI workflow generation.

## [Treat forge-docs as the source of truth for subsystem behavior]
**Status:** Accepted  
**Context:** The repository structure defines `forge-docs/` as the location for all TRDs and PRDs, and those documents are the authoritative basis for implementation. CraftedApp must remain aligned with technical requirements that may span build, CI, coordination, security, and UI concerns.  
**Decision:** Read and honor requirements from `forge-docs/` before implementing or modifying CraftedApp behavior. Treat TRDs and PRDs in `forge-docs/` as authoritative over inferred behavior from code alone.  
**Consequences:** Implementation work must be traceable to documented requirements. Changes that diverge from TRDs require updating the documents first or in tandem. CraftedApp design cannot rely solely on local code conventions when they conflict with repository documentation.  
**Rejected alternatives:**  
- Treat current source code as the sole source of truth. Rejected because repository guidance explicitly places TRDs and PRDs in `forge-docs/` as authoritative.  
- Duplicate requirements into subsystem-specific files and ignore upstream docs. Rejected because duplication creates drift and undermines a single source of truth.

## [Protect critical integration files with targeted change discipline]
**Status:** Accepted  
**Context:** Several files are called out as critical because they define core generation, orchestration, GitHub I/O, path security, and CI workflow behavior. Changes in these areas have broad system impact and can break every generated PR or compromise the security boundary.  
**Decision:** Require CraftedApp changes that affect `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, or `src/ci_workflow.py` to preserve existing contracts and pass through heightened review discipline. Avoid incidental refactors in these files when implementing subsystem features.  
**Consequences:** CraftedApp implementation must prefer extension over broad rewrites in critical files. Engineers must evaluate blast radius explicitly when touching these modules. Security, GitHub, and CI logic remain centralized rather than reimplemented within CraftedApp.  
**Rejected alternatives:**  
- Freely refactor critical files during subsystem work. Rejected because these modules affect all PR generation and security-sensitive operations.  
- Copy critical behaviors into CraftedApp-specific modules to avoid touching the originals. Rejected because it creates duplicate logic and inconsistent enforcement.  
- Ignore the critical-files guidance for local-only changes. Rejected because even small changes in these modules can have system-wide effects.

## [Enforce centralized GitHub I/O through the existing GitHub tools layer]
**Status:** Accepted  
**Context:** GitHub operations in this repository are governed by path validation, rate limiting, and SHA-aware protocols. Direct or duplicate GitHub access from CraftedApp would bypass those guarantees and create inconsistent behavior.  
**Decision:** Route all CraftedApp GitHub reads, writes, commits, and workflow-related repository operations through `src/github_tools.py`. Do not implement parallel GitHub I/O paths inside CraftedApp.  
**Consequences:** CraftedApp inherits repository-wide safeguards for path validation, rate limiting, and commit semantics. Implementation may be less direct but remains consistent with system constraints. Testing must validate integration with the shared GitHub layer rather than isolated custom clients.  
**Rejected alternatives:**  
- Use direct GitHub API calls from CraftedApp for flexibility. Rejected because it bypasses established security and protocol handling.  
- Introduce a CraftedApp-specific GitHub wrapper. Rejected because it duplicates core infrastructure and risks divergence from required SHA and rate-limit behavior.

## [Preserve the path security boundary for every write]
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the repository security boundary, and every write path must pass through it. CraftedApp will generate and modify files, making path handling a primary security concern.  
**Decision:** Validate every CraftedApp filesystem and repository write through the centralized path security module before execution. Do not permit direct writes based on unchecked string concatenation, relative traversal, or caller-supplied paths.  
**Consequences:** CraftedApp code must be structured around validated path objects or approved helpers. Some convenience APIs are disallowed if they cannot enforce path checks. Security review can focus on one boundary rather than many dispersed checks.  
**Rejected alternatives:**  
- Perform lightweight local validation within CraftedApp. Rejected because fragmented validation weakens the security model and invites inconsistency.  
- Trust internally generated paths without validation. Rejected because bugs in path construction still cross trust boundaries.  
- Validate only remote GitHub writes and not local filesystem writes. Rejected because both are part of the same security surface.

## [Keep pipeline and stage logic within the complexity ceiling]
**Status:** Accepted  
**Context:** The build pipeline explicitly requires that every stage maintain a maximum cyclomatic complexity of 15. `src/build_director.py` is singled out with that constraint strictly enforced. CraftedApp will participate in orchestration and must not introduce control-flow sprawl.  
**Decision:** Design CraftedApp pipeline, orchestration, and stage-transition logic so that each function or stage implementation remains at or below cyclomatic complexity 15. Split decision logic into composable helpers instead of accumulating branching inside stage directors.  
**Consequences:** CraftedApp implementations must favor smaller units, explicit stage handlers, and strategy extraction. Large monolithic orchestration functions are prohibited. Complexity becomes a design constraint, not just a linting outcome.  
**Rejected alternatives:**  
- Allow higher complexity in orchestration code because pipelines are inherently branch-heavy. Rejected because the repository explicitly caps complexity per stage.  
- Rely on later refactoring if complexity grows too high. Rejected because the constraint is preventative and must shape implementation from the start.  
- Exempt CraftedApp-specific stages from the ceiling. Rejected because the requirement applies to every stage.

## [Checkpoint every CraftedApp state transition]
**Status:** Accepted  
**Context:** The build pipeline requires that every state transition be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. CraftedApp participates in this staged workflow and must support resumability and auditability.  
**Decision:** Persist a checkpoint for every CraftedApp state transition and align checkpoint naming with the repository’s staged workflow model. Do not advance to a new stage without recording the prior transition outcome.  
**Consequences:** CraftedApp must model progress as explicit states rather than implicit control flow. Recovery, retry, and audit tooling can resume from known checkpoints. Additional persistence logic is mandatory wherever state advances occur.  
**Rejected alternatives:**  
- Checkpoint only major milestones such as commit and CI pass. Rejected because the repository requires every transition to be checkpointed.  
- Derive state from Git history or logs after the fact. Rejected because derived state is incomplete and unreliable for resumption.  
- Keep state only in memory during a run. Rejected because it breaks restartability and audit expectations.

## [Generate and maintain CI workflows in the standard locations]
**Status:** Accepted  
**Context:** The build pipeline defines standard CI outputs: `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. CI workflow generation is handled by a critical file and depends on `.github` being an allowed root. CraftedApp must not invent incompatible workflow placement or naming.  
**Decision:** Generate CraftedApp CI workflows under `.github` using the repository’s established workflow conventions and standard filenames where applicable, including `crafted-ci.yml` and `crafted-ci-macos.yml` for Swift-related paths.  
**Consequences:** CraftedApp CI integration remains discoverable and compatible with existing automation. Workflow naming and placement are constrained by repository convention, limiting custom layout choices. Swift-capable components must account for macOS workflow generation.  
**Rejected alternatives:**  
- Place workflows under a custom directory such as `configs/ci`. Rejected because GitHub Actions requires `.github/workflows` conventions and the repository already standardizes CI generation.  
- Use subsystem-specific workflow names without the standard prefixes. Rejected because it reduces consistency and complicates automation.  
- Support only Ubuntu CI. Rejected because Swift-related paths require macOS CI support.

## [Align CraftedApp with the gated pipeline rather than auto-merging]
**Status:** Accepted  
**Context:** The pipeline includes a gate in which the operator approves or corrects before merge. CraftedApp may automate generation, testing, and CI preparation, but final merge authority is intentionally not fully autonomous.  
**Decision:** Stop CraftedApp automation at the operator gate and require explicit approval or correction before merge. Do not implement autonomous merge behavior as part of the subsystem.  
**Consequences:** CraftedApp must expose outputs suitable for operator review and correction. End-to-end automation remains intentionally bounded, which may reduce throughput but preserves control. Merge-related features must integrate with approval state rather than bypass it.  
**Rejected alternatives:**  
- Auto-merge once tests and CI pass. Rejected because the documented pipeline requires an operator gate before merge.  
- Make operator approval optional via configuration. Rejected because the gate is a process control, not a convenience setting.  
- Defer gating to external GitHub branch protection only. Rejected because the repository defines an explicit application-level gate.

## [Prefer extension of shared pipeline stages over CraftedApp-specific parallel workflows]
**Status:** Accepted  
**Context:** The repository describes a common staged pipeline for generation, validation, fix loops, test, CI, and gating. Parallel subsystem-specific workflows would fragment state handling, checkpoints, and review expectations.  
**Decision:** Implement CraftedApp behavior as extensions or parameterizations of the shared pipeline stages rather than as a separate bespoke workflow engine.  
**Consequences:** CraftedApp must fit into existing stage semantics and state names. Subsystem behavior may need adaptation to common abstractions, but operational consistency is preserved. Tooling for checkpoints, CI, and operator review can be reused.  
**Rejected alternatives:**  
- Build an independent CraftedApp workflow tailored only to subsystem needs. Rejected because it duplicates orchestration and breaks common pipeline guarantees.  
- Encode CraftedApp as a single opaque pipeline stage. Rejected because it would hide meaningful transitions and undermine checkpoint granularity.