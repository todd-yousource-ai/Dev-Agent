## Repository Source of Truth and Layout
**Status:** Accepted

**Context:** The FullPlatform subsystem spans Python backend orchestration, Swift/macOS shell code, tests, standards, and requirements documentation. Multiple TRDs define behavior, and implementation must remain aligned with those documents and the established repository structure.

**Decision:** Treat `forge-docs/` as the source of truth for product and technical requirements, and preserve the repository layout exactly as documented. Implement FullPlatform code only within the designated areas: `src/` for Python backend runtime, `Crafted/` for the Swift/SwiftUI application shell, `CraftedTests/` for XCTest coverage, `tests/` for pytest coverage, and `forge-standards/` for architectural constraints and generated standards artifacts.

**Consequences:**  
- No implementation may redefine requirements outside the TRDs and PRDs in `forge-docs/`.  
- Cross-cutting FullPlatform changes must be reflected in the proper layer rather than added ad hoc to miscellaneous directories.  
- Tooling, automation, and contributor workflows can rely on a stable filesystem contract.  
- Documentation and implementation reviews must validate conformance against both TRDs and the published repository layout.

**Rejected alternatives:**  
- **Flat repository layout with mixed concerns:** Rejected because it obscures boundaries between standards, backend, app shell, and tests.  
- **Using code as the sole source of truth:** Rejected because requirements are explicitly maintained in `forge-docs/` and must be read before building.  
- **Subsystem-specific shadow documentation outside `forge-docs/`:** Rejected because it creates divergent specifications and weakens traceability.

## Critical File Boundaries Are Mandatory
**Status:** Accepted

**Context:** Several files are identified as critical because they enforce system-wide behavior and security boundaries. Changes in these files have disproportionate impact on FullPlatform correctness, safety, and operability.

**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as protected architectural boundaries. Route all relevant FullPlatform behavior through these files rather than duplicating their responsibilities elsewhere.

**Consequences:**  
- Generation-loop changes must occur through `src/consensus.py`.  
- Pipeline orchestration changes must occur through `src/build_director.py`.  
- All GitHub I/O must be centralized in `src/github_tools.py`.  
- Every write path must pass through `src/path_security.py`.  
- CI workflow generation must be owned by `src/ci_workflow.py`.  
- Review scrutiny and test requirements are higher for these files because regressions affect the entire platform.

**Rejected alternatives:**  
- **Re-implementing critical behaviors in feature modules:** Rejected because it fragments control logic and bypasses required safeguards.  
- **Direct filesystem writes from arbitrary modules:** Rejected because it breaks the security boundary enforced by `src/path_security.py`.  
- **Direct GitHub API usage outside `src/github_tools.py`:** Rejected because it undermines path validation, rate limiting, and SHA protocol consistency.

## Build Pipeline Stages Are Fixed and Explicit
**Status:** Accepted

**Context:** The FullPlatform subsystem depends on a staged build pipeline with clearly named phases, validation steps, and control points. Predictable stage boundaries are necessary for checkpointing, debugging, and safe recovery.

**Decision:** Implement and operate the FullPlatform build flow as an explicit staged pipeline, including syntax and static validation, fix-loop behavior, test and CI execution, and operator gate before merge. Preserve named stage semantics rather than collapsing them into opaque orchestration.

**Consequences:**  
- Each stage must have a clear entry, exit, and failure mode.  
- Pipeline observability, retries, and audits can attach to stable stage names.  
- Future features must integrate into an existing stage boundary or justify a new explicit stage rather than embedding hidden side effects.  
- Merge readiness is not inferred solely from local execution; it must pass through the defined gate.

**Rejected alternatives:**  
- **Single-pass monolithic pipeline execution:** Rejected because it reduces debuggability and weakens failure isolation.  
- **Implicit stage transitions inside helper functions:** Rejected because checkpointing and audit requirements need explicit transitions.  
- **Skipping operator gate for fully automated merges:** Rejected because the documented process requires operator approval or correction before merge.

## Cyclomatic Complexity Limit of 15 Is an Architectural Constraint
**Status:** Accepted

**Context:** The build pipeline documentation explicitly caps cyclomatic complexity at 15 for every stage. This is not a style preference; it is a maintainability and safety constraint for orchestration code.

