# DECISIONS.md

## [Adopt the canonical monorepo layout for ForgeAgent]
**Status:** Accepted

**Context:** ForgeAgent operates within a repository whose structure is already defined by the TRDs and README. The location of specifications, implementation, standards, tests, and platform-specific code is part of the system contract. Allowing subsystem-specific layout drift would break discoverability, automation, and build orchestration.

**Decision:** Keep ForgeAgent implementation within the existing canonical repository layout. Treat `forge-docs/` as the source of truth for TRDs and PRDs, `forge-standards/` as the source of implementation constraints and conventions, `src/` as the Python backend location, `tests/` as the Python test location, and `Crafted/` and `CraftedTests/` as the Swift application shell and XCTest locations. Do not introduce parallel documentation, standards, or backend roots for ForgeAgent.

**Consequences:** ForgeAgent code must be implemented in `src/` and tested from `tests/`. Design constraints must be reflected in `forge-standards/DECISIONS.md` rather than subsystem-local ad hoc documents. Automation may assume fixed paths for docs, standards, and code. Any new ForgeAgent assets must fit into the established structure instead of creating a bespoke subsystem tree.

**Rejected alternatives:** Creating a standalone `forge-agent/` subtree was rejected because it would duplicate repository responsibilities and fragment source-of-truth documents. Storing agent-specific standards beside implementation was rejected because repository-wide automation expects standards in `forge-standards/`. Splitting Python backend code across multiple top-level roots was rejected because it weakens build and test determinism.

## [Treat TRDs and PRDs in forge-docs as binding inputs before implementation]
**Status:** Accepted

**Context:** The repository explicitly states that all TRDs and PRDs live in `forge-docs/` and must be read before building. ForgeAgent is expected to implement behavior derived from these documents, not from inferred or local-only assumptions.

**Decision:** Read and treat the documents in `forge-docs/` as authoritative requirements before modifying ForgeAgent behavior. When implementation conflicts with undocumented assumptions, prefer the documented TRD/PRD contract and update implementation accordingly.

**Consequences:** ForgeAgent changes must be traceable to documented requirements. Implementation work cannot rely solely on code-local interpretation. Engineers modifying ForgeAgent must consult the relevant TRDs before changing orchestration, consensus, GitHub integration, security boundaries, CI behavior, or UI-related interactions.

**Rejected alternatives:** Treating code as the only source of truth was rejected because the repository explicitly elevates TRDs/PRDs as authoritative. Using informal team knowledge instead of repository documents was rejected because it is not auditable or durable. Maintaining a separate ForgeAgent requirements file outside `forge-docs/` was rejected because it would create conflicting requirement sources.

## [Require critical-file review before modifying ForgeAgent behavior]
**Status:** Accepted

**Context:** Several files are identified as critical because they define core generation, pipeline orchestration, GitHub I/O, path security, and CI workflow generation. Changes in these locations have system-wide impact.

**Decision:** Before modifying ForgeAgent behavior that touches generation, orchestration, GitHub operations, write-path handling, or CI workflow generation, review the designated critical files: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Treat these files as high-risk integration boundaries.

**Consequences:** Changes to ForgeAgent must account for subsystem interactions already embodied in the critical files. Reviews and tests must focus on regression risk around these boundaries. New behavior should integrate through existing critical-file interfaces where possible rather than bypassing them.

**Rejected alternatives:** Allowing changes without reviewing the critical files was rejected because these modules affect every PR, security boundary, and CI path. Duplicating logic outside these files was rejected because it would create inconsistent behavior and hidden integration points. Marking all files as equally critical was rejected because it dilutes review focus and weakens risk management.

## [Route all repository writes through path security validation]
**Status:** Accepted

**Context:** `src/path_security.py` is explicitly identified as the security boundary, and every write path must pass through it. ForgeAgent performs automated code and workflow generation, making write safety a primary control.

**Decision:** Enforce that every filesystem write initiated by ForgeAgent passes through the path validation and security mechanisms defined in `src/path_security.py`. Do not permit direct writes that bypass this boundary.

**Consequences:** Any file creation, modification, patch application, workflow generation, or artifact persistence in ForgeAgent must use approved path-security entry points. Security review can assume a single write boundary. Refactors must preserve central enforcement rather than moving validation into scattered call sites.

**Rejected alternatives:** Performing validation only at API edges was rejected because internal call paths could still bypass protections. Relying on developer discipline to avoid unsafe paths was rejected because automated agents require enforceable controls. Implementing per-module custom path checks was rejected because it creates inconsistent policy enforcement and increases audit complexity.

