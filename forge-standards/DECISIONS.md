# DECISIONS.md

## Repository source of truth lives in `forge-docs`
**Status:** Accepted  
**Context:** The platform is constrained by a document-driven development process. TRDs and PRDs define expected behavior, subsystem boundaries, and implementation constraints before code changes are made. The repository structure explicitly places all TRDs and PRDs in `forge-docs/`, and implementation must align with those documents.  
**Decision:** Treat `forge-docs/` as the authoritative source of product and technical requirements. Read relevant TRDs and PRDs before implementing or modifying FullPlatform behavior.  
**Consequences:** Implementation choices in the FullPlatform subsystem must trace back to documented requirements. Code changes that conflict with TRDs are invalid unless the documents are updated first. Engineers must consult documentation before altering architecture or workflow behavior.  
**Rejected alternatives:**  
- Treating code as the sole source of truth — rejected because the repository is explicitly organized around TRD-first development.  
- Allowing ad hoc implementation decisions without document review — rejected because it creates drift from approved architecture and workflow intent.

## Preserve the documented repository layout
**Status:** Accepted  
**Context:** The repository layout assigns clear responsibilities across documentation, standards, backend code, Swift application code, and test suites. FullPlatform spans these areas and depends on stable structure for orchestration, tooling, and automation.  
**Decision:** Preserve the documented top-level repository layout and place FullPlatform changes only in the appropriate directory: `src/` for Python backend logic, `Crafted/` for Swift application shell code, `CraftedTests/` for XCTest coverage, `tests/` for pytest coverage, `forge-standards/` for standards documents, and `forge-docs/` for requirements.  
**Consequences:** Implementations must not blur boundaries between backend, UI shell, standards, and requirements. Tooling and automation may assume stable paths. Refactors that move major areas require an explicit architectural update.  
**Rejected alternatives:**  
- Flattening the repository into a smaller number of directories — rejected because it weakens subsystem boundaries and breaks documented expectations.  
- Co-locating generated artifacts with source indiscriminately — rejected because it increases ambiguity and complicates automation.

## Honor critical-file ownership boundaries
**Status:** Accepted  
**Context:** Several files are identified as critical because they define core execution paths, orchestration, GitHub I/O, security boundaries, and CI generation. Changes to these files have system-wide impact.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as controlled integration points. Modify them only when a FullPlatform change directly requires it, and preserve their stated responsibilities.  
**Consequences:** New behavior should be added at the correct seam instead of bypassing existing core modules. Cross-cutting changes require extra scrutiny because these files affect every generated PR, security validation, or CI path.  
**Rejected alternatives:**  
- Duplicating logic outside the critical files to avoid touching them — rejected because it fragments core behavior and increases inconsistency.  
- Freely expanding responsibilities of critical files — rejected because they already serve as system choke points and must remain comprehensible.

## Enforce a maximum cyclomatic complexity of 15 per stage
**Status:** Accepted  
**Context:** The build pipeline is explicitly constrained so that every stage has a maximum cyclomatic complexity of 15. This is both an implementation rule and a maintainability guardrail. `src/build_director.py` is specifically called out with this limit.  
**Decision:** Keep each FullPlatform pipeline stage and stage-level orchestration function at or below cyclomatic complexity 15. Decompose logic into helper functions or smaller units rather than increasing branch density.  
**Consequences:** Pipeline logic must be modular. Large conditional controllers, monolithic retry logic, and deeply nested decision trees are disallowed. Complexity management becomes a first-class design concern during implementation and review.  
**Rejected alternatives:**  
- Allowing higher complexity in orchestrators because they are “central” — rejected because the documented limit applies to every stage.  
- Enforcing complexity only at file level — rejected because the requirement is stage-oriented and must constrain operational logic directly.

## Implement the build pipeline as explicit staged flow
**Status:** Accepted  
**Context:** The README defines a staged pipeline including generation checks, a fix loop, test and CI execution, and an operator gate before merge. FullPlatform must execute within this prescribed lifecycle rather than inventing a different orchestration model.  
**Decision:** Implement FullPlatform workflow as explicit stages matching the documented pipeline, including generation validation, fix-loop execution, CI/test execution, and final gating before merge.  
**Consequences:** Stage semantics must remain visible in code and persisted state. New features must integrate into existing stages or add clearly defined new stages rather than introducing hidden side paths. Operational observability and restart behavior depend on stage clarity.  
**Rejected alternatives:**  
- Using a free-form event-driven flow with implicit transitions — rejected because the documented system is stage-based and checkpointed.  
- Collapsing multiple stages into a single opaque execution step — rejected because it obscures failures and conflicts with checkpointing requirements.

## Checkpoint every state transition, including per-PR transitions
**Status:** Accepted  
**Context:** The pipeline documentation requires every state transition to be checkpointed, including per-PR states such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This enables resumability, auditability, and gate enforcement.  
**Decision:** Persist every FullPlatform state transition as a checkpoint, including all per-PR lifecycle states and stage boundaries. Do not perform untracked in-memory-only transitions for meaningful workflow progress.  
**Consequences:** State management must be durable and granular. Recovery, retries, and operator review can rely on persisted execution history. Implementations must define checkpoint writes as part of the success path for each transition.  
**Rejected alternatives:**  
- Checkpointing only terminal states — rejected because intermediate progress is explicitly required.  
- Using logs as a substitute for checkpoints — rejected because logs do not provide structured resumable state.

