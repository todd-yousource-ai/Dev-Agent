# DECISIONS.md

## Repository documentation is the source of truth
**Status:** Accepted  
**Context:** The subsystem operates inside a repository where requirements, constraints, and architecture are already defined in TRDs, PRDs, and standards documents. Implementation drift would create unsafe or noncompliant behavior, especially in orchestration, GitHub interaction, and security-sensitive file writes.  
**Decision:** Treat `forge-docs/` and `forge-standards/` as authoritative inputs before making implementation changes, and align CraftedDevAgent behavior with those documents rather than inferring behavior from code alone.  
**Consequences:** Implementations must be validated against repository documentation first. Changes that contradict documented standards are invalid unless the documentation is updated through the defined workflow. The agent must preserve compatibility with `ARCHITECTURE.md`, `INTERFACES.md`, `CONVENTIONS.md`, and this file.  
**Rejected alternatives:**  
- **Code-as-truth only:** Rejected because existing code may lag documented requirements and would allow silent divergence from intended architecture.  
- **README-only guidance:** Rejected because README summaries are incomplete relative to the TRDs and standards set.  

## Critical implementation files require elevated change discipline
**Status:** Accepted  
**Context:** Several files are identified as high-risk because they define core generation, orchestration, GitHub I/O, path validation, and CI workflow generation. Changes to these files have system-wide effects.  
**Decision:** Require explicit review of `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` before modifying related behavior, and treat edits to them as architectural changes rather than routine refactors.  
**Consequences:** Feature work touching these files must preserve security, protocol, and complexity constraints. Refactors must be limited, intentional, and validated with targeted tests. Indirect changes elsewhere must not bypass responsibilities owned by these files.  
**Rejected alternatives:**  
- **Allow equivalent logic to be reimplemented in new modules:** Rejected because it would fragment security and orchestration boundaries.  
- **Treat these files as ordinary implementation details:** Rejected because the repository explicitly marks them as critical and high-impact.  

## Build execution shall remain a staged pipeline
**Status:** Accepted  
**Context:** The build pipeline is defined as a sequence of bounded stages, including validation and fix-loop behavior. Predictability and checkpointability depend on retaining this staged model.  
**Decision:** Implement CraftedDevAgent work as an explicit staged pipeline with preserved stage boundaries, including parse/lint/import validation, fix-loop execution, test/CI, and final gate behavior.  
**Consequences:** The subsystem must not collapse multiple stages into opaque execution steps. Stage outputs must be inspectable, resumable, and attributable to a named phase. Error handling should remain stage-aware.  
**Rejected alternatives:**  
- **Single-pass autonomous generation:** Rejected because it reduces observability and breaks failure isolation.  
- **Dynamic stage creation at runtime without canonical stages:** Rejected because it undermines checkpointing and operator comprehension.  

## Cyclomatic complexity per stage is capped at 15
**Status:** Accepted  
**Context:** The repository explicitly sets a maximum cyclomatic complexity of 15 for every stage. This is both a maintainability and reliability constraint on orchestration code.  
**Decision:** Keep each pipeline stage implementation at cyclomatic complexity 15 or below, and decompose logic into helper functions or strategy modules when a stage risks exceeding that limit.  
**Consequences:** Large conditional flows must be split rather than accumulated in a single stage function. Orchestration design favors composable, testable units. Complexity growth in `src/build_director.py` and related stage code is a correctness concern, not merely a style issue.  
**Rejected alternatives:**  
- **Permit higher complexity in orchestration because it is “central” logic:** Rejected because the repository explicitly forbids it.  
- **Enforce complexity only at file level:** Rejected because the constraint is stage-specific, not module-wide.  

## Every state transition shall be checkpointed
**Status:** Accepted  
**Context:** The build pipeline requires checkpointing of every state transition, including per-PR transitions such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This supports resumability, auditing, and recovery.  
**Decision:** Persist a checkpoint for each state transition and make stage progression dependent on recorded state rather than transient in-memory flow alone.  
**Consequences:** Pipeline execution must be resumable after interruption. Implementations must model transitions explicitly and avoid hidden state changes. Observability and audit tooling can rely on durable progression records.  
**Rejected alternatives:**  
- **Checkpoint only major milestones:** Rejected because the documented requirement includes every transition, including per-PR stages.  
- **Use logs instead of structured checkpoints:** Rejected because logs are insufficient for deterministic resume and state validation.  

## Gate decisions must be recorded explicitly
**Status:** Accepted  
**Context:** The pipeline includes an operator gate before merge, and documentation states that gate decisions are checkpointed. This decision point is material for compliance and auditability.  
**Decision:** Record every operator gate decision as structured state, including approval and correction outcomes, before merge-related actions proceed.  
**Consequences:** Merge behavior must remain blocked pending recorded operator disposition. The subsystem must preserve an audit trail for human intervention and correction cycles.  
**Rejected alternatives:**  
- **Treat operator approval as an ephemeral UI action:** Rejected because it would not satisfy checkpointing and auditability requirements.  
- **Auto-merge on passing CI with optional operator override:** Rejected because the documented pipeline defines an operator gate before merge.  

