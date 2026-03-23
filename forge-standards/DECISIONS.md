# DECISIONS.md

## Repository documentation is the source of truth
**Status:** Accepted  
**Context:** The repository structure explicitly states that all TRDs and PRDs live in `forge-docs/` and must be read before building. The platform spans backend, CI, coordination, GitHub integration, security, and the macOS shell, so implementation must remain anchored to the authored requirements rather than inferred behavior.  
**Decision:** Treat `forge-docs/` as the authoritative source of product and technical requirements, and require implementers to consult relevant TRDs/PRDs before changing FullPlatform behavior.  
**Consequences:** Design and implementation choices in FullPlatform must trace back to documents in `forge-docs/`. Local code comments, incidental behavior, or ad hoc conventions must not override documented requirements. Work that conflicts with TRDs must be updated through documentation-first change management.  
**Rejected alternatives:**  
- **Use code as the sole source of truth:** Rejected because the platform is intentionally document-driven and spans multiple subsystems not fully inferable from current code.  
- **Allow parallel undocumented conventions in subsystem folders:** Rejected because it creates drift between implementation and approved requirements.

## FullPlatform must preserve the repository boundary layout
**Status:** Accepted  
**Context:** The repository layout defines stable locations for requirements, standards, Python backend code, Swift application code, and tests. FullPlatform must interoperate across these areas without collapsing boundaries.  
**Decision:** Preserve and rely on the established top-level repository layout: `forge-docs/`, `forge-standards/`, `src/`, `Crafted/`, `CraftedTests/`, `tests/`, and root governance files.  
**Consequences:** FullPlatform code must not relocate or repurpose these directories. Cross-subsystem logic should reference them by their defined responsibilities. Tooling, automation, and generated artifacts must fit within this structure rather than introducing competing layouts.  
**Rejected alternatives:**  
- **Flatten the repository into a single app/service structure:** Rejected because it would erase the separation between standards, requirements, backend runtime, and macOS shell.  
- **Introduce subsystem-specific parallel roots for docs/tests/builds:** Rejected because it would fragment discoverability and weaken governance.

## Critical integration files are protected change points
**Status:** Accepted  
**Context:** Several files are identified as critical because they define generation, orchestration, GitHub I/O, path security, and CI workflow behavior. FullPlatform depends on these interfaces and behaviors remaining stable and intentionally modified.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as protected integration points that require impact-aware modification.  
**Consequences:** Changes touching these files must be made conservatively and with explicit consideration of cross-platform and cross-stage effects. FullPlatform features must integrate with these files through stable responsibilities rather than bypassing them.  
**Rejected alternatives:**  
- **Permit direct subsystem-specific rewrites of critical files without special treatment:** Rejected because changes here have system-wide blast radius.  
- **Duplicate critical logic inside FullPlatform:** Rejected because duplication would create inconsistent security, orchestration, and CI behavior.

## The build pipeline remains stage-based and checkpointed
**Status:** Accepted  
**Context:** The build pipeline is defined as a sequence of stages, including parse/lint/import validation, a bounded fix loop, CI execution, and an operator gate. State transitions are checkpointed, including per-PR states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`.  
**Decision:** Implement and extend FullPlatform only through the existing stage-based pipeline model, and checkpoint every stage transition and per-PR state transition.  
**Consequences:** FullPlatform cannot introduce opaque long-running workflows that skip stage transitions or suppress state persistence. Recovery, auditability, and restart behavior must rely on explicit checkpoints.  
**Rejected alternatives:**  
- **Use an event-only or fire-and-forget orchestration model:** Rejected because it weakens restartability and traceability.  
- **Collapse multiple stages into a single execution step for simplicity:** Rejected because it removes observability and narrows operator control.

## Every pipeline stage must respect a cyclomatic complexity ceiling of 15
**Status:** Accepted  
**Context:** The build pipeline requirements explicitly state that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is highlighted as strictly enforcing this limit. FullPlatform orchestration must not erode this maintainability constraint.  
**Decision:** Keep each FullPlatform pipeline stage and stage-level control unit at cyclomatic complexity 15 or below.  
**Consequences:** Complex behavior must be decomposed into helper functions, smaller strategies, or explicit state handlers rather than accumulating branching in a single stage function. Review and testing should treat complexity growth as a design failure, not a cleanup item.  
**Rejected alternatives:**  
- **Allow higher complexity in orchestration code because it is central infrastructure:** Rejected because orchestration complexity is exactly where maintainability and correctness risks compound.  
- **Enforce complexity only at file level:** Rejected because the stated requirement applies per stage, not just per module.

## The fix loop is bounded and failure-type-aware
**Status:** Accepted  
**Context:** The pipeline defines a fix loop that runs `pytest` for up to 20 attempts and uses a failure-type-aware strategy. FullPlatform must preserve bounded automated remediation rather than allowing unbounded retries or generic patch churn.  
**Decision:** Limit automated test-fix iteration to 20 attempts and select remediation strategy based on failure type.  
**Consequences:** FullPlatform must classify failures sufficiently to drive targeted fixes and must stop after the defined retry budget. Operators receive a deterministic escalation point instead of endless automation.  
**Rejected alternatives:**  
- **Retry until green:** Rejected because it can loop indefinitely, waste CI resources, and hide systemic defects.  
- **Use a fixed remediation strategy for all failures:** Rejected because syntax, import, test, and environment failures require different corrective actions.

## CI execution must remain platform-specific where required
**Status:** Accepted  
**Context:** The pipeline defines `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. FullPlatform spans Python backend and Swift/macOS application concerns, so CI must preserve environment fidelity rather than forcing a single runner model.  
**Decision:** Maintain separate CI workflows for Linux-compatible backend validation and macOS-specific Swift validation.  
**Consequences:** FullPlatform changes affecting Python and Swift may require validation in different environments. CI generation and orchestration must route work to the appropriate workflow instead of assuming cross-platform equivalence.  
**Rejected alternatives:**  
- **Run all CI on Ubuntu only:** Rejected because Swift/macOS shell validation requires macOS-specific execution.  
- **Run all CI on macOS only:** Rejected because it increases cost and latency for backend work without adding value to Linux-compatible checks.

## Operator approval remains a mandatory gate before merge
**Status:** Accepted  
**Context:** The pipeline includes a gate where the operator approves or corrects before merge, and every gate decision is checkpointed. FullPlatform is not authorized to autonomously merge changes solely on passing automation.  
**Decision:** Require an explicit operator gate before merge, and persist every gate decision as part of the checkpointed workflow state.  
**Consequences:** FullPlatform must surface sufficient context for human approval and cannot silently bypass review after tests or CI pass. Audit trails must include approvals, corrections, and gate outcomes.  
**Rejected alternatives:**  
- **Auto-merge after CI passes:** Rejected because the workflow explicitly preserves human control at the final gate.  
- **Record gate outcomes only in ephemeral logs:** Rejected because checkpointed decisions are required for auditability and recovery.

## All GitHub I/O must flow through the GitHub tools boundary
**Status:** Accepted  
**Context:** `src/github_tools.py` is designated as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. FullPlatform must not bypass this boundary when interacting with repositories or pull requests.  
**Decision:** Route all FullPlatform GitHub interactions exclusively through `src/github_tools.py` or approved abstractions built directly on it.  
**Consequences:** FullPlatform cannot make ad hoc GitHub API calls that skip rate limiting, SHA discipline, or repository safety checks. GitHub behavior remains centralized and auditable.  
**Rejected alternatives:**  
- **Allow direct API calls from feature modules for convenience:** Rejected because it bypasses safety and consistency mechanisms.  
- **Reimplement GitHub access inside FullPlatform:** Rejected because it duplicates protocol logic and increases defect risk.

## Every write path must pass through the path security boundary
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. FullPlatform manipulates repository content and generated artifacts, so write safety is a non-negotiable constraint.  
**Decision:** Require every filesystem write initiated by FullPlatform to be validated through `src/path_security.py` before execution.  
**Consequences:** FullPlatform must not perform raw writes, temp-file promotions, generated artifact output, or patch application outside the path security boundary. Security review can therefore focus on a single enforcement point.  
**Rejected alternatives:**  
- **Validate paths at the caller only:** Rejected because distributed validation is easy to miss and hard to audit.  
- **Rely on repository-relative path construction without centralized checks:** Rejected because relative path logic alone does not provide an adequate security boundary.

## CI workflow generation must remain centralized
**Status:** Accepted  
**Context:** `src/ci_workflow.py` generates the CI workflows. FullPlatform depends on coherent workflow generation across backend and Swift validation and should not fork workflow creation logic.  
**Decision:** Centralize CI workflow generation in `src/ci_workflow.py` and prohibit subsystem-specific workflow generation code paths that bypass it.  
**Consequences:** FullPlatform features that affect CI must be expressed through the existing generator boundary. This keeps workflow naming, structure, and policy consistent across the repository.  
**Rejected alternatives:**  
- **Generate workflows independently in each subsystem:** Rejected because it creates policy drift and inconsistent CI semantics.  
- **Hand-maintain workflow YAML outside the generator:** Rejected because the repository explicitly identifies a generating authority for CI workflows.

## FullPlatform must preserve backend–macOS shell separation
**Status:** Accepted  
**Context:** The repository layout separates Python backend implementation in `src/` from the Swift/SwiftUI application shell in `Crafted/` and `CraftedTests/`. TRD-1 defines app-shell behavior such as the root view decision tree, while backend responsibilities live elsewhere.  
**Decision:** Keep FullPlatform responsibilities split between backend runtime/orchestration and macOS shell presentation, with interfaces between them instead of direct responsibility overlap.  
**Consequences:** Backend code must not absorb SwiftUI view logic, and the macOS shell must not reimplement backend orchestration or policy. Tests should validate each side in its native test stack.  
**Rejected alternatives:**  
- **Embed orchestration logic directly into the macOS app:** Rejected because it couples UI concerns to backend workflow control.  
- **Move shell decision logic into Python-rendered views or generic templates:** Rejected because the application shell is explicitly Swift/SwiftUI-based.

## The macOS shell root view must follow onboarding-first routing
**Status:** Accepted  
**Context:** TRD-1 defines a root view decision tree in which incomplete onboarding routes to `OnboardingContainerView`, which then selects onboarding steps such as `WelcomeView`, `APIKeysView`, and `GitHubAuthView`. FullPlatform must not undermine this user-state-driven shell flow.  
**Decision:** Preserve onboarding-state-driven root routing in the macOS shell, with onboarding screens taking precedence until onboarding is complete.  
**Consequences:** FullPlatform features exposed through the shell must respect onboarding prerequisites and cannot route users directly into post-onboarding views before required setup is complete.  
**Rejected alternatives:**  
- **Use a single root dashboard and present onboarding modally as needed:** Rejected because the TRD specifies a root-level decision tree keyed by onboarding state.  
- **Allow deep links to bypass onboarding steps:** Rejected because it would violate required setup sequencing and state guarantees.