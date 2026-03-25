# DECISIONS.md

## [Treat `forge-docs/` TRDs and PRDs as the source of truth]
**Status:** Accepted

**Context:** CraftedDevAgent operates within a repository where all product and technical requirements are defined in `forge-docs/`. The subsystem must not infer repository behavior from implementation alone when explicit requirements exist in TRDs or PRDs.

**Decision:** Read and honor documents in `forge-docs/` before implementing, modifying, or orchestrating work in CraftedDevAgent. Treat `forge-docs/` as authoritative over inferred behavior from surrounding code.

**Consequences:** Implementation must include a requirements-ingestion step or equivalent discipline before changes are made. Behavior that conflicts with documented TRDs/PRDs is non-compliant even if current code permits it. Repository tooling and agent flows must preserve `forge-docs/` and avoid bypassing it as a planning input.

**Rejected alternatives:**  
- Rely on current source code as the primary truth because it is faster to inspect. Rejected because TRDs/PRDs explicitly define intended behavior and constraints.  
- Treat documentation as advisory only. Rejected because this would allow divergence from approved architecture and workflows.  
- Cache requirements outside `forge-docs/` as an independent authority. Rejected because it creates a second source of truth.

## [Preserve and respect critical subsystem files before modification]
**Status:** Accepted

**Context:** Several files are explicitly identified as high-impact and security-sensitive: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes in these files can alter generation behavior, orchestration guarantees, security boundaries, and CI outputs.

**Decision:** Require explicit review of designated critical files before modifying behavior that touches generation loops, pipeline orchestration, GitHub I/O, path security, or CI workflow generation. Route all implementation changes affecting these domains through the existing critical-file abstractions rather than duplicating logic elsewhere.

**Consequences:** Contributors must inspect these files first and avoid shadow implementations. Security and orchestration behavior must remain centralized. Refactors that bypass these modules are disallowed unless the decision record is updated.

**Rejected alternatives:**  
- Permit feature work to reimplement equivalent logic in new modules for speed. Rejected because it fragments security and orchestration behavior.  
- Treat critical files as informational only. Rejected because the repository explicitly marks them as high-impact.  
- Allow direct writes or GitHub operations outside `src/path_security.py` and `src/github_tools.py`. Rejected because this breaks the intended control boundary.

## [Enforce repository root allowlisting for all file operations]
**Status:** Accepted

**Context:** GitHub integration lessons learned state that commits to unexpected root directories fail silently or are rejected by path security guards. Standard projects must explicitly allow `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`.

**Decision:** Validate every read/write/commit target against an explicit repository-root allowlist, including dot-prefixed `.github`. Reject operations targeting roots outside the allowlist unless the allowlist is intentionally extended.

**Consequences:** CraftedDevAgent must normalize paths and validate root segments before file creation, update, or commit. CI workflow generation under `.github` must pass through explicit allowlisting. New top-level directories require deliberate policy updates before use.

**Rejected alternatives:**  
- Allow arbitrary repository paths and rely on GitHub API failures. Rejected because failures may be silent and do not provide a reliable security boundary.  
- Infer allowed roots dynamically from the current filesystem. Rejected because accidental or malicious directories could become implicitly trusted.  
- Exclude dot-prefixed directories from support. Rejected because `.github` is required for CI workflows.

## [Route every write path through the path security boundary]
**Status:** Accepted

**Context:** `src/path_security.py` is identified as the security boundary, and every write path must pass through it. CraftedDevAgent will generate code, tests, docs, and workflow files, making path validation a mandatory safeguard.

**Decision:** Send every filesystem write target and GitHub content-write path through `src/path_security.py` validation before execution. Do not perform direct write operations that bypass this module.

**Consequences:** File creation, updates, patch application, and generated artifacts must all use the centralized path-security mechanism. Helper utilities that write files must delegate to the security boundary. Testing must cover bypass attempts and path traversal cases.

**Rejected alternatives:**  
- Validate paths only at the orchestration layer. Rejected because lower-level helpers could still bypass controls.  
- Perform ad hoc validation in each caller. Rejected because validation logic would drift and create inconsistent enforcement.  
- Trust repository-relative paths without validation. Rejected because relative-path assumptions do not prevent traversal or root violations.

## [Centralize all GitHub I/O in `src/github_tools.py`]
**Status:** Accepted

**Context:** `src/github_tools.py` is the designated location for GitHub I/O, including path validation interactions, rate limiting, and SHA protocol handling. GitHub operations are stateful and failure-prone, especially when multiple agent stages interact with the same branch and files.

**Decision:** Perform all GitHub reads, writes, branch operations, and commit-related API interactions through `src/github_tools.py`. Preserve SHA-aware update semantics and built-in rate limiting as mandatory behavior.

**Consequences:** No subsystem may call GitHub APIs directly when equivalent functionality belongs in `src/github_tools.py`. Implementations must honor optimistic concurrency using SHAs and avoid custom retry logic that conflicts with centralized rate limiting. Error handling should be standardized around this module.

**Rejected alternatives:**  
- Call GitHub APIs directly from stage-specific code for convenience. Rejected because it duplicates protocol handling and weakens consistency.  
- Abstract GitHub access into multiple domain-specific wrappers. Rejected because it scatters SHA and rate-limit logic.  
- Ignore SHA protocol for overwrite simplicity. Rejected because it risks clobbering concurrent changes.

## [Keep pipeline stage logic within a cyclomatic complexity limit of 15]
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is called out as a file where this limit is strictly enforced. CraftedDevAgent depends on predictable, auditable stage orchestration.

**Decision:** Implement each pipeline stage and stage-transition handler so that cyclomatic complexity does not exceed 15. Decompose orchestration into smaller helpers rather than concentrating branching logic in `src/build_director.py` or adjacent stage code.

