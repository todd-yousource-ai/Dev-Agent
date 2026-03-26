# DECISIONS.md

## [Repository documentation is the source of truth]
**Status:** Accepted

**Context:** CraftedAgent operates inside a repository with explicit architectural documentation boundaries. The repository layout distinguishes `forge-docs/` as the location for all TRDs and PRDs, and `forge-standards/` as the location for implementation constraints such as architecture, interfaces, decisions, and conventions. The subsystem must be constrained by these documents before any implementation work proceeds.

**Decision:** Read and treat `forge-docs/` and `forge-standards/` as authoritative inputs before modifying CraftedAgent behavior. Require implementation and changes in CraftedAgent to conform to documented TRDs, PRDs, and standards artifacts, with `DECISIONS.md` acting as a binding implementation constraint.

**Consequences:** CraftedAgent cannot define behavior solely from code-local assumptions. Changes must remain traceable to repository documentation. Implementations that conflict with documented standards are invalid even if they appear locally correct. Build and orchestration logic must preserve compatibility with the documented repository structure.

**Rejected alternatives:**  
- Infer behavior only from existing source code; rejected because repository documents are explicitly designated as source of truth.  
- Store subsystem decisions ad hoc in code comments or issues; rejected because standards belong in `forge-standards/` and must be consistently discoverable.  
- Allow implementation to precede document review; rejected because the repository explicitly requires reading these materials before building.

## [Critical files are protected change points]
**Status:** Accepted

**Context:** Several files are identified as critical because they enforce system-wide behavior: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Modifications to these files can alter generation, orchestration, GitHub interactions, security boundaries, and CI behavior across every pull request.

**Decision:** Treat the listed critical files as protected change points. Require any CraftedAgent change that touches these files to preserve their documented responsibilities and system invariants, especially generation loop integrity, orchestration limits, path validation, SHA-safe GitHub writes, and CI workflow generation.

**Consequences:** CraftedAgent implementation must not bypass or duplicate the responsibilities held by these files. Security, orchestration, and GitHub write behavior must be centralized in their designated modules. Refactors that spread these concerns into unrelated files are constrained. Reviews for these files must be held to a higher scrutiny because their blast radius is system-wide.

**Rejected alternatives:**  
- Freely redistribute logic from critical files across the codebase; rejected because it weakens the documented control points and increases risk.  
- Bypass critical modules for expedient feature work; rejected because these files define mandatory system boundaries.  
- Treat all files as equally mutable; rejected because the repository explicitly identifies certain files as affecting every PR and therefore requiring special protection.

## [All write paths must pass through path security]
**Status:** Accepted

**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. Lessons learned from GitHub integration show that invalid root handling can fail silently or be rejected, especially for unexpected roots and dot-prefixed paths.

**Decision:** Route every CraftedAgent file write, file update, and repository path mutation through the centralized path security layer. Forbid direct write operations that bypass `src/path_security.py`.

**Consequences:** CraftedAgent must not perform raw filesystem or repository writes without security validation. New features involving file creation, patching, artifact generation, or workflow updates must integrate with the existing path validation boundary. This centralizes enforcement of root allowlists and prevents drift in path handling logic.

**Rejected alternatives:**  
- Perform local path checks inside each feature module; rejected because duplicated validation creates inconsistency and weakens the security boundary.  
- Allow direct writes for “trusted” internal operations; rejected because the requirement applies to every write path.  
- Validate only before GitHub commits rather than before all writes; rejected because the security boundary is defined at the write-path level, not only at commit time.

## [Repository root writes are constrained by an explicit allowlist]
**Status:** Accepted

