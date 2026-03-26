# DECISIONS.md

## Repository structure is fixed and documentation-first
**Status:** Accepted  
**Context:** CraftedApp is developed within a repository layout where `forge-docs/` contains all TRDs and PRDs and serves as the source of truth. The subsystem must align implementation with the documented architecture and workflow rather than invent local structure ad hoc.  
**Decision:** Preserve the documented repository layout and treat `forge-docs/` as authoritative input before implementing or modifying CraftedApp. Place subsystem code only in approved repository locations consistent with the standard layout.  
**Consequences:** Implementation must not relocate source-of-truth documents, redefine top-level structure, or introduce parallel documentation trees. Build and coordination logic must assume the documented repo shape exists and remains stable.  
**Rejected alternatives:**  
- Allowing each subsystem to define its own repository layout was rejected because it breaks agent coordination and undermines shared tooling assumptions.  
- Treating implementation code as the source of truth over TRDs was rejected because it conflicts with the documented development workflow and weakens traceability.  

## Critical orchestration and security files are controlled modification points
**Status:** Accepted  
**Context:** Several files are explicitly designated as critical because they enforce generation, orchestration, GitHub I/O, path security, and CI workflow behavior. Changes to these files have system-wide impact.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as controlled modification points requiring heightened review and strict adherence to their stated responsibilities.  
**Consequences:** CraftedApp changes must avoid bypassing these modules or duplicating their responsibilities elsewhere. Any implementation touching these files must preserve their role as the sole enforcement points for generation loop control, orchestration, GitHub operations, write-path validation, and CI workflow generation.  
**Rejected alternatives:**  
- Re-implementing similar logic inside CraftedApp-specific modules was rejected because it would fragment enforcement and create inconsistent behavior.  
- Allowing direct file writes or GitHub access outside the critical modules was rejected because it weakens security and operational guarantees.  

## All write paths must pass through path security validation
**Status:** Accepted  
**Context:** Path security is a defined security boundary, and every write path must pass through `src/path_security.py`. Silent failures or rejected writes occur when paths fall outside allowed roots.  
**Decision:** Route every CraftedApp file write, file generation action, and repository mutation through the shared path security validation layer before execution.  
**Consequences:** CraftedApp must not perform raw filesystem writes to repository paths without validation. Features that create files, update CI config, generate code, or modify docs must integrate with the centralized validator.  
**Rejected alternatives:**  
- Letting individual modules validate their own paths was rejected because it produces inconsistent policy enforcement.  
- Trusting caller-provided paths without centralized validation was rejected because it breaks the security boundary and increases risk of unauthorized writes.  

## Root-directory writes are restricted to an explicit allowlist
**Status:** Accepted  
**Context:** The GitHub integration lessons learned specify that committing to unexpected root directories fails silently or is blocked by path security guards. Standard projects require an explicit root allowlist, including dot-prefixed `.github`.  
**Decision:** Restrict CraftedApp-generated or committed paths to explicitly allowlisted repository roots: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`, unless the allowlist is intentionally extended through the shared security mechanism.  
**Consequences:** CraftedApp must not create new top-level directories opportunistically. Dot-prefixed roots such as `.github` require explicit support and must never be assumed valid by generic path logic.  
**Rejected alternatives:**  
- Permitting writes to any discovered directory was rejected because it leads to silent commit failures and weakens repository integrity.  
- Inferring allowed roots dynamically from current filesystem contents was rejected because presence does not imply policy approval.  

## CI workflow output must be generated in the approved GitHub workflows location
**Status:** Accepted  
**Context:** CI workflow generation is handled by a critical file and the build pipeline defines standard workflows including `crafted-ci.yml` and `crafted-ci-macos.yml`. `.github` is a special allowed root that must be explicitly handled.  
**Decision:** Generate and update CraftedApp CI workflows only through the CI workflow generation path and place them under `.github/workflows/` using the approved workflow naming conventions.  
**Consequences:** CraftedApp must not emit ad hoc CI files elsewhere in the repository or handcraft workflow placement outside the guarded path. Workflow generation must respect both path allowlisting and centralized CI conventions.  
**Rejected alternatives:**  
- Storing CI definitions under `scripts/` or another root and copying them later was rejected because it obscures source of execution truth and complicates validation.  
- Allowing arbitrary workflow file names and locations was rejected because it reduces operability and breaks shared tooling assumptions.  

## Build pipeline stages are mandatory and sequential
**Status:** Accepted  
**Context:** The documented build pipeline defines ordered stages including parse/lint/import checks, a fix loop, test and CI execution, and a final gate. Stage transitions are checkpointed.  
**Decision:** Implement CraftedApp changes to participate in the defined pipeline stages in order, without skipping validation stages or collapsing them into a single opaque execution step.  
**Consequences:** CraftedApp orchestration must expose state transitions compatible with the shared pipeline. Validation, fixing, testing, CI, and approval remain distinct operational phases.  
**Rejected alternatives:**  
- Combining all build behavior into one monolithic “build” step was rejected because it reduces observability and weakens checkpointing.  
- Skipping intermediate validation when earlier signals look healthy was rejected because it violates the documented stage model.  

## State transitions must be checkpointed
**Status:** Accepted  
**Context:** The pipeline documentation requires every state transition to be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`.  
**Decision:** Record every CraftedApp pipeline state transition as an explicit checkpoint using the shared stage model and never rely on implicit in-memory progress only.  
**Consequences:** CraftedApp must preserve recoverability, auditability, and resumability across execution boundaries. Long-running or multi-step operations must emit durable progress markers rather than assuming uninterrupted execution.  
**Rejected alternatives:**  
- Tracking progress only in logs was rejected because logs are insufficient as authoritative workflow state.  
- Maintaining transient in-process state without checkpoint persistence was rejected because failures would force unsafe recomputation or ambiguous recovery.  

