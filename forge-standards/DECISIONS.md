# DECISIONS.md

## [ConsensusDevAgent repositories must treat `forge-docs/` as the source of truth]
**Status:** Accepted  
**Context:** The subsystem operates inside a repository structure where all TRDs and PRDs are stored under `forge-docs/`. The provided repository guidance explicitly states that all TRDs and PRDs live there and must be read before building. The README repository layout also establishes `forge-docs/` as the location for source design documents. Consensus behavior depends on consistent access to the same authoritative specifications.  
**Decision:** Implement ConsensusDevAgent so that it reads requirements and design inputs from `forge-docs/` as the authoritative document source before planning, generation, review, or gating. Do not treat prompts, ad hoc notes, or generated summaries as a substitute for repository documents.  
**Consequences:**  
- All planning and generation flows must resolve against documents in `forge-docs/`.  
- The subsystem must not proceed as if undocumented intent is authoritative when repository docs exist.  
- Implementations must preserve traceability from decisions and outputs back to TRD/PRD artifacts in `forge-docs/`.  
- Tooling and prompts must be designed assuming the document store is repository-backed and checked in.  
**Rejected alternatives:**  
- **Use transient prompt context as the primary source of truth:** Rejected because it breaks traceability and allows implementation to drift from approved documents.  
- **Store design inputs across multiple top-level folders:** Rejected because the repository contract already centralizes TRDs/PRDs in `forge-docs/`, and fragmentation would weaken consistency.  
- **Allow generated intermediate summaries to override TRDs:** Rejected because summaries are derivative artifacts and may omit normative constraints.

## [ConsensusDevAgent must align with the staged build pipeline]
**Status:** Accepted  
**Context:** The build pipeline is defined as the core loop, triggered by `/prd start <intent>`, with explicit stages from scope confirmation through review and audit. ConsensusDevAgent participates in a larger multi-stage workflow and therefore must not invent a conflicting execution model. The TRD excerpts also reference stage contracts, escalation behavior, and audit trail requirements.  
**Decision:** Design ConsensusDevAgent to operate as a pipeline-bound subsystem that supports the documented stages: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, and 3-Pass Review. Any consensus logic must integrate into these stages rather than bypass them or collapse them into a single opaque step.  
**Consequences:**  
- Consensus outputs must be attributable to a pipeline stage.  
- Internal APIs and state machines must preserve stage boundaries for auditability and operator control.  
- The subsystem must support handoff into review and gating rather than directly finalizing code without staged checks.  
- Error handling and escalation must fit the stage model documented elsewhere.  
**Rejected alternatives:**  
- **Single-pass autonomous implementation flow:** Rejected because it conflicts with the required staged workflow and would reduce auditability and controllability.  
- **Custom ConsensusDevAgent-specific stage model:** Rejected because it would diverge from the documented repository-wide pipeline and complicate integration.  
- **Embedding review into generation with no explicit review stage:** Rejected because the build pipeline requires a separate 3-pass review phase.

## [Gate decisions are final and must not support undo]
**Status:** Accepted  
**Context:** The design inputs explicitly state “No undo on gate decisions — document this explicitly” and repeat “No undo on gate decisions” in pipeline guidance. Because ConsensusDevAgent will produce or respond to gate outcomes, the subsystem must preserve finality to maintain an auditable, tamper-resistant process.  
**Decision:** Treat every gate decision handled by ConsensusDevAgent as immutable once recorded. Do not implement undo, rollback, silent reversal, or post hoc mutation of gate outcomes. Any subsequent change in course must be represented as a new decision event, not an edit to the prior one.  
**Consequences:**  
- The audit model must be append-only for gate outcomes.  
- UI, API, and storage layers must not expose “undo gate,” “reopen by edit,” or equivalent functionality.  
- Recovery from an incorrect gate requires a new explicit operator-mediated decision, preserving history.  
- Consumers of gate state must be designed for event sequencing rather than mutable status overwrites.  
**Rejected alternatives:**  
- **Allow operator undo for convenience:** Rejected because it breaks audit integrity and contradicts explicit requirements.  
- **Permit administrative reversal by editing stored gate status:** Rejected because silent mutation destroys provenance.  
- **Auto-clear failed gates after regeneration:** Rejected because it would function as an implicit undo and obscure decision history.

## [SECURITY_REFUSAL must be treated as a hard stop]
**Status:** Accepted  
**Context:** Security controls require `SECURITY_REFUSAL` rules in every generation system prompt and specify that `SECURITY_REFUSAL` in output must stop the PR, gate, log, and never auto-bypass. ConsensusDevAgent will process model outputs and therefore must honor this as a mandatory security invariant.  
**Decision:** Implement ConsensusDevAgent so that detection of `SECURITY_REFUSAL` in any relevant LLM output immediately stops the current PR flow, raises a gate, records the event in the audit trail, and forbids automatic continuation or bypass.  
**Consequences:**  
- Output parsers must explicitly detect `SECURITY_REFUSAL`.  
- The subsystem must transition into a blocked/gated state instead of retrying silently past the refusal.  
- Logging and audit records for such events are mandatory.  
- Any orchestration logic must treat this condition as terminal for the current path unless a new explicit operator-driven action starts a subsequent path.  
**Rejected alternatives:**  
- **Retry automatically with a modified prompt:** Rejected because requirements explicitly prohibit auto-bypass.  
- **Treat `SECURITY_REFUSAL` as a warning and continue review:** Rejected because the specified behavior is stop, gate, and log.  
- **Filter refusal tokens from model output before downstream processing:** Rejected because it would conceal a mandatory security signal.

