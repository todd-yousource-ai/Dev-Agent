# DECISIONS.md

## [Use the documented repository layout as a hard architectural boundary]
**Status:** Accepted

**Context:** ForgeAgent operates inside a repository with explicitly separated concerns: `forge-docs/` is the source of truth for TRDs/PRDs, `forge-standards/` contains architectural constraints and conventions, `src/` contains the Python backend, `Crafted/` and `CraftedTests/` contain the macOS shell and tests, and `tests/` contains the Python test suite. The TRDs and README define this layout as part of the system design, not as a convenience.

**Decision:** Treat the documented repository layout as immutable architecture. Implement ForgeAgent so that:
- requirements are read from `forge-docs/`,
- implementation lives in `src/`,
- standards and generated rules are read from `forge-standards/`,
- Swift/macOS shell changes are confined to `Crafted/` and `CraftedTests/`,
- Python tests live in `tests/`,
- no subsystem writes design-source content into ad hoc locations.

**Consequences:** Implementation must not invent parallel directories for specs, generated standards, backend code, or tests. File discovery, planning, and write operations must be path-aware and repository-layout-aware. Any automation that generates or edits files must target only the approved subtree for that artifact type.

**Rejected alternatives:**  
- **Allow flexible directory discovery at runtime:** Rejected because it weakens determinism and increases the chance of writing to incorrect locations.  
- **Co-locate generated artifacts beside source files opportunistically:** Rejected because the repository structure already encodes ownership and review boundaries.  
- **Treat `forge-docs/` as optional reference material:** Rejected because TRDs/PRDs are explicitly the source of truth and must be consulted before building.

## [Read source-of-truth documents before modifying implementation]
**Status:** Accepted

**Context:** The repository explicitly states that all TRDs and PRDs live in `forge-docs/` and must be read before building. Several implementation files are also marked critical because changes there affect all PR generation, pipeline orchestration, GitHub I/O, security boundaries, and CI workflow generation.

**Decision:** Require ForgeAgent to read relevant documents in `forge-docs/` and inspect designated critical files before making implementation changes. At minimum, any change that affects generation, orchestration, GitHub access, path validation, or CI behavior must review the corresponding critical file first.

**Consequences:** Planning must include a document/context acquisition step before code edits. The agent cannot safely make broad changes based only on local assumptions or partial code inspection. This increases upfront work but prevents architectural drift and accidental violation of system constraints.

**Rejected alternatives:**  
- **Rely on codebase inspection alone:** Rejected because key behavior and constraints are specified in TRDs/PRDs, not only in code.  
- **Read only files directly touched by a patch:** Rejected because critical subsystem files define cross-cutting guarantees that may be affected indirectly.  
- **Make document-reading optional for small changes:** Rejected because even small changes in core orchestration or security-sensitive files can have system-wide impact.

## [Preserve `src/consensus.py` as the core generation control point]
**Status:** Accepted

**Context:** `src/consensus.py` is identified as the core generation loop, and changes there affect every PR the agent builds. This file therefore acts as a central behavioral boundary for generation quality, coordination, and output consistency.

**Decision:** Keep the core generation loop centralized in `src/consensus.py`. Route generation-policy changes, sequencing decisions, and consensus-related behavior through this file rather than duplicating generation control logic across multiple modules.

**Consequences:** New generation features must integrate with the existing consensus control point instead of introducing competing orchestration paths. This constrains implementation to preserve a single authoritative generation loop, improving traceability and reducing divergence across PR creation flows.

**Rejected alternatives:**  
- **Distribute generation logic across feature-specific modules:** Rejected because it would fragment the core PR-building behavior and make systemic changes difficult to reason about.  
- **Create a second orchestration path for experimental generation:** Rejected because parallel control paths would cause inconsistency and complicate correctness and checkpointing.  
- **Move consensus behavior into UI or GitHub integration layers:** Rejected because those layers are not the proper authority for generation control.

## [Preserve `src/build_director.py` as the pipeline orchestrator and enforce complexity limits]
**Status:** Accepted

**Context:** `src/build_director.py` is identified as the pipeline orchestration point, and the system requires that every stage maintain a maximum cyclomatic complexity of 15. The build pipeline includes multiple staged transitions and fix loops that must remain understandable and auditable.

**Decision:** Centralize pipeline orchestration in `src/build_director.py` and enforce a maximum cyclomatic complexity of 15 for every stage implementation. Decompose logic into helper functions or modules when a stage risks exceeding that threshold.

**Consequences:** Stage logic must be written in small, composable units. The implementation cannot hide complex branching inside a monolithic stage function. Refactors are required when new behavior would push orchestration paths beyond the complexity cap. This improves maintainability and auditability at the cost of additional structure.

