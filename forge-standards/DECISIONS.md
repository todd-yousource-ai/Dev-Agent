# DECISIONS.md

## [Adopt the documented monorepo layout as a hard architectural boundary]
**Status:** Accepted

**Context:** ForgeAgent operates within a repository that already defines authoritative locations for requirements, standards, implementation, app shell, and tests. The TRDs and README identify `forge-docs/` as the source of truth for product and technical requirements, `forge-standards/` as the location for architecture and implementation constraints, `src/` as the Python backend, `Crafted/` and `CraftedTests/` as the macOS shell and its tests, and `tests/` as the Python test suite. The subsystem must not blur these boundaries or invent parallel structure.

**Decision:** Preserve and implement ForgeAgent within the documented repository layout. Treat `forge-docs/` as read-first source material, `forge-standards/` as binding engineering constraints, `src/` as the only location for Python backend runtime code, `tests/` as the only location for Python automated tests, and `Crafted/` plus `CraftedTests/` as the Swift application shell boundary.

**Consequences:** Implementation must not relocate subsystem code outside `src/`, must not place generated backend logic into documentation or standards folders, and must not create duplicate standards or requirements directories. Any tooling that consumes requirements must read from `forge-docs/` rather than embedded copies. Any change that affects the app shell must respect the separation between Python backend and Swift frontend. Build and test automation must assume this directory structure is stable.

**Rejected alternatives:**  
- Storing ForgeAgent code in a dedicated top-level `agents/` directory: rejected because it would diverge from the documented repository contract and fragment the backend runtime.  
- Copying TRD requirements into code-local configuration files as a second source of truth: rejected because it creates drift and weakens the authority of `forge-docs/`.  
- Mixing Python and Swift implementation under a feature-oriented directory tree: rejected because the repository explicitly separates backend runtime from the macOS shell.

## [Treat designated critical files as controlled integration points]
**Status:** Accepted

**Context:** Several files are explicitly identified as critical because changes to them have system-wide impact: `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. ForgeAgent must integrate with these components carefully because they define generation flow, orchestration, GitHub I/O, security boundaries, and CI generation.

**Decision:** Route ForgeAgent behavior through the designated critical files only via deliberate, minimal, well-tested changes. Treat these files as controlled integration points whose interfaces and invariants must be preserved unless a requirements-driven change explicitly demands otherwise.

**Consequences:** New subsystem functionality must prefer extension over invasive rewrites in critical files. Changes to orchestration, code generation, path handling, GitHub operations, or CI generation require focused tests and review because they affect all PRs and repository operations. ForgeAgent code must not bypass these components with shadow implementations.

**Rejected alternatives:**  
- Reimplementing GitHub, path validation, or orchestration logic in new helper modules to avoid touching critical files: rejected because it would create duplicate logic and inconsistent behavior.  
- Broad refactors of critical files during feature delivery: rejected because they increase system-wide risk and obscure the intent of subsystem changes.  
- Treating critical files as ordinary modules with no extra constraints: rejected because the TRDs explicitly identify them as high-impact boundaries.

## [Enforce a maximum cyclomatic complexity of 15 per stage and orchestration unit]
**Status:** Accepted

**Context:** The build pipeline documentation states that every stage has a maximum cyclomatic complexity of 15, and `src/build_director.py` is specifically called out as strictly enforcing this constraint. ForgeAgent participates in orchestration and must remain decomposable and testable.

**Decision:** Keep each ForgeAgent stage handler, orchestration function, and decision-heavy unit at or below cyclomatic complexity 15. Split behavior into smaller functions or explicit strategy objects rather than accumulating conditional branches in a single unit.

**Consequences:** Implementation must prefer composition and stage-specific helpers over large coordinator methods. Failure handling, retries, and branching logic must be factored into separate units to stay within the limit. Reviews should reject new orchestration code that centralizes too many branches in one place even if functionally correct.

**Rejected alternatives:**  
- Allowing higher complexity in orchestration code because pipeline logic is inherently branchy: rejected because the documented rule is explicit and intended to preserve maintainability.  
- Enforcing complexity only at module level rather than per stage/function: rejected because the TRD language constrains every stage, not just aggregate files.  
- Deferring complexity control to later refactoring: rejected because complexity debt in orchestration code compounds quickly and undermines checkpointed stage transitions.

## [Implement ForgeAgent as a checkpointed stage machine]
**Status:** Accepted

**Context:** The build pipeline specifies discrete stages and requires every state transition to be checkpointed, including per-PR progression through `branch_opened → code_generated → tests_passed → committed → ci_passed`. This implies ForgeAgent must model work as explicit stages rather than opaque long-running procedures.

**Decision:** Represent ForgeAgent execution as a checkpointed state machine with explicit stage transitions and durable recording of each transition, including per-PR states defined by the build pipeline.

**Consequences:** Long-running or multi-step tasks must be resumable from checkpoints. The subsystem must emit state transitions as first-class events or persisted records rather than relying on in-memory progress only. Recovery logic must resume from the last valid checkpoint instead of restarting all work by default. Any stage addition must define transition semantics and checkpoint behavior.

**Rejected alternatives:**  
- Using a single linear job function with logs as the only progress record: rejected because logs are insufficient for deterministic resume and do not satisfy the checkpoint requirement.  
- Checkpointing only terminal states such as success and failure: rejected because the requirements explicitly call for every state transition to be checkpointed.  
- Tracking state only at repository level and not per PR: rejected because per-PR stage transitions are explicitly required.

## [Preserve the documented pipeline stage order and semantics]
**Status:** Accepted

**Context:** The README defines a build pipeline with ordered stages, including generation validation and a failure-type-aware fix loop, followed by test/CI and an operator gate before merge. ForgeAgent is part of this execution chain and must not reorder or collapse stages in ways that invalidate the documented process.

**Decision:** Implement ForgeAgent so that it honors the documented pipeline order and semantics: generation validation must occur before fix attempts, fix attempts are capped and strategy-aware, CI generation and execution follow local validation, and operator approval is required before merge.

**Consequences:** The subsystem may optimize within a stage but must not skip required stages, move merge before approval, or run fix loops without prior validation signals. Any internal APIs should expose stage boundaries clearly. Test suites must validate stage ordering and disallow illegal transitions.

**Rejected alternatives:**  
- Running CI before local validation to catch everything remotely: rejected because it wastes resources and contradicts the documented local validation-first flow.  
- Auto-merging after local tests pass: rejected because the process includes CI and an operator gate before merge.  
- Collapsing validation and fix loop into one opaque “self-heal” stage: rejected because explicit stage semantics are required for checkpointing, observability, and control.

## [Cap automated fix attempts at 20 and make repair strategy failure-type-aware]
**Status:** Accepted

**Context:** The pipeline documentation specifies a fix loop with `pytest` up to 20 attempts and requires a failure-type-aware strategy. ForgeAgent must therefore avoid unbounded retries and must classify failures to choose appropriate remediation behavior.

**Decision:** Limit automated fix loops to a maximum of 20 attempts and select repair actions based on classified failure type rather than applying a generic retry-or-regenerate approach.

**Consequences:** The subsystem must maintain attempt counts, stop deterministically at the configured cap, and record why each attempt was made. Failure parsing and taxonomy mapping become required implementation concerns. Generic blind retries are insufficient. Persistent failures must escalate rather than loop indefinitely.

**Rejected alternatives:**  
- Unlimited retries until success: rejected because it risks runaway automation and directly violates the documented cap.  
- A small arbitrary cap such as 3 or 5 attempts: rejected because it diverges from the specified pipeline contract.  
- Applying the same fix strategy to all failures: rejected because the requirements explicitly call for failure-type-aware handling.

## [Centralize all GitHub I/O through src/github_tools.py]
**Status:** Accepted

**Context:** `src/github_tools.py` is identified as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. ForgeAgent must interact with GitHub for branch, commit, PR, and file operations without bypassing these controls.

**Decision:** Perform all GitHub reads and writes for ForgeAgent through `src/github_tools.py` or its explicitly exposed interfaces. Do not invoke ad hoc GitHub clients or direct API calls from subsystem code paths.

**Consequences:** GitHub-related behavior such as retries, rate limiting, SHA-safe updates, and validation remains consistent across the system. New GitHub operations may require extending `src/github_tools.py` rather than calling external libraries directly from feature modules. Tests should mock at this boundary instead of mocking multiple divergent clients.

**Rejected alternatives:**  
- Calling the GitHub API directly from ForgeAgent modules for convenience: rejected because it would bypass rate limiting, SHA protocol, and validation guarantees.  
- Using local git CLI commands as the primary integration path: rejected because the documented critical file establishes GitHub I/O through `src/github_tools.py`.  
- Introducing a second GitHub abstraction dedicated to ForgeAgent: rejected because it duplicates a critical cross-cutting concern.

## [Route every write path through src/path_security.py]
**Status:** Accepted

**Context:** `src/path_security.py` is explicitly defined as the security boundary, and every write path must pass through it. ForgeAgent generates and modifies files, so it is directly exposed to path traversal and repository boundary risks.

**Decision:** Validate and authorize every filesystem write, update, or generated output path through `src/path_security.py` before performing the operation. Do not write files via unchecked path concatenation or direct path use.

**Consequences:** File generation utilities must be designed around validated repository-relative paths. Any code path that writes temporary, generated, or committed files must invoke the shared security boundary. Tests must include malicious and malformed path cases. Convenience write helpers that bypass validation are prohibited.

**Rejected alternatives:**  
- Validating paths only for user-supplied inputs and skipping internal writes: rejected because internal generation paths can still be corrupted by logic errors or compromised upstream inputs.  
- Relying on `pathlib` normalization alone: rejected because normalization is not equivalent to policy enforcement.  
- Implementing per-module path checks: rejected because a single shared security boundary is explicitly required.

## [Generate CI workflows through src/ci_workflow.py and preserve platform split]
**Status:** Accepted

**Context:** CI workflow generation is identified as a critical responsibility of `src/ci_workflow.py`, and the documented pipeline distinguishes `crafted-ci.yml` on `ubuntu-latest` from `crafted-ci-macos.yml` for Swift. ForgeAgent must generate or update CI in a way that respects this separation.

**Decision:** Create and modify CI workflows only through `src/ci_workflow.py`, preserving the documented split between general/backend CI on Ubuntu and Swift/macOS CI for the Crafted application shell.

**Consequences:** ForgeAgent must not emit handcrafted workflow YAML from arbitrary modules. CI changes must maintain the Linux/macOS distinction and avoid collapsing Swift validation into Ubuntu-only workflows. Tests for workflow generation should assert expected platform targeting and file outputs.

**Rejected alternatives:**  
- Generating workflow YAML directly inside pipeline orchestration code: rejected because it bypasses the designated critical file and central policy.  
- Using a single universal CI workflow for all technologies: rejected because Swift/macOS requirements differ and the documentation explicitly specifies separate workflows.  
- Leaving CI workflow generation entirely manual: rejected because the subsystem participates in automated pipeline execution and must produce consistent CI artifacts.

## [Require operator approval before merge]
**Status:** Accepted

**Context:** The documented pipeline includes a final gate where the operator approves or corrects before merge, and every gate decision is checkpointed. ForgeAgent must therefore stop before merge and expose enough state for a human decision.

**Decision:** Do not allow ForgeAgent to merge changes autonomously. Require an explicit operator approval checkpoint before any merge action proceeds.

**Consequences:** The subsystem must surface a pending-review state and persist gate decisions. Merge APIs and automation must enforce the presence of an approval record. UX and status reporting must support human review of generated changes, CI results, and unresolved risks. Fully unattended merge flows are out of scope.

**Rejected alternatives:**  
- Auto-merging when tests and CI pass: rejected because the documented process explicitly requires operator approval.  
- Optional approval only for risky changes: rejected because the gate is a general pipeline stage, not an exception path.  
- Email or log-based implied approval: rejected because gate decisions must be explicit and checkpointed.

## [Use document-first development: read TRDs before implementing or modifying ForgeAgent]
**Status:** Accepted

**Context:** The repository structure states that all TRDs and PRDs live in `forge-docs/` and must be read before building. ForgeAgent is constrained by cross-cutting requirements spanning consensus, pipeline, multi-agent coordination, GitHub integration, security, CI, and backend runtime.

**Decision:** Require implementation and modification of ForgeAgent to begin from the authoritative documents in `forge-docs/`, with subsystem behavior derived from those documents before code changes are made.

**Consequences:** Contributors must consult `forge-docs/` for requirements interpretation rather than inferring behavior solely from existing code. Design and implementation decisions should trace back to documented requirements. When code and documents diverge, the documents are the initial authority for reconciliation unless formally superseded.

**Rejected alternatives:**  
- Treating the current codebase as the sole source of truth: rejected because the repository explicitly designates the documents as authoritative.  
- Maintaining ForgeAgent-specific requirements in code comments only: rejected because it fragments the requirements model and hides rationale from the standards process.  
- Reading only directly related TRDs and ignoring cross-cutting ones such as security or CI: rejected because ForgeAgent interacts with multiple critical system boundaries.

## [Maintain a strict backend–app shell separation]
**Status:** Accepted

**Context:** The repository separates Python backend runtime in `src/` from the Swift/SwiftUI macOS shell in `Crafted/`. TRD-1 further defines app-shell view flow, indicating that UI concerns are independently structured from backend execution. ForgeAgent belongs to the backend subsystem and must not entangle itself with macOS UI implementation details.

**Decision:** Keep ForgeAgent logic, orchestration, state management, GitHub integration, and file generation in the Python backend. Expose any app-consumable state through defined interfaces rather than embedding Swift-specific assumptions or UI logic into backend modules.

**Consequences:** Backend modules must remain UI-agnostic. Any integration with the macOS shell must occur through stable contracts, not direct coupling to view hierarchy or SwiftUI lifecycle. Swift code should consume ForgeAgent outputs or statuses without reimplementing backend orchestration. Cross-language duplication of business logic is prohibited.

**Rejected alternatives:**  
- Moving parts of ForgeAgent orchestration into the macOS app for convenience: rejected because it would couple core automation to UI runtime and break backend separation.  
- Embedding SwiftUI state assumptions directly into Python workflow logic: rejected because the UI decision tree is a shell concern, not a backend concern.  
- Duplicating orchestration logic in both Python and Swift: rejected because it creates drift and inconsistent execution semantics.