# DECISIONS.md

## [ForgeAgent repository structure is fixed to the monorepo layout]
**Status:** Accepted  
**Context:** The TRDs define a single repository containing product documentation, standards, backend runtime, tests, and the macOS shell. ForgeAgent must operate within this structure because documentation is the source of truth and implementation spans Python and Swift.  
**Decision:** Treat the repository layout as a hard contract. Read requirements from `forge-docs/`, follow standards in `forge-standards/`, implement backend behavior in `src/`, place Python tests in `tests/`, and treat `Crafted/` and `CraftedTests/` as the Swift application shell and its test suite. Do not relocate, virtualize, or redefine these top-level directories.  
**Consequences:** Implementation must resolve paths against this layout. Agent workflows must read TRDs and PRDs before making code changes. Cross-language changes must preserve both Python and Swift directory boundaries. Tooling and prompts must assume the documented repository shape.  
**Rejected alternatives:**  
- Allowing ForgeAgent to infer arbitrary repository layouts from discovery: rejected because TRDs explicitly define the canonical structure and many workflows depend on stable locations.  
- Splitting ForgeAgent into a separate repository: rejected because required artifacts, standards, and code live together and must be versioned together.  
- Treating documentation as advisory instead of authoritative: rejected because `forge-docs/` is defined as the source of truth.

## [Critical files require heightened modification discipline]
**Status:** Accepted  
**Context:** Several files are identified as critical because they define core generation, orchestration, GitHub I/O, path security, and CI workflow generation. Changes to these files have system-wide impact.  
**Decision:** Require ForgeAgent to treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as protected implementation hotspots. Before modifying any of them, read the file, preserve existing contracts, and constrain changes to the smallest viable scope.  
**Consequences:** Refactors in these files must be deliberate and narrowly targeted. New behavior should prefer composition around these modules rather than broad rewrites inside them. Tests and validation must be strengthened when any of these files change.  
**Rejected alternatives:**  
- Treating all source files as equally risky: rejected because the TRDs explicitly call out these modules as having outsized systemic impact.  
- Freely refactoring critical modules during feature work: rejected because it increases regression risk across generation, orchestration, security, and CI.  
- Freezing critical files completely: rejected because the subsystem must still evolve, but under tighter constraints.

## [Pipeline stages and ordering are mandatory]
**Status:** Accepted  
**Context:** The build pipeline is specified as an ordered, staged process with explicit generation, validation, fix-loop, CI, and gating behavior. Consistency of execution is necessary for reproducibility and recovery.  
**Decision:** Implement ForgeAgent workflows as the documented staged pipeline, including syntax/format/import validation, a bounded fix loop, CI execution, and operator gate before merge. Do not bypass, collapse, or reorder stages without an explicit new decision.  
**Consequences:** Orchestration logic must model stage boundaries directly. Intermediate artifacts and failures must be attributable to a specific stage. Optimizations may exist inside a stage, but not by eliminating required stages.  
**Rejected alternatives:**  
- A free-form agent loop that decides validation order dynamically: rejected because it weakens determinism and checkpoint semantics.  
- Running CI before local validation: rejected because local static and unit checks are intended to fail fast before remote or heavier execution.  
- Merging generation and fix-loop into a single unconstrained loop: rejected because the TRD requires a structured, bounded repair process.

## [Cyclomatic complexity per stage is capped at 15]
**Status:** Accepted  
**Context:** The build pipeline specification explicitly states that every stage has a maximum cyclomatic complexity of 15. This is an implementation constraint intended to preserve maintainability and auditability.  
**Decision:** Keep each pipeline stage implementation at cyclomatic complexity 15 or below. Split logic into helper functions, strategy objects, or subroutines rather than allowing stage handlers to exceed the cap.  
**Consequences:** Stage orchestration code must remain modular. Large conditional trees must be decomposed. Reviews should reject implementations that exceed the complexity limit even if functionally correct.  
**Rejected alternatives:**  
- Enforcing complexity only at file level: rejected because the requirement applies to each stage, not just aggregate modules.  
- Allowing exceptions for “orchestration-heavy” code: rejected because `src/build_director.py` is explicitly called out and the limit is strict.  
- Relying on post hoc refactoring after implementation: rejected because complexity must constrain design up front.

