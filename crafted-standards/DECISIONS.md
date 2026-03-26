## [Use forge-docs as the authoritative requirements source]
**Status:** Accepted

**Context:** CraftedAgent operates in a repository where all TRDs and PRDs are explicitly centralized under `forge-docs/`. The subsystem must be constrained by documented requirements before implementation changes are made, or behavior will drift from the intended product and architecture.

**Decision:** Treat `forge-docs/` as the mandatory source of truth for subsystem requirements. Read relevant TRDs and PRDs before implementing or modifying CraftedAgent behavior.

**Consequences:** Implementation work must be traceable to documents in `forge-docs/`. Features or behavioral changes that are not grounded in those documents should not be introduced. Development workflow and review must assume requirements come from documentation first, not inferred code behavior.

**Rejected alternatives:**  
- Use current code behavior as the primary specification — rejected because it allows undocumented drift and entrenches accidental behavior.  
- Distribute requirements across source comments and ad hoc notes — rejected because it fragments the source of truth and weakens reviewability.  
- Treat `forge-standards/` as equivalent to `forge-docs/` for product requirements — rejected because standards constrain implementation, but TRDs/PRDs define the intended system behavior.

## [Protect critical files as subsystem control points]
**Status:** Accepted

**Context:** Several files are identified as critical because changes to them affect core generation, orchestration, security boundaries, GitHub I/O, and CI workflow generation. CraftedAgent must not modify these casually or without understanding their systemic impact.

**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as critical control points. Read and understand their role before modifying them, and apply a higher change bar to any edits.

**Consequences:** Changes in these files require tighter review, explicit justification, and validation against subsystem-wide behavior. Implementers must assume edits can affect every generated PR, repository write safety, CI generation, and orchestration semantics.

**Rejected alternatives:**  
- Treat all source files uniformly — rejected because these files define system-wide invariants and failure boundaries.  
- Encode the same logic elsewhere to avoid touching critical files — rejected because duplicating control logic creates divergence and hidden behavior.  
- Permit direct edits without prerequisite review of file purpose — rejected because it increases the risk of breaking global guarantees.

## [Enforce path security through a single boundary]
**Status:** Accepted

**Context:** Repository write safety is a security boundary. The critical-files guidance states that every write path must pass through `src/path_security.py`. GitHub integration lessons also show that invalid roots may fail silently or be rejected by guards.

**Decision:** Route every filesystem and repository write performed by CraftedAgent through `src/path_security.py`. Do not bypass this module for convenience, performance, or special cases.

**Consequences:** All path validation logic remains centralized and auditable. New write flows must integrate with the existing security boundary rather than introducing bespoke checks. Any feature requiring writes to new locations must update the allowlist and validation rules explicitly.

**Rejected alternatives:**  
- Validate paths at each call site — rejected because it duplicates logic and creates inconsistent enforcement.  
- Allow direct writes for “trusted” internal operations — rejected because trusted-path exceptions erode the security boundary.  
- Validate only before commit, not before file creation — rejected because unsafe intermediate writes still violate security assumptions.

## [Use an explicit root allowlist for repository writes]
**Status:** Accepted

**Context:** The GitHub integration lessons learned specify that committing to unexpected root directories fails silently or is rejected by path guards. Standard project roots are known, and dot-prefixed roots such as `.github` require explicit allowlisting.

**Decision:** Permit CraftedAgent writes only to explicitly allowed repository roots. At minimum, support the standard roots `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`, and require explicit allowlist updates for any new root.

**Consequences:** CraftedAgent cannot create or modify files in arbitrary top-level directories. Features that require new repository areas must first declare and authorize those roots. Dot-prefixed directories must never be assumed valid without explicit configuration.

**Rejected alternatives:**  
- Allow any root under the repository if the path is normalized — rejected because normalization alone does not express repository policy.  
- Infer allowed roots from existing directories on disk — rejected because repository contents can vary and may include unsafe or unintended paths.  
- Special-case `.github` as always allowed outside the general policy — rejected because it weakens consistency and makes the security model harder to audit.

## [Centralize all GitHub I/O in github_tools.py]
**Status:** Accepted

**Context:** `src/github_tools.py` is designated as the location for all GitHub I/O, including path validation interactions, rate limiting, and SHA protocol handling. Fragmenting these behaviors would create inconsistent remote-state handling.