## [Centralize all GitHub I/O in github_tools]
**Status:** Accepted

**Context:** `src/github_tools.py` is identified as handling all GitHub I/O, including path validation, rate limiting, and SHA protocol. ForgeAgent interacts with pull requests, branches, commits, and repository content, making API consistency essential.

**Decision:** Route all ForgeAgent GitHub reads and writes through `src/github_tools.py`. Preserve centralized handling for path validation, rate limiting, and SHA-aware update semantics. Do not call GitHub APIs directly from feature modules when an operation falls within repository I/O.

**Consequences:** ForgeAgent implementations must depend on shared GitHub abstractions rather than bespoke API clients. Cross-cutting concerns such as retries, validation, optimistic concurrency, and protocol compliance remain enforceable in one place. Tests can mock GitHub interactions at a single boundary.

**Rejected alternatives:** Direct per-feature GitHub API calls were rejected because they duplicate rate-limit and SHA logic and increase inconsistency. Introducing a second GitHub client layer inside ForgeAgent was rejected because it fragments ownership of protocol behavior. Treating local git operations as equivalent to GitHub I/O was rejected because repository-hosted PR workflows still require centralized remote protocol handling.

## [Keep the core generation loop in consensus as the single orchestration source]
**Status:** Accepted

**Context:** `src/consensus.py` is identified as the core generation loop, and changes there affect every PR the agent builds. ForgeAgent depends on consistent generation behavior across all automated work.

**Decision:** Preserve `src/consensus.py` as the single source for the core generation loop used by ForgeAgent. Integrate new generation behavior through this loop rather than creating parallel orchestration paths.

**Consequences:** Feature work that alters how code is generated, revised, or reconciled must be expressed through the existing consensus flow. System-wide behavior remains predictable and reviewable. Testing must prioritize regressions that affect all PR generation.

**Rejected alternatives:** Building feature-specific generation loops was rejected because it causes divergence in PR behavior. Embedding generation control inside pipeline stages or GitHub tooling was rejected because it obscures responsibility and complicates testing. Allowing ad hoc invocation chains from multiple modules was rejected because it weakens determinism.

## [Enforce maximum cyclomatic complexity of 15 per pipeline stage]
**Status:** Accepted

**Context:** The build pipeline requires that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is explicitly noted as strictly enforcing this limit. ForgeAgent orchestration must remain understandable and maintainable.

**Decision:** Design ForgeAgent pipeline stages so that each stage remains at or below cyclomatic complexity 15. When a stage approaches the limit, split behavior into smaller helpers or subroutines without violating stage semantics.

**Consequences:** Pipeline code must favor decomposition over large conditional branches. Reviews should reject stage logic that exceeds or obscures the complexity limit. Additional features may require introducing well-bounded helper functions rather than expanding a single stage controller.

**Rejected alternatives:** Raising the complexity cap for “special” stages was rejected because the repository states the limit as universal. Ignoring complexity in orchestration code was rejected because the build director depends on disciplined stage structure. Measuring only file-level complexity was rejected because the constraint is specifically per stage.

## [Implement the build pipeline as the required staged flow]
**Status:** Accepted

**Context:** The README defines the build pipeline stages, including validation and fix-loop behavior, followed by test/CI and a merge gate. ForgeAgent is a pipeline-driven subsystem and must conform to this staged contract.

**Decision:** Implement ForgeAgent execution as the defined staged pipeline, including validation steps (`ast.parse`, `ruff`, import check), a bounded fix loop with up to 20 pytest attempts using failure-type-aware strategy, CI workflow execution, and a final operator gate before merge.

**Consequences:** ForgeAgent cannot skip validation, collapse the fix loop into unbounded retries, or bypass the operator gate. Pipeline telemetry, checkpoints, and UI/reporting can rely on stable stage semantics. Failure handling must classify and respond to failure types rather than retrying blindly.

**Rejected alternatives:** A single-pass generate-and-merge flow was rejected because it omits required validation, testing, and approval stages. Unlimited retry loops were rejected because the pipeline explicitly bounds pytest fix attempts to 20. Fully autonomous merge without operator approval was rejected because the gate stage requires human approval or correction before merge.

## [Checkpoint every pipeline state transition, including per-PR milestones]
**Status:** Accepted

**Context:** The README requires that every state transition be checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. ForgeAgent coordinates long-running and failure-prone work, so resumability and auditability are necessary.

