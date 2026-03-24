# DECISIONS.md

## Repository structure and source-of-truth boundaries
**Status:** Accepted

**Context:** ForgeAgent operates in a repository with explicit separation between product/design documents, engineering standards, backend runtime, application shell, and tests. The TRDs state that all TRDs and PRDs live under `forge-docs/`, and the repository layout defines `forge-standards/`, `src/`, `Crafted/`, `CraftedTests/`, and `tests/` as distinct areas with different purposes. The agent must not blur these boundaries because implementation, review, and governance depend on them.

**Decision:** Treat `forge-docs/` as the authoritative source for requirements, treat `forge-standards/` as the authoritative source for engineering constraints, implement ForgeAgent backend logic only under `src/`, place macOS shell code only under `Crafted/`, place Swift tests only under `CraftedTests/`, and place Python tests only under `tests/`.

**Consequences:**  
- ForgeAgent implementation must not relocate requirements or standards into code directories.  
- Changes to behavior must trace back to documents in `forge-docs/` and constraints in `forge-standards/`.  
- Backend features for the subsystem must be added in `src/`, not embedded in workflow files, docs, or app-shell code.  
- Test placement is constrained by language and runtime.  
- Any automation that reads or writes across these boundaries must preserve the repository layout.

**Rejected alternatives:**  
- **Co-locating requirements next to implementation:** Rejected because TRDs and PRDs are explicitly centralized in `forge-docs/` as the source of truth.  
- **Placing ForgeAgent logic in the Swift app shell:** Rejected because backend implementation belongs in `src/`, and mixing orchestration logic into `Crafted/` would violate repository boundaries.  
- **Using a flat repository layout:** Rejected because the documented layout encodes ownership, review expectations, and execution context.

## Critical-file modification discipline
**Status:** Accepted

**Context:** Several files are designated as critical and must be read before modification because they define core generation, orchestration, GitHub I/O, path security, and CI workflow generation. Uninformed edits to these files can destabilize all pull requests produced by ForgeAgent or weaken security boundaries.

**Decision:** Require any change that affects generation, orchestration, GitHub operations, write-path validation, or CI generation to first read and preserve the contracts embodied in `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`.

**Consequences:**  
- ForgeAgent changes must be designed with awareness of subsystem-critical contracts.  
- Refactors touching these files must preserve externally relied upon behavior unless the change explicitly updates standards and dependent code.  
- Reviews for changes in these files must treat them as high-risk and verify backward compatibility, security, and checkpoint semantics.  
- New code must integrate with these files rather than bypass them.

**Rejected alternatives:**  
- **Allowing direct feature additions without reading critical files:** Rejected because these files define cross-cutting contracts that affect every generated PR and all repository writes.  
- **Treating critical files as internal implementation details:** Rejected because the TRDs explicitly elevate them as files that must be read before modifying related behavior.  
- **Duplicating their functionality elsewhere:** Rejected because duplication would create divergent security, orchestration, and CI behavior.

## Consensus loop as the core generation path
**Status:** Accepted

**Context:** `src/consensus.py` is identified as the core generation loop, and changes there affect every PR the agent builds. ForgeAgent therefore needs a single, recognized generation path rather than multiple competing orchestration mechanisms.

**Decision:** Centralize PR generation behavior around the consensus-driven generation loop and require all feature work that changes generation semantics to integrate through `src/consensus.py` rather than introducing parallel generation paths.

**Consequences:**  
- PR generation behavior remains consistent across tasks.  
- Observability and debugging focus on one core loop instead of fragmented implementations.  
- New generation features must compose with the existing loop and its checkpoints.  
- Global behavior changes become explicit and reviewable in one place.

**Rejected alternatives:**  
- **Creating feature-specific generation loops in separate modules:** Rejected because it would fragment behavior and make every PR path inconsistent.  
- **Embedding generation logic inside CI or GitHub tooling layers:** Rejected because generation is a core runtime concern, not an I/O concern.  
- **Distributing generation decisions across multiple stages without a core loop:** Rejected because the TRD identifies a single core generation loop as the controlling mechanism.

## Pipeline orchestration through the build director
**Status:** Accepted

**Context:** `src/build_director.py` is the pipeline orchestrator, and the build pipeline is explicitly staged from generation through test, CI, and gate. The TRDs also state that complexity limits are strictly enforced per stage.

**Decision:** Orchestrate ForgeAgent stage progression exclusively through `src/build_director.py`, and preserve explicit stage boundaries for generation, validation, fix loop, CI, and gate.

**Consequences:**  
- Stage ordering remains explicit and inspectable.  
- Cross-stage transitions can be checkpointed and audited.  
- Feature additions that alter stage behavior must be expressed as changes to orchestration rather than ad hoc calls between modules.  
- The subsystem remains compatible with the documented build pipeline.

