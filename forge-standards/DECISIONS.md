# DECISIONS.md

## [Use `forge-docs/` as the source of truth for ConsensusDevAgent requirements]
**Status:** Accepted  
**Context:** The repository structure TRD defines a strict separation between specification artifacts and implementation. ConsensusDevAgent behavior must be grounded in approved TRDs and PRDs, and those documents are stored under `forge-docs/`. The README repository layout also identifies `forge-docs/` as the location for all TRDs and PRDs.  
**Decision:** Treat `forge-docs/` as the authoritative source for ConsensusDevAgent requirements, sequencing, and constraints. Read relevant TRDs and PRDs from `forge-docs/` before implementation, planning, or modification of subsystem behavior. Do not treat code comments, ad hoc prompts, or unstored drafts as authoritative over documents in `forge-docs/`.  
**Consequences:** ConsensusDevAgent implementations must be traceable back to repository documents. Requirement changes must be reflected in `forge-docs/` before behavior is changed in code. Planning, review, and audits can rely on a single authoritative document location.  
**Rejected alternatives:**  
- Using implementation code as the primary source of truth — rejected because it allows drift from approved product and technical requirements.  
- Storing subsystem requirements across multiple ad hoc directories — rejected because it weakens discoverability, traceability, and auditability.  
- Allowing prompts or operator chat to override TRDs without document updates — rejected because it breaks reproducibility and governance.

## [Constrain ConsensusDevAgent artifacts to the standard repository layout]
**Status:** Accepted  
**Context:** The repository layout is explicitly defined across the repository structure and README materials. ConsensusDevAgent must fit within the same layout so that planning, implementation, testing, and review remain predictable.  
**Decision:** Place ConsensusDevAgent implementation in the established repository structure: Python backend code under `src/`, tests under `tests/`, and governing documentation under `forge-standards/` and `forge-docs/` as appropriate. Do not introduce a parallel top-level subsystem layout for ConsensusDevAgent.  
**Consequences:** The subsystem must integrate with existing tooling, CI, test discovery, and review conventions. New files must be placed in existing standard directories rather than custom top-level folders. Team members and automation can locate subsystem code and documents without special-case handling.  
**Rejected alternatives:**  
- Creating a dedicated top-level `ConsensusDevAgent/` backend folder — rejected because it fragments the documented repository contract.  
- Mixing standards, specs, and executable code in one directory — rejected because it obscures ownership and increases review friction.  
- Storing tests beside all source files by default — rejected because the documented repository uses `tests/` for Python test organization.

## [Implement ConsensusDevAgent as a stage-bound participant in the build pipeline]
**Status:** Accepted  
**Context:** The README defines the core loop as a staged build pipeline triggered by `/prd start <intent>`, with ordered stages from scope through merge. TRD-3 is identified as the source for full stage contracts, escalation, and audit schema. ConsensusDevAgent must operate within this staged model rather than inventing an independent workflow.  
**Decision:** Implement ConsensusDevAgent to participate only through the documented pipeline stages and contracts. Bind subsystem actions, state transitions, and outputs to the existing stages: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and Merge. Do not bypass or reorder stages in subsystem logic.  
**Consequences:** ConsensusDevAgent behavior must expose stage-aware state and respect handoff boundaries. Subsystem logic must be compatible with audit trails, gate handling, and escalation defined by the build pipeline. Features that require cross-stage shortcuts are disallowed unless the pipeline contract is updated first.  
**Rejected alternatives:**  
- Allowing the subsystem to free-run outside the pipeline — rejected because it breaks auditability and operator expectations.  
- Collapsing multiple stages into one ConsensusDevAgent internal step — rejected because it hides required review and governance checkpoints.  
- Permitting dynamic stage reordering based on model preference — rejected because the pipeline is specified as ordered and contract-driven.

## [Do not support undo or automatic reversal of gate decisions]
**Status:** Accepted  
**Context:** The requirements explicitly state “No undo on gate decisions — document this explicitly” and repeat “No undo on gate decisions” in build pipeline material. Gate decisions are therefore final events in the control flow and audit history. ConsensusDevAgent must not create any mechanism that weakens this guarantee.  
**Decision:** Treat every gate decision as immutable once recorded. Do not implement undo, rollback, silent reopening, automatic bypass, or state mutation that functionally reverses a gate outcome. Any further progress after a gate must occur only through explicit subsequent operator action defined outside an undo mechanism.  
**Consequences:** State models, APIs, UI affordances, and audit logging must represent gate decisions as append-only. Error recovery must use new decisions or new workflow runs rather than reversal of prior gates. The subsystem must be designed for irreversible gating semantics from the outset.  
**Rejected alternatives:**  
- Adding an “undo last gate” operator command — rejected because it directly violates stated requirements.  
- Allowing administrators to silently clear a gate flag in storage — rejected because it undermines audit integrity.  
- Implementing automatic retry that removes prior gate outcomes — rejected because it is a functional undo even if not labeled as such.

## [Make gate outcomes append-only and audit-visible]
**Status:** Accepted  
**Context:** The build pipeline references full stage contracts, error escalation, and an audit trail schema. Since gate decisions cannot be undone, their representation must preserve history rather than overwrite it. ConsensusDevAgent needs a storage and event model consistent with irreversible governance decisions.  
**Decision:** Record gate outcomes as append-only audit events with explicit timestamps, actors, stage context, and reasons. Preserve prior gate records permanently and represent subsequent actions as new events rather than updates that erase history.  
**Consequences:** Persistence models must favor event records over mutable single-row status fields as the canonical history. Debugging, compliance review, and incident reconstruction will rely on immutable gate event history. Any convenience status projection must be derived from audit events, not used as a substitute for them.  
**Rejected alternatives:**  
- Updating a single mutable “current gate status” field in place — rejected because it loses decision history.  
- Keeping gate history only in logs — rejected because logs alone are insufficient as a structured control record.  
- Storing gate reasons only in free-form chat transcripts — rejected because they are difficult to validate, query, and audit.

