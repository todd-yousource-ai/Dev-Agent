# DECISIONS.md

## Repository source-of-truth placement
**Status:** Accepted

**Context:** ForgeAgent operates in a repository with explicit separation between product requirements, engineering standards, and implementation. The repository structure defines `forge-docs/` as the location for all TRDs and PRDs, and `forge-standards/` as the location for architecture and implementation standards. This separation is required so the agent can reliably discover authoritative inputs before generating or modifying code.

**Decision:** Treat `forge-docs/` as the sole source of truth for TRDs and PRDs, and treat `forge-standards/` as the sole source of truth for implementation standards including `DECISIONS.md`, `ARCHITECTURE.md`, `INTERFACES.md`, `CONVENTIONS.md`, and `build_rules.md`.

**Consequences:** ForgeAgent implementations must read requirements from `forge-docs/` before making changes. Standards and constraints must be loaded from `forge-standards/`. The subsystem must not infer requirements from scattered code comments, ad hoc markdown, or undocumented conventions when authoritative documents exist in these directories.

**Rejected alternatives:** Storing TRDs alongside source code was rejected because it weakens discoverability and increases drift between requirements and implementation. Allowing standards to live across multiple arbitrary directories was rejected because the agent needs deterministic locations for policy loading. Treating README files as equal authority to TRDs was rejected because README content is summary-oriented and not the formal source of truth.

## Critical-file change discipline
**Status:** Accepted

**Context:** Several files define core system behavior and security boundaries for the agent: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes to these files have disproportionate impact on generation, orchestration, GitHub interactions, path safety, and CI workflow creation.

**Decision:** Require explicit review of the designated critical files before modifying them, and treat changes to these files as high-risk subsystem changes that must preserve their documented responsibilities.

**Consequences:** Implementations must inspect these files before edits and must avoid incidental refactors that change behavior outside the intended scope. Changes touching these files should be minimized, narrowly scoped, and validated against the subsystem invariants they protect. New code must not bypass or duplicate responsibilities owned by these files.

**Rejected alternatives:** Treating all files as equal risk was rejected because it obscures the files that define global behavior and security boundaries. Freely refactoring critical files during feature work was rejected because it increases regression risk in generation, orchestration, and security-sensitive paths. Re-implementing their logic in parallel helper modules was rejected because it fragments authority and creates inconsistent behavior.

## Path writes must pass through the security boundary
**Status:** Accepted

**Context:** The subsystem includes `src/path_security.py` as the explicit security boundary for filesystem writes. GitHub integration lessons learned show that unexpected root directories may be silently rejected or fail path validation, and dot-prefixed roots such as `.github` require explicit handling.

**Decision:** Route every repository write path through `src/path_security.py` validation before file creation, modification, staging, or commit preparation.

**Consequences:** No component in ForgeAgent may write directly to the repository without first passing path validation. All file-writing helpers, GitHub commit builders, code generators, and CI workflow emitters must use the same validation path. This constrains implementation toward centralized path authorization and prevents ad hoc exceptions.

**Rejected alternatives:** Letting each module validate its own paths was rejected because duplicated path logic diverges and creates bypass opportunities. Validating only at commit time was rejected because unsafe paths could still be generated, cached, or acted on earlier in the workflow. Relying on GitHub API failures alone was rejected because silent rejection and inconsistent behavior are not a sufficient security boundary.

## Repository root allowlist enforcement
**Status:** Accepted

