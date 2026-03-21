# DECISIONS.md

## ConsensusDevAgent repository and document source of truth
**Status:** Accepted  
**Context:** The subsystem operates inside a larger repository with strict separation between implementation, standards, and product/design documents. The build and coordination flow depends on deterministic discovery of TRDs and PRDs.  
**Decision:** Treat `forge-docs/` as the sole source of truth for all TRDs and PRDs, and implement ConsensusDevAgent to read required design inputs from that location before planning or execution. Keep implementation in `src/`, standards in `forge-standards/`, and do not duplicate authoritative requirements into code-owned paths.  
**Consequences:** ConsensusDevAgent must resolve planning and execution decisions against documents in `forge-docs/`. Any implementation shortcut that hardcodes requirements outside the documented source of truth is non-compliant. Document lookup, validation, and references must assume the repository layout defined in the shared repository structure.  
**Rejected alternatives:**  
- Reading TRDs/PRDs from ad hoc locations near implementation code was rejected because it breaks shared repository conventions and weakens traceability.  
- Duplicating requirements into subsystem-local config files was rejected because it creates drift between implementation and authoritative documents.  
- Treating standards documents as interchangeable with TRDs/PRDs was rejected because standards constrain implementation, while TRDs/PRDs define planned work and technical requirements.

## ConsensusDevAgent must align to the staged build pipeline
**Status:** Accepted  
**Context:** The subsystem participates in a repository-wide build pipeline with explicit stages and contracts. Consensus generation is not an isolated action; it feeds and is constrained by scope confirmation, PR planning, code generation, review, and gating.  
**Decision:** Implement ConsensusDevAgent as a stage-aware subsystem that respects the repository pipeline ordering: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, and 3-Pass Review. Do not allow the subsystem to skip, reorder, or silently merge stage boundaries.  
**Consequences:** Interfaces and outputs must preserve stage identity and handoff semantics. Consensus artifacts must be attributable to their pipeline stage and suitable for downstream audit and review. The subsystem cannot independently decide to advance work outside the declared stage flow.  
**Rejected alternatives:**  
- A free-form agent loop with dynamic stage ordering was rejected because it reduces auditability and weakens operator control.  
- Collapsing planning and generation into one subsystem action was rejected because the documented pipeline requires explicit decomposition and checkpoints.  
- Allowing automatic progression on ambiguous stage state was rejected because stage contracts require deterministic escalation and gating.

## No undo on gate decisions
**Status:** Accepted  
**Context:** The repository requirements explicitly state that gate decisions are final and must be documented as such. This is a critical control for security, auditability, and operator trust.  
**Decision:** Treat every gate decision made or emitted by ConsensusDevAgent as irreversible within the subsystem. Do not implement undo, rollback, silent reopening, or automatic bypass of a gate once recorded.  
**Consequences:** State models, APIs, UI affordances, and logs must not expose an “undo gate” capability. Recovery must occur through a new explicit operator-authorized action or a new pipeline attempt, not mutation of the historical gate decision. Audit trails must preserve the original gate event as final.  
**Rejected alternatives:**  
- Supporting “undo last gate” for operator convenience was rejected because it contradicts explicit repository requirements.  
- Allowing administrators to reopen gates in place was rejected because it undermines audit integrity.  
- Silently replacing a gate with a later success state was rejected because it destroys the required historical record.

## SECURITY_REFUSAL is a hard stop
**Status:** Accepted  
**Context:** Security controls require that certain model outputs trigger a refusal condition. The requirements explicitly state that `SECURITY_REFUSAL` in output stops the PR, gates progress, logs the event, and is never auto-bypassed.  
**Decision:** Detect any `SECURITY_REFUSAL` emitted during ConsensusDevAgent operation as a mandatory hard-stop condition. Stop the affected PR or work item, create a gate event, log the refusal, and require explicit operator handling. Never auto-bypass, suppress, reinterpret, or continue past the refusal.  
**Consequences:** Output parsers, orchestration logic, and persistence must reserve `SECURITY_REFUSAL` as a control signal, not ordinary text. Downstream automation must halt on detection. ConsensusDevAgent must preserve the refusal in logs and audit artifacts.  
**Rejected alternatives:**  
- Treating `SECURITY_REFUSAL` as advisory text was rejected because the security controls define it as a stop condition.  
- Automatically retrying with prompt variations until refusal disappears was rejected because it functions as an implicit bypass.  
- Allowing continuation for “low-risk” changes was rejected because the control is mandatory and not risk-optional.

