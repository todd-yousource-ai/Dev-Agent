# DECISIONS.md

## Repository source of truth lives in forge-docs
**Status:** Accepted  
**Context:** The subsystem operates in a repository where TRDs and PRDs are the authoritative requirements. The documented repository structure explicitly places all TRDs in `forge-docs/`, and implementation is expected to read these before building.  
**Decision:** Treat `forge-docs/` as the authoritative source of product and technical requirements, and require CraftedAgent behavior to align with documents stored there before generating or modifying code.  
**Consequences:** Implementation must read from and preserve `forge-docs/`. Feature behavior, workflow assumptions, and generated changes must be traceable back to these documents. Logic must not substitute ad hoc configuration or undocumented conventions for requirements defined in `forge-docs/`.  
**Rejected alternatives:**  
- Using code comments or inferred repository patterns as the primary source of truth — rejected because requirements are explicitly centralized in `forge-docs/`.  
- Duplicating TRD-derived rules into multiple implementation locations and treating those copies as authoritative — rejected because it creates drift from the documented source of truth.  

## Critical subsystem files are protected and must be treated as control points
**Status:** Accepted  
**Context:** Several files are explicitly identified as critical because they define core generation, orchestration, GitHub I/O, path security, and CI workflow generation. Changes to these files have system-wide effects.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as protected control points, requiring any modification to preserve their documented responsibility boundaries.  
**Consequences:** CraftedAgent implementations must avoid bypassing these files with duplicate logic elsewhere. New features affecting generation, orchestration, path validation, GitHub writes, or CI generation must integrate through these control points rather than around them. Reviews for changes touching these files must be stricter because they affect every generated PR or security boundary.  
**Rejected alternatives:**  
- Spreading equivalent logic across new helper modules for convenience — rejected because it weakens the documented control boundaries and increases drift.  
- Allowing direct writes or GitHub operations outside the designated modules — rejected because it bypasses security, SHA, and rate-limit controls.  

## All repository writes must pass through path security validation
**Status:** Accepted  
**Context:** Path security is explicitly identified as the security boundary, and lessons learned note that unexpected root directories fail silently or are rejected. The system relies on guarded write paths.  
**Decision:** Route every filesystem write, generated file change, and commit-target path through `src/path_security.py` validation before persistence or GitHub submission.  
**Consequences:** No component may write directly to arbitrary paths. File creation and update flows must fail closed when a path is not validated. Testing must cover allowlisted and rejected paths. Security review must focus on preserving this single validation choke point.  
**Rejected alternatives:**  
- Performing lightweight path checks inside each feature module — rejected because distributed validation is inconsistent and easier to bypass.  
- Validating only at commit time — rejected because unsafe intermediate writes would still occur locally.  

## Repository root writes are limited to an explicit allowlist
**Status:** Accepted  
**Context:** The GitHub integration lessons learned identify a required allowlist of valid repo roots. Standard allowed roots include `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`, with dot-prefixed roots such as `.github` requiring explicit permission.  
**Decision:** Enforce an explicit root-directory allowlist for all CraftedAgent-created or modified paths, including explicit support for `.github` as a dot-prefixed allowed root.  
**Consequences:** New write targets outside the allowlist require an intentional policy update rather than ad hoc acceptance. The path validator must distinguish valid dot-prefixed roots from invalid hidden paths. GitHub commits targeting other roots must be rejected deterministically.  
**Rejected alternatives:**  
- Allowing writes to any existing directory in the repository — rejected because repository presence is not a sufficient security or policy signal.  
- Using a denylist of dangerous roots instead of an allowlist — rejected because it is easier to miss unsafe or unintended locations.  
- Blocking all dot-prefixed directories — rejected because CI workflow files under `.github` are explicitly required.  

## GitHub I/O must be centralized in github_tools
**Status:** Accepted  
**Context:** `src/github_tools.py` is designated as the location for all GitHub I/O and is responsible for path validation, rate limiting, and SHA protocol handling. These concerns are cross-cutting and correctness-sensitive.  
**Decision:** Centralize all repository API reads, writes, branch operations, and commit interactions through `src/github_tools.py`.  
**Consequences:** No other module may call GitHub APIs directly. SHA handling, concurrency safeguards, retries, and rate-limit behavior remain consistent across the subsystem. Future GitHub behavior changes must be implemented once in the centralized module.  
**Rejected alternatives:**  
- Allowing each workflow stage to call GitHub APIs directly — rejected because it duplicates SHA and rate-limit logic and increases inconsistency.  
- Wrapping GitHub calls in multiple stage-specific clients — rejected because it obscures policy enforcement and weakens observability.  

