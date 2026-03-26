# DECISIONS.md

## Repository structure is a hard precondition for CraftedDevAgent operation
**Status:** Accepted

**Context:** CraftedDevAgent depends on a fixed repository layout in which requirements and technical source documents live in known locations. The subsystem must read TRDs and PRDs before building, and implementation behavior is constrained by standards and generated rules stored in dedicated directories.

**Decision:** Require the repository to preserve the canonical top-level layout, including `forge-docs/` for TRDs and PRDs and `forge-standards/` for architecture, interfaces, decisions, conventions, and generated build rules. Treat these locations as required inputs to subsystem operation rather than optional documentation.

**Consequences:** Implementation must resolve planning and execution inputs from these directories first. Code that attempts to infer requirements from ad hoc locations is non-compliant. Repository bootstrapping, validation, and runtime checks must fail clearly when required directories or governing documents are missing or relocated.

**Rejected alternatives:**  
- Allow arbitrary document locations discovered by search: rejected because it weakens determinism and makes requirements discovery ambiguous.  
- Copy TRD content into code or configuration at runtime: rejected because `forge-docs/` is the source of truth and duplication creates drift.  
- Make standards files optional: rejected because the subsystem is governed by repository-level standards, not local convention.

## Critical files must be treated as protected architectural boundaries
**Status:** Accepted

**Context:** Several files are identified as critical because they define cross-cutting behavior for generation, orchestration, GitHub I/O, path security, and CI workflow generation. Modifying them without explicit awareness risks system-wide regressions.

