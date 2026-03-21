# DECISIONS.md

## ConsensusDevAgent repository boundaries and source-of-truth
**Status:** Accepted  
**Context:** The ConsensusDevAgent subsystem operates within a repository that separates requirements, standards, implementation, and tests. The TRDs explicitly define where authoritative documents live and the README defines the repository layout. Without a hard boundary, implementation risks drifting away from documented intent or writing artifacts into the wrong locations.  
**Decision:** Treat `forge-docs/` as the authoritative source for all TRDs and PRDs and require the ConsensusDevAgent to read those documents before building. Constrain implementation artifacts to the established repository layout: `forge-standards/` for governing standards documents, `src/` for Python backend code, `ForgeAgent/` and `ForgeAgentTests/` for the macOS shell, `tests/` for pytest suites, and `.github/workflows/` for CI definitions. Do not create alternate requirement stores, parallel standards directories, or undocumented artifact locations.  
**Consequences:** Implementation must resolve behavior from documents in `forge-docs/` first, not from ad hoc prompts or generated summaries. Code generation, planning, and review logic must assume fixed repository locations. Tooling must avoid scattering outputs across new folders unless the standards documentation is updated first.  
**Rejected alternatives:**  
- Allowing PRDs or TRDs to be copied into subsystem-specific directories for convenience — rejected because it creates multiple sources of truth.  
- Letting the agent infer repository structure dynamically from current contents — rejected because it weakens consistency and makes audits harder.  
- Storing standards alongside code in `src/` — rejected because repository governance documents are intentionally separated from implementation.

## Pipeline-first orchestration for ConsensusDevAgent
**Status:** Accepted  
**Context:** The build loop is explicitly defined as a staged pipeline triggered from intent through planning, generation, review, and merge. ConsensusDevAgent must fit into that larger orchestration model rather than inventing a custom execution flow.  
**Decision:** Implement ConsensusDevAgent as a stage-conforming subsystem within the defined build pipeline: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and subsequent gated progression. Preserve stage boundaries and contracts from the documented pipeline rather than collapsing planning, generation, and review into a single free-form agent loop.  
**Consequences:** ConsensusDevAgent must emit artifacts and decisions that are attributable to a specific pipeline stage. Handoffs between planning, generation, and review must remain explicit. Failures and escalations must be reported in stage terms so they can participate in the shared audit trail and operator gating model.  
**Rejected alternatives:**  
- A monolithic autonomous agent that plans, codes, reviews, and merges in one loop — rejected because it violates documented stage contracts and reduces auditability.  
- A lightweight helper used only during code generation — rejected because consensus behavior is also required in document generation and review arbitration.  
- Stage skipping when confidence is high — rejected because the pipeline is mandatory and confidence does not replace gated review.

## No undo on gate decisions
**Status:** Accepted  
**Context:** The TRDs and pipeline notes explicitly state that there is no undo on gate decisions. This must be documented as a hard implementation constraint because it affects workflow state management, retries, auditability, and operator trust.  
**Decision:** Treat every gate decision as final and append-only. Do not implement undo, rollback, silent reversal, or automatic reopening of a closed gate state. Any further progress after a gate outcome must occur through a new explicit operator action or a new pipeline run, not by mutating prior gate history.  
**Consequences:** State models must represent gate outcomes as immutable events. UI and API flows must not expose “undo gate,” “reopen automatically,” or equivalent functionality. Recovery paths must create new decisions rather than editing old ones. Audit logs remain linear and trustworthy.  
**Rejected alternatives:**  
- Supporting operator undo for convenience — rejected because it conflicts with explicit requirements and weakens the audit trail.  
- Allowing automatic rollback after downstream failure — rejected because rollback is effectively an undo of a gate decision.  
- Soft-final gates that can be superseded in place — rejected because in-place supersession obscures history.

## SECURITY_REFUSAL is a hard stop
**Status:** Accepted  
**Context:** Security controls require SECURITY_REFUSAL rules in system prompts and define that SECURITY_REFUSAL in output must stop the PR, gate, log, and never auto-bypass. ConsensusDevAgent must therefore treat refusal detection as a mandatory control, not advisory metadata.  
**Decision:** When any model output contains a SECURITY_REFUSAL condition, immediately stop the active PR or equivalent unit of work, create a gate for operator review, log the event in the audit trail, and prohibit automatic bypass or silent retry continuation.  
**Consequences:** ConsensusDevAgent must include explicit detection and handling paths for SECURITY_REFUSAL across generation and review flows. Arbitration logic cannot overrule or suppress a refusal. Retry logic must not continue as if the refusal were an ordinary model error. Security events become first-class pipeline outcomes.  
**Rejected alternatives:**  
- Automatically retrying with a different model when one model refuses — rejected because the requirement is to stop and gate, not model-shop around the refusal.  
- Downgrading SECURITY_REFUSAL to a warning when confidence is otherwise high — rejected because security controls are mandatory.  
- Allowing operator-configured auto-bypass — rejected because the requirement explicitly says never auto-bypass.

