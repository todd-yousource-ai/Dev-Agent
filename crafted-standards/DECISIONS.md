# DECISIONS.md

## [Treat forge-docs as the authoritative source before implementation]
**Status:** Accepted

**Context:** CraftedAgent operates in a repository where technical requirements are defined in TRDs and PRDs under `forge-docs/`. The subsystem must not infer behavior from implementation alone when the documented requirements are intended to be the source of truth.

**Decision:** Read applicable documents in `forge-docs/` before implementing or modifying CraftedAgent behavior, and treat those documents as authoritative over inferred local conventions.

**Consequences:** Implementation work is constrained by documented requirements first. Changes that conflict with TRDs or PRDs must be treated as design mismatches rather than silently implemented. Contributors must review relevant documents before changing subsystem behavior.

**Rejected alternatives:**  
- **Use code as the sole source of truth:** Rejected because repository guidance explicitly places TRDs and PRDs in `forge-docs` as authoritative inputs.  
- **Rely on informal contributor knowledge:** Rejected because it is not durable, reviewable, or enforceable.  
- **Read documentation only when tests fail:** Rejected because it makes requirements validation reactive instead of mandatory.

## [Require review of critical files before modifying agent behavior]
**Status:** Accepted

**Context:** Several files form the operational and security backbone of the agent system. Changes to these files have disproportionate impact on generation behavior, orchestration, repository writes, and CI output.