**Rejected alternatives:**  
- **Letting individual modules call each other directly to advance stages:** Rejected because it would obscure pipeline control flow and break checkpointability.  
- **Encoding orchestration primarily in CI workflows:** Rejected because runtime orchestration belongs in backend code and must exist independently of external workflow execution.  
- **Collapsing stages into a monolithic function:** Rejected because the documented pipeline is stage-based and subject to complexity limits.

## Maximum cyclomatic complexity of 15 per stage
**Status:** Accepted

**Context:** The README states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is called out as strictly enforcing this. This is a hard implementation constraint, not a guideline.

**Decision:** Enforce a maximum cyclomatic complexity of 15 for every pipeline stage implementation and refactor stage logic whenever a change would exceed that limit.

**Consequences:**  
- Stage implementations must remain decomposed into smaller helpers.  
- New feature work may require extracting subroutines instead of extending existing stage bodies.  
- Complexity growth is bounded, improving maintainability and reviewability.  
- Changes that would be simpler as large conditional blocks are disallowed.

**Rejected alternatives:**  
- **Allowing higher complexity for “core” stages:** Rejected because the README defines the limit for every stage, not only selected ones.  
- **Treating 15 as a soft target:** Rejected because the build director constraint is stated as strictly enforced.  
- **Measuring complexity only at module level:** Rejected because the requirement is stage-specific.

## Mandatory checkpointing of every state transition
**Status:** Accepted

**Context:** The build pipeline requires that every state transition be checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This supports recovery, auditability, and operator oversight.

**Decision:** Persist a checkpoint for every pipeline state transition, including all per-PR transitions, before considering the transition complete.

**Consequences:**  
- ForgeAgent must maintain durable state for resumability and audit trails.  
- Transition logic cannot be purely in-memory.  
- Any new stage or sub-state introduced in the subsystem must define corresponding checkpoint semantics.  
- Recovery behavior can rely on explicit prior state rather than inferred execution.

**Rejected alternatives:**  
- **Checkpointing only major milestones:** Rejected because the requirement explicitly applies to every state transition.  
- **Using logs alone instead of checkpoints:** Rejected because logs do not provide reliable resumable state.  
- **Checkpointing only after success paths:** Rejected because transition visibility is needed across all pipeline movement, not only final outcomes.

## Gate decisions require explicit operator approval or correction
**Status:** Accepted

**Context:** The build pipeline includes a gate stage where the operator approves or corrects before merge, and gate decisions are recorded. ForgeAgent must therefore preserve human control at merge boundaries.

**Decision:** Require explicit operator approval or correction at the gate before merge, and record each gate decision as part of the pipeline state.

**Consequences:**  
- ForgeAgent cannot auto-merge solely on technical success.  
- Human review remains a required control point.  
- Audit trails must include gate outcomes and any operator corrections.  
- UX and backend flows must model gate status as a first-class state.

**Rejected alternatives:**  
- **Automatically merging when tests and CI pass:** Rejected because the documented pipeline requires operator approval or correction before merge.  
- **Treating gate review as optional metadata:** Rejected because gate decisions are part of the required recorded process.  
- **Embedding approval implicitly in CI success:** Rejected because CI success and operator approval are separate stages.

## GitHub I/O must be centralized in github_tools
**Status:** Accepted

**Context:** `src/github_tools.py` is designated as handling all GitHub I/O, including path validation, rate limiting, and SHA protocol. Centralizing these concerns prevents inconsistent API usage and accidental bypass of safety checks.

**Decision:** Route all GitHub reads, writes, branch operations, and related API interactions through `src/github_tools.py`; do not perform direct GitHub I/O elsewhere in the subsystem.

**Consequences:**  
- Rate limiting behavior is consistent.  
- SHA handling and update semantics remain uniform.  
- Security and validation policies can be enforced at one boundary.  
- Tests can mock GitHub behavior through a single integration seam.

**Rejected alternatives:**  
- **Calling GitHub APIs directly from feature modules:** Rejected because it would bypass centralized path validation, rate limiting, and SHA protocol enforcement.  
- **Splitting GitHub I/O across orchestration and generation modules:** Rejected because it would create duplicate protocol logic and inconsistent behavior.  
- **Delegating all GitHub concerns to external CI workflows:** Rejected because ForgeAgent runtime needs controlled repository interaction before and beyond CI.

## All write paths must pass through the path security boundary
**Status:** Accepted

**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. This is a direct threat-containment rule for repository mutation.

**Decision:** Validate every filesystem and repository write target through `src/path_security.py` before performing the write, with no bypasses for internal tools, tests, or “trusted” code paths.

**Consequences:**  
- All mutation logic must call the security boundary first.  
- New write-capable utilities must integrate with the same validator instead of performing independent checks.  
- Security review can focus on a single enforcement point.  
- Convenience shortcuts that write directly to disk or repository paths are prohibited.

