# DECISIONS.md

## Source-of-truth documentation lives under `forge-docs/`
**Status:** Accepted

**Context:** The subsystem is implemented in a repository where all TRDs and PRDs are explicitly designated as the source of truth. The documented repository structure places all requirements documents under `forge-docs/` and instructs implementers to read them before building. ForgeAgent behavior must remain traceable to those documents rather than to ad hoc code comments or inferred behavior.

**Decision:** Treat documents in `forge-docs/` as the authoritative requirements source for ForgeAgent. Implementations, refactors, and fixes must align with those documents before introducing behavior changes. Do not create parallel requirement sources elsewhere in the codebase.

**Consequences:** ForgeAgent implementation must be explainable against the TRDs/PRDs in `forge-docs/`. Design changes require corresponding documentation updates or explicit reconciliation with existing documents. Engineers must review relevant documents before modifying subsystem behavior.

**Rejected alternatives:**  
- Treating code as the only source of truth was rejected because it allows behavioral drift away from approved product and technical requirements.  
- Duplicating requirements in multiple folders was rejected because it creates inconsistency and ambiguity during implementation and review.  
- Storing subsystem requirements only in inline comments was rejected because comments are incomplete for cross-cutting architectural constraints.

## Critical pipeline and security files are controlled change points
**Status:** Accepted

**Context:** Several files are identified as critical because they define core generation, pipeline orchestration, GitHub I/O, path security, and CI workflow generation. Changes to these files have subsystem-wide impact, especially for correctness and security.

**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as controlled change points. Any ForgeAgent work that touches generation flow, orchestration, repository mutation, file writes, or CI emission must route through these files rather than introducing duplicate mechanisms elsewhere.

**Consequences:** Implementers must inspect these files before modifying related behavior. New features must integrate with the existing control surfaces instead of bypassing them. Review burden is higher for these files, and local shortcuts are not acceptable where they weaken shared guarantees.

**Rejected alternatives:**  
- Creating parallel helper modules for write security or GitHub access was rejected because it fragments enforcement and increases the chance of bypassing safety checks.  
- Allowing direct repository writes from feature code was rejected because it undermines path validation and auditability.  
- Generating CI workflows from multiple locations was rejected because it risks divergence and invalid workflow output.

## All repository write paths must pass through path security validation
**Status:** Accepted

**Context:** `src/path_security.py` is identified as the security boundary. The repository includes automated code generation and GitHub integration, so file writes are a primary risk surface. Security requirements demand that write operations be constrained and validated.

**Decision:** Route every ForgeAgent file write, modification, or generated artifact path through `src/path_security.py` before touching the filesystem or preparing a GitHub write. Do not permit direct path concatenation or unchecked writes in feature code.

**Consequences:** All write-capable code must depend on the path security boundary. Utility code that writes files must expose validation hooks or use approved wrappers. Refactors must preserve centralized enforcement. Security testing must focus on guaranteeing that no write path bypass exists.

**Rejected alternatives:**  
- Relying on callers to manually validate paths was rejected because distributed validation is easy to omit and hard to audit.  
- Validating only external inputs was rejected because internal transformations can still produce unsafe paths.  
- Using repository-root string prefix checks alone was rejected because naive prefix validation is brittle and insufficient for a security boundary.

## All GitHub I/O must be centralized in `src/github_tools.py`
**Status:** Accepted

**Context:** GitHub operations have explicit concerns: path validation, rate limiting, and SHA protocol handling. These are correctness and safety requirements, not optional conveniences. ForgeAgent interacts with repositories and pull requests, so inconsistent GitHub access would cause race conditions, integrity errors, or API misuse.

**Decision:** Perform all ForgeAgent GitHub reads and writes through `src/github_tools.py`. Enforce path validation, rate limiting, and SHA-aware update semantics there. Do not call GitHub APIs directly from orchestration, generation, or fix-loop code.

