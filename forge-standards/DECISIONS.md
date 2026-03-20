# DECISIONS.md

## [ConsensusDevAgent documentation source of truth]
**Status:** Accepted  
**Context:** The subsystem operates inside a repository with a strict separation between implementation, standards, and design documents. The TRDs and PRDs are explicitly defined as the authoritative inputs to implementation, and the repository structure reserves `forge-docs/` for those artifacts. ConsensusDevAgent must make decisions and produce outputs that align with that document hierarchy.  
**Decision:** Treat `forge-docs/` as the authoritative source of truth for all TRDs and PRDs, and require ConsensusDevAgent to read and conform to those documents before planning, generating, reviewing, or modifying implementation artifacts.  
**Consequences:** Implementation logic, planning behavior, and review outcomes must be traceable back to artifacts in `forge-docs/`. The subsystem must not invent requirements that conflict with those documents. Standards and implementation may refine behavior, but they may not supersede TRD/PRD intent without updated documents.  
**Rejected alternatives:**  
- Treating source code as the primary source of truth was rejected because the repository structure explicitly assigns that role to TRDs and PRDs.  
- Allowing ad hoc operator instructions to override documented requirements was rejected because it weakens traceability and consensus discipline.  
- Distributing design authority across multiple folders was rejected because it increases ambiguity during arbitration and review.

## [ConsensusDevAgent is constrained by the staged build pipeline]
**Status:** Accepted  
**Context:** The build pipeline defines a fixed progression from scoping through planning, generation, review, and CI. ConsensusDevAgent participates in this pipeline and must respect stage contracts rather than acting as a free-form coding agent. The README and TRD references define this as the core operational loop.  
**Decision:** Implement ConsensusDevAgent as a stage-bound subsystem that only performs actions permitted by the current pipeline stage and hands off outputs in the documented order: Scope, PRD Plan, PRD Generation, PR Plan, Code Generation, 3-Pass Review, and CI.  
**Consequences:** The subsystem must maintain explicit awareness of stage boundaries, required inputs, and expected outputs. It cannot skip directly from intent to code, bypass review, or collapse intermediate artifacts. Observability and audit data must preserve the stage sequence.  
**Rejected alternatives:**  
- A single-pass “generate everything from prompt” workflow was rejected because it conflicts with the defined build pipeline and removes structured checkpoints.  
- Allowing arbitrary stage skipping based on confidence was rejected because it undermines repeatability and auditability.  
- Merging review into generation was rejected because the pipeline explicitly requires a distinct 3-pass review stage.

## [No undo on gate decisions]
**Status:** Accepted  
**Context:** The requirements explicitly state “No undo on gate decisions” and reference gate behavior as part of build pipeline operation and security enforcement. This must be made explicit because ConsensusDevAgent will surface and enforce gates during execution.  
**Decision:** Once ConsensusDevAgent raises or records a gate decision, it must treat that decision as irreversible within the current pipeline execution. It may only stop, log, escalate, or await operator action; it must never auto-clear, auto-retry past, or silently reverse a gate.  
**Consequences:** Gate handling logic must be append-only and monotonic. UI, logs, and audit records must reflect that a gate was reached and cannot be undone in-process. Recovery requires a new explicit operator-driven action or a new pipeline run, not an internal rollback.  
**Rejected alternatives:**  
- Allowing automatic ungating after a subsequent successful check was rejected because it contradicts the explicit no-undo requirement.  
- Permitting manual in-memory reversal by the agent was rejected because it breaks audit integrity.  
- Hiding superseded gate states from the operator was rejected because it weakens traceability.

## [SECURITY_REFUSAL is a hard stop]
**Status:** Accepted  
**Context:** Security controls require `SECURITY_REFUSAL` handling in every generation system prompt and specify that when it appears in output, the PR must stop, gate, and log, with no auto-bypass. ConsensusDevAgent is responsible for generation and arbitration behavior, so it must enforce this consistently.  
**Decision:** Treat any `SECURITY_REFUSAL` emitted during generation, review, or related model output as a hard-stop event: stop the PR flow, raise a gate, log the event, and never auto-bypass or continue execution using that output.  
**Consequences:** ConsensusDevAgent must inspect model outputs for `SECURITY_REFUSAL`, terminate downstream actions immediately, and persist the event to the audit trail. Arbitration logic must not select, sanitize, or partially reuse refused output. Operator intervention is required before any subsequent action.  
**Rejected alternatives:**  
- Stripping the refusal token and continuing with the remaining content was rejected because it defeats the security control.  
- Automatically retrying with a modified prompt and hiding the original refusal was rejected because the requirement mandates stop, gate, and log behavior.  
- Treating refusal as a soft warning was rejected because the security controls define it as a blocking condition.

## [Security review is mandatory and cannot be bypassed]
**Status:** Accepted  
**Context:** The mandatory security controls require all generated code to pass Pass 3 security review, including bandit, and the build pipeline defines a dedicated 3-pass review stage. ConsensusDevAgent cannot claim consensus-complete output until security review has executed.  
**Decision:** Require every generated code change handled by ConsensusDevAgent to pass the full 3-pass review sequence, with Pass 3 security review mandatory and non-bypassable before PR completion or progression to finalization.  
**Consequences:** Consensus decisions on code quality remain provisional until the security pass completes successfully. The subsystem must integrate security findings into gating and audit behavior. Performance or correctness success cannot compensate for missing or failed security review.  
**Rejected alternatives:**  
- Skipping security review for low-risk or documentation-only code paths was rejected because the requirement states all generated code must pass Pass 3.  
- Running only correctness and performance review was rejected because it conflicts with the explicit 3-pass contract.  
- Allowing operator preference to bypass security review was rejected because the control is mandatory.

