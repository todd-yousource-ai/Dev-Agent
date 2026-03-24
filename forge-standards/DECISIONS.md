# DECISIONS.md

## [ForgeAgent repository boundaries and source-of-truth]
**Status:** Accepted

**Context:** ForgeAgent operates inside a repository with strict separation between specifications, standards, backend code, and application shell. The documented repository layout defines `forge-docs/` as the location for all TRDs and PRDs, and `forge-standards/` as the location for architecture and implementation constraints. The backend implementation lives in `src/`, while the macOS shell lives in `Crafted/`. This separation is necessary to keep implementation aligned with governing documents and to prevent subsystem logic from drifting away from approved requirements.

**Decision:** Treat `forge-docs/` and `forge-standards/` as authoritative inputs to ForgeAgent design and implementation. Implement ForgeAgent runtime code only under `src/` unless a requirement explicitly belongs to the Swift shell in `Crafted/`. Do not embed product requirements, architectural policy, or mutable standards directly in code when they belong in documentation.

**Consequences:** ForgeAgent implementations must read and conform to the documents before changing behavior. Cross-cutting rules must be represented in standards documents, not redefined ad hoc in code. Backend changes cannot silently redefine requirements owned by TRDs or standards. Swift UI concerns remain outside the ForgeAgent backend unless an explicit integration boundary is defined.

**Rejected alternatives:**  
- Storing subsystem-specific requirements only in code comments: rejected because comments are not the approved source of truth and drift easily.  
- Allowing ForgeAgent logic to span `src/` and `Crafted/` opportunistically: rejected because it weakens subsystem boundaries and complicates ownership.  
- Treating README fragments as sufficient authority over TRDs and standards: rejected because README content is supportive, not the governing specification set.

## [Critical-file change discipline]
**Status:** Accepted

**Context:** Several files are explicitly marked as critical because they define global behavior, security boundaries, and orchestration contracts: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes to these files can affect all pull requests, all repository writes, and CI behavior across the system.

**Decision:** Require ForgeAgent changes touching designated critical files to preserve their global contracts and to be evaluated as system-level modifications rather than local refactors. Do not alter these files incidentally while implementing unrelated functionality. Any modification must maintain compatibility with the documented role of the file.

**Consequences:** Work in these files must be deliberate, narrowly scoped, and validated against subsystem-wide impact. Feature work should prefer extension points and composition before editing critical-path code. Reviews must treat such changes as high-risk and verify they do not violate security, orchestration, or GitHub interaction guarantees.

**Rejected alternatives:**  
- Allowing opportunistic cleanup in critical files during unrelated work: rejected because it increases regression risk in global paths.  
- Treating all source files as equal-risk: rejected because the documents identify explicit security and orchestration choke points.  
- Splitting critical behavior across many new files without preserving clear ownership: rejected because it hides system invariants and complicates review.

## [Pipeline stages are explicit and ordered]
**Status:** Accepted

**Context:** The build pipeline is defined as a staged process, including generation, validation, fix loops, test and CI, and an approval gate. The README specifies ordered stages and ties them to operational behavior. ForgeAgent depends on deterministic progression through these stages to support traceability, retries, and operator control.

**Decision:** Implement ForgeAgent pipeline execution as explicit ordered stages with no implicit skipping or reordering. Preserve the documented stage semantics, including the validation sequence and the presence of a failure-aware fix loop before CI gating.

**Consequences:** Pipeline orchestration must expose stage boundaries as first-class transitions. Implementations cannot collapse multiple stages into a monolithic run method if doing so hides state transitions or bypasses required validation. Retry behavior must remain within the intended stage structure rather than becoming free-form recursive execution.

**Rejected alternatives:**  
- A single end-to-end pipeline function with internal branching: rejected because it obscures checkpoints and weakens recoverability.  
- Dynamically reordering stages for performance: rejected because correctness and auditability take precedence over speculative optimization.  
- Skipping intermediate validation when prior runs succeeded: rejected because each run must satisfy the defined control flow and quality gates.

## [Cyclomatic complexity cap of 15 per stage implementation]
**Status:** Accepted

**Context:** The pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is specifically called out as enforcing this limit strictly. This is a design constraint intended to preserve maintainability and reduce orchestration fragility.

**Decision:** Keep each ForgeAgent pipeline stage implementation at cyclomatic complexity 15 or below. Refactor using helpers, strategy objects, or smaller composable functions rather than allowing stage logic to exceed the limit.

