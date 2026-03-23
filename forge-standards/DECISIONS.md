# DECISIONS.md

## [Treat forge-docs TRDs and PRDs as the implementation source of truth]
**Status:** Accepted  
**Context:** The repository structure explicitly defines `forge-docs/` as the location where all TRDs and PRDs live and instructs implementers to read them before building. The CraftedDevAgent subsystem must operate within those documented requirements rather than inventing behavior ad hoc.  
**Decision:** Always treat documents in `forge-docs/` as the authoritative source of product and technical requirements before implementing or modifying CraftedDevAgent behavior.  
**Consequences:** Implementation must be traceable to TRD/PRD requirements. Changes that conflict with `forge-docs/` are invalid unless the documentation is updated first. Agent workflows must include document-reading as a prerequisite to execution.  
**Rejected alternatives:**  
- Using source code as the sole source of truth — rejected because the repository explicitly places requirements authority in `forge-docs/`.  
- Allowing the agent to infer behavior from tests alone — rejected because tests may be incomplete and do not replace documented requirements.  
- Keeping subsystem-local rules outside the documented repository standards — rejected because it creates drift from the defined governance model.

## [Read critical files before modifying subsystem behavior]
**Status:** Accepted  
**Context:** The repository identifies a set of critical files whose behavior impacts generation, orchestration, GitHub I/O, security boundaries, and CI workflow creation. These files are high-risk change points for CraftedDevAgent.  
**Decision:** Require explicit review of `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` before making changes that could affect CraftedDevAgent behavior.  
**Consequences:** Modifications must account for cross-cutting effects in generation, orchestration, path validation, GitHub interaction, and workflow generation. Developers cannot safely change adjacent code paths without understanding these files.  
**Rejected alternatives:**  
- Treating all files as equally important — rejected because the repository explicitly marks these as critical and higher impact.  
- Allowing changes without dependency review — rejected because it increases regression risk across the pipeline and security boundary.  
- Embedding duplicated logic outside these files to avoid touching them — rejected because it would fragment core behavior and weaken guarantees.

## [Preserve the staged build pipeline as the governing execution model]
**Status:** Accepted  
**Context:** The README defines a staged build pipeline, including parse/lint/import validation, fix loops, test and CI execution, and an operator gate before merge. CraftedDevAgent must fit inside that pipeline rather than bypass it.  
**Decision:** Implement CraftedDevAgent behavior as a participant in the repository’s staged build pipeline and never bypass required stages, validation steps, or merge gates.  
**Consequences:** Generated changes must flow through syntax validation, linting, import checks, test/fix loops, CI, and operator approval. Subsystem logic must expose state in ways compatible with pipeline orchestration and checkpointing.  
**Rejected alternatives:**  
- Running a simplified subsystem-local pipeline — rejected because it would create inconsistent quality gates.  
- Skipping validation for small or “safe” changes — rejected because the documented pipeline applies universally.  
- Merging automatically after local success — rejected because operator approval is an explicit gate.

## [Enforce cyclomatic complexity maximum of 15 per stage]
**Status:** Accepted  
**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is specifically called out as strictly enforcing this limit. CraftedDevAgent must not introduce orchestration logic that violates this architectural constraint.  
**Decision:** Keep each CraftedDevAgent pipeline stage and stage-level orchestration function at cyclomatic complexity 15 or below; refactor branching logic rather than exceeding the limit.  
**Consequences:** Complex behavior must be decomposed into smaller functions or strategy objects. Stage implementations must remain auditable and maintainable. Reviews should reject changes that centralize excessive branching in one stage.  
**Rejected alternatives:**  
- Allowing exceptions for “core orchestration” code — rejected because the limit is stated as universal and strictly enforced.  
- Measuring complexity only at file level — rejected because the requirement applies per stage.  
- Deferring complexity reduction until later refactoring — rejected because it undermines the active constraint and makes enforcement unreliable.