## [All file writes must use validated paths]
**Status:** Accepted  
**Context:** Security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may generate or modify files as part of code generation and related artifact production, so path handling must be constrained centrally.  
**Decision:** Validate every filesystem write path through `path_security.validate_write_path()` before ConsensusDevAgent creates, overwrites, appends, or otherwise mutates any file.  
**Consequences:** File output code must be structured to centralize write operations behind validated path APIs. Direct writes, ad hoc path joins, and bypass code paths are not permitted. Failures in validation must halt the relevant operation and be surfaced through standard gate or error handling.  
**Rejected alternatives:**  
- Validating only user-supplied paths was rejected because generated paths can also be unsafe.  
- Performing best-effort validation only in high-risk stages was rejected because the requirement applies to every file path before write.  
- Relying on repository-relative path normalization alone was rejected because it is weaker than the mandated validation function.

## [Untrusted review comments must remain explicitly labeled]
**Status:** Accepted  
**Context:** Security controls state that PR review comments must be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. ConsensusDevAgent may consume review feedback during arbitration, code revision, or summarization, and must preserve trust boundaries when presenting external input to models.  
**Decision:** Preserve and inject PR review comments into model prompts only with the explicit `[UNTRUSTED REVIEWER COMMENT]` label, and never present such comments as trusted instructions, requirements, or system-authoritative guidance.  
**Consequences:** Prompt construction must maintain provenance and trust annotations for reviewer-supplied content. The subsystem must ensure external review input influences decisions only as untrusted evidence to be evaluated, not obeyed. This reduces prompt-injection risk from review channels.  
**Rejected alternatives:**  
- Merging reviewer comments into plain-language prompt context without labels was rejected because it erases trust boundaries.  
- Treating repository collaborator comments as trusted by default was rejected because the security requirement labels PR review comments as untrusted.  
- Omitting reviewer comments entirely was rejected because they are still useful inputs when correctly labeled.

## [Flagged chunks require operator gate before use]
**Status:** Accepted  
**Context:** Security controls specify that when a flagged chunk is used in generation, a gate card must be shown to the operator before proceeding. ConsensusDevAgent may retrieve, assemble, or reuse text fragments during generation and therefore must recognize flagged content as a controlled input.  
**Decision:** If ConsensusDevAgent is about to use any flagged chunk in generation, it must pause execution, present a gate to the operator, and await explicit operator approval before continuing.  
**Consequences:** Retrieval and prompt-assembly logic must carry flagged-state metadata through to generation time. The subsystem cannot silently include flagged content in context windows. Audit records must show that flagged material was present and that operator gating occurred before use.  
**Rejected alternatives:**  
- Auto-allowing flagged chunks when confidence is high was rejected because the requirement mandates an operator gate.  
- Silently dropping all flagged chunks was rejected because some may be legitimately needed and the specified control is gating, not blanket exclusion.  
- Deferring disclosure until after generation was rejected because the gate must occur before proceeding.

## [Claude-defined stage contracts govern pipeline behavior where referenced]
**Status:** Accepted  
**Context:** The pipeline notes reference TRD-3 for full stage contracts, error escalation, and the audit trail schema, and associated implementation notes indicate Claude-authored stage definitions for build pipeline behavior. ConsensusDevAgent needs a concrete authority for stage semantics and escalation handling.  
**Decision:** Follow the documented stage contracts, error escalation rules, and audit trail expectations referenced from TRD-3 as binding operational constraints for ConsensusDevAgent behavior.  
**Consequences:** The subsystem must not invent alternative transition semantics, custom escalation shortcuts, or incompatible audit formats. Error handling and consensus outcomes must map to the documented stage model. This decision constrains orchestration, persistence, and observability design.  
**Rejected alternatives:**  
- Defining subsystem-local stage semantics independent of TRD-3 was rejected because it would fragment pipeline behavior.  
- Using informal runtime behavior as the source of truth was rejected because stage contracts must be documentable and auditable.  
- Allowing per-agent interpretation of escalation rules was rejected because it would produce inconsistent gate behavior.

## [ConsensusDevAgent must preserve auditability across all blocking and security events]
**Status:** Accepted  
**Context:** Multiple requirements reference audit trail expectations, security logging, and gate recording. Because ConsensusDevAgent mediates generation, review, and arbitration, it is a key source of evidence for why changes progressed or stopped.  
**Decision:** Record auditable events for stage transitions, gate creation, `SECURITY_REFUSAL` incidents, path-validation failures, flagged-chunk approvals, and review-pass outcomes in a durable, append-oriented audit trail compatible with the pipeline’s documented schema.  
**Consequences:** The subsystem must emit structured records rather than relying on transient console output. Operators and downstream systems must be able to reconstruct why a run stopped, what inputs were considered unsafe, and which approvals were obtained. This increases implementation complexity but is required for traceability and security posture.  
**Rejected alternatives:**  
- Logging only final success or failure was rejected because it is insufficient for gate and security investigations.  
- Using unstructured text logs alone was rejected because they are hard to validate against stage contracts and audit schemas.  
- Allowing mutable audit entries was rejected because gate and security events require durable history.