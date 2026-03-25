# DECISIONS.md

## Repository structure is fixed and documentation-first
**Status:** Accepted  
**Context:** The CraftedDevAgent subsystem operates in a repository where `forge-docs/` contains all TRDs and PRDs and is the source of truth. The repository layout also reserves `forge-standards/` for architecture and implementation constraints. The TRDs explicitly require these locations to be read before building.  
**Decision:** Treat `forge-docs/` as the authoritative requirements source and preserve the top-level repository structure. Read relevant TRDs and standards documents before implementing or modifying subsystem behavior. Do not relocate, merge, or virtualize `forge-docs/` or `forge-standards/` into source directories.  
**Consequences:** Implementation must assume a stable, documentation-first layout. Tooling and code that resolve requirements must read from these fixed locations. Features that infer behavior from code alone are insufficient when they bypass TRD/PRD inputs. Repository refactors that change these paths are out of scope unless all dependent tooling and standards are updated together.  
**Rejected alternatives:**  
- Deriving behavior only from source code and tests — rejected because TRDs/PRDs are the source of truth.  
- Moving requirements docs under `src/` or a hidden metadata directory — rejected because it obscures required pre-build reading and breaks documented repository conventions.  
- Allowing per-project custom doc locations without a stable default — rejected because it weakens determinism and increases orchestration complexity.

## Critical files must be treated as protected architectural boundaries
**Status:** Accepted  
**Context:** Several files are identified as critical because they define core generation, orchestration, GitHub I/O, path security, and CI workflow generation. Changes to these files have system-wide impact.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as protected architectural boundaries. Require targeted review, preserve their responsibilities, and avoid incidental modification when implementing unrelated changes.  
**Consequences:** Work in the subsystem must minimize coupling to these files and prefer extension over ad hoc edits. Refactors involving these files must be intentional and scoped. Testing and review expectations are higher for these files because defects propagate across every generated PR, write path, or CI workflow.  
**Rejected alternatives:**  
- Treating all source files uniformly — rejected because these files carry disproportionate system risk.  
- Freely redistributing responsibilities across new modules during feature work — rejected because it erodes the documented architecture and complicates review.  
- Duplicating logic outside critical files for speed of implementation — rejected because it creates inconsistent security, orchestration, and GitHub behaviors.

## All repository writes must pass through path security
**Status:** Accepted  
**Context:** The path security layer is the explicit security boundary for file writes. GitHub integration lessons learned show that unexpected root writes fail silently or are rejected, and dot-prefixed roots such as `.github` require explicit allowlisting.  
**Decision:** Route every file write, commit target, and generated path through `src/path_security.py` validation before any local or GitHub write occurs. Do not bypass path validation for internal tools, generated files, or CI assets.  
**Consequences:** Any component that writes files must integrate with the centralized path validation mechanism. Security rules become enforceable and auditable in one place. Convenience writes directly to the filesystem or GitHub APIs are prohibited. Feature delivery may require path-security updates before new file locations can be supported.  
**Rejected alternatives:**  
- Letting each subsystem perform its own path checks — rejected because it duplicates logic and weakens the security boundary.  
- Validating only GitHub writes and not local writes — rejected because unsafe local writes can still poison later commit stages.  
- Allowing trusted internal generators to bypass validation — rejected because internal tools are still sources of path errors and policy drift.

## Repository root writes are constrained by an explicit allowlist
**Status:** Accepted  
**Context:** The subsystem must commit only into approved repository roots. Lessons learned specify standard allowed roots and note that `.github` must be explicitly allowlisted because dot-prefixed roots are commonly rejected by validators.  
**Decision:** Enforce an explicit root allowlist for writes and commits. At minimum, support the standard project roots: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Reject or block writes outside the allowlist until policy is intentionally expanded.  
**Consequences:** Generated changes remain within expected project boundaries, reducing silent commit failures and security risk. New root-level directories require an explicit policy change rather than opportunistic use. CI workflow generation into `.github` is supported only because it is explicitly allowlisted.  
**Rejected alternatives:**  
- Permitting writes to any existing directory in the repository — rejected because existence is not a sufficient security or policy signal.  
- Using a denylist instead of an allowlist — rejected because unknown directories would still be writable by default.  
- Special-casing `.github` outside normal validation — rejected because it creates inconsistent path handling and weakens policy clarity.

## GitHub interactions must be centralized in github_tools
**Status:** Accepted  
**Context:** `src/github_tools.py` is designated as the single place for GitHub I/O, including path validation, rate limiting, and SHA protocol handling. Fragmenting these concerns risks inconsistent behavior and API misuse.  
**Decision:** Centralize all GitHub reads, writes, commits, branch operations, and related protocol handling in `src/github_tools.py` or its controlled abstractions. Do not call GitHub APIs directly from feature modules when equivalent functionality belongs in the GitHub tools boundary.  
**Consequences:** Rate limiting, SHA correctness, path validation integration, and error handling remain consistent. Future GitHub API changes can be isolated. Modules that need repository effects must depend on the centralized interface rather than embedding bespoke HTTP or SDK logic.  
**Rejected alternatives:**  
- Direct GitHub API calls from each module — rejected because it duplicates protocol logic and increases bug surface area.  
- Splitting branch, commit, and content operations across unrelated helper modules — rejected because the boundary is explicitly defined and should remain coherent.  
- Allowing temporary direct calls during rapid prototyping — rejected because shortcuts in I/O layers tend to persist and create inconsistent semantics.

