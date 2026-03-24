# DECISIONS.md

## [Keep ForgeAgent design artifacts outside implementation code]
**Status:** Accepted

**Context:** ForgeAgent operates within a repository that separates source-of-truth documentation from executable code. The repository layout explicitly places TRDs and PRDs under `forge-docs/` and standards under `forge-standards/`. This separation is necessary because the agent must read governing documents before building, while avoiding accidental coupling of implementation code with normative design artifacts.

**Decision:** Store all TRDs and PRDs in `forge-docs/` and all architecture/standards artifacts in `forge-standards/`; do not colocate these documents inside `src/` or other implementation directories.

**Consequences:** Implementation must treat `forge-docs/` and `forge-standards/` as authoritative inputs, not as generated output locations. Build and agent logic should read from these locations before making changes. Code generation and repository modification routines must preserve this directory boundary.

**Rejected alternatives:**  
- Storing TRDs beside implementation modules in `src/` was rejected because it blurs the boundary between source code and governing requirements.  
- Duplicating standards documents into multiple directories was rejected because it creates drift and ambiguity about the source of truth.  
- Embedding design decisions only in code comments was rejected because they are not discoverable or durable enough for cross-subsystem governance.

## [Treat critical orchestration and security files as constrained modification points]
**Status:** Accepted

**Context:** Several files have subsystem-wide impact and must be treated as critical before modification: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes to these files affect generation, orchestration, GitHub I/O, security boundaries, and CI generation across all agent-produced PRs.

**Decision:** Require explicit review discipline when modifying the identified critical files, and preserve their subsystem responsibilities as stable boundaries.

**Consequences:** Implementations must avoid incidental edits to these files while making unrelated changes. New behavior should prefer extension around these modules rather than uncontrolled expansion within them. Tests and validation should be strongest around these files because regressions propagate broadly.

**Rejected alternatives:**  
- Treating all files as equally safe to modify was rejected because it ignores the real blast radius of orchestration and security code.  
- Splitting critical behavior arbitrarily across many files was rejected because it weakens discoverability and review focus.  
- Allowing generated code to freely rewrite these modules was rejected because it would undermine subsystem integrity.

## [Use src/path_security.py as the mandatory write-path security boundary]
**Status:** Accepted

**Context:** Path handling is a primary security boundary. The documented critical-file guidance states that every write path must pass through `src/path_security.py`. Lessons learned from GitHub integration show that writes outside approved roots fail silently or are rejected, especially for unexpected or dot-prefixed roots.

**Decision:** Route every repository write-path validation through `src/path_security.py`; do not bypass this module for direct filesystem or GitHub write operations.

**Consequences:** All file creation, modification, staging, and commit preparation flows must invoke the same path validation logic. Security fixes and allowlist changes become centralized. Any implementation that writes files without this boundary is non-compliant.

**Rejected alternatives:**  
- Performing ad hoc path checks at each call site was rejected because it is inconsistent and error-prone.  
- Trusting upstream inputs to provide safe paths was rejected because agent-produced and external inputs can be malformed or malicious.  
- Enforcing path validation only at GitHub commit time was rejected because unsafe local writes could already have occurred.

## [Maintain an explicit allowlist of writable repository root directories]
**Status:** Accepted

**Context:** The agent must only write within explicitly approved repository roots. Lessons learned from GitHub integration document the allowed roots for a standard project: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Dot-prefixed roots such as `.github` require explicit allowlisting because generic validators often reject them.

**Decision:** Enforce an explicit root-directory allowlist for all agent write operations, including dot-prefixed roots that are intentionally permitted.

**Consequences:** New writable top-level directories require deliberate allowlist updates before use. Agent changes targeting non-allowlisted roots must be blocked. CI workflow generation under `.github` must succeed only because that root is explicitly approved.

