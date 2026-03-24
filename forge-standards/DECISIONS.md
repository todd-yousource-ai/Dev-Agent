# DECISIONS.md

## [Keep ForgeAgent implementation inside the existing monorepo layout]
**Status:** Accepted

**Context:** The repository structure is already defined as the source of truth. Documentation lives in `forge-docs/`, standards in `forge-standards/`, Python backend code in `src/`, the macOS shell in `Crafted/`, Swift tests in `CraftedTests/`, and Python tests in `tests/`. The ForgeAgent subsystem must fit this structure rather than introducing a parallel layout.

**Decision:** Implement ForgeAgent within the existing repository layout. Place backend agent logic in `src/`, tests in `tests/`, and any standards or architecture updates in `forge-standards/`. Treat `forge-docs/` as read-first source material, not as an implementation location.

**Consequences:** New ForgeAgent code must not create a separate top-level agent repository or alternate source tree. Cross-cutting changes must preserve the documented monorepo boundaries. Contributors must consult TRDs and PRDs in `forge-docs/` before modifying implementation.

**Rejected alternatives:**  
- Creating a separate `agents/` top-level runtime directory: rejected because it conflicts with the documented repository layout and fragments ownership.  
- Storing implementation code in `forge-docs/`: rejected because documentation is the source of truth, not executable runtime code.  
- Introducing a new service repository for ForgeAgent: rejected because current standards assume an integrated backend in `src/`.

## [Treat specific files as mandatory integration boundaries]
**Status:** Accepted

**Context:** Several files are explicitly identified as critical and must be read before modification. These files define core loops, orchestration, GitHub I/O, path security, and CI workflow generation.

**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as mandatory integration boundaries for ForgeAgent. Any ForgeAgent behavior affecting generation, orchestration, repository writes, GitHub operations, or CI generation must route through these files or their established interfaces.

**Consequences:** Implementers cannot bypass these files with parallel utility layers that duplicate security, orchestration, or GitHub behavior. Changes in these areas require heightened review because they affect all generated PRs and repository safety.

**Rejected alternatives:**  
- Adding separate ForgeAgent-specific GitHub and path utilities: rejected because it would duplicate security and protocol logic.  
- Writing directly to the filesystem without `src/path_security.py`: rejected because it violates the repository’s write-path security boundary.  
- Creating an alternative orchestration loop outside `src/build_director.py`: rejected because it would split pipeline control and weaken complexity enforcement.

## [Preserve the staged build pipeline as the execution model]
**Status:** Accepted

**Context:** The build pipeline is defined as a staged system with explicit validation, fix-loop behavior, test and CI execution, and operator gating. This pipeline is central to how the agent produces changes safely.

**Decision:** Implement ForgeAgent workflows as explicit pipeline stages that conform to the documented build pipeline. Preserve validation, fix-loop, test, CI, and operator gate semantics rather than collapsing them into a single opaque execution pass.

**Consequences:** Agent execution must remain inspectable by stage. Stage-specific logic must be isolated enough to support retries, reporting, and checkpointing. Implementations must not replace the pipeline with one-shot generation followed by best-effort validation.

**Rejected alternatives:**  
- A single-pass “generate then merge” workflow: rejected because it removes structured validation and recovery behavior.  
- Fully autonomous merge without staged gates: rejected because the documented pipeline requires operator approval before merge.  
- Ad hoc stage ordering per task: rejected because consistency of execution flow is required for debugging and control.

## [Enforce cyclomatic complexity limit of 15 per stage]
**Status:** Accepted

**Context:** The build pipeline explicitly states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is specifically called out as having a strict complexity limit. This is a design constraint, not a style preference.

**Decision:** Keep each ForgeAgent pipeline stage at cyclomatic complexity 15 or below. Refactor into helper functions or subcomponents when stage logic approaches the limit.

**Consequences:** Large conditional orchestration functions are not permitted. Stage logic must be decomposed early to preserve readability, testability, and maintainability. Reviews must reject implementations that exceed the limit even if functionally correct.

