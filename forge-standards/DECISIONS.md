# DECISIONS.md

## FullPlatform repository structure is fixed and documentation-led
**Status:** Accepted  
**Context:** The FullPlatform subsystem operates inside a repository with prescribed top-level directories and a documented source-of-truth model. TRDs and PRDs are explicitly stored under `forge-docs/`, standards under `forge-standards/`, Python backend code under `src/`, and the macOS shell under `Crafted/` with tests in `CraftedTests/` and `tests/`. This structure is part of the operating model for agents and implementers.  
**Decision:** Preserve the repository layout exactly as documented, and treat `forge-docs/` as the authoritative source of product and technical requirements before implementation changes are made. Place backend runtime code in `src/`, macOS application code in `Crafted/`, Swift tests in `CraftedTests/`, Python tests in `tests/`, and standards artifacts in `forge-standards/`.  
**Consequences:** Implementation may not relocate subsystem code arbitrarily, invent parallel standards directories, or bypass TRD/PRD review. Tooling, scripts, and agents must assume these paths are stable. Changes to FullPlatform must be evaluated against the documents in `forge-docs/` before code is modified.  
**Rejected alternatives:**  
- Use a feature-based or service-per-directory layout: rejected because it would diverge from the documented repository contract and break agent expectations.  
- Treat code as the primary source of truth and docs as advisory: rejected because TRDs are explicitly designated as the source of truth.  
- Merge backend and macOS shell code into one application directory: rejected because the repository separates Python backend and Swift shell responsibilities.

## Critical implementation files are protected change boundaries
**Status:** Accepted  
**Context:** Several files are identified as critical because they define core generation, orchestration, GitHub I/O, path security, and CI workflow behavior. Modifications to these files have system-wide effects and represent architectural boundaries.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as protected architectural boundaries. Require implementers to read and preserve their contracts before modifying any related FullPlatform behavior. Route new functionality through these boundaries rather than duplicating their responsibilities elsewhere.  
**Consequences:** New code must not reimplement path validation, GitHub write logic, CI generation, orchestration, or consensus behavior in parallel modules. Refactors affecting these files must preserve their central role and avoid hidden side channels. Risk and review depth are higher for changes touching these files.  
**Rejected alternatives:**  
- Freely distribute these responsibilities across new helper files: rejected because it weakens security and orchestration boundaries.  
- Duplicate GitHub, path, or CI logic in subsystem-specific modules: rejected because it would create inconsistent behavior and bypass the designated controls.  
- Treat critical files as informational only: rejected because the TRD explicitly marks them as required reading before modification.

## FullPlatform pipeline stages are mandatory and sequential
**Status:** Accepted  
**Context:** The build pipeline is defined as a staged workflow with explicit phases, including static validation, fix loops, test and CI execution, and an operator gate. The pipeline is part of the subsystem’s execution model, not an implementation detail.  
**Decision:** Implement and maintain FullPlatform work as a sequential staged pipeline that includes the documented validation, fix, test, CI, and gate phases. Do not remove, merge away, or skip required stages in normal operation.  
**Consequences:** Pipeline orchestration must expose distinct stages with stable semantics. Short-circuiting directly from generation to merge is not allowed. Error handling and progress reporting must align to stage boundaries. Subsystem features that interact with generation or delivery must fit into this staged model.  
**Rejected alternatives:**  
- Collapse the workflow into a single end-to-end task: rejected because it removes checkpointing and stage-specific recovery.  
- Make validation and CI optional by default: rejected because the pipeline definition requires them.  
- Allow arbitrary stage ordering per feature: rejected because it undermines deterministic orchestration and observability.

## Cyclomatic complexity per pipeline stage is capped at 15
**Status:** Accepted  
**Context:** The repository standards state that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is explicitly noted as having a strict complexity limit. This is a hard maintainability and control-flow constraint.  
**Decision:** Keep the implementation of each pipeline stage at cyclomatic complexity 15 or lower. Split logic into helpers, strategy objects, or composable functions when a stage approaches the limit.  
**Consequences:** Stage implementations must remain modular and auditable. Large conditional trees inside a single stage are disallowed. Refactoring is required when new behavior would push a stage above the limit. Static analysis and code review should enforce this limit as a design constraint, not merely a style preference.  
**Rejected alternatives:**  
- Permit exceptions for “core” orchestration code: rejected because the complexity cap is explicitly stated for every stage.  
- Enforce complexity only at file level: rejected because the requirement is stage-specific.  
- Accept temporary violations to ship faster: rejected because orchestration clarity and reliability are core constraints.

## All pipeline state transitions must be checkpointed
**Status:** Accepted  
**Context:** The pipeline requirements specify that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This supports recovery, auditability, and deterministic execution.  
**Decision:** Persist a checkpoint for every FullPlatform state transition, including the documented per-PR lifecycle states and any additional approved intermediate states. Require transitions to be recorded before advancing to the next stage.  
**Consequences:** Stateless orchestration is not allowed. Recovery logic must resume from checkpoints rather than infer progress heuristically. New states must include persistence semantics from the outset. Observability, debugging, and operator review depend on this data being complete and ordered.  
**Rejected alternatives:**  
- Checkpoint only failures or terminal states: rejected because the requirement covers every transition.  
- Keep transitions only in memory during a run: rejected because it prevents recovery and audit.  
- Infer state from Git history or CI status after the fact: rejected because external systems do not fully represent internal pipeline progress.