## [Checkpoint every state transition, including per-PR states]
**Status:** Accepted  
**Context:** The pipeline documentation requires that every state transition be checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. CraftedDevAgent must preserve recoverability and traceability across runs.  
**Decision:** Persist a checkpoint for every CraftedDevAgent state transition, including all per-PR progression states and gate decisions.  
**Consequences:** The subsystem must support restart, audit, and partial recovery without recomputing hidden state. State changes cannot be ephemeral-only. Logging alone is insufficient unless paired with durable checkpoint state.  
**Rejected alternatives:**  
- Checkpointing only major milestones — rejected because the requirement covers every transition.  
- Relying on in-memory state during one run — rejected because it breaks recovery and observability.  
- Using Git history as the only state record — rejected because not all pipeline states correspond to commits.

## [Record every gate decision as durable audit data]
**Status:** Accepted  
**Context:** The build pipeline specifies that every gate decision is recorded. CraftedDevAgent includes automated and operator-mediated progression, so gate outcomes must be inspectable after the fact.  
**Decision:** Persist each gate decision, including approvals, rejections, and corrections, as durable audit data linked to the relevant stage or PR state.  
**Consequences:** The subsystem must expose enough metadata to reconstruct why work progressed or stopped. Operator interactions are part of the system record and cannot remain informal or external-only.  
**Rejected alternatives:**  
- Keeping gate decisions only in transient logs — rejected because logs are not sufficient durable audit state.  
- Recording only negative decisions — rejected because complete approval lineage is required.  
- Leaving operator decisions in GitHub comments alone — rejected because auditability must remain available within subsystem state, not just external tools.

## [Route all write paths through the path security boundary]
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. CraftedDevAgent performs file generation and modification, making path handling a primary attack and correctness surface.  
**Decision:** Validate and authorize every filesystem write performed by CraftedDevAgent through `src/path_security.py`; do not write directly to disk through unvetted paths.  
**Consequences:** New file-writing utilities must integrate with the shared path security mechanism. Direct `open()`/write flows that bypass path validation are prohibited for repository mutations. Security review should focus on preserving this boundary.  
**Rejected alternatives:**  
- Performing local path normalization within each caller — rejected because it duplicates security logic and weakens the central boundary.  
- Trusting repository-relative paths from upstream components — rejected because upstream data may be malformed or adversarial.  
- Applying path checks only for user-provided paths — rejected because all writes are required to cross the security boundary.

## [Centralize all GitHub I/O in github_tools with path validation, rate limiting, and SHA protocol]
**Status:** Accepted  
**Context:** `src/github_tools.py` is designated as the location for all GitHub I/O and is responsible for path validation, rate limiting, and SHA protocol handling. CraftedDevAgent must interact with GitHub safely and consistently.  
**Decision:** Perform all CraftedDevAgent GitHub reads and writes exclusively through `src/github_tools.py`, preserving its path validation, rate limiting, and SHA-based update semantics.  
**Consequences:** Subsystem code must not call GitHub APIs directly when repository content or PR state is involved. Concurrency, update safety, and API hygiene remain centralized. Changes to GitHub behavior must be made in one place.  
**Rejected alternatives:**  
- Using direct REST or GraphQL calls from subsystem code — rejected because it bypasses shared safety and consistency controls.  
- Implementing a second GitHub helper for agent-specific needs — rejected because it would duplicate logic and risk protocol divergence.  
- Ignoring SHA protocol on writes for simplicity — rejected because content updates require concurrency-safe semantics.

## [Keep consensus generation changes aligned with the shared core loop]
**Status:** Accepted  
**Context:** `src/consensus.py` is identified as the core generation loop affecting every PR the agent builds. CraftedDevAgent behavior that changes generation quality or control flow must remain compatible with this shared mechanism.  
**Decision:** Integrate generation-related CraftedDevAgent changes through the shared consensus loop in `src/consensus.py` rather than introducing parallel generation pipelines.  
**Consequences:** Prompting, synthesis, and generation control should remain coherent across PRs. Improvements or regressions in generation behavior will affect all agent-created PRs, so changes require high scrutiny and broad testing.  
**Rejected alternatives:**  
- Building a subsystem-specific generation loop — rejected because it fragments behavior and bypasses the shared core.  
- Forking consensus logic for experimentation — rejected because it creates maintenance and behavior drift.  
- Embedding generation decisions directly in orchestration stages — rejected because it mixes concerns and bypasses the designated generation core.

