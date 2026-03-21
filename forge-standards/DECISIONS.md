# DECISIONS.md

## ConsensusDevAgent repository placement and boundaries
**Status:** Accepted  
**Context:** The repository has a fixed top-level structure and the subsystem must fit within it without creating ambiguity about source of truth, runtime code, tests, or standards. The TRDs and README establish that documentation artifacts live under `forge-docs/`, standards under `forge-standards/`, backend implementation under `src/`, Swift app shell under `ForgeAgent/`, and tests under `tests/` and `ForgeAgentTests/`.  
**Decision:** Implement ConsensusDevAgent backend code under `src/`, place its tests under `tests/`, and record its architectural constraints in `forge-standards/DECISIONS.md`. Treat `forge-docs/` as read-first source material and not as an implementation location.  
**Consequences:** The subsystem may not introduce parallel top-level folders for agent runtime code, specs, or ad hoc standards. Design notes that constrain implementation must be captured here rather than embedded only in code comments or scattered docs.  
**Rejected alternatives:**  
- Placing ConsensusDevAgent implementation under `forge-docs/` because TRDs live there; rejected because `forge-docs/` is for requirements and design source artifacts, not runtime code.  
- Creating a dedicated top-level `agents/` directory; rejected because it violates the prescribed repository layout and fragments ownership.  
- Storing subsystem decisions only in TRDs; rejected because TRDs are inputs, while implementation constraints must be preserved in repository standards.

## TRDs and PRDs are mandatory inputs before implementation
**Status:** Accepted  
**Context:** The repository structure explicitly states that all TRDs and PRDs live in `forge-docs/` and must be read before building. ConsensusDevAgent participates in a document-driven workflow and must not operate from unstated assumptions.  
**Decision:** Require ConsensusDevAgent implementation and behavior to be derived from documents in `forge-docs/`; read applicable TRDs and generated PRDs before coding, orchestration changes, or gate logic changes.  
**Consequences:** Features, workflow stages, and integration behavior must trace back to repository documents. The subsystem must not invent undocumented stages, mutate process semantics implicitly, or bypass document review by encoding policy solely in implementation.  
**Rejected alternatives:**  
- Allowing implementation-first changes with documentation added later; rejected because it breaks the documented development workflow and weakens traceability.  
- Treating README snippets as sufficient without consulting TRDs/PRDs; rejected because README is summary material, while TRDs define the authoritative constraints.  
- Permitting operator prompts to redefine core subsystem behavior at runtime; rejected because persistent behavior must remain document-governed.

## Build pipeline stage adherence is mandatory
**Status:** Accepted  
**Context:** The build pipeline is defined as a staged flow: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and subsequent gate behavior. ConsensusDevAgent must operate inside this pipeline rather than inventing a parallel execution model.  
**Decision:** Implement ConsensusDevAgent to respect the declared pipeline stages and their ordering; only perform actions appropriate to the current stage and defer full stage contracts, escalation, and audit semantics to TRD-3.  
**Consequences:** The subsystem cannot skip directly from intent to code merge, collapse review stages into generation, or reorder stage execution for convenience. Internal abstractions must preserve stage identity for auditability and operator understanding.  
**Rejected alternatives:**  
- A single-step “generate and merge” agent flow; rejected because it bypasses documented decomposition, review, and gate controls.  
- Dynamically reordering stages based on model confidence; rejected because deterministic governance is more important than opportunistic speed.  
- Treating review as advisory rather than a formal pipeline stage; rejected because the documented pipeline requires explicit review passes.

## Gate decisions are irreversible
**Status:** Accepted  
**Context:** The requirements explicitly state: no undo on gate decisions. This is repeated in the build pipeline material and must be documented as a hard constraint, especially for failure, escalation, and operator intervention paths.  
**Decision:** Treat every gate decision produced by ConsensusDevAgent as append-only and irreversible; do not implement undo, silent rollback, or automatic reopening of a closed gate decision. Any subsequent action must be recorded as a new decision event, not a mutation of the prior one.  
**Consequences:** Audit history remains stable. Data models, APIs, and UI affordances must not offer “undo gate,” “reopen previous gate,” or in-place decision rewriting. Recovery from an incorrect gate requires an explicit new gate or operator-mediated forward action with preserved history.  
**Rejected alternatives:**  
- Allowing operators to undo a gate for convenience; rejected because it destroys audit integrity and conflicts with the explicit requirement.  
- Automatically clearing a gate after retries pass; rejected because retries are new events and may not erase prior conclusions.  
- Soft-delete or mutable gate records; rejected because mutability undermines traceability and security review.

