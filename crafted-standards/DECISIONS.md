# DECISIONS.md

## Repository source-of-truth lives in forge-docs
**Status:** Accepted  
**Context:** The subsystem operates in a repository where all TRDs and PRDs are explicitly centralized under `forge-docs/`. Implementation must be constrained by those documents before code changes are made, and repository conventions identify them as the authoritative specification set.  
**Decision:** Treat `forge-docs/` as the authoritative source of product and technical requirements, and require CraftedApp implementation decisions to align with the TRDs and PRDs stored there before code generation or repository mutation.  
**Consequences:** CraftedApp must be implemented to read and honor requirements from `forge-docs/` first. Local assumptions, inferred behavior, or code-only conventions must not override documented TRDs. Any subsystem behavior that conflicts with `forge-docs/` is invalid until the documents are updated.  
**Rejected alternatives:**  
- Using source code as the primary source of truth was rejected because the repository explicitly defines TRDs and PRDs as governing artifacts.  
- Distributing requirements across multiple ad hoc folders was rejected because it weakens discoverability and increases the risk of building against stale guidance.  

## Preserve critical-file boundaries for core orchestration and security
**Status:** Accepted  
**Context:** The repository identifies a set of critical files whose behavior affects generation, orchestration, GitHub I/O, path validation, and CI workflow generation. These files form subsystem boundaries with elevated change risk.  
**Decision:** Preserve the architectural responsibilities of the critical files and require any CraftedApp implementation to respect these boundaries: `src/consensus.py` for core generation flow, `src/build_director.py` for pipeline orchestration, `src/github_tools.py` for GitHub I/O, `src/path_security.py` for write-path enforcement, and `src/ci_workflow.py` for CI workflow generation.  
**Consequences:** CraftedApp changes must not bypass or duplicate these responsibilities in new modules. Security checks must remain anchored in `src/path_security.py`; GitHub writes and reads must flow through `src/github_tools.py`; orchestration logic must remain centralized in `src/build_director.py`. Refactors that relocate these responsibilities require explicit architectural revision, not incidental implementation drift.  
**Rejected alternatives:**  
- Allowing features to implement their own file-write security checks was rejected because it creates inconsistent enforcement and weakens the security boundary.  
- Splitting GitHub I/O across multiple convenience modules was rejected because the repository defines a single integration boundary and rate/path/SHA handling must remain consistent.  
- Embedding orchestration logic directly into feature modules was rejected because it undermines pipeline control and increases complexity spread.  

## Enforce allowlisted repository root directories for all writes
**Status:** Accepted  
**Context:** GitHub integration lessons learned state that commits to unexpected repository roots fail silently or are blocked by path security guards. Dot-prefixed roots such as `.github` require explicit allowlisting.  
**Decision:** Restrict CraftedApp file creation and modification to an explicit allowlist of approved repository root directories, including at minimum `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`, and require all write paths to pass through path validation.  
**Consequences:** CraftedApp must not write to new top-level directories unless the allowlist is intentionally extended. CI workflow generation under `.github` must be explicitly permitted and validated. Unexpected output locations are treated as errors rather than best-effort writes.  
**Rejected alternatives:**  
- Permitting writes anywhere inside the repository was rejected because prior experience showed silent failures and security-guard rejections.  
- Allowing dot-prefixed roots implicitly was rejected because path validators commonly deny them by default and the repository explicitly requires allowlisting.  
- Creating roots on demand from prompts was rejected because it expands the attack surface and breaks predictable repository layout.  

## Route every repository write through path security validation
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. This is a hard implementation guard, not a guideline.  
**Decision:** Require every CraftedApp filesystem write, patch, generated artifact, and repository mutation to be validated through the centralized path security layer before execution.  
**Consequences:** No direct file write APIs may bypass path validation. Helper utilities, CI generators, GitHub commit flows, and test artifact writers must all use the same security gate. This constrains implementation patterns and prohibits “trusted internal write” shortcuts.  
**Rejected alternatives:**  
- Trusting internal modules to write directly was rejected because internal callers are still a source of path mistakes and policy drift.  
- Validating only user-supplied paths was rejected because generated and derived paths can also violate repository policy.  
- Post-write auditing was rejected because the repository requires prevention at the boundary, not detection after mutation.  