## [Generate CI workflows through the shared workflow generator]
**Status:** Accepted  
**Context:** `src/ci_workflow.py` is a critical file responsible for generating CI workflows, and the repository defines `crafted-ci.yml` for Ubuntu and `crafted-ci-macos.yml` for Swift. CraftedDevAgent must use the standardized CI workflow path.  
**Decision:** Generate or modify CI workflow definitions for CraftedDevAgent only through `src/ci_workflow.py`, preserving the standard Linux and macOS workflow split.  
**Consequences:** CI changes stay consistent with repository conventions and platform requirements. The subsystem must not emit ad hoc workflow files or encode workflow YAML generation in unrelated modules.  
**Rejected alternatives:**  
- Writing GitHub Actions YAML directly from subsystem code — rejected because it bypasses the critical shared generator.  
- Collapsing all CI into a single workflow — rejected because the repository explicitly distinguishes Ubuntu and macOS workflows.  
- Letting generated PRs define custom CI behavior independently — rejected because it weakens standard validation guarantees.

## [Respect repository layout boundaries across Python backend and Swift shell]
**Status:** Accepted  
**Context:** The repository layout separates Python backend implementation under `src/`, the Swift/SwiftUI application shell under `Crafted/`, XCTest suites under `CraftedTests/`, and pytest suites under `tests/`. CraftedDevAgent spans development tasks and must not blur these boundaries.  
**Decision:** Place CraftedDevAgent backend logic in `src/`, limit macOS shell changes to `Crafted/`, and add tests only to the corresponding platform-appropriate test directories.  
**Consequences:** Implementation remains discoverable and aligned with language/runtime boundaries. Cross-language coupling must occur through defined interfaces rather than arbitrary code placement. Build and test tooling can rely on stable project structure.  
**Rejected alternatives:**  
- Co-locating Python and Swift support code in one subsystem folder — rejected because it conflicts with the established repository layout.  
- Putting backend tests next to implementation files by default — rejected because the repository already defines `tests/` as the Python test location.  
- Embedding agent logic in the app shell for convenience — rejected because backend implementation belongs in `src/`.

## [Honor the operator gate before merge]
**Status:** Accepted  
**Context:** The pipeline explicitly defines Stage 6 as a gate where the operator approves or corrects before merge. CraftedDevAgent may automate many stages, but final merge authority remains human-mediated.  
**Decision:** Require operator approval or explicit operator correction before merging CraftedDevAgent-produced changes; do not auto-merge solely on automated success.  
**Consequences:** Merge completion depends on human review workflows. The subsystem must surface artifacts needed for operator decision-making and must tolerate pause/resume at the gate.  
**Rejected alternatives:**  
- Fully autonomous merge after tests and CI pass — rejected because it violates the documented gate.  
- Approval by heuristic confidence score instead of operator review — rejected because the required gate is human, not statistical.  
- Treating low-risk changes as exempt — rejected because no exemption is specified.

## [Preserve failure-aware fix-loop behavior instead of generic retries]
**Status:** Accepted  
**Context:** The build pipeline defines a fix loop with up to 20 pytest attempts and a failure-type-aware strategy. CraftedDevAgent must respond intelligently to failures rather than repeatedly re-running identical steps.  
**Decision:** Implement fix-loop behavior using bounded retries and failure-type-aware remediation strategies, with a hard maximum of 20 pytest attempts.  
**Consequences:** Retry logic must classify failures and adapt remediation accordingly. Infinite or unbounded repair loops are prohibited. The subsystem must expose enough failure context to support categorized response behavior.  
**Rejected alternatives:**  
- Retrying until success with no cap — rejected because the pipeline defines a maximum of 20 attempts.  
- Using naive identical retries — rejected because the strategy must be failure-type-aware.  
- Aborting after the first failure — rejected because the pipeline explicitly includes a repair loop.