**Rejected alternatives:**  
- Allowing writes anywhere inside the repository was rejected because it weakens security and predictability.  
- Using a denylist of forbidden roots was rejected because it is incomplete and easier to bypass.  
- Inferring allowed roots dynamically from repository contents was rejected because presence does not imply authorization.

## [Centralize all GitHub I/O in src/github_tools.py]
**Status:** Accepted

**Context:** `src/github_tools.py` is the designated location for GitHub interactions, including path validation integration, rate limiting, and SHA protocol handling. GitHub operations are correctness- and security-sensitive, and inconsistent implementations can create race conditions, invalid updates, or bypassed safeguards.

**Decision:** Implement all GitHub reads and writes through `src/github_tools.py`; do not duplicate GitHub protocol logic elsewhere in the subsystem.

**Consequences:** Features that interact with GitHub must depend on the shared tool layer. Rate limiting, SHA handling, and path security integration remain consistent across workflows. Refactors must preserve this module as the single integration boundary.

**Rejected alternatives:**  
- Allowing each feature module to call GitHub APIs directly was rejected because it duplicates protocol handling and increases drift.  
- Wrapping only write operations while letting reads occur elsewhere was rejected because consistency, telemetry, and throttling concerns apply to both directions.  
- Pushing GitHub logic down into every agent strategy was rejected because transport concerns should not be mixed with planning logic.

## [Keep the core generation loop centralized in src/consensus.py]
**Status:** Accepted

**Context:** `src/consensus.py` is identified as the core generation loop, and changes there affect every PR the agent builds. The subsystem needs one authoritative generation flow to preserve predictability, checkpointing, and reviewability across tasks.

**Decision:** Keep ForgeAgent’s core generation loop centralized in `src/consensus.py` and treat it as the canonical execution path for PR generation.

**Consequences:** New generation behaviors should integrate into the existing consensus flow rather than creating parallel orchestration loops. Changes to generation semantics require heightened scrutiny because they alter global agent behavior. Testing should focus on end-to-end impact when this module changes.

**Rejected alternatives:**  
- Creating multiple independent generation loops per feature area was rejected because it fragments behavior and complicates guarantees.  
- Moving generation flow entirely into task-specific plugins was rejected because core lifecycle control would become inconsistent.  
- Duplicating consensus logic in build orchestration code was rejected because it creates divergence between planning and execution.

## [Use src/build_director.py as the sole pipeline orchestrator]
**Status:** Accepted

**Context:** `src/build_director.py` is the designated orchestration point for the build pipeline, and the complexity limit of 15 is strictly enforced. The pipeline spans staged execution, checkpoints, and operator gates, which requires a single orchestration authority.

**Decision:** Centralize pipeline orchestration in `src/build_director.py` and preserve a maximum cyclomatic complexity of 15 for every stage implementation.

**Consequences:** New stages or transitions must be added without violating the per-stage complexity cap. Complex logic should be decomposed into helper units while keeping orchestration readable and bounded. Parallel orchestration paths outside `src/build_director.py` are not allowed.

**Rejected alternatives:**  
- Distributing orchestration logic across individual stage modules without a director was rejected because lifecycle control becomes opaque.  
- Allowing the orchestrator to exceed the complexity threshold was rejected because maintainability constraints are explicit.  
- Encoding the pipeline as a loose script sequence was rejected because it weakens checkpointing and state management.

## [Implement and preserve the staged build pipeline]
**Status:** Accepted

**Context:** The documented build pipeline includes explicit stages, including syntax/lint/import validation and a fix loop, followed by test/CI and operator gate phases. The pipeline is part of the subsystem’s expected behavior and must remain stable enough to support checkpointing and recovery.

**Decision:** Implement ForgeAgent execution as an explicit staged pipeline, including validation, fix-loop, test/CI, and final gate behavior, rather than as an unstructured task runner.

**Consequences:** Stage boundaries become implementation constraints and should be observable in code and state. Recovery, retries, and operator interaction must map to defined stages. New functionality should attach to a stage or introduce a clearly bounded new stage.

