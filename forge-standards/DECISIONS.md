# DECISIONS.md

## Repository structure is fixed and document-driven
**Status:** Accepted  
**Context:** The ForgeAgent subsystem is implemented inside a larger repository whose source of truth is the TRD/PRD corpus under `forge-docs/`. The repository layout explicitly separates standards, backend runtime, tests, and the macOS shell. Unstructured relocation of files would break discoverability, implementation assumptions, and cross-team coordination.

**Decision:** Preserve the repository structure as defined by the TRDs and README. Treat `forge-docs/` as the authoritative requirements source, `forge-standards/` as the authoritative implementation constraints location, `src/` as the Python backend implementation root, `tests/` as the Python validation root, and `Crafted/` plus `CraftedTests/` as the Swift application shell and its tests. Do not introduce alternative top-level layouts or move critical subsystem files without an explicit architecture decision.

**Consequences:** Implementation must assume stable paths and responsibilities for major directories. Tooling, tests, build orchestration, and developer workflows may rely on these locations. Any new ForgeAgent code must fit within the existing repository boundaries rather than creating parallel structures. Documentation-first development is enforced because engineers must consult `forge-docs/` before making changes.

**Rejected alternatives:**  
- **Reorganize by feature area at the repository root:** Rejected because it conflicts with the documented canonical layout and would make TRD alignment harder.  
- **Treat code as the source of truth and docs as advisory:** Rejected because the repository explicitly defines the TRDs/PRDs as the source of truth.  
- **Create a separate ForgeAgent root outside `src/`:** Rejected because it fragments the backend runtime and complicates standards enforcement.

## Critical files are controlled interfaces and must be read before modification
**Status:** Accepted  
**Context:** Several files are identified as high-risk change points because they define core generation, orchestration, GitHub I/O, path security, and CI workflow generation. Changes to these files have repository-wide impact and can silently introduce security, correctness, or operational regressions.

**Decision:** Treat `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py` as controlled interfaces. Read and understand the existing implementation and surrounding constraints before modifying them. Route changes through tests and preserve each file’s declared responsibility boundary.

**Consequences:** Engineers cannot safely make isolated edits to these files without understanding downstream effects. Refactors in these areas must be narrow, justified, and validated against pipeline, security, and integration behavior. New functionality should prefer extension around these files rather than casual modification inside them.

**Rejected alternatives:**  
- **Allow opportunistic edits when implementing nearby features:** Rejected because these files affect every PR build, all GitHub operations, or the repository security boundary.  
- **Duplicate logic into new helper modules to avoid touching critical files:** Rejected because it creates divergent behavior and weakens the intended control points.  
- **Treat only security-sensitive files as critical:** Rejected because orchestration and consensus errors are also systemic failures.

