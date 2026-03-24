# DECISIONS.md

## Repository documentation is the source of truth
**Status:** Accepted  
**Context:** The repository structure explicitly defines `forge-docs/` as the location where all TRDs and PRDs live and states they must be read before building. The ForgeAgent subsystem operates from requirements that are document-driven, and implementation must remain aligned with those artifacts.  
**Decision:** Treat documents in `forge-docs/` as the authoritative source of product and technical requirements before implementing or modifying ForgeAgent behavior.  
**Consequences:** Implementation decisions must trace back to TRDs/PRDs. Code changes that conflict with documented requirements are invalid unless the documents are updated first. Agent workflows should prefer document-derived constraints over ad hoc code conventions when conflicts arise.  
**Rejected alternatives:**  
- Treating code as the primary source of truth was rejected because the repository explicitly places requirements in `forge-docs/` and expects builders to read them first.  
- Allowing undocumented behavior to evolve in implementation was rejected because it creates divergence between the agent and its governing specifications.

## ForgeAgent must preserve the defined repository boundary
**Status:** Accepted  
**Context:** The repository layout assigns clear responsibilities to top-level directories: `forge-docs/` for requirements, `forge-standards/` for architecture and conventions, `src/` for Python backend implementation, `Crafted/` and `CraftedTests/` for Swift app code, and `tests/` for Python tests. ForgeAgent must operate within this structure predictably.  
**Decision:** Enforce the existing repository layout and place ForgeAgent implementation work only in the designated locations for each concern.  
**Consequences:** Backend agent logic belongs in `src/`, Python validation in `tests/`, and standards updates in `forge-standards/`. The subsystem must not create parallel structures for equivalent concerns. Tooling and prompts should reference these canonical locations.  
**Rejected alternatives:**  
- Creating a dedicated top-level `agents/` tree was rejected because it duplicates responsibilities already assigned to `src/` and `forge-standards/`.  
- Allowing free-form file placement was rejected because it weakens traceability and increases maintenance cost.

## Critical files require heightened change discipline
**Status:** Accepted  
**Context:** Several files are identified as critical before modification: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. These files define core loop behavior, orchestration, GitHub I/O, security boundaries, and CI generation.  
**Decision:** Treat the enumerated critical files as protected architectural surfaces and require changes to them to preserve their documented responsibilities exactly.  
**Consequences:** Modifications in these files must be minimal, intentional, and validated against subsystem-wide effects. Refactors that move or dilute these responsibilities are constrained. New functionality should prefer extension around these files rather than responsibility drift into unrelated modules.  
**Rejected alternatives:**  
- Treating all source files as equally mutable was rejected because the repository explicitly identifies these files as system-critical.  
- Redistributing the responsibilities of critical files across many modules was rejected because it obscures review boundaries and weakens operational guarantees.

## Path validation is a mandatory security boundary for all writes
**Status:** Accepted  
**Context:** `src/path_security.py` is declared the security boundary, and every write path must pass through it. ForgeAgent performs repository mutations and therefore must not bypass path enforcement.  
**Decision:** Route every filesystem write performed by ForgeAgent through the path security layer without exception.  
**Consequences:** Any write helper, generation stage, GitHub integration, or repair loop that creates or modifies files must depend on validated paths. Direct writes that bypass `src/path_security.py` are prohibited. This constrains utility design and test setup to model the same enforcement path.  
**Rejected alternatives:**  
- Allowing trusted internal modules to write directly was rejected because it creates bypasses in the primary security boundary.  
- Validating only user-supplied paths was rejected because generated and transformed paths can also become unsafe.

## GitHub interactions must be centralized in github_tools
**Status:** Accepted  
**Context:** `src/github_tools.py` is defined as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. ForgeAgent relies on GitHub operations during PR construction and repository mutation.  
**Decision:** Centralize all GitHub API and repository I/O for ForgeAgent in `src/github_tools.py` and require consumers to use that interface rather than ad hoc clients.  
**Consequences:** Rate limiting, SHA handling, and validation remain consistent across the subsystem. New GitHub features must extend the shared integration surface instead of instantiating alternate clients. Testing can mock a single boundary.  
**Rejected alternatives:**  
- Letting each workflow stage use its own GitHub client was rejected because it would duplicate protocol logic and increase inconsistency.  
- Performing raw HTTP calls from orchestration code was rejected because it bypasses required validation and rate-limit controls.

## The core generation loop remains centralized in consensus.py
**Status:** Accepted  
**Context:** `src/consensus.py` is identified as the core generation loop, and changes there affect every PR the agent builds. ForgeAgent’s behavior depends on a stable central mechanism for generation and convergence.  
**Decision:** Keep the primary generation and consensus loop centralized in `src/consensus.py` and treat it as the single control point for PR-wide generation behavior.  
**Consequences:** Cross-cutting generation policy belongs in this module, not scattered among stage-specific helpers. Feature work that changes how the agent generates code must integrate through the consensus layer. Regressions here are considered subsystem-wide risks.  
**Rejected alternatives:**  
- Splitting generation logic across independent stage modules was rejected because it would fragment policy and make PR behavior harder to reason about.  
- Embedding generation decisions directly in UI, CI, or GitHub adapters was rejected because those layers are not the proper control point.