**Consequences:** GitHub behavior becomes easier to audit, test, and evolve. Feature code must use shared abstractions and accept the constraints they impose. Optimizations that bypass shared SHA or rate-limit handling are prohibited. Error handling for GitHub interactions must be modeled around the centralized interface.

**Rejected alternatives:**  
- Allowing direct REST calls from individual modules was rejected because it duplicates protocol logic and weakens safety guarantees.  
- Wrapping GitHub access separately per feature was rejected because it leads to inconsistent retry, validation, and update semantics.  
- Deferring SHA handling to callers was rejected because concurrency correctness depends on consistent enforcement.

## Pipeline orchestration must remain stage-based and checkpoint every state transition
**Status:** Accepted

**Context:** The build pipeline is explicitly defined in stages, and every state transition must be checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This supports recovery, auditability, and operator visibility.

**Decision:** Implement ForgeAgent orchestration as an explicit stage pipeline with persisted checkpoints on every transition. Include both global pipeline transitions and per-PR transitions. Do not collapse stages into opaque monolithic execution.

**Consequences:** The subsystem must maintain durable state and transition records. Recovery and resume logic must operate from checkpoints rather than recomputing hidden state. Stage names and transitions become part of operational compatibility and must be handled carefully during changes.

**Rejected alternatives:**  
- A single in-memory end-to-end job runner was rejected because failures would lose progress and hinder debugging.  
- Checkpointing only terminal states was rejected because it is insufficient for resume, audit, and gate enforcement.  
- Inferring stage progress from Git state alone was rejected because it does not fully capture internal pipeline transitions or operator decisions.

