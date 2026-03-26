# DECISIONS.md

## Repository root writes must be constrained by an explicit allowlist
**Status:** Accepted  
**Context:** CraftedApp performs automated repository writes and GitHub commits. Prior lessons learned show that commits to unexpected root directories either fail silently or are blocked by path security guards. Dot-prefixed roots such as `.github` are especially prone to rejection unless explicitly permitted.  
**Decision:** Enforce an explicit root-directory allowlist for all file creation, update, and commit operations. At minimum, permit writes only under `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs` unless the allowlist is deliberately extended. Require every write path to pass through the path security boundary before any filesystem or GitHub I/O occurs.  
**Consequences:** CraftedApp cannot write arbitrary files anywhere in the repository. New top-level directories require a deliberate allowlist change before use. CI workflow generation under `.github` must be treated as a first-class allowed case rather than a special bypass. Implementation must route all path decisions through the security layer and must not perform direct unchecked writes.  
**Rejected alternatives:**  
- Allow writes anywhere inside the repo if the path is relative — rejected because relative-path checks are insufficient against invalid roots and inconsistent tooling behavior.  
- Special-case `.github` outside normal validation — rejected because it weakens the security boundary and creates inconsistent path handling.  
- Validate paths only at commit time — rejected because unsafe paths must be blocked before filesystem mutation, not after.

## All repository mutations must traverse the path security boundary
**Status:** Accepted  
**Context:** The subsystem has designated security-critical files, and `src/path_security.py` is identified as the write boundary for the system. Automated generation, patching, and GitHub operations all depend on trustworthy path validation.  
**Decision:** Route every repository mutation through the path security module, including local file writes, generated CI workflows, patch application, and GitHub content updates. Prohibit direct filesystem writes or GitHub update calls that bypass this boundary.  
**Consequences:** Implementations must centralize mutation logic and may need adapters around lower-level tools. Security behavior becomes auditable and consistent. Refactors that introduce convenience write helpers must still delegate to the path security layer.  
**Rejected alternatives:**  
- Permit direct local writes while validating only remote GitHub operations — rejected because local state can become unsafe before push.  
- Duplicate path validation in each module — rejected because duplicated security logic drifts and creates inconsistent enforcement.  
- Trust upstream generators to emit safe paths — rejected because generators are not security boundaries.

## Pipeline orchestration stages must remain below cyclomatic complexity 15
**Status:** Accepted  
**Context:** The build pipeline explicitly limits complexity to 15 per stage, and `src/build_director.py` is identified as a critical orchestration file where this rule is strictly enforced. The subsystem must remain maintainable under iterative agent-driven changes.  
**Decision:** Keep each pipeline stage and orchestration unit at cyclomatic complexity 15 or lower. Split branching behavior into smaller helpers or strategy components rather than accumulating conditional logic inside stage handlers.  
**Consequences:** The subsystem must favor composition over large controller methods. Failure-handling, stage transitions, and branch-specific behavior will be decomposed into discrete units. Code reviews must treat complexity growth in orchestration as a design violation, not merely a style issue.  
**Rejected alternatives:**  
- Allow higher complexity in orchestration because it centralizes pipeline logic — rejected because centralization without decomposition makes agent-modified flow brittle and hard to verify.  
- Enforce complexity only at file level — rejected because large complex functions can hide inside compliant files.  
- Rely on reviewers without a hard cap — rejected because the pipeline already defines the cap as a structural constraint.

## Every pipeline state transition must be checkpointed
**Status:** Accepted  
**Context:** The pipeline definition requires checkpointing every state transition, including per-PR stages such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. Automated workflows need durable progress tracking and recoverability.  
**Decision:** Persist a checkpoint at every stage transition and at each required per-PR milestone. Treat checkpoint creation as part of the transition contract rather than optional logging.  
**Consequences:** Recovery, retries, and auditability depend on checkpoint data being complete and current. Stage handlers must not advance process state without recording the transition. Any redesign of state names or ordering must preserve explicit durable checkpoints.  
**Rejected alternatives:**  
- Checkpoint only major stages — rejected because per-PR progress must be resumable and auditable at finer granularity.  
- Use transient logs instead of durable checkpoints — rejected because logs do not provide reliable recovery semantics.  
- Checkpoint only on failure — rejected because successful transitions are equally necessary for resume and traceability.