**Consequences:** Large condition trees, multi-mode handlers, and deeply nested recovery logic must be split into focused units. Complexity checks become a design constraint, not just a lint target. Refactors should prefer explicit smaller functions and strategy dispatch over monolithic stage controllers.

**Rejected alternatives:**  
- Allow higher complexity in orchestration because pipeline logic is inherently branching. Rejected because the repository explicitly constrains stage complexity.  
- Enforce complexity only at repository level, not per stage. Rejected because the requirement is stage-specific.  
- Ignore the limit in critical path files for performance. Rejected because maintainability and auditability are primary goals.

## [Checkpoint every state transition in the generation and PR lifecycle]
**Status:** Accepted

**Context:** The README states that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. CraftedDevAgent must support resumability, auditability, and operator review across long-running workflows.

**Decision:** Persist a checkpoint at every meaningful stage transition and PR lifecycle transition. Include at minimum the canonical per-PR states `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`, and do not skip checkpoint creation on successful transitions.

**Consequences:** Orchestration must be resumable from persisted state rather than inferred process memory. Failure recovery and operator visibility depend on durable checkpoints. Stage implementations must emit transition records as part of normal flow, not as optional logging.

**Rejected alternatives:**  
- Checkpoint only on failures. Rejected because successful transitions also need auditability and resumability.  
- Store only a final status per PR. Rejected because it loses progression detail needed for debugging and governance.  
- Infer state from Git and CI artifacts after the fact. Rejected because inference is incomplete and brittle.

## [Implement a bounded, failure-type-aware test fix loop]
**Status:** Accepted

**Context:** The build pipeline specifies a fix loop where `pytest` may run up to 20 attempts with a failure-type-aware strategy. CraftedDevAgent must iteratively repair issues without entering unbounded retry behavior.

**Decision:** Limit automated test-fix iterations to 20 attempts and choose remediation strategy based on observed failure type. Stop retrying when the attempt limit is reached or when failure signals indicate non-repairable conditions under the current scope.

**Consequences:** The subsystem must classify failures rather than applying the same patching strategy repeatedly. Retry loops must be deterministic and bounded. Telemetry and checkpoints should record attempt count and failure categories to support operator intervention.

**Rejected alternatives:**  
- Retry until tests pass. Rejected because it risks infinite loops and wasted compute.  
- Use a fixed repair strategy for all failures. Rejected because syntax, import, test, and environment failures require different actions.  
- Limit retries to a very small number such as 3. Rejected because the documented workflow explicitly allows up to 20 attempts.

## [Generate and manage CI workflows under `.github` as part of the pipeline contract]
**Status:** Accepted

**Context:** The pipeline requires `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is identified as the generator for these workflows, and `.github` must be explicitly allowed as a root.

**Decision:** Generate and maintain CI workflows through `src/ci_workflow.py`, writing them under `.github` using the approved path-security and GitHub-I/O paths. Support both the standard Ubuntu workflow and the macOS workflow for Swift projects as part of the subsystem contract.

**Consequences:** Workflow file generation is not optional or ad hoc. Implementations must preserve compatibility with `.github` allowlisting and must not emit CI definitions to alternative locations. Language/runtime-aware pipeline behavior must account for macOS CI when Swift is involved.

**Rejected alternatives:**  
- Commit CI YAML from arbitrary templates or manual file writes. Rejected because workflow generation is centralized in `src/ci_workflow.py`.  
- Support only Ubuntu CI for simplicity. Rejected because Swift requires macOS workflow support.  
- Store generated workflow files outside `.github`. Rejected because GitHub Actions requires the standard location.

## [Require an operator gate before merge]
**Status:** Accepted

**Context:** The build pipeline defines a final gate where an operator approves or corrects before merge. CraftedDevAgent is therefore not authorized to unilaterally complete the full change lifecycle through merge without human review.

**Decision:** Stop the automated pipeline at the gate stage and require operator approval or correction before merge. Do not auto-merge solely based on successful generation, tests, commits, or CI completion.

**Consequences:** Merge completion remains a supervised action. Automation must surface enough context for an operator to make a decision and must preserve checkpointed status awaiting review. End-to-end autonomy is intentionally constrained at the final step.

**Rejected alternatives:**  
- Auto-merge after CI passes. Rejected because the documented workflow requires operator approval or correction.  
- Require operator approval earlier and skip final review. Rejected because the final merge decision is the explicitly defined gate.  
- Treat the gate as optional for low-risk changes. Rejected because no exception policy is defined in the provided requirements.

## [Preserve the documented repository layout and standards directories]
**Status:** Accepted

**Context:** The repository layout explicitly identifies `forge-docs/` for source-of-truth requirements and `forge-standards/` for architecture and standards artifacts, including `DECISIONS.md`. CraftedDevAgent must fit into this structure instead of inventing parallel organizational schemes.

**Decision:** Keep subsystem documentation and standards artifacts aligned with the documented repository layout. Store decision records in `forge-standards/DECISIONS.md` and avoid creating parallel directories for requirements or standards that duplicate `forge-docs/` or `forge-standards/`.

**Consequences:** Documentation placement is constrained by repository conventions. Tooling that reads standards and requirements can rely on stable locations. New implementation work must integrate with the existing layout instead of introducing competing documentation roots.

**Rejected alternatives:**  
- Place subsystem decisions alongside source code for convenience. Rejected because standards documents are centrally organized in `forge-standards/`.  
- Create a subsystem-specific docs root outside `forge-docs/` and `forge-standards/`. Rejected because it fragments the documented repository model.  
- Treat repository layout as non-binding guidance. Rejected because it is explicitly documented as the repository structure.