## Every pipeline stage must maintain cyclomatic complexity at or below 15
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` specifically notes that this limit is strictly enforced. ForgeAgent orchestration is complex and prone to branching growth, so a hard maintainability constraint is required.

**Decision:** Keep the implementation of each ForgeAgent pipeline stage at cyclomatic complexity 15 or below. When a stage approaches the limit, extract helpers or split responsibilities without changing stage semantics.

**Consequences:** Stage implementations must remain decomposed and reviewable. Refactors may be required before adding functionality to a crowded stage. Complexity budgeting becomes a design constraint, not a post hoc cleanup task. Build and lint tooling should fail changes that exceed the limit where configured.

**Rejected alternatives:**  
- Enforcing only repository-wide average complexity was rejected because it allows orchestration hotspots to become unmaintainable.  
- Applying the limit only to new code was rejected because legacy stage growth would continue unchecked.  
- Waiving the limit for orchestration code was rejected because orchestration is exactly where complexity must be controlled.

## The fix loop must be failure-type-aware and capped at 20 pytest attempts
**Status:** Accepted

**Context:** The documented build pipeline defines a fix loop that runs `pytest` with a maximum of 20 attempts and uses a failure-type-aware strategy. ForgeAgent generates and repairs code, so bounded iteration and classified response behavior are necessary to avoid runaway retries and low-signal patching.

**Decision:** Implement the ForgeAgent fix loop as a bounded remediation cycle with at most 20 pytest attempts, selecting repair behavior based on failure type rather than applying generic retries.

**Consequences:** Failure classification becomes a required input to remediation. The subsystem must stop and surface unresolved issues after the attempt cap instead of retrying indefinitely. Telemetry and logs should preserve which failure type drove each repair attempt. New failure handlers must fit within the bounded loop model.

**Rejected alternatives:**  
- Infinite or operator-unbounded retry loops were rejected because they waste time and obscure terminal failures.  
- A fixed identical retry strategy for all failures was rejected because syntax, import, test, and environment failures require different responses.  
- Immediate failure after a single pytest run was rejected because controlled automated repair is a core subsystem function.

## Validation order before the fix loop must be syntax, lint, and import checks
**Status:** Accepted

**Context:** The build pipeline defines a pre-test validation sequence of `ast.parse`, then `ruff`, then import checking before entering the fix loop. This ordering catches cheap, deterministic failures early and prevents expensive test runs on obviously invalid output.

**Decision:** Preserve the validation sequence: parse with `ast.parse`, run `ruff`, then run import checks before invoking pytest-based remediation. Do not reorder or skip these gates in normal execution.

**Consequences:** ForgeAgent must model validation as layered gates. Early failures should be handled before any full test execution. Tooling and stage APIs should expose these checks as distinct outcomes to support targeted repairs and better diagnostics.

**Rejected alternatives:**  
- Running pytest first was rejected because it is slower and produces noisier feedback for syntax and lint failures.  
- Merging all validations into one opaque “precheck” result was rejected because targeted remediation depends on distinct failure modes.  
- Making lint optional in the default pipeline was rejected because style and static issues are part of required quality gates.

## CI generation must target `ubuntu-latest` by default and add macOS workflows for Swift
**Status:** Accepted

**Context:** The build pipeline specifies two workflow targets: `crafted-ci.yml` on `ubuntu-latest`, and `crafted-ci-macos.yml` for Swift. The repository contains both Python backend code and a Swift/SwiftUI application shell, so CI must reflect language/runtime needs.

**Decision:** Generate CI workflows such that standard pipeline validation runs in `crafted-ci.yml` on `ubuntu-latest`, and Swift-specific validation runs in `crafted-ci-macos.yml`. Keep CI generation centralized in `src/ci_workflow.py`.

**Consequences:** ForgeAgent must distinguish cross-platform backend validation from Apple-platform Swift validation. Workflow naming and runner selection are constrained. Changes to CI behavior must preserve support for the Swift shell rather than assuming Linux-only execution.

**Rejected alternatives:**  
- Running all CI exclusively on Ubuntu was rejected because Swift/macOS validation requires Apple runners.  
- Running everything exclusively on macOS was rejected because it increases cost and is unnecessary for the Python backend default path.  
- Emitting per-feature ad hoc workflows was rejected because it fragments CI behavior and weakens standardization.

## Operator approval is a required gate before merge
**Status:** Accepted

**Context:** The pipeline defines a gate where the operator approves or corrects before merge, and every gate decision is checkpointed. ForgeAgent is an automation subsystem that can generate code and open pull requests, but final merge authority remains explicitly human-governed.

**Decision:** Require an operator approval or correction step before merge. Persist the gate decision as part of the checkpointed pipeline state. Do not permit unattended automatic merge from ForgeAgent pipeline success alone.

**Consequences:** Merge completion depends on human review even after code generation, testing, commit, and CI success. The subsystem must expose enough state and artifacts for efficient operator decision-making. Audit trails must include the recorded gate outcome.

**Rejected alternatives:**  
- Fully automated merge on green CI was rejected because documented governance requires operator approval.  
- Recording approval outside the pipeline state was rejected because gate decisions must be checkpointed.  
- Treating lack of operator response as implicit approval was rejected because it weakens accountability.

## ForgeAgent must align with the documented repository layout and not relocate subsystem responsibilities
**Status:** Accepted

**Context:** The repository layout assigns backend implementation to `src/`, Swift application shell code to `Crafted/`, tests to `tests/` and `CraftedTests/`, standards to `forge-standards/`, and requirements to `forge-docs/`. ForgeAgent spans orchestration and generation but must fit this structure.

**Decision:** Keep ForgeAgent backend implementation in `src/`, place Python tests in `tests/`, and avoid moving standards or requirements content out of `forge-standards/` and `forge-docs/`. Respect existing layout boundaries when adding subsystem artifacts.

**Consequences:** New modules should be added within the established backend and test directories. Generated or supporting files must not blur the separation between code, standards, and requirements. Tooling paths and documentation references can assume stable layout conventions.

**Rejected alternatives:**  
- Creating a separate top-level `agent/` tree was rejected because it duplicates the backend structure and fragments implementation.  
- Mixing generated backend artifacts into `forge-docs/` or `forge-standards/` was rejected because those directories have distinct purposes.  
- Storing Python tests beside every implementation file by default was rejected because the repository already defines `tests/` as the Python test suite location.