**Decision:** Perform all GitHub API and repository remote operations for CraftedAgent through `src/github_tools.py`. Do not introduce parallel GitHub clients or bypasses in other modules.

**Consequences:** Rate limiting, SHA handling, and repository interaction semantics remain consistent across the subsystem. New GitHub capabilities must be added by extending the shared tool layer. Testing and audit efforts can focus on a single integration boundary.

**Rejected alternatives:**  
- Let each component call GitHub APIs directly — rejected because it duplicates protocol logic and causes inconsistent behavior.  
- Use shell-based git commands for some operations and API calls for others — rejected because split transport semantics complicate correctness and error handling.  
- Create a second helper module for convenience — rejected because it dilutes the single integration boundary and invites drift.

## [Keep pipeline stage logic within cyclomatic complexity 15]
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is specifically identified as having this limit strictly enforced. CraftedAgent’s orchestration must remain decomposable and reviewable.

**Decision:** Keep each CraftedAgent pipeline stage and orchestration unit at cyclomatic complexity 15 or below. When logic approaches the limit, extract helpers or separate stage-specific strategies rather than adding branching in place.

**Consequences:** Implementation must favor composable stage functions, explicit strategy objects, or helper modules over large control blocks. Reviews should reject changes that increase stage complexity beyond the threshold. The subsystem becomes easier to test and safer to modify incrementally.

**Rejected alternatives:**  
- Allow exceptions for orchestration code because it is inherently complex — rejected because orchestration complexity is exactly where failures become hardest to reason about.  
- Enforce complexity only at file level — rejected because large stage functions can still become opaque even in small files.  
- Defer complexity control to later refactoring — rejected because complexity debt accumulates quickly in pipeline code.

## [Checkpoint every state transition in the generation pipeline]
**Status:** Accepted

**Context:** The build pipeline requires every state transition to be checkpointed, including per-PR states such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. CraftedAgent coordinates long-running, failure-prone work that must be recoverable and auditable.

**Decision:** Persist a checkpoint at every pipeline state transition, including all per-PR progression states and gate outcomes. Do not rely on in-memory state alone for recovery or audit.

**Consequences:** CraftedAgent must expose explicit state transitions rather than implicit progress. Recovery, retry, and operator inspection workflows can resume from known states. Storage and serialization become part of the subsystem contract.

**Rejected alternatives:**  
- Checkpoint only major milestones — rejected because fine-grained recovery and auditability are required.  
- Keep state only in process memory and reconstruct from logs — rejected because reconstruction is unreliable and burdensome.  
- Checkpoint only on failure — rejected because successful transitions are also needed for replay, audit, and deterministic resume behavior.

## [Model PR progression as explicit ordered states]
**Status:** Accepted

**Context:** The documented pipeline names concrete per-PR states: `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. CraftedAgent needs a consistent lifecycle model for orchestration, checkpointing, and gate enforcement.

**Decision:** Represent per-PR execution as an explicit ordered state machine using the documented progression states. Require transitions to occur in order unless an intentionally designed rollback or retry path exists.

**Consequences:** The subsystem must encode state semantics clearly and reject invalid jumps. Features such as resume, reporting, and operator approval can depend on stable lifecycle meaning. Ad hoc status flags should not replace the canonical state sequence.

**Rejected alternatives:**  
- Track progress with independent booleans — rejected because booleans allow invalid combinations and obscure ordering.  
- Use free-form status strings emitted by each component — rejected because they are hard to validate and maintain.  
- Infer state from artifacts on disk or GitHub — rejected because inference is brittle and can misrepresent partial progress.

## [Use failure-type-aware fix loops with bounded retries]
**Status:** Accepted

**Context:** The build pipeline specifies a fix loop driven by pytest with up to 20 attempts and a failure-type-aware strategy. CraftedAgent must correct generated code iteratively without retrying indefinitely or applying generic fixes blindly.

**Decision:** Implement fix loops as bounded retries with a maximum of 20 attempts, and choose remediation strategies based on classified failure type rather than a one-size-fits-all retry.

**Consequences:** Retry behavior is deterministic and auditable. The subsystem must classify failures sufficiently to select an appropriate strategy. Infinite or open-ended correction loops are prohibited, and hitting the retry ceiling becomes a defined terminal condition requiring escalation or operator intervention.

**Rejected alternatives:**  
- Retry until tests pass — rejected because it risks non-terminating loops and unbounded cost.  
- Use a fixed generic repair prompt for every failure — rejected because syntax, import, and test logic failures need different handling.  
- Stop after the first failure — rejected because iterative repair is an explicit part of the pipeline design.

## [Validate generated code before entering repair/test loops]
**Status:** Accepted

**Context:** The build pipeline defines a validation sequence including `ast.parse`, `ruff`, and import checks before the fix loop. CraftedAgent should reject structurally invalid output early and classify issues before expensive test execution.

**Decision:** Run generated code through syntax parsing, lint/static hygiene, and import validation before invoking broader repair or test stages.

**Consequences:** Cheap and high-signal failures are detected earlier, reducing noisy downstream test cycles. Repair logic can distinguish generation validity issues from functional test failures. The subsystem must preserve this ordering rather than jumping directly to pytest.

**Rejected alternatives:**  
- Run pytest first and let tests reveal all problems — rejected because syntax and import failures are cheaper and clearer to detect directly.  
- Rely only on linting — rejected because syntax and import validity are separate constraints.  
- Collapse validation and repair into a single undifferentiated loop — rejected because stage-specific signals improve correctness and efficiency.

## [Generate standard CI workflows for Linux and macOS targets]
**Status:** Accepted

**Context:** The build pipeline requires `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is the critical file responsible for generating these workflows.

