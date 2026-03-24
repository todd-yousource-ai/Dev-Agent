# DECISIONS.md

## [Keep ForgeAgent implementation inside the existing monorepo layout]
**Status:** Accepted  
**Context:** ForgeAgent is developed within a repository whose structure is already defined as a system-level constraint. The source of truth documents live under `forge-docs/`, implementation standards under `forge-standards/`, Python backend code under `src/`, Swift/macOS shell code under `Crafted/`, Swift tests under `CraftedTests/`, and Python tests under `tests/`. The subsystem must fit this layout so documentation, implementation, and validation remain aligned.  
**Decision:** Implement ForgeAgent within the existing repository layout. Place backend agent logic in `src/`, tests in `tests/`, and subsystem-level architectural constraints in `forge-standards/`. Treat `forge-docs/` as read-before-build source material and do not relocate or duplicate it into implementation directories.  
**Consequences:** All ForgeAgent code must be discoverable within the established monorepo structure. Documentation-driven development is enforced because TRDs and PRDs remain centralized in `forge-docs/`. Cross-cutting concerns such as standards, interfaces, and design decisions must remain in `forge-standards/` rather than being redefined locally in ad hoc subsystem files.  
**Rejected alternatives:**  
- Creating a standalone ForgeAgent repository: rejected because it would fragment the source of truth and break the documented repository contract.  
- Embedding TRD copies inside `src/`: rejected because duplicated documents drift and invalidate document-first development.  
- Placing agent code under a new top-level directory: rejected because it would diverge from the prescribed repository layout and reduce consistency with existing tooling and reviews.

## [Treat forge-docs as authoritative input and read before modifying implementation]
**Status:** Accepted  
**Context:** The repository explicitly identifies `forge-docs/` as the location where all TRDs and PRDs live and instructs builders to read them before building. ForgeAgent behavior is constrained by those documents, not by inferred implementation shortcuts.  
**Decision:** Read relevant TRDs and PRDs in `forge-docs/` before implementing or modifying ForgeAgent behavior. Treat those documents as authoritative requirements inputs and resolve ambiguity in favor of documented requirements rather than local convention.  
**Consequences:** ForgeAgent changes must be traceable to documented requirements. Developers cannot safely implement behavior based only on current code shape. This increases implementation discipline and reduces requirement drift.  
**Rejected alternatives:**  
- Using current source code as the primary source of truth: rejected because implementation may lag or diverge from approved design documents.  
- Treating TRDs as optional background material: rejected because the repository explicitly defines them as mandatory pre-build inputs.  
- Copying selected requirements into code comments and relying on those copies: rejected because derivative summaries are incomplete and become stale.

## [Do not modify critical pipeline and security files without explicit review]
**Status:** Accepted  
**Context:** Several files are explicitly called out as critical because they define system-wide behavior and safety boundaries: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes in these files have disproportionate impact across every generated PR, pipeline transition, repository write, and CI workflow.  
**Decision:** Require explicit targeted review before modifying any critical file. Read the file and its documented role before editing, and constrain changes to the minimal scope necessary. Preserve documented invariants in generation loops, orchestration, GitHub I/O, path validation, and CI workflow generation.  
**Consequences:** ForgeAgent contributors must treat these files as subsystem boundaries rather than ordinary modules. Refactors that touch them must account for system-wide effects, regression risk, and safety properties. Convenience edits in these files are disallowed when equivalent behavior can be implemented elsewhere.  
**Rejected alternatives:**  
- Treating all files uniformly for modification risk: rejected because the repository explicitly identifies high-impact files requiring extra care.  
- Freely refactoring critical files for style consistency: rejected because stylistic churn in control and security boundaries increases regression risk without product value.  
- Moving security or GitHub write behavior out of designated files ad hoc: rejected because it weakens boundary clarity and makes review harder.