**Decision:** Enforce special handling for `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Require any implementation that reads, edits, or extends behavior touching these concerns to inspect these files first and preserve their boundary responsibilities.

**Consequences:** Changes that bypass or duplicate logic from these files are disallowed. New capabilities must extend the existing boundary rather than creating parallel paths for orchestration, path validation, GitHub writes, or CI generation. Review and testing expectations are elevated for changes affecting these files.

**Rejected alternatives:**  
- Treat all source files uniformly: rejected because these files anchor subsystem-wide invariants.  
- Reimplement equivalent logic in new modules for convenience: rejected because duplicated security and orchestration logic creates divergence.  
- Allow direct writes or workflow generation outside the designated modules: rejected because it bypasses enforced guards and rate-limit/SHA protocols.

## All repository writes must pass through path security validation
**Status:** Accepted

**Context:** Path handling is an explicit security boundary. Unexpected root directories fail silently or are rejected by guards, and every write path must be validated centrally to prevent unsafe or out-of-policy modifications.

**Decision:** Route every filesystem or repository write through `src/path_security.py` validation before execution. Forbid direct path writes that do not use the approved security boundary.

**Consequences:** Any component that creates, updates, moves, or deletes files must integrate with centralized path validation. Convenience helpers, test utilities, and GitHub write flows are all constrained by this rule. Implementations must not bypass validation even for internal-generated paths.

**Rejected alternatives:**  
- Validate paths locally in each caller: rejected because duplicated validation is inconsistent and error-prone.  
- Validate only user-supplied paths: rejected because generated paths can also violate policy.  
- Trust GitHub API errors as sufficient protection: rejected because policy enforcement must occur before write attempts.

## Allowed root directories must be explicitly allowlisted
**Status:** Accepted

**Context:** Standard projects require writes to a known set of root directories, and dot-prefixed roots such as `.github` are not safely handled by generic validators unless explicitly permitted. Silent failure or security rejection occurs when roots are not allowlisted.

**Decision:** Maintain and enforce an explicit allowlist of valid repository root directories, at minimum including `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs` for standard projects. Require explicit configuration changes to permit additional roots.

**Consequences:** New repository roots cannot be written opportunistically. Features that need additional top-level directories must update the allowlist deliberately. CI workflow generation under `.github` is permitted only because that root is explicitly approved.

**Rejected alternatives:**  
- Permit any top-level directory matching a pattern: rejected because pattern-based approval is too permissive.  
- Infer allowed roots from existing repository contents: rejected because presence is not authorization.  
- Exclude dot-prefixed directories categorically: rejected because CI workflows must be generated in `.github`.

## GitHub repository I/O must be centralized in the GitHub tools boundary
**Status:** Accepted

**Context:** GitHub interactions are constrained by path validation, rate limiting, and SHA protocol requirements. Fragmented API usage would make these guarantees difficult to enforce consistently.

**Decision:** Centralize all GitHub read/write operations in `src/github_tools.py`. Require callers to use this module for repository I/O and preserve its responsibility for path validation integration, rate limiting, and SHA-aware update semantics.

**Consequences:** Direct GitHub API calls elsewhere in the subsystem are prohibited. New behaviors such as commits, branch updates, file writes, and content fetches must be added through the shared GitHub tools boundary. Testing can focus on one integration surface for GitHub semantics.

**Rejected alternatives:**  
- Allow each feature module to call the GitHub API directly: rejected because it would fragment rate limiting and correctness guarantees.  
- Split reads and writes across multiple helper modules: rejected because policy and protocol enforcement belong in one place.  
- Ignore SHA protocol for simple updates: rejected because repository consistency depends on correct SHA-aware operations.

## The core generation loop must remain centered in the consensus engine
**Status:** Accepted

**Context:** `src/consensus.py` is identified as the core generation loop, and changes there affect every PR the agent builds. The subsystem therefore requires a single authoritative execution loop for generation behavior.

**Decision:** Keep the primary generation and iteration loop in `src/consensus.py` and require new generation logic to compose into that loop rather than creating alternate top-level generation paths.

**Consequences:** Global generation behavior changes must be made in one place and evaluated for system-wide impact. Experimental flows must still integrate with the consensus boundary if they affect PR construction. Observability, checkpointing hooks, and failure handling must attach to the central loop.

**Rejected alternatives:**  
- Create separate generation loops per feature area: rejected because behavior would diverge across PR types.  
- Move orchestration into ad hoc command handlers: rejected because it obscures the system’s central control flow.  
- Duplicate consensus behavior in tests or utilities for convenience: rejected because it encourages drift from production execution.

## Pipeline orchestration must remain in the build director and respect a complexity ceiling
**Status:** Accepted

**Context:** `src/build_director.py` owns pipeline orchestration, and a strict cyclomatic complexity limit of 15 applies to every stage. The build pipeline is multi-stage and must remain auditable and maintainable.

**Decision:** Implement pipeline orchestration through `src/build_director.py` and keep each stage’s control logic at or below cyclomatic complexity 15. Refactor by decomposition rather than increasing conditional complexity inside stage handlers.

**Consequences:** New stage logic must be factored into helper functions or subcomponents when complexity grows. Implementations that concentrate branching in the director or any stage beyond the threshold are non-compliant. The subsystem architecture favors explicit stage boundaries over monolithic orchestration.

**Rejected alternatives:**  
- Permit higher complexity in orchestration because it is “central”: rejected because the complexity ceiling is a hard pipeline rule.  
- Replace staged orchestration with a single free-form loop: rejected because it reduces traceability and checkpoint clarity.  
- Enforce complexity only at module level instead of per stage: rejected because stage-level maintainability is the explicit constraint.

## Build pipeline execution must follow staged validation and bounded fix-loop behavior
**Status:** Accepted

**Context:** The documented pipeline includes syntax and lint validation, import checks, a fix loop, testing, CI generation, and operator gating. The fix loop is explicitly bounded to up to 20 pytest-driven attempts with failure-type-aware strategy.

**Decision:** Execute the CraftedDevAgent pipeline as explicit stages, including parse/lint/import validation before iterative repair, and cap the test/fix loop at 20 attempts. Apply failure-type-aware remediation within that bounded loop rather than retrying indefinitely.

**Consequences:** The subsystem must fail deterministically when bounded repair does not converge. Earlier validation stages must prevent wasteful downstream retries on invalid code. Retry strategy must classify failures rather than blindly rerunning the same action.

**Rejected alternatives:**  
- Allow unlimited retries until tests pass: rejected because it risks non-terminating behavior and hides quality problems.  
- Run tests before syntax/lint/import validation: rejected because cheaper validation should fail fast first.  
- Use a fixed generic retry strategy: rejected because the pipeline requires failure-type-aware repair.

## State transitions must be checkpointed for every pipeline and PR stage
**Status:** Accepted

**Context:** Every state transition is required to be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. This is necessary for auditability, resumption, and controlled gating.

**Decision:** Persist a checkpoint at every stage transition in the pipeline and at every per-PR lifecycle transition. Treat checkpoint creation as part of the state transition contract, not as optional logging.

**Consequences:** Execution engines must write durable state after each transition and must be able to resume or inspect progress from checkpoints. Stage handlers cannot silently advance state. Observability and recovery logic must consume checkpointed transitions as the source of truth.

**Rejected alternatives:**  
- Checkpoint only major milestones: rejected because the requirement applies to every transition.  
- Use ephemeral logs instead of structured checkpoints: rejected because logs do not provide a reliable resumable state model.  
- Checkpoint only on failure: rejected because successful transitions also require traceability.

## Operator gate decisions are mandatory before merge
**Status:** Accepted

**Context:** The pipeline includes a final gate where the operator approves or corrects before merge. This gate prevents fully autonomous merging and preserves human oversight on final integration.

**Decision:** Require an explicit operator approval or correction decision before merge. Do not permit automatic merge solely on the basis of generated code, local tests, or CI success.

**Consequences:** Merge workflows must pause for human input after automated stages complete. “Green pipeline” status is necessary but not sufficient for merge. Audit records must include the gate decision as part of the PR lifecycle.

**Rejected alternatives:**  
- Auto-merge when tests and CI pass: rejected because the documented process requires operator gating.  
- Make operator review optional for low-risk changes: rejected because no such exception is defined.  
- Replace approval with passive timeout: rejected because a gate requires an active decision.

## CI workflow generation must use dedicated crafted workflow outputs
**Status:** Accepted

**Context:** The build pipeline specifies generated workflows `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. CI generation is owned by a dedicated critical module.