## Centralize all GitHub I/O behind github_tools
**Status:** Accepted  
**Context:** `src/github_tools.py` is the declared boundary for all GitHub I/O, including path validation concerns, rate limiting, and SHA protocol handling. Consistency in remote repository operations is required.  
**Decision:** Implement all CraftedApp GitHub reads, writes, commits, tree operations, and related API interactions exclusively through `src/github_tools.py` or abstractions layered directly on top of it without bypassing its controls.  
**Consequences:** CraftedApp cannot call GitHub APIs directly from feature code. SHA handling, retries, rate limits, and path checks remain consistent across the subsystem. This also constrains test seams and integration mocking to the GitHub tools boundary.  
**Rejected alternatives:**  
- Direct per-feature GitHub API clients were rejected because they fragment protocol handling and create inconsistent safety behavior.  
- Using shell-based git commands as a parallel write path was rejected because it bypasses the established GitHub I/O controls and repository policy checks.  
- Duplicating a simplified GitHub helper for speed was rejected because correctness and consistency take precedence over local convenience.  

## Keep build pipeline stage complexity at or below 15
**Status:** Accepted  
**Context:** The repository states that every stage has a maximum cyclomatic complexity of 15, and specifically notes that `src/build_director.py` is under a strict complexity limit. The build pipeline is a controlled staged system rather than an open-ended orchestrator.  
**Decision:** Design CraftedApp pipeline logic so that each stage implementation remains at cyclomatic complexity 15 or lower, and split logic into subordinate helpers instead of expanding stage controllers beyond that limit.  
**Consequences:** Complex feature behavior must be decomposed rather than accumulated in stage methods. Reviews and implementation choices must optimize for bounded control flow. Large conditional orchestrators and monolithic recovery logic are disallowed.  
**Rejected alternatives:**  
- Allowing higher complexity in “core” orchestration files was rejected because the repository explicitly applies the limit to every stage.  
- Deferring complexity control to linting only was rejected because this is an architectural constraint, not merely a style preference.  
- Consolidating all pipeline recovery logic into one decision tree was rejected because it would violate the complexity ceiling and reduce maintainability.  

## Preserve the staged build pipeline and ordered validation flow
**Status:** Accepted  
**Context:** The repository README defines an ordered pipeline with syntax/lint/import checks, a fix loop with bounded attempts, CI generation, and an operator gate before merge. This sequence is part of the subsystem’s behavior contract.  
**Decision:** Implement CraftedApp as a staged pipeline that preserves ordered validation: parse and static checks before iterative test-fix attempts, CI workflow generation before merge gating, and no stage skipping without explicit architectural approval.  
**Consequences:** CraftedApp must not run merge, commit-finalization, or CI success reporting before earlier validation stages complete. Syntax and import validity are mandatory early gates. Pipeline optimizations may parallelize internals only if externally visible stage order and gate semantics remain intact.  
**Rejected alternatives:**  
- A free-form agent loop that decides validation order dynamically was rejected because the repository defines explicit stages and transitions.  
- Running tests before basic syntax and import validation was rejected because cheap deterministic checks should fail fast earlier in the pipeline.  
- Skipping CI workflow generation for non-Swift or simple changes was rejected because CI definition is part of the standard pipeline contract.  

## Bound the automated fix loop to 20 pytest attempts
**Status:** Accepted  
**Context:** The build pipeline description specifies a fix loop of “pytest up to 20 attempts” with failure-type-aware strategy. This imposes both a retry cap and an expectation of structured remediation behavior.  
**Decision:** Limit CraftedApp’s automated test-fix loop to a maximum of 20 pytest-driven remediation attempts per pipeline execution and require each retry to be based on the observed failure type rather than blind repetition.  
**Consequences:** CraftedApp must terminate remediation after the cap and surface failure for external review or gating. Retry logic must remain bounded and diagnosable. Infinite or open-ended self-healing behavior is prohibited.  
**Rejected alternatives:**  
- Unlimited retry loops were rejected because they can stall pipelines and mask underlying defects.  
- A very small fixed retry budget was rejected because the documented process explicitly allows up to 20 attempts.  
- Naive identical retries were rejected because the pipeline expects failure-type-aware repair strategy, not repeated execution without adaptation.  

