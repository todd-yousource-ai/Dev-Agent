# DECISIONS.md

## [Use the documented repository layout as the only supported baseline]
**Status:** Accepted  
**Context:** CraftedDevAgent operates in a repository with prescribed top-level directories and explicit separation of concerns. The TRDs define `forge-docs/` as the source of truth for requirements and `forge-standards/` as the location for architectural and implementation constraints. The README also defines a fixed repository layout that implementation must respect.  
**Decision:** Treat the documented repository layout as normative. Read requirements from `forge-docs/` before implementation work, and store subsystem-wide standards and design constraints in `forge-standards/`. Do not invent alternate top-level layout conventions for this subsystem.  
**Consequences:** Implementation, tooling, and documentation must assume the standard repository shape. Code that discovers documents, standards, or project roots must target this structure. Changes that depend on moving TRDs, PRDs, or standards files are out of scope unless the repository standard is revised first.  
**Rejected alternatives:**  
- Auto-discover arbitrary document locations across the repo — rejected because it weakens source-of-truth guarantees and increases ambiguity.  
- Co-locate standards inside `src/` — rejected because standards are repository-level governance, not runtime code.  
- Support multiple repository layouts simultaneously — rejected because it increases complexity and undermines deterministic agent behavior.

## [Read critical control files before modifying subsystem behavior]
**Status:** Accepted  
**Context:** Several files are identified as critical because they define security boundaries, orchestration behavior, GitHub I/O, and CI generation. Uninformed changes to these files can affect every generated PR or bypass required safeguards.  
**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as mandatory review targets before modifying related behavior. Require implementers to inspect the relevant critical file before changing generation loops, orchestration, GitHub operations, path handling, or CI workflow generation.  
**Consequences:** Design and implementation work must account for existing logic in these files instead of layering duplicate behavior elsewhere. Changes in these areas require higher scrutiny and must preserve the documented responsibilities of each file.  
**Rejected alternatives:**  
- Permit changes without first reading the critical files if tests pass — rejected because behavioral coupling and security implications are broader than test coverage.  
- Duplicate logic in new modules to avoid touching critical files — rejected because it creates inconsistent control paths and hidden bypasses.  
- Collapse all critical responsibilities into one file — rejected because it would increase complexity and reduce maintainability.

## [Enforce allowed repository root directories for all write operations]
**Status:** Accepted  
**Context:** GitHub integration lessons learned show that commits to unexpected root directories fail silently or are blocked by path security guards. The subsystem relies on an explicit allowlist of valid repository roots, including dot-prefixed roots such as `.github`.  
**Decision:** Allow writes only under explicitly approved repository roots. At minimum, support `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs` as valid standard-project roots, and require explicit allowlisting for any additional root.  
**Consequences:** All file creation, modification, and commit preparation paths must validate the root directory before proceeding. Features that need new top-level directories must update the allowlist intentionally rather than writing opportunistically. Dot-prefixed roots must be handled explicitly, not via generic path heuristics.  
**Rejected alternatives:**  
- Allow writes anywhere inside the repository if the path is relative — rejected because it weakens the security boundary and permits unintended top-level sprawl.  
- Block all dot-prefixed roots — rejected because CI workflow files under `.github` are required.  
- Infer allowed roots dynamically from existing files — rejected because repository drift or malicious paths could expand the write surface unintentionally.

## [Route every writable path through path security validation]
**Status:** Accepted  
**Context:** `src/path_security.py` is defined as the security boundary, and every write path must pass through it. This boundary prevents invalid roots, path traversal, and other unsafe filesystem actions.  
**Decision:** Require every file write, update, rename, delete, or commit candidate path to be validated through the path security layer before use. Do not permit direct filesystem writes that bypass `src/path_security.py`.  
**Consequences:** All modules performing file operations must depend on the central path security mechanism. Convenience helpers, GitHub utilities, and workflow generators must call the same validation path. Any implementation that writes directly to the filesystem without validation is non-compliant.  
**Rejected alternatives:**  
- Validate paths independently in each module — rejected because duplicated security logic diverges and creates bypass risks.  
- Validate only before GitHub commit operations — rejected because unsafe local writes can still corrupt state before commit time.  
- Rely on OS path normalization alone — rejected because normalization does not enforce repository policy or root allowlists.

## [Centralize all GitHub I/O in the GitHub tools layer]
**Status:** Accepted  
**Context:** `src/github_tools.py` owns GitHub I/O, including path validation integration, rate limiting, and SHA protocol handling. Splitting these concerns across modules would risk inconsistent repository updates and API misuse.  
**Decision:** Perform all GitHub reads and writes through `src/github_tools.py` or interfaces directly backed by it. Do not call the GitHub API from ad hoc modules for repository content mutation or retrieval that affects agent execution state.  
**Consequences:** GitHub-related concerns such as SHA handling, retries, throttling, and path validation remain consistent. New features requiring GitHub access must extend the shared tools layer rather than introducing parallel clients.  
**Rejected alternatives:**  
- Allow each feature module to instantiate its own GitHub client — rejected because it duplicates rate-limit and SHA semantics and makes failures inconsistent.  
- Use raw HTTP requests directly from orchestration code — rejected because it bypasses shared safeguards and increases coupling.  
- Restrict `github_tools.py` to writes only — rejected because read/write symmetry is needed for coherent repository state management.