**Decision:** Persist a checkpoint at every ForgeAgent state transition, including all per-PR milestone transitions defined by the pipeline. Checkpoints must be sufficient to reconstruct progress and resume safely after interruption.

**Consequences:** ForgeAgent implementations must model transitions explicitly rather than relying on implicit in-memory progress. Recovery logic can resume from the latest valid checkpoint. Auditing and debugging can trace exactly where a PR or task failed or paused.

**Rejected alternatives:** Checkpointing only stage boundaries was rejected because the requirement includes per-PR milestones. Logging without durable checkpoint state was rejected because it is insufficient for safe recovery. End-of-run persistence only was rejected because it loses intermediate progress and failure provenance.

## [Record every gate decision]
**Status:** Accepted

**Context:** The pipeline documentation requires that every gate decision be recorded. ForgeAgent includes operator approval or correction before merge, and those decisions affect auditability, accountability, and reproducibility.

**Decision:** Persist every gate decision made during ForgeAgent execution, including approvals, rejections, corrections, and any associated rationale or outcome metadata necessary to understand the decision.

**Consequences:** Merge-related workflows must have an auditable history. UI, reporting, and recovery flows can distinguish between automated completion and operator-directed intervention. Implementations must not treat gate actions as ephemeral UI events only.

**Rejected alternatives:** Recording only final merge outcomes was rejected because the requirement is to record every gate decision. Storing gate decisions only in transient logs was rejected because they are not durable or queryable enough for audit purposes. Capturing approval without correction rationale was rejected because it undermines traceability when operators intervene.

## [Use crafted CI workflow split by platform]
**Status:** Accepted

**Context:** The pipeline defines Stage 5 as Test + CI, using `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. ForgeAgent must generate or rely on CI workflows that respect platform-specific execution.

**Decision:** Maintain the CI workflow split such that general CI runs in `crafted-ci.yml` on `ubuntu-latest`, while Swift/macOS-specific CI runs in `crafted-ci-macos.yml`. ForgeAgent must not collapse these into a single undifferentiated workflow.

**Consequences:** Python/backend and Swift/macOS validation remain aligned with their execution environments. Workflow generation and updates in `src/ci_workflow.py` must preserve platform separation. CI failures can be attributed more clearly to backend versus macOS-specific issues.

**Rejected alternatives:** A single cross-platform workflow was rejected because Swift validation requires macOS-specific execution. Running all CI on macOS was rejected because it is unnecessarily expensive and diverges from the documented Ubuntu workflow for general CI. Running all CI on Ubuntu was rejected because it cannot validate the Swift/macOS shell correctly.

## [Preserve operator approval as a mandatory pre-merge gate]
**Status:** Accepted

**Context:** Stage 6 of the pipeline requires that an operator approve or correct before merge. ForgeAgent may automate generation and validation, but final merge authority is intentionally constrained.

**Decision:** Require explicit operator approval or correction before merging ForgeAgent-produced changes. Do not implement unattended auto-merge that bypasses this gate.

**Consequences:** ForgeAgent must support human-in-the-loop workflows and surface sufficient context for approval decisions. Merge automation must pause pending operator action. Product expectations must account for supervised, not fully autonomous, completion.

**Rejected alternatives:** Fully automatic merge after passing tests and CI was rejected because it conflicts with the mandatory gate. Optional operator review was rejected because the documented stage requires operator action. Post-merge human review was rejected because the decision point must occur before merge.

## [Respect the existing macOS application shell root view decision tree]
**Status:** Accepted

**Context:** TRD-1 defines the root view decision tree for the Crafted macOS application shell, beginning with onboarding state and routing to onboarding containers before the main experience. ForgeAgent features exposed through the app must not violate this navigation contract.

**Decision:** Integrate any ForgeAgent-related UI in the Crafted app without breaking the existing RootView decision tree. Preserve onboarding-state-driven routing and do not surface ForgeAgent functionality ahead of required onboarding completion.

**Consequences:** ForgeAgent UI work must fit into the app’s established navigation and state model. Features depending on API keys, GitHub authentication, or environment readiness must remain inaccessible until onboarding requirements are satisfied. UI changes may require coordination with existing onboarding and root state handling rather than shortcut entry points.

**Rejected alternatives:** Adding a separate ForgeAgent root entry independent of onboarding was rejected because it bypasses the defined app flow. Exposing partial ForgeAgent UI before required credentials are configured was rejected because it violates dependency ordering. Replacing the root decision tree with subsystem-specific routing was rejected because TRD-1 already defines the application shell contract.