## Preserve explicit gate decisions before merge
**Status:** Accepted  
**Context:** The pipeline requires an operator gate before merge, and every gate decision is part of the documented process. FullPlatform must support human approval or correction rather than silently auto-merging all successful work.  
**Decision:** Require an explicit gate decision before merge and record that decision as part of workflow state. Do not bypass operator approval for changes that reach the final gate.  
**Consequences:** Full automation ends at the merge gate unless policy is updated. UI and backend behavior must expose pending approval states and support correction paths. Audit history must include gate outcomes.  
**Rejected alternatives:**  
- Automatically merging after CI success — rejected because it violates the documented operator gate.  
- Treating gate review as informal communication outside the system — rejected because gate decisions are part of the managed workflow.

## Keep the Python fix loop failure-type-aware and bounded
**Status:** Accepted  
**Context:** The build pipeline specifies a fix loop using pytest with up to 20 attempts and a failure-type-aware strategy. This is a concrete operational requirement for remediation behavior.  
**Decision:** Implement the Python fix loop as a bounded retry mechanism with a hard cap of 20 attempts and branch logic informed by failure type. Do not use unbounded retries or a single generic repair strategy for all failures.  
**Consequences:** Failure classification becomes part of the repair system design. Retry controllers must stop deterministically. Observability should expose attempt count and failure category.  
**Rejected alternatives:**  
- Infinite or open-ended retries until green — rejected because it risks runaway execution and contradicts the documented 20-attempt cap.  
- A uniform retry strategy for all failures — rejected because the process explicitly requires failure-type-aware handling.

## Run CI with platform-specific workflows
**Status:** Accepted  
**Context:** The documented pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. FullPlatform spans Python backend and Swift/macOS application concerns, so CI must reflect platform differences.  
**Decision:** Use distinct CI workflows for Linux-oriented and macOS/Swift validation, specifically preserving Ubuntu-based CI for general pipeline execution and macOS CI for Swift-related validation.  
**Consequences:** CI generation and invocation must remain platform-aware. Swift and macOS-specific validation cannot be collapsed into Linux-only execution. Workflow maintenance must account for separate runtime environments.  
**Rejected alternatives:**  
- Running all CI only on Ubuntu — rejected because Swift/macOS validation requires macOS-specific execution.  
- Running all CI only on macOS — rejected because it increases cost and does not reflect the documented split workflow design.

## Route all GitHub I/O through `src/github_tools.py`
**Status:** Accepted  
**Context:** `src/github_tools.py` is the designated module for GitHub interactions and is responsible for path validation, rate limiting, and SHA protocol handling. Bypassing it would undermine consistency and safety.  
**Decision:** Perform all FullPlatform GitHub reads and writes through `src/github_tools.py`. Do not introduce direct GitHub API access paths that bypass its validation and protocol logic.  
**Consequences:** GitHub integration behavior remains centralized and enforceable. Changes to rate limiting, SHA handling, or validation are applied uniformly. New integrations must extend the existing abstraction rather than sidestep it.  
**Rejected alternatives:**  
- Calling GitHub APIs directly from feature modules — rejected because it duplicates critical logic and weakens controls.  
- Splitting GitHub behavior across multiple ad hoc utility modules — rejected because repository I/O policy must stay centralized.

## Route every write path through `src/path_security.py`
**Status:** Accepted  
**Context:** `src/path_security.py` is explicitly described as the security boundary and requires every write path to pass through it. FullPlatform may generate, update, or checkpoint files across the repository, making this boundary non-optional.  
**Decision:** Validate every filesystem write path through `src/path_security.py` before performing the write. Do not allow alternate write code paths that bypass path security checks.  
**Consequences:** File generation, patching, checkpointing, and workflow artifact creation must integrate with the central security validator. Unsafe path manipulation patterns are prohibited. Security review can focus on one enforced boundary.  
**Rejected alternatives:**  
- Validating paths only in high-risk features — rejected because the requirement applies to every write path.  
- Relying on caller discipline rather than a central boundary — rejected because it is unenforceable and error-prone.

## Keep CI workflow generation centralized in `src/ci_workflow.py`
**Status:** Accepted  
**Context:** CI workflow generation is identified as a critical responsibility of `src/ci_workflow.py`. FullPlatform behavior that affects CI must use this module to preserve consistency across generated workflows.  
**Decision:** Generate or modify CI workflow definitions through `src/ci_workflow.py` rather than emitting workflow YAML from unrelated modules.  
**Consequences:** CI logic remains centralized and reviewable. Platform-specific workflow updates can be controlled in one place. Feature modules must request CI changes through this integration point.  
**Rejected alternatives:**  
- Allowing each subsystem to generate its own workflow fragments independently — rejected because it leads to drift and inconsistent workflow structure.  
- Storing CI YAML generation inline in orchestration code — rejected because it mixes concerns and complicates maintenance.

## Preserve the root-view onboarding decision tree in the macOS shell
**Status:** Accepted  
**Context:** TRD-1 defines a root view decision tree where `RootView` branches based on `OnboardingState`, with incomplete onboarding routed through `OnboardingContainerView` and specific onboarding screens. FullPlatform must not undermine this user flow in the macOS shell.  
**Decision:** Implement and preserve root navigation in the Swift application shell according to the documented `OnboardingState` decision tree. Do not bypass onboarding-dependent routing in `RootView`.  
**Consequences:** UI features in FullPlatform must integrate with onboarding state rather than presenting primary application flows prematurely. Authentication, API key setup, and related prerequisites remain first-class routing conditions.  
**Rejected alternatives:**  
- Presenting the main application immediately and prompting for setup later — rejected because it violates the documented root-view flow.  
- Encoding onboarding navigation as scattered conditional logic across multiple entry views — rejected because the TRD defines a central decision tree in `RootView`.