## [Security review is mandatory for generated code and cannot be skipped by consensus]
**Status:** Accepted  
**Context:** Mandatory security controls state that all generated code must pass Pass 3 security review, including bandit. The build pipeline also defines a distinct 3-pass review sequence: correctness, performance, and security. ConsensusDevAgent may arbitrate generation outcomes, but it cannot declare code complete without the required review stages.  
**Decision:** Require all ConsensusDevAgent-generated or ConsensusDevAgent-selected code artifacts to pass the full review pipeline, including Pass 3 security review and required security tooling, before they are considered acceptable for advancement. Consensus results do not override mandatory review gates.  
**Consequences:**  
- Consensus selection is only a candidate acceptance step, not final approval.  
- Review integration must include a security pass and associated tooling outputs.  
- The subsystem must not merge, finalize, or mark complete code that has not passed mandatory security review.  
- Audit records must show that security review occurred after generation and before advancement.  
**Rejected alternatives:**  
- **Allow consensus winner to bypass security review if confidence is high:** Rejected because mandatory controls require Pass 3 security review for all generated code.  
- **Run security checks only on changed files opportunistically without a formal pass:** Rejected because the pipeline defines an explicit security review stage.  
- **Treat prior approvals as reusable across regenerated outputs:** Rejected because each generated output must independently satisfy review requirements.

## [All file writes initiated by ConsensusDevAgent must pass path validation]
**Status:** Accepted  
**Context:** Security controls explicitly require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may generate, modify, or stage files, making file-path enforcement a mandatory implementation constraint.  
**Decision:** Validate every file path with `path_security.validate_write_path()` before any write operation initiated directly or indirectly by ConsensusDevAgent. Do not permit write operations that bypass this validation layer.  
**Consequences:**  
- File-writing abstractions must centralize through a validated path utility.  
- Ad hoc writes, temporary patch application, and generated artifact emission must all conform to the same path validation rule.  
- Security review can assume path validation is universal rather than best-effort.  
- Implementation must be structured to make bypass difficult or impossible.  
**Rejected alternatives:**  
- **Validate only user-provided paths:** Rejected because generated or derived paths are also attack surfaces.  
- **Validate only writes outside the repository root:** Rejected because the requirement is explicit for every file path before write.  
- **Rely on OS sandboxing instead of application-level validation:** Rejected because the control is mandated and provides repository-aware enforcement not guaranteed by the OS alone.

## [Untrusted review content must remain explicitly labeled in prompts and processing]
**Status:** Accepted  
**Context:** Security controls specify that PR review comments must be labeled `[UNTRUSTED REVIEWER COMMENT]` in the prompt, and flagged content used in generation must gate to an operator before proceeding. ConsensusDevAgent consumes review input as part of arbitration and iteration, so it must preserve trust boundaries.  
**Decision:** Treat reviewer-supplied PR comments and similarly untrusted external review text as untrusted input. Preserve explicit labeling such as `[UNTRUSTED REVIEWER COMMENT]` in prompts and downstream processing, and require gating to the operator before proceeding when flagged untrusted chunks are used in generation.  
**Consequences:**  
- Prompt construction must encode trust labels rather than flattening all context into a single trusted narrative.  
- The subsystem must track provenance of review content used during consensus or regeneration.  
- Flagged untrusted content cannot silently influence generation without operator visibility.  
- Review ingestion and arbitration code must distinguish repository-trusted artifacts from external comments.  
**Rejected alternatives:**  
- **Normalize all review text into trusted planning context:** Rejected because it would erase provenance and violate security control requirements.  
- **Drop untrusted comments entirely:** Rejected because review input may still be useful when clearly labeled and gated appropriately.  
- **Label only comments from unknown users:** Rejected because the requirement applies to PR review comments as untrusted prompt content, not just anonymous sources.

## [ConsensusDevAgent must preserve auditability across decisions, gates, and escalations]
**Status:** Accepted  
**Context:** The build pipeline references full stage contracts, error escalation, and the audit trail schema. Additional requirements around final gate decisions and security refusal handling depend on durable, inspectable history. ConsensusDevAgent is a decision-making subsystem and therefore must be designed for forensic traceability.  
**Decision:** Record ConsensusDevAgent decisions, gate outcomes, escalation events, and security-triggered stops as durable audit events tied to the relevant pipeline stage and artifact. Use append-only semantics for critical decision records.  
**Consequences:**  
- Data models must include decision provenance, stage association, and immutable event history.  
- Operational debugging and compliance review can reconstruct why a candidate was selected, blocked, or escalated.  
- Storage design must prefer event records over mutable summary-only state.  
- Interfaces must expose enough metadata for downstream audit consumers.  
**Rejected alternatives:**  
- **Store only current status without historical events:** Rejected because it cannot support gate finality, escalation analysis, or security forensics.  
- **Log only failures, not successful decisions:** Rejected because consensus and gate history require full traceability, not selective reporting.  
- **Keep audit data only in ephemeral runtime logs:** Rejected because durable auditability is required across stages and operator actions.