## Pipeline stages must preserve the documented staged build flow
**Status:** Accepted  
**Context:** The build pipeline is documented as a sequence of stages including parse/lint/import checks, a bounded pytest fix loop, CI workflow generation, and an operator gate before merge. CraftedAgent must fit this staged model.  
**Decision:** Implement CraftedAgent workflows as explicit pipeline stages matching the documented build flow, including syntax and lint validation, bounded test-fix iteration, CI generation, and a pre-merge gate.  
**Consequences:** Stage boundaries must remain visible in code and runtime state. Features cannot collapse validation, testing, and gate behavior into a single opaque step. Pipeline telemetry and error handling must map to these stages.  
**Rejected alternatives:**  
- Using a monolithic generate-and-commit flow — rejected because it removes stage-level controls and weakens recovery.  
- Making CI generation optional within the default flow — rejected because CI workflow generation is an explicit documented stage.  

## The automated test-fix loop is bounded to 20 attempts
**Status:** Accepted  
**Context:** The build pipeline explicitly states a fix loop of “pytest up to 20 attempts” with failure-type-aware strategy. This bound prevents unending repair cycles and constrains runtime.  
**Decision:** Cap the automated test-fix loop at 20 attempts per run.  
**Consequences:** Repair logic must track attempts and stop deterministically when the limit is reached. Failure reporting must surface exhaustion clearly for operator review. Strategies may improve within the loop, but may not exceed the cap.  
**Rejected alternatives:**  
- Retrying until tests pass — rejected because it can loop indefinitely and hides failure boundaries.  
- Using a lower unconfigurable cap such as 3 or 5 — rejected because the documented pipeline explicitly allows up to 20 attempts.  
- Allowing arbitrary caller-defined retry counts — rejected because it undermines the documented operational constraint.  

## Cyclomatic complexity per stage is capped at 15
**Status:** Accepted  
**Context:** The repository documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is explicitly called out as having this limit strictly enforced.  
**Decision:** Keep each pipeline stage implementation at cyclomatic complexity 15 or lower, and refactor rather than expanding a stage beyond that threshold.  
**Consequences:** Complex behavior must be decomposed into helpers or subcomponents without obscuring stage boundaries. Build director changes require active complexity monitoring. Code review must reject stage logic that exceeds the cap even if functionally correct.  
**Rejected alternatives:**  
- Enforcing complexity only at the file or module level — rejected because the documented constraint applies to each stage.  
- Waiving the limit for orchestration code — rejected because `src/build_director.py` is specifically identified as strictly constrained.  

## Every pipeline state transition must be checkpointed
**Status:** Accepted  
**Context:** The build pipeline documentation requires that every state transition be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. This supports recovery and traceability.  
**Decision:** Persist a checkpoint for every pipeline state transition, including the documented per-PR milestone states.  
**Consequences:** Runtime design must include durable state recording rather than ephemeral in-memory progress only. Recovery, resumption, and audit features must use these checkpoints. New states added to the workflow must also be checkpointed.  
**Rejected alternatives:**  
- Checkpointing only major milestones such as start and finish — rejected because the documentation requires every transition.  
- Keeping state only in logs — rejected because logs are not a sufficient structured recovery mechanism.  
- Tracking progress only in memory — rejected because it prevents crash recovery and auditability.  

## Operator approval is required before merge
**Status:** Accepted  
**Context:** The documented build flow includes a gate where the operator approves or corrects before merge, and every gate decision is intended to be recorded. This preserves human oversight over generated changes.  
**Decision:** Require an explicit operator gate before merge, and record the resulting approval or correction decision as part of pipeline state.  
**Consequences:** CraftedAgent must not auto-merge solely on the basis of generation and CI success. UI, CLI, or API surfaces must support a distinct approval/correction action. Audit trails must include the gate outcome.  
**Rejected alternatives:**  
- Fully automatic merge after passing tests and CI — rejected because it bypasses the documented operator gate.  
- Informal operator review without recorded state — rejected because gate decisions must be checkpointed and auditable.  

## CI workflow generation must include Linux by default and macOS for Swift projects
**Status:** Accepted  
**Context:** The build pipeline defines CI as `crafted-ci.yml` on `ubuntu-latest`, with `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is the designated generator for these workflows.  
**Decision:** Generate `.github` workflow files through `src/ci_workflow.py`, always producing the standard Ubuntu workflow and adding the macOS workflow when the project requires Swift support.  
**Consequences:** Workflow generation logic must be deterministic and repository-aware. `.github` must remain on the path allowlist. Swift-capable repositories incur dual-platform CI generation, while non-Swift repositories do not receive unnecessary macOS workflows.  
**Rejected alternatives:**  
- Generating CI files ad hoc in other modules — rejected because CI generation is centralized in the designated control file.  
- Always generating both Ubuntu and macOS workflows for every project — rejected because the documentation scopes macOS workflow generation to Swift use cases.  
- Omitting Linux CI when macOS is present — rejected because Ubuntu is the baseline workflow.