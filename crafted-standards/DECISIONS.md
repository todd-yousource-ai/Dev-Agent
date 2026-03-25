# DECISIONS.md

## [Use forge-docs as the authoritative requirements source]
**Status:** Accepted

**Context:** CraftedDevAgent operates in a repository where all TRDs and PRDs are centralized under `forge-docs/`. The subsystem must not infer behavior from partial local conventions when formal requirements already exist. Implementation drift is especially risky because the agent modifies code, CI, and repository structure across multiple stages.

**Decision:** Treat `forge-docs/` as the single authoritative source for product and technical requirements before implementing or modifying CraftedDevAgent behavior.

**Consequences:** Implementation must read and align with TRDs/PRDs in `forge-docs/` before changing orchestration, generation, CI, GitHub integration, or security behavior. Local code comments, inferred patterns, or undocumented operator expectations must not override documented requirements. Any implementation that conflicts with `forge-docs/` is invalid until the documents are updated.

**Rejected alternatives:**  
- Use source code as the primary truth because it reflects current behavior. Rejected because current behavior may already have drifted from approved requirements.  
- Split authority across `README`, code comments, and TRDs. Rejected because multiple authorities create ambiguity during agent-driven changes.  
- Allow subsystem-specific conventions to override TRDs when expedient. Rejected because this undermines traceability and governance.

## [Require review of critical files before modifying core behavior]
**Status:** Accepted

**Context:** Several files form the operational and security boundary for CraftedDevAgent. Changes to these files have system-wide impact: generation loops, pipeline orchestration, GitHub I/O, path security, and CI workflow generation. Modifying adjacent logic without understanding these files creates regressions and security gaps.

**Decision:** Read and account for the designated critical files before modifying any behavior that touches generation, orchestration, GitHub operations, path validation, or CI workflow generation.

**Consequences:** Changes affecting the agent loop must account for `src/consensus.py`. Pipeline changes must account for `src/build_director.py`. GitHub write/read behavior must account for `src/github_tools.py`. Any filesystem write path must account for `src/path_security.py`. CI workflow changes must account for `src/ci_workflow.py`. Implementation work is constrained to preserve these files’ contract boundaries unless explicitly changing those boundaries.

**Rejected alternatives:**  
- Modify only the local file being touched and rely on tests to catch regressions. Rejected because these files enforce cross-cutting constraints not always covered by tests.  
- Treat critical files as informational only. Rejected because they define actual system boundaries.  
- Permit indirect changes without reviewing critical files if no imports change. Rejected because behavioral coupling exists beyond import relationships.

## [Enforce an explicit repository root allowlist for all write operations]
**Status:** Accepted

**Context:** CraftedDevAgent writes code, tests, docs, scripts, CI files, and infrastructure artifacts. GitHub integration lessons show that commits to unexpected root directories fail silently or are rejected by security guards. Dot-prefixed roots such as `.github` require explicit treatment because many validators reject leading dots by default.

**Decision:** Validate every write target against an explicit allowlist of approved repository root directories, including dot-prefixed roots that are intentionally supported.

**Consequences:** Writes are constrained to approved roots only. Standard approved roots include `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs` unless repository policy is updated. New top-level roots require explicit allowlist changes before the agent may write to them. Silent writes to undeclared roots are prohibited.

**Rejected alternatives:**  
- Allow writes anywhere within the repository after path normalization. Rejected because it weakens the security boundary and permits accidental sprawl.  
- Infer allowed roots from existing directories in the working tree. Rejected because attacker-controlled or incidental directories could become writable.  
- Ban dot-prefixed roots entirely. Rejected because CI workflow files in `.github` are a required output.

## [Route every filesystem write through path security]
**Status:** Accepted

**Context:** `src/path_security.py` is identified as the security boundary. CraftedDevAgent performs automated file creation and modification, which makes path traversal, root escape, and unintended overwrite risks materially important.

**Decision:** Require every file write, update, or generated artifact to pass through the path security layer before execution.

**Consequences:** Direct writes that bypass path validation are not permitted. Helper utilities, GitHub commit preparation, CI generation, and code generation must all invoke the same security boundary. Security behavior becomes centralized and auditable. Refactors must preserve this choke point.

**Rejected alternatives:**  
- Let each module implement its own path validation. Rejected because duplicated validation leads to inconsistent enforcement.  
- Validate only external or user-provided paths. Rejected because internally generated paths can also be wrong or unsafe.  
- Rely on GitHub API errors to catch invalid paths. Rejected because API rejection is not equivalent to local security enforcement.

## [Centralize all GitHub I/O in github_tools]
**Status:** Accepted

**Context:** `src/github_tools.py` is the designated integration point for path validation, rate limiting, and SHA protocol handling. CraftedDevAgent depends on reliable repository reads and writes, and fragmented GitHub access would duplicate protocol and security logic.

**Decision:** Perform all GitHub API reads and writes through `src/github_tools.py`; do not implement ad hoc GitHub calls elsewhere in the subsystem.

**Consequences:** Path checks, rate limiting, and SHA handling remain consistent across all repository operations. New GitHub features must extend `github_tools` rather than bypass it. This constrains implementation structure and reduces hidden API behavior.

**Rejected alternatives:**  
- Permit direct GitHub API calls from feature modules for convenience. Rejected because it fragments rate limiting and SHA semantics.  
- Use separate clients for reads and writes. Rejected because path and protocol enforcement must stay uniform.  
- Push GitHub logic into the build orchestrator. Rejected because orchestration should consume repository operations, not redefine them.