## [Enforce the build pipeline as a staged state machine]
**Status:** Accepted  
**Context:** The build pipeline is defined as an ordered sequence of stages, including generation, static validation, fix loops, test and CI, and operator gating. Additionally, per-PR state transitions are explicitly named: `branch_opened → code_generated → tests_passed → committed → ci_passed`. This implies a stateful orchestration model rather than a best-effort script chain.  
**Decision:** Implement ForgeAgent pipeline orchestration as an explicit staged state machine with named transitions and durable stage progression. Do not bypass, reorder, or collapse required stages. Represent per-PR lifecycle states using the documented checkpoint sequence.  
**Consequences:** ForgeAgent must expose deterministic progress through known states, making recovery, audit, and resume behavior possible. Implementations must preserve stage semantics even when optimizing internals. Informal “run everything in one function” orchestration is prohibited.  
**Rejected alternatives:**  
- A linear fire-and-forget script without explicit states: rejected because it cannot support checkpointing, recovery, or reliable auditing.  
- Dynamically skipping documented stages when they appear unnecessary: rejected because it undermines governance and reproducibility.  
- Modeling only coarse success/failure without per-PR transitions: rejected because documented lifecycle states require more granular progression tracking.

## [Checkpoint every pipeline and per-PR state transition durably]
**Status:** Accepted  
**Context:** The pipeline specification requires every state transition to be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. This requirement exists to support resume, inspection, and operational control.  
**Decision:** Persist a durable checkpoint at every pipeline state transition and every per-PR lifecycle transition. Make checkpoint writes part of the transition contract rather than an optional observability feature.  
**Consequences:** ForgeAgent implementations must include persistent state recording for orchestrated progress. Recovery logic must resume from the last successful checkpoint instead of re-running arbitrarily. Failures to checkpoint are pipeline failures, not ignorable logging issues.  
**Rejected alternatives:**  
- Logging transitions without durable checkpoint persistence: rejected because logs are insufficient for reliable resume semantics.  
- Checkpointing only major stages: rejected because the requirement explicitly includes per-PR transitions.  
- Checkpointing only at the end of successful runs: rejected because it defeats failure recovery and auditability.

## [Maintain cyclomatic complexity of 15 or less for every pipeline stage]
**Status:** Accepted  
**Context:** The build pipeline documentation explicitly states that every stage has a maximum cyclomatic complexity of 15. This is a hard maintainability and reviewability constraint on orchestration logic.  
**Decision:** Keep each ForgeAgent pipeline stage at cyclomatic complexity 15 or below. When a stage approaches the limit, extract helpers or split responsibilities without changing the documented stage boundaries.  
**Consequences:** Implementations must favor decomposition over deeply branched stage logic. Reviews must reject stage methods that exceed the complexity threshold. Complexity reduction cannot be achieved by hiding logic in opaque dynamic dispatch that makes control flow less understandable.  
**Rejected alternatives:**  
- Allowing exceptions for “core orchestration” code: rejected because the complexity cap is explicitly stated as universal across stages.  
- Enforcing complexity only at the file or module level: rejected because the requirement applies per stage.  
- Ignoring complexity in favor of fewer functions: rejected because maintainability and bounded branching are explicit constraints.

## [Run static validation in the documented order before entering fix loops]
**Status:** Accepted  
**Context:** The pipeline defines a static validation sequence that includes `ast.parse`, `ruff`, and import checks before the fix loop and test execution phases. Ordering matters because syntax and lint failures should be surfaced before more expensive or noisier remediation cycles.  
**Decision:** Execute static validation in the documented order: parse, lint, then import validation, before entering test-driven fix loops. Do not run fix-loop remediation ahead of these prerequisite checks.  
**Consequences:** ForgeAgent must fail fast on malformed or structurally invalid code. Fix strategies can assume baseline syntactic validity before attempting iterative test repair. Pipeline changes that merge or reorder these checks require design-level reconsideration rather than implementation convenience.  
**Rejected alternatives:**  
- Running tests before static validation: rejected because it wastes resources and obscures simpler root causes.  
- Combining all checks into one opaque validation pass: rejected because it removes ordered failure semantics and makes remediation less targeted.  
- Entering fix loops immediately after code generation: rejected because the documented pipeline requires static gates first.