**Decision:** Generate CI workflows through `src/ci_workflow.py` using the standard dual-target model: `crafted-ci.yml` for Ubuntu-based CI and `crafted-ci-macos.yml` when macOS/Swift coverage is required.

**Consequences:** CI generation stays centralized and consistent with platform expectations. CraftedAgent must not emit ad hoc workflow files outside the standard naming and generation path without an explicit design change. Platform-specific behavior belongs in workflow generation logic, not scattered across unrelated modules.

**Rejected alternatives:**  
- Generate a single universal workflow for all stacks — rejected because the documented pipeline distinguishes Linux and macOS/Swift needs.  
- Hand-author workflow files directly in each feature flow — rejected because it bypasses the centralized generator and invites inconsistency.  
- Omit macOS workflow generation unless manually requested in code — rejected because supported platform coverage must be expressed through the subsystem’s standard CI generation path.

## [Require an operator gate before merge]
**Status:** Accepted

**Context:** The pipeline defines Stage 6 as a gate where an operator approves or corrects before merge, and every gate decision is checkpointed. CraftedAgent must therefore stop short of autonomous merge completion.

**Decision:** Require explicit operator approval or correction before merge. Do not permit CraftedAgent to merge changes autonomously past the defined gate.

**Consequences:** Human oversight is a mandatory control in the delivery path. The subsystem must surface sufficient state and artifacts for operator review and must checkpoint the decision. Full end-to-end autonomous merge behavior is out of scope unless the governing documents change.

**Rejected alternatives:**  
- Auto-merge once tests and CI pass — rejected because it violates the documented gate.  
- Make operator approval optional by repository setting — rejected because the gate is a system-level requirement, not a convenience feature.  
- Treat lack of response as implicit approval — rejected because gate decisions must be explicit and checkpointed.

## [Preserve a standards-driven repository layout]
**Status:** Accepted

**Context:** The repository layout separates requirements in `forge-docs/` from implementation standards in `forge-standards/`, including `ARCHITECTURE.md`, `INTERFACES.md`, `DECISIONS.md`, `CONVENTIONS.md`, and `build_rules.md`. CraftedAgent must fit into this structure rather than inventing parallel governance files.

**Decision:** Keep CraftedAgent aligned with the repository’s standards-driven layout: requirements in `forge-docs/`, implementation standards in `forge-standards/`, and source code in `src/`. Update the appropriate standards artifact rather than creating duplicate governance documents elsewhere.

**Consequences:** Architectural, interface, convention, and decision records remain discoverable and consistent. CraftedAgent documentation changes must be placed in the correct repository area. Generated rule artifacts such as `build_rules.md` must be respected as part of the established structure.

**Rejected alternatives:**  
- Store subsystem-specific decisions next to source code only — rejected because it fragments governance and breaks repository conventions.  
- Duplicate standards documents under a subsystem folder for convenience — rejected because duplication causes divergence.  
- Mix requirements, standards, and code artifacts in one directory tree — rejected because the repository has an explicit separation of concerns.