**Rejected alternatives:**  
- Allowing higher complexity in orchestration code because it is “central”: rejected because the limit is explicitly strict for the pipeline.  
- Enforcing complexity only at module level, not stage level: rejected because the requirement is stage-specific.  
- Deferring refactoring until after feature delivery: rejected because complexity growth in orchestration is costly and destabilizing.

## [Checkpoint every state transition, including per-PR progression]
**Status:** Accepted

**Context:** The system requires that every state transition be checkpointed, including per-PR states such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This ensures resumability, observability, and auditable execution.

**Decision:** Persist a checkpoint on every ForgeAgent state transition, including pipeline-stage transitions and per-PR lifecycle transitions. Treat checkpointing as mandatory system behavior, not optional telemetry.

**Consequences:** State mutation logic must be paired with durable checkpoint writes. Recovery and resume flows must read from checkpoints rather than infer state from partial side effects. Implementations must not batch multiple transitions into a single final write if intermediate states would be lost.

**Rejected alternatives:**  
- Checkpointing only major milestones: rejected because the requirement covers every transition.  
- Reconstructing state from Git history or CI status after failure: rejected because reconstruction is incomplete and non-deterministic.  
- In-memory-only state progression during runs: rejected because failures would make recovery impossible.

## [Record every gate decision for auditability]
**Status:** Accepted

**Context:** The pipeline includes an operator gate before merge, and every gate decision must be logged. Gate records are necessary for auditability and for understanding why changes were approved, corrected, or blocked.

**Decision:** Log every ForgeAgent gate decision with enough structured context to reconstruct the outcome, including the gate type, decision taken, and associated execution context.

**Consequences:** Approval, rejection, and correction events must be durable and queryable. Implementations cannot treat human gate actions as ephemeral UI events only. Merge logic must depend on recorded gate outcomes rather than transient session state.

**Rejected alternatives:**  
- Logging only rejected decisions: rejected because the requirement applies to every gate decision.  
- Capturing gate decisions only in UI state: rejected because UI state is not a durable audit record.  
- Inferring approvals from subsequent merges: rejected because inference loses timing and rationale context.

## [Use GitHub operations only through the established SHA, validation, and rate-limit protocol]
**Status:** Accepted

**Context:** `src/github_tools.py` is the defined boundary for all GitHub I/O and is responsible for path validation, rate limiting, and SHA protocol handling. ForgeAgent must not weaken these guarantees.

**Decision:** Route all ForgeAgent GitHub reads and writes through `src/github_tools.py` and preserve its path validation, rate limiting, and SHA-based update protocol.

**Consequences:** Direct API calls that bypass repository safeguards are disallowed. File updates must respect SHA preconditions to avoid clobbering concurrent changes. Repository interactions must remain consistent with existing retry and validation behavior.

**Rejected alternatives:**  
- Calling the GitHub API directly from new ForgeAgent modules: rejected because it bypasses validated repository safety controls.  
- Writing files without SHA checks for simplicity: rejected because it risks overwriting concurrent updates.  
- Disabling rate limiting for agent throughput: rejected because it would create reliability and abuse-control issues.

## [Require all write paths to pass through the path security boundary]
**Status:** Accepted

**Context:** `src/path_security.py` is identified as the security boundary for filesystem writes, and every write path must pass through it. ForgeAgent will create or modify files and therefore operates directly in a sensitive area.

**Decision:** Validate every ForgeAgent filesystem write through `src/path_security.py` before the write occurs. Do not introduce alternate path validation codepaths for convenience or performance.

**Consequences:** File creation and modification code must be structured to centralize path validation. Unsafe direct writes, path concatenation shortcuts, and bypasses for temporary files inside the repository are prohibited unless they also traverse the same security boundary.

**Rejected alternatives:**  
- Inline per-call path checks in individual modules: rejected because duplicated checks drift and are easy to miss.  
- Trusting caller-provided relative paths: rejected because caller trust is not a security control.  
- Validating only externally supplied paths: rejected because internal composition bugs can also create unsafe writes.

