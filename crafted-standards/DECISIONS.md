# DECISIONS.md

## [Adopt the documented repository structure as a hard implementation boundary]
**Status:** Accepted

**Context:** CraftedAgent operates inside a repository whose source of truth is explicitly structured. The TRDs and PRDs live under `forge-docs/`, standards live under `forge-standards/`, and implementation code lives under `src/` and other approved project roots. Because the agent reads requirements and writes code across these boundaries, a fixed repository model is required to prevent ambiguity, misplaced outputs, and accidental drift from the documented system layout.

**Decision:** Treat the documented repository layout as mandatory. Read TRDs and PRDs from `forge-docs/`, treat `forge-standards/` as the governing standards location, and limit implementation behavior to the expected project roots defined by repository policy.

**Consequences:** Implementation must not infer alternate layouts dynamically as a primary mode of operation. File discovery, document loading, code generation, and validation logic must be built around the documented top-level directories. New behaviors that require additional top-level locations must be explicitly added to policy rather than silently supported.

**Rejected alternatives:**  
- Auto-detect arbitrary repository layouts at runtime — rejected because it increases ambiguity and makes path security and standards enforcement unreliable.  
- Allow each subsystem to define its own document locations — rejected because TRDs are the source of truth and must remain discoverable in a single canonical location.  
- Permit writes anywhere under the repo if the path exists — rejected because it weakens safety boundaries and makes generated changes harder to audit.

## [Require critical-file awareness before modifying core agent behavior]
**Status:** Accepted

**Context:** Several files are identified as critical because changes to them affect global agent behavior, security, or CI output. These include `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, and `src/ci_workflow.py`. CraftedAgent must treat these files differently from ordinary implementation files because modifications can have repository-wide impact.

**Decision:** Require explicit critical-file awareness in any implementation touching the identified critical files. Before modifying those files, read and evaluate their role-specific constraints, and preserve their system-level contracts.

**Consequences:** Changes in these files must be conservative, reviewable, and constrained by their stated purpose. Implementation must avoid incidental refactors in these locations. Cross-cutting behavior such as generation flow, pipeline orchestration, GitHub I/O, path validation, and CI generation must not be changed indirectly without recognizing those files as protected integration points.

**Rejected alternatives:**  
- Treat all source files uniformly — rejected because these files define high-risk boundaries and require stronger change discipline.  
- Encode no special handling and rely only on tests — rejected because tests may not fully capture orchestration, security, and integration regressions.  
- Freeze critical files entirely — rejected because evolution is necessary, but must happen under tighter constraints rather than prohibition.

## [Enforce allowed-root path security for all repository writes]
**Status:** Accepted

**Context:** The GitHub integration lessons learned establish that writes to unexpected root directories fail silently or are rejected by security guards. The repository uses an allowlist of valid root directories, including `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Dot-prefixed roots such as `.github` require explicit allowlisting.

**Decision:** Validate every write target against an explicit allowlist of approved repository root directories, including dot-prefixed roots only when specifically permitted.

**Consequences:** CraftedAgent must not create, modify, or commit files outside approved roots. Path validation must occur before write and commit operations, not after. Support for new root directories requires an intentional allowlist change. CI workflow generation under `.github` must be explicitly supported rather than handled as a special bypass.

**Rejected alternatives:**  
- Allow any path under the repository checkout — rejected because it weakens the security boundary and permits unintended writes.  
- Validate only on commit, not on file creation — rejected because unsafe intermediate writes still violate the intended boundary.  
- Block dot-prefixed roots categorically — rejected because `.github` is required for CI workflow generation.

## [Route all write-path decisions through the path security boundary]
**Status:** Accepted

**Context:** `src/path_security.py` is designated as the security boundary and every write path must pass through it. CraftedAgent cannot safely perform repository mutations if multiple independent path-validation mechanisms exist, because inconsistent enforcement would create bypasses.

**Decision:** Centralize write-path authorization through the path security boundary and prohibit alternate write validation paths.

**Consequences:** All file creation, modification, staging, and commit preparation logic must call the shared path security mechanism. Helper utilities and GitHub integration code must not implement separate permissive validators. Security fixes to path handling become effective system-wide because enforcement is centralized.

**Rejected alternatives:**  
- Let each subsystem validate its own paths — rejected because duplicated logic leads to inconsistent enforcement and bypass risk.  
- Validate only external inputs while trusting internal path construction — rejected because internal composition bugs can still produce unsafe paths.  
- Use ad hoc checks at call sites instead of a boundary module — rejected because such checks are difficult to audit and easy to omit.

## [Preserve the core generation loop as a globally shared control point]
**Status:** Accepted

**Context:** `src/consensus.py` is identified as the core generation loop, and changes there affect every PR the agent builds. CraftedAgent needs a stable orchestration locus for generation behavior so that task execution, code synthesis, and downstream pipeline stages remain coherent.

**Decision:** Implement and evolve generation behavior through the shared consensus loop rather than through fragmented per-feature generation entry points.

**Consequences:** Feature work that alters how code is generated must integrate with the consensus loop’s contract. Per-task shortcuts that bypass the loop are disallowed unless explicitly elevated into the shared mechanism. Global generation behavior remains traceable and testable in one place.

**Rejected alternatives:**  
- Create independent generation loops per capability — rejected because it fragments behavior and makes PR outcomes inconsistent.  
- Put generation control inside GitHub integration or build orchestration layers — rejected because those layers are consumers of generation, not its authoritative control point.  
- Permit direct code generation from feature modules — rejected because bypasses would undermine consistency across PRs.

## [Keep pipeline orchestration within the build director and under the complexity limit]
**Status:** Accepted

**Context:** `src/build_director.py` owns pipeline orchestration, and the complexity-15 limit is strictly enforced. The README further states that every stage has a maximum cyclomatic complexity of 15. CraftedAgent must preserve both the ownership boundary and the structural simplicity constraint.

**Decision:** Centralize pipeline orchestration in the build director and enforce a maximum cyclomatic complexity of 15 for every pipeline stage and orchestration unit.

**Consequences:** Complex branching logic must be decomposed into smaller helpers rather than accumulated inside orchestration methods. New pipeline features must fit the existing staged architecture without creating oversized controller functions. Complexity budget becomes a design constraint, not merely a lint target.

**Rejected alternatives:**  
- Allow orchestration complexity to grow with new features — rejected because the documented limit is explicit and protects maintainability.  
- Spread orchestration state transitions across many unrelated modules — rejected because it obscures stage ownership and makes checkpointing harder.  
- Enforce complexity only at file level instead of per stage — rejected because the requirement applies to every stage, not just aggregate modules.

## [Use a staged build pipeline with mandatory validation and fix-loop behavior]
**Status:** Accepted

**Context:** The README defines a staged build pipeline including validation steps `ast.parse → ruff → import check`, followed by a fix loop using `pytest` for up to 20 attempts with failure-type-aware strategy. This sequence is part of how CraftedAgent turns generated changes into shippable PRs.

**Decision:** Implement the build workflow as an explicit staged pipeline that includes syntax/structure validation, lint/import validation, and a bounded fix loop of up to 20 pytest-driven repair attempts.

**Consequences:** Generated code must pass through the documented validation sequence before being considered ready. Retry behavior must be bounded and strategy-aware, not indefinite. Pipeline stages must remain explicit enough to checkpoint and diagnose individually.

**Rejected alternatives:**  
- Run only tests and skip parse/lint/import validation — rejected because earlier validation catches failures more cheaply and is explicitly documented.  
- Use an unbounded self-healing loop — rejected because it can hang pipelines and hides non-converging failures.  
- Replace staged execution with a single opaque “build” command — rejected because it reduces observability and weakens checkpoint semantics.

## [Generate and maintain required CI workflows for both Linux and macOS targets]
**Status:** Accepted

**Context:** The build pipeline requires `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is a critical file because it generates these workflows. CraftedAgent must ensure CI configuration is produced consistently and within approved repository paths.

**Decision:** Generate and maintain named CI workflow files under `.github` for the required Linux and macOS execution targets, using the CI workflow generator as the authoritative source.

**Consequences:** CI definitions must not be scattered across hand-authored variants without generator support. macOS-specific support for Swift remains a first-class requirement, not an optional extension. Workflow output paths must conform to the path allowlist and dot-root security rules.

**Rejected alternatives:**  
- Generate only a Linux workflow — rejected because macOS CI is explicitly required for Swift.  
- Hand-edit workflow YAML independently of the generator — rejected because it creates drift from the authoritative workflow generation path.  
- Store workflows outside `.github` and copy them later — rejected because it complicates repository semantics and collides with path policy.

## [Checkpoint every stage transition and per-PR state transition]
**Status:** Accepted

**Context:** The README states that every state transition is checkpointed, including per-PR stages `branch_opened → code_generated → tests_passed → committed → ci_passed`. CraftedAgent requires durable progress tracking so work can be resumed, audited, and gated without ambiguous in-memory state.

**Decision:** Persist checkpoints for every pipeline stage transition and for each documented per-PR state transition.

**Consequences:** State progression must be explicit and recoverable. Implementations cannot rely solely on transient process memory for workflow status. Resumption, debugging, and operator review must consume the checkpointed state model rather than infer progress indirectly from Git or logs alone.

**Rejected alternatives:**  
- Track only final success/failure — rejected because the documented workflow requires stage-by-stage checkpointing.  
- Keep state only in memory during a run — rejected because crashes or restarts would lose progress and auditability.  
- Infer state from repository artifacts after the fact — rejected because artifact-based inference is incomplete and error-prone.

## [Require an operator gate before merge]
**Status:** Accepted

**Context:** The build pipeline defines Stage 6 as a gate where the operator approves or corrects before merge. CraftedAgent is therefore not authorized to treat successful generation, tests, and CI as sufficient for autonomous merge.

**Decision:** Enforce a mandatory operator approval or correction gate before merge completion.

**Consequences:** Merge automation must stop short of final integration without explicit operator action. UX, state management, and GitHub integration must preserve a pending-review state after CI success. “Green pipeline” does not equal “merge now” in subsystem behavior.

**Rejected alternatives:**  
- Auto-merge after tests and CI pass — rejected because it bypasses the documented operator gate.  
- Make operator review optional behind a default-on flag — rejected because the gate is part of the required pipeline, not a preference.  
- Collapse correction handling into post-merge follow-up work — rejected because corrections must happen before merge.

## [Centralize all GitHub I/O in the GitHub tools module]
**Status:** Accepted

**Context:** `src/github_tools.py` is identified as handling all GitHub I/O, including path validation, rate limiting, and SHA protocol. CraftedAgent needs a single integration surface for repository mutations and remote coordination to avoid inconsistent API handling and broken commit semantics.

**Decision:** Route all GitHub API and repository I/O through the GitHub tools module and preserve its responsibilities for validation, rate limiting, and SHA-aware operations.

**Consequences:** Other modules must not implement direct ad hoc GitHub API calls for commits, file updates, PR operations, or related remote actions. SHA protocol correctness and rate-limit behavior remain centralized concerns. Changes to GitHub interaction semantics must be made in the shared integration layer.

**Rejected alternatives:**  
- Let each subsystem call GitHub APIs directly — rejected because it duplicates protocol logic and increases inconsistency risk.  
- Split rate limiting, SHA handling, and write operations across separate uncoordinated modules — rejected because those concerns are tightly coupled in safe GitHub mutation flows.  
- Bypass GitHub tools for “simple” operations — rejected because even simple operations must respect validation and protocol constraints.