**Rejected alternatives:**  
- Running all actions in a single monolithic pass was rejected because failures become harder to classify and recover from.  
- Allowing arbitrary stage ordering per task was rejected because it undermines consistency and checkpoint semantics.  
- Skipping validation stages for perceived speed was rejected because it reduces output quality and increases downstream failures.

## [Use failure-type-aware fix loops with bounded retries]
**Status:** Accepted

**Context:** The build pipeline specifies a fix loop with pytest retries up to 20 attempts and a failure-type-aware strategy. This exists to improve agent resilience while preventing infinite repair cycles.

**Decision:** Implement automated fix loops as bounded retries capped at 20 attempts, and select repair actions based on classified failure type.

**Consequences:** Retry behavior must be deterministic, auditable, and finite. Error handling must include failure classification sufficient to choose appropriate remediation strategies. Tasks that exceed the retry cap must surface as failures rather than looping indefinitely.

**Rejected alternatives:**  
- Retrying indefinitely until success was rejected because it can deadlock the system and obscure true failures.  
- Using a single generic retry strategy for all failures was rejected because syntax, import, and test failures require different responses.  
- Disabling automated retries entirely was rejected because many agent-generated issues are recoverable within bounded attempts.

## [Generate CI workflows through src/ci_workflow.py only]
**Status:** Accepted

**Context:** `src/ci_workflow.py` is the critical file responsible for generating CI workflows. The documented pipeline requires `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. Workflow generation also depends on `.github` being an explicitly allowlisted root.

**Decision:** Generate CI workflow files exclusively through `src/ci_workflow.py`, targeting the documented workflow variants and approved CI locations.

**Consequences:** Workflow naming, platform targeting, and file placement must remain consistent. Manual or duplicate workflow generation logic elsewhere in the codebase is prohibited. Changes to CI behavior should be implemented through the shared workflow generator and validated against path security rules.

**Rejected alternatives:**  
- Hardcoding workflow file contents at multiple call sites was rejected because it creates drift and inconsistent CI behavior.  
- Writing CI files directly from orchestration code was rejected because it bypasses the dedicated generation boundary.  
- Generating platform-specific workflows opportunistically without stable filenames was rejected because downstream automation relies on predictable artifacts.

## [Checkpoint every stage transition and per-PR state transition]
**Status:** Accepted

**Context:** The build pipeline requires that every state transition be checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. Checkpointing is necessary for recovery, observability, and operator intervention.

**Decision:** Persist a checkpoint at every stage transition and at every per-PR lifecycle transition; do not allow silent in-memory-only progression through the pipeline.

**Consequences:** The implementation must expose discrete state transitions and write checkpoint data frequently enough to resume safely. Debugging and auditability improve, but stage logic must remain explicit rather than hidden in nested control flow. Recovery logic must consume checkpoints as authoritative progress markers.

**Rejected alternatives:**  
- Checkpointing only at the start and end of a run was rejected because intermediate recovery would be impossible.  
- Recording transitions only in logs was rejected because logs are not sufficient as resumable state.  
- Using implicit derived state from repository contents was rejected because it is ambiguous and unreliable across failures.

## [Require an operator gate before merge]
**Status:** Accepted

**Context:** The pipeline defines a final gate where the operator approves or corrects before merge, and every gate decision must be recorded. ForgeAgent is therefore not authorized to silently self-merge without human oversight at the final decision point.

**Decision:** Enforce a mandatory operator approval/correction gate before merge, and record each gate decision as part of the run state.

**Consequences:** Fully autonomous merge behavior is out of scope for this subsystem configuration. The implementation must pause for operator input at the final gate and maintain an auditable record of the decision. Merge automation may proceed only after explicit approval.

**Rejected alternatives:**  
- Auto-merging once CI passes was rejected because the documented process requires human approval.  
- Using informal approval outside the system record was rejected because gate decisions must be captured.  
- Making the operator gate optional per run was rejected because it would weaken a defined control point.