**Context:** GitHub integration requires explicit allowlisting of valid repository roots. Standard project roots include `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Dot-prefixed roots are especially sensitive because generic validators often reject them.

**Decision:** Enforce an explicit root-directory allowlist for all repository paths, including explicit support for `.github` when CI workflow files are generated or modified.

**Consequences:** ForgeAgent may only create or modify files under approved roots unless the allowlist is intentionally expanded. New project layouts require explicit policy updates rather than opportunistic writes. Workflow generation must account for `.github` as a valid root and may not depend on generic path normalization that strips or rejects dot-prefixed roots.

**Rejected alternatives:** Allowing writes under any path beneath the repository root was rejected because it weakens security and increases the chance of malformed or policy-breaking commits. Inferring valid roots dynamically from current repository contents was rejected because accidental files could expand the effective trust boundary. Special-casing `.github` outside the general allowlist mechanism was rejected because it creates inconsistent enforcement.

## Centralize all GitHub I/O in `src/github_tools.py`
**Status:** Accepted

**Context:** `src/github_tools.py` is identified as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. GitHub operations are a failure-prone integration point and require consistent behavior across reads, writes, commits, and updates.

**Decision:** Centralize all GitHub API interactions in `src/github_tools.py` and prohibit direct GitHub I/O from other modules.

**Consequences:** Other components must depend on `src/github_tools.py` abstractions rather than calling GitHub APIs directly. Rate limiting, SHA precondition handling, path checks, and repository mutation semantics remain consistent. This constrains implementation toward a single integration boundary and simplifies testing and auditing.

**Rejected alternatives:** Allowing each subsystem to call the GitHub API directly was rejected because it would duplicate rate-limit handling, path validation, and SHA logic. Splitting reads and writes across separate modules was rejected because the same protocol constraints apply to both and should remain coordinated. Performing path validation outside the GitHub layer was rejected because repository mutation safety must be enforced at the point of I/O as well as earlier in the workflow.

## Preserve the consensus engine as the core generation loop
**Status:** Accepted

**Context:** `src/consensus.py` is identified as the core generation loop, and changes here affect every pull request the agent builds. This makes the consensus engine a subsystem-wide control point rather than a feature-local implementation detail.

**Decision:** Keep generation orchestration centered in `src/consensus.py`, and require all PR-building generation flows to pass through this core loop.

**Consequences:** New generation capabilities must integrate with the consensus engine rather than bypassing it with custom one-off flows. Behavioral changes in generation must be implemented as controlled changes to the shared loop or as explicit extensions around it. This constrains architectural evolution toward one authoritative PR-generation pathway.

**Rejected alternatives:** Creating specialized generation loops for different task types was rejected because it would fragment behavior and reduce predictability across PRs. Moving core generation logic into scattered feature modules was rejected because it would make global reasoning and validation difficult. Treating `src/consensus.py` as just one possible implementation path was rejected because the documented architecture defines it as the core loop.

## Build pipeline orchestration belongs in `src/build_director.py`
**Status:** Accepted

**Context:** `src/build_director.py` is identified as the pipeline orchestrator, and the repository enforces a strict maximum cyclomatic complexity of 15 for every stage. The build pipeline includes staged execution and a structured fix loop, making orchestration logic both central and constrained.

**Decision:** Concentrate pipeline orchestration in `src/build_director.py` and enforce a maximum cyclomatic complexity of 15 for every pipeline stage implementation.

**Consequences:** Pipeline stages must remain decomposed enough to satisfy the complexity limit. New build behavior should extend stage composition, not accumulate unbounded branching in orchestration code. The build director remains the authority for sequencing pipeline stages and coordinating transitions between them.

**Rejected alternatives:** Embedding orchestration directly inside individual stage modules was rejected because sequencing authority would become fragmented. Ignoring the complexity limit for orchestration code was rejected because the repository explicitly mandates it. Building a monolithic controller with deeply nested conditionals was rejected because it would violate maintainability and the stated complexity bound.

## Implement and preserve the staged build pipeline
**Status:** Accepted

**Context:** The documented build pipeline includes explicit stages, including static validation (`ast.parse`, `ruff`, import check), a failure-type-aware fix loop with up to 20 pytest attempts, CI workflow generation, and a final approval gate before merge. The stages are part of the operating model of ForgeAgent rather than optional implementation details.

**Decision:** Implement the build process as explicit ordered stages, including static validation, fix-loop retries capped at 20 attempts, CI execution, and an operator gate before merge.

**Consequences:** ForgeAgent cannot collapse the workflow into an unstructured “generate and hope” loop. Retry behavior must be bounded and must use failure-type-aware strategies. CI and human approval remain required gates in the pipeline. Stage boundaries must be visible enough to support checkpointing and auditability.

**Rejected alternatives:** Using an unlimited self-healing loop was rejected because retry count is explicitly capped. Skipping static validation in favor of tests only was rejected because the documented pipeline requires syntax, lint, and import checks. Auto-merging after tests without an operator gate was rejected because the process requires approval or correction before merge.

## Checkpoint every pipeline state transition
**Status:** Accepted

**Context:** The build pipeline requires that every state transition be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. Checkpointing is necessary for auditability, recovery, and deterministic progress tracking.

**Decision:** Persist a checkpoint for every pipeline state transition, including the documented per-PR milestones.

**Consequences:** The subsystem must expose explicit state transitions rather than implicit progress. Recovery and resume logic must use checkpoints as the source of truth for current status. New stages or milestones must define corresponding checkpoints. Implementations may not treat transitions as ephemeral in-memory events only.

**Rejected alternatives:** Checkpointing only final success or failure was rejected because intermediate recovery and audit needs require transition-level persistence. Logging transitions without structured checkpoints was rejected because logs are not sufficient as resumable state. Checkpointing only selected “major” milestones was rejected because the requirement is every state transition.

## Generate CI workflows through `src/ci_workflow.py`
**Status:** Accepted

**Context:** `src/ci_workflow.py` is the module responsible for generating CI workflow files. The documented pipeline requires `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift projects, which implies consistent workflow emission with path-security compliance under `.github`.

**Decision:** Generate CI workflow definitions exclusively through `src/ci_workflow.py`, including `crafted-ci.yml` for Ubuntu and `crafted-ci-macos.yml` when Swift or macOS-specific builds are required.

**Consequences:** Workflow file generation must not be hand-assembled in unrelated modules. Platform-specific workflow selection belongs to the CI workflow generator. The module must interoperate with path security and `.github` allowlist rules. Changes to CI structure should be made in one place.

**Rejected alternatives:** Writing workflow YAML directly from the build director was rejected because workflow generation already has an owning module. Generating a single workflow for all languages and platforms was rejected because the documented pipeline requires a macOS workflow for Swift. Allowing arbitrary workflow filenames was rejected because standard names improve predictability and downstream automation.

## Enforce operator approval before merge
**Status:** Accepted

**Context:** The pipeline defines a final gate where the operator approves or corrects before merge. This gate is a control point for quality, safety, and oversight after automated generation, repair, commit, and CI execution.

**Decision:** Require an explicit operator approval or correction step before merge, and prohibit fully autonomous merge after CI success.

**Consequences:** ForgeAgent may prepare changes, run tests, commit, and validate CI, but it must stop short of merge until the operator authorizes continuation. User-facing flow and internal state models must represent this gate explicitly. Automation around merging must remain disabled unless approval is recorded.

**Rejected alternatives:** Auto-merging immediately after tests pass was rejected because the process requires operator review. Auto-merging after CI passes was rejected for the same reason. Making operator review optional only for “low-risk” changes was rejected because no such exception is defined in the documented process.