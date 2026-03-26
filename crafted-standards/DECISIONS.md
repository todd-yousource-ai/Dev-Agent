# DECISIONS.md

## [Use the documented repository layout as the implementation boundary]
**Status:** Accepted  
**Context:** CraftedAgent operates inside a repository with a fixed, documented structure. TRDs and PRDs are the source of truth and live under `forge-docs/`. Shared engineering constraints and generated standards live under `forge-standards/`. The subsystem must not infer an alternate layout because repository structure errors affect generation, validation, and CI behavior.  
**Decision:** Implement CraftedAgent against the documented repository layout and treat `forge-docs/` and `forge-standards/` as required top-level locations. Read requirements from `forge-docs/` before execution logic that depends on product or technical policy, and preserve `forge-standards/build_rules.md` as generated content that must not be deleted or treated as hand-authored source.  
**Consequences:** Path handling, document discovery, standards loading, and write operations must assume this layout. Features that depend on requirements or standards must fail clearly if these directories are missing or malformed rather than silently falling back to guessed locations. Tooling must avoid scattering generated artifacts into undocumented roots.  
**Rejected alternatives:** Deriving repository structure dynamically from heuristics was rejected because it creates nondeterministic behavior across repos. Allowing arbitrary top-level locations for TRDs and standards was rejected because it weakens enforcement of source-of-truth documents. Treating generated standards files as editable source was rejected because it would create drift from the generation pipeline.

## [Require pre-modification review of critical files]
**Status:** Accepted  
**Context:** Several files define system-wide behavior and safety boundaries. The TRDs explicitly call out `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as critical files that must be understood before modifying. Changes in these files can impact every pull request, every write path, and CI generation.  
**Decision:** Require CraftedAgent to explicitly load and evaluate the designated critical files before proposing or applying modifications that affect their domains, and treat these files as protected design surfaces requiring heightened change scrutiny.  
**Consequences:** Implementation must include a pre-change read step or equivalent guardrail for work touching consensus, orchestration, GitHub I/O, path security, or CI workflow generation. Changes in adjacent modules must account for these files’ contracts. Review workflows should surface modifications to these files as higher risk.  
**Rejected alternatives:** Allowing opportunistic edits without first reading the critical files was rejected because it increases the chance of violating hidden invariants. Treating all files uniformly was rejected because these files are explicitly identified as system-critical. Relying only on tests to detect mistakes was rejected because some failures are security or workflow regressions not fully captured by tests.

## [Enforce allowed repository root directories for all GitHub write operations]
**Status:** Accepted  
**Context:** Lessons learned from GitHub integration show that committing to unexpected root directories either fails silently or is blocked by path security guards. Standard project operation requires explicit allowlisting of valid roots, including dot-prefixed roots such as `.github`.  
**Decision:** Permit CraftedAgent to create or modify files only under an explicit allowlist of repository roots: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`, unless the allowlist is intentionally expanded through a controlled standards change.  
**Consequences:** All write-path validation must check the top-level root before file creation, update, staging, or commit. CI workflow generation under `.github` must be explicitly supported rather than incidentally allowed. New top-level directories cannot be used ad hoc by the agent.  
**Rejected alternatives:** Allowing writes anywhere inside the repository was rejected because it bypasses the security model and causes inconsistent repository layouts. Implicitly allowing dot-prefixed directories was rejected because common validators deny them and `.github` must be handled intentionally. Maintaining a denylist instead of an allowlist was rejected because it is weaker and more error-prone.

## [Route every write path through the path security boundary]
**Status:** Accepted  
**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. CraftedAgent performs file generation, patching, workflow creation, and GitHub commits; each of these actions can become a security issue if path normalization and validation are bypassed.  
**Decision:** Require all filesystem writes, file mutations, staging operations, and GitHub content updates initiated by CraftedAgent to be validated through the path security boundary before execution.  
**Consequences:** No direct file write helper, GitHub utility, or workflow generator may bypass centralized path validation. Refactors must preserve a single enforceable path-security chokepoint. Security auditing and test coverage must focus on this boundary.  
**Rejected alternatives:** Performing path validation separately in each caller was rejected because duplicated checks drift and leave gaps. Validating only local filesystem writes but not GitHub content paths was rejected because both mutate repository state. Trusting upstream callers to provide safe paths was rejected because the security model requires central enforcement.

## [Centralize GitHub I/O in github_tools with path validation, rate limiting, and SHA protocol]
**Status:** Accepted  
**Context:** `src/github_tools.py` is the designated module for all GitHub I/O and is responsible for path validation, rate limiting, and SHA protocol handling. Distributed GitHub access would make consistency and safety difficult, especially during automated branch and commit workflows.  
**Decision:** Implement all CraftedAgent interactions with GitHub repository contents, branches, and related write operations through `src/github_tools.py` or an equivalent single integration boundary that preserves path validation, rate limiting, and SHA-aware update semantics.  
**Consequences:** The subsystem must not create alternate direct GitHub clients for convenience. Update flows must honor SHA-based concurrency expectations to avoid clobbering remote changes. Rate limiting behavior becomes a shared operational concern instead of an implementation detail hidden in each feature.  
**Rejected alternatives:** Allowing each component to call GitHub APIs directly was rejected because it fragments safety and retry logic. Omitting SHA-aware updates was rejected because it risks overwriting concurrent changes. Handling rate limiting only at the network client layer was rejected because repository workflows need domain-aware throttling and retries.