## GitHub interactions must flow exclusively through the GitHub tools boundary
**Status:** Accepted  
**Context:** `src/github_tools.py` is designated as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. Scattering GitHub logic would weaken correctness and security guarantees.  
**Decision:** Route all GitHub API reads, writes, branch operations, and content updates through `src/github_tools.py` or narrowly scoped abstractions built directly on it; do not perform ad hoc GitHub I/O elsewhere.  
**Consequences:** Rate limiting, SHA handling, and path safety remain centralized. Testing can mock a single boundary. Future protocol changes are localized.  
**Rejected alternatives:**  
- **Direct GitHub SDK calls from feature modules:** Rejected because it bypasses repository-mandated safeguards and protocol handling.  
- **Separate read and write clients in unrelated modules:** Rejected because it fragments consistency and security controls.  

## All write paths must pass through the path security boundary
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary for file writes. The subsystem may generate and modify repository files, which creates path traversal and unauthorized write risks.  
**Decision:** Validate every filesystem write target through `src/path_security.py` before any write occurs, without exception.  
**Consequences:** No module may write directly to disk using unchecked paths. File generation, patch application, temp-file promotion, and workflow emission must all use the path validation boundary. Security review can focus on one enforcement point.  
**Rejected alternatives:**  
- **Validate paths only for user-supplied inputs:** Rejected because generated and derived paths can also be unsafe.  
- **Use per-module path checks:** Rejected because duplicate validation logic increases inconsistency and bypass risk.  

## CI workflow generation remains centralized
**Status:** Accepted  
**Context:** `src/ci_workflow.py` is the designated generator for CI workflows, including Ubuntu and macOS variants referenced by the build pipeline. Workflow generation affects repository-wide validation behavior.  
**Decision:** Centralize generated CI workflow definitions in `src/ci_workflow.py` and preserve support for `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift-related execution.  
**Consequences:** CI behavior remains consistent across generated changes. Platform-specific workflow logic stays in one place. The subsystem must not emit one-off workflow YAML from unrelated components.  
**Rejected alternatives:**  
- **Inline workflow templates in orchestration code:** Rejected because it duplicates CI logic and obscures ownership.  
- **Generate only a single cross-platform workflow:** Rejected because the documented pipeline explicitly distinguishes Ubuntu and macOS workflows.  

## The fix loop is bounded and failure-type-aware
**Status:** Accepted  
**Context:** The build pipeline specifies a fix loop with pytest retries up to 20 attempts and a failure-type-aware strategy. Unlimited or naive retry behavior would waste resources and reduce determinism.  
**Decision:** Implement the fix loop with a hard cap of 20 attempts and select remediation strategies based on classified failure type rather than repeating the same action blindly.  
**Consequences:** Retry logic must maintain attempt counts and use failure taxonomy or equivalent classification input. The subsystem must stop after the bounded limit and surface unresolved failures clearly.  
**Rejected alternatives:**  
- **Unlimited retries until green:** Rejected because it risks nontermination and contradicts the documented cap.  
- **Fixed retry strategy for all failures:** Rejected because the pipeline explicitly requires failure-type-aware behavior.  

## Validation order shall preserve syntax, lint, and import checks before fix-loop iteration
**Status:** Accepted  
**Context:** The documented pipeline identifies an ordered validation segment: `ast.parse → ruff → import check`, followed by the fix loop. Early structural validation prevents expensive downstream retries on trivial defects.  
**Decision:** Execute syntax parsing first, then linting, then import validation, and only then enter test-driven fix-loop behavior.  
**Consequences:** The subsystem must fail fast on malformed code and unresolved import structure before invoking broader tests. Remediation can target the earliest failing validation layer.  
**Rejected alternatives:**  
- **Run tests before syntax and lint checks:** Rejected because it wastes execution and obscures root causes.  
- **Perform validations in arbitrary order:** Rejected because documented ordering is intentional and operationally useful.  

## The subsystem shall preserve the documented repository layout
**Status:** Accepted  
**Context:** The repository layout assigns clear responsibility boundaries across documentation, standards, Python backend, Swift shell, and test suites. The CraftedDevAgent must operate within those boundaries to remain maintainable.  
**Decision:** Place implementation and generated changes into the existing repository areas according to responsibility: backend logic in `src/`, Swift shell code in `Crafted/`, XCTest in `CraftedTests/`, pytest in `tests/`, and standards/docs in their designated directories.  
**Consequences:** The subsystem must not introduce parallel top-level structures that duplicate these roles. Tests must be added to the appropriate framework location. Documentation artifacts belong with standards or source docs, not mixed into runtime code paths.  
**Rejected alternatives:**  
- **Create a separate agent-specific top-level tree:** Rejected because it would fragment repository organization and bypass established conventions.  
- **Co-locate tests beside runtime code indiscriminately:** Rejected because the repository already defines dedicated test locations.  

## The macOS application shell shall honor the documented root view decision tree
**Status:** Accepted  
**Context:** TRD-1 defines a root view decision tree where onboarding state determines whether onboarding containers or post-onboarding application views are shown. The subsystem must not invent alternative shell navigation behavior.  
**Decision:** Preserve the root-shell navigation model driven by `OnboardingState`, with incomplete onboarding routing to `OnboardingContainerView` and its documented child states before main application flow is entered.  
**Consequences:** Any changes affecting the Swift shell must respect the onboarding-first gating model. New features cannot bypass required onboarding states such as API keys or GitHub authentication.  
**Rejected alternatives:**  
- **Flatten onboarding into optional modals after app launch:** Rejected because it violates the documented root decision structure.  
- **Allow direct entry into the main app before onboarding completion:** Rejected because it conflicts with the specified state-driven routing.