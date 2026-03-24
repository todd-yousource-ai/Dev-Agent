# DECISIONS.md

## Repository structure is fixed around docs-first source of truth
**Status:** Accepted

**Context:** The ForgeAgent subsystem operates inside a repository where technical requirements and product requirements are already organized as the authoritative design input. The documented repository structure explicitly places all TRDs and PRDs in `forge-docs/`, implementation in `src/`, standards in `forge-standards/`, the macOS shell in `Crafted/`, Swift tests in `CraftedTests/`, and Python tests in `tests/`. ForgeAgent must be constrained by this layout so that implementation, automation, and review behavior remain predictable.

**Decision:** Treat the repository layout as immutable contract. Read requirements from `forge-docs/` before implementation, place backend runtime code in `src/`, place standards and generated rules in `forge-standards/`, place macOS shell code in `Crafted/`, and place tests only in `tests/` or `CraftedTests/` according to language.

**Consequences:** ForgeAgent may not introduce alternate top-level source trees, duplicate requirement stores, or relocate critical code paths. Implementation logic must assume `forge-docs/` is the requirements source of truth and that generated or modified files must respect the existing layout. Tooling, prompts, and validation should be written against this structure.

**Rejected alternatives:**  
- Allowing ForgeAgent to create its own subsystem-specific top-level directories was rejected because it would fragment the repository contract and make review and automation less reliable.  
- Storing working copies of TRDs inside `src/` was rejected because it would create ambiguity about the source of truth.  
- Co-locating Python and Swift tests under a single generic test directory was rejected because the repository already separates runtime domains and their test infrastructure.

## ForgeAgent must treat designated critical files as high-risk change points
**Status:** Accepted

**Context:** Several files are explicitly identified as critical because they define core orchestration, security, CI generation, and GitHub integration behavior. Changes to these files have disproportionate system-wide impact.

**Decision:** Require ForgeAgent to read and account for the following files before modifying related behavior: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. Treat modifications to these files as constrained changes that must preserve their documented responsibilities.

**Consequences:** ForgeAgent must not make incidental or opportunistic edits to critical files without first evaluating downstream effects. Design and implementation should prefer extension around these files over broad rewrites. Tests and review scrutiny should increase for any change touching these paths.

**Rejected alternatives:**  
- Treating all files as equal-risk was rejected because the TRD content explicitly identifies a smaller set of control-plane files with broader blast radius.  
- Allowing automated refactors of critical files without special handling was rejected because orchestration, security, and GitHub I/O failures would affect every generated PR.  
- Hiding criticality in code comments only was rejected because the constraint must be a subsystem-level design decision, not an informal convention.

## Pipeline stages and ordering are mandatory
**Status:** Accepted

**Context:** The build pipeline is explicitly defined as a staged process including generation validation, a bounded fix loop, test and CI execution, and an operator gate before merge. ForgeAgent participates in this pipeline and must not improvise alternate stage ordering.

**Decision:** Implement ForgeAgent workflows to follow the prescribed stage sequence, including generation validation, fix loop execution, CI generation and execution, and operator approval before merge. Do not skip, reorder, or collapse mandatory stages.

**Consequences:** Any orchestration logic in ForgeAgent must preserve stage boundaries. Intermediate artifacts, retries, and approval semantics must map to the documented pipeline stages. The subsystem cannot merge work directly from generation output without passing through validation, testing, CI, and gate phases.

**Rejected alternatives:**  
- A simplified generate-and-merge flow was rejected because it bypasses required validation and approval controls.  
- Dynamically reordering stages based on heuristics was rejected because it would weaken reproducibility and checkpoint semantics.  
- Collapsing test and CI into a single undifferentiated phase was rejected because the documented pipeline distinguishes local correction behavior from CI gate behavior.

## Cyclomatic complexity per stage is capped at 15
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is explicitly called out as enforcing this strictly. ForgeAgent must preserve this maintainability constraint.

**Decision:** Keep each ForgeAgent pipeline stage implementation at cyclomatic complexity 15 or below. When logic exceeds that threshold, refactor by extracting helpers or splitting responsibilities rather than increasing stage complexity.

**Consequences:** Stage handlers must remain narrowly scoped and composable. Complex branching behavior should be moved into explicit helper functions, strategy objects, or stage-local modules that do not cause a single stage implementation to exceed the limit. Reviews should reject additions that raise stage complexity beyond the cap.