## The build pipeline shall remain staged, explicit, and checkpointed
**Status:** Accepted  
**Context:** The README defines a multi-stage build pipeline with explicit stages, including parse/lint/import checks, a bounded fix loop, test/CI execution, and an operator gate. It also states that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`.

**Decision:** Implement ForgeAgent workflow as an explicit staged pipeline with named transitions and persisted checkpoints at every stage transition. Preserve the documented phase model, including generation, validation, fix loop, CI execution, and operator gate. Do not collapse stages into opaque monolithic execution.

**Consequences:** Pipeline state must be inspectable, resumable, and auditable. Failures can be localized to a stage and replayed from checkpoints. State persistence becomes a mandatory implementation concern, not an optional observability feature. Any new pipeline behavior must integrate into the checkpoint model rather than bypassing it.

**Rejected alternatives:**  
- **Single-pass orchestration without durable stage records:** Rejected because it prevents resumability and weakens auditability.  
- **Best-effort logging instead of formal checkpoints:** Rejected because logs do not provide structured state transition recovery.  
- **Dynamic stage ordering with no fixed lifecycle:** Rejected because the TRD-defined pipeline requires explicit and predictable progression.

## Cyclomatic complexity per stage is capped at 15
**Status:** Accepted  
**Context:** The build pipeline documentation explicitly states that every stage has a maximum cyclomatic complexity of 15. `src/build_director.py` is called out as having this limit strictly enforced. This is a maintainability and reviewability constraint, not a suggestion.

**Decision:** Enforce a maximum cyclomatic complexity of 15 for every pipeline stage implementation. Split logic into helpers, strategies, or subcomponents when a stage approaches the limit. Do not centralize branching behavior into a single stage function that exceeds the cap.

**Consequences:** Stage implementations must remain small and composable. Complex decision-making must be expressed through decomposition rather than nested branching. Reviews should reject stage changes that push complexity above the limit even if functionally correct.

**Rejected alternatives:**  
- **Permit exceptions for orchestration-heavy stages:** Rejected because the documented rule applies to every stage.  
- **Measure complexity only at the module level:** Rejected because the requirement is stage-specific.  
- **Rely on reviewer judgment without a hard threshold:** Rejected because the TRD states a strict limit.

## Validation order shall be parse, lint, import-check, then targeted fixing
**Status:** Accepted  
**Context:** The build pipeline defines a specific quality sequence: `ast.parse → ruff → import check`, followed by a failure-aware fix loop. Ordering matters because earlier checks are cheaper and provide prerequisite correctness for later checks.

**Decision:** Execute generated Python validation in the documented order: syntax parsing first, linting second, import validation third, and only then enter the targeted fix loop. Do not reorder these checks or skip earlier gates when attempting automated repair.

**Consequences:** Syntax-invalid outputs are rejected before spending cycles on lint or tests. Automated repair logic can assume increasingly stronger invariants as it progresses. Diagnostics and retry strategies can be mapped to a stable validation sequence.

**Rejected alternatives:**  
- **Run tests before static checks:** Rejected because it wastes runtime on code that may not even parse or import.  
- **Use linting as the first check:** Rejected because syntax validity is the cheapest prerequisite gate.  
- **Combine all checks in a single tool invocation:** Rejected because it obscures failure classification and weakens targeted remediation.

## The automated fix loop is bounded to 20 attempts and must be failure-type-aware
**Status:** Accepted  
**Context:** The pipeline description specifies a fix loop with `pytest` and up to 20 attempts, using a failure-type-aware strategy. This implies bounded automation, controlled retries, and categorization-driven repair rather than undirected regeneration.

**Decision:** Limit the automated fix loop to a maximum of 20 attempts and choose remediation strategies based on classified failure types. Stop retrying when the limit is reached or when failure conditions indicate non-progress. Do not implement unbounded retries or generic “try again” loops.

**Consequences:** The subsystem remains predictable in cost and runtime. Failure analysis becomes a required precursor to retries. Implementation must maintain enough structured diagnostic data to distinguish failure types and apply the correct remediation path.

**Rejected alternatives:**  
- **Unlimited retries until tests pass:** Rejected because it risks runaway execution and hides non-convergent failures.  
- **A very small retry budget such as 3 attempts:** Rejected because the documented design explicitly allows up to 20 attempts.  
- **Blindly regenerate on every failure:** Rejected because the strategy must be failure-type-aware.

## CI workflow generation shall target Ubuntu by default and macOS for Swift
**Status:** Accepted  
**Context:** The build pipeline documentation defines two generated workflow targets: `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. The repository also contains a Swift/SwiftUI shell under `Crafted/`, which requires platform-appropriate validation.

**Decision:** Generate CI workflows with platform specialization: use Ubuntu for the standard backend workflow and macOS for Swift-related validation. Keep these workflows distinct rather than collapsing all jobs into a single generic runner definition.

**Consequences:** Backend CI remains cost-effective and fast on Ubuntu, while Swift/macOS validation remains accurate to platform requirements. Workflow generation logic must understand language/platform boundaries. Changes to CI must preserve the documented file outputs and execution intent.

**Rejected alternatives:**  
- **Run all CI on macOS:** Rejected because it is unnecessarily expensive and slower for non-Swift workloads.  
- **Run all CI on Ubuntu only:** Rejected because Swift/macOS shell validation requires macOS semantics.  
- **Generate a single mixed workflow file only:** Rejected because the documented outputs are separate and purpose-specific.

## Operator approval is a mandatory gate before merge
**Status:** Accepted  
**Context:** The pipeline defines a final gate where the operator approves or corrects before merge. This establishes human oversight over automated changes and prevents fully autonomous merge behavior.

**Decision:** Require an explicit operator gate before merge. ForgeAgent may prepare artifacts, surface recommendations, and advance through automated stages, but it shall not treat CI success alone as authority to merge without human approval or correction.

**Consequences:** Full end-to-end autonomy is intentionally constrained. UX and orchestration must preserve a pause point for review and intervention. Merge automation must integrate with operator decisions rather than bypassing them.

**Rejected alternatives:**  
- **Automatic merge after CI passes:** Rejected because it violates the documented operator gate.  
- **Optional human review only for high-risk changes:** Rejected because the gate is defined as a standard stage, not a conditional exception.  
- **Post-merge human audit:** Rejected because the required control point is before merge.

## All write paths must pass through the path security boundary
**Status:** Accepted  
**Context:** `src/path_security.py` is explicitly identified as the security boundary, and every write path must pass through it. ForgeAgent interacts with repository files and generated artifacts, making path validation a primary defense against traversal and repository escape vulnerabilities.

**Decision:** Route every filesystem write, overwrite, move, or generated artifact path through the path security layer. Do not perform direct path concatenation or raw filesystem writes that bypass `src/path_security.py`.

**Consequences:** File-producing code must be structured around approved path validation APIs. Security review can focus on a single boundary for write-path enforcement. Convenience shortcuts in utility code are prohibited if they bypass validation.

**Rejected alternatives:**  
- **Validate only user-supplied paths:** Rejected because generated or derived paths can also become unsafe.  
- **Perform ad hoc validation in each module:** Rejected because it duplicates logic and weakens the single security boundary.  
- **Rely on repository-relative assumptions without validation:** Rejected because assumptions are not enforcement.

## All GitHub I/O shall be centralized in github_tools with path validation, rate limiting, and SHA protocol
**Status:** Accepted  
**Context:** `src/github_tools.py` is designated as the locus for GitHub I/O and specifically called out as handling path validation, rate limiting, and SHA protocol. GitHub interactions are high-impact and must remain consistent across the subsystem.

**Decision:** Centralize all GitHub reads, writes, updates, and metadata operations in `src/github_tools.py` or tightly controlled interfaces built on it. Enforce path validation, API rate limiting behavior, and SHA-based update semantics through this layer. Do not call GitHub APIs directly from feature code.

**Consequences:** GitHub behavior stays consistent, secure, and easier to test. Concurrency and update correctness can rely on a single SHA protocol implementation. Feature code becomes dependent on the central abstraction rather than vendor-specific call sites.

**Rejected alternatives:**  
- **Allow direct GitHub API calls in individual modules:** Rejected because it would fragment rate limiting, path validation, and conflict handling.  
- **Use a generic SCM abstraction that hides SHA semantics:** Rejected because the documented protocol explicitly depends on GitHub SHA behavior.  
- **Centralize only write operations and leave reads distributed:** Rejected because reads also affect rate limiting and path safety assumptions.

## Consensus logic in src/consensus.py is the core generation loop and must remain the single orchestration authority for generation
**Status:** Accepted  
**Context:** `src/consensus.py` is identified as the core generation loop, and changes there affect every PR the agent builds. This makes it the central behavioral control point for generated output.

**Decision:** Keep generation consensus logic centralized in `src/consensus.py`. New generation policies, voting heuristics, or output selection behavior must integrate with this module rather than creating parallel generation loops elsewhere in the codebase.

**Consequences:** Generation behavior remains consistent across PRs. Testing and evaluation can focus on a single decision engine. Feature teams must extend the established consensus mechanism rather than introducing independent generation pathways.

**Rejected alternatives:**  
- **Embed generation logic inside each pipeline stage:** Rejected because it would duplicate core behavior and produce inconsistent outputs.  
- **Create multiple specialized consensus engines per feature area:** Rejected because the subsystem defines one core generation loop affecting all PRs.  
- **Move consensus decisions into the UI layer:** Rejected because generation authority belongs in the backend runtime.

## The root application flow shall preserve the documented onboarding-first decision tree
**Status:** Accepted  
**Context:** TRD-1 defines a root view decision tree in which incomplete onboarding routes users into `OnboardingContainerView` and its staged subviews before reaching the rest of the application. ForgeAgent changes that interact with app-shell state must not violate this entry flow.

**Decision:** Preserve the documented onboarding-first root view decision tree in the macOS shell. Any ForgeAgent-driven UI integration must respect `OnboardingState` gating and shall not bypass incomplete onboarding to expose authenticated or operational screens prematurely.

**Consequences:** UI integration work must align backend readiness and credential/state requirements with onboarding state. Shortcut flows that jump directly into operational views are constrained. Testing must cover routing behavior for each onboarding state.

**Rejected alternatives:**  
- **Allow direct entry into the main app if partial configuration exists:** Rejected because it conflicts with the documented root decision tree.  
- **Move onboarding behind the main view as a modal flow:** Rejected because the TRD defines onboarding as the root-level branch.  
- **Permit ForgeAgent actions before onboarding completion:** Rejected because credentials and environment prerequisites are part of onboarding.