## [Preserve the documented CI split between ubuntu-latest and macOS workflows]
**Status:** Accepted

**Context:** The README specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. The repository contains both Python backend and Swift/macOS application concerns, so CI must reflect platform-specific execution.

**Decision:** Keep ForgeAgent-generated or ForgeAgent-managed CI aligned to the documented split: use Ubuntu-based workflows for general backend validation and a dedicated macOS workflow for Swift-related validation.

**Consequences:** CI generation and updates must not collapse all checks onto a single runner class. Swift and macOS-specific validation must remain on macOS-capable infrastructure. Backend-only checks should not consume macOS runners unnecessarily.

**Rejected alternatives:**  
- Running all CI on macOS for consistency: rejected because it is inefficient and contradicts the documented Ubuntu workflow for general CI.  
- Running all CI on Ubuntu only: rejected because Swift/macOS validation requires macOS.  
- Selecting runners dynamically without preserving the two-workflow model: rejected because it obscures the documented CI contract.

## [Respect operator gate before merge as a hard stop]
**Status:** Accepted

**Context:** The pipeline defines Stage 6 as a gate where the operator approves or corrects before merge. This means merge is not a purely autonomous agent action.

**Decision:** Require explicit operator approval before ForgeAgent merges changes. Treat the gate as a hard control point, not as advisory feedback.

**Consequences:** Merge automation must remain blocked until gate approval is recorded. “Auto-merge on green” behavior is not allowed unless it occurs after the operator gate has been satisfied. Correction paths must return execution to the pipeline rather than forcing merge.

**Rejected alternatives:**  
- Fully autonomous merge after tests and CI pass: rejected because it skips the required operator gate.  
- Optional operator review only for risky changes: rejected because the gate is a standard stage, not a conditional one.  
- Silent timeout-to-approve behavior: rejected because it is not explicit operator approval.

## [Use failure-aware retry logic in the fix loop, capped at 20 attempts]
**Status:** Accepted

**Context:** The build pipeline defines a fix loop driven by pytest with up to 20 attempts and a failure-type-aware strategy. The repository also includes `FAILURE_TAXONOMY.md`, indicating that failures should be categorized and handled intentionally.

**Decision:** Implement ForgeAgent retry behavior as a bounded fix loop with a maximum of 20 attempts and strategy selection informed by failure type. Use the failure taxonomy to guide remediation behavior rather than retrying blindly.

**Consequences:** Infinite or open-ended retries are prohibited. Retry logic must classify failures and adapt the response, improving determinism and reducing wasted runs. Terminal failure reporting must include attempt exhaustion and failure categorization.

**Rejected alternatives:**  
- Unlimited retries until success: rejected because it is operationally unsafe and contradicts the documented cap.  
- A fixed retry strategy regardless of failure type: rejected because the pipeline requires failure-type-aware behavior.  
- No automated fix loop after test failures: rejected because iterative repair is part of the documented execution model.

## [Keep ForgeAgent backend concerns separate from macOS root-view navigation logic]
**Status:** Accepted

**Context:** TRD-1 defines a SwiftUI root view decision tree for onboarding and app-shell navigation. ForgeAgent is a backend subsystem inside the broader product and should not entangle agent runtime behavior with UI navigation state.

**Decision:** Keep ForgeAgent implementation focused on backend runtime concerns and integrate with the macOS shell through clear interfaces rather than embedding agent decision logic into SwiftUI root-view navigation structures.

**Consequences:** Backend orchestration state and UI onboarding state must remain distinct. UI code may observe or present agent state, but it must not become the primary execution engine for ForgeAgent workflows. Interface contracts between `src/` and `Crafted/` should remain explicit.

**Rejected alternatives:**  
- Driving ForgeAgent execution directly from SwiftUI view state transitions: rejected because view lifecycle is not a reliable backend orchestration mechanism.  
- Embedding pipeline state machines in the macOS shell: rejected because it couples platform UI to backend runtime behavior.  
- Treating the macOS app as the only control plane for agent execution: rejected because the backend must remain independently structured and testable.