## [Keep pipeline orchestration in build_director and enforce cyclomatic complexity limits]
**Status:** Accepted  
**Context:** `src/build_director.py` owns pipeline orchestration, and the complexity limit of 15 is strictly enforced. The build pipeline is multi-stage and stateful, so orchestration can easily become a monolith unless constrained deliberately.  
**Decision:** Keep stage orchestration centralized in `src/build_director.py` while enforcing a maximum cyclomatic complexity of 15 for every stage implementation and orchestration unit. Decompose behavior into focused helpers rather than embedding branching logic into large controller methods.  
**Consequences:** New stages or recovery paths must be added through composition, not by growing deeply nested orchestration code. Complexity checks become a release gate for this subsystem. The architecture favors explicit stage boundaries and helper modules over compact but opaque controller logic.  
**Rejected alternatives:** Allowing orchestration complexity to grow as features are added was rejected because the pipeline becomes unmaintainable and error-prone. Distributing orchestration state transitions across many unrelated modules was rejected because it obscures pipeline control flow. Using a single large workflow method was rejected because it would quickly violate the stated complexity ceiling.

## [Treat the consensus loop as a core invariant-bearing subsystem]
**Status:** Accepted  
**Context:** `src/consensus.py` is the core generation loop, and changes there affect every PR the agent builds. Because CraftedAgent depends on repeatable code generation and correction behavior, the consensus loop must be treated as a stable subsystem with carefully controlled evolution.  
**Decision:** Preserve a single authoritative consensus/generation loop in `src/consensus.py` and require changes to it to maintain deterministic stage behavior, compatibility with checkpointing, and downstream build/test orchestration contracts.  
**Consequences:** Features that alter generation strategy must integrate with the existing consensus boundary rather than introducing side loops or bypass paths. Regression risk for this module is inherently high and must be addressed with targeted tests and review. The subsystem design should assume that consensus output influences every later pipeline stage.  
**Rejected alternatives:** Creating multiple independent generation loops for different task types was rejected because it fragments behavior and complicates checkpointing. Embedding generation logic directly into orchestration was rejected because it blurs responsibilities. Treating consensus as a replaceable utility with no special constraints was rejected because the TRD identifies it as globally impactful.

## [Checkpoint every pipeline state transition, including per-PR stages]
**Status:** Accepted  
**Context:** The build pipeline requires checkpointing on every state transition, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. This is necessary for resumability, auditability, and operator oversight.  
**Decision:** Persist a checkpoint for every pipeline stage transition and every per-PR state transition, with explicit state names matching the documented workflow.  
**Consequences:** CraftedAgent must maintain durable state rather than relying on in-memory progression alone. Recovery, retries, and operator interventions must read and update checkpointed state. Any new stage must define its checkpoint semantics as part of implementation.  
**Rejected alternatives:** Checkpointing only major milestones was rejected because it prevents precise recovery and auditing. Using implicit state reconstructed from Git history or logs was rejected because it is brittle and incomplete. Keeping transition state only in memory was rejected because failures would destroy execution context.

## [Implement the documented staged build pipeline with validation and bounded fix attempts]
**Status:** Accepted  
**Context:** The README defines a staged pipeline that includes syntax and lint validation (`ast.parse`, `ruff`, import check), a fix loop, test/CI execution, and gating. The fix loop is bounded to up to 20 pytest-driven attempts with failure-type-aware strategy.  
**Decision:** Implement CraftedAgent as a staged pipeline that executes documented validation steps in order and caps automated fix attempts at 20, using failure-type-aware remediation rather than unbounded retry.  
**Consequences:** The subsystem must expose stage boundaries clearly enough to support retries, checkpoints, and operator understanding. Automated repair behavior must stop at a defined limit and surface unresolved failure context instead of looping indefinitely. Validation must include syntax parsing, linting, and import integrity before broader test execution.  
**Rejected alternatives:** Allowing unlimited fix retries was rejected because it can stall execution and hide irrecoverable defects. Collapsing validation into a single generic “build” step was rejected because it weakens diagnosis and stage-specific recovery. Skipping early static validation and relying only on tests was rejected because syntax and import failures should be detected earlier and more cheaply.

## [Generate and maintain CI workflows for both standard and Swift/macOS cases]
**Status:** Accepted  
**Context:** The pipeline requires `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is responsible for generating these workflows, making CI generation part of the subsystem’s core responsibilities rather than an external manual step.  
**Decision:** Generate CI workflow definitions through `src/ci_workflow.py`, producing Linux CI by default and a separate macOS workflow for Swift-capable repositories when required by project contents or standards.  
**Consequences:** CI workflow files must be treated as generated artifacts under the approved `.github` root. Workflow changes belong in the generator logic, not as ad hoc manual edits to emitted files. The subsystem must distinguish between standard repositories and those needing macOS/Swift coverage.  
**Rejected alternatives:** Maintaining CI workflow files purely by hand was rejected because it breaks consistency with generator-driven standards. Using only a single Linux workflow was rejected because Swift/macOS projects require platform-specific coverage. Generating workflows outside `.github` was rejected because GitHub Actions requires the documented location.

## [Require an explicit operator gate before merge]
**Status:** Accepted  
**Context:** The documented pipeline ends with a gate in which the operator approves or corrects before merge. Automated code generation and remediation are not sufficient authority to merge without human confirmation.  
**Decision:** Stop CraftedAgent at a pre-merge operator gate and require explicit human approval or correction before completing merge-related actions.  
**Consequences:** The subsystem must expose enough state, artifacts, and rationale for an operator to make a decision. Fully autonomous merge flows are out of scope unless the governing standards are changed. Error handling must preserve the ability for an operator to intervene after automated stages complete.  
**Rejected alternatives:** Automatically merging after tests and CI pass was rejected because the documented workflow requires human gating. Requiring operator approval at every minor substep was rejected because it would destroy pipeline usability. Treating operator review as optional metadata was rejected because it is a mandatory gate, not an advisory signal.