# DECISIONS.md

## Repository structure is fixed and documentation-led
**Status:** Accepted  
**Context:** CraftedApp is implemented within a repository whose source of truth is the TRD/PRD corpus under `forge-docs/`. The documented repository structure distinguishes product code, standards, and generated build rules. Unstructured placement of code or docs would break agent assumptions and weaken traceability from implementation back to requirements.  
**Decision:** Preserve the documented top-level repository layout and treat `forge-docs/` as the authoritative requirements source. Keep standards and architectural constraints in `forge-standards/`, and place subsystem implementation only within its designated code roots.  
**Consequences:** Implementation must not invent new top-level locations for requirements, standards, or core subsystem code without an explicit standards update. Tooling and agents may rely on these fixed paths. Documentation-first traceability is mandatory for changes affecting CraftedApp.  
**Rejected alternatives:**  
- Allow arbitrary top-level directories for team convenience — rejected because agent workflows and path validation depend on predictable roots.  
- Treat README content as equal to TRDs for implementation authority — rejected because TRDs/PRDs are the declared source of truth.  
- Co-locate standards files inside `src/` — rejected because it blurs enforcement boundaries between code and governing documents.

## Critical orchestration and security files are controlled change points
**Status:** Accepted  
**Context:** Several files are identified as critical because they enforce generation flow, orchestration complexity, GitHub I/O safety, path security, and CI workflow generation. Changes to these files have system-wide impact beyond the CraftedApp subsystem.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as controlled change points. Require implementers to read and preserve their contracts before modifying behavior that interacts with generation, orchestration, repository writes, GitHub operations, or CI generation.  
**Consequences:** CraftedApp code must integrate with these files rather than bypass them. Any change touching these files must preserve subsystem invariants such as path validation, rate limiting, SHA-based GitHub update protocol, complexity limits, and workflow generation expectations.  
**Rejected alternatives:**  
- Reimplement similar logic inside CraftedApp-specific modules — rejected because duplicated control logic creates drift and bypasses safety guarantees.  
- Permit direct repository writes without `src/path_security.py` review — rejected because this breaks the documented security boundary.  
- Allow ad hoc GitHub API calls outside `src/github_tools.py` — rejected because rate limiting, validation, and SHA protocol must remain centralized.

## Repository writes must be constrained to explicitly allowed root directories
**Status:** Accepted  
**Context:** The system’s path security guards reject or silently fail writes to unexpected roots. Standard project operation requires a known allowlist, including dot-prefixed roots such as `.github`, which are commonly blocked unless explicitly permitted.  
**Decision:** Restrict all CraftedApp-generated or CraftedApp-modified repository writes to explicitly allowlisted root directories only. At minimum, honor the standard roots: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Route every write path through the path security layer.  
**Consequences:** CraftedApp must not write to undeclared roots. New root directories require explicit allowlist expansion before use. CI workflow generation under `.github` is permitted only because that root is explicitly recognized.  
**Rejected alternatives:**  
- Permit writes anywhere under the repository so long as paths are relative — rejected because relative-path checks alone do not enforce repository policy.  
- Infer allowed roots dynamically from existing folders — rejected because presence does not imply authorization.  
- Ban dot-prefixed directories entirely — rejected because CI workflows under `.github` are a required capability.

## Pipeline stages and state transitions must remain explicit and checkpointed
**Status:** Accepted  
**Context:** The build pipeline is defined as staged execution with validation and a failure-aware fix loop. In addition, every state transition is checkpointed, including per-PR progression such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. This is required for recoverability, observability, and gated delivery.  
**Decision:** Model CraftedApp workflow progression as explicit pipeline stages with checkpointed state transitions. Persist and honor per-PR stage progression, and do not collapse, skip, or hide state transitions that affect generation, testing, commit, or CI gate outcomes.  
**Consequences:** CraftedApp implementations must expose enough state to resume, audit, and gate work reliably. Error handling must preserve the last valid checkpoint. Features that affect PR lifecycle must integrate with the canonical transition model rather than invent private state machines.  
**Rejected alternatives:**  
- Use a single monolithic “in progress/done” state — rejected because it prevents reliable recovery and obscures gate enforcement.  
- Keep stage progression only in logs — rejected because logs are not a durable or queryable checkpoint model.  
- Allow individual features to define independent lifecycle states — rejected because inconsistent state models break orchestration and operator review.

