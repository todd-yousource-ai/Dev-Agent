# DECISIONS.md

## Repository roots must be explicitly allowlisted for all ForgeAgent writes
**Status:** Accepted

**Context:** ForgeAgent performs repository mutations through automation, and path validation is a primary security boundary. Lessons learned from GitHub integration show that commits to unexpected root directories fail silently or are rejected by path security guards. Standard projects require support for roots such as `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Dot-prefixed roots like `.github` are especially prone to rejection unless explicitly permitted.

**Decision:** Route every ForgeAgent file write, file creation, update, and commit path through the path security layer and enforce an explicit root-directory allowlist. Include `.github` as an explicitly allowed root when CI workflow generation is enabled. Reject any path outside approved repository roots before GitHub or filesystem I/O is attempted.

**Consequences:** ForgeAgent implementations cannot write arbitrary files anywhere in a repository. New top-level directories require an intentional allowlist update before use. CI workflow generation must account for `.github` being a special-case allowed root. Path validation behavior becomes deterministic and auditable, but repository flexibility is constrained by policy.

**Rejected alternatives:** Allowing any path under the repo root was rejected because it weakens the security boundary and increases the chance of unintended or malicious writes. Inferring allowed roots dynamically from existing files was rejected because it is error-prone and can legitimize unsafe layouts. Handling path rejection only at commit time was rejected because failures occur too late and complicate recovery.

## ForgeAgent must treat the path security module as the mandatory write boundary
**Status:** Accepted

**Context:** The critical files guidance identifies `src/path_security.py` as the security boundary and states that every write path must pass through it. Because ForgeAgent touches generated code, workflows, and repository metadata, bypassing this boundary would create inconsistent enforcement and increase security risk.

**Decision:** Require all ForgeAgent code paths that mutate repository state to call the path security module before performing filesystem writes, staged changes, or GitHub content updates. Do not duplicate path-validation logic in ad hoc helpers except as thin wrappers around the security module.

**Consequences:** Implementations are constrained to a single authoritative validation mechanism. Security fixes in the path security module propagate everywhere. Developers cannot add direct write shortcuts without violating subsystem design. Some convenience and speed are traded for consistency and safety.

**Rejected alternatives:** Allowing individual modules to implement their own validation was rejected because it leads to drift and inconsistent enforcement. Validating only local filesystem writes and not GitHub writes was rejected because both are mutation surfaces. Post-write auditing was rejected because it detects violations after repository state has already been changed.

## ForgeAgent orchestration must preserve staged pipeline execution
**Status:** Accepted

**Context:** The build pipeline is defined as a staged flow with generation, static validation, fix loops, test and CI, and operator gating. The pipeline documentation also requires checkpointed state transitions for every stage and per-PR states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`.

**Decision:** Implement ForgeAgent orchestration as an explicit stage-based pipeline with durable state transitions and checkpoints at every stage boundary and required per-PR milestone. Do not collapse generation, validation, fixing, commit, and CI into a single opaque execution step.

**Consequences:** ForgeAgent must model and persist workflow state, enabling resumability, auditability, and operator inspection. Stage-specific recovery becomes possible, but orchestration code must remain disciplined and state-aware. Hidden transitions and implicit progress are not permitted.

**Rejected alternatives:** A monolithic “run until done” workflow was rejected because it obscures failure modes and prevents reliable checkpointing. Best-effort in-memory state tracking was rejected because it does not survive interruption. Checkpointing only final outcomes was rejected because it loses operational visibility and undermines recovery.

## Every ForgeAgent stage must remain at or below cyclomatic complexity 15
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is called out as having this limit strictly enforced. ForgeAgent orchestration is especially susceptible to complexity growth because it coordinates retries, validation, CI, and GitHub operations.

**Decision:** Design each ForgeAgent pipeline stage and stage-level orchestrator function to stay at or below cyclomatic complexity 15. Split branching behavior into focused helpers or strategy objects when complexity approaches the limit.

**Consequences:** Implementation must favor decomposition over large conditional controllers. Complexity limits constrain how retries, failure handling, and provider-specific behavior are expressed. Refactoring is mandatory when a stage grows too complex, which improves maintainability but may increase the number of modules and helper abstractions.

**Rejected alternatives:** Enforcing complexity only at the file or class level was rejected because stage logic can still become unreadable. Allowing targeted exceptions for orchestration code was rejected because pipeline code is the highest-risk area for complexity creep. Relying on code review alone was rejected because the limit is an explicit design constraint, not a subjective preference.

## ForgeAgent must preserve the generation-validation-fix loop defined by the build pipeline
**Status:** Accepted

**Context:** The build pipeline specifies a concrete loop: generation is followed by static validation (`ast.parse`, `ruff`, import checks), then a fix loop with pytest for up to 20 attempts using failure-type-aware strategy. This sequence is central to producing mergeable changes rather than raw generated code.

**Decision:** Execute code generation, static validation, and iterative test-driven fixing as separate, ordered steps. Enforce static validation before entering pytest-based fix attempts, and cap automated pytest repair attempts at 20 per change set unless an upstream product decision revises the limit.

**Consequences:** ForgeAgent cannot skip directly from generation to commit. Static checks become mandatory gates, and repair loops are bounded to avoid runaway automation. Implementations must classify failures well enough to support failure-type-aware fixes. Some valid edge cases may require operator intervention once retry limits are reached.

**Rejected alternatives:** Running tests without static validation first was rejected because cheap structural failures should be caught earlier. Using unlimited fix attempts was rejected because it creates non-terminating behavior and poor resource control. Combining validation and fixing into a single undifferentiated retry loop was rejected because it obscures failure causes and weakens stage semantics.

## ForgeAgent must generate and manage CI workflows within approved repository boundaries
**Status:** Accepted