**Rejected alternatives:**  
- **Per-module ad hoc path checks:** Rejected because distributed checks are harder to verify and easier to bypass.  
- **Trusting only the caller to provide safe paths:** Rejected because the TRD defines a dedicated security boundary for all writes.  
- **Applying path validation only to user-supplied paths:** Rejected because the requirement covers every write path.

## CI workflow generation must be owned by ci_workflow
**Status:** Accepted

**Context:** `src/ci_workflow.py` is identified as the generator for CI workflow output. The README specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift, so workflow generation must stay consistent with the documented platform split.

**Decision:** Generate CI workflow definitions through `src/ci_workflow.py` and preserve the two-target model: `crafted-ci.yml` on `ubuntu-latest` for general pipeline execution and `crafted-ci-macos.yml` for Swift/macOS-specific execution.

**Consequences:**  
- Workflow generation logic remains centralized and testable.  
- Platform-specific CI responsibilities stay explicit.  
- Changes to CI behavior must update the generator rather than hand-editing generated output in multiple places.  
- Swift-specific validation continues to target the correct macOS environment.

**Rejected alternatives:**  
- **Hand-maintaining workflow YAML without a generator boundary:** Rejected because workflow generation is already assigned to a dedicated critical file.  
- **Using a single CI workflow for all runtimes:** Rejected because Swift/macOS work requires a separate macOS-targeted workflow.  
- **Generating workflows from multiple modules:** Rejected because it would fragment ownership and increase drift risk.

## Validation and fix-loop stages are mandatory before CI gate progression
**Status:** Accepted

**Context:** The documented build pipeline includes validation (`ast.parse → ruff → import check`) and a fix loop (`pytest` up to 20 attempts with failure-type-aware strategy) before CI and gate. These are not optional optimizations; they are part of the standard path to producing a candidate PR.

**Decision:** Execute validation and the bounded fix loop before advancing work to CI and gate, and cap automated test-fix attempts at 20 with behavior informed by failure type.

**Consequences:**  
- ForgeAgent must distinguish validation failures from test failures and respond appropriately.  
- Infinite or open-ended self-repair loops are prohibited.  
- The system must classify failures well enough to support failure-type-aware remediation strategy.  
- CI is reserved for code that has already passed local validation and bounded test repair attempts.

**Rejected alternatives:**  
- **Skipping local validation and relying on CI only:** Rejected because the documented pipeline includes validation before CI.  
- **Using an unbounded repair loop until success:** Rejected because the fix loop is explicitly capped at 20 attempts.  
- **Applying a single generic retry strategy to all failures:** Rejected because the pipeline requires failure-type-aware handling.

## Failure handling must align with repository-level taxonomy
**Status:** Accepted

**Context:** The repository includes `FAILURE_TAXONOMY.md` with seven root-cause buckets, and the build pipeline references failure-type-aware strategy in the fix loop. ForgeAgent needs a common vocabulary for diagnosing and reacting to failures.

**Decision:** Classify build, validation, test, and CI failures according to the repository failure taxonomy and use that classification to drive remediation and reporting.

**Consequences:**  
- Failure responses become consistent across runs and reviewers.  
- Telemetry, checkpoint data, and operator-facing reports can aggregate failures by root cause.  
- New remediation logic must key off taxonomy categories rather than ad hoc string matching alone.  
- The fix loop can remain deterministic and auditable.

**Rejected alternatives:**  
- **Handling failures as raw tool output only:** Rejected because raw output does not provide stable categories for strategy selection.  
- **Defining a separate ForgeAgent-specific taxonomy:** Rejected because the repository already defines a shared failure taxonomy.  
- **Retrying all failures identically:** Rejected because the documented fix loop is failure-type-aware.

## ForgeAgent must preserve the macOS application shell boundary
**Status:** Accepted

**Context:** TRD-1 defines the macOS application shell and root view decision tree under the `Crafted/` app. ForgeAgent is a backend subsystem and must not subsume application navigation or onboarding concerns.

**Decision:** Keep ForgeAgent backend responsibilities separate from the SwiftUI application shell, and treat app navigation, onboarding state, and root-view selection as concerns owned by `Crafted/`, not by backend orchestration code.

**Consequences:**  
- Backend code in `src/` must expose service/state interfaces rather than directly encoding UI navigation logic.  
- The Swift app remains responsible for onboarding and root view composition.  
- Backend changes must not require UI-layer architectural inversion.  
- Cross-layer integration should occur through defined interfaces, not shared implementation assumptions.

**Rejected alternatives:**  
- **Embedding UI flow decisions in ForgeAgent backend code:** Rejected because root-view and onboarding decisions belong to the macOS application shell.  
- **Moving onboarding logic into Python runtime for convenience:** Rejected because it would violate the documented shell architecture.  
- **Treating the app shell as a thin wrapper around backend state machine internals:** Rejected because the SwiftUI tree has its own explicit decision structure and ownership.