**Decision:** Review the designated critical files before modifying related CraftedAgent behavior: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`.

**Consequences:** Contributors must inspect existing logic and invariants in these files before making changes in adjacent areas. This reduces accidental regressions in core generation loops, orchestration, GitHub I/O, path enforcement, and workflow generation.

**Rejected alternatives:**  
- **Allow local changes without reviewing critical files:** Rejected because subsystem behavior depends on hidden invariants in those files.  
- **Document critical behavior only in external docs:** Rejected because the critical constraints are embodied in code paths that must be understood directly.  
- **Treat all files as equally sensitive:** Rejected because it weakens attention on the highest-risk components.

## [Enforce path writes through the path security boundary]
**Status:** Accepted

**Context:** CraftedAgent performs repository writes and must respect repository path security constraints. `src/path_security.py` is identified as the security boundary, and write-path validation must be uniformly enforced.

**Decision:** Route every repository write performed by CraftedAgent through the path security boundary, and do not permit bypasses or direct filesystem writes that skip validation.

**Consequences:** All write operations must use approved validation mechanisms. Any feature that writes files must integrate with path security first. This constrains implementation convenience in favor of a uniform security control point.

**Rejected alternatives:**  
- **Permit trusted internal callers to bypass validation:** Rejected because trust assumptions erode the security boundary over time.  
- **Validate only on commit, not on write:** Rejected because invalid paths should be blocked at the earliest point of side effect.  
- **Rely on GitHub API failures to catch bad paths:** Rejected because repository security must not depend on downstream rejection behavior.

## [Maintain an explicit allowlist of repository root directories]
**Status:** Accepted

**Context:** GitHub integration lessons show that writes to unexpected root directories fail silently or are rejected by path security guards. Standard projects require explicit root allowlisting, including dot-prefixed roots such as `.github`.

**Decision:** Validate all CraftedAgent write targets against an explicit root-directory allowlist that includes at minimum `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs` when applicable to the project.

**Consequences:** New top-level directories require deliberate allowlist updates before use. Dot-prefixed directories are not implicitly permitted. Agent features that generate files in new roots must include corresponding security and configuration updates.

**Rejected alternatives:**  
- **Allow any root path under the repository:** Rejected because it defeats the guard against unexpected write locations.  
- **Infer allowed roots from existing repository contents:** Rejected because presence does not equal permission and can drift over time.  
- **Special-case `.github` as always allowed:** Rejected because dot-prefixed roots require explicit treatment and should remain visible in policy.

## [Centralize all GitHub I/O in github_tools]
**Status:** Accepted

**Context:** GitHub operations carry repository integrity, rate limiting, path validation, and SHA-handling requirements. `src/github_tools.py` is designated as the integration point for these concerns.

**Decision:** Perform all CraftedAgent GitHub reads and writes through `src/github_tools.py`, and keep path validation, rate limiting, and SHA protocol handling centralized there.

**Consequences:** Callers must not implement ad hoc GitHub API access paths. Changes to GitHub behavior must be made in the shared integration layer. This improves consistency but increases the importance of regression-safe changes in that module.

**Rejected alternatives:**  
- **Allow each feature to call GitHub APIs directly:** Rejected because it duplicates security, rate limiting, and SHA logic.  
- **Split SHA handling into a separate utility layer immediately:** Rejected because the critical file designation already centralizes these concerns in `github_tools.py`.  
- **Handle rate limiting only at higher orchestration layers:** Rejected because enforcement belongs at the actual I/O boundary.

## [Keep build pipeline stage logic within a cyclomatic complexity limit of 15]
**Status:** Accepted

**Context:** The build pipeline imposes a strict maximum cyclomatic complexity of 15 per stage, and `src/build_director.py` is explicitly called out as enforcing this limit.

**Decision:** Implement each CraftedAgent pipeline stage so that its cyclomatic complexity does not exceed 15, and refactor stage logic when complexity approaches the limit.

**Consequences:** Complex behavior must be decomposed into helpers or smaller units instead of accumulating branching in stage handlers. This constrains implementation style and discourages monolithic orchestration methods.

**Rejected alternatives:**  
- **Permit exceptions for central orchestration code:** Rejected because orchestration complexity is specifically identified as needing strict enforcement.  
- **Apply the limit only to files, not stages:** Rejected because the requirement is stage-scoped.  
- **Use code review discretion instead of a hard limit:** Rejected because a discretionary rule is easier to erode and less testable.

## [Checkpoint every state transition in the agent pipeline]
**Status:** Accepted

**Context:** The build pipeline requires that every state transition be checkpointed, including per-PR states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. This supports recoverability, auditing, and operator visibility.

**Decision:** Persist a checkpoint at every CraftedAgent state transition, including all per-PR lifecycle transitions and gate outcomes.

**Consequences:** Pipeline implementations must define explicit transition boundaries and durable checkpoint writes. Recovery logic can rely on saved state, but developers must maintain checkpoint compatibility when evolving the state model.

**Rejected alternatives:**  
- **Checkpoint only major milestones:** Rejected because the requirement calls for every state transition.  
- **Keep transitions only in memory until completion:** Rejected because it prevents reliable recovery and auditability.  
- **Checkpoint only failure states:** Rejected because successful progression also needs traceability and resumability.

## [Model per-PR lifecycle states explicitly]
**Status:** Accepted

**Context:** The pipeline documentation names specific per-PR stages: `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. These states are not incidental logs; they are the tracked lifecycle for generated work.

**Decision:** Represent the CraftedAgent per-PR lifecycle with explicit, named states that include at least `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`.

**Consequences:** State handling, checkpointing, and operator tooling must align to these named lifecycle points. Implementations may add internal substates, but they must not collapse or obscure the required externally meaningful states.

**Rejected alternatives:**  
- **Use a generic progress percentage instead of named states:** Rejected because it is ambiguous and weak for recovery and audit purposes.  
- **Infer state from repository artifacts after the fact:** Rejected because inference is brittle and can become inconsistent.  
- **Track only a final success/failure outcome:** Rejected because it loses the required intermediate lifecycle semantics.

## [Use a failure-type-aware fix loop with bounded retry attempts]
**Status:** Accepted

**Context:** The build pipeline specifies a fix loop driven by `pytest` with up to 20 attempts and a failure-type-aware strategy. CraftedAgent must improve code iteratively without entering unbounded retry behavior.

**Decision:** Implement the CraftedAgent fix loop as a bounded retry process with a maximum of 20 attempts, and select remediation behavior based on classified failure type rather than a single generic retry action.