## [Preserve a staged build pipeline with explicit validation and fix loop]
**Status:** Accepted  
**Context:** The build pipeline includes a validation sequence of `ast.parse`, `ruff`, and import checks, followed by a failure-type-aware pytest fix loop capped at 20 attempts. This staged approach structures code generation and remediation.  
**Decision:** Implement and preserve the build pipeline as discrete stages, including syntax validation, linting, import validation, and a bounded test-fix loop with failure-aware remediation. Do not collapse these checks into a single opaque execution step.  
**Consequences:** Pipeline code must expose stage boundaries and execute validation in the prescribed order. Remediation logic must remain bounded and strategy-driven rather than open-ended. Diagnostic output and checkpoints can refer to stable stage names.  
**Rejected alternatives:**  
- Run only pytest and infer all failures from test output — rejected because syntax, lint, and import failures should be caught earlier and more cheaply.  
- Keep retrying until tests pass — rejected because it creates unbounded execution and unpredictable behavior.  
- Merge all validation into one generic “verify” function — rejected because it obscures failure modes and complicates targeted recovery.

## [Cap per-stage cyclomatic complexity at 15]
**Status:** Accepted  
**Context:** The README explicitly states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` enforces this limit strictly. This is a design constraint to keep orchestration understandable and maintainable.  
**Decision:** Keep every build-pipeline stage and equivalent orchestration unit at cyclomatic complexity 15 or lower. Refactor branching logic into helpers rather than allowing stage controllers to exceed the limit.  
**Consequences:** Stage implementations must remain compositional and narrowly scoped. Complex decision trees need decomposition into helper functions or strategy objects. Code review must reject stage logic that exceeds the limit even if functionally correct.  
**Rejected alternatives:**  
- Allow higher complexity in orchestration code because it is “centralized” — rejected because central code is exactly where maintainability risk is highest.  
- Apply the limit only to new code — rejected because all stage logic must remain governed uniformly.  
- Measure only file-level complexity — rejected because the constraint is explicitly stage-level.

## [Checkpoint every pipeline state transition]
**Status:** Accepted  
**Context:** The pipeline requires that every state transition be checkpointed, including per-PR states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. Checkpointing provides recoverability, auditability, and controlled resumption.  
**Decision:** Persist a checkpoint at every defined pipeline state transition, including all per-PR milestone states. Do not advance stages solely in memory without recording the transition.  
**Consequences:** Orchestration must model explicit states rather than implicit progress. Resume, retry, and audit flows can rely on recorded checkpoints. New stages or transitions must define corresponding checkpoint behavior as part of their implementation.  
**Rejected alternatives:**  
- Checkpoint only at major milestones such as commit and CI pass — rejected because intermediate failure recovery would be lossy.  
- Keep pipeline state only in process memory — rejected because crashes and restarts would lose execution context.  
- Infer previous state from repository contents — rejected because repository state alone does not reliably encode orchestration progress.

## [Require an explicit operator gate before merge]
**Status:** Accepted  
**Context:** The pipeline defines a gate stage where the operator approves or corrects before merge. This ensures human oversight after generation, testing, and CI completion.  
**Decision:** Do not auto-merge generated changes. Require an explicit operator approval or correction step before merge is considered complete.  
**Consequences:** The subsystem must support a paused pre-merge state and expose artifacts needed for human review. Automation may prepare a PR and gather evidence, but final merge remains gated by operator action.  
**Rejected alternatives:**  
- Auto-merge once tests and CI pass — rejected because technical correctness alone does not satisfy intent, risk, or governance review.  
- Require approval only for failed or risky changes — rejected because the documented pipeline defines a universal gate.  
- Treat PR creation as implicit approval — rejected because creation and approval are distinct control points.

## [Generate CI workflows for both standard and macOS-specific paths]
**Status:** Accepted  
**Context:** The documented pipeline requires `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is responsible for generating these workflows.  
**Decision:** Generate and maintain CI workflows that cover both the standard Linux path and the macOS-specific path when applicable, using `.github` as an explicitly allowed root. Do not limit workflow generation to a single generic CI configuration.  
**Consequences:** CI generation logic must account for at least two workflow targets and write them through the approved path security boundary into `.github`. Repositories with Swift or macOS requirements must receive the macOS workflow rather than relying on Linux-only validation.  
**Rejected alternatives:**  
- Use a single universal CI workflow for all languages and platforms — rejected because macOS/Swift requirements need dedicated execution environments.  
- Generate workflows outside `.github` — rejected because GitHub Actions requires the standard workflow location.  
- Skip CI generation and assume repositories bring their own workflows — rejected because the subsystem’s pipeline explicitly includes generated CI artifacts.