**Context:** CI workflow generation is a named responsibility of `src/ci_workflow.py`, and the pipeline requires crafted CI workflows on `ubuntu-latest`, with a macOS workflow for Swift projects. Workflow files live under `.github`, which must be explicitly allowlisted due to dot-prefixed path restrictions.

**Decision:** Generate CI workflow artifacts only through the CI workflow module and write them only under the explicitly approved `.github` root. Produce the Linux workflow by default and add the macOS workflow when the project stack requires Swift or equivalent macOS-specific execution.

**Consequences:** ForgeAgent cannot emit CI definitions in arbitrary locations or through unrelated modules. CI generation depends on correct root allowlisting and path security integration. Platform-specific workflow decisions must be explicit and traceable. Repositories with nonstandard CI layout require intentional design changes rather than silent accommodation.

**Rejected alternatives:** Writing workflows outside `.github` was rejected because it conflicts with platform conventions and security policy. Embedding CI generation directly into general orchestration code was rejected because it couples concerns and bypasses the dedicated module boundary. Generating all platform workflows unconditionally was rejected because it adds unnecessary cost and noise for non-macOS projects.

## ForgeAgent must centralize GitHub I/O through the GitHub tools module
**Status:** Accepted

**Context:** The critical files guidance identifies `src/github_tools.py` as the module for all GitHub I/O, including path validation interactions, rate limiting, and SHA protocol handling. ForgeAgent depends heavily on repository reads, writes, branch operations, and commit updates, making consistent protocol handling essential.

**Decision:** Perform all GitHub API interactions for ForgeAgent through the GitHub tools module. Preserve its handling of rate limiting, SHA-based update semantics, and repository safety checks. Do not add direct API clients in stage code except as internal implementations hidden behind the module boundary.

**Consequences:** GitHub behavior remains consistent across ForgeAgent features, and concurrency/update semantics are handled in one place. Stage code is constrained to higher-level operations and cannot bypass SHA or rate-limit logic for convenience. Module contracts must be stable enough to support orchestration needs.

**Rejected alternatives:** Allowing each subsystem to instantiate its own GitHub client was rejected because it duplicates rate-limit and update logic. Using shell-based git and GitHub CLI commands as the primary interface was rejected because it is less structured and harder to secure consistently. Bypassing SHA checks for simpler updates was rejected because it risks clobbering concurrent changes.

## ForgeAgent must treat consensus generation as a shared core dependency, not a private fork
**Status:** Accepted

**Context:** `src/consensus.py` is identified as the core generation loop, and changes there affect every PR the agent builds. ForgeAgent relies on generation behavior that has system-wide impact, so divergence or private rewrites would fragment behavior across the platform.

**Decision:** Consume the shared consensus generation loop as the authoritative generation mechanism for ForgeAgent. Extend behavior through stable interfaces, configuration, or composition rather than forking or reimplementing the core loop inside the subsystem.

**Consequences:** ForgeAgent remains aligned with platform-wide generation semantics, and improvements to the core loop benefit all agents. Subsystem-specific customization must fit extension seams rather than patching around the shared engine. This limits local autonomy but reduces drift and duplicated logic.

**Rejected alternatives:** Copying the consensus loop into ForgeAgent for local modification was rejected because it creates divergence and multiplies maintenance risk. Replacing consensus with a ForgeAgent-specific generator was rejected because it undermines shared behavior across PR-building agents. Making unreviewed direct edits to the core loop for subsystem needs was rejected because changes there have cross-cutting impact and require broader coordination.

## ForgeAgent must maintain operator gating before merge-equivalent completion
**Status:** Accepted

**Context:** The pipeline defines a gate in which the operator approves or corrects before merge, and every gate decision is checkpointed. ForgeAgent automates code production and validation, but final progression beyond the gate remains a controlled human decision point.

**Decision:** Preserve an explicit operator approval gate after automated generation, validation, testing, commit, and CI stages and before any merge-equivalent completion state. Checkpoint the gate outcome and any operator-supplied corrections as first-class workflow events.

**Consequences:** ForgeAgent cannot be fully autonomous through merge completion without a separate product decision. Human oversight remains part of the system contract, improving control and accountability but adding latency. Audit trails must include gate decisions, not just automated results.

**Rejected alternatives:** Fully automatic merge on green CI was rejected because the documented workflow requires operator approval. Treating operator review as an optional notification was rejected because it weakens the gate into a non-binding advisory. Recording only approve/reject without associated correction context was rejected because it loses important operational history.

## ForgeAgent documentation and design constraints must align with forge-standards as the source of implementation policy
**Status:** Accepted

**Context:** The repository layout defines `forge-standards/` as the location for `ARCHITECTURE.md`, `INTERFACES.md`, `DECISIONS.md`, `CONVENTIONS.md`, and `build_rules.md`, with `forge-docs/` holding all TRDs and PRDs as source material. ForgeAgent design decisions must therefore be codified in standards-facing artifacts rather than remaining implicit in code.

**Decision:** Treat TRDs and PRDs in `forge-docs/` as the source of requirements and record implementation-constraining decisions for ForgeAgent in `forge-standards` documentation artifacts. Keep subsystem implementation aligned to these documented decisions and do not rely on undocumented code behavior as policy.

**Consequences:** ForgeAgent changes that alter architecture or operating constraints require documentation updates, not just code changes. The subsystem becomes easier to review and govern, but development must account for documentation discipline. Hidden conventions are discouraged.

**Rejected alternatives:** Using code comments as the sole record of subsystem policy was rejected because they are too localized and easy to miss. Keeping design decisions only in issue threads or PR discussions was rejected because that does not create a stable source of truth. Treating TRDs as optional guidance was rejected because the repository structure explicitly designates them as foundational inputs.