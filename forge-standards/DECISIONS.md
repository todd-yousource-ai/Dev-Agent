# DECISIONS.md

## Repository structure is fixed and documentation-first
**Status:** Accepted

**Context:** ForgeAgent operates within a repository layout where the documentation set is the source of truth. The TRDs and PRDs in `forge-docs/` must be read before implementation, and standards live in `forge-standards/`. This structure is part of the subsystem contract and cannot be inferred dynamically without risking divergence from the documented workflow.

**Decision:** Preserve and implement against the repository structure with `forge-docs/` as the authoritative requirements source and `forge-standards/` as the authoritative standards source. Require ForgeAgent changes to respect the documented layout rather than introducing alternate locations for requirements, standards, or generated governance files.

**Consequences:** Implementation must assume:
- `forge-docs/` contains all TRDs and PRDs and must be consulted before building.
- `forge-standards/` contains `ARCHITECTURE.md`, `INTERFACES.md`, `DECISIONS.md`, `CONVENTIONS.md`, and `build_rules.md`.
- Code should not relocate, duplicate, or redefine these sources elsewhere.
- Tooling that discovers requirements or standards must read from these canonical directories.

**Rejected alternatives:**  
- Allowing ForgeAgent to discover requirements from arbitrary folders was rejected because it weakens traceability and risks implementing against stale or partial inputs.  
- Embedding standards directly in code was rejected because it creates drift from the maintained documentation set.  
- Supporting per-project alternate documentation roots by default was rejected because the TRDs define a fixed repository contract.

## Critical subsystem files are protected integration boundaries
**Status:** Accepted

**Context:** Several files are identified as critical because changes to them affect all pull requests, core orchestration, GitHub I/O, security boundaries, and CI generation. These files are high-risk modification points and define the subsystem’s internal control surfaces.

**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as protected integration boundaries. Require any implementation touching their responsibilities to preserve their documented role and route behavior through them rather than bypassing them.

**Consequences:** Implementation must:
- Keep the core generation loop centralized in `src/consensus.py`.
- Keep pipeline orchestration centralized in `src/build_director.py`.
- Route GitHub reads/writes through `src/github_tools.py`.
- Route every write path through `src/path_security.py`.
- Generate CI workflows through `src/ci_workflow.py`.
- Avoid introducing parallel mechanisms that duplicate or bypass these responsibilities.

**Rejected alternatives:**  
- Splitting these responsibilities across ad hoc helper modules was rejected because it obscures control flow and weakens enforcement points.  
- Bypassing `src/path_security.py` for “trusted” writes was rejected because it breaks the security boundary.  
- Performing GitHub I/O outside `src/github_tools.py` was rejected because it undermines path validation, rate limiting, and SHA handling consistency.

## All repository writes must pass through path security
**Status:** Accepted

**Context:** Path security is the explicit security boundary for the subsystem. The lessons learned from GitHub integration show that unexpected roots are rejected or fail silently, and dot-prefixed roots such as `.github` require explicit allowlisting.

**Decision:** Enforce that every repository write path is validated through the path security boundary and restricted to an explicit allowlist of permitted root directories.

