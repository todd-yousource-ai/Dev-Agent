# DECISIONS.md

## Protect repository writes with explicit root allowlisting
**Status:** Accepted

**Context:** ForgeAgent writes code, tests, docs, scripts, and CI assets into target repositories. Prior implementation lessons show that commits to unexpected root directories either fail silently or are rejected by path security guards. Dot-prefixed roots such as `.github` are especially prone to rejection unless explicitly permitted. `src/path_security.py` is the write boundary and `src/github_tools.py` is the GitHub I/O layer, so write safety must be enforced consistently across both.

**Decision:** Require every ForgeAgent file write, update, move, or delete to pass through path validation backed by an explicit root-directory allowlist. Allow at minimum these standard roots for normal projects: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Treat dot-prefixed roots as denied unless explicitly allowlisted. Reject operations outside allowed roots before any GitHub API call or local mutation is attempted.

**Consequences:** Implementation must centralize path validation and may not bypass `src/path_security.py`. New repository roots require explicit policy updates. CI workflow generation under `.github` must use the allowlist path. Silent partial writes to disallowed locations are prohibited; failures must be explicit and actionable.

**Rejected alternatives:**  
- Allow arbitrary repository-relative paths and rely on GitHub failures: rejected because failures can be silent, inconsistent, or late.  
- Validate only on commit creation: rejected because unsafe local mutations could already have occurred.  
- Allow all dot-prefixed roots by default: rejected because hidden directories expand the attack and error surface.  
- Keep per-call ad hoc validation in each tool: rejected because it creates inconsistent security behavior.

## Route all repository mutations through the GitHub tools layer
**Status:** Accepted

**Context:** `src/github_tools.py` is identified as the single location for GitHub I/O, including path validation, rate limiting, and SHA protocol handling. ForgeAgent depends on reliable repository mutation semantics across branch creation, file updates, commits, and pull request progression.

**Decision:** Funnel all GitHub reads and writes used by ForgeAgent through `src/github_tools.py`. Enforce SHA-aware update semantics, API rate-limit handling, and path-security checks in this layer. Do not permit direct GitHub API calls from orchestration, consensus, or pipeline stages.

**Consequences:** Feature work in ForgeAgent must extend shared GitHub tooling rather than introducing bespoke clients. Testing can concentrate on one mutation layer. Branch, commit, and PR logic become easier to audit, but implementation flexibility is constrained by the shared interface.

**Rejected alternatives:**  
- Permit direct GitHub API usage in stage-specific modules: rejected because it duplicates security and SHA logic.  
- Split reads and writes across separate clients: rejected because consistency of validation and retry behavior would degrade.  
- Trust the caller to provide correct SHAs and paths: rejected because the subsystem must enforce repository safety centrally.

## Keep orchestration stages below cyclomatic complexity 15
**Status:** Accepted

**Context:** The build pipeline imposes a strict maximum cyclomatic complexity of 15 for every stage. `src/build_director.py` is specifically called out as pipeline orchestration and must remain within this constraint. ForgeAgent coordinates multi-step generation, validation, test/fix loops, and CI gating, which naturally pushes complexity upward unless explicitly constrained.

**Decision:** Design each ForgeAgent orchestration stage and stage helper to remain at or below cyclomatic complexity 15. Split branching logic into smaller functions, strategy objects, or stage-specific handlers rather than accumulating conditionals in a single control loop. Treat complexity regressions in `src/build_director.py` as design failures, not cleanup work for later.

**Consequences:** Implementations must favor decomposition over monolithic flow control. Some additional indirection is required, but stage behavior remains auditable and testable. Complexity enforcement constrains how retry policies, failure classification, and stage transitions are expressed.

**Rejected alternatives:**  
- Allow higher complexity in orchestration because the pipeline is inherently stateful: rejected because the documented rule is strict and intended to preserve maintainability.  
- Enforce complexity only at file level: rejected because single high-risk functions would still become unreadable.  
- Defer refactoring until after features ship: rejected because orchestration debt compounds rapidly in agent systems.

## Checkpoint every pipeline state transition
**Status:** Accepted

**Context:** The pipeline requires that every state transition be checkpointed, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. ForgeAgent performs long-running and failure-prone workflows, so resumability and auditability depend on durable stage tracking.

**Decision:** Persist a checkpoint at every ForgeAgent stage transition and at each required per-PR milestone. Record enough metadata to resume safely, explain current state, and support operator review. Do not advance pipeline state in memory only.

**Consequences:** Implementations must include durable state recording around branch creation, generation, validation, test/fix attempts, commit creation, and CI completion. Recovery logic must read checkpoints as the source of truth. State schemas become part of subsystem compatibility and must evolve carefully.

**Rejected alternatives:**  
- Checkpoint only major stages: rejected because per-PR progression is explicitly required and needed for recovery.  
- Keep transient in-memory state until the run completes: rejected because crashes or restarts would lose audit history and resumability.  
- Infer state solely from GitHub repository artifacts: rejected because not every internal transition is externally visible or unambiguous.

## Preserve the documented stage order of the build pipeline
**Status:** Accepted

**Context:** The build pipeline is defined as an ordered sequence that includes validation (`ast.parse`, `ruff`, import checks), a failure-type-aware fix loop with up to 20 pytest attempts, CI generation, and an operator gate before merge. ForgeAgent is a subsystem within this pipeline and must not reorder semantics casually.