## Cyclomatic complexity per pipeline stage is capped at 15
**Status:** Accepted  
**Context:** The build pipeline explicitly requires a maximum cyclomatic complexity of 15 for every stage, and `src/build_director.py` is called out as enforcing this limit strictly. Without this constraint, orchestration logic becomes brittle and unreviewable.  
**Decision:** Keep each CraftedApp pipeline stage and orchestration unit at cyclomatic complexity 15 or lower. Refactor by extracting helpers or splitting stages rather than concentrating conditional logic in a single controller path.  
**Consequences:** Implementation must favor composable stage logic, strategy extraction, and narrow responsibilities. Pull requests that increase stage complexity beyond 15 are non-compliant even if functionally correct.  
**Rejected alternatives:**  
- Allow higher complexity in central orchestration modules for convenience — rejected because those modules are the highest-risk points for regressions.  
- Enforce only file-level or class-level complexity limits — rejected because the documented rule applies per stage.  
- Defer complexity control to code review judgment — rejected because the requirement is explicit, objective, and must be mechanically enforceable.

## Validation and fix-loop behavior must remain staged and failure-aware
**Status:** Accepted  
**Context:** The documented build pipeline includes a validation sequence (`ast.parse → ruff → import check`) followed by a fix loop that runs `pytest` for up to 20 attempts using failure-type-aware strategy. This ordering constrains how code quality and repair are performed.  
**Decision:** Preserve the staged validation order and implement test-repair behavior as a bounded, failure-type-aware fix loop with a maximum of 20 pytest attempts. Do not replace these checks with a single opaque validation pass.  
**Consequences:** CraftedApp features that generate or modify code must be compatible with syntax validation, linting, import validation, and bounded iterative repair. Retry behavior must be finite and strategy-driven, not indefinite.  
**Rejected alternatives:**  
- Run tests first and lint later — rejected because cheaper static failures should be detected before expensive test execution.  
- Use unlimited retries until green — rejected because it risks non-terminating loops and resource waste.  
- Replace failure-type-aware repair with generic retries — rejected because the pipeline explicitly requires strategy based on failure category.

## CI workflow generation must target the documented environments
**Status:** Accepted  
**Context:** The repository defines CI expectations: `crafted-ci.yml` on `ubuntu-latest`, and `crafted-ci-macos.yml` for Swift/macOS concerns. Since workflow files live under `.github`, they are both operationally required and path-security sensitive.  
**Decision:** Generate and maintain CI workflows according to the documented split: use `crafted-ci.yml` for Ubuntu-based CI and `crafted-ci-macos.yml` for Swift/macOS execution. Manage workflow file creation and updates through the centralized CI workflow generator and approved `.github` path handling.  
**Consequences:** CraftedApp must not introduce incompatible or duplicative CI entrypoints that bypass the standard generator. Platform-specific behavior belongs in the designated workflow. Any workflow write must satisfy the `.github` allowlist and security checks.  
**Rejected alternatives:**  
- Use a single universal CI workflow for all platforms — rejected because the documented design requires separate handling for macOS/Swift.  
- Hand-author workflow YAML directly in feature code paths — rejected because workflow generation is centralized in a critical file.  
- Store workflow definitions outside `.github` — rejected because GitHub Actions requires the standard location and path policy already accounts for it.

## Operator gate before merge is mandatory
**Status:** Accepted  
**Context:** The pipeline includes a final gate where the operator approves or corrects before merge. This human checkpoint is part of the delivery contract and complements automated validation and CI.  
**Decision:** Require an operator approval/correction gate before merge for CraftedApp changes processed through the pipeline. Do not treat passing tests and CI as sufficient authorization to merge automatically.  
**Consequences:** CraftedApp automation must surface enough context for operator review and must preserve the distinction between machine validation and human acceptance. Merge automation must remain gate-aware.  
**Rejected alternatives:**  
- Auto-merge on green CI — rejected because it removes the explicitly required human gate.  
- Make operator review optional for low-risk changes — rejected because no such exception is specified in the governing requirements.  
- Collapse operator review into earlier generation approval — rejected because the documented gate occurs before merge after pipeline evidence is available.