## Cyclomatic complexity per stage is capped at 15
**Status:** Accepted  
**Context:** The build pipeline documentation and critical file guidance explicitly state that every stage has a maximum cyclomatic complexity of 15, with `src/build_director.py` called out for strict enforcement.  
**Decision:** Keep each CraftedApp pipeline stage implementation at cyclomatic complexity 15 or below, factoring logic into smaller helpers when necessary rather than expanding stage controllers.  
**Consequences:** Stage logic must remain decomposed, reviewable, and mechanically enforceable. Large conditional flows must be split across well-scoped helpers or subcomponents.  
**Rejected alternatives:**  
- Allowing more complex stage controllers “for convenience” was rejected because it violates the repository’s enforceable implementation rule.  
- Hiding complexity inside large anonymous closures or deeply nested conditionals was rejected because it preserves the problem while evading the intent of the limit.  

## The fix loop is bounded and failure-type-aware
**Status:** Accepted  
**Context:** The documented build pipeline includes a fix loop that runs `pytest` for up to 20 attempts and applies a strategy based on failure type.  
**Decision:** Implement CraftedApp automated repair behavior as a bounded fix loop with a maximum of 20 attempts and require failure-type-aware remediation instead of blind repetition.  
**Consequences:** CraftedApp must stop retrying after the bounded limit and must classify failures to choose appropriate repair actions. Infinite or unstructured retry behavior is prohibited.  
**Rejected alternatives:**  
- Retrying until success was rejected because it creates non-terminating workflows and unpredictable resource use.  
- Using the same repair action for all failures was rejected because the documented process requires strategy selection based on failure type.  

## GitHub interactions must go through the shared GitHub tools layer
**Status:** Accepted  
**Context:** `src/github_tools.py` is identified as the single place for GitHub I/O, including path validation, rate limiting, and SHA protocol handling. These concerns are cross-cutting and safety-critical.  
**Decision:** Perform all CraftedApp GitHub reads, writes, branch updates, commits, and related remote operations through the shared GitHub tools layer only.  
**Consequences:** CraftedApp must not call GitHub APIs directly from feature code. Rate limiting, SHA handling, and path guard behavior remain centralized and consistent across the system.  
**Rejected alternatives:**  
- Using direct GitHub SDK/API calls from CraftedApp modules was rejected because it bypasses core safeguards and duplicates protocol logic.  
- Creating a second GitHub abstraction specific to CraftedApp was rejected because it would diverge from the shared enforcement model.  

## Operator gate remains required before merge
**Status:** Accepted  
**Context:** The pipeline defines a final gate in which the operator approves or corrects before merge, and every gate decision is checkpointed. CraftedApp must fit within this governance model.  
**Decision:** Require explicit operator approval or correction handling before any CraftedApp-generated changes are considered ready to merge.  
**Consequences:** CraftedApp cannot self-authorize merge completion based solely on local validation or CI success. Human oversight remains a required control point and must be represented in workflow state.  
**Rejected alternatives:**  
- Auto-merging on passing CI alone was rejected because it bypasses the documented gate.  
- Making operator review optional for low-risk changes was rejected because the workflow specifies the gate as a standard stage, not a conditional one.