**Decision:** Enforce a maximum cyclomatic complexity of 15 for every FullPlatform pipeline stage and preserve decomposition when adding features. Refactor rather than extending a stage beyond the limit.

**Consequences:**  
- New logic must be extracted into helpers, strategy objects, or subordinate components before stage complexity exceeds 15.  
- Reviews must reject implementations that satisfy behavior but violate this complexity ceiling.  
- Pipeline code remains analyzable and less error-prone under failure-heavy control flow.  
- The subsystem favors composition over deeply branched stage logic.

**Rejected alternatives:**  
- **Allowing higher complexity in orchestrators because they are “control-heavy”:** Rejected because the constraint explicitly applies to every stage.  
- **Treating complexity as advisory only:** Rejected because architectural decisions must constrain implementation, not merely suggest preferences.  
- **Moving complex logic into undocumented closures or inline lambdas to evade metrics:** Rejected because it preserves actual complexity while reducing transparency.

## Every State Transition Must Be Checkpointed
**Status:** Accepted

**Context:** FullPlatform workflows span multiple long-running and failure-prone transitions, especially around pull request processing. The README specifies that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`.

**Decision:** Persist a checkpoint on every FullPlatform state transition, including all per-PR lifecycle transitions and gate decisions. Do not rely on in-memory progress tracking for recoverability-critical workflow state.

**Consequences:**  
- Recovery after crash, restart, or partial failure must resume from the last durable transition.  
- Audit trails can reconstruct how a PR advanced through the system.  
- State model changes must include explicit checkpoint schema and migration considerations.  
- Hidden transitional states are discouraged unless they are also checkpointed and observable.

**Rejected alternatives:**  
- **Checkpointing only major milestones:** Rejected because the requirement is every state transition, not a subset.  
- **In-memory state machines with periodic snapshots:** Rejected because they risk losing exact progression and gate history.  
- **Logging transitions without durable structured checkpoints:** Rejected because logs are insufficient as authoritative resumable state.

## Gate Decisions Must Be Recorded and Human Approval Is Required Before Merge
**Status:** Accepted

**Context:** The documented pipeline includes a gate stage where the operator approves or corrects before merge, and every gate decision is recorded. This is a governance mechanism, not an optional UX detail.

**Decision:** Require an explicit operator decision before merge and record each gate decision as durable workflow state. Prevent merge finalization without a captured approval or correction outcome.

**Consequences:**  
- FullPlatform cannot implement unattended direct-to-merge behavior for governed flows.  
- Auditability of who approved, corrected, or blocked a change becomes a first-class requirement.  
- UI and backend APIs must expose gate state clearly enough for operators to act on it.  
- Automated recommendations may inform the gate but cannot replace the recorded human decision.

**Rejected alternatives:**  
- **Auto-merge after CI passes:** Rejected because the process explicitly requires operator approval or correction before merge.  
- **Transient approval state stored only in UI session memory:** Rejected because gate decisions must be recorded.  
- **Implicit approval by inactivity or timeout:** Rejected because approval must be explicit and durable.

## Failure Recovery Uses a Bounded, Failure-Type-Aware Fix Loop
**Status:** Accepted

**Context:** The build pipeline includes a fix loop that runs pytest for up to 20 attempts and applies failure-type-aware strategy. This defines both the retry budget and the recovery approach for iterative correction.

**Decision:** Implement FullPlatform test remediation as a bounded fix loop with a maximum of 20 attempts, and choose corrective strategy based on failure type rather than a uniform retry action.

**Consequences:**  
- Infinite or open-ended self-healing loops are prohibited.  
- Failure classification becomes part of orchestration design, not an afterthought.  
- Test remediation behavior must remain deterministic enough to audit and tune.  
- The subsystem must surface exhaustion of the retry budget as a distinct terminal condition.

**Rejected alternatives:**  
- **Unlimited retry until green:** Rejected because it can livelock and contradicts the explicit 20-attempt cap.  
- **Single generic retry strategy for all failures:** Rejected because the process requires failure-type-aware handling.  
- **Immediate hard fail after first test failure:** Rejected because the documented pipeline includes an intentional iterative fix loop.

## CI Workflow Targets Are Platform-Specific and Must Remain Separate
**Status:** Accepted

**Context:** The repository uses `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. FullPlatform spans both Python and Swift/macOS concerns, so CI must preserve platform-appropriate execution environments.