## Mandatory security review in the three-pass pipeline
**Status:** Accepted  
**Context:** The documented pipeline includes a 3-pass review sequence of correctness, performance, and security. Security controls further require that all generated code pass the security review, including Bandit. ConsensusDevAgent must preserve this review ordering and enforce the security pass as non-optional.  
**Decision:** Require all code produced through ConsensusDevAgent to pass the documented 3-pass review pipeline, with security as a mandatory pass after correctness and performance. Include Bandit in the security review and do not merge or advance code that has not completed the security pass successfully.  
**Consequences:** ConsensusDevAgent cannot mark code complete after generation alone. Review orchestration must preserve pass separation and record outcomes per pass. Security findings must block progression until resolved or explicitly handled by the defined gate process.  
**Rejected alternatives:**  
- Combining all reviews into one generalized quality pass — rejected because the pipeline explicitly defines three distinct passes.  
- Running only correctness and performance for low-risk changes — rejected because all generated code must pass security review.  
- Making Bandit best-effort — rejected because the controls explicitly require it.

## File writes must be path-validated
**Status:** Accepted  
**Context:** Security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent generates and edits repository files, so unchecked writes would create a direct path traversal and boundary violation risk.  
**Decision:** Validate every filesystem write path through `path_security.validate_write_path()` before creating, modifying, or replacing files. Apply this uniformly to generated code, tests, documents, workflow files, and any intermediate persisted artifacts.  
**Consequences:** All write-capable tools used by ConsensusDevAgent must route through a shared validated write path. Direct raw writes are disallowed. The subsystem must fail closed on invalid or unresolved paths rather than attempting partial writes.  
**Rejected alternatives:**  
- Validating only user-supplied paths — rejected because generated and derived paths can also be unsafe.  
- Relying on repository-relative path joins without a security validator — rejected because normalization alone is not a sufficient control.  
- Validating only code files and not docs or CI files — rejected because the requirement applies to every file path before write.

## Untrusted review comments must remain explicitly labeled
**Status:** Accepted  
**Context:** Security controls state that PR review comments must be labeled `[UNTRUSTED REVIEWER COMMENT]` in the prompt. ConsensusDevAgent consumes review material during arbitration and revision, so provenance must remain visible to the model and to the audit trail.  
**Decision:** Preserve and inject external PR review comments into model prompts only with the explicit `[UNTRUSTED REVIEWER COMMENT]` label. Do not normalize away, merge invisibly, or present reviewer comments as trusted system or developer instructions.  
**Consequences:** Prompt-building logic must maintain provenance metadata for review input. Consensus and arbitration routines must treat reviewer comments as advisory, not authoritative. Audit records must distinguish trusted instructions from untrusted review content.  
**Rejected alternatives:**  
- Folding review comments into a single summarized instruction block — rejected because it erases trust boundaries.  
- Treating maintainer comments as implicitly trusted — rejected unless the trust model explicitly elevates them elsewhere; the provided control requires labeling PR review comments.  
- Excluding all review comments from prompts — rejected because review feedback is operationally useful and expected by the pipeline.

## Flagged chunks require operator gating before use
**Status:** Accepted  
**Context:** Security controls state that when a flagged chunk is used in generation, a gate card must be presented to the operator before proceeding. ConsensusDevAgent may assemble context from multiple sources, so use of flagged material must trigger a human-visible checkpoint.  
**Decision:** If generation would use any flagged chunk of context, halt progression at that point and present a gate card to the operator before proceeding. Do not silently include flagged content in prompts or outputs.  
**Consequences:** Context assembly must track chunk-level flags and provenance. Prompt construction cannot be a blind concatenation step. The subsystem must support pre-generation gating based on content risk, not only post-generation review.  
**Rejected alternatives:**  
- Allowing flagged chunks if they score below a threshold — rejected because the requirement mandates operator gating when used.  
- Stripping the flag and using the text anyway — rejected because it defeats the purpose of the control.  
- Deferring review until after generation — rejected because the requirement is to gate before proceeding.

## Claude-wins rule for PRD generation
**Status:** Accepted  
**Context:** The documented pipeline specifies that PRD generation uses both models and that Claude wins. ConsensusDevAgent must therefore implement deterministic arbitration for this stage rather than inventing a new tie-breaker.  
**Decision:** During PRD generation, run the defined multi-model generation process and resolve final PRD output according to the documented rule that Claude wins. Do not substitute another arbitration strategy for this stage.  
**Consequences:** PRD-generation code must preserve model-specific outputs and apply a deterministic winner selection. Downstream stages can rely on stable PRD artifacts. Any future change to the winner rule requires a standards or TRD update, not local subsystem discretion.  
**Rejected alternatives:**  
- Majority-vote consensus across more than two models — rejected because the documented stage contract already defines the winner.  
- Score-based arbitration by heuristic quality metrics — rejected because it introduces nondeterminism and contradicts the explicit rule.  
- Rotating winner preference by document type — rejected because no such exception is specified.