# DECISIONS.md

## Repository documentation is the source of truth
**Status:** Accepted  
**Context:** CraftedApp exists within a repository structure where all TRDs and PRDs live under `forge-docs/`, and repository-wide standards live under `forge-standards/`. The subsystem must be implemented against these documents, not inferred conventions. This is necessary because generation, review, CI, and security behavior are specified externally and must remain consistent across agents and PRs.  
**Decision:** Treat `forge-docs/` and `forge-standards/` as authoritative inputs before implementing or modifying CraftedApp behavior. Require implementation decisions to align with documented TRDs, PRDs, architecture standards, interfaces, conventions, and generated build rules.  
**Consequences:** CraftedApp cannot introduce behavior that contradicts repository documentation, even if a local implementation shortcut seems simpler. Changes to subsystem behavior must be justified against the documented standards. Implementers must read and preserve constraints defined outside the subsystem code.  
**Rejected alternatives:**  
- **Rely on code as the primary source of truth:** Rejected because the repository explicitly places design authority in `forge-docs/` and `forge-standards/`.  
- **Allow subsystem-local conventions to override repository standards:** Rejected because it would create divergence across agents and break coordinated workflows.  
- **Treat generated artifacts such as build rules as optional guidance:** Rejected because build behavior depends on them and inconsistency would destabilize the pipeline.

## Critical orchestration and security files must be preserved as architectural boundaries
**Status:** Accepted  
**Context:** Specific files are identified as critical: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. These files define core generation, orchestration, GitHub I/O, path security, and CI generation boundaries. CraftedApp must not bypass or dilute these responsibilities.  
**Decision:** Preserve the designated critical files as the only valid boundaries for their respective concerns. Route generation through `src/consensus.py`, orchestration through `src/build_director.py`, GitHub mutations through `src/github_tools.py`, path validation through `src/path_security.py`, and CI workflow generation through `src/ci_workflow.py`.  
**Consequences:** CraftedApp implementations must integrate with, not bypass, these modules. New code must not duplicate GitHub write logic, create alternate path validation layers, or generate workflows outside the designated CI module. Refactors must maintain the same architectural responsibility split.  
**Rejected alternatives:**  
- **Inline GitHub operations directly inside feature code:** Rejected because it bypasses validation, rate limiting, and SHA handling.  
- **Perform direct filesystem writes without path security:** Rejected because `src/path_security.py` is the defined security boundary.  
- **Distribute orchestration logic across multiple ad hoc modules:** Rejected because it weakens checkpointing and complexity control.  
- **Generate CI YAML from arbitrary feature modules:** Rejected because CI generation is explicitly centralized.

## All repository writes must pass through path security validation
**Status:** Accepted  
**Context:** The repository defines path security as a hard boundary, and lessons learned from GitHub integration show that commits to unexpected root directories fail silently or are rejected. CraftedApp must enforce safe and predictable write paths.  
**Decision:** Validate every write path through the repository path security mechanism before any local or GitHub-backed mutation. Reject or block writes that do not resolve to an explicitly allowed root.  
**Consequences:** CraftedApp cannot write files opportunistically or infer path legitimacy from caller intent. Any new writable directory must be added to the allowlist intentionally. This constrains file generation, patch application, and CI/config updates to approved locations only.  
**Rejected alternatives:**  
- **Validate only remote GitHub writes:** Rejected because unsafe local writes can still violate repository guarantees before commit time.  
- **Use simple string-prefix checks in individual modules:** Rejected because decentralized checks are error-prone and inconsistent.  
- **Permit writes first and rely on downstream failures:** Rejected because silent failures and partial state are explicitly identified risks.

