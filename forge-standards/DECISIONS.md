# DECISIONS.md

## ConsensusDevAgent lives in the Python backend under `src/`
**Status:** Accepted  
**Context:** The repository structure assigns Python backend implementation to `src/`, while documents remain in `forge-docs/` and standards in `forge-standards/`. The ConsensusDevAgent is part of the backend runtime and multi-agent orchestration stack, not the macOS shell. Clear placement is required so build, testing, and ownership boundaries remain unambiguous.  
**Decision:** Implement the ConsensusDevAgent subsystem in the Python backend under `src/`. Do not place subsystem logic in `forge-docs/`, `forge-standards/`, or the Swift application shell.  
**Consequences:** Backend code, tests, and interfaces for ConsensusDevAgent must follow Python project conventions and live alongside other backend runtime components. The macOS app may invoke or display results from the subsystem, but it must not contain its core decision logic. Documentation remains external to implementation.  
**Rejected alternatives:**  
- Implementing ConsensusDevAgent inside the Swift/macOS shell: rejected because the subsystem belongs to backend orchestration rather than UI.  
- Storing executable logic alongside TRDs in `forge-docs/`: rejected because `forge-docs/` is the source of truth for requirements, not runtime code.  
- Creating a standalone top-level repository area for the subsystem: rejected because it would violate the prescribed repository layout and fragment backend ownership.

## TRDs and PRDs are the controlling source of truth before implementation
**Status:** Accepted  
**Context:** Repository guidance explicitly states that all TRDs and PRDs live in `forge-docs/` and must be read before building. The ConsensusDevAgent must therefore be constrained by documented requirements rather than ad hoc implementation choices.  
**Decision:** Read and conform to applicable TRDs and PRDs in `forge-docs/` before implementing or modifying ConsensusDevAgent behavior. Treat those documents as controlling inputs for scope, interfaces, stage behavior, and security constraints.  
**Consequences:** Implementation work must be traceable to documents. Changes that conflict with TRDs/PRDs require document updates first or in lockstep. Local code convenience cannot override documented subsystem contracts.  
**Rejected alternatives:**  
- Treating code as the primary source of truth: rejected because the documented workflow places requirements and design artifacts ahead of implementation.  
- Allowing undocumented implementation drift: rejected because it breaks auditability and coordinated multi-agent development.  
- Using only README summaries instead of source TRDs/PRDs: rejected because summaries are insufficient for full contract fidelity.

## ConsensusDevAgent must operate within the staged build pipeline
**Status:** Accepted  
**Context:** The build pipeline is defined as a fixed staged process triggered by `/prd start <intent>`, including scope, PRD planning, PRD generation, PR planning, code generation, 3-pass review, and later gates. The subsystem must fit into this pipeline rather than inventing an alternate lifecycle.  
**Decision:** Design ConsensusDevAgent behavior to integrate with and respect the defined build pipeline stages. Do not bypass, collapse, or reorder mandatory stages through subsystem-specific shortcuts.  
**Consequences:** Consensus outputs must be consumable by existing stage contracts. Agent coordination must support handoff into PR planning, code generation, and review rather than replacing them. Pipeline observability and audit expectations apply to subsystem actions.  
**Rejected alternatives:**  
- Letting ConsensusDevAgent directly generate and merge code outside the stage model: rejected because it would bypass required controls and audit points.  
- Collapsing planning and review into a single consensus step: rejected because the pipeline explicitly separates responsibilities.  
- Making stage participation optional per subsystem: rejected because stage contracts are mandatory, not advisory.

## Gate decisions are irreversible
**Status:** Accepted  
**Context:** The requirements explicitly state: “No undo on gate decisions.” This must be documented explicitly and enforced in subsystem behavior because consensus and review flows may otherwise attempt to reopen or auto-reverse prior gates.  
**Decision:** Treat every gate decision made within or by ConsensusDevAgent as final and non-reversible. Do not implement undo, rollback, silent reopening, or automatic bypass of gate outcomes. Any further progress must occur through explicit subsequent process steps, not reversal of the original gate.  
**Consequences:** The subsystem must model gate transitions as append-only decisions. UI, APIs, and internal orchestration must not expose an undo action for gate outcomes. Audit trails must preserve the finality of each gate decision.  
**Rejected alternatives:**  
- Providing an operator “undo gate” action: rejected because requirements explicitly forbid undo on gate decisions.  
- Automatically reopening failed gates after regeneration: rejected because it would create an implicit undo path.  
- Mutating prior gate records in place: rejected because it destroys auditability and violates finality.

## SECURITY_REFUSAL is a hard stop, not a recoverable warning
**Status:** Accepted  
**Context:** Mandatory security controls require SECURITY_REFUSAL rules in generation prompts and state that SECURITY_REFUSAL in output must stop the PR, gate, log, and never auto-bypass. ConsensusDevAgent must therefore treat such signals as terminal security events in the active flow.  
**Decision:** On any SECURITY_REFUSAL emitted by participating models or downstream generation/review steps, immediately stop the active PR flow, create a gate, and log the event. Never auto-bypass, suppress, reinterpret, or continue past a SECURITY_REFUSAL.  
**Consequences:** Consensus arbitration cannot “vote away” a refusal. A refusal from one participant is sufficient to halt the flow. Recovery, if any, must occur through explicit operator-governed follow-up outside automatic continuation.  
**Rejected alternatives:**  
- Continuing if a majority of agents did not refuse: rejected because security refusal is mandatory and not subject to consensus override.  
- Downgrading refusal to a warning for low-risk changes: rejected because the control says stop PR, gate, and log.  
- Retrying automatically until a model stops refusing: rejected because it would function as an auto-bypass.