## [Enforce SECURITY_REFUSAL as a hard stop with no auto-bypass]
**Status:** Accepted  
**Context:** Mandatory security controls require SECURITY_REFUSAL rules in every generation system prompt and specify that SECURITY_REFUSAL in output must stop the PR, gate, log, and never auto-bypass. ConsensusDevAgent, as part of multi-model generation and arbitration, must treat this as a non-negotiable safety control.  
**Decision:** On any SECURITY_REFUSAL emitted by a participating model or generation step, immediately stop the active PR flow, create a gate, and log the event. Never auto-bypass, suppress, rewrite away, or continue execution past the refusal.  
**Consequences:** ConsensusDevAgent must surface refusal handling as a first-class state transition. Arbitration logic may not overrule or mask a refusal from one model with output from another. Recovery requires explicit operator involvement through the gated workflow, not automated continuation.  
**Rejected alternatives:**  
- Ignoring SECURITY_REFUSAL if another model produces usable output — rejected because security refusal is a hard stop, not a soft vote.  
- Automatically re-prompting until refusal disappears — rejected because it is an implicit bypass.  
- Downgrading refusal to a warning for low-risk tasks — rejected because the control is defined as mandatory.

## [Treat security review as mandatory and include bandit in Pass 3]
**Status:** Accepted  
**Context:** The mandatory security controls state that all generated code passes Pass 3 security review including bandit. The README build pipeline defines a 3-pass review stage of correctness, performance, and security. ConsensusDevAgent must not consider generation complete before security review passes.  
**Decision:** Require Pass 3 security review for all code generated through ConsensusDevAgent, and include bandit as part of that pass. Do not allow merge progression or completion status if Pass 3 has not succeeded.  
**Consequences:** The subsystem must integrate with the review pipeline and expose Pass 3 results as gating inputs. Performance or correctness success cannot compensate for failed or skipped security review. Generated code workflows must budget time and state for security analysis before merge.  
**Rejected alternatives:**  
- Running security review only for high-risk changes — rejected because the requirement applies to all generated code.  
- Making bandit advisory rather than required — rejected because bandit is explicitly included in Pass 3.  
- Performing security review after merge — rejected because review is a pre-merge stage gate.

## [Validate every write path before file output]
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent generates and applies code and document outputs, making path handling a direct attack surface.  
**Decision:** Call `path_security.validate_write_path()` for every filesystem write initiated by ConsensusDevAgent, without exception. Reject or gate any attempted write whose path has not been validated or fails validation.  
**Consequences:** All write code paths must route through a shared validated file-writing abstraction or equivalently enforced guard. Direct writes that bypass validation are prohibited. Refactoring and new features must preserve this invariant for both code and document outputs.  
**Rejected alternatives:**  
- Validating only user-supplied paths — rejected because generated and derived paths can also be unsafe.  
- Validating directory roots once per session — rejected because per-write validation is explicitly required.  
- Relying on repository-relative path normalization alone — rejected because normalization is not a substitute for the mandated validator.

## [Surface untrusted review content with explicit labeling and gating]
**Status:** Accepted  
**Context:** The security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts and require a gate card to the operator when flagged content is used in generation. ConsensusDevAgent consumes review signals and may incorporate them into planning or generation, so provenance and trust boundaries must be explicit.  
**Decision:** Label untrusted review content exactly as required when included in model prompts, and if flagged content is used in generation, present a gate to the operator before proceeding. Do not silently blend untrusted reviewer content into trusted instructions.  
**Consequences:** Prompt assembly, provenance tracking, and operator UX must preserve trust labels end to end. The subsystem must track whether flagged content influenced generation and trigger an operator gate in that case. Review ingestion pipelines must distinguish trusted system guidance from untrusted external commentary.  
**Rejected alternatives:**  
- Treating PR comments as trusted by default — rejected because review comments are explicitly untrusted unless handled with labels.  
- Omitting labels once comments are summarized — rejected because summarization does not remove trust concerns.  
- Proceeding automatically after using flagged content — rejected because operator gating is explicitly required.

## [Use consensus/arbitration only within safety and pipeline constraints]
**Status:** Accepted  
**Context:** The build pipeline indicates parallel generation and arbitration during Code Gen, while security controls impose hard stops and mandatory reviews. ConsensusDevAgent exists to coordinate consensus behavior, but consensus cannot supersede documented gates, refusals, or stage contracts.  
**Decision:** Restrict consensus and arbitration logic to selecting among compliant candidate outputs within the current pipeline stage. Do not allow consensus mechanisms to override SECURITY_REFUSAL, skip reviews, reverse gates, or bypass required operator approvals.  
**Consequences:** Arbitration modules must evaluate candidates after applying safety and process constraints, not before. “Best” output selection is subordinate to compliance. Metrics or voting schemes that favor throughput over required controls are out of bounds.  
**Rejected alternatives:**  
- Letting majority model agreement override a single refusal — rejected because refusal is a hard stop, not a vote.  
- Allowing arbitration to advance code directly to merge when confidence is high — rejected because mandatory stages still apply.  
- Optimizing consensus solely for speed or token efficiency — rejected because safety and governance constraints are higher priority.