## Root directory writes are restricted to an explicit allowlist
**Status:** Accepted  
**Context:** Standard project roots are explicitly allowed: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Dot-prefixed roots such as `.github` require explicit allowlisting because generic validators often reject them. CraftedApp must operate within these approved repository roots.  
**Decision:** Allow CraftedApp to create or modify files only under explicitly allowlisted root directories, including explicit support for `.github`. Require intentional allowlist updates for any additional root.  
**Consequences:** CraftedApp cannot introduce new top-level directories without a deliberate repository decision. CI workflow generation under `.github` is permitted and supported, but only because it is explicitly allowed. Path validation logic must account for dot-prefixed approved roots.  
**Rejected alternatives:**  
- **Allow any root under the repository if it appears safe:** Rejected because this caused silent failures or path-security rejection in prior integration work.  
- **Disallow dot-prefixed roots entirely:** Rejected because CI workflow files must be written under `.github`.  
- **Hardcode only `src` and `tests` as writable roots:** Rejected because documented workflows require writes to docs, scripts, config, tooling, schema, contract, and CI locations.

## Build and generation orchestration must remain stage-based
**Status:** Accepted  
**Context:** The build pipeline is defined as a sequence of explicit stages, including parse/lint/import validation, a bounded fix loop, test and CI execution, and a final gate before merge. State transitions are checkpointed, including per-PR transitions such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. CraftedApp must fit this operational model.  
**Decision:** Implement CraftedApp workflow as explicit, named stages with checkpointed state transitions. Preserve the documented stage ordering and per-PR transition semantics rather than collapsing them into a monolithic execution flow.  
**Consequences:** CraftedApp must expose enough state to resume, audit, and diagnose each stage independently. Failures must be attributable to a specific stage. The subsystem cannot hide generation, validation, fixing, commit, or CI progression inside opaque helper chains.  
**Rejected alternatives:**  
- **Run the workflow as one end-to-end task without persistent stage boundaries:** Rejected because checkpointing and recovery are required.  
- **Permit stages to execute in arbitrary order based on heuristics:** Rejected because the repository defines a fixed progression and gate model.  
- **Track only final success/failure:** Rejected because per-stage and per-PR auditability are required.

## Every state transition must be checkpointed
**Status:** Accepted  
**Context:** The pipeline documentation requires that every state transition is checkpointed, including the main build flow and fine-grained PR lifecycle states. CraftedApp must support resumability, traceability, and controlled gating.  
**Decision:** Persist a checkpoint at every meaningful workflow transition, including at minimum `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`, as well as equivalent internal stage transitions.  
**Consequences:** CraftedApp must maintain durable state records rather than ephemeral in-memory progression only. Recovery logic must resume from checkpoints instead of restarting blindly. Operational observability and audit trails become mandatory design constraints.  
**Rejected alternatives:**  
- **Checkpoint only on success or failure boundaries:** Rejected because intermediate recovery and gate review require finer granularity.  
- **Store state only in logs:** Rejected because logs are insufficiently structured for deterministic resume behavior.  
- **Use transient in-process state only:** Rejected because crashes or reruns would lose progression context.

## Cyclomatic complexity per stage must not exceed 15
**Status:** Accepted  
**Context:** The repository explicitly imposes a maximum cyclomatic complexity of 15 on every stage, and `src/build_director.py` is called out as strictly enforcing this limit. CraftedApp must be designed to remain composable and reviewable within that constraint.  
**Decision:** Keep each CraftedApp stage implementation at cyclomatic complexity 15 or below. Split behavior into smaller helpers or sub-stages rather than allowing orchestration methods to accumulate branching logic beyond the limit.  
**Consequences:** Stage handlers must remain narrow in scope. Error classification, retries, and branching behavior may require decomposition into helper functions or strategy objects. Complexity budgeting becomes a design-time requirement, not a cleanup task.  
**Rejected alternatives:**  
- **Enforce complexity only at file or module level:** Rejected because the documented constraint is per stage.  
- **Permit exceptions for orchestration code:** Rejected because orchestration complexity is specifically identified as a controlled boundary.  
- **Rely on code review rather than an explicit limit:** Rejected because the limit is a hard repository rule.