## Security controls apply to all generated code paths used by ConsensusDevAgent
**Status:** Accepted  
**Context:** Mandatory controls require that all generated code pass security review, that `path_security.validate_write_path()` be called on every file path before write, and that generated outputs remain subject to security handling. Since ConsensusDevAgent influences or arbitrates code generation, it must preserve these controls across all paths.  
**Decision:** Enforce mandatory generation-time and write-time security controls on every code artifact produced, selected, transformed, or emitted through ConsensusDevAgent. Validate every write path before file output and ensure generated code proceeds through required security review.  
**Consequences:** Consensus selection does not exempt an artifact from validation. Intermediate or merged outputs must be treated as generated code and reviewed accordingly. File-writing helpers in the subsystem must require path validation before persistence.  
**Rejected alternatives:**  
- Validating only final selected artifacts: rejected because intermediate and merged outputs can also introduce risk.  
- Trusting model-provided paths: rejected because every file path must be validated before write.  
- Skipping security review for consensus-approved code: rejected because approval is not a substitute for Pass 3 security review.

## Untrusted review content must remain explicitly labeled and non-authoritative
**Status:** Accepted  
**Context:** Security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts, and flagged chunks must gate to the operator before proceeding when used in generation. ConsensusDevAgent will ingest reviewer and model feedback, so trust boundaries must be preserved.  
**Decision:** Preserve explicit untrusted labeling for external review comments and any flagged content when incorporating them into ConsensusDevAgent prompts or deliberation. Do not treat such content as authoritative instructions. If flagged chunks are used in generation, gate to the operator before proceeding.  
**Consequences:** Prompt construction and evidence aggregation must carry trust metadata. Consensus logic must distinguish requirements, trusted internal outputs, and untrusted reviewer input. Operator gates are mandatory when flagged content participates in generation.  
**Rejected alternatives:**  
- Normalizing all input into a single unlabeled evidence pool: rejected because it erases trust boundaries required by security controls.  
- Treating reviewer comments as direct execution instructions: rejected because reviewer content is explicitly untrusted.  
- Silently using flagged chunks without gating: rejected because flagged usage requires operator gating before proceeding.

## Three-pass review remains mandatory after code generation
**Status:** Accepted  
**Context:** The pipeline defines Stage 6 as a 3-pass review: correctness, performance, then security. ConsensusDevAgent may improve generated output quality, but it does not replace the required review sequence.  
**Decision:** Require all ConsensusDevAgent-produced or selected implementation outputs to proceed through the full three-pass review sequence in order: correctness, performance, then security. Do not merge review passes, skip passes, or reorder them.  
**Consequences:** Consensus acceptance is provisional until review completion. Interfaces between generation and review must preserve enough metadata and artifacts for each pass. Security review remains the final mandatory review gate, including required tooling such as bandit where applicable.  
**Rejected alternatives:**  
- Replacing the 3-pass review with consensus among generators: rejected because the pipeline defines a separate review stage.  
- Running only security review: rejected because correctness and performance are also mandatory.  
- Reordering security ahead of correctness/performance: rejected because the stage contract defines the review order.

## Consensus arbitration must not override stage contracts or security outcomes
**Status:** Accepted  
**Context:** The subsystem’s purpose is to coordinate and arbitrate among multiple agents, but repository guidance and pipeline rules establish fixed contracts. Without an explicit constraint, arbitration logic could improperly supersede required process decisions.  
**Decision:** Limit ConsensusDevAgent arbitration to selecting, synthesizing, or escalating among candidate outputs within stage boundaries. Do not allow arbitration to override documented stage contracts, gate finality, SECURITY_REFUSAL outcomes, or mandatory security controls.  
**Consequences:** The subsystem is a constrained coordinator, not a superuser controller. Some disagreements must resolve to escalation or gating rather than forced consensus. Arbitration APIs and result schemas must represent “blocked” and “escalate” outcomes explicitly.  
**Rejected alternatives:**  
- Giving arbitration authority to overrule failed gates or refusals: rejected because it conflicts with mandatory controls.  
- Treating consensus as the highest authority in the pipeline: rejected because documents and stage contracts remain authoritative.  
- Forcing a winner in every disagreement: rejected because some conditions require halt or escalation, not selection.

## Auditability must be append-only for decisions, gates, and security events
**Status:** Accepted  
**Context:** The pipeline references error escalation and an audit trail schema, and gate decisions are non-undoable. To support traceability, ConsensusDevAgent records must preserve historical decisions rather than rewrite them.  
**Decision:** Record ConsensusDevAgent decisions, gate outcomes, escalations, and security events as append-only audit entries. Do not edit prior records to reflect later interpretations or reversals.  
**Consequences:** The subsystem must support chronological reconstruction of deliberation and outcomes. Storage models should prefer immutable events over mutable status replacement where feasible. Later actions must reference earlier entries instead of altering them.  
**Rejected alternatives:**  
- Updating records in place to show only the current state: rejected because it obscures decision history and undermines auditability.  
- Deleting superseded or erroneous entries: rejected because it breaks traceability.  
- Storing only final outcomes without intermediate gates/escalations: rejected because the process requires a durable audit trail.