**Decision:** Generate CI workflows through `src/ci_workflow.py` using the standard crafted workflow outputs, including `crafted-ci.yml` for general Linux CI and `crafted-ci-macos.yml` when Swift or macOS-specific execution is required.

**Consequences:** Workflow naming and generation behavior are standardized across repositories. Implementations must not handcraft divergent CI files when the crafted workflow generator applies. macOS-specific language or platform needs must result in the dedicated macOS workflow.

**Rejected alternatives:**  
- Generate arbitrary workflow names per project: rejected because standardized outputs simplify tooling and review.  
- Use only Ubuntu workflows for all projects: rejected because Swift/macOS workloads require dedicated macOS CI.  
- Allow direct YAML authoring outside the generator: rejected because CI generation is a protected boundary.

## CraftedDevAgent must prefer clear failure over silent rejection when constraints are violated
**Status:** Accepted

**Context:** Lessons learned note that committing to unexpected root directories can fail silently or be rejected by security guards. Silent behavior makes diagnosis difficult and undermines operator control.

**Decision:** Surface explicit, actionable failures whenever repository structure, path allowlists, checkpoint contracts, or pipeline constraints prevent progress. Do not rely on silent no-ops or ambiguous rejection states.

**Consequences:** Error handling must preserve enough context for operators and developers to correct configuration or implementation mistakes. Validation layers should fail fast with reasoned messages. Observability and audit trails must distinguish policy rejection from runtime failure.

**Rejected alternatives:**  
- Silently skip invalid operations for resilience: rejected because it obscures policy violations.  
- Collapse all constraint failures into generic errors: rejected because operators need actionable remediation guidance.  
- Defer detection until GitHub or CI reports failure: rejected because local policy violations should be surfaced immediately.