## Checkpoint every stage transition, including per-PR states
**Status:** Accepted  
**Context:** The repository requires every state transition to be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. This supports recoverability, auditability, and controlled progression.  
**Decision:** Persist a checkpoint record for every CraftedApp pipeline state transition, including all required per-PR milestones, and treat checkpoint creation as mandatory for advancing to the next state.  
**Consequences:** CraftedApp must maintain durable stage progress and resume semantics. Observability, restart behavior, and debugging must rely on explicit transition records rather than inferred state. Implementations that mutate repository or PR state without checkpointing are non-compliant.  
**Rejected alternatives:**  
- Checkpointing only major milestones was rejected because the repository requires every state transition to be recorded.  
- Keeping state only in memory was rejected because it breaks recovery and audit expectations.  
- Inferring state from GitHub or filesystem side effects was rejected because such inference is ambiguous and not sufficient for deterministic pipeline control.  

## Require an operator gate before merge
**Status:** Accepted  
**Context:** The pipeline definition includes a gate where the operator approves or corrects before merge, and every gate decision is checkpointed. Human approval is therefore part of the merge contract.  
**Decision:** Do not allow CraftedApp to merge automatically without an explicit operator approval gate, and checkpoint the gate outcome as part of the pipeline state model.  
**Consequences:** Even after tests and CI pass, final merge remains blocked pending operator action. CraftedApp must support correction or approval outcomes and must not collapse this into a silent auto-merge path.  
**Rejected alternatives:**  
- Fully automated merge on green CI was rejected because it violates the documented gate requirement.  
- Optional operator approval based on change size was rejected because the repository describes the gate as a standard pipeline stage, not a heuristic branch.  
- Recording approval outside the checkpoint system was rejected because all gate decisions must be statefully tracked.  

## Generate standard CI workflows in .github for platform coverage
**Status:** Accepted  
**Context:** The build pipeline specifies `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. The `.github` root is also explicitly called out as needing allowlist support.  
**Decision:** Generate and maintain standard CraftedApp CI workflow definitions under `.github`, including Linux CI via `crafted-ci.yml` and macOS CI via `crafted-ci-macos.yml` when Swift or macOS-specific validation is required.  
**Consequences:** CI configuration is a first-class generated artifact and must live under the approved `.github` root. CraftedApp implementations that affect Swift or macOS behavior must preserve macOS workflow support rather than relying only on Ubuntu validation.  
**Rejected alternatives:**  
- Storing generated CI outside `.github` was rejected because GitHub Actions requires the standard workflow location and path security must explicitly allow it.  
- Running only Ubuntu CI for all projects was rejected because Swift and macOS validation require dedicated macOS workflow coverage.  
- Leaving CI workflow creation to manual setup was rejected because workflow generation is an explicit pipeline responsibility.  

## Preserve repository layout conventions under forge-standards
**Status:** Accepted  
**Context:** The repository layout defines `forge-standards/` as the location for architecture and convention documents, including `ARCHITECTURE.md`, `INTERFACES.md`, `DECISIONS.md`, `CONVENTIONS.md`, and `build_rules.md`. This establishes where enduring implementation constraints belong.  
**Decision:** Store CraftedApp architectural standards and design constraints in `forge-standards/`, and treat `DECISIONS.md` as the persistent record of implementation-constraining architectural decisions.  
**Consequences:** New long-lived design rules for CraftedApp must be added to the standards location rather than buried in code comments or ephemeral task notes. Implementers must consult these standards artifacts when changing subsystem structure or behavior.  
**Rejected alternatives:**  
- Keeping architectural decisions only in issue threads or PR descriptions was rejected because those are not durable standards artifacts.  
- Storing standards documents beside implementation modules was rejected because the repository already defines a dedicated standards location.  
- Treating `DECISIONS.md` as optional documentation was rejected because the repository layout explicitly reserves it for governing design decisions.