**Consequences:** New behavior must be decomposed instead of added as nested branching inside stage methods. Complexity budgeting becomes part of design review. The subsystem may require more files or helper abstractions, but stage controllers remain understandable and testable.

**Rejected alternatives:**  
- Allowing temporary exceptions above 15 for “core” orchestration code: rejected because the limit exists specifically to constrain orchestration complexity.  
- Measuring complexity only at module level: rejected because the requirement is stage-specific.  
- Relying on reviewer judgment without an explicit cap: rejected because subjective enforcement is inconsistent and degrades over time.

## [Checkpoint every state transition]
**Status:** Accepted

**Context:** The pipeline documentation requires that every state transition be checkpointed, including per-PR states such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This requirement supports resumability, auditability, and post-failure diagnosis.

**Decision:** Persist a checkpoint at every ForgeAgent state transition, including intermediate per-PR transitions and gate outcomes. Do not rely solely on in-memory state for progress tracking across pipeline stages.

**Consequences:** Implementations must define durable state recording around transitions. Recovery logic must resume from checkpoints rather than infer state heuristically from repository side effects alone. State progression becomes observable and testable. Writes must be ordered so that persisted state reflects actual completed transitions, not intended transitions.

**Rejected alternatives:**  
- Checkpointing only major milestones such as “started” and “completed”: rejected because it loses the granularity explicitly required.  
- Reconstructing state entirely from Git history and CI status: rejected because not all operational transitions are encoded there.  
- Using only process memory or logs as checkpoints: rejected because they are insufficient for durable recovery and audit.

## [Gate decisions are mandatory and persisted]
**Status:** Accepted

**Context:** The build pipeline includes a gate in which an operator approves or corrects before merge, and the documentation states that every gate decision is persisted. ForgeAgent must therefore support human control as a first-class part of execution, not as an optional afterthought.

**Decision:** Require an explicit persisted gate decision before merge-adjacent progression. Represent operator approval or correction as durable state in the ForgeAgent workflow, and do not auto-merge or auto-advance past the gate without that recorded decision.

**Consequences:** Fully autonomous merge completion is out of scope for the standard flow unless separately authorized by documented policy. Systems integrating ForgeAgent must expose gate state and decision capture. Audit records must show whether a human approved or redirected the workflow.

**Rejected alternatives:**  
- Auto-approving when all tests and CI pass: rejected because the documented gate requires operator approval or correction.  
- Treating gate decisions as ephemeral UI events: rejected because persistence is explicitly required.  
- Encoding approval only in GitHub comments without internal state: rejected because comments are not a reliable workflow state store.

## [Failure-aware fix loop with bounded retries]
**Status:** Accepted

**Context:** The pipeline documentation defines a fix loop that runs `pytest` with up to 20 attempts and uses a failure-type-aware strategy. This implies that retries are intentional, bounded, and informed by categorized failures rather than blind repetition.

**Decision:** Implement the ForgeAgent fix loop as a bounded retry mechanism with a maximum of 20 attempts and behavior that varies by failure type. Do not use infinite retries, unbounded recursion, or a generic “rerun until green” approach.

**Consequences:** Failure classification becomes a required input to remediation logic. The subsystem must surface attempt counts and terminal exhaustion states. Retry logic should distinguish transient, deterministic, and structural failures where possible. Exhausting the retry budget must produce a clear stoppage state rather than silent abandonment.

**Rejected alternatives:**  
- Unlimited retries until tests pass: rejected because it risks nontermination and contradicts the documented cap.  
- A fixed retry loop with identical behavior on every failure: rejected because the design requires failure-type-aware strategy.  
- No automatic fix loop at all: rejected because remediation is an explicit stage of the pipeline.

## [GitHub I/O is centralized in github_tools]
**Status:** Accepted

**Context:** `src/github_tools.py` is identified as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. Concentrating external repository operations in one module is necessary to maintain consistency and enforce repository safety rules.

**Decision:** Route all ForgeAgent GitHub reads and writes through `src/github_tools.py` or a narrow abstraction that delegates to it. Do not perform direct ad hoc GitHub API calls elsewhere in the subsystem.

**Consequences:** Rate limiting, SHA handling, and repository mutation rules remain consistent across the codebase. Testing can mock a single integration boundary. New GitHub operations must extend the central toolset rather than duplicating client logic in pipeline stages or agents.

**Rejected alternatives:**  
- Letting each stage call the GitHub API directly: rejected because it duplicates protocol logic and weakens enforcement.  
- Creating multiple parallel GitHub helper modules by feature area: rejected because it fragments repository I/O policy.  
- Bypassing centralized tooling for “simple” read-only operations: rejected because consistency and future policy enforcement matter even for reads.