**Rejected alternatives:**  
- Raising the limit for orchestration-heavy stages was rejected because the documented constraint is explicit and system-wide.  
- Measuring only file-level or class-level complexity was rejected because the requirement is stage-specific.  
- Ignoring complexity in generated or auto-maintained code was rejected because orchestration correctness depends on readable, reviewable stage logic.

## Every state transition must be checkpointed
**Status:** Accepted

**Context:** The pipeline documentation requires checkpointing for every state transition, including per-PR lifecycle states such as `branch_opened`, `code_generated`, `tests_passed`, `committed`, and `ci_passed`. ForgeAgent must support recovery, auditability, and deterministic progress tracking.

**Decision:** Persist a checkpoint for every ForgeAgent state transition, including all per-PR stage transitions. Do not perform implicit transitions without durable state recording.

**Consequences:** ForgeAgent must include explicit state models and durable checkpoint writes around transitions. Recovery logic should resume from the last valid checkpoint instead of recomputing uncertain state. Observability, auditing, and operator review should rely on checkpoint records rather than inferred execution history.

**Rejected alternatives:**  
- Checkpointing only major milestones was rejected because the requirement explicitly covers every state transition.  
- Keeping transition state only in memory was rejected because it prevents reliable recovery after interruption.  
- Reconstructing state from Git history or CI history alone was rejected because those sources do not fully represent internal orchestration transitions.

## Gate decisions must be logged and require operator approval before merge
**Status:** Accepted

**Context:** The pipeline defines a gate stage where the operator approves or corrects before merge, and it states that every gate decision is logged. ForgeAgent must preserve human control over final integration.

**Decision:** Require explicit operator approval before merge and log every gate decision with enough detail to reconstruct why work was approved, blocked, or corrected.

**Consequences:** ForgeAgent cannot auto-merge generated changes after successful tests and CI alone. Human-in-the-loop review is a hard constraint. Audit logs must capture gate outcomes and should be treated as part of the subsystem’s compliance and debugging surface.

**Rejected alternatives:**  
- Fully autonomous merge after green CI was rejected because it violates the documented operator gate.  
- Logging only rejected decisions was rejected because the requirement applies to every gate decision.  
- Treating comments in pull requests as sufficient logging was rejected because gate logs must be durable and systematically available to the subsystem.

## The fix loop is bounded to 20 pytest attempts and must be failure-type-aware
**Status:** Accepted

**Context:** The pipeline description specifies a fix loop with up to 20 attempts and requires a failure-type-aware strategy. ForgeAgent must correct issues iteratively without entering unbounded retry behavior.

**Decision:** Limit the ForgeAgent fix loop to a maximum of 20 pytest-driven correction attempts and select remediation strategy based on the classified failure type rather than applying generic retries.

**Consequences:** Retry orchestration must track attempt counts and stop deterministically at the configured cap. The subsystem must incorporate or consume failure classification logic to decide whether to patch code, adjust tests, halt for operator input, or surface a non-recoverable condition. Infinite or opaque retry cycles are disallowed.

**Rejected alternatives:**  
- Unlimited retries until success was rejected because it risks runaway execution and violates the explicit bound.  
- A single generic retry strategy for all failures was rejected because the pipeline requires failure-type-aware handling.  
- Using CI reruns as the main fix loop was rejected because the documented correction loop is pytest-driven and intended to resolve issues before CI gate evaluation.

## Generation validation must include parse, lint, and import checks before fix attempts
**Status:** Accepted

**Context:** The build pipeline specifies a validation sequence of `ast.parse`, `ruff`, and import checking before entering the fix loop. ForgeAgent must fail fast on invalid generated code and avoid wasting test cycles on syntax or basic hygiene errors.

**Decision:** Run generated Python outputs through syntax parsing, linting with Ruff, and import validation before invoking pytest-based correction attempts.

**Consequences:** ForgeAgent must model validation as a prerequisite stage and classify failures from these checks distinctly from test failures. Basic code invalidity must be corrected before test execution. This reduces noisy feedback and constrains the agent to a deterministic validation order.

**Rejected alternatives:**  
- Running pytest first and letting syntax errors surface indirectly was rejected because earlier checks are cheaper and explicitly required.  
- Replacing Ruff with ad hoc style checking was rejected because the pipeline names Ruff directly.  
- Deferring import validation until runtime tests was rejected because import correctness is part of the mandatory pre-test validation chain.