**Consequences:** Retry logic must include attempt tracking and failure classification. The subsystem cannot loop indefinitely on failing changes. Remediation strategies must be explicit enough to vary by failure category.

**Rejected alternatives:**  
- **Retry until tests pass:** Rejected because it creates non-terminating behavior and contradicts the documented cap.  
- **Use a fixed generic repair prompt for every failure:** Rejected because the pipeline requires failure-type-aware strategy selection.  
- **Stop after the first failure without repair:** Rejected because the pipeline explicitly includes an iterative fix loop.

## [Validate generated code through the defined parse-lint-import sequence]
**Status:** Accepted

**Context:** The build pipeline defines a validation sequence for generated code: `ast.parse`, then `ruff`, then import check. This sequence provides fast structural and style feedback before deeper testing.

**Decision:** Validate CraftedAgent-generated Python code in the order `ast.parse` → `ruff` → import check before entering later repair or test stages.

**Consequences:** Early-stage validation ordering is fixed and should not be rearranged casually. Faster structural failures are surfaced before slower checks. Tooling and error handling should preserve this sequence for consistent diagnostics.

**Rejected alternatives:**  
- **Run tests before syntax and lint checks:** Rejected because it is slower and bypasses the intended early-failure pipeline.  
- **Use only linting as a proxy for syntax and import safety:** Rejected because the documented sequence separates these concerns explicitly.  
- **Allow stage-specific reordering based on convenience:** Rejected because consistent validation ordering improves determinism and debugging.

## [Generate CI workflows for both general and Swift/macOS cases]
**Status:** Accepted

**Context:** The pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is the workflow-generation component and therefore must preserve this split.

**Decision:** Generate distinct CI workflows for general builds and Swift/macOS builds, using `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` when Swift/macOS support is required.

**Consequences:** Workflow generation must account for platform-specific execution instead of forcing all projects through a single CI target. CI logic remains explicit about OS differences. Changes to workflow generation must preserve both workflow classes.

**Rejected alternatives:**  
- **Use a single universal workflow for all languages and platforms:** Rejected because Swift/macOS requirements are explicitly distinct.  
- **Run all CI on macOS to simplify branching:** Rejected because it is unnecessarily costly and conflicts with the defined Ubuntu workflow for general cases.  
- **Generate workflows manually outside the subsystem:** Rejected because `src/ci_workflow.py` is designated as the generator.

## [Preserve an operator approval gate before merge]
**Status:** Accepted

**Context:** The build pipeline includes a gate where the operator approves or corrects before merge. This is a control point for quality, safety, and accountability.

**Decision:** Do not permit CraftedAgent to merge autonomously past the final gate; require operator approval or operator correction before merge completion.

**Consequences:** The subsystem must surface artifacts and status for human review rather than treating successful CI as sufficient for merge. Full automation ends before final merge authority. UX and state handling must represent pending operator action.

**Rejected alternatives:**  
- **Auto-merge after CI passes:** Rejected because the documented gate requires operator approval or correction.  
- **Require operator review only on failures:** Rejected because the gate exists before merge, not only as an exception path.  
- **Replace operator approval with configurable confidence thresholds:** Rejected because probabilistic confidence does not satisfy the explicit review gate.

## [Record every gate decision durably]
**Status:** Accepted

**Context:** Repository guidance states that every gate decision is recorded. Because gate outcomes affect merge authority and auditability, these decisions must be durable and reviewable.

**Decision:** Persist every CraftedAgent gate decision as a durable record linked to the relevant pipeline or PR state.

**Consequences:** Approval, rejection, and correction actions must be stored rather than treated as ephemeral UI events. Audit and recovery flows can reconstruct why a merge did or did not proceed. Schema evolution must preserve gate-decision history.

**Rejected alternatives:**  
- **Log gate decisions only in transient application memory:** Rejected because decisions must survive restarts and support auditability.  
- **Record only final approvals:** Rejected because corrections and rejections are also meaningful gate decisions.  
- **Rely on GitHub review state alone:** Rejected because subsystem-level gate semantics must remain available within CraftedAgent’s own state model.