**Consequences:** Implementation must:
- Validate all write targets before any filesystem or GitHub write.
- Fail closed on paths outside the allowlist.
- Explicitly allow standard roots: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`.
- Preserve explicit handling for dot-prefixed roots such as `.github`.
- Avoid silent fallback behavior for invalid paths.

**Rejected alternatives:**  
- Allowing writes anywhere under the repository root was rejected because it weakens the security model and enables accidental or malicious file placement.  
- Using pattern-based allow rules without explicit root enumeration was rejected because it is harder to audit and easier to bypass.  
- Special-casing `.github` outside the allowlist was rejected because it creates inconsistent path handling and hidden exceptions.

## GitHub operations must be centralized and protocol-enforced
**Status:** Accepted

**Context:** GitHub I/O is called out as a critical file responsibility, including path validation, rate limiting, and SHA protocol handling. Decentralized GitHub access risks inconsistent correctness and API misuse.

**Decision:** Centralize all GitHub interactions in `src/github_tools.py` and enforce path validation, rate limiting, and SHA-aware update semantics there.

**Consequences:** Implementation must:
- Use a single integration layer for repository content operations.
- Apply path validation before GitHub writes.
- Respect API rate limits centrally rather than in callers.
- Use SHA protocol consistently for content updates to prevent overwrite races and invalid commits.
- Prevent direct ad hoc GitHub API usage from other modules.

**Rejected alternatives:**  
- Letting each module call the GitHub API directly was rejected because it duplicates logic and causes inconsistent safety behavior.  
- Treating rate limiting as a caller concern was rejected because callers cannot reliably coordinate shared API consumption.  
- Omitting SHA-aware writes was rejected because it increases the chance of write conflicts and repository corruption.

## Build pipeline stages are fixed and sequential
**Status:** Accepted

**Context:** The build pipeline is documented as a staged process with defined validation and fix-loop behavior, followed by test/CI and operator gating. The sequence is part of the subsystem’s operational contract.

**Decision:** Implement ForgeAgent pipeline execution as the documented staged sequence and do not collapse, reorder, or skip defined validation, fix-loop, test/CI, and gate stages.

**Consequences:** Implementation must preserve:
- Validation including `ast.parse`, `ruff`, and import checks.
- A fix loop driven by `pytest` with up to 20 attempts and failure-type-aware strategy.
- Test + CI generation and execution before merge gating.
- A final operator approval or correction gate before merge.
- Deterministic stage boundaries suitable for checkpointing and audit.

**Rejected alternatives:**  
- Running validation, fixes, and CI opportunistically in a single undifferentiated loop was rejected because it reduces observability and control.  
- Skipping validation before entering the fix loop was rejected because it wastes repair iterations on fast-fail issues.  
- Auto-merging after tests without operator gate was rejected because the documented process requires human approval or correction before merge.

## Pipeline orchestration complexity is capped at 15 per stage
**Status:** Accepted

**Context:** The README specifies that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is explicitly called out as strictly enforcing this limit. This is both a maintainability and implementation constraint.

**Decision:** Enforce a maximum cyclomatic complexity of 15 for every pipeline stage, especially within orchestration logic in `src/build_director.py`.

**Consequences:** Implementation must:
- Decompose stage logic before it exceeds the complexity threshold.
- Reject designs that accumulate branching behavior into a single stage function.
- Use helper functions or subcomponents without obscuring the documented stage model.
- Preserve readability and auditability of orchestration code.

**Rejected alternatives:**  
- Allowing higher complexity in “central” orchestration code was rejected because the build director is the highest-risk place for opaque logic.  
- Enforcing only a module-level average complexity target was rejected because individual stage functions can still become unmaintainable.  
- Deferring complexity control to code review alone was rejected because the TRD establishes a strict implementation limit, not a soft guideline.

## State transitions must be checkpointed end-to-end
**Status:** Accepted

**Context:** Every state transition is required to be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. This supports resumability, auditability, and operational recovery.

**Decision:** Checkpoint every pipeline state transition and represent per-PR progress using the documented discrete states.

**Consequences:** Implementation must:
- Persist state transitions rather than infer them from transient runtime state.
- Record at minimum the documented per-PR checkpoints: `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`.
- Make pipeline recovery and resume logic consume checkpoints rather than reconstructing progress heuristically.
- Ensure gate decisions are also auditable as stateful events.

**Rejected alternatives:**  
- Only checkpointing major milestones was rejected because it weakens recovery fidelity and audit detail.  
- Inferring state from Git history, CI status, or filesystem contents was rejected because these sources are incomplete and ambiguous.  
- Keeping state only in memory during a run was rejected because it prevents crash recovery and operator traceability.

## CI workflow generation must support Linux by default and macOS for Swift
**Status:** Accepted

**Context:** The documented pipeline requires generated CI workflows: `crafted-ci.yml` on `ubuntu-latest`, and `crafted-ci-macos.yml` for Swift. CI generation is a dedicated responsibility of `src/ci_workflow.py`.

**Decision:** Generate CI workflows through `src/ci_workflow.py` with Linux CI as the default and an additional macOS workflow when the project requires Swift support.

**Consequences:** Implementation must:
- Generate `crafted-ci.yml` targeting `ubuntu-latest`.
- Generate `crafted-ci-macos.yml` when Swift or equivalent macOS-specific build requirements are present.
- Keep workflow generation logic centralized rather than hand-authoring CI in unrelated modules.
- Treat CI generation as part of the build pipeline contract, not an optional enhancement.

**Rejected alternatives:**  
- Generating only one universal workflow for all projects was rejected because Swift/macOS requirements are explicitly distinct.  
- Making CI generation entirely manual was rejected because the subsystem contract assigns this responsibility to `src/ci_workflow.py`.  
- Defaulting all projects to macOS CI was rejected because Linux is the documented baseline and is more appropriate for general projects.

## Operator approval before merge is mandatory
**Status:** Accepted

**Context:** The final gate in the build pipeline requires operator approval or correction before merge. This is an explicit control point and not merely a notification step.

**Decision:** Require an operator gate before merge and do not permit ForgeAgent to merge autonomously after passing automated checks.

**Consequences:** Implementation must:
- Stop at the gate after CI completion.
- Surface sufficient context for operator approval or correction.
- Record the gate decision as part of checkpointed state.
- Prevent any direct path from `ci_passed` to merged without explicit operator action.

**Rejected alternatives:**  
- Fully autonomous merge after tests and CI pass was rejected because it violates the documented gate requirement.  
- Treating operator review as optional for “low-risk” changes was rejected because no such exception is defined.  
- Using passive timeout-based approval was rejected because approval must be explicit and auditable.