**Context:** GitHub integration lessons learned require an explicit allowlist of valid repository roots. Standard allowed roots include `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Dot-prefixed roots such as `.github` require explicit handling because generic validators often reject them.

**Decision:** Enforce an explicit allowlist of permitted repository root directories for all CraftedAgent write operations, including explicit support for `.github` as a valid dot-prefixed root.

**Consequences:** CraftedAgent cannot write to arbitrary top-level directories. New root-level targets must be intentionally added to the allowlist before use. CI workflow generation under `.github` remains supported, while unexpected roots are denied consistently. Path validation logic must preserve dot-prefixed root handling rather than relying on generic directory-name heuristics.

**Rejected alternatives:**  
- Allow writes to any existing directory in the repository; rejected because unexpected roots can fail silently or violate security constraints.  
- Use a denylist of forbidden roots; rejected because the documented requirement is explicit allowlisting.  
- Exclude dot-prefixed roots from automation; rejected because `.github` is required for CI workflow generation.

## [GitHub I/O is centralized in github_tools]
**Status:** Accepted

**Context:** `src/github_tools.py` is designated as the module for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. GitHub writes are operationally sensitive and require consistency to avoid conflicts, stale updates, and API misuse.

**Decision:** Centralize all CraftedAgent GitHub reads and writes through `src/github_tools.py`. Preserve path validation, rate limiting, and SHA-aware update protocol as mandatory behavior for GitHub interactions.

**Consequences:** CraftedAgent must not call GitHub APIs through ad hoc clients in feature-specific modules when existing I/O paths apply. Update flows must remain SHA-safe to prevent overwriting concurrent changes. Rate limiting and path validation behavior remain consistent across all GitHub operations. New GitHub capabilities must extend the central module rather than bypass it.

**Rejected alternatives:**  
- Let each subsystem own its own GitHub API client; rejected because it fragments protocol handling and increases security and correctness risk.  
- Omit SHA handling for simpler file updates; rejected because concurrent repository changes require correct GitHub update semantics.  
- Defer rate limiting to external infrastructure; rejected because the critical file definition explicitly assigns this responsibility to `github_tools.py`.

## [Pipeline orchestration remains in build_director with bounded complexity]
**Status:** Accepted

**Context:** `src/build_director.py` owns pipeline orchestration, and the repository imposes a strict cyclomatic complexity limit of 15 for every stage. The build pipeline spans multiple phases, and orchestration logic is a known complexity hotspot.

**Decision:** Keep CraftedAgent pipeline orchestration centralized in `src/build_director.py` and enforce a maximum cyclomatic complexity of 15 for every stage implementation and stateful orchestration path.

**Consequences:** New pipeline behavior must be decomposed into simpler units rather than added as nested branching inside orchestration stages. Stage logic that would push complexity above 15 must be split or refactored. CraftedAgent cannot introduce orchestration shortcuts that undermine the documented stage structure or checkpointing behavior.

**Rejected alternatives:**  
- Allow orchestration complexity to grow in a single controller for convenience; rejected because the complexity limit is explicitly strict.  
- Distribute orchestration arbitrarily across many modules without a director; rejected because the build director is the designated orchestration point.  
- Enforce complexity only at file level rather than per stage; rejected because the documented limit applies to every stage.

## [Consensus generation remains centralized in consensus.py]
**Status:** Accepted

**Context:** `src/consensus.py` is the core generation loop, and changes there affect every PR the agent builds. CraftedAgent depends on predictable generation behavior to produce consistent pull request outputs across the pipeline.

**Decision:** Preserve `src/consensus.py` as the central generation loop for CraftedAgent. Require changes to generation behavior to extend or modify the consensus path deliberately rather than creating parallel generation loops.

**Consequences:** CraftedAgent must not introduce competing generation engines that diverge from the main consensus flow. Cross-cutting generation behavior should be applied at the central loop so it affects all PRs consistently. Changes to this file must be considered high-impact and validated accordingly.

**Rejected alternatives:**  
- Create feature-specific generation loops outside `consensus.py`; rejected because this would fragment behavior and make PR outputs inconsistent.  
- Treat consensus as optional for some PR classes; rejected because it is defined as the core generation loop affecting every PR.  
- Duplicate consensus logic in callers for speed of implementation; rejected because duplication increases drift and correctness risk.

## [State transitions are checkpointed end-to-end]
**Status:** Accepted

**Context:** The build pipeline requires that every state transition be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. Checkpointing is necessary for recovery, auditability, and operator control across long-running automation.

**Decision:** Checkpoint every CraftedAgent state transition, including all documented per-PR lifecycle stages, and do not advance pipeline state without recording the transition.

**Consequences:** CraftedAgent must maintain durable state records throughout execution. Recovery logic can resume from known checkpoints rather than recomputing ambiguous state. Implementations that collapse multiple stages into an untracked transition are disallowed. Audit trails become available for diagnosing failures and operator interventions.

**Rejected alternatives:**  
- Checkpoint only major milestones such as commit and CI completion; rejected because every state transition is required to be checkpointed.  
- Keep state only in memory during a run; rejected because recovery and auditability require durable transitions.  
- Infer missing states after the fact from Git history or CI status; rejected because explicit checkpointing is mandated.

## [Per-PR lifecycle stages are fixed control points]
**Status:** Accepted

**Context:** The documented per-PR stages are `branch_opened → code_generated → tests_passed → committed → ci_passed`. These stages define the expected control flow from generation through validation and integration.

**Decision:** Implement CraftedAgent PR execution against the fixed documented lifecycle stages and preserve their ordering as control points for status, gating, and recovery.

**Consequences:** CraftedAgent cannot skip, reorder, or merge these lifecycle stages without a documented change to standards. Monitoring, checkpointing, and operator workflows can rely on stable stage names and sequencing. New internal substeps may exist, but they must map cleanly onto the fixed lifecycle.

**Rejected alternatives:**  
- Use subsystem-specific stage names; rejected because shared lifecycle names are needed for consistency across the build system.  
- Merge testing, commit, and CI into one generic “validated” state; rejected because the documented stages are more granular and checkpointed individually.  
- Permit dynamic stage ordering based on repository type; rejected because stable control points are required.

## [Test remediation uses a bounded fix loop]
**Status:** Accepted

**Context:** The build pipeline defines a fix loop after parsing, linting, and import checks, using `pytest` with up to 20 attempts and a failure-type-aware strategy. This loop is part of the standard generation-and-repair workflow.

**Decision:** Implement CraftedAgent test remediation as a bounded fix loop of at most 20 `pytest` attempts, with repair behavior informed by failure type rather than blind repetition.

**Consequences:** CraftedAgent must stop after the configured upper bound instead of retrying indefinitely. Repair logic should inspect failure classes and adapt remediation strategies. Pipeline timing and resource usage remain predictable. A failure after the maximum attempts must surface as a controlled pipeline failure rather than hidden churn.

**Rejected alternatives:**  
- Retry tests indefinitely until green; rejected because it creates unbounded execution and contradicts the documented limit.  
- Use a single retry only; rejected because the standard workflow explicitly includes an iterative fix loop.  
- Retry identically without failure-aware adaptation; rejected because the strategy is required to be failure-type-aware.

## [CI workflow generation is a first-class subsystem responsibility]
**Status:** Accepted

**Context:** `src/ci_workflow.py` generates CI workflows, and the pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. Workflow files live under `.github`, which must be explicitly allowlisted.

**Decision:** Generate and manage CraftedAgent CI workflows through `src/ci_workflow.py`, producing the documented Linux and macOS workflow variants as appropriate for repository content.

**Consequences:** CraftedAgent must not emit CI YAML from unrelated modules or templates that bypass the CI workflow generator. CI outputs must remain compatible with `.github` path security rules and the documented platform split. Swift-targeting repositories require macOS workflow support in addition to standard Linux CI.

**Rejected alternatives:**  
- Handcraft workflow files in feature code; rejected because workflow generation is assigned to a dedicated critical module.  
- Emit only a single Ubuntu workflow for all repositories; rejected because Swift support requires a macOS workflow variant.  
- Store generated workflows outside `.github`; rejected because GitHub Actions expects workflows there and `.github` is explicitly allowed for this purpose.

## [Operator gate is mandatory before merge]
**Status:** Accepted

**Context:** The build pipeline includes a gate in which the operator approves or corrects before merge. Gate decisions are part of the controlled process, not optional post-processing.

**Decision:** Require an explicit operator approval or correction step before CraftedAgent-driven changes are considered merge-ready.

**Consequences:** CraftedAgent cannot self-merge solely on the basis of generated code, passing tests, or passing CI. Human oversight remains part of the release control boundary. Workflow implementations must expose sufficient state and artifacts for operator review before merge progression.

**Rejected alternatives:**  
- Auto-merge after CI passes; rejected because the documented gate requires operator approval or correction before merge.  
- Make operator review optional for low-risk changes; rejected because the gate is defined as a standard pipeline stage.  
- Replace operator review with heuristic confidence thresholds; rejected because a human approval/correction decision is explicitly required.