## Security refusal is a hard stop
**Status:** Accepted  
**Context:** Mandatory security controls require `SECURITY_REFUSAL` rules in generation prompts and specify that `SECURITY_REFUSAL` in output must stop the PR, create a gate, log the event, and never auto-bypass. ConsensusDevAgent must enforce this consistently.  
**Decision:** On any `SECURITY_REFUSAL` emitted by a model involved in ConsensusDevAgent workflows, immediately stop PR progression, create or raise the appropriate gate, persist an audit log entry, and prohibit automatic bypass or continued generation within the same execution path.  
**Consequences:** The subsystem must model `SECURITY_REFUSAL` as terminal for the active flow segment. Retry logic, arbitration, and fallback models may not silently continue past a refusal. Operator intervention must occur through explicit gated handling, not automatic suppression.  
**Rejected alternatives:**  
- Ignoring refusals if another model succeeds; rejected because mandatory controls require refusal handling, not best-of-N masking.  
- Auto-retrying with a reformulated prompt until refusal disappears; rejected because it functions as an implicit bypass.  
- Logging only and continuing execution; rejected because the requirement demands stop, gate, and log.

## Untrusted external review content must remain labeled and non-authoritative
**Status:** Accepted  
**Context:** Security controls specify that PR review comments are labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts, and flagged chunks used in generation must produce a gate card to the operator before proceeding. ConsensusDevAgent must preserve provenance of untrusted inputs.  
**Decision:** Treat external reviewer comments and other flagged chunks as untrusted input; preserve explicit labeling in prompts and require gating before generation proceeds when flagged content is incorporated. Do not elevate such content to authoritative instructions.  
**Consequences:** Prompt construction, context assembly, and audit records must retain trust labeling. The subsystem must not merge untrusted comments into system or policy instructions, nor let them silently drive code changes without operator-visible gating.  
**Rejected alternatives:**  
- Normalizing reviewer comments into plain prompt context; rejected because it erases trust boundaries.  
- Allowing flagged content to flow into generation without a gate if deemed low risk; rejected because the control is mandatory.  
- Treating repository comments as implicitly trusted because they are in GitHub; rejected because source location does not equal trustworthiness.

## Security review is a required pass, not an optimization
**Status:** Accepted  
**Context:** The build pipeline includes a 3-pass review sequence: correctness, performance, then security. Mandatory controls also require generated code to pass security review including bandit. ConsensusDevAgent must preserve security review as a first-class gate.  
**Decision:** Require ConsensusDevAgent-generated code to complete the full 3-pass review sequence and to pass the security pass, including bandit or equivalent configured checks, before PR progression.  
**Consequences:** The subsystem cannot mark work complete after code generation alone or after partial review success. Security findings must block advancement according to gate behavior. Review orchestration must preserve pass ordering and explicit outcomes.  
**Rejected alternatives:**  
- Running only correctness and performance for trusted internal changes; rejected because security pass is mandatory for generated code.  
- Collapsing all review passes into a single undifferentiated review result; rejected because the pipeline specifies distinct passes.  
- Making security review asynchronous after merge; rejected because it weakens the documented gate model.

## File writes must be path-validated
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent will generate or modify repository files and must not permit unchecked writes.  
**Decision:** Validate every filesystem write path through `path_security.validate_write_path()` before any create, overwrite, append, rename, or generated artifact emission performed by ConsensusDevAgent.  
**Consequences:** All write-capable code paths must route through a validated file operation layer. The subsystem may not perform direct writes from ad hoc utility code, model output handlers, or test helpers without the same path validation guarantee.  
**Rejected alternatives:**  
- Validating only paths originating from model output; rejected because all write paths are attack surfaces.  
- Relying on repository-relative path joins alone; rejected because normalization is insufficient without explicit validation policy.  
- Applying validation only in production and not tests; rejected because tests should exercise the same security contract.

## Claude is the tie-breaking authority where the pipeline specifies it
**Status:** Accepted  
**Context:** The documented pipeline states that PRD generation uses both models and that Claude wins. ConsensusDevAgent must honor this explicit arbitration rule where it applies rather than substituting a new consensus heuristic.  
**Decision:** In PRD generation contexts governed by the documented pipeline, use both configured models and resolve disagreements by selecting Claude’s result as the authoritative output.  
**Consequences:** Arbitration logic must be stage-aware and may not apply a generic majority-vote or score-only strategy in places where the pipeline prescribes a winner. This keeps behavior aligned with the documented workflow and predictable to operators.  
**Rejected alternatives:**  
- Majority vote across all available models; rejected because the pipeline explicitly defines Claude as winner in PRD generation.  
- Always preferring the cheapest or fastest model; rejected because cost and latency do not override the documented contract.  
- Free-form human-less blending of model outputs; rejected because it obscures provenance and weakens determinism.