## [Bound automated fix loops to 20 attempts and make them failure-type-aware]
**Status:** Accepted  
**Context:** The pipeline specifies a fix loop using pytest with up to 20 attempts and a failure-type-aware strategy. This indicates bounded remediation rather than open-ended self-modification and requires strategy selection based on categorized failures.  
**Decision:** Limit ForgeAgent automated fix loops to a maximum of 20 attempts and select remediation strategies based on failure type rather than applying generic retries. Terminate the loop when the attempt budget is exhausted.  
**Consequences:** ForgeAgent must classify failures sufficiently to choose targeted repair behavior. Infinite or unbounded retry behavior is prohibited. Operators can reason about worst-case runtime and intervention points.  
**Rejected alternatives:**  
- Unlimited retries until tests pass: rejected because it creates runaway execution, unpredictable cost, and weakens operator control.  
- A fixed number of retries with identical behavior each time: rejected because the requirement explicitly calls for failure-type-aware strategy.  
- Manual intervention after the first failure: rejected because the documented pipeline includes an automated fix loop.

## [Generate and use platform-specific CI workflows]
**Status:** Accepted  
**Context:** The build pipeline requires Stage 5 CI execution using `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. The repository also contains both Python backend and macOS Swift application code, which have different runtime and platform needs.  
**Decision:** Generate and maintain distinct CI workflows for Linux-oriented general checks and macOS-specific Swift validation. Use `crafted-ci.yml` for Ubuntu-based execution and `crafted-ci-macos.yml` for Swift/macOS execution as documented.  
**Consequences:** ForgeAgent cannot collapse all CI behavior into a single platform workflow. CI generation logic must preserve the separation between general backend validation and Apple-platform-specific validation. Changes to CI must account for both environments.  
**Rejected alternatives:**  
- A single universal workflow on one runner type: rejected because Swift/macOS validation requires macOS-specific execution and the documents name separate workflows.  
- Running all checks only on macOS: rejected because it increases cost and diverges from the documented Ubuntu workflow.  
- Running only Python checks in CI and omitting Swift-specific validation: rejected because the repository includes a Swift application shell and documented macOS workflow.

## [Require operator approval or correction at the gate before merge]
**Status:** Accepted  
**Context:** The pipeline includes a final gate where the operator approves or corrects before merge. This establishes a human-controlled governance checkpoint rather than a fully autonomous merge path.  
**Decision:** Require an operator gate before merge. Do not allow ForgeAgent to merge solely on the basis of automated stage completion, test success, or CI success. Support operator approval and operator correction as explicit gate outcomes.  
**Consequences:** ForgeAgent remains human-supervised at merge time. Full automation ends at candidate readiness, not repository integration. Audit records must reflect human gate decisions distinctly from automated outcomes.  
**Rejected alternatives:**  
- Auto-merging after CI passes: rejected because it bypasses the explicitly required operator gate.  
- Treating operator review as advisory only: rejected because the gate is a required control point, not an optional review.  
- Allowing the system to infer approval from inactivity: rejected because gate decisions must be explicit.

## [Route every repository write path through src/path_security.py]
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary and every write path must pass through it. ForgeAgent performs code generation and repository modifications, so write-path enforcement is central to preventing unsafe file access and unintended mutations.  
**Decision:** Route every ForgeAgent filesystem write that affects the repository through `src/path_security.py`. Do not write directly to repository paths from agent logic, utilities, or adapters without path validation by this boundary module.  
**Consequences:** Path validation becomes mandatory for all code generation, file edits, workflow output, and patch application. New write helpers must integrate with the security boundary rather than bypassing it for convenience or performance.  
**Rejected alternatives:**  
- Performing local path checks in each caller: rejected because distributed validation is inconsistent and weakens the security boundary.  
- Validating only external or user-supplied paths: rejected because generated internal paths can also be unsafe if unchecked.  
- Writing directly and relying on code review for safety: rejected because the repository explicitly defines an enforced security boundary.

## [Centralize all GitHub I/O in src/github_tools.py]
**Status:** Accepted  
**Context:** `src/github_tools.py` is designated as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. GitHub interactions are cross-cutting and correctness-sensitive, especially when creating branches, updating contents, and coordinating PR state.  
**Decision:** Perform all ForgeAgent GitHub API interactions through `src/github_tools.py`. Preserve its responsibilities for path validation, rate limiting, and SHA-aware update protocol, and do not reimplement GitHub access in parallel modules.  
**Consequences:** ForgeAgent integrations must depend on a single GitHub I/O boundary. This reduces protocol drift, centralizes rate-limit behavior, and keeps SHA handling consistent. Direct HTTP or SDK calls from unrelated modules are prohibited unless first incorporated into `src/github_tools.py`.  
**Rejected alternatives:**  
- Allowing each feature module to call GitHub APIs directly: rejected because it duplicates protocol logic and undermines rate-limit coordination.  
- Splitting GitHub reads and writes across multiple ad hoc helpers: rejected because repository interaction semantics must remain centralized.  
- Bypassing SHA protocol handling for simple updates: rejected because content integrity and conflict handling depend on consistent protocol use.

## [Preserve src/consensus.py as the core generation loop boundary]
**Status:** Accepted  
**Context:** `src/consensus.py` is identified as the core generation loop, and changes there affect every PR the agent builds. ForgeAgent behavior depends on reliable, system-wide generation semantics.  
**Decision:** Treat `src/consensus.py` as the canonical generation loop boundary for ForgeAgent. Extend generation behavior by composing around this module or making narrowly scoped changes within it, rather than creating competing generation loops elsewhere.  
**Consequences:** The subsystem has one recognized center of generation control. Architectural experiments must not fork generation behavior into parallel orchestration paths that are hard to reason about or test consistently.  
**Rejected alternatives:**  
- Building new feature-specific generation loops outside `src/consensus.py`: rejected because they would fragment behavior and make PR outcomes inconsistent.  
- Replacing the core loop indirectly through wrappers that bypass its semantics: rejected because it obscures control flow and weakens reviewability.  
- Treating `src/consensus.py` as just another helper module: rejected because its impact is explicitly system-wide.

## [Preserve src/build_director.py as the pipeline orchestration boundary]
**Status:** Accepted  
**Context:** `src/build_director.py` is identified as the location for pipeline orchestration and is specifically associated with the strict complexity 15 limit. This file defines how stages coordinate, advance, and recover.  
**Decision:** Keep ForgeAgent pipeline orchestration centralized in `src/build_director.py`. Implement stage coordination there and avoid introducing shadow orchestrators in feature modules, tests, or CLI wrappers.  
**Consequences:** Pipeline behavior remains inspectable and coherent. Complexity management applies where orchestration actually lives. New execution entry points must delegate to the build director rather than implementing independent orchestration logic.  
**Rejected alternatives:**  
- Distributing orchestration decisions across many modules: rejected because it hides stage control flow and complicates checkpointing.  
- Moving orchestration into CLI scripts or UI handlers: rejected because orchestration must remain a backend concern with enforceable invariants.  
- Creating separate orchestrators for different artifact types: rejected because it would fragment pipeline semantics and state handling.

## [Record gate decisions and stage outcomes as explicit audit events]
**Status:** Accepted  
**Context:** The pipeline description states that every gate decision must be recorded, and all stage transitions are checkpointed. This implies an auditable execution trail distinguishing automated progression from human approval or correction.  
**Decision:** Persist explicit audit events for stage outcomes, checkpoint transitions, and operator gate decisions. Make approval, correction, failure, and progression visible as first-class recorded events rather than inferring them from incidental logs.  
**Consequences:** ForgeAgent must provide a clear operational history for debugging, governance, and compliance review. Event schemas must distinguish automated and human-originated decisions. Systems consuming execution history can rely on structured records rather than parsing free-form output.  
**Rejected alternatives:**  
- Using standard application logs as the only record: rejected because logs are not a sufficient audit contract.  
- Recording only failures and final success: rejected because the requirement covers every gate decision and state transition.  
- Inferring operator intent from resulting merge actions: rejected because explicit gate decisions are required artifacts.