## Automated fix loops must be bounded and failure-type-aware
**Status:** Accepted  
**Context:** The documented build pipeline includes a fix loop that runs `pytest` up to 20 attempts and uses a failure-type-aware strategy. CraftedApp must remediate issues predictably without entering unbounded retry behavior.  
**Decision:** Implement fix/retry behavior as a bounded loop with a maximum of 20 attempts and branch remediation strategy based on failure type rather than generic repeated retries.  
**Consequences:** CraftedApp cannot retry indefinitely or apply the same remediation regardless of failure mode. The subsystem must classify failures sufficiently to choose targeted actions. Exhaustion of the retry budget must be surfaced as a terminal workflow state.  
**Rejected alternatives:**  
- **Unlimited retries until tests pass:** Rejected because it risks non-terminating execution and wasted resources.  
- **A fixed small retry count without failure classification:** Rejected because different failure modes require different corrective strategies.  
- **Manual-only remediation after first failure:** Rejected because the pipeline explicitly includes an automated fix loop.

## Syntax, lint, and import validation must precede iterative test fixing
**Status:** Accepted  
**Context:** The pipeline specifies a validation sequence of `ast.parse`, `ruff`, and import checking before entering the fix loop. CraftedApp should fail fast on structural and static issues before spending retries on test execution.  
**Decision:** Run syntax parsing, linting, and import validation before test-driven fix attempts. Block progression to iterative test fixing until these checks pass or are repaired within the current stage logic.  
**Consequences:** CraftedApp will surface structural errors earlier and avoid wasting test retries on code that cannot import or parse. Validation ordering becomes fixed and predictable. Static failures must be handled separately from runtime test failures.  
**Rejected alternatives:**  
- **Run tests first and infer static problems from failures:** Rejected because parse and import failures are cheaper and more deterministic to detect upfront.  
- **Make linting optional:** Rejected because `ruff` is part of the documented pipeline.  
- **Interleave all checks in arbitrary order:** Rejected because it complicates diagnosis and weakens stage determinism.

## CI workflow generation must target both standard and macOS-specific pipelines
**Status:** Accepted  
**Context:** The repository defines `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. CraftedApp must support standard CI as well as macOS-specific validation needs.  
**Decision:** Generate and maintain two CI workflow variants: a standard workflow targeting `ubuntu-latest` and a macOS-specific workflow for Swift-related execution. Route workflow file generation through the centralized CI workflow module.  
**Consequences:** CraftedApp cannot assume a single-platform CI model. Changes affecting workflow generation must preserve both Linux and macOS coverage where applicable. CI definitions must live under approved `.github` paths.  
**Rejected alternatives:**  
- **Use only Ubuntu CI for all cases:** Rejected because Swift and macOS-specific behavior require dedicated macOS execution.  
- **Use only macOS CI to simplify parity:** Rejected because standard non-Swift validation should remain on the documented Ubuntu workflow.  
- **Hand-maintain workflow files outside the CI generator:** Rejected because workflow generation is centralized by design.

## Merge progression must include an explicit operator gate
**Status:** Accepted  
**Context:** The pipeline includes a final gate where an operator approves or corrects before merge. CraftedApp must not fully automate merge progression past this decision point.  
**Decision:** Require an explicit operator approval or correction step before merge completion. Do not allow CraftedApp to auto-merge solely on the basis of successful generation, tests, commit, and CI.  
**Consequences:** CraftedApp must expose artifacts and status suitable for human review. End-to-end automation stops short of final merge authority. Workflows must model operator intervention as a first-class state, not an exception path.  
**Rejected alternatives:**  
- **Auto-merge immediately after CI passes:** Rejected because the documented process includes a human gate.  
- **Treat operator review as optional for low-risk changes:** Rejected because no such exception is defined.  
- **Fold operator review into CI status checks:** Rejected because approval/correction is a distinct human decision, not a machine check.