## Pipeline stages and state transitions must remain explicit and checkpointed
**Status:** Accepted  
**Context:** The build pipeline is defined in staged form, and every state transition is checkpointed, including per-PR states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. This supports recovery, auditability, and gate decisions.  
**Decision:** Model the CraftedDevAgent workflow as explicit pipeline stages with explicit state transitions, and checkpoint each transition durably. Preserve the named per-PR lifecycle states and extend them only in a backward-compatible, reviewable way.  
**Consequences:** Orchestration code must expose clear stage boundaries and persisted progress markers. Recovery and rerun logic can resume from checkpoints rather than replaying the entire workflow. State naming becomes part of subsystem compatibility and operational tooling.  
**Rejected alternatives:**  
- Using an implicit in-memory workflow with no durable transitions — rejected because failures would be hard to recover and audit.  
- Collapsing multiple stages into a single “in progress” status — rejected because it removes observability and gate precision.  
- Allowing ad hoc stage names per feature — rejected because it breaks consistency across PRs and operators.

## Cyclomatic complexity per stage is capped at 15
**Status:** Accepted  
**Context:** The README explicitly states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is called out as having this limit strictly enforced. This is a maintainability and reviewability constraint.  
**Decision:** Keep the implementation of each pipeline stage at cyclomatic complexity 15 or lower. When logic grows beyond that threshold, split responsibilities into smaller helpers or subordinate components without obscuring stage boundaries.  
**Consequences:** Stage orchestration remains understandable, testable, and reviewable. Implementation may require additional helper abstractions and deliberate decomposition. Complexity-driven refactoring is not optional when thresholds are exceeded.  
**Rejected alternatives:**  
- Allowing occasional exceptions for central orchestration code — rejected because the limit is explicitly strict for pipeline orchestration.  
- Enforcing complexity only at module level — rejected because the requirement applies per stage.  
- Relying on reviewer judgment without a hard threshold — rejected because the documented standard is quantitative, not subjective.

## Validation and fix-loop sequencing is mandatory
**Status:** Accepted  
**Context:** The build pipeline defines a validation sequence including `ast.parse`, `ruff`, and import checks, followed by a fix loop using `pytest` for up to 20 attempts with failure-type-aware strategy. This sequence is part of the subsystem’s expected behavior.  
**Decision:** Execute code validation in the documented order: parse validation, linting, then import checks, followed by a bounded test-driven fix loop of at most 20 attempts. Implement fix strategies that respond to failure type rather than retrying blindly.  
**Consequences:** Generated code is filtered through consistent static and dynamic quality gates before promotion. Retry behavior is bounded and observable. The subsystem must classify failures well enough to apply targeted fixes instead of wasting attempts.  
**Rejected alternatives:**  
- Running tests before static validation — rejected because cheap structural failures should be caught first.  
- Using unlimited retries until tests pass — rejected because it risks runaway loops and unpredictable runtime.  
- Repeating the same generic fix prompt on every failure — rejected because the documented strategy requires failure-type-aware handling.

## CI workflow generation is a first-class subsystem responsibility
**Status:** Accepted  
**Context:** `src/ci_workflow.py` generates CI workflows, and the pipeline requires `crafted-ci.yml` on `ubuntu-latest` plus `crafted-ci-macos.yml` for Swift. CI generation therefore is not incidental output but part of core deliverables.  
**Decision:** Generate and maintain CI workflows through the dedicated CI workflow component. Produce `crafted-ci.yml` targeting `ubuntu-latest`, and generate `crafted-ci-macos.yml` when Swift/macOS support is required. Place generated workflow files under `.github` through approved path-security flows.  
**Consequences:** CI definitions are standardized and reproducible rather than hand-authored ad hoc. Platform-specific workflow needs must be expressed through the CI generation boundary. Path validation and `.github` allowlisting are prerequisites for successful workflow commits.  
**Rejected alternatives:**  
- Treating CI files as manually maintained repository artifacts — rejected because workflow generation is an explicit subsystem responsibility.  
- Generating only Linux CI for all projects — rejected because Swift/macOS support requires a dedicated macOS workflow.  
- Writing workflow files outside `.github` and moving them later — rejected because it complicates validation and violates repository conventions.

## Operator gate before merge is mandatory
**Status:** Accepted  
**Context:** The pipeline includes a final gate where the operator approves or corrects before merge. Gate decisions are checkpointed, making human review part of the intended control flow rather than an optional courtesy.  
**Decision:** Require an explicit operator approval or correction step before merge. Do not auto-merge solely on the basis of generated code, passing tests, or passing CI. Persist the gate decision as part of the workflow state.  
**Consequences:** The subsystem remains human-supervised at the merge boundary, reducing the chance of autonomous propagation of subtle defects or requirement mismatches. Merge automation must stop short of bypassing operator review. Audit logs must include the gate outcome.  
**Rejected alternatives:**  
- Fully autonomous merge after CI passes — rejected because the documented gate requires operator approval or correction.  
- Optional human review only for risky changes — rejected because the gate is defined as a standard stage, not an exception path.  
- Recording approval outside workflow state — rejected because gate decisions must be checkpointed.