## [All pipeline state transitions must be checkpointed]
**Status:** Accepted  
**Context:** The README specifies that every state transition is checkpointed, including per-PR lifecycle states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. This is required for auditability and resumption.  
**Decision:** Persist a checkpoint at every pipeline state transition and at each defined per-PR state milestone. Checkpoints must be recorded as part of the normal control flow, not as best-effort logging.  
**Consequences:** ForgeAgent must model states explicitly and write durable transition records. Recovery logic can resume from known stages instead of re-running the entire flow. Implementations that mutate state without recording a checkpoint are non-compliant.  
**Rejected alternatives:**  
- Checkpointing only major stages: rejected because the requirement explicitly includes per-PR states.  
- Using transient logs instead of durable checkpoints: rejected because logs do not provide reliable resumability or explicit state reconstruction.  
- Checkpointing only on success: rejected because transitions, including failure-relevant transitions, must be auditable.

## [Gate decisions must be recorded before merge]
**Status:** Accepted  
**Context:** The pipeline includes an operator approval/correction gate before merge, and the README states every gate decision is recorded. This supports accountability and operational safety.  
**Decision:** Require an explicit, recorded gate decision before any merge action. ForgeAgent must not auto-merge work that has not passed through the documented gate.  
**Consequences:** Merge logic must depend on gate state, not just technical success. The system must preserve an auditable record of approval or correction. Fully autonomous merge behavior is disallowed within this subsystem.  
**Rejected alternatives:**  
- Auto-merging after tests and CI pass: rejected because the process requires an operator gate.  
- Recording approvals only in external systems informally: rejected because the decision must be captured in the pipeline record.  
- Allowing silent default approval after timeout: rejected because it undermines the gate’s control purpose.

## [The fix loop is bounded to 20 pytest attempts]
**Status:** Accepted  
**Context:** The build pipeline defines a fix loop with `pytest` and a maximum of 20 attempts, using failure-type-aware strategy. This prevents runaway repair behavior while allowing iterative correction.  
**Decision:** Enforce a hard maximum of 20 fix-loop attempts for test repair. Each attempt must be informed by the observed failure type rather than repeating a generic retry.  
**Consequences:** Repair logic must track attempt count and stop deterministically at the limit. Implementations must classify or otherwise interpret failures to select a remediation strategy. Infinite or open-ended self-healing loops are prohibited.  
**Rejected alternatives:**  
- Unlimited retries until tests pass: rejected because it risks non-termination and hides poor repair quality.  
- A single retry only: rejected because the TRD explicitly provides for iterative repair.  
- Blindly rerunning the same step without failure analysis: rejected because the strategy must be failure-type-aware.

## [Validation order is syntax parse, Ruff, then import check]
**Status:** Accepted  
**Context:** The documented build pipeline specifies local validation in a concrete order: `ast.parse`, then `ruff`, then import checking, before entering the fix loop. This establishes fast-fail behavior and consistent diagnostics.  
**Decision:** Execute validation in the prescribed sequence: syntax parse first, lint/style/static issues via Ruff second, and import check third. Do not reorder these checks.  
**Consequences:** Early failures stop later checks and produce more actionable diagnostics. Tooling must preserve this order in both normal runs and resumptions. Any new checks must be inserted without violating the mandated sequence of these existing checks.  
**Rejected alternatives:**  
- Running Ruff before syntax parse: rejected because linting on syntactically invalid code is less reliable and slower to diagnose.  
- Import checking before linting: rejected because unresolved imports should not preempt simpler local correctness checks.  
- Parallelizing all checks and reporting a mixed result: rejected because the TRD defines an ordered stage, not a concurrent bundle.

## [CI workflow targets are fixed by platform]
**Status:** Accepted  
**Context:** The README specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. This encodes platform-specific CI responsibilities for Python/backend versus macOS/Swift concerns.  
**Decision:** Generate and maintain CI workflows using the documented split: `crafted-ci.yml` for Ubuntu-based CI and `crafted-ci-macos.yml` for Swift/macOS execution. Do not collapse them into a single cross-platform workflow by default.  
**Consequences:** CI generation logic must preserve separate workflow files and runner targets. Changes affecting Swift validation must account for macOS-specific execution. Backend-only checks should remain runnable on Ubuntu unless a new requirement says otherwise.  
**Rejected alternatives:**  
- A single unified CI workflow for all languages and platforms: rejected because Swift/macOS requires distinct runner support and the TRD names separate workflows.  
- Running all CI on macOS only: rejected because it increases cost and diverges from the specified Ubuntu workflow for general CI.  
- Running Swift checks on Ubuntu through emulation or stubs: rejected because it would not faithfully validate the macOS shell.