## GitHub interactions must be centralized through `src/github_tools.py`
**Status:** Accepted

**Context:** `src/github_tools.py` is identified as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. ForgeAgent must not bypass these protections with direct API calls scattered across the codebase.

**Decision:** Route all ForgeAgent GitHub reads and writes through `src/github_tools.py` or abstractions that preserve it as the single control point for GitHub I/O.

**Consequences:** New GitHub operations must be added to the centralized integration layer rather than implemented ad hoc in orchestration or business logic. Path validation, rate limiting, and SHA-handling behavior remain consistent across the subsystem. Reviews should reject direct GitHub API usage outside the approved control point.

**Rejected alternatives:**  
- Allowing each module to call the GitHub API directly was rejected because it duplicates security and correctness logic.  
- Splitting GitHub write operations into separate helper modules without a single authority was rejected because it weakens rate limiting and SHA protocol consistency.  
- Embedding GitHub I/O inside stage implementations was rejected because it mixes orchestration with integration concerns and bypasses centralized controls.

## All write paths must pass through `src/path_security.py`
**Status:** Accepted

**Context:** `src/path_security.py` is explicitly identified as the security boundary and states that every write path must pass through it. ForgeAgent performs file generation and modification, so path handling is a core security concern.

**Decision:** Enforce `src/path_security.py` as the only approved path validation boundary for ForgeAgent write operations. Do not write files to disk without passing the target path through this control.

**Consequences:** Any file creation, update, patch application, artifact write, or generated output in ForgeAgent must be mediated by the path security layer. This constrains implementation choices for editors, patchers, and generators. Security review can focus on one boundary instead of auditing ad hoc path logic across the subsystem.

**Rejected alternatives:**  
- Performing path validation independently in each writer was rejected because it creates inconsistent enforcement and increases bypass risk.  
- Relying on repository-relative paths without explicit validation was rejected because relative paths alone do not prevent traversal or boundary mistakes.  
- Deferring path validation to Git operations was rejected because invalid or unsafe local writes must be blocked before version control interaction.

## CI workflow generation must preserve Linux default and macOS Swift specialization
**Status:** Accepted

**Context:** The documented pipeline uses `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. ForgeAgent may generate or modify CI behavior, but it must respect the split between general CI and Swift-specific macOS execution.

**Decision:** Generate and maintain CI workflows such that general pipeline execution targets `ubuntu-latest` via `crafted-ci.yml`, while Swift-specific validation runs in `crafted-ci-macos.yml` on macOS runners.

**Consequences:** ForgeAgent must not collapse all CI into a single runner or move Swift validation to unsupported environments. Workflow generation in `src/ci_workflow.py` should preserve the platform distinction. Cross-platform changes must account for the cost and necessity of macOS execution only where Swift validation requires it.

**Rejected alternatives:**  
- Running all CI on macOS was rejected because it is slower, more expensive, and unnecessary for non-Swift work.  
- Running Swift validation on Ubuntu was rejected because the repository explicitly distinguishes macOS for Swift.  
- Combining both workflows into one generic file was rejected because the documented design separates concerns by platform and runtime.

## ForgeAgent must respect the existing root-view onboarding decision tree in the macOS shell
**Status:** Accepted

**Context:** TRD-1 defines a root view decision tree for the Crafted macOS shell, where incomplete onboarding routes to `OnboardingContainerView` and its specific sub-states. ForgeAgent may touch integration points or generated UI-adjacent code, so it must not break this application-shell contract.

**Decision:** Preserve the documented RootView onboarding decision tree and state routing semantics when modifying or generating code that affects the macOS application shell.

**Consequences:** ForgeAgent must avoid introducing alternate initial navigation paths that bypass onboarding state checks. Changes in `Crafted/` must align with the existing onboarding states and transition model. Backend-driven state assumptions must remain compatible with the shell’s documented root routing.

**Rejected alternatives:**  
- Replacing the onboarding tree with a flatter single-view bootstrap was rejected because it conflicts with the documented state model.  
- Letting backend readiness determine the first rendered screen was rejected because RootView routing is explicitly controlled by onboarding completion state.  
- Deferring shell routing decisions to implementation convenience was rejected because the TRD defines the application entry decision tree as a design constraint.