**Decision:** Implement ForgeAgent to honor the documented pipeline ordering: generate code, validate syntax and style, execute the bounded fix loop, generate CI workflow artifacts, and require operator gating before merge progression. Allow internal substeps only when they do not violate the external stage contract.

**Consequences:** Optimization opportunities that depend on skipping or reordering validation and test stages are constrained. The subsystem must expose clear stage boundaries aligned with the published process. Merge automation cannot bypass operator approval.

**Rejected alternatives:**  
- Run tests before static validation to catch more issues sooner: rejected because the defined pipeline places syntax/style/import validation first for cheaper failure detection.  
- Auto-merge after CI success: rejected because operator approval is a required gate.  
- Use an unbounded fix loop until tests pass: rejected because the process explicitly caps attempts.

## Bound the automated fix loop to 20 pytest attempts
**Status:** Accepted

**Context:** The pipeline specifies a fix loop that runs `pytest` for up to 20 attempts using a failure-type-aware strategy. ForgeAgent must iterate to repair generated code, but without a hard ceiling it risks runaway execution, wasted CI time, and opaque behavior.

**Decision:** Limit ForgeAgent’s automated test/fix loop to a maximum of 20 `pytest` attempts per PR iteration. Use failure classification to choose repair strategies within that bound. Surface exhaustion of the limit as an explicit terminal state requiring human review or a new run.

**Consequences:** The subsystem must track attempt counts durably and stop predictably. Repair quality matters because retries are finite. Long-tail failures will be handed off instead of chased indefinitely.

**Rejected alternatives:**  
- Retry until tests pass: rejected because it creates unbounded cost and can mask systemic defects.  
- Use a smaller universal cap such as 3 or 5: rejected because the documented process explicitly allows up to 20 attempts.  
- Count non-pytest validation retries against the same limit: rejected because the requirement is specifically scoped to the pytest fix loop.

## Generate CI workflow artifacts in the allowed `.github` root
**Status:** Accepted

**Context:** Stage 5 requires generated CI workflows, including `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is responsible for generating these files. Because `.github` is dot-prefixed, it must be explicitly allowlisted to satisfy path security.

**Decision:** Write generated CI workflow files through `src/ci_workflow.py` into the `.github` root only after path validation confirms `.github` is allowlisted. Produce the documented workflow variants required by project type, including macOS workflow support for Swift-targeting repositories.

**Consequences:** CI generation is standardized and auditable. Repositories lacking `.github` in the allowlist must fail clearly rather than writing elsewhere. Workflow naming and placement are constrained by the documented pipeline contract.

**Rejected alternatives:**  
- Store workflow templates under `docs` or `scripts` and ask users to move them manually: rejected because Stage 5 requires actual CI workflow generation.  
- Write to hidden directories generically and let downstream tools discover files: rejected because only `.github` is the expected GitHub Actions location and hidden roots must remain explicit.  
- Inline workflow generation inside build orchestration: rejected because CI generation is a distinct responsibility already assigned to `src/ci_workflow.py`.

## Treat Forge documentation repositories as read-before-build sources of truth
**Status:** Accepted

**Context:** The repository structure states that all TRDs and PRDs live in `forge-docs/` and must be read before building. The standard repository layout also places architecture and convention documents in `forge-standards/`, including `DECISIONS.md`. ForgeAgent implementation must remain consistent with these design sources rather than drifting toward code-first behavior.

**Decision:** Require ForgeAgent changes to consult `forge-docs/` as the source of truth before implementing behavior that touches documented pipeline, coordination, GitHub integration, security, CI, or runtime concerns. Treat `forge-standards/DECISIONS.md` as a binding implementation constraint for subsystem design.

**Consequences:** Engineering changes must be documentation-aligned, and undocumented deviations require explicit standards updates. Implementation speed may decrease slightly, but subsystem behavior remains traceable to approved design artifacts.

**Rejected alternatives:**  
- Let code become the primary source of truth once implemented: rejected because the repository structure explicitly prioritizes TRDs and PRDs.  
- Consult docs only for new features, not modifications: rejected because regressions often come from changing existing behavior without revisiting requirements.  
- Treat standards documents as advisory only: rejected because they exist to constrain implementation across the system.

## Protect core control points as high-scrutiny modules
**Status:** Accepted

**Context:** Several files are designated critical before modification: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes in these modules affect every PR, pipeline orchestration, repository safety, and CI generation across ForgeAgent workflows.

**Decision:** Treat the identified critical files as high-scrutiny control points. Require changes to preserve their subsystem responsibilities: `src/consensus.py` for the core generation loop, `src/build_director.py` for orchestration, `src/github_tools.py` for all GitHub I/O, `src/path_security.py` for the write boundary, and `src/ci_workflow.py` for workflow generation. Do not redistribute these responsibilities casually into unrelated modules.

**Consequences:** Refactoring must respect clear ownership boundaries. Reviews and tests should concentrate heavily on these modules. Cross-cutting behavior should be added by extending designated control points rather than creating shadow implementations elsewhere.

**Rejected alternatives:**  
- Freely move responsibilities into feature modules for convenience: rejected because it weakens auditability and duplicates critical logic.  
- Collapse all control logic into one module: rejected because it would violate complexity constraints and increase blast radius.  
- Ignore critical-file guidance once tests pass: rejected because these modules define architectural boundaries, not just behavior.