## Gate decisions must require explicit operator approval or correction before merge
**Status:** Accepted  
**Context:** The pipeline includes a final gate where the operator approves or corrects before merge. Automated generation and testing do not eliminate the need for human control over final integration.  
**Decision:** Require an explicit gate decision by an operator before merge. Do not permit the subsystem to auto-merge solely on the basis of generated code, test success, or CI pass status.  
**Consequences:** Merge automation must stop at a human approval boundary. UI, CLI, or API flows must expose pending gate state and accept explicit approval or correction actions. Delivery latency may increase, but final control remains with the operator.  
**Rejected alternatives:**  
- Auto-merge when tests and CI pass — rejected because the pipeline defines operator gating as mandatory.  
- Make human review configurable per repository — rejected because this weakens a core control for the subsystem.  
- Allow silent timeout-based approval — rejected because absence of intervention is not equivalent to an explicit gate decision.

## CI workflow generation must produce platform-appropriate crafted workflows
**Status:** Accepted  
**Context:** The build pipeline defines generated workflows `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. Workflow generation is handled by a critical file and must align with repository path constraints.  
**Decision:** Generate CI workflows under `.github` using the crafted workflow naming convention. Use `crafted-ci.yml` targeting `ubuntu-latest` for standard workflows and `crafted-ci-macos.yml` when Swift or macOS-specific execution is required.  
**Consequences:** Workflow generation logic must distinguish platform/runtime needs and write only to approved CI paths. Repositories that need macOS execution must receive a separate crafted macOS workflow rather than overloading the default Linux workflow. Naming and placement become contractually stable for downstream tooling.  
**Rejected alternatives:**  
- Generate a single generic workflow for all stacks — rejected because Swift/macOS workloads require distinct runner behavior.  
- Place generated workflows outside `.github` and copy them later — rejected because GitHub Actions only recognizes workflow files in the standard location and delayed copying complicates security validation.  
- Use arbitrary workflow names per project — rejected because stable names are needed for orchestration and discovery.

## Source-of-truth documentation must be read from forge-docs before implementation changes
**Status:** Accepted  
**Context:** The repository structure declares `forge-docs/` as the location where all TRDs and PRDs live and explicitly states they must be read before building. CraftedApp must conform to documented requirements rather than infer behavior from code alone.  
**Decision:** Treat documents in `forge-docs/` as the authoritative source for subsystem behavior and implementation constraints. Require implementation changes to be aligned against relevant TRDs/PRDs before modifying code.  
**Consequences:** Engineers and agents must consult documentation first, especially for critical subsystems and architectural behavior. Code that conflicts with documented decisions must be treated as suspect until reconciled. Implementation shortcuts based only on local code context are not acceptable.  
**Rejected alternatives:**  
- Treat code as the sole source of truth once implementation exists — rejected because the repository explicitly defines TRDs and PRDs as authoritative.  
- Read documentation only for new features — rejected because maintenance changes can still violate documented constraints.  
- Depend on inline comments instead of formal docs — rejected because comments do not replace repository-level design authority.

## Critical subsystem files must be treated as constrained modification zones
**Status:** Accepted  
**Context:** Several files are identified as critical before modification, including `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Changes in these files have broad system impact.  
**Decision:** Apply heightened change discipline to critical files. Require modifications to preserve the documented responsibility of each file and prohibit incidental cross-cutting logic from being introduced into them without explicit design justification.  
**Consequences:** Implementers must avoid opportunistic edits that expand scope within critical modules. Security, orchestration, GitHub I/O, consensus behavior, and CI generation remain clearly bounded. When new behavior affects these areas, dedicated helper modules or ADR-backed refactors should be preferred over uncontrolled growth in critical files.  
**Rejected alternatives:**  
- Treat all files uniformly during implementation — rejected because the repository explicitly marks these files as high-impact.  
- Freely add unrelated helper logic into critical files for convenience — rejected because it accelerates erosion of architectural boundaries.  
- Protect critical files by forbidding edits entirely — rejected because the subsystem must still evolve; discipline is required, not immutability.

## Validation and fix loops must remain staged rather than collapsed into a single pass
**Status:** Accepted  
**Context:** The build pipeline defines separate validation steps including parsing, linting, import checks, and a bounded pytest fix loop with up to 20 attempts and failure-type-aware strategy. This staged design supports targeted remediation and observability.  
**Decision:** Preserve validation as explicit staged checks and preserve the bounded fix loop as a distinct phase. Do not collapse parse, lint, import, and test remediation into a single opaque “verify and fix” operation.  
**Consequences:** The subsystem must expose intermediate validation outcomes and tailor remediation to failure type. Retry logic must remain bounded, observable, and strategically differentiated rather than open-ended. Implementations will be easier to debug and safer to resume from checkpoints.  
**Rejected alternatives:**  
- Run one monolithic validation command and infer failures from aggregate output — rejected because it obscures failure type and weakens targeted recovery.  
- Permit unbounded test-fix retries — rejected because the pipeline explicitly bounds attempts and unbounded loops are unsafe.  
- Skip early parse/lint/import checks and rely on tests only — rejected because fast-fail validation reduces wasted fix-loop cycles and improves error isolation.