## Gate decisions require explicit operator approval before merge
**Status:** Accepted  
**Context:** The build pipeline defines a gate stage in which an operator approves or corrects before merge. Gate decisions are also required to be checkpointed. This makes human approval a formal control point.  
**Decision:** Require explicit operator approval or correction at the gate stage before merge actions occur. Record the gate decision as a checkpointed event and do not auto-merge around this control.  
**Consequences:** FullPlatform cannot be fully autonomous through merge. UX, API, and orchestration flows must support pending-review states and operator intervention. Merge automation must remain blocked until the gate decision is recorded.  
**Rejected alternatives:**  
- Automatically merge after tests and CI pass: rejected because the documented pipeline requires operator approval.  
- Treat operator review as advisory and non-blocking: rejected because the gate is a required stage.  
- Encode approval implicitly from CI status: rejected because CI success is not equivalent to operator approval.

## CI targets must distinguish general and Swift-specific workflows
**Status:** Accepted  
**Context:** The build pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. The repository contains both Python backend and Swift/SwiftUI application code, requiring platform-specific CI handling.  
**Decision:** Maintain separate CI workflow paths for general/backend validation and Swift/macOS validation. Run the general crafted workflow on `ubuntu-latest` and use a distinct macOS-targeted workflow for Swift-related validation.  
**Consequences:** CI generation and execution must preserve platform distinctions instead of forcing one workflow to serve all stacks. Swift changes must be validated in a macOS-capable context. Backend-only checks should remain runnable in the general workflow without unnecessary macOS coupling.  
**Rejected alternatives:**  
- Run all CI only on macOS: rejected because it is more expensive and unnecessary for the general/backend path.  
- Run all CI only on Ubuntu: rejected because Swift/macOS validation requires platform-specific support.  
- Hide both stacks behind one monolithic workflow file: rejected because the TRD explicitly names separate workflows and responsibilities.

## Static validation must include parse, lint, import, and bounded fix-loop behavior
**Status:** Accepted  
**Context:** The pipeline definition includes a static validation sequence of `ast.parse → ruff → import check` and a fix loop with `pytest` for up to 20 attempts using failure-type-aware strategy. These behaviors define the minimum validation contract for generated or modified code.  
**Decision:** Enforce static validation in the documented order and implement a bounded fix loop capped at 20 pytest-driven attempts with failure-type-aware remediation. Do not allow unbounded retry behavior.  
**Consequences:** Validation logic must be ordered and deterministic. Retry orchestration must classify failures and adapt strategy rather than blindly rerunning tests. Infinite or open-ended self-healing loops are prohibited. Tooling and metrics should make attempt counts visible.  
**Rejected alternatives:**  
- Use a generic “run all checks” step without ordered substeps: rejected because the sequence is explicitly defined.  
- Retry until success with no hard limit: rejected because the fix loop is capped at 20 attempts.  
- Apply identical remediation on every failure: rejected because the strategy must be failure-type-aware.

## Path writes must traverse the central security boundary
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary and every write path must pass through it. FullPlatform necessarily writes generated artifacts, workflow files, and other repository changes, making write-path control critical.  
**Decision:** Route every filesystem write performed by FullPlatform through the central path security mechanism in `src/path_security.py`. Do not permit direct write operations that bypass path validation.  
**Consequences:** Convenience writes, ad hoc file output, and subsystem-local path validation are not acceptable substitutes. Security review can focus on one boundary. Tests must verify that write paths are mediated through the approved mechanism.  
**Rejected alternatives:**  
- Validate paths independently in each module: rejected because it creates inconsistent security behavior.  
- Trust internal callers and write directly to disk: rejected because it bypasses the designated security boundary.  
- Restrict only external input paths while allowing internal direct writes: rejected because all write paths are required to pass through the boundary.

## GitHub interactions must be centralized in the GitHub tools boundary
**Status:** Accepted  
**Context:** `src/github_tools.py` is designated as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. This defines a central integration boundary for repository operations.  
**Decision:** Centralize all FullPlatform GitHub API and repository interaction logic in `src/github_tools.py` or its approved abstractions. Preserve path validation, rate limiting, and SHA-aware update semantics as mandatory parts of GitHub operations.  
**Consequences:** Direct ad hoc GitHub API usage from unrelated modules is prohibited. Subsystem features that create branches, commits, PRs, or file updates must use the central boundary. Concurrency and update correctness must respect SHA-based protocols.  
**Rejected alternatives:**  
- Allow each feature module to call GitHub APIs directly: rejected because it would fragment safety and rate-limiting logic.  
- Treat SHA handling as optional for simple updates: rejected because the protocol is part of the documented GitHub I/O boundary.  
- Split rate limiting into a separate unconstrained utility layer: rejected because the designated boundary already owns the end-to-end behavior.

## The RootView onboarding decision tree is the required macOS shell entry flow
**Status:** Accepted  
**Context:** TRD-1 defines a RootView decision tree in which `OnboardingState != .complete` routes to `OnboardingContainerView` and then to specific onboarding screens such as welcome, API keys, and GitHub auth. This governs the entry behavior of the macOS shell.  
**Decision:** Implement the macOS FullPlatform shell so that `RootView` follows the documented onboarding-state decision tree. Gate access to the main application experience behind completion of onboarding, and route incomplete onboarding states to their prescribed onboarding views.  
**Consequences:** The application may not bypass onboarding when required state is incomplete. Root navigation must be state-driven and deterministic. New startup experiences must integrate with, not replace, the onboarding tree unless the TRD is revised.  
**Rejected alternatives:**  
- Present the main app immediately and surface onboarding as optional modals: rejected because the root decision tree explicitly gates on onboarding completion.  
- Use ad hoc startup routing based on view-local logic: rejected because root navigation is centrally defined.  
- Flatten onboarding into a single screen regardless of state: rejected because the TRD specifies distinct state-based branches.