**Rejected alternatives:**  
- **Allow selective exceptions to the complexity limit for orchestrators:** Rejected because the orchestration layer is exactly where complexity must remain controlled.  
- **Enforce the complexity limit only at file level:** Rejected because the requirement applies to every stage, not just aggregate module complexity.  
- **Split orchestration across unrelated modules without a central director:** Rejected because it weakens stage ownership and obscures state transitions.

## [Treat GitHub I/O as a single controlled boundary in `src/github_tools.py`]
**Status:** Accepted

**Context:** `src/github_tools.py` is designated as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. GitHub interactions are operationally sensitive and must behave consistently.

**Decision:** Route all GitHub reads and writes through `src/github_tools.py`. Do not perform direct GitHub API access from other modules. Implement and preserve path validation, rate limiting, and SHA-aware update semantics at this boundary.

**Consequences:** Other modules must depend on abstractions provided by `src/github_tools.py` rather than importing GitHub clients directly. This constrains implementation but creates a single point for auditing correctness, retry policy, write safety, and API contract handling.

**Rejected alternatives:**  
- **Allow direct GitHub API calls from feature modules for convenience:** Rejected because it would bypass shared safety checks and create inconsistent update behavior.  
- **Separate rate limiting and SHA handling into optional wrappers:** Rejected because these are not optional concerns; they are mandatory parts of safe GitHub I/O.  
- **Embed path validation in callers instead of the GitHub boundary:** Rejected because validation must be consistently enforced at the point of I/O.

## [Enforce `src/path_security.py` as the mandatory write-path security boundary]
**Status:** Accepted

**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. File writes are a primary risk surface for repository integrity and must be constrained to approved locations.

**Decision:** Require every filesystem write performed by ForgeAgent to pass through `src/path_security.py`. Do not permit direct writes, path joins, or unchecked path normalization in callers when creating or modifying repository files.

**Consequences:** All write-capable code must use path-security-approved APIs before touching disk. This constrains implementation patterns, especially in utility code and integrations, but ensures uniform enforcement of repository boundaries and mitigates path traversal or accidental out-of-scope writes.

**Rejected alternatives:**  
- **Validate paths only in high-level orchestration code:** Rejected because lower-level utilities could still bypass the protection.  
- **Rely on developer discipline rather than a mandatory boundary:** Rejected because security guarantees must be enforced mechanically.  
- **Validate only external-input-derived paths:** Rejected because internal path construction bugs can also violate repository boundaries.

## [Generate CI workflows through `src/ci_workflow.py` as the sole authority]
**Status:** Accepted