## Pipeline orchestration must remain in build_director with strict complexity limits
**Status:** Accepted  
**Context:** `src/build_director.py` owns pipeline orchestration, and the repository states that every stage has a maximum cyclomatic complexity of 15, with the complexity 15 limit strictly enforced for this file. ForgeAgent coordinates multi-stage work and must do so within maintainable control-flow bounds.  
**Decision:** Implement and preserve pipeline orchestration in `src/build_director.py`, and keep every stage implementation at cyclomatic complexity 15 or below.  
**Consequences:** Complex branching must be decomposed into helpers or state-driven handlers rather than accumulated in monolithic methods. Review of orchestration changes must include complexity checks. The subsystem is constrained toward explicit, composable stage logic.  
**Rejected alternatives:**  
- Allowing orchestration complexity to grow beyond 15 for convenience was rejected because the repository explicitly forbids it.  
- Moving orchestration into a large implicit workflow engine was rejected because it would reduce transparency and complicate checkpoint semantics.

## The build pipeline stages are fixed and must be implemented explicitly
**Status:** Accepted  
**Context:** The build pipeline is defined in the README with explicit stages, including syntax and lint checks, import checks, a failure-type-aware fix loop with up to 20 pytest attempts, CI generation, and an operator gate before merge. ForgeAgent is the subsystem responsible for carrying out this flow.  
**Decision:** Implement ForgeAgent workflows as explicit ordered pipeline stages matching the documented build pipeline, including the fix loop, CI stage, and final operator gate.  
**Consequences:** Stage boundaries must remain visible in code and state. The agent may optimize within a stage but must not collapse or skip documented stages. Retry logic is constrained to the documented fix loop semantics, including the 20-attempt maximum for pytest repair.  
**Rejected alternatives:**  
- Using an unconstrained agentic loop without explicit stages was rejected because it conflicts with the documented pipeline contract.  
- Skipping intermediate verification stages to reduce latency was rejected because correctness and auditability take precedence.

## Failure repair must be failure-type-aware and capped
**Status:** Accepted  
**Context:** The build pipeline specifies a fix loop that is failure-type-aware and runs pytest with up to 20 attempts. The repository also includes `FAILURE_TAXONOMY.md`, indicating standardized failure categorization.  
**Decision:** Drive ForgeAgent repair behavior using explicit failure categorization and cap automated pytest repair attempts at 20.  
**Consequences:** Repair logic must classify failures before selecting a remediation strategy. Infinite or open-ended retry loops are prohibited. Integrations should align with the repository’s failure taxonomy rather than inventing incompatible ad hoc categories.  
**Rejected alternatives:**  
- Retrying blindly until success was rejected because it wastes resources and obscures root cause.  
- Using a single generic fix strategy for all failures was rejected because the documented pipeline requires failure-type-aware handling.

## State transitions must be checkpointed exhaustively
**Status:** Accepted  
**Context:** The README states that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. Gate decisions are also expected to be persisted.  
**Decision:** Persist a checkpoint for every ForgeAgent state transition and for every gate decision, including the documented per-PR lifecycle states.  
**Consequences:** The subsystem must expose durable state progression suitable for recovery, audit, and operator inspection. Transitions cannot be implicit or in-memory only. Workflow code must emit checkpoints as part of state mutation rather than as best-effort logging.  
**Rejected alternatives:**  
- Checkpointing only major milestones was rejected because the requirement is to checkpoint every transition.  
- Relying on logs instead of structured checkpoints was rejected because logs are insufficient for deterministic recovery and lifecycle tracking.

## Operator approval is mandatory before merge
**Status:** Accepted  
**Context:** The build pipeline includes a final gate where the operator approves or corrects before merge. ForgeAgent can automate generation and validation, but merge authority remains gated by a human decision point.  
**Decision:** Require an explicit operator approval or correction step before any ForgeAgent-produced change is considered merge-ready.  
**Consequences:** Full end-to-end autonomous merge is out of scope for this subsystem. Workflow completion must distinguish between “technically ready” and “approved for merge.” UI and backend state models must support pending-approval and correction flows.  
**Rejected alternatives:**  
- Automatically merging after CI success was rejected because it violates the documented operator gate.  
- Making operator review optional was rejected because the gate is part of the required pipeline.

## CI workflow generation must target the documented runners
**Status:** Accepted  
**Context:** The pipeline documentation specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is the generator for these workflows. ForgeAgent must emit CI consistent with platform responsibilities.  
**Decision:** Generate CI workflows through `src/ci_workflow.py` using `crafted-ci.yml` on `ubuntu-latest` for general pipeline execution and `crafted-ci-macos.yml` for Swift-related execution.  
**Consequences:** CI generation logic must preserve this split between Linux and macOS responsibilities. ForgeAgent must not emit a single undifferentiated workflow that ignores Swift platform needs. Changes to runner targeting require an architectural decision, not a local implementation shortcut.  
**Rejected alternatives:**  
- Running all CI exclusively on Ubuntu was rejected because Swift/macOS work requires a macOS workflow.  
- Running everything exclusively on macOS was rejected because it is unnecessary for the full pipeline and would increase cost and queue time.

## ForgeAgent must respect the Swift application shell boundary
**Status:** Accepted  
**Context:** The repository contains a separate Swift/SwiftUI application shell in `Crafted/` with tests in `CraftedTests/`, and TRD-1 defines a specific Root View decision tree for onboarding and application flow. ForgeAgent may interact with this codebase but must not violate the app shell’s architectural contract.  
**Decision:** Treat the Swift application shell and its documented Root View decision tree as a separate bounded architecture that ForgeAgent may modify only in ways consistent with the documented state-driven navigation model.  
**Consequences:** Agent-generated Swift changes must preserve onboarding-state-driven root navigation and should not introduce alternate top-level flow control that conflicts with the specified tree. Backend concerns must not leak into the Swift shell structure arbitrarily.  
**Rejected alternatives:**  
- Allowing ForgeAgent to redesign root navigation opportunistically was rejected because TRD-1 already specifies the root decision model.  
- Treating the Swift app as just another file tree without architectural constraints was rejected because it has explicit UI flow requirements.