## [All write paths must pass through path_security]
**Status:** Accepted

**Context:** `src/path_security.py` is explicitly identified as the security boundary, and every write path must pass through it. This is a hard constraint from the critical-files guidance and a central defense against unsafe filesystem access.

**Decision:** Require every ForgeAgent filesystem write path to be validated through `src/path_security.py` before execution. Do not write files, create directories, or modify repository content through unchecked paths.

**Consequences:** Any component that produces files must integrate with the path security boundary. Convenience writes using raw path concatenation are disallowed. Refactors must preserve the validation call path. Security review can focus on one enforced mechanism instead of searching for scattered safeguards.

**Rejected alternatives:**  
- Validating only user-provided paths: rejected because generated or internal paths can also become unsafe through bugs or composition errors.  
- Trusting repository-relative joins without centralized validation: rejected because local assumptions are error-prone and inconsistent.  
- Performing security checks only at API boundaries but not at write time: rejected because downstream path transformations can invalidate earlier assumptions.

## [Consensus loop changes are treated as globally impactful]
**Status:** Accepted

**Context:** `src/consensus.py` is identified as the core generation loop, and changes there affect every PR the agent builds. This makes consensus behavior a subsystem-wide contract rather than an isolated implementation detail.

**Decision:** Design ForgeAgent features so that modifications to `src/consensus.py` are minimized, isolated, and justified as changes to global generation behavior. Prefer extending inputs, strategies, or plugin-like decision points over rewriting the core loop.

**Consequences:** Team members must treat consensus changes as high-blast-radius modifications requiring broad validation. Feature-specific logic should not be hardcoded into the global generation loop when narrower extension points are available. Regression testing for consensus changes must cover representative PR generation paths.

**Rejected alternatives:**  
- Embedding feature-specific branching directly into the core loop: rejected because it causes the global path to accumulate unrelated conditions.  
- Treating consensus changes as local implementation tweaks: rejected because the file’s documented role makes them system-wide.  
- Forking multiple independent consensus loops by workflow type: rejected because it fragments core behavior and increases maintenance cost.

## [CI workflow generation remains explicit and platform-specific]
**Status:** Accepted

**Context:** The pipeline documentation states that testing and CI use `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is the generator for these workflows. This implies that ForgeAgent must preserve platform-specific CI behavior rather than collapsing all jobs into a single generic workflow.

**Decision:** Generate and maintain explicit CI workflows that preserve the documented platform split: Ubuntu-based CI for general crafted pipeline work and macOS-specific CI for Swift-related execution. Keep workflow generation centralized in `src/ci_workflow.py`.

**Consequences:** Swift and Python/backend concerns remain appropriately separated in CI. Platform selection is not left to ad hoc job conditionals scattered across the repository. Changes to CI behavior must be reflected through the generator and verified against both workflow targets.

**Rejected alternatives:**  
- A single unified workflow for all languages and platforms: rejected because the documented design explicitly separates Ubuntu and macOS responsibilities.  
- Hand-editing generated workflows as the primary maintenance path: rejected because generation is centralized in a critical file.  
- Running Swift validation only on Ubuntu via cross-platform tooling: rejected because the design specifies a macOS workflow for Swift.

## [ForgeAgent must respect the macOS shell boundary]
**Status:** Accepted

**Context:** The repository contains a Swift/SwiftUI macOS application shell under `Crafted/`, with its own documented root view decision tree. ForgeAgent is a backend subsystem and should not absorb UI state-machine concerns that belong to the macOS shell.

**Decision:** Keep ForgeAgent concerns in the backend runtime and integration layer; do not reimplement or own the macOS shell’s root view decision tree or onboarding state logic inside ForgeAgent. Integrate through clear APIs and persisted state rather than duplicated UI control flow.

**Consequences:** Backend and UI can evolve with stable interfaces. ForgeAgent may provide status and gate information, but the shell remains responsible for view routing and onboarding presentation. UI state duplication in Python is disallowed unless a documented synchronization contract requires a shared representation.

**Rejected alternatives:**  
- Mirroring the Swift root view decision tree in backend logic: rejected because it duplicates ownership and risks drift.  
- Moving onboarding flow decisions into ForgeAgent for convenience: rejected because those decisions belong to the application shell.  
- Allowing backend state names to implicitly define UI navigation without an interface contract: rejected because it creates hidden coupling.