**Context:** `src/ci_workflow.py` is designated as the workflow generator, and the README specifies CI targets including `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. CI generation must remain consistent with repository conventions and platform-specific requirements.

**Decision:** Use `src/ci_workflow.py` as the only authority for generating CI workflow definitions. Ensure Linux-oriented workflow output targets `crafted-ci.yml` on `ubuntu-latest` and Swift/macOS workflow output targets `crafted-ci-macos.yml`.

**Consequences:** Workflow creation and updates must not be scattered across templates, ad hoc scripts, or unrelated modules. CI behavior becomes easier to reason about and review, but all workflow feature work must be implemented through the dedicated generator.

**Rejected alternatives:**  
- **Commit hand-maintained workflow files without generator ownership:** Rejected because it allows drift from the system’s intended pipeline model.  
- **Generate workflows in multiple modules based on language or platform:** Rejected because CI policy would fragment across implementations.  
- **Use a single workflow for all platforms:** Rejected because the documented design explicitly distinguishes general CI from Swift/macOS CI needs.

## [Implement the build pipeline as explicit staged execution]
**Status:** Accepted

**Context:** The README defines a staged build pipeline, including generation, validation, a fix loop, test and CI execution, and a human gate before merge. The pipeline is not informal; it is a required control flow for how ForgeAgent produces changes.

**Decision:** Implement ForgeAgent’s work as explicit pipeline stages, including:
- validation steps such as `ast.parse`, `ruff`, and import checks,
- a fix loop with up to 20 pytest attempts using failure-type-aware strategy,
- CI execution,
- an operator gate before merge.

**Consequences:** The subsystem must model and execute work in ordered stages rather than as an undifferentiated “run until done” loop. Recovery behavior must be stage-aware, and validation/fix actions must be attached to the documented points in the pipeline. This increases orchestration rigor and observability.

**Rejected alternatives:**  
- **Use a single iterative repair loop without named stages:** Rejected because it obscures progress, policy enforcement, and checkpoint semantics.  
- **Treat lint, import, and parse validation as optional optimizations:** Rejected because they are explicitly part of the pipeline.  
- **Allow unlimited test-fix retries:** Rejected because the design sets a 20-attempt cap and requires bounded recovery behavior.

## [Checkpoint every pipeline state transition, including per-PR substates]
**Status:** Accepted

**Context:** The system requires that every state transition be checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This is essential for recoverability, observability, and operator trust.

**Decision:** Persist a checkpoint at every pipeline state transition and every documented per-PR substate transition. Do not skip checkpoints for “fast” transitions or collapse multiple transitions into one persisted event.

**Consequences:** State management must be explicit and durable. Recovery logic can resume from known points, and operators can audit what happened. This adds persistence overhead and schema discipline, but it prevents opaque execution and reduces ambiguity during retries or failures.

**Rejected alternatives:**  
- **Checkpoint only major milestones:** Rejected because the requirement explicitly includes every transition, not just selected ones.  
- **Keep transient state in memory until the end of a stage:** Rejected because failures would erase execution history and hinder safe resume.  
- **Log transitions without durable checkpoints:** Rejected because logs alone do not provide reliable resumability or authoritative workflow state.

## [Make gate decisions explicit and human-controlled before merge]
**Status:** Accepted

**Context:** The pipeline includes a gate where the operator approves or corrects before merge, and every gate decision must be recorded. The system therefore requires a human-in-the-loop control point rather than autonomous merge authority.

**Decision:** Require explicit operator approval or correction before merge, and record every gate decision as part of pipeline state. ForgeAgent must not self-authorize merges after passing automated checks.

**Consequences:** Merge completion depends on human review even when generation, tests, and CI succeed. The subsystem must support paused execution, surfaced evidence for review, and durable recording of the gate outcome. This reduces full automation but is necessary for trust, oversight, and controlled rollout.

**Rejected alternatives:**  
- **Auto-merge when tests and CI pass:** Rejected because the documented process requires operator approval or correction before merge.  
- **Treat gate decisions as informal comments rather than structured state:** Rejected because gate decisions must be recorded.  
- **Allow bypass of the gate for low-risk changes:** Rejected because no such exception is documented.

## [Use failure-type-aware repair within a bounded pytest fix loop]
**Status:** Accepted

**Context:** The pipeline specifies a fix loop with pytest capped at 20 attempts and requiring a failure-type-aware strategy. Repair behavior must therefore be bounded and informed by failure classification, not blind repetition.

**Decision:** Implement the pytest repair loop with a hard maximum of 20 attempts and choose repair actions based on failure type. Do not retry indiscriminately with identical behavior after each failure.

**Consequences:** The subsystem must classify failures sufficiently to select targeted remediation strategies. Retry accounting becomes part of orchestration state. The implementation cannot rely on endless or naive retries, which improves efficiency and predictability but requires more disciplined error handling.

**Rejected alternatives:**  
- **Use unlimited retries until tests pass:** Rejected because the design explicitly caps attempts at 20.  
- **Retry with the same generic fix strategy each time:** Rejected because the system requires failure-type-aware handling.  
- **Abort after the first failure without repair attempts:** Rejected because the pipeline explicitly includes a fix loop.

## [Respect the documented root-view decision tree for macOS shell integration]
**Status:** Accepted

**Context:** TRD-1 defines a root-view decision tree for the Crafted macOS application shell, with onboarding state determining which container or screen is shown. ForgeAgent may need to modify or generate code affecting the app shell, so these navigation rules must remain stable.

**Decision:** Preserve and implement macOS shell changes in accordance with the documented root-view decision tree. In particular, onboarding-state-driven routing must remain the authority for initial view selection rather than ad hoc navigation logic.

**Consequences:** Changes in `Crafted/` that affect startup flow must conform to the existing decision tree and state model. The agent cannot introduce alternate startup routing patterns that bypass onboarding-state evaluation. This preserves UX consistency and prevents regressions in app entry behavior.

**Rejected alternatives:**  
- **Replace the root decision tree with imperative navigation side effects:** Rejected because the TRD specifies a state-driven root-view model.  
- **Infer initial view from scattered feature flags or persisted values independently:** Rejected because it would duplicate and potentially contradict the onboarding-state authority.  
- **Treat UI shell behavior as outside ForgeAgent constraints:** Rejected because the repository and TRDs explicitly include the Swift shell as part of the system.

## [Do not delete or bypass generated standards artifacts]
**Status:** Accepted

**Context:** The repository layout identifies `forge-standards/build_rules.md` as auto-generated and explicitly marked “do not delete.” Standards artifacts are part of the enforcement surface for repository-wide behavior.

**Decision:** Preserve generated standards artifacts, including `forge-standards/build_rules.md`, and update them only through their intended generation mechanism. Do not delete, manually bypass, or silently replace them.

**Consequences:** ForgeAgent must treat generated standards files as controlled outputs with special handling. Manual edits or cleanup routines must not remove them. This constrains repository maintenance behavior but protects important derived policy artifacts from accidental loss or drift.

**Rejected alternatives:**  
- **Allow manual deletion and regeneration on demand:** Rejected because the repository explicitly marks the artifact as not to be deleted.  
- **Inline build rules elsewhere and deprecate the generated file informally:** Rejected because doing so would create ambiguity about the active standards source.  
- **Treat generated standards files as disposable cache:** Rejected because they are repository-visible policy artifacts, not transient build outputs.