## [All GitHub I/O must flow through the GitHub tools boundary]
**Status:** Accepted  
**Context:** `src/github_tools.py` is identified as the module for all GitHub I/O and is responsible for path validation, rate limiting, and SHA protocol handling. Concentrating this behavior is necessary for correctness and safety.  
**Decision:** Route all GitHub API interactions through `src/github_tools.py` or abstractions built directly on top of it. Do not introduce ad hoc GitHub HTTP calls elsewhere in the subsystem.  
**Consequences:** Rate limiting, SHA handling, and path validation remain centralized. Testing can mock a single GitHub integration boundary. New GitHub features must extend the existing integration layer rather than bypass it.  
**Rejected alternatives:**  
- Direct GitHub API calls from feature modules: rejected because they would fragment rate-limit handling, path validation, and update semantics.  
- Multiple specialized GitHub clients per feature area: rejected because shared protocol behavior would drift.  
- Shelling out to git or GitHub CLI for equivalent operations by default: rejected because the designated module is the authoritative integration boundary.

## [All write paths must pass through path security validation]
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. This is a core protection against unsafe file system access.  
**Decision:** Validate every filesystem write target through `src/path_security.py` before performing the write. No component may write directly to disk using unchecked paths.  
**Consequences:** File creation and modification APIs must be designed to require security validation as part of the call path. Convenience utilities that bypass validation are prohibited. Security review can focus on one enforced boundary.  
**Rejected alternatives:**  
- Performing inline path checks in each caller: rejected because distributed checks are inconsistent and easy to miss.  
- Validating only external or user-provided paths: rejected because all write paths are required to pass through the boundary.  
- Relying on repository-relative writes without explicit validation: rejected because relative paths can still be abused or mishandled.

## [Document artifacts remain the source of truth for ForgeAgent behavior]
**Status:** Accepted  
**Context:** The repository structure states that all TRDs and PRDs live in `forge-docs/`, and the repository layout describes them as the source of truth. ForgeAgent is expected to read them before building.  
**Decision:** Derive ForgeAgent behavior and implementation constraints from documents in `forge-docs/` and standards in `forge-standards/` before changing code. Where code and docs diverge, treat the documents as authoritative until explicitly updated.  
**Consequences:** Development workflows must include document review before implementation. Code generation and modification should trace back to specific requirements. “Code says otherwise” is not sufficient justification to ignore documented constraints.  
**Rejected alternatives:**  
- Treating runtime code as the primary source of truth: rejected because the repository contract explicitly assigns that role to TRDs and PRDs.  
- Using tribal knowledge or prompt defaults when documents exist: rejected because it undermines reproducibility and governance.  
- Updating code first and documentation later as a normal pattern: rejected because it creates drift against the declared authority model.

## [Swift root-view navigation must preserve the documented onboarding decision tree]
**Status:** Accepted  
**Context:** TRD-1 defines a root view decision tree in which `RootView` branches on onboarding completion state and routes through `OnboardingContainerView` and its staged views. ForgeAgent may touch the macOS shell and must not violate this top-level navigation model.  
**Decision:** Preserve the documented root-view decision tree for the Crafted macOS application shell. Changes to SwiftUI navigation must conform to the onboarding-state-driven structure unless a new architectural decision supersedes it.  
**Consequences:** Feature additions in the Swift shell must integrate into the existing onboarding and root routing model rather than replacing it with ad hoc navigation. Tests and previews should reflect state-based entry points.  
**Rejected alternatives:**  
- Replacing the root decision tree with implicit navigation side effects: rejected because the TRD specifies explicit state-driven root routing.  
- Collapsing onboarding into a single undifferentiated screen: rejected because the onboarding flow is defined as staged.  
- Letting backend agent behavior redefine UI root structure opportunistically: rejected because the shell architecture is document-driven, not agent-inferred.