**Decision:** Maintain separate CI workflow definitions and execution targets for Linux-oriented backend validation and macOS-specific Swift validation. Do not collapse all validation into a single runner class or single workflow file.

**Consequences:**  
- Python/backend checks can remain efficient on Ubuntu runners.  
- Swift and macOS shell validation stays on macOS runners where the toolchain is valid.  
- CI generation and maintenance must account for divergent platform capabilities and costs.  
- Cross-platform changes must be tested in both workflows when applicable.

**Rejected alternatives:**  
- **Running all validation only on macOS:** Rejected because it increases cost and latency for backend checks without technical necessity.  
- **Running all validation only on Ubuntu:** Rejected because Swift/macOS application-shell validation requires macOS-capable runners.  
- **Single workflow with conditional branching for all platforms:** Rejected because separate workflows provide clearer ownership, simpler reasoning, and better alignment with documented files.

## All GitHub I/O Must Use Centralized Protocol Handling
**Status:** Accepted

**Context:** `src/github_tools.py` is identified as the entry point for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. FullPlatform must interact with GitHub safely and consistently.

**Decision:** Route all FullPlatform GitHub reads and writes through `src/github_tools.py`, and enforce its validation, rate-limiting, and SHA-handling rules uniformly.

**Consequences:**  
- GitHub operations gain consistent safety checks and concurrency semantics.  
- Rate-limit handling can be improved centrally without sweeping changes across features.  
- SHA protocol expectations remain uniform, reducing race and stale-write errors.  
- Feature code must depend on abstractions from `src/github_tools.py` instead of raw API clients.

**Rejected alternatives:**  
- **Direct Octokit/PyGitHub calls in feature code:** Rejected because they bypass the documented control point.  
- **Per-feature GitHub wrappers:** Rejected because they duplicate logic and create inconsistent protocol handling.  
- **Best-effort path checks at call sites:** Rejected because validation belongs in the centralized GitHub I/O boundary.

## Path Security Is the Mandatory Write Boundary
**Status:** Accepted

**Context:** `src/path_security.py` is explicitly defined as the security boundary and every write path must pass through it. FullPlatform manipulates repository files and generated artifacts, making path traversal and boundary enforcement critical.

**Decision:** Validate every filesystem write path through `src/path_security.py` before performing the write. Forbid bypasses, convenience shortcuts, or direct writes that skip this boundary.

**Consequences:**  
- File generation, patch application, and artifact creation must integrate with the path security API.  
- Security review can focus on one enforcement point for write authorization.  
- Unsafe relative paths, traversal attempts, and boundary escapes can be blocked consistently.  
- Refactors that introduce new write flows must include path-security integration from the outset.

**Rejected alternatives:**  
- **Caller-side manual path sanitization:** Rejected because distributed checks are inconsistent and easy to miss.  
- **Relying on repository root conventions without enforcement:** Rejected because conventions do not provide a real security boundary.  
- **Post-write validation or cleanup:** Rejected because prevention is required; validating after a write is too late.

## FullPlatform Must Preserve the Defined Root View Decision Tree
**Status:** Accepted

**Context:** The macOS application shell TRD defines a root view decision tree in which `RootView` branches first on `OnboardingState != .complete`, leading to `OnboardingContainerView` and its sub-states such as `WelcomeView`, `APIKeysView`, and `GitHubAuthView`. This establishes the top-level navigation model.

**Decision:** Implement the FullPlatform macOS shell root navigation according to the defined `RootView` decision tree, with onboarding completeness as the first top-level branch and onboarding substates rendered through `OnboardingContainerView`.

**Consequences:**  
- Top-level app flow remains predictable and traceable to the TRD.  
- Onboarding cannot be treated as a secondary modal or optional overlay when incomplete.  
- New root-level experiences must fit into or explicitly revise the documented decision tree.  
- State management and test cases must validate the defined view branching behavior.

**Rejected alternatives:**  
- **Free-form root routing based on ad hoc view model conditions:** Rejected because it drifts from the documented root decision tree.  
- **Presenting onboarding as a dismissible modal over the main app:** Rejected because the TRD makes incomplete onboarding the primary branch.  
- **Skipping intermediate onboarding container abstraction:** Rejected because `OnboardingContainerView` is part of the prescribed hierarchy.