## Security gates must escalate to the operator, not self-resolve
**Status:** Accepted  
**Context:** Mandatory security controls require gate cards to the operator when flagged content influences generation, and require strict handling of untrusted inputs and review comments. ConsensusDevAgent must not convert these controls into autonomous self-resolution behavior.  
**Decision:** Escalate security-relevant flags, including use of flagged chunks in generation and other mandatory gate conditions, to the operator through explicit gate artifacts. Do not let ConsensusDevAgent self-approve, self-dismiss, or continue without operator-visible escalation.  
**Consequences:** The subsystem must emit structured operator-facing gate data and pause progression until the appropriate external action occurs. Security-relevant provenance must be retained so operators can see why the gate was raised.  
**Rejected alternatives:**  
- Auto-resolving flagged content if confidence is high was rejected because the controls require operator gating.  
- Hiding low-severity security flags from the operator was rejected because it weakens the mandatory review path.  
- Reducing security events to log-only notifications was rejected because the requirement is to gate before proceeding.

## Untrusted review content must remain explicitly labeled
**Status:** Accepted  
**Context:** Security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. The subsystem must preserve trust boundaries when incorporating external review content into consensus work.  
**Decision:** Preserve and propagate explicit trust labeling for untrusted reviewer content in every prompt, intermediate artifact, and consensus input path where such content is used. Never strip, normalize away, or silently merge the label into trusted instructions.  
**Consequences:** Prompt builders and context assemblers must support trust annotations as first-class metadata. ConsensusDevAgent must maintain separation between trusted system/operator instructions and untrusted reviewer-supplied text.  
**Rejected alternatives:**  
- Sanitizing by removing the label after ingestion was rejected because it hides trust provenance from downstream model calls.  
- Treating all review comments as trusted repository input was rejected because the controls explicitly define them as untrusted.  
- Ignoring reviewer comments entirely was rejected because they may still be useful when correctly labeled and bounded.

## ConsensusDevAgent outputs must be audit-trailed
**Status:** Accepted  
**Context:** The pipeline documentation references explicit error escalation behavior and an audit trail schema. Since ConsensusDevAgent influences planning and implementation decisions, its outputs must be reconstructible for review and compliance.  
**Decision:** Record ConsensusDevAgent decisions, gate events, refusals, stage transitions, and operator escalations in an audit trail compatible with the repository’s build pipeline expectations. Do not emit unaudited consensus outcomes that materially affect execution.  
**Consequences:** The subsystem must persist structured metadata for inputs, selected outputs, arbitration results, and halt conditions. Observability is a required feature, not an optional debug mode.  
**Rejected alternatives:**  
- Keeping only ephemeral runtime logs was rejected because they are insufficient for pipeline audit needs.  
- Auditing only failures was rejected because successful consensus decisions also affect execution and must be traceable.  
- Storing only final selected output was rejected because it omits the decision path needed for review and escalation analysis.

## ConsensusDevAgent must not bypass mandatory security and review stages
**Status:** Accepted  
**Context:** Generated code is subject to mandatory controls, including security review and tool-based checks such as bandit, as well as path validation on writes. ConsensusDevAgent may influence code generation, but it cannot exempt work from these downstream obligations.  
**Decision:** Ensure all outputs from ConsensusDevAgent that lead to code changes continue through mandatory repository review and security controls. Do not mark consensus-selected changes as pre-approved, trusted-by-default, or exempt from Pass 3 security review or write-path validation.  
**Consequences:** Integration points must hand off work into existing review and write-validation mechanisms. The subsystem cannot introduce a shortcut path from consensus result to repository mutation.  
**Rejected alternatives:**  
- Trusting consensus-selected code as already reviewed was rejected because mandatory security stages still apply.  
- Letting the subsystem write files directly without shared path validation was rejected because every write path must be validated.  
- Skipping security review for documentation-only or “obvious” changes was rejected because the controls are mandatory at the pipeline level.