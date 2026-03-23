# DECISIONS.md

## Repository structure is fixed and document-first
**Status:** Accepted  
**Context:** The platform depends on TRDs and PRDs as the source of truth, and implementation spans Python backend, Swift shell, tests, and standards. Unstructured or ad hoc placement would break traceability and increase coordination cost across agents and subsystems.  
**Decision:** Keep the repository organized exactly by responsibility: `forge-docs/` for TRDs and PRDs, `forge-standards/` for governing standards and generated build rules, `src/` for Python backend implementation, `Crafted/` for the Swift/SwiftUI application shell, `CraftedTests/` for XCTest suites, and `tests/` for Python tests. Treat `forge-docs/` as the authoritative input before implementation work begins.  
**Consequences:** Implementation in FullPlatform must preserve these boundaries. New code must be placed in the designated subtree rather than creating parallel structures. Design and implementation changes must remain traceable back to documents in `forge-docs/`. Tooling and automation may assume this layout.  
**Rejected alternatives:**  
- Use a feature-based mixed layout across backend, UI, and docs: rejected because it weakens document traceability and increases cross-language coordination complexity.  
- Co-locate standards with implementation code: rejected because standards must remain stable, discoverable, and separate from runtime concerns.  
- Permit teams or agents to create new top-level directories freely: rejected because it causes drift from the documented structure and breaks automation assumptions.

## Critical files are protected modification points
**Status:** Accepted  
**Context:** Several files define core platform behavior and security boundaries. Changes to them have outsized impact on generation, orchestration, GitHub I/O, path safety, and CI workflow generation.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as critical files requiring explicit review and constraint-aware modification. Route all changes affecting core generation, orchestration, GitHub operations, write-path validation, or CI generation through these files rather than reimplementing equivalent logic elsewhere.  
**Consequences:** FullPlatform implementations must integrate with these files instead of bypassing them. Duplicate orchestration, path validation, or GitHub write logic is not allowed. Review scrutiny is higher for these files, and changes must preserve their subsystem responsibilities.  
**Rejected alternatives:**  
- Recreate similar helper logic in new modules to avoid touching critical files: rejected because it creates inconsistent behavior and bypasses established control points.  
- Spread security and GitHub concerns across many files: rejected because it weakens auditability and makes enforcement unreliable.  
- Treat all files uniformly: rejected because these files are explicit control and safety boundaries.

## Pipeline stages are explicit and must remain checkpointed
**Status:** Accepted  
**Context:** The build pipeline is multi-stage and recovery-oriented. Reliable orchestration requires visible state transitions and durable progress tracking, including per-PR lifecycle states.  
**Decision:** Implement and preserve explicit staged execution with checkpointed transitions for every stage and per-PR state, including `branch_opened → code_generated → tests_passed → committed → ci_passed`. Persist every state transition and gate decision so interrupted work can resume deterministically and audits can reconstruct execution history.  
**Consequences:** FullPlatform cannot use implicit in-memory progress only. Any workflow runner, UI, or backend integration must model stages and transitions as first-class state. Recovery, observability, and approval flows must rely on persisted checkpoints.  
**Rejected alternatives:**  
- Track only final success or failure: rejected because it prevents safe resume and obscures failure location.  
- Keep stage state only in process memory: rejected because crashes or restarts would lose orchestration state.  
- Collapse per-PR states into a single generic status: rejected because it removes operational clarity and weakens gate enforcement.

## Cyclomatic complexity per pipeline stage is capped at 15
**Status:** Accepted  
**Context:** The build pipeline is inherently complex; without a hard limit, orchestration code can become unmaintainable and unsafe to modify. The README explicitly states a maximum cyclomatic complexity of 15 for every stage.  
**Decision:** Enforce a maximum cyclomatic complexity of 15 for each pipeline stage implementation, including orchestration paths in FullPlatform. Refactor into smaller helpers or subcomponents rather than allowing stage logic to exceed the limit.  
**Consequences:** New features in FullPlatform must be decomposed instead of added as branching logic inside existing stages. Reviews should reject stage implementations that exceed the limit. Monitoring and linting may assume this threshold as a hard constraint.  
**Rejected alternatives:**  
- Allow higher complexity in “core” stages for convenience: rejected because those are the exact areas where maintainability and correctness matter most.  
- Apply the limit only to files, not stages: rejected because the documented constraint is stage-oriented and aims to bound orchestration complexity where behavior is concentrated.  
- Use subjective review instead of a fixed threshold: rejected because it leads to inconsistent enforcement.

## Syntax, lint, import, and fix-loop validation are mandatory pipeline steps
**Status:** Accepted  
**Context:** The documented build pipeline includes syntax parsing, Ruff linting, import validation, and a bounded pytest-based fix loop. These checks are foundational for generated or modified code quality before CI gate progression.  
**Decision:** Run validation in the documented order: syntax parse, Ruff, import check, then a failure-type-aware pytest fix loop with a maximum of 20 attempts. Do not skip or reorder these steps in FullPlatform execution.  
**Consequences:** Orchestration must expose these as defined steps and must stop or adapt based on their outcomes. The fix loop must remain bounded and strategy-aware. FullPlatform cannot replace these checks with less strict heuristics.  
**Rejected alternatives:**  
- Run only tests and omit syntax or import checks: rejected because earlier cheaper checks catch classes of failures faster and more deterministically.  
- Permit unlimited fix attempts: rejected because it risks non-terminating repair cycles.  
- Reorder checks based on implementation preference: rejected because the documented sequence is optimized for fast failure and controlled repair.

## CI workflow generation is platform-specific and standardized
**Status:** Accepted  
**Context:** The platform supports both Python/backend and Swift/macOS concerns. The documented pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift.  
**Decision:** Generate and maintain separate standardized CI workflows: use `crafted-ci.yml` for general CI on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift/macOS validation. FullPlatform must not collapse these into a single generic workflow when platform-specific execution is required.  
**Consequences:** CI generation logic must preserve platform distinctions. Swift validation remains explicitly tied to macOS-capable workflow execution, while general pipeline checks can run on Ubuntu. Tooling and docs can rely on the existence of these workflow identities.  
**Rejected alternatives:**  
- Use one unified workflow for all languages and platforms: rejected because Swift/macOS requirements are distinct and would complicate or weaken CI fidelity.  
- Run everything only on macOS: rejected because it is more expensive and unnecessary for non-Swift stages.  
- Run everything only on Ubuntu: rejected because it cannot faithfully validate Swift/macOS-specific behavior.

## Operator gate approval is required before merge-affecting progression
**Status:** Accepted  
**Context:** The pipeline includes a gate stage where an operator approves or corrects before merge. Automated generation alone is insufficient for merge-affecting decisions in this subsystem.  
**Decision:** Require an explicit operator gate before merge or equivalent final progression. Record every gate decision as part of checkpointed state and do not treat silence or pipeline completion as implicit approval.  
**Consequences:** FullPlatform must provide a mechanism for approval or correction and must persist the outcome. Merge-capable automation must stop at the gate until approval is given. Audit trails must include who approved and when.  
**Rejected alternatives:**  
- Auto-merge after tests and CI pass: rejected because the documented process requires human gating.  
- Treat approval as optional for low-risk changes: rejected because the decision applies uniformly unless a future documented exception is added.  
- Infer approval from lack of rejection: rejected because it is not auditable and creates ambiguity.

## All write paths must pass through the path security boundary
**Status:** Accepted  
**Context:** `src/path_security.py` is explicitly identified as the security boundary, and every write path must pass through it. FullPlatform will perform file operations across generated code, workflows, and repository updates.  
**Decision:** Route every filesystem write, update, or generated artifact path through `src/path_security.py` validation before performing the operation. Do not perform direct writes that bypass this boundary.  
**Consequences:** FullPlatform file-writing components must integrate with the shared path validation layer. Security review can focus on a single enforcement point. Any bypass is a correctness and security defect.  
**Rejected alternatives:**  
- Validate paths locally in each module: rejected because distributed enforcement is inconsistent and harder to audit.  
- Validate only external or user-provided paths: rejected because internal generation paths can still be dangerous if miscomputed.  
- Rely on repository-relative writes without validation: rejected because relative path assumptions do not guarantee safety.

## All GitHub I/O must go through the centralized GitHub tools layer
**Status:** Accepted  
**Context:** `src/github_tools.py` is designated for all GitHub I/O and encapsulates path validation, rate limiting, and SHA protocol requirements. FullPlatform interacts with GitHub branches, commits, PRs, and related state.  
**Decision:** Perform all GitHub reads and writes through `src/github_tools.py`. Preserve its controls for path validation, rate limiting, and SHA-based update protocol; do not call GitHub APIs directly from new FullPlatform code when equivalent functionality belongs in this layer.  
**Consequences:** GitHub integration remains consistent, auditable, and concurrency-safe. New functionality may extend the tools layer, but must not bypass it. Rate limiting and SHA correctness become enforceable in one place.  
**Rejected alternatives:**  
- Call GitHub APIs directly from feature modules: rejected because it duplicates protocol handling and risks inconsistent safety behavior.  
- Create a second GitHub abstraction for FullPlatform only: rejected because it fragments policy enforcement and operational knowledge.  
- Ignore SHA protocol for “simple” writes: rejected because it risks lost updates and inconsistent repository state.

## The root macOS application flow must follow the documented onboarding decision tree
**Status:** Accepted  
**Context:** TRD-1 defines the root view decision tree, beginning with onboarding completeness and routing to onboarding views when incomplete. FullPlatform includes the macOS application shell and must preserve predictable entry behavior.  
**Decision:** Implement the root SwiftUI application flow so that `RootView` first evaluates onboarding state and routes incomplete onboarding to `OnboardingContainerView`, with state-specific presentation for `.notStarted`, `.apiKeys`, `.githubAuth`, and subsequent documented onboarding steps; only fully completed onboarding may proceed to the main application experience.  
**Consequences:** The macOS shell cannot bypass onboarding prerequisites or substitute a different top-level routing model without updating the governing TRD. Root navigation and state restoration must align with onboarding state semantics.  
**Rejected alternatives:**  
- Enter the main application by default and surface onboarding later: rejected because it conflicts with the documented root decision tree.  
- Use independent modal onboarding flows from arbitrary screens: rejected because it weakens deterministic startup behavior.  
- Collapse all onboarding into one undifferentiated screen: rejected because the documented flow is state-based and step-specific.