## [Preserve the consensus loop as the core generation mechanism]
**Status:** Accepted

**Context:** `src/consensus.py` is identified as the core generation loop affecting every pull request the agent builds. CraftedDevAgent’s output quality and determinism depend on a stable central generation mechanism rather than scattered generation entry points.

**Decision:** Keep `src/consensus.py` as the canonical core generation loop for CraftedDevAgent and route generation-affecting changes through that mechanism.

**Consequences:** Feature work that changes how code is proposed, revised, or finalized must integrate with the consensus loop rather than create parallel generation paths. PR behavior remains governed by one core mechanism, making output easier to reason about and checkpoint.

**Rejected alternatives:**  
- Let each pipeline stage own its own generation strategy independently. Rejected because it creates divergent behavior across PRs.  
- Replace the consensus loop with stage-local direct generation. Rejected because it removes the shared control point identified as core.  
- Treat consensus as optional for simple changes. Rejected because exceptions tend to become ungoverned defaults.

## [Keep pipeline orchestration in build_director and enforce complexity limits]
**Status:** Accepted

**Context:** `src/build_director.py` is the pipeline orchestrator, and repository guidance states that every stage has a maximum cyclomatic complexity of 15. CraftedDevAgent’s pipeline spans generation, validation, fixing, testing, CI, and gating, so orchestration can easily become unmaintainable without hard structural constraints.

**Decision:** Centralize pipeline orchestration in `src/build_director.py` and enforce a maximum cyclomatic complexity of 15 for every stage implementation.

**Consequences:** Stage logic must be decomposed when complexity rises. New orchestration behavior must be added through smaller helpers or state handlers rather than expanding monolithic stage methods. This constrains implementation style toward explicit, testable stage boundaries.

**Rejected alternatives:**  
- Allow higher complexity in orchestration because pipelines are inherently branchy. Rejected because complexity growth directly harms maintainability.  
- Distribute orchestration opportunistically across modules. Rejected because stage ownership becomes unclear.  
- Enforce complexity only at file level. Rejected because problematic branching often hides inside individual stages.

## [Checkpoint every state transition in the pipeline]
**Status:** Accepted

**Context:** The build pipeline requires that every state transition be checkpointed, including per-PR transitions such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. CraftedDevAgent needs resumability, auditability, and clear operator visibility when stages fail or pause.

**Decision:** Persist a checkpoint for every pipeline state transition, including all per-PR milestones and gate decisions.

**Consequences:** The subsystem must record transitions as first-class events rather than infer them from side effects. Resumption logic must rely on checkpoints. Operators gain an auditable trail of what completed, failed, or awaited approval. Implementations that skip intermediate checkpointing are non-compliant.

**Rejected alternatives:**  
- Checkpoint only major milestones such as commit and CI completion. Rejected because intermediate recovery and diagnosis become unreliable.  
- Infer state from repository artifacts instead of storing checkpoints. Rejected because artifacts do not fully encode decision history.  
- Log transitions without durable checkpoint semantics. Rejected because logs alone do not support deterministic recovery.

## [Model the pipeline as ordered stages including validation and bounded fix loops]
**Status:** Accepted

**Context:** The documented build pipeline includes explicit stages, including validation (`ast.parse`, `ruff`, import check), a fix loop, CI generation, and operator gating. The fix loop is bounded to up to 20 pytest attempts and uses failure-type-aware strategy. CraftedDevAgent must implement this sequence predictably rather than improvising remediation behavior.

**Decision:** Implement CraftedDevAgent as an ordered staged pipeline with explicit validation, a bounded fix loop of at most 20 pytest-driven attempts, CI execution, and a final operator gate.

**Consequences:** Validation is mandatory before fix attempts proceed. Automated remediation must stop after the defined limit rather than retry indefinitely. Fix behavior must be aware of failure type rather than applying one generic retry action. Operator approval remains a required gate before merge completion.

**Rejected alternatives:**  
- Use an unbounded retry loop until tests pass. Rejected because it risks runaway execution and non-terminating behavior.  
- Collapse validation into test execution only. Rejected because syntax, lint, and import failures should be caught earlier and handled distinctly.  
- Skip operator gating when CI passes. Rejected because the documented process requires explicit human approval or correction before merge.

## [Generate required CI workflows, including macOS support for Swift]
**Status:** Accepted

**Context:** The pipeline defines CI outputs: `crafted-ci.yml` on `ubuntu-latest`, and `crafted-ci-macos.yml` for Swift. `src/ci_workflow.py` is the designated generator for these workflow artifacts. CraftedDevAgent must reliably produce the correct workflow set for the project type.

**Decision:** Generate CI workflows through `src/ci_workflow.py`, including `crafted-ci.yml` for standard CI and `crafted-ci-macos.yml` when Swift/macOS support is required.

**Consequences:** CI workflow creation must remain standardized and generator-driven. Swift-capable projects require macOS workflow generation instead of relying solely on Ubuntu CI. Workflow filenames and generation responsibility are constrained and must not drift into bespoke per-feature YAML creation.

**Rejected alternatives:**  
- Generate CI files inline from the orchestrator. Rejected because CI generation has an explicit owning module.  
- Use only a single Ubuntu workflow for all projects. Rejected because Swift/macOS workloads require dedicated macOS